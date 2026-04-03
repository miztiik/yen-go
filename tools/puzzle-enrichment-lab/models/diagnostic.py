"""Per-puzzle enrichment diagnostic model (G10).

Captures what stages ran, what signals were computed, goal agreement,
errors, timings, and quality score for each enriched puzzle. Aggregated
at batch level by BatchSummaryAccumulator.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class PuzzleDiagnostic(BaseModel):
    """Structured diagnostic for a single puzzle enrichment run (AC-15)."""

    puzzle_id: str = ""
    source_file: str = ""
    timestamp: str = ""
    stages_run: list[str] = Field(default_factory=list)
    stages_skipped: list[str] = Field(default_factory=list)
    signals_computed: dict[str, Any] = Field(default_factory=dict)
    goal_stated: str = ""
    goal_inferred: str = ""
    goal_agreement: str = Field(
        default="unknown",
        description="Match status: 'match' | 'mismatch' | 'unknown'",
    )
    disagreements: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    phase_timings: dict[str, float] = Field(default_factory=dict)
    qk_score: int = Field(default=0, ge=0, le=5)
    ac_level: int = Field(default=0, ge=0, le=3)
    enrichment_tier: int = Field(default=0, ge=0, le=3)
