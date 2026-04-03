"""Single-puzzle enrichment orchestrator (thin).

Delegates to stage modules under analyzers/stages/ via StageRunner.
This file contains only:
1. Config init + trace_id generation
2. PipelineContext construction
3. Solve-path dispatch (position-only vs has-solution vs standard)
4. StageRunner.run_pipeline() call with stage list
5. Timing finalization + return result
"""

from __future__ import annotations

import logging
import time
from datetime import UTC
from typing import TYPE_CHECKING

try:
    from log_config import clear_trace_context, get_run_id, set_trace_context
except ImportError:
    from ..log_config import clear_trace_context, get_run_id, set_trace_context

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

try:
    from config import EnrichmentConfig, load_enrichment_config
    from models.ai_analysis_result import AiAnalysisResult, generate_trace_id
    from models.diagnostic import PuzzleDiagnostic
    from models.enrichment_state import EnrichmentRunState

    from analyzers.result_builders import compute_config_hash, make_error_result
    from analyzers.single_engine import SingleEngineManager
    from analyzers.stages.analyze_stage import AnalyzeStage
    from analyzers.stages.assembly_stage import AssemblyStage
    from analyzers.stages.difficulty_stage import DifficultyStage
    from analyzers.stages.instinct_stage import InstinctStage
    from analyzers.stages.parse_stage import ParseStage
    from analyzers.stages.protocols import PipelineContext
    from analyzers.stages.query_stage import QueryStage  # backward-compat alias
    from analyzers.stages.refutation_stage import RefutationStage
    from analyzers.stages.sgf_writeback_stage import SgfWritebackStage
    from analyzers.stages.solve_path_stage import SolvePathStage
    from analyzers.stages.solve_paths import (
        run_has_solution_path,
        run_position_only_path,
        run_standard_path,
    )
    from analyzers.stages.stage_runner import StageRunner
    from analyzers.stages.teaching_stage import TeachingStage
    from analyzers.stages.technique_stage import TechniqueStage
    from analyzers.stages.validation_stage import ValidationStage
except ImportError:
    from ..analyzers.result_builders import compute_config_hash, make_error_result
    from ..analyzers.single_engine import SingleEngineManager
    from ..analyzers.stages.analyze_stage import AnalyzeStage
    from ..analyzers.stages.assembly_stage import AssemblyStage
    from ..analyzers.stages.difficulty_stage import DifficultyStage
    from ..analyzers.stages.instinct_stage import InstinctStage
    from ..analyzers.stages.parse_stage import ParseStage
    from ..analyzers.stages.protocols import PipelineContext
    from ..analyzers.stages.refutation_stage import RefutationStage
    from ..analyzers.stages.sgf_writeback_stage import SgfWritebackStage
    from ..analyzers.stages.solve_path_stage import SolvePathStage
    from ..analyzers.stages.solve_paths import (
        run_has_solution_path,
        run_position_only_path,
        run_standard_path,
    )
    from ..analyzers.stages.stage_runner import StageRunner
    from ..analyzers.stages.teaching_stage import TeachingStage
    from ..analyzers.stages.technique_stage import TechniqueStage
    from ..analyzers.stages.validation_stage import ValidationStage
    from ..config import EnrichmentConfig, load_enrichment_config
    from ..models.ai_analysis_result import AiAnalysisResult, generate_trace_id
    from ..models.diagnostic import PuzzleDiagnostic

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Backward-compatible re-exports (tests import these private names)
# ---------------------------------------------------------------------------
_run_position_only_path = run_position_only_path
_run_has_solution_path = run_has_solution_path
_run_standard_path = run_standard_path



