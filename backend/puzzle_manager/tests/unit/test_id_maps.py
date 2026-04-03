"""Unit tests for core/id_maps.py — numeric ID maps, parse_yx, parse_yx_full, build_batch_ref."""


import pytest

from backend.puzzle_manager.core.id_maps import (
    IdMaps,
    build_batch_ref,
    parse_yx,
    parse_yx_full,
)


@pytest.mark.unit
class TestParseYx:
    """Tests for parse_yx() helper."""

    def test_standard_yx_string(self) -> None:
        assert parse_yx("d:3;r:2;s:19;u:1") == [3, 2, 19, 1]

    def test_none_returns_zeros(self) -> None:
        assert parse_yx(None) == [0, 0, 0, 0]

    def test_empty_string_returns_zeros(self) -> None:
        assert parse_yx("") == [0, 0, 0, 0]

    def test_partial_yx(self) -> None:
        result = parse_yx("d:5;r:3")
        assert result == [5, 3, 0, 0]

    def test_order_independent(self) -> None:
        assert parse_yx("s:19;u:1;d:3;r:2") == [3, 2, 19, 1]

    def test_malformed_returns_zeros(self) -> None:
        assert parse_yx("garbage") == [0, 0, 0, 0]

    def test_a_field_tolerated_but_excluded(self) -> None:
        """parse_yx should tolerate 'a' field but NOT include it in output."""
        assert parse_yx("d:3;r:2;s:19;u:1;a:2") == [3, 2, 19, 1]

    def test_a_field_with_partial_yx(self) -> None:
        """'a' field should be ignored even with partial input."""
        result = parse_yx("d:5;a:3")
        assert result == [5, 0, 0, 0]


@pytest.mark.unit
class TestParseYxFull:
    """Tests for parse_yx_full() helper."""

    def test_all_fields_returned(self) -> None:
        result = parse_yx_full("d:3;r:2;s:19;u:1;a:2")
        assert result == {"d": 3, "r": 2, "s": 19, "u": 1, "a": 2}

    def test_without_a_defaults_to_zero(self) -> None:
        result = parse_yx_full("d:3;r:2;s:19;u:1")
        assert result["a"] == 0

    def test_none_returns_all_zeros(self) -> None:
        result = parse_yx_full(None)
        assert result == {"d": 0, "r": 0, "s": 0, "u": 0, "a": 0}

    def test_empty_returns_all_zeros(self) -> None:
        result = parse_yx_full("")
        assert result == {"d": 0, "r": 0, "s": 0, "u": 0, "a": 0}

    def test_partial_returns_defaults(self) -> None:
        result = parse_yx_full("d:5;a:3")
        assert result["d"] == 5
        assert result["a"] == 3
        assert result["r"] == 0


@pytest.mark.unit
class TestBuildBatchRef:
    """Tests for build_batch_ref() helper."""

    def test_flat_batch_path(self) -> None:
        assert build_batch_ref("sgf/0001/fc38f029205dde14.sgf") == "0001/fc38f029205dde14"

    def test_legacy_level_path(self) -> None:
        # Legacy format: sgf/{level}/batch-{NNNN}/{hash}.sgf
        assert build_batch_ref("sgf/beginner/batch-0001/abc123def4567890.sgf") == "0001/abc123def4567890"

    def test_high_batch_number(self) -> None:
        assert build_batch_ref("sgf/0042/deadbeef12345678.sgf") == "0042/deadbeef12345678"


