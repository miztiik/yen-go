"""Double-atari detector — detect moves that put two groups in atari.

A double atari occurs when a single move reduces two separate opponent
groups to exactly 1 liberty each. Detection simulates placing the
correct move and checks adjacent opponent groups' liberty counts.
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


class DoubleAtariDetector:
    """Detects double-atari patterns."""

    def detect(
        self,
        position: Position,
        analysis: AnalysisResponse,
        solution_tree: SolutionNode | None,
        config: EnrichmentConfig,
    ) -> DetectionResult:
        tc = config.technique_detection
        wr_thresh = tc.double_atari.winrate_threshold if tc else 0.8

        top = analysis.top_move
        if not top:
            return _no_detection("No top move available")

        move_xy = _gtp_to_xy(top.move, position.board_size)
        if move_xy is None:
            return _no_detection(f"Cannot parse move {top.move}")

        if top.winrate < wr_thresh:
            return _no_detection(
                f"Winrate {top.winrate:.3f} < threshold {wr_thresh}"
            )

        board_size = position.board_size
        player_color = position.player_to_move.value
        opponent_color = "W" if player_color == "B" else "B"

        # Build occupied map and simulate placing the stone
        occupied = {(s.x, s.y): s.color.value for s in position.stones}
        occupied[move_xy] = player_color  # simulate the move

        # Find distinct opponent groups adjacent to the move
        atari_groups = _adjacent_opponent_groups_in_atari(
            move_xy, opponent_color, occupied, board_size,
        )

        if len(atari_groups) >= 2:
            confidence = min(0.95, 0.75 + 0.05 * len(atari_groups))
            return DetectionResult(
                detected=True,
                confidence=confidence,
                tag_slug="double-atari",
                evidence=(
                    f"Move {top.move} puts {len(atari_groups)} opponent groups "
                    f"in atari (1 liberty each)"
                ),
            )

        return _no_detection(
            f"Move {top.move} puts {len(atari_groups)} group(s) in atari (need 2+)"
        )


def _adjacent_opponent_groups_in_atari(
    point: tuple[int, int],
    opponent_color: str,
    occupied: dict[tuple[int, int], str],
    board_size: int,
) -> list[frozenset[tuple[int, int]]]:
    """Find distinct opponent groups adjacent to *point* that have exactly 1 liberty."""
    groups: list[frozenset[tuple[int, int]]] = []
    seen: set[tuple[int, int]] = set()
    px, py = point
    for dx, dy in _NEIGHBORS:
        nx, ny = px + dx, py + dy
        if nx < 0 or nx >= board_size or ny < 0 or ny >= board_size:
            continue
        nc = (nx, ny)
        if nc in seen or occupied.get(nc) != opponent_color:
            continue
        # BFS to find the group and count liberties
        group: set[tuple[int, int]] = set()
        liberties: set[tuple[int, int]] = set()
        queue = [nc]
        group.add(nc)
        while queue:
            cx, cy = queue.pop()
            for ddx, ddy in _NEIGHBORS:
                nnx, nny = cx + ddx, cy + ddy
                nn = (nnx, nny)
                if nnx < 0 or nnx >= board_size or nny < 0 or nny >= board_size:
                    continue
                if nn not in occupied:
                    liberties.add(nn)
                elif occupied[nn] == opponent_color and nn not in group:
                    group.add(nn)
                    queue.append(nn)
        seen |= group
        if len(liberties) == 1:
            groups.append(frozenset(group))
    return groups


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


def _no_detection(evidence: str) -> DetectionResult:
    return DetectionResult(
        detected=False,
        confidence=0.0,
        tag_slug="double-atari",
        evidence=evidence,
    )
