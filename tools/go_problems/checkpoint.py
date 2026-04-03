"""
Checkpoint management for GoProblems downloader.

Uses tools.core.checkpoint for base functionality with GoProblems-specific fields.
Batch tracking uses the core BatchTrackingMixin for DRY compliance.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from tools.core.checkpoint import (
    BatchTrackingMixin,
    ToolCheckpoint,
)
from tools.core.checkpoint import (
    clear_checkpoint as core_clear,
)
from tools.core.checkpoint import (
    load_checkpoint as core_load,
)
from tools.core.checkpoint import (
    save_checkpoint as core_save,
)

logger = logging.getLogger("go_problems.checkpoint")


@dataclass
class GoProblemsCheckpoint(ToolCheckpoint, BatchTrackingMixin):
    """GoProblems-specific checkpoint state.

    Extends ToolCheckpoint with GoProblems ID-based tracking.
    Batch tracking is provided by BatchTrackingMixin.
    """

    # Position tracking
    last_processed_id: int = 0
    last_successful_id: int = 0

    # Pagination tracking (for list mode)
    last_page: int = 0
    puzzle_index_in_page: int = -1  # -1 means page complete

    # Counters
    puzzles_downloaded: int = 0
    puzzles_skipped: int = 0
    puzzles_errors: int = 0
    puzzles_not_found: int = 0

    # Error tracking (last N errors)
    recent_errors: list[str] = field(default_factory=list)

    def record_success(self, puzzle_id: int, batch_size: int) -> None:
        """Record a successful file save and update batch tracking.

        Args:
            puzzle_id: ID of successfully saved puzzle
            batch_size: Maximum files per batch
        """
        self.last_processed_id = puzzle_id
        self.last_successful_id = puzzle_id
        self.puzzles_downloaded += 1
        self.record_file_saved(batch_size)

    def record_skip(self, puzzle_id: int, reason: str) -> None:
        """Record a skipped puzzle."""
        self.last_processed_id = puzzle_id
        self.puzzles_skipped += 1

    def record_not_found(self, puzzle_id: int) -> None:
        """Record a 404 (puzzle not found)."""
        self.last_processed_id = puzzle_id
        self.puzzles_not_found += 1

    def record_error(self, puzzle_id: int, error: str) -> None:
        """Record an error."""
        self.last_processed_id = puzzle_id
        self.puzzles_errors += 1
        error_entry = f"puzzle {puzzle_id}: {error}"
        self.recent_errors.append(error_entry)
        if len(self.recent_errors) > 100:
            self.recent_errors = self.recent_errors[-100:]


def load_checkpoint(output_dir: Path) -> GoProblemsCheckpoint | None:
    """Load GoProblems checkpoint from file."""
    checkpoint = core_load(output_dir, GoProblemsCheckpoint)
    if checkpoint:
        logger.info(
            f"Loaded checkpoint: {checkpoint.puzzles_downloaded} downloaded, "
            f"last_id {checkpoint.last_processed_id}, batch {checkpoint.current_batch}"
        )
    return checkpoint


def save_checkpoint(checkpoint: GoProblemsCheckpoint, output_dir: Path) -> None:
    """Save GoProblems checkpoint to file."""
    core_save(checkpoint, output_dir)
    logger.debug(f"Saved checkpoint: {checkpoint.puzzles_downloaded} puzzles")


def clear_checkpoint(output_dir: Path) -> None:
    """Remove checkpoint file."""
    core_clear(output_dir)
    logger.info("Cleared checkpoint")
