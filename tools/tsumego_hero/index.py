"""
Index management for Tsumego Hero puzzles.

Thin wrapper around tools.core.index for O(1) puzzle dedup.
Puzzle filenames: th-{url_id}.sgf → IDs are numeric integers.
"""

from __future__ import annotations

import re
from pathlib import Path

from tools.core.index import (
    add_entry,
    rebuild_from_filesystem,
    sort_and_rewrite,
)
from tools.core.index import (
    load_index as core_load_index,
)

INDEX_FILENAME = "sgf-index.txt"
SGF_DIR_NAME = "sgf"


def load_puzzle_ids(output_dir: Path) -> set[int]:
    """Load all known puzzle IDs from the index file.

    Extracts numeric IDs from the th-{id}.sgf filename pattern.

    Args:
        output_dir: Base output directory (e.g., external-sources/t-hero/).

    Returns:
        Set of numeric puzzle IDs.
    """
    raw_lines = core_load_index(output_dir / INDEX_FILENAME)
    ids: set[int] = set()
    for line in raw_lines:
        m = re.search(r"th-(\d+)\.sgf$", line)
        if m:
            ids.add(int(m.group(1)))
    return ids


def add_to_index(
    output_dir: Path,
    batch_name: str,
    filename: str,
) -> None:
    """Append a newly saved puzzle to the index.

    Args:
        output_dir: Base output directory.
        batch_name: e.g. "batch-001".
        filename: e.g. "th-5225.sgf".
    """
    add_entry(
        output_dir / INDEX_FILENAME,
        f"{SGF_DIR_NAME}/{batch_name}/{filename}",
    )


def sort_index(output_dir: Path) -> None:
    """Sort the index file for deterministic, diffable output."""
    sort_and_rewrite(output_dir / INDEX_FILENAME)


def rebuild_index(output_dir: Path) -> None:
    """Rebuild the index from filesystem contents."""
    rebuild_from_filesystem(
        index_path=output_dir / INDEX_FILENAME,
        sgf_dir=output_dir / SGF_DIR_NAME,
        prefix=SGF_DIR_NAME,
    )
