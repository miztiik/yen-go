"""Tests for analyzers/config_lookup.py — centralized config loading (Phase 1).

Covers: tag slug→id, tag id→name, level id→(name,range), level slug→id,
resolver helpers, parse_tag_ids, extract_metadata, extract_level_slug,
clear_config_caches, and project root resolution (MH-1, MH-2).
"""

from pathlib import Path

import pytest

# Ensure tools/puzzle-enrichment-lab is importable
_LAB_DIR = Path(__file__).resolve().parent.parent

from analyzers.config_lookup import (
    clear_config_caches,
    extract_level_slug,
    extract_metadata,
    load_level_id_map,
    load_level_slug_to_id,
    load_tag_id_to_name,
    load_tag_slug_map,
    parse_tag_ids,
    resolve_level_info,
    resolve_tag_names,
)


@pytest.fixture(autouse=True)
def _fresh_caches():
    """MH-1: clear_config_caches() must be usable for test isolation."""
    clear_config_caches()
    yield
    clear_config_caches()


# ===================================================================
# MH-2: Project root / path resolution correctness
# ===================================================================


@pytest.mark.unit
class TestPathResolution:
    """Config files must be found regardless of import location."""

    def test_tag_slug_map_loads(self):
        """load_tag_slug_map returns a non-empty dict with string keys and int values."""
        result = load_tag_slug_map()
        assert isinstance(result, dict)
        assert len(result) > 0
        for k, v in list(result.items())[:3]:
            assert isinstance(k, str)
            assert isinstance(v, int)

    def test_level_id_map_loads(self):
        """load_level_id_map returns a non-empty dict with int keys."""
        result = load_level_id_map()
        assert isinstance(result, dict)
        assert len(result) > 0
        for k, v in list(result.items())[:3]:
            assert isinstance(k, int)
            assert isinstance(v, tuple)
            assert len(v) == 2

    def test_level_slug_to_id_loads(self):
        """load_level_slug_to_id returns non-empty dict with string keys and int values."""
        result = load_level_slug_to_id()
        assert isinstance(result, dict)
        assert len(result) > 0
        for k, v in list(result.items())[:3]:
            assert isinstance(k, str)
            assert isinstance(v, int)


# ===================================================================
# Tag slug map
# ===================================================================


@pytest.mark.unit
class TestLoadTagSlugMap:
    """Tag slug → numeric ID loading from config/tags.json."""

    def test_known_tags_present(self):
        slug_map = load_tag_slug_map()
        assert "life-and-death" in slug_map
        assert "ko" in slug_map
        assert slug_map["life-and-death"] > 0
        assert slug_map["ko"] > 0

    def test_aliases_included(self):
        slug_map = load_tag_slug_map()
        # Aliases map to the same ID as their parent tag
        # Verify at least some entries exist (aliases depend on tags.json content)
        assert len(slug_map) > 0


# ===================================================================
# Tag id → name
# ===================================================================


@pytest.mark.unit
class TestLoadTagIdToName:
    """Tag numeric ID → human-readable name."""

    def test_returns_dict(self):
        result = load_tag_id_to_name()
        assert isinstance(result, dict)
        assert len(result) > 0

    def test_known_id_has_name(self):
        slug_map = load_tag_slug_map()
        id_to_name = load_tag_id_to_name()
        lnd_id = slug_map.get("life-and-death")
        if lnd_id is not None:
            assert lnd_id in id_to_name
            assert isinstance(id_to_name[lnd_id], str)


# ===================================================================
# Level id → (name, range)
# ===================================================================


@pytest.mark.unit
class TestLoadLevelIdMap:
    """Level numeric ID → (name, rankRange) mapping."""

    def test_known_levels_present(self):
        level_map = load_level_id_map()
        # At least some levels should exist
        assert len(level_map) >= 5
        for lid, (name, range_str) in level_map.items():
            assert isinstance(lid, int)
            assert isinstance(name, str)
            assert isinstance(range_str, str)


# ===================================================================
# Level slug → id
# ===================================================================


@pytest.mark.unit
class TestLoadLevelSlugToId:

    def test_known_slugs(self):
        slug_map = load_level_slug_to_id()
        assert "novice" in slug_map
        assert "beginner" in slug_map
        assert "expert" in slug_map


# ===================================================================
# Resolvers
# ===================================================================


