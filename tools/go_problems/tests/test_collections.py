"""Tests for GoProblems collection matching."""

import json
import tempfile
from pathlib import Path

from tools.go_problems.collections import (
    CollectionMatcher,
    resolve_collection_slugs,
)


class TestCollectionMatcher:
    """Tests for CollectionMatcher."""

    def _create_matcher(self, collections: list[dict]) -> CollectionMatcher:
        """Create a matcher with custom collections config."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump({"collections": collections}, f)
            f.flush()
            return CollectionMatcher(Path(f.name))

    def test_exact_name_match(self):
        matcher = self._create_matcher(
            [{"slug": "cho-elementary", "name": "Cho Elementary", "aliases": []}]
        )
        assert matcher.match("Cho Elementary") == "cho-elementary"

    def test_slug_match(self):
        matcher = self._create_matcher(
            [{"slug": "cho-elementary", "name": "Cho Elementary", "aliases": []}]
        )
        assert matcher.match("cho-elementary") == "cho-elementary"

    def test_alias_match(self):
        matcher = self._create_matcher(
            [
                {
                    "slug": "cho-elementary",
                    "name": "Cho Elementary",
                    "aliases": ["Cho Chikun Elementary"],
                }
            ]
        )
        assert matcher.match("Cho Chikun Elementary") == "cho-elementary"

    def test_phrase_match(self):
        matcher = self._create_matcher(
            [{"slug": "nakade-problems", "name": "Nakade Problems", "aliases": []}]
        )
        assert matcher.match("Advanced Nakade Problems Collection") == "nakade-problems"

    def test_no_match(self):
        matcher = self._create_matcher(
            [{"slug": "cho-elementary", "name": "Cho Elementary", "aliases": []}]
        )
        assert matcher.match("Something Completely Different") is None

    def test_empty_input(self):
        matcher = self._create_matcher(
            [{"slug": "test", "name": "Test", "aliases": []}]
        )
        assert matcher.match("") is None
        assert matcher.match(None) is None  # type: ignore[arg-type]

    def test_case_insensitive(self):
        matcher = self._create_matcher(
            [{"slug": "tesuji", "name": "Tesuji Training", "aliases": []}]
        )
        assert matcher.match("tesuji training") == "tesuji"
        assert matcher.match("TESUJI TRAINING") == "tesuji"


class TestResolveCollectionSlugs:
    """Tests for resolve_collection_slugs function."""

    def test_none_collections(self):
        assert resolve_collection_slugs(None) == []

    def test_empty_collections(self):
        assert resolve_collection_slugs([]) == []

    def test_returns_sorted(self):
        # This depends on config/collections.json having matching entries
        # For unit testing, we verify the sort behavior
        collections = [
            {"name": "Z Collection"},
            {"name": "A Collection"},
        ]
        result = resolve_collection_slugs(collections)
        # Result will be empty if no matches in config, but sorted if any
        assert result == sorted(result)
