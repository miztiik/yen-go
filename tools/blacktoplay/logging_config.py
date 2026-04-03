"""
Logging configuration for BTP downloader.

Uses tools.core.logging for base functionality with BTP-specific convenience methods.
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

# Re-export EventType for convenience
__all__ = ["EventType", "StructuredLogger", "setup_logging", "get_logger"]


class StructuredLogger(CoreStructuredLogger):
    """BTP-specific structured logger with convenience methods."""

    def puzzle_skip(self, puzzle_id: int | str, reason: str) -> None:
        """Log puzzle skipped with reason."""
        self.item_skip(item_id=str(puzzle_id), reason=reason)

    def puzzle_save(
        self,
        puzzle_id: int | str,
        path: str,
        downloaded: int = 0,
        skipped: int = 0,
        errors: int = 0,
    ) -> None:
        """Log puzzle saved with running totals."""
        self.item_save(
            item_id=str(puzzle_id),
            path=path,
            downloaded=downloaded,
            skipped=skipped,
            errors=errors,
        )

    def puzzle_error(self, puzzle_id: int | str, error: str) -> bool:
        """Log puzzle error."""
        return self.item_error(item_id=str(puzzle_id), error=error)

    def run_start(
        self,
        max_puzzles: int = 0,
        resume: bool = False,
        output_dir: str = "",
        puzzle_types: str = "",
        **kwargs,
    ) -> None:
        """Log BTP run start."""
        super().run_start(
            output_dir=output_dir,
            max_items=max_puzzles,
            resume=resume,
            puzzle_types=puzzle_types,
            **kwargs,
        )

    def type_start(self, puzzle_type: int, type_name: str, total: int) -> None:
        """Log start of a puzzle type download."""
        self.event(
            EventType.BATCH_START,
            f"Starting {type_name} (type {puzzle_type}): {total} puzzles",
            puzzle_type=puzzle_type,
            type_name=type_name,
            total_puzzles=total,
        )

    def type_end(self, puzzle_type: int, type_name: str, downloaded: int, skipped: int, errors: int) -> None:
        """Log end of a puzzle type download."""
        self.event(
            EventType.BATCH_END,
            f"Finished {type_name}: {downloaded} downloaded, {skipped} skipped, {errors} errors",
            puzzle_type=puzzle_type,
            type_name=type_name,
            downloaded=downloaded,
            skipped=skipped,
            errors=errors,
        )


def setup_logging(
    logs_dir: Path | None = None,
    verbose: bool = False,
) -> StructuredLogger:
    """Set up logging for BTP downloader.

    Args:
        logs_dir: Directory for log files. If None, console only.
        verbose: Enable DEBUG level output.

    Returns:
        Configured StructuredLogger instance.
    """
    # When logs_dir is None, use console-only mode with a dummy path
    core_logger = core_setup_logging(
        output_dir=logs_dir or Path("."),
        logger_name="btp",
        verbose=verbose,
        log_to_file=(logs_dir is not None),
        log_suffix="btp-download",
    )

    # Wrap in BTP-specific logger
    return StructuredLogger(core_logger.logger, core_logger.extra)


def get_logger() -> StructuredLogger:
    """Get the BTP structured logger (assumes setup_logging was called)."""
    base_logger = logging.getLogger("btp")
    return StructuredLogger(base_logger, {})
