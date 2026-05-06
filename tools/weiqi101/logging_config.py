"""
Structured logging setup for 101weiqi downloader.

Configures console + JSONL file logging via tools.core.logging.

v5.55.0: console output is routed through a stdlib QueueHandler/
QueueListener pair so that high-frequency log calls inside the
HTTP request thread (per-/capture: CAPTURE-RECV, SAVED, PROGRESS,
TIMING, etc.) do not block on Win32 console WriteFile syscalls.
The receiver's request thread now spends microseconds on log calls
instead of tens of milliseconds, eliminating the burst-and-flush
appearance on the receiver terminal. File handlers are NOT moved
behind the queue so on-disk JSONL ordering remains exactly per-call
deterministic for forensic audits.
"""

from __future__ import annotations

import atexit
import logging
import logging.handlers
import queue
import sys
from pathlib import Path

from tools.core.logging import setup_logging as core_setup_logging


def setup_logging(
    output_dir: Path,
    verbose: bool = False,
    log_to_file: bool = True,
) -> object:
    """Configure structured logging for the 101weiqi downloader.

    Args:
        output_dir: Base output directory (logs go in logs/ subdir).
        verbose: Whether to enable DEBUG logging.
        log_to_file: Whether to write JSONL log file.

    Returns:
        Configured logger.
    """
    structured = core_setup_logging(
        output_dir=output_dir,
        logger_name="101weiqi",
        verbose=verbose,
        log_suffix="101weiqi",
    )
    _wrap_console_in_queue(structured)
    return structured


def _wrap_console_in_queue(structured: object) -> None:
    """Replace the console StreamHandler on the underlying logger with a
    QueueHandler whose listener thread holds the original handler.

    Idempotent: if the logger already has a QueueHandler attached, no-op.
    Safe to call after every setup; only the FIRST call wires the queue.
    Console-only: the JSONL file handler stays in the request thread so
    on-disk ordering matches the call order exactly.
    """
    underlying = getattr(structured, "logger", None)
    if underlying is None or not isinstance(underlying, logging.Logger):
        return
    # Already wrapped?
    if any(isinstance(h, logging.handlers.QueueHandler) for h in underlying.handlers):
        return

    # Find the console StreamHandler that core_setup_logging attached.
    # Identification: a StreamHandler whose stream is sys.stdout (file
    # handlers are FileHandler subclasses; the QueueHandler we add is
    # not yet present). We move ONLY this handler behind the queue.
    console_handlers: list[logging.Handler] = []
    for h in list(underlying.handlers):
        if (
            isinstance(h, logging.StreamHandler)
            and not isinstance(h, logging.FileHandler)
            and getattr(h, "stream", None) is sys.stdout
        ):
            console_handlers.append(h)
            underlying.removeHandler(h)

    if not console_handlers:
        # Nothing to wrap (unexpected layout); leave logger untouched.
        return

    log_queue: queue.Queue = queue.Queue(maxsize=10000)
    queue_handler = logging.handlers.QueueHandler(log_queue)
    queue_handler.setLevel(logging.DEBUG)
    underlying.addHandler(queue_handler)

    listener = logging.handlers.QueueListener(
        log_queue, *console_handlers, respect_handler_level=True,
    )
    listener.start()

    # Best-effort drain on interpreter shutdown so the last few lines
    # (e.g. SIGINT-driven shutdown summary) still surface.
    atexit.register(listener.stop)
