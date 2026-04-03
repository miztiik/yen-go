"""Unit tests for daily challenge predicate functions and helpers.

Extracted from test_daily_master_index.py (T12 cleanup).  The master-index
generation tests were dropped (feature removed); these tests cover live code in
timed.py, by_tag.py, _helpers.py, and generator.py.

Functions under test:
- timed.py:    _is_easy, _is_medium, _is_hard, generate_timed_challenge
- by_tag.py:   _has_tag, _get_related_tags, _get_tag_info, generate_tag_challenge
- _helpers.py: extract_puzzle_id, to_puzzle_ref, get_level_slug_categories,
               get_level_numeric_categories, build_level_slug_to_id_map,
               build_tag_slug_to_id_map, build_tag_rotation, build_tag_category_map
- generator.py: DailyGenerator._load_puzzle_pool, generate_daily_for_date
"""

from datetime import datetime
from pathlib import Path

import pytest

from backend.puzzle_manager.daily._helpers import (
    build_level_slug_to_id_map,
    build_tag_category_map,
    build_tag_rotation,
    build_tag_slug_to_id_map,
    extract_puzzle_id,
    get_level_numeric_categories,
    get_level_slug_categories,
    to_puzzle_ref,
)
from backend.puzzle_manager.daily.by_tag import (
    _get_related_tags,
    _has_tag,
    generate_tag_challenge,
)
from backend.puzzle_manager.daily.timed import (
    _is_easy,
    _is_hard,
    _is_medium,
    generate_timed_challenge,
)
from backend.puzzle_manager.exceptions import DailyGenerationError
from backend.puzzle_manager.models.config import DailyConfig
from backend.puzzle_manager.tests.conftest import make_compact_entry

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Compact Format Support in timed.py
# ---------------------------------------------------------------------------


class TestTimedCompactFormat:
    """Tests for compact entry support in timed challenge generation."""

    def test_is_easy_compact(self) -> None:
        """_is_easy should recognize compact entries with l < 140."""
        entry = make_compact_entry(level_id=120)  # beginner
        assert _is_easy(entry) is True

    def test_is_medium_compact(self) -> None:
        """_is_medium should recognize compact entries with 140 <= l < 160."""
        entry = make_compact_entry(level_id=140)  # intermediate
        assert _is_medium(entry) is True

    def test_is_hard_compact(self) -> None:
        """_is_hard should recognize compact entries with l >= 160."""
        entry = make_compact_entry(level_id=210)  # low-dan
        assert _is_hard(entry) is True

    def test_timed_to_puzzle_ref_compact(self) -> None:
        """to_puzzle_ref should convert compact entry to PuzzleRef."""
        entry = make_compact_entry(batch="0002", hash_id="abc123", level_id=130)
        ref = to_puzzle_ref(entry)
        assert ref.path == "sgf/0002/abc123.sgf"
        assert ref.id == "abc123"
        assert ref.level == "elementary"

    def test_timed_extract_puzzle_id_compact(self) -> None:
        """extract_puzzle_id should extract hash from compact path."""
        entry = make_compact_entry(hash_id="deadbeef12345678")
        assert extract_puzzle_id(entry) == "deadbeef12345678"

    def test_generate_timed_with_compact_pool(self) -> None:
        """generate_timed_challenge should work with compact entry pool."""
        pool = (
            [make_compact_entry(hash_id=f"e{i:03d}", level_id=120) for i in range(20)]
            + [make_compact_entry(hash_id=f"m{i:03d}", level_id=140) for i in range(20)]
            + [make_compact_entry(hash_id=f"h{i:03d}", level_id=210) for i in range(20)]
        )
        config = DailyConfig(puzzles_per_day=5)
        result = generate_timed_challenge(datetime(2026, 2, 1), pool, config)

        assert result is not None
        assert len(result.sets) == 3
        for timed_set in result.sets:
            for p in timed_set.puzzles:
                assert "\\" not in p.path
                assert p.path.startswith("sgf/")


# ---------------------------------------------------------------------------
# Compact Format Support in by_tag.py
# ---------------------------------------------------------------------------


