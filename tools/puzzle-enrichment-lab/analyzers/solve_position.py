"""AI-Solve position analysis, move classification, and tree building.

Phases 3-4 of ai-solve-enrichment-plan-v3.

Functions:
- normalize_winrate(): Perspective normalization helper (DD-2)
- classify_move_quality(): Delta-based classification (DD-2, DD-6)
- analyze_position_candidates(): Full position analysis with pre-filtering (DD-2)
- build_solution_tree(): Recursive tree builder with stopping conditions (DD-1, DD-3)

Design decisions:
- DD-1: Category-aware depth profiles with 6 stopping conditions
- DD-2: Correct moves ranked by winrate, wrong by policy (most tempting traps)
- DD-3: Branch at opponent nodes, budget-capped
- DD-6: Pre/post winrate are confidence annotations, NOT gates
- DD-12: Corner/ladder visit boosts, seki early-exit
- EDGE-4: Pass as best move → explicit rejection

This module does NOT import from backend/puzzle_manager/.
All thresholds from config — zero hardcoded values.
"""

from __future__ import annotations

import logging
import random
import time
from typing import TYPE_CHECKING, Protocol

try:
    from config.ai_solve import AiSolveConfig
    from config.helpers import get_level_category
    from models.solve_result import (
        AiCorrectnessLevel,
        MoveClassification,
        MoveQuality,
        PositionAnalysis,
        QueryBudget,
        SolutionNode,
        TreeCompletenessMetrics,
    )
    from models.validation import ConfidenceLevel

    from core.sgf_parser import SGFNode
except ImportError:
    from ..config import AiSolveConfig
    from ..config.helpers import get_level_category
    from ..core.sgf_parser import SGFNode
    from ..models.solve_result import (
        AiCorrectnessLevel,
        MoveClassification,
        MoveQuality,
        PositionAnalysis,
        QueryBudget,
        SolutionNode,
        TreeCompletenessMetrics,
    )
    from ..models.validation import ConfidenceLevel

if TYPE_CHECKING:
    from models.analysis_response import AnalysisResponse, MoveAnalysis

logger = logging.getLogger(__name__)


def normalize_winrate(
    winrate: float,
    reported_player: str,
    puzzle_player: str,
) -> float:
    """Normalize winrate to puzzle player perspective.

    KataGo reports winrate from the perspective of the move's color.
    This function converts to the puzzle player's perspective so all
    comparisons are consistent.

    Args:
        winrate: Raw winrate (0.0 to 1.0) from KataGo.
        reported_player: Color that KataGo reported for ('B' or 'W').
        puzzle_player: Color of the puzzle player ('B' or 'W').

    Returns:
        Winrate from puzzle player perspective (0.0 to 1.0).
    """
    reported_player = reported_player.upper()
    puzzle_player = puzzle_player.upper()

    if reported_player == puzzle_player:
        return winrate
    return 1.0 - winrate


def classify_move_quality(
    move_winrate: float,
    root_winrate: float,
    move_policy: float,
    config: AiSolveConfig,
    *,
    score_lead: float = 0.0,
) -> MoveQuality:
    """Classify a single move using delta-based thresholds (DD-2, DD-6).

    No absolute winrate gates — classification is purely delta-based.
    The delta is computed as (root_winrate - move_winrate) so that
    positive delta means the move is WORSE than root.

    Args:
        move_winrate: Winrate after this move (puzzle player perspective).
        root_winrate: Root position winrate (puzzle player perspective).
        move_policy: Policy prior for this move.
        config: AiSolveConfig with thresholds.
        score_lead: Score lead for this move (puzzle player perspective, S1-G15).
            Available for downstream consumers but not used in classification.

    Returns:
        MoveQuality: TE, BM, BM_HO, or NEUTRAL.
    """
    # Delta: how much worse is this move vs root?
    # Positive delta = move is worse than root position
    delta = root_winrate - move_winrate

    thresholds = config.thresholds

    if delta <= thresholds.t_good:
        return MoveQuality.TE
    elif delta >= thresholds.t_hotspot:
        return MoveQuality.BM_HO
    elif delta >= thresholds.t_bad:
        return MoveQuality.BM
    else:
        return MoveQuality.NEUTRAL


def analyze_position_candidates(
    analysis: AnalysisResponse,
    puzzle_player: str,
    puzzle_id: str,
    config: AiSolveConfig,
    *,
    engine: AnalysisEngine | None = None,
    initial_moves: list[str] | None = None,
) -> PositionAnalysis:
    """Analyze and classify all candidate moves from a KataGo analysis.

    Steps:
    1. Check for pass as best move → reject (EDGE-4)
    2. Pre-filter: only confirm moves with policy >= confirmation_min_policy
    3. S1-G16: If engine provided, run per-candidate confirmation queries
       at confirmation_visits for precise delta judgements
    4. Classify each move using delta-based thresholds
    5. Separate into correct/wrong/neutral pools
    6. Annotate confidence from root winrate (DD-6, annotations not gates)

    Args:
        analysis: KataGo AnalysisResponse with move candidates.
        puzzle_player: Puzzle player color ('B' or 'W').
        puzzle_id: Puzzle identifier for logging.
        config: AiSolveConfig with all thresholds.
        engine: Optional analysis engine for per-candidate confirmation
            queries (S1-G16). When provided, each candidate that passes the
            policy pre-filter receives a dedicated query at
            config.solution_tree.confirmation_visits for precise deltas.
            When None, uses shared analysis data (backward compatible).
        initial_moves: Move sequence leading to this position (for engine
            queries). Required when engine is provided.

    Returns:
        PositionAnalysis with classified moves and metadata.

    Raises:
        ValueError: If pass is the best move (position already resolved).
    """
    move_infos = _get_move_infos(analysis)
    if not move_infos:
        logger.warning("No move candidates for puzzle %s", puzzle_id)
        return PositionAnalysis(
            puzzle_id=puzzle_id,
            root_winrate=0.5,
            player_color=puzzle_player,
            ac_level=AiCorrectnessLevel.UNTOUCHED,
        )

    # Determine root winrate from best move
    # KataGo reports winrate for the player whose turn it is
    best_move_info = move_infos[0]
    best_move_str = _get_move_str(best_move_info)

    # EDGE-4: Pass as best move → reject
    if best_move_str.upper() == "PASS":
        raise ValueError(
            f"Puzzle {puzzle_id}: pass is the best move — position already resolved"
        )

    # DD-1: Use root winrate from KataGo rootInfo (canonical position evaluation)
    # Normalize to puzzle player perspective — under SIDETOMOVE config, rootInfo
    # reports from the side-to-move (= puzzle player) so this is a no-op for Black
    # puzzles, but flips correctly for White puzzles where side-to-move is White.
    root_winrate = normalize_winrate(
        analysis.root_winrate, puzzle_player, puzzle_player,
    )

    logger.info(
        "Puzzle %s: root_winrate=%.3f (puzzle_player=%s perspective)",
        puzzle_id, root_winrate, puzzle_player,
    )

    # Classify all candidate moves
    all_classifications: list[MoveClassification] = []
    correct_moves: list[MoveClassification] = []
    wrong_moves: list[MoveClassification] = []
    neutral_moves: list[MoveClassification] = []

    tree_config = config.solution_tree
    _initial = initial_moves or []

    # Collect candidates passing pre-filter
    candidates_for_confirmation: list[tuple[int, dict | MoveAnalysis]] = []

    for rank, move_info in enumerate(move_infos):
        move_str = _get_move_str(move_info)
        if move_str.upper() == "PASS":
            continue

        move_policy = _get_policy(move_info)

        # Pre-filter: skip low-policy moves (DD-2, STR-1)
        if move_policy < tree_config.confirmation_min_policy:
            continue

        candidates_for_confirmation.append((rank, move_info))

    # S1-G16: Per-candidate confirmation queries for precise deltas
    # When engine is available, query each candidate at confirmation_visits
    # to get precise per-move winrate/score_lead data, rather than relying
    # solely on the shared multi-move scan.
    confirmed_data: dict[str, dict] = {}
    if engine is not None and candidates_for_confirmation:
        confirmation_visits = tree_config.confirmation_visits
        logger.info("Per-candidate confirmation queries for precise deltas")
        logger.info(
            "Puzzle %s: running %d confirmation queries at %d visits",
            puzzle_id, len(candidates_for_confirmation), confirmation_visits,
        )
        for _rank, move_info in candidates_for_confirmation:
            move_str = _get_move_str(move_info)
            try:
                # Query engine with candidate move applied to position
                confirm_analysis = engine.query(
                    _initial + [move_str],
                    max_visits=confirmation_visits,
                )
                confirm_infos = _get_move_infos(confirm_analysis)
                if confirm_infos:
                    # After playing move_str, the opponent responds.
                    # The winrate reported is from the opponent's perspective,
                    # so we flip to get the puzzle player's winrate.
                    opponent_color = "W" if puzzle_player.upper() == "B" else "B"
                    opp_wr = _get_winrate(confirm_infos[0])
                    confirmed_wr = normalize_winrate(opp_wr, opponent_color, puzzle_player)
                    confirmed_sl = _get_score_lead(confirm_infos[0])
                    # Negate score_lead since it's from opponent perspective
                    if opponent_color != puzzle_player.upper():
                        confirmed_sl = -confirmed_sl
                    confirmed_data[move_str.upper()] = {
                        "winrate": confirmed_wr,
                        "score_lead": confirmed_sl,
                    }
            except Exception as e:
                logger.warning(
                    "Puzzle %s: confirmation query failed for %s: %s",
                    puzzle_id, move_str, e,
                )

    # D3: Perspective delta fix — rebase root winrate when confirmation data
    # shows ALL confirmed moves are significantly worse than root.  This happens
    # when the tsumego frame introduces evaluation noise, making root_winrate
    # unreliable.  In that case, use the best confirmed move's winrate as the
    # effective root, so delta classification compares moves against each other
    # rather than against an artificially inflated root.
    effective_root = root_winrate
    if confirmed_data:
        max_confirmed_wr = max(d["winrate"] for d in confirmed_data.values())
        # If ALL confirmed moves are significantly below root, root is likely unreliable
        if root_winrate - max_confirmed_wr > config.thresholds.t_rebase_gap:
            effective_root = max_confirmed_wr
            logger.info(
                "Puzzle %s: rebasing root_winrate %.3f → %.3f "
                "(all confirmed moves significantly below root, likely frame noise)",
                puzzle_id, root_winrate, effective_root,
            )

    for rank, move_info in candidates_for_confirmation:
        move_str = _get_move_str(move_info)
        move_policy = _get_policy(move_info)

        # Use confirmed data if available (S1-G16), else fall back to shared scan
        confirmed = confirmed_data.get(move_str.upper())
        if confirmed is not None:
            move_wr = confirmed["winrate"]
            move_score_lead = confirmed["score_lead"]
        else:
            move_wr_raw = _get_winrate(move_info)
            move_wr = normalize_winrate(move_wr_raw, puzzle_player, puzzle_player)
            move_score_lead = _get_score_lead(move_info)

        quality = classify_move_quality(
            move_wr, effective_root, move_policy, config,
            score_lead=move_score_lead,
        )
        delta = effective_root - move_wr

        classification = MoveClassification(
            move_gtp=move_str,
            color=puzzle_player,
            quality=quality,
            winrate=move_wr,
            delta=delta,
            policy=move_policy,
            rank=rank,
            score_lead=move_score_lead,
        )

        logger.info(
            "Puzzle %s: move %s quality=%s delta=%.4f "
            "(root=%.3f - move=%.3f) policy=%.4f rank=%d",
            puzzle_id, move_str, quality.name, delta,
            root_winrate, move_wr, move_policy, rank,
        )

        all_classifications.append(classification)

        if quality == MoveQuality.TE:
            correct_moves.append(classification)
        elif quality in (MoveQuality.BM, MoveQuality.BM_HO):
            wrong_moves.append(classification)
        else:
            neutral_moves.append(classification)

    # Sort: correct by winrate desc, wrong by policy desc (DD-2)
    correct_moves.sort(key=lambda m: (-m.winrate, -m.policy))
    wrong_moves.sort(key=lambda m: (-m.policy, m.delta))

    # Confidence annotation from root winrate (DD-6: annotations, not gates)
    confidence_metrics = config.confidence_metrics
    if root_winrate < confidence_metrics.pre_winrate_floor:
        root_winrate_confidence = ConfidenceLevel.LOW
        root_winrate_confidence_reason = "root_wr_below_floor"
    elif root_winrate > confidence_metrics.post_winrate_ceiling:
        root_winrate_confidence = ConfidenceLevel.HIGH
        root_winrate_confidence_reason = "root_wr_above_ceiling"
    else:
        root_winrate_confidence = ConfidenceLevel.MEDIUM
        root_winrate_confidence_reason = "root_wr_in_range"

    confirmed_count = len(confirmed_data)
    result = PositionAnalysis(
        puzzle_id=puzzle_id,
        root_winrate=root_winrate,
        player_color=puzzle_player,
        correct_moves=correct_moves,
        wrong_moves=wrong_moves,
        neutral_moves=neutral_moves,
        all_classifications=all_classifications,
        root_winrate_confidence=root_winrate_confidence,
        root_winrate_confidence_reason=root_winrate_confidence_reason,
    )

    logger.info(
        "Puzzle %s: %d correct, %d wrong, %d neutral "
        "(root_wr=%.3f, confidence=%s, confirmed=%d/%d)",
        puzzle_id, len(correct_moves), len(wrong_moves), len(neutral_moves),
        root_winrate, root_winrate_confidence,
        confirmed_count, len(candidates_for_confirmation),
    )

    return result


