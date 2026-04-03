"""Teaching comment config models and loader.

Groups: teaching thresholds, teaching comment entries, wrong-move
templates, signal templates, assembly rules, annotation policy,
and the teaching comments loader.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Resolve project root: tools/puzzle-enrichment-lab/config/ → tools/puzzle-enrichment-lab/ → tools/ → yen-go/
_CONFIG_DIR = Path(__file__).resolve().parent
_LAB_DIR = _CONFIG_DIR.parent
_PROJECT_ROOT = _LAB_DIR.parent.parent


class TeachingConfig(BaseModel):
    """Teaching comment generation thresholds (Plan 010, D41)."""
    description: str = ""
    non_obvious_policy: float = Field(default=0.10, ge=0.0, le=1.0)
    ko_delta_threshold: float = Field(default=0.12, ge=0.0, le=1.0)
    capture_depth_threshold: int = Field(default=1, ge=0, le=20)
    significant_loss_threshold: float = Field(default=0.5, ge=0.0, le=1.0)
    moderate_loss_threshold: float = Field(default=0.2, ge=0.0, le=1.0)
    use_opponent_policy: bool = Field(
        default=False,
        description="PI-10: Append opponent-response phrase to wrong-move comments. "
        "When True, uses PV[0] from refutation analysis to name opponent's punishing action. "
        "Feature-gated: False = no change to current behavior.",
    )


class TeachingCommentEntry(BaseModel):
    """A single tag's teaching comment configuration."""
    comment: str
    technique_phrase: str = ""
    vital_move_comment: str = ""
    hint_text: str
    min_confidence: str = Field(pattern=r"^(HIGH|CERTAIN)$")
    alias_comments: dict[str, str] | None = None


class WrongMoveTemplate(BaseModel):
    """A wrong-move comment template with its selection condition."""
    condition: str
    comment: str
    guard: str | None = None


class DeltaAnnotation(BaseModel):
    """Delta annotation threshold and template for wrong-move severity."""
    threshold: float = Field(ge=0.0, le=1.0)
    template: str


class WrongMoveComments(BaseModel):
    """Wrong-move comment templates and delta annotations."""
    templates: list[WrongMoveTemplate]
    delta_annotations: dict[str, DeltaAnnotation]
    almost_correct_threshold: float = Field(
        default=0.05, ge=0.0, le=1.0,
        description="Delta below this threshold triggers 'almost correct' instead of 'Wrong'",
    )


class SignalTemplates(BaseModel):
    """Layer 2 signal phrase templates."""
    vital_point: str = ""
    forcing: str = ""
    non_obvious: str = ""
    unique_solution: str = ""
    sacrifice_setup: str = ""
    opponent_takes_vital: str = ""


class AssemblyRules(BaseModel):
    """Rules for composing Layer 1 + Layer 2 into final comment."""
    composition: str = "{technique_phrase} \u2014 {signal_phrase}."
    max_words: int = 15
    overflow_strategy: str = "signal_replaces_mechanism"
    parenthetical_counting: str = ""
    coord_token: str = ""


class AnnotationPolicy(BaseModel):
    """Policy controlling comment placement on solution tree nodes."""
    max_correct_node_annotations: int = 2
    vital_move_annotation_scope: str = "strict_only"
    alias_placement: str = "vital_move_preferred"
    max_causal_wrong_moves: int = 3
    causal_wrong_move_ranking: str = "refutation_depth_desc"


class TeachingCommentsConfig(BaseModel):
    """Top-level config model for config/teaching-comments.json."""
    model_config = {"populate_by_name": True}
    version: str = Field(alias="schema_version")
    description: str = ""
    last_updated: str = ""
    design_principles: dict[str, str] = Field(default_factory=dict)
    correct_move_comments: dict[str, TeachingCommentEntry]
    wrong_move_comments: WrongMoveComments
    signal_templates: SignalTemplates = Field(default_factory=SignalTemplates)
    assembly_rules: AssemblyRules = Field(default_factory=AssemblyRules)
    annotation_policy: AnnotationPolicy = Field(default_factory=AnnotationPolicy)


