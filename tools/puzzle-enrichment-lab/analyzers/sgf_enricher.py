"""SGF enricher — apply KataGo enrichment results to SGF properties and tree.

Policy-aligned enricher that respects ``config/sgf-property-policies.json``:

- ``enrich_if_absent``  → write only when property is missing
- ``enrich_if_partial`` → write when value is absent or fails validation
- ``override``          → always write

Properties handled:
  - **YR**: Derived from refutation branches added to the SGF tree
  - **YG**: Difficulty level slug (with configurable mismatch threshold)
  - **YX**: Complexity metrics (``d:depth;r:refutations;s:solution_length;u:unique``)

Refutation branches are added as SGF variations at root level::

    (;B[cd]C[Wrong. After this move, winrate drops to 15%.]
     ;W[dc]
     ;B[dd])

REJECTED status returns the original SGF unchanged.

See also: ADR-007 (007-adr-policy-aligned-enrichment.md)
"""

from __future__ import annotations

import importlib.util
import logging
from pathlib import Path

from core.sgf_parser import SGF, SGFNode

# Import canonical correctness inference from tools/core/sgf_correctness.py.
# This is the single source of truth for determining whether an SGF comment
# is a correctness marker (Wrong, Incorrect, -, Correct, Right, +).
# We reuse it here instead of maintaining a separate _WRONG_COMMENT_PREFIXES
# tuple, ensuring consistent detection across all tools.
_SGF_CORRECTNESS_PATH = (
    Path(__file__).resolve().parents[2] / "core" / "sgf_correctness.py"
)
_spec = importlib.util.spec_from_file_location("sgf_correctness", _SGF_CORRECTNESS_PATH)
_sgf_correctness = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_sgf_correctness)
infer_correctness_from_comment = _sgf_correctness.infer_correctness_from_comment

try:
    from config.difficulty import QualityWeightsConfig
    from core.tsumego_analysis import (
        compose_enriched_sgf,
        extract_solution_tree_moves,
        parse_sgf,
    )
    from models.ai_analysis_result import AiAnalysisResult
    from models.validation import ValidationStatus

    from analyzers.config_lookup import clear_config_caches, load_level_slug_to_id
    from analyzers.hint_generator import format_yh_property
    from analyzers.property_policy import clear_policy_cache, is_enrichment_needed
except ImportError:
    from ..analyzers.config_lookup import clear_config_caches, load_level_slug_to_id
    from ..analyzers.hint_generator import format_yh_property
    from ..analyzers.property_policy import clear_policy_cache, is_enrichment_needed
    from ..config.difficulty import QualityWeightsConfig
    from ..core.tsumego_analysis import (
        compose_enriched_sgf,
        extract_solution_tree_moves,
        parse_sgf,
    )
    from ..models.ai_analysis_result import AiAnalysisResult
    from ..models.validation import ValidationStatus

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Level mismatch configuration
# ---------------------------------------------------------------------------

_ENRICHMENT_CONFIG_PATH = Path(__file__).resolve().parents[3] / "config" / "katago-enrichment.json"

# Overwrite existing YG only when the suggested level differs by at least
# this many level steps.
_MISMATCH_THRESHOLD = 3


def _compute_level_distance(slug_a: str, slug_b: str) -> int:
    """Compute distance between two level slugs in steps.

    Uses numeric IDs from puzzle-levels.json. The gap between kyu (160)
    and dan (210) counts as 5 steps (50 / 10).

    Returns 0 if either slug is unknown.
    """
    ids = load_level_slug_to_id()
    id_a = ids.get(slug_a, 0)
    id_b = ids.get(slug_b, 0)
    if not id_a or not id_b:
        return 0
    return abs(id_a - id_b) // 10


def clear_enricher_cache() -> None:
    """Clear all caches (for testing)."""
    clear_config_caches()
    clear_policy_cache()


# ---------------------------------------------------------------------------
# Refutation branch detection
# ---------------------------------------------------------------------------


