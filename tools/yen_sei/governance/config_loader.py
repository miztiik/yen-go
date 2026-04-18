"""Load and validate curation_config.json into a typed object."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from tools.core.go_teaching_constants import MARKER_ONLY_PATTERNS

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[1] / "curation_config.json"


@dataclass(frozen=True)
class ProsePath:
    """Alternative content-shape path for a tier. None = tier has no prose escape."""
    min_correct_explanation_chars: int
    min_refutation_phrase_count: int
    min_causal_phrases: int
    min_technique_mentions: int
    min_english_word_ratio: float


@dataclass(frozen=True)
class TierRule:
    name: str
    min_correct_explanation_chars: int
    min_wrong_explanation_chars: int
    min_explanation_node_count: int
    min_causal_phrases: int
    min_english_word_ratio: float
    min_technique_mentions: int
    prose_path: ProsePath | None = None


@dataclass(frozen=True)
class SourceOverride:
    tier_cap: str  # "gold" | "silver" | "bronze" | "drop"
    weight_multiplier: float
    notes: str


@dataclass(frozen=True)
class ProseFallback:
    enabled: bool
    min_correct_explanation_chars: int
    min_refutation_phrase_count: int
    refutation_phrases: tuple[str, ...]


@dataclass(frozen=True)
class HardGates:
    min_stones: int
    max_stones: int
    valid_board_sizes: frozenset[int]
    min_variations: int
    exclude_full_games: bool
    max_total_moves: int
    prose_fallback: ProseFallback


@dataclass(frozen=True)
class MarkerConfig:
    all_markers: frozenset[str]
    prefix_regex: re.Pattern[str]
    anywhere_regex: re.Pattern[str]
    min_chars_after_strip: int


@dataclass(frozen=True)
class LanguageConfig:
    method: str
    min_ascii_letter_ratio: float
    min_stopword_hits_per_100_chars: float
    stopwords: frozenset[str]
    wordfreq_min_zipf: float
    strip_cjk_via_core: bool


_TIER_ORDER = {"drop": 0, "bronze": 1, "silver": 2, "gold": 3}


@dataclass(frozen=True)
class CurationConfig:
    schema_version: int
    curation_run_id: str
    description: str
    markers: MarkerConfig
    language: LanguageConfig
    hard_gates: HardGates
    tier_rules: tuple[TierRule, ...]  # ordered gold → bronze
    source_overrides: dict[str, SourceOverride]
    filename_pattern: str
    training_weights: dict[str, float]
    split_ratios: dict[str, float]
    dedup_method: str
    dedup_tie_break: str
    raw: dict[str, Any] = field(default_factory=dict)

    def cap_tier(self, tier: str, source: str) -> str:
        """Apply per-source tier_cap. Returns the lower of (tier, cap)."""
        override = self.source_overrides.get(source)
        if not override:
            return tier
        cap = override.tier_cap
        if _TIER_ORDER.get(tier, 0) > _TIER_ORDER.get(cap, 0):
            return cap
        return tier


def _build_marker_config(d: dict[str, Any]) -> MarkerConfig:
    base = set(MARKER_ONLY_PATTERNS) if d.get("use_core_constants", True) else set()
    base.update(m.lower() for m in d.get("additional_markers", []))
    return MarkerConfig(
        all_markers=frozenset(base),
        prefix_regex=re.compile(d["marker_prefix_regex"], re.IGNORECASE),
        anywhere_regex=re.compile(d["marker_anywhere_regex"], re.IGNORECASE),
        min_chars_after_strip=int(d.get("min_chars_after_strip", 20)),
    )


def _build_language_config(d: dict[str, Any]) -> LanguageConfig:
    return LanguageConfig(
        method=d.get("method", "heuristic"),
        min_ascii_letter_ratio=float(d.get("min_ascii_letter_ratio", 0.6)),
        min_stopword_hits_per_100_chars=float(d.get("min_stopword_hits_per_100_chars", 3.0)),
        stopwords=frozenset(s.lower() for s in d.get("stopwords", [])),
        wordfreq_min_zipf=float(d.get("wordfreq_min_zipf", 2.0)),
        strip_cjk_via_core=bool(d.get("strip_cjk_via_core", True)),
    )


def _build_hard_gates(d: dict[str, Any]) -> HardGates:
    pf_raw = d.get("prose_fallback", {}) or {}
    pf = ProseFallback(
        enabled=bool(pf_raw.get("enabled", False)),
        min_correct_explanation_chars=int(pf_raw.get("min_correct_explanation_chars", 150)),
        min_refutation_phrase_count=int(pf_raw.get("min_refutation_phrase_count", 2)),
        refutation_phrases=tuple(str(p).lower() for p in pf_raw.get("refutation_phrases", []) if not str(p).startswith("_")),
    )
    return HardGates(
        min_stones=int(d["min_stones"]),
        max_stones=int(d["max_stones"]),
        valid_board_sizes=frozenset(int(b) for b in d["valid_board_sizes"]),
        min_variations=int(d["min_variations"]),
        exclude_full_games=bool(d.get("exclude_full_games", True)),
        max_total_moves=int(d.get("max_total_moves", 60)),
        prose_fallback=pf,
    )


def _build_tier_rules(d: dict[str, Any]) -> tuple[TierRule, ...]:
    rules = []
    for name in ("gold", "silver", "bronze"):
        if name not in d:
            continue
        r = d[name]
        prose_raw = r.get("prose_path")
        prose: ProsePath | None = None
        if isinstance(prose_raw, dict):
            prose = ProsePath(
                min_correct_explanation_chars=int(prose_raw["min_correct_explanation_chars"]),
                min_refutation_phrase_count=int(prose_raw["min_refutation_phrase_count"]),
                min_causal_phrases=int(prose_raw["min_causal_phrases"]),
                min_technique_mentions=int(prose_raw["min_technique_mentions"]),
                min_english_word_ratio=float(prose_raw["min_english_word_ratio"]),
            )
        rules.append(TierRule(
            name=name,
            min_correct_explanation_chars=int(r["min_correct_explanation_chars"]),
            min_wrong_explanation_chars=int(r["min_wrong_explanation_chars"]),
            min_explanation_node_count=int(r["min_explanation_node_count"]),
            min_causal_phrases=int(r["min_causal_phrases"]),
            min_english_word_ratio=float(r["min_english_word_ratio"]),
            min_technique_mentions=int(r["min_technique_mentions"]),
            prose_path=prose,
        ))
    return tuple(rules)


def _build_source_overrides(d: dict[str, Any]) -> dict[str, SourceOverride]:
    out: dict[str, SourceOverride] = {}
    for src, ov in d.items():
        if src.startswith("_"):  # comment fields
            continue
        out[src] = SourceOverride(
            tier_cap=ov.get("tier_cap", "gold"),
            weight_multiplier=float(ov.get("weight_multiplier", 1.0)),
            notes=ov.get("notes", ""),
        )
    return out


def load_config(path: Path | str | None = None) -> CurationConfig:
    """Load and validate the curation config from disk."""
    config_path = Path(path) if path else DEFAULT_CONFIG_PATH
    raw = json.loads(config_path.read_text(encoding="utf-8"))

    return CurationConfig(
        schema_version=int(raw["schema_version"]),
        curation_run_id=raw["curation_run_id"],
        description=raw.get("description", ""),
        markers=_build_marker_config(raw["marker_patterns"]),
        language=_build_language_config(raw["language"]),
        hard_gates=_build_hard_gates(raw["hard_gates"]),
        tier_rules=_build_tier_rules(raw["tier_rules"]),
        source_overrides=_build_source_overrides(raw["source_overrides"]),
        filename_pattern=raw["filename_convention"]["pattern"],
        training_weights=dict(raw["training_weights"]),
        split_ratios={k: v for k, v in raw["split_ratios"].items() if not k.startswith("_")},
        dedup_method=raw["dedup"]["method"],
        dedup_tie_break=raw["dedup"]["tie_break"],
        raw=raw,
    )