# --- Internal helpers for extracting data from MoveAnalysis ---


def _get_move_infos(analysis) -> list:
    """Extract move info list from AnalysisResponse or mock.

    Real AnalysisResponse uses 'move_infos' (snake_case).
    Mock objects from tests may use 'moveInfos' (camelCase).
    Prioritizes move_infos if it's a real list (not a MagicMock).
    """
    # Check for real AnalysisResponse.move_infos first
    mi = getattr(analysis, "move_infos", None)
    if isinstance(mi, list):
        return mi
    # Fall back to mock-style moveInfos
    mi = getattr(analysis, "moveInfos", None)
    if isinstance(mi, list):
        return mi
    return []


def _get_move_str(move_info: MoveAnalysis | dict) -> str:
    """Extract move string from MoveAnalysis or dict."""
    if isinstance(move_info, dict):
        return move_info.get("move", "pass")
    return getattr(move_info, "move", "pass")


def _get_winrate(move_info: MoveAnalysis | dict) -> float:
    """Extract winrate from MoveAnalysis or dict."""
    if isinstance(move_info, dict):
        return move_info.get("winrate", 0.5)
    return getattr(move_info, "winrate", 0.5)


def _get_policy(move_info: MoveAnalysis | dict) -> float:
    """Extract policy prior from MoveAnalysis or dict."""
    if isinstance(move_info, dict):
        # Dicts from mock engines use 'prior'; real MoveAnalysis uses 'policy_prior'
        return move_info.get("prior", move_info.get("policy_prior", 0.0))
    # Real MoveAnalysis objects use policy_prior
    return getattr(move_info, "policy_prior", getattr(move_info, "prior", 0.0))


def _get_score_lead(move_info: MoveAnalysis | dict) -> float:
    """Extract score lead from MoveAnalysis or dict (S1-G15)."""
    if isinstance(move_info, dict):
        return move_info.get("score_lead", move_info.get("scoreLead", 0.0))
    return getattr(move_info, "score_lead", 0.0)


def _get_pv(move_info: MoveAnalysis | dict) -> list[str]:
    """Extract principal variation from MoveAnalysis or dict (S1-G12)."""
    if isinstance(move_info, dict):
        return move_info.get("pv", [])
    return getattr(move_info, "pv", [])


def _get_ownership(analysis) -> list[list[float]] | None:
    """Extract ownership data from analysis response (S1-G1).

    Returns the ownership map from the top move if available.
    """
    move_infos = _get_move_infos(analysis)
    if not move_infos:
        return None
    top = move_infos[0]
    if isinstance(top, dict):
        return top.get("ownership", None)
    return getattr(top, "ownership", None)


# ---------------------------------------------------------------------------
# Phase 4: Tree Builder
# ---------------------------------------------------------------------------


class AnalysisEngine(Protocol):
    """Protocol for engine that can analyze positions.

    This allows build_solution_tree to work with any engine implementation
    without importing concrete engine classes.
    """

    def query(
        self,
        moves: list[str],
        *,
        max_visits: int | None = None,
    ) -> AnalysisResponse:
        """Query the engine with a move sequence and return analysis."""
        ...


class SyncEngineAdapter:
    """Adapter that wraps an async SingleEngineManager for sync tree builder.

    The tree builder uses synchronous `engine.query()` calls, but
    SingleEngineManager only has `async analyze()`. This adapter
    builds a proper AnalysisRequest (with tsumego frame, komi=0,
    puzzle region restriction) and runs the async method synchronously.

    Usage in enrich_single.py:
        adapter = SyncEngineAdapter(engine_manager, position)
        tree = build_solution_tree(engine=adapter, ...)
    """

    def __init__(self, engine_manager, position, config=None):
        """Initialize adapter.

        Applies tsumego frame and komi override to the position so that
        every subsequent query sends KataGo a properly framed tsumego.

        Args:
            engine_manager: SingleEngineManager with async analyze().
            position: Position object (raw, unframed).
            config: Optional EnrichmentConfig for query building.
        """
        self._engine_manager = engine_manager
        self._raw_position = position
        self._config = config
        self._player_color = position.player_to_move.value

        # Single source of truth: prepare_tsumego_query handles
        # komi override, region computation, and tsumego frame.
        try:
            from analyzers.query_builder import prepare_tsumego_query
        except ImportError:
            from ..analyzers.query_builder import prepare_tsumego_query

        bundle = prepare_tsumego_query(position, config=config)
        self._position = bundle.framed_position
        self._region_moves = bundle.region_moves

    def query(
        self,
        moves: list[str],
        *,
        max_visits: int | None = None,
    ):
        """Synchronous query that delegates to async engine.

        Builds a proper AnalysisRequest with tsumego frame applied,
        converts GTP move list to KataGo format [color, coord], and
        runs the async analyze() synchronously.

        Args:
            moves: GTP move coordinates, e.g. ["C3", "D4"].
                Colors alternate starting from puzzle player.
            max_visits: Override max visits for this query.
        """
        import asyncio

        try:
            from models.analysis_request import AnalysisRequest
        except ImportError:
            from ..models.analysis_request import AnalysisRequest

        # Convert flat GTP list to KataGo [color, coord] format
        katago_moves: list[list[str]] = []
        current_color = self._player_color
        for m in moves:
            katago_moves.append([current_color, m])
            current_color = "W" if current_color == "B" else "B"

        request = AnalysisRequest(
            position=self._position,
            max_visits=max_visits or 500,
            moves=katago_moves,
            allowed_moves=self._region_moves if self._region_moves else None,
            include_ownership=True,
            include_pv=True,
            include_policy=True,
        )

        # Run async analyze synchronously.
        # Use get_running_loop() to detect whether we're inside an async
        # context.  When called from a ThreadPoolExecutor worker thread
        # (e.g. S2-G13 parallel alt-tree building) there is no running
        # loop, so asyncio.run() is safe and correct.
        try:
            asyncio.get_running_loop()
            # Running loop exists → offload to a fresh thread so
            # asyncio.run() can create its own loop there.
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(
                    asyncio.run,
                    self._engine_manager.analyze(request),
                )
                return future.result()
        except RuntimeError:
            # No running event loop → safe to use asyncio.run() directly
            return asyncio.run(self._engine_manager.analyze(request))


