"""
Batching utilities for Tsumego Hero downloader.

Uses tools.core.batching for base functionality.
"""

from __future__ import annotations

import logging
from pathlib import Path

# Re-export all core batching functions
from tools.core.batching import (
    DEFAULT_BATCH_SIZE,
    BatchInfo,
    BatchState,
    count_total_files,
    find_existing_batches,
    get_batch_for_file,
    get_batch_for_file_fast,
    get_current_batch,
)

logger = logging.getLogger("tsumego_hero.batching")


# Default batch size for Tsumego Hero - 500 files per directory
THERO_BATCH_SIZE = 500


__all__ = [
    "BatchInfo",
    "BatchState",
    "get_batch_for_file",
    "get_batch_for_file_fast",
    "get_current_batch",
    "find_existing_batches",
    "count_total_files",
    "DEFAULT_BATCH_SIZE",
    "THERO_BATCH_SIZE",
    "get_sgf_dir",
]


def get_sgf_dir(output_dir: Path) -> Path:
    """Get the sgf/ subdirectory for storing puzzle files.

    Args:
        output_dir: Base output directory (e.g., external-sources/t-hero/).

    Returns:
        Path to sgf/ subdirectory.
    """
    return output_dir / "sgf"


# puzzle_exists() removed — use index-based O(1) dedup via tools.tsumego_hero.index
