"""SGF writeback stage — builds enriched SGF from analysis result.

Isolated from TeachingStage for SRP: this stage only writes enriched SGF.
Error policy: DEGRADE (SGF enrichment is optional).
"""
from __future__ import annotations

import logging
import time

try:
    from analyzers.sgf_enricher import enrich_sgf as _enrich_sgf
    from analyzers.stages.protocols import EnrichmentStage, ErrorPolicy, PipelineContext
except ImportError:
    from ..sgf_enricher import enrich_sgf as _enrich_sgf
    from ..stages.protocols import ErrorPolicy, PipelineContext

logger = logging.getLogger(__name__)


class SgfWritebackStage:
    """Build enriched SGF string from analysis result."""

    @property
    def name(self) -> str:
        return "sgf_writeback"

    @property
    def error_policy(self) -> ErrorPolicy:
        return ErrorPolicy.DEGRADE

    async def run(self, ctx: PipelineContext) -> PipelineContext:
        result = ctx.result
        puzzle_id = ctx.metadata.puzzle_id

        if ctx.notify_fn is not None:
            await ctx.notify_fn("enriched_sgf", {
                "puzzle_id": puzzle_id,
                "status": "building",
            })

        t_enrich_sgf_start = time.monotonic()
        try:
            enriched_sgf_text = _enrich_sgf(ctx.sgf_text, result)
            result.enriched_sgf = enriched_sgf_text
            if ctx.notify_fn is not None:
                await ctx.notify_fn("enriched_sgf", {
                    "puzzle_id": puzzle_id,
                    "sgf": enriched_sgf_text,
                    "status": "complete",
                })
            logger.info(
                "enriched_sgf",
                extra={"stage": "sgf_writeback", "sgf_length": len(enriched_sgf_text)},
            )
            logger.info("enriched_sgf_content: %s", enriched_sgf_text)
        except Exception as e:
            logger.warning(
                "enriched_sgf_failed",
                extra={"stage": "sgf_writeback", "error": str(e)},
            )
            if ctx.notify_fn is not None:
                await ctx.notify_fn("enriched_sgf", {
                    "puzzle_id": puzzle_id,
                    "status": "failed",
                    "error": str(e),
                })
        ctx.timings["enrich_sgf"] = time.monotonic() - t_enrich_sgf_start

        return ctx