class _BoardState:
    """Minimal board state tracker for transposition hashing (KM-02).

    Tracks stone placements on a grid, resolves captures via flood-fill
    liberty counting. Uses Zobrist hashing for O(1) amortized position
    hash computation (incremental XOR on place/capture).

    This is NOT a full Go rules engine — it handles placement + capture
    only (no ko superko rules, no scoring). Sufficient for tsumego
    solution tree transposition detection.
    """

    # Zobrist hash tables — initialized once at class level
    # Standard Go engine technique: pre-generate random bitstrings for each
    # (color, row, col) combination. Position hash = XOR of all placed stones.
    _ZOBRIST_SEED = 42  # Deterministic for reproducibility
    _zobrist_table: dict[tuple[str, int, int], int] | None = None
    _zobrist_turn: dict[str, int] | None = None
    _zobrist_ko: dict | None = None

    @classmethod
    def _init_zobrist(cls, board_size: int = 19) -> None:
        """Initialize Zobrist hash tables if not already done."""
        if cls._zobrist_table is not None:
            return
        max_size = 19  # Always initialize for max board size
        rng = random.Random(cls._ZOBRIST_SEED)
        cls._zobrist_table = {}
        for color in ("B", "W"):
            for row in range(max_size):
                for col in range(max_size):
                    cls._zobrist_table[(color, row, col)] = rng.getrandbits(64)
        cls._zobrist_turn = {
            "B": rng.getrandbits(64),
            "W": rng.getrandbits(64),
        }
        cls._zobrist_ko = {}
        for row in range(max_size):
            for col in range(max_size):
                cls._zobrist_ko[(row, col)] = rng.getrandbits(64)
        cls._zobrist_ko[None] = 0  # No ko

    def __init__(self, board_size: int = 19):
        self._init_zobrist(board_size)
        self.size = board_size
        self.grid: list[list[str | None]] = [
            [None] * board_size for _ in range(board_size)
        ]
        self._hash: int = 0  # Incremental Zobrist hash
        self.last_capture_point: tuple[int, int] | None = None  # For simple ko detection

    def copy(self) -> _BoardState:
        """Deep copy of the board state."""
        new = _BoardState.__new__(_BoardState)
        new.size = self.size
        new.grid = [row[:] for row in self.grid]
        new._hash = self._hash
        new.last_capture_point = self.last_capture_point
        return new

    def place_stone(self, gtp_coord: str, color: str) -> None:
        """Place a stone and resolve captures.

        Args:
            gtp_coord: GTP coordinate like "C3", "D4".
            color: "B" or "W".
        """
        row, col = self._gtp_to_rc(gtp_coord)
        if row < 0 or row >= self.size or col < 0 or col >= self.size:
            return
        self.grid[row][col] = color
        self._hash ^= self._zobrist_table[(color, row, col)]  # XOR in new stone

        # Check for captures of opponent groups adjacent to placed stone
        opponent = "W" if color == "B" else "B"
        captured_count = 0
        captured_single: tuple[int, int] | None = None
        for nr, nc in self._neighbors(row, col):
            if self.grid[nr][nc] == opponent:
                group = self._flood_fill(nr, nc, opponent)
                if not self._has_liberty(group):
                    for gr, gc in group:
                        self._hash ^= self._zobrist_table[(opponent, gr, gc)]  # XOR out captured
                        self.grid[gr][gc] = None
                    captured_count += len(group)
                    if len(group) == 1:
                        captured_single = list(group)[0]

        # Simple ko detection: if exactly 1 stone captured, record the point
        self.last_capture_point = captured_single if captured_count == 1 else None

    def add_initial_stone(self, color: str, x: int, y: int) -> None:
        """Add an initial stone (from SGF AB/AW) without capture resolution."""
        if 0 <= y < self.size and 0 <= x < self.size:
            self.grid[y][x] = color
            self._hash ^= self._zobrist_table[(color, y, x)]

    def position_hash(self, player_to_move: str) -> int:
        """Compute position hash using Zobrist hashing (O(1) amortized).

        The hash is maintained incrementally via XOR on place/capture.
        This method just XORs in the turn and ko components.
        """
        h = self._hash
        h ^= self._zobrist_turn.get(player_to_move, 0)
        if self.last_capture_point is not None:
            h ^= self._zobrist_ko.get(self.last_capture_point, 0)
        return h

    def _gtp_to_rc(self, gtp: str) -> tuple[int, int]:
        """Convert GTP coordinate to (row, col). Row 0 = top."""
        if len(gtp) < 2:
            return -1, -1
        col_letter = gtp[0].upper()
        col = ord(col_letter) - ord('A')
        if col_letter > 'I':
            col -= 1  # GTP skips 'I'
        try:
            row = self.size - int(gtp[1:])
        except ValueError:
            return -1, -1
        return row, col

    def _rc_to_gtp(self, row: int, col: int) -> str:
        """Convert (row, col) to GTP coordinate."""
        letters = "ABCDEFGHJKLMNOPQRST"
        col_letter = letters[col] if col < len(letters) else "?"
        gtp_row = self.size - row
        return f"{col_letter}{gtp_row}"

    def _neighbors(self, row: int, col: int) -> list[tuple[int, int]]:
        """Return valid neighbor coordinates."""
        result: list[tuple[int, int]] = []
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = row + dr, col + dc
            if 0 <= nr < self.size and 0 <= nc < self.size:
                result.append((nr, nc))
        return result

    def _flood_fill(self, row: int, col: int, color: str) -> set[tuple[int, int]]:
        """Find all stones connected to (row, col) of the given color."""
        group: set[tuple[int, int]] = set()
        stack = [(row, col)]
        while stack:
            r, c = stack.pop()
            if (r, c) in group:
                continue
            if self.grid[r][c] != color:
                continue
            group.add((r, c))
            for nr, nc in self._neighbors(r, c):
                if (nr, nc) not in group and self.grid[nr][nc] == color:
                    stack.append((nr, nc))
        return group

    def _has_liberty(self, group: set[tuple[int, int]]) -> bool:
        """Check if a group has at least one liberty."""
        for r, c in group:
            for nr, nc in self._neighbors(r, c):
                if self.grid[nr][nc] is None:
                    return True
        return False


def _compute_position_hash(
    moves: list[str],
    player_to_move: str = "B",
    ko_point: str = "none",
) -> int:
    """Legacy position hash from move set (KM-02, Review Panel Topic 4).

    DEPRECATED: Kept for backward compatibility with direct callers.
    New code should use ``_BoardState.position_hash()`` which tracks
    actual board state including captures.

    Args:
        moves: GTP move sequence from initial position.
        player_to_move: Color to move at the END of the move sequence.
        ko_point: Ko ban point as GTP coordinate, or "none".

    Returns:
        Hash of the position (int).
    """
    hash_elements = frozenset(moves) | {("turn", player_to_move), ("ko", ko_point)}
    return hash(hash_elements)


def _extract_player_reply_sequence(node: SolutionNode) -> list[str]:
    """Extract player move sequence from a proven subtree (KM-01).

    Walks the correct-line children and extracts the player's GTP moves.
    Used by simulation to test if the same reply works for sibling
    opponent responses.

    Args:
        node: Root of a proven correct-line subtree.

    Returns:
        List of player move GTP strings from the correct line.
        Empty list if the subtree is truncated or has no correct children.
    """
    reply_moves: list[str] = []
    current = node
    while current.children:
        # Find the correct child (player's reply)
        correct_child = None
        for child in current.children:
            if child.is_correct:
                correct_child = child
                break
        if correct_child is None:
            break
        reply_moves.append(correct_child.move_gtp)
        current = correct_child
    return reply_moves


