"""Clamp detector — detect 2nd-line squeeze play patterns.

A clamp places a stone on the 2nd line between two opponent stones,
squeezing and reducing their liberties. The move is typically a
sacrifice that creates a shortage of liberties.
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


class ClampDetector:
    """Detects clamp (2nd-line squeeze play) patterns."""

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

        board_size = position.board_size
        mx, my = move_xy

        # Check if move is on 2nd line (line 2 from any edge)
        edge_line = _edge_line(mx, my, board_size)
        if edge_line > 2:
            return _no_detection(
                f"Move {top.move} on line {edge_line} (need line 1-2)"
            )

        opponent_color = "W" if position.player_to_move.value == "B" else "B"
        occupied = {(s.x, s.y): s.color.value for s in position.stones}

        # Check for opponent stones on both sides along the edge direction
        # A clamp squeezes between two opponent stones
        opponent_sides = _count_opponent_sides(
            mx, my, opponent_color, occupied, board_size,
        )

        if opponent_sides < 2:
            return _no_detection(
                f"Move {top.move} not between opponent stones "
                f"(sides={opponent_sides})"
            )

        # Clamp signature: typically low policy (squeeze looks odd) + decent winrate
        confidence = 0.65
        if top.policy_prior < 0.15:
            confidence = min(0.85, confidence + 0.10)
        if top.winrate >= 0.7:
            confidence = min(0.85, confidence + 0.05)

        return DetectionResult(
            detected=True,
            confidence=confidence,
            tag_slug="clamp",
            evidence=(
                f"Clamp: {top.move} on line {edge_line}, between {opponent_sides} "
                f"opponent stone directions, policy={top.policy_prior:.3f}"
            ),
        )


def _count_opponent_sides(
    mx: int,
    my: int,
    opponent_color: str,
    occupied: dict[tuple[int, int], str],
    board_size: int,
) -> int:
    """Count how many orthogonal directions have an opponent stone within 2 steps."""
    sides = 0
    for dx, dy in _NEIGHBORS:
        for dist in (1, 2):
            nx, ny = mx + dx * dist, my + dy * dist
            if 0 <= nx < board_size and 0 <= ny < board_size:
                if occupied.get((nx, ny)) == opponent_color:
                    sides += 1
                    break
    return sides


def _edge_line(x: int, y: int, board_size: int) -> int:
    """Return the closest edge line number (1 = edge, 2 = second line)."""
    return min(x + 1, y + 1, board_size - x, board_size - y)


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
        tag_slug="clamp",
        evidence=evidence,
    )
