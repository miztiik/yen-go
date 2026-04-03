"""Cutting detector — detect moves that separate opponent groups.

A cutting move places a stone that splits opponent stones into two or
more isolated groups. This is the inverse of connection — the target
is the opponent's connectivity.
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


class CuttingDetector:
    """Detects cutting moves that separate opponent groups."""

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
        opponent_color = "W" if player_color == "B" else "B"
        occupied = {(s.x, s.y): s.color.value for s in position.stones}
        board_size = position.board_size

        # Count opponent groups before and after the move
        groups_before = _count_groups(occupied, opponent_color, board_size)

        occupied_after = dict(occupied)
        occupied_after[move_xy] = player_color
        groups_after = _count_groups(occupied_after, opponent_color, board_size)

        if groups_after > groups_before:
            return DetectionResult(
                detected=True,
                confidence=min(0.90, 0.65 + 0.1 * (groups_after - groups_before)),
                tag_slug="cutting",
                evidence=(
                    f"Move {top.move} splits opponent from "
                    f"{groups_before} to {groups_after} group(s)"
                ),
            )

        return _no_detection(
            f"Opponent groups unchanged ({groups_before} → {groups_after})"
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


def _count_groups(
    occupied: dict[tuple[int, int], str],
    color: str,
    board_size: int,
) -> int:
    """Count the number of separate groups of *color*."""
    visited: set[tuple[int, int]] = set()
    count = 0
    for coord, c in occupied.items():
        if c != color or coord in visited:
            continue
        count += 1
        queue = [coord]
        visited.add(coord)
        while queue:
            cx, cy = queue.pop()
            for dx, dy in _NEIGHBORS:
                nx, ny = cx + dx, cy + dy
                nc = (nx, ny)
                if (
                    0 <= nx < board_size
                    and 0 <= ny < board_size
                    and nc not in visited
                    and occupied.get(nc) == color
                ):
                    visited.add(nc)
                    queue.append(nc)
    return count


def _no_detection(evidence: str) -> DetectionResult:
    return DetectionResult(
        detected=False,
        confidence=0.0,
        tag_slug="cutting",
        evidence=evidence,
    )
