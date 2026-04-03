"""Difficulty estimation and validation config models.

Groups: difficulty weights, score-to-level mapping, MCTS config,
validation thresholds, quality gates, normalization, escalation,
Elo anchor, and sparse position detection.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class OwnershipThresholds(BaseModel):
    alive: float = 0.7
    dead: float = -0.7
    seki_low: float = -0.3
    seki_high: float = 0.3
    center_reduction: float = 0.2
    center_alive: float = 0.5
    center_dead: float = -0.5


class CuratedPruningConfig(BaseModel):
    """Curated solution path pruning (T4B).

    Skip validation of curated sub-branches (depth>=2) where KataGo
    visits are < min_visit_ratio of the top move. Branches above
    trap_threshold are kept as tricky traps.
    """
    enabled: bool = Field(default=True, description="Enable curated branch pruning")
    min_visit_ratio: float = Field(
        default=0.01, ge=0.0, le=1.0,
        description="Skip branches with visits < this fraction of top move",
    )
    trap_threshold: float = Field(
        default=0.02, ge=0.0, le=1.0,
        description="Branches above this ratio are tricky traps — keep them",
    )
    min_depth: int = Field(
        default=2, ge=1, le=20,
        description="Never prune at depth < this (first-moves always validated)",
    )


class ValidationConfig(BaseModel):
    flagged_value_low: float = 0.3
    flagged_value_high: float = 0.7
    rejected_not_in_top_n: int = 20
    ko_visit_ratio: float = 0.8
    winrate_rescue_auto_accept: float = 0.85
    min_visits_for_accept: int = Field(
        default=50, ge=1, le=10000,
        description=(
            "Minimum per-move MCTS visits for winrate-based acceptance. "
            "Moves with WR >= flagged_value_high but fewer visits are "
            "FLAGGED as under-explored rather than ACCEPTED."
        ),
    )
    source_trust_min_tier: int = Field(
        default=4, ge=1, le=5,
        description=(
            "Source quality tier threshold for trust-based softening. "
            "Puzzles from sources with tier >= this value get REJECTED "
            "softened to FLAGGED (curated sources have <0.1% error rate)."
        ),
    )
    curated_pruning: CuratedPruningConfig = Field(
        default_factory=CuratedPruningConfig,
        description="Curated solution path pruning (T4B)",
    )


class DifficultyWeights(BaseModel):
    """Difficulty formula weights. Structural > trap > complexity > policy+visits.

    Policy and visits are PUCT-coupled (high-policy moves get more visits),
    so their combined weight should be < 40% to reduce collinearity.
    Structural signals (depth, branches, refutations) are independent.
    Complexity measures weighted average score loss across all moves.
    """
    policy_rank: float = 15.0
    visits_to_solve: float = 15.0
    trap_density: float = 20.0
    structural: float = 35.0
    complexity: float = 15.0

    @model_validator(mode="after")
    def check_weights_sum(self) -> DifficultyWeights:
        """P1.7: Validate weights sum to 100."""
        total = self.policy_rank + self.visits_to_solve + self.trap_density + self.structural + self.complexity
        if abs(total - 100.0) > 0.01:
            raise ValueError(f"Difficulty weights must sum to 100, got {total}")
        return self


class StructuralDifficultyWeights(BaseModel):
    """SGF-structural difficulty formula weights (Phase R.3).

    Replaces KataGo-signal formula. All weights should sum to 100.
    """
    solution_depth: float = Field(default=35.0, description="Weight for solution tree depth (moves)")
    branch_count: float = Field(default=22.0, description="Weight for branching points in solution tree")
    local_candidates: float = Field(default=18.0, description="Weight for nearby empty intersections (ambiguity)")
    refutation_count: float = Field(default=15.0, description="Weight for plausible wrong first moves")
    proof_depth: float = Field(default=10.0, description="Weight for proof depth — search effort to resolve (KM-04)")

    @model_validator(mode="after")
    def check_weights_sum(self) -> StructuralDifficultyWeights:
        """P1.7: Validate weights sum to 100."""
        total = self.solution_depth + self.branch_count + self.local_candidates + self.refutation_count + self.proof_depth
        if abs(total - 100.0) > 0.01:
            raise ValueError(f"Structural difficulty weights must sum to 100, got {total}")
        return self


class ScoreToLevelEntry(BaseModel):
    max_score: float
    level_slug: str


class PolicyToLevelEntry(BaseModel):
    min_prior: float
    level_slug: str


class PolicyToLevel(BaseModel):
    description: str = ""
    thresholds: list[PolicyToLevelEntry] = Field(default_factory=list)


class MCTSConfig(BaseModel):
    base_visits: int = 50
    max_trap_density_moves: int = 5


class DifficultyNormalizationConfig(BaseModel):
    """Difficulty normalization ceilings (Plan 010, D41)."""
    description: str = ""
    max_solution_depth: float = Field(default=15.0, gt=0)
    max_branch_count: float = Field(default=5.0, gt=0)
    max_local_candidates: float = Field(default=20.0, gt=0)
    max_refutation_count: float = Field(default=5.0, gt=0)
    max_visits_cap: int = Field(default=20000, gt=0)
    disagree_multiplier: int = Field(default=2, ge=1, le=10)
    max_resolved_depth_ceiling: int = Field(default=20, gt=0, description="Normalization ceiling for proof-depth signal (KM-04)")


class DifficultyConfig(BaseModel):
    description: str = ""
    weights: DifficultyWeights = Field(default_factory=DifficultyWeights)
    structural_weights: StructuralDifficultyWeights = Field(
        default_factory=StructuralDifficultyWeights,
    )
    score_to_level_thresholds: list[ScoreToLevelEntry] = Field(default_factory=list)
    policy_to_level: PolicyToLevel = Field(default_factory=PolicyToLevel)
    mcts: MCTSConfig = Field(default_factory=MCTSConfig)
    normalization: DifficultyNormalizationConfig | None = Field(
        default=None,
        description="Normalization ceilings for structural difficulty components",
    )
    score_normalization_cap: float = Field(
        default=30.0, gt=0,
        description="Cap for |score_delta| normalization in trap density (v1.17)",
    )
    trap_density_floor: float = Field(
        default=0.05, ge=0.0, le=1.0,
        description="Per-puzzle floor for trap density when >=1 refutation exists (v1.17)",
    )


class QualityGatesConfig(BaseModel):
    """Configurable acceptance thresholds for performance tests and calibration."""
    acceptance_threshold: float = Field(
        default=0.95,
        ge=0.0, le=1.0,
        description="Minimum fraction of puzzles that must pass validation (e.g. 0.85 = 85%)",
    )
    difficulty_match_threshold: float = Field(
        default=0.85,
        ge=0.0, le=1.0,
        description="Minimum fraction of puzzles whose difficulty must be within ±1 level",
    )


class SparsePositionConfig(BaseModel):
    """Sparse position detection (R1).

    Auto-escalate to referee for low-density boards where the
    quick model struggles with global context.
    """
    density_threshold: float = Field(
        default=0.08, ge=0.0, le=1.0,
        description="Stone density below which the position is considered sparse",
    )
    min_board_size: int = Field(
        default=13, ge=5, le=19,
        description="Only apply sparse detection for boards >= this size",
    )
    action: str = Field(
        default="escalate_to_referee",
        description="What to do for sparse positions: escalate_to_referee",
    )


class EscalationLevel(BaseModel):
    visits: int
    description: str = ""


class EscalationConfig(BaseModel):
    levels: list[EscalationLevel] = Field(default_factory=list)
    uncertain_value_low: float = 0.3
    uncertain_value_high: float = 0.7


class CalibratedRankElo(BaseModel):
    """A single row in KaTrain's CALIBRATED_RANK_ELO table.

    MIT licensed, sourced from github.com/sanderland/katrain.
    kyu_rank uses the convention: positive = kyu, 0 = 1d, negative = higher dan.
    """
    elo: float = Field(description="Calibrated Elo rating")
    kyu_rank: int = Field(description="Kyu rank (positive=kyu, 0=1d, -1=2d, etc.)")


class EloAnchorConfig(BaseModel):
    """Elo-anchor hard gate for level validation (v1.17).

    Cross-checks composite difficulty level against KaTrain's
    CALIBRATED_RANK_ELO table. Overrides level when divergence
    exceeds threshold. Covered range: elementary through high-dan.
    """
    enabled: bool = Field(
        default=True,
        description="Enable Elo-anchor hard gate",
    )
    override_threshold_levels: int = Field(
        default=2, ge=1, le=5,
        description="Override level when divergence >= this many level steps",
    )
    min_covered_rank_kyu: int = Field(
        default=18,
        description="Lowest kyu rank covered by calibration data (18 = 18k = elementary)",
    )
    max_covered_rank_dan: int = Field(
        default=5,
        description="Highest dan rank covered (5 = 5d = high-dan)",
    )
    calibrated_rank_elo: list[CalibratedRankElo] = Field(
        default_factory=list,
        description="KaTrain CALIBRATED_RANK_ELO table (MIT licensed)",
    )


class QualityWeightsConfig(BaseModel):
    """Panel-validated qk quality algorithm weights (GQ-1, C3).

    qk_raw = trap_density_w * trap + avg_depth_w * norm(depth) + rank_w * norm(rank) + entropy_w * entropy
    Visit gate: qk_raw *= low_visit_multiplier when total_visits < rank_min_visits
    Final: qk = clamp(round(qk_raw * 5), 0, 5)
    """
    trap_density: float = Field(default=0.40, ge=0.0, le=1.0)
    avg_refutation_depth: float = Field(default=0.30, ge=0.0, le=1.0)
    correct_move_rank: float = Field(default=0.20, ge=0.0, le=1.0)
    policy_entropy: float = Field(default=0.10, ge=0.0, le=1.0)
    rank_min_visits: int = Field(default=500, ge=0)
    rank_clamp_max: int = Field(default=8, ge=1)
    avg_depth_max: int = Field(default=10, ge=1)
    low_visit_multiplier: float = Field(default=0.7, ge=0.0, le=1.0)
