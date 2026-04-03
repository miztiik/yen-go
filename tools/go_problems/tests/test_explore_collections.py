"""
Tests for GoProblems collection discovery (explore_collections).

Tests accumulation logic, API discovery, puzzle enrichment, checkpoint
save/load, puzzle ID parsing, and JSONL output generation.
"""

import json
from pathlib import Path
from typing import Any

import pytest

from tools.go_problems.explore_collections import (
    DiscoveredCollection,
    _clear_explore_checkpoint,
    _load_explore_checkpoint,
    _save_explore_checkpoint,
    accumulate_puzzle,
    discover_collections_via_api,
    enrich_from_puzzles,
    load_puzzle_ids_from_file,
    write_collections_jsonl,
)

# ==============================
# Mock Client
# ==============================

class MockGoProblemsClient:
    """Lightweight mock for GoProblemsClient used in API discovery tests."""

    def __init__(
        self,
        collections_pages: list[dict[str, Any]] | None = None,
        puzzles: dict[int, dict[str, Any]] | None = None,
    ) -> None:
        self.collections_pages = collections_pages or []
        self.puzzles = puzzles or {}
        self._collections_call_count = 0
        self._puzzle_call_count = 0

    def get_collections(self, offset: int = 0, limit: int = 100) -> dict[str, Any]:
        if self._collections_call_count < len(self.collections_pages):
            page = self.collections_pages[self._collections_call_count]
            self._collections_call_count += 1
            return page
        return {"entries": [], "totalRecords": 0}

    def get_puzzle(self, puzzle_id: int) -> dict[str, Any] | None:
        self._puzzle_call_count += 1
        return self.puzzles.get(puzzle_id)

    def __enter__(self) -> "MockGoProblemsClient":
        return self

    def __exit__(self, *args: Any) -> None:
        pass


# ==============================
# DiscoveredCollection Tests
# ==============================

class TestDiscoveredCollection:
    def test_to_jsonl_record_basic(self) -> None:
        dc = DiscoveredCollection(
            id=35, name="Symmetrical",
            puzzle_count=3, puzzle_ids=[1, 2, 3],
            total_stars=12.0, total_votes=30,
            rated_puzzle_count=3, canon_count=2,
            genre_counts={"life and death": 2, "tesuji": 1},
            rank_sum=45, ranked_puzzle_count=3,
        )
        record = dc.to_jsonl_record()
        assert record["type"] == "collection"
        assert record["id"] == 35
        assert record["name"] == "Symmetrical"
        assert record["stats"]["puzzle_count"] == 3
        assert record["stats"]["avg_stars"] == 4.0
        assert record["stats"]["avg_votes"] == 10.0
        assert record["stats"]["canon_count"] == 2
        assert record["stats"]["canon_ratio"] == pytest.approx(0.6667, abs=0.001)
        assert record["stats"]["avg_rank"] == 15.0

    def test_to_jsonl_record_no_ratings(self) -> None:
        dc = DiscoveredCollection(id=1, name="Empty Stats", puzzle_count=5)
        record = dc.to_jsonl_record()
        assert record["stats"]["avg_stars"] == 0.0
        assert record["stats"]["avg_votes"] == 0.0
        assert record["stats"]["canon_ratio"] == 0.0

    def test_to_jsonl_record_zero_puzzles(self) -> None:
        dc = DiscoveredCollection(id=2, name="No Puzzles")
        record = dc.to_jsonl_record()
        assert record["stats"]["puzzle_count"] == 0
        assert record["stats"]["canon_ratio"] == 0.0

    def test_to_jsonl_record_includes_api_fields(self) -> None:
        dc = DiscoveredCollection(
            id=18, name="Semeai / Capturing Race",
            puzzle_count=2546,
            group="Style", description="Semeai problems",
            author_name="admin", enriched=True,
        )
        record = dc.to_jsonl_record()
        assert record["group"] == "Style"
        assert record["description"] == "Semeai problems"
        assert record["author"] == "admin"
        assert record["enriched"] is True

    def test_to_jsonl_record_unenriched_defaults(self) -> None:
        dc = DiscoveredCollection(id=5, name="API Only", puzzle_count=100)
        record = dc.to_jsonl_record()
        assert record["group"] == ""
        assert record["enriched"] is False
        assert record["author"] == ""