def _try_simulation(
    engine: AnalysisEngine,
    moves: list[str],
    cached_reply_sequence: list[str],
    config: AiSolveConfig,
    query_budget: QueryBudget,
    completeness: TreeCompletenessMetrics,
    player_color: str,
    effective_visits: int,
    reference_winrate: float = 0.5,
) -> SolutionNode | None:
    """Attempt Kawano simulation for a sibling opponent response (KM-01).

    Replays the FULL cached player reply sequence from a proven sibling,
    alternating colors. Runs a final verification query to confirm the
    position remains resolved.

    Args:
        engine: Analysis engine.
        moves: Move sequence including the sibling opponent move.
        cached_reply_sequence: Player reply moves from a proven sibling.
        config: AiSolveConfig with thresholds.
        query_budget: Budget tracker.
        completeness: Metrics tracker.
        player_color: Puzzle player color.
        effective_visits: Normal visit count (used for reference only).
        reference_winrate: Reference winrate for delta-based verification.
            At shallow depths (< 3), this is root_winrate (global context).
            At deeper depths (>= 3), this is first_child_winrate (local peer).

    Returns:
        SolutionNode if simulation succeeds, None if it fails.
    """
    if not cached_reply_sequence:
        return None

    if not query_budget.can_query():
        return None

    # Replay the full cached sequence (faithfully per paper §4.2)
    # After opponent's move (already in `moves`), play all cached replies
    sim_moves = list(moves)
    for reply_move in cached_reply_sequence:
        sim_moves.append(reply_move)

    tree_config = config.solution_tree
    verify_visits = tree_config.simulation_verify_visits

    try:
        query_budget.consume()
        analysis = engine.query(sim_moves, max_visits=verify_visits)
    except Exception:
        completeness.simulation_misses += 1
        return None

    move_infos = _get_move_infos(analysis)
    if not move_infos:
        completeness.simulation_misses += 1
        return None

    best_wr = _get_winrate(move_infos[0])
    sim_wr = normalize_winrate(best_wr, player_color, player_color)

    t_good = config.thresholds.t_good

    delta = reference_winrate - sim_wr
    if delta <= t_good:
        completeness.simulation_hits += 1
        # Build node chain from the cached sequence
        # The outermost node is the first player reply
        root_reply = SolutionNode(
            move_gtp=cached_reply_sequence[0],
            color=player_color,
            winrate=sim_wr,
            visits=verify_visits,
            is_correct=True,
        )
        # Build remaining sequence as linear chain
        current = root_reply
        opp_color = _opponent_color(player_color)
        for i, move in enumerate(cached_reply_sequence[1:], start=1):
            child_color = opp_color if i % 2 == 1 else player_color
            child = SolutionNode(
                move_gtp=move,
                color=child_color,
                winrate=sim_wr,
                visits=verify_visits,
                is_correct=(child_color == player_color),
            )
            current.children.append(child)
            current = child

        return root_reply
    else:
        completeness.simulation_misses += 1
        return None


def build_solution_tree(
    engine: AnalysisEngine,
    initial_moves: list[str],
    correct_move_gtp: str,
    player_color: str,
    config: AiSolveConfig,
    level_slug: str,
    query_budget: QueryBudget,
    puzzle_id: str = "",
    *,
    corner_position: str = "",
    pv_length: int = 0,
    puzzle_region: frozenset[tuple[int, int]] | None = None,
) -> SolutionNode:
    """Build a recursive solution tree from a correct first move (DD-1, DD-3).

    Stopping conditions (DD-1):
    1. Winrate stability: |wr - root_wr| < wr_epsilon
    2. Ownership convergence: key stones' ownership change < own_epsilon (S1-G1)
    3. Seki detection: winrate in seki band for consecutive depths
    4. Hard cap: solution_max_depth reached
    5. Budget: max_total_tree_queries exhausted
    6. Terminal: pass in PV, or no legal non-terminal continuations

    Minimum floor: never stop before solution_min_depth (while continuations exist).

    Args:
        engine: Analysis engine with query() method.
        initial_moves: Move sequence leading to the position to analyze.
        correct_move_gtp: The correct first move (GTP format).
        player_color: Puzzle player color ('B' or 'W').
        config: AiSolveConfig with thresholds and depth profiles.
        level_slug: Level slug for depth profile selection.
        query_budget: Required budget tracker.
        puzzle_id: Puzzle ID for logging.
        corner_position: Corner position hint (e.g. 'TL', 'BR') for visit boost (S1-G12).
        pv_length: Principal variation length for ladder detection (S1-G12).

    Returns:
        SolutionNode with solution tree and completeness metrics at root.
    """
    tree_config = config.solution_tree

    # Select depth profile from level category (DD-1)
    try:
        category = get_level_category(level_slug)
    except KeyError:
        category = "core"  # fallback
        logger.warning(
            "Puzzle %s: unknown level '%s', using 'core' depth profile",
            puzzle_id, level_slug,
        )

    profile = tree_config.depth_profiles.get(category)
    if profile is None:
        # Should not happen with valid config, but defensive
        from config.solution_tree import DepthProfile
        profile = DepthProfile(solution_min_depth=3, solution_max_depth=16)

    # Visit count with edge case boosts (DD-12, S1-G12)
    effective_visits = tree_config.tree_visits
    edge_boosts = config.edge_case_boosts

    # S1-G12: Apply corner visit boost when puzzle has corner position
    if corner_position and corner_position in ("TL", "TR", "BL", "BR"):
        effective_visits = int(effective_visits * edge_boosts.corner_visit_boost)
        logger.info(
            "Puzzle %s: applying corner visit boost %.1fx → %d visits",
            puzzle_id, edge_boosts.corner_visit_boost, effective_visits,
        )

    # S1-G12: Apply ladder visit boost when PV length exceeds threshold
    if pv_length > edge_boosts.ladder_pv_threshold:
        effective_visits = int(effective_visits * edge_boosts.ladder_visit_boost)
        logger.info(
            "Puzzle %s: applying ladder visit boost %.1fx (PV=%d > %d) → %d visits",
            puzzle_id, edge_boosts.ladder_visit_boost, pv_length,
            edge_boosts.ladder_pv_threshold, effective_visits,
        )

    # PI-2: Adaptive visit allocation
    # v1.26: Compound with edge-case boosts instead of overriding them.
    # In fixed mode, boosts are already applied to tree_visits above.
    # In adaptive mode, apply boosts to branch_visits as the new base.
    if tree_config.visit_allocation_mode == "adaptive":
        # Start from branch_visits, then apply any edge-case boost
        base_visits = tree_config.branch_visits
        boost_factor = 1.0
        if corner_position and corner_position in ("TL", "TR", "BL", "BR"):
            boost_factor *= edge_boosts.corner_visit_boost
        if pv_length > edge_boosts.ladder_pv_threshold:
            boost_factor *= edge_boosts.ladder_visit_boost
        effective_visits = int(base_visits * boost_factor)
        logger.info(
            "Puzzle %s: adaptive visit allocation mode — branch=%d, continuation=%d, boost=%.2fx, effective=%d",
            puzzle_id, tree_config.branch_visits, tree_config.continuation_visits,
            boost_factor, effective_visits,
        )

    completeness = TreeCompletenessMetrics()

    # KM-02: Transposition table (position hash → cached node)
    transposition_cache: dict[int, SolutionNode] | None = None
    if tree_config.transposition_enabled:
        transposition_cache = {}

    # Board state tracker: needed for transposition hashing AND terminal detection gates
    board_state: _BoardState | None = None
    if tree_config.transposition_enabled or tree_config.terminal_detection_enabled:
        _bs = 19  # Default fallback
        if hasattr(engine, '_raw_position') and hasattr(engine._raw_position, 'board_size'):
            _bs = engine._raw_position.board_size
        board_state = _BoardState(board_size=_bs)
        # Populate initial stones from engine adapter if available
        if hasattr(engine, '_raw_position') and hasattr(engine._raw_position, 'stones'):
            for stone in engine._raw_position.stones:
                board_state.add_initial_stone(stone.color.value, stone.x, stone.y)
        # Replay initial_moves on the board
        current_color = player_color
        for move in initial_moves:
            board_state.place_stone(move, current_color)
            current_color = "W" if current_color == "B" else "B"
        # Place the correct first move
        board_state.place_stone(correct_move_gtp, player_color)

    # Build the root node (correct first move)
    root = _build_tree_recursive(
        engine=engine,
        moves=initial_moves + [correct_move_gtp],
        player_color=player_color,
        move_gtp=correct_move_gtp,
        is_player_turn=False,  # After player's correct move, it's opponent's turn
        depth=1,
        min_depth=profile.solution_min_depth,
        max_depth=profile.solution_max_depth,
        config=config,
        query_budget=query_budget,
        effective_visits=effective_visits,
        completeness=completeness,
        seki_consecutive_count=0,
        root_winrate=None,
        puzzle_id=puzzle_id,
        prev_ownership=None,
        transposition_cache=transposition_cache,
        board_state=board_state,
        puzzle_region=puzzle_region,
    )

    root.is_correct = True
    root.tree_completeness = completeness

    # KM-04: Compute max resolved depth for difficulty signal
    completeness.max_resolved_depth = _compute_max_resolved_depth(root)

    return root


