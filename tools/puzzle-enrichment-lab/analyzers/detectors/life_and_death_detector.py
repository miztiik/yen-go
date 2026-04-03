"""Life-and-death detector — base technique tag for tsumego puzzles.

Every tsumego puzzle is fundamentally a life-and-death problem.
This detector always returns detected=True with high confidence,
serving as the fallback/base tag.

If ownership data is available, it checks for significant ownership
swings between the top move and the second-best move, boosting
confidence when swings are large.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from models.detection import DetectionResult

if TYPE_CHECKING:
    from config import EnrichmentConfig
    from models.analysis_response import AnalysisResponse
    from models.position import Position
    from models.solve_result import SolutionNode


class LifeAndDeathDetector:
    """Detects life-and-death — the fundamental tsumego tag."""

    def detect(
        self,
        position: Position,
        analysis: AnalysisResponse,
        solution_tree: SolutionNode | None,
        config: EnrichmentConfig,
    ) -> DetectionResult:
        confidence = 0.9
        evidence = "Default tsumego classification"

        # Boost confidence if ownership data shows significant swing
        if analysis.move_infos and len(analysis.move_infos) >= 2:
            top = analysis.move_infos[0]
            second = analysis.move_infos[1]
            if top.ownership and second.ownership:
                try:
                    swing = _ownership_swing(top.ownership, second.ownership)
                    if swing > 0.3:
                        confidence = min(0.99, 0.9 + swing * 0.1)
                        evidence = f"Ownership swing {swing:.2f} between top moves"
                except (ValueError, IndexError):
                    pass

        return DetectionResult(
            detected=True,
            confidence=confidence,
            tag_slug="life-and-death",
            evidence=evidence,
        )


def _ownership_swing(
    ownership_a: list[list[float]],
    ownership_b: list[list[float]],
) -> float:
    """Compute average absolute ownership difference between two move ownership maps."""
    flat_a = [v for row in ownership_a for v in row]
    flat_b = [v for row in ownership_b for v in row]
    if len(flat_a) != len(flat_b) or not flat_a:
        return 0.0
    total = sum(abs(a - b) for a, b in zip(flat_a, flat_b, strict=False))
    return total / len(flat_a)
