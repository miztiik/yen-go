"""Centralized structured logging for puzzle-enrichment-lab.

Design principles:
  1. **Structured JSON payloads** — every log record is a JSON object with
     run_id, timestamp, level, logger name, and message.
  2. **Dual output** — stderr (for console/pytest capture) + rotating file
      in ``.lab-runtime/logs/`` directory.
  3. **Project-aligned** — reads ``config/logging.json`` for global settings
     (rotation, retention, date format) but applies them locally.
  4. **Handler-ready** — call ``get_root_logger()`` once at entry point;
     all child loggers inherit.  Add custom handlers via
     ``add_handler()`` for future integrations (e.g. JSON-lines sink,
     remote collection).
  5. **Error at INFO** — errors are always emitted at INFO *and* ERROR so
     that non-verbose runs still surface failures.
  6. **Verbose mode** — ``--verbose`` / ``LOG_LEVEL=DEBUG`` enables full
     tracebacks and debug-level messages.

Usage::

    # At entry point (cli.py, bridge.py, scripts, tests):
    from log_config import setup_logging
    setup_logging(run_id="20260302-a1b2c3d4", verbose=True)

    # In any module:
    import logging
    logger = logging.getLogger(__name__)   # unchanged — works as before
    logger.info("enriched puzzle %s", puzzle_id)
"""

from __future__ import annotations

import json
import logging
import logging.handlers
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_LAB_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _LAB_DIR.parent.parent  # yen-go/
_GLOBAL_LOG_CONFIG = _PROJECT_ROOT / "config" / "logging.json"
_DEFAULT_LOG_DIR = _LAB_DIR / ".lab-runtime" / "logs"

# Workspace root for relative path stripping (Plan 010, P3.2)
# Walk up from __file__ to find the directory containing .git/
_WORKSPACE_ROOT: str | None = None


def _find_workspace_root() -> str:
    """Find the workspace root by walking up to find .git directory.

    Cached on first call. Uses str.removeprefix() for path stripping.
    """
    global _WORKSPACE_ROOT
    if _WORKSPACE_ROOT is not None:
        return _WORKSPACE_ROOT
    current = Path(__file__).resolve().parent
    for _ in range(10):  # Safety limit
        if (current / ".git").exists():
            _WORKSPACE_ROOT = str(current) + os.sep
            return _WORKSPACE_ROOT
        parent = current.parent
        if parent == current:
            break
        current = parent
    _WORKSPACE_ROOT = ""  # Not found — don't strip
    return _WORKSPACE_ROOT


def strip_workspace_root(path: str | Path) -> str:
    """Strip the workspace root from a path for cleaner log output.

    Plan 010, P3.2: Uses str.removeprefix() (no regex).
    Respects config.logging.use_relative_paths flag.
    Example: 'C:/Users/.../yen-go/tools/puzzle-enrichment-lab/logs/x.log'
             → 'tools/puzzle-enrichment-lab/logs/x.log'
    """
    # Plan 010, P3.2: check use_relative_paths config flag
    if not _use_relative_paths:
        return str(path)
    root = _find_workspace_root()
    if not root:
        return str(path)
    s = str(path)
    result = s.removeprefix(root)
    # Also handle forward-slash variant on Windows
    root_fwd = root.replace(os.sep, "/")
    result = result.removeprefix(root_fwd)
    return result

# Module prefixes that belong to the puzzle-enrichment-lab.
# Modules use logging.getLogger(__name__) which produces names like
# "analyzers.enrich_single", "engine.single_engine", etc.
_LAB_MODULE_PREFIXES = (
    "analyzers", "engine", "models", "config", "cli", "log_config",
    "puzzle_enrichment_lab",  # backward compat for tests
    "conftest",
)
LOGGER_NAMESPACE = _LAB_MODULE_PREFIXES

# The package sets this once via setup_logging(); child loggers read it
# through the filter.
_active_run_id: str = ""

