"""
Checkpoint/resume support for 101weiqi downloader.

Tracks download progress for resumable operations using tools.core.checkpoint.
"""

from __future__ import annotations

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

from .config import CHECKPOINT_VERSION


@dataclass
class WeiQiCheckpoint(ToolCheckpoint, BatchTrackingMixin):
    """Checkpoint state for 101weiqi downloader.

    Tracks progress through daily dates or puzzle ID ranges,
    along with batch directory state for O(1) file placement.
    """

    version: str = CHECKPOINT_VERSION

    # Source-specific progress
    source_mode: str = ""  # "daily" or "puzzle"

    # Daily mode progress
    last_date: str = ""      # "YYYY-MM-DD"
    last_puzzle_num: int = 0  # 1-8

    # Puzzle mode progress
    last_puzzle_id: int = 0

    # Counters
    puzzles_downloaded: int = 0
    puzzles_skipped: int = 0
    puzzles_errors: int = 0

    # Error tracking (last N errors for diagnostics)
    recent_errors: list[dict] = field(default_factory=list)

    def record_success(self, batch_size: int) -> None:
        """Record a successfully downloaded puzzle."""
        self.puzzles_downloaded += 1
        self.record_file_saved(batch_size)

    def record_skip(self, reason: str = "") -> None:
        """Record a skipped puzzle."""
        self.puzzles_skipped += 1

    def record_error(self, puzzle_ref: str, error: str) -> None:
        """Record a puzzle download error."""
        self.puzzles_errors += 1
        self.recent_errors.append({"puzzle": puzzle_ref, "error": error})
        # Keep only last 100 errors
        if len(self.recent_errors) > 100:
            self.recent_errors = self.recent_errors[-100:]


def load_checkpoint(output_dir: Path) -> WeiQiCheckpoint | None:
    """Load checkpoint from output directory."""
    return core_load(output_dir, WeiQiCheckpoint)


def save_checkpoint(checkpoint: WeiQiCheckpoint, output_dir: Path) -> None:
    """Save checkpoint to output directory."""
    core_save(checkpoint, output_dir)


def clear_checkpoint(output_dir: Path) -> None:
    """Clear checkpoint file."""
    core_clear(output_dir)
