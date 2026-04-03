"""Corner detector — position-based detection of corner puzzles.

Checks whether the majority of stones are in a corner quadrant,
using the position's bounding box to determine corner proximity.
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


class CornerDetector:
    """Detects corner positions based on stone placement."""

    def detect(
        self,
        position: Position,
        analysis: AnalysisResponse,
        solution_tree: SolutionNode | None,
        config: EnrichmentConfig,
    ) -> DetectionResult:
        if not position.stones:
            return _no_detection("No stones on board")

        board_size = position.board_size
        try:
            min_x, min_y, max_x, max_y = position.get_bounding_box()
        except ValueError:
            return _no_detection("Cannot compute bounding box")

        # Check if stones are concentrated in a corner quadrant
        half = board_size // 2
        width = max_x - min_x
        height = max_y - min_y

        # Small cluster (fits in ~half the board in both dimensions)
        if width > half or height > half:
            return _no_detection(
                f"Stones too spread out ({width}x{height} > {half})"
            )

        # Determine which corner the cluster is closest to
        center_x = (min_x + max_x) / 2
        center_y = (min_y + max_y) / 2
        corner = _classify_corner(center_x, center_y, board_size)

        if corner is None:
            return _no_detection("Stones not in a corner quadrant")

        # Confidence based on how tightly clustered in the corner
        max_dim = max(width, height)
        tightness = 1.0 - (max_dim / half) if half > 0 else 0.5
        confidence = min(0.85, 0.55 + tightness * 0.25)

        return DetectionResult(
            detected=True,
            confidence=confidence,
            tag_slug="corner",
            evidence=(
                f"Corner puzzle ({corner}): stones in "
                f"({min_x},{min_y})-({max_x},{max_y}), board={board_size}"
            ),
        )


def _classify_corner(
    cx: float, cy: float, board_size: int
) -> str | None:
    """Classify center of mass into a corner quadrant."""
    board_size / 2
    threshold = board_size * 0.35  # Must be within 35% of corner

    if cx < threshold and cy < threshold:
        return "TL"
    if cx > board_size - 1 - threshold and cy < threshold:
        return "TR"
    if cx < threshold and cy > board_size - 1 - threshold:
        return "BL"
    if cx > board_size - 1 - threshold and cy > board_size - 1 - threshold:
        return "BR"
    return None


def _no_detection(evidence: str) -> DetectionResult:
    return DetectionResult(
        detected=False,
        confidence=0.0,
        tag_slug="corner",
        evidence=evidence,
    )
