"""Data models for puzzle intent resolution.

Frozen dataclasses for objectives (loaded from config) and match results.
All types are immutable for safe sharing across matchers.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class MatchTier(str, Enum):
    """Which matching strategy produced the result."""

    EXACT = "exact"
    KEYWORD = "keyword"
    SEMANTIC = "semantic"
    NONE = "none"


class ObjectiveCategory(str, Enum):
    """Top-level objective category."""

    MOVE_ORDER = "MOVE_ORDER"
    LIFE_AND_DEATH = "LIFE_AND_DEATH"
    CAPTURING = "CAPTURING"
    SHAPE = "SHAPE"
    FIGHT = "FIGHT"
    TESUJI = "TESUJI"
    ENDGAME = "ENDGAME"


@dataclass(frozen=True)
class Objective:
    """Single puzzle objective definition from config/puzzle-objectives.json."""

    objective_id: str
    slug: str
    name: str
    category: ObjectiveCategory
    side: str | None
    objective_type: str
    result_condition: str | None
    engine_verifiable: bool
    aliases: tuple[str, ...]


@dataclass(frozen=True)
class IntentResult:
    """Result of intent resolution for a single text input."""

    objective_id: str | None
    objective: Objective | None
    matched_alias: str | None
    confidence: float
    match_tier: MatchTier
    cleaned_text: str
    raw_text: str

    @property
    def matched(self) -> bool:
        """True if an objective was matched."""
        return self.objective_id is not None

    def to_dict(self) -> dict:
        """JSON-serializable dict for pipeline output."""
        return {
            "objective_id": self.objective_id,
            "slug": self.objective.slug if self.objective else None,
            "name": self.objective.name if self.objective else None,
            "matched_alias": self.matched_alias,
            "confidence": self.confidence,
            "match_tier": self.match_tier.value,
            "matched": self.matched,
            "cleaned_text": self.cleaned_text,
            "raw_text": self.raw_text,
        }

    @classmethod
    def no_match(cls, raw_text: str, cleaned_text: str) -> IntentResult:
        """Factory for no-match results."""
        return cls(
            objective_id=None,
            objective=None,
            matched_alias=None,
            confidence=0.0,
            match_tier=MatchTier.NONE,
            cleaned_text=cleaned_text,
            raw_text=raw_text,
        )
