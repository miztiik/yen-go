"""Connection detector — detect moves that connect friendly groups.

A connection move places a stone that joins two or more previously
separate friendly groups into one. Detection checks whether the
correct move point is adjacent to 2+ distinct friendly groups.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from models.detection import DetectionResult

if TYPE_CHECKING:
    from config import EnrichmentConfig
    from models.analysis_response import AnalysisResponse
    from models.position import Position
    from models.solve_result import SolutionNode

logger = logging.getLogger(__name__)

_NEIGHBORS = ((0, 1), (0, -1), (1, 0), (-1, 0))
_GTP_LETTERS = "ABCDEFGHJKLMNOPQRST"


class ConnectionDetector:
    """Detects connection moves that join friendly groups."""

    def detect(
        self,
        position: Position,
        analysis: AnalysisResponse,
        solution_tree: SolutionNode | None,
        config: EnrichmentConfig,
    ) -> DetectionResult:
        top = analysis.top_move
        if not top:
            return _no_detection("No top move available")

        move_xy = _gtp_to_xy(top.move, position.board_size)
        if move_xy is None:
            return _no_detection(f"Cannot parse move {top.move}")

        player_color = position.player_to_move.value
        occupied = {(s.x, s.y): s.color.value for s in position.stones}
        board_size = position.board_size

        # Find distinct friendly groups adjacent to the move point
        adjacent_groups = _distinct_adjacent_groups(
            move_xy, player_color, occupied, board_size,
        )

        if len(adjacent_groups) >= 2:
            return DetectionResult(
                detected=True,
                confidence=min(0.90, 0.65 + 0.1 * len(adjacent_groups)),
                tag_slug="connection",
                evidence=f"Move {top.move} connects {len(adjacent_groups)} groups",
            )

        return _no_detection(
            f"Move {top.move} adjacent to {len(adjacent_groups)} friendly group(s)"
        )


def _gtp_to_xy(gtp: str, board_size: int) -> tuple[int, int] | None:
    """Convert GTP coord to (x, y) 0-indexed."""
    if not gtp or gtp.lower() == "pass":
        return None
    gtp = gtp.upper()
    if len(gtp) < 2 or gtp[0] not in _GTP_LETTERS:
        return None
    try:
        col = _GTP_LETTERS.index(gtp[0])
        row = int(gtp[1:])
    except (ValueError, IndexError):
        return None
    x = col
    y = board_size - row
    if x < 0 or x >= board_size or y < 0 or y >= board_size:
        return None
    return (x, y)


def _distinct_adjacent_groups(
    point: tuple[int, int],
    color: str,
    occupied: dict[tuple[int, int], str],
    board_size: int,
) -> list[frozenset[tuple[int, int]]]:
    """Return list of distinct friendly groups adjacent to *point*."""
    groups: list[frozenset[tuple[int, int]]] = []
    seen: set[tuple[int, int]] = set()
    px, py = point
    for dx, dy in _NEIGHBORS:
        nx, ny = px + dx, py + dy
        if nx < 0 or nx >= board_size or ny < 0 or ny >= board_size:
            continue
        nc = (nx, ny)
        if nc in seen or occupied.get(nc) != color:
            continue
        # BFS to find the group
        group: set[tuple[int, int]] = set()
        queue = [nc]
        group.add(nc)
        while queue:
            cx, cy = queue.pop()
            for ddx, ddy in _NEIGHBORS:
                nnx, nny = cx + ddx, cy + ddy
                nn = (nnx, nny)
                if (
                    0 <= nnx < board_size
                    and 0 <= nny < board_size
                    and nn not in group
                    and occupied.get(nn) == color
                ):
                    group.add(nn)
                    queue.append(nn)
        seen |= group
        groups.append(frozenset(group))
    return groups


def _no_detection(evidence: str) -> DetectionResult:
    return DetectionResult(
        detected=False,
        confidence=0.0,
        tag_slug="connection",
        evidence=evidence,
    )
