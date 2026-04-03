"""Unit tests for quality dimension in IdMaps.

Plan V2 Task: V2-T13A — Quality dimension backend integration.
"""

import json

import pytest

from backend.puzzle_manager.core.id_maps import (
    IdMaps,
    _build_quality_maps,
    _default_quality_id_to_slug,
    _default_quality_slug_to_id,
)


class TestDefaultQualityMaps:
    """Test default quality maps when config is unavailable."""

    def test_slug_to_id_has_all_levels(self):
        maps = _default_quality_slug_to_id()
        assert maps["unassigned"] == 0
        assert maps["unverified"] == 1
        assert maps["basic"] == 2
        assert maps["standard"] == 3
        assert maps["high"] == 4
        assert maps["premium"] == 5

    def test_id_to_slug_has_all_levels(self):
        maps = _default_quality_id_to_slug()
        assert maps[0] == "unassigned"
        assert maps[1] == "unverified"
        assert maps[2] == "basic"
        assert maps[3] == "standard"
        assert maps[4] == "high"
        assert maps[5] == "premium"

    def test_bidirectional_roundtrip(self):
        s2i = _default_quality_slug_to_id()
        i2s = _default_quality_id_to_slug()
        for slug, id_ in s2i.items():
            assert i2s[id_] == slug


class TestBuildQualityMaps:
    """Test _build_quality_maps from config file."""

    def test_from_valid_config(self, tmp_path):
        config = {
            "levels": {
                "1": {"name": "unverified", "label": "Unverified"},
                "2": {"name": "basic", "label": "Basic"},
                "3": {"name": "standard", "label": "Standard"},
                "4": {"name": "high", "label": "High"},
                "5": {"name": "premium", "label": "Premium"},
            }
        }
        path = tmp_path / "puzzle-quality.json"
        path.write_text(json.dumps(config), encoding="utf-8")

        s2i, i2s, i2n = _build_quality_maps(path)

        assert s2i["unassigned"] == 0  # Always present
        assert s2i["unverified"] == 1
        assert s2i["premium"] == 5
        assert i2s[0] == "unassigned"
        assert i2s[5] == "premium"
        assert i2n[0] == "Unassigned"

    def test_unassigned_always_included(self, tmp_path):
        config = {"levels": {"3": {"name": "standard"}}}
        path = tmp_path / "puzzle-quality.json"
        path.write_text(json.dumps(config), encoding="utf-8")

        s2i, i2s, _i2n = _build_quality_maps(path)

        assert s2i["unassigned"] == 0
        assert i2s[0] == "unassigned"

    def test_empty_levels_still_has_unassigned(self, tmp_path):
        config = {"levels": {}}
        path = tmp_path / "puzzle-quality.json"
        path.write_text(json.dumps(config), encoding="utf-8")

        s2i, i2s, _i2n = _build_quality_maps(path)

        assert len(s2i) == 1
        assert s2i["unassigned"] == 0

    def test_non_integer_key_skipped(self, tmp_path):
        config = {"levels": {"abc": {"name": "bad"}}}
        path = tmp_path / "puzzle-quality.json"
        path.write_text(json.dumps(config), encoding="utf-8")

        s2i, i2s, _i2n = _build_quality_maps(path)

        assert "bad" not in s2i
        assert len(s2i) == 1  # Only unassigned


class TestIdMapsQualityIntegration:
    """Test quality lookups on IdMaps instance."""

    @pytest.fixture
    def maps_with_quality(self):
        return IdMaps(
            level_slug_to_id_map={"novice": 110},
            level_id_to_slug_map={110: "novice"},
            tag_slug_to_id_map={"ladder": 34},
            tag_id_to_slug_map={34: "ladder"},
            collection_slug_to_id_map={"test": 1},
            collection_id_to_slug_map={1: "test"},
            quality_slug_to_id_map={"unassigned": 0, "standard": 3, "high": 4},
            quality_id_to_slug_map={0: "unassigned", 3: "standard", 4: "high"},
        )

    def test_quality_slug_to_id(self, maps_with_quality):
        assert maps_with_quality.quality_slug_to_id("standard") == 3

    def test_quality_id_to_slug(self, maps_with_quality):
        assert maps_with_quality.quality_id_to_slug(3) == "standard"

    def test_quality_slug_to_id_raises_for_unknown(self, maps_with_quality):
        with pytest.raises(KeyError):
            maps_with_quality.quality_slug_to_id("nonexistent")

    def test_quality_slug_to_id_safe_returns_none(self, maps_with_quality):
        assert maps_with_quality.quality_slug_to_id_safe("nonexistent") is None

    def test_quality_id_to_slug_safe_returns_none(self, maps_with_quality):
        assert maps_with_quality.quality_id_to_slug_safe(99) is None


class TestIdMapsDefaultQuality:
    """Test that IdMaps uses defaults when quality maps are omitted."""

    def test_default_quality_when_none(self):
        maps = IdMaps(
            level_slug_to_id_map={},
            level_id_to_slug_map={},
            tag_slug_to_id_map={},
            tag_id_to_slug_map={},
            collection_slug_to_id_map={},
            collection_id_to_slug_map={},
        )
        assert maps.quality_slug_to_id("standard") == 3
        assert maps.quality_id_to_slug(3) == "standard"

    def test_backward_compat_positional_args(self):
        """Existing code passes 6 positional args — quality should default."""
        maps = IdMaps(
            {"novice": 110}, {110: "novice"},
            {"ladder": 34}, {34: "ladder"},
            {"test": 1}, {1: "test"},
        )
        assert maps.quality_slug_to_id("unassigned") == 0


class TestIdMapsLoadQuality:
    """Test that IdMaps.load() picks up quality config."""

    def test_load_with_quality_config(self, tmp_path):
        # Create minimal config dir
        levels = {"levels": [{"slug": "novice", "id": 110}]}
        tags = {"tags": {"ladder": {"id": 34}}}
        collections = {"collections": [{"slug": "test", "id": 1}]}
        quality = {
            "levels": {
                "1": {"name": "unverified"},
                "2": {"name": "basic"},
                "3": {"name": "standard"},
            }
        }
        (tmp_path / "puzzle-levels.json").write_text(json.dumps(levels), encoding="utf-8")
        (tmp_path / "tags.json").write_text(json.dumps(tags), encoding="utf-8")
        (tmp_path / "collections.json").write_text(json.dumps(collections), encoding="utf-8")
        (tmp_path / "puzzle-quality.json").write_text(json.dumps(quality), encoding="utf-8")

        maps = IdMaps.load(config_dir=tmp_path)

        assert maps.quality_slug_to_id("standard") == 3
        assert maps.quality_id_to_slug(0) == "unassigned"

    def test_load_without_quality_file_uses_defaults(self, tmp_path):
        levels = {"levels": [{"slug": "novice", "id": 110}]}
        tags = {"tags": {"ladder": {"id": 34}}}
        collections = {"collections": [{"slug": "test", "id": 1}]}
        (tmp_path / "puzzle-levels.json").write_text(json.dumps(levels), encoding="utf-8")
        (tmp_path / "tags.json").write_text(json.dumps(tags), encoding="utf-8")
        (tmp_path / "collections.json").write_text(json.dumps(collections), encoding="utf-8")

        maps = IdMaps.load(config_dir=tmp_path)

        assert maps.quality_slug_to_id("premium") == 5
