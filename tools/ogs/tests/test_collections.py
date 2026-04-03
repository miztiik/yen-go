"""
Tests for tools.ogs.collections module.

Tests collection name matching against config/collections.json
and multi-collection resolution via resolve_all_collection_slugs.
"""

import json
from pathlib import Path

import pytest

import tools.ogs.collections as collections_mod
from tools.ogs.collection_index import CollectionIndex
from tools.ogs.collections import (
    CollectionMatcher,
    match_collection_name,
    resolve_all_collection_slugs,
)

# ==============================
# Fixtures
# ==============================

@pytest.fixture
def sample_collections(tmp_path: Path) -> Path:
    """Create a minimal collections.json for testing."""
    config = {
        "version": "2.0",
        "collections": [
            {
                "slug": "cho-chikun-life-death-elementary",
                "name": "Cho Chikun Life & Death: Elementary",
                "aliases": [
                    "encyclopedia life and death elementary",
                    "encyclopedia life death elementary",
                    "cho elementary",
                ],
            },
            {
                "slug": "cho-chikun-life-death-intermediate",
                "name": "Cho Chikun Life & Death: Intermediate",
                "aliases": [
                    "encyclopedia life and death intermediate",
                    "cho intermediate",
                ],
            },
            {
                "slug": "tesuji-training",
                "name": "Tesuji Training",
                "aliases": ["tactical problems", "tesujis"],
            },
            {
                "slug": "gokyo-shumyo",
                "name": "Gokyo Shumyo",
                "aliases": ["shumyo", "玄妙"],
            },
        ],
    }
    path = tmp_path / "collections.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    return path


@pytest.fixture
def matcher(sample_collections: Path) -> CollectionMatcher:
    """CollectionMatcher loaded from sample config."""
    return CollectionMatcher(sample_collections)


# ==============================
# Exact Match Tests
# ==============================

class TestExactMatch:
    def test_exact_name_match(self, matcher: CollectionMatcher) -> None:
        """Exact match against a registered name."""
        assert matcher.match("Tesuji Training") == "tesuji-training"

    def test_exact_slug_match(self, matcher: CollectionMatcher) -> None:
        """Exact match against a slug."""
        assert matcher.match("gokyo-shumyo") == "gokyo-shumyo"

    def test_exact_alias_match(self, matcher: CollectionMatcher) -> None:
        """Exact match against a registered alias."""
        assert matcher.match("tactical problems") == "tesuji-training"

    def test_case_insensitive(self, matcher: CollectionMatcher) -> None:
        """Matching is case-insensitive."""
        assert matcher.match("TESUJI TRAINING") == "tesuji-training"
        assert matcher.match("tesuji training") == "tesuji-training"

    def test_cjk_alias(self, matcher: CollectionMatcher) -> None:
        """CJK alias matching works."""
        assert matcher.match("玄妙") == "gokyo-shumyo"


# ==============================
# Phrase Match Tests
# ==============================

class TestPhraseMatch:
    def test_cho_chikun_real_world(self, matcher: CollectionMatcher) -> None:
        """Real OGS collection name matches via phrase matching."""
        result = matcher.match(
            "Cho Chikun's Encyclopedia of Life and Death - Elementary"
        )
        assert result == "cho-chikun-life-death-elementary"

    def test_cho_chikun_intermediate(self, matcher: CollectionMatcher) -> None:
        """Intermediate volume matched separately from elementary."""
        result = matcher.match(
            "Cho Chikun's Encyclopedia of Life and Death - Intermediate"
        )
        assert result == "cho-chikun-life-death-intermediate"

    def test_longest_match_wins(self, matcher: CollectionMatcher) -> None:
        """More specific alias is preferred over shorter."""
        # "cho elementary" (2 tokens) vs "encyclopedia life and death elementary" (5 tokens)
        # Both match, but the longer one should win and pick the right slug
        result = matcher.match(
            "Cho Chikun's Encyclopedia of Life and Death - Elementary"
        )
        assert result == "cho-chikun-life-death-elementary"

    def test_partial_name_in_longer_text(self, matcher: CollectionMatcher) -> None:
        """Alias found as contiguous subsequence in longer input."""
        result = matcher.match("My Custom Tesuji Training Collection")
        assert result == "tesuji-training"


# ==============================
# No Match Tests
# ==============================

class TestNoMatch:
    def test_no_match_returns_none(self, matcher: CollectionMatcher) -> None:
        """Unrecognized collection returns None."""
        assert matcher.match("Completely Unknown Collection XYZ") is None

    def test_empty_string_returns_none(self, matcher: CollectionMatcher) -> None:
        """Empty string returns None."""
        assert matcher.match("") is None

    def test_none_input_returns_none(self, matcher: CollectionMatcher) -> None:
        """Empty/whitespace input returns None."""
        assert matcher.match("   ") is None


# ==============================
# Edge Cases
# ==============================