# ==============================
# accumulate_puzzle Tests
# ==============================

class TestAccumulatePuzzle:
    def test_basic_accumulation(self) -> None:
        cmap: dict[int, DiscoveredCollection] = {}
        puzzle = {
            "id": 42,
            "collections": [
                {"id": 1, "name": "Basic Set"},
                {"id": 2, "name": "Advanced Set"},
            ],
            "rating": {"stars": 4.0, "votes": 10},
            "isCanon": True,
            "genre": "life and death",
            "rank": {"value": 15, "unit": "kyu"},
        }
        accumulate_puzzle(cmap, puzzle)

        assert len(cmap) == 2
        assert cmap[1].puzzle_count == 1
        assert cmap[1].puzzle_ids == [42]
        assert cmap[1].total_stars == 4.0
        assert cmap[1].total_votes == 10
        assert cmap[1].rated_puzzle_count == 1
        assert cmap[1].canon_count == 1
        assert cmap[1].genre_counts == {"life and death": 1}
        assert cmap[1].rank_sum == 15
        assert cmap[1].ranked_puzzle_count == 1

    def test_accumulates_across_puzzles(self) -> None:
        cmap: dict[int, DiscoveredCollection] = {}
        puzzle1 = {
            "id": 1,
            "collections": [{"id": 5, "name": "Shared"}],
            "rating": {"stars": 3.0, "votes": 5},
            "isCanon": False,
            "genre": "tesuji",
        }
        puzzle2 = {
            "id": 2,
            "collections": [{"id": 5, "name": "Shared"}],
            "rating": {"stars": 5.0, "votes": 20},
            "isCanon": True,
            "genre": "tesuji",
        }
        accumulate_puzzle(cmap, puzzle1)
        accumulate_puzzle(cmap, puzzle2)

        dc = cmap[5]
        assert dc.puzzle_count == 2
        assert dc.puzzle_ids == [1, 2]
        assert dc.total_stars == 8.0
        assert dc.total_votes == 25
        assert dc.rated_puzzle_count == 2
        assert dc.canon_count == 1
        assert dc.genre_counts == {"tesuji": 2}

    def test_no_collections_array(self) -> None:
        cmap: dict[int, DiscoveredCollection] = {}
        accumulate_puzzle(cmap, {"id": 1})
        assert len(cmap) == 0

    def test_none_collections(self) -> None:
        cmap: dict[int, DiscoveredCollection] = {}
        accumulate_puzzle(cmap, {"id": 1, "collections": None})
        assert len(cmap) == 0

    def test_empty_collections(self) -> None:
        cmap: dict[int, DiscoveredCollection] = {}
        accumulate_puzzle(cmap, {"id": 1, "collections": []})
        assert len(cmap) == 0

    def test_missing_rating(self) -> None:
        cmap: dict[int, DiscoveredCollection] = {}
        puzzle = {
            "id": 1,
            "collections": [{"id": 5, "name": "Set"}],
        }
        accumulate_puzzle(cmap, puzzle)
        assert cmap[5].rated_puzzle_count == 0
        assert cmap[5].total_stars == 0.0

    def test_missing_rank(self) -> None:
        cmap: dict[int, DiscoveredCollection] = {}
        puzzle = {
            "id": 1,
            "collections": [{"id": 5, "name": "Set"}],
            "rating": {"stars": 3.0, "votes": 5},
        }
        accumulate_puzzle(cmap, puzzle)
        assert cmap[5].ranked_puzzle_count == 0

    def test_no_puzzle_id_ignored(self) -> None:
        cmap: dict[int, DiscoveredCollection] = {}
        accumulate_puzzle(cmap, {"collections": [{"id": 1, "name": "X"}]})
        assert len(cmap) == 0


# ==============================
# Checkpoint Tests
# ==============================

