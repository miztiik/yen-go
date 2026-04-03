"""Task A.3: Estimate puzzle difficulty from KataGo signals.

Uses policy prior, visits to solve, trap density, structural signals,
and complexity to produce a difficulty rating mapping to Yen-Go's 9-level
system.

A.3.1: Policy-only difficulty (Tier 0.5) — maps raw policy prior to level.
A.3.2: Composite difficulty (G11/T17) — structural signals dominant (35%),
       trap density (20%), complexity (15%),
       PUCT-coupled signals reduced (policy+visits < 40%).

All thresholds and weights are loaded from config/katago-enrichment.json.
Level IDs are loaded from config/puzzle-levels.json (source of truth).
"""

from __future__ import annotations

import logging
import math

try:
    from config import get_level_id, load_enrichment_config, load_puzzle_levels
    from models.difficulty_estimate import DifficultyEstimate
    from models.refutation_result import RefutationResult
    from models.validation import ConfidenceLevel, CorrectMoveResult

    from analyzers.config_lookup import load_tag_slug_map
except ImportError:
    from ..analyzers.config_lookup import load_tag_slug_map
    from ..config import get_level_id, load_enrichment_config
    from ..models.difficulty_estimate import DifficultyEstimate
    from ..models.refutation_result import RefutationResult
    from ..models.validation import ConfidenceLevel, CorrectMoveResult

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# R-1: Computed teaching signals (KataGo-LLM-Team inspired, zero new queries)
# ---------------------------------------------------------------------------

def compute_log_policy_score(policy_prior: float) -> float:
    """Log-scaled policy score mapping raw prior to [0, 1].

    Formula: (log10(max(P, 1e-6)) + 6.0) / 6.0
    - P=1e-6 → 0.0 (invisible move)
    - P=0.001 → 0.5 (hidden tesuji)
    - P=0.1 → ~0.83 (reasonable candidate)
    - P=1.0 → 1.0 (dominant move)

    Inspired by KataGo-LLM-Team R_policy_log.
    """
    clamped = max(policy_prior, 1e-6)
    return min(max((math.log10(clamped) + 6.0) / 6.0, 0.0), 1.0)


def compute_score_lead_rank(move_infos: list, target_move_gtp: str) -> float:
    """Percentile rank of a move's scoreLead among all evaluated moves.

    Returns 1.0 for the best move (highest scoreLead),
    0.0 for the worst. Returns 0.5 if only one move or target not found.

    Inspired by KataGo-LLM-Team R_rank.
    """
    if not move_infos or not target_move_gtp:
        return 0.5

    scores = sorted([m.score_lead for m in move_infos])
    n = len(scores)
    if n <= 1:
        return 0.5

    target = target_move_gtp.upper()
    target_score = None
    for m in move_infos:
        if m.move.upper() == target:
            target_score = m.score_lead
            break
    if target_score is None:
        return 0.5

    # Count how many scores are strictly less than target
    rank_below = sum(1 for s in scores if s < target_score)
    return rank_below / (n - 1)


def compute_position_closeness(root_winrate: float) -> float:
    """Position closeness metric: how contested the position is.

    Returns 1.0 when root_winrate is exactly 0.5 (most contested),
    0.0 when root_winrate is 0.0 or 1.0 (completely decided).

    Formula: 1.0 - 2.0 * |root_winrate - 0.5|

    Inspired by KataGo-LLM-Team adaptive closeness weighting.
    """
    return max(0.0, 1.0 - 2.0 * abs(root_winrate - 0.5))


