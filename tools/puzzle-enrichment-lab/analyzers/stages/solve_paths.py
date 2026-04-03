"""Solve paths — code-path dispatch for solution tree handling.

Extracted from enrich_single.py lines 276–720. Contains the three
solve paths: position-only, has-solution, and standard.

These are standalone functions (not a stage class) because the
orchestrator dispatches to exactly one based on SGF content.

Error policy: DEGRADE (fallback to partial enrichment on failure).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

try:
    from core.tsumego_analysis import (
        extract_correct_first_move,
        extract_solution_tree_moves,
    )
    from models.analysis_response import gtp_to_sgf, sgf_to_gtp

    from analyzers.config_lookup import (
        extract_level_slug as _extract_level_slug,
    )
    from analyzers.estimate_difficulty import estimate_difficulty_policy_only
    from analyzers.result_builders import (
        build_partial_result,
        make_error_result,
    )
except ImportError:
    from ...core.tsumego_analysis import (
        extract_correct_first_move,
        extract_solution_tree_moves,
    )
    from ...models.analysis_response import gtp_to_sgf, sgf_to_gtp
    from ..config_lookup import (
        extract_level_slug as _extract_level_slug,
    )
    from ..estimate_difficulty import estimate_difficulty_policy_only
    from ..result_builders import (
        build_partial_result,
        make_error_result,
    )

if TYPE_CHECKING:
    from models.ai_analysis_result import AiAnalysisResult
    from models.enrichment_state import EnrichmentRunState

logger = logging.getLogger(__name__)


async def run_position_only_path(
    state: EnrichmentRunState,
    root,
    position,
    engine_manager,
    config,
    metadata,
    *,
    ai_solve_config=None,
    source_file: str | None = None,
    trace_id: str | None = None,
    run_id: str | None = None,
) -> tuple[EnrichmentRunState, AiAnalysisResult | None]:
    """Position-only code path: build a solution tree from scratch via AI-Solve.

    When the SGF has no existing solution (correct_move_sgf is None), this
    function uses the engine to discover correct/wrong moves and build a
    multi-root solution tree (Priority A/B/C allocation).

    Returns ``(state, None)`` on success (continue to downstream steps) or
    ``(state, AiAnalysisResult)`` for early-return error/partial results.
    """
    # Support both dict and SgfMetadata
    puzzle_id = metadata["puzzle_id"] if isinstance(metadata, dict) else metadata.puzzle_id
    tags = metadata["tags"] if isinstance(metadata, dict) else metadata.tags
    corner = metadata["corner"] if isinstance(metadata, dict) else metadata.corner
    move_order = metadata["move_order"] if isinstance(metadata, dict) else metadata.move_order
    ko_type = metadata["ko_type"] if isinstance(metadata, dict) else metadata.ko_type
    board_size = position.board_size

    logger.info(
        "Puzzle %s: position-only SGF, running AI-Solve",
        puzzle_id,
    )
    from models.solve_result import QueryBudget

    from analyzers.solve_position import (
        SyncEngineAdapter,
        analyze_position_candidates,
        build_solution_tree,
        inject_solution_into_sgf,
    )

    # DD-9: Use existing ai_solve_config or create default for position-only
    if ai_solve_config is None:
        from config.ai_solve import AiSolveConfig
        ai_solve_config = AiSolveConfig()

    # PI-9: Auto-detect player alternative rate based on puzzle type
    tree_cfg = ai_solve_config.solution_tree
    if tree_cfg.player_alternative_auto_detect:
        # Position-only puzzles should explore alternatives
        tree_cfg = tree_cfg.model_copy(update={"player_alternative_rate": 0.05})
        ai_solve_config = ai_solve_config.model_copy(
            update={"solution_tree": tree_cfg}
        )
        logger.info(
            "PI-9: Auto-detected position-only puzzle — player_alternative_rate=0.05"
        )

    try:
        # Build analysis request for position (C-1 fix: use build_query_from_position)
        from analyzers.query_builder import build_query_from_position

        query_result = build_query_from_position(
            position, config=config, ko_type=ko_type,
        )

        # Compute puzzle_region for Benson/interior-point pre-query gates (F-01/F-02)
        from analyzers.frame_utils import compute_regions
        _frame_regions = compute_regions(
            position,
            margin=config.analysis_defaults.puzzle_region_margin,
        )
        puzzle_region = _frame_regions.puzzle_region or None

        # Log tsumego frame application (mirrors Stage 3b in main flow)
        framed = query_result.request.position
        logger.info(
            "Tsumego frame applied: %dx%d board, "
            "total stones after frame=%d (original=%d) for puzzle %s",
            framed.board_size, framed.board_size,
            len(framed.stones), len(position.stones),
            puzzle_id,
        )
        logger.info("position_only_original_sgf: %s", position.to_sgf())
        logger.info("position_only_framed_sgf: %s", framed.to_sgf())

        pre_analysis = await engine_manager.analyze(query_result.request)
        state.pre_analysis = pre_analysis  # forward to AnalyzeStage

        # Create engine adapter BEFORE first use (C-2 fix)
        tree_engine = SyncEngineAdapter(engine_manager, position, config)

        pos_analysis = analyze_position_candidates(
            pre_analysis, position.player_to_move.value,
            puzzle_id, ai_solve_config,
            engine=tree_engine,
            initial_moves=[],
        )

        if not pos_analysis.correct_moves:
            # DD-3: AI-Solve found no correct moves — fallback to tier-2
            logger.warning(
                "Puzzle %s: AI-Solve found no correct moves — "
                "falling back to partial enrichment (tier 2)",
                puzzle_id,
            )
            # RC-P2: Use pre_analysis (raw AnalysisResponse) for pseudo-correct
            top_move = pre_analysis.top_move
            pseudo_correct_policy = top_move.policy_prior if top_move else 0.0

            difficulty_estimate = estimate_difficulty_policy_only(
                policy_prior=pseudo_correct_policy,
                move_order=move_order, puzzle_id=puzzle_id,
            )
            return state, build_partial_result(
                puzzle_id=puzzle_id, config=config,
                difficulty_estimate=difficulty_estimate,
                scan_response=pre_analysis,
                source_file=source_file, trace_id=trace_id, run_id=run_id,
                tags=tags, corner=corner, move_order=move_order,
                board_size=board_size, enrichment_tier=2,
                position=position,
            )

        # S2-G2: Multi-root tree building with A/B/C priority allocation
        # Priority A: primary correct tree
        best_correct = pos_analysis.correct_moves[0]
        budget = QueryBudget(
            total=ai_solve_config.solution_tree.max_total_tree_queries,
        )
        # Determine level slug for depth profile
        level_slug = _extract_level_slug(root) or "intermediate"

        # Detect corner position and PV length for visit boosts (S1-G12)
        corner_pos = metadata.get("corner", "") if isinstance(metadata, dict) else metadata.corner
        # M-5 fix: PV length from analysis response, not move string length
        best_pv_len = 0
        for mi in getattr(pre_analysis, "move_infos", []):
            if getattr(mi, "move", "").upper() == best_correct.move_gtp.upper():
                best_pv_len = len(getattr(mi, "pv", []))
                break

        solution_tree = build_solution_tree(
            engine=tree_engine,
            initial_moves=[],
            correct_move_gtp=best_correct.move_gtp,
            player_color=position.player_to_move.value,
            config=ai_solve_config,
            level_slug=level_slug,
            query_budget=budget,
            puzzle_id=puzzle_id,
            corner_position=corner_pos,
            pv_length=best_pv_len,
            puzzle_region=puzzle_region,
        )

        # G-01/G-02: Track position-only path and tree completeness
        state.position_only_path = True
        state.solution_tree_completeness = solution_tree.tree_completeness
        state.budget_exhausted = not budget.can_query()

        # Inject solution into SGF
        inject_solution_into_sgf(
            root, solution_tree,
            wrong_moves=pos_analysis.wrong_moves,
            player_color=position.player_to_move.value,
        )

        # Priority B: wrong-root refutation trees (S2-G2)
        # S-4 fix: inject wrong trees into SGF instead of discarding them
        max_refutation_trees = ai_solve_config.solution_tree.max_refutation_root_trees
        for i, wrong_mc in enumerate(pos_analysis.wrong_moves[:max_refutation_trees]):
            if not budget.can_query():
                break
            try:
                wrong_tree = build_solution_tree(
                    engine=tree_engine,
                    initial_moves=[],
                    correct_move_gtp=wrong_mc.move_gtp,
                    player_color=position.player_to_move.value,
                    config=ai_solve_config,
                    level_slug=level_slug,
                    query_budget=budget,
                    puzzle_id=puzzle_id,
                    puzzle_region=puzzle_region,
                )
                # Mark the wrong tree root as NOT correct, then inject
                wrong_tree.is_correct = False
                wrong_tree.comment = "Wrong"
                inject_solution_into_sgf(
                    root, wrong_tree,
                    player_color=position.player_to_move.value,
                )
                logger.info(
                    "Puzzle %s: built and injected refutation root tree %d for %s",
                    puzzle_id, i + 1, wrong_mc.move_gtp,
                )
            except Exception as e:
                logger.warning(
                    "Puzzle %s: failed to build refutation tree for %s: %s",
                    puzzle_id, wrong_mc.move_gtp, e,
                )

        # Priority C: additional correct-root trees (S2-G2)
        max_correct_trees = ai_solve_config.solution_tree.max_correct_root_trees
        for i, alt_mc in enumerate(pos_analysis.correct_moves[1:max_correct_trees]):
            if not budget.can_query():
                break
            try:
                alt_tree = build_solution_tree(
                    engine=tree_engine,
                    initial_moves=[],
                    correct_move_gtp=alt_mc.move_gtp,
                    player_color=position.player_to_move.value,
                    config=ai_solve_config,
                    level_slug=level_slug,
                    query_budget=budget,
                    puzzle_id=puzzle_id,
                    puzzle_region=puzzle_region,
                )
                inject_solution_into_sgf(
                    root, alt_tree, player_color=position.player_to_move.value,
                )
                logger.info(
                    "Puzzle %s: built additional correct root tree %d for %s",
                    puzzle_id, i + 1, alt_mc.move_gtp,
                )
            except Exception as e:
                logger.warning(
                    "Puzzle %s: failed to build additional correct tree for %s: %s",
                    puzzle_id, alt_mc.move_gtp, e,
                )

        # Roundtrip assertion (S3-G7): verify injection succeeded
        re_extracted = extract_correct_first_move(root)
        assert re_extracted is not None, (
            f"Puzzle {puzzle_id}: inject-then-extract roundtrip failed — "
            "correct first move not found after injection"
        )

        # Set flow-through variables on state for downstream steps
        state.correct_move_gtp = best_correct.move_gtp
        state.correct_move_sgf = gtp_to_sgf(best_correct.move_gtp, board_size)
        state.solution_moves = [best_correct.move_gtp]

        logger.info(
            "Puzzle %s: AI-Solve built solution tree "
            "(move=%s, queries=%d/%d)",
            puzzle_id, best_correct.move_gtp,
            budget.used, budget.total,
        )
        state.queries_used = budget.used

    except ValueError as e:
        # Pass-as-best-move or other rejection — still a hard error
        logger.error("Puzzle %s: AI-Solve rejected: %s", puzzle_id, e)
        return state, make_error_result(
            f"AI-Solve rejected: {e}",
            puzzle_id=puzzle_id,
            source_file=source_file,
            trace_id=trace_id,
            run_id=run_id,
        )
    except Exception as e:
        # DD-7: Engine unavailable or unexpected error → tier-1 fallback
        logger.warning(
            "Puzzle %s: AI-Solve failed (%s): %s — "
            "falling back to stone-pattern enrichment (tier 1)",
            puzzle_id, type(e).__name__, e,
        )
        return state, build_partial_result(
            puzzle_id=puzzle_id, config=config,
            difficulty_estimate=None, scan_response=None,
            source_file=source_file, trace_id=trace_id, run_id=run_id,
            tags=tags, corner=corner, move_order=move_order,
            board_size=board_size, enrichment_tier=1,
            position=position,
        )

    return state, None


async def run_has_solution_path(
    state: EnrichmentRunState,
    root,
    position,
    engine_manager,
    config,
    metadata,
    *,
    ai_solve_config,
    correct_move_sgf: str,
) -> EnrichmentRunState:
    """Has-solution code path: validate existing solution + discover alternatives.

    When the SGF already has a solution and AI-Solve is active, this function
    validates the human solution and injects any alternative trees.

    Exception handling sets ``state.ai_solve_failed = True`` and falls through
    (MH-5) — never returns an early-return result.
    """
    # Support both dict and SgfMetadata
    puzzle_id = metadata["puzzle_id"] if isinstance(metadata, dict) else metadata.puzzle_id
    ko_type = metadata["ko_type"] if isinstance(metadata, dict) else metadata.ko_type
    board_size = position.board_size

    logger.info(
        "has_solution_validate",
        extra={
            "stage": "solve_paths",
        },
    )
    from models.solve_result import HumanSolutionConfidence, QueryBudget

    from analyzers.solve_position import (
        SyncEngineAdapter,
        analyze_position_candidates,
        discover_alternatives,
        inject_solution_into_sgf,
    )

    try:
        state.has_solution_path = True  # G-01: Mark has-solution path

        # C-1 fix: use build_query_from_position instead of non-existent build_query
        from analyzers.query_builder import build_query_from_position

        query_result = build_query_from_position(
            position, config=config, ko_type=ko_type,
        )

        # Log tsumego frame application (mirrors Stage 3b in main flow)
        framed = query_result.request.position
        logger.info(
            "Tsumego frame applied: %dx%d board, "
            "total stones after frame=%d (original=%d) for puzzle %s",
            framed.board_size, framed.board_size,
            len(framed.stones), len(position.stones),
            puzzle_id,
        )
        logger.info("has_solution_original_sgf: %s", position.to_sgf())
        logger.info("has_solution_framed_sgf: %s", framed.to_sgf())

        pre_analysis = await engine_manager.analyze(query_result.request)
        state.pre_analysis = pre_analysis  # forward to AnalyzeStage

        # Compute puzzle_region for Benson/interior-point pre-query gates (F-01/F-02)
        from analyzers.frame_utils import compute_regions
        _frame_regions = compute_regions(
            position,
            margin=config.analysis_defaults.puzzle_region_margin,
        )
        puzzle_region = _frame_regions.puzzle_region or None

        # Discover alternatives and validate human solution (S2-G5, S2-G6)
        correct_move_gtp = sgf_to_gtp(correct_move_sgf, board_size)
        level_slug = _extract_level_slug(root) or "intermediate"
        budget = QueryBudget(
            total=ai_solve_config.solution_tree.max_total_tree_queries,
        )
        tree_engine = SyncEngineAdapter(engine_manager, position, config)

        # S1-G16: Pass engine for per-candidate confirmation queries
        pos_analysis = analyze_position_candidates(
            pre_analysis, position.player_to_move.value,
            puzzle_id, ai_solve_config,
            engine=tree_engine,
            initial_moves=[],
        )

        # S-5 fix: pass pre-computed analysis to avoid redundant engine queries
        alts, co_correct, human_confidence = discover_alternatives(
            pre_analysis,
            correct_move_gtp,
            position.player_to_move.value,
            puzzle_id,
            ai_solve_config,
            engine=tree_engine,
            initial_moves=[],
            level_slug=level_slug,
            query_budget=budget,
            pre_computed_analysis=pos_analysis,
            puzzle_region=puzzle_region,
        )

        # S2-G6: Set ai_solution_validated when AI agrees
        ai_validated = (human_confidence is None)

        # S2-G5: Set human_solution_confidence
        pos_analysis.ai_solution_validated = ai_validated
        if human_confidence is not None:
            try:
                pos_analysis.human_solution_confidence = HumanSolutionConfidence(human_confidence)
            except (ValueError, KeyError):
                pos_analysis.human_solution_confidence = HumanSolutionConfidence.WEAK
        else:
            pos_analysis.human_solution_confidence = None
        pos_analysis.co_correct_detected = co_correct

        # Inject alternatives into SGF (additive-only)
        if alts:
            for alt_mc in alts:
                # Check if we have a built tree from discover_alternatives
                alt_tree_for_mc = None
                for sm in pos_analysis.solved_moves:
                    if sm.move_gtp.upper() == alt_mc.move_gtp.upper() and sm.solution_tree:
                        alt_tree_for_mc = sm.solution_tree
                        break
                if alt_tree_for_mc:
                    inject_solution_into_sgf(
                        root, alt_tree_for_mc,
                        player_color=position.player_to_move.value,
                    )

        logger.info(
            "has_solution_complete",
            extra={
                "stage": "solve_paths",
                "alternatives": len(alts),
                "co_correct": co_correct,
                "human_confidence": human_confidence,
                "ai_validated": ai_validated,
            },
        )

        # G-03: Wire human solution confidence + AI validated to tracking vars
        state.human_solution_confidence = human_confidence
        state.ai_solution_validated = ai_validated
        state.queries_used = budget.used
        state.co_correct_detected = co_correct
        state.correct_move_gtp = correct_move_gtp
        state.correct_move_sgf = correct_move_sgf
        state.solution_moves = extract_solution_tree_moves(root)

    except (ValueError, RuntimeError, AssertionError) as e:
        # G-06: Narrowed exception types; log at ERROR; set failure flag
        logger.error(
            "Puzzle %s: has-solution AI enrichment failed (%s): %s "
            "(falling back to original solution, ac_level will be 0)",
            puzzle_id, type(e).__name__, e,
        )
        state.ai_solve_failed = True
        state.correct_move_gtp = sgf_to_gtp(correct_move_sgf, board_size)
        state.correct_move_sgf = correct_move_sgf
        state.solution_moves = extract_solution_tree_moves(root)

    return state


def run_standard_path(
    state: EnrichmentRunState,
    root,
    position,
    correct_move_sgf: str,
) -> EnrichmentRunState:
    """Standard code path: extract moves from existing solution tree.

    Simplest path — SGF already has a solution and AI-Solve is not active.
    """
    board_size = position.board_size
    state.correct_move_gtp = sgf_to_gtp(correct_move_sgf, board_size)
    state.correct_move_sgf = correct_move_sgf
    state.solution_moves = extract_solution_tree_moves(root)
    return state