def _is_terse_correctness_label(comment: str) -> bool:
    """Check whether a comment is ONLY a terse correctness marker.

    Terse markers are short labels that convey correctness status but carry
    no teaching content (e.g. ``Wrong``, ``Incorrect.``, ``Correct!``,
    ``Right``, ``+``, ``-``).  These are safe to *replace* with a richer
    teaching comment because no pedagogical information is lost.

    In contrast, substantive comments like ``Wrong — this loses the corner``
    contain author-written teaching text **beyond** the marker prefix and
    should be preserved via append, not replacement.

    Detection uses the canonical ``infer_correctness_from_comment()`` from
    ``tools/core/sgf_correctness.py`` which recognises all established
    correctness conventions found across 80,000+ SGF files from 9 sources:

      Wrong markers:   "wrong…", "incorrect…", "-"
      Correct markers: "correct…", "right…", "+"

    A comment is terse when:
      1. It is recognised as a correctness marker by the canonical utility, AND
      2. Stripping the marker prefix leaves nothing meaningful (only
         punctuation and whitespace).
    """
    stripped = comment.strip()
    if not stripped:
        return False

    # Must be a known correctness marker at all
    if infer_correctness_from_comment(stripped) is None:
        return False

    # Exact single-char markers: "+" and "-"
    if stripped in ("+", "-"):
        return True

    # Strip the known prefix and check if anything meaningful remains.
    # The canonical prefixes are: wrong, incorrect, correct, right
    lower = stripped.lower()
    for prefix in ("wrong", "incorrect", "correct", "right"):
        if lower.startswith(prefix):
            remainder = stripped[len(prefix):]
            # Terse if remainder is only punctuation/whitespace
            # e.g. "Wrong.", "Wrong!", "Incorrect;", "Correct! "
            if not remainder.strip(" \t.!;:—-"):
                return True
            return False

    return False


def _has_existing_refutation_branches(root) -> bool:
    """Check whether the SGF tree already has wrong-move branches.

    Detection uses the canonical ``infer_correctness_from_comment()`` from
    ``tools/core/sgf_correctness.py`` (three-layer system) to recognise all
    established correctness conventions across sources:

    - Layer 1: WV (Wrong Variation) or BM (Bad Move) SGF property markers
    - Layer 2: Comment text recognised as a wrong marker by the canonical
      utility ("wrong", "incorrect", or exact "-")
    """
    for child in root.children:
        # Layer 1: WV marker (kisvadim-goproblems, gotools)
        if child.get_property("WV") and "WV" in child.properties:
            return True

        # Layer 1: BM marker
        if child.get_property("BM"):
            return True

        # Layer 2: canonical comment-based correctness inference
        comment = child.get_property("C", "")
        if comment and infer_correctness_from_comment(comment) is False:
            return True

    return False


def _count_existing_refutation_branches(root) -> int:
    """Count existing wrong-move branches in the SGF tree.

    Uses the same detection logic as ``_has_existing_refutation_branches``
    but returns the count instead of a boolean. Each direct child of root
    that is detected as a wrong branch is counted.
    """
    count = 0
    for child in root.children:
        if child.get_property("WV") and "WV" in child.properties:
            count += 1
            continue
        if child.get_property("BM"):
            count += 1
            continue
        comment = child.get_property("C", "")
        if comment and infer_correctness_from_comment(comment) is False:
            count += 1
    return count


def _collect_existing_wrong_coords(root) -> set[str]:
    """Collect SGF coordinates of existing wrong-move branches.

    Returns a set of move coordinates for all root-level children detected
    as wrong branches. Used to dedup AI branches against curated wrongs.
    """
    coords: set[str] = set()
    for child in root.children:
        is_wrong = False
        if child.get_property("WV") and "WV" in child.properties:
            is_wrong = True
        elif child.get_property("BM"):
            is_wrong = True
        else:
            comment = child.get_property("C", "")
            if comment and infer_correctness_from_comment(comment) is False:
                is_wrong = True
        if is_wrong:
            coord = _get_node_move_coord_from_child(child)
            if coord:
                coords.add(coord)
    return coords


