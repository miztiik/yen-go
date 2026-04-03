"""
Checkpoint management for TsumegoDragon downloader.

Uses tools.core.checkpoint for base functionality with t-dragon-specific fields.
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

logger = logging.getLogger("tsumegodragon.checkpoint")


@dataclass
class TDragonCheckpoint(ToolCheckpoint, BatchTrackingMixin):
    """TsumegoDragon-specific checkpoint state.

    Extends ToolCheckpoint with category-based progress tracking
    and O(1) batch tracking via BatchTrackingMixin.
    """

    # Category progress
    categories_completed: list[str] = field(default_factory=list)
    current_category: str | None = None
    current_cursor: int = 0

    # Counters
    puzzles_downloaded: int = 0
    puzzles_skipped: int = 0

    # Error tracking
    errors: list[str] = field(default_factory=list)

    def record_success(self, batch_size: int = 500) -> None:
        """Record a successful download."""
        self.puzzles_downloaded += 1
        self.record_file_saved(batch_size)

    def record_skip(self, reason: str) -> None:
        """Record a skipped puzzle."""
        self.puzzles_skipped += 1

    def record_error(self, puzzle_id: str, error: str) -> None:
        """Record an error."""
        error_entry = f"{puzzle_id}: {error}"
        self.errors.append(error_entry)
        # Keep only last 100 errors
        if len(self.errors) > 100:
            self.errors = self.errors[-100:]

    def complete_category(self, category: str) -> None:
        """Mark a category as completed."""
        if category not in self.categories_completed:
            self.categories_completed.append(category)
        self.current_category = None
        self.current_cursor = 0


# Re-export core functions with type hints for t-dragon
def load_checkpoint(output_dir: Path) -> TDragonCheckpoint | None:
    """Load TsumegoDragon checkpoint from file."""
    checkpoint = core_load(output_dir, TDragonCheckpoint)
    if checkpoint:
        logger.info(
            f"Loaded checkpoint: {checkpoint.puzzles_downloaded} puzzles downloaded, "
            f"current category: {checkpoint.current_category}"
        )
    return checkpoint


def save_checkpoint(checkpoint: TDragonCheckpoint, output_dir: Path) -> None:
    """Save TsumegoDragon checkpoint to file."""
    core_save(checkpoint, output_dir)
    logger.debug(f"Saved checkpoint: {checkpoint.puzzles_downloaded} puzzles")


def clear_checkpoint(output_dir: Path) -> None:
    """Remove checkpoint file."""
    core_clear(output_dir)
    logger.info("Cleared checkpoint")