def compute_policy_entropy(
    move_infos: list,
    top_k: int = 10,
) -> float:
    """Compute Shannon entropy over KataGo policy distribution.

    H = -Σ(p * log2(p)) for the top-K moves by policy prior.
    Normalized to 0.0-1.0 range: H / log2(K) where K = min(top_k,
    count of moves with positive prior).

    Higher entropy = more uncertain = harder puzzle.
    Lower entropy = one dominant move = easier puzzle.

    Args:
        move_infos: List of MoveAnalysis objects with .policy_prior attribute.
        top_k: Number of top moves to consider (default: 10).

    Returns:
        Normalized entropy in [0.0, 1.0]. Returns 0.0 if no valid priors.
    """
    if not move_infos:
        return 0.0

    # Sort by policy prior descending, take top-K
    priors = sorted(
        [m.policy_prior for m in move_infos if m.policy_prior > 0],
        reverse=True,
    )[:top_k]

    if not priors:
        return 0.0

    # Normalize priors to sum to 1.0 (they may not after filtering)
    total = sum(priors)
    if total <= 0:
        return 0.0

    normalized = [p / total for p in priors]

    # Shannon entropy
    entropy = -sum(p * math.log2(p) for p in normalized if p > 0)

    # Normalize to [0, 1]: max entropy = log2(len(normalized))
    max_entropy = math.log2(len(normalized)) if len(normalized) > 1 else 1.0
    return min(entropy / max_entropy, 1.0) if max_entropy > 0 else 0.0


def find_correct_move_rank(
    move_infos: list,
    correct_move_gtp: str,
) -> int:
    """Find the rank of the correct move in KataGo's candidate list.

    Rank is 1-based: rank 1 = KataGo's top move.
    Moves are sorted by visits (descending), matching KataGo's ordering.

    Args:
        move_infos: List of MoveAnalysis objects with .move and .visits attributes.
        correct_move_gtp: GTP coordinate of the correct move (e.g., "D4").

    Returns:
        1-based rank of the correct move. 0 if not found in candidate list.
    """
    if not move_infos or not correct_move_gtp:
        return 0

    # Sort by visits descending (KataGo's preferred ordering)
    sorted_moves = sorted(move_infos, key=lambda m: m.visits, reverse=True)

    target = correct_move_gtp.upper()
    for i, m in enumerate(sorted_moves, start=1):
        if m.move.upper() == target:
            return i

    return 0


def _get_normalization_config():
    """Get difficulty normalization config (Plan 010, P5.3)."""
    cfg = load_enrichment_config()
    if cfg.difficulty.normalization:
        return cfg.difficulty.normalization
    from config.difficulty import DifficultyNormalizationConfig
    return DifficultyNormalizationConfig()


def _get_disagree_multiplier() -> int:
    """Get visits disagree multiplier from config (Plan 010, P5.3)."""
    return _get_normalization_config().disagree_multiplier




# ===================================================================
# A.3.1 — Policy-only difficulty (Tier 0.5)
# ===================================================================


def estimate_difficulty_policy_only(
    policy_prior: float,
    move_order: str = "strict",
    correct_move_priors: list[float] | None = None,
    puzzle_id: str = "",
) -> DifficultyEstimate:
    """Tier 0.5: Estimate difficulty from raw policy prior alone.

    This requires NO MCTS search — it uses the neural network's raw policy
    output to estimate how "obvious" the correct move looks to a strong AI.

    For miai puzzles (move_order="miai"), uses max(correct_move_priors)
    instead of the single policy_prior. This is because miai means either
    move is acceptable — the difficulty should reflect the easiest correct
    move, not the sum of all correct moves' priors.

    Thresholds loaded from config/katago-enrichment.json "policy_to_level".
    Level IDs loaded from config/puzzle-levels.json (source of truth).

    Args:
        policy_prior: Raw policy prior for the correct move (0-1).
        move_order: "strict", "flexible", or "miai" (from YO property).
        correct_move_priors: For miai puzzles, list of all correct moves' priors.
        puzzle_id: Optional identifier.

    Returns:
        DifficultyEstimate with level mapping based on policy alone.
    """
    cfg = load_enrichment_config()

    # For miai puzzles, use the max of correct move priors (not sum)
    effective_prior = policy_prior
    if move_order == "miai" and correct_move_priors:
        effective_prior = max(correct_move_priors)
        logger.debug(
            "Miai puzzle %s: using max(priors)=%.4f from %s (not sum=%.4f)",
            puzzle_id,
            effective_prior,
            correct_move_priors,
            sum(correct_move_priors),
        )

    # Map policy prior to level using config thresholds
    level_slug, level_id = _policy_to_level(effective_prior, cfg)

    return DifficultyEstimate(
        puzzle_id=puzzle_id,
        policy_prior=effective_prior,
        visits_to_solve=0,  # Not computed in Tier 0.5
        solution_depth=0,  # Not computed in Tier 0.5
        refutation_count=0,  # Not computed in Tier 0.5
        raw_difficulty_score=0.0,  # Not computed in Tier 0.5
        estimated_level=level_slug,
        estimated_level_id=level_id,
        confidence=ConfidenceLevel.MEDIUM,  # Policy-only is less confident than full MCTS
    )


