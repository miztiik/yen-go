"""Net detector — detect loose net (geta) surrounding patterns.

A net move surrounds opponent stones so they cannot escape regardless
of their responses. Characteristics:

1. High winrate with multiple refutations that all fail
2. Refutation winrates are similar (opponent can't find a way out)
3. Config thresholds from technique_detection.net
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


class NetDetector:
    """Detects net (geta) — loose surrounding patterns."""

    def detect(
        self,
        position: Position,
        analysis: AnalysisResponse,
        solution_tree: SolutionNode | None,
        config: EnrichmentConfig,
    ) -> DetectionResult:
        tc = config.technique_detection
        winrate_thresh = tc.net.winrate_threshold if tc else 0.9
        min_refutations = tc.net.min_refutations if tc else 2
        delta_spread = tc.net.delta_spread if tc else 0.1

        top = analysis.top_move
        if not top:
            return _no_detection("No top move available")

        if top.winrate < winrate_thresh:
            return _no_detection(
                f"Winrate {top.winrate:.3f} < threshold {winrate_thresh}"
            )

        # Count refutations: non-top moves with significantly lower winrate
        alternatives = analysis.move_infos[1:]
        if len(alternatives) < min_refutations:
            return _no_detection(
                f"Only {len(alternatives)} alternative(s), need {min_refutations}"
            )

        # Check that top refutations have similar (clustered) winrates
        refutation_wrs = [m.winrate for m in alternatives[:min_refutations + 2]]
        if not refutation_wrs:
            return _no_detection("No refutation winrates")

        wr_spread = max(refutation_wrs) - min(refutation_wrs)
        if wr_spread > delta_spread:
            return _no_detection(
                f"Refutation spread {wr_spread:.3f} > threshold {delta_spread}"
            )

        # All refutations fail similarly — this is a net pattern
        avg_ref_wr = sum(refutation_wrs) / len(refutation_wrs)
        delta = top.winrate - avg_ref_wr
        confidence = min(0.95, 0.65 + delta * 0.3)

        return DetectionResult(
            detected=True,
            confidence=confidence,
            tag_slug="net",
            evidence=(
                f"Net pattern: winrate={top.winrate:.3f}, "
                f"{len(refutation_wrs)} refutations clustered "
                f"(spread={wr_spread:.3f}, avg_wr={avg_ref_wr:.3f})"
            ),
        )


def _no_detection(evidence: str) -> DetectionResult:
    return DetectionResult(
        detected=False,
        confidence=0.0,
        tag_slug="net",
        evidence=evidence,
    )
