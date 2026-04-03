"""
Checkpoint management for OGS downloader.

Uses tools.core.checkpoint for base functionality with OGS-specific fields.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from tools.core.checkpoint import (
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

logger = logging.getLogger("ogs.checkpoint")


@dataclass
class OGSCheckpoint(ToolCheckpoint):
    """OGS-specific checkpoint state.

    Extends ToolCheckpoint with OGS pagination and batch tracking.
    """

    # Pagination state
    last_page: int = 0
    last_puzzle_id: int = 0
    puzzle_index_in_page: int = -1  # -1 means page complete

    # Counters
    puzzles_downloaded: int = 0
    puzzles_skipped: int = 0
    puzzles_errors: int = 0

    # Current batch info
    current_batch: int = 1
    files_in_current_batch: int = 0

    # Error tracking (last N errors)
    recent_errors: list[str] = field(default_factory=list)

    def record_success(self) -> None:
        """Record a successful download."""
        self.puzzles_downloaded += 1
        self.files_in_current_batch += 1

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

    def advance_batch(self, batch_size: int) -> None:
        """Check if we need to move to next batch."""
        if self.files_in_current_batch >= batch_size:
            self.current_batch += 1
            self.files_in_current_batch = 0


# Re-export core functions with type hints for OGS
def load_checkpoint(output_dir: Path) -> OGSCheckpoint | None:
    """Load OGS checkpoint from file."""
    checkpoint = core_load(output_dir, OGSCheckpoint)
    if checkpoint:
        logger.info(
            f"Loaded checkpoint: {checkpoint.puzzles_downloaded} downloaded, "
            f"page {checkpoint.last_page}, batch {checkpoint.current_batch}"
        )
    return checkpoint


def save_checkpoint(checkpoint: OGSCheckpoint, output_dir: Path) -> None:
    """Save OGS checkpoint to file."""
    core_save(checkpoint, output_dir)
    logger.debug(f"Saved checkpoint: {checkpoint.puzzles_downloaded} puzzles")


def clear_checkpoint(output_dir: Path) -> None:
    """Remove checkpoint file."""
    core_clear(output_dir)
    logger.info("Cleared checkpoint")


# Backwards compatibility alias
DownloadCheckpoint = OGSCheckpoint
