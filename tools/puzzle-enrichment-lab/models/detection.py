"""Detection result model — output of individual technique detectors."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class DetectionResult:
    """Per-detector output."""
    detected: bool
    confidence: float  # 0.0-1.0
    tag_slug: str      # matches config/tags.json slug
    evidence: str      # human-readable explanation
