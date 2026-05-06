"""
Index file management for 101weiqi downloader.

Thin wrapper around tools.core.index for sgf-index.txt tracking.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from tools.core.index import (
    add_entry,
    load_index,
    sort_and_rewrite,
)

INDEX_FILENAME = "sgf-index.txt"

logger = logging.getLogger(__name__)


def get_index_path(output_dir: Path) -> Path:
    """Get the index file path."""
    return output_dir / INDEX_FILENAME


def _load_book_puzzle_ids(output_dir: Path) -> set[int]:
    """Load puzzle IDs from all consolidated ``book.json`` files under books/.

    Scans ``books/*/book.json`` for positions with status ``captured``
    or ``external``. (The legacy ``book-index.json`` was retired in
    favour of a single per-book file in 2026-04-24.)
    """
    books_dir = output_dir / "books"
    if not books_dir.is_dir():
        return set()

    ids: set[int] = set()
    for book_state_path in books_dir.glob("*/book.json"):
        try:
            data = json.loads(book_state_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        for pos in data.get("positions", []):
            if pos.get("status") in ("captured", "external"):
                pid = pos.get("pid")
                if isinstance(pid, int):
                    ids.add(pid)
    if ids:
        logger.debug(f"Loaded {len(ids)} puzzle IDs from book.json files")
    return ids


def load_puzzle_ids(output_dir: Path) -> set[int]:
    """Load all known puzzle IDs from the index file and book state files.

    Sources:
    - sgf-index.txt (batch and qday entries)
    - books/*/book.json (captured and external positions)

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

    # Also load puzzle IDs from book captures
    ids.update(_load_book_puzzle_ids(output_dir))

    return ids


def add_to_index(output_dir: Path, batch_name: str, filename: str) -> None:
    """Add a new entry to the index file."""
    add_entry(output_dir / INDEX_FILENAME, f"{batch_name}/{filename}")


def add_book_to_index(
    output_dir: Path, book_dir_name: str, filename: str, pid: int
) -> None:
    """Add a book puzzle entry to the index file.

    Format mirrors the qday colon-pid convention so that
    ``load_puzzle_ids`` parses book entries via the existing
    ``":" in entry`` branch with zero reader changes.

    Example entry::

        books/197-life-and-death/sgf/ch01_005_life-and-death_9538.sgf:9538
    """
    entry = f"books/{book_dir_name}/sgf/{filename}:{pid}"
    add_entry(output_dir / INDEX_FILENAME, entry)


def sort_index(output_dir: Path) -> None:
    """Sort the index file for clean diffs."""
    sort_and_rewrite(output_dir / INDEX_FILENAME)
