"""
State models for pipeline execution tracking.
"""

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from backend.puzzle_manager.models.enums import RunStatus


def _utc_now() -> datetime:
    """Return current UTC datetime (timezone-aware)."""
    return datetime.now(UTC)


class Failure(BaseModel):
    """Record of a failed item."""

    item_id: str = Field(..., description="Puzzle/file identifier")
    stage: str = Field(..., description="Stage where failure occurred")
    error_type: str = Field(..., description="Exception class name")
    error_message: str = Field(..., description="Error description")
    timestamp: datetime = Field(default_factory=_utc_now)
    source_path: str | None = Field(None, description="Original file path")
    failed_path: str | None = Field(None, description="Path in failed/ directory")


class StageState(BaseModel):
    """State of a single pipeline stage."""

    name: str = Field(..., description="Stage name: ingest, analyze, publish")
    status: RunStatus = Field(RunStatus.PENDING, description="Stage status")
    started_at: datetime | None = Field(None, description="Stage start time")
    completed_at: datetime | None = Field(None, description="Stage completion time")
    processed_count: int = Field(0, description="Items processed")
    failed_count: int = Field(0, description="Items failed")
    skipped_count: int = Field(0, description="Items skipped")
    last_batch_id: str | None = Field(None, description="Last completed batch")

    def start(self) -> None:
        """Mark stage as started."""
        self.status = RunStatus.RUNNING
        self.started_at = datetime.now(UTC)

    def complete(self) -> None:
        """Mark stage as completed."""
        self.status = RunStatus.COMPLETED
        self.completed_at = datetime.now(UTC)

    def fail(self) -> None:
        """Mark stage as failed."""
        self.status = RunStatus.FAILED
        self.completed_at = datetime.now(UTC)

    def add_processed(self, count: int = 1) -> None:
        """Add to processed count."""
        self.processed_count += count

    def add_failed(self, count: int = 1) -> None:
        """Add to failed count."""
        self.failed_count += count

    def add_skipped(self, count: int = 1) -> None:
        """Add to skipped count."""
        self.skipped_count += count


class RunState(BaseModel):
    """Complete state of a pipeline run."""

    run_id: str = Field(..., description="UUID for this run")
    status: RunStatus = Field(RunStatus.PENDING, description="Run status")
    started_at: datetime = Field(default=None, description="Run start time")
    completed_at: datetime | None = Field(None, description="Run completion time")
    stages: list[StageState] = Field(
        default_factory=lambda: [
            StageState(name="ingest"),
            StageState(name="analyze"),
            StageState(name="publish"),
        ],
        description="State of each stage",
    )
    failures: list[Failure] = Field(default_factory=list, description="Failed items")
    config_snapshot: dict[str, Any] | None = Field(None, description="Config used for this run")

    def __init__(self, **data):
        """Initialize with timezone-aware started_at default."""
        if "started_at" not in data:
            data["started_at"] = _utc_now()
        super().__init__(**data)

    @property
    def current_stage(self) -> str | None:
        """Get name of currently running stage."""
        for stage in self.stages:
            if stage.status == RunStatus.RUNNING:
                return stage.name
        return None

    @property
    def is_complete(self) -> bool:
        """Check if all stages are complete."""
        return all(
            s.status in (RunStatus.COMPLETED, RunStatus.FAILED)
            for s in self.stages
        )

    def get_stage(self, name: str) -> StageState | None:
        """Get stage by name."""
        for stage in self.stages:
            if stage.name == name:
                return stage
        return None

    def start(self) -> None:
        """Mark run as started."""
        self.status = RunStatus.RUNNING
        self.started_at = datetime.now(UTC)

    def complete(self) -> None:
        """Mark run as completed."""
        self.status = RunStatus.COMPLETED
        self.completed_at = datetime.now(UTC)

    def fail(self) -> None:
        """Mark run as failed."""
        self.status = RunStatus.FAILED
        self.completed_at = datetime.now(UTC)

    def add_failure(self, failure: Failure) -> None:
        """Add a failure record."""
        self.failures.append(failure)

    def get_total_processed(self) -> int:
        """Get total items processed across all stages."""
        return sum(s.processed_count for s in self.stages)

    def get_total_failed(self) -> int:
        """Get total items failed across all stages."""
        return sum(s.failed_count for s in self.stages)

    model_config = {
        "validate_assignment": True,
    }