async def enrich_single_puzzle(
    sgf_text: str,
    engine_manager: SingleEngineManager,
    config: EnrichmentConfig | None = None,
    source_file: str = "",
    run_id: str = "",
    progress_cb: Callable[[str, dict], Awaitable[None]] | None = None,
) -> AiAnalysisResult:
    """Orchestrate full enrichment pipeline for a single puzzle.

    Steps:
        1. Parse SGF -> extract metadata (puzzle_id, tags, corner, move_order)
        2. Extract correct first move + solution tree
        3. Build analysis query (with tsumego frame)
        4. Run single-engine analysis
        5. Validate correct move (tag-aware dispatch)
        6. Generate wrong-move refutations
        7. Estimate difficulty (policy-only + MCTS composite)
        8. Assemble AiAnalysisResult
        9-10. Teaching enrichment (technique, comments, hints, SGF writeback)

    Args:
        sgf_text: Raw SGF string.
        engine_manager: Pre-started SingleEngineManager instance.
        config: Enrichment config (loads default if None).
        source_file: Source SGF filename with extension (for traceability
            when GN property is absent). If GN is empty, the filename
            (without extension) is used as puzzle_id fallback.
        run_id: Batch run ID (YYYYMMDD-8charhex). Shared by all puzzles
            in one batch invocation. Empty string if not in batch mode.

    Returns:
        Fully populated AiAnalysisResult. On error, returns a result
        with status=REJECTED and flags describing the failure.
    """
    if config is None:
        config = load_enrichment_config()

    config_hash = compute_config_hash(config)
    trace_id = generate_trace_id()

    # When called outside batch mode (run_id=""), fall back to the
    # global run_id set by setup_logging / conftest.
    effective_run_id = run_id or get_run_id()
    run_id = effective_run_id

    # P0: Set per-puzzle trace context so all downstream log lines
    # automatically include trace_id (puzzle_id set after parse).
    set_trace_context(trace_id=trace_id)

    logger.info(
        "session_start",
        extra={
            "trace_id": trace_id,
            "run_id": run_id,
            "source_file": source_file or "<unknown>",
            "config_hash": config_hash,
        },
    )

    t_total_start = time.monotonic()

    # Reset per-puzzle visit counter so total_visits in enrichment_complete
    # reflects only queries for this puzzle, not the whole session.
    if hasattr(engine_manager, "reset_visit_counter"):
        engine_manager.reset_visit_counter()

    # --- Build PipelineContext ---
    ctx = PipelineContext(
        sgf_text=sgf_text,
        config=config,
        engine_manager=engine_manager,
        source_file=source_file,
        run_id=run_id,
        trace_id=trace_id,
        config_hash=config_hash,
        notify_fn=progress_cb,
    )

    # --- Step 1-2: Parse SGF and extract metadata ---
    try:
        await StageRunner.run_stage(ParseStage(), ctx)
    except Exception as e:
        logger.error("Parse stage failed: %s", e)
        clear_trace_context()
        return make_error_result(
            f"SGF parse failure: {e}",
            source_file=source_file,
            trace_id=trace_id,
            run_id=run_id,
        )

    # After parse: puzzle_id is known, upgrade trace context.
    parsed_puzzle_id = ctx.metadata.puzzle_id if ctx.metadata else ""
    set_trace_context(trace_id=trace_id, puzzle_id=parsed_puzzle_id)

    # P4: Centralized enrichment_begin (was in parse_stage.py)
    logger.info(
        "enrichment_begin",
        extra={
            "puzzle_id": parsed_puzzle_id,
            "source_file": source_file or "<unknown>",
        },
    )

    # --- Step 2b: Solve-path dispatch (via SolvePathStage) ---
    try:
        await StageRunner.run_stage(SolvePathStage(), ctx)
    except Exception as e:
        logger.error("Solve-path stage failed: %s", e)
        puzzle_id = ctx.metadata.puzzle_id if ctx.metadata else ""
        return make_error_result(
            f"Solve-path failure: {e}",
            puzzle_id=puzzle_id,
            source_file=source_file,
            trace_id=trace_id,
            run_id=run_id,
        )

    # Early return: position-only path produced a partial/error result
    if ctx.result is not None:
        return ctx.result

    metadata = ctx.metadata

    # --- Stages 3-10: Run via StageRunner ---
    stage_results: list = []
    stages = [
        AnalyzeStage(),
        ValidationStage(),
        RefutationStage(),
        DifficultyStage(),
        AssemblyStage(),
        TechniqueStage(),
        InstinctStage(),
        TeachingStage(),
        SgfWritebackStage(),
    ]

    try:
        _ctx, stage_results = await StageRunner.run_pipeline(stages, ctx)
    except Exception as e:
        logger.error("Pipeline stage failed: %s", e)
        puzzle_id = metadata.puzzle_id if metadata else ""
        return make_error_result(
            f"Pipeline failure: {e}",
            puzzle_id=puzzle_id,
            source_file=source_file,
            trace_id=trace_id,
            run_id=run_id,
        )

    # --- Finalize timings ---
    ctx.timings["total"] = time.monotonic() - t_total_start
    result = ctx.result
    if result is not None:
        result.phase_timings = ctx.timings

    puzzle_id = metadata.puzzle_id if metadata else ""

    # P4: Centralized enrichment_complete summary (was in teaching_stage.py)
    if result is not None:
        logger.info(
            "enrichment_complete",
            extra={
                "puzzle_id": puzzle_id,
                "status": result.validation.status.value if hasattr(result.validation.status, "value") else str(result.validation.status),
                "refutations": len(result.refutations),
                "level": result.difficulty.suggested_level if result.difficulty else "n/a",
                "technique_tags": result.technique_tags,
                "hints_count": len(result.hints) if result.hints else 0,
                "hints_text": list(result.hints) if result.hints else [],
                "phase_timings": {k: round(v, 3) for k, v in ctx.timings.items()},
                "queries_used": result.queries_used if hasattr(result, "queries_used") else 0,
                "queries_by_stage": dict(ctx.queries_by_stage),
                "total_visits": engine_manager.total_visits_used if hasattr(engine_manager, "total_visits_used") else None,
                "enrichment_tier": result.enrichment_quality_level if hasattr(result, "enrichment_quality_level") else 0,
                "original_level": result.original_level if hasattr(result, "original_level") else "",
                "correct_move_sgf": ctx.correct_move_sgf if hasattr(ctx, "correct_move_sgf") else None,
                "correct_move_gtp": ctx.correct_move_gtp if hasattr(ctx, "correct_move_gtp") else None,
                "goal": result.goal if hasattr(result, "goal") else None,
                "goal_confidence": result.goal_confidence if hasattr(result, "goal_confidence") else None,
                "ac_level": result.ac_level if hasattr(result, "ac_level") else None,
            },
        )

    _final_status = (
        result.validation.status.value
        if result and hasattr(result.validation.status, "value")
        else str(result.validation.status) if result else "unknown"
    )
    logger.info(
        "enrichment_end",
        extra={
            "trace_id": trace_id,
            "puzzle_id": puzzle_id,
            "source_file": source_file or "<unknown>",
            "status": _final_status,
            "elapsed_s": f"{ctx.timings.get('total', 0.0):.3f}",
        },
    )

    # P0: Clear per-puzzle trace context between puzzles in batch mode.
    clear_trace_context()

    # --- G10: Build per-puzzle diagnostic ---
    ctx.diagnostic = _build_diagnostic(ctx, result, stage_results)

    return result


