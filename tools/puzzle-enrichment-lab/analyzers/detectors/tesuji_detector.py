"""Tesuji detector — meta-tag that aggregates specific technique detections.

Returns True if any specific tesuji technique was detected by other
detectors (ladder, snapback, throw-in, net, double-atari, sacrifice,
nakade, clamp, under-the-stones). This detector does NOT run engine
analysis itself — it checks if OTHER detectors found techniques.

Usage: call this detector AFTER all individual technique detectors
have run, passing their results via the solution_tree's metadata
or by checking previously collected DetectionResults.

Since this detector can't access other detectors' results directly
(no cross-detector dependencies), it uses a heuristic based on
analysis signatures that suggest tesuji play.
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

# Tesuji signatures: combinations of analysis features
# that suggest a tactical technique is involved
_TESUJI_SLUGS = frozenset({
    "ladder", "snapback", "throw-in", "net", "double-atari",
    "sacrifice", "nakade", "clamp", "under-the-stones",
})


class TesujiDetector:
    """Meta-tag detector: tesuji is present if analysis shows tactical signatures.

    Since individual detector results aren't available here, this uses
    heuristic analysis signatures (low policy + high winrate, long PV,
    significant delta) as proxies for tesuji presence.
    """

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

        signals = 0
        evidence_parts: list[str] = []

        # Signal 1: low policy (non-obvious move — hallmark of tesuji)
        if top.policy_prior < 0.15:
            signals += 1
            evidence_parts.append(f"low_policy={top.policy_prior:.3f}")

        # Signal 2: high winrate despite low policy (counter-intuitive success)
        if top.winrate >= 0.8:
            signals += 1
            evidence_parts.append(f"high_wr={top.winrate:.3f}")

        # Signal 3: long PV (multi-move tactical sequence)
        if len(top.pv) >= 4:
            signals += 1
            evidence_parts.append(f"long_pv={len(top.pv)}")

        # Signal 4: large delta vs second move (decisive technique)
        if len(analysis.move_infos) >= 2:
            second = analysis.move_infos[1]
            delta = abs(top.winrate - second.winrate)
            if delta > 0.25:
                signals += 1
                evidence_parts.append(f"delta={delta:.3f}")

        if signals >= 2:
            confidence = min(0.80, 0.45 + signals * 0.10)
            return DetectionResult(
                detected=True,
                confidence=confidence,
                tag_slug="tesuji",
                evidence=f"Tesuji signals ({signals}): {', '.join(evidence_parts)}",
            )

        return _no_detection(
            f"Only {signals} tesuji signal(s): {', '.join(evidence_parts) or 'none'}"
        )

    @staticmethod
    def tesuji_tag_slugs() -> frozenset[str]:
        """Return the set of technique tag slugs that constitute tesuji."""
        return _TESUJI_SLUGS


def _no_detection(evidence: str) -> DetectionResult:
    return DetectionResult(
        detected=False,
        confidence=0.0,
        tag_slug="tesuji",
        evidence=evidence,
    )
