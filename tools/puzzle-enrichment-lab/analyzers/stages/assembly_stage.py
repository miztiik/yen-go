"""Assembly stage — assemble AiAnalysisResult from pipeline state.

Extracts from enrich_single.py Step 8 (AC level decision matrix,
goal inference, field wiring).

Error policy: FAIL_FAST (assembly failure = no result).
"""

from __future__ import annotations

import logging

try:
    from models.ai_analysis_result import AiAnalysisResult

    from analyzers.config_lookup import (
        load_level_id_map,
    )
    from analyzers.config_lookup import (
        resolve_level_info as _resolve_level_info,
    )
    from analyzers.config_lookup import (
        resolve_tag_names as _resolve_tag_names,
    )
    from analyzers.result_builders import (
        build_difficulty_snapshot,
        build_refutation_entries,
    )
    from analyzers.stages.protocols import (
        EnrichmentStage,
        ErrorPolicy,
        PipelineContext,
    )
except ImportError:
    from ...models.ai_analysis_result import AiAnalysisResult
    from ..config_lookup import (
        load_level_id_map,
    )
    from ..config_lookup import (
        resolve_level_info as _resolve_level_info,
    )
    from ..config_lookup import (
        resolve_tag_names as _resolve_tag_names,
    )
    from ..result_builders import (
        build_difficulty_snapshot,
        build_refutation_entries,
    )
    from ..stages.protocols import (
        ErrorPolicy,
        PipelineContext,
    )

logger = logging.getLogger(__name__)


