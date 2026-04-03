"""Teaching stage — generate teaching comments and hints.

Assumes technique_tags are already set by TechniqueStage upstream.
SGF writeback is handled downstream by SgfWritebackStage.

Error policy: DEGRADE (teaching enrichment is optional).
"""

from __future__ import annotations

import logging

try:
    from analyzers.hint_generator import generate_hints
    from analyzers.stages.protocols import (
        EnrichmentStage,
        ErrorPolicy,
        PipelineContext,
    )
    from analyzers.teaching_comments import generate_teaching_comments
except ImportError:
    from ..hint_generator import generate_hints
    from ..stages.protocols import (
        ErrorPolicy,
        PipelineContext,
    )
    from ..teaching_comments import generate_teaching_comments

logger = logging.getLogger(__name__)


class TeachingStage:
    """Generate teaching comments and hints from analysis data.

    Expects ``result.technique_tags`` to be populated by TechniqueStage.
    """

    @property
    def name(self) -> str:
        return "teaching_enrichment"

    @property
    def error_policy(self) -> ErrorPolicy:
        return ErrorPolicy.DEGRADE

    async def run(self, ctx: PipelineContext) -> PipelineContext:
        metadata = ctx.metadata
        puzzle_id = metadata.puzzle_id
        result = ctx.result
        board_size = ctx.position.board_size

        if ctx.notify_fn is not None:
            await ctx.notify_fn("teaching_enrichment", {
                "puzzle_id": puzzle_id,
                "validation_status": result.validation.status.value if hasattr(result.validation.status, "value") else str(result.validation.status),
                "refutation_count": len(result.refutations),
                "difficulty_level": result.difficulty.suggested_level if result.difficulty else None,
            })

        analysis_dict = result.model_dump()
        # technique_tags already set by TechniqueStage; use them directly

        # T13: Prepare new signals for teaching enrichment
        detection_results = ctx.detection_results or []
        instinct_results = ctx.instinct_results or []

        # Get level category for level-adaptive hints
        level_slug = result.difficulty.suggested_level if result.difficulty else "unknown"
        from config.helpers import get_level_category
        try:
            level_category = get_level_category(level_slug)
        except KeyError:
            level_category = "entry"

        result.teaching_comments = generate_teaching_comments(
            analysis_dict, result.technique_tags, board_size=board_size,
            detection_results=detection_results,
            instinct_results=instinct_results,
        )
        result.hints = generate_hints(
            analysis_dict, result.technique_tags, board_size=board_size,
            detection_results=detection_results,
            instinct_results=instinct_results,
            level_category=level_category,
        )

        # Detail log for teaching comments
        if result.teaching_comments:
            tc = result.teaching_comments
            logger.debug(
                "Teaching comments for %s: correct=%r, vital=%r, "
                "wrong_count=%d, hc_level=%s, summary=%r",
                puzzle_id,
                tc.get("correct_comment", ""),
                tc.get("vital_comment", ""),
                len(tc.get("wrong_comments", {})),
                tc.get("hc_level", "?"),
                tc.get("summary", ""),
            )

        logger.info(
            "teaching_enrichment",
            extra={
                "stage": "teaching_enrichment",
                "technique_tags": result.technique_tags,
                "hints_count": len(result.hints) if result.hints else 0,
                "hints_text": list(result.hints) if result.hints else [],
                "teaching_comments": len(result.teaching_comments) if result.teaching_comments else 0,
            },
        )

        return ctx
