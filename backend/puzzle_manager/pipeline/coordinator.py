"""
Pipeline coordinator for orchestrating 3-stage pipeline.

Manages full pipeline execution: INGEST → ANALYZE → PUBLISH

Source ID Requirement (Spec 043)
--------------------------------
The `--source` flag is **required** for pipeline runs. This ensures:

1. **Log correlation**: Every log entry includes `source_id` for filtering/tracing
2. **Publish-log consistency**: All `PublishLogEntry` records have `source_id`
3. **State tracking**: Config snapshot preserves `source_id` for resume

On `--resume`, the coordinator restores `source_id` from the persisted
`config_snapshot` in RunState, ensuring interrupted runs maintain correlation.

Example:
    # This will error - source is required
    python -m backend.puzzle_manager run

    # Correct usage
    python -m backend.puzzle_manager run --source sanderland

    # Resume restores source_id automatically
    python -m backend.puzzle_manager run --resume
"""

from __future__ import annotations

import logging
import time
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from backend.puzzle_manager.config.loader import ConfigLoader
from backend.puzzle_manager.exceptions import PipelineError
from backend.puzzle_manager.inventory.manager import InventoryManager
from backend.puzzle_manager.models.enums import RunStatus
from backend.puzzle_manager.paths import (
    get_output_dir,
    get_pm_staging_dir,
    get_pm_state_dir,
)
from backend.puzzle_manager.pipeline.cleanup import cleanup_old_files
from backend.puzzle_manager.pipeline.executor import StageExecutor
from backend.puzzle_manager.pipeline.lock import PipelineLock
from backend.puzzle_manager.pipeline.prerequisites import check_prerequisites
from backend.puzzle_manager.pm_logging import create_run_logger, set_staging_root
from backend.puzzle_manager.stages.analyze import AnalyzeStage
from backend.puzzle_manager.stages.ingest import IngestStage
from backend.puzzle_manager.stages.protocol import StageContext, StageResult, StageRunner
from backend.puzzle_manager.stages.publish import PublishStage
from backend.puzzle_manager.state.manager import StateManager

if TYPE_CHECKING:
    from backend.puzzle_manager.core.enrichment import EnrichmentConfig


logger = logging.getLogger("puzzle_manager.pipeline")


@dataclass
class PipelineResult:
    """Result of full pipeline execution."""

    success: bool
    stages: dict[str, StageResult] = field(default_factory=dict)
    duration_seconds: float = 0.0
    errors: list[str] = field(default_factory=list)

    @property
    def total_processed(self) -> int:
        """Return unique puzzle count (max of stage counts, not sum).

        Each stage processes the same puzzles, so max reflects actual puzzle count.
        Use total_operations for the sum across all stages if needed.
        """
        if not self.stages:
            return 0
        return max(s.processed for s in self.stages.values())

    @property
    def total_operations(self) -> int:
        """Return sum of all items processed across all stages."""
        return sum(s.processed for s in self.stages.values())

    @property
    def total_failed(self) -> int:
        return sum(s.failed for s in self.stages.values())

    @property
    def total_remaining(self) -> int:
        """Return sum of remaining files across all stages."""
        return sum(s.remaining for s in self.stages.values())

    def __str__(self) -> str:
        status = "OK" if self.success else "FAILED"
        return (
            f"PipelineResult({status}: "
            f"processed={self.total_processed}, "
            f"failed={self.total_failed}, "
            f"duration={self.duration_seconds:.2f}s)"
        )