class TestCheckpoint:
    def test_save_and_load(self, tmp_path: Path) -> None:
        cmap = {
            1: DiscoveredCollection(
                id=1, name="Test",
                puzzle_count=5, puzzle_ids=[10, 20, 30, 40, 50],
                total_stars=20.0, total_votes=100,
                rated_puzzle_count=5, canon_count=3,
            ),
        }
        _save_explore_checkpoint(tmp_path, 42, cmap, "test", 50)

        result = _load_explore_checkpoint(tmp_path)
        assert result is not None
        last_idx, loaded_map, puzzles_scanned = result
        assert last_idx == 42
        assert puzzles_scanned == 50
        assert len(loaded_map) == 1
        assert loaded_map[1].name == "Test"
        assert loaded_map[1].puzzle_count == 5
        assert loaded_map[1].puzzle_ids == [10, 20, 30, 40, 50]

    def test_load_nonexistent(self, tmp_path: Path) -> None:
        result = _load_explore_checkpoint(tmp_path)
        assert result is None

    def test_clear(self, tmp_path: Path) -> None:
        cmap = {1: DiscoveredCollection(id=1, name="X")}
        _save_explore_checkpoint(tmp_path, 0, cmap, "test", 1)
        _clear_explore_checkpoint(tmp_path)
        assert _load_explore_checkpoint(tmp_path) is None


# ==============================
# JSONL Writer Tests
# ==============================

class TestWriteCollectionsJsonl:
    def test_writes_metadata_and_collections(self, tmp_path: Path) -> None:
        cmap = {
            1: DiscoveredCollection(
                id=1, name="Alpha", puzzle_count=10,
                puzzle_ids=list(range(10)),
            ),
            2: DiscoveredCollection(
                id=2, name="Beta", puzzle_count=5,
                puzzle_ids=list(range(5)),
            ),
        }
        output = tmp_path / "test.jsonl"
        write_collections_jsonl(output, cmap, puzzles_scanned=100, puzzle_ids_source="test")

        lines = output.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 3  # 1 metadata + 2 collections

        metadata = json.loads(lines[0])
        assert metadata["type"] == "metadata"
        assert metadata["source"] == "goproblems.com"
        assert metadata["total_collections"] == 2
        assert metadata["puzzles_scanned"] == 100

        # Sorted by puzzle_count descending
        coll1 = json.loads(lines[1])
        coll2 = json.loads(lines[2])
        assert coll1["puzzle_count"] >= coll2["puzzle_count"]

    def test_empty_map(self, tmp_path: Path) -> None:
        output = tmp_path / "empty.jsonl"
        write_collections_jsonl(output, {}, puzzles_scanned=0, puzzle_ids_source="test")

        lines = output.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 1  # Just metadata
        metadata = json.loads(lines[0])
        assert metadata["total_collections"] == 0

    def test_discovery_method_in_metadata(self, tmp_path: Path) -> None:
        output = tmp_path / "api.jsonl"
        write_collections_jsonl(
            output, {}, puzzles_scanned=0,
            puzzle_ids_source="collections_api",
            discovery_method="api",
        )
        metadata = json.loads(
            output.read_text(encoding="utf-8").splitlines()[0]
        )
        assert metadata["discovery_method"] == "api"

    def test_hybrid_discovery_method(self, tmp_path: Path) -> None:
        cmap = {
            1: DiscoveredCollection(
                id=1, name="Enriched", puzzle_count=10, enriched=True,
            ),
        }
        output = tmp_path / "hybrid.jsonl"
        write_collections_jsonl(
            output, cmap, puzzles_scanned=50,
            puzzle_ids_source="file:sgf-index.txt",
            discovery_method="hybrid",
        )
        metadata = json.loads(
            output.read_text(encoding="utf-8").splitlines()[0]
        )
        assert metadata["discovery_method"] == "hybrid"
        assert metadata["enriched_collections"] == 1


# ==============================
# Puzzle ID Loading Tests
# ==============================

