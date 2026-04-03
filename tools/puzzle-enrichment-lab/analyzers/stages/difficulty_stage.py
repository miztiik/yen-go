"""Difficulty stage — estimate puzzle difficulty.

Extracts from enrich_single.py Step 7 (structural formula + policy-only fallback).

Error policy: DEGRADE (fallback to policy-only).
"""

from __future__ import annotations

import logging

try:
    from core.tsumego_analysis import count_solution_branches
    from models.validation import ConfidenceLevel

    from analyzers.estimate_difficulty import (
        compute_policy_entropy,
        estimate_difficulty,
        estimate_difficulty_policy_only,
        find_correct_move_rank,
    )
    from analyzers.stages.protocols import (
        EnrichmentStage,
        ErrorPolicy,
        PipelineContext,
    )
except ImportError:
    from ...core.tsumego_analysis import count_solution_branches
    from ...models.validation import ConfidenceLevel
    from ..estimate_difficulty import (
        compute_policy_entropy,
        estimate_difficulty,
        estimate_difficulty_policy_only,
        find_correct_move_rank,
    )
    from ..stages.protocols import (
        ErrorPolicy,
        PipelineContext,
    )

logger = logging.getLogger(__name__)


class DifficultyStage:
    """Estimate difficulty (structural + policy-only fallback)."""

    @property
    def name(self) -> str:
        return "estimate_difficulty"

    @property
    def error_policy(self) -> ErrorPolicy:
        return ErrorPolicy.DEGRADE

    async def run(self, ctx: PipelineContext) -> PipelineContext:
        metadata = ctx.metadata
        puzzle_id = metadata.puzzle_id

        if ctx.notify_fn is not None:
            await ctx.notify_fn("estimate_difficulty", {"puzzle_id": puzzle_id})

        correct_move_result = ctx.validation_result
        correct_move_result.puzzle_id = puzzle_id
        correct_move_result.visits_used = ctx.engine_visits
        correct_move_result.confidence = ConfidenceLevel.HIGH if correct_move_result.katago_agrees else ConfidenceLevel.LOW

        # Compute structural signals
        branch_count = count_solution_branches(ctx.root)
        local_candidate_count = len(ctx.nearby_moves) if ctx.nearby_moves else 0

        # KM-04: Extract max_resolved_depth from tree completeness metrics
        max_resolved_depth = 0
        if ctx.state.solution_tree_completeness is not None:
            max_resolved_depth = ctx.state.solution_tree_completeness.max_resolved_depth

        try:
            difficulty_estimate = estimate_difficulty(
                validation=correct_move_result,
                refutation_result=ctx.refutation_result,
                solution_moves=ctx.solution_moves,
                puzzle_id=puzzle_id,
                branch_count=branch_count,
                local_candidate_count=local_candidate_count,
                max_resolved_depth=max_resolved_depth,
                tags=metadata.tags,
                visits_used=ctx.engine_visits,
            )
        except Exception as e:
            logger.warning(
                "Difficulty estimation failed for puzzle %s: %s (using policy-only fallback)",
                puzzle_id,
                e,
            )
            # Collect miai correct move priors if applicable
            all_correct_gtp = None
            if metadata.move_order == "miai" and ctx.root.children:
                from models.analysis_response import sgf_to_gtp
                all_correct_gtp = []
                board_size = ctx.position.board_size
                for child in ctx.root.children:
                    move = child.move
                    if move:
                        all_correct_gtp.append(sgf_to_gtp(move[1], board_size))

            difficulty_estimate = estimate_difficulty_policy_only(
                policy_prior=correct_move_result.correct_move_policy,
                move_order=metadata.move_order,
                correct_move_priors=(
                    [correct_move_result.correct_move_policy]
                    if metadata.move_order == "miai" and all_correct_gtp
                    else None
                ),
                puzzle_id=puzzle_id,
            )

        ctx.difficulty_estimate = difficulty_estimate

        # G-1: Compute policy entropy as difficulty signal
        policy_entropy = 0.0
        if ctx.response and ctx.response.move_infos:
            policy_entropy = compute_policy_entropy(ctx.response.move_infos)
        ctx.policy_entropy = policy_entropy

        # G-6: Find correct move rank for observability
        correct_move_rank = 0
        correct_move = ctx.correct_move_gtp or ""
        if ctx.response and ctx.response.move_infos and correct_move:
            correct_move_rank = find_correct_move_rank(
                ctx.response.move_infos, correct_move,
            )
        ctx.correct_move_rank = correct_move_rank

        logger.info(
            "estimate_difficulty",
            extra={
                "stage": "estimate_difficulty",
                "estimated_level": difficulty_estimate.estimated_level,
                "raw_score": round(difficulty_estimate.raw_difficulty_score, 3),
                "confidence": difficulty_estimate.confidence,
                "policy_entropy": round(policy_entropy, 4),
                "correct_move_rank": correct_move_rank,
            },
        )

        # R-1: Teaching signal payload is built in AssemblyStage (after ctx.result is populated).
        # Signal functions (log_policy_score, score_lead_rank, position_closeness) remain here
        # because they only need AnalysisResponse, not AiAnalysisResult.

        return ctx
