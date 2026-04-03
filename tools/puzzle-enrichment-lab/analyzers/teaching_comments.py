"""Teaching comments V2 -- config-driven two-layer composition for SGF C[] embedding.

Entry point that wires:
  - Signal detection from engine PV data
  - Vital move detection (analyzers.vital_move)
  - Wrong-move classification (analyzers.refutation_classifier)
  - Comment assembly (analyzers.comment_assembler)

Replaces V1 analyzers/teaching_comments.py (RC-1).

Output:
  - correct_comment: Teaching explanation for the correct first move
  - vital_comment: Teaching explanation for the vital (decisive) move
  - wrong_comments: dict[wrong_move → explanation] for refutations
  - summary: One-line puzzle summary
  - hc_level: Quality level (0=suppressed, 2=V1 fallback, 3=signal-enriched)
"""

from __future__ import annotations

import logging
from typing import Any

from config import load_enrichment_config
from config.teaching import (
    TeachingCommentsConfig,
    TeachingConfig,
    load_teaching_comments_config,
)

from analyzers.comment_assembler import (
    assemble_correct_comment,
    assemble_vital_comment,
    assemble_wrong_comment,
)
from analyzers.hint_generator import _gtp_to_sgf_token
from analyzers.refutation_classifier import (
    classify_all_refutations,
)
from analyzers.vital_move import detect_vital_move

logger = logging.getLogger(__name__)

_CONFIDENCE_RANK = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CERTAIN": 3}


def _get_teaching_config() -> TeachingConfig:
    """Load teaching comment thresholds from enrichment config (cached)."""
    cfg = load_enrichment_config()
    return cfg.teaching


def _resolve_alias(
    technique_tags: list[str],
    tc_config: TeachingCommentsConfig,
) -> str | None:
    """Resolve alias name from technique tags.

    Returns the first technique tag that is an alias in any entry's
    alias_comments dict, or None.
    """
    comments = tc_config.correct_move_comments
    for tag in technique_tags:
        if tag in comments:
            entry = comments[tag]
            if entry.alias_comments:
                for t in technique_tags:
                    if t in entry.alias_comments:
                        return t
    # Cross-entry alias scan
    for tag in technique_tags:
        for entry in comments.values():
            if entry.alias_comments and tag in entry.alias_comments:
                return tag
    return None


def _resolve_v1_comment(
    technique_tags: list[str],
    tc_config: TeachingCommentsConfig,
) -> str:
    """Resolve V1-style correct-move comment (fallback path).

    Lookup order:
    1. First canonical slug match
    2. Alias-specific comment within that entry
    3. Cross-entry alias scan
    4. Fallback to life-and-death
    """
    comments = tc_config.correct_move_comments
    for tag in technique_tags:
        if tag in comments:
            entry = comments[tag]
            if entry.alias_comments:
                for t in technique_tags:
                    if t in entry.alias_comments:
                        return entry.alias_comments[t]
            return entry.comment
    for tag in technique_tags:
        for entry in comments.values():
            if entry.alias_comments and tag in entry.alias_comments:
                return entry.alias_comments[tag]
    return ""


def _detect_signal(
    analysis: dict[str, Any],
    technique_tags: list[str],
    tc_config: TeachingCommentsConfig,
    board_size: int = 19,
) -> tuple[str, str]:
    """Detect the highest-priority signal from engine data.

    Returns:
        (signal_type, signal_phrase) tuple. Both empty if no signal detected.
    """
    validation = analysis.get("validation", {})
    analysis.get("refutations", [])
    signals = tc_config.signal_templates

    correct_move_policy = validation.get("correct_move_policy", 1.0)
    correct_move_gtp = validation.get("correct_move_gtp", "")

    # Priority-ordered signal detection

    # 1. Vital point -- when validation includes vital_coord
    vital_coord = validation.get("vital_coord", "")
    if vital_coord and signals.vital_point:
        phrase = signals.vital_point.replace("{!xy}", "{!" + vital_coord + "}")
        return ("vital_point", phrase)

    # 2. Forcing -- unique solution (no alternative correct moves)
    alternative_count = validation.get("alternative_correct_moves", -1)
    if alternative_count == 0 and signals.forcing:
        return ("forcing", signals.forcing)

    # 3. Sacrifice setup -- sacrifice tag present
    if "sacrifice" in technique_tags and signals.sacrifice_setup:
        return ("sacrifice_setup", signals.sacrifice_setup)

    # 4. Non-obvious -- low policy (engine initially rates move low)
    tc = _get_teaching_config()
    if tc and correct_move_policy < tc.non_obvious_policy and signals.non_obvious:
        coord_part = _gtp_to_sgf_token(correct_move_gtp, board_size=board_size) if correct_move_gtp else ""
        phrase = signals.non_obvious.replace("{!xy}", "{!" + coord_part + "}")
        return ("non_obvious", phrase)

    # 5. Unique solution -- only one correct sequence
    solution_branches = analysis.get("solution_branches", 0)
    if solution_branches == 1 and signals.unique_solution:
        return ("unique_solution", signals.unique_solution)

    return ("", "")