def _build_tree_recursive(
    engine: AnalysisEngine,
    moves: list[str],
    player_color: str,
    move_gtp: str,
    is_player_turn: bool,
    depth: int,
    min_depth: int,
    max_depth: int,
    config: AiSolveConfig,
    query_budget: QueryBudget,
    effective_visits: int,
    completeness: TreeCompletenessMetrics,
    seki_consecutive_count: int,
    root_winrate: float | None,
    puzzle_id: str,
    prev_ownership: list[list[float]] | None = None,
    transposition_cache: dict[int, SolutionNode] | None = None,
    board_state: _BoardState | None = None,
    puzzle_region: frozenset[tuple[int, int]] | None = None,
) -> SolutionNode:
    """Recursively build a solution tree node.

    At opponent nodes: branch up to max_branch_width responses.
    At player nodes: single correct follow-up.
    """
    tree_config = config.solution_tree
    seki_config = config.seki_detection

    # Create the node
    node = SolutionNode(
        move_gtp=move_gtp,
        color=player_color if not is_player_turn else _opponent_color(player_color),
    )

    # KM-02: Transposition table lookup (board-state based hashing)
    if transposition_cache is not None and board_state is not None:
        current_player = player_color if is_player_turn else _opponent_color(player_color)
        pos_hash = board_state.position_hash(current_player)
        if pos_hash in transposition_cache:
            cached = transposition_cache[pos_hash].model_copy(deep=True)
            completeness.transposition_hits += 1
            return cached

    # Stopping condition 4: Hard cap
    if depth > max_depth:
        logger.info(
            "Puzzle %s: tree depth=%d stop=max_depth move=%s",
            puzzle_id, depth, move_gtp,
        )
        completeness.completed_branches += 1
        completeness.total_attempted_branches += 1
        return node

    # Stopping condition 5: Budget exhausted
    if not query_budget.can_query():
        logger.info(
            "Puzzle %s: tree depth=%d stop=budget_exhausted move=%s",
            puzzle_id, depth, move_gtp,
        )
        node.truncated = True
        completeness.total_attempted_branches += 1
        return node

    # Pre-query terminal detection (Benson gate G1 + Interior-point G2)
    benson_cfg = tree_config.benson_gate
    if (tree_config.terminal_detection_enabled
            and benson_cfg.enabled
            and board_state is not None and puzzle_region is not None
            and depth >= min_depth):
        from analyzers.benson_check import (
            check_interior_point_death,
            find_unconditionally_alive_groups,
        )
        _gate_t0 = time.monotonic()

        # Convert _BoardState grid to dict format
        stones_dict: dict[tuple[int, int], str] = {}
        for r in range(board_state.size):
            for c in range(board_state.size):
                cell = board_state.grid[r][c]
                if cell is not None:
                    stones_dict[(r, c)] = cell

        defender_color = _opponent_color(player_color)

        # G1: Benson's unconditional life — contest group alive?
        alive_groups = find_unconditionally_alive_groups(stones_dict, board_state.size)
        if alive_groups:
            contest_stones = frozenset(
                pos for pos, clr in stones_dict.items()
                if pos in puzzle_region and clr == defender_color
            )
            if (len(contest_stones) >= benson_cfg.min_contest_stones
                    and any(contest_stones <= group for group in alive_groups)):
                _gate_ms = (time.monotonic() - _gate_t0) * 1000
                logger.info(
                    "Benson gate: puzzle=%s depth=%d gate_result=alive "
                    "contest_stones=%d alive_groups=%d elapsed_ms=%.1f",
                    puzzle_id, depth, len(contest_stones),
                    len(alive_groups), _gate_ms,
                )
                completeness.completed_branches += 1
                completeness.total_attempted_branches += 1
                return node

        # G2: Interior-point death — defender cannot form two eyes?
        if check_interior_point_death(stones_dict, defender_color, puzzle_region, board_state.size):
            _gate_ms = (time.monotonic() - _gate_t0) * 1000
            logger.info(
                "Benson gate: puzzle=%s depth=%d gate_result=interior_death "
                "contest_stones=%d elapsed_ms=%.1f",
                puzzle_id, depth,
                sum(1 for pos, clr in stones_dict.items()
                    if pos in puzzle_region and clr == defender_color),
                _gate_ms,
            )
            completeness.completed_branches += 1
            completeness.total_attempted_branches += 1
            return node

        _gate_ms = (time.monotonic() - _gate_t0) * 1000
        if _gate_ms > 1.0:  # Only log pass-through if it took notable time
            logger.debug(
                "Benson gate: puzzle=%s depth=%d gate_result=pass_through elapsed_ms=%.1f",
                puzzle_id, depth, _gate_ms,
            )

    # Query the engine
    try:
        query_budget.consume()
        analysis = engine.query(moves, max_visits=effective_visits)
    except Exception as e:
        logger.warning("Puzzle %s: engine query failed at depth %d: %s", puzzle_id, depth, e)
        node.truncated = True
        completeness.total_attempted_branches += 1
        return node

    move_infos = _get_move_infos(analysis)
    if not move_infos:
        # Stopping condition 6: No legal moves
        logger.info(
            "Puzzle %s: tree depth=%d stop=no_legal_moves move=%s turn=%s",
            puzzle_id, depth, move_gtp,
            "player" if is_player_turn else "opponent",
        )
        completeness.completed_branches += 1
        completeness.total_attempted_branches += 1
        return node

    best_move = move_infos[0]
    best_wr = _get_winrate(best_move)
    node_wr = normalize_winrate(best_wr, player_color, player_color)
    node.winrate = node_wr
    node.visits = effective_visits

    if root_winrate is None:
        root_winrate = node_wr

    best_move_str_log = _get_move_str(best_move)
    logger.info(
        "Puzzle %s: tree depth=%d move=%s turn=%s best=%s "
        "wr=%.4f policy=%.4f visits=%d candidates=%d",
        puzzle_id, depth, move_gtp,
        "player" if is_player_turn else "opponent",
        best_move_str_log, node_wr, _get_policy(best_move),
        effective_visits, len(move_infos),
    )

    # S1-G1: Extract ownership data for convergence checking
    current_ownership = _get_ownership(analysis)

    # Stopping condition 6: Pass in PV
    best_move_str = _get_move_str(best_move)
    if best_move_str.upper() == "PASS":
        logger.info(
            "Puzzle %s: tree depth=%d stop=pass_in_pv move=%s",
            puzzle_id, depth, move_gtp,
        )
        completeness.completed_branches += 1
        completeness.total_attempted_branches += 1
        return node

    # Stopping condition 1: Winrate stability (only after min_depth)
    if depth >= min_depth and abs(node_wr - root_winrate) < tree_config.wr_epsilon:
        logger.info(
            "Puzzle %s: tree depth=%d stop=wr_stable move=%s "
            "wr=%.4f root_wr=%.4f delta=%.4f epsilon=%.4f",
            puzzle_id, depth, move_gtp, node_wr, root_winrate,
            abs(node_wr - root_winrate), tree_config.wr_epsilon,
        )
        completeness.completed_branches += 1
        completeness.total_attempted_branches += 1
        return node

    # Stopping condition 2: Ownership convergence (S1-G1)
    # Compare key stones' ownership values with previous depth
    if (
        depth >= min_depth
        and prev_ownership is not None
        and current_ownership is not None
        and tree_config.own_epsilon > 0
    ):
        ownership_converged = _check_ownership_convergence(
            prev_ownership, current_ownership, tree_config.own_epsilon,
        )
        if ownership_converged:
            logger.info(
                "Puzzle %s: tree depth=%d stop=ownership_converged move=%s",
                puzzle_id, depth, move_gtp,
            )
            completeness.completed_branches += 1
            completeness.total_attempted_branches += 1
            return node

    # Stopping condition 3: Seki detection (DD-12, G-05)
    # Check winrate band AND score-lead bound (score_lead_seki_max)
    new_seki_count = seki_consecutive_count
    node_score_lead = abs(_get_score_lead(best_move))
    if (
        seki_config.winrate_band_low <= node_wr <= seki_config.winrate_band_high
        and node_score_lead <= seki_config.score_lead_seki_max
    ):
        new_seki_count += 1
    else:
        new_seki_count = 0

    if depth >= min_depth and new_seki_count >= seki_config.seki_consecutive_depth:
        logger.info(
            "Puzzle %s: tree depth=%d stop=seki move=%s "
            "wr=%.4f seki_count=%d",
            puzzle_id, depth, move_gtp, node_wr, new_seki_count,
        )
        completeness.completed_branches += 1
        completeness.total_attempted_branches += 1
        return node

    # Branch based on whose turn it is
    if is_player_turn:
        # Player node: single best correct follow-up

        # PI-2: Adaptive visit allocation — player continuation nodes
        # get fewer visits since they're typically forced sequences
        child_effective_visits = effective_visits
        if tree_config.visit_allocation_mode == "adaptive":
            child_effective_visits = tree_config.continuation_visits

        # KM-03: Forced move detection
        # Check if position is forced: single candidate above branch_min_policy
        # with high policy prior
        if tree_config.forced_move_visits > 0:
            best_policy = _get_policy(best_move)
            # Count candidates passing the depth-adjusted policy threshold
            effective_min_policy_for_count = (
                tree_config.branch_min_policy
                + tree_config.depth_policy_scale * depth
            )
            candidates_above_threshold = sum(
                1 for mi in move_infos
                if _get_move_str(mi).upper() != "PASS"
                and _get_policy(mi) >= effective_min_policy_for_count
            )
            if (
                best_policy > tree_config.forced_move_policy_threshold
                and candidates_above_threshold == 1
            ):
                child_effective_visits = tree_config.forced_move_visits
                completeness.forced_move_count += 1
                logger.debug(
                    "Puzzle %s: forced move %s at depth %d (policy=%.3f > %.3f), "
                    "reducing visits %d → %d",
                    puzzle_id, best_move_str, depth, best_policy,
                    tree_config.forced_move_policy_threshold,
                    effective_visits, child_effective_visits,
                )

        # KM-02: Create child board state for player move
        child_board = board_state.copy() if board_state is not None else None
        if child_board is not None:
            child_board.place_stone(best_move_str, player_color)

        child = _build_tree_recursive(
            engine=engine,
            moves=moves + [best_move_str],
            player_color=player_color,
            move_gtp=best_move_str,
            is_player_turn=False,
            depth=depth + 1,
            min_depth=min_depth,
            max_depth=max_depth,
            config=config,
            query_budget=query_budget,
            effective_visits=child_effective_visits,
            completeness=completeness,
            seki_consecutive_count=new_seki_count,
            root_winrate=root_winrate,
            puzzle_id=puzzle_id,
            prev_ownership=current_ownership,
            transposition_cache=transposition_cache,
            board_state=child_board,
            puzzle_region=puzzle_region,
        )
        child.is_correct = True

        # KM-03 safety net: if forced-move reduced visits produced a
        # disagreeing result, re-query the child at full visits.
        if (
            child_effective_visits != effective_visits  # was reduced (forced move)
            and root_winrate is not None
            and child.winrate > 0  # child was queried (not truncated)
            and abs(root_winrate - child.winrate) > config.thresholds.t_good
            and query_budget.can_query()
        ):
            logger.debug(
                "Puzzle %s: forced-move safety net triggered at depth %d — "
                "child wr=%.3f, root_wr=%.3f, delta=%.3f > t_good=%.3f. "
                "Re-querying at full visits (%d).",
                puzzle_id, depth, child.winrate, root_winrate,
                abs(root_winrate - child.winrate), config.thresholds.t_good,
                effective_visits,
            )
            # Re-build the child at full visits
            child = _build_tree_recursive(
                engine=engine,
                moves=moves + [best_move_str],
                player_color=player_color,
                move_gtp=best_move_str,
                is_player_turn=False,
                depth=depth + 1,
                min_depth=min_depth,
                max_depth=max_depth,
                config=config,
                query_budget=query_budget,
                effective_visits=effective_visits,  # FULL visits this time
                completeness=completeness,
                seki_consecutive_count=new_seki_count,
                root_winrate=root_winrate,
                puzzle_id=puzzle_id,
                prev_ownership=current_ownership,
                transposition_cache=transposition_cache,
                board_state=child_board,
                puzzle_region=puzzle_region,
            )
            child.is_correct = True

        node.children.append(child)

        # PI-9: Player-side alternative exploration
        # At player nodes, optionally explore alternatives to discover
        # co-correct paths or trick moves
        alt_rate = tree_config.player_alternative_rate
        if alt_rate > 0 and depth < max_depth and query_budget.can_query():
            # Explore top alternatives (moves with policy above threshold
            # that aren't the best move)
            alt_candidates = [
                mi for mi in move_infos
                if _get_move_str(mi).upper() != best_move_str.upper()
                and _get_move_str(mi).upper() != "PASS"
                and _get_policy(mi) >= tree_config.branch_min_policy
            ]
            # Limit to at most 2 alternatives
            for alt_mi in alt_candidates[:2]:
                if not query_budget.can_query():
                    break
                if random.random() > alt_rate:
                    continue
                alt_move_str = _get_move_str(alt_mi)
                alt_board = board_state.copy() if board_state is not None else None
                if alt_board is not None:
                    alt_board.place_stone(alt_move_str, player_color)
                alt_child = _build_tree_recursive(
                    engine=engine,
                    moves=moves + [alt_move_str],
                    player_color=player_color,
                    move_gtp=alt_move_str,
                    is_player_turn=False,
                    depth=depth + 1,
                    min_depth=min_depth,
                    max_depth=max_depth,
                    config=config,
                    query_budget=query_budget,
                    effective_visits=child_effective_visits,
                    completeness=completeness,
                    seki_consecutive_count=new_seki_count,
                    root_winrate=root_winrate,
                    puzzle_id=puzzle_id,
                    prev_ownership=current_ownership,
                    transposition_cache=transposition_cache,
                    board_state=alt_board,
                    puzzle_region=puzzle_region,
                )
                alt_child.is_correct = False  # alternative, not primary
                node.children.append(alt_child)
                logger.debug(
                    "PI-9: Player alternative %s at depth %d (policy=%.3f)",
                    alt_move_str, depth, _get_policy(alt_mi),
                )
    else:
        # Opponent node: branch up to max_branch_width (DD-3)
        branch_count = 0
        first_child_built = False
        cached_reply_sequence: list[str] = []
        first_child_winrate: float = root_winrate or 0.5  # local reference for simulation

        # Log opponent branching candidates above policy threshold
        _effective_min_p = (
            tree_config.branch_min_policy
            + tree_config.depth_policy_scale * depth
        )
        _viable = [
            _get_move_str(mi) for mi in move_infos
            if _get_move_str(mi).upper() != "PASS"
            and _get_policy(mi) >= _effective_min_p
        ][:tree_config.max_branch_width]
        logger.info(
            "Puzzle %s: tree depth=%d opponent_branches=%d "
            "candidates=%s min_policy=%.4f",
            puzzle_id, depth, len(_viable),
            ",".join(_viable) if _viable else "none",
            _effective_min_p,
        )

        for move_info in move_infos:
            if branch_count >= tree_config.max_branch_width:
                break
            if not query_budget.can_query():
                break

            m_str = _get_move_str(move_info)
            m_policy = _get_policy(move_info)

            if m_str.upper() == "PASS":
                continue
            # L3: depth-dependent policy threshold (Thomsen lambda-search)
            effective_min_policy = (
                tree_config.branch_min_policy
                + tree_config.depth_policy_scale * depth
            )
            if m_policy < effective_min_policy:
                # Track when depth scaling made the difference
                if m_policy >= tree_config.branch_min_policy:
                    completeness.branches_pruned_by_depth_policy += 1
                continue

            branch_count += 1

            # KM-01: For siblings after the first, try simulation
            if (
                first_child_built
                and tree_config.simulation_enabled
                and cached_reply_sequence
            ):
                # KM-01: Pre-flight collision check — skip if cached reply
                # contains a coordinate already in the move path (would be
                # rejected by KataGo as illegal/duplicate).
                path_coords = {mv.upper() for mv in moves} | {m_str.upper()}
                collision = [
                    r for r in cached_reply_sequence if r.upper() in path_coords
                ]
                if collision:
                    completeness.simulation_collisions += 1
                    logger.info(
                        "Puzzle %s: simulation collision at depth %d — "
                        "cached reply %s overlaps path move %s, "
                        "skipping simulation",
                        puzzle_id, depth, collision, m_str,
                    )
                else:
                    sim_result = _try_simulation(
                        engine=engine,
                        moves=moves + [m_str],
                        cached_reply_sequence=cached_reply_sequence,
                        config=config,
                        query_budget=query_budget,
                        completeness=completeness,
                        player_color=player_color,
                        effective_visits=effective_visits,
                        reference_winrate=first_child_winrate if depth >= 3 else (root_winrate or 0.5),
                    )
                    if sim_result is not None:
                        # F4-3: Wrap player reply in opponent-move node to match
                        # the structure of fully-built children.
                        opp_node = SolutionNode(
                            move_gtp=m_str,
                            color=_opponent_color(player_color),
                            winrate=sim_result.winrate,
                            visits=sim_result.visits,
                            children=[sim_result],
                        )
                        node.children.append(opp_node)
                        continue
                    # Simulation failed — fall through to full expansion

            # KM-02: Create child board state for opponent move
            child_board = board_state.copy() if board_state is not None else None
            if child_board is not None:
                child_board.place_stone(m_str, _opponent_color(player_color))

            child = _build_tree_recursive(
                engine=engine,
                moves=moves + [m_str],
                player_color=player_color,
                move_gtp=m_str,
                is_player_turn=True,
                depth=depth + 1,
                min_depth=min_depth,
                max_depth=max_depth,
                config=config,
                query_budget=query_budget,
                effective_visits=effective_visits,
                completeness=completeness,
                seki_consecutive_count=new_seki_count,
                root_winrate=root_winrate,
                puzzle_id=puzzle_id,
                prev_ownership=current_ownership,
                transposition_cache=transposition_cache,
                board_state=child_board,
                puzzle_region=puzzle_region,
            )
            node.children.append(child)

            # PI-7: Branch-local disagreement escalation
            # After evaluating an opponent branch, compare its search winrate
            # against the first (policy-top) sibling. Large deviations indicate
            # policy and search disagree on the best opponent response.
            if (
                tree_config.branch_escalation_enabled
                and first_child_built
                and child.winrate is not None
                and query_budget.can_query()
            ):
                # Compare with first child (highest policy prior).
                # Both values are search winrates — same unit, same scale.
                disagreement = abs(child.winrate - first_child_winrate)
                if disagreement > tree_config.branch_disagreement_threshold:
                    # Re-evaluate this branch with escalated visits
                    escalated_visits = min(
                        effective_visits * 2,
                        tree_config.tree_visits * 2,
                    )
                    if escalated_visits > effective_visits and query_budget.can_query():
                        logger.debug(
                            "PI-7: Branch escalation for %s at depth %d "
                            "(disagreement=%.3f > %.3f), visits %d → %d",
                            m_str, depth, disagreement,
                            tree_config.branch_disagreement_threshold,
                            effective_visits, escalated_visits,
                        )
                        esc_board = board_state.copy() if board_state is not None else None
                        if esc_board is not None:
                            esc_board.place_stone(m_str, _opponent_color(player_color))
                        esc_child = _build_tree_recursive(
                            engine=engine,
                            moves=moves + [m_str],
                            player_color=player_color,
                            move_gtp=m_str,
                            is_player_turn=True,
                            depth=depth + 1,
                            min_depth=min_depth,
                            max_depth=max_depth,
                            config=config,
                            query_budget=query_budget,
                            effective_visits=escalated_visits,
                            completeness=completeness,
                            seki_consecutive_count=new_seki_count,
                            root_winrate=root_winrate,
                            puzzle_id=puzzle_id,
                            prev_ownership=current_ownership,
                            transposition_cache=transposition_cache,
                            board_state=esc_board,
                            puzzle_region=puzzle_region,
                        )
                        # Replace the original child with the escalated one
                        node.children[-1] = esc_child

            # KM-01: After first child, extract reply sequence for simulation
            if not first_child_built:
                first_child_built = True
                first_child_winrate = child.winrate if child.winrate > 0 else (root_winrate or 0.5)
                # Only extract if the first child's subtree is not truncated
                if not child.truncated:
                    cached_reply_sequence = _extract_player_reply_sequence(child)

    # KM-02: Store in transposition cache (board-state based, deep copy)
    if transposition_cache is not None and board_state is not None:
        current_player = player_color if is_player_turn else _opponent_color(player_color)
        pos_hash = board_state.position_hash(current_player)
        transposition_cache[pos_hash] = node.model_copy(deep=True)

    return node


