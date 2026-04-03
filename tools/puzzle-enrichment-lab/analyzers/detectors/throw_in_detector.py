"""Throw-in detector — detect sacrifice moves inside opponent territory.

A throw-in places a stone on the edge (1st/2nd line) adjacent to opponent
stones. The move looks suicidal (low policy) but reduces opponent liberties
and leads to a favorable outcome (high winrate).

Config: technique_detection.throw_in.edge_lines (default 2)
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


class ThrowInDetector:
    """Detects throw-in (sacrifice at edge) patterns."""

    def detect(
        self,
        position: Position,
        analysis: AnalysisResponse,
        solution_tree: SolutionNode | None,
        config: EnrichmentConfig,
    ) -> DetectionResult:
        tc = config.technique_detection
        edge_lines = tc.throw_in.edge_lines if tc else 2

        top = analysis.top_move
        if not top:
            return _no_detection("No top move available")

        move_xy = _gtp_to_xy(top.move, position.board_size)
        if move_xy is None:
            return _no_detection(f"Cannot parse move {top.move}")

        board_size = position.board_size
        mx, my = move_xy

        # Check if move is on an edge line
        if not _is_edge(mx, my, board_size, edge_lines):
            return _no_detection(
                f"Move {top.move} not on edge (lines 1-{edge_lines})"
            )

        # Check if move is adjacent to opponent stones
        opponent_color = "W" if position.player_to_move.value == "B" else "B"
        occupied = {(s.x, s.y): s.color.value for s in position.stones}

        adj_opponent = 0
        for dx, dy in _NEIGHBORS:
            nx, ny = mx + dx, my + dy
            if 0 <= nx < board_size and 0 <= ny < board_size:
                if occupied.get((nx, ny)) == opponent_color:
                    adj_opponent += 1

        if adj_opponent == 0:
            return _no_detection(f"Move {top.move} not adjacent to opponent stones")

        # Throw-in signature: low policy (suicidal look) + high winrate
        if top.policy_prior > 0.15:
            return _no_detection(
                f"Policy {top.policy_prior:.3f} too high for throw-in"
            )

        if top.winrate < 0.7:
            return _no_detection(
                f"Winrate {top.winrate:.3f} too low for throw-in"
            )

        confidence = min(0.90, 0.60 + (1.0 - top.policy_prior) * 0.2 + adj_opponent * 0.05)
        return DetectionResult(
            detected=True,
            confidence=confidence,
            tag_slug="throw-in",
            evidence=(
                f"Edge sacrifice: move={top.move}, line={_edge_line(mx, my, board_size)}, "
                f"adj_opponent={adj_opponent}, policy={top.policy_prior:.3f}, "
                f"winrate={top.winrate:.3f}"
            ),
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


def _edge_line(x: int, y: int, board_size: int) -> int:
    """Return the closest edge line number (1 = edge, 2 = second line, etc.)."""
    return min(x + 1, y + 1, board_size - x, board_size - y)


def _is_edge(x: int, y: int, board_size: int, max_line: int) -> bool:
    """Return True if (x, y) is on line 1 through *max_line*."""
    return _edge_line(x, y, board_size) <= max_line


def _no_detection(evidence: str) -> DetectionResult:
    return DetectionResult(
        detected=False,
        confidence=0.0,
        tag_slug="throw-in",
        evidence=evidence,
    )
