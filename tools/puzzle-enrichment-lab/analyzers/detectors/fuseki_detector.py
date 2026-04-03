"""Fuseki detector — heuristic detection of whole-board opening puzzles.

Heuristic-only: checks for very low stone count relative to board size,
indicating an early opening (fuseki) position. Confidence capped at 0.4
due to lowest heuristic quality.
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

_MAX_CONFIDENCE = 0.40  # Lowest quality heuristic


class FusekiDetector:
    """Detects fuseki (whole-board opening) puzzles via heuristics.

    Limitations: No opening book reference — relies on stone density
    and spread. Confidence capped at 0.4.
    """

    def detect(
        self,
        position: Position,
        analysis: AnalysisResponse,
        solution_tree: SolutionNode | None,
        config: EnrichmentConfig,
    ) -> DetectionResult:
        board_size = position.board_size
        total_points = board_size * board_size
        stone_count = len(position.stones)

        # Fuseki: very low stone density (early opening)
        density = stone_count / total_points if total_points > 0 else 0.0

        if density > 0.08:
            return _no_detection(
                f"Stone density {density:.3f} too high for fuseki"
            )

        if stone_count < 3:
            return _no_detection(
                f"Too few stones ({stone_count}) for fuseki puzzle"
            )

        # Check that stones are spread across the board (not clustered)
        if not position.stones:
            return _no_detection("No stones on board")

        try:
            min_x, min_y, max_x, max_y = position.get_bounding_box()
        except ValueError:
            return _no_detection("Cannot compute bounding box")

        spread_x = max_x - min_x
        spread_y = max_y - min_y
        half = board_size // 2

        # Fuseki typically involves stones across multiple areas
        if spread_x < half and spread_y < half:
            return _no_detection(
                f"Stones too clustered ({spread_x}x{spread_y}) for fuseki"
            )

        # Balanced colors (both sides playing)
        black_count = len(position.black_stones)
        white_count = len(position.white_stones)
        if black_count == 0 or white_count == 0:
            return _no_detection("Only one color present")

        confidence = min(
            _MAX_CONFIDENCE,
            0.20 + (1.0 - density) * 0.10 + min(spread_x, spread_y) / board_size * 0.10,
        )

        return DetectionResult(
            detected=True,
            confidence=confidence,
            tag_slug="fuseki",
            evidence=(
                f"Fuseki heuristic: {stone_count} stones, density={density:.3f}, "
                f"spread={spread_x}x{spread_y}, board={board_size}"
            ),
        )


def _no_detection(evidence: str) -> DetectionResult:
    return DetectionResult(
        detected=False,
        confidence=0.0,
        tag_slug="fuseki",
        evidence=evidence,
    )