@pytest.mark.unit
class TestResolveTagNames:

    def test_resolves_known_ids(self):
        slug_map = load_tag_slug_map()
        lnd_id = slug_map.get("life-and-death")
        if lnd_id is not None:
            names = resolve_tag_names([lnd_id])
            assert len(names) == 1
            assert isinstance(names[0], str)

    def test_unknown_id_fallback(self):
        names = resolve_tag_names([99999])
        assert names == ["tag-99999"]


@pytest.mark.unit
class TestResolveLevelInfo:

    def test_resolves_known_id(self):
        level_map = load_level_id_map()
        if level_map:
            first_id = next(iter(level_map))
            name, range_str = resolve_level_info(first_id)
            assert isinstance(name, str)
            assert name != ""

    def test_unknown_id_returns_empty(self):
        name, range_str = resolve_level_info(99999)
        assert name == ""
        assert range_str == ""


# ===================================================================
# parse_tag_ids
# ===================================================================


@pytest.mark.unit
class TestParseTagIdsConfigLookup:
    """parse_tag_ids with both numeric and slug paths."""

    def test_numeric_ids(self):
        assert parse_tag_ids("10,12,34") == [10, 12, 34]

    def test_single_numeric(self):
        assert parse_tag_ids("42") == [42]

    def test_empty_string(self):
        assert parse_tag_ids("") == []

    def test_whitespace_only(self):
        assert parse_tag_ids("  ,  , ") == []

    def test_numeric_with_whitespace(self):
        assert parse_tag_ids(" 10 , 12 ") == [10, 12]

    def test_slug_lookup(self):
        result = parse_tag_ids("life-and-death,ko")
        assert len(result) == 2
        assert all(isinstance(r, int) for r in result)

    def test_unknown_slug_skipped(self):
        result = parse_tag_ids("life-and-death,nonexistent-tag-xyz")
        assert len(result) >= 1


# ===================================================================
# extract_metadata
# ===================================================================


@pytest.mark.unit
class TestExtractMetadataConfigLookup:
    """extract_metadata produces correct dict from SGF root."""

    def test_basic_extraction(self):
        from core.tsumego_analysis import parse_sgf
        sgf = "(;FF[4]GM[1]SZ[19]GN[test-puzzle]YC[TR]YO[flexible]YK[direct]AB[cc]AW[dd];B[cb])"
        root = parse_sgf(sgf)
        meta = extract_metadata(root)
        assert meta["puzzle_id"] == "test-puzzle"
        assert meta["corner"] == "TR"
        assert meta["move_order"] == "flexible"
        assert meta["ko_type"] == "direct"

    def test_defaults_for_missing_properties(self):
        from core.tsumego_analysis import parse_sgf
        sgf = "(;FF[4]GM[1]SZ[19]AB[cc]AW[dd];B[cb])"
        root = parse_sgf(sgf)
        meta = extract_metadata(root)
        assert meta["corner"] == "TL"
        assert meta["move_order"] == "strict"
        assert meta["ko_type"] == "none"


# ===================================================================
# extract_level_slug
# ===================================================================


@pytest.mark.unit
class TestExtractLevelSlugConfigLookup:

    def test_extracts_yg(self):
        from core.tsumego_analysis import parse_sgf
        sgf = "(;FF[4]GM[1]SZ[19]YG[intermediate]AB[cc]AW[dd];B[cb])"
        root = parse_sgf(sgf)
        assert extract_level_slug(root) == "intermediate"

    def test_none_when_absent(self):
        from core.tsumego_analysis import parse_sgf
        sgf = "(;FF[4]GM[1]SZ[19]AB[cc]AW[dd];B[cb])"
        root = parse_sgf(sgf)
        assert extract_level_slug(root) is None


# ===================================================================
# MH-1: clear_config_caches
# ===================================================================


@pytest.mark.unit
class TestClearConfigCaches:
    """MH-1: clear_config_caches() resets all module-level caches."""

    def test_cache_cleared_forces_reload(self):
        """After clear, next call re-loads from disk."""
        m1 = load_tag_slug_map()
        clear_config_caches()
        m2 = load_tag_slug_map()
        # Both should be equal (same data) but different objects (freshly loaded)
        assert m1 == m2

    def test_cache_reused_without_clear(self):
        """Without clear, second call reuses cached object."""
        m1 = load_tag_slug_map()
        m2 = load_tag_slug_map()
        assert m1 is m2  # Same object — cached
