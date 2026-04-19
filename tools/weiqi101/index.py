"""
Index file management for 101weiqi downloader.

Thin wrapper around tools.core.index for sgf-index.txt tracking.
"""

from __future__ import annotations

from pathlib import Path

from tools.core.index import (
    add_entry,
    load_index,
    sort_and_rewrite,
)

INDEX_FILENAME = "sgf-index.txt"


def get_index_path(output_dir: Path) -> Path:
    """Get the index file path."""
    return output_dir / INDEX_FILENAME


def load_puzzle_ids(output_dir: Path) -> set[int]:
    """Load all known puzzle IDs from the index file.

    Supports two entry formats:
    - Batch: "batch-001/78000.sgf" (puzzle ID is the filename stem)
    - Qday:  "qday/2026/04/20260414-3.sgf:354411" (puzzle ID after colon)

    Returns:
        Set of puzzle IDs for O(1) duplicate checking.
    """
    entries = load_index(output_dir / INDEX_FILENAME)
    ids: set[int] = set()
    for entry in entries:
        # Qday format: path:puzzle_id
        if ":" in entry:
            _, _, pid_str = entry.rpartition(":")
            try:
                ids.add(int(pid_str))
            except ValueError:
                pass
            continue
        # Batch format: batch-001/78000.sgf
        filename = entry.rsplit("/", 1)[-1] if "/" in entry else entry
        stem = filename.replace(".sgf", "")
        try:
            ids.add(int(stem))
        except ValueError:
            continue
    return ids


def add_to_index(output_dir: Path, batch_name: str, filename: str) -> None:
    """Add a new entry to the index file."""
    add_entry(output_dir / INDEX_FILENAME, f"{batch_name}/{filename}")


def sort_index(output_dir: Path) -> None:
    """Sort the index file for clean diffs."""
    sort_and_rewrite(output_dir / INDEX_FILENAME)
