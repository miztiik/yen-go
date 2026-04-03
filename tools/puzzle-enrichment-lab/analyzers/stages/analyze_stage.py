"""Analyze stage — build analysis query and run KataGo engine analysis.

Uses the already-parsed Position from PipelineContext (no re-parsing).
Builds query via build_query_from_position, runs engine, stores response.

Error policy: FAIL_FAST (can't continue without analysis).
"""

from __future__ import annotations

import logging

try:
    from config.helpers import get_effective_max_visits
    from models.analysis_response import AnalysisResponse

    from analyzers.query_builder import QueryResult, build_query_from_position
    from analyzers.stages.protocols import (
        EnrichmentStage,
        ErrorPolicy,
        PipelineContext,
    )
except ImportError:
    from ...config.helpers import get_effective_max_visits
    from ...models.analysis_response import AnalysisResponse
    from ..query_builder import QueryResult, build_query_from_position
    from ..stages.protocols import (
        ErrorPolicy,
        PipelineContext,
    )

logger = logging.getLogger(__name__)


class AnalyzeStage:
    """Build analysis query from Position and run single-engine analysis."""

    @property
    def name(self) -> str:
        return "analyze"

    @property
    def error_policy(self) -> ErrorPolicy:
        return ErrorPolicy.FAIL_FAST

    async def run(self, ctx: PipelineContext) -> PipelineContext:
        metadata = ctx.metadata
        puzzle_id = metadata.puzzle_id
        position = ctx.position
        board_size = position.board_size

        # Puzzle context header: logged once with all session-constant puzzle metadata.
        logger.info(
            "puzzle_context",
            extra={
                "trace_id": ctx.trace_id, "puzzle_id": puzzle_id,
                "source_file": ctx.source_file or "<unknown>",
                "board_size": board_size,
                "player": position.player_to_move.value,
                "tags": metadata.tags, "corner": metadata.corner,
                "ko": metadata.ko_type, "move_order": metadata.move_order,
                "collection": metadata.collection or "<none>",
            },
        )

        # Notify GUI with initial board state
        if ctx.notify_fn is not None:
            await ctx.notify_fn("board_state", {
                "puzzle_id": puzzle_id,
                "board_size": board_size,
                "player_to_move": position.player_to_move.value,
                "black_stones": [[s.x, s.y] for s in position.black_stones],
                "white_stones": [[s.x, s.y] for s in position.white_stones],
                "sgf": ctx.sgf_text,
            })

        logger.info(
            "board_state",
            extra={
                "stage": "analyze", "board_size": board_size,
                "player": position.player_to_move.value,
                "num_stones": len(position.stones),
                "correct_move_sgf": ctx.correct_move_sgf,
                "correct_move_gtp": ctx.correct_move_gtp,
                "solution_depth": len(ctx.solution_moves),
            },
        )

        # Step 3: Build analysis query
        if ctx.notify_fn is not None:
            await ctx.notify_fn("build_query", {
                "puzzle_id": puzzle_id,
                "board_size": board_size,
                "player_to_move": position.player_to_move.value,
                "num_stones": len(position.stones),
            })

        # T21: Use visit tier T1 for standard analysis, with escalation to T2
        # for uncertain positions. get_effective_max_visits is the fallback
        # when visit tiers are not configured.
        if ctx.config and ctx.config.visit_tiers:
            ctx.effective_visits = ctx.config.visit_tiers.T1.visits
        else:
            ctx.effective_visits = get_effective_max_visits(
                ctx.config, mode_override=ctx.engine_manager.mode,
            )

        # Build query directly from Position (no SGF re-parsing needed)
        query_result: QueryResult = build_query_from_position(
            position,
            max_visits=ctx.effective_visits,
            ko_type=metadata.ko_type,
            config=ctx.config,
        )
        request = query_result.request

        # Log tsumego frame application — store for downstream stages (T16)
        framed_position = request.position
        ctx.framed_position = framed_position
        logger.info(
            "tsumego_frame",
            extra={
                "stage": "analyze.frame",
                "frame_board_size": f"{framed_position.board_size}x{framed_position.board_size}",
                "stones_after_frame": len(framed_position.stones),
                "stones_original": len(position.stones),
            },
        )
        logger.info("framed_sgf: %s", framed_position.to_sgf())
        logger.debug(
            "[STAGE 3b] Framed position stones: %s",
            framed_position.to_katago_initial_stones(),
        )

        logger.info(
            "build_query",
            extra={
                "stage": "analyze",
                "eval_board": f"{framed_position.board_size}x{framed_position.board_size}",
                "visits": ctx.effective_visits,
            },
        )

        # Step 4: Run single-engine analysis (or reuse solve-path pre_analysis)
        if ctx.notify_fn is not None:
            await ctx.notify_fn("katago_analysis", {"puzzle_id": puzzle_id})

        if ctx.pre_analysis is not None:
            logger.info("Reusing solve-path pre_analysis (saving one engine query)")
            response = ctx.pre_analysis
            ctx.pre_analysis = None  # consumed
            ctx.queries_by_stage["analyze"] = 0
        else:
            response: AnalysisResponse = await ctx.engine_manager.analyze(request)
            ctx.queries_by_stage["analyze"] = 1

        ctx.response = response
        ctx.engine_model = ctx.engine_manager.model_label()
        ctx.engine_visits = response.total_visits

        # Compute entropy ROI from ownership data
        if response.ownership:
            from analyzers.entropy_roi import compute_entropy_roi
            threshold = (
                ctx.config.frame.entropy_quality_check.variance_threshold
                if ctx.config else 0.5
            )
            ctx.entropy_roi = compute_entropy_roi(
                response.ownership, position.board_size,
                threshold=threshold,
            )

        # P3.6: Post-analysis structured log
        _top_move_info = response.top_move
        logger.info(
            "katago_analysis",
            extra={
                "stage": "analyze", "correct_move": ctx.correct_move_gtp,
                "winrate": round(_top_move_info.winrate, 3) if _top_move_info else 0.0,
                "policy": round(_top_move_info.policy_prior, 4) if _top_move_info else 0.0,
                "visits": ctx.engine_visits,
                "top_move": _top_move_info.move if _top_move_info else "?",
                "model": ctx.engine_model,
            },
        )

        # T21: Escalate to T2 visits if analysis result is uncertain
        if (
            ctx.config
            and ctx.config.visit_tiers
            and _top_move_info is not None
        ):
            de = ctx.config.deep_enrich
            wr = _top_move_info.winrate
            if de.escalation_winrate_low <= wr <= de.escalation_winrate_high:
                t2_visits = ctx.config.visit_tiers.T2.visits
                logger.info(
                    "T21 escalation: uncertain winrate %.3f in [%.2f, %.2f], "
                    "re-running at T2=%d visits",
                    wr, de.escalation_winrate_low, de.escalation_winrate_high,
                    t2_visits,
                )
                ctx.effective_visits = t2_visits
                query_result_t2: QueryResult = build_query_from_position(
                    position,
                    max_visits=t2_visits,
                    ko_type=metadata.ko_type,
                    config=ctx.config,
                )
                response = await ctx.engine_manager.analyze(query_result_t2.request)
                ctx.response = response
                ctx.engine_visits = response.total_visits

        return ctx
