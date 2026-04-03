"""
Batching utilities for GoProblems downloader.

Uses tools.core.batching for all functionality with GoProblems-specific helpers.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .checkpoint import GoProblemsCheckpoint

# Re-export all core batching functions
from tools.core.batching import (
    DEFAULT_BATCH_SIZE,
    BatchInfo,
    count_total_files,
    find_existing_batches,
    get_batch_for_file,
    get_current_batch,
)
from tools.core.batching import (
    get_batch_for_file_fast as core_get_batch_for_file_fast,
)

__all__ = [
    "BatchInfo",
    "get_batch_for_file",
    "get_batch_for_file_fast",
    "get_current_batch",
    "find_existing_batches",
    "count_total_files",
    "DEFAULT_BATCH_SIZE",
]


def get_batch_for_file_fast(
    sgf_dir: Path,
    checkpoint: GoProblemsCheckpoint,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> Path:
    """Get batch directory using checkpoint state (O(1), no filesystem scan).

    Args:
        sgf_dir: SGF parent directory
        checkpoint: Current checkpoint with batch tracking state
        batch_size: Maximum files per batch

    Returns:
        Path to the batch directory for the next file
    """
    batch_dir, _ = core_get_batch_for_file_fast(
        parent_dir=sgf_dir,
        current_batch=checkpoint.current_batch,
        files_in_current_batch=checkpoint.files_in_current_batch,
        batch_size=batch_size,
    )
    return batch_dir
