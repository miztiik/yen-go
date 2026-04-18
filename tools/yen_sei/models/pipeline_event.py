"""PipelineEvent: telemetry event schema.

SSE-compatible event envelope for streaming pipeline progress
to the GUI and structured log files.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


class PipelineEvent(BaseModel):
    """SSE-compatible event envelope."""

    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    stage: str = Field(description="Pipeline stage: 'harvest', 'refine', etc.")
    event_type: Literal["started", "progress", "completed", "error", "log"] = Field(
        description="Event category"
    )
    data: dict[str, Any] = Field(default_factory=dict, description="Stage-specific payload")
    trace_id: str = Field(default="", description="Pipeline run identifier")
    progress_pct: float | None = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="Completion percentage if known",
    )

    def to_sse(self) -> str:
        """Format as Server-Sent Event string."""
        return f"event: {self.stage}\ndata: {self.model_dump_json()}\n\n"
