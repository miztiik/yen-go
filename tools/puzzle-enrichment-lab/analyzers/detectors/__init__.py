"""Technique detectors — individual pattern/analysis-based tag detectors.

Each detector implements the TechniqueDetector protocol and returns a
DetectionResult indicating whether a specific technique was found.

The dispatcher calls all registered detectors and merges results.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from config import EnrichmentConfig
    from models.analysis_response import AnalysisResponse
    from models.detection import DetectionResult
    from models.position import Position
    from models.solve_result import SolutionNode


@runtime_checkable
class TechniqueDetector(Protocol):
    """Protocol that all technique detectors must implement."""

    def detect(
        self,
        position: Position,
        analysis: AnalysisResponse,
        solution_tree: SolutionNode | None,
        config: EnrichmentConfig,
    ) -> DetectionResult: ...
