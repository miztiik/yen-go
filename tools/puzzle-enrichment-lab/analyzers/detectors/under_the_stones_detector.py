"""Under-the-stones detector — sacrifice-then-place-inside pattern.

Detects the tesuji where a player sacrifices stones that get captured,
then plays inside the newly created space (the captured area). The PV
shows: player stones placed → opponent captures → player fills inside.
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
_NEIGHBORS = ((0, 1), (0, -1), (1, 0), (-1, 0))


class UnderTheStonesDetector:
    """Detects under-the-stones (sacrifice → capture → play inside) pattern."""

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

        # Under-the-stones requires a sacrifice: low policy + high winrate
        if top.policy_prior > 0.20:
            return _no_detection(
                f"Policy {top.policy_prior:.3f} too high for sacrifice"
            )

        if top.winrate < 0.7:
            return _no_detection(
                f"Winrate {top.winrate:.3f} too low"
            )

        # Need a long enough PV to show the sacrifice-capture-play-inside sequence
        if len(top.pv) < 4:
            return _no_detection(
                f"PV too short ({len(top.pv)}) for under-the-stones"
            )

        board_size = position.board_size

        # Check if later player moves in PV revisit the area of earlier moves
        # (playing "under" the captured stones)
        player_moves_xy = []
        for i, move in enumerate(top.pv):
            if i % 2 == 0:  # Player's moves (even indices)
                xy = _gtp_to_xy(move, board_size)
                if xy:
                    player_moves_xy.append(xy)

        if len(player_moves_xy) < 2:
            return _no_detection("Not enough player moves in PV")

        # Check if any later player move is adjacent to an earlier player move
        # This suggests playing back into the area where stones were sacrificed
        revisit_found = False
        for i in range(1, len(player_moves_xy)):
            for j in range(i):
                if _adjacent(player_moves_xy[i], player_moves_xy[j]):
                    revisit_found = True
                    break
            if revisit_found:
                break

        if revisit_found:
            confidence = min(0.80, 0.55 + (1.0 - top.policy_prior) * 0.15)
            return DetectionResult(
                detected=True,
                confidence=confidence,
                tag_slug="under-the-stones",
                evidence=(
                    f"Under-the-stones: sacrifice (policy={top.policy_prior:.3f}) "
                    f"then revisit area, pv_len={len(top.pv)}"
                ),
            )

        return _no_detection(
            f"No revisit pattern in PV of length {len(top.pv)}"
        )


def _adjacent(p1: tuple[int, int], p2: tuple[int, int]) -> bool:
    """Check if two points are orthogonally adjacent."""
    return abs(p1[0] - p2[0]) + abs(p1[1] - p2[1]) == 1


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
        tag_slug="under-the-stones",
        evidence=evidence,
    )
