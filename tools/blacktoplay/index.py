"""
Index file management for BTP puzzles.

Thin wrapper around tools.core.index with BTP-specific helpers.
Maintains sgf-index.txt with format: batch-XXX/btp-{id}.sgf
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from tools.core.index import (
    add_entry as core_add_entry,
)
from tools.core.index import (
    load_index as core_load_index,
)
from tools.core.index import (
    sort_and_rewrite as core_sort_and_rewrite,
)

logger = logging.getLogger("btp.index")

INDEX_FILENAME = "sgf-index.txt"

# BTP puzzle ID pattern: btp-XXXXXX where X is alphanumeric
_BTP_ID_PATTERN = re.compile(r"btp-([a-zA-Z0-9]+)\.sgf$")


def get_index_path(output_dir: Path) -> Path:
    """Get path to the index file."""
    return output_dir / INDEX_FILENAME


def load_puzzle_ids(output_dir: Path) -> set[str]:
    """Load index and extract puzzle IDs as a set of strings.

    Args:
        output_dir: Base output directory.

    Returns:
        Set of puzzle ID strings (e.g., {"000719", "82q0Z4", ...}).
    """
    index_path = get_index_path(output_dir)
    entries = core_load_index(index_path)
    return extract_ids(entries)


def extract_ids(entries: set[str]) -> set[str]:
    """Extract BTP puzzle IDs from index entries.

    Entry format: "batch-NNN/btp-{id}.sgf"

    Examples:
        "batch-001/btp-000719.sgf" -> "000719"
        "batch-001/btp-82q0Z4.sgf" -> "82q0Z4"

    Args:
        entries: Set of index entry strings.

    Returns:
        Set of puzzle ID strings.
    """
    ids: set[str] = set()
    for entry in entries:
        filename = entry.rsplit("/", 1)[-1] if "/" in entry else entry
        m = _BTP_ID_PATTERN.search(filename)
        if m:
            ids.add(m.group(1))
    return ids


def add_to_index(
    output_dir: Path,
    batch_name: str,
    filename: str,
) -> None:
    """Add an entry to the index file.

    Args:
        output_dir: Base output directory.
        batch_name: Batch directory name (e.g., "batch-001").
        filename: SGF filename (e.g., "btp-000719.sgf").
    """
    index_path = get_index_path(output_dir)
    entry = f"{batch_name}/{filename}"
    core_add_entry(index_path, entry)


def sort_index(output_dir: Path) -> int:
    """Sort index file by puzzle ID for readability and clean diffs.

    BTP IDs are alphanumeric so sorted lexicographically.

    Args:
        output_dir: Base output directory.

    Returns:
        Number of entries written.
    """
    index_path = get_index_path(output_dir)
    return core_sort_and_rewrite(index_path)


def rebuild_index(output_dir: Path, sgf_dir: Path) -> int:
    """Rebuild index from existing SGF files on disk.

    Uses BTP-specific sorting: numeric IDs first (ascending), then alphanumeric (lexicographic).

    Args:
        output_dir: Base output directory.
        sgf_dir: Directory containing batch subdirectories.

    Returns:
        Number of entries in rebuilt index.
    """
    entries: list[str] = []

    if sgf_dir.exists():
        for batch_dir in sorted(sgf_dir.iterdir()):
            if batch_dir.is_dir() and batch_dir.name.startswith("batch-"):
                for sgf_file in sorted(batch_dir.glob("*.sgf")):
                    entry = f"{batch_dir.name}/{sgf_file.name}"
                    entries.append(entry)

    # BTP-specific sort: numeric IDs first (by value), then alphanumeric (lexicographic)
    def sort_key(entry: str) -> tuple[int, int, str]:
        filename = entry.rsplit("/", 1)[-1] if "/" in entry else entry
        m = _BTP_ID_PATTERN.search(filename)
        if m:
            puzzle_id = m.group(1)
            # Check if it's a 6-digit numeric ID
            if len(puzzle_id) == 6 and puzzle_id.isdigit():
                return (0, int(puzzle_id), puzzle_id)  # Numeric: sort by value
            else:
                return (1, 0, puzzle_id)  # Alphanumeric: sort lexicographically
        return (2, 0, filename)  # Fallback: sort by filename

    entries.sort(key=sort_key)

    index_path = get_index_path(output_dir)
    try:
        with open(index_path, "w", encoding="utf-8") as f:
            for entry in entries:
                f.write(f"{entry}\n")
        logger.info(f"Rebuilt index: {len(entries)} entries from {sgf_dir}")
    except OSError as e:
        logger.error(f"Failed to rebuild index {index_path}: {e}")
        return 0

    return len(entries)
