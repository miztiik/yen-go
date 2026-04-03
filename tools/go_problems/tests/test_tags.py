"""Tests for GoProblems genre-to-tag mapping."""

from tools.go_problems.tags import (
    map_collections_to_tags,
    map_genre_to_tags,
)


class TestMapGenreToTags:
    """Tests for genre -> tag mapping."""

    def test_life_and_death(self):
        assert map_genre_to_tags("life and death") == ["life-and-death"]

    def test_life_and_death_hyphenated(self):
        assert map_genre_to_tags("life-and-death") == ["life-and-death"]

    def test_tesuji(self):
        assert map_genre_to_tags("tesuji") == ["tesuji"]

    def test_best_move_maps_to_tesuji(self):
        assert map_genre_to_tags("best move") == ["tesuji"]

    def test_endgame(self):
        assert map_genre_to_tags("endgame") == ["endgame"]

    def test_joseki(self):
        assert map_genre_to_tags("joseki") == ["joseki"]

    def test_fuseki(self):
        assert map_genre_to_tags("fuseki") == ["fuseki"]

    def test_opening_maps_to_fuseki(self):
        assert map_genre_to_tags("opening") == ["fuseki"]

    def test_none_returns_empty(self):
        assert map_genre_to_tags(None) == []

    def test_empty_string_returns_empty(self):
        assert map_genre_to_tags("") == []

    def test_unknown_genre_returns_empty(self):
        assert map_genre_to_tags("unknown_genre") == []

    def test_case_insensitive(self):
        assert map_genre_to_tags("Life And Death") == ["life-and-death"]
        assert map_genre_to_tags("TESUJI") == ["tesuji"]

    def test_no_partial_match(self):
        """Unknown genres return empty — no fuzzy guessing."""
        assert map_genre_to_tags("life and death problems") == []


class TestMapCollectionsToTags:
    """Tests for collection -> tag mapping."""

    def test_nakade_collection(self):
        collections = [{"id": 1, "name": "Nakade"}]
        assert map_collections_to_tags(collections) == ["nakade"]

    def test_connect_collection(self):
        collections = [{"id": 2, "name": "Connect"}]
        assert map_collections_to_tags(collections) == ["connection"]

    def test_unknown_collection(self):
        collections = [{"id": 3, "name": "Unknown Collection"}]
        assert map_collections_to_tags(collections) == []

    def test_none_collections(self):
        assert map_collections_to_tags(None) == []

    def test_empty_collections(self):
        assert map_collections_to_tags([]) == []

    def test_multiple_collections(self):
        collections = [
            {"id": 1, "name": "Nakade"},
            {"id": 2, "name": "Connect"},
        ]
        tags = map_collections_to_tags(collections)
        assert "nakade" in tags
        assert "connection" in tags

    def test_deduplication(self):
        collections = [
            {"id": 1, "name": "Nakade"},
            {"id": 2, "name": "Nakade"},
        ]
        tags = map_collections_to_tags(collections)
        assert tags == ["nakade"]

    def test_custom_mapping(self):
        collections = [{"id": 1, "name": "Custom"}]
        mapping = {"Custom": "custom-tag"}
        tags = map_collections_to_tags(collections, mapping=mapping)
        assert tags == ["custom-tag"]
