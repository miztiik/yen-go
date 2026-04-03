"""Snapback detector — detect sacrifice-then-recapture patterns.

A snapback occurs when a player sacrifices one or more stones to be
captured, then immediately recaptures a larger group. Detection uses:

1. Policy/winrate signature: low policy (sacrifice looks bad to the engine)
   but high winrate (it actually wins) — the hallmark of a sacrifice.
2. PV capture pattern: verifies that the principal variation shows the
   mechanical sacrifice → capture → recapture sequence.
3. Config thresholds from technique_detection.snapback.
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


def _parse_gtp(move: str) -> tuple[int, int] | None:
    """Parse GTP coordinate to (row, col) 0-indexed. Returns None on failure."""
    if not move or move.lower() == "pass":
        return None
    move = move.upper()
    if len(move) < 2 or move[0] not in _GTP_LETTERS:
        return None
    try:
        col = _GTP_LETTERS.index(move[0])
        row = int(move[1:]) - 1  # GTP rows are 1-indexed
    except (ValueError, IndexError):
        return None
    return (row, col)


def _pv_has_recapture_pattern(pv: list[str], min_pv_length: int) -> bool:
    """Check if PV shows sacrifice → capture → recapture near original point.

    A snapback PV: move 1 = sacrifice, move 2 = opponent captures,
    move 3 = recapture at/near the sacrifice point (Manhattan distance ≤ 2).
    """
    if len(pv) < min_pv_length:
        return False
    first = _parse_gtp(pv[0])
    third = _parse_gtp(pv[2])
    if first is None or third is None:
        return False
    manhattan = abs(first[0] - third[0]) + abs(first[1] - third[1])
    return manhattan <= 2


class SnapbackDetector:
    """Detects snapback (sacrifice + recapture) patterns."""

    def detect(
        self,
        position: Position,
        analysis: AnalysisResponse,
        solution_tree: SolutionNode | None,
        config: EnrichmentConfig,
    ) -> DetectionResult:
        tc = config.technique_detection
        policy_thresh = tc.snapback.policy_threshold if tc else 0.05
        winrate_thresh = tc.snapback.winrate_threshold if tc else 0.9
        delta_thresh = tc.snapback.delta_threshold if tc else 0.3
        min_pv_len = tc.snapback.min_pv_length if tc else 3

        top = analysis.top_move
        if not top:
            return _no_detection("No top move available")

        # Pre-filter: snapback signature — low policy (sacrifice) + high winrate
        if top.policy_prior >= policy_thresh:
            return _no_detection(
                f"Policy {top.policy_prior:.3f} >= threshold {policy_thresh}"
            )

        if top.winrate < winrate_thresh:
            return _no_detection(
                f"Winrate {top.winrate:.3f} < threshold {winrate_thresh}"
            )

        # Signal strength from delta between top move and alternatives
        has_delta_signal = False
        delta = 0.0
        if len(analysis.move_infos) >= 2:
            second = analysis.move_infos[1]
            delta = abs(top.winrate - second.winrate)
            has_delta_signal = delta > delta_thresh

        has_strong_sacrifice = (
            top.policy_prior < policy_thresh * 0.5
            and top.winrate > winrate_thresh
        )

        if not has_delta_signal and not has_strong_sacrifice:
            return _no_detection("No snapback pattern found")

        # PV capture pattern verification
        pv_confirmed = _pv_has_recapture_pattern(top.pv, min_pv_len)

        if pv_confirmed:
            confidence = 0.85
            if has_delta_signal:
                confidence = min(0.95, 0.85 + delta * 0.1)
            return DetectionResult(
                detected=True,
                confidence=confidence,
                tag_slug="snapback",
                evidence=(
                    f"Sacrifice signature: policy={top.policy_prior:.3f}, "
                    f"winrate={top.winrate:.3f}, "
                    f"PV recapture confirmed"
                ),
            )

        # Signal-only detection (no PV confirmation) — reduced confidence
        return DetectionResult(
            detected=True,
            confidence=0.45,
            tag_slug="snapback",
            evidence=(
                f"Sacrifice signal (PV unconfirmed): "
                f"policy={top.policy_prior:.3f}, "
                f"winrate={top.winrate:.3f}"
            ),
        )


def _no_detection(evidence: str) -> DetectionResult:
    return DetectionResult(
        detected=False,
        confidence=0.0,
        tag_slug="snapback",
        evidence=evidence,
    )
