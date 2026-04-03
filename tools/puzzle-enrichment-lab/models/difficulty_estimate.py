"""Difficulty estimation model — Task A.3 output.

G10: Renamed from difficulty_result.py to match the class name
(DifficultyEstimate). The old module name caused three independent
reviewers to flag it as dead code.
"""


from pydantic import BaseModel, Field

from models.validation import ConfidenceLevel


class DifficultyEstimate(BaseModel):
    """KataGo-derived difficulty estimate for a puzzle (Phase S.3)."""
    puzzle_id: str = ""
    policy_prior: float = Field(
        default=0.0, description="Correct move's raw policy prior (0-1). Primary KataGo signal."
    )
    visits_to_solve: int | None = Field(
        default=0, description="Estimated MCTS visits to identify correct move as top. KataGo signal."
    )
    trap_density: float | None = Field(
        default=0.0,
        description="KaTrain-style trap density — how tempting wrong moves are (0-1). KataGo signal.",
    )
    solution_depth: int = Field(
        default=0, description="PV length for correct line"
    )
    branch_count: int = Field(
        default=0, description="Branching points in correct solution tree (Phase R.3)"
    )
    local_candidate_count: int = Field(
        default=0, description="Empty intersections near stones (positional ambiguity, Phase R.3)"
    )
    refutation_count: int = Field(
        default=0, description="Number of plausible wrong moves"
    )
    raw_difficulty_score: float = Field(
        default=0.0, description="Composite difficulty score 0-100"
    )
    estimated_level: str = Field(
        default="unknown", description="Yen-Go level slug (novice..expert)"
    )
    estimated_level_id: int = Field(
        default=0, description="Numeric level ID from puzzle-levels.json"
    )
    confidence: ConfidenceLevel = Field(default=ConfidenceLevel.LOW, description="Epistemic confidence in difficulty estimate")
    confidence_reason: str = Field(
        default="",
        description="Why confidence was set to this level (e.g. 'depth_capped', 'ko_capped', 'katago_disagrees')",
    )
