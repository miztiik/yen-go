"""Structured JSON logger for yen-sei pipeline.

Inspired by tools/puzzle-enrichment-lab/log_config.py.
Emits JSON log lines with trace_id, stage context for SSE bridging.
"""

from __future__ import annotations

import json
import logging
import sys
from contextvars import ContextVar
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tools.yen_sei.config import DATA_DIR
from tools.yen_sei.data_paths import (
    cleanup_old,
    cleanup_old_latest_pointers,
    legacy_latest_pointer,
    latest_pointer,
    now_stamp,
    stamped_path,
)

_trace_id: ContextVar[str] = ContextVar("trace_id", default="")
_stage: ContextVar[str] = ContextVar("stage", default="")


def set_context(*, trace_id: str = "", stage: str = "") -> None:
    """Set the current trace/stage context for log enrichment."""
    if trace_id:
        _trace_id.set(trace_id)
    if stage:
        _stage.set(stage)


class _JsonFormatter(logging.Formatter):
    """Formats log records as single-line JSON."""

    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "stage": _stage.get(""),
            "trace_id": _trace_id.get(""),
            "msg": record.getMessage(),
            "module": record.module,
        }
        if record.exc_info and record.exc_info[1]:
            entry["error"] = str(record.exc_info[1])
        return json.dumps(entry, default=str)


def configure_stage_file_logging(
    stage: str,
    *,
    logger: logging.Logger | None = None,
    keep: int = 3,
    stamp: str | None = None,
) -> tuple[Path, Path, list[Path]]:
    """Attach stage log file handlers.

    Writes to both:
            - data/YYYYMMDDHHMMSS_{stage}_run.log
            - data/YYYYMMDDHHMMSS_{stage}_run_latest.log

    Returns:
      (timestamped_log_path, latest_log_path, deleted_old_logs)
    """
    if not stage:
        raise ValueError("stage must be non-empty")

    target_logger = logger or logging.getLogger("yen_sei")
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    kind = f"{stage}_run"
    run_stamp = stamp or now_stamp()
    stamped_log = stamped_path(kind, "log", DATA_DIR, ts=run_stamp)
    latest_log = latest_pointer(kind, "log", DATA_DIR, ts=run_stamp)

    # Ensure one active stage file handler set per logger.
    for handler in list(target_logger.handlers):
        if getattr(handler, "_yen_sei_stage_file_handler", False):
            target_logger.removeHandler(handler)
            try:
                handler.close()
            except OSError:
                pass

    for path in (stamped_log, latest_log):
        file_handler = logging.FileHandler(path, mode="w", encoding="utf-8")
        file_handler.setFormatter(_JsonFormatter())
        setattr(file_handler, "_yen_sei_stage_file_handler", True)
        target_logger.addHandler(file_handler)

    deleted = cleanup_old(kind, "log", keep=keep, dirpath=DATA_DIR)
    deleted += cleanup_old_latest_pointers(kind, "log", keep=keep, dirpath=DATA_DIR)

    legacy_log = legacy_latest_pointer(kind, "log", DATA_DIR)
    if legacy_log.exists() or legacy_log.is_symlink():
        try:
            legacy_log.unlink()
        except OSError:
            pass

    return stamped_log, latest_log, deleted


def setup_logger(name: str = "yen_sei", *, verbose: bool = False) -> logging.Logger:
    """Configure and return the yen-sei logger."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(_JsonFormatter())
        logger.addHandler(handler)

    return logger
