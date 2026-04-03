"""Shape detector — detect common Go shape patterns formed by moves.

Checks for known good-shape patterns (bamboo joint, tiger mouth,
empty triangle, etc.) created by the correct move in conjunction
with existing friendly stones.
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

# Shape patterns: (name, relative offsets of OTHER friendly stones from the move)
# The move itself is at (0, 0). These offsets indicate where friendly stones
# must exist for the shape to be recognized.
_SHAPE_PATTERNS: list[tuple[str, list[tuple[int, int]]]] = [
    # Tiger mouth: stone diagonal + stone orthogonal forming mouth
    ("tiger-mouth", [(1, 0), (0, 1)]),
    ("tiger-mouth-r", [(-1, 0), (0, 1)]),
    ("tiger-mouth-u", [(1, 0), (0, -1)]),
    ("tiger-mouth-ul", [(-1, 0), (0, -1)]),
    # Bamboo joint: two pairs connected diagonally
    ("bamboo-joint", [(1, 1), (0, 1), (1, 0)]),
    # Empty triangle (bad shape - still a shape tag)
    ("empty-triangle", [(1, 0), (0, 1)]),
    # Table shape (4 stones in 2x3 arrangement)
    ("table", [(1, 0), (2, 0), (1, 1)]),
    # Hane (diagonal + adjacent, creating turn)
    ("hane", [(1, 0), (1, 1)]),
    ("hane-r", [(-1, 0), (-1, 1)]),
]


class ShapeDetector:
    """Detects common Go shape patterns formed by the correct move."""

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
        friendly = {
            (s.x, s.y)
            for s in position.stones
            if s.color.value == player_color
        }
        mx, my = move_xy

        # Check each shape pattern
        for shape_name, offsets in _SHAPE_PATTERNS:
            required = {(mx + dx, my + dy) for dx, dy in offsets}
            # All required positions must have friendly stones
            if required <= friendly:
                # Verify all required positions are on the board
                if all(
                    0 <= x < board_size and 0 <= y < board_size
                    for x, y in required
                ):
                    confidence = min(0.80, 0.55 + len(offsets) * 0.08)
                    return DetectionResult(
                        detected=True,
                        confidence=confidence,
                        tag_slug="shape",
                        evidence=(
                            f"Shape '{shape_name}' formed by {top.move} "
                            f"with {len(offsets)} friendly stones"
                        ),
                    )

        return _no_detection(f"No known shape pattern at {top.move}")


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
        tag_slug="shape",
        evidence=evidence,
    )