# ---------------------------------------------------------------------------
# G10: Diagnostic builder
# ---------------------------------------------------------------------------

def _build_diagnostic(
    ctx: PipelineContext,
    result: AiAnalysisResult | None,
    stage_results: list | None = None,
) -> PuzzleDiagnostic:
    """Build a PuzzleDiagnostic from pipeline context and stage results."""
    from datetime import datetime

    metadata = ctx.metadata
    puzzle_id = metadata.puzzle_id if metadata else ""

    # Stages that ran / skipped / errored
    all_stage_names = [
        "parse_sgf", "solve_path", "analyze", "validate", "refutation",
        "difficulty", "assemble_result", "technique", "instinct",
        "teaching", "sgf_writeback",
    ]
    stages_run: list[str] = []
    stages_skipped: list[str] = []
    errors: list[str] = []
    warnings: list[str] = []

    if stage_results:
        for sr in stage_results:
            stages_run.append(sr.stage_name)
            if sr.degraded:
                warnings.append(f"{sr.stage_name}: degraded ({sr.error})")
            elif not sr.success and sr.error:
                errors.append(f"{sr.stage_name}: {sr.error}")
        ran_set = {sr.stage_name for sr in stage_results}
        stages_skipped = [s for s in all_stage_names if s not in ran_set]

    # Always include parse + solve_path (run before the pipeline stages)
    for early in ("parse_sgf", "solve_path"):
        if early in ctx.timings and early not in stages_run:
            stages_run.insert(0, early)
        if early in stages_skipped:
            stages_skipped.remove(early)

    # Signals computed
    signals: dict = {}
    if result and result.difficulty:
        if result.difficulty.policy_entropy >= 0:
            signals["policy_entropy"] = result.difficulty.policy_entropy
        if result.difficulty.correct_move_rank >= 0:
            signals["correct_move_rank"] = result.difficulty.correct_move_rank
        if result.difficulty.trap_density >= 0:
            signals["trap_density"] = result.difficulty.trap_density
    if result and result.difficulty and result.difficulty.composite_score > 0:
        signals["composite_score"] = result.difficulty.composite_score

    # Goal agreement
    goal_agreement = "unknown"
    goal_stated = ""
    goal_inferred = ""
    if result:
        goal_inferred = result.goal or ""
        # No explicit "stated" goal in result; mark unknown unless tags hint
        if goal_inferred and goal_inferred != "unknown":
            goal_agreement = "inferred"

    # Validation flags as warnings
    if result and result.validation.flags:
        for flag in result.validation.flags:
            warnings.append(f"validation_flag: {flag}")

    return PuzzleDiagnostic(
        puzzle_id=puzzle_id,
        source_file=ctx.source_file,
        timestamp=datetime.now(UTC).isoformat(),
        stages_run=stages_run,
        stages_skipped=stages_skipped,
        signals_computed=signals,
        goal_stated=goal_stated,
        goal_inferred=goal_inferred,
        goal_agreement=goal_agreement,
        errors=errors,
        warnings=warnings,
        phase_timings=dict(ctx.timings) if ctx.timings else {},
        qk_score=0,
        ac_level=result.ac_level if result else 0,
        enrichment_tier=result.enrichment_tier if result else 0,
    )


