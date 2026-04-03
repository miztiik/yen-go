"""
Reverse index from puzzle IDs to OGS collection names.

Built from the sorted JSONL file produced by sort_collections.py.
Each OGS collection record contains a ``puzzles`` array listing all
puzzle IDs in that collection.  Inverting this gives: for any puzzle ID,
which OGS collections contain it?

Pattern: follows tools/ogs/collections.py singleton structure.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger("ogs.collection_index")


class CollectionIndex:
    """Reverse index from puzzle_id to OGS collection names.

    Loaded from the sorted JSONL file produced by sort_collections.py.
    """

    def __init__(self) -> None:
        # puzzle_id -> list of (ogs_collection_name, ogs_collection_id)
        self._reverse_index: dict[int, list[tuple[str, int]]] = {}
        self._collection_count: int = 0

    @classmethod
    def from_jsonl(cls, jsonl_path: Path) -> CollectionIndex:
        """Build reverse index from sorted JSONL file.

        Args:
            jsonl_path: Path to sorted (or unsorted) collections JSONL.

        Returns:
            Populated CollectionIndex.
        """
        index = cls()

        if not jsonl_path.exists():
            logger.warning(f"Collections JSONL not found: {jsonl_path}")
            return index

        lines = jsonl_path.read_text(encoding="utf-8").splitlines()

        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue

            # Skip the metadata line (type == "metadata")
            if record.get("type") != "collection":
                continue

            ogs_id: int = record["id"]
            ogs_name: str = record["name"]
            puzzles: list[int] = record.get("puzzles", [])

            if not puzzles:
                continue

            index._collection_count += 1

            for puzzle_id in puzzles:
                if puzzle_id not in index._reverse_index:
                    index._reverse_index[puzzle_id] = []
                index._reverse_index[puzzle_id].append((ogs_name, ogs_id))

        logger.info(
            f"Built reverse index: {len(index._reverse_index)} puzzle IDs "
            f"across {index._collection_count} collections"
        )
        return index

    def get_collections(self, puzzle_id: int) -> list[tuple[str, int]]:
        """Get all OGS collections containing this puzzle.

        Args:
            puzzle_id: OGS puzzle ID.

        Returns:
            List of (collection_name, collection_id) tuples.
            Empty list if puzzle not found in any collection.
        """
        return self._reverse_index.get(puzzle_id, [])

    @property
    def total_puzzle_ids(self) -> int:
        """Number of unique puzzle IDs in the index."""
        return len(self._reverse_index)

    @property
    def total_collections(self) -> int:
        """Number of collections indexed."""
        return self._collection_count


# ---------------------------------------------------------------------------
# Singleton + convenience function
# ---------------------------------------------------------------------------

_collection_index: CollectionIndex | None = None


def get_collection_index(jsonl_path: Path | None = None) -> CollectionIndex:
    """Get the global CollectionIndex instance.

    Lazily loads from the JSONL file on first access.

    Args:
        jsonl_path: Optional explicit path to the sorted collections JSONL.
            If None, attempts auto-discovery in the default output directory.

    Returns:
        CollectionIndex (may be empty if file not found).
    """
    global _collection_index
    if _collection_index is None:
        if jsonl_path is None:
            jsonl_path = find_sorted_jsonl()
        if jsonl_path is not None:
            _collection_index = CollectionIndex.from_jsonl(jsonl_path)
        else:
            logger.warning("No collections JSONL found; reverse index is empty")
            _collection_index = CollectionIndex()
    return _collection_index


def reset_collection_index() -> None:
    """Reset the global singleton (for testing)."""
    global _collection_index
    _collection_index = None


def find_sorted_jsonl(search_dir: Path | None = None) -> Path | None:
    """Find the most recent sorted collections JSONL file.

    Looks for ``*-collections-sorted.jsonl`` in the search directory.
    Falls back to unsorted ``*-collections.jsonl`` if no sorted file found.

    Args:
        search_dir: Directory to search in (default: external-sources/ogs).

    Returns:
        Path to the best JSONL file found, or None.
    """
    if search_dir is None:
        from tools.ogs.config import DEFAULT_OUTPUT_DIR, get_project_root
        search_dir = get_project_root() / DEFAULT_OUTPUT_DIR

    if not search_dir.exists():
        return None

    # Prefer sorted files
    sorted_files = sorted(
        search_dir.glob("*-collections-sorted.jsonl"),
        reverse=True,
    )
    if sorted_files:
        return sorted_files[0]

    # Fall back to unsorted
    unsorted_files = sorted(
        search_dir.glob("*-collections.jsonl"),
        reverse=True,
    )
    if unsorted_files:
        return unsorted_files[0]

    return None