def _policy_to_level(
    policy_prior: float,
    cfg: EnrichmentConfig | None = None,  # noqa: F821
) -> tuple[str, int]:
    """Map a raw policy prior to a Yen-Go level.

    Uses config/katago-enrichment.json "policy_to_level" thresholds.
    Thresholds are sorted descending by min_prior: first match wins.
    Higher prior → easier puzzle (novice); lower prior → harder (expert).

    Args:
        policy_prior: Neural network policy prior for the correct move (0-1).
        cfg: Optional pre-loaded config.

    Returns:
        Tuple of (level_slug, level_id).
    """
    if cfg is None:
        cfg = load_enrichment_config()

    thresholds = cfg.difficulty.policy_to_level.thresholds

    for entry in thresholds:
        if policy_prior >= entry.min_prior:
            slug = entry.level_slug
            level_id = get_level_id(slug)
            return slug, level_id

    # Fallback to last (expert — lowest min_prior, typically 0.0)
    last = thresholds[-1]
    return last.level_slug, get_level_id(last.level_slug)


def estimate_difficulty(
    validation: CorrectMoveResult,
    refutation_result: RefutationResult,
    solution_moves: list[str] | None = None,
    puzzle_id: str = "",
    branch_count: int = 0,
    local_candidate_count: int = 0,
    max_resolved_depth: int = 0,
    tags: list[int] | None = None,
    visits_used: int = 0,
) -> DifficultyEstimate:
    """Estimate puzzle difficulty from KataGo + structural signals (Phase S.3).

    **KataGo signals (≥65% weight):**
      policy_component = (1.0 - policy_prior) × w_policy_rank            (15)
      visits_component = log2(visits/base) / log2(max/base) × w_visits   (15)
      trap_component   = trap_density × w_trap_density                   (20)
      complexity_component = complexity × w_complexity                    (15)

    **Structural signals (35% weight):**
      structural_component = blend(depth, branches) × w_structural       (35)

    **Trap density** uses score-based formula (v1.17):
      sum(min(|score_delta|/cap, 1.0) × prior) / sum(prior)
    with configurable per-puzzle floor and |winrate_delta| fallback.

    **Complexity** (5th component):
      sum(prior × max(|score_delta|/cap, 0)) / sum(prior)
    Measures weighted average score loss across all moves.

    **Elo-anchor gate** (v1.17): After composite scoring, cross-checks
    against policy-based level using KaTrain's CALIBRATED_RANK_ELO.
    Overrides level when divergence ≥ threshold (config-driven).

    All weights are loaded from config/katago-enrichment.json "weights".
    Level IDs are loaded from config/puzzle-levels.json.

    Args:
        validation: Result from validate_correct_move
        refutation_result: Result from generate_refutations
        solution_moves: Main-line solution move list (for depth)
        puzzle_id: Optional identifier
        branch_count: Branching points in correct solution tree
        local_candidate_count: Empty intersections near stones
        max_resolved_depth: Deepest non-truncated branch in AI solution tree (KM-04)

    Returns:
        DifficultyEstimate with level mapping
    """
    cfg = load_enrichment_config()
    w = cfg.difficulty.weights

    policy_prior = validation.correct_move_policy
    depth = len(solution_moves) if solution_moves else 0
    refutation_count = len(refutation_result.refutations)

    # ── KataGo signal 1: Policy rank (30% default) ─────────────────
    # Lower policy_prior → harder puzzle (NN doesn't immediately see it)
    # On a cropped board (S.1), policy is concentrated so 0.01 = hard,
    # but on a full 19×19 board 0.01 might just be diluted.
    policy_component = (1.0 - min(policy_prior, 1.0)) * w.policy_rank
    logger.debug(
        "Component policy: prior=%.4f, weight=%.0f, score=%.2f",
        policy_prior, w.policy_rank, policy_component,
    )

    # ── KataGo signal 2: Visits to solve (30% default) ─────────────
    # C1 fix: use per-move visit count (correct_move_visits) rather
    # than total visits (visits_used).  In lab mode (10K total visits)
    # visits_used is constant for every puzzle, making this a uniform
    # addend that provides ZERO differentiation.  correct_move_visits
    # reflects how deeply KataGo explored the correct move specifically:
    # a high-confidence easy move gets many per-move visits; a tricky
    # move that even KataGo finds hard gets fewer.
    # Fall back to visits_used (or 50) if correct_move_visits is missing
    # (e.g. Tier 2 structural-only enrichment).
    visits_used = validation.correct_move_visits or validation.visits_used or 50
    base_visits = cfg.difficulty.mcts.base_visits  # default 50
    visits_to_solve = visits_used
    if not validation.katago_agrees:
        visits_to_solve = visits_used * _get_disagree_multiplier()  # Needed more than we gave

    # Log-scale normalization: [base_visits, 20000] → [0.0, 1.0]
    max_visits_cap = _get_normalization_config().max_visits_cap
    if visits_to_solve <= base_visits:
        normalized_visits = 0.0
    else:
        normalized_visits = min(
            math.log2(visits_to_solve / base_visits)
            / math.log2(max_visits_cap / base_visits),
            1.0,
        )
    visits_component = normalized_visits * w.visits_to_solve
    logger.debug(
        "Component visits: raw=%d, normalized=%.3f, weight=%.0f, score=%.2f",
        visits_to_solve, normalized_visits, w.visits_to_solve, visits_component,
    )

    # ── KataGo signal 3: Trap density (20% default) ────────────────
    # How tempting are the wrong moves? High trap density → harder.
    trap_density = _compute_trap_density(refutation_result)
    trap_component = trap_density * w.trap_density
    logger.debug(
        "Component trap: density=%.3f, weight=%.0f, score=%.2f",
        trap_density, w.trap_density, trap_component,
    )

    # ── Structural signal (20% default) ─────────────────────────────
    # G4 fix: Use config-driven structural sub-weights instead of
    # hardcoded 0.6/0.4.  Now uses all 4 dimensions from
    # cfg.difficulty.structural_weights (sum to 100).
    sw = cfg.difficulty.structural_weights
    norm_cfg = _get_normalization_config()
    structural_raw = (
        min(depth / norm_cfg.max_solution_depth, 1.0) * (sw.solution_depth / 100.0)
        + min(branch_count / norm_cfg.max_branch_count, 1.0) * (sw.branch_count / 100.0)
        + min(local_candidate_count / norm_cfg.max_local_candidates, 1.0) * (sw.local_candidates / 100.0)
        + min(refutation_count / norm_cfg.max_refutation_count, 1.0) * (sw.refutation_count / 100.0)
        + min(max_resolved_depth / norm_cfg.max_resolved_depth_ceiling, 1.0) * (sw.proof_depth / 100.0)
    )
    structural_component = structural_raw * w.structural
    logger.debug(
        "Component structural: raw=%.3f, weight=%.0f, score=%.2f",
        structural_raw, w.structural, structural_component,
    )

    # ── Complexity signal (15% default) ─────────────────────────────
    # Weighted average score loss: measures how many tempting wrong
    # moves exist.  High complexity = many reasonable-looking moves
    # that are actually wrong.
    complexity = _compute_complexity(refutation_result)
    complexity_component = complexity * w.complexity
    logger.debug(
        "Component complexity: raw=%.3f, weight=%.0f, score=%.2f",
        complexity, w.complexity, complexity_component,
    )

    raw_score = (
        policy_component + visits_component + trap_component
        + structural_component + complexity_component
    )
    raw_score = min(raw_score, 100.0)

    # Map raw score to level using config-driven thresholds
    level_slug, level_id = _score_to_level(raw_score, cfg)

    # Elo-anchor hard gate (v1.17): cross-check against policy-based level
    level_slug, level_id = _elo_anchor_gate(
        policy_prior=policy_prior,
        composite_level_slug=level_slug,
        composite_level_id=level_id,
        cfg=cfg,
        puzzle_id=puzzle_id,
    )

    # Determine confidence
    confidence = ConfidenceLevel.HIGH
    confidence_reason = ""
    if not validation.katago_agrees:
        confidence = ConfidenceLevel.LOW
        confidence_reason = "katago_disagrees"
    elif depth == 0:
        confidence = ConfidenceLevel.MEDIUM
        confidence_reason = "zero_depth"

    # Depth-modulated confidence cap: deep puzzles are harder for KataGo
    # to read correctly within typical visit budgets.
    effective_visits = visits_used or validation.visits_used
    if depth >= 12 and effective_visits < 5000:
        if confidence == ConfidenceLevel.HIGH:
            confidence = ConfidenceLevel.LOW
            confidence_reason = "depth_capped_12"
    elif depth >= 8 and effective_visits < 2000:
        if confidence == ConfidenceLevel.HIGH:
            confidence = ConfidenceLevel.MEDIUM
            confidence_reason = "depth_capped_8"

    # Ko confidence cap: ko evaluation is inherently noisy because the
    # position's value depends on ko threats the frame doesn't model.
    # Tag ID resolved from config/tags.json via config_lookup (REC-2).
    tag_map = load_tag_slug_map()
    ko_tag_id = tag_map.get("ko", 12)
    if tags and ko_tag_id in tags:
        if confidence == ConfidenceLevel.HIGH:
            confidence = ConfidenceLevel.MEDIUM
            confidence_reason = "ko_capped"

    logger.info(
        "Difficulty %s: policy=%.1f (prior=%.4f, w=%.0f) "
        "visits=%.1f (raw=%d, w=%.0f) trap=%.1f (density=%.3f, w=%.0f) "
        "structural=%.1f (w=%.0f) complexity=%.1f (raw=%.3f, w=%.0f) "
        "→ raw_score=%.1f → %s (id=%d) confidence=%s",
        puzzle_id, policy_component, policy_prior, w.policy_rank,
        visits_component, visits_to_solve, w.visits_to_solve,
        trap_component, trap_density, w.trap_density,
        structural_component, w.structural,
        complexity_component, complexity, w.complexity,
        raw_score, level_slug, level_id, confidence,
    )

    return DifficultyEstimate(
        puzzle_id=puzzle_id or validation.puzzle_id,
        policy_prior=policy_prior,
        visits_to_solve=visits_to_solve,
        trap_density=trap_density,
        solution_depth=depth,
        branch_count=branch_count,
        local_candidate_count=local_candidate_count,
        refutation_count=refutation_count,
        raw_difficulty_score=raw_score,
        estimated_level=level_slug,
        estimated_level_id=level_id,
        confidence=confidence,
        confidence_reason=confidence_reason,
    )