class TestByTagCompactFormat:
    """Tests for compact entry support in tag challenge generation."""

    def test_has_tag_with_numeric_ids(self) -> None:
        """_has_tag should match numeric tag IDs in compact entries."""
        slug_to_id = build_tag_slug_to_id_map()
        ladder_id = slug_to_id.get("ladder")
        lad_id = slug_to_id.get("life-and-death")
        assert ladder_id is not None, "ladder must exist in tags.json"
        assert lad_id is not None, "life-and-death must exist in tags.json"
        entry = make_compact_entry(tag_ids=[ladder_id, lad_id])
        assert _has_tag(entry, "ladder") is True
        assert _has_tag(entry, "snapback") is False

    def test_by_tag_to_puzzle_ref_compact(self) -> None:
        """to_puzzle_ref should convert compact entry to PuzzleRef."""
        entry = make_compact_entry(batch="0003", hash_id="xyz789", level_id=160)
        ref = to_puzzle_ref(entry)
        assert ref.path == "sgf/0003/xyz789.sgf"
        assert ref.id == "xyz789"
        assert ref.level == "advanced"

    def test_by_tag_extract_puzzle_id_compact(self) -> None:
        """extract_puzzle_id should extract hash from compact path."""
        entry = make_compact_entry(hash_id="cafebabe")
        assert extract_puzzle_id(entry) == "cafebabe"

    def test_generate_tag_challenge_with_compact_pool(self) -> None:
        """generate_tag_challenge should work with compact entry pool."""
        slug_to_id = build_tag_slug_to_id_map()
        ladder_id = slug_to_id.get("ladder")
        assert ladder_id is not None, "ladder must exist in tags.json"
        pool = [
            make_compact_entry(hash_id=f"t{i:03d}", level_id=130, tag_ids=[ladder_id])
            for i in range(30)
        ]
        config = DailyConfig(puzzles_per_day=5)
        result = generate_tag_challenge(datetime(2026, 2, 1), pool, config)

        assert result is not None
        assert result.total > 0
        for p in result.puzzles:
            assert "\\" not in p.path
            assert p.path.startswith("sgf/")


# ---------------------------------------------------------------------------
# DB-based puzzle pool loading (generator.py)
# ---------------------------------------------------------------------------


class TestLoadPuzzlePool:
    """Tests for DB-based puzzle pool loading."""

    def test_no_db_raises(self, tmp_path: Path) -> None:
        """Missing yengo-search.db should raise DailyGenerationError."""
        from backend.puzzle_manager.daily.generator import DailyGenerator

        gen = DailyGenerator(db_path=tmp_path / "yengo-search.db")
        with pytest.raises(DailyGenerationError):
            gen._load_puzzle_pool()


# ---------------------------------------------------------------------------
# Predicate boundary conditions and helper consistency
# ---------------------------------------------------------------------------


class TestPredicateBoundaries:
    """Edge-case tests for predicate functions (extracted from TestReviewFindings)."""

    def test_get_tag_info_returns_display_name(self) -> None:
        """_get_tag_info should return display_name from tags config."""
        from backend.puzzle_manager.daily.by_tag import _get_tag_info

        info = _get_tag_info("ladder")
        assert isinstance(info, dict)
        if info:
            assert "display_name" in info

    def test_get_tag_info_unknown_tag(self) -> None:
        """_get_tag_info should return empty dict for unknown tags."""
        from backend.puzzle_manager.daily.by_tag import _get_tag_info

        info = _get_tag_info("nonexistent-tag-xyz")
        assert info == {}

    def test_level_id_zero_not_classified(self) -> None:
        """Compact entries with level_id=0 should not match any bucket."""
        entry = make_compact_entry(level_id=0)
        assert _is_easy(entry) is False
        assert _is_medium(entry) is False
        assert _is_hard(entry) is False

    def test_shared_helpers_level_categories_consistent(self) -> None:
        """Slug and numeric level categories should be consistent with each other."""
        slug_cats = get_level_slug_categories()
        num_cats = get_level_numeric_categories()
        id_map = build_level_slug_to_id_map()

        for slug in slug_cats[0]:  # beginner slugs
            assert id_map[slug] in num_cats[0], f"{slug} not in numeric beginner set"

    def test_generate_daily_for_date_convenience(self, tmp_path: Path) -> None:
        """generate_daily_for_date should produce a valid DailyChallenge."""
        from backend.puzzle_manager.core.db_builder import build_search_db
        from backend.puzzle_manager.core.db_models import PuzzleEntry
        from backend.puzzle_manager.daily.generator import generate_daily_for_date

        entries = [
            PuzzleEntry(
                content_hash=f"c{i:03d}abcdef012345",
                batch="0001",
                level_id=120,
                quality=3,
                content_type=2,
                cx_depth=1,
                cx_refutations=1,
                cx_solution_len=5,
                cx_unique_resp=1,
                tag_ids=[10],
                collection_ids=[],
            )
            for i in range(30)
        ]
        build_search_db(
            entries=entries,
            collections=[],
            output_path=tmp_path / "yengo-search.db",
        )

        result = generate_daily_for_date(datetime(2026, 3, 1), db_path=tmp_path / "yengo-search.db")
        assert result is not None
        assert result.date == "2026-03-01"


