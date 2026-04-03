"""Refutation result model — Task A.2 output."""

from pydantic import BaseModel, Field


class Refutation(BaseModel):
    """A single wrong move and its refutation sequence."""
    wrong_move: str = Field(description="SGF coordinate of the wrong move")
    wrong_move_policy: float = Field(default=0.0, description="How tempting the wrong move looks")
    refutation_sequence: list[str] = Field(
        default_factory=list,
        description="PV after wrong move (2-4 moves, SGF coordinates)"
    )
    refutation_branches: list[list[str]] = Field(
        default_factory=list,
        description="Alternative refutation PV branches (each branch is SGF coordinates)",
    )
    winrate_after_wrong: float = Field(
        default=0.5,
        description="Puzzle-player's winrate after wrong move + opponent response"
    )
    winrate_delta: float = Field(
        default=0.0,
        description="Drop from initial winrate (negative = bad for puzzle player)"
    )
    score_delta: float = Field(
        default=0.0,
        description="Score delta from root position (negative = points lost for puzzle player)",
    )
    ownership_consequence: dict = Field(
        default_factory=dict,
        description="Which key points change ownership"
    )
    refutation_depth: int = Field(
        default=1,
        ge=1,
        description="Number of moves in the refutation PV (how deep the refutation goes)"
    )
    refutation_type: str = Field(
        default="unclassified",
        description="Refutation technique type (unclassified in Phase A; Phase B adds classification)"
    )
    tenuki_flagged: bool = Field(
        default=False,
        description="True when KataGo's PV response is far from the wrong move (T18B)",
    )
    ownership_delta: float = Field(
        default=0.0,
        description="Max absolute ownership shift caused by the wrong move (R-1 signal)",
    )


class RefutationResult(BaseModel):
    """Collection of wrong-move refutations for a puzzle."""
    puzzle_id: str = ""
    refutations: list[Refutation] = Field(default_factory=list)
    total_candidates_evaluated: int = 0
    visits_per_candidate: int = 0
