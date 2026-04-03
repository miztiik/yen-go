"""
Batching utilities for TsumegoDragon downloader.

Uses tools.core.batching for base functionality.
Extra utilities for batch organization are included for standalone use.
"""

from __future__ import annotations

import logging
import re
import shutil
from pathlib import Path

# Re-export all core batching functions
from tools.core.batching import (
    DEFAULT_BATCH_SIZE,
    BatchInfo,
    count_total_files,
    find_existing_batches,
    get_batch_for_file,
    get_batch_for_file_fast,
    get_current_batch,
)

logger = logging.getLogger("tsumegodragon.batching")


__all__ = [
    "BatchInfo",
    "get_batch_for_file",
    "get_batch_for_file_fast",
    "get_current_batch",
    "find_existing_batches",
    "count_total_files",
    "batch_existing_files",
    "DEFAULT_BATCH_SIZE",
]


def extract_puzzle_number(filename: str) -> int | None:
    """Extract puzzle number from filename for sorting.

    Args:
        filename: Filename like '123.sgf' or 'puzzle-45.sgf'

    Returns:
        Extracted number or None if no number found.
    """
    # Try to extract leading numbers
    match = re.match(r'^(\d+)', filename)
    if match:
        return int(match.group(1))

    # Try to extract any number
    numbers = re.findall(r'\d+', filename)
    if numbers:
        return int(numbers[0])

    return None


def batch_existing_files(
    target_dir: Path,
    batch_size: int = DEFAULT_BATCH_SIZE,
    dry_run: bool = False,
    file_pattern: str = "*.sgf",
) -> dict[str, int]:
    """Organize existing files into batch subdirectories.

    Files are sorted numerically by filename and distributed into
    batch-001, batch-002, etc. subdirectories.

    Args:
        target_dir: Directory containing files to organize.
        batch_size: Maximum files per batch directory.
        dry_run: If True, only report what would be done.
        file_pattern: Glob pattern for files to organize.

    Returns:
        Dictionary with 'moved', 'batches' counts.
    """
    if not target_dir.exists():
        return {"moved": 0, "batches": 0}

    # Find all files in root (not in batch subdirectories)
    files = [f for f in target_dir.glob(file_pattern) if f.is_file()]

    if not files:
        return {"moved": 0, "batches": 0}

    # Sort files numerically
    files.sort(key=lambda f: (extract_puzzle_number(f.stem) or 0, f.name))

    moved = 0
    batches_created = set()

    for i, file_path in enumerate(files):
        batch_num = (i // batch_size) + 1
        batch_dir = target_dir / f"batch-{batch_num:03d}"

        if not dry_run:
            batch_dir.mkdir(exist_ok=True)
            dest = batch_dir / file_path.name
            shutil.move(str(file_path), str(dest))

        batches_created.add(batch_num)
        moved += 1

    return {"moved": moved, "batches": len(batches_created)}