def _get_node_move_coord_from_child(node) -> str | None:
    """Extract the SGF coordinate from a child node's B or W property."""
    for color in ("B", "W"):
        val = node.get_property(color)
        if val:
            return val
    return None


def _load_max_refutation_root_trees() -> int:
    """Load max_refutation_root_trees from enrichment config.

    Reads from katago-enrichment.json → ai_solve.solution_tree.max_refutation_root_trees.
    Falls back to 3 if config loading fails.
    """
    try:
        try:
            from config import load_enrichment_config
        except ImportError:
            from ..config import load_enrichment_config
        return load_enrichment_config().ai_solve.solution_tree.max_refutation_root_trees
    except Exception:
        logger.warning("Failed to load max_refutation_root_trees from config; using default 3")
        return 3


# ---------------------------------------------------------------------------
# Refutation branch building
# ---------------------------------------------------------------------------


def _build_refutation_branches(
    result: AiAnalysisResult,
    player_color: str,
) -> list[dict]:
    """Build refutation branch dicts from enrichment result.

    Each branch is a dict with:
      - wrong_move: SGF coordinate of the wrong first move
      - color: player color ("B" or "W")
      - refutation: list of (color, coord) tuples for the response PV
      - comment: "Wrong. After this move, ..."
    """
    opponent_color = "W" if player_color == "B" else "B"
    branches = []

    for ref in result.refutations:
        if not ref.wrong_move:
            continue

        raw_branches = ref.refutation_branches or []
        if not raw_branches:
            raw_branches = [ref.refutation_pv] if ref.refutation_pv else []

        delta_pct = abs(ref.delta) * 100
        for branch_index, pv_branch in enumerate(raw_branches, start=1):
            moves: list[tuple[str, str]] = []
            for i, sgf_coord in enumerate(pv_branch):
                if sgf_coord:
                    color = opponent_color if i % 2 == 0 else player_color
                    moves.append((color, sgf_coord))

            if not moves:
                continue

            comment = "Wrong."
            logger.debug(
                "Refutation %s: delta=%.1f%%, branch %d/%d",
                ref.wrong_move, delta_pct, branch_index, len(raw_branches),
            )

            branches.append({
                "wrong_move": ref.wrong_move,
                "color": player_color,
                "refutation": moves,
                "comment": comment,
            })

    return branches


# ---------------------------------------------------------------------------
# Teaching comment embedding (Phase 3)
# ---------------------------------------------------------------------------


def _get_node_move_coord(node: SGFNode) -> str | None:
    """Get the SGF coordinate of the move on a KaTrain SGFNode."""
    if node.move is not None:
        return node.move.sgf(node.board_size)
    for color in ("B", "W"):
        if color in node.properties:
            return node.get_property(color)
    return None


def _append_node_comment(node: SGFNode, text: str) -> None:
    """Append text to a node's C[] property with \\n\\n separator."""
    existing = node.get_property("C", "")
    if existing:
        node.set_property("C", f"{existing}\n\n{text}")
    else:
        node.set_property("C", text)