# Per-puzzle trace context — set by enrich_single_puzzle() at puzzle entry,
# injected into every log record by _TraceIdFilter.
_active_trace_id: str = ""
_active_puzzle_id: str = ""

# Config-driven flags (Plan 010, P3.2/P3.1) — set from katago-enrichment.json
_use_relative_paths: bool = True  # Default to True for backward compat
_per_run_files: bool = True       # Default to True for backward compat


# ---------------------------------------------------------------------------
# JSON formatter
# ---------------------------------------------------------------------------

class _StructuredJsonFormatter(logging.Formatter):
    """Emit each log record as a single-line JSON object.

    Field ordering (optimized for operator readability):
      ``ts``, ``run_id``, ``trace_id``, ``puzzle_id``, ``stage``,
      ``msg``, [extra fields], ``level``, ``logger``.

    Level and logger are pushed to the end because operators scan
    timestamp → puzzle → stage → message first; level/logger are
    metadata consulted only when filtering.
    """

    # Standard LogRecord attributes excluded from extra-field propagation.
    _STANDARD_ATTRS = {
        "name", "msg", "args", "created", "relativeCreated", "thread",
        "threadName", "msecs", "pathname", "filename", "module",
        "exc_info", "exc_text", "stack_info", "lineno", "funcName",
        "levelno", "levelname", "message", "processName", "process",
        "run_id", "trace_id", "puzzle_id", "taskName", "asctime",
    }

    # Fields that get special placement (not dumped as generic extras).
    _POSITIONED_FIELDS = {
        "ts", "run_id", "puzzle_id", "trace_id", "stage", "msg",
        "level", "logger",
    }

    def __init__(self, *, datefmt: str = "%Y-%m-%d %H:%M:%S") -> None:
        super().__init__(datefmt=datefmt)
        self._datefmt = datefmt

    def format(self, record: logging.LogRecord) -> str:
        ts = datetime.fromtimestamp(record.created, tz=UTC).strftime(self._datefmt)
        run_id = getattr(record, "run_id", _active_run_id)
        puzzle_id = getattr(record, "puzzle_id", "") or ""
        trace_id = getattr(record, "trace_id", "") or ""
        stage = getattr(record, "stage", "") or ""

        # --- Build payload with deliberate field ordering ---
        payload: dict[str, Any] = {"ts": ts, "run_id": run_id}

        # Puzzle context (present when inside a puzzle enrichment span)
        if trace_id:
            payload["trace_id"] = trace_id
        if puzzle_id:
            payload["puzzle_id"] = puzzle_id
        if stage:
            payload["stage"] = stage

        payload["msg"] = record.getMessage()

        # Propagate all extra fields attached via extra={...} on the log call.
        for key, val in record.__dict__.items():
            if key.startswith("_") or key in self._STANDARD_ATTRS:
                continue
            if val is not None and key not in self._POSITIONED_FIELDS and key not in payload:
                payload[key] = val

        # Level + logger at the end (metadata, not primary signal)
        payload["level"] = record.levelname
        payload["logger"] = record.name

        # Exception info — always include in verbose (DEBUG), summarise at
        # INFO+.  The _ErrorToInfoFilter below duplicates errors at INFO.
        if record.exc_info and record.exc_info[1] is not None:
            payload["exc_type"] = type(record.exc_info[1]).__name__
            payload["exc_msg"] = str(record.exc_info[1])
            # Full traceback only when root logger is at DEBUG
            if logging.getLogger().isEnabledFor(logging.DEBUG):
                payload["exc_traceback"] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=False, default=str)


class _HumanReadableFormatter(logging.Formatter):
    """Compact line format for interactive console use.

    Falls back to this when ``LOG_FORMAT=human`` is set, to keep terminal
    output readable during development.
    """

    _FMT = "%(asctime)s [%(levelname)-5s] %(name)s: %(message)s"
    _DATEFMT = "%H:%M:%S"

    def __init__(self) -> None:
        super().__init__(fmt=self._FMT, datefmt=self._DATEFMT)


