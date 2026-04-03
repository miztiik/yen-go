"""Instinct classification stage — classify move intent from position geometry.

New stage (OPT-2): runs after TechniqueStage, before TeachingStage.
Error policy: DEGRADE (instinct classification is optional enrichment).
"""
from __future__ import annotations

import logging

try:
    from config.teaching import get_instinct_config

    from analyzers.instinct_classifier import classify_instinct
    from analyzers.stages.protocols import EnrichmentStage, ErrorPolicy, PipelineContext
except ImportError:
    from ...config.teaching import get_instinct_config
    from ..instinct_classifier import classify_instinct
    from ..stages.protocols import ErrorPolicy, PipelineContext

logger = logging.getLogger(__name__)


class InstinctStage:
    """Classify correct move intent from position geometry.

    Reads ctx.position and ctx.correct_move_gtp.
    Writes ctx.instinct_results.
    """

    @property
    def name(self) -> str:
        return "instinct_classification"

    @property
    def error_policy(self) -> ErrorPolicy:
        return ErrorPolicy.DEGRADE

    async def run(self, ctx: PipelineContext) -> PipelineContext:
        position = ctx.position
        correct_move = ctx.correct_move_gtp or ""

        if not position or not correct_move:
            ctx.instinct_results = []
            logger.debug("instinct_classification: skipped (no position or correct move)")
            return ctx

        instinct_config = get_instinct_config()
        config_dict = {
            "min_confidence_to_log": instinct_config.min_confidence_to_log,
            "min_confidence_to_surface": instinct_config.min_confidence_to_surface,
            "clarity_threshold": instinct_config.clarity_threshold,
            "max_instincts_before_ambiguous": instinct_config.max_instincts_before_ambiguous,
        }

        instinct_results = classify_instinct(
            position=position,
            correct_move_gtp=correct_move,
            config=config_dict,
        )

        ctx.instinct_results = instinct_results

        # Enhanced structured logging with tiers, primary, and clarity
        primary = next((r for r in instinct_results if r.is_primary), None)
        if len(instinct_results) >= 2:
            clarity = instinct_results[0].confidence - instinct_results[1].confidence
        elif instinct_results:
            clarity = instinct_results[0].confidence
        else:
            clarity = 0.0

        logger.info(
            "instinct_classification",
            extra={
                "stage": "instinct",
                "instinct_count": len(instinct_results),
                "instincts": [
                    {
                        "type": r.instinct,
                        "confidence": round(r.confidence, 2),
                        "tier": r.tier,
                        "is_primary": r.is_primary,
                    }
                    for r in instinct_results
                ],
                "primary": primary.instinct if primary else None,
                "clarity": round(clarity, 2),
                "ambiguous": primary is None and len(instinct_results) > 0,
            },
        )

        return ctx
