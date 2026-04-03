"""
Structured logging for download tools.

Provides both human-readable console output and structured JSON file logging
for programmatic analysis.

Log Sequence Pattern:
    1. RUN_START - Starting run with config
    2. For each page/batch:
       a. API_WAIT - Wait before request (with delay)
       b. API_REQUEST - Fetching URL
       c. ITEM_SAVE / ITEM_SKIP / ITEM_ERROR - Per-item status
       d. PROGRESS - Running totals
    3. RUN_END - Final summary

Usage:
    from tools.core.logging import setup_logging, StructuredLogger, EventType

    logger = setup_logging(output_dir, "ogs", verbose=True)
    logger.run_start(max_items=100, output_dir=str(output_dir))
    logger.api_request(url, "page 1")
    logger.item_save("puzzle-123", "batch-001/puzzle-123.sgf")
    logger.progress(downloaded=10, skipped=2, errors=0, page=1)
    logger.run_end(downloaded=10, skipped=2, errors=0, duration_sec=120.5)
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from tools.core.paths import rel_path


def _enable_windows_ansi() -> None:
    """Enable ANSI escape sequence processing on Windows cmd.

    Windows cmd.exe does not process ANSI escape codes by default.
    This sets the ENABLE_VIRTUAL_TERMINAL_PROCESSING flag (0x0004)
    on stdout so ``\\033[32m`` etc. render as colors instead of
    appearing as raw bytes.
    """
    if sys.platform != "win32":
        return
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        handle = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
        mode = ctypes.c_ulong()
        kernel32.GetConsoleMode(handle, ctypes.byref(mode))
        kernel32.SetConsoleMode(handle, mode.value | 0x0004)
    except Exception:
        pass  # Fall back to uncolored output


class EventType:
    """Standard event types for structured logging."""

    # Run lifecycle
    RUN_START = "run_start"
    RUN_END = "run_end"

    # Batch lifecycle
    BATCH_START = "batch_start"
    BATCH_END = "batch_end"

    # Page/cursor lifecycle
    PAGE_START = "page_start"
    PAGE_FETCH = "page_fetch"
    PAGE_END = "page_end"

    # API operations
    API_REQUEST = "api_request"
    API_RESPONSE = "api_response"
    API_ERROR = "api_error"
    API_RATE_LIMIT = "api_rate_limit"
    API_WAIT = "api_wait"

    # Item operations
    ITEM_FETCH = "item_fetch"
    ITEM_SAVE = "item_save"
    ITEM_SKIP = "item_skip"
    ITEM_ERROR = "item_error"

    # Checkpoint
    CHECKPOINT_LOAD = "checkpoint_load"
    CHECKPOINT_SAVE = "checkpoint_save"

    # Progress
    PROGRESS = "progress"

    # Intent matching
    INTENT_MATCH = "intent_match"
    INTENT_NO_MATCH = "intent_no_match"
    INTENT_MODEL_LOAD = "intent_model_load"


class StructuredLogFormatter(logging.Formatter):
    """JSON formatter for structured log analysis."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON line."""
        log_data = {
            "ts": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if hasattr(record, "event_type"):
            log_data["event_type"] = record.event_type
        if hasattr(record, "event_data"):
            log_data["data"] = record.event_data

        return json.dumps(log_data, default=str)


class ConsoleFormatter(logging.Formatter):
    """Human-readable console formatter with colors (no emojis)."""

    COLORS = {
        "DEBUG": "\033[36m",     # Cyan
        "INFO": "\033[32m",      # Green
        "WARNING": "\033[33m",   # Yellow
        "ERROR": "\033[31m",     # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        """Format with color - clean output, no emojis."""
        color = self.COLORS.get(record.levelname, "")

        timestamp = datetime.now().strftime("%H:%M:%S")
        msg = f"{timestamp} [{record.levelname:5s}] {record.getMessage()}"

        if color and sys.stdout.isatty():
            return f"{color}{msg}{self.RESET}"
        return msg


class StructuredLogger(logging.LoggerAdapter):
    """Logger adapter with structured event data and fail-fast support."""

    def __init__(self, logger: logging.Logger, extra: dict | None = None):
        super().__init__(logger, extra or {})
        self._consecutive_errors = 0
        self._max_consecutive_errors = 10

    def set_max_errors(self, max_errors: int) -> None:
        """Set max consecutive errors before fail-fast."""
        self._max_consecutive_errors = max_errors

    def reset_error_count(self) -> None:
        """Reset consecutive error counter (call on success)."""
        self._consecutive_errors = 0

    def process(self, msg: str, kwargs: Any) -> tuple[str, dict]:
        """Process the logging call to add extra data."""
        extra = kwargs.get("extra", {})
        kwargs["extra"] = {**self.extra, **extra}
        return msg, kwargs

    def event(
        self,
        event_type: str,
        message: str,
        level: int = logging.INFO,
        **data: Any,
    ) -> None:
        """Log a structured event."""
        extra = {
            "event_type": event_type,
            "event_data": data,
        }
        self.log(level, message, extra=extra)

    # --- Run lifecycle ---

    def run_start(
        self,
        output_dir: str,
        max_items: int = 0,
        resume: bool = False,
        dry_run: bool = False,
        **kwargs,
    ) -> None:
        """Log run start."""
        rel_dir = rel_path(output_dir)
        mode = "dry-run" if dry_run else ("resume" if resume else "fresh")
        self.event(
            EventType.RUN_START,
            f"START {rel_dir} max={max_items} mode={mode}",
            output_dir=rel_dir,
            max_items=max_items,
            resume=resume,
            dry_run=dry_run,
            **kwargs,
        )

    def run_end(
        self,
        downloaded: int,
        skipped: int,
        errors: int,
        duration_sec: float,
    ) -> None:
        """Log run completion."""
        duration_str = format_duration(duration_sec)
        self.event(
            EventType.RUN_END,
            f"END saved={downloaded} skipped={skipped} errors={errors} [{duration_str}]",
            downloaded=downloaded,
            skipped=skipped,
            errors=errors,
            duration_sec=duration_sec,
        )

    # --- API operations ---

    def api_request(self, url: str, description: str = "") -> None:
        """Log API request."""
        desc = f" {description}" if description else ""
        self.event(
            EventType.API_REQUEST,
            f"GET {url}{desc}",
            url=url,
            description=description,
        )

    def api_wait(self, delay: float, reason: str = "rate_limit") -> None:
        """Log wait before request."""
        self.event(
            EventType.API_WAIT,
            f"WAIT {delay:.1f}s ({reason})",
            delay=delay,
            reason=reason,
        )

    def api_error(self, url: str, error: str, status_code: int = 0) -> None:
        """Log API error."""
        self.event(
            EventType.API_ERROR,
            f"API_ERROR {status_code} {url} {error}",
            level=logging.ERROR,
            url=url,
            error=error,
            status_code=status_code,
        )

    # --- Batch ---

    def batch_start(self, batch_num: int, batch_dir: str) -> None:
        """Log batch start."""
        rel_dir = rel_path(batch_dir)
        self.event(
            EventType.BATCH_START,
            f"BATCH {batch_num:03d} {rel_dir}",
            batch_num=batch_num,
            batch_dir=rel_dir,
        )

    def batch_end(self, batch_num: int, file_count: int) -> None:
        """Log batch completion."""
        self.event(
            EventType.BATCH_END,
            f"BATCH {batch_num:03d} done files={file_count}",
            batch_num=batch_num,
            file_count=file_count,
        )

    # --- Item operations ---

    def item_save(
        self,
        item_id: str,
        path: str,
        downloaded: int = 0,
        skipped: int = 0,
        errors: int = 0,
        **kwargs,
    ) -> None:
        """Log item saved."""
        rel_file = rel_path(path)
        self._consecutive_errors = 0  # Reset on success
        self.event(
            EventType.ITEM_SAVE,
            f"SAVE {item_id} -> {rel_file} [saved={downloaded} skip={skipped} err={errors}]",
            item_id=item_id,
            path=rel_file,
            downloaded=downloaded,
            skipped=skipped,
            errors=errors,
            status="success",
            **kwargs,
        )

    def item_skip(self, item_id: str, reason: str) -> None:
        """Log item skipped."""
        self.event(
            EventType.ITEM_SKIP,
            f"SKIP {item_id} ({reason})",
            item_id=item_id,
            reason=reason,
            status="skipped",
        )

    def item_error(self, item_id: str, error: str) -> bool:
        """Log item error. Returns True if should fail-fast."""
        self._consecutive_errors += 1
        should_fail = self._consecutive_errors >= self._max_consecutive_errors

        self.event(
            EventType.ITEM_ERROR,
            f"ERROR {item_id} {error}",
            level=logging.ERROR,
            item_id=item_id,
            error=error,
            status="failed",
            consecutive_errors=self._consecutive_errors,
        )

        if should_fail:
            self.warning(
                f"FAIL_FAST {self._consecutive_errors} consecutive errors"
            )

        return should_fail

    # --- Progress ---

    def progress(
        self,
        downloaded: int,
        skipped: int,
        errors: int,
        page: int = 0,
        total_pages: int = 0,
        elapsed_sec: float = 0,
        on_disk: int = 0,
        max_target: int = 0,
        rate: float = 0.0,
        **kwargs,
    ) -> None:
        """Log progress summary.

        When *on_disk* and *max_target* are provided the console output
        uses the rich two-line format required by the tool-development
        standards::

            [saved/max_target] saved | N on disk | elapsed | ~N.N puzzles/min

        The JSONL file always receives the full structured data regardless
        of which console format is used.
        """
        total = downloaded + skipped + errors
        elapsed_str = format_duration(elapsed_sec) if elapsed_sec else ""

        # Rich console line when on_disk/max_target are available
        if on_disk and max_target and elapsed_str:
            rate_str = f"~{rate:.1f} puzzles/min" if rate else ""
            console_msg = (
                f"  [{downloaded}/{max_target}] saved | "
                f"{on_disk} on disk | "
                f"{elapsed_str} elapsed | "
                f"{rate_str}"
            )
        else:
            # Fallback: original compact format
            page_info = f"page={page}/{total_pages}" if total_pages else ""
            parts = [f"saved={downloaded} total={total}"]
            if page_info:
                parts.append(page_info)
            if elapsed_str:
                parts.append(f"[{elapsed_str}]")
            console_msg = f"PROGRESS {' '.join(parts)}"

        self.event(
            EventType.PROGRESS,
            console_msg,
            downloaded=downloaded,
            skipped=skipped,
            errors=errors,
            page=page,
            total_pages=total_pages,
            elapsed_sec=elapsed_sec,
            on_disk=on_disk,
            max_target=max_target,
            rate=rate,
            **kwargs,
        )

    # --- Checkpoint ---

    def checkpoint_load(self, downloaded: int, page: int = 0) -> None:
        """Log checkpoint loaded."""
        self.event(
            EventType.CHECKPOINT_LOAD,
            f"RESUME downloaded={downloaded} page={page}",
            downloaded=downloaded,
            page=page,
        )

    def checkpoint_save(self, downloaded: int, page: int = 0) -> None:
        """Log checkpoint saved."""
        self.event(
            EventType.CHECKPOINT_SAVE,
            f"CHECKPOINT saved={downloaded} page={page}",
            level=logging.DEBUG,
            downloaded=downloaded,
            page=page,
        )


def setup_logging(
    output_dir: Path,
    logger_name: str,
    verbose: bool = False,
    log_to_file: bool = True,
    log_suffix: str = "",
    max_consecutive_errors: int = 10,
) -> StructuredLogger:
    """Set up logging with console and file handlers.

    Args:
        output_dir: Directory for log files.
        logger_name: Logger name (e.g., "ogs", "tsumegodragon").
        verbose: Enable debug logging to console.
        log_to_file: Write JSON logs to file.
        log_suffix: Optional suffix for log filename (e.g., "ogs" -> "20260205-143022-ogs.jsonl").
                    If empty, uses just timestamp: "20260205-143022.jsonl".
        max_consecutive_errors: Fail-fast threshold.

    Returns:
        StructuredLogger instance.

    Log filename format:
        {YYYYMMDD-HHMMSS}[-{suffix}].jsonl

        Timestamp-first format ensures logs auto-sort chronologically.
        Examples:
          - "20260205-143022.jsonl" (no suffix)
          - "20260205-143022-ogs.jsonl" (with suffix)
    """
    _enable_windows_ansi()

    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG if verbose else logging.INFO)
    console_handler.setFormatter(ConsoleFormatter())
    logger.addHandler(console_handler)

    # File handler
    if log_to_file:
        logs_dir = output_dir / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)

        # Timestamp-first for auto-sorting, optional suffix for identification
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        suffix_part = f"-{log_suffix}" if log_suffix else ""
        log_file = logs_dir / f"{timestamp}{suffix_part}.jsonl"

        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(StructuredLogFormatter())
        logger.addHandler(file_handler)

        logger.info(f"Log: {rel_path(log_file)}")

    structured = StructuredLogger(logger)
    structured.set_max_errors(max_consecutive_errors)
    return structured


def get_logger(logger_name: str) -> StructuredLogger:
    """Get existing logger by name."""
    return StructuredLogger(logging.getLogger(logger_name))


def format_duration(seconds: float) -> str:
    """Format duration in human-readable form."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes}m{secs:.0f}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h{minutes}m"