@pytest.mark.unit
class TestIdMaps:
    """Tests for IdMaps loaded from config files."""

    @pytest.fixture
    def id_maps(self) -> IdMaps:
        """Load ID maps from actual config files."""
        return IdMaps.load()

    def test_level_slug_to_id_novice(self, id_maps: IdMaps) -> None:
        assert id_maps.level_slug_to_id("novice") == 110

    def test_level_slug_to_id_expert(self, id_maps: IdMaps) -> None:
        assert id_maps.level_slug_to_id("expert") == 230

    def test_level_slug_to_id_intermediate(self, id_maps: IdMaps) -> None:
        assert id_maps.level_slug_to_id("intermediate") == 140

    def test_level_id_to_slug(self, id_maps: IdMaps) -> None:
        assert id_maps.level_id_to_slug(130) == "elementary"

    def test_level_slug_to_id_unknown_raises(self, id_maps: IdMaps) -> None:
        with pytest.raises(KeyError):
            id_maps.level_slug_to_id("nonexistent")

    def test_level_slug_to_id_safe_returns_none(self, id_maps: IdMaps) -> None:
        assert id_maps.level_slug_to_id_safe("nonexistent") is None

    def test_tag_slug_to_id_ladder(self, id_maps: IdMaps) -> None:
        assert id_maps.tag_slug_to_id("ladder") == 34

    def test_tag_slug_to_id_life_and_death(self, id_maps: IdMaps) -> None:
        assert id_maps.tag_slug_to_id("life-and-death") == 10

    def test_tag_id_to_slug(self, id_maps: IdMaps) -> None:
        assert id_maps.tag_id_to_slug(36) == "net"

    def test_tag_slugs_to_ids_sorted(self, id_maps: IdMaps) -> None:
        result = id_maps.tag_slugs_to_ids(["net", "ladder", "ko"])
        assert result == [12, 34, 36]  # sorted by numeric ID

    def test_tag_slugs_to_ids_unknown_skipped(self, id_maps: IdMaps) -> None:
        result = id_maps.tag_slugs_to_ids(["ladder", "fake-tag"])
        assert result == [34]

    def test_collection_slug_to_id(self, id_maps: IdMaps) -> None:
        # First collection in collections.json
        assert id_maps.collection_slug_to_id("advanced-essentials") == 1

    def test_collection_slugs_to_ids(self, id_maps: IdMaps) -> None:
        result = id_maps.collection_slugs_to_ids(["beginner-essentials", "advanced-essentials"])
        assert result == [1, 2]  # sorted by numeric ID

    def test_all_9_levels_have_ids(self, id_maps: IdMaps) -> None:
        expected = {
            "novice": 110, "beginner": 120, "elementary": 130,
            "intermediate": 140, "upper-intermediate": 150, "advanced": 160,
            "low-dan": 210, "high-dan": 220, "expert": 230,
        }
        for slug, expected_id in expected.items():
            assert id_maps.level_slug_to_id(slug) == expected_id

    def test_all_28_tags_have_ids(self, id_maps: IdMaps) -> None:
        # Objectives
        assert id_maps.tag_slug_to_id("life-and-death") == 10
        assert id_maps.tag_slug_to_id("ko") == 12
        assert id_maps.tag_slug_to_id("living") == 14
        assert id_maps.tag_slug_to_id("seki") == 16
        # Tesuji (sampled)
        assert id_maps.tag_slug_to_id("snapback") == 30
        assert id_maps.tag_slug_to_id("tesuji") == 52
        # Techniques (sampled)
        assert id_maps.tag_slug_to_id("capture-race") == 60
        assert id_maps.tag_slug_to_id("fuseki") == 82

    def test_resolve_dimension_label_level(self, id_maps: IdMaps) -> None:
        assert id_maps.resolve_dimension_label("l", 120) == "Beginner"
        assert id_maps.resolve_dimension_label("l", 130) == "Elementary"
        assert id_maps.resolve_dimension_label("l", 110) == "Novice"

    def test_resolve_dimension_label_tag(self, id_maps: IdMaps) -> None:
        assert id_maps.resolve_dimension_label("t", 10) == "Life & Death"
        assert id_maps.resolve_dimension_label("t", 36) == "Net"

    def test_resolve_dimension_label_collection(self, id_maps: IdMaps) -> None:
        label = id_maps.resolve_dimension_label("c", 6)
        assert "Cho Chikun" in label  # "Cho Chikun Life & Death: Elementary"

    def test_resolve_dimension_label_quality(self, id_maps: IdMaps) -> None:
        # Quality names are loaded from puzzle-quality.json
        label = id_maps.resolve_dimension_label("q", 3)
        assert isinstance(label, str)
        assert len(label) > 0

    def test_resolve_dimension_label_unknown_falls_back(self, id_maps: IdMaps) -> None:
        assert id_maps.resolve_dimension_label("l", 999) == "l999"
        assert id_maps.resolve_dimension_label("t", 999) == "t999"

    def test_resolve_dimension_label_unknown_prefix(self, id_maps: IdMaps) -> None:
        assert id_maps.resolve_dimension_label("z", 42) == "z42"
