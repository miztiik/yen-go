"""
Logging configuration for the puzzle manager.

Provides structured logging with rotation support, run correlation, and
immediate flush for real-time monitoring.

Immediate Flush
---------------
All file handlers use FlushingFileHandler which flushes after every write.
This enables:
- Real-time log monitoring (tail -f)
- External tools to detect errors immediately
- No lost logs on crashes or abrupt termination

Run Correlation (Spec 043)
--------------------------
Every pipeline run has a unique `run_id` (format: YYYYMMDD-xxxxxxxx).
Use `create_run_logger()` to get a logger that automatically includes
`run_id` and `source_id` in all log entries:

    from backend.puzzle_manager.pm_logging import create_run_logger

    run_logger = create_run_logger(run_id="20260129-abc12345", source_id="sanderland")
    run_logger.info("Processing puzzle", extra={"puzzle_id": "gp-12345"})
    # Output: {"run_id": "20260129-abc12345", "source_id": "sanderland", "puzzle_id": "gp-12345", ...}

The `RunContextAdapter` is a LoggerAdapter that injects `run_id` and `source_id`
into all log records, enabling correlation across the entire pipeline execution.

Log Format (Spec 043)
---------------------
- Main log (puzzle_manager.log): Full format with level and logger name
- Stage logs (ingest.log, analyze.log, publish.log): Compact format, no level/logger
- Timestamps: HH:MM:SS.mmm format (milliseconds precision)
- Paths: Relative to staging/output root, POSIX format (forward slashes)
"""

import json
import logging
import sys
from pathlib import Path
from typing import Any

from backend.puzzle_manager.core.datetime_utils import utc_now
from backend.puzzle_manager.paths import get_logs_dir

# Custom DETAIL level: between DEBUG (10) and INFO (20).
# Per-puzzle messages use DETAIL so they appear in stage log files
# (file handler threshold = DETAIL) but NOT on the console (console
# handler threshold = INFO).  This keeps the console as a "dashboard"
# while stage logs remain the full audit trail.
DETAIL = 15
logging.addLevelName(DETAIL, "DETAIL")


# Module-level variable to store staging root for relative path computation
_staging_root: Path | None = None


def set_staging_root(path: Path) -> None:
    """Set the staging root for relative path computation in logs."""
    global _staging_root
    _staging_root = path


def get_staging_root() -> Path | None:
    """Get the staging root for relative path computation."""
    return _staging_root


def to_relative_path(path: str | Path) -> str:
    """Convert absolute path to relative path for logging.

    Paths are made relative to staging_root if set, otherwise uses
    the path as-is but converts to POSIX format (forward slashes).

    Delegates POSIX conversion to paths.to_posix_path() for DRY compliance.

    Args:
        path: Path to convert (string or Path object)

    Returns:
        Relative path string with forward slashes
    """
    from backend.puzzle_manager.paths import to_posix_path

    if not path:
        return ""

    path_obj = Path(path) if isinstance(path, str) else path

    # Try to make relative to staging root
    if _staging_root is not None:
        try:
            rel = path_obj.relative_to(_staging_root)
            return to_posix_path(rel)
        except ValueError:
            pass  # Not under staging root

    # Try to make relative to parent of pm_staging (e.g., backend/puzzle_manager)
    try:
        # Look for pm_staging in the path
        parts = path_obj.parts
        for i, part in enumerate(parts):
            if part in ("pm_staging", "yengo-puzzle-collections"):
                # Return from this part onwards using POSIX separator
                return "/".join(parts[i:])
    except Exception:
        pass

    # Convert to POSIX format
    posix = to_posix_path(path_obj)

    # If path is already relative (no drive letter, doesn't start with /), preserve it
    # This ensures paths like "sgf/advanced/batch-0001/xyz.sgf" aren't truncated
    if not path_obj.is_absolute():
        return posix

    # Fallback for absolute paths: return last few parts for readability
    parts = posix.split("/")
    if len(parts) > 3:
        return "/".join(parts[-3:])
    return posix


class FlushingFileHandler(logging.FileHandler):
    """File handler that flushes after every write for real-time monitoring.

    This ensures:
    - Log entries appear immediately in the file (no buffering delay)
    - External monitoring tools can detect errors in real-time
    - No logs are lost on crashes or abrupt termination
    - `tail -f logfile` shows entries as they happen

    Performance note: The flush overhead is minimal (~0.1ms per entry) and
    is acceptable for pipeline workloads where correctness and observability
    are more important than throughput.
    """

    def emit(self, record: logging.LogRecord) -> None:
        """Emit a record and immediately flush to disk."""
        super().emit(record)
        self.flush()


