"""
Checkpoint management for Tsumego Hero downloader.

Uses tools.core.checkpoint for base functionality with Tsumego Hero-specific fields.
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

logger = logging.getLogger("tsumego_hero.checkpoint")


@dataclass
class THeroCheckpoint(ToolCheckpoint, BatchTrackingMixin):
    """Tsumego Hero-specific checkpoint state.

    Extends ToolCheckpoint with collection-based progress tracking.
    Batch tracking is provided by BatchTrackingMixin.
    """

    # Collection progress
    collections_completed: list[str] = field(default_factory=list)
    current_collection: str | None = None
    current_collection_name: str | None = None
    puzzle_index_in_collection: int = 0

    # Counters
    puzzles_downloaded: int = 0
    puzzles_skipped: int = 0
    puzzles_errors: int = 0

    # Error tracking (last N errors)
    recent_errors: list[str] = field(default_factory=list)

    def record_success(self, batch_size: int) -> None:
        """Record a successful file save and update batch tracking.

        MUST be called AFTER file is successfully written to disk.

        Args:
            batch_size: Maximum files per batch.
        """
        self.puzzles_downloaded += 1
        # Use mixin's batch tracking
        self.record_file_saved(batch_size)

    def record_skip(self, reason: str) -> None:
        """Record a skipped puzzle."""
        self.puzzles_skipped += 1

    def record_error(self, puzzle_id: int, error: str) -> None:
        """Record an error."""
        self.puzzles_errors += 1
        error_entry = f"puzzle {puzzle_id}: {error}"
        self.recent_errors.append(error_entry)
        # Keep only last 100 errors
        if len(self.recent_errors) > 100:
            self.recent_errors = self.recent_errors[-100:]

    def complete_collection(self, set_id: str) -> None:
        """Mark a collection as completed."""
        if set_id not in self.collections_completed:
            self.collections_completed.append(set_id)
        self.current_collection = None
        self.current_collection_name = None
        self.puzzle_index_in_collection = 0

    def start_collection(self, set_id: str, name: str) -> None:
        """Mark a collection as in-progress."""
        self.current_collection = set_id
        self.current_collection_name = name
        self.puzzle_index_in_collection = 0


# Re-export core functions with type hints for Tsumego Hero
def load_checkpoint(output_dir: Path) -> THeroCheckpoint | None:
    """Load Tsumego Hero checkpoint from file."""
    checkpoint = core_load(output_dir, THeroCheckpoint)
    if checkpoint:
        logger.info(
            f"Loaded checkpoint: {checkpoint.puzzles_downloaded} downloaded, "
            f"collection {checkpoint.current_collection or 'none'}, "
            f"batch {checkpoint.current_batch}"
        )
    return checkpoint


def save_checkpoint(checkpoint: THeroCheckpoint, output_dir: Path) -> None:
    """Save Tsumego Hero checkpoint to file."""
    core_save(checkpoint, output_dir)
    logger.debug(f"Saved checkpoint: {checkpoint.puzzles_downloaded} puzzles")


def clear_checkpoint(output_dir: Path) -> None:
    """Remove checkpoint file."""
    core_clear(output_dir)
    logger.info("Cleared checkpoint")
