"""
Tests for tools.ogs.collection_index module.

Tests the reverse index from puzzle IDs to OGS collection names.
"""

import json
from pathlib import Path

import pytest

from tools.ogs.collection_index import CollectionIndex, find_sorted_jsonl

# ==============================
# Fixtures
# ==============================

def _make_metadata() -> dict:
    """Minimal metadata line for JSONL."""
    return {"type": "metadata", "total_collections": 0}


def _make_collection(
    coll_id: int, name: str, puzzles: list[int],
) -> dict:
    """Minimal collection record for JSONL."""
    return {
        "type": "collection",
        "id": coll_id,
        "name": name,
        "puzzles": puzzles,
    }


def _write_jsonl(path: Path, records: list[dict]) -> None:
    """Write records as JSONL lines."""
    lines = [json.dumps(r) for r in records]
    path.write_text("\n".join(lines), encoding="utf-8")


@pytest.fixture
def sample_jsonl(tmp_path: Path) -> Path:
    """JSONL with two collections sharing some puzzles."""
    path = tmp_path / "collections-sorted.jsonl"
    _write_jsonl(path, [
        _make_metadata(),
        _make_collection(100, "Cho Chikun Elementary", [1, 2, 3]),
        _make_collection(200, "Tesuji Training", [2, 4, 5]),
    ])
    return path


# ==============================
# Build & Lookup Tests
# ==============================

class TestCollectionIndex:
    def test_build_from_jsonl(self, sample_jsonl: Path) -> None:
        """Index loads and reports correct counts."""
        index = CollectionIndex.from_jsonl(sample_jsonl)
        assert index.total_collections == 2
        assert index.total_puzzle_ids == 5  # {1, 2, 3, 4, 5}

    def test_puzzle_in_single_collection(self, sample_jsonl: Path) -> None:
        """Puzzle 1 is only in Cho Chikun Elementary."""
        index = CollectionIndex.from_jsonl(sample_jsonl)
        result = index.get_collections(1)
        assert len(result) == 1
        assert result[0] == ("Cho Chikun Elementary", 100)

    def test_puzzle_in_multiple_collections(self, sample_jsonl: Path) -> None:
        """Puzzle 2 appears in both collections."""
        index = CollectionIndex.from_jsonl(sample_jsonl)
        result = index.get_collections(2)
        assert len(result) == 2
        names = {name for name, _ in result}
        assert names == {"Cho Chikun Elementary", "Tesuji Training"}

    def test_puzzle_not_found(self, sample_jsonl: Path) -> None:
        """Unknown puzzle ID returns empty list."""
        index = CollectionIndex.from_jsonl(sample_jsonl)
        assert index.get_collections(9999) == []

    def test_empty_index(self) -> None:
        """Default-constructed index is empty."""
        index = CollectionIndex()
        assert index.total_collections == 0
        assert index.total_puzzle_ids == 0
        assert index.get_collections(1) == []


# ==============================
# Edge Cases
# ==============================

class TestEdgeCases:
    def test_missing_file(self, tmp_path: Path) -> None:
        """Non-existent JSONL returns empty index."""
        index = CollectionIndex.from_jsonl(tmp_path / "no-such-file.jsonl")
        assert index.total_collections == 0
        assert index.total_puzzle_ids == 0

    def test_empty_file(self, tmp_path: Path) -> None:
        """Empty JSONL returns empty index."""
        path = tmp_path / "empty.jsonl"
        path.write_text("", encoding="utf-8")
        index = CollectionIndex.from_jsonl(path)
        assert index.total_collections == 0

    def test_metadata_line_skipped(self, tmp_path: Path) -> None:
        """Metadata record (type != collection) is not indexed."""
        path = tmp_path / "test.jsonl"
        _write_jsonl(path, [
            _make_metadata(),
            _make_collection(1, "Test", [10, 20]),
        ])
        index = CollectionIndex.from_jsonl(path)
        assert index.total_collections == 1
        assert index.total_puzzle_ids == 2

    def test_collection_with_empty_puzzles(self, tmp_path: Path) -> None:
        """Collection with no puzzles is counted but adds no puzzle IDs."""
        path = tmp_path / "test.jsonl"
        _write_jsonl(path, [
            _make_metadata(),
            _make_collection(1, "Empty Collection", []),
        ])
        index = CollectionIndex.from_jsonl(path)
        # Empty puzzles array: collection not counted (per implementation)
        assert index.total_collections == 0
        assert index.total_puzzle_ids == 0

    def test_malformed_json_line_skipped(self, tmp_path: Path) -> None:
        """Malformed JSON line is skipped gracefully."""
        path = tmp_path / "test.jsonl"
        lines = [
            json.dumps(_make_metadata()),
            "not valid json {{{",
            json.dumps(_make_collection(1, "Good", [10])),
        ]
        path.write_text("\n".join(lines), encoding="utf-8")
        index = CollectionIndex.from_jsonl(path)
        assert index.total_collections == 1
        assert index.total_puzzle_ids == 1


# ==============================
# find_sorted_jsonl Tests
# ==============================

class TestFindSortedJsonl:
    def test_prefers_sorted_over_unsorted(self, tmp_path: Path) -> None:
        """Sorted JSONL is preferred over unsorted."""
        (tmp_path / "20260211-collections.jsonl").write_text("{}", encoding="utf-8")
        (tmp_path / "20260211-collections-sorted.jsonl").write_text("{}", encoding="utf-8")
        result = find_sorted_jsonl(tmp_path)
        assert result is not None
        assert "sorted" in result.name

    def test_falls_back_to_unsorted(self, tmp_path: Path) -> None:
        """Falls back to unsorted if no sorted file exists."""
        (tmp_path / "20260211-collections.jsonl").write_text("{}", encoding="utf-8")
        result = find_sorted_jsonl(tmp_path)
        assert result is not None
        assert result.name == "20260211-collections.jsonl"

    def test_returns_none_when_no_files(self, tmp_path: Path) -> None:
        """Returns None when no JSONL files found."""
        result = find_sorted_jsonl(tmp_path)
        assert result is None

    def test_returns_none_when_dir_missing(self, tmp_path: Path) -> None:
        """Returns None when search directory doesn't exist."""
        result = find_sorted_jsonl(tmp_path / "no-such-dir")
        assert result is None
