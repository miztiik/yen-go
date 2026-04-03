"""Ko detector — detect ko patterns from PV analysis and position metadata.

Ko detection strategy:
1. Check PV for repeated coordinates (same point captured/recaptured)
2. Check if analysis metadata hints at ko (ko_type field)
3. Use config thresholds from ko_detection section

A ko is detected when the same intersection appears multiple times
in the principal variation, indicating a capture-recapture cycle.
"""

from __future__ import annotations

import logging
from collections import Counter
from typing import TYPE_CHECKING

from models.detection import DetectionResult

if TYPE_CHECKING:
    from config import EnrichmentConfig
    from models.analysis_response import AnalysisResponse
    from models.position import Position
    from models.solve_result import SolutionNode

logger = logging.getLogger(__name__)


class KoDetector:
    """Detects ko patterns from PV sequences and metadata."""

    def detect(
        self,
        position: Position,
        analysis: AnalysisResponse,
        solution_tree: SolutionNode | None,
        config: EnrichmentConfig,
    ) -> DetectionResult:
        ko_cfg = config.ko_detection
        min_pv_length = ko_cfg.min_pv_length if ko_cfg else 3
        min_repeat = ko_cfg.min_repeat_count if ko_cfg else 2

        # Strategy 1: Check PV of top moves for repeated coordinates
        for move_info in analysis.move_infos:
            if len(move_info.pv) >= min_pv_length:
                repeated = _find_repeated_coords(move_info.pv, min_repeat)
                if repeated:
                    return DetectionResult(
                        detected=True,
                        confidence=0.85,
                        tag_slug="ko",
                        evidence=f"PV contains repeated coords: {', '.join(repeated)}",
                    )

        # Strategy 2: Check solution tree for ko patterns
        if solution_tree:
            if _solution_tree_has_ko(solution_tree, min_pv_length):
                return DetectionResult(
                    detected=True,
                    confidence=0.75,
                    tag_slug="ko",
                    evidence="Solution tree contains recapture pattern",
                )

        return DetectionResult(
            detected=False,
            confidence=0.0,
            tag_slug="ko",
            evidence="No ko pattern found",
        )


def _find_repeated_coords(pv: list[str], min_count: int = 2) -> list[str]:
    """Find coordinates that appear multiple times in PV (ko recapture)."""
    normalized = [m.upper() for m in pv if m.lower() != "pass"]
    counts = Counter(normalized)
    return [coord for coord, count in counts.items() if count >= min_count]


def _solution_tree_has_ko(node: SolutionNode, min_depth: int) -> bool:
    """Check if solution tree contains a recapture pattern."""
    moves: list[str] = []
    _collect_mainline(node, moves, max_depth=min_depth * 2)
    if len(moves) >= min_depth:
        return len(_find_repeated_coords(moves)) > 0
    return False


def _collect_mainline(node: SolutionNode, moves: list[str], max_depth: int) -> None:
    """Collect moves along the first child (mainline) of the solution tree."""
    if max_depth <= 0:
        return
    moves.append(node.move_gtp)
    if node.children:
        _collect_mainline(node.children[0], moves, max_depth - 1)
