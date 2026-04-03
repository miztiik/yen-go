"""
Tests for tools.ogs.bootstrap_collections module.

Tests name cleanup, slug generation, curator/type inference,
and the end-to-end bootstrap logic.
"""

import json
import re
from pathlib import Path

import pytest

from tools.ogs.bootstrap_collections import (
    _NAME_OVERRIDES,
    _SKIP_IDS,
    _SLUG_OVERRIDES,
    bootstrap_collections,
    clean_name,
    generate_collection_entry,
    generate_slug,
    infer_curator,
    infer_type,
)

# ==============================
# clean_name Tests
# ==============================

class TestCleanName:
    def test_strips_bracket_suffix(self) -> None:
        assert clean_name("Life and Death [Atorrante]") == "Life and Death"

    def test_strips_possessives(self) -> None:
        assert clean_name("Cho Chikun's Problems") == "Cho Chikun Problems"

    def test_strips_leading_number(self) -> None:
        assert clean_name("1. Elementary Problems") == "Elementary Problems"

    def test_collapses_whitespace(self) -> None:
        assert clean_name("Too   Many  Spaces") == "Too Many Spaces"

    def test_strips_trailing_dashes(self) -> None:
        assert clean_name("Collection -") == "Collection"

    def test_combined_cleanup(self) -> None:
        result = clean_name("3. Cho Chikun's Life & Death [kisvadim]")
        assert result == "Cho Chikun Life & Death"


# ==============================
# generate_slug Tests
# ==============================

