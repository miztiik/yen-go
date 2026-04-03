"""Refutation analysis config models.

Groups: candidate scoring, refutation overrides, tenuki rejection,
refutation escalation, and the main refutations config.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class CandidateScoringConfig(BaseModel):
    """Temperature-weighted candidate scoring (T16B).

    KaTrain-style: weight = exp(-temperature * max(0, points_lost)).
    Final score = policy * weight. 'policy_only' ignores score deltas.
    """
    mode: str = Field(
        default="temperature",
        description="'policy_only' for legacy sort, 'temperature' for weighted",
    )
    temperature: float = Field(
        default=1.5, ge=0.0, le=10.0,
        description="Temperature scalar; higher = penalise bad moves more",
    )


class RefutationOverridesConfig(BaseModel):
    """Per-query KataGo overrides for refutation analysis (T18)."""
    root_policy_temperature: float = Field(
        default=1.3,
        description="Explore more candidates via softened root policy",
    )
    root_fpu_reduction_max: float = Field(
        default=0.0,
        description="Don't penalise unexplored moves",
    )
    wide_root_noise: float = Field(
        default=0.08,
        description="Exploration noise at root",
    )
    noise_scaling: str = Field(
        default="fixed",
        description="PI-5: Noise scaling mode. 'fixed' = current behavior, "
        "'board_scaled' = scale by board size (alpha = base * reference_area / legal_moves)",
    )
    noise_base: float = Field(
        default=0.03, ge=0.0, le=1.0,
        description="PI-5: Base noise value for board-scaled mode. "
        "Paper: alpha_19x19 ~ 0.05, alpha_9x9 ~ 0.27.",
    )
    noise_reference_area: int = Field(
        default=361, ge=1, le=1000,
        description="PI-5: Reference area for noise scaling (361 = 19x19 board).",
    )


class TenukiRejectionConfig(BaseModel):
    """Reject refutations where KataGo's response is a tenuki (T18B).

    If the Manhattan distance between the wrong move and the first
    refutation PV move exceeds the threshold, flag as tenuki.
    """
    enabled: bool = Field(default=True, description="Master switch")
    manhattan_threshold: float = Field(
        default=4.0, ge=0.0, le=38.0,
        description="Max Manhattan distance between wrong move and PV response",
    )


class SuboptimalBranchesConfig(BaseModel):
    """Generate branches for suboptimal (winning-but-not-best) moves.

    When enabled, moves that technically win but are not the correct
    move get traced to their logical end and annotated with teaching
    comments explaining why they're suboptimal.  This is useful for
    puzzles where multiple moves "work" but only one is truly best
    (e.g., chase/capture puzzles where any move captures eventually,
    but the correct move captures most efficiently).

    Feature-gated: disabled by default.  When disabled, only moves
    that cross the winrate delta_threshold are treated as refutations.
    """
    enabled: bool = Field(
        default=False,
        description="Master switch for suboptimal move branch generation",
    )
    score_delta_threshold: float = Field(
        default=2.0, ge=0.0, le=100.0,
        description="Minimum score lead difference to qualify as suboptimal "
        "(points lost vs best move)",
    )
    max_branches: int = Field(
        default=3, ge=1, le=10,
        description="Maximum suboptimal branches to generate",
    )
    max_pv_depth: int = Field(
        default=8, ge=1, le=30,
        description="Maximum PV depth to trace for suboptimal branches",
    )
    min_policy: float = Field(
        default=0.01, ge=0.0, le=1.0,
        description="Minimum policy prior for a move to be considered "
        "as a plausible suboptimal candidate",
    )
    visits: int = Field(
        default=200, ge=10, le=10000,
        description="Visits for analyzing suboptimal move continuations",
    )


class RefutationsConfig(BaseModel):
    candidate_min_policy: float = 0.0
    candidate_max_count: int = 5
    refutation_max_count: int = 3
    delta_threshold: float = 0.08
    refutation_visits: int = 100
    locality_max_distance: int = Field(
        default=2, ge=0, le=10,
        description="Max Chebyshev distance from any stone for candidate wrong moves (0=disabled)",
    )
    max_pv_length: int = Field(
        default=4, ge=1, le=20,
        description="P0.4: Max moves in refutation PV. Was hardcoded 4. "
        "Elementary=4, Intermediate=6, Dan=8-10.",
    )
    pv_mode: str = Field(
        default="multi_query",
        description="'pv_extract' = single-query PV; 'multi_query' = per-candidate (current)",
    )
    pv_extract_min_depth: int = Field(
        default=3, ge=1, le=20,
        description="Min PV depth for pv_extract; fallback to multi_query if shorter",
    )
    pv_quality_min_visits: int = Field(
        default=50, ge=1, le=100000,
        description="Min visits for PV trust in pv_extract mode",
    )
    candidate_scoring: CandidateScoringConfig = Field(
        default_factory=CandidateScoringConfig,
        description="Temperature-weighted candidate scoring (T16B)",
    )
    refutation_overrides: RefutationOverridesConfig = Field(
        default_factory=RefutationOverridesConfig,
        description="Per-query KataGo overrides for refutation analysis (T18)",
    )
    tenuki_rejection: TenukiRejectionConfig = Field(
        default_factory=TenukiRejectionConfig,
        description="Tenuki rejection for refutation responses (T18B)",
    )
    suboptimal_branches: SuboptimalBranchesConfig = Field(
        default_factory=SuboptimalBranchesConfig,
        description="Generate branches for winning-but-suboptimal moves (feature-gated, off by default)",
    )
    ownership_delta_weight: float = Field(
        default=0.0, ge=0.0, le=1.0,
        description="PI-1: Weight for ownership delta in composite refutation scoring. "
        "0.0 = winrate-only (current behavior), 1.0 = ownership-only. "
        "Composite: wr_delta * (1-w) + ownership_delta * w",
    )
    score_delta_enabled: bool = Field(
        default=False,
        description="PI-3: Enable score-lead delta as complementary refutation filter. "
        "When True, candidates qualify if EITHER winrate delta OR score delta exceeds threshold.",
    )
    score_delta_threshold: float = Field(
        default=5.0, ge=0.0, le=100.0,
        description="PI-3: Minimum score-lead delta for a candidate to qualify as refutation. "
        "Only used when score_delta_enabled=True.",
    )
    forced_min_visits_formula: bool = Field(
        default=False,
        description="PI-6: Enable forced minimum visits per refutation candidate. "
        "Formula: nforced(c) = sqrt(k * P(c) * total_visits). "
        "Ensures low-policy sacrifice/throw-in moves get explored.",
    )
    forced_visits_k: float = Field(
        default=2.0, ge=0.1, le=20.0,
        description="PI-6: Scaling factor k in forced min visits formula. "
        "Higher k forces more visits on low-policy candidates.",
    )
    multi_pass_harvesting: bool = Field(
        default=False,
        description="PI-8: Enable diversified root candidate harvesting. "
        "After initial candidate scan, run a secondary scan with higher noise "
        "to find human-tempting wrong moves missed by the first pass.",
    )
    secondary_noise_multiplier: float = Field(
        default=2.0, ge=1.0, le=10.0,
        description="PI-8: Noise multiplier for secondary harvesting pass. "
        "Applied on top of effective_noise (PI-5 or wide_root_noise).",
    )
    best_resistance_enabled: bool = Field(
        default=False,
        description="PI-12: Enable best-resistance line generation. "
        "After getting the initial refutation PV, evaluate up to N alternative "
        "opponent responses and select the one that maximizes punishment.",
    )
    best_resistance_max_candidates: int = Field(
        default=3, ge=1, le=10,
        description="PI-12: Maximum alternative opponent responses to evaluate "
        "for best-resistance selection.",
    )


class RefutationEscalationConfig(BaseModel):
    """Escalation settings when 0 refutations found on first pass.

    Retries with higher visits and relaxed thresholds to ensure
    refutation trees are always built.
    """
    enabled: bool = Field(
        default=True,
        description="Whether to retry refutation generation when 0 refutations found",
    )
    min_refutations_required: int = Field(
        default=1, ge=0, le=10,
        description="Minimum refutations required before considering escalation",
    )
    escalation_visits: int = Field(
        default=500, ge=100, le=10000,
        description="Higher visit count for escalation retry",
    )
    escalation_delta_threshold: float = Field(
        default=0.03, ge=0.0, le=1.0,
        description="Relaxed delta threshold for escalation retry",
    )
    escalation_candidate_min_policy: float = Field(
        default=0.003, ge=0.0, le=1.0,
        description="Relaxed candidate min policy for escalation retry",
    )
    use_referee_engine: bool = Field(
        default=True,
        description="Use referee engine for escalation (if available)",
    )
    max_escalation_attempts: int = Field(
        default=1, ge=1, le=5,
        description="Maximum number of escalation attempts",
    )
