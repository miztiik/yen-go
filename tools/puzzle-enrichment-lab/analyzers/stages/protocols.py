"""Protocols and data structures for the enrichment stage pipeline.

Defines the contracts between the orchestrator and individual stages:
- SgfMetadata: TypedDict for parsed SGF metadata keys
- PipelineContext: Mutable state flowing through the pipeline
- StageResult: Per-stage outcome
- ErrorPolicy: Stage failure behavior
- EnrichmentStage: Protocol all stages implement
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from config import EnrichmentConfig
    from models.ai_analysis_result import AiAnalysisResult
    from models.analysis_response import AnalysisResponse
    from models.detection import DetectionResult
    from models.difficulty_estimate import DifficultyEstimate
    from models.enrichment_state import EnrichmentRunState
    from models.instinct_result import InstinctResult
    from models.position import Position
    from models.refutation_result import RefutationResult
    from models.validation import CorrectMoveResult

    from analyzers.entropy_roi import EntropyROI
    from analyzers.single_engine import SingleEngineManager
    from core.sgf_parser import SGFNode


class SgfMetadata:
    """Typed container for parsed SGF metadata keys.

    Replaces bare ``dict`` for type safety (Must-Hold #1).
    """

    __slots__ = (
        "puzzle_id", "tags", "corner", "move_order",
        "ko_type", "collection",
    )

    def __init__(
        self,
        puzzle_id: str = "",
        tags: list[int] | None = None,
        corner: str = "TL",
        move_order: str = "strict",
        ko_type: str = "none",
        collection: str = "",
    ) -> None:
        self.puzzle_id = puzzle_id
        self.tags = tags if tags is not None else []
        self.corner = corner
        self.move_order = move_order
        self.ko_type = ko_type
        self.collection = collection

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for backward compatibility with existing code."""
        return {
            "puzzle_id": self.puzzle_id,
            "tags": self.tags,
            "corner": self.corner,
            "move_order": self.move_order,
            "ko_type": self.ko_type,
            "collection": self.collection,
        }

    def __getitem__(self, key: str) -> Any:
        """Dict-style access for backward compatibility."""
        return getattr(self, key)

    def get(self, key: str, default: Any = None) -> Any:
        """Dict-style .get() for backward compatibility."""
        return getattr(self, key, default)


class ErrorPolicy(enum.Enum):
    """How the runner should handle stage failures."""
    FAIL_FAST = "fail_fast"
    DEGRADE = "degrade"


@dataclass
class StageResult:
    """Outcome of a single stage execution."""
    stage_name: str
    success: bool
    error: str | None = None
    degraded: bool = False


@dataclass
class PipelineContext:
    """Mutable state flowing through the enrichment pipeline.

    Each stage reads upstream fields and writes its own fields.
    Field ownership is documented in the plan's Field Ownership Table.
    """

    # --- Init fields (set by orchestrator) ---
    sgf_text: str = ""
    config: EnrichmentConfig | None = None
    engine_manager: SingleEngineManager | None = None
    source_file: str = ""
    run_id: str = ""
    trace_id: str = ""
    config_hash: str = ""

    # --- Parse stage outputs ---
    root: SGFNode | None = None
    metadata: SgfMetadata | None = None
    position: Position | None = None
    correct_move_sgf: str | None = None

    # --- Solve paths outputs ---
    correct_move_gtp: str | None = None
    solution_moves: list[str] = field(default_factory=list)
    state: EnrichmentRunState | None = None
    pre_analysis: AnalysisResponse | None = None  # Reusable by AnalyzeStage

    # --- Query stage outputs ---
    response: AnalysisResponse | None = None
    framed_position: Position | None = None  # Framed position used for main analysis
    engine_model: str | None = None
    engine_visits: int = 0
    effective_visits: int = 0

    # --- Validation stage outputs ---
    validation_result: CorrectMoveResult | None = None
    curated_wrongs: list[dict] | None = None
    nearby_moves: list[str] | None = None

    # --- Refutation stage outputs ---
    refutation_result: RefutationResult | None = None

    # --- Entropy ROI outputs ---
    entropy_roi: EntropyROI | None = None

    # --- Difficulty stage outputs ---
    difficulty_estimate: DifficultyEstimate | None = None
    policy_entropy: float = 0.0
    correct_move_rank: int = 0

    # --- R-1: Teaching signal payload (computed from existing KataGo data) ---
    teaching_signals: dict = field(default_factory=dict)

    # --- Technique stage outputs ---
    detection_results: list[DetectionResult] | None = None

    # --- Instinct stage outputs ---
    instinct_results: list[InstinctResult] | None = None

    # --- Assembly stage outputs ---
    result: AiAnalysisResult | None = None

    # --- Diagnostic (G10) ---
    diagnostic: Any | None = None

    # --- Notify callback ---
    notify_fn: Callable[[str, dict], Awaitable[None]] | None = None

    # --- Timing (managed by runner) ---
    timings: dict[str, float] = field(default_factory=dict)

    # --- Per-stage query counts (managed by individual stages) ---
    queries_by_stage: dict[str, int] = field(default_factory=dict)


@runtime_checkable
class EnrichmentStage(Protocol):
    """Protocol that all enrichment stages must implement."""

    @property
    def name(self) -> str:
        """Human-readable stage name for logging and notifications."""
        ...

    @property
    def error_policy(self) -> ErrorPolicy:
        """How the runner should handle failures in this stage."""
        ...

    async def run(self, ctx: PipelineContext) -> PipelineContext:
        """Execute the stage, reading/writing fields on ctx."""
        ...
