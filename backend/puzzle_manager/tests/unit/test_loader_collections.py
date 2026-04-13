"""Tests for collection loader functions in ConfigLoader.

Tests: load_collections, get_collection_slugs, get_collection_aliases,
       resolve_collection_alias, and alias collision detection.
"""

from unittest.mock import patch

import pytest

from backend.puzzle_manager.config.loader import ConfigLoader
from backend.puzzle_manager.exceptions import (
    ConfigValidationError,
)


@pytest.fixture
def loader() -> ConfigLoader:
    """Create a ConfigLoader instance."""
    return ConfigLoader()


class TestLoadCollections:
    """T024: Tests for load_collections()."""

    def test_load_collections_returns_dict(self, loader: ConfigLoader) -> None:
        """load_collections() returns a dict with version and collections keys."""
        data = loader.load_collections()
        assert isinstance(data, dict)
        assert "schema_version" in data
        assert "collections" in data

    def test_load_collections_has_version(self, loader: ConfigLoader) -> None:
        data = loader.load_collections()
        assert data["schema_version"] == "5.0"

    def test_load_collections_has_entries(self, loader: ConfigLoader) -> None:
        data = loader.load_collections()
        assert len(data["collections"]) >= 50

    def test_load_collections_all_have_tier(self, loader: ConfigLoader) -> None:
        """Every collection entry must have a tier field."""
        data = loader.load_collections()
        valid_tiers = {"editorial", "premier", "curated", "community", "reference"}
        for coll in data["collections"]:
            assert "tier" in coll, f"Collection '{coll['slug']}' missing tier field"
            assert coll["tier"] in valid_tiers, (
                f"Collection '{coll['slug']}' has invalid tier '{coll['tier']}'"
            )


class TestGetCollectionSlugs:
    """T025: Tests for get_collection_slugs()."""

    def test_returns_list(self, loader: ConfigLoader) -> None:
        slugs = loader.get_collection_slugs()
        assert isinstance(slugs, list)

    def test_returns_50_plus_slugs(self, loader: ConfigLoader) -> None:
        slugs = loader.get_collection_slugs()
        assert len(slugs) >= 50

    def test_all_valid_strings(self, loader: ConfigLoader) -> None:
        slugs = loader.get_collection_slugs()
        for slug in slugs:
            assert isinstance(slug, str)
            assert len(slug) > 0

    def test_known_slug_present(self, loader: ConfigLoader) -> None:
        slugs = loader.get_collection_slugs()
        assert "gokyo-shumyo" in slugs
        assert "ladder-problems" in slugs


class TestGetCollectionAliases:
    """T026: Tests for get_collection_aliases()."""

    def test_returns_dict(self, loader: ConfigLoader) -> None:
        aliases = loader.get_collection_aliases()
        assert isinstance(aliases, dict)

    def test_slug_self_resolution(self, loader: ConfigLoader) -> None:
        """Slugs should self-resolve in the alias map."""
        aliases = loader.get_collection_aliases()
        assert aliases["gokyo-shumyo"] == "gokyo-shumyo"
        assert aliases["ladder-problems"] == "ladder-problems"

    def test_japanese_alias_present(self, loader: ConfigLoader) -> None:
        aliases = loader.get_collection_aliases()
        # 碁経衆妙 → gokyo-shumyo
        assert "碁経衆妙" in aliases
        assert aliases["碁経衆妙"] == "gokyo-shumyo"

    def test_all_values_are_valid_slugs(self, loader: ConfigLoader) -> None:
        aliases = loader.get_collection_aliases()
        slugs = set(loader.get_collection_slugs())
        for alias, slug in aliases.items():
            assert slug in slugs, f"Alias '{alias}' maps to unknown slug '{slug}'"


class TestResolveCollectionAlias:
    """T027: Tests for resolve_collection_alias()."""

    def test_japanese_alias_resolves(self, loader: ConfigLoader) -> None:
        result = loader.resolve_collection_alias("碁経衆妙")
        assert result == "gokyo-shumyo"

    def test_slug_self_resolves(self, loader: ConfigLoader) -> None:
        result = loader.resolve_collection_alias("gokyo-shumyo")
        assert result == "gokyo-shumyo"

    def test_unknown_returns_none(self, loader: ConfigLoader) -> None:
        result = loader.resolve_collection_alias("nonexistent-thing")
        assert result is None

    def test_case_insensitive(self, loader: ConfigLoader) -> None:
        result = loader.resolve_collection_alias("HATSUYORON")
        assert result == "igo-hatsuyoron"

    def test_empty_string_returns_none(self, loader: ConfigLoader) -> None:
        result = loader.resolve_collection_alias("")
        assert result is None

    def test_english_alias_resolves(self, loader: ConfigLoader) -> None:
        result = loader.resolve_collection_alias("shicho")
        assert result == "ladder-problems"