class TestLoadPuzzleIdsFromFile:
    def test_plain_ids(self, tmp_path: Path) -> None:
        f = tmp_path / "ids.txt"
        f.write_text("42\n100\n250\n", encoding="utf-8")
        ids = load_puzzle_ids_from_file(f)
        assert ids == [42, 100, 250]

    def test_sgf_index_format(self, tmp_path: Path) -> None:
        f = tmp_path / "sgf-index.txt"
        f.write_text(
            "batch-0001/12345.sgf\nbatch-0001/67890.sgf\n", encoding="utf-8"
        )
        ids = load_puzzle_ids_from_file(f)
        assert ids == [12345, 67890]

    def test_skips_comments_and_blanks(self, tmp_path: Path) -> None:
        f = tmp_path / "ids.txt"
        f.write_text("# comment\n\n42\n\n100\n", encoding="utf-8")
        ids = load_puzzle_ids_from_file(f)
        assert ids == [42, 100]

    def test_deduplicates(self, tmp_path: Path) -> None:
        f = tmp_path / "ids.txt"
        f.write_text("42\n42\n42\n", encoding="utf-8")
        ids = load_puzzle_ids_from_file(f)
        assert ids == [42]

    def test_invalid_lines_skipped(self, tmp_path: Path) -> None:
        f = tmp_path / "ids.txt"
        f.write_text("42\nnot_a_number\n100\n", encoding="utf-8")
        ids = load_puzzle_ids_from_file(f)
        assert ids == [42, 100]


# ==============================
# API Discovery Tests
# ==============================

class TestDiscoverCollectionsViaApi:
    def test_basic_discovery(self) -> None:
        """API discovery populates new fields from collections endpoint."""
        client = MockGoProblemsClient(collections_pages=[
            {
                "entries": [
                    {
                        "id": 18,
                        "name": "Semeai / Capturing Race",
                        "description": "Semeai problems",
                        "group": "Style",
                        "numberOfProblems": 2546,
                        "author": {"id": 1, "name": "admin"},
                        "createdAt": "2003-05-24T09:11:07+00:00",
                    },
                    {
                        "id": 42,
                        "name": "User Collection",
                        "description": "",
                        "group": "Collection",
                        "numberOfProblems": 50,
                        "author": {"id": 5, "name": "player1"},
                        "createdAt": "2020-01-01T00:00:00+00:00",
                    },
                ],
                "totalRecords": 2,
            },
        ])

        result = discover_collections_via_api(client, delay=0)

        assert len(result) == 2
        assert 18 in result
        assert 42 in result

        dc = result[18]
        assert dc.name == "Semeai / Capturing Race"
        assert dc.group == "Style"
        assert dc.description == "Semeai problems"
        assert dc.author_name == "admin"
        assert dc.author_id == 1
        assert dc.puzzle_count == 2546
        assert dc.enriched is False
        assert dc.created_at == "2003-05-24T09:11:07+00:00"

    def test_pagination(self) -> None:
        """API discovery handles multiple pages."""
        # totalRecords=200 ensures offset < totalRecords after first page
        # (limit=100, so offset goes 0 -> 100, still < 200)
        client = MockGoProblemsClient(collections_pages=[
            {
                "entries": [
                    {"id": 1, "name": "Page1", "numberOfProblems": 10, "group": "Style"},
                ],
                "totalRecords": 200,
            },
            {
                "entries": [
                    {"id": 2, "name": "Page2", "numberOfProblems": 20, "group": "Collection"},
                ],
                "totalRecords": 200,
            },
        ])

        result = discover_collections_via_api(client, delay=0)
        assert len(result) == 2
        assert result[1].name == "Page1"
        assert result[2].name == "Page2"

    def test_empty_response(self) -> None:
        """Empty API response returns empty map."""
        client = MockGoProblemsClient(collections_pages=[
            {"entries": [], "totalRecords": 0},
        ])
        result = discover_collections_via_api(client, delay=0)
        assert len(result) == 0

    def test_missing_author(self) -> None:
        """Entry with missing author field handled gracefully."""
        client = MockGoProblemsClient(collections_pages=[
            {
                "entries": [
                    {"id": 99, "name": "No Author", "numberOfProblems": 5},
                ],
                "totalRecords": 1,
            },
        ])
        result = discover_collections_via_api(client, delay=0)
        assert result[99].author_name == ""
        assert result[99].author_id == 0

    def test_missing_collection_id_skipped(self) -> None:
        """Entry without id is skipped."""
        client = MockGoProblemsClient(collections_pages=[
            {
                "entries": [
                    {"name": "No ID", "numberOfProblems": 5},
                    {"id": 1, "name": "Has ID", "numberOfProblems": 10},
                ],
                "totalRecords": 2,
            },
        ])
        result = discover_collections_via_api(client, delay=0)
        assert len(result) == 1
        assert 1 in result