def generate_teaching_comments(
    analysis: dict[str, Any],
    technique_tags: list[str],
    *,
    tag_confidence: str = "HIGH",
    board_size: int = 19,
    detection_results: list | None = None,
    instinct_results: list | None = None,
) -> dict[str, Any]:
    """Generate V2 teaching comments for a puzzle.

    Two-layer composition:
      Layer 1: technique_phrase (from config, per primary tag)
      Layer 2: signal_phrase (detected from engine data)
      Assembly: "{technique_phrase} -- {signal_phrase}." under 15-word cap.

    Args:
        analysis: AiAnalysisResult as dict.
        technique_tags: Classified technique tags.
        tag_confidence: Classification confidence (HIGH, CERTAIN, MEDIUM, LOW).

    Returns:
        dict with:
          - correct_comment: str -- teaching explanation for correct first move
          - vital_comment: str -- explanation for the vital (decisive) move
          - wrong_comments: dict[str, str] -- {wrong_move -> explanation}
          - summary: str -- one-line summary
          - hc_level: int -- 0=suppressed, 2=V1 fallback, 3=signal-enriched
    """
    tc_config = load_teaching_comments_config()
    difficulty = analysis.get("difficulty", {})
    refutations = analysis.get("refutations", [])
    validation = analysis.get("validation", {})

    suggested_level = difficulty.get("suggested_level", "unknown")
    if not technique_tags:
        tag_desc = "Unclassified"
        return {
            "correct_comment": "",
            "vital_comment": "",
            "wrong_comments": {},
            "summary": f"{tag_desc} problem ({suggested_level} level).",
            "hc_level": 0,
        }

    primary_tag = technique_tags[0]
    move_order = analysis.get("move_order", "strict")

    # T15: Add instinct to summary when available
    # RC-2: Gated behind instinct_enabled (C-3: requires AC-4 calibration)
    instinct_phrase = ""
    if instinct_results:
        from config.teaching import get_instinct_config
        instinct_cfg = get_instinct_config()
        if instinct_cfg.enabled:
            primary_instinct = instinct_results[0]
            instinct_phrase = instinct_cfg.instinct_phrases.get(
                primary_instinct.instinct, ""
            )

    # --- Confidence gating ---
    entry = tc_config.correct_move_comments.get(primary_tag)
    min_confidence = entry.min_confidence if entry else "HIGH"
    effective = _CONFIDENCE_RANK.get(tag_confidence, 0)
    required = _CONFIDENCE_RANK.get(min_confidence, 2)

    if effective < required:
        # Suppressed -- hc:0
        tag_desc = primary_tag.replace("-", " ").title()
        return {
            "correct_comment": "",
            "vital_comment": "",
            "wrong_comments": {},
            "summary": f"{tag_desc} problem ({suggested_level} level).",
            "hc_level": 0,
        }

    # --- Layer 1: technique_phrase ---
    technique_phrase = entry.technique_phrase if entry else ""
    v1_comment = _resolve_v1_comment(technique_tags, tc_config)
    vital_move_comment = entry.vital_move_comment if entry else ""

    # --- Layer 2: signal detection ---
    signal_type, signal_phrase = _detect_signal(
        analysis, technique_tags, tc_config, board_size=board_size,
    )

    # --- Correct move assembly ---
    correct_comment = assemble_correct_comment(
        technique_phrase=technique_phrase,
        signal_phrase=signal_phrase,
        v1_comment=v1_comment,
        config=tc_config,
        instinct_phrase=instinct_phrase,
    )

    # --- Vital move detection + assembly ---
    alias = _resolve_alias(technique_tags, tc_config)
    solution_tree = analysis.get("solution_tree", [])

    vital_result = detect_vital_move(
        solution_tree=solution_tree,
        move_order=move_order,
        technique_tags=technique_tags,
        alias=alias,
    )

    vital_comment = ""
    vital_node_index = None
    if vital_result and vital_move_comment:
        vital_comment = assemble_vital_comment(
            vital_move_comment=vital_move_comment,
            signal_phrase=signal_phrase,
            config=tc_config,
        )
        # F16: Suppress root comment when vital move is deeper in the tree
        # MH-6: Only when vital_node_index > 0 AND confidence == CERTAIN
        if (vital_result.move_index > 0
                and tag_confidence == "CERTAIN"):
            correct_comment = ""  # Suppress root — vital node gets the comment
            vital_node_index = vital_result.move_index

    # --- Wrong move classification + assembly ---
    correct_first_coord = validation.get("correct_move_sgf", "")
    classification = classify_all_refutations(
        refutations=refutations,
        correct_first_coord=correct_first_coord,
        technique_tags=technique_tags,
        alias=alias,
        max_causal=tc_config.annotation_policy.max_causal_wrong_moves,
    )

    # F17/F23: Delta gate — moves below almost_correct_threshold
    # get "almost correct" instead of "Wrong".
    # Exception: curated wrongs (refutation_type="curated") always keep
    # their author's "Wrong" judgment — the puzzle creator explicitly
    # marked the move as wrong, so we never override that with "Close"
    # even if KataGo's winrate delta is near-zero.
    almost_threshold = tc_config.wrong_move_comments.almost_correct_threshold

    wrong_comments: dict[str, str] = {}
    for ref in classification.causal:
        is_curated = ref.refutation_type == "curated"
        if abs(ref.delta) < almost_threshold and not is_curated:
            wrong_comments[ref.wrong_move] = assemble_wrong_comment(
                condition="almost_correct",
                coord="",
                config=tc_config,
            )
        else:
            wrong_comments[ref.wrong_move] = assemble_wrong_comment(
                condition=ref.condition,
                coord=ref.refutation_coord,
                alias=ref.alias,
                delta=ref.delta,
                config=tc_config,
            )
    for ref in classification.default_moves:
        is_curated = ref.refutation_type == "curated"
        if abs(ref.delta) < almost_threshold and not is_curated:
            wrong_comments[ref.wrong_move] = assemble_wrong_comment(
                condition="almost_correct",
                coord="",
                config=tc_config,
            )
        else:
            wrong_comments[ref.wrong_move] = assemble_wrong_comment(
                condition="default",
                delta=ref.delta,
                config=tc_config,
            )

    # --- hc level ---
    hc_level = 3 if signal_phrase else 2

    # --- Summary ---
    tag_desc = primary_tag.replace("-", " ").title()
    if instinct_phrase:
        summary = f"{instinct_phrase}: {tag_desc} problem ({suggested_level} level)."
    else:
        summary = f"{tag_desc} problem ({suggested_level} level)."

    return {
        "correct_comment": correct_comment,
        "vital_comment": vital_comment,
        "vital_node_index": vital_node_index,
        "wrong_comments": wrong_comments,
        "summary": summary,
        "hc_level": hc_level,
    }