class TestEdgeCases:
    def test_missing_config_file(self, tmp_path: Path) -> None:
        """Non-existent config file results in no matches."""
        matcher = CollectionMatcher(tmp_path / "does_not_exist.json")
        assert matcher.match("anything") is None

    def test_empty_collections_list(self, tmp_path: Path) -> None:
        """Empty collections array results in no matches."""
        path = tmp_path / "empty.json"
        path.write_text('{"collections": []}', encoding="utf-8")
        matcher = CollectionMatcher(path)
        assert matcher.match("anything") is None

    def test_collection_without_aliases(self, tmp_path: Path) -> None:
        """Collection with no aliases only matches by name/slug."""
        path = tmp_path / "no_aliases.json"
        path.write_text(
            json.dumps({
                "collections": [
                    {"slug": "my-collection", "name": "My Collection"}
                ]
            }),
            encoding="utf-8",
        )
        matcher = CollectionMatcher(path)
        assert matcher.match("My Collection") == "my-collection"
        assert matcher.match("something else") is None


# ==============================
# Global Convenience Function
# ==============================

class TestConvenienceFunction:
    def test_match_collection_name_uses_global_config(self) -> None:
        """match_collection_name() loads from config/collections.json."""
        # Reset the global singleton so it loads the real config
        collections_mod._matcher = None
        try:
            result = match_collection_name(
                "Cho Chikun's Encyclopedia of Life and Death - Elementary"
            )
            # The real config has this collection, so it should match
            assert result == "cho-chikun-life-death-elementary"
        finally:
            # Reset again so other tests aren't affected
            collections_mod._matcher = None


# ==============================
# resolve_all_collection_slugs Tests
# ==============================

def _make_jsonl_content(collections: list[dict]) -> str:
    """Build JSONL content string from collection records."""
    metadata = {"type": "metadata", "total_collections": len(collections)}
    lines = [json.dumps(metadata)]
    for c in collections:
        lines.append(json.dumps(c))
    return "\n".join(lines)


@pytest.fixture
def collection_index(tmp_path: Path, sample_collections: Path) -> CollectionIndex:
    """CollectionIndex loaded from sample JSONL with known puzzle-to-collection mapping."""
    jsonl_path = tmp_path / "collections-sorted.jsonl"
    content = _make_jsonl_content([
        {
            "type": "collection",
            "id": 100,
            "name": "Cho Chikun Life & Death: Elementary",
            "puzzles": [10, 20, 30],
        },
        {
            "type": "collection",
            "id": 200,
            "name": "Tesuji Training",
            "puzzles": [20, 40],
        },
    ])
    jsonl_path.write_text(content, encoding="utf-8")
    return CollectionIndex.from_jsonl(jsonl_path)


class TestResolveAllCollectionSlugs:
    def test_api_only_source(self, matcher: CollectionMatcher) -> None:
        """When no collection_index, only API name is used."""
        slugs = resolve_all_collection_slugs(
            puzzle_id=999,
            api_collection_name="Tesuji Training",
            collection_index=None,
            matcher=matcher,
        )
        assert slugs == ["tesuji-training"]

    def test_index_only_source(
        self, matcher: CollectionMatcher, collection_index: CollectionIndex,
    ) -> None:
        """When API name is None, uses reverse index only."""
        # Puzzle 10 is in "Cho Chikun Life & Death: Elementary"
        slugs = resolve_all_collection_slugs(
            puzzle_id=10,
            api_collection_name=None,
            collection_index=collection_index,
            matcher=matcher,
        )
        assert slugs == ["cho-chikun-life-death-elementary"]

    def test_dual_source_dedup(
        self, matcher: CollectionMatcher, collection_index: CollectionIndex,
    ) -> None:
        """API name and index resolve to same slug => deduplicated."""
        # Puzzle 10 is in "Cho Chikun Life & Death: Elementary" via index
        # API also says "Cho Chikun Life & Death: Elementary"
        slugs = resolve_all_collection_slugs(
            puzzle_id=10,
            api_collection_name="Cho Chikun Life & Death: Elementary",
            collection_index=collection_index,
            matcher=matcher,
        )
        assert slugs == ["cho-chikun-life-death-elementary"]

    def test_multi_collection_puzzle(
        self, matcher: CollectionMatcher, collection_index: CollectionIndex,
    ) -> None:
        """Puzzle in multiple collections gets all slugs, sorted."""
        # Puzzle 20 is in both collections
        slugs = resolve_all_collection_slugs(
            puzzle_id=20,
            api_collection_name=None,
            collection_index=collection_index,
            matcher=matcher,
        )
        assert slugs == ["cho-chikun-life-death-elementary", "tesuji-training"]

    def test_no_matches_returns_empty(
        self, matcher: CollectionMatcher,
    ) -> None:
        """No API name and no index => empty list."""
        slugs = resolve_all_collection_slugs(
            puzzle_id=999,
            api_collection_name=None,
            collection_index=None,
            matcher=matcher,
        )
        assert slugs == []

    def test_unmatched_api_name_returns_empty(
        self, matcher: CollectionMatcher,
    ) -> None:
        """API name that doesn't match any collection => empty."""
        slugs = resolve_all_collection_slugs(
            puzzle_id=999,
            api_collection_name="Unknown Collection XYZ",
            collection_index=None,
            matcher=matcher,
        )
        assert slugs == []

    def test_result_sorted_alphabetically(
        self, matcher: CollectionMatcher, collection_index: CollectionIndex,
    ) -> None:
        """Result slugs are sorted alphabetically."""
        slugs = resolve_all_collection_slugs(
            puzzle_id=20,
            api_collection_name=None,
            collection_index=collection_index,
            matcher=matcher,
        )
        assert slugs == sorted(slugs)