# ---------------------------------------------------------------------------
# Filters
# ---------------------------------------------------------------------------

class _LabNamespaceFilter(logging.Filter):
    """Pass only records originating from puzzle-enrichment-lab modules.

    Attached to the file handler so that external library noise (e.g. httpx,
    sgfmill, asyncio) is kept out of the lab log file even though the handler
    lives on the root logger.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        return any(record.name.startswith(p) for p in _LAB_MODULE_PREFIXES)


class _RunIdFilter(logging.Filter):
    """Inject ``run_id`` into every record so formatters can include it."""

    def filter(self, record: logging.LogRecord) -> bool:
        if not getattr(record, "run_id", ""):
            record.run_id = _active_run_id  # type: ignore[attr-defined]
        return True


class _TraceIdFilter(logging.Filter):
    """Inject ``trace_id`` and ``puzzle_id`` into every record.

    These are set per-puzzle by ``set_trace_context()`` in enrich_single.py
    and cleared at puzzle completion.  If a log call already provides these
    fields via ``extra={}``, they are NOT overwritten.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        if not getattr(record, "trace_id", ""):
            record.trace_id = _active_trace_id  # type: ignore[attr-defined]
        if not getattr(record, "puzzle_id", ""):
            record.puzzle_id = _active_puzzle_id  # type: ignore[attr-defined]
        return True


class _ErrorToInfoFilter(logging.Filter):
    """Ensure ERROR/CRITICAL messages are also emitted at INFO.

    Rationale: operators running at INFO level must see failures without
    enabling DEBUG.  This filter intercepts ERROR+ records on the *handler*
    attached to the file/stderr sinks and re-emits a copy at INFO.

    Implemented as a module-level dedup set to avoid infinite loops.
    """

    _seen: set[int] = set()

    def filter(self, record: logging.LogRecord) -> bool:
        # Always allow the record through
        if record.levelno >= logging.ERROR:
            rec_id = id(record)
            if rec_id not in self._seen:
                self._seen.add(rec_id)
                # Emit a duplicate at INFO level on the root logger
                info_record = logging.makeLogRecord(record.__dict__)
                info_record.levelno = logging.INFO
                info_record.levelname = "INFO"
                info_record.msg = f"[mirrored-error] {record.getMessage()}"
                info_record.args = ()
                # Use root logger to propagate to all handlers
                logging.getLogger().handle(info_record)
                # Prevent set from growing unbounded
                if len(self._seen) > 10_000:
                    self._seen.clear()
        return True


# ---------------------------------------------------------------------------
# Global config loader
# ---------------------------------------------------------------------------

