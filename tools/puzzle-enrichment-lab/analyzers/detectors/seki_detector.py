"""Seki detector — detect mutual-life (seki) patterns.

Seki occurs when neither side can profitably attack the other's group,
resulting in a stalemate. Detection uses:

1. Winrate near 50% (within configured band)
2. Low score differential (neither side has a big lead)
3. Ownership contestation if available (neither side owns the area)
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


class SekiDetector:
    """Detects seki (mutual life) patterns."""

    def detect(
        self,
        position: Position,
        analysis: AnalysisResponse,
        solution_tree: SolutionNode | None,
        config: EnrichmentConfig,
    ) -> DetectionResult:
        tc = config.technique_detection
        wr_low = tc.seki.winrate_low if tc else 0.3
        wr_high = tc.seki.winrate_high if tc else 0.7
        score_thresh = tc.seki.score_threshold if tc else 5.0

        top = analysis.top_move
        if not top:
            return _no_detection("No top move available")

        # Seki: winrate clustered near 50% — neither side winning clearly
        if not (wr_low <= top.winrate <= wr_high):
            return _no_detection(
                f"Winrate {top.winrate:.3f} outside seki band "
                f"[{wr_low:.2f}, {wr_high:.2f}]"
            )

        # Low score lead — stalemate territory
        if abs(top.score_lead) > score_thresh:
            return _no_detection(
                f"Score lead |{top.score_lead:.1f}| > threshold {score_thresh}"
            )

        confidence = 0.65

        # Boost if multiple top moves have similar winrate (characteristic of seki)
        if len(analysis.move_infos) >= 2:
            second = analysis.move_infos[1]
            spread = abs(top.winrate - second.winrate)
            if spread < 0.1:
                confidence = min(0.90, confidence + 0.15)

        # Boost with ownership contestation data
        if analysis.ownership:
            contested = _contested_ratio(analysis.ownership, position.board_size)
            if contested > 0.2:
                confidence = min(0.95, confidence + contested * 0.15)

        return DetectionResult(
            detected=True,
            confidence=confidence,
            tag_slug="seki",
            evidence=(
                f"Seki signal: winrate={top.winrate:.3f}, "
                f"score_lead={top.score_lead:.1f}"
            ),
        )


def _contested_ratio(ownership: list[float], board_size: int) -> float:
    """Ratio of board points with contested ownership (abs < 0.3)."""
    total = board_size * board_size
    count = min(len(ownership), total)
    if count == 0:
        return 0.0
    contested = sum(1 for v in ownership[:count] if abs(v) < 0.3)
    return contested / count


def _no_detection(evidence: str) -> DetectionResult:
    return DetectionResult(
        detected=False,
        confidence=0.0,
        tag_slug="seki",
        evidence=evidence,
    )