class TestGenerateSlug:
    def test_basic_slug(self) -> None:
        assert generate_slug("Tesuji Training") == "tesuji-training"

    def test_special_characters_replaced(self) -> None:
        assert generate_slug("Life & Death: Elementary") == "life-death-elementary"

    def test_consecutive_hyphens_collapsed(self) -> None:
        assert generate_slug("A -- B") == "a-b"

    def test_leading_trailing_hyphens_stripped(self) -> None:
        assert generate_slug("-Leading-") == "leading"

    def test_max_64_chars(self) -> None:
        long_name = "A" * 100
        slug = generate_slug(long_name)
        assert len(slug) <= 64

    def test_min_length_short_input(self) -> None:
        slug = generate_slug("X")
        assert len(slug) >= 2

    def test_empty_input(self) -> None:
        slug = generate_slug("")
        assert slug == "unknown"
        assert len(slug) >= 2

    def test_cyrillic_transliterated(self) -> None:
        """Cyrillic text is transliterated to ASCII via unidecode."""
        slug = generate_slug("базовые формы")
        assert slug == "bazovye-formy"

    def test_cjk_transliterated(self) -> None:
        """CJK characters are transliterated to ASCII via unidecode."""
        slug = generate_slug("四路官子譜")
        assert slug != "ogs-unknown"
        assert re.match(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$", slug)

    def test_thai_transliterated(self) -> None:
        """Thai characters are transliterated to ASCII via unidecode."""
        slug = generate_slug("ปิดประตู")
        assert slug != "ogs-unknown"
        assert re.match(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$", slug)


# ==============================
# infer_curator Tests
# ==============================

class TestInferCurator:
    def test_known_author_cho_chikun(self) -> None:
        assert infer_curator("Cho Chikun's Elementary Problems") == "Cho Chikun"

    def test_known_author_go_seigen(self) -> None:
        assert infer_curator("Go Seigen Tesuji Collection") == "Go Seigen"

    def test_known_author_lee_changho(self) -> None:
        assert infer_curator("Lee Changho's Life and Death") == "Lee Changho"

    def test_unknown_author_defaults_community(self) -> None:
        assert infer_curator("Random Collection XYZ") == "Community"

    def test_case_insensitive(self) -> None:
        assert infer_curator("CHO CHIKUN problems") == "Cho Chikun"


# ==============================
# infer_type Tests
# ==============================

class TestInferType:
    def test_known_curator_returns_author(self) -> None:
        assert infer_type("Anything", "Cho Chikun") == "author"

    def test_technique_keyword(self) -> None:
        assert infer_type("Life and Death Problems", "Community") == "technique"

    def test_tesuji_keyword(self) -> None:
        assert infer_type("Basic Tesuji", "Community") == "technique"

    def test_graded_keyword(self) -> None:
        assert infer_type("Beginner Collection", "Community") == "graded"

    def test_dan_keyword(self) -> None:
        assert infer_type("Dan Level Puzzles", "Community") == "graded"

    def test_default_reference(self) -> None:
        assert infer_type("Random Puzzles", "Community") == "reference"


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
        assert entry["source"] == "ogs"
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
        """Tier field is mapped from OGS quality_tier."""
        for ogs_tier, expected_schema_tier in [
            ("premier", "premier"),
            ("curated", "curated"),
            ("community", "community"),
            ("unvetted", "community"),
        ]:
            record = {
                "name": f"Test {ogs_tier}",
                "stats": {"puzzle_count": 50},
                "quality_tier": ogs_tier,
            }
            entry = generate_collection_entry(record)
            assert entry["tier"] == expected_schema_tier, (
                f"OGS tier '{ogs_tier}' should map to schema tier '{expected_schema_tier}'"
            )

    def test_missing_quality_tier_defaults_to_community(self) -> None:
        """Missing quality_tier defaults to community."""
        record = {
            "name": "No Tier Collection",
            "stats": {"puzzle_count": 10},
        }
        entry = generate_collection_entry(record)
        assert entry["tier"] == "community"


# ==============================
# bootstrap_collections (end-to-end) Tests
# ==============================

def _make_metadata() -> dict:
    return {"type": "metadata", "total_collections": 0}


def _make_collection(
    coll_id: int, name: str, tier: str = "premier",
    puzzle_count: int = 50,
) -> dict:
    return {
        "type": "collection",
        "id": coll_id,
        "name": name,
        "quality_tier": tier,
        "puzzles": [1, 2, 3],
        "stats": {
            "puzzle_count": puzzle_count,
            "view_count": 100,
            "solved_count": 50,
            "attempt_count": 80,
            "rating": 4.5,
            "rating_count": 10,
        },
        "difficulty": {"yengo_level": "intermediate"},
    }


def _write_jsonl(path: Path, records: list[dict]) -> None:
    lines = [json.dumps(r) for r in records]
    path.write_text("\n".join(lines), encoding="utf-8")


@pytest.fixture
def collections_json(tmp_path: Path) -> Path:
    """Minimal collections.json with one existing collection."""
    config = {
        "version": "3.0",
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


class TestBootstrapCollections:
    def test_matched_collection_not_bootstrapped(
        self, tmp_path: Path, collections_json: Path,
    ) -> None:
        """OGS collection matching existing YenGo slug is reported as matched."""
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
        assert new_entries[0]["source"] == "ogs"
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

    def test_slug_collision_skipped(
        self, tmp_path: Path, collections_json: Path,
    ) -> None:
        """Collection whose generated slug collides with existing is skipped."""
        # "Tesuji Training" already exists in collections_json
        jsonl = tmp_path / "sorted.jsonl"
        _write_jsonl(jsonl, [
            _make_metadata(),
            # Same slug would be generated: "tesuji-training"
            _make_collection(1, "Tesuji Training", tier="premier"),
        ])
        new_entries, matched, skipped = bootstrap_collections(jsonl, collections_json)
        # This should match via CollectionMatcher (exact name match)
        assert len(matched) == 1 or len(skipped) >= 1

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

    def test_multiple_new_entries_unique_slugs(
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
# Override / Skip / Map Tests
# ==============================

class TestOverrides:
    def test_slug_override_applied(self) -> None:
        """Overridden OGS ID gets the manually curated slug."""
        record = {
            "id": 9389,
            "name": "базовые формы 1",
            "stats": {"puzzle_count": 41},
            "quality_tier": "premier",
        }
        entry = generate_collection_entry(record)
        assert entry["slug"] == "basic-shape-recognition"
        assert entry["name"] == "Basic Shape Recognition"
        # Original OGS name preserved in aliases for matching
        assert "базовые формы 1" in entry["aliases"]

    def test_name_override_applied(self) -> None:
        """Overridden OGS ID gets the manually curated display name."""
        record = {
            "id": 5442,
            "name": "ปิดประตู",
            "stats": {"puzzle_count": 30},
            "quality_tier": "premier",
        }
        entry = generate_collection_entry(record)
        assert entry["slug"] == "geta-technique"
        assert entry["name"] == "Geta Technique"

    def test_non_overridden_uses_auto_slug(self) -> None:
        """Non-overridden collection uses auto-generated slug."""
        record = {
            "id": 99999,
            "name": "Standard Collection",
            "stats": {"puzzle_count": 50},
            "quality_tier": "premier",
        }
        entry = generate_collection_entry(record)
        assert entry["slug"] == "standard-collection"

    def test_skip_ids_excluded(
        self, tmp_path: Path, collections_json: Path,
    ) -> None:
        """Collections in _SKIP_IDS are skipped with manual_skip reason."""
        skip_id = next(iter(_SKIP_IDS))
        jsonl = tmp_path / "sorted.jsonl"
        _write_jsonl(jsonl, [
            _make_metadata(),
            _make_collection(skip_id, "Some Username Collection", tier="premier"),
        ])
        new_entries, matched, skipped = bootstrap_collections(jsonl, collections_json)
        assert len(new_entries) == 0
        assert any(s[3] == "manual_skip" for s in skipped)

    def test_all_overrides_have_matching_names(self) -> None:
        """Every slug override also has a corresponding name override."""
        for ogs_id in _SLUG_OVERRIDES:
            assert ogs_id in _NAME_OVERRIDES, (
                f"OGS ID {ogs_id} has slug override but no name override"
            )

    def test_override_slugs_are_valid(self) -> None:
        """All override slugs match the collection schema regex."""
        slug_pattern = re.compile(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$")
        for ogs_id, slug in _SLUG_OVERRIDES.items():
            assert slug_pattern.match(slug), (
                f"Override slug '{slug}' for OGS {ogs_id} doesn't match schema"
            )
            assert len(slug) <= 64
