"""
Structured logging setup for 101weiqi downloader.

Configures console + JSONL file logging via tools.core.logging.
"""

from __future__ import annotations

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
    return core_setup_logging(
        output_dir=output_dir,
        logger_name="101weiqi",
        verbose=verbose,
        log_suffix="101weiqi",
    )
