"""Refutation stage — generate wrong-move refutations with escalation.

Extracts from enrich_single.py Step 6 (generate refutations + escalation loop).

Error policy: DEGRADE (zero refutations is acceptable).
"""

from __future__ import annotations

import logging

try:
    from models.refutation_result import RefutationResult

    from analyzers.generate_refutations import generate_refutations
    from analyzers.stages.protocols import (
        EnrichmentStage,
        ErrorPolicy,
        PipelineContext,
    )
except ImportError:
    from ...models.refutation_result import RefutationResult
    from ..generate_refutations import generate_refutations
    from ..stages.protocols import (
        ErrorPolicy,
        PipelineContext,
    )

logger = logging.getLogger(__name__)


class RefutationStage:
    """Generate wrong-move refutations with escalation logic."""

    @property
    def name(self) -> str:
        return "generate_refutations"

    @property
    def error_policy(self) -> ErrorPolicy:
        return ErrorPolicy.DEGRADE

    async def run(self, ctx: PipelineContext) -> PipelineContext:
        metadata = ctx.metadata
        puzzle_id = metadata.puzzle_id
        # T16: Use framed position (consistent with AnalyzeStage) when available
        position = ctx.framed_position if ctx.framed_position is not None else ctx.position

        if ctx.notify_fn is not None:
            await ctx.notify_fn("generate_refutations", {
                "puzzle_id": puzzle_id,
                "correct_move": ctx.correct_move_gtp,
                "solution_depth": len(ctx.solution_moves),
            })

        pv_mode = ctx.config.refutations.pv_mode
        if pv_mode == "pv_extract":
            logger.info(
                "PV extract mode active for puzzle %s (min_depth=%d, min_visits=%d)",
                puzzle_id,
                ctx.config.refutations.pv_extract_min_depth,
                ctx.config.refutations.pv_quality_min_visits,
            )

        refutation_engine = ctx.engine_manager.engine
        refutation_result = RefutationResult(puzzle_id=puzzle_id)
        refutation_queries = 0

        # T22: Use T2 visit tier for refutation queries when available
        refutation_visits: int | None = None
        if ctx.config and ctx.config.visit_tiers:
            refutation_visits = ctx.config.visit_tiers.T2.visits
            logger.info(
                "Using T2 visit tier (%d visits) for refutation generation",
                refutation_visits,
            )

        if refutation_engine is not None:
            try:
                refutation_result = await generate_refutations(
                    engine=refutation_engine,
                    position=position,
                    correct_move_gtp=ctx.correct_move_gtp,
                    initial_analysis=ctx.response,
                    config=ctx.config,
                    max_visits=refutation_visits,
                    puzzle_id=puzzle_id,
                    nearby_moves=ctx.nearby_moves,
                    curated_wrongs=ctx.curated_wrongs,
                    entropy_roi=ctx.entropy_roi,
                )
                refutation_queries += refutation_result.total_candidates_evaluated
            except Exception as e:
                logger.warning(
                    "Refutation generation failed for puzzle %s: %s (continuing to escalation)",
                    puzzle_id,
                    e,
                )

            # Refutation escalation
            esc_cfg = ctx.config.refutation_escalation
            if (
                esc_cfg.enabled
                and len(refutation_result.refutations) < esc_cfg.min_refutations_required
            ):
                logger.info(
                    "Refutation escalation triggered for puzzle %s: "
                    "got %d refutations (need %d). Escalating visits=%d, delta=%.3f",
                    puzzle_id,
                    len(refutation_result.refutations),
                    esc_cfg.min_refutations_required,
                    esc_cfg.escalation_visits,
                    esc_cfg.escalation_delta_threshold,
                )

                escalated_config = ctx.config.model_copy(
                    update={
                        "refutations": ctx.config.refutations.model_copy(
                            update={
                                "candidate_min_policy": esc_cfg.escalation_candidate_min_policy,
                                "delta_threshold": esc_cfg.escalation_delta_threshold,
                                "refutation_visits": esc_cfg.escalation_visits,
                            }
                        )
                    }
                )

                escalation_engine = refutation_engine

                for attempt in range(esc_cfg.max_escalation_attempts):
                    try:
                        escalated_result = await generate_refutations(
                            engine=escalation_engine,
                            position=position,
                            correct_move_gtp=ctx.correct_move_gtp,
                            initial_analysis=None,
                            config=escalated_config,
                            max_visits=esc_cfg.escalation_visits,
                            puzzle_id=puzzle_id,
                            nearby_moves=ctx.nearby_moves,
                            curated_wrongs=ctx.curated_wrongs,
                            entropy_roi=ctx.entropy_roi,
                        )
                        if len(escalated_result.refutations) >= esc_cfg.min_refutations_required:
                            logger.info(
                                "Refutation escalation succeeded for puzzle %s on attempt %d: "
                                "%d refutations found",
                                puzzle_id,
                                attempt + 1,
                                len(escalated_result.refutations),
                            )
                            refutation_queries += escalated_result.total_candidates_evaluated
                            refutation_result = escalated_result
                            break
                        else:
                            logger.info(
                                "Refutation escalation attempt %d for puzzle %s: "
                                "still only %d refutations",
                                attempt + 1,
                                puzzle_id,
                                len(escalated_result.refutations),
                            )
                            refutation_queries += escalated_result.total_candidates_evaluated
                            if len(escalated_result.refutations) > len(refutation_result.refutations):
                                refutation_result = escalated_result
                    except Exception as e:
                        logger.warning(
                            "Refutation escalation attempt %d failed for puzzle %s: %s",
                            attempt + 1,
                            puzzle_id,
                            e,
                        )
                        break

                if len(refutation_result.refutations) < esc_cfg.min_refutations_required:
                    logger.warning(
                        "Refutation escalation exhausted for puzzle %s: "
                        "only %d refutations found (need %d). "
                        "This may indicate a trivial puzzle with no plausible wrong moves.",
                        puzzle_id,
                        len(refutation_result.refutations),
                        esc_cfg.min_refutations_required,
                    )
        else:
            logger.error(
                "No engine available for refutation generation (puzzle %s).",
                puzzle_id,
            )

        ctx.refutation_result = refutation_result
        ctx.queries_by_stage["refutations"] = refutation_queries

        logger.info(
            "generate_refutations",
            extra={
                "stage": "generate_refutations",
                "refutation_count": len(refutation_result.refutations),
                "pv_mode": pv_mode,
                "escalation_used": (
                    len(refutation_result.refutations) < ctx.config.refutation_escalation.min_refutations_required
                    if ctx.config.refutation_escalation.enabled else False
                ),
            },
        )

        return ctx
