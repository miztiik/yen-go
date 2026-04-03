"""
Tests for GoProblems collection bootstrap (bootstrap_collections).

Tests entry generation, matching, skip/override logic, min-puzzle filtering,
slug collision resolution, API description usage, schema validation,
auto-merge, and end-to-end bootstrap pipeline.
"""

import json
import re
from pathlib import Path

import pytest

from tools.go_problems.bootstrap_collections import (
    _GP_NAME_OVERRIDES,
    _GP_SKIP_IDS,
    _GP_SLUG_OVERRIDES,
    _merge_into_collections_json,
    _resolve_slug_collision,
    _validate_entry,
    bootstrap_collections,
    generate_collection_entry,
)

# ==============================
# Helpers
# ==============================

def _make_metadata() -> dict:
    return {"type": "metadata", "total_collections": 0}


def _make_collection(
    coll_id: int,
    name: str,
    tier: str = "premier",
    puzzle_count: int = 50,
) -> dict:
    return {
        "type": "collection",
        "id": coll_id,
        "name": name,
        "quality_tier": tier,
        "puzzle_count": puzzle_count,
        "puzzles": [1, 2, 3],
        "stats": {
            "puzzle_count": puzzle_count,
            "avg_stars": 4.0,
            "avg_votes": 10.0,
            "rated_puzzle_count": 10,
            "canon_count": 5,
            "canon_ratio": 0.5,
            "avg_rank": 15.0,
            "ranked_puzzle_count": puzzle_count,
        },
        "genre_distribution": {"life and death": puzzle_count},
    }


def _write_jsonl(path: Path, records: list[dict]) -> None:
    lines = [json.dumps(r) for r in records]
    path.write_text("\n".join(lines), encoding="utf-8")


@pytest.fixture
def collections_json(tmp_path: Path) -> Path:
    """Minimal collections.json with one existing collection."""
    config = {
        "schema_version": "3.0",
        "_reference": "docs/concepts/collections.md",
        "collections": [
            {
                "slug": "tesuji-training",
                "name": "Tesuji Training",
                "tier": "editorial",
                "aliases": ["tactical problems"],
            },
        ],
    }
    path = tmp_path / "collections.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    return path


# ==============================
# generate_collection_entry Tests
# ==============================

class TestGenerateCollectionEntry:
    def test_basic_entry(self) -> None:
        record = {
            "name": "Life and Death [user123]",
            "stats": {"puzzle_count": 50},
            "quality_tier": "premier",
        }
        entry = generate_collection_entry(record)
        assert entry["slug"] == "life-and-death"
        assert entry["name"] == "Life and Death"
        assert entry["source"] == "goproblems"
        assert entry["ordering"] == "source"
        assert entry["tier"] == "premier"
        assert "Life and Death [user123]" in entry["aliases"]

    def test_curator_inferred(self) -> None:
        record = {
            "name": "Cho Chikun's Elementary Problems",
            "stats": {"puzzle_count": 100},
            "quality_tier": "premier",
        }
        entry = generate_collection_entry(record)
        assert entry["curator"] == "Cho Chikun"
        assert entry["type"] == "author"

    def test_description_includes_tier_and_count(self) -> None:
        record = {
            "name": "Test Collection",
            "stats": {"puzzle_count": 42},
            "quality_tier": "curated",
        }
        entry = generate_collection_entry(record)
        assert "curated" in entry["description"]
        assert "42 puzzles" in entry["description"]
        assert entry["tier"] == "curated"

    def test_tier_mapped_from_quality_tier(self) -> None:
        for gp_tier, expected in [
            ("premier", "premier"),
            ("curated", "curated"),
            ("community", "community"),
            ("unvetted", "community"),
        ]:
            record = {
                "name": f"Test {gp_tier}",
                "stats": {"puzzle_count": 50},
                "quality_tier": gp_tier,
            }
            entry = generate_collection_entry(record)
            assert entry["tier"] == expected, (
                f"GP tier '{gp_tier}' should map to '{expected}'"
            )

    def test_missing_quality_tier_defaults_to_community(self) -> None:
        record = {
            "name": "No Tier Collection",
            "stats": {"puzzle_count": 10},
        }
        entry = generate_collection_entry(record)
        assert entry["tier"] == "community"

    def test_source_is_goproblems(self) -> None:
        record = {
            "name": "Any Collection",
            "stats": {"puzzle_count": 10},
            "quality_tier": "premier",
        }
        entry = generate_collection_entry(record)
        assert entry["source"] == "goproblems"


