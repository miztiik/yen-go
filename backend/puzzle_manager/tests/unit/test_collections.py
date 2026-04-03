"""Unit tests for collections feature (Spec 126, Phase 6).

Tests:
- YL[] parsing from SGF (T028)
- YL[] serialization to SGF (T029)
- YL[] round-trip (parse → build → parse)
- Collection view index generation (T030)
- Multi-collection membership (FR-015)
- Schema version bump to 10 (T033)
- config/collections.json structure (T026)
- config/schemas/collections.schema.json existence (T025)
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.puzzle_manager.core.primitives import Color, Point
from backend.puzzle_manager.core.sgf_builder import SGFBuilder
from backend.puzzle_manager.core.sgf_parser import YenGoProperties, parse_sgf

# =============================================================================
# T028: YL Parsing
# =============================================================================


class TestYLParsing:
    """Tests for YL[] (collection membership) parsing from SGF."""

    def test_parse_single_collection(self) -> None:
        """YL with single slug should parse to list with one element."""
        sgf = "(;GM[1]FF[4]SZ[9]PL[B]YV[10]YG[beginner]YL[essential-life-and-death]AB[dd];B[ee])"
        game = parse_sgf(sgf)
        assert game.yengo_props.collections == ["essential-life-and-death"]

    def test_parse_multiple_collections(self) -> None:
        """YL with comma-separated slugs should parse to sorted list."""
        sgf = "(;GM[1]FF[4]SZ[9]PL[B]YV[10]YG[beginner]YL[ko-problems,tesuji-training]AB[dd];B[ee])"
        game = parse_sgf(sgf)
        assert game.yengo_props.collections == ["ko-problems", "tesuji-training"]

    def test_parse_collections_sorted(self) -> None:
        """YL slugs should be sorted after parsing."""
        sgf = "(;GM[1]FF[4]SZ[9]PL[B]YV[10]YG[beginner]YL[tesuji-training,ko-problems]AB[dd];B[ee])"
        game = parse_sgf(sgf)
        assert game.yengo_props.collections == ["ko-problems", "tesuji-training"]

    def test_parse_no_yl_property(self) -> None:
        """Missing YL should result in empty collections list."""
        sgf = "(;GM[1]FF[4]SZ[9]PL[B]YV[10]YG[beginner]AB[dd];B[ee])"
        game = parse_sgf(sgf)
        assert game.yengo_props.collections == []

    def test_parse_empty_yl(self) -> None:
        """Empty YL[] should result in empty collections list."""
        sgf = "(;GM[1]FF[4]SZ[9]PL[B]YV[10]YG[beginner]YL[]AB[dd];B[ee])"
        game = parse_sgf(sgf)
        assert game.yengo_props.collections == []

    def test_yengo_properties_default_collections(self) -> None:
        """YenGoProperties default should have empty collections."""
        props = YenGoProperties()
        assert props.collections == []
        assert props.collection_sequences == {}

    # --- v14: YL with :CHAPTER/POSITION sequence parsing ---

    def test_parse_yl_with_sequence(self) -> None:
        """YL with slug:CHAPTER/POSITION should extract sequence info."""
        sgf = "(;GM[1]FF[4]SZ[9]PL[B]YV[14]YG[beginner]YL[cho-elementary:3/12]AB[dd];B[ee])"
        game = parse_sgf(sgf)
        assert game.yengo_props.collections == ["cho-elementary"]
        assert game.yengo_props.collection_sequences == {"cho-elementary": ("3", 12)}

    def test_parse_yl_mixed_bare_and_sequenced(self) -> None:
        """YL with both bare slugs and sequenced entries."""
        sgf = "(;GM[1]FF[4]SZ[9]PL[B]YV[14]YG[beginner]YL[life-and-death,cho-elementary:1/5]AB[dd];B[ee])"
        game = parse_sgf(sgf)
        assert sorted(game.yengo_props.collections) == ["cho-elementary", "life-and-death"]
        assert game.yengo_props.collection_sequences == {"cho-elementary": ("1", 5)}

    def test_parse_yl_bare_slug_has_no_sequence(self) -> None:
        """Bare slugs should not appear in collection_sequences."""
        sgf = "(;GM[1]FF[4]SZ[9]PL[B]YV[14]YG[beginner]YL[life-and-death]AB[dd];B[ee])"
        game = parse_sgf(sgf)
        assert game.yengo_props.collections == ["life-and-death"]
        assert game.yengo_props.collection_sequences == {}

    def test_parse_yl_multiple_sequenced_entries(self) -> None:
        """Multiple collections can each have their own sequence."""
        sgf = "(;GM[1]FF[4]SZ[9]PL[B]YV[14]YG[beginner]YL[col-a:2/3,col-b:1/7]AB[dd];B[ee])"
        game = parse_sgf(sgf)
        assert sorted(game.yengo_props.collections) == ["col-a", "col-b"]
        assert game.yengo_props.collection_sequences == {
            "col-a": ("2", 3),
            "col-b": ("1", 7),
        }

    def test_parse_yl_dashed_chapter(self) -> None:
        """Dashed chapter names like 'intro-a' should parse correctly with / separator."""
        sgf = "(;GM[1]FF[4]SZ[9]PL[B]YV[14]YG[beginner]YL[col-x:intro-a/5]AB[dd];B[ee])"
        game = parse_sgf(sgf)
        assert game.yengo_props.collections == ["col-x"]
        assert game.yengo_props.collection_sequences == {"col-x": ("intro-a", 5)}

    def test_parse_yl_position_only(self) -> None:
        """Position-only format (slug:N, no chapter) should use empty chapter."""
        sgf = "(;GM[1]FF[4]SZ[9]PL[B]YV[14]YG[beginner]YL[col-x:12]AB[dd];B[ee])"
        game = parse_sgf(sgf)
        assert game.yengo_props.collections == ["col-x"]
        assert game.yengo_props.collection_sequences == {"col-x": ("", 12)}

    def test_parse_yl_invalid_position_logs_warning(self, caplog) -> None:
        """Non-integer position should log a warning and skip sequence."""
        sgf = "(;GM[1]FF[4]SZ[9]PL[B]YV[14]YG[beginner]YL[col-x:abc/xyz]AB[dd];B[ee])"
        import logging
        with caplog.at_level(logging.WARNING, logger="sgf_parser"):
            game = parse_sgf(sgf)
        assert game.yengo_props.collections == ["col-x"]
        assert game.yengo_props.collection_sequences == {}
        assert "Invalid position in YL entry" in caplog.text

    def test_parse_yl_invalid_position_only_logs_warning(self, caplog) -> None:
        """Non-integer position-only value should log a warning."""
        sgf = "(;GM[1]FF[4]SZ[9]PL[B]YV[14]YG[beginner]YL[col-x:abc]AB[dd];B[ee])"
        import logging
        with caplog.at_level(logging.WARNING, logger="sgf_parser"):
            game = parse_sgf(sgf)
        assert game.yengo_props.collections == ["col-x"]
        assert game.yengo_props.collection_sequences == {}
        assert "Invalid YL sequence format" in caplog.text


# =============================================================================
# T029: YL Serialization
# =============================================================================


class TestYLSerialization:
    """Tests for YL[] serialization in SGFBuilder."""

    def test_build_with_single_collection(self) -> None:
        """Builder with one collection should output YL[slug]."""
        builder = SGFBuilder(board_size=9)
        builder.set_player_to_move(Color.BLACK)
        builder.add_black_stone(Point(3, 3))
        builder.set_level_slug("beginner")
        builder.set_version(10)
        builder.add_collection("essential-life-and-death")
        builder.add_solution_move(Color.BLACK, Point(4, 4))

        sgf = builder.build()
        assert "YL[essential-life-and-death]" in sgf

    def test_build_with_multiple_collections(self) -> None:
        """Builder with multiple collections should output sorted, deduplicated YL."""
        builder = SGFBuilder(board_size=9)
        builder.set_player_to_move(Color.BLACK)
        builder.add_black_stone(Point(3, 3))
        builder.set_level_slug("beginner")
        builder.set_version(10)
        builder.add_collection("tesuji-training")
        builder.add_collection("ko-problems")
        builder.add_solution_move(Color.BLACK, Point(4, 4))

        sgf = builder.build()
        assert "YL[ko-problems,tesuji-training]" in sgf

    def test_build_without_collections(self) -> None:
        """Builder with no collections should omit YL property."""
        builder = SGFBuilder(board_size=9)
        builder.set_player_to_move(Color.BLACK)
        builder.add_black_stone(Point(3, 3))
        builder.set_level_slug("beginner")
        builder.set_version(10)
        builder.add_solution_move(Color.BLACK, Point(4, 4))

        sgf = builder.build()
        assert "YL[" not in sgf

    def test_set_collections_replaces(self) -> None:
        """set_collections() should replace existing collections."""
        builder = SGFBuilder(board_size=9)
        builder.add_collection("old-collection")
        builder.set_collections(["new-one", "new-two"])

        assert builder.yengo_props.collections == ["new-one", "new-two"]

    def test_add_collection_deduplicates(self) -> None:
        """add_collection() should not add duplicate slugs."""
        builder = SGFBuilder(board_size=9)
        builder.add_collection("ko-problems")
        builder.add_collection("ko-problems")

        assert builder.yengo_props.collections == ["ko-problems"]


# =============================================================================
# Round-trip: parse → build → parse
# =============================================================================


class TestYLRoundTrip:
    """Tests for YL[] round-trip: parse SGF → build from game → parse again."""

    def test_roundtrip_single_collection(self) -> None:
        """YL with single slug should survive a round-trip."""
        sgf = "(;GM[1]FF[4]SZ[9]PL[B]YV[10]YG[beginner]YL[essential-life-and-death]AB[dd];B[ee])"
        game = parse_sgf(sgf)

        builder = SGFBuilder.from_game(game)
        rebuilt_sgf = builder.build()

        game2 = parse_sgf(rebuilt_sgf)
        assert game2.yengo_props.collections == ["essential-life-and-death"]

    def test_roundtrip_multiple_collections(self) -> None:
        """YL with multiple slugs should survive a round-trip."""
        sgf = "(;GM[1]FF[4]SZ[9]PL[B]YV[10]YG[beginner]YL[ko-problems,tesuji-training]AB[dd];B[ee])"
        game = parse_sgf(sgf)

        builder = SGFBuilder.from_game(game)
        rebuilt_sgf = builder.build()

        game2 = parse_sgf(rebuilt_sgf)
        assert game2.yengo_props.collections == ["ko-problems", "tesuji-training"]

    def test_roundtrip_no_collections(self) -> None:
        """No YL should remain absent after round-trip."""
        sgf = "(;GM[1]FF[4]SZ[9]PL[B]YV[10]YG[beginner]AB[dd];B[ee])"
        game = parse_sgf(sgf)

        builder = SGFBuilder.from_game(game)
        rebuilt_sgf = builder.build()

        game2 = parse_sgf(rebuilt_sgf)
        assert game2.yengo_props.collections == []
        assert "YL[" not in rebuilt_sgf

    def test_roundtrip_with_chapter_position(self) -> None:
        """YL with chapter/position should survive round-trip (RC-3)."""
        sgf = "(;GM[1]FF[4]SZ[9]PL[B]YV[14]YG[beginner]YL[cho-elementary:3/12]AB[dd];B[ee])"
        game = parse_sgf(sgf)

        builder = SGFBuilder.from_game(game)
        rebuilt_sgf = builder.build()

        assert "YL[cho-elementary:3/12]" in rebuilt_sgf
        game2 = parse_sgf(rebuilt_sgf)
        assert game2.yengo_props.collections == ["cho-elementary"]
        assert game2.yengo_props.collection_sequences == {"cho-elementary": ("3", 12)}

    def test_roundtrip_position_only(self) -> None:
        """YL with position-only should survive round-trip."""
        sgf = "(;GM[1]FF[4]SZ[9]PL[B]YV[14]YG[beginner]YL[col-x:12]AB[dd];B[ee])"
        game = parse_sgf(sgf)

        builder = SGFBuilder.from_game(game)
        rebuilt_sgf = builder.build()

        assert "YL[col-x:12]" in rebuilt_sgf
        game2 = parse_sgf(rebuilt_sgf)
        assert game2.yengo_props.collection_sequences == {"col-x": ("", 12)}

    def test_roundtrip_dashed_chapter(self) -> None:
        """YL with dashed chapter name should survive round-trip."""
        sgf = "(;GM[1]FF[4]SZ[9]PL[B]YV[14]YG[beginner]YL[col-x:intro-a/5]AB[dd];B[ee])"
        game = parse_sgf(sgf)

        builder = SGFBuilder.from_game(game)
        rebuilt_sgf = builder.build()

        assert "YL[col-x:intro-a/5]" in rebuilt_sgf
        game2 = parse_sgf(rebuilt_sgf)
        assert game2.yengo_props.collection_sequences == {"col-x": ("intro-a", 5)}

    def test_roundtrip_mixed_bare_and_sequenced(self) -> None:
        """Mixed bare slugs and sequenced entries survive round-trip."""
        sgf = "(;GM[1]FF[4]SZ[9]PL[B]YV[14]YG[beginner]YL[life-and-death,cho-elementary:1/5]AB[dd];B[ee])"
        game = parse_sgf(sgf)

        builder = SGFBuilder.from_game(game)
        rebuilt_sgf = builder.build()

        game2 = parse_sgf(rebuilt_sgf)
        assert sorted(game2.yengo_props.collections) == ["cho-elementary", "life-and-death"]
        assert game2.yengo_props.collection_sequences == {"cho-elementary": ("1", 5)}


# =============================================================================
# RC-1: Natural chapter sort + RC-5: Deterministic tiebreaker
# =============================================================================


class TestSequenceSorting:
    """Tests for publish-stage sort helpers."""

    def test_chapter_sort_key_empty(self) -> None:
        """Empty chapter (position-only) sorts first."""
        from backend.puzzle_manager.stages.publish import _chapter_sort_key
        assert _chapter_sort_key("") < _chapter_sort_key("1")

    def test_chapter_sort_key_numeric_natural(self) -> None:
        """Numeric chapters sort by integer value, not lexicographic."""
        from backend.puzzle_manager.stages.publish import _chapter_sort_key
        assert _chapter_sort_key("2") < _chapter_sort_key("10")

    def test_chapter_sort_key_named_after_numeric(self) -> None:
        """Named chapters sort after numeric chapters."""
        from backend.puzzle_manager.stages.publish import _chapter_sort_key
        assert _chapter_sort_key("10") < _chapter_sort_key("intro")

    def test_sequence_sort_key_ordering(self) -> None:
        """Full sequence sort: empty < numeric < named, then by position."""
        from backend.puzzle_manager.stages.publish import _sequence_sort_key
        seqs = [("intro", 1), ("2", 5), ("", 3), ("1", 10), ("1", 2)]
        sorted_seqs = sorted(seqs, key=_sequence_sort_key)
        assert sorted_seqs == [("", 3), ("1", 2), ("1", 10), ("2", 5), ("intro", 1)]


# =============================================================================
# T030: Collection view index generation
# =============================================================================
# NOTE: TestCollectionViewGeneration removed (C4 audit cleanup).
# Collection view generation is now tested via SQLite database tests in
# test_db_builder.py and test_publish_db_wiring.py.
# The maintenance/views.py module (which produced incompatible flat files)
# has been deleted as dead code.


# =============================================================================
# T033: Schema version
# =============================================================================


class TestSchemaVersion:
    """Tests for SGF schema version bump to 13."""

    def test_schema_file_version_is_13(self) -> None:
        """config/schemas/sgf-properties.schema.json should be at version 14."""
        schema_path = Path("config/schemas/sgf-properties.schema.json")
        if not schema_path.exists():
            # Try absolute path
            schema_path = Path(__file__).parents[4] / "config" / "schemas" / "sgf-properties.schema.json"

        data = json.loads(schema_path.read_text(encoding="utf-8"))
        assert data["schema_version"] == 15

    def test_schema_has_yl_definition(self) -> None:
        """Schema should define YL property."""
        schema_path = Path("config/schemas/sgf-properties.schema.json")
        if not schema_path.exists():
            schema_path = Path(__file__).parents[4] / "config" / "schemas" / "sgf-properties.schema.json"

        data = json.loads(schema_path.read_text(encoding="utf-8"))
        assert "YL" in data["definitions"]
        assert data["definitions"]["YL"]["added_in_version"] == 10

    def test_schema_has_ym_definition(self) -> None:
        """Schema should define YM property (v12)."""
        schema_path = Path("config/schemas/sgf-properties.schema.json")
        if not schema_path.exists():
            schema_path = Path(__file__).parents[4] / "config" / "schemas" / "sgf-properties.schema.json"

        data = json.loads(schema_path.read_text(encoding="utf-8"))
        assert "YM" in data["definitions"]
        assert data["definitions"]["YM"]["added_in_version"] == 12

    def test_get_yengo_sgf_version_returns_15(self) -> None:
        """get_yengo_sgf_version() should return 15."""
        from backend.puzzle_manager.core.schema import get_yengo_sgf_version
        assert get_yengo_sgf_version() == 15


# =============================================================================
# T026: config/collections.json structure
# =============================================================================


class TestCollectionsConfig:
    """Tests for config/collections.json structure."""

    @pytest.fixture
    def collections_data(self) -> dict:
        """Load config/collections.json."""
        path = Path("config/collections.json")
        if not path.exists():
            path = Path(__file__).parents[4] / "config" / "collections.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def test_has_version(self, collections_data: dict) -> None:
        assert collections_data["schema_version"] == "5.0"

    def test_has_collections_list(self, collections_data: dict) -> None:
        assert isinstance(collections_data["collections"], list)

    def test_has_50_plus_collections(self, collections_data: dict) -> None:
        """Should have >=50 collections after v2.0 taxonomy overhaul."""
        count = len(collections_data["collections"])
        assert count >= 50, f"Expected ≥50 collections, got {count}"

    def test_each_collection_has_required_fields(self, collections_data: dict) -> None:
        required = {"slug", "name", "description", "curator", "source", "type", "ordering"}
        for c in collections_data["collections"]:
            missing = required - set(c.keys())
            assert not missing, f"Collection '{c.get('slug', '?')}' missing: {missing}"

    def test_slug_format(self, collections_data: dict) -> None:
        """Slugs should be kebab-case."""
        import re
        for c in collections_data["collections"]:
            assert re.match(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$", c["slug"]), \
                f"Invalid slug format: {c['slug']}"

    def test_valid_types(self, collections_data: dict) -> None:
        valid_types = {"author", "reference", "graded", "technique", "system"}
        for c in collections_data["collections"]:
            assert c["type"] in valid_types, f"Invalid type '{c['type']}' for {c['slug']}"

    def test_valid_ordering(self, collections_data: dict) -> None:
        valid_orderings = {"source", "difficulty", "manual"}
        for c in collections_data["collections"]:
            assert c["ordering"] in valid_orderings, f"Invalid ordering '{c['ordering']}' for {c['slug']}"

    def test_unique_slugs(self, collections_data: dict) -> None:
        slugs = [c["slug"] for c in collections_data["collections"]]
        assert len(slugs) == len(set(slugs)), "Duplicate slugs found"

    def test_aliases_format(self, collections_data: dict) -> None:
        """When present, aliases must be a list of non-empty strings."""
        for c in collections_data["collections"]:
            aliases = c.get("aliases", [])
            assert isinstance(aliases, list), f"aliases must be list for {c['slug']}"
            for alias in aliases:
                assert isinstance(alias, str), f"alias must be string in {c['slug']}"
                assert len(alias) > 0, f"empty alias in {c['slug']}"

    def test_alias_global_uniqueness(self, collections_data: dict) -> None:
        """No alias may appear in two different collections."""
        seen: dict[str, str] = {}
        for c in collections_data["collections"]:
            for alias in c.get("aliases", []):
                key = alias.lower()
                assert key not in seen, (
                    f"Alias '{alias}' duplicated in '{c['slug']}' and '{seen[key]}'"
                )
                seen[key] = c["slug"]

    def test_author_type_has_named_curator(self, collections_data: dict) -> None:
        """When type=='author', curator must be a real name, not 'Curated' or 'System'."""
        for c in collections_data["collections"]:
            if c["type"] == "author":
                assert c["curator"] not in ("Curated", "System"), (
                    f"Author collection '{c['slug']}' has curator '{c['curator']}'"
                )

    def test_no_source_branded_slugs(self, collections_data: dict) -> None:
        """No source-branded collection slugs should remain."""
        banned = {"ogs-collection", "goproblems-collection", "tsumegodragon-collection"}
        slugs = {c["slug"] for c in collections_data["collections"]}
        overlap = slugs & banned
        assert not overlap, f"Source-branded slugs found: {overlap}"

    def test_graded_essentials_naming(self, collections_data: dict) -> None:
        """Graded collections use *-essentials pattern with ordering 'manual'."""
        for c in collections_data["collections"]:
            if c["type"] == "graded":
                assert c["slug"].endswith("-essentials"), (
                    f"Graded collection '{c['slug']}' must use *-essentials naming"
                )
                assert c["ordering"] == "manual", (
                    f"Graded collection '{c['slug']}' must have ordering 'manual'"
                )

    def test_slug_pattern_valid(self, collections_data: dict) -> None:
        """All slugs match ^[a-z0-9][a-z0-9-]*[a-z0-9]$ with max 64 chars."""
        import re
        pattern = re.compile(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$")
        for c in collections_data["collections"]:
            slug = c["slug"]
            assert len(slug) <= 64, f"Slug too long ({len(slug)}): {slug}"
            assert pattern.match(slug), f"Invalid slug pattern: {slug}"


# =============================================================================
# T025: collections.schema.json existence
# =============================================================================


class TestCollectionsSchema:
    """Tests for config/schemas/collections.schema.json existence."""

    def test_schema_file_exists(self) -> None:
        path = Path("config/schemas/collections.schema.json")
        if not path.exists():
            path = Path(__file__).parents[4] / "config" / "schemas" / "collections.schema.json"
        assert path.exists()

    def test_schema_defines_collection(self) -> None:
        path = Path("config/schemas/collections.schema.json")
        if not path.exists():
            path = Path(__file__).parents[4] / "config" / "schemas" / "collections.schema.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        assert "Collection" in data["definitions"]
        assert "slug" in data["definitions"]["Collection"]["properties"]
