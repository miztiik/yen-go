"""Validation outcome types for KataGo puzzle enrichment.

Extracted from analyzers/validate_correct_move.py to break the inverse
dependency (V-1): models should not import from analyzers.

These types are the canonical definitions — analyzers/validate_correct_move.py
re-exports them for backward compatibility.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Confidence enum (shared across difficulty, root winrate, goal confidence)
# ---------------------------------------------------------------------------


class ConfidenceLevel(str, Enum):
    """Epistemic confidence in a pipeline assessment.

    Shared across difficulty estimation, root winrate confidence,
    goal inference confidence, and solved-move confidence.
    """
    HIGH = "high"       # Multiple convergent signals; production-ready
    MEDIUM = "medium"   # Primary signal strong, secondary mixed
    LOW = "low"         # Insufficient or conflicting signals; needs review


# ---------------------------------------------------------------------------
# Status enum
# ---------------------------------------------------------------------------


class ValidationStatus(str, Enum):
    """Outcome of KataGo validation against the SGF's correct move."""
    ACCEPTED = "accepted"   # KataGo agrees
    FLAGGED = "flagged"     # Uncertain — needs human review
    REJECTED = "rejected"   # KataGo disagrees


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


class CorrectMoveResult(BaseModel):
    """Result of validating one correct move against KataGo analysis.

    Pydantic BaseModel consistent with all other models in the project.
    Also serves as input to estimate_difficulty (eliminating the need for
    a separate bridge model).
    """

    status: ValidationStatus = Field(description="Validation outcome")
    katago_agrees: bool = Field(description="True if KataGo's top move matches the correct move")
    correct_move_gtp: str = Field(description="GTP coordinate of the correct move")
    katago_top_move: str = Field(default="", description="GTP coordinate of KataGo's top move")
    correct_move_winrate: float = Field(default=0.0, description="Winrate after the correct move")
    correct_move_policy: float = Field(default=0.0, description="Policy prior for the correct move")
    validator_used: str = Field(default="", description="Which validator handled this puzzle")
    flags: list[str] = Field(default_factory=list, description="Diagnostic flags")
    # Fields used by estimate_difficulty
    puzzle_id: str = Field(default="", description="Puzzle identifier")
    visits_used: int = Field(default=0, ge=0, description="Total MCTS visits allocated for the analysis call")
    correct_move_visits: int = Field(
        default=0, ge=0,
        description=(
            "MCTS visits KataGo allocated to THIS correct move in the search tree "
            "(C1 fix: per-move signal, not total visits). "
            "Higher = KataGo explored this move more deeply. "
            "Used as the visits_to_solve difficulty signal in estimate_difficulty()."
        ),
    )
    confidence: ConfidenceLevel = Field(default=ConfidenceLevel.LOW, description="Epistemic confidence in validation")
    # Phase R.4: Deep tree validation fields
    tree_validation_depth: int = Field(
        default=0, ge=0,
        description="Number of solution moves validated against KataGo (Phase R.4)",
    )
    tree_validation_status: str = Field(
        default="not_validated",
        description="Solution tree validation status: not_validated | pass | partial | fail (Phase R.4)",
    )
    unframed_root_winrate: float | None = Field(
        default=None,
        description=(
            "Root winrate from unframed position (tree validation depth-0 query). "
            "None if tree validation was skipped. Used to detect frame-induced "
            "value distortion when framed WR << unframed WR."
        ),
    )
