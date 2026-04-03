"""
Configuration models for the puzzle manager.
"""

from enum import Enum

from pydantic import BaseModel, Field, field_validator


class CleanupPolicy(str, Enum):
    """Staging cleanup policy.

    Per Spec 027:
    - ON_SUCCESS: Delete processed files after stage completes successfully
    - NEVER: Keep all intermediate files (for debugging)
    """
    ON_SUCCESS = "on_success"
    NEVER = "never"


class BatchConfig(BaseModel):
    """Batch processing configuration.

    Controls pipeline throughput and output directory sharding.

    Attributes:
        size: Maximum puzzles to process per pipeline run.
        max_files_per_dir: Maximum SGF files per batch directory (e.g. sgf/0001/).
            Source of truth for sharding. BatchWriter reads this value;
            it does NOT define its own default.
        flush_interval: Flush batch state to disk every N successfully processed files.
            Reduces data loss window on crash. Set to 0 to disable.
    """

    size: int = Field(2000, ge=1, le=10000, description="Items per batch")
    max_files_per_dir: int = Field(2000, ge=1, le=10000, description="Max SGF files per batch directory")
    flush_interval: int = Field(500, ge=0, le=10000, description="Flush batch state every N processed files (0=disable)")


class RetentionConfig(BaseModel):
    """File retention configuration."""

    logs_days: int = Field(45, ge=1, le=365, description="Log retention days")
    state_days: int = Field(45, ge=1, le=365, description="State file retention days")
    failed_files_days: int = Field(45, ge=1, le=365, description="Failed file retention days")

    @property
    def days(self) -> int:
        """Default retention days (uses logs_days as general default)."""
        return self.logs_days


class DailyConfig(BaseModel):
    """Daily challenge generation configuration."""

    standard_puzzle_count: int = Field(30, ge=1, le=100, description="Standard daily count")
    timed_set_count: int = Field(3, ge=1, le=10, description="Number of timed sets")
    timed_puzzles_per_set: int = Field(50, ge=1, le=200, description="Puzzles per timed set")
    tag_puzzle_count: int = Field(50, ge=1, le=200, description="Puzzles per tag")
    min_quality: int = Field(2, ge=1, le=5, description="Minimum quality level for pool (1=unverified, 5=premium)")
    excluded_content_types: list[int] = Field(
        default_factory=lambda: [3],
        description="Content types to exclude from pool (3=training)",
    )
    level_weights: dict[str, float] = Field(
        default_factory=lambda: {
            "novice": 0.35,
            "beginner": 0.30,
            "elementary": 0.20,
            "intermediate": 0.15,
        },
        description="Weight distribution per level",
    )
    rolling_window_days: int = Field(90, ge=7, le=365, description="Rolling window size in days")

    @property
    def puzzles_per_day(self) -> int:
        """Alias for standard_puzzle_count."""
        return self.standard_puzzle_count

    @field_validator("level_weights")
    @classmethod
    def validate_weights(cls, v: dict[str, float]) -> dict[str, float]:
        """Validate level weights sum to approximately 1.0."""
        total = sum(v.values())
        if not 0.99 <= total <= 1.01:
            raise ValueError(f"Level weights must sum to 1.0, got {total}")
        return v


class OutputConfig(BaseModel):
    """Output path configuration."""

    root: str = Field("yengo-puzzle-collections", description="Output root directory")
    sgf_path: str = Field("sgf/{batch}", description="SGF path template (flat batch dirs, e.g. sgf/0001/)")
    sgf_paths_resolved: list[str] = Field(default_factory=list, description="Actual SGF paths written during run (populated at runtime)")


class StagingConfig(BaseModel):
    """Staging directory configuration."""

    cleanup_policy: CleanupPolicy = Field(
        CleanupPolicy.ON_SUCCESS,
        description="When to clean processed files: on_success or never"
    )


class AdapterConfig(BaseModel):
    """Adapter-specific configuration."""

    request_timeout_seconds: int = Field(30, ge=1, le=300, description="HTTP request timeout")
    max_retries: int = Field(3, ge=0, le=10, description="Retry attempts")
    path: str | None = Field(None, description="Local path (LocalAdapter)")
    move_processed_to: str | None = Field(None, description="Post-process move path")
    base_url: str | None = Field(None, description="API base URL")

    model_config = {
        "extra": "allow",  # Allow adapter-specific fields
    }


class RollbackConfig(BaseModel):
    """Rollback and publish log configuration.

    Per Spec 036 requirements.
    """

    retention_days: int = Field(90, ge=1, le=365, description="Publish log retention days (FR-051)")
    confirmation_threshold: int = Field(100, ge=1, le=10000, description="Puzzles count requiring confirmation (FR-018)")
    max_batch_size: int = Field(10000, ge=1, le=100000, description="Maximum puzzles per rollback (FR-065)")
    validate_before_publish: bool = Field(True, description="Validate SGF before publishing (T084)")
    lock_timeout_hours: int = Field(1, ge=1, le=24, description="Lock file stale threshold in hours (FR-027)")


class SourceConfig(BaseModel):
    """Source definition configuration.

    Note: The 'enabled' field is deprecated (spec-051). Use 'active_adapter'
    in sources.json to select which adapter is active.
    """

    id: str = Field(..., description="Unique source identifier")
    name: str = Field(..., description="Human-readable name")
    adapter: str = Field(..., description="Adapter type name")
    enabled: bool = Field(True, description="DEPRECATED: Use active_adapter in sources.json instead")
    config: AdapterConfig = Field(default_factory=AdapterConfig, description="Adapter-specific config")  # type: ignore[arg-type]


class PipelineConfig(BaseModel):
    """Root pipeline configuration."""

    version: str = Field("1.0", description="Config schema version")
    batch: BatchConfig = Field(default_factory=BatchConfig, description="Batch processing settings")  # type: ignore[arg-type]
    retention: RetentionConfig = Field(default_factory=RetentionConfig, description="Cleanup settings")  # type: ignore[arg-type]
    staging: StagingConfig = Field(default_factory=StagingConfig, description="Staging directory settings")  # type: ignore[arg-type]
    daily: DailyConfig = Field(default_factory=DailyConfig, description="Daily generation settings")  # type: ignore[arg-type]
    output: OutputConfig = Field(default_factory=OutputConfig, description="Output path settings")  # type: ignore[arg-type]
    reconcile_interval: int = Field(
        default=20,
        ge=0,
        le=1000,
        description="Number of publish runs between automatic periodic reconciliation. Set to 0 to disable.",
    )

    model_config = {
        "validate_assignment": True,
    }