def _embed_teaching_comments(
    sgf_text: str,
    correct_comment: str,
    wrong_comments: dict[str, str],
    vital_comment: str = "",
    vital_node_index: int | None = None,
) -> str:
    """Embed teaching comments as C[] on solution tree nodes via sgfmill.

    - correct_comment → C[] on the first child of root (correct line)
    - vital_comment → C[] on the vital node (at vital_node_index in main line)
    - wrong_comments[coord] → append to C[] on matching refutation branch roots
    - Appends to existing C[] with ``\\n\\n`` separator (never overwrites)
    - No-op when all are empty
    """
    if not correct_comment and not wrong_comments and not vital_comment:
        return sgf_text

    try:
        root = SGF.parse_sgf(sgf_text)
    except Exception as e:
        logger.error("Failed to parse SGF for teaching comment embedding: %s", e)
        return sgf_text

    if not root.children:
        return sgf_text

    # Correct comment on first child (main line = correct move by SGF convention)
    if correct_comment:
        marked = f"Correct. {correct_comment}" if not correct_comment.startswith("Correct") else correct_comment
        _append_node_comment(root.children[0], marked)

    # Vital comment on the vital node (F16: deeper in solution tree)
    if vital_comment and vital_node_index is not None and vital_node_index > 0:
        node = root.children[0]  # Start at first child (main line)
        for _step in range(vital_node_index - 1):
            if node.children:
                node = node.children[0]  # Follow main line
            else:
                logger.warning(
                    "Vital node index %d exceeds tree depth; skipping vital comment.",
                    vital_node_index,
                )
                node = None
                break
        if node is not None:
            marked_vital = f"Correct. {vital_comment}" if not vital_comment.startswith("Correct") else vital_comment
            _append_node_comment(node, marked_vital)

    # Wrong comments on matching refutation branch root nodes.
    # When the node already has a terse correctness label (e.g. "Wrong",
    # "Incorrect.", "-") we REPLACE it with the teaching comment because
    # terse labels carry no teaching value — the richer text is strictly
    # better.  Substantive author comments (e.g. "Wrong — loses corner")
    # are preserved via append so no pedagogical content is lost.
    # Detection uses the canonical infer_correctness_from_comment() from
    # tools/core/sgf_correctness.py which recognises all established
    # correctness conventions (wrong/incorrect/-/correct/right/+).
    if wrong_comments:
        for child in root.children:
            coord = _get_node_move_coord(child)
            if coord and coord in wrong_comments:
                text = wrong_comments[coord]
                # RC-1: All wrong-move comments get canonical "Wrong." prefix
                # so infer_correctness_from_comment() can detect them.
                marked = f"Wrong. {text}" if not text.startswith("Wrong") else text

                existing = child.get_property("C", "")
                if _is_terse_correctness_label(existing):
                    # Terse label (e.g. "Wrong", "Incorrect.", "-") →
                    # replace with richer teaching comment
                    child.set_property("C", marked)
                elif existing:
                    # Substantive comment → append to preserve
                    _append_node_comment(child, marked)
                else:
                    # No existing comment → set directly
                    child.set_property("C", marked)

    return root.sgf()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def enrich_sgf(sgf_text: str, result: AiAnalysisResult) -> str:
    """Apply enrichment results to SGF properties and tree structure.

    Respects property policies from ``config/sgf-property-policies.json``:
    - ``enrich_if_absent``: write only when property is missing
    - ``enrich_if_partial``: write when value is absent or invalid
    - ``override``: always write

    Adds refutation branches to the SGF tree if none exist, then derives
    the ``YR`` property from the branch root moves.

    Args:
        sgf_text: Original SGF string.
        result: AiAnalysisResult from KataGo enrichment.

    Returns:
        Enriched SGF string. If status=REJECTED, returns unchanged.
    """
    status = result.validation.status

    # REJECTED → return original unchanged
    if status == ValidationStatus.REJECTED:
        logger.info(
            "Skipping enrichment for puzzle %s: status=REJECTED",
            result.puzzle_id,
        )
        return sgf_text

    # Parse SGF tree for inspection
    try:
        root = parse_sgf(sgf_text)
    except Exception as e:
        logger.error("Failed to parse SGF for enrichment: %s", e)
        return sgf_text

    # Extract solution tree for YX metrics
    solution_moves = extract_solution_tree_moves(root)

    # Determine player color from PL property
    player_color = root.get_property("PL", "B")

    # ------------------------------------------------------------------
    # Phase 1: Refutation branches (SGF tree modification)
    # ------------------------------------------------------------------
    refutation_branches: list[dict] = []
    needs_tree_rewrite = False

    if result.refutations:
        # Count existing curated wrong branches and cap AI additions
        existing_count = _count_existing_refutation_branches(root)
        max_total = _load_max_refutation_root_trees()
        budget = max(0, max_total - existing_count)

        if budget > 0:
            # Collect coordinates of existing curated wrong branches for dedup
            existing_coords = _collect_existing_wrong_coords(root)

            all_branches = _build_refutation_branches(result, player_color)
            # Dedup: skip AI branches whose coord already exists in curated
            deduped = [b for b in all_branches if b["wrong_move"] not in existing_coords]
            refutation_branches = deduped[:budget]

            if refutation_branches:
                needs_tree_rewrite = True
                logger.info(
                    "Adding %d refutation branches to puzzle %s "
                    "(existing=%d, budget=%d, deduped=%d)",
                    len(refutation_branches),
                    result.puzzle_id,
                    existing_count,
                    budget,
                    len(all_branches) - len(deduped),
                )
        else:
            logger.debug(
                "Puzzle %s already has %d wrong branches (cap=%d); "
                "skipping AI refutation branch addition",
                result.puzzle_id,
                existing_count,
                max_total,
            )

    # If we need to add branches, rewrite the SGF tree first
    if needs_tree_rewrite:
        sgf_text = compose_enriched_sgf(root, refutation_branches)

    # ------------------------------------------------------------------
    # Phase 2: Root property enrichment (policy-driven)
    # ------------------------------------------------------------------
    patches: dict[str, str] = {}

    # YR — derive from ALL wrong first-move coords in the tree
    existing_yr = root.get_property("YR", "")
    if refutation_branches:
        # We added AI branches → combine curated + AI coords
        all_coords: set[str] = _collect_existing_wrong_coords(root)
        for b in refutation_branches:
            if b.get("wrong_move"):
                all_coords.add(b["wrong_move"])
        yr_value = ",".join(sorted(all_coords))
        if yr_value:
            patches["YR"] = yr_value
    elif is_enrichment_needed("YR", existing_yr):
        # No AI branches added but YR absent → index curated wrongs
        curated_coords = _collect_existing_wrong_coords(root)
        if curated_coords:
            patches["YR"] = ",".join(sorted(curated_coords))

    # YG — difficulty level (with mismatch threshold)
    existing_yg = root.get_property("YG", "")
    suggested_level = result.difficulty.suggested_level
    if suggested_level and suggested_level != "unknown":
        if is_enrichment_needed("YG", existing_yg):
            # Policy says enrich (absent) → set it
            patches["YG"] = suggested_level
        elif existing_yg:
            # Existing value present — check level mismatch threshold
            threshold = _MISMATCH_THRESHOLD
            distance = _compute_level_distance(existing_yg, suggested_level)
            if distance > threshold:
                patches["YG"] = suggested_level
                logger.warning(
                    "Level mismatch overwrite for puzzle %s: "
                    "existing=%s (distance=%d steps > threshold=%d) -> %s",
                    result.puzzle_id,
                    existing_yg,
                    distance,
                    threshold,
                    suggested_level,
                )

    # YX — complexity metrics (enrich_if_partial)
    existing_yx = root.get_property("YX", "")
    if is_enrichment_needed("YX", existing_yx):
        yx_value = _build_yx(result, solution_moves)
        if yx_value:
            patches["YX"] = yx_value

    # S3-G4: YQ — quality metrics with AC field
    existing_yq = root.get_property("YQ", "")
    if is_enrichment_needed("YQ", existing_yq) or existing_yq:
        yq_value = _build_yq(result, existing_yq)
        if yq_value:
            patches["YQ"] = yq_value

    # YT — technique tags (enrich_if_absent)
    existing_yt = root.get_property("YT", "")
    if result.technique_tags and is_enrichment_needed("YT", existing_yt):
        patches["YT"] = ",".join(sorted(result.technique_tags))

    # YH — hints (enrich_if_absent, skip if all hints are empty)
    if result.hints and is_enrichment_needed("YH", root.get_property("YH", "")):
        yh_value = format_yh_property(result.hints)
        if yh_value:
            patches["YH"] = yh_value

    # Apply property patches to SGF string (after tree rewrite if any)
    if patches:
        sgf_text = _apply_patches(sgf_text, patches)

    # ------------------------------------------------------------------
    # Phase 3: Teaching comment embedding (solution tree C[] properties)
    # ------------------------------------------------------------------
    tc = result.teaching_comments
    teaching_embedded = False
    if tc:
        correct_comment = tc.get("correct_comment", "")
        wrong_comments = tc.get("wrong_comments", {})
        vital_comment = tc.get("vital_comment", "")
        vital_node_index = tc.get("vital_node_index")
        if correct_comment or wrong_comments or vital_comment:
            sgf_text = _embed_teaching_comments(
                sgf_text, correct_comment, wrong_comments,
                vital_comment=vital_comment,
                vital_node_index=vital_node_index,
            )
            teaching_embedded = True

    if not patches and not needs_tree_rewrite and not teaching_embedded:
        logger.debug("No enrichment needed for puzzle %s", result.puzzle_id)
        return sgf_text

    logger.info(
        "Enriched puzzle %s: status=%s, properties=%s, branches=%d",
        result.puzzle_id,
        status.value,
        list(patches.keys()),
        len(refutation_branches),
    )

    return sgf_text


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _compute_qk(
    trap_density: float,
    avg_refutation_depth: float,
    correct_move_rank: int,
    policy_entropy: float,
    total_visits: int,
    weights: QualityWeightsConfig,
) -> int:
    """Compute qk quality score (0-5) using panel-validated algorithm (GQ-1).

    Weights loaded from config (C3). Visit-count gate at rank_min_visits (C4).
    """
    def normalize(value: float, min_val: float, max_val: float) -> float:
        if max_val <= min_val:
            return 0.0
        return max(0.0, min(1.0, (value - min_val) / (max_val - min_val)))

    qk_raw = (
        weights.trap_density * normalize(trap_density, 0.0, 1.0)
        + weights.avg_refutation_depth * normalize(avg_refutation_depth, 0, weights.avg_depth_max)
        + weights.correct_move_rank * normalize(
            max(1, min(correct_move_rank, weights.rank_clamp_max)),
            1, weights.rank_clamp_max,
        )
        + weights.policy_entropy * normalize(policy_entropy, 0.0, 1.0)
    )

    if total_visits < weights.rank_min_visits:
        qk_raw *= weights.low_visit_multiplier

    return max(0, min(5, round(qk_raw * 5)))


