"""Enrichment config package — composition root.

Defines EnrichmentConfig and provides loader functions, caches,
and path resolution. Domain models live in sub-modules.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

# --- Sub-module imports for EnrichmentConfig field types ---
from config.ai_solve import AiSolveConfig
from config.analysis import (
    AnalysisDefaultsConfig,
    DeepEnrichConfig,
    FrameConfig,
    HumanSLConfig,
    KoAnalysisConfig,
    ModelsConfig,
    TreeValidationConfig,
    VisitTiersConfig,
)
from config.difficulty import (
    DifficultyConfig,
    EloAnchorConfig,
    EscalationConfig,
    OwnershipThresholds,
    QualityGatesConfig,
    QualityWeightsConfig,
    SparsePositionConfig,
    ValidationConfig,
)
from config.infrastructure import (
    CalibrationConfig,
    LoggingExtraConfig,
    PathsConfig,
    TestDefaultsConfig,
)
from config.refutations import RefutationEscalationConfig, RefutationsConfig
from config.teaching import TeachingConfig, TeachingSignalConfig
from config.technique import KoDetectionConfig, TechniqueDetectionConfig

logger = logging.getLogger(__name__)

# Resolve project root: tools/puzzle-enrichment-lab/config/ → … → yen-go/
_CONFIG_PKG_DIR = Path(__file__).resolve().parent
_LAB_DIR = _CONFIG_PKG_DIR.parent
_PROJECT_ROOT = _LAB_DIR.parent.parent

class EnrichmentConfig(BaseModel):
    """Top-level enrichment configuration."""
    model_config = {"populate_by_name": True}

    version: str = Field(default="1.0", alias="schema_version")
    config_min_version: str = Field(
        default="",
        description="Minimum config version required. Logs WARNING if stored version < min.",
    )
    description: str = ""
    last_updated: str = ""
    ownership_thresholds: OwnershipThresholds = Field(
        default_factory=OwnershipThresholds
    )
    validation: ValidationConfig = Field(default_factory=ValidationConfig)
    difficulty: DifficultyConfig = Field(default_factory=DifficultyConfig)
    refutations: RefutationsConfig = Field(default_factory=RefutationsConfig)
    refutation_escalation: RefutationEscalationConfig = Field(
        default_factory=RefutationEscalationConfig
    )
    sparse_position: SparsePositionConfig = Field(
        default_factory=SparsePositionConfig
    )
    escalation: EscalationConfig = Field(default_factory=EscalationConfig)
    quality_gates: QualityGatesConfig = Field(default_factory=QualityGatesConfig)
    analysis_defaults: AnalysisDefaultsConfig = Field(default_factory=AnalysisDefaultsConfig)
    visit_tiers: VisitTiersConfig = Field(default_factory=VisitTiersConfig)
    ko_analysis: KoAnalysisConfig = Field(default_factory=KoAnalysisConfig)
    deep_enrich: DeepEnrichConfig = Field(default_factory=DeepEnrichConfig)
    frame: FrameConfig = Field(default_factory=FrameConfig)

    ai_solve: AiSolveConfig | None = Field(default_factory=AiSolveConfig, description="AI-solve config; defaults to AiSolveConfig() for Phase 0 activation")
    elo_anchor: EloAnchorConfig | None = None
    quality_weights: QualityWeightsConfig = Field(default_factory=QualityWeightsConfig)
    models: ModelsConfig = Field(description="Model name indirection")
    test_defaults: TestDefaultsConfig | None = None
    tree_validation: TreeValidationConfig | None = None
    technique_detection: TechniqueDetectionConfig | None = None
    ko_detection: KoDetectionConfig | None = None
    teaching: TeachingConfig | None = None
    teaching_signal: TeachingSignalConfig | None = None
    calibration: CalibrationConfig | None = None
    logging_config: LoggingExtraConfig | None = Field(default=None, alias="logging")
    paths: PathsConfig | None = None
    humansl: HumanSLConfig = Field(default_factory=HumanSLConfig)

_cached_config: EnrichmentConfig | None = None
_cached_levels: dict[str, int] | None = None
_cached_tag_ids: dict[str, int] | None = None


def load_puzzle_levels(path: Path | None = None) -> dict[str, int]:
    """Load level slug → numeric ID mapping from puzzle-levels.json."""
    if path is None:
        path = _PROJECT_ROOT / "config" / "puzzle-levels.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    return {lv["slug"]: lv["id"] for lv in data["levels"]}


def load_enrichment_config(path: Path | None = None) -> EnrichmentConfig:
    """Load and cache the enrichment config from katago-enrichment.json."""
    global _cached_config
    if _cached_config is not None and path is None:
        return _cached_config

    if path is None:
        path = _PROJECT_ROOT / "config" / "katago-enrichment.json"

    logger.info("Loading config from: %s (exists=%s, size=%d)", path, path.exists(), path.stat().st_size if path.exists() else -1)
    raw = path.read_text(encoding="utf-8")
    if not raw.strip():
        raise ValueError(
            f"Config file is empty: {path}\n"
            f"Expected: {_PROJECT_ROOT / 'config' / 'katago-enrichment.json'}"
        )
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Invalid JSON in config: {path}\n"
            f"First 200 chars: {raw[:200]!r}\n"
            f"JSON error: {exc}"
        ) from exc
    config = EnrichmentConfig(**data)

    # T62: Version-gate — warn if stored version < min required
    if config.config_min_version and config.version < config.config_min_version:
        logger.warning(
            "Config version %s is below minimum required %s — "
            "some features may not work correctly. Consider updating config.",
            config.version, config.config_min_version,
        )

    if path == _PROJECT_ROOT / "config" / "katago-enrichment.json":
        _cached_config = config

    from log_config import strip_workspace_root
    logger.info(
        "Loaded enrichment config v%s",
        config.version,
        extra={"config_path": strip_workspace_root(path)},
    )
    return config


def get_level_id(slug: str) -> int:
    """Get numeric level ID for a slug, from puzzle-levels.json."""
    global _cached_levels
    if _cached_levels is None:
        _cached_levels = load_puzzle_levels()
    return _cached_levels[slug]


def clear_cache() -> None:
    """Clear cached config, levels, tag IDs, and teaching comments."""
    global _cached_config, _cached_levels, _cached_tag_ids
    _cached_config = None
    _cached_levels = None
    _cached_tag_ids = None
    # Clear teaching comments cache via its public API
    from config.teaching import clear_teaching_cache
    clear_teaching_cache()
    # MH-2: Invalidate _get_cfg lru_cache so next access reloads config
    from config.helpers import _get_cfg
    _get_cfg.cache_clear()


def resolve_path(config: EnrichmentConfig, path_key: str) -> Path:
    """Resolve a config path relative to the lab tool root."""
    defaults = PathsConfig()
    value = getattr(config.paths, path_key, None) if config.paths else None
    if value is None or not isinstance(value, str):
        value = getattr(defaults, path_key)
    return _LAB_DIR / value


def load_tag_ids(path: Path | None = None) -> dict[str, int]:
    """Load tag slug → numeric ID mapping from config/tags.json."""
    global _cached_tag_ids
    if _cached_tag_ids is not None and path is None:
        return _cached_tag_ids

    if path is None:
        path = _PROJECT_ROOT / "config" / "tags.json"

    data = json.loads(path.read_text(encoding="utf-8"))
    tags = data.get("tags", {})
    result = {slug: info["id"] for slug, info in tags.items() if "id" in info}

    if path == _PROJECT_ROOT / "config" / "tags.json":
        _cached_tag_ids = result

    logger.debug("Loaded %d tag IDs from %s", len(result), path)
    return result


def get_tag_id(slug: str) -> int:
    """Get numeric tag ID for a slug from config/tags.json."""
    return load_tag_ids()[slug]
