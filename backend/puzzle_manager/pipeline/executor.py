"""
Stage executor for running individual stages.

Handles stage lifecycle, timing, state updates, and error handling.
"""

import logging
import time
from typing import Any

from backend.puzzle_manager.stages.protocol import StageContext, StageResult, StageRunner
from backend.puzzle_manager.state.manager import StateManager

logger = logging.getLogger("puzzle_manager.pipeline.executor")


class StageExecutor:
    """Executes pipeline stages with proper lifecycle management.

    Handles:
    - Prerequisite validation
    - Timing and metrics
    - State updates
    - Error handling
    """

    def __init__(self, state_manager: StateManager):
        """Initialize executor.

        Args:
            state_manager: State manager for tracking progress
        """
        self.state_manager = state_manager

    def execute(self, stage: StageRunner, context: StageContext) -> StageResult:
        """Execute a single stage.

        Args:
            stage: Stage runner to execute
            context: Execution context

        Returns:
            StageResult with execution outcome

        Raises:
            PipelineError: If prerequisites fail or unrecoverable error
        """
        stage_name = stage.name

        # Build extra fields for logging
        log_extra: dict[str, Any] = {
            "stage": stage_name,
            "action": "stage_start",
        }
        if context.source_id:
            log_extra["source_id"] = context.source_id
        if context.batch_size:
            log_extra["batch_size"] = context.batch_size

        logger.info("Stage starting", extra=log_extra)

        # Update state
        self.state_manager.start_stage(stage_name)

        start_time = time.time()

        try:
            # Check prerequisites
            prereq_errors = stage.validate_prerequisites(context)
            if prereq_errors:
                error_msg = f"Prerequisites failed: {', '.join(prereq_errors)}"
                logger.warning(f"Stage {stage_name}: {error_msg}")
                result = StageResult.failure_result(
                    error_msg,
                    duration=time.time() - start_time,
                )
                self.state_manager.complete_stage(stage_name, 0, 0, error_msg)
                return result

            # Execute stage
            result = stage.run(context)

            # Update state
            self.state_manager.complete_stage(
                stage_name,
                result.processed,
                result.failed,
                result.errors[0] if result.errors else None,
                result.skipped,
            )

            logger.info(
                "Stage complete",
                extra={
                    "stage": stage_name,
                    "action": "stage_complete",
                    "processed": result.processed,
                    "failed": result.failed,
                    "duration_s": round(time.time() - start_time, 2),
                },
            )
            return result

        except Exception as e:
            duration = time.time() - start_time
            error_msg = f"Stage execution error: {e}"
            logger.error(f"Stage {stage_name} failed: {e}", exc_info=True)

            self.state_manager.complete_stage(stage_name, 0, 0, error_msg)

            return StageResult.failure_result(error_msg, duration=duration)

    def can_resume(self, stage_name: str) -> bool:
        """Check if a stage can be resumed from previous state.

        Args:
            stage_name: Name of stage to check

        Returns:
            True if stage can be resumed
        """
        state = self.state_manager.get_current_run()
        if not state:
            return False

        # Check if stage was started but not completed
        stage_state = state.stages.get(stage_name)
        if not stage_state:
            return False

        return (
            stage_state.started_at is not None
            and stage_state.completed_at is None
        )

    def get_stage_status(self, stage_name: str) -> dict | None:
        """Get status of a specific stage.

        Args:
            stage_name: Name of stage

        Returns:
            Stage status dict or None if not found
        """
        state = self.state_manager.get_current_run()
        if not state:
            return None

        stage_state = state.stages.get(stage_name)
        if not stage_state:
            return None

        return {
            "name": stage_name,
            "status": stage_state.status.value,
            "processed": stage_state.processed,
            "failed": stage_state.failed,
            "started_at": stage_state.started_at,
            "completed_at": stage_state.completed_at,
            "error": stage_state.error,
        }