# ==============================
# bootstrap_collections Tests
# ==============================

class TestBootstrapCollections:
    def test_matched_collection_not_bootstrapped(
        self, tmp_path: Path, collections_json: Path,
    ) -> None:
        """GP collection matching existing YenGo slug is reported as matched."""
        jsonl = tmp_path / "sorted.jsonl"
        _write_jsonl(jsonl, [
            _make_metadata(),
            _make_collection(1, "Tesuji Training Collection"),
        ])
        new_entries, matched, skipped = bootstrap_collections(jsonl, collections_json)
        assert len(matched) == 1
        assert matched[0][2] == "tesuji-training"
        assert len(new_entries) == 0

    def test_premier_unmatched_creates_entry(
        self, tmp_path: Path, collections_json: Path,
    ) -> None:
        """Premier-tier unmatched collection generates a new entry."""
        jsonl = tmp_path / "sorted.jsonl"
        _write_jsonl(jsonl, [
            _make_metadata(),
            _make_collection(1, "Completely New Collection", tier="premier"),
        ])
        new_entries, matched, skipped = bootstrap_collections(jsonl, collections_json)
        assert len(new_entries) == 1
        assert new_entries[0]["source"] == "goproblems"
        assert "Completely New Collection" in new_entries[0]["aliases"]

    def test_unvetted_tier_skipped(
        self, tmp_path: Path, collections_json: Path,
    ) -> None:
        """Unvetted-tier collection is skipped."""
        jsonl = tmp_path / "sorted.jsonl"
        _write_jsonl(jsonl, [
            _make_metadata(),
            _make_collection(1, "Low Quality Set", tier="unvetted"),
        ])
        new_entries, matched, skipped = bootstrap_collections(jsonl, collections_json)
        assert len(new_entries) == 0
        assert len(skipped) == 1
        assert skipped[0][3] == "tier_too_low"

    def test_community_tier_skipped(
        self, tmp_path: Path, collections_json: Path,
    ) -> None:
        """Community-tier collection is skipped by default."""
        jsonl = tmp_path / "sorted.jsonl"
        _write_jsonl(jsonl, [
            _make_metadata(),
            _make_collection(1, "Community Set", tier="community"),
        ])
        new_entries, matched, skipped = bootstrap_collections(jsonl, collections_json)
        assert len(new_entries) == 0
        assert len(skipped) == 1
        assert skipped[0][3] == "tier_too_low"

    def test_slug_collision_handled(
        self, tmp_path: Path, collections_json: Path,
    ) -> None:
        """Collection whose slug collides with existing is matched or resolved."""
        jsonl = tmp_path / "sorted.jsonl"
        _write_jsonl(jsonl, [
            _make_metadata(),
            _make_collection(1, "Tesuji Training", tier="premier"),
        ])
        new_entries, matched, skipped = bootstrap_collections(jsonl, collections_json)
        # Should match via CollectionMatcher, or resolve collision with -gp suffix
        assert len(matched) == 1 or (
            len(new_entries) == 1 and new_entries[0]["slug"].endswith("-gp")
        )

    def test_curated_tier_included(
        self, tmp_path: Path, collections_json: Path,
    ) -> None:
        """Curated-tier unmatched collection generates a new entry."""
        jsonl = tmp_path / "sorted.jsonl"
        _write_jsonl(jsonl, [
            _make_metadata(),
            _make_collection(1, "Brand New Curated Set", tier="curated"),
        ])
        new_entries, matched, skipped = bootstrap_collections(jsonl, collections_json)
        assert len(new_entries) == 1

    def test_multiple_entries_unique_slugs(
        self, tmp_path: Path, collections_json: Path,
    ) -> None:
        """Multiple new entries all have unique slugs."""
        jsonl = tmp_path / "sorted.jsonl"
        _write_jsonl(jsonl, [
            _make_metadata(),
            _make_collection(1, "Alpha Collection", tier="premier"),
            _make_collection(2, "Beta Collection", tier="premier"),
            _make_collection(3, "Gamma Collection", tier="curated"),
        ])
        new_entries, matched, skipped = bootstrap_collections(jsonl, collections_json)
        slugs = [e["slug"] for e in new_entries]
        assert len(slugs) == len(set(slugs)), "Slugs must be unique"
        assert len(new_entries) == 3


