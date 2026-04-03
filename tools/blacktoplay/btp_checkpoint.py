"""
Checkpoint state for BTP downloader.

Extends tools.core.checkpoint with BTP-specific fields for tracking
download progress across puzzle types.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from tools.core.checkpoint import (
    BatchTrackingMixin,
    ToolCheckpoint,
)
from tools.core.checkpoint import (
    clear_checkpoint as _core_clear,
)
from tools.core.checkpoint import (
    load_checkpoint as _core_load,
)
from tools.core.checkpoint import (
    save_checkpoint as _core_save,
)


@dataclass
class BTPCheckpoint(ToolCheckpoint, BatchTrackingMixin):
    """Checkpoint state for BTP puzzle downloads.

    Tracks per-type progress so downloads can resume after interruption.

    Attributes:
        puzzles_downloaded: Total puzzles successfully saved.
        puzzles_skipped: Total puzzles skipped (already exist).
        puzzles_errors: Total puzzles that failed.
        completed_types: List of puzzle types fully downloaded.
        current_type: Currently downloading type (0/1/2).
        current_type_index: Index within current type's puzzle list.
    """

    puzzles_downloaded: int = 0
    puzzles_skipped: int = 0
    puzzles_errors: int = 0
    completed_types: list[int] = field(default_factory=list)
    current_type: int = 0
    current_type_index: int = 0


def load_checkpoint(output_dir: Path) -> BTPCheckpoint | None:
    """Load BTP checkpoint from output directory.

    Returns:
        BTPCheckpoint if found, None otherwise.
    """
    return _core_load(output_dir, BTPCheckpoint)


def save_checkpoint(checkpoint: BTPCheckpoint, output_dir: Path) -> None:
    """Save BTP checkpoint to output directory."""
    _core_save(checkpoint, output_dir)


def clear_checkpoint(output_dir: Path) -> None:
    """Clear BTP checkpoint file."""
    _core_clear(output_dir)
