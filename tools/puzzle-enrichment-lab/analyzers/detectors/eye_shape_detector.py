"""Eye-shape detector — detect moves that create or destroy eye shapes.

Checks whether the correct move affects eye formation by looking at
ownership shifts (alive/dead transitions) in the vicinity of the move.
An eye-shape move typically places a stone that either:
- Creates an eye for the player's group (gives life)
- Destroys an opponent's potential eye (kills)
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


class EyeShapeDetector:
    """Detects moves that create or destroy eye shapes."""

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

        # Check if move point is surrounded by same-color stones (eye creation)
        # or opponent stones (eye destruction / false-eye creation)
        player_adj = 0
        opponent_adj = 0
        empty_adj = 0
        total = 0
        for dx, dy in _NEIGHBORS:
            nx, ny = mx + dx, my + dy
            if 0 <= nx < board_size and 0 <= ny < board_size:
                total += 1
                c = occupied.get((nx, ny))
                if c == player_color:
                    player_adj += 1
                elif c == opponent_color:
                    opponent_adj += 1
                else:
                    empty_adj += 1

        # Eye creation: move surrounded mostly by own stones
        # This fills an eye-vital-point or shapes around eye space
        if player_adj >= 2 and empty_adj <= 1:
            # Check ownership shift for confirmation
            if _has_ownership_shift(analysis):
                return DetectionResult(
                    detected=True,
                    confidence=min(0.85, 0.60 + player_adj * 0.08),
                    tag_slug="eye-shape",
                    evidence=(
                        f"Eye creation: {top.move} near {player_adj} friendly stones, "
                        f"ownership shift detected"
                    ),
                )

        # Eye destruction: move inside opponent's potential eye space
        if opponent_adj >= 3:
            if top.winrate >= 0.7:
                return DetectionResult(
                    detected=True,
                    confidence=min(0.85, 0.55 + opponent_adj * 0.08 + top.winrate * 0.1),
                    tag_slug="eye-shape",
                    evidence=(
                        f"Eye destruction: {top.move} surrounded by {opponent_adj} "
                        f"opponent stones, winrate={top.winrate:.3f}"
                    ),
                )

        return _no_detection(
            f"Move {top.move}: player_adj={player_adj}, opponent_adj={opponent_adj}"
        )


def _has_ownership_shift(analysis: AnalysisResponse) -> bool:
    """Check if top two moves cause significant ownership difference."""
    if len(analysis.move_infos) < 2:
        return False
    top = analysis.move_infos[0]
    second = analysis.move_infos[1]
    if not top.ownership or not second.ownership:
        return True  # Assume shift if no ownership data (benefit of doubt)
    flat_a = [v for row in top.ownership for v in row]
    flat_b = [v for row in second.ownership for v in row]
    if len(flat_a) != len(flat_b) or not flat_a:
        return False
    total = sum(abs(a - b) for a, b in zip(flat_a, flat_b, strict=False))
    avg_diff = total / len(flat_a)
    return avg_diff > 0.2


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
        tag_slug="eye-shape",
        evidence=evidence,
    )
