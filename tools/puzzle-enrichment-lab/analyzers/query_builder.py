"""Query builder — converts SGF text into a KataGo AnalysisRequest.

Task A.1.1: Build query from SGF.

Orchestrates: parse SGF → extract position → infer player color →
override komi to 0 → apply tsumego frame → build AnalysisRequest.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

try:
    from config import EnrichmentConfig
    from core.tsumego_analysis import (
        extract_correct_first_move_color,
        extract_position,
        parse_sgf,
    )
    from models.analysis_request import AnalysisRequest
    from models.position import Position

    from analyzers.frame_adapter import apply_frame
except ImportError:
    from ..analyzers.frame_adapter import apply_frame
    from ..config import EnrichmentConfig
    from ..core.tsumego_analysis import (
        extract_correct_first_move_color,
        extract_position,
        parse_sgf,
    )
    from ..models.analysis_request import AnalysisRequest
    from ..models.position import Position

logger = logging.getLogger(__name__)

# Tsumego puzzles are life-and-death; komi is irrelevant (override to 0).
_TSUMEGO_KOMI = 0.0


@dataclass
class QueryResult:
    """Analysis request plus metadata."""
    request: AnalysisRequest
    original_board_size: int
    approach_ko_pv_may_truncate: bool = False
    """C3: True when ko_type='approach' and analysisPVLen >= 30.

    Approach-ko fight sequences can exceed 30 moves.  When this flag is
    set the caller should validate whether the last PV move represents a
    terminal position; if not, the ko-threat count may be under-estimated
    and the validation result should be downgraded to FLAGGED.
    """


@dataclass
class TsumegoQueryBundle:
    """Result of tsumego query preparation — all data needed for AnalysisRequest."""
    framed_position: Position
    region_moves: list[str]
    rules: str
    pv_len: int | None
    komi: float


def prepare_tsumego_query(
    position: Position,
    *,
    config: EnrichmentConfig | None = None,
    ko_type: str = "none",
    puzzle_region_margin: int = 2,
) -> TsumegoQueryBundle:
    """Single source of truth for tsumego query preparation.

    Steps (always in this order):
    1. Override komi to 0.0 (tsumego = life/death, not scoring)
    2. Compute puzzle region moves (bounding box + margin)
    3. Apply tsumego frame (fill empty areas with offense/defense stones)
    4. Resolve ko-aware rules and PV length from config

    This is a PURE function: no engine reference, no side effects, no I/O.
    All three query paths must call this function.
    """
    # 1. Override komi
    tsumego_position = Position(
        board_size=position.board_size,
        stones=position.stones,
        player_to_move=position.player_to_move,
        komi=_TSUMEGO_KOMI,
    )

    # 2. Compute puzzle region
    region_moves = tsumego_position.get_puzzle_region_moves(margin=puzzle_region_margin)

    # 3. Apply tsumego frame
    frame_result = apply_frame(
        tsumego_position,
        margin=puzzle_region_margin,
        ko=(ko_type != "none"),
    )
    framed_position = frame_result.position

    # 3b. Log overlap between region_moves and frame-occupied coords
    if region_moves:
        _COL = "ABCDEFGHJKLMNOPQRST"
        framed_occupied = {
            (s.x, s.y) for s in framed_position.stones
        }
        occupied_count = 0
        for gtp in region_moves:
            x = _COL.index(gtp[0])
            y = framed_position.board_size - int(gtp[1:])
            if (x, y) in framed_occupied:
                occupied_count += 1
        playable = len(region_moves) - occupied_count
        if occupied_count > 0:
            logger.info(
                "Query allowed_moves: %d coords total, %d playable, "
                "%d occupied by frame stones (%.1f%% overlap)",
                len(region_moves), playable,
                occupied_count, 100 * occupied_count / len(region_moves),
            )
        else:
            logger.info(
                "Query allowed_moves: %d coords (first 10: %s)",
                len(region_moves),", ".join(region_moves[:10]),
            )

    # 4. Resolve ko-aware rules and PV length
    ko_type_key = ko_type if ko_type in ("none", "direct", "approach") else "none"
    if config is not None:
        rules = config.ko_analysis.rules_by_ko_type.get(ko_type_key, "chinese")
        pv_len: int | None = config.ko_analysis.pv_len_by_ko_type.get(ko_type_key)
        if pv_len is not None and pv_len <= 15:
            pv_len = None
    else:
        rules = "chinese"
        pv_len = None

    if rules != "chinese":
        logger.info(
            "Ko-aware analysis: ko_type=%s → rules=%s, analysisPVLen=%s",
            ko_type_key, rules, pv_len,
        )

    return TsumegoQueryBundle(
        framed_position=framed_position,
        region_moves=region_moves,
        rules=rules,
        pv_len=pv_len,
        komi=_TSUMEGO_KOMI,
    )


def build_query_from_sgf(
    sgf_text: str,
    max_visits: int | None = None,
    puzzle_region_margin: int | None = None,
    ko_type: str = "none",
    config: EnrichmentConfig | None = None,
    symmetries: int | None = None,
    referee: bool = False,
) -> QueryResult:
    """Build a KataGo analysis request from raw SGF text.

    Steps:
        1. Parse SGF into node tree.
        2. Extract board position (stones, size, player).
           - If PL property absent, infer player from first correct move.
        3. Override komi to 0 (tsumego = life/death, not scoring).
        4. Compute puzzle region.
        5. Apply tsumego frame around puzzle stones.
        6. Build AnalysisRequest with ownership + policy flags.
           - For ko puzzles (S.4): use tromp-taylor rules + longer PV.

    Args:
        sgf_text: Raw SGF string.
        max_visits: MCTS visits for KataGo. If None, uses config.analysis_defaults.
        puzzle_region_margin: Margin around puzzle stones. If None, uses config.analysis_defaults.
        ko_type: Ko context from YK property ("none", "direct", "approach").
        config: Enrichment config. Loaded automatically if None.
        symmetries: Override rootNumSymmetriesToSample per-query (A8).
            If None, falls back to config.deep_enrich.root_num_symmetries_to_sample
            when config is provided, or uses the .cfg file default.

    Returns:
        QueryResult containing the AnalysisRequest.

    Raises:
        ValueError: If SGF is unparseable or has no stones.
    """
    # P5.8: Load config if not provided (Plan 010)
    if config is None:
        try:
            from config import load_enrichment_config
            config = load_enrichment_config()
        except Exception:
            logger.warning("Config load failed — using hardcoded defaults (test mode only)")

    # Resolve defaults from config.analysis_defaults (P5.8)
    if max_visits is None:
        max_visits = config.analysis_defaults.default_max_visits if config else 200
    if puzzle_region_margin is None:
        puzzle_region_margin = config.analysis_defaults.puzzle_region_margin if config else 2
    # 1. Parse
    root = parse_sgf(sgf_text)

    # 2. Extract position — with color inference if PL absent
    player_override = None
    pl_property = root.get("PL")
    if not pl_property:
        inferred_color = extract_correct_first_move_color(root)
        if inferred_color is not None:
            player_override = inferred_color
            logger.debug(
                f"No PL property; inferred player={inferred_color.value} "
                f"from first correct move"
            )

    position = extract_position(root, player_override=player_override)

    # 2b. Board size validation guard (R.0.2)
    if position.board_size < 5 or position.board_size > 19:
        raise ValueError(
            f"Unsupported board size {position.board_size}: "
            f"KataGo requires 5×5 through 19×19"
        )

    # 3. Override komi + compute region + apply frame + resolve ko rules
    original_board_size = position.board_size

    # 4. Tsumego query preparation (komi, region, frame, ko rules)
    bundle = prepare_tsumego_query(
        position,
        config=config,
        ko_type=ko_type,
        puzzle_region_margin=puzzle_region_margin,
    )

    # 5. Build request with puzzle region restriction
    # A8: Resolve rootNumSymmetriesToSample override
    effective_symmetries = symmetries
    if effective_symmetries is None and config is not None:
        if referee:
            effective_symmetries = config.deep_enrich.referee_symmetries
        else:
            effective_symmetries = config.deep_enrich.root_num_symmetries_to_sample

    override_dict: dict[str, int | float | str | bool] | None = None
    if effective_symmetries is not None:
        override_dict = {"rootNumSymmetriesToSample": effective_symmetries}

    request = AnalysisRequest(
        position=bundle.framed_position,
        max_visits=max_visits,
        allowed_moves=bundle.region_moves if bundle.region_moves else None,
        include_ownership=True,
        include_pv=True,
        include_policy=True,
        rules=bundle.rules,
        analysis_pv_len=bundle.pv_len,
        override_settings=override_dict,
        # Q8: Wire max_time from deep_enrich config (0 = no limit)
        max_time=config.deep_enrich.max_time if config is not None else 0,
    )

    logger.debug(
        f"Query built: {len(bundle.framed_position.stones)} stones "
        f"(board {position.board_size}x{position.board_size}, "
        f"player={bundle.framed_position.player_to_move.value}, komi={bundle.framed_position.komi}, "
        f"allowed_moves={len(bundle.region_moves) if bundle.region_moves else 'all'})"
    )

    # C3: Flag approach-ko queries where the PV may be truncated before
    # all ko threats are resolved.  Approach ko sequences can exceed 30
    # moves; a capped PV may miscount ko threats.  Callers should treat
    # validation results for flagged queries as FLAGGED not ACCEPTED.
    ko_type_key = ko_type if ko_type in ("none", "direct", "approach") else "none"
    approach_ko_pv_may_truncate = (
        ko_type_key == "approach" and bundle.pv_len is not None and bundle.pv_len >= 30
    )
    if approach_ko_pv_may_truncate:
        logger.warning(
            "Approach-ko PV may be truncated: ko_type=%s, analysisPVLen=%d. "
            "Validate whether the last PV move is a terminal position.",
            ko_type_key, bundle.pv_len,
        )

    return QueryResult(
        request=request,
        original_board_size=original_board_size,
        approach_ko_pv_may_truncate=approach_ko_pv_may_truncate,
    )


def build_query_from_position(
    position: Position,
    max_visits: int = 500,
    puzzle_region_margin: int = 2,
    config: EnrichmentConfig | None = None,
    ko_type: str = "none",
) -> QueryResult:
    """Build a KataGo analysis request from a Position object.

    Used by the AI-Solve path where the Position is already extracted
    from the SGF. Applies komi override, tsumego frame, and puzzle
    region restriction. Does NOT crop (tree builder operates in the
    original coordinate space to avoid coordinate translation overhead).

    Args:
        position: Board position with stones.
        max_visits: MCTS visits for KataGo.
        puzzle_region_margin: Margin around puzzle stones.
        config: Enrichment config. Loaded automatically if None.
        ko_type: Ko context ("none", "direct", "approach").

    Returns:
        QueryResult with AnalysisRequest.
    """
    if config is None:
        try:
            from config import load_enrichment_config as _load
            config = _load()
        except Exception:
            pass

    if max_visits <= 0:
        max_visits = config.analysis_defaults.default_max_visits if config else 500
    if puzzle_region_margin <= 0:
        puzzle_region_margin = config.analysis_defaults.puzzle_region_margin if config else 2

    # Tsumego query preparation (komi, region, frame, ko rules)
    bundle = prepare_tsumego_query(
        position,
        config=config,
        ko_type=ko_type,
        puzzle_region_margin=puzzle_region_margin,
    )

    request = AnalysisRequest(
        position=bundle.framed_position,
        max_visits=max_visits,
        allowed_moves=bundle.region_moves if bundle.region_moves else None,
        include_ownership=True,
        include_pv=True,
        include_policy=True,
        rules=bundle.rules,
        analysis_pv_len=bundle.pv_len,
    )

    logger.debug(
        "Query from position: %d stones (board %dx%d, player=%s, komi=%.1f, "
        "allowed_moves=%s)",
        len(bundle.framed_position.stones),
        position.board_size,
        position.board_size,
        bundle.framed_position.player_to_move.value,
        bundle.framed_position.komi,
        len(bundle.region_moves) if bundle.region_moves else "all",
    )
    if bundle.region_moves:
        logger.info(
            "Query allowed_moves: %d coords (first 10: %s)",
            len(bundle.region_moves),
            ", ".join(sorted(bundle.region_moves)[:10]),
        )

    return QueryResult(
        request=request,
        original_board_size=position.board_size,
    )
