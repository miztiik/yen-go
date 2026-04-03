"""Vital-point detector — detect moves at shared liberties of critical groups.

A vital point move is placed at a position that is adjacent to both
the player's and opponent's groups, making it a crux point in the
local fight. Detection checks proximity to both attacking and
defending groups.
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


class VitalPointDetector:
    """Detects vital-point moves (shared liberty of attacking/defending groups)."""

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
        player_color = position.player_to_move.value
        opponent_color = "W" if player_color == "B" else "B"
        occupied = {(s.x, s.y): s.color.value for s in position.stones}
        mx, my = move_xy

        # Count adjacent friendly and opponent stones
        player_adj = 0
        opponent_adj = 0
        for dx, dy in _NEIGHBORS:
            nx, ny = mx + dx, my + dy
            if 0 <= nx < board_size and 0 <= ny < board_size:
                c = occupied.get((nx, ny))
                if c == player_color:
                    player_adj += 1
                elif c == opponent_color:
                    opponent_adj += 1

        # Vital point: adjacent to BOTH player and opponent groups
        if player_adj >= 1 and opponent_adj >= 1:
            # Higher confidence when surrounded from both sides
            total_contact = player_adj + opponent_adj
            confidence = min(0.90, 0.55 + total_contact * 0.08)

            # Boost if move has high winrate impact
            if top.winrate >= 0.8:
                confidence = min(0.90, confidence + 0.05)

            return DetectionResult(
                detected=True,
                confidence=confidence,
                tag_slug="vital-point",
                evidence=(
                    f"Vital point: {top.move} adjacent to {player_adj} friendly "
                    f"and {opponent_adj} opponent stones"
                ),
            )

        return _no_detection(
            f"Move {top.move}: player_adj={player_adj}, opponent_adj={opponent_adj} "
            f"(need both >= 1)"
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


def _no_detection(evidence: str) -> DetectionResult:
    return DetectionResult(
        detected=False,
        confidence=0.0,
        tag_slug="vital-point",
        evidence=evidence,
    )
