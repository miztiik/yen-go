"""Solve path stage — dispatches to the correct solve path via StageRunner.

Wraps the three solve-path functions (position-only, has-solution, standard)
in an EnrichmentStage so they get timing/notify/error handling like other stages.

Error policy: FAIL_FAST (downstream stages cannot proceed without a correct move).

Early return: If position-only produces a partial/error AiAnalysisResult,
it is stored in ``ctx.result``. The orchestrator should check ``ctx.result``
after this stage and skip downstream stages if set.
"""

from __future__ import annotations

import logging

try:
    from models.enrichment_state import EnrichmentRunState

    from analyzers.stages.protocols import (
        ErrorPolicy,
        PipelineContext,
    )
    from analyzers.stages.solve_paths import (
        run_has_solution_path,
        run_position_only_path,
        run_standard_path,
    )
except ImportError:
    from ...models.enrichment_state import EnrichmentRunState
    from ..stages.protocols import (
        ErrorPolicy,
        PipelineContext,
    )
    from ..stages.solve_paths import (
        run_has_solution_path,
        run_position_only_path,
        run_standard_path,
    )

logger = logging.getLogger(__name__)


class SolvePathStage:
    """Dispatch to the correct solve path based on SGF content and config.

    After execution, ctx.state, ctx.correct_move_sgf, ctx.correct_move_gtp,
    and ctx.solution_moves are populated.  If the position-only path returns
    an early-return result, it is stored in ctx.result so the orchestrator
    can short-circuit the remaining pipeline.
    """

    @property
    def name(self) -> str:
        return "solve_paths"

    @property
    def error_policy(self) -> ErrorPolicy:
        return ErrorPolicy.FAIL_FAST

    async def run(self, ctx: PipelineContext) -> PipelineContext:
        state = EnrichmentRunState(notify_fn=ctx.notify_fn)
        ctx.state = state
        metadata = ctx.metadata
        ai_solve_config = ctx.config.ai_solve if ctx.config else None

        if ctx.correct_move_sgf is None:
            # Position-only -> AI-Solve builds solution from scratch
            state, early_result = await run_position_only_path(
                state, ctx.root, ctx.position, ctx.engine_manager, ctx.config,
                metadata.to_dict(),
                ai_solve_config=ai_solve_config,
                source_file=ctx.source_file,
                trace_id=ctx.trace_id,
                run_id=ctx.run_id,
            )
            if early_result is not None:
                ctx.result = early_result
                ctx.state = state
                return ctx
            ctx.correct_move_sgf = state.correct_move_sgf
            ctx.correct_move_gtp = state.correct_move_gtp
            ctx.solution_moves = state.solution_moves
            ctx.pre_analysis = state.pre_analysis

        elif ctx.correct_move_sgf is not None and ai_solve_config is not None:
            # Has-solution -> validate + discover alternatives
            state = await run_has_solution_path(
                state, ctx.root, ctx.position, ctx.engine_manager, ctx.config,
                metadata.to_dict(),
                ai_solve_config=ai_solve_config,
                correct_move_sgf=ctx.correct_move_sgf,
            )
            ctx.correct_move_gtp = state.correct_move_gtp
            ctx.correct_move_sgf = state.correct_move_sgf
            ctx.solution_moves = state.solution_moves
            ctx.pre_analysis = state.pre_analysis

        else:
            # Standard -> extract from existing solution tree
            state = run_standard_path(
                state, ctx.root, ctx.position, ctx.correct_move_sgf,
            )
            ctx.correct_move_gtp = state.correct_move_gtp
            ctx.correct_move_sgf = state.correct_move_sgf
            ctx.solution_moves = state.solution_moves

        ctx.state = state
        ctx.queries_by_stage["solve_paths"] = state.queries_used
        return ctx
