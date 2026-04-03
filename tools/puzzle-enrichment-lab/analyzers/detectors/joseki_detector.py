"""Joseki detector — heuristic detection of joseki (opening corner sequence) puzzles.

Heuristic-only: checks for low stone count, corner focus, and opening
patterns. Confidence capped at 0.5 due to heuristic quality — proper
joseki detection requires a reference database.
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

_MAX_CONFIDENCE = 0.50  # Heuristic quality cap


class JosekiDetector:
    """Detects joseki (corner opening sequences) via heuristics.

    Limitations: No joseki reference database — relies on stone count,
    corner placement, and opening characteristics. Confidence is capped
    at 0.5.
    """

    def detect(
        self,
        position: Position,
        analysis: AnalysisResponse,
        solution_tree: SolutionNode | None,
        config: EnrichmentConfig,
    ) -> DetectionResult:
        board_size = position.board_size
        stone_count = len(position.stones)

        # Joseki: typically few stones (opening phase)
        if stone_count > 20:
            return _no_detection(
                f"Too many stones ({stone_count}) for joseki"
            )

        if stone_count < 2:
            return _no_detection(
                f"Too few stones ({stone_count}) for joseki"
            )

        # Check corner focus: stones should be in a corner quadrant
        if not position.stones:
            return _no_detection("No stones on board")

        try:
            min_x, min_y, max_x, max_y = position.get_bounding_box()
        except ValueError:
            return _no_detection("Cannot compute bounding box")

        half = board_size // 2
        center_x = (min_x + max_x) / 2
        center_y = (min_y + max_y) / 2

        # Stones should be in one corner
        in_corner = (
            (center_x < half and center_y < half)
            or (center_x >= half and center_y < half)
            or (center_x < half and center_y >= half)
            or (center_x >= half and center_y >= half)
        )

        if not in_corner:
            return _no_detection("Stones not focused in a corner")

        # Check for balanced color distribution (joseki involves both sides)
        black_count = len(position.black_stones)
        white_count = len(position.white_stones)
        if black_count == 0 or white_count == 0:
            return _no_detection("Only one color present")

        color_ratio = min(black_count, white_count) / max(black_count, white_count)
        if color_ratio < 0.3:
            return _no_detection(
                f"Unbalanced colors (ratio={color_ratio:.2f})"
            )

        # Joseki stones are typically on 3rd/4th line
        star_pts = _count_star_point_stones(position)
        confidence = min(
            _MAX_CONFIDENCE,
            0.25 + color_ratio * 0.15 + star_pts * 0.05,
        )

        return DetectionResult(
            detected=True,
            confidence=confidence,
            tag_slug="joseki",
            evidence=(
                f"Joseki heuristic: {stone_count} stones in corner, "
                f"B/W ratio={color_ratio:.2f}, star_points={star_pts}"
            ),
        )


def _count_star_point_stones(position: Position) -> int:
    """Count stones on or near 3rd/4th line (typical joseki lines)."""
    board_size = position.board_size
    count = 0
    for s in position.stones:
        line_x = min(s.x + 1, board_size - s.x)
        line_y = min(s.y + 1, board_size - s.y)
        if line_x in (3, 4) or line_y in (3, 4):
            count += 1
    return count


def _no_detection(evidence: str) -> DetectionResult:
    return DetectionResult(
        detected=False,
        confidence=0.0,
        tag_slug="joseki",
        evidence=evidence,
    )
