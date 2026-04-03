"""Stage runner — auto-wraps enrichment stages with notify/timing/error handling.

The runner eliminates boilerplate from individual stages: each stage
focuses purely on its enrichment logic, while the runner handles
cross-cutting concerns (notifications, timing, error policy).
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

from analyzers.stages.protocols import (
    EnrichmentStage,
    ErrorPolicy,
    PipelineContext,
    StageResult,
)

logger = logging.getLogger(__name__)


class StageRunner:
    """Runs enrichment stages with auto-wrapped notify/timing/error handling."""

    @staticmethod
    async def run_stage(
        stage: EnrichmentStage,
        ctx: PipelineContext,
    ) -> StageResult:
        """Execute a single stage with timing, notify, and error policy."""
        # Notify start
        if ctx.notify_fn is not None:
            await ctx.notify_fn(stage.name, {"step": stage.name, "status": "running"})

        t_start = time.monotonic()
        puzzle_id = ctx.metadata.puzzle_id if ctx.metadata else ""
        logger.info(
            f"stage_start: {stage.name}",
            extra={"stage": stage.name, "puzzle_id": puzzle_id},
        )
        try:
            ctx = await stage.run(ctx)
            elapsed = time.monotonic() - t_start
            ctx.timings[stage.name] = elapsed
            logger.info(
                f"stage_end: {stage.name} completed in {elapsed:.3f}s",
                extra={"stage": stage.name, "elapsed_s": f"{elapsed:.3f}", "puzzle_id": puzzle_id},
            )
            return StageResult(stage_name=stage.name, success=True)
        except Exception as e:
            elapsed = time.monotonic() - t_start
            ctx.timings[stage.name] = elapsed

            if stage.error_policy == ErrorPolicy.FAIL_FAST:
                logger.error(
                    f"stage_end: {stage.name} failed (FAIL_FAST) after {elapsed:.3f}s: {e}",
                    extra={"stage": stage.name, "elapsed_s": f"{elapsed:.3f}", "puzzle_id": puzzle_id},
                )
                raise
            else:
                # DEGRADE: log warning and continue
                logger.warning(
                    f"stage_end: {stage.name} degraded after {elapsed:.3f}s: {e} (continuing)",
                    extra={"stage": stage.name, "elapsed_s": f"{elapsed:.3f}", "puzzle_id": puzzle_id},
                )
                return StageResult(
                    stage_name=stage.name,
                    success=False,
                    error=str(e),
                    degraded=True,
                )

    @staticmethod
    async def run_pipeline(
        stages: Sequence[EnrichmentStage],
        ctx: PipelineContext,
    ) -> tuple[PipelineContext, list[StageResult]]:
        """Run an ordered sequence of stages, returning context and results."""
        results: list[StageResult] = []
        for stage in stages:
            result = await StageRunner.run_stage(stage, ctx)
            results.append(result)
            if not result.success and stage.error_policy == ErrorPolicy.FAIL_FAST:
                break
        return ctx, results
