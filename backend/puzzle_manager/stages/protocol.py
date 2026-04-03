"""
Stage protocol definitions for pipeline stages.

Implements stage-protocol.md contract.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from backend.puzzle_manager.models.config import PipelineConfig
from backend.puzzle_manager.state.models import RunState

if TYPE_CHECKING:
    from backend.puzzle_manager.core.enrichment import EnrichmentConfig


@dataclass
class StageContext:
    """Context passed to stage runner.

    Contains configuration, paths, state, and execution options.

    IMPORTANT: All output paths must be derived from output_dir.
    Do NOT call get_output_dir() or similar functions directly in stages.
    This ensures tests can use tmp_path without polluting production data.
    """

    config: PipelineConfig
    staging_dir: Path
    output_dir: Path
    state: RunState
    dry_run: bool = False
    batch_size: int | None = None
    source_id: str | None = None  # Source adapter ID (required in production per spec-043)
    skip_validation: bool = False  # Skip SGF validation (T086: emergency bypass)
    enrichment_config: "EnrichmentConfig | None" = None  # Enrichment configuration (spec 042)
    resume: bool = False  # Spec 109: Resume from adapter checkpoint
    flush_interval: int | None = None  # Override flush interval (None = use config default)

    @property
    def run_id(self) -> str:
        """Get the run ID from state.

        Convenience property for accessing run_id consistently.
        """
        return self.state.run_id

    # === Derived output paths (use these instead of get_*_dir() functions) ===

    @property
    def ops_dir(self) -> Path:
        """Get operational state directory (output_dir/.puzzle-inventory-state/).

        Spec 107: Operational files (inventory, publish-log, rollback-backup)
        are stored separately from content (sgf/, views/).
        """
        return self.output_dir / ".puzzle-inventory-state"

    @property
    def sgf_output_dir(self) -> Path:
        """Get SGF output directory (output_dir/sgf/)."""
        return self.output_dir / "sgf"

    @property
    def db_output_path(self) -> Path:
        """Get search database output path (output_dir/yengo-search.db)."""
        return self.output_dir / "yengo-search.db"

    @property
    def db_version_path(self) -> Path:
        """Get database version file path (output_dir/db-version.json)."""
        return self.output_dir / "db-version.json"

    @property
    def content_db_path(self) -> Path:
        """Get content database path (output_dir/yengo-content.db)."""
        return self.output_dir / "yengo-content.db"

    @property
    def publish_log_dir(self) -> Path:
        """Get publish log directory (ops_dir/publish-log/).

        Spec 107: Moved to ops_dir for clear separation of content vs operational files.
        """
        return self.ops_dir / "publish-log"

    @property
    def rollback_backup_dir(self) -> Path:
        """Get rollback backup directory (ops_dir/rollback-backup/).

        Spec 107: Moved to ops_dir for clear separation of content vs operational files.
        """
        return self.ops_dir / "rollback-backup"

    @property
    def inventory_path(self) -> Path:
        """Get inventory file path (ops_dir/inventory.json).

        Spec 107: Renamed from puzzle-collection-inventory.json and moved to ops_dir.
        """
        return self.ops_dir / "inventory.json"

    @property
    def audit_log_path(self) -> Path:
        """Get audit log file path (ops_dir/audit.jsonl).

        Spec 107: Moved to ops_dir for clear separation of content vs operational files.
        """
        return self.ops_dir / "audit.jsonl"



    # === Staging paths ===

    def get_ingest_dir(self) -> Path:
        """Get ingest staging directory."""
        return self.staging_dir / "ingest"

    def get_analyzed_dir(self) -> Path:
        """Get analyzed staging directory."""
        return self.staging_dir / "analyzed"

    def get_failed_dir(self, stage: str) -> Path:
        """Get failed files directory for a stage."""
        return self.staging_dir / "failed" / stage


@dataclass
class StageResult:
    """Result of stage execution."""

    success: bool
    processed: int = 0
    failed: int = 0
    skipped: int = 0
    remaining: int = 0  # Files remaining in staging after this stage
    errors: list[str] = field(default_factory=list)
    duration_seconds: float = 0.0
    resolved_paths: list[str] = field(default_factory=list)  # Spec 105: Actual paths written (e.g., publish stage SGF dirs)

    @classmethod
    def success_result(cls, processed: int, duration: float) -> "StageResult":
        """Create a successful result."""
        return cls(success=True, processed=processed, duration_seconds=duration)

    @classmethod
    def partial_result(
        cls,
        processed: int,
        failed: int,
        errors: list[str],
        duration: float,
        skipped: int = 0,
        remaining: int = 0,
        resolved_paths: list[str] | None = None,
    ) -> "StageResult":
        """Create a partial success result (some failures)."""
        return cls(
            success=failed == 0,
            processed=processed,
            failed=failed,
            skipped=skipped,
            remaining=remaining,
            errors=errors,
            duration_seconds=duration,
            resolved_paths=resolved_paths or [],
        )

    @classmethod
    def failure_result(cls, error: str, duration: float = 0.0) -> "StageResult":
        """Create a failure result."""
        return cls(
            success=False,
            errors=[error],
            duration_seconds=duration,
        )

    def __str__(self) -> str:
        status = "OK" if self.success else "FAILED"
        parts = [
            f"StageResult({status}: ",
            f"processed={self.processed}, ",
            f"failed={self.failed}, ",
            f"skipped={self.skipped}, ",
        ]
        if self.remaining > 0:
            parts.append(f"remaining={self.remaining}, ")
        parts.append(f"duration={self.duration_seconds:.2f}s)")
        return "".join(parts)


@runtime_checkable
class StageRunner(Protocol):
    """Protocol for pipeline stage implementations.

    All stages must implement this protocol for execution by StageExecutor.
    """

    @property
    def name(self) -> str:
        """Stage name: 'ingest', 'analyze', or 'publish'."""
        ...

    def run(self, context: StageContext) -> StageResult:
        """Execute the stage.

        Args:
            context: Execution context with config, paths, state.

        Returns:
            StageResult with counts and errors.
        """
        ...

    def validate_prerequisites(self, context: StageContext) -> list[str]:
        """Check prerequisites before running.

        Returns:
            List of error messages (empty if all prerequisites met).
        """
        ...
