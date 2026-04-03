"""Endgame detector — detect endgame (yose) puzzles.

Heuristic: high stone density overall, moves near edges, small score
differentials between candidate moves. Endgame puzzles typically
feature nearly-settled positions with local boundary disputes.
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


class EndgameDetector:
    """Detects endgame (yose) puzzles via density and score differential heuristics."""

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

        # Endgame requires relatively high stone density
        density = stone_count / total_points if total_points > 0 else 0.0
        if density < 0.25:
            return _no_detection(
                f"Stone density {density:.2f} too low for endgame"
            )

        # Check if moves are near edges (endgame fights are often border disputes)
        top = analysis.top_move
        if not top:
            return _no_detection("No top move available")

        move_xy = _gtp_to_xy(top.move, board_size)
        if move_xy is None:
            return _no_detection(f"Cannot parse move {top.move}")

        mx, my = move_xy
        edge_line = _edge_line(mx, my, board_size)

        # Check score differential between top moves (small in endgame)
        if len(analysis.move_infos) >= 2:
            score_diff = abs(
                analysis.move_infos[0].score_lead - analysis.move_infos[1].score_lead
            )
            # Endgame: tight score battles
            if score_diff < 5.0 and edge_line <= 4:
                confidence = min(
                    0.75,
                    0.45 + density * 0.3 + (5.0 - score_diff) * 0.03,
                )
                return DetectionResult(
                    detected=True,
                    confidence=confidence,
                    tag_slug="endgame",
                    evidence=(
                        f"Endgame: density={density:.2f}, score_diff={score_diff:.1f}, "
                        f"move on line {edge_line}"
                    ),
                )

        # High density + edge move alone is a weaker signal
        if density >= 0.35 and edge_line <= 3:
            return DetectionResult(
                detected=True,
                confidence=0.50,
                tag_slug="endgame",
                evidence=(
                    f"Endgame (heuristic): density={density:.2f}, "
                    f"move on line {edge_line}"
                ),
            )

        return _no_detection(
            f"Insufficient endgame signal: density={density:.2f}, "
            f"line={edge_line}"
        )


def _edge_line(x: int, y: int, board_size: int) -> int:
    """Return the closest edge line number (1 = edge, 2 = second line)."""
    return min(x + 1, y + 1, board_size - x, board_size - y)


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
        tag_slug="endgame",
        evidence=evidence,
    )