# ==============================
# Enrichment Tests
# ==============================

class TestEnrichFromPuzzles:
    def test_enrichment_adds_stats(self) -> None:
        """Enrichment adds per-puzzle stats to API-discovered collections."""
        collections_map = {
            5: DiscoveredCollection(
                id=5, name="Test Collection",
                puzzle_count=100, group="Style",
                enriched=False,
            ),
        }
        client = MockGoProblemsClient(puzzles={
            42: {
                "id": 42,
                "collections": [{"id": 5, "name": "Test Collection"}],
                "rating": {"stars": 4.5, "votes": 20},
                "isCanon": True,
                "genre": "life and death",
                "rank": {"value": 12},
            },
            43: {
                "id": 43,
                "collections": [{"id": 5, "name": "Test Collection"}],
                "rating": {"stars": 3.5, "votes": 10},
                "isCanon": False,
                "genre": "tesuji",
            },
        })

        scanned = enrich_from_puzzles(
            collections_map, client, [42, 43], delay=0,
        )

        assert scanned == 2
        dc = collections_map[5]
        assert dc.enriched is True
        assert dc.puzzle_count == 100  # API count preserved
        assert dc.rated_puzzle_count == 2
        assert dc.total_stars == 8.0
        assert dc.total_votes == 30
        assert dc.canon_count == 1
        assert dc.genre_counts == {"life and death": 1, "tesuji": 1}

    def test_api_puzzle_count_preserved(self) -> None:
        """API numberOfProblems is restored as puzzle_count after enrichment."""
        collections_map = {
            10: DiscoveredCollection(
                id=10, name="Big Collection",
                puzzle_count=500,
                enriched=False,
            ),
        }
        client = MockGoProblemsClient(puzzles={
            1: {
                "id": 1,
                "collections": [{"id": 10, "name": "Big Collection"}],
                "rating": {"stars": 4.0, "votes": 5},
            },
        })

        enrich_from_puzzles(collections_map, client, [1], delay=0)

        # puzzle_count should be API's 500, not enrichment's 1
        assert collections_map[10].puzzle_count == 500

    def test_unenriched_collection_stays_false(self) -> None:
        """Collections not referenced by any scanned puzzle stay enriched=False."""
        collections_map = {
            1: DiscoveredCollection(id=1, name="Referenced", puzzle_count=50),
            2: DiscoveredCollection(id=2, name="Not Referenced", puzzle_count=30),
        }
        client = MockGoProblemsClient(puzzles={
            99: {
                "id": 99,
                "collections": [{"id": 1, "name": "Referenced"}],
                "rating": {"stars": 4.0, "votes": 10},
            },
        })

        enrich_from_puzzles(collections_map, client, [99], delay=0)

        assert collections_map[1].enriched is True
        assert collections_map[2].enriched is False

    def test_sample_limits_puzzles(self) -> None:
        """--enrich-sample limits the number of puzzles scanned."""
        collections_map = {
            1: DiscoveredCollection(id=1, name="Test", puzzle_count=100),
        }
        client = MockGoProblemsClient(puzzles={
            i: {
                "id": i,
                "collections": [{"id": 1, "name": "Test"}],
                "rating": {"stars": 4.0, "votes": 5},
            }
            for i in range(1, 11)
        })

        scanned = enrich_from_puzzles(
            collections_map, client, list(range(1, 11)),
            sample=3, delay=0,
        )

        assert scanned == 3
        assert client._puzzle_call_count == 3

    def test_missing_puzzle_skipped(self) -> None:
        """Puzzles returning None (404) don't count as scanned."""
        collections_map = {
            1: DiscoveredCollection(id=1, name="Test", puzzle_count=50),
        }
        client = MockGoProblemsClient(puzzles={})  # All puzzles return None

        scanned = enrich_from_puzzles(
            collections_map, client, [1, 2, 3], delay=0,
        )

        assert scanned == 0
        assert collections_map[1].enriched is False