class StructuredFormatter(logging.Formatter):
    """JSON structured log formatter for main puzzle_manager log.

    Includes level and logger name since this log aggregates all sources.
    Timestamp format: YYYY-MM-DD HH:MM:SS.mmm (full date for log correlation)
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        # Full timestamp: YYYY-MM-DD HH:MM:SS.mmm
        now = utc_now()
        timestamp = now.strftime("%Y-%m-%d %H:%M:%S") + f".{now.microsecond // 1000:03d}"

        log_entry: dict[str, Any] = {
            "ts": timestamp,
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Add extra fields from record, converting paths to relative
        for key, value in record.__dict__.items():
            if key not in (
                "name",
                "msg",
                "args",
                "created",
                "filename",
                "funcName",
                "levelname",
                "levelno",
                "lineno",
                "module",
                "msecs",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "stack_info",
                "exc_info",
                "exc_text",
                "thread",
                "threadName",
                "taskName",
                "message",
            ):
                # Convert path-like values to relative paths
                if isinstance(value, (str, Path)) and ("/" in str(value) or "\\" in str(value)):
                    value = to_relative_path(value)
                log_entry[key] = value

        return json.dumps(log_entry)


class StageFormatter(logging.Formatter):
    """Compact JSON formatter for stage-specific logs (ingest, analyze, publish).

    Omits level and logger name since the log file provides that context.
    Timestamp format: YYYY-MM-DD HH:MM:SS.mmm (full date for log correlation)
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as compact JSON."""
        # Full timestamp: YYYY-MM-DD HH:MM:SS.mmm
        now = utc_now()
        timestamp = now.strftime("%Y-%m-%d %H:%M:%S") + f".{now.microsecond // 1000:03d}"

        log_entry: dict[str, Any] = {
            "ts": timestamp,
            "msg": record.getMessage(),
        }

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Add extra fields from record, converting paths to relative
        for key, value in record.__dict__.items():
            if key not in (
                "name",
                "msg",
                "args",
                "created",
                "filename",
                "funcName",
                "levelname",
                "levelno",
                "lineno",
                "module",
                "msecs",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "stack_info",
                "exc_info",
                "exc_text",
                "thread",
                "threadName",
                "taskName",
                "message",
            ):
                # Convert path-like values to relative paths
                if isinstance(value, (str, Path)) and ("/" in str(value) or "\\" in str(value)):
                    value = to_relative_path(value)
                log_entry[key] = value

        return json.dumps(log_entry)


class ConsoleFormatter(logging.Formatter):
    """Human-readable console formatter."""

    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def __init__(self, use_colors: bool = True) -> None:
        super().__init__()
        self.use_colors = use_colors

    def format(self, record: logging.LogRecord) -> str:
        """Format log record for console output."""
        level = record.levelname
        if self.use_colors and level in self.COLORS:
            level_str = f"{self.COLORS[level]}{level:8}{self.RESET}"
        else:
            level_str = f"{level:8}"

        # Full timestamp: YYYY-MM-DD HH:MM:SS.mmm
        now = utc_now()
        timestamp = now.strftime("%Y-%m-%d %H:%M:%S") + f".{now.microsecond // 1000:03d}"
        message = record.getMessage()

        # Console output is human-readable: extras go to log files via
        # StructuredFormatter/StageFormatter, not repeated on console.
        formatted = f"{timestamp} {level_str} {record.name}: {message}"

        if record.exc_info:
            formatted += "\n" + self.formatException(record.exc_info)

        return formatted


def setup_logging(
    name: str = "puzzle_manager",
    level: int = logging.INFO,
    log_file: bool = True,
    console: bool = True,
    verbose: bool = False,
) -> logging.Logger:
    """Set up logging for the puzzle manager.

    Args:
        name: Logger name.
        level: Base logging level.
        log_file: Whether to write to log file.
        console: Whether to write to console.
        verbose: If True, use DEBUG level.

    Returns:
        Configured logger.
    """
    logger = logging.getLogger(name)

    # Avoid duplicate handlers
    if logger.handlers:
        return logger

    if verbose:
        level = logging.DEBUG

    # Root logger should accept all messages (DEBUG) so file handlers can capture them.
    # Console handler filters to the requested level.
    logger.setLevel(logging.DEBUG)

    # Console handler - uses the requested level (WARNING by default, INFO with -v)
    if console:
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setLevel(level)
        console_handler.setFormatter(ConsoleFormatter(use_colors=sys.stderr.isatty()))
        logger.addHandler(console_handler)

    # File handler with daily log files (date-prefixed for natural sorting)
    # Each day gets its own file; cleanup utility deletes files older than logs_days
    # Uses FlushingFileHandler for immediate flush after each entry
    if log_file:
        logs_dir = get_logs_dir()
        logs_dir.mkdir(parents=True, exist_ok=True)

        # Date prefix for automatic sorting: 2026-01-29-puzzle_manager.log
        today = utc_now().strftime("%Y-%m-%d")
        log_path = logs_dir / f"{today}-{name}.log"
        file_handler = FlushingFileHandler(log_path, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)  # Always log everything to file
        file_handler.setFormatter(StructuredFormatter())
        logger.addHandler(file_handler)

        # Set up per-stage log files with same console level
        _setup_stage_loggers(logs_dir, today, console_level=level if console else None)

    return logger


def _setup_stage_loggers(logs_dir: Path, today: str, console_level: int | None = None) -> None:
    """Set up separate log files for each pipeline stage.

    Creates individual log files:
      - 2026-01-29-ingest.log
      - 2026-01-29-analyze.log
      - 2026-01-29-publish.log

    Each stage uses a simple logger name (ingest, analyze, publish) since
    the log file itself provides the context.

    Stage logs use StageFormatter which omits level and logger name for brevity.

    Args:
        logs_dir: Directory for log files.
        today: Date string for file naming.
        console_level: If set, add console handler at this level.
    """
    stages = ["ingest", "analyze", "publish"]

    for stage in stages:
        stage_logger = logging.getLogger(stage)
        stage_logger.setLevel(logging.DEBUG)  # Accept all levels

        # Avoid duplicate handlers (check for FlushingFileHandler or FileHandler)
        if any(isinstance(h, logging.FileHandler) for h in stage_logger.handlers):
            continue

        # Use FlushingFileHandler for immediate flush after each entry
        log_path = logs_dir / f"{today}-{stage}.log"
        handler = FlushingFileHandler(log_path, encoding="utf-8")
        handler.setLevel(DETAIL)  # Stage logs: DETAIL and above (captures per-puzzle messages)
        handler.setFormatter(StageFormatter())  # Compact format without level/logger
        stage_logger.addHandler(handler)

        # Add console handler so stage logs appear on console too
        if console_level is not None:
            console_handler = logging.StreamHandler(sys.stderr)
            console_handler.setLevel(console_level)
            console_handler.setFormatter(ConsoleFormatter(use_colors=sys.stderr.isatty()))
            stage_logger.addHandler(console_handler)


def get_logger(name: str) -> logging.Logger:
    """Get a child logger.

    Args:
        name: Logger name (will be prefixed with puzzle_manager).

    Returns:
        Logger instance.
    """
    return logging.getLogger(f"puzzle_manager.{name}")


class RunContextAdapter(logging.LoggerAdapter):
    """Adapter that adds run context (run_id, source_id, trace_id) to all log messages.

    This enables log correlation across all pipeline components. Every log
    entry made through this adapter will automatically include:
    - run_id: Pipeline run identifier (YYYYMMDD-xxxxxxxx format)
    - source_id: Source adapter being processed (required per spec-043)
    - trace_id: Optional per-file trace identifier (spec-110)

    Usage:
        logger = create_run_logger(run_id="20260129-abc12345", source_id="sanderland")
        logger.info("Processing puzzle", extra={"puzzle_id": "gp-123"})
        # Output includes: run_id, source_id, puzzle_id

        # With trace_id:
        trace_logger = create_trace_logger(run_id=..., source_id=..., trace_id=...)
        trace_logger.info("Processing file")
        # Output includes: run_id, source_id, trace_id

    Why LoggerAdapter:
    - Thread-safe (each adapter instance is independent)
    - Test-isolated (create new adapter per test)
    - Standard Python pattern
    - Future-proof for async execution
    """

    def process(self, msg: str, kwargs: dict) -> tuple[str, dict]:
        """Add context fields to log record extras.

        Args:
            msg: Log message
            kwargs: Logging keyword arguments

        Returns:
            Tuple of (message, modified kwargs with extra context)
        """
        extra = kwargs.setdefault("extra", {})
        extra.update(self.extra)
        return msg, kwargs


def create_run_logger(run_id: str, source_id: str) -> RunContextAdapter:
    """Create a logger adapter with run context for log correlation.

    All log entries made through this logger will include run_id and source_id
    fields, enabling filtering and correlation of logs by pipeline run.

    Args:
        run_id: Pipeline run identifier (YYYYMMDD-xxxxxxxx format)
        source_id: Source adapter being processed (required - single-adapter mode)

    Returns:
        LoggerAdapter with run context attached to all messages

    Example:
        >>> logger = create_run_logger("20260129-abc12345", "sanderland")
        >>> logger.info("Started processing")
        # Log entry: {..., "run_id": "20260129-abc12345", "source_id": "sanderland", ...}
    """
    context = {
        "run_id": run_id,
        "source_id": source_id,
    }
    return RunContextAdapter(
        logging.getLogger("puzzle_manager.pipeline"),
        extra=context,
    )


def create_trace_logger(
    run_id: str,
    source_id: str,
    trace_id: str,
    stage: str = "ingest",
) -> RunContextAdapter:
    """Create a logger adapter with trace context for per-file observability.

    All log entries made through this logger will include run_id, source_id,
    and trace_id fields, enabling correlation of logs by individual file.

    Logs are directed to the appropriate stage log file (e.g., ingest.log,
    analyze.log, publish.log) based on the stage parameter.

    Spec 110: Per-file trace_id for end-to-end observability.

    Args:
        run_id: Pipeline run identifier (YYYYMMDD-xxxxxxxx format)
        source_id: Source adapter being processed
        trace_id: Per-file trace identifier (16-char hex)
        stage: Pipeline stage name ("ingest", "analyze", "publish")
            Determines which log file receives the messages.
            Defaults to "ingest".

    Returns:
        LoggerAdapter with trace context attached to all messages

    Example:
        >>> logger = create_trace_logger("20260129-abc12345", "sanderland", "a1b2c3d4e5f67890")
        >>> logger.info("Processing file")
        # Log entry in ingest.log: {..., "run_id": "...", "source_id": "...", "trace_id": "a1b2c3d4e5f67890", ...}

        >>> logger = create_trace_logger("20260129-abc12345", "sanderland", "a1b2c3d4e5f67890", stage="analyze")
        >>> logger.info("Analyzing file")
        # Log entry in analyze.log: {...}
    """
    context = {
        "run_id": run_id,
        "source_id": source_id,
        "trace_id": trace_id,
    }
    # Use stage-specific logger (ingest, analyze, publish) so logs go to correct file
    return RunContextAdapter(
        logging.getLogger(stage),
        extra=context,
    )


# Convenience function for logging with context
def log_with_context(
    logger: logging.Logger,
    level: int,
    message: str,
    **context: Any,
) -> None:
    """Log a message with structured context.

    Args:
        logger: Logger instance.
        level: Logging level.
        message: Log message.
        **context: Additional context fields.
    """
    logger.log(level, message, extra=context)


def close_all_file_handlers() -> int:
    """Close all file handlers on all loggers.

    This is necessary on Windows before cleaning up log files, as Windows
    does not allow deleting files that are open by another process.

    Returns:
        Number of handlers closed.
    """
    closed = 0

    # Close handlers on the root logger
    root = logging.getLogger()
    for handler in root.handlers[:]:
        if isinstance(handler, logging.FileHandler):
            handler.close()
            root.removeHandler(handler)
            closed += 1

    # Close handlers on puzzle_manager and stage loggers
    logger_names = [
        "puzzle_manager",
        "puzzle_manager.pipeline",
        "puzzle_manager.pipeline.cleanup",
        "puzzle_manager.adapters",
        "puzzle_manager.cli",
        "puzzle_manager.state",
        "ingest",
        "analyze",
        "publish",
    ]

    for name in logger_names:
        logger = logging.getLogger(name)
        for handler in logger.handlers[:]:
            if isinstance(handler, logging.FileHandler):
                handler.close()
                logger.removeHandler(handler)
                closed += 1

    return closed
