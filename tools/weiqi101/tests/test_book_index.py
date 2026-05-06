"""Tests for book puzzle entries in sgf-index.txt.

Verifies that:
- add_book_to_index writes the correct colon-pid format
- load_puzzle_ids round-trips book entries alongside batch/qday entries
- sort_and_rewrite handles mixed entry formats correctly
"""

from __future__ import annotations

import json
from pathlib import Path

from tools.core.index import extract_ids, sort_and_rewrite
from tools.weiqi101.index import (
    INDEX_FILENAME,
    add_book_to_index,
    add_to_index,
    load_puzzle_ids,
)


class TestAddBookToIndex:
    """add_book_to_index appends the correct format."""

    def test_appends_colon_pid_format(self, tmp_path: Path):
        add_book_to_index(tmp_path, "197-life-and-death", "ch01_005_ld_9538.sgf", 9538)

        index_path = tmp_path / INDEX_FILENAME
        lines = index_path.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 1
        assert lines[0] == "books/197-life-and-death/sgf/ch01_005_ld_9538.sgf:9538"

    def test_multiple_entries(self, tmp_path: Path):
        add_book_to_index(tmp_path, "197-ld", "ch01_001_ld_100.sgf", 100)
        add_book_to_index(tmp_path, "197-ld", "ch01_002_ld_200.sgf", 200)

        index_path = tmp_path / INDEX_FILENAME
        lines = index_path.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 2


class TestLoadPuzzleIdsWithBooks:
    """load_puzzle_ids handles book entries from sgf-index.txt."""

    def test_book_entry_parsed_from_index(self, tmp_path: Path):
        """Book entries in sgf-index.txt are parsed into the known_ids set."""
        index_path = tmp_path / INDEX_FILENAME
        index_path.write_text(
            "books/197-ld/sgf/ch01_005_ld_9538.sgf:9538\n",
            encoding="utf-8",
        )
        ids = load_puzzle_ids(tmp_path)
        assert 9538 in ids

    def test_mixed_formats(self, tmp_path: Path):
        """Batch, qday, and book entries all parse correctly."""
        index_path = tmp_path / INDEX_FILENAME
        index_path.write_text(
            "batch-001/78000.sgf\n"
            "qday/2026/04/20260414-3-354411.sgf:354411\n"
            "books/197-ld/sgf/ch01_005_ld_9538.sgf:9538\n",
            encoding="utf-8",
        )
        ids = load_puzzle_ids(tmp_path)
        assert ids == {78000, 354411, 9538}

    def test_book_json_fallback_still_works(self, tmp_path: Path):
        """Old books without index entries are still loaded from book.json."""
        # Create a book.json with captured positions (no sgf-index.txt entry)
        books_dir = tmp_path / "books" / "100-old-book"
        books_dir.mkdir(parents=True)
        book_data = {
            "schema_version": 4,
            "book_id": 100,
            "chapters": [],
            "positions": [
                {"pos": 1, "pid": 5555, "status": "captured", "file": "x.sgf"},
                {"pos": 2, "pid": 6666, "status": "pending"},
            ],
        }
        (books_dir / "book.json").write_text(
            json.dumps(book_data), encoding="utf-8",
        )
        ids = load_puzzle_ids(tmp_path)
        assert 5555 in ids
        assert 6666 not in ids  # pending is not loaded

    def test_dedup_across_sources(self, tmp_path: Path):
        """Same pid in both sgf-index.txt and book.json produces no error."""
        index_path = tmp_path / INDEX_FILENAME
        index_path.write_text(
            "books/100-book/sgf/ch01_001_x_5555.sgf:5555\n",
            encoding="utf-8",
        )
        books_dir = tmp_path / "books" / "100-book"
        books_dir.mkdir(parents=True)
        book_data = {
            "schema_version": 4,
            "book_id": 100,
            "chapters": [],
            "positions": [
                {"pos": 1, "pid": 5555, "status": "captured", "file": "x.sgf"},
            ],
        }
        (books_dir / "book.json").write_text(
            json.dumps(book_data), encoding="utf-8",
        )
        ids = load_puzzle_ids(tmp_path)
        assert 5555 in ids
        assert len([x for x in ids if x == 5555]) == 1  # set dedup


class TestSortAndRewriteWithBooks:
    """sort_and_rewrite handles colon-pid entries correctly."""

    def test_sorts_by_pid(self, tmp_path: Path):
        index_path = tmp_path / INDEX_FILENAME
        index_path.write_text(
            "books/197-ld/sgf/ch01_005_ld_9538.sgf:9538\n"
            "batch-001/100.sgf\n"
            "qday/2026/04/20260414-3-354411.sgf:354411\n"
            "batch-001/50.sgf\n",
            encoding="utf-8",
        )
        count = sort_and_rewrite(index_path)
        assert count == 4

        lines = index_path.read_text(encoding="utf-8").strip().splitlines()
        # Should be sorted by numeric pid: 50, 100, 9538, 354411
        assert "50.sgf" in lines[0]
        assert "100.sgf" in lines[1]
        assert "9538" in lines[2]
        assert "354411" in lines[3]

    def test_no_entries_dropped(self, tmp_path: Path):
        """Book entries are not dropped or corrupted by sort_and_rewrite."""
        index_path = tmp_path / INDEX_FILENAME
        original = "books/197-ld/sgf/ch01_005_ld_9538.sgf:9538\n"
        index_path.write_text(original, encoding="utf-8")
        sort_and_rewrite(index_path)
        lines = index_path.read_text(encoding="utf-8").strip().splitlines()
        assert lines[0] == "books/197-ld/sgf/ch01_005_ld_9538.sgf:9538"


class TestExtractIdsWithBooks:
    """extract_ids handles colon-pid entries from book/qday formats."""

    def test_colon_pid_entry(self):
        entries = {"books/197-ld/sgf/ch01_005_ld_9538.sgf:9538"}
        ids = extract_ids(entries)
        assert ids == {9538}

    def test_mixed_entries(self):
        entries = {
            "batch-001/78000.sgf",
            "qday/2026/04/20260414-3-354411.sgf:354411",
            "books/197-ld/sgf/ch01_005_ld_9538.sgf:9538",
        }
        ids = extract_ids(entries)
        assert ids == {78000, 354411, 9538}