def _check_ownership_convergence(
    prev_ownership: list[list[float]],
    curr_ownership: list[list[float]],
    own_epsilon: float,
) -> bool:
    """Check if ownership values have converged between depths (S1-G1).

    Compares key stones (cells with |ownership| > 0.3) between consecutive
    depth analyses. If the max change among key stones is below own_epsilon,
    ownership has converged and the tree can stop.

    Args:
        prev_ownership: Ownership map from previous depth.
        curr_ownership: Ownership map from current depth.
        own_epsilon: Convergence threshold.

    Returns:
        True if ownership has converged.
    """
    if not prev_ownership or not curr_ownership:
        return False

    # Compare dimensions
    rows_prev = len(prev_ownership)
    rows_curr = len(curr_ownership)
    if rows_prev != rows_curr or rows_prev == 0:
        return False

    max_change = 0.0
    key_stone_count = 0
    for r in range(min(rows_prev, rows_curr)):
        cols = min(len(prev_ownership[r]), len(curr_ownership[r]))
        for c in range(cols):
            prev_val = prev_ownership[r][c]
            curr_val = curr_ownership[r][c]
            # Key stones: cells with significant ownership in either map
            if abs(prev_val) > 0.3 or abs(curr_val) > 0.3:
                key_stone_count += 1
                change = abs(curr_val - prev_val)
                if change > max_change:
                    max_change = change

    if key_stone_count == 0:
        return False

    return max_change < own_epsilon


