"""Dead-shapes detector — detect known killable shape patterns.

Checks for known dead shape formations (bulky five, L-shape, etc.)
in the vicinity of the correct move. Uses pattern matching against
the local stone configuration around the move point.
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

# Known dead shapes as relative coordinate sets (opponent stones).
# Each pattern is a frozenset of (dx, dy) offsets from a reference point.
# These represent internal shapes that cannot make two eyes.
_DEAD_SHAPE_PATTERNS: list[tuple[str, list[tuple[int, int]]]] = [
    # Straight four (1x4 internal space)
    ("straight-four", [(0, 0), (1, 0), (2, 0), (3, 0)]),
    # L-shape (bent four variant)
    ("L-shape", [(0, 0), (1, 0), (2, 0), (2, 1)]),
    ("L-shape-r", [(0, 0), (1, 0), (2, 0), (2, -1)]),
    # Bulky five (2x3 minus corner)
    ("bulky-five", [(0, 0), (1, 0), (2, 0), (0, 1), (1, 1)]),
    # T-shape
    ("T-shape", [(0, 0), (1, 0), (2, 0), (1, 1)]),
    # Square four (2x2)
    ("square-four", [(0, 0), (1, 0), (0, 1), (1, 1)]),
]


class DeadShapesDetector:
    """Detects known dead (killable) shape patterns near the correct move."""

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

        opponent_color = "W" if position.player_to_move.value == "B" else "B"
        {(s.x, s.y): s.color.value for s in position.stones}
        mx, my = move_xy

        # Collect opponent stones in a local window around the move
        search_radius = 4
        local_opponent: set[tuple[int, int]] = set()
        for s in position.stones:
            if s.color.value == opponent_color:
                if abs(s.x - mx) <= search_radius and abs(s.y - my) <= search_radius:
                    local_opponent.add((s.x, s.y))

        if len(local_opponent) < 3:
            return _no_detection(
                f"Only {len(local_opponent)} opponent stones near {top.move}"
            )

        # Try matching each dead shape pattern against local opponent stones
        for shape_name, offsets in _DEAD_SHAPE_PATTERNS:
            if _pattern_matches_anywhere(offsets, local_opponent):
                confidence = min(0.85, 0.60 + len(offsets) * 0.04)
                return DetectionResult(
                    detected=True,
                    confidence=confidence,
                    tag_slug="dead-shapes",
                    evidence=(
                        f"Dead shape '{shape_name}' found near {top.move} "
                        f"({len(local_opponent)} opponent stones in area)"
                    ),
                )

        return _no_detection(
            f"No known dead shape near {top.move} ({len(local_opponent)} opponent stones)"
        )


def _pattern_matches_anywhere(
    offsets: list[tuple[int, int]],
    stones: set[tuple[int, int]],
) -> bool:
    """Check if pattern (as relative offsets) matches against stone set at any anchor."""
    for sx, sy in stones:
        # Try using this stone as the anchor for offset (0, 0)
        # Check all 4 rotations
        for rotation in range(4):
            rotated = _rotate_offsets(offsets, rotation)
            translated = {(sx + dx, sy + dy) for dx, dy in rotated}
            if translated <= stones:
                return True
    return False


def _rotate_offsets(
    offsets: list[tuple[int, int]], rotation: int
) -> list[tuple[int, int]]:
    """Rotate offsets by 0/90/180/270 degrees."""
    result = offsets
    for _ in range(rotation % 4):
        result = [(-dy, dx) for dx, dy in result]
    return result


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
        tag_slug="dead-shapes",
        evidence=evidence,
    )
