"""
Logging configuration for GoProblems downloader.

Uses tools.core.logging for base functionality with GoProblems-specific
convenience methods.
"""

from __future__ import annotations

import logging
from pathlib import Path

from tools.core.logging import (
    EventType,
)
from tools.core.logging import (
    StructuredLogger as CoreStructuredLogger,
)
from tools.core.logging import (
    setup_logging as core_setup_logging,
)

__all__ = ["EventType", "StructuredLogger", "setup_logging", "get_logger"]


class StructuredLogger(CoreStructuredLogger):
    """GoProblems-specific structured logger with convenience methods."""

    def run_start(
        self,
        max_puzzles: int = 0,
        resume: bool = False,
        output_dir: str = "",
        **kwargs,
    ) -> None:
        """Log GoProblems run start."""
        super().run_start(
            output_dir=output_dir,
            max_items=max_puzzles,
            resume=resume,
            **kwargs,
        )

    def puzzle_fetch(self, puzzle_id: int, url: str) -> None:
        """Log puzzle detail fetch."""
        self.event(
            EventType.ITEM_FETCH,
            f"GET {url}",
            puzzle_id=puzzle_id,
            url=url,
        )

    def puzzle_save(
        self,
        puzzle_id: int,
        path: str,
        downloaded: int = 0,
        skipped: int = 0,
        errors: int = 0,
    ) -> None:
        """Log puzzle saved."""
        self.item_save(
            item_id=str(puzzle_id),
            path=path,
            downloaded=downloaded,
            skipped=skipped,
            errors=errors,
        )

    def puzzle_skip(self, puzzle_id: int, reason: str) -> None:
        """Log puzzle skipped."""
        self.item_skip(item_id=str(puzzle_id), reason=reason)

    def puzzle_error(self, puzzle_id: int, error: str) -> bool:
        """Log puzzle error. Returns True if should fail-fast."""
        return self.item_error(item_id=str(puzzle_id), error=error)

    def puzzle_not_found(self, puzzle_id: int) -> None:
        """Log puzzle not found (404)."""
        self.event(
            EventType.ITEM_SKIP,
            f"Puzzle {puzzle_id} not found (404)",
            puzzle_id=puzzle_id,
            reason="not_found",
        )


def setup_logging(
    output_dir: Path,
    verbose: bool = False,
    log_to_file: bool = True,
    max_consecutive_errors: int = 10,
) -> StructuredLogger:
    """Set up GoProblems logging.

    Args:
        output_dir: Directory for log files.
        verbose: Enable debug logging to console.
        log_to_file: Write JSON logs to file.
        max_consecutive_errors: Fail-fast threshold.

    Returns:
        StructuredLogger instance with GoProblems methods.
    """
    core_logger = core_setup_logging(
        output_dir=output_dir,
        logger_name="go_problems",
        verbose=verbose,
        log_to_file=log_to_file,
        log_suffix="goproblems",
        max_consecutive_errors=max_consecutive_errors,
    )

    gp_logger = StructuredLogger(core_logger.logger)
    gp_logger.set_max_errors(max_consecutive_errors)
    return gp_logger


def get_logger(name: str = "go_problems") -> StructuredLogger:
    """Get existing GoProblems logger by name."""
    return StructuredLogger(logging.getLogger(name))