def _opponent_color(color: str) -> str:
    """Return the opponent's color."""
    return "W" if color.upper() == "B" else "B"


def _compute_max_resolved_depth(tree: SolutionNode, depth: int = 0) -> int:
    """Compute the deepest non-truncated branch in a solution tree (KM-04).

    Recursively traverses the tree, returning the maximum depth reached
    by a branch that completed naturally (not truncated).

    Args:
        tree: Root node of the solution tree.
        depth: Current depth in the recursion (0 at root).

    Returns:
        Maximum resolved depth. 0 if the tree is empty or all truncated.
    """
    if tree.truncated:
        return 0  # Truncated branches don't count

    if not tree.children:
        return depth  # Leaf node = this depth

    max_child_depth = 0
    for child in tree.children:
        child_depth = _compute_max_resolved_depth(child, depth + 1)
        if child_depth > max_child_depth:
            max_child_depth = child_depth

    return max_child_depth


# ---------------------------------------------------------------------------
# Phase 5: SGF Injection
# ---------------------------------------------------------------------------


def inject_solution_into_sgf(
    root_node,
    solution_tree: SolutionNode,
    wrong_moves: list[MoveClassification] | None = None,
    player_color: str = "B",
) -> None:
    """Inject AI solution tree and wrong moves into an SGF tree (DD-5).

    This is the SOLE SGF mutator for AI-Solve. It adds solution
    nodes and wrong-move branches WITHOUT deleting any existing children.

    Additive-only rule: ``set(children_before) ⊆ set(children_after)``.

    Args:
        root_node: SGF root node (sgfmill TreeNode or similar with .children).
        solution_tree: SolutionNode tree to inject.
        wrong_moves: Wrong first-move classifications to add as BM branches.
        player_color: Puzzle player color ('B' or 'W').
    """
    if wrong_moves is None:
        wrong_moves = []

    # Track existing children before injection
    existing_moves = set()
    for child in root_node.children:
        move = _extract_move_from_sgf_node(child, player_color)
        if move:
            existing_moves.add(move)

    # Inject solution tree (correct move + continuations)
    if solution_tree and solution_tree.move_gtp not in existing_moves:
        child_node = _solution_node_to_sgf(solution_tree, root_node, player_color)
        if child_node is not None:
            root_node.children.append(child_node)

    # Inject wrong move branches
    for wm in wrong_moves:
        if wm.move_gtp not in existing_moves:
            wrong_node = _create_sgf_move_node(
                root_node, wm.move_gtp, player_color, comment="Wrong",
            )
            if wrong_node is not None:
                root_node.children.append(wrong_node)


def _extract_move_from_sgf_node(node, player_color: str) -> str | None:
    """Extract GTP move string from an SGF node."""
    prop = "B" if player_color.upper() == "B" else "W"
    if hasattr(node, "get"):
        move = node.get(prop)
        if move is not None:
            return _sgf_to_gtp(move)
    if hasattr(node, "properties"):
        props = node.properties
        if prop in props:
            return _sgf_to_gtp(props[prop][0] if isinstance(props[prop], list) else props[prop])
    return None


def _solution_node_to_sgf(solution_node: SolutionNode, parent, player_color: str):
    """Convert SolutionNode tree to SGF child nodes (recursive).

    Returns a new SGF node to be appended to parent.children.
    """
    color = solution_node.color or player_color
    comment_parts = []
    if solution_node.is_correct:
        comment_parts.append("Correct")
    if solution_node.comment:
        comment_parts.append(solution_node.comment)
    comment = " - ".join(comment_parts) if comment_parts else ""

    new_node = _create_sgf_move_node(parent, solution_node.move_gtp, color, comment)
    if new_node is None:
        return None

    # Recursively add children
    for child_solution in solution_node.children:
        child_sgf = _solution_node_to_sgf(child_solution, new_node, player_color)
        if child_sgf is not None:
            new_node.children.append(child_sgf)

    return new_node


def _create_sgf_move_node(parent, move_gtp: str, color: str, comment: str = ""):
    """Create a new SGF tree node with a move property.

    Returns an SGFNode (same type as parse_sgf produces) so
    that injected nodes are compatible with compose_enriched_sgf(),
    extract_correct_first_move(), and all other tree traversal code.
    """
    sgf_coord = _gtp_to_sgf(move_gtp)
    props: dict[str, list[str]] = {color.upper(): [sgf_coord]}
    if comment:
        props["C"] = [comment]
    node = SGFNode(properties=props)
    node.parent = parent if isinstance(parent, SGFNode) else None
    return node


def _sgf_to_gtp(sgf_coord) -> str:
    """Convert SGF coordinate (e.g. 'cc') to GTP (e.g. 'C3')."""
    if isinstance(sgf_coord, tuple):
        row, col = sgf_coord
        col_letter = chr(ord('A') + col + (1 if col >= 8 else 0))  # skip 'I'
        return f"{col_letter}{row + 1}"
    if isinstance(sgf_coord, str) and len(sgf_coord) == 2:
        col = ord(sgf_coord[0]) - ord('a')
        row = ord(sgf_coord[1]) - ord('a')
        col_letter = chr(ord('A') + col + (1 if col >= 8 else 0))
        return f"{col_letter}{row + 1}"
    return str(sgf_coord)


def _gtp_to_sgf(gtp_move: str) -> str:
    """Convert GTP coordinate (e.g. 'C3') to SGF (e.g. 'cc')."""
    if len(gtp_move) < 2:
        return gtp_move
    col_letter = gtp_move[0].upper()
    col = ord(col_letter) - ord('A')
    if col_letter > 'I':
        col -= 1  # GTP skips 'I'
    row = int(gtp_move[1:]) - 1
    return chr(ord('a') + col) + chr(ord('a') + row)


# ---------------------------------------------------------------------------
# Phase 5b: Goal Inference (S3-G11, DD-8)
# ---------------------------------------------------------------------------


