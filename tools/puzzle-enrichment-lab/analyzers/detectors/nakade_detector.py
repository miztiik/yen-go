"""Nakade detector — detect interior vital-point moves.

Nakade is a move played inside an opponent's potential eye space that
prevents the opponent from forming two eyes. Detection checks:

1. The correct move is surrounded mostly by opponent stones
2. High winrate (the vital point works)
3. Config thresholds from technique_detection.nakade
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

_NEIGHBORS = ((0, 1), (0, -1), (1, 0), (-1, 0))
_GTP_LETTERS = "ABCDEFGHJKLMNOPQRST"


class NakadeDetector:
    """Detects nakade (interior vital point) patterns."""

    def detect(
        self,
        position: Position,
        analysis: AnalysisResponse,
        solution_tree: SolutionNode | None,
        config: EnrichmentConfig,
    ) -> DetectionResult:
        tc = config.technique_detection
        min_opp = tc.nakade.min_opponent_neighbors if tc else 3
        wr_thresh = tc.nakade.winrate_threshold if tc else 0.8

        top = analysis.top_move
        if not top:
            return _no_detection("No top move available")

        move_xy = _gtp_to_xy(top.move, position.board_size)
        if move_xy is None:
            return _no_detection(f"Cannot parse move {top.move}")

        if top.winrate < wr_thresh:
            return _no_detection(
                f"Winrate {top.winrate:.3f} < threshold {wr_thresh}"
            )

        board_size = position.board_size
        opponent_color = "W" if position.player_to_move.value == "B" else "B"
        occupied = {(s.x, s.y): s.color.value for s in position.stones}

        mx, my = move_xy
        opp_count = 0
        total_neighbors = 0
        for dx, dy in _NEIGHBORS:
            nx, ny = mx + dx, my + dy
            if 0 <= nx < board_size and 0 <= ny < board_size:
                total_neighbors += 1
                if occupied.get((nx, ny)) == opponent_color:
                    opp_count += 1

        if opp_count < min_opp:
            return _no_detection(
                f"Only {opp_count} opponent neighbors (need {min_opp})"
            )

        confidence = min(0.90, 0.60 + opp_count * 0.08 + top.winrate * 0.1)
        return DetectionResult(
            detected=True,
            confidence=confidence,
            tag_slug="nakade",
            evidence=(
                f"Vital point: {top.move} surrounded by {opp_count}/{total_neighbors} "
                f"opponent stones, winrate={top.winrate:.3f}"
            ),
        )


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
        tag_slug="nakade",
        evidence=evidence,
    )
