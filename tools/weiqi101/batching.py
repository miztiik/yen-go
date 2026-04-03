"""
Batch directory management for 101weiqi downloader.

Thin wrapper around tools.core.batching for batch-001/, batch-002/, etc.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from tools.core.batching import (
    get_batch_for_file_fast as core_get_batch_fast,
)

from .config import DEFAULT_BATCH_SIZE

if TYPE_CHECKING:
    from .checkpoint import WeiQiCheckpoint


def get_batch_for_file_fast(
    sgf_dir: Path,
    checkpoint: WeiQiCheckpoint,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> Path:
    """Get the batch directory for the next file using checkpoint state.

    O(1) operation — no filesystem scan needed.
    """
    batch_dir, _batch_num = core_get_batch_fast(
        sgf_dir,
        checkpoint.current_batch,
        checkpoint.files_in_current_batch,
        batch_size,
    )
    return batch_dir
