"""Pydantic data models for KataGo Lab.

All inter-module communication uses these typed models.
Designed so they can trivially become REST request/response bodies.
"""

from .analysis_request import AnalysisRequest
from .analysis_response import AnalysisResponse, MoveAnalysis
from .detection import DetectionResult
from .diagnostic import PuzzleDiagnostic
from .difficulty_estimate import DifficultyEstimate
from .position import Color, Position, Stone
from .refutation_result import Refutation, RefutationResult
from .solve_result import (
    AiCorrectnessLevel,
    BatchSummary,
    DisagreementRecord,
    HumanSolutionConfidence,
    MoveClassification,
    MoveQuality,
    PositionAnalysis,
    QueryBudget,
    SolutionNode,
    SolvedMove,
    TreeCompletenessMetrics,
)
from .validation import CorrectMoveResult, ValidationStatus

__all__ = [
    "Position", "Stone", "Color",
    "AnalysisRequest",
    "AnalysisResponse", "MoveAnalysis",
    "RefutationResult", "Refutation",
    "DifficultyEstimate",
    "ValidationStatus", "CorrectMoveResult",
    # AI-Solve models (Phase 2)
    "AiCorrectnessLevel",
    "BatchSummary",
    "DisagreementRecord",
    "HumanSolutionConfidence",
    "MoveClassification",
    "MoveQuality",
    "PositionAnalysis",
    "QueryBudget",
    "SolutionNode",
    "SolvedMove",
    "TreeCompletenessMetrics",
    # Detection infrastructure
    "DetectionResult",
    # Diagnostics
    "PuzzleDiagnostic",
]
