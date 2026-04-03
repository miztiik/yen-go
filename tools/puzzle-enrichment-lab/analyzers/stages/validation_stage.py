"""Validation stage — validate correct move and extract wrong branches.

Extracts from enrich_single.py Steps 5-5.5 (validate correct move,
tree validation, curated wrongs, nearby moves).

Error policy: DEGRADE (validation failure shouldn't block enrichment).
"""

from __future__ import annotations

import logging

try:
    from core.tsumego_analysis import extract_wrong_move_branches
    from models.analysis_response import sgf_to_gtp
    from models.validation import ValidationStatus

    from analyzers.config_lookup import resolve_tag_names as _resolve_tag_names
    from analyzers.stages.protocols import (
        EnrichmentStage,
        ErrorPolicy,
        PipelineContext,
    )
    from analyzers.validate_correct_move import (
        get_required_validation_depth,
        validate_correct_move,
        validate_solution_tree_depth,
    )
except ImportError:
    from ...core.tsumego_analysis import extract_wrong_move_branches
    from ...models.analysis_response import sgf_to_gtp
    from ...models.validation import ValidationStatus
    from ..config_lookup import resolve_tag_names as _resolve_tag_names
    from ..stages.protocols import (
        ErrorPolicy,
        PipelineContext,
    )
    from ..validate_correct_move import (
        get_required_validation_depth,
        validate_correct_move,
        validate_solution_tree_depth,
    )

logger = logging.getLogger(__name__)