def infer_goal(
    pre_score_lead: float,
    post_score_lead: float,
    ownership: list[list[float]] | None,
    config: AiSolveConfig,
    *,
    ko_type: str = "none",
) -> tuple[str, ConfidenceLevel, str]:
    """Infer the puzzle goal from score delta and ownership data (DD-8, S3-G11).

    Uses score delta as primary signal, ownership as secondary with variance gate.

    Args:
        pre_score_lead: Score lead BEFORE the correct move (root position).
        post_score_lead: Score lead AFTER the correct move.
        ownership: Ownership map from post-move analysis (19x19 grid, -1=W, +1=B).
            Can be None if unavailable.
        config: AiSolveConfig with goal_inference parameters.
        ko_type: Ko context from puzzle metadata ('none', 'direct', 'approach').

    Returns:
        Tuple of (goal, goal_confidence, goal_confidence_reason):
        - goal: 'kill', 'live', 'ko', 'capture', 'unknown'
        - goal_confidence: ConfidenceLevel
        - goal_confidence_reason: str explaining why confidence was set
    """
    goal_config = config.goal_inference
    score_delta = abs(post_score_lead - pre_score_lead)

    # Ko context overrides other inference
    if ko_type in ("direct", "approach"):
        confidence = ConfidenceLevel.HIGH if score_delta >= goal_config.score_delta_ko else ConfidenceLevel.MEDIUM
        reason = "ko_context_high_delta" if confidence == ConfidenceLevel.HIGH else "ko_context_low_delta"
        return "ko", confidence, reason

    # Primary signal: score delta
    if score_delta >= goal_config.score_delta_kill:
        goal = "kill"
        confidence = ConfidenceLevel.HIGH
        reason = "score_delta_kill"
    elif score_delta >= goal_config.score_delta_ko:
        goal = "capture"
        confidence = ConfidenceLevel.MEDIUM
        reason = "score_delta_capture"
    else:
        goal = "live"
        confidence = ConfidenceLevel.MEDIUM
        reason = "score_delta_live"

    # Secondary signal: ownership variance gate
    if ownership is not None:
        # Compute ownership variance for occupied cells
        values = []
        for row in ownership:
            for val in row:
                if abs(val) > goal_config.ownership_threshold:
                    values.append(abs(val))
        if values:
            mean_own = sum(values) / len(values)
            variance = sum((v - mean_own) ** 2 for v in values) / len(values)
            if variance > goal_config.ownership_variance_gate:
                confidence = ConfidenceLevel.LOW
                reason = "ownership_variance"

    return goal, confidence, reason


# ---------------------------------------------------------------------------
# Phase 6: Alternative Discovery
# ---------------------------------------------------------------------------


def discover_alternatives(
    analysis: AnalysisResponse,
    existing_correct_move_gtp: str,
    puzzle_player: str,
    puzzle_id: str,
    config: AiSolveConfig,
    *,
    engine: AnalysisEngine | None = None,
    initial_moves: list[str] | None = None,
    level_slug: str = "intermediate",
    query_budget: QueryBudget | None = None,
    pre_computed_analysis: PositionAnalysis | None = None,
    puzzle_region: frozenset[tuple[int, int]] | None = None,
) -> tuple[list[MoveClassification], bool, str | None]:
    """Find AI alternative correct moves not in the existing solution (DD-7, DD-10).

    Steps:
    1. Classify all candidates (or reuse pre_computed_analysis)
    2. Find TE moves that differ from existing_correct_move_gtp
    3. Check for co-correct detection (three-signal check, DD-7, S1-G14)
    4. Determine human_solution_confidence (DD-10)
    5. Optionally build solution trees for alternatives (S2-G17)

    Args:
        analysis: KataGo AnalysisResponse.
        existing_correct_move_gtp: The existing human correct move.
        puzzle_player: Puzzle player color.
        puzzle_id: Puzzle identifier.
        config: AiSolveConfig.
        engine: Optional engine for building alternative solution trees (S2-G17).
        initial_moves: Initial move sequence for tree building.
        level_slug: Level slug for depth profile selection.
        query_budget: Budget tracker for tree building.
        pre_computed_analysis: If provided, reuse this instead of re-running
            analyze_position_candidates (S-5 fix: avoids redundant engine queries).

    Returns:
        Tuple of (alternative_correct_moves, co_correct_detected, human_solution_confidence).
        human_solution_confidence is None if AI agrees, else 'strong'/'weak'/'losing'.
    """
    from models.solve_result import HumanSolutionConfidence, SolvedMove

    # S-5 fix: reuse pre-computed analysis when available
    if pre_computed_analysis is not None:
        position = pre_computed_analysis
    else:
        # Classify all candidates (only when not pre-computed)
        position = analyze_position_candidates(analysis, puzzle_player, puzzle_id, config)

    # Find the human move's classification
    human_classification = None
    for mc in position.all_classifications:
        if mc.move_gtp.upper() == existing_correct_move_gtp.upper():
            human_classification = mc
            break

    # Determine human_solution_confidence (DD-10)
    human_confidence: str | None = None
    if human_classification is None:
        # Human move not even in candidate list → weak
        human_confidence = HumanSolutionConfidence.WEAK.value
        logger.warning(
            "Puzzle %s: human move %s not found in KataGo candidates",
            puzzle_id, existing_correct_move_gtp,
        )
    elif human_classification.quality != MoveQuality.TE:
        # AI disagrees — determine severity
        alternatives_config = config.alternatives
        if abs(human_classification.delta) >= alternatives_config.losing_threshold:
            human_confidence = HumanSolutionConfidence.LOSING.value
        elif abs(human_classification.delta) >= alternatives_config.disagreement_threshold:
            human_confidence = HumanSolutionConfidence.WEAK.value
        else:
            human_confidence = HumanSolutionConfidence.STRONG.value
    else:
        # AI agrees: human move is correct
        human_confidence = None  # No disagreement

    # Find alternatives (TE moves that are not the existing correct move)
    alternatives: list[MoveClassification] = [
        mc for mc in position.correct_moves
        if mc.move_gtp.upper() != existing_correct_move_gtp.upper()
    ]

    # Co-correct detection (DD-7): three-signal check (S1-G14)
    co_correct_detected = False
    if alternatives and human_classification and human_classification.quality == MoveQuality.TE:
        best_alt = alternatives[0]
        alternatives_config = config.alternatives
        winrate_gap = abs(best_alt.winrate - human_classification.winrate)
        both_te = (best_alt.quality == MoveQuality.TE
                   and human_classification.quality == MoveQuality.TE)
        winrate_gap_ok = winrate_gap < alternatives_config.co_correct_min_gap

        # S1-G14: Third signal — score lead gap
        score_gap = abs(best_alt.score_lead - human_classification.score_lead)
        score_gap_ok = score_gap < alternatives_config.co_correct_score_gap

        if both_te and winrate_gap_ok and score_gap_ok:
            co_correct_detected = True
            logger.info(
                "Puzzle %s: co-correct detected — %s (wr=%.3f, sl=%.1f) and "
                "%s (wr=%.3f, sl=%.1f), wr_gap=%.4f, score_gap=%.1f",
                puzzle_id, existing_correct_move_gtp, human_classification.winrate,
                human_classification.score_lead,
                best_alt.move_gtp, best_alt.winrate, best_alt.score_lead,
                winrate_gap, score_gap,
            )

    # S2-G17 + S2-G13: Build solution trees for alternatives when engine is provided
    # S2-G13: Use parallel execution with split budgets for multi-alternative puzzles
    if engine is not None and alternatives and query_budget is not None:
        _initial = initial_moves or []

        # Split budget across alternatives for parallel execution
        remaining_budget = query_budget.total - query_budget.used
        num_alts = min(len(alternatives), remaining_budget)  # can't build more than budget allows
        if num_alts > 0:
            per_alt_budget = max(1, remaining_budget // num_alts)

            import concurrent.futures

            def _build_alt_tree(alt: MoveClassification, alt_budget: QueryBudget) -> SolvedMove | None:
                """Build a single alternative tree in a thread (S2-G13)."""
                try:
                    alt_tree = build_solution_tree(
                        engine=engine,
                        initial_moves=_initial,
                        correct_move_gtp=alt.move_gtp,
                        player_color=puzzle_player,
                        config=config,
                        level_slug=level_slug,
                        query_budget=alt_budget,
                        puzzle_id=puzzle_id,
                        puzzle_region=puzzle_region,
                    )
                    return SolvedMove(
                        move_gtp=alt.move_gtp,
                        color=puzzle_player,
                        winrate=alt.winrate,
                        confidence=ConfidenceLevel.HIGH if alt.delta <= config.thresholds.t_good else ConfidenceLevel.MEDIUM,
                        solution_tree=alt_tree,
                    )
                except Exception as e:
                    logger.warning(
                        "Puzzle %s: failed to build tree for alternative %s: %s",
                        puzzle_id, alt.move_gtp, e,
                    )
                    return None

            # Create split budgets for each alternative
            alt_budgets = [QueryBudget(total=per_alt_budget) for _ in range(num_alts)]
            alts_to_build = alternatives[:num_alts]

            # S2-G13: Parallel execution using ThreadPoolExecutor
            # build_solution_tree is synchronous, so we parallelize via threads
            with concurrent.futures.ThreadPoolExecutor(max_workers=num_alts) as executor:
                futures = [
                    executor.submit(_build_alt_tree, alt, alt_budgets[i])
                    for i, alt in enumerate(alts_to_build)
                ]
                results = [f.result() for f in concurrent.futures.as_completed(futures)]

            # Aggregate budget usage from split budgets back to parent
            total_used = sum(b.used for b in alt_budgets)
            if total_used > 0 and query_budget.remaining >= total_used:
                query_budget.consume(total_used)
            elif total_used > 0:
                # Consume what we can — split budgets may have used more than parent has
                query_budget.consume(query_budget.remaining)

            # Collect successful results
            for solved in results:
                if solved is not None:
                    position.solved_moves.append(solved)
                    logger.info(
                        f"Puzzle {puzzle_id}: built alternative tree for {solved.move_gtp}")

    return alternatives, co_correct_detected, human_confidence
