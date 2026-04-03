"""Analysis defaults, visit tiers, and engine config models.

Groups: analysis defaults, visit tier configs, ko analysis,
deep enrichment, models, tree validation, frame config, HumanSL.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class AnalysisDefaultsConfig(BaseModel):
    """Default analysis parameters used across query builders and models."""
    default_max_visits: int = Field(
        default=200,
        ge=1, le=100000,
        description="Default MCTS visits when no override is provided",
    )
    puzzle_region_margin: int = Field(
        default=2,
        ge=0, le=10,
        description="Margin (in intersections) around puzzle stones for analysis region",
    )
    visits_escalation_multiplier: int = Field(
        default=2,
        ge=1, le=10,
        description="Multiplier for visits_to_solve when KataGo disagrees (visits * N)",
    )
    visits_escalation_addend: int = Field(
        default=200,
        ge=0, le=10000,
        description="Addend for visits_to_solve when KataGo disagrees (visits + N)",
    )


class VisitTierConfig(BaseModel):
    """Configuration for a single visit tier."""
    visits: int = Field(ge=1)
    purpose: str = ""


class VisitTiersConfig(BaseModel):
    """Graduated visit tier configuration."""
    T0: VisitTierConfig = Field(default_factory=lambda: VisitTierConfig(visits=50, purpose="Policy snapshot"))
    T1: VisitTierConfig = Field(default_factory=lambda: VisitTierConfig(visits=500, purpose="Standard analysis"))
    T2: VisitTierConfig = Field(default_factory=lambda: VisitTierConfig(visits=2000, purpose="Deep analysis"))
    T3: VisitTierConfig = Field(default_factory=lambda: VisitTierConfig(visits=5000, purpose="Referee"))


class KoAnalysisConfig(BaseModel):
    """Ko-aware analysis configuration (Phase S.4, ADR D31).

    Configures per-ko-type overrides for KataGo rules and PV length.
    Motivated by KataGo PR #261: superko rules prevent KataGo from
    exploring ko recapture sequences. Using simple ko rules (tromp-taylor)
    lets the search tree include ko fights that superko would prune.
    """
    rules_by_ko_type: dict[str, str] = Field(
        default_factory=lambda: {
            "none": "chinese",
            "direct": "tromp-taylor",
            "approach": "tromp-taylor",
        },
        description=(
            "KataGo rules string per YK ko-type. "
            "'tromp-taylor' uses simple ko (only immediate recapture banned) "
            "instead of superko, letting KataGo explore ko sequences freely."
        ),
    )
    pv_len_by_ko_type: dict[str, int] = Field(
        default_factory=lambda: {
            "none": 15,
            "direct": 30,
            "approach": 30,
        },
        description=(
            "Per-request analysisPVLen override by ko-type. "
            "Ko fights produce longer PV sequences (captures + recaptures). "
            "Default cfg is 15; ko puzzles need 30 to capture full ko fight."
        ),
    )


class DeepEnrichConfig(BaseModel):
    """Deep enrichment settings (Plan 010, D47).

    Renamed from LabModeConfig. Behavior-descriptive naming;
    location-agnostic for mainline pipeline migration.
    b18 at 2K visits = ~13,600 Elo. b28 reserved for referee escalation.
    """
    enabled: bool = Field(
        default=True,
        description="Enable deep enrichment mode",
    )
    model: str = Field(
        description="Model architecture label (via models.deep_enrich)",
    )
    visits: int = Field(
        default=2000,
        ge=100, le=1000000,
        description="MCTS visits per puzzle (2K = ~13,600 Elo with b18)",
    )
    root_num_symmetries_to_sample: int = Field(
        default=4,
        ge=1, le=8,
        description="Board symmetries to sample at root for standard analysis (T25)",
    )
    referee_symmetries: int = Field(
        default=8,
        ge=1, le=8,
        description="Board symmetries to sample for referee/T3 tier analysis (T25)",
    )
    max_time: int = Field(
        default=0,
        ge=0,
        description="Max time per query in seconds (0 = no limit)",
    )
    escalate_to_referee: bool = Field(
        default=True,
        description="Escalate uncertain puzzles to referee model",
    )
    escalation_winrate_low: float = Field(
        default=0.3, ge=0.0, le=1.0,
        description="Winrate below this triggers escalation",
    )
    escalation_winrate_high: float = Field(
        default=0.7, ge=0.0, le=1.0,
        description="Winrate above this skips escalation",
    )
    tiebreaker_tolerance: float = Field(
        default=0.05, ge=0.0, le=1.0,
        description="Winrate agreement tolerance between models",
    )


class ModelEntry(BaseModel):
    """A single model label -> filename mapping (Plan 010, P2.1)."""
    label: str = Field(description="Logical name for this model")
    arch: str = Field(description="Architecture identifier (e.g. b18c384)")
    filename: str = Field(description="Model filename (resolved relative to models-data/)")
    description: str = Field(default="", description="Optional human-readable description")


class ModelsConfig(BaseModel):
    """Model name indirection (Plan 010, D42).

    Code references labels only, never filenames directly.
    All model entries MUST be provided via config/katago-enrichment.json.
    No hardcoded model filenames or architectures in .py files.
    """
    description: str = ""
    quick: ModelEntry = Field(
        description="Quick analysis model (required in config JSON)",
    )
    referee: ModelEntry = Field(
        description="Referee/arbiter model (required in config JSON)",
    )
    deep_enrich: ModelEntry = Field(
        description="Deep enrichment model (required in config JSON)",
    )
    test_fast: ModelEntry = Field(
        description="Fast test model (required in config JSON)",
    )
    test_smallest: ModelEntry | None = Field(
        default=None,
        description="Smallest test model for smoke/validation tests (optional)",
    )
    benchmark: ModelEntry | None = Field(
        default=None,
        description="Benchmark model for performance comparison tests (optional)",
    )


class TreeValidationConfig(BaseModel):
    """Deep solution tree validation thresholds (Plan 010, D44)."""
    enabled: bool = Field(default=True, description="Master switch for tree validation")
    skip_when_confident: bool = Field(
        default=True,
        description="Skip tree validation if initial analysis is confident",
    )
    confidence_winrate: float = Field(
        default=0.85, ge=0.0, le=1.0,
        description="Winrate threshold for confident skip",
    )
    confidence_winrate_ko: float = Field(
        default=0.75, ge=0.0, le=1.0,
        description="Winrate threshold for ko puzzles (lower -- ko winrates oscillate)",
    )
    confidence_winrate_seki: float = Field(
        default=0.70, ge=0.0, le=1.0,
        description="Winrate threshold for seki puzzles (lower -- balanced winrates)",
    )
    confidence_top_n: int = Field(
        default=1, ge=1, le=10,
        description="Must be in top-N for confident skip",
    )
    visits_per_depth: int = Field(
        default=500, ge=50, le=100000,
        description="MCTS visits per tree-depth query",
    )
    top_n_match: int = Field(
        default=3, ge=1, le=20,
        description="Correct move must be in top-N at each depth",
    )
    depth_base: int = Field(default=3, ge=1, le=20, description="Min validation depth")
    depth_intermediate: int = Field(
        default=5, ge=1, le=20,
        description="Depth for intermediate+ puzzles",
    )
    depth_advanced: int = Field(
        default=7, ge=1, le=20,
        description="Depth for advanced+ puzzles",
    )
    depth_ko: int = Field(default=5, ge=1, le=20, description="Depth for ko-tagged puzzles")
    level_intermediate_threshold: int = Field(
        default=140,
        description="Level ID boundary for intermediate depth",
    )
    level_advanced_threshold: int = Field(
        default=170,
        description="Level ID boundary for advanced depth",
    )
    quick_only_depth_cap: int = Field(
        default=2, ge=0, le=10,
        description="Max depth in quick_only mode",
    )


class FrameEntropyQualityConfig(BaseModel):
    """Entropy-based frame quality check configuration."""
    enabled: bool = True
    variance_threshold: float = 0.15
    entropy_contest_threshold: float = 0.5


class FrameConfig(BaseModel):
    """Frame generation and validation configuration."""
    entropy_quality_check: FrameEntropyQualityConfig = Field(
        default_factory=FrameEntropyQualityConfig,
    )


class HumanSLConfig(BaseModel):
    """HumanSL feature-gated configuration."""
    enabled: bool = False
    model_path: str = ""
    profile_name: str = "humanSLProfile"
    humanSLCalibrateStrength: float | None = None
