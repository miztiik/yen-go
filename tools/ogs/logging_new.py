"""
Logging configuration for OGS downloader.

Uses tools.core.logging for base functionality with OGS-specific convenience methods.
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

# Re-export EventType for backwards compatibility
__all__ = ["EventType", "StructuredLogger", "setup_logging", "get_logger"]


class StructuredLogger(CoreStructuredLogger):
    """OGS-specific structured logger with convenience methods.

    Extends core StructuredLogger with OGS-specific event methods.
    """

    # OGS-specific convenience methods

    def run_start(
        self,
        max_puzzles: int = 0,
        resume: bool = False,
        output_dir: str = "",
        **kwargs,
    ) -> None:
        """Log OGS run start."""
        # Call parent with standardized parameters
        super().run_start(
            output_dir=output_dir,
            max_items=max_puzzles,
            resume=resume,
            **kwargs,
        )

    def page_start(self, page: int, total_pages: int, url: str = "") -> None:
        """Log page fetch start."""
        self.event(
            EventType.PAGE_START,
            f"GET page {page}/{total_pages}",
            page=page,
            total_pages=total_pages,
            url=url,
        )

    def page_fetch(self, page: int, url: str, puzzle_count: int) -> None:
        """Log page URL being fetched."""
        self.event(
            EventType.PAGE_FETCH,
            f"FETCHED page {page}: {puzzle_count} puzzles",
            page=page,
            url=url,
            puzzle_count=puzzle_count,
        )

    def puzzle_fetch(self, puzzle_id: int, url: str) -> None:
        """Log puzzle detail fetch."""
        self.event(
            EventType.ITEM_FETCH,
            f"GET puzzle {puzzle_id}",
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


def setup_logging(
    output_dir: Path,
    verbose: bool = False,
    log_to_file: bool = True,
    max_consecutive_errors: int = 10,
) -> StructuredLogger:
    """Set up OGS logging.

    Args:
        output_dir: Directory for log files.
        verbose: Enable debug logging to console.
        log_to_file: Write JSON logs to file.
        max_consecutive_errors: Fail-fast threshold.

    Returns:
        StructuredLogger instance with OGS methods.
    """
    # Use core setup but wrap result in OGS-specific logger
    core_logger = core_setup_logging(
        output_dir=output_dir,
        logger_name="ogs",
        verbose=verbose,
        log_to_file=log_to_file,
        log_prefix="ogs-download",
        max_consecutive_errors=max_consecutive_errors,
    )

    # Create OGS logger that wraps the same underlying logger
    ogs_logger = StructuredLogger(core_logger.logger)
    ogs_logger.set_max_errors(max_consecutive_errors)
    return ogs_logger


def get_logger(name: str = "ogs") -> StructuredLogger:
    """Get existing OGS logger by name."""
    return StructuredLogger(logging.getLogger(name))
