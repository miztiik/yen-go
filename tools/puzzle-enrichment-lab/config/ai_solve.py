"""AI-Solve enrichment config models.

Groups: thresholds, confidence metrics, alternatives, calibration,
observability, and the unified AiSolveConfig that composes
SolutionTreeConfig from solution_tree module.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from config.solution_tree import (
    AiSolveGoalInference,
    AiSolveSekiDetectionConfig,
    EdgeCaseBoosts,
    SolutionTreeConfig,
)


class AiSolveThresholds(BaseModel):
    """Move classification thresholds (DD-2, DD-6).

    Delta-based classification only — no absolute winrate gates.
    """
    t_good: float = Field(
        default=0.05, ge=0.0, le=1.0,
        description="Max Δwr for a move to be correct (TE)",
    )
    t_bad: float = Field(
        default=0.15, ge=0.0, le=1.0,
        description="Min Δwr for a move to be wrong (BM)",
    )
    t_hotspot: float = Field(
        default=0.30, ge=0.0, le=1.0,
        description="Min Δwr for a blunder hotspot (BM_HO)",
    )
    t_disagreement: float = Field(
        default=0.10, ge=0.0, le=1.0,
        description="Min Δwr gap between AI and human correct move to log disagreement",
    )
    t_rebase_gap: float = Field(
        default=0.15, ge=0.0, le=1.0,
        description=(
            "D3: Min gap between root_winrate and max confirmed move winrate "
            "to trigger root rebasing. When ALL confirmed moves are this far "
            "below root, the root evaluation is likely unreliable (frame noise). "
            "Decoupled from t_bad to allow independent calibration."
        ),
    )

    @model_validator(mode="after")
    def thresholds_ordered(self) -> AiSolveThresholds:
        if self.t_good >= self.t_bad:
            raise ValueError(
                f"t_good ({self.t_good}) must be < t_bad ({self.t_bad})"
            )
        if self.t_bad >= self.t_hotspot:
            raise ValueError(
                f"t_bad ({self.t_bad}) must be < t_hotspot ({self.t_hotspot})"
            )
        return self


class AiSolveConfidenceMetrics(BaseModel):
    """Pre/post winrate as confidence annotations, not gates (DD-6)."""
    pre_winrate_floor: float = Field(
        default=0.30, ge=0.0, le=1.0,
        description="Root winrate below which confidence is annotated low",
    )
    post_winrate_ceiling: float = Field(
        default=0.95, ge=0.0, le=1.0,
        description="Post-move winrate above which confidence is annotated high",
    )


class AiSolveAlternativesConfig(BaseModel):
    """Alternative discovery and disagreement handling (DD-7, DD-10)."""
    co_correct_min_gap: float = Field(
        default=0.02, ge=0.0, le=0.5,
        description="Max winrate gap for co-correct detection",
    )
    co_correct_score_gap: float = Field(
        default=2.0, ge=0.0, le=50.0,
        description="Max score gap for co-correct detection",
    )
    disagreement_threshold: float = Field(
        default=0.10, ge=0.0, le=1.0,
        description="Min Δwr to log AI vs human disagreement",
    )
    losing_threshold: float = Field(
        default=0.30, ge=0.0, le=1.0,
        description="Δwr above which human solution is classified as 'losing'",
    )


class AiSolveCalibrationConfig(BaseModel):
    """Calibration parameters for AI-Solve thresholds (DD-9)."""
    min_samples_per_class: int = Field(
        default=30, ge=10, le=1000,
        description="Min calibration samples per class (TE/BM/neutral)",
    )
    target_macro_f1: float = Field(
        default=0.85, ge=0.5, le=1.0,
        description="Target macro-F1 for threshold optimization",
    )
    visit_counts: list[int] = Field(
        default_factory=lambda: [500, 1000, 2000],
        description="Visit counts to sweep during calibration",
    )


class ObservabilityConfig(BaseModel):
    """Observability settings for AI-Solve (DD-11)."""
    disagreement_sink_path: str = Field(
        default=".lab-runtime/logs/disagreements",
        description="Directory for disagreement JSONL files",
    )
    collection_warning_threshold: float = Field(
        default=0.20, ge=0.0, le=1.0,
        description="Per-collection disagreement rate that triggers WARNING",
    )


class AiSolveConfig(BaseModel):
    """AI-Solve unified enrichment configuration (v1.14, ai-solve-enrichment-plan-v3).

    Controls solution tree building, move classification, alternative discovery,
    and observability for the AI-Solve pipeline. Always active — the `enabled`
    flag was removed as AI-Solve is mature and always-on.

    Design decisions DD-1 through DD-12 are documented in:
    ``TODO/ai-solve-enrichment-plan-v3.md``
    """
    thresholds: AiSolveThresholds = Field(
        default_factory=AiSolveThresholds,
        description="Move classification thresholds (DD-2)",
    )
    confidence_metrics: AiSolveConfidenceMetrics = Field(
        default_factory=AiSolveConfidenceMetrics,
        description="Pre/post winrate confidence annotations (DD-6)",
    )
    solution_tree: SolutionTreeConfig = Field(
        default_factory=SolutionTreeConfig,
        description="Solution tree construction parameters (DD-1, DD-3)",
    )
    seki_detection: AiSolveSekiDetectionConfig = Field(
        default_factory=AiSolveSekiDetectionConfig,
        description="Seki early-exit for tree building (DD-12)",
    )
    goal_inference: AiSolveGoalInference = Field(
        default_factory=AiSolveGoalInference,
        description="Goal inference parameters (DD-8)",
    )
    edge_case_boosts: EdgeCaseBoosts = Field(
        default_factory=EdgeCaseBoosts,
        description="Visit boosts for edge cases (DD-12)",
    )
    alternatives: AiSolveAlternativesConfig = Field(
        default_factory=AiSolveAlternativesConfig,
        description="Alternative discovery and disagreement config (DD-7, DD-10)",
    )
    calibration: AiSolveCalibrationConfig = Field(
        default_factory=AiSolveCalibrationConfig,
        description="Calibration parameters (DD-9)",
    )
    observability: ObservabilityConfig = Field(
        default_factory=ObservabilityConfig,
        description="Observability settings (DD-11)",
    )
    model_by_category: dict[str, str] = Field(
        default_factory=lambda: {"strong": "referee"},
        description="PI-4: Map level categories to model names for routing. "
        "Empty dict = no routing. 'strong' category (advanced/low-dan/high-dan/expert) "
        "routes to the referee model (b28) for higher accuracy on complex puzzles. "
        "Example: {\"entry\": \"test_fast\", \"core\": \"quick\", \"strong\": \"referee\"}",
    )
