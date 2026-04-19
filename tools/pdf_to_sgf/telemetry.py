"""Structured telemetry for PDF-to-SGF pipeline runs.

Provides a RunLogger that:
- Collects typed event payloads (from models.py)
- Writes them as JSONL to a log file
- Produces a RunSummary with yield/review report at completion
- Generates human-readable report for manual validation

Usage:
    from tools.pdf_to_sgf.telemetry import RunLogger
    from tools.pdf_to_sgf.models import PageExtractedEvent

    logger = RunLogger(output_dir=Path("./output"))
    logger.emit(PageExtractedEvent(page_number=1, ...))
    summary = logger.finalize(pdf_path="book.pdf")
    print(logger.format_report(summary))
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

from tools.pdf_to_sgf.models import (
    BaseEvent,
    BoardConfidence,
    BoardDetectedEvent,
    BoardRecognizedEvent,
    BoardSkippedEvent,
    ColumnDetectedEvent,
    ErrorEvent,
    EventType,
    MatchConfidence,
    MatchFoundEvent,
    PageExtractedEvent,
    RunStartEvent,
    RunSummary,
    SgfGeneratedEvent,
    SgfRejectedEvent,
    SgfValidatedEvent,
)

log = logging.getLogger(__name__)


class RunLogger:
    """Accumulates pipeline events and writes JSONL telemetry."""

    def __init__(self, output_dir: Path | None = None) -> None:
        self.events: list[BaseEvent] = []
        self.output_dir = output_dir
        self._start_time = time.monotonic()
        self._log_file: Path | None = None
        # Per-page tracking for report
        self._page_boards: dict[int, list[dict[str, Any]]] = {}

        if output_dir:
            output_dir.mkdir(parents=True, exist_ok=True)
            self._log_file = output_dir / "run.jsonl"
            # Truncate from any prior run
            self._log_file.write_text("", encoding="utf-8")

    def emit(self, event: BaseEvent) -> None:
        """Record an event and optionally append to JSONL file."""
        self.events.append(event)

        if self._log_file is not None:
            with self._log_file.open("a", encoding="utf-8") as f:
                f.write(event.model_dump_json() + "\n")

        log.debug("[TELEM] %s", event.event_type.value)

    def track_page_board(self, page_number: int, board_info: dict[str, Any]) -> None:
        """Track a board result for per-page summary."""
        if page_number not in self._page_boards:
            self._page_boards[page_number] = []
        self._page_boards[page_number].append(board_info)

    def finalize(self, pdf_path: str, key_path: str = "") -> RunSummary:
        """Build and emit the final RunSummary with full yield report."""
        elapsed = time.monotonic() - self._start_time

        pages = sum(1 for e in self.events if e.event_type == EventType.PAGE_EXTRACTED)
        columns = sum(1 for e in self.events if e.event_type == EventType.COLUMN_DETECTED)
        boards_detected = sum(1 for e in self.events if e.event_type == EventType.BOARD_DETECTED)
        boards_skipped = sum(1 for e in self.events if e.event_type == EventType.BOARD_SKIPPED)
        boards_recognized = sum(1 for e in self.events if e.event_type == EventType.BOARD_RECOGNIZED)
        matches = sum(1 for e in self.events if e.event_type == EventType.MATCH_FOUND)
        sgf_gen = sum(1 for e in self.events if e.event_type == EventType.SGF_GENERATED)
        sgf_valid = sum(1 for e in self.events if e.event_type == EventType.SGF_VALIDATED)
        sgf_reject = sum(1 for e in self.events if e.event_type == EventType.SGF_REJECTED)
        errors = sum(1 for e in self.events if e.event_type == EventType.ERROR)

        # Average confidences
        board_confs = [
            e.confidence.overall
            for e in self.events
            if isinstance(e, BoardRecognizedEvent)
        ]
        match_confs = [
            e.confidence.overall
            for e in self.events
            if isinstance(e, MatchFoundEvent)
        ]

        # SGFs with warnings (need review)
        review_needed = sum(
            1 for e in self.events
            if isinstance(e, SgfValidatedEvent) and e.warnings > 0
        )

        # Yield rate
        yield_rate = 0.0
        if boards_detected > 0:
            yield_rate = round(sgf_valid / boards_detected, 3)

        # Per-page summary
        page_summary: list[dict[str, Any]] = []
        for pg_num in sorted(self._page_boards.keys()):
            boards = self._page_boards[pg_num]
            page_summary.append({
                "page": pg_num,
                "boards": len(boards),
                "details": boards,
            })

        summary = RunSummary(
            pdf_path=pdf_path,
            key_path=key_path,
            pages_processed=pages,
            columns_detected=columns,
            boards_detected=boards_detected,
            boards_skipped=boards_skipped,
            boards_recognized=boards_recognized,
            matches_found=matches,
            sgf_generated=sgf_gen,
            sgf_validated=sgf_valid,
            sgf_rejected=sgf_reject,
            sgf_failed=errors,
            errors=errors,
            duration_seconds=round(elapsed, 2),
            avg_board_confidence=round(sum(board_confs) / len(board_confs), 3) if board_confs else 0.0,
            avg_match_confidence=round(sum(match_confs) / len(match_confs), 3) if match_confs else 0.0,
            yield_rate=yield_rate,
            review_needed=review_needed,
            page_summary=page_summary,
        )

        self.emit(summary)
        return summary

    @property
    def error_count(self) -> int:
        return sum(1 for e in self.events if e.event_type == EventType.ERROR)

    def get_events(self, event_type: EventType) -> list[BaseEvent]:
        return [e for e in self.events if e.event_type == event_type]

    @staticmethod
    def format_report(summary: RunSummary) -> str:
        """Format a human-readable yield report for the run.

        Designed for manual validation — shows source, processing
        stats, yield rate, and items needing review.
        """
        lines: list[str] = []
        lines.append("=" * 60)
        lines.append("PDF-to-SGF Conversion Report")
        lines.append("=" * 60)
        lines.append(f"Source PDF:     {summary.pdf_path}")
        if summary.key_path:
            lines.append(f"Answer PDF:     {summary.key_path}")
        lines.append(f"Duration:       {summary.duration_seconds:.1f}s")
        lines.append("")

        lines.append("--- Processing Summary ---")
        lines.append(f"Pages processed:     {summary.pages_processed}")
        if summary.columns_detected > 0:
            lines.append(f"Columns detected:    {summary.columns_detected}")
        lines.append(f"Board regions found: {summary.boards_detected}")
        if summary.boards_skipped > 0:
            lines.append(f"Regions skipped:     {summary.boards_skipped} (failed grid filter)")
        lines.append(f"Boards recognized:   {summary.boards_recognized}")
        if summary.matches_found > 0:
            lines.append(f"Matches found:       {summary.matches_found}")
        lines.append("")

        lines.append("--- Yield ---")
        lines.append(f"SGFs generated:  {summary.sgf_generated}")
        lines.append(f"SGFs validated:  {summary.sgf_validated}")
        if summary.sgf_rejected > 0:
            lines.append(f"SGFs rejected:   {summary.sgf_rejected}")
        # Yield rate: validated / recognized (not all detected, which includes answer pages)
        if summary.boards_recognized > 0:
            rate = summary.sgf_validated / summary.boards_recognized
            lines.append(f"Yield rate:      {rate:.0%} "
                         f"({summary.sgf_validated}/{summary.boards_recognized} recognized boards)")
        lines.append("")

        lines.append("--- Quality ---")
        lines.append(f"Avg board confidence: {summary.avg_board_confidence:.0%}")
        if summary.avg_match_confidence > 0:
            lines.append(f"Avg match confidence: {summary.avg_match_confidence:.0%}")
        lines.append(f"Errors:               {summary.errors}")
        if summary.review_needed > 0:
            lines.append(f"Review needed:        {summary.review_needed} SGFs have warnings")
        lines.append("")

        # Per-page breakdown
        if summary.page_summary:
            lines.append("--- Per-Page Breakdown ---")
            warning_details: list[tuple[str, list[str]]] = []
            for pg in summary.page_summary:
                page_num = pg["page"]
                board_count = pg["boards"]
                lines.append(f"  Page {page_num}: {board_count} board(s)")
                for b in pg.get("details", []):
                    status = b.get("status", "")
                    label = b.get("label", "")
                    conf = b.get("confidence", 0)
                    sgf_file = b.get("sgf_file", "")
                    validation = b.get("validation", "")
                    codes = b.get("warning_codes", [])
                    yield_num = b.get("yield_number")
                    prefix = f"    - #{yield_num}" if yield_num else "    -"
                    detail = f"{prefix} {label}" if label else prefix
                    if sgf_file:
                        detail += f" -> {sgf_file}"
                    if conf:
                        detail += f" (conf={conf:.0%})"
                    if validation:
                        detail += f" [{validation}]"
                    if status:
                        detail += f" {status}"
                    lines.append(detail)
                    if codes:
                        warning_details.append((sgf_file, codes))
            lines.append("")

            if warning_details:
                lines.append("--- Warnings Detail ---")
                for sgf_file, codes in warning_details:
                    lines.append(f"  {sgf_file}: {', '.join(codes)}")
                lines.append("")

        lines.append("=" * 60)
        return "\n".join(lines)
