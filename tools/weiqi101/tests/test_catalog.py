"""Tests for tools.weiqi101.catalog — book catalog join."""

from __future__ import annotations

import json
from pathlib import Path

from tools.weiqi101 import catalog


def _write_jsonl(path: Path, records: list[dict]) -> None:
    path.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in records) + "\n",
        encoding="utf-8",
    )


def _write_book_ids(dir: Path, books: list[dict]) -> None:
    _write_jsonl(dir / catalog.BOOK_IDS_FILE, books)


def _write_reviews(dir: Path, reviews: list[dict]) -> None:
    _write_jsonl(dir / catalog.REVIEWS_FILE, reviews)


def _write_discovery(dir: Path, books: list[dict]) -> None:
    (dir / catalog.DISCOVERY_CATALOG_FILE).write_text(
        json.dumps({"books": books}, ensure_ascii=False), encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# consensus_tier
# ---------------------------------------------------------------------------


class TestConsensusTier:
    def test_average_floors_to_better_tier(self):
        # tier-1(1) + tier-3(3) avg=2 -> tier-2
        assert catalog.consensus_tier("tier-1", "tier-3") == "tier-2"

    def test_both_same_tier(self):
        assert catalog.consensus_tier("tier-1", "tier-1") == "tier-1"
        assert catalog.consensus_tier("skip", "skip") == "skip"

    def test_falls_back_to_go_advisor_when_modern_missing(self):
        assert catalog.consensus_tier("tier-1", None) == "tier-1"
        assert catalog.consensus_tier("tier-3", None) == "tier-3"

    def test_falls_back_to_modern_when_go_advisor_missing(self):
        assert catalog.consensus_tier(None, "tier-2") == "tier-2"

    def test_unrated_when_both_missing(self):
        assert catalog.consensus_tier(None, None) == "unrated"

    def test_skip_floors_with_tier1_to_tier2(self):
        # tier-1(1) + skip(4) avg=2.5 -> int floor = 2 -> tier-2
        # Matches legacy _build_priority_report.consensus_tier behavior.
        assert catalog.consensus_tier("tier-1", "skip") == "tier-2"


# ---------------------------------------------------------------------------
# rebuild_books_catalog
# ---------------------------------------------------------------------------


class TestRebuild:
    def test_unrated_when_review_missing(self, tmp_path: Path):
        _write_book_ids(tmp_path, [{"book_id": 1, "book_name": "X", "puzzle_count": 10}])
        _write_reviews(tmp_path, [])
        n = catalog.rebuild_books_catalog(tmp_path)
        assert n == 1
        entries = catalog.load_catalog(tmp_path)
        assert entries[0]["consensus_tier"] == "unrated"
        assert entries[0]["go_advisor_tier"] is None

    def test_review_stale_when_drift_exceeds_threshold(self, tmp_path: Path):
        # 100 -> 120 = 20% drift -> stale
        _write_book_ids(
            tmp_path,
            [{"book_id": 1, "book_name": "X",
              "chapters": [{"puzzle_ids": list(range(120))}]}],
        )
        _write_reviews(
            tmp_path,
            [{"book_id": 1, "puzzle_count_at_review": 100,
              "reviews": {"go_advisor": {"tier": "tier-1", "type": "ref", "note": "n"}}}],
        )
        catalog.rebuild_books_catalog(tmp_path)
        entries = catalog.load_catalog(tmp_path)
        assert entries[0]["review_stale"] is True
        assert entries[0]["puzzle_count"] == 120

    def test_review_not_stale_within_threshold(self, tmp_path: Path):
        # 100 -> 105 = 5% drift -> NOT stale
        _write_book_ids(
            tmp_path,
            [{"book_id": 1, "book_name": "X",
              "chapters": [{"puzzle_ids": list(range(105))}]}],
        )
        _write_reviews(
            tmp_path,
            [{"book_id": 1, "puzzle_count_at_review": 100,
              "reviews": {"go_advisor": {"tier": "tier-1", "type": "ref", "note": "n"}}}],
        )
        catalog.rebuild_books_catalog(tmp_path)
        entries = catalog.load_catalog(tmp_path)
        assert entries[0]["review_stale"] is False

    def test_idempotent_rebuild(self, tmp_path: Path):
        _write_book_ids(
            tmp_path,
            [
                {"book_id": 2, "book_name": "B", "puzzle_count": 5},
                {"book_id": 1, "book_name": "A", "puzzle_count": 10},
            ],
        )
        _write_reviews(tmp_path, [])
        catalog.rebuild_books_catalog(tmp_path)
        first = (tmp_path / catalog.CATALOG_FILE).read_bytes()
        catalog.rebuild_books_catalog(tmp_path)
        second = (tmp_path / catalog.CATALOG_FILE).read_bytes()
        assert first == second

    def test_sort_order_unrated_after_tier3_before_skip(self, tmp_path: Path):
        _write_book_ids(
            tmp_path,
            [
                {"book_id": 1, "book_name": "A-skip", "puzzle_count": 1},
                {"book_id": 2, "book_name": "B-tier1", "puzzle_count": 1},
                {"book_id": 3, "book_name": "C-unrated", "puzzle_count": 1},
                {"book_id": 4, "book_name": "D-tier3", "puzzle_count": 1},
            ],
        )
        _write_reviews(
            tmp_path,
            [
                {"book_id": 1, "reviews": {
                    "go_advisor": {"tier": "skip", "type": "x", "note": "n"}}},
                {"book_id": 2, "reviews": {
                    "go_advisor": {"tier": "tier-1", "type": "x", "note": "n"}}},
                {"book_id": 4, "reviews": {
                    "go_advisor": {"tier": "tier-3", "type": "x", "note": "n"}}},
            ],
        )
        catalog.rebuild_books_catalog(tmp_path)
        entries = catalog.load_catalog(tmp_path)
        order = [e["consensus_tier"] for e in entries]
        assert order == ["tier-1", "tier-3", "unrated", "skip"]

    def test_discovery_metadata_merged(self, tmp_path: Path):
        _write_book_ids(tmp_path, [{"book_id": 1, "book_name": "X", "puzzle_count": 1}])
        _write_discovery(
            tmp_path,
            [{"book_id": 1, "difficulty": "5K", "sharer": "alice",
              "tags": ["tesuji"], "chapter_count": 3}],
        )
        _write_reviews(tmp_path, [])
        catalog.rebuild_books_catalog(tmp_path)
        entry = catalog.load_catalog(tmp_path)[0]
        assert entry["difficulty"] == "5K"
        assert entry["sharer"] == "alice"
        assert entry["tags"] == ["tesuji"]
        assert entry["chapter_count"] == 3

    def test_missing_inputs_yields_empty_catalog(self, tmp_path: Path):
        # No book-ids.jsonl, no reviews — should write zero entries, not crash
        n = catalog.rebuild_books_catalog(tmp_path)
        assert n == 0
        assert catalog.load_catalog(tmp_path) == []