def _load_global_config() -> dict[str, Any]:
    """Load ``config/logging.json`` from project root if available."""
    if _GLOBAL_LOG_CONFIG.exists():
        try:
            return json.loads(_GLOBAL_LOG_CONFIG.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def setup_logging(
    *,
    run_id: str = "",
    verbose: bool = False,
    log_dir: Path | str | None = None,
    console_format: str = "json",
) -> logging.Logger:
    """Configure structured logging for the entire puzzle-enrichment-lab.

    Call **once** at the entry point (cli.py ``main()``, bridge startup,
    test conftest, calibration script).  All modules that use
    ``logging.getLogger(__name__)`` automatically inherit the configuration.

    Args:
        run_id: Pipeline run identifier (``YYYYMMDD-8hexchars``).  If empty,
            the run_id field is omitted from log payloads.
        verbose: When True, sets root level to DEBUG and includes full
            stack traces in log records.
        log_dir: Override log file directory.  Defaults to
            ``tools/puzzle-enrichment-lab/.lab-runtime/logs/``.
        console_format: ``"json"`` (default) or ``"human"`` — controls
            stderr formatter.  ``LOG_FORMAT`` env var overrides this.

    Returns:
        The root logger (convenience for chaining).
    """
    global _active_run_id, _use_relative_paths, _per_run_files
    _active_run_id = run_id

    # Resolve log directory and logging config flags (Plan 010, P3.1/P3.2)
    _cfg = None
    if log_dir:
        resolved_log_dir = Path(log_dir)
    else:
        try:
            from config import load_enrichment_config, resolve_path
            _cfg = load_enrichment_config()
            resolved_log_dir = resolve_path(_cfg, "logs_dir")
        except Exception:
            resolved_log_dir = _DEFAULT_LOG_DIR
    resolved_log_dir.mkdir(parents=True, exist_ok=True)

    # Read logging config flags from katago-enrichment.json (Plan 010, P3.1/P3.2)
    if _cfg is not None:
        log_cfg = getattr(_cfg, "logging", None)
        if log_cfg is not None:
            _use_relative_paths = getattr(log_cfg, "use_relative_paths", True)
            _per_run_files = getattr(log_cfg, "per_run_files", True)

    # Ensure .gitignore so log files are never committed
    _ensure_gitignore(resolved_log_dir)

    # Load project-wide settings (non-blocking if missing)
    global_cfg = _load_global_config()
    datefmt = global_cfg.get("date_format", "%Y-%m-%d %H:%M:%S")
    retention_days = global_cfg.get("retention_days", 45)
    rotation_cfg = global_cfg.get("rotation", {})
    rotation_when = rotation_cfg.get("when", "midnight")
    backup_count = rotation_cfg.get("backup_count", retention_days)

    # Determine effective level
    env_level = os.environ.get("LOG_LEVEL", "").upper()
    if env_level in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
        effective_level = getattr(logging, env_level)
    elif verbose:
        effective_level = logging.DEBUG
    else:
        effective_level = logging.INFO

    # --- Reset root logger ---
    root = logging.getLogger()
    root.setLevel(effective_level)
    # Remove and close existing handlers (prevents duplicate output and
    # file-handle leaks on Windows when temp dirs are cleaned up)
    for h in root.handlers[:]:
        root.removeHandler(h)
        try:
            h.close()
        except Exception:
            pass

    # (No per-namespace handler cleanup needed: file handler lives on root,
    #  scoped via _LabNamespaceFilter.)

    # --- Formatters ---
    json_formatter = _StructuredJsonFormatter(datefmt=datefmt)

    env_format = os.environ.get("LOG_FORMAT", "").lower()
    console_fmt_choice = env_format if env_format in ("json", "human") else console_format
    console_formatter = (
        _HumanReadableFormatter() if console_fmt_choice == "human"
        else json_formatter
    )

    # --- Stderr handler ---
    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setLevel(effective_level)
    stderr_handler.setFormatter(console_formatter)
    stderr_handler.addFilter(_RunIdFilter())
    stderr_handler.addFilter(_TraceIdFilter())
    root.addHandler(stderr_handler)

    # --- File handler (P3.1: per-run log gated on config.logging.per_run_files) ---
    use_per_run = run_id and _per_run_files
    if use_per_run:
        log_file = resolved_log_dir / f"{run_id}-enrichment.log"  # dash per plan
    else:
        log_file = resolved_log_dir / "enrichment.log"
    try:
        if use_per_run:
            file_handler = logging.FileHandler(
                filename=str(log_file),
                encoding="utf-8",
            )
        else:
            file_handler = logging.handlers.TimedRotatingFileHandler(
                filename=str(log_file),
                when=rotation_when,
                backupCount=backup_count,
                encoding="utf-8",
            )
        file_handler.setLevel(logging.DEBUG)  # file always captures everything
        file_handler.setFormatter(json_formatter)
        file_handler.addFilter(_LabNamespaceFilter())  # scoped: only puzzle_enrichment_lab.* logs to file
        file_handler.addFilter(_RunIdFilter())
        file_handler.addFilter(_TraceIdFilter())
        file_handler.addFilter(_ErrorToInfoFilter())
        root.addHandler(file_handler)  # on root so root.handlers is single source of truth
    except OSError as exc:
        # Don't fail hard if log file can't be opened (e.g. read-only FS)
        sys.stderr.write(f"WARNING: Could not open log file {log_file}: {exc}\n")

    root.info(
        "Logging initialised (level=%s, log_dir=%s, run_id=%s)",
        logging.getLevelName(effective_level),
        strip_workspace_root(resolved_log_dir),
        run_id or "<none>",
    )
    return root


def bootstrap(
    *,
    verbose: bool = False,
    log_dir: Path | str | None = None,
    console_format: str = "json",
) -> str:
    """Initialize enrichment lab: generate run_id, setup logging, set run_id context.

    Convenience function that centralises the 3-step logging ceremony
    (generate_run_id → setup_logging → set_run_id) used by every entry point.

    Returns the generated run_id.
    """
    from models.ai_analysis_result import generate_run_id
    run_id = generate_run_id()
    setup_logging(run_id=run_id, verbose=verbose, log_dir=log_dir, console_format=console_format)
    set_run_id(run_id)
    return run_id


def add_handler(handler: logging.Handler) -> None:
    """Attach an additional handler to the root logger.

    Use this for future integrations: JSON-lines file sink, remote
    log collector, structured test capture, etc.
    """
    handler.addFilter(_RunIdFilter())
    handler.addFilter(_TraceIdFilter())
    logging.getLogger().addHandler(handler)


def set_run_id(run_id: str) -> None:
    """Update the active run_id mid-session (e.g. after ``generate_run_id()``)."""
    global _active_run_id
    _active_run_id = run_id


def get_run_id() -> str:
    """Return the currently active run_id."""
    return _active_run_id


def set_trace_context(*, trace_id: str = "", puzzle_id: str = "") -> None:
    """Set per-puzzle trace context injected into every log record.

    Called by ``enrich_single_puzzle()`` at puzzle entry.  Clear with
    ``clear_trace_context()`` at puzzle completion.
    """
    global _active_trace_id, _active_puzzle_id
    _active_trace_id = trace_id
    _active_puzzle_id = puzzle_id


def clear_trace_context() -> None:
    """Clear per-puzzle trace context (between puzzles in batch mode)."""
    global _active_trace_id, _active_puzzle_id
    _active_trace_id = ""
    _active_puzzle_id = ""


def log_with_context(
    logger: logging.Logger,
    level: int,
    msg: str,
    *args: Any,
    puzzle_id: str = "",
    stage: str = "",
    collection: str = "",
    **kwargs: Any,
) -> None:
    """Emit a log record with structured extra fields.

    Convenience wrapper — avoids ``extra=`` dict boilerplate::

        log_with_context(logger, logging.INFO, "enriched %s", pid,
                         puzzle_id=pid, stage="analyze")
    """
    extra: dict[str, Any] = {}
    if puzzle_id:
        extra["puzzle_id"] = puzzle_id
    if stage:
        extra["stage"] = stage
    if collection:
        extra["collection"] = collection
    for k, v in kwargs.items():
        if k not in ("exc_info", "stack_info", "stacklevel"):
            extra[k] = v
    logger.log(level, msg, *args, extra=extra,
               exc_info=kwargs.get("exc_info"),
               stack_info=kwargs.get("stack_info"))


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------

def _ensure_gitignore(log_dir: Path) -> None:
    """Create ``.gitignore`` in log dir so files are never committed."""
    gi = log_dir / ".gitignore"
    if not gi.exists():
        try:
            gi.write_text(
                "# Auto-generated — log files are machine-specific\n"
                "*\n"
                "!.gitignore\n",
                encoding="utf-8",
            )
        except OSError:
            pass
