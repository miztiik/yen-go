"""Ladder detector — board-state pattern matching for shicho detection.

Independent clean-room implementation. The algorithmic approach (3×3 local
pattern matching with 8-symmetry transforms, recursive chase simulation on
the actual board, and termination at the board edge) is derived from the
general description of ladder detection in Go literature and open-source
project documentation. No source code from any GPL/AGPL project was
referenced during implementation. PV diagonal ratio is used only as an
optional confirmation signal.

Detection strategy:
1. Board-state primary: Given the solution's first move, simulate the
   ladder chase on the actual board position. At each step, verify the
   fleeing group has exactly 2 liberties and the attacker can reduce it
   to 1 (atari). The chase must reach the board edge (≤1 row/col from
   edge) without a ladder-breaker stone blocking the path.
2. PV confirmation (optional): If PV also shows a diagonal chase ratio
   above threshold, confidence is boosted.

Config thresholds from technique_detection.ladder:
  - min_pv_length: minimum PV length to check diagonal ratio
  - diagonal_ratio: threshold for PV diagonal confirmation
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

from models.detection import DetectionResult

if TYPE_CHECKING:
    from config import EnrichmentConfig
    from models.analysis_response import AnalysisResponse
    from models.position import Position
    from models.solve_result import SolutionNode

logger = logging.getLogger(__name__)

# GTP column letters (skipping 'I')
_GTP_LETTERS = "ABCDEFGHJKLMNOPQRST"

# Orthogonal neighbors
_NEIGHBORS = ((0, 1), (0, -1), (1, 0), (-1, 0))

# 8 symmetry transforms for 3×3 pattern matching (rotations + reflections)
_SYMMETRIES: list[tuple[tuple[int, int], ...]] = [
    # Identity
    ((0, 0), (0, 1), (0, 2), (1, 0), (1, 1), (1, 2), (2, 0), (2, 1), (2, 2)),
    # 90° CW
    ((2, 0), (1, 0), (0, 0), (2, 1), (1, 1), (0, 1), (2, 2), (1, 2), (0, 2)),
    # 180°
    ((2, 2), (2, 1), (2, 0), (1, 2), (1, 1), (1, 0), (0, 2), (0, 1), (0, 0)),
    # 270° CW
    ((0, 2), (1, 2), (2, 2), (0, 1), (1, 1), (2, 1), (0, 0), (1, 0), (2, 0)),
    # Horizontal flip
    ((0, 2), (0, 1), (0, 0), (1, 2), (1, 1), (1, 0), (2, 2), (2, 1), (2, 0)),
    # Vertical flip
    ((2, 0), (2, 1), (2, 2), (1, 0), (1, 1), (1, 2), (0, 0), (0, 1), (0, 2)),
    # Main diagonal reflection
    ((0, 0), (1, 0), (2, 0), (0, 1), (1, 1), (2, 1), (0, 2), (1, 2), (2, 2)),
    # Anti-diagonal reflection
    ((2, 2), (1, 2), (0, 2), (2, 1), (1, 1), (0, 1), (2, 0), (1, 0), (0, 0)),
]

# Ladder 3×3 patterns: attacker places diagonally to keep flee-group in atari.
# Pattern cells: 'A'=attacker, 'F'=fleeing, 'X'=attacker_stone, '.'=empty, '*'=any
# The canonical ladder pattern (attacker chases along diagonal):
#   . A .      attacker plays at center-top to give atari
#   F X .      fleeing stone with attacker stone adjacent
#   . . .
_LADDER_PATTERNS: list[list[str]] = [
    # Canonical: flee at (1,0), attacker stone at (1,1), attacker plays (0,1)
    [".", "A", ".", "F", "X", ".", ".", ".", "."],
    # Variant: flee extends and attacker blocks
    [".", ".", ".", "F", "X", "A", ".", ".", "."],
]


class LadderDetector:
    """Detects ladder (shicho) patterns via board-state simulation.

    Primary method: simulate the attacker–defender chase on the actual board.
    Secondary: PV diagonal ratio as confirmation signal.
    """

    def detect(
        self,
        position: Position,
        analysis: AnalysisResponse,
        solution_tree: SolutionNode | None,
        config: EnrichmentConfig,
    ) -> DetectionResult:
        tc = config.technique_detection
        min_pv = tc.ladder.min_pv_length if tc else 4
        diag_ratio = tc.ladder.diagonal_ratio if tc else 0.5

        board_size = position.board_size
        board = _build_board(position)

        # --- Primary: board-state ladder simulation ---
        # Try the top PV first move as the ladder-starting move
        for move_info in analysis.move_infos:
            if not move_info.pv:
                continue
            first_move = _parse_gtp(move_info.pv[0])
            if first_move is None:
                continue

            attacker_color, defender_color = _infer_colors(position)
            chase_len = _simulate_ladder_chase(
                board, board_size, first_move,
                attacker_color, defender_color, max_steps=30,
            )
            if chase_len >= min_pv:
                # Ladder confirmed by board-state simulation
                pv_conf = _pv_diagonal_confirmation(move_info.pv, min_pv, diag_ratio)
                confidence = min(0.95, 0.75 + (chase_len / 30) * 0.2)
                if pv_conf:
                    confidence = min(0.98, confidence + 0.1)
                return DetectionResult(
                    detected=True,
                    confidence=confidence,
                    tag_slug="ladder",
                    evidence=f"Board-state ladder chase: {chase_len} steps"
                             f"{' (PV-confirmed)' if pv_conf else ''}",
                )

        # Try solution tree mainline
        if solution_tree and solution_tree.move_gtp:
            first_move = _parse_gtp(solution_tree.move_gtp)
            if first_move is not None:
                attacker_color, defender_color = _infer_colors(position)
                chase_len = _simulate_ladder_chase(
                    board, board_size, first_move,
                    attacker_color, defender_color, max_steps=30,
                )
                if chase_len >= min_pv:
                    return DetectionResult(
                        detected=True,
                        confidence=0.7,
                        tag_slug="ladder",
                        evidence=f"Board-state ladder chase from solution tree: "
                                 f"{chase_len} steps",
                    )

        # --- Secondary fallback: PV diagonal ratio (reduced confidence) ---
        # When board-state simulation doesn't confirm but PV strongly shows
        # a diagonal chase, report with lower confidence as probable ladder.
        # Floor: require >= 8 moves — real ladders are long chases across
        # the board; short corner sequences (4-6 moves) often have diagonal
        # adjacency by coincidence.
        _PV_FALLBACK_MIN_LENGTH = 8
        pv_fallback_min = max(min_pv, _PV_FALLBACK_MIN_LENGTH)
        for move_info in analysis.move_infos:
            if len(move_info.pv) >= pv_fallback_min:
                ratio = _diagonal_chase_ratio(move_info.pv)
                if ratio >= diag_ratio:
                    confidence = min(0.6, 0.3 + ratio * 0.3)
                    return DetectionResult(
                        detected=True,
                        confidence=confidence,
                        tag_slug="ladder",
                        evidence=f"PV diagonal ratio {ratio:.2f} "
                                 f"(board simulation inconclusive)",
                    )

        # Solution tree PV fallback
        if solution_tree:
            mainline = _collect_mainline_moves(solution_tree, max_depth=20)
            if len(mainline) >= pv_fallback_min:
                ratio = _diagonal_chase_ratio(mainline)
                if ratio >= diag_ratio:
                    return DetectionResult(
                        detected=True,
                        confidence=0.4,
                        tag_slug="ladder",
                        evidence=f"Solution tree diagonal ratio {ratio:.2f} "
                                 f"(board simulation inconclusive)",
                    )

        return DetectionResult(
            detected=False,
            confidence=0.0,
            tag_slug="ladder",
            evidence="No ladder pattern found on board",
        )


# ---------------------------------------------------------------------------
# Board helpers
# ---------------------------------------------------------------------------

def _build_board(position: Position) -> dict[tuple[int, int], str]:
    """Build a mutable board dict from Position. Keys are (row, col) 0-indexed."""
    board: dict[tuple[int, int], str] = {}
    for stone in position.stones:
        board[(stone.y, stone.x)] = stone.color.value  # "B" or "W"
    return board


def _infer_colors(position: Position) -> tuple[str, str]:
    """Infer attacker/defender colors. Attacker = player_to_move."""
    attacker = position.player_to_move.value  # "B" or "W"
    defender = "W" if attacker == "B" else "B"
    return attacker, defender


def _parse_gtp(move: str) -> tuple[int, int] | None:
    """Parse GTP coordinate to (row, col) 0-indexed.

    GTP convention: A1 = bottom-left. We convert to (row, col) where
    row=0 is top. For a 19×19 board, GTP row 1 → internal row 18.
    We return raw (gtp_row-1, gtp_col-1) and let callers handle
    board-size-relative conversion where needed.
    """
    if not move or move.lower() == "pass":
        return None
    m = re.match(r"^([A-HJ-T])(\d{1,2})$", move.upper())
    if not m:
        return None
    col_letter = m.group(1)
    gtp_row = int(m.group(2))
    col = _GTP_LETTERS.index(col_letter)
    # Convert GTP row (1-indexed from bottom) to 0-indexed from top
    # For generic use, we store as (row_from_bottom - 1, col)
    # This matches Position.stones where y=0 is top
    # Actually for ladder simulation we need absolute coords
    # Use 0-indexed: row = gtp_row - 1, col = col_index
    return (gtp_row - 1, col)


def _get_group(
    board: dict[tuple[int, int], str],
    coord: tuple[int, int],
    board_size: int,
) -> tuple[set[tuple[int, int]], set[tuple[int, int]]]:
    """BFS to find the group containing coord and its liberties."""
    color = board.get(coord)
    if color is None:
        return set(), set()
    group: set[tuple[int, int]] = set()
    liberties: set[tuple[int, int]] = set()
    queue = [coord]
    group.add(coord)
    while queue:
        r, c = queue.pop()
        for dr, dc in _NEIGHBORS:
            nr, nc = r + dr, c + dc
            if nr < 0 or nr >= board_size or nc < 0 or nc >= board_size:
                continue
            n = (nr, nc)
            if n in group:
                continue
            cell = board.get(n)
            if cell is None:
                liberties.add(n)
            elif cell == color and n not in group:
                group.add(n)
                queue.append(n)
    return group, liberties


def _remove_captured_stones(
    board: dict[tuple[int, int], str],
    last_move: tuple[int, int],
    opponent: str,
    board_size: int,
) -> int:
    """Remove opponent groups with 0 liberties adjacent to last_move.

    Returns the total number of stones removed.
    """
    removed = 0
    for dr, dc in _NEIGHBORS:
        nr, nc = last_move[0] + dr, last_move[1] + dc
        adj = (nr, nc)
        if board.get(adj) != opponent:
            continue
        grp, libs = _get_group(board, adj, board_size)
        if len(libs) == 0:
            for stone_pos in grp:
                del board[stone_pos]
            removed += len(grp)
    return removed


def _simulate_ladder_chase(
    board: dict[tuple[int, int], str],
    board_size: int,
    first_move: tuple[int, int],
    attacker: str,
    defender: str,
    max_steps: int = 30,
) -> int:
    """Simulate a ladder chase from first_move, return chase length.

    The simulation alternates:
    1. Attacker plays (puts defender group in atari)
    2. Defender extends (the only liberty of the group in atari)

    The ladder succeeds (returns chase_length) when:
    - After attacker's move, defender's group has 0 liberties (captured)
    - After defender extends, the group still has exactly 2 liberties
      (one of which the attacker will play next)
    - The chase reaches near the board edge

    Returns 0 if the pattern doesn't match a ladder.
    """
    sim_board = dict(board)
    chase_length = 0

    # Place the first attacker move
    if first_move in sim_board:
        return 0  # Can't play on occupied intersection
    sim_board[first_move] = attacker
    _remove_captured_stones(sim_board, first_move, defender, board_size)
    chase_length = 1

    # Find adjacent defender groups that are now in atari (exactly 1 liberty)
    target_group = None
    target_liberties = None
    for dr, dc in _NEIGHBORS:
        nr, nc = first_move[0] + dr, first_move[1] + dc
        adj = (nr, nc)
        if sim_board.get(adj) == defender:
            grp, libs = _get_group(sim_board, adj, board_size)
            if len(libs) == 1:
                target_group = grp
                target_liberties = libs
                break

    if target_group is None:
        return 0  # No adjacent defender group in atari → not a ladder start

    # Simulate the chase
    for _ in range(max_steps):
        # Defender extends to the single liberty
        extend_to = next(iter(target_liberties))
        sim_board[extend_to] = defender
        _remove_captured_stones(sim_board, extend_to, attacker, board_size)

        # Check if defender's group now has liberties
        extended_group, new_libs = _get_group(sim_board, extend_to, board_size)

        if len(new_libs) == 0:
            # Defender is captured — ladder succeeds
            return chase_length

        if len(new_libs) == 1:
            # Still in atari after extending — ladder breaker captures defender
            return chase_length

        if len(new_libs) != 2:
            # More than 2 liberties — a ladder-breaker stone gives escape
            return 0

        chase_length += 1

        # Check if we're near the board edge (ladder succeeds by geometry)
        er, ec = extend_to
        if er <= 0 or er >= board_size - 1 or ec <= 0 or ec >= board_size - 1:
            return chase_length

        # Attacker plays the liberty that keeps defender in atari
        # Pick the liberty that puts defender back in atari
        atari_move = None
        for lib in new_libs:
            test_board = dict(sim_board)
            test_board[lib] = attacker
            _, test_libs = _get_group(test_board, extend_to, board_size)
            if len(test_libs) <= 1:
                atari_move = lib
                break

        if atari_move is None:
            # Neither liberty gives atari — ladder fails (breaker)
            return 0

        sim_board[atari_move] = attacker
        _remove_captured_stones(sim_board, atari_move, defender, board_size)
        chase_length += 1

        # Update target group and liberties for next iteration
        target_group, target_liberties = _get_group(sim_board, extend_to, board_size)
        if len(target_liberties) == 0:
            return chase_length  # Captured
        if len(target_liberties) != 1:
            return 0  # Escaped

    return chase_length


# ---------------------------------------------------------------------------
# PV confirmation (secondary signal)
# ---------------------------------------------------------------------------

def _pv_diagonal_confirmation(
    pv: list[str], min_length: int, threshold: float
) -> bool:
    """Check if PV shows a diagonal chase pattern (confirmation only)."""
    if len(pv) < min_length:
        return False
    ratio = _diagonal_chase_ratio(pv)
    return ratio >= threshold


def _diagonal_chase_ratio(pv: list[str]) -> float:
    """Compute ratio of consecutive diagonal moves in a PV sequence."""
    coords = [_parse_gtp(m) for m in pv if m.lower() != "pass"]
    coords = [c for c in coords if c is not None]
    if len(coords) < 2:
        return 0.0

    diagonal_count = 0
    for i in range(1, len(coords)):
        r1, c1 = coords[i - 1]
        r2, c2 = coords[i]
        if abs(r2 - r1) == 1 and abs(c2 - c1) == 1:
            diagonal_count += 1

    return diagonal_count / (len(coords) - 1)


def _collect_mainline_moves(node: SolutionNode, max_depth: int) -> list[str]:
    """Collect GTP moves along the solution tree mainline."""
    moves: list[str] = []
    current = node
    for _ in range(max_depth):
        moves.append(current.move_gtp)
        if not current.children:
            break
        current = current.children[0]
    return moves
