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
from typing import Any

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


def setup_logger(name: str = "yen_sei", *, verbose: bool = False) -> logging.Logger:
    """Configure and return the yen-sei logger."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(_JsonFormatter())
        logger.addHandler(handler)

    return logger
