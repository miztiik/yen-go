"""
Index file management for OGS puzzles.

Thin wrapper around tools.core.index with OGS-specific helpers.
Maintains sgf-index.txt with format: batch-XXX/{id}.sgf
"""

from __future__ import annotations

import logging
from pathlib import Path

from tools.core.index import (
    add_entry as core_add_entry,
)
from tools.core.index import (
    extract_ids as core_extract_ids,
)
from tools.core.index import (
    load_index as core_load_index,
)
from tools.core.index import (
    rebuild_from_filesystem as core_rebuild_from_filesystem,
)
from tools.core.index import (
    sort_and_rewrite as core_sort_and_rewrite,
)

logger = logging.getLogger("ogs.index")


INDEX_FILENAME = "sgf-index.txt"


def get_index_path(output_dir: Path) -> Path:
    """Get path to the index file."""
    return output_dir / INDEX_FILENAME


def load_puzzle_ids(output_dir: Path) -> set[int]:
    """Load index and extract puzzle IDs as a set of ints.

    Args:
        output_dir: Base output directory.

    Returns:
        Set of puzzle IDs (e.g., {45, 1555, 6544, ...}).
    """
    index_path = get_index_path(output_dir)
    entries = core_load_index(index_path)
    return core_extract_ids(entries)


def add_to_index(
    output_dir: Path,
    batch_name: str,
    filename: str,
) -> None:
    """Add an entry to the index file.

    Args:
        output_dir: Base output directory.
        batch_name: Batch directory name (e.g., "batch-001").
        filename: SGF filename (e.g., "12345.sgf").
    """
    index_path = get_index_path(output_dir)
    entry = f"{batch_name}/{filename}"
    core_add_entry(index_path, entry)


def sort_index(output_dir: Path) -> int:
    """Sort index file by puzzle ID for readability and clean diffs.

    Args:
        output_dir: Base output directory.

    Returns:
        Number of entries written.
    """
    index_path = get_index_path(output_dir)
    return core_sort_and_rewrite(index_path)


def rebuild_index(output_dir: Path, sgf_dir: Path) -> int:
    """Rebuild index from existing SGF files on disk.

    Args:
        output_dir: Base output directory.
        sgf_dir: Directory containing batch subdirectories.

    Returns:
        Number of entries in rebuilt index.
    """
    index_path = get_index_path(output_dir)
    return core_rebuild_from_filesystem(sgf_dir, index_path)