# ==============================
# Override / Skip Tests
# ==============================

class TestOverrides:
    def test_non_overridden_uses_auto_slug(self) -> None:
        record = {
            "id": 99999,
            "name": "Standard Collection",
            "stats": {"puzzle_count": 50},
            "quality_tier": "premier",
        }
        entry = generate_collection_entry(record)
        assert entry["slug"] == "standard-collection"

    def test_override_maps_consistent(self) -> None:
        """Every slug override should have a corresponding name override."""
        for gp_id in _GP_SLUG_OVERRIDES:
            assert gp_id in _GP_NAME_OVERRIDES, (
                f"GP ID {gp_id} has slug override but no name override"
            )

    def test_override_slugs_are_valid(self) -> None:
        """All override slugs match the collection schema regex."""
        slug_pattern = re.compile(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$")
        for gp_id, slug in _GP_SLUG_OVERRIDES.items():
            assert slug_pattern.match(slug), (
                f"Override slug '{slug}' for GP {gp_id} doesn't match schema"
            )
            assert len(slug) <= 64

    def test_skip_ids_excluded(
        self, tmp_path: Path, collections_json: Path,
    ) -> None:
        """Collections in _GP_SKIP_IDS are skipped with manual_skip reason."""
        if not _GP_SKIP_IDS:
            pytest.skip("No skip IDs configured yet")
        skip_id = next(iter(_GP_SKIP_IDS))
        jsonl = tmp_path / "sorted.jsonl"
        _write_jsonl(jsonl, [
            _make_metadata(),
            _make_collection(skip_id, "Skipped Collection", tier="premier"),
        ])
        new_entries, matched, skipped = bootstrap_collections(jsonl, collections_json)
        assert len(new_entries) == 0
        assert any(s[3] == "manual_skip" for s in skipped)


# ==============================
# Minimum Puzzle Count Tests
# ==============================

class TestMinPuzzleCountFilter:
    def test_small_collection_filtered(
        self, tmp_path: Path, collections_json: Path,
    ) -> None:
        """Collection with fewer than MIN_PUZZLE_COUNT puzzles is skipped."""
        jsonl = tmp_path / "sorted.jsonl"
        _write_jsonl(jsonl, [
            _make_metadata(),
            _make_collection(1, "Tiny Set", tier="premier", puzzle_count=20),
        ])
        new_entries, _, skipped = bootstrap_collections(jsonl, collections_json)
        assert len(new_entries) == 0
        assert any(s[3] == "too_few_puzzles" for s in skipped)

    def test_large_collection_passes(
        self, tmp_path: Path, collections_json: Path,
    ) -> None:
        """Collection with enough puzzles passes the filter."""
        jsonl = tmp_path / "sorted.jsonl"
        _write_jsonl(jsonl, [
            _make_metadata(),
            _make_collection(1, "Big Set", tier="premier", puzzle_count=50),
        ])
        new_entries, _, _ = bootstrap_collections(jsonl, collections_json)
        assert len(new_entries) == 1

    def test_exactly_30_passes(
        self, tmp_path: Path, collections_json: Path,
    ) -> None:
        """Collection with exactly MIN_PUZZLE_COUNT puzzles passes."""
        jsonl = tmp_path / "sorted.jsonl"
        _write_jsonl(jsonl, [
            _make_metadata(),
            _make_collection(1, "Borderline Set", tier="premier", puzzle_count=30),
        ])
        new_entries, _, _ = bootstrap_collections(jsonl, collections_json)
        assert len(new_entries) == 1

    def test_custom_min_puzzles(
        self, tmp_path: Path, collections_json: Path,
    ) -> None:
        """Custom min_puzzle_count parameter is respected."""
        jsonl = tmp_path / "sorted.jsonl"
        _write_jsonl(jsonl, [
            _make_metadata(),
            _make_collection(1, "Small Custom Set", tier="premier", puzzle_count=15),
        ])
        new_entries, _, _ = bootstrap_collections(
            jsonl, collections_json, min_puzzle_count=10,
        )
        assert len(new_entries) == 1


# ==============================
# Slug Collision Resolution Tests
# ==============================

class TestSlugCollisionResolution:
    def test_resolve_with_gp_suffix(self) -> None:
        """First collision gets -gp suffix."""
        existing = {"life-and-death"}
        resolved = _resolve_slug_collision("life-and-death", existing)
        assert resolved == "life-and-death-gp"

    def test_multiple_collisions_get_numbered_suffix(self) -> None:
        """Subsequent collisions get -gp-2, -gp-3, etc."""
        existing = {"tesuji", "tesuji-gp"}
        resolved = _resolve_slug_collision("tesuji", existing)
        assert resolved == "tesuji-gp-2"

    def test_slug_collision_in_bootstrap(
        self, tmp_path: Path, collections_json: Path,
    ) -> None:
        """Within-batch slug collision is resolved with -gp suffix.

        Two GP collections whose names generate the same slug after
        clean_name() get resolved: the second gets a -gp suffix.
        """
        jsonl = tmp_path / "sorted.jsonl"
        # Both names clean to "Test Set" -> slug "test-set"
        _write_jsonl(jsonl, [
            _make_metadata(),
            _make_collection(1, "Test Set [user1]", tier="premier"),
            _make_collection(2, "Test Set [user2]", tier="premier"),
        ])
        new_entries, _, _ = bootstrap_collections(jsonl, collections_json)
        assert len(new_entries) == 2
        slugs = [e["slug"] for e in new_entries]
        assert "test-set" in slugs
        assert "test-set-gp" in slugs


# ==============================
# Description from API Tests
# ==============================

class TestDescriptionFromApi:
    def test_goproblems_description_used(self) -> None:
        """Record with a valid English description uses it."""
        record = {
            "name": "Semeai Collection",
            "description": "Semeai (capturing race) problems from GoProblems community",
            "stats": {"puzzle_count": 50},
            "quality_tier": "premier",
        }
        entry = generate_collection_entry(record)
        assert "Semeai (capturing race)" in entry["description"]
        assert entry["description"].endswith(".")

    def test_non_english_description_ignored(self) -> None:
        """CJK description falls back to auto-generated."""
        record = {
            "name": "Test Collection",
            "description": "\u6b7b\u6d3b\u554f\u984c\u96c6",
            "stats": {"puzzle_count": 50},
            "quality_tier": "premier",
        }
        entry = generate_collection_entry(record)
        assert "GoProblems community collection" in entry["description"]

    def test_short_description_ignored(self) -> None:
        """Description shorter than 10 chars falls back to auto-generated."""
        record = {
            "name": "Test Collection",
            "description": "Short",
            "stats": {"puzzle_count": 50},
            "quality_tier": "premier",
        }
        entry = generate_collection_entry(record)
        assert "GoProblems community collection" in entry["description"]

    def test_long_description_truncated(self) -> None:
        """Description longer than 512 chars is truncated."""
        long_desc = "A" * 600
        record = {
            "name": "Test Collection",
            "description": long_desc,
            "stats": {"puzzle_count": 50},
            "quality_tier": "premier",
        }
        entry = generate_collection_entry(record)
        assert len(entry["description"]) <= 512
        assert entry["description"].endswith("...")

    def test_description_gets_period(self) -> None:
        """Description without trailing period gets one added."""
        record = {
            "name": "Test Collection",
            "description": "Problems about life and death situations",
            "stats": {"puzzle_count": 50},
            "quality_tier": "premier",
        }
        entry = generate_collection_entry(record)
        assert entry["description"].endswith(".")


# ==============================
# Schema Validation Tests
# ==============================

class TestSchemaValidation:
    def test_valid_entry_passes(self) -> None:
        """Standard valid entry has no validation errors."""
        entry = {
            "slug": "test-collection",
            "name": "Test Collection",
            "description": "A valid test collection for Go problems.",
            "type": "reference",
            "ordering": "source",
            "tier": "premier",
        }
        errors = _validate_entry(entry)
        assert errors == []

    def test_invalid_slug_rejected(self) -> None:
        """Entry with bad slug is rejected."""
        entry = {
            "slug": "BAD SLUG!",
            "name": "Test",
            "description": "Valid description here.",
            "type": "reference",
            "ordering": "source",
            "tier": "premier",
        }
        errors = _validate_entry(entry)
        assert any("slug" in e.lower() for e in errors)

    def test_single_char_slug_rejected(self) -> None:
        """Single-character slug doesn't match regex (needs at least 2)."""
        entry = {
            "slug": "x",
            "name": "Test",
            "description": "Valid description here.",
            "type": "reference",
            "ordering": "source",
            "tier": "premier",
        }
        errors = _validate_entry(entry)
        assert any("slug" in e.lower() for e in errors)

    def test_invalid_type_rejected(self) -> None:
        """Entry with invalid type is rejected."""
        entry = {
            "slug": "test-collection",
            "name": "Test",
            "description": "Valid description here.",
            "type": "invalid_type",
            "ordering": "source",
            "tier": "premier",
        }
        errors = _validate_entry(entry)
        assert any("type" in e.lower() for e in errors)

    def test_generated_entries_pass_validation(self) -> None:
        """All auto-generated entries pass schema validation."""
        record = {
            "name": "Life and Death Problems",
            "stats": {"puzzle_count": 100},
            "quality_tier": "premier",
        }
        entry = generate_collection_entry(record)
        errors = _validate_entry(entry)
        assert errors == [], f"Generated entry should be valid: {errors}"


# ==============================
# Auto-Merge Tests
# ==============================

class TestAutoMerge:
    def test_merge_appends_entries(self, tmp_path: Path) -> None:
        """New entries are appended to existing collections."""
        config = {
            "schema_version": "3.0",
            "_reference": "docs/concepts/collections.md",
            "collections": [
                {"slug": "existing-one", "name": "Existing One"},
            ],
        }
        coll_path = tmp_path / "collections.json"
        coll_path.write_text(
            json.dumps(config, indent=2) + "\n", encoding="utf-8",
        )

        new_entries = [
            {"slug": "new-gp-entry", "name": "New GP Entry"},
        ]
        _merge_into_collections_json(coll_path, new_entries, backup=False)

        merged = json.loads(coll_path.read_text(encoding="utf-8"))
        assert len(merged["collections"]) == 2
        slugs = [c["slug"] for c in merged["collections"]]
        assert "existing-one" in slugs
        assert "new-gp-entry" in slugs

    def test_merge_creates_backup(self, tmp_path: Path) -> None:
        """Backup file is created before merge."""
        config = {
            "schema_version": "3.0",
            "collections": [{"slug": "old", "name": "Old"}],
        }
        coll_path = tmp_path / "collections.json"
        coll_path.write_text(json.dumps(config), encoding="utf-8")

        _merge_into_collections_json(
            coll_path, [{"slug": "new", "name": "New"}], backup=True,
        )

        backup_files = list(tmp_path.glob("collections-backup-*.json"))
        assert len(backup_files) == 1

        backup_data = json.loads(backup_files[0].read_text(encoding="utf-8"))
        assert len(backup_data["collections"]) == 1
        assert backup_data["collections"][0]["slug"] == "old"

    def test_merge_preserves_version_and_reference(self, tmp_path: Path) -> None:
        """Merged file preserves version and _reference fields."""
        config = {
            "_reference": "custom/ref.md",
            "schema_version": "3.0",
            "collections": [],
        }
        coll_path = tmp_path / "collections.json"
        coll_path.write_text(json.dumps(config), encoding="utf-8")

        _merge_into_collections_json(
            coll_path, [{"slug": "aa-test", "name": "Test"}], backup=False,
        )

        merged = json.loads(coll_path.read_text(encoding="utf-8"))
        assert merged["_reference"] == "custom/ref.md"
        assert merged["schema_version"] == "3.0"

    def test_idempotent_second_run(
        self, tmp_path: Path,
    ) -> None:
        """Second bootstrap run produces zero new entries (idempotent)."""
        config = {
            "schema_version": "3.0",
            "_reference": "docs/concepts/collections.md",
            "collections": [],
        }
        coll_path = tmp_path / "collections.json"
        coll_path.write_text(json.dumps(config), encoding="utf-8")

        jsonl = tmp_path / "sorted.jsonl"
        _write_jsonl(jsonl, [
            _make_metadata(),
            _make_collection(1, "Unique Life and Death Set", tier="premier"),
        ])

        # First run: should create an entry
        new_entries_1, _, _ = bootstrap_collections(jsonl, coll_path)
        assert len(new_entries_1) == 1

        # Merge the entries
        _merge_into_collections_json(coll_path, new_entries_1, backup=False)

        # Second run: should find zero new entries (matched via alias)
        new_entries_2, matched_2, _ = bootstrap_collections(jsonl, coll_path)
        assert len(new_entries_2) == 0
        assert len(matched_2) == 1
