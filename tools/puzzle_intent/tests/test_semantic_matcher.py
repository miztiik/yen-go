"""Tests for semantic_matcher module.

Tests requiring sentence-transformers are skipped if the dependency
is not installed. Install with: pip install sentence-transformers
"""

import pytest

from tools.puzzle_intent.semantic_matcher import (
    _CACHE_DIR,
    SemanticMatcher,
    _check_available,
    _compute_cache_key,
)

requires_semantic = pytest.mark.requires_semantic


class TestSemanticMatcher:
    @requires_semantic
    def test_paraphrase_black_to_play(self):
        matcher = SemanticMatcher()
        result = matcher.match("it is black's turn to move", raw_text="")
        assert result is not None
        assert result.objective_id == "MOVE.BLACK.PLAY"
        assert result.confidence > 0.5

    @requires_semantic
    def test_paraphrase_survive(self):
        matcher = SemanticMatcher()
        result = matcher.match("black group needs to make life", raw_text="")
        assert result is not None
        assert "LIVE" in result.objective_id or "ESCAPE" in result.objective_id

    @requires_semantic
    def test_below_threshold_returns_none(self):
        matcher = SemanticMatcher(similarity_threshold=0.99)
        result = matcher.match("completely unrelated text about cooking", raw_text="")
        assert result is None

    @requires_semantic
    def test_exact_alias_gets_high_score(self):
        matcher = SemanticMatcher()
        result = matcher.match("black to play", raw_text="")
        assert result is not None
        assert result.confidence > 0.8

    @requires_semantic
    def test_is_available(self):
        matcher = SemanticMatcher()
        assert matcher.is_available is True


class TestSemanticMatcherAvailability:
    def test_is_available_reports_correctly(self):
        result = _check_available()
        assert isinstance(result, bool)


class TestEmbeddingCache:
    def test_cache_key_deterministic(self):
        """Same inputs produce same hash."""
        key1 = _compute_cache_key("model-a", ["alpha", "beta"])
        key2 = _compute_cache_key("model-a", ["alpha", "beta"])
        assert key1 == key2

    def test_cache_key_order_independent(self):
        """Alias order doesn't affect hash (sorted internally)."""
        key1 = _compute_cache_key("model-a", ["beta", "alpha"])
        key2 = _compute_cache_key("model-a", ["alpha", "beta"])
        assert key1 == key2

    def test_cache_key_changes_with_model(self):
        """Different model name → different hash."""
        key1 = _compute_cache_key("model-a", ["alpha"])
        key2 = _compute_cache_key("model-b", ["alpha"])
        assert key1 != key2

    def test_cache_key_changes_with_aliases(self):
        """Different aliases → different hash."""
        key1 = _compute_cache_key("model-a", ["alpha"])
        key2 = _compute_cache_key("model-a", ["alpha", "gamma"])
        assert key1 != key2

    def test_cache_key_is_16_hex_chars(self):
        key = _compute_cache_key("model", ["alias"])
        assert len(key) == 16
        assert all(c in "0123456789abcdef" for c in key)

    @requires_semantic
    def test_cache_file_created_after_match(self):
        """After first match, a .npy cache file should exist."""
        matcher = SemanticMatcher()
        matcher.match("black to play", raw_text="")
        npy_files = list(_CACHE_DIR.glob("*.npy"))
        assert len(npy_files) >= 1

    @requires_semantic
    def test_rebuild_creates_cache(self):
        from tools.puzzle_intent.semantic_matcher import rebuild_embedding_cache

        cache_file = rebuild_embedding_cache()
        assert cache_file.exists()
        assert cache_file.suffix == ".npy"