class InstinctConfig(BaseModel):
    """Configuration for instinct classification (G-3)."""
    enabled: bool = Field(
        default=False,
        description="Gate for instinct phrases in hints/comments. "
        "Default False per C-3: flip to True after AC-4 golden-set calibration confirms >=70% accuracy.",
    )
    min_confidence_to_log: float = Field(
        default=0.40,
        description="Minimum confidence to include an instinct in ctx.instinct_results for logging/calibration.",
    )
    min_confidence_to_surface: float = Field(
        default=0.65,
        description="Minimum confidence for an instinct to be eligible as primary (hint/comment display).",
    )
    clarity_threshold: float = Field(
        default=0.15,
        description="Minimum gap between #1 and #2 confidence to designate a primary instinct.",
    )
    max_instincts_before_ambiguous: int = Field(
        default=4,
        description="If >= this many instincts detected, suppress primary (ambiguous position).",
    )
    confidence_thresholds: dict[str, float] = Field(
        default_factory=lambda: {
            "push": 0.7,
            "hane": 0.7,
            "cut": 0.8,
            "descent": 0.6,
            "extend": 0.5,
        },
        description="Legacy minimum confidence per instinct type. Superseded by per-position tier scoring.",
    )
    instinct_phrases: dict[str, str] = Field(
        default_factory=lambda: {
            "push": "Push",
            "hane": "Hane",
            "cut": "Cut",
            "descent": "Descend",
            "extend": "Extend",
        },
        description="Short display phrase per instinct for hints/comments.",
    )


# Module-level default instances for direct access
_DEFAULT_INSTINCT_CONFIG: InstinctConfig | None = None


def get_instinct_config() -> InstinctConfig:
    """Get the default instinct config (cached)."""
    global _DEFAULT_INSTINCT_CONFIG
    if _DEFAULT_INSTINCT_CONFIG is None:
        _DEFAULT_INSTINCT_CONFIG = InstinctConfig()
    return _DEFAULT_INSTINCT_CONFIG


# --- Teaching comments config loader ---

_cached_teaching_comments: TeachingCommentsConfig | None = None
_cached_raw_teaching_config: dict | None = None


def clear_teaching_cache() -> None:
    """Clear the cached teaching comments config (Pydantic and raw)."""
    global _cached_teaching_comments, _DEFAULT_INSTINCT_CONFIG, _cached_raw_teaching_config
    _cached_teaching_comments = None
    _DEFAULT_INSTINCT_CONFIG = None
    _cached_raw_teaching_config = None


def load_raw_teaching_config() -> dict:
    """Load raw teaching-comments.json as dict (bypasses Pydantic model).

    Used by comment_assembler for opponent_response_templates lookup.
    Cache is cleared by clear_teaching_cache().
    """
    global _cached_raw_teaching_config
    if _cached_raw_teaching_config is not None:
        return _cached_raw_teaching_config
    path = _PROJECT_ROOT / "config" / "teaching-comments.json"
    _cached_raw_teaching_config = json.loads(path.read_text(encoding="utf-8"))
    return _cached_raw_teaching_config


def load_teaching_comments_config(
    path: Path | None = None,
) -> TeachingCommentsConfig:
    """Load and cache the teaching comments config.

    Args:
        path: Optional override path. If None, uses config/teaching-comments.json

    Returns:
        Validated TeachingCommentsConfig
    """
    global _cached_teaching_comments
    if _cached_teaching_comments is not None and path is None:
        return _cached_teaching_comments

    if path is None:
        path = _PROJECT_ROOT / "config" / "teaching-comments.json"

    data = json.loads(path.read_text(encoding="utf-8"))
    config = TeachingCommentsConfig(**data)

    if path == _PROJECT_ROOT / "config" / "teaching-comments.json":
        _cached_teaching_comments = config

    logger.debug(
        "Loaded teaching comments config v%s (%d tags)",
        config.version,
        len(config.correct_move_comments),
    )
    return config


class TeachingSignalConfig(BaseModel):
    """Configuration for structured teaching signal emission (R-1).

    Controls which KataGo-derived signals are emitted in the
    teaching_signals payload on AiAnalysisResult. Thresholds are
    config-driven per governance RC-1/RC-2/RC-3.
    """

    enabled: bool = Field(
        default=False,
        description="Master gate for teaching signal emission. "
        "False = no teaching_signals payload computed.",
    )
    max_wrong_moves: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Max wrong moves to include in teaching signal payload.",
    )
    instructiveness_threshold: float = Field(
        default=0.05,
        ge=0.0,
        le=1.0,
        description="RC-2: Minimum abs(delta) for a wrong move to be 'instructive'.",
    )
    seki_closeness_threshold: float = Field(
        default=0.9,
        ge=0.0,
        le=1.0,
        description="RC-1: position_closeness above this bypasses instructiveness threshold (seki exception).",
    )
    ownership_delta_threshold: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="RC-3: Only emit ownership_delta_max when above this value.",
    )