def _build_yq(result: AiAnalysisResult, existing_yq: str) -> str:
    """Build or update YQ property with AC and qk fields (S3-G4, GQ-1).

    Format: q:{quality};rc:{refutation_confidence};hc:{hint_confidence};ac:{ac_level};qk:{qk}

    Preserves existing q/rc/hc values when present; always sets ac and qk from result.
    """
    # Parse existing YQ fields
    q_val = "0"
    rc_val = "0"
    hc_val = "0"
    if existing_yq:
        for part in existing_yq.split(";"):
            if ":" in part:
                key, val = part.split(":", 1)
                if key == "q":
                    q_val = val
                elif key == "rc":
                    rc_val = val
                elif key == "hc":
                    hc_val = val

    ac_val = str(getattr(result, "ac_level", 0))

    # Compute qk from result signals + config weights
    try:
        from config import load_enrichment_config
    except ImportError:
        from ..config import load_enrichment_config
    weights = load_enrichment_config().quality_weights

    trap_density = getattr(result.difficulty, "trap_density", 0.0)
    if trap_density < 0:
        trap_density = 0.0
    avg_ref_depth = 0.0
    if result.refutations:
        avg_ref_depth = sum(r.refutation_depth for r in result.refutations) / len(result.refutations)
    correct_move_rank = getattr(result.difficulty, "correct_move_rank", -1)
    if correct_move_rank < 0:
        correct_move_rank = 0
    policy_entropy = getattr(result.difficulty, "policy_entropy", -1.0)
    if policy_entropy < 0:
        policy_entropy = 0.0
    total_visits = getattr(result.difficulty, "visits_to_solve", 0)
    if total_visits < 0:
        total_visits = 0

    qk_val = _compute_qk(
        trap_density=trap_density,
        avg_refutation_depth=avg_ref_depth,
        correct_move_rank=correct_move_rank,
        policy_entropy=policy_entropy,
        total_visits=total_visits,
        weights=weights,
    )

    return f"q:{q_val};rc:{rc_val};hc:{hc_val};ac:{ac_val};qk:{qk_val}"


