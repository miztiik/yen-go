"""Instinct classification result model."""

from __future__ import annotations

from dataclasses import dataclass, field

# Tsumego-relevant instincts (5 of 8 from PLNech/gogogo; filtered per NG-8)
INSTINCT_TYPES: frozenset[str] = frozenset({
    "push", "hane", "cut", "descent", "extend",
})

# Confidence tier boundaries
TIER_HIGH = "HIGH"
TIER_MEDIUM = "MEDIUM"
TIER_LOW = "LOW"


def confidence_tier(confidence: float) -> str:
    """Map a confidence value to a tier label."""
    if confidence >= 0.75:
        return TIER_HIGH
    if confidence >= 0.55:
        return TIER_MEDIUM
    return TIER_LOW


@dataclass
class InstinctResult:
    """Output of instinct classification for a single move.

    Attributes:
        instinct: One of INSTINCT_TYPES (push/hane/cut/descent/extend).
        confidence: Per-position confidence (0.0-1.0), computed from
            geometric evidence strength — not a fixed threshold.
        evidence: Human-readable explanation of classification.
        tier: HIGH/MEDIUM/LOW derived from confidence value.
        is_primary: True if this is the selected primary instinct.
    """
    instinct: str
    confidence: float
    evidence: str
    tier: str = field(default="", init=False)
    is_primary: bool = False

    def __post_init__(self) -> None:
        if not self.tier:
            self.tier = confidence_tier(self.confidence)