def _compute_complexity(refutation_result: RefutationResult) -> float:
    """Compute complexity: weighted average score loss across all refutations.

    Formula: Σ(prior × max(score_delta, 0)) / Σ(prior)

    Measures how many tempting wrong moves exist. A puzzle where multiple
    plausible-looking moves (high prior) lead to large losses (high score_delta)
    has high complexity.

    Returns:
        Complexity in [0, 1]. 0 = no complexity data available.
    """
    if not refutation_result.refutations:
        return 0.0

    cfg = load_enrichment_config()
    score_cap = cfg.difficulty.score_normalization_cap

    weighted_sum = 0.0
    prior_sum = 0.0

    for ref in refutation_result.refutations:
        prior = ref.wrong_move_policy
        # Use score_delta (positive = points lost); fallback to winrate_delta
        if abs(ref.score_delta) > 1e-9:
            loss = max(abs(ref.score_delta), 0.0)
            normalized_loss = min(loss / score_cap, 1.0)
        else:
            normalized_loss = abs(ref.winrate_delta)
        weighted_sum += prior * normalized_loss
        prior_sum += prior

    if prior_sum < 1e-9:
        return 0.0

    return min(weighted_sum / prior_sum, 1.0)


def _compute_trap_density(refutation_result: RefutationResult) -> float:
    """Compute trap density from refutation data using score-based formula.

    Score-based formula (v1.17, KaTrain-inspired):
      sum(normalized_loss * prior) / sum(prior)
    where normalized_loss = min(|score_delta| / score_normalization_cap, 1.0).

    Falls back to |winrate_delta| when score_delta == 0 (legacy/curated data
    without score enrichment).

    When refutations exist, a configurable per-puzzle floor is applied to
    ensure trap density is never trivially zero for puzzles with known wrong
    moves.

    Returns:
        Trap density in [0, 1]. 0 = no traps (or no refutations).
    """
    if not refutation_result.refutations:
        return 0.0

    cfg = load_enrichment_config()
    score_cap = cfg.difficulty.score_normalization_cap
    floor = cfg.difficulty.trap_density_floor

    weighted_sum = 0.0
    prior_sum = 0.0

    for ref in refutation_result.refutations:
        prior = ref.wrong_move_policy
        # Prefer score_delta; fall back to |winrate_delta| for legacy data
        if abs(ref.score_delta) > 1e-9:
            raw_loss = abs(ref.score_delta)
            normalized_loss = min(raw_loss / score_cap, 1.0)
        else:
            normalized_loss = abs(ref.winrate_delta)  # fallback [0, 1]
        weighted_sum += normalized_loss * prior
        prior_sum += prior

    if prior_sum < 1e-9:
        logger.warning(
            "Trap density: prior_sum=0 for puzzle %s — "
            "returning 0.0 (all %d refutation priors are near-zero). "
            "Check locality filter or curated policy enrichment.",
            refutation_result.refutations[0].wrong_move if refutation_result.refutations else "unknown",
            len(refutation_result.refutations),
        )
        return 0.0

    raw_density = min(weighted_sum / prior_sum, 1.0)
    # Per-puzzle floor: when refutations exist, trap density >= floor
    return max(raw_density, floor)


