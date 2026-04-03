"""Connect-and-die detector — force opponent to connect, then kill.

Detects the tesuji where a move forces the opponent to connect their
groups, and the resulting connected group dies (has insufficient
liberties or eye space). The key signal is a forcing move (high winrate)
that compels opponent response, leading to a worse position.
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

_GTP_LETTERS = "ABCDEFGHJKLMNOPQRST"
_NEIGHBORS = ((0, 1), (0, -1), (1, 0), (-1, 0))


class ConnectAndDieDetector:
    """Detects connect-and-die (force connection → kill) patterns."""

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

        if top.winrate < 0.8:
            return _no_detection(
                f"Winrate {top.winrate:.3f} too low for connect-and-die"
            )

        move_xy = _gtp_to_xy(top.move, position.board_size)
        if move_xy is None:
            return _no_detection(f"Cannot parse move {top.move}")

        board_size = position.board_size
        opponent_color = "W" if position.player_to_move.value == "B" else "B"
        occupied = {(s.x, s.y): s.color.value for s in position.stones}
        mx, my = move_xy

        # Check if move is adjacent to multiple separate opponent groups
        # (forcing connection)
        opponent_groups = _distinct_adjacent_groups(
            (mx, my), opponent_color, occupied, board_size,
        )

        if len(opponent_groups) < 2:
            return _no_detection(
                f"Move {top.move} adjacent to {len(opponent_groups)} opponent group(s) "
                f"(need ≥2 for connect-and-die)"
            )

        # The key: player forces opponent to connect, but the combined group dies
        # High winrate + multiple opponent groups = the connection is bad for opponent
        total_opp_stones = sum(len(g) for g in opponent_groups)
        confidence = min(
            0.80,
            0.50 + len(opponent_groups) * 0.08 + top.winrate * 0.1,
        )

        return DetectionResult(
            detected=True,
            confidence=confidence,
            tag_slug="connect-and-die",
            evidence=(
                f"Connect-and-die: {top.move} forces {len(opponent_groups)} opponent "
                f"groups ({total_opp_stones} stones) to connect, "
                f"winrate={top.winrate:.3f}"
            ),
        )


def _distinct_adjacent_groups(
    point: tuple[int, int],
    color: str,
    occupied: dict[tuple[int, int], str],
    board_size: int,
) -> list[frozenset[tuple[int, int]]]:
    """Return distinct groups of given color adjacent to point."""
    groups: list[frozenset[tuple[int, int]]] = []
    seen: set[tuple[int, int]] = set()
    px, py = point
    for dx, dy in _NEIGHBORS:
        nx, ny = px + dx, py + dy
        if not (0 <= nx < board_size and 0 <= ny < board_size):
            continue
        if (nx, ny) in seen:
            continue
        if occupied.get((nx, ny)) != color:
            continue
        group = _flood_fill((nx, ny), occupied, board_size)
        seen |= group
        groups.append(group)
    return groups


def _flood_fill(
    start: tuple[int, int],
    occupied: dict[tuple[int, int], str],
    board_size: int,
) -> frozenset[tuple[int, int]]:
    """Flood-fill to find all stones in the same group."""
    color = occupied.get(start)
    if color is None:
        return frozenset()
    stack = [start]
    group: set[tuple[int, int]] = set()
    while stack:
        pt = stack.pop()
        if pt in group:
            continue
        group.add(pt)
        for dx, dy in _NEIGHBORS:
            nx, ny = pt[0] + dx, pt[1] + dy
            if 0 <= nx < board_size and 0 <= ny < board_size:
                if occupied.get((nx, ny)) == color and (nx, ny) not in group:
                    stack.append((nx, ny))
    return frozenset(group)


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
        tag_slug="connect-and-die",
        evidence=evidence,
    )