class ValidationStage:
    """Validate correct move and extract curated wrongs + nearby moves."""

    @property
    def name(self) -> str:
        return "validate_move"

    @property
    def error_policy(self) -> ErrorPolicy:
        return ErrorPolicy.DEGRADE

    async def run(self, ctx: PipelineContext) -> PipelineContext:
        metadata = ctx.metadata
        puzzle_id = metadata.puzzle_id
        position = ctx.position
        board_size = position.board_size

        if ctx.notify_fn is not None:
            await ctx.notify_fn("validate_move", {"puzzle_id": puzzle_id})

        # Collect all correct moves for miai handling
        all_correct_gtp: list[str] | None = None
        if metadata.move_order == "miai" and ctx.root.children:
            all_correct_gtp = []
            for child in ctx.root.children:
                move = child.move
                if move:
                    gtp = sgf_to_gtp(move[1], board_size)
                    all_correct_gtp.append(gtp)
                if len(all_correct_gtp) <= 1:
                    all_correct_gtp = None

        correct_move_result = validate_correct_move(
            response=ctx.response,
            correct_move_gtp=ctx.correct_move_gtp,
            tags=metadata.tags,
            corner=metadata.corner,
            move_order=metadata.move_order,
            all_correct_moves_gtp=all_correct_gtp,
            config=ctx.config,
            ko_type=metadata.ko_type,
            position=position,
        )

        # Step 5a: Deep solution tree validation
        validation_engine = ctx.engine_manager.engine
        _skip_tree_validation = False
        solution_moves = ctx.solution_moves

        if validation_engine is not None and solution_moves and ctx.config.tree_validation:
            tv_cfg = ctx.config.tree_validation
            if tv_cfg.enabled and tv_cfg.skip_when_confident:
                tag_names = set(_resolve_tag_names(metadata.tags))
                _wr_threshold = tv_cfg.confidence_winrate
                if "ko" in tag_names or metadata.ko_type in {"direct", "approach"}:
                    _wr_threshold = tv_cfg.confidence_winrate_ko
                elif "seki" in tag_names:
                    _wr_threshold = tv_cfg.confidence_winrate_seki

                sorted_moves = sorted(
                    ctx.response.move_infos, key=lambda m: m.visits, reverse=True,
                )
                confident_top_n = max(1, tv_cfg.confidence_top_n)
                in_confident_top_n = any(
                    m.move.upper() == ctx.correct_move_gtp.upper()
                    for m in sorted_moves[:confident_top_n]
                )

                if (
                    in_confident_top_n
                    and correct_move_result.correct_move_winrate >= _wr_threshold
                ):
                    _skip_tree_validation = True
                    correct_move_result.tree_validation_status = "skipped_confident"
                    logger.info(
                        "Tree validation skipped for puzzle %s: "
                        "winrate=%.3f >= threshold=%.3f, top-%d match",
                        puzzle_id,
                        correct_move_result.correct_move_winrate,
                        _wr_threshold,
                        confident_top_n,
                    )

        if validation_engine is not None and solution_moves and not _skip_tree_validation:
            required_depth = get_required_validation_depth(
                tags=metadata.tags,
                estimated_level_id=0,
                config=ctx.config,
            )
            if ctx.engine_manager.mode == "quick_only":
                required_depth = min(required_depth, ctx.config.tree_validation.quick_only_depth_cap)
            actual_check_depth = min(required_depth, len(solution_moves))

            if actual_check_depth > 0:
                try:
                    tree_depth, tree_status, unframed_wr = await validate_solution_tree_depth(
                        engine=validation_engine,
                        position=position,
                        solution_moves=solution_moves,
                        board_size=board_size,
                        required_depth=actual_check_depth,
                        player_color=position.player_to_move.value,
                        config=ctx.config,
                    )
                    correct_move_result.tree_validation_depth = tree_depth
                    correct_move_result.tree_validation_status = tree_status
                    correct_move_result.unframed_root_winrate = unframed_wr
                    if tree_status == "fail":
                        correct_move_result.flags.append(
                            f"tree_validation_fail:depth_0/{actual_check_depth}"
                        )
                    elif tree_status == "partial":
                        correct_move_result.flags.append(
                            f"tree_validation_partial:depth_{tree_depth}/{actual_check_depth}"
                        )
                    logger.info(
                        "Tree validation for puzzle %s: %s (depth %d/%d)",
                        puzzle_id, tree_status, tree_depth, actual_check_depth,
                    )

                    # --- P2a: Frame imbalance structured diagnostic ---
                    framed_wr = correct_move_result.correct_move_winrate
                    if unframed_wr is not None:
                        frame_wr_delta = abs(unframed_wr - framed_wr)
                        if frame_wr_delta > 0.5:
                            correct_move_result.flags.append("frame_imbalance")
                        logger.info(
                            "frame_imbalance_diagnostic",
                            extra={
                                "stage": "validate_move.frame_imbalance",
                                "puzzle_id": puzzle_id,
                                "framed_winrate": round(framed_wr, 4),
                                "unframed_winrate": round(unframed_wr, 4),
                                "frame_wr_delta": round(frame_wr_delta, 4),
                                "frame_imbalance": frame_wr_delta > 0.5,
                                "tree_validation_status": tree_status,
                                "tree_validation_depth": tree_depth,
                                "katago_agrees": correct_move_result.katago_agrees,
                                "original_status": correct_move_result.status.value,
                                "correct_move_gtp": correct_move_result.correct_move_gtp,
                                "correct_move_policy": round(correct_move_result.correct_move_policy, 4),
                                "board_size": board_size,
                                "tags": metadata.tags,
                                "corner": metadata.corner,
                                "ko_type": metadata.ko_type,
                                "collection": getattr(metadata, "collection", ""),
                            },
                        )

                    # --- P1: Tree-validation override ---
                    # When framed winrate triggers low_winrate REJECTED but
                    # tree validation on the unframed position fully passes
                    # AND KataGo agrees (correct move is top), the rejection
                    # is likely caused by frame territory imbalance.
                    # Upgrade REJECTED -> FLAGGED so the puzzle isn't dropped.
                    if (
                        correct_move_result.status == ValidationStatus.REJECTED
                        and "reason:low_winrate" in correct_move_result.flags
                        and tree_status == "pass"
                        and correct_move_result.katago_agrees
                    ):
                        correct_move_result.status = ValidationStatus.FLAGGED
                        correct_move_result.flags.append("tree_validation_override")
                        logger.info(
                            "Tree-validation override for puzzle %s: "
                            "REJECTED -> FLAGGED (tree_status=pass, katago_agrees=True, "
                            "framed_wr=%.3f, unframed_wr=%.3f, delta=%.3f)",
                            puzzle_id,
                            framed_wr,
                            unframed_wr if unframed_wr is not None else -1.0,
                            frame_wr_delta if unframed_wr is not None else -1.0,
                        )

                except Exception as e:
                    logger.warning(
                        "Tree validation failed for puzzle %s: %s (continuing)",
                        puzzle_id, e,
                    )
                    correct_move_result.tree_validation_status = "not_validated"

        # Step 5.5: Extract curated wrong branches + nearby moves
        curated_wrongs = extract_wrong_move_branches(ctx.root)
        # Count correct first-move children (total children with moves minus wrong branches)
        children_with_moves = sum(1 for c in ctx.root.children if c.move is not None)
        curated_corrects = children_with_moves - len(curated_wrongs) if curated_wrongs else children_with_moves
        if curated_wrongs:
            logger.info(
                "Found %d curated wrong branches in SGF for puzzle %s: %s",
                len(curated_wrongs),
                puzzle_id,
                [cw["move"] for cw in curated_wrongs],
            )

        # Compute nearby moves for spatial locality filter
        locality_distance = ctx.config.refutations.locality_max_distance
        nearby_moves: list[str] | None = None
        if locality_distance > 0:
            nearby_moves = position.get_nearby_moves(max_distance=locality_distance)
            logger.debug(
                "Locality filter: %d nearby moves within Chebyshev distance %d for puzzle %s",
                len(nearby_moves) if nearby_moves else 0,
                locality_distance,
                puzzle_id,
            )

        ctx.validation_result = correct_move_result
        ctx.curated_wrongs = curated_wrongs
        ctx.nearby_moves = nearby_moves

        logger.info(
            "validate_move",
            extra={
                "stage": "validate_move",
                "katago_agrees": correct_move_result.katago_agrees,
                "status": str(correct_move_result.status),
                "tree_validation": getattr(correct_move_result, 'tree_validation_status', 'n/a'),
                "curated_wrongs": len(curated_wrongs) if curated_wrongs else 0,
                "curated_corrects": curated_corrects,
                "flags": correct_move_result.flags,
            },
        )

        return ctx
