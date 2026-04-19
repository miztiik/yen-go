"""Pydantic models for PDF-to-SGF pipeline events and data.

Provides validated, serializable models for:
- Configuration (extraction, detection, matching)
- Confidence scoring (board, match, puzzle-level)
- Structured event payloads (JSONL telemetry)
- Run summaries

All events inherit from BaseEvent which provides event_type + timestamp.
Use `.model_dump_json()` for JSONL serialization.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class EventType(str, Enum):
    """Structured event types emitted during a pipeline run."""

    RUN_START = "run_start"
    PAGE_EXTRACTED = "page_extracted"
    COLUMN_DETECTED = "column_detected"
    BOARD_DETECTED = "board_detected"
    BOARD_SKIPPED = "board_skipped"
    BOARD_RECOGNIZED = "board_recognized"
    MATCH_ATTEMPTED = "match_attempted"
    MATCH_FOUND = "match_found"
    SGF_GENERATED = "sgf_generated"
    SGF_VALIDATED = "sgf_validated"
    SGF_REJECTED = "sgf_rejected"
    ANSWER_SECTION_DETECTED = "answer_section_detected"
    RUN_COMPLETE = "run_complete"
    ERROR = "error"


class ExtractionSource(str, Enum):
    EMBEDDED = "embedded"
    RENDERED = "rendered"


class MatchStrategy(str, Enum):
    JACCARD = "jaccard"
    POSITIONAL = "positional"


# ---------------------------------------------------------------------------
# Confidence models
# ---------------------------------------------------------------------------


class BoardConfidence(BaseModel):
    """Confidence metrics for a single recognized board."""

    grid_completeness: float = Field(
        0.0, ge=0, le=1,
        description="Grid completeness: (n_rows + n_cols) / (2 * max(n_rows, n_cols))",
    )
    stone_density: float = Field(
        0.0, ge=0, le=1,
        description="Occupied intersections / total intersections",
    )
    edge_fraction: float = Field(
        0.0, ge=0, le=1,
        description="Detected edges / expected edges based on board position (1.0 if no edges expected)",
    )
    overall: float = Field(
        0.0, ge=0, le=1,
        description="Weighted composite: 0.5*grid + 0.3*edge + 0.2*density",
    )


class MatchConfidence(BaseModel):
    """Confidence metrics for a problem-answer match."""

    jaccard_similarity: float = Field(0.0, ge=0, le=1)
    stone_count_ratio: float = Field(
        0.0, ge=0, le=1,
        description="min(p_stones, a_stones) / max(p_stones, a_stones)",
    )
    solution_plausibility: float = Field(
        0.0, ge=0, le=1,
        description="1.0 if 1-10 solution moves, scaled down outside that range",
    )
    moves_ordered: float = Field(
        0.0, ge=0, le=1,
        description="Fraction of solution moves with digit-detected order",
    )
    overall: float = Field(
        0.0, ge=0, le=1,
        description="Weighted composite: 0.4*jaccard + 0.2*ratio + 0.2*plausibility + 0.2*ordered",
    )


class PuzzleConfidence(BaseModel):
    """Composite confidence for a generated puzzle SGF."""

    board: BoardConfidence
    match: MatchConfidence | None = None
    overall: float = Field(0.0, ge=0, le=1)


# ---------------------------------------------------------------------------
# Event payloads
# ---------------------------------------------------------------------------


class BaseEvent(BaseModel):
    """Base for all pipeline events. Provides type + ISO timestamp."""

    event_type: EventType
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class RunStartEvent(BaseEvent):
    """Emitted when a pipeline run begins."""

    event_type: EventType = EventType.RUN_START
    pdf_path: str
    key_path: str = ""
    pages: str = ""  # e.g. "3-5" or "" for all
    preset: str = "default"
    command: str = "convert"


class PageExtractedEvent(BaseEvent):
    """Emitted after extracting a page image from the PDF."""

    event_type: EventType = EventType.PAGE_EXTRACTED
    pdf_source: str = ""
    page_number: int
    total_pages: int = 0
    source: ExtractionSource
    width: int
    height: int


class ColumnDetectedEvent(BaseEvent):
    """Emitted after detecting column layout on a page."""

    event_type: EventType = EventType.COLUMN_DETECTED
    page_number: int
    column_count: int
    column_widths: list[int] = []


class BoardDetectedEvent(BaseEvent):
    """Emitted after detecting a board region on a page."""

    event_type: EventType = EventType.BOARD_DETECTED
    pdf_source: str = ""
    page_number: int
    board_index: int
    bbox: tuple[int, int, int, int]
    width: int
    height: int
    detection_confidence: float = 0.0


class BoardSkippedEvent(BaseEvent):
    """Emitted when a candidate region fails grid pre-filter."""

    event_type: EventType = EventType.BOARD_SKIPPED
    page_number: int
    bbox: tuple[int, int, int, int]
    grid_lines: int
    reason: str


class BoardRecognizedEvent(BaseEvent):
    """Emitted after recognizing stones on a detected board."""

    event_type: EventType = EventType.BOARD_RECOGNIZED
    page_number: int
    board_index: int
    grid_rows: int
    grid_cols: int
    black_stones: int
    white_stones: int
    confidence: BoardConfidence


class MatchAttemptedEvent(BaseEvent):
    """Emitted when a match is attempted between problem and answer."""

    event_type: EventType = EventType.MATCH_ATTEMPTED
    problem_index: int
    answer_index: int
    similarity: float
    matched: bool
    strategy: MatchStrategy


class MatchFoundEvent(BaseEvent):
    """Emitted when a successful match is found."""

    event_type: EventType = EventType.MATCH_FOUND
    problem_index: int
    answer_index: int
    similarity: float
    strategy: MatchStrategy
    solution_moves: int
    moves_with_order: int
    confidence: MatchConfidence
    problem_label: str = ""


class SgfGeneratedEvent(BaseEvent):
    """Emitted after writing an SGF file."""

    event_type: EventType = EventType.SGF_GENERATED
    output_file: str
    pdf_source: str = ""
    page_number: int = 0
    black_stones: int
    white_stones: int
    solution_moves: int
    has_solution_tree: bool
    problem_label: str = ""
    yield_number: int = 0
    book_label: str = ""
    confidence: PuzzleConfidence


class SgfValidatedEvent(BaseEvent):
    """Emitted when a generated SGF passes validation."""

    event_type: EventType = EventType.SGF_VALIDATED
    output_file: str
    board_size: int
    black_stones: int
    white_stones: int
    solution_moves: int
    warnings: int = 0
    warning_codes: list[str] = []


class SgfRejectedEvent(BaseEvent):
    """Emitted when a generated SGF fails validation."""

    event_type: EventType = EventType.SGF_REJECTED
    output_file: str
    error_count: int
    warning_count: int
    issue_codes: list[str] = []
    detail: str = ""


class AnswerSectionDetectedEvent(BaseEvent):
    """Emitted when answer section auto-detection finds a marker."""

    event_type: EventType = EventType.ANSWER_SECTION_DETECTED
    page_number: int
    marker_text: str
    confidence: float = 1.0


class ErrorEvent(BaseEvent):
    """Emitted on recoverable errors during processing."""

    event_type: EventType = EventType.ERROR
    stage: str  # "extraction", "detection", "recognition", "matching", "sgf_gen"
    detail: str
    page_number: int = 0
    board_index: int = 0


class RunSummary(BaseEvent):
    """Final summary emitted at end of run with yield/review report."""

    event_type: EventType = EventType.RUN_COMPLETE
    pdf_path: str
    key_path: str = ""
    pages_processed: int = 0
    columns_detected: int = 0
    boards_detected: int = 0
    boards_skipped: int = 0
    boards_recognized: int = 0
    matches_found: int = 0
    sgf_generated: int = 0
    sgf_validated: int = 0
    sgf_rejected: int = 0
    sgf_failed: int = 0
    errors: int = 0
    duration_seconds: float = 0.0
    avg_board_confidence: float = 0.0
    avg_match_confidence: float = 0.0
    # Yield metrics
    yield_rate: float = 0.0  # sgf_validated / boards_detected (if >0)
    review_needed: int = 0   # sgf with warnings that need manual review
    # Per-page breakdown for manual validation
    page_summary: list[dict[str, Any]] = []