# ---------------------------------------------------------------------------
# Config-Driven Tag Rotation
# ---------------------------------------------------------------------------


class TestConfigDrivenTagRotation:
    """Verify tag rotation and related-tag fallback are fully config-driven.

    No tag slugs should be hardcoded in by_tag.py.  All expected values are
    derived from config/tags.json at runtime.
    """

    def test_rotation_contains_all_config_tags(self) -> None:
        """build_tag_rotation() must include every tag defined in config/tags.json."""
        slug_to_id = build_tag_slug_to_id_map()
        rotation = build_tag_rotation()
        for slug in slug_to_id:
            assert slug in rotation, f"Tag '{slug}' from config is missing from rotation"

    def test_rotation_ordered_by_id(self) -> None:
        """build_tag_rotation() slugs must be sorted ascending by their numeric config ID."""
        slug_to_id = build_tag_slug_to_id_map()
        rotation = build_tag_rotation()
        ids = [slug_to_id[s] for s in rotation if s in slug_to_id]
        assert ids == sorted(ids), "Rotation is not sorted by config ID"

    def test_rotation_length_matches_config(self) -> None:
        """Rotation length must equal the total number of tags in config/tags.json."""
        slug_to_id = build_tag_slug_to_id_map()
        rotation = build_tag_rotation()
        assert len(rotation) == len(slug_to_id)

    def test_rotation_is_immutable_tuple(self) -> None:
        """build_tag_rotation() must return a tuple (hashable, lru_cache-safe)."""
        rotation = build_tag_rotation()
        assert isinstance(rotation, tuple)

    def test_category_map_covers_all_rotation_slugs(self) -> None:
        """Every slug in the rotation must have a non-empty category in config."""
        rotation = build_tag_rotation()
        category_map = build_tag_category_map()
        for slug in rotation:
            assert slug in category_map, f"'{slug}' in rotation but not in category map"
            assert category_map[slug], f"'{slug}' has empty category in config"

    def test_get_related_tags_returns_siblings(self) -> None:
        """_get_related_tags must return other slugs in the same config category."""
        category_map = build_tag_category_map()
        related = _get_related_tags("ladder")
        ladder_category = category_map.get("ladder")
        assert ladder_category, "ladder must have a category in config"
        for slug in related:
            assert slug in category_map, f"Related tag '{slug}' not in config"
            assert category_map[slug] == ladder_category, (
                f"Related tag '{slug}' has category '{category_map[slug]}', "
                f"expected '{ladder_category}'"
            )
        assert "ladder" not in related, "Tag should not be related to itself"

    def test_get_related_tags_unknown_returns_empty(self) -> None:
        """_get_related_tags for a non-existent tag returns empty list."""
        assert _get_related_tags("nonexistent-tag-xyz") == []

    def test_generate_tag_challenge_selected_tag_from_config(self) -> None:
        """The tag selected for any date must be a valid config slug."""
        slug_to_id = build_tag_slug_to_id_map()
        rotation = build_tag_rotation()
        for day_of_year in range(1, len(rotation) + 1):
            tag_index = day_of_year % len(rotation)
            selected = rotation[tag_index]
            assert selected in slug_to_id, (
                f"Day {day_of_year}: selected tag '{selected}' not in config/tags.json"
            )

    def test_rotation_stable_across_calls(self) -> None:
        """build_tag_rotation() must return the same tuple on every call (lru_cache)."""
        rotation_a = build_tag_rotation()
        rotation_b = build_tag_rotation()
        assert rotation_a is rotation_b, "lru_cache should return the same object"
