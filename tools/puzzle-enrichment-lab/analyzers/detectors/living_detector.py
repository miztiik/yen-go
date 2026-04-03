"""Living detector — detect group survival confirmation via ownership.

Checks for high ownership values for the player's stones after the
correct move sequence, confirming that the group lives.
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


class LivingDetector:
    """Detects group survival (living) via ownership analysis after PV."""

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

        # Living: high winrate for the player after the correct move
        if top.winrate < 0.7:
            return _no_detection(
                f"Winrate {top.winrate:.3f} too low for living confirmation"
            )

        # Check ownership data for strong player control
        if top.ownership:
            player_sign = 1.0 if position.player_to_move.value == "B" else -1.0
            flat = [v for row in top.ownership for v in row]
            if flat:
                # Count how many cells are strongly owned by player
                strong_cells = sum(1 for v in flat if v * player_sign > 0.5)
                total = len(flat)
                ratio = strong_cells / total if total > 0 else 0.0
                if ratio > 0.05:  # At least some strong ownership
                    confidence = min(0.80, 0.55 + ratio * 0.5 + top.winrate * 0.1)
                    return DetectionResult(
                        detected=True,
                        confidence=confidence,
                        tag_slug="living",
                        evidence=(
                            f"Living: winrate={top.winrate:.3f}, "
                            f"{strong_cells}/{total} cells strongly owned"
                        ),
                    )

        # Fallback: very high winrate alone suggests successful living
        if top.winrate >= 0.9:
            return DetectionResult(
                detected=True,
                confidence=0.55,
                tag_slug="living",
                evidence=f"Living (heuristic): winrate={top.winrate:.3f}, no ownership data",
            )

        return _no_detection(
            f"Insufficient evidence for living: winrate={top.winrate:.3f}"
        )


def _no_detection(evidence: str) -> DetectionResult:
    return DetectionResult(
        detected=False,
        confidence=0.0,
        tag_slug="living",
        evidence=evidence,
    )