def _build_yx(result: AiAnalysisResult, solution_moves: list[str]) -> str:
    """Build YX complexity value from enrichment result.

    Format: d:{depth};r:{refutation_count};s:{solution_length};u:{unique};w:{wrong_count};a:{avg_ref_depth};b:{branch_count};t:{trap_pct}
    where:
      d = solution tree depth (number of moves in main line)
      r = number of refutations generated
      s = solution length (total moves in solution PV)
      u = unique correct first move indicator (1=unique, 0=miai)
          Per pipeline canonical definition in core/complexity.py:
          u is a BINARY field indicating whether there is exactly one
          correct first move (u=1) or multiple equivalent first moves (u=0).
      w = count of distinct wrong first moves found
      a = average refutation depth (rounded integer, 0 if no refutations)
      b = branch count from difficulty snapshot (0 if unavailable)
      t = trap density as integer percentage 0-100 (0 if unavailable)

    P0.1 fix: Align `u` with pipeline's canonical binary definition.
    Previous code computed u = count of unique wrong moves (0-N), which
    conflicts with the pipeline's `is_unique_first_move()` semantics.
    Wrong-move count is now tracked as the separate `w` field.
    """
    solution_length = len(solution_moves) if solution_moves else 0
    depth = solution_length
    refutation_count = len(result.refutations)

    # P0.1: u = binary unique-correct-first-move indicator
    # Default to 1 (unique). Set to 0 if move_order is 'miai'.
    move_order = getattr(result, "move_order", "strict")
    unique = 0 if move_order == "miai" else 1

    # w: count of distinct wrong first moves
    wrong_count = len({
        ref.wrong_move for ref in result.refutations if ref.wrong_move
    })

    # a: average refutation depth (rounded integer)
    if result.refutations:
        avg_ref_depth = round(
            sum(ref.refutation_depth for ref in result.refutations)
            / len(result.refutations)
        )
    else:
        avg_ref_depth = 0

    # b: branch count from difficulty snapshot
    branch_count = getattr(result.difficulty, "branch_count", 0)

    # t: trap density as integer percentage (sentinel -1.0 → 0)
    trap_density = getattr(result.difficulty, "trap_density", 0.0)
    trap_pct = int(round(trap_density * 100)) if trap_density >= 0 else 0

    if depth == 0 and refutation_count == 0 and solution_length == 0:
        return ""

    # w is additive — omit when zero (no wrong moves found)
    w_part = f";w:{wrong_count}" if wrong_count > 0 else ""
    return (
        f"d:{depth};r:{refutation_count};s:{solution_length};u:{unique}"
        f"{w_part};a:{avg_ref_depth};b:{branch_count};t:{trap_pct}"
    )


def _apply_patches(sgf_text: str, patches: dict[str, str]) -> str:
    """Apply property patches to SGF string at the root node level.

    Uses sgfmill to parse, modify root properties, then re-serialize.
    """
    try:
        root = SGF.parse_sgf(sgf_text)
    except Exception as e:
        logger.error("Failed to parse SGF for patching: %s", e)
        return sgf_text

    for prop_key, prop_value in patches.items():
        root.set_property(prop_key, prop_value)

    return root.sgf()


