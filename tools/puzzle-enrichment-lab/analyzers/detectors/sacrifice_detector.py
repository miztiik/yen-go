"""Sacrifice detector — detect deliberate stone-loss for positional gain.

A sacrifice occurs when a player intentionally allows their own stones
to be captured in order to gain a larger advantage. Detection uses:

1. Low policy prior (the move looks bad / counter-intuitive)
2. High winrate (it actually works)
3. PV suggests own stones lost then position gained
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


class SacrificeDetector:
    """Detects sacrifice patterns (low policy + high winrate)."""

    def detect(
        self,
        position: Position,
        analysis: AnalysisResponse,
        solution_tree: SolutionNode | None,
        config: EnrichmentConfig,
    ) -> DetectionResult:
        tc = config.technique_detection
        policy_thresh = tc.sacrifice.policy_threshold if tc else 0.10
        wr_thresh = tc.sacrifice.winrate_threshold if tc else 0.85
        pv_min = tc.sacrifice.pv_min_length if tc else 3

        top = analysis.top_move
        if not top:
            return _no_detection("No top move available")

        # Sacrifice signature: low policy (looks bad) + high winrate (works)
        if top.policy_prior >= policy_thresh:
            return _no_detection(
                f"Policy {top.policy_prior:.3f} >= threshold {policy_thresh}"
            )

        if top.winrate < wr_thresh:
            return _no_detection(
                f"Winrate {top.winrate:.3f} < threshold {wr_thresh}"
            )

        confidence = 0.70

        # Boost if PV is long enough (sacrifice sequences are multi-move)
        if len(top.pv) >= pv_min:
            confidence = min(0.90, confidence + 0.10)

        # Boost if delta vs second move is large
        if len(analysis.move_infos) >= 2:
            second = analysis.move_infos[1]
            delta = top.winrate - second.winrate
            if delta > 0.2:
                confidence = min(0.95, confidence + delta * 0.15)

        return DetectionResult(
            detected=True,
            confidence=confidence,
            tag_slug="sacrifice",
            evidence=(
                f"Sacrifice signal: policy={top.policy_prior:.3f}, "
                f"winrate={top.winrate:.3f}, pv_len={len(top.pv)}"
            ),
        )


def _no_detection(evidence: str) -> DetectionResult:
    return DetectionResult(
        detected=False,
        confidence=0.0,
        tag_slug="sacrifice",
        evidence=evidence,
    )