class PipelineCoordinator:
    """Coordinates execution of the 3-stage pipeline.

    Usage:
        coordinator = PipelineCoordinator()  # Uses production paths
        result = coordinator.run()  # Run all stages
        result = coordinator.run(stages=["ingest"])  # Run specific stages

        # For testing:
        coordinator = PipelineCoordinator(
            staging_dir=tmp_path / "staging",
            state_dir=tmp_path / "state",
            output_dir=tmp_path / "output",
        )
    """

    def __init__(
        self,
        staging_dir: Path | None = None,
        state_dir: Path | None = None,
        output_dir: Path | None = None,
        config_path: str | None = None,
        dry_run: bool = False,
        batch_size: int | None = None,
        source_id: str | None = None,
        enrichment_config: EnrichmentConfig | None = None,
        flush_interval: int | None = None,
    ):
        """Initialize coordinator.

        Args:
            staging_dir: Staging directory (default: get_pm_staging_dir())
            state_dir: State directory (default: get_pm_state_dir())
            output_dir: Output directory (default: get_output_dir())
            config_path: Optional path to config directory
            dry_run: If True, don't write any files
            batch_size: Override batch size from config
            source_id: Filter ingest to specific source
            enrichment_config: Enrichment configuration (spec 042)
            flush_interval: Override flush interval from config (None = use default)
        """
        # Use defaults if not provided
        self.staging_dir = staging_dir or get_pm_staging_dir()
        self.state_dir = state_dir or get_pm_state_dir()
        self.output_dir = output_dir or get_output_dir()

        self.dry_run = dry_run
        self.batch_size = batch_size
        self.source_id = source_id
        self.enrichment_config = enrichment_config
        self.flush_interval = flush_interval
        self._resume = False  # Set by run() method

        # Load configuration
        self.config_loader = ConfigLoader(config_path)
        self.config = self.config_loader.load_pipeline_config()

        # Initialize state manager with explicit path
        self.state_manager = StateManager(state_dir=self.state_dir)
        self.state_manager.init()

        # Initialize inventory manager for stage metrics tracking (Spec 052)
        self.inventory_manager = InventoryManager()

        # Create executor
        self.executor = StageExecutor(self.state_manager)

        # Register stages
        self._stages: dict[str, StageRunner] = {
            "ingest": IngestStage(),
            "analyze": AnalyzeStage(),
            "publish": PublishStage(),
        }

    def run(
        self,
        stages: Sequence[str] | None = None,
        skip_prerequisites: bool = False,
        skip_cleanup: bool = False,
        resume: bool = False,
    ) -> PipelineResult:
        """Run the pipeline.

        Args:
            stages: Specific stages to run (default: all)
            skip_prerequisites: Skip prerequisite checks
            skip_cleanup: Skip cleanup of old files
            resume: Resume from last checkpoint if interrupted

        Returns:
            PipelineResult with stage results
        """
        start_time = time.time()
        errors: list[str] = []

        # Store resume flag for context creation (Spec 109: adapter-level resume)
        self._resume = resume

        # Determine stages to run
        stage_order = ["ingest", "analyze", "publish"]
        if stages:
            # Validate stage names
            invalid = set(stages) - set(stage_order)
            if invalid:
                raise PipelineError(f"Invalid stages: {invalid}")
            stage_order = [s for s in stage_order if s in stages]

        # Acquire pipeline lock to prevent concurrent operations
        pipeline_lock = PipelineLock(run_id=f"pending-{int(start_time)}")
        pipeline_lock.acquire()
        logger.debug("Pipeline lock acquired")

        try:
            return self._run_with_lock(
                stage_order=stage_order,
                skip_prerequisites=skip_prerequisites,
                skip_cleanup=skip_cleanup,
                resume=resume,
                start_time=start_time,
                errors=errors,
            )
        finally:
            pipeline_lock.release()
            logger.debug("Pipeline lock released")

    def _run_with_lock(
        self,
        stage_order: list[str],
        skip_prerequisites: bool,
        skip_cleanup: bool,
        resume: bool,
        start_time: float,
        errors: list[str],
    ) -> PipelineResult:
        """Internal run method executed while holding pipeline lock."""
        # Check for resumable state (must happen before source_id validation for resume to work)
        start_stage_index = 0
        if resume:
            current_run = self.state_manager.load_current()
            if current_run and current_run.status == RunStatus.RUNNING:
                # Find where we left off
                last_stage = current_run.current_stage
                if last_stage and last_stage in stage_order:
                    start_stage_index = stage_order.index(last_stage)
                    logger.info(f"Resuming from stage: {last_stage}")

                # Spec-043: On resume, restore source_id from saved config_snapshot
                if not self.source_id and current_run.config_snapshot:
                    saved_source = current_run.config_snapshot.get("source_id")
                    if saved_source and saved_source != "all":
                        self.source_id = saved_source
                        logger.info(f"Restored source_id from config_snapshot: {saved_source}")

            elif current_run:
                logger.info("Previous run completed, starting fresh")
            else:
                logger.info("No interrupted run found, starting fresh")

        # Spec-051: Fallback to active_adapter if --source not provided
        if not self.source_id:
            try:
                self.source_id = self.config_loader.get_active_adapter()
                logger.info(f"Using active_adapter from sources.json: {self.source_id}")
            except Exception as e:
                # Fall back to old error if active_adapter not configured
                from backend.puzzle_manager.adapters._registry import list_adapters
                available = ", ".join(list_adapters())
                raise PipelineError(
                    f"--source is required (or set 'active_adapter' in sources.json). "
                    f"Available adapters: {available}. Error: {e}"
                ) from e

        # Set staging root for relative path logging (spec-043)
        set_staging_root(self.staging_dir.parent)

        # Log which adapter is selected for this run
        logger.info(f"Pipeline starting with adapter: {self.source_id}")
        logger.info(f"Pipeline stages: {stage_order}")

        # Check prerequisites
        if not skip_prerequisites:
            prereq_errors = check_prerequisites(
                staging_dir=self.staging_dir,
                state_dir=self.state_dir,
                output_dir=self.output_dir,
            )
            if prereq_errors:
                errors.extend(prereq_errors)
                return PipelineResult(
                    success=False,
                    errors=errors,
                    duration_seconds=time.time() - start_time,
                )

        # Start new run (or resume existing) - MUST happen before creating context
        if resume and self.state_manager.load_current():
            run_id = self.state_manager.load_current().run_id
            logger.info(f"Resuming run: {run_id}")
        else:
            # Snapshot config for reproducibility/debugging
            config_snapshot = self.config.model_dump(mode="json")
            run_id = self.state_manager.start_run(config_snapshot=config_snapshot)
            logger.info(f"Started run: {run_id}")

        # Create run logger with context for log correlation (spec-043)
        # Use source_id if provided, otherwise use "all" for multi-source runs
        effective_source_id = self.source_id or "all"
        run_logger = create_run_logger(run_id=run_id, source_id=effective_source_id)
        run_logger.info("Pipeline started", extra={"stages": stage_order})

        # Create context AFTER starting the run so it has the correct run_id
        context = self._create_context()

        # Execute stages (starting from resume point if applicable)
        results: dict[str, StageResult] = {}
        success = True

        for i, stage_name in enumerate(stage_order):
            # Skip already completed stages if resuming
            if i < start_stage_index:
                logger.debug(f"Skipping completed stage: {stage_name}")
                continue

            stage = self._stages[stage_name]

            try:
                result = self.executor.execute(stage, context)
                results[stage_name] = result

                # Spec 105: Collect resolved paths from publish stage
                if stage_name == "publish" and result.resolved_paths:
                    self.state_manager.update_resolved_paths(result.resolved_paths)

                if not result.success:
                    success = False
                    errors.extend(result.errors)
                    # Stop pipeline on stage failure
                    logger.warning(f"Stage {stage_name} failed, stopping pipeline")
                    break

            except Exception as e:
                logger.error(f"Stage {stage_name} error: {e}")
                results[stage_name] = StageResult.failure_result(str(e))
                errors.append(f"Stage {stage_name}: {e}")
                success = False
                break

        # Complete run - pass requested_stages so unrequested stages are marked SKIPPED (spec-043)
        total_processed = sum(r.processed for r in results.values())
        total_failed = sum(r.failed for r in results.values())
        self.state_manager.complete_run(total_processed, total_failed, requested_stages=stage_order)

        # Cleanup old files
        if not skip_cleanup:
            try:
                cleanup_old_files(
                    self.config.retention.days,
                    dry_run=self.dry_run,
                )
            except Exception as e:
                logger.warning(f"Cleanup failed: {e}")
                # Don't fail pipeline for cleanup errors

        duration = time.time() - start_time

        # Structured summary log at pipeline completion (spec-043)
        run_logger.info(
            "Pipeline complete",
            extra={
                "run_id": run_id,
                "source_id": effective_source_id,
                "stages": list(results.keys()),
                "processed": total_processed,
                "failed": total_failed,
                "duration_s": round(duration, 2),
                "success": success,
            },
        )

        return PipelineResult(
            success=success,
            stages=results,
            duration_seconds=duration,
            errors=errors,
        )

    def _create_context(self) -> StageContext:
        """Create stage execution context."""
        return StageContext(
            config=self.config,
            staging_dir=self.staging_dir,
            output_dir=self.output_dir,
            state=self.state_manager.get_current_run(),
            dry_run=self.dry_run,
            batch_size=self.batch_size,
            source_id=self.source_id,
            enrichment_config=self.enrichment_config,
            resume=self._resume,
            flush_interval=self.flush_interval,
        )

    def get_status(self) -> dict:
        """Get pipeline status summary."""
        state = self.state_manager.load_state()
        return {
            "current_run": state.current_run.model_dump() if state.current_run else None,
            "last_run": state.last_run.model_dump() if state.last_run else None,
            "runs_total": len(state.history),
            "available_stages": list(self._stages.keys()),
        }