def _score_to_level(
    score: float,
    cfg: EnrichmentConfig | None = None,  # noqa: F821
) -> tuple[str, int]:
    """Map a raw difficulty score (0-100) to a Yen-Go level.

    Thresholds are loaded from config/katago-enrichment.json.
    Level IDs are loaded from config/puzzle-levels.json.
    """
    if cfg is None:
        cfg = load_enrichment_config()

    thresholds = cfg.difficulty.score_to_level_thresholds

    for entry in thresholds:
        if score <= entry.max_score:
            slug = entry.level_slug
            level_id = get_level_id(slug)
            return slug, level_id

    # Fallback to last (expert)
    last = thresholds[-1]
    return last.level_slug, get_level_id(last.level_slug)


# ── Level slug → rank midpoint mapping ──────────────────────────────
# Derived from config/puzzle-levels.json rank ranges.
# Positive = kyu, 0 = 1d, negative = higher dan.
_LEVEL_RANK_MIDPOINT: dict[str, int] = {
    "novice": 28,       # 30k-26k → midpoint 28k
    "beginner": 23,     # 25k-21k → midpoint 23k
    "elementary": 18,   # 20k-16k → midpoint 18k
    "intermediate": 13, # 15k-11k → midpoint 13k
    "upper-intermediate": 8,  # 10k-6k → midpoint 8k
    "advanced": 3,      # 5k-1k → midpoint 3k
    "low-dan": -2,      # 1d-3d → midpoint 2d → -2
    "high-dan": -5,     # 4d-6d → midpoint 5d → -5
    "expert": -8,       # 7d-9d → midpoint 8d → -8
}