# ── T63: Ownership settledness delta ────────────────────────────────


def compute_ownership_settledness(
    ownership_before: list[float] | None,
    ownership_after: list[float] | None,
    puzzle_region_coords: list[int] | None = None,
) -> dict[str, float] | None:
    """Compute per-move settledness from ownership data.

    Detects "locally winning but globally losing" situations by comparing
    ownership magnitude changes before/after a move.

    Args:
        ownership_before: Ownership array before the move (361 floats for 19×19).
        ownership_after: Ownership array after the move.
        puzzle_region_coords: Indices of intersections in the puzzle region.
            If provided, computes local vs global delta separately.

    Returns:
        Dict with:
          - global_delta: Average ownership magnitude change (all points).
          - local_delta: Average ownership change in puzzle region.
          - settledness_gap: local_delta - global_delta (positive = locally
            improving but globally losing territory).
        None if ownership data is unavailable.
    """
    if not ownership_before or not ownership_after:
        return None

    n = min(len(ownership_before), len(ownership_after))
    if n == 0:
        return None

    # Global: average absolute ownership change
    global_deltas = [
        abs(ownership_after[i]) - abs(ownership_before[i])
        for i in range(n)
    ]
    global_delta = sum(global_deltas) / n

    # Local: average change in puzzle region only
    if puzzle_region_coords:
        local_coords = [c for c in puzzle_region_coords if c < n]
        if local_coords:
            local_delta = sum(
                abs(ownership_after[c]) - abs(ownership_before[c])
                for c in local_coords
            ) / len(local_coords)
        else:
            local_delta = global_delta
    else:
        local_delta = global_delta

    return {
        "global_delta": global_delta,
        "local_delta": local_delta,
        "settledness_gap": local_delta - global_delta,
    }
