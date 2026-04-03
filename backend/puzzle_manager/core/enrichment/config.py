"""
Configuration for enrichment processing.

Provides EnrichmentConfig dataclass for controlling enrichment behavior,
and structured logging dataclasses for diagnostics.
"""

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Literal

# Reason codes for enrichment failures/skips
HINT_REASON_CODES = {
    "no_stones": "Board has no black or white stones",
    "no_solution_tree": "Puzzle lacks a solution tree",
    "no_matching_tags": "No tags match known techniques",
    "insufficient_techniques": "Position too complex for analysis",
    "timeout": "Operation exceeded time limit",
}


@dataclass
class HintOperationLog:
    """Log entry for hint generation (YH1, YH2, YH3)."""

    status: Literal["success", "partial", "failed"] = "failed"
    yh1_generated: bool = False
    yh1_reason: str | None = None  # Only if not generated
    yh1_value: str | None = None  # Only if generated
    yh2_generated: bool = False
    yh2_reason: str | None = None
    yh2_value: str | None = None
    yh3_generated: bool = False
    yh3_reason: str | None = None
    yh3_value: str | None = None
    final_hint_count: int = 0  # Number of hints in compact list
    duration_ms: int = 0
    errors: list[str] = field(default_factory=list)


@dataclass
class EnrichmentOperationLog:
    """Complete structured log entry for enrichment operations."""

    puzzle_id: str = ""
    stage: str = "enrichment"
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    enrichment_operations: dict = field(default_factory=dict)
    overall_status: Literal["success", "partial", "failed"] = "success"
    total_duration_ms: int = 0
    errors: list[str] = field(default_factory=list)

    def to_json(self) -> str:
        """Serialize to JSON for logging."""
        return json.dumps(asdict(self), separators=(",", ":"))


@dataclass
class EnrichmentConfig:
    """Configuration for enrichment processing.

    Attributes:
        enable_hints: Generate YH compact hints property.
        enable_region: Generate YC board region property.
        enable_ko: Generate YK ko context property.
        enable_move_order: Generate YO move order flexibility property.
        enable_refutation: Generate YR refutation moves property.
        include_liberty_analysis: Add liberty info to YH1 hints.
        include_technique_reasoning: Add "why" explanation to YH2 hints.
        include_consequence: Add "what if" text to YH3 hints.
        verbose: Enable verbose logging of enrichment decisions.
        preserve_root_comment: Preserve root C[] in enriched output (default: True).

    Note:
        Region detection thresholds (corner/edge) are now computed
        proportionally from board_size inside ``detect_region()``.
        They are no longer configurable here.
    """

    enable_hints: bool = True
    enable_region: bool = True
    enable_ko: bool = True
    enable_move_order: bool = True
    enable_refutation: bool = True
    include_liberty_analysis: bool = True
    include_technique_reasoning: bool = True
    include_consequence: bool = True
    verbose: bool = True
    preserve_root_comment: bool = True  # Preserve root C[] in enriched output