def build_diagnostic_from_result(result: AiAnalysisResult) -> PuzzleDiagnostic:
    """Build a PuzzleDiagnostic from an AiAnalysisResult (for CLI use).

    When the caller doesn't have access to the PipelineContext, this
    function extracts available diagnostic data from the result alone.
    """
    from datetime import datetime

    signals: dict = {}
    if result.difficulty:
        if result.difficulty.policy_entropy >= 0:
            signals["policy_entropy"] = result.difficulty.policy_entropy
        if result.difficulty.correct_move_rank >= 0:
            signals["correct_move_rank"] = result.difficulty.correct_move_rank
        if result.difficulty.trap_density >= 0:
            signals["trap_density"] = result.difficulty.trap_density
        if result.difficulty.composite_score > 0:
            signals["composite_score"] = result.difficulty.composite_score

    stages_run = list(result.phase_timings.keys()) if result.phase_timings else []

    warnings: list[str] = []
    if result.validation.flags:
        for flag in result.validation.flags:
            warnings.append(f"validation_flag: {flag}")

    return PuzzleDiagnostic(
        puzzle_id=result.puzzle_id,
        source_file=result.source_file,
        timestamp=datetime.now(UTC).isoformat(),
        stages_run=stages_run,
        signals_computed=signals,
        goal_inferred=result.goal or "",
        goal_agreement="inferred" if result.goal and result.goal != "unknown" else "unknown",
        warnings=warnings,
        phase_timings=dict(result.phase_timings) if result.phase_timings else {},
        qk_score=0,
        ac_level=result.ac_level,
        enrichment_tier=result.enrichment_tier,
    )