class AssemblyStage:
    """Assemble AiAnalysisResult with AC level, goal inference, and field wiring."""

    @property
    def name(self) -> str:
        return "assemble_result"

    @property
    def error_policy(self) -> ErrorPolicy:
        return ErrorPolicy.FAIL_FAST

    async def run(self, ctx: PipelineContext) -> PipelineContext:
        metadata = ctx.metadata
        puzzle_id = metadata.puzzle_id
        state = ctx.state

        if ctx.notify_fn is not None:
            await ctx.notify_fn("assemble_result", {"puzzle_id": puzzle_id})

        result = AiAnalysisResult.from_validation(
            puzzle_id=puzzle_id,
            correct_move_result=ctx.validation_result,
            model_name=ctx.engine_model,
            visits=ctx.engine_visits,
            config_hash=ctx.config_hash,
            tags=metadata.tags,
            tag_names=_resolve_tag_names(metadata.tags),
            corner=metadata.corner,
            move_order=metadata.move_order,
            source_file=ctx.source_file,
            trace_id=ctx.trace_id,
            run_id=ctx.run_id,
        )

        # Populate refutations
        result.refutations = build_refutation_entries(ctx.refutation_result)

        # Populate difficulty
        result.difficulty = build_difficulty_snapshot(ctx.difficulty_estimate)

        # T6: Wire policy_entropy + correct_move_rank from stage context
        if ctx.policy_entropy > 0:
            result.difficulty.policy_entropy = ctx.policy_entropy
        if ctx.correct_move_rank > 0:
            result.difficulty.correct_move_rank = ctx.correct_move_rank

        # T61: Compute per-move accuracy from refutation data
        if ctx.refutation_result and ctx.refutation_result.refutations:
            try:
                from analyzers.estimate_difficulty import compute_per_move_accuracy
                result.per_move_accuracy = compute_per_move_accuracy(ctx.refutation_result)
            except Exception:
                try:
                    from ..estimate_difficulty import compute_per_move_accuracy
                    result.per_move_accuracy = compute_per_move_accuracy(ctx.refutation_result)
                except Exception:
                    pass

        # S3-G4: Determine and set AC level (G-01/G-02 decision matrix)
        ai_solve_config = ctx.config.ai_solve
        if ai_solve_config is None:
            result.ac_level = 0
        elif state.ai_solve_failed:
            result.ac_level = 0
        elif state.has_solution_path:
            result.ac_level = 1
        elif state.position_only_path:
            if (
                state.solution_tree_completeness is not None
                and state.solution_tree_completeness.is_complete()
                and not state.budget_exhausted
            ):
                result.ac_level = 2
            else:
                result.ac_level = 1
        else:
            result.ac_level = 1

        # G-03: Wire human solution confidence + AI validated flag
        if state.has_solution_path and not state.ai_solve_failed:
            result.human_solution_confidence = state.human_solution_confidence
            result.ai_solution_validated = state.ai_solution_validated

        # Wire observability fields
        result.collection = metadata.collection
        result.queries_used = state.queries_used
        result.original_level = ctx.root.get("YG", "") if ctx.root else ""
        result.co_correct_detected = state.co_correct_detected
        if ai_solve_config is not None and not state.ai_solve_failed:
            if state.solution_tree_completeness is not None:
                result.tree_truncated = not state.solution_tree_completeness.is_complete()
            elif state.budget_exhausted:
                result.tree_truncated = True

        # S3-G11: Goal inference
        if ai_solve_config is not None:
            try:
                from analyzers.solve_position import infer_goal
                pre_score = ctx.response.root_score if hasattr(ctx.response, 'root_score') and ctx.response.root_score else 0.0
                correct_move_score = 0.0
                for mi in ctx.response.move_infos:
                    if mi.move.upper() == ctx.correct_move_gtp.upper():
                        correct_move_score = mi.score_lead
                        break
                else:
                    top_move = ctx.response.top_move
                    correct_move_score = top_move.score_lead if top_move else 0.0
                ownership_data = None
                for mi in ctx.response.move_infos:
                    if mi.move.upper() == ctx.correct_move_gtp.upper():
                        ownership_data = getattr(mi, "ownership", None)
                        break
                goal, goal_conf, goal_reason = infer_goal(
                    pre_score_lead=pre_score,
                    post_score_lead=correct_move_score,
                    ownership=ownership_data,
                    config=ai_solve_config,
                    ko_type=metadata.ko_type,
                )
                result.goal = goal
                result.goal_confidence = goal_conf
                result.goal_confidence_reason = goal_reason
                logger.info(
                    "Puzzle %s: goal=%s confidence=%s "
                    "(pre_score=%.1f, post_score=%.1f, ko_type=%s)",
                    puzzle_id, goal, goal_conf,
                    pre_score, correct_move_score, metadata.ko_type,
                )
            except Exception as e:
                logger.warning(
                    "Puzzle %s: goal inference failed: %s", puzzle_id, e,
                )

        # Wire AI top move winrate
        top_move = ctx.response.top_move
        if top_move:
            result.ai_top_move_winrate = top_move.winrate

        # Populate human-readable level info
        level_name, level_range = _resolve_level_info(result.difficulty.suggested_level_id)
        result.suggested_level_name = level_name
        result.suggested_level_range = level_range

        # P3.8: Level mismatch log
        existing_yg = ctx.root.get("YG", "")
        if existing_yg and result.difficulty.suggested_level:
            katago_level = result.difficulty.suggested_level
            if existing_yg != katago_level:
                existing_id = result.difficulty.suggested_level_id
                orig_id = 0
                level_map = load_level_id_map()
                for lid, (lname, _) in level_map.items():
                    if lname.lower().replace(" ", "-").replace("–", "-") == existing_yg:
                        orig_id = lid
                        break
                distance = abs(existing_id - orig_id) // 10 if orig_id else 0
                if distance > 0:
                    logger.warning(
                        "Level mismatch: puzzle_id=%s, original_level=%s, "
                        "katago_level=%s, distance=%d steps",
                        puzzle_id, existing_yg, katago_level, distance,
                    )

        # T52: Set enrichment quality level based on completed stages
        # Level 3 = full (default), Level 2 = partial, Level 1 = stone-pattern only
        if state.ai_solve_failed or not ctx.validation_result:
            result.enrichment_quality_level = 1
        elif not ctx.refutation_result or not ctx.difficulty_estimate:
            result.enrichment_quality_level = 2
        else:
            result.enrichment_quality_level = 3

        logger.info(
            "assemble_result",
            extra={
                "stage": "assemble_result",
                "ac_level": result.ac_level,
                "enrichment_quality_level": result.enrichment_quality_level,
                "status": result.validation.status.value if hasattr(result.validation.status, 'value') else str(result.validation.status),
                "refutations": len(result.refutations),
                "level": result.difficulty.suggested_level if result.difficulty else 'n/a',
            },
        )

        # R-1: Build structured teaching signal payload (must run AFTER refutations are wired)
        try:
            from analyzers.teaching_signal_payload import build_teaching_signal_payload
        except ImportError:
            from ..teaching_signal_payload import build_teaching_signal_payload

        ctx.teaching_signals = build_teaching_signal_payload(
            response=ctx.response,
            correct_move_gtp=ctx.correct_move_gtp or "",
            policy_entropy=ctx.policy_entropy,
            correct_move_rank=ctx.correct_move_rank,
            result=result,
            board_size=ctx.position.board_size if ctx.position else 19,
            config=ctx.config.teaching_signal if ctx.config else None,
        )

        # R-1: Persist teaching signals on the output result
        result.teaching_signals = ctx.teaching_signals

        ctx.result = result
        return ctx
