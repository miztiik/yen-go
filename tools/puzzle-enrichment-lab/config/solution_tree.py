"""Solution tree construction config models.

Groups: depth profiles, Benson gate, solution tree config,
seki detection for trees, goal inference, and edge case boosts.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class DepthProfile(BaseModel):
    """Solution tree depth limits for a level category (DD-1)."""
    solution_min_depth: int = Field(ge=1, le=50, description="Min plies before stopping")
    solution_max_depth: int = Field(ge=1, le=50, description="Hard cap on tree depth")

    @model_validator(mode="after")
    def min_le_max(self) -> DepthProfile:
        if self.solution_min_depth > self.solution_max_depth:
            raise ValueError(
                f"solution_min_depth ({self.solution_min_depth}) "
                f"> solution_max_depth ({self.solution_max_depth})"
            )
        return self


class BensonGateConfig(BaseModel):
    """Config for Benson unconditional life (G1) and interior-point death (G2) gates.

    Controls whether pre-query terminal detection is active and sets
    minimum thresholds to avoid running the algorithm on trivial positions.
    """
    enabled: bool = Field(
        default=True,
        description="Master enable/disable for Benson gate and interior-point gate",
    )
    min_contest_stones: int = Field(
        default=1, ge=0, le=100,
        description="Minimum defender stones in puzzle_region to run Benson check",
    )


class SolutionTreeConfig(BaseModel):
    """Solution tree construction parameters (DD-1, DD-3).

    Category-aware depth profiles, branching limits, and query budget.
    """
    depth_profiles: dict[str, DepthProfile] = Field(
        default_factory=lambda: {
            "entry": DepthProfile(solution_min_depth=2, solution_max_depth=10),
            "core": DepthProfile(solution_min_depth=3, solution_max_depth=16),
            "strong": DepthProfile(solution_min_depth=4, solution_max_depth=28),
        },
        description="Depth limits per level category (entry/core/strong)",
    )
    wr_epsilon: float = Field(
        default=0.02, ge=0.0, le=0.5,
        description="Winrate stability threshold for stopping",
    )
    own_epsilon: float = Field(
        default=0.05, ge=0.0, le=0.5,
        description="Ownership convergence threshold for stopping",
    )
    branch_min_policy: float = Field(
        default=0.05, ge=0.0, le=1.0,
        description="Base min policy for opponent branches at depth 1 (DD-3, L3)",
    )
    depth_policy_scale: float = Field(
        default=0.01, ge=0.0, le=0.1,
        description=(
            "Per-depth increment added to branch_min_policy at opponent nodes. "
            "Effective threshold = branch_min_policy + depth_policy_scale * depth. "
            "Deeper branches require higher policy to be explored (L3 — Thomsen lambda-search). "
        ),
    )
    max_branch_width: int = Field(
        default=3, ge=1, le=10,
        description="Max opponent branches per node (DD-3)",
    )
    max_total_tree_queries: int = Field(
        default=50, ge=1, le=1000,
        description="Global per-puzzle query budget for tree construction (DD-3)",
    )
    confirmation_min_policy: float = Field(
        default=0.03, ge=0.0, le=1.0,
        description="Min policy to confirm a candidate move (pre-filter, DD-2)",
    )
    confirmation_visits: int = Field(
        default=750, ge=50, le=100000,
        description="MCTS visits for per-candidate confirmation queries (S1-G16, DD-2)",
    )
    tree_visits: int = Field(
        default=500, ge=50, le=100000,
        description="MCTS visits per tree-depth query",
    )
    max_correct_root_trees: int = Field(
        default=2, ge=1, le=5,
        description="Max first-move correct roots to build (DD-4, §4)",
    )
    max_refutation_root_trees: int = Field(
        default=3, ge=0, le=10,
        description="Max wrong first-move roots to build (DD-4, §4)",
    )
    simulation_enabled: bool = Field(
        default=True,
        description="Enable Kawano simulation across sibling branches (KM-01)",
    )
    simulation_verify_visits: int = Field(
        default=50, ge=1, le=100000,
        description="MCTS visits for simulation verification queries (KM-01)",
    )
    forced_move_visits: int = Field(
        default=125, ge=0, le=100000,
        description=(
            "MCTS visits for forced-move fast-path queries (KM-03). "
            "0 disables forced-move detection."
        ),
    )
    forced_move_policy_threshold: float = Field(
        default=0.85, ge=0.0, le=1.0,
        description="Min policy prior to consider a move forced (KM-03)",
    )
    transposition_enabled: bool = Field(
        default=True,
        description="Enable position-hash transposition table within tree building (KM-02)",
    )
    terminal_detection_enabled: bool = Field(
        default=True,
        description=(
            "Enable pre-query terminal detection gates: "
            "Benson unconditional life (G1) + interior-point death check (G2)"
        ),
    )
    benson_gate: BensonGateConfig = Field(
        default_factory=BensonGateConfig,
        description="Benson gate and interior-point gate configuration (RC-3)",
    )
    visit_allocation_mode: str = Field(
        default="fixed",
        description="PI-2: Visit allocation mode. 'fixed' = current behavior "
        "(all nodes get tree_visits), 'adaptive' = branch nodes get branch_visits, "
        "continuation/forced nodes get continuation_visits.",
    )
    branch_visits: int = Field(
        default=500, ge=50, le=100000,
        description="PI-2: MCTS visits for decision-point (branch) nodes in adaptive mode.",
    )
    continuation_visits: int = Field(
        default=125, ge=50, le=100000,
        description="PI-2: MCTS visits for forced/continuation nodes in adaptive mode.",
    )
    player_alternative_rate: float = Field(
        default=0.0, ge=0.0, le=1.0,
        description="PI-9: Probability of exploring player alternatives at player nodes. "
        "0.0 = never explore alternatives (current behavior). "
        "When player_alternative_auto_detect=True, this is overridden per puzzle type.",
    )
    player_alternative_auto_detect: bool = Field(
        default=True,
        description="PI-9: Auto-detect whether to explore player alternatives based on "
        "puzzle type. position-only → rate=0.05, multi-solution → rate=0.05, "
        "single-answer curated → rate=0.0.",
    )
    branch_escalation_enabled: bool = Field(
        default=False,
        description="PI-7: Enable branch-local disagreement escalation. "
        "When policy vs search outcome disagree above threshold at an opponent node, "
        "re-evaluate that branch with escalated visits.",
    )
    branch_disagreement_threshold: float = Field(
        default=0.10, ge=0.0, le=1.0,
        description="PI-7: Min disagreement between policy-preferred and search-preferred "
        "move to trigger branch-local escalation. Disagreement = abs(policy_rank - search_rank) "
        "normalized, or abs(policy_best_wr - search_best_wr).",
    )


class AiSolveSekiDetectionConfig(BaseModel):
    """Seki-specific early-exit heuristic for solution trees (DD-1, DD-12).

    Distinct from technique_detection.seki — this controls tree stopping,
    not technique classification.
    """
    winrate_band_low: float = Field(
        default=0.40, ge=0.0, le=0.5,
        description="Lower bound of seki winrate band (aligned with technique_detection.seki)",
    )
    winrate_band_high: float = Field(
        default=0.60, ge=0.5, le=1.0,
        description="Upper bound of seki winrate band (aligned with technique_detection.seki)",
    )
    seki_consecutive_depth: int = Field(
        default=3, ge=1, le=10,
        description="Consecutive depths in seki band before early-exit",
    )
    score_lead_seki_max: float = Field(
        default=2.0, ge=0.0, le=50.0,
        description="Max score lead consistent with seki (low score = balanced)",
    )


class AiSolveGoalInference(BaseModel):
    """Goal inference parameters (DD-8).

    Score delta is primary signal; ownership is secondary with variance gate.
    """
    score_delta_kill: float = Field(
        default=15.0, ge=0.0,
        description="Score delta above which goal is inferred as kill/capture",
    )
    score_delta_ko: float = Field(
        default=5.0, ge=0.0,
        description="Score delta in ko range",
    )
    ownership_threshold: float = Field(
        default=0.7, ge=0.0, le=1.0,
        description="Ownership magnitude threshold for goal inference",
    )
    ownership_variance_gate: float = Field(
        default=0.3, ge=0.0, le=1.0,
        description="If ownership variance > this, goal_confidence='low'",
    )


class EdgeCaseBoosts(BaseModel):
    """Visit boosts for edge cases (DD-12)."""
    corner_visit_boost: float = Field(
        default=1.5, ge=1.0, le=5.0,
        description="Visit multiplier for corner positions",
    )
    ladder_visit_boost: float = Field(
        default=2.0, ge=1.0, le=5.0,
        description="Visit multiplier for suspected ladders (PV > 8 moves)",
    )
    ladder_pv_threshold: int = Field(
        default=8, ge=3, le=30,
        description="PV length above which ladder is suspected",
    )