class TestAliasCollisionDetection:
    """T028: Tests for alias uniqueness validation."""

    def test_duplicate_alias_raises_error(self, loader: ConfigLoader) -> None:
        """If two collections share an alias, ConfigValidationError is raised."""
        fake_config = {
            "schema_version": "2.0",
            "collections": [
                {
                    "slug": "collection-a",
                    "name": "A",
                    "description": "A",
                    "curator": "Curated",
                    "source": "mixed",
                    "type": "technique",
                    "ordering": "difficulty",
                    "aliases": ["shared-alias"],
                },
                {
                    "slug": "collection-b",
                    "name": "B",
                    "description": "B",
                    "curator": "Curated",
                    "source": "mixed",
                    "type": "technique",
                    "ordering": "difficulty",
                    "aliases": ["shared-alias"],
                },
            ],
        }

        with patch.object(loader, "load_collections", return_value=fake_config):
            with pytest.raises(ConfigValidationError, match="shared-alias"):
                loader.get_collection_aliases()

    def test_no_collision_in_real_config(self, loader: ConfigLoader) -> None:
        """The real config should have no alias collisions."""
        # Should not raise
        aliases = loader.get_collection_aliases()
        assert len(aliases) > 0


class TestGetCollectionLevelHints:
    """Tests for collection-based level hint loading."""

    @pytest.fixture
    def loader(self) -> ConfigLoader:
        return ConfigLoader()

    def test_returns_dict(self, loader: ConfigLoader) -> None:
        hints = loader.get_collection_level_hints()
        assert isinstance(hints, dict)

    def test_has_all_nine_essentials(self, loader: ConfigLoader) -> None:
        """All 9 graded essentials should have level hints."""
        hints = loader.get_collection_level_hints()
        essentials = [
            "novice-essentials",
            "beginner-essentials",
            "elementary-essentials",
            "intermediate-essentials",
            "upper-intermediate-essentials",
            "advanced-essentials",
            "low-dan-essentials",
            "high-dan-essentials",
            "expert-essentials",
        ]
        for slug in essentials:
            assert slug in hints, f"Missing level_hint for {slug}"

    def test_essentials_match_level_slugs(self, loader: ConfigLoader) -> None:
        """Each essentials level_hint should match its slug prefix."""
        hints = loader.get_collection_level_hints()
        assert hints["novice-essentials"] == "novice"
        assert hints["beginner-essentials"] == "beginner"
        assert hints["elementary-essentials"] == "elementary"
        assert hints["intermediate-essentials"] == "intermediate"
        assert hints["upper-intermediate-essentials"] == "upper-intermediate"
        assert hints["advanced-essentials"] == "advanced"
        assert hints["low-dan-essentials"] == "low-dan"
        assert hints["high-dan-essentials"] == "high-dan"
        assert hints["expert-essentials"] == "expert"

    def test_author_collections_have_hints(self, loader: ConfigLoader) -> None:
        """Author collections with level in slug should have hints."""
        hints = loader.get_collection_level_hints()
        assert hints.get("cho-chikun-life-death-elementary") == "elementary"
        assert hints.get("cho-chikun-life-death-intermediate") == "intermediate"
        assert hints.get("cho-chikun-life-death-advanced") == "advanced"

    def test_technique_collections_no_hints(self, loader: ConfigLoader) -> None:
        """Technique collections should NOT have level hints."""
        hints = loader.get_collection_level_hints()
        technique_slugs = ["capture-problems", "ko-problems", "ladder-problems"]
        for slug in technique_slugs:
            assert slug not in hints, f"{slug} should not have a level_hint"

    def test_at_least_15_level_hints(self, loader: ConfigLoader) -> None:
        """Should have at least 15 collections with level hints (9 essentials + 6 author)."""
        hints = loader.get_collection_level_hints()
        assert len(hints) >= 15
