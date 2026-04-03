"""
Batching utilities for OGS downloader.

Uses tools.core.batching for base functionality with OGS-specific helpers.
"""

from __future__ import annotations

from pathlib import Path

# Re-export all core batching functions
from tools.core.batching import (
    DEFAULT_BATCH_SIZE,
    BatchInfo,
    count_total_files,
    find_existing_batches,
    get_batch_for_file,
    get_current_batch,
)

__all__ = [
    "BatchInfo",
    "get_batch_for_file",
    "get_current_batch",
    "find_existing_batches",
    "count_total_files",
    "puzzle_exists",
    "DEFAULT_BATCH_SIZE",
]


def puzzle_exists(puzzle_id: int, sgf_dir: Path) -> bool:
    """Check if puzzle is already downloaded.

    Args:
        puzzle_id: OGS puzzle ID
        sgf_dir: SGF parent directory

    Returns:
        True if SGF file exists in any batch
    """
    if not sgf_dir.exists():
        return False

    # Check both old format (ogs-{id}.sgf) and new format ({id}.sgf)
    old_filename = f"ogs-{puzzle_id}.sgf"
    new_filename = f"{puzzle_id}.sgf"

    for batch_dir in sgf_dir.iterdir():
        if batch_dir.is_dir() and batch_dir.name.startswith("batch-"):
            if (batch_dir / old_filename).exists():
                return True
            if (batch_dir / new_filename).exists():
                return True

    return False
