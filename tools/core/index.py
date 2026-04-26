"""
Generic file index for duplicate prevention and tracking.

Provides a simple text-file-based index: one entry per line.
Entries are typically relative POSIX paths like "batch-001/12345.sgf".
Reusable across all download tools.

Usage:
    from tools.core.index import load_index, extract_ids, add_entry

    entries = load_index(index_path)
    known_ids = extract_ids(entries)

    if puzzle_id not in known_ids:
        # download and save...
        add_entry(index_path, "batch-001/12345.sgf")
        known_ids.add(puzzle_id)

    # At end of run, sort for human readability and git diffs:
    sort_and_rewrite(index_path)
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

logger = logging.getLogger("tools.core.index")

# Regex: last numeric sequence before .sgf extension
_ID_PATTERN = re.compile(r"(\d+)\.sgf$")


def load_index(index_path: Path) -> set[str]:
    """Load index entries from text file.

    Returns set of entry strings (e.g., {"batch-001/12345.sgf", ...}).
    Ignores comments (lines starting with #) and blank lines.

    Args:
        index_path: Path to the index text file.

    Returns:
        Set of entry strings. Empty set if file doesn't exist.
    """
    if not index_path.exists():
        return set()

    entries: set[str] = set()
    try:
        with open(index_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    entries.add(line)
        logger.debug(f"Loaded {len(entries)} entries from {index_path.name}")
    except OSError as e:
        logger.warning(f"Failed to load index {index_path}: {e}")

    return entries


def extract_ids(entries: set[str]) -> set[int]:
    """Extract numeric IDs from index entries.

    Handles both "{id}.sgf" and "prefix-{id}.sgf" naming conventions,
    plus the colon-pid suffix used by qday and book entries.

    Examples:
        "batch-001/12345.sgf" -> 12345
        "batch-001/ogs-12345.sgf" -> 12345
        "qday/2026/04/20260414-3-354411.sgf:354411" -> 354411
        "books/197-ld/sgf/ch01_005_ld_9538.sgf:9538" -> 9538

    Args:
        entries: Set of index entry strings.

    Returns:
        Set of integer IDs.
    """
    ids: set[int] = set()
    for entry in entries:
        # Colon-pid suffix (qday / book entries): extract pid after last colon
        if ":" in entry:
            _, _, pid_str = entry.rpartition(":")
            try:
                ids.add(int(pid_str))
            except ValueError:
                pass
            continue
        # Batch format: extract from filename
        filename = entry.rsplit("/", 1)[-1] if "/" in entry else entry
        m = _ID_PATTERN.search(filename)
        if m:
            ids.add(int(m.group(1)))
    return ids


def add_entry(index_path: Path, entry: str) -> None:
    """Append a single entry to the index file.

    Args:
        index_path: Path to the index text file.
        entry: Entry string (e.g., "batch-001/12345.sgf").
    """
    try:
        with open(index_path, "a", encoding="utf-8") as f:
            f.write(f"{entry}\n")
    except OSError as e:
        logger.error(f"Failed to write to index {index_path}: {e}")


def sort_and_rewrite(index_path: Path) -> int:
    """Sort index entries by numeric ID and rewrite the file.

    Deduplicates entries and sorts by the numeric puzzle ID extracted
    from the filename. Produces stable output for clean git diffs.

    Args:
        index_path: Path to the index text file.

    Returns:
        Number of entries written. 0 if file doesn't exist or on error.
    """
    entries = load_index(index_path)
    if not entries:
        return 0

    def sort_key(entry: str) -> int:
        # Colon-pid suffix (qday / book entries): use pid for sorting
        if ":" in entry:
            try:
                return int(entry.rpartition(":")[2])
            except ValueError:
                pass
        filename = entry.rsplit("/", 1)[-1] if "/" in entry else entry
        m = _ID_PATTERN.search(filename)
        return int(m.group(1)) if m else 0

    sorted_entries = sorted(entries, key=sort_key)

    try:
        with open(index_path, "w", encoding="utf-8") as f:
            for entry in sorted_entries:
                f.write(f"{entry}\n")
        logger.info(f"Sorted index: {len(sorted_entries)} entries")
    except OSError as e:
        logger.error(f"Failed to sort index {index_path}: {e}")
        return 0

    return len(sorted_entries)


def rebuild_from_filesystem(
    scan_dir: Path,
    index_path: Path,
    file_pattern: str = "*.sgf",
    dir_prefix: str = "batch-",
) -> int:
    """Rebuild index by scanning filesystem.

    Scans all directories matching dir_prefix under scan_dir, collects
    matching files, and writes a sorted index file.

    Args:
        scan_dir: Parent directory containing batch subdirectories.
        index_path: Path to write the index file.
        file_pattern: Glob pattern for files to index.
        dir_prefix: Directory name prefix to scan.

    Returns:
        Number of entries written.
    """
    entries: list[str] = []

    if scan_dir.exists():
        for batch_dir in sorted(scan_dir.iterdir()):
            if batch_dir.is_dir() and batch_dir.name.startswith(dir_prefix):
                for sgf_file in sorted(batch_dir.glob(file_pattern)):
                    entry = f"{batch_dir.name}/{sgf_file.name}"
                    entries.append(entry)

    # Sort by numeric ID
    def sort_key(entry: str) -> int:
        filename = entry.rsplit("/", 1)[-1] if "/" in entry else entry
        m = _ID_PATTERN.search(filename)
        return int(m.group(1)) if m else 0

    entries.sort(key=sort_key)

    try:
        with open(index_path, "w", encoding="utf-8") as f:
            for entry in entries:
                f.write(f"{entry}\n")
        logger.info(f"Rebuilt index: {len(entries)} entries from {scan_dir}")
    except OSError as e:
        logger.error(f"Failed to rebuild index {index_path}: {e}")
        return 0

    return len(entries)