# Reverse: rank → level slug (for Elo anchor lookup)
_RANK_TO_LEVEL: list[tuple[int, str]] = [
    # Sorted by rank descending (highest kyu first)
    (26, "novice"),           # >= 26k
    (21, "beginner"),         # >= 21k
    (16, "elementary"),       # >= 16k
    (11, "intermediate"),     # >= 11k
    (6,  "upper-intermediate"),  # >= 6k
    (1,  "advanced"),         # >= 1k
    (-3, "low-dan"),          # >= -3 (i.e. <= 3d)
    (-6, "high-dan"),         # >= -6 (i.e. <= 6d)
]
# expert: anything below -6


def _rank_to_level_slug(kyu_rank: int) -> tuple[str, int]:
    """Map a kyu rank to Yen-Go level slug and ID.

    kyu_rank convention: positive = kyu, 0 = 1d, negative = higher dan.
    """
    for threshold, slug in _RANK_TO_LEVEL:
        if kyu_rank >= threshold:
            return slug, get_level_id(slug)
    return "expert", get_level_id("expert")


def _elo_anchor_gate(
    policy_prior: float,
    composite_level_slug: str,
    composite_level_id: int,
    cfg,
    puzzle_id: str = "",
) -> tuple[str, int]:
    """Apply Elo-anchor hard gate: override level if divergence exceeds threshold.

    Uses KaTrain's CALIBRATED_RANK_ELO (MIT licensed, github.com/sanderland/katrain)
    to map policy_prior → approximate kyu rank → Yen-Go level.
    Compares against the composite-assigned level and overrides when the
    level divergence exceeds the configured threshold.

    Covered range: elementary (18k) through high-dan (5d).
    Outside this range (novice, beginner, expert): logs and returns original.

    Returns:
        (level_slug, level_id) — either original or overridden.
    """
    elo_cfg = cfg.elo_anchor
    if elo_cfg is None or not elo_cfg.enabled:
        return composite_level_slug, composite_level_id

    # Step 1: Get the composite level's rank midpoint
    composite_rank = _LEVEL_RANK_MIDPOINT.get(composite_level_slug)
    if composite_rank is None:
        logger.warning(
            "Elo anchor %s: unknown level slug '%s' — skipping",
            puzzle_id, composite_level_slug,
        )
        return composite_level_slug, composite_level_id

    # Step 2: Get the policy-based level's rank midpoint
    policy_level_slug, policy_level_id = _policy_to_level(policy_prior, cfg)
    policy_rank = _LEVEL_RANK_MIDPOINT.get(policy_level_slug)
    if policy_rank is None:
        return composite_level_slug, composite_level_id

    # Step 3: Check if both are in covered range
    min_kyu = elo_cfg.min_covered_rank_kyu   # 18 (elementary)
    max_dan = elo_cfg.max_covered_rank_dan   # 5 → -5

    # Uncovered composites: novice (28k), beginner (23k), expert (-8d)
    if composite_rank > min_kyu or composite_rank < -max_dan:
        logger.debug(
            "Elo anchor %s: composite level '%s' (rank=%d) outside covered range "
            "[%dk..%dd] — no Elo anchor available",
            puzzle_id, composite_level_slug, composite_rank,
            min_kyu, max_dan,
        )
        return composite_level_slug, composite_level_id

    if policy_rank > min_kyu or policy_rank < -max_dan:
        logger.debug(
            "Elo anchor %s: policy level '%s' (rank=%d) outside covered range — "
            "no Elo anchor available",
            puzzle_id, policy_level_slug, policy_rank,
        )
        return composite_level_slug, composite_level_id

    # Step 4: Compute level divergence
    # Use level IDs for comparison (110, 120, ..., 230)
    # Each step is 10 units, so divergence in level steps = abs(diff) / 10
    level_diff = abs(composite_level_id - policy_level_id) // 10
    threshold = elo_cfg.override_threshold_levels

    if level_diff >= threshold:
        logger.info(
            "Elo anchor OVERRIDE %s: composite='%s'(id=%d) vs policy='%s'(id=%d) "
            "divergence=%d levels >= threshold=%d — overriding to policy level",
            puzzle_id, composite_level_slug, composite_level_id,
            policy_level_slug, policy_level_id, level_diff, threshold,
        )
        return policy_level_slug, policy_level_id
    else:
        logger.debug(
            "Elo anchor %s: composite='%s' vs policy='%s' divergence=%d < threshold=%d — keeping composite",
            puzzle_id, composite_level_slug, policy_level_slug, level_diff, threshold,
        )
        return composite_level_slug, composite_level_id


def compute_per_move_accuracy(refutation_result: RefutationResult) -> float | None:
    """Compute per-move accuracy: 100 × 0.75^weighted_ptloss.

    weighted_ptloss is the complexity metric (weighted average score loss).
    Higher accuracy = easier puzzle (fewer tempting wrong moves).

    Returns:
        Accuracy in [0, 100], or None if no refutation data.
    """
    complexity = _compute_complexity(refutation_result)
    if complexity < 1e-9:
        return None
    return 100.0 * (0.75 ** complexity)
