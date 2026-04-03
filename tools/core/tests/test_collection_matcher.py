"""Tests for tools.core.collection_matcher shared module."""

import json
from pathlib import Path

import pytest

from tools.core.collection_matcher import (
    DOMAIN_STOP_WORDS,
    ENGLISH_STOP_WORDS,
    CollectionMatcher,
    _is_contiguous_subsequence,
    _normalize,
    _tokenize,
)

# ==============================
# Fixtures
# ==============================


@pytest.fixture
def sample_config(tmp_path: Path) -> Path:
    """Minimal collections.json for testing."""
    config = {
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
                "aliases": ["shumyo", "\u7384\u5999"],
            },
            {
                "slug": "nakade-problems",
                "name": "Nakade Problems",
                "aliases": [],
            },
        ],
    }
    path = tmp_path / "collections.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    return path


@pytest.fixture
def matcher(sample_config: Path) -> CollectionMatcher:
    return CollectionMatcher(collections_path=sample_config)


# ==============================
# Exact Match
# ==============================


class TestExactMatch:
    def test_exact_name(self, matcher: CollectionMatcher) -> None:
        result = matcher.match("Tesuji Training")
        assert result is not None
        assert result.slug == "tesuji-training"
        assert result.confidence == 1.0

    def test_exact_slug(self, matcher: CollectionMatcher) -> None:
        result = matcher.match("gokyo-shumyo")
        assert result is not None
        assert result.slug == "gokyo-shumyo"

    def test_exact_alias(self, matcher: CollectionMatcher) -> None:
        result = matcher.match("tactical problems")
        assert result is not None
        assert result.slug == "tesuji-training"
        assert result.confidence == 1.0

    def test_case_insensitive_exact(self, matcher: CollectionMatcher) -> None:
        result = matcher.match("TESUJI TRAINING")
        assert result is not None
        assert result.slug == "tesuji-training"

        result2 = matcher.match("tesuji training")
        assert result2 is not None
        assert result2.slug == "tesuji-training"


# ==============================
# Phrase Match
# ==============================


class TestPhraseMatch:
    def test_phrase_in_longer_text(self, matcher: CollectionMatcher) -> None:
        result = matcher.match("My Custom Tesuji Training Collection")
        assert result is not None
        assert result.slug == "tesuji-training"
        assert 0.0 < result.confidence < 1.0

    def test_contiguous_subsequence(self, matcher: CollectionMatcher) -> None:
        result = matcher.match("Advanced Nakade Problems Collection")
        assert result is not None
        assert result.slug == "nakade-problems"

    def test_cho_elementary_real_world(self, matcher: CollectionMatcher) -> None:
        result = matcher.match(
            "Cho Chikun's Encyclopedia of Life and Death - Elementary"
        )
        assert result is not None
        assert result.slug == "cho-chikun-life-death-elementary"


# ==============================
# Longest Match Wins
# ==============================


class TestLongestMatchWins:
    def test_longer_alias_preferred(self, matcher: CollectionMatcher) -> None:
        """'encyclopedia life death elementary' (4 tokens) beats 'cho elementary' (2)."""
        result = matcher.match(
            "Cho Chikun's Encyclopedia of Life and Death - Elementary"
        )
        assert result is not None
        assert result.slug == "cho-chikun-life-death-elementary"


# ==============================
# Stop-Word Filtering
# ==============================


class TestStopWords:
    def test_stop_words_removed(self) -> None:
        tokens = _tokenize("encyclopedia of life and death", ENGLISH_STOP_WORDS)
        assert "of" not in tokens
        assert "and" not in tokens
        assert "encyclopedia" in tokens
        assert "life" in tokens
        assert "death" in tokens

    def test_domain_stop_words(self) -> None:
        combined = ENGLISH_STOP_WORDS | DOMAIN_STOP_WORDS
        tokens = _tokenize("go problems for beginners", combined)
        assert "go" not in tokens
        assert "beginners" in tokens

    def test_no_stop_words(self) -> None:
        tokens = _tokenize("the encyclopedia of life", None)
        assert "the" in tokens
        assert "of" in tokens


# ==============================
# CJK Input Handling
# ==============================


class TestCJK:
    def test_cjk_exact_alias(self, matcher: CollectionMatcher) -> None:
        result = matcher.match("\u7384\u5999")
        assert result is not None
        assert result.slug == "gokyo-shumyo"
        assert result.confidence == 1.0

    def test_cjk_tokens_preserved(self) -> None:
        tokens = _tokenize("\u7384\u5999\u306e\u8a70\u7881", ENGLISH_STOP_WORDS)
        # CJK characters should not be split apart
        assert len(tokens) >= 1


# ==============================
# Local Override Priority
# ==============================


class TestLocalOverrides:
    def test_local_override_exact(self, sample_config: Path) -> None:
        overrides = {"Easy Capture": "capture-problems"}
        m = CollectionMatcher(
            collections_path=sample_config, local_overrides=overrides
        )
        result = m.match("Easy Capture")
        assert result is not None
        assert result.slug == "capture-problems"
        assert result.confidence == 1.0

    def test_local_override_beats_global(self, sample_config: Path) -> None:
        """Local override takes priority over global alias match."""
        overrides = {"Tesuji Training": "custom-override-slug"}
        m = CollectionMatcher(
            collections_path=sample_config, local_overrides=overrides
        )
        result = m.match("Tesuji Training")
        assert result is not None
        assert result.slug == "custom-override-slug"

    def test_global_fallback_when_no_local(self, sample_config: Path) -> None:
        overrides = {"Something Else": "other-slug"}
        m = CollectionMatcher(
            collections_path=sample_config, local_overrides=overrides
        )
        result = m.match("Tesuji Training")
        assert result is not None
        assert result.slug == "tesuji-training"


# ==============================
# No Match
# ==============================


class TestNoMatch:
    def test_unknown_returns_none(self, matcher: CollectionMatcher) -> None:
        assert matcher.match("Completely Unknown XYZ") is None

    def test_empty_returns_none(self, matcher: CollectionMatcher) -> None:
        assert matcher.match("") is None

    def test_whitespace_returns_none(self, matcher: CollectionMatcher) -> None:
        assert matcher.match("   ") is None

    def test_none_input_returns_none(self, matcher: CollectionMatcher) -> None:
        assert matcher.match(None) is None  # type: ignore[arg-type]


# ==============================
# match_all
# ==============================


class TestMatchAll:
    def test_match_all_returns_list(self, matcher: CollectionMatcher) -> None:
        results = matcher.match_all("Tesuji Training")
        assert len(results) >= 1
        assert results[0].slug == "tesuji-training"

    def test_match_all_empty_input(self, matcher: CollectionMatcher) -> None:
        assert matcher.match_all("") == []
        assert matcher.match_all(None) == []  # type: ignore[arg-type]

    def test_match_all_sorted_by_confidence(self, matcher: CollectionMatcher) -> None:
        results = matcher.match_all("Tesuji Training")
        confidences = [r.confidence for r in results]
        assert confidences == sorted(confidences, reverse=True)


# ==============================
# Edge Cases
# ==============================


class TestEdgeCases:
    def test_missing_config_file(self, tmp_path: Path) -> None:
        m = CollectionMatcher(collections_path=tmp_path / "missing.json")
        assert m.match("anything") is None

    def test_empty_collections(self, tmp_path: Path) -> None:
        path = tmp_path / "empty.json"
        path.write_text('{"collections": []}', encoding="utf-8")
        m = CollectionMatcher(collections_path=path)
        assert m.match("anything") is None

    def test_collection_without_aliases(self, tmp_path: Path) -> None:
        path = tmp_path / "c.json"
        path.write_text(
            json.dumps(
                {"collections": [{"slug": "test", "name": "Test Collection"}]}
            ),
            encoding="utf-8",
        )
        m = CollectionMatcher(collections_path=path)
        result = m.match("Test Collection")
        assert result is not None
        assert result.slug == "test"


# ==============================
# Internal helpers
# ==============================


class TestHelpers:
    def test_normalize_nfkc(self) -> None:
        # Fullwidth A → normal A after NFKC
        assert _normalize("\uff21") == "a"

    def test_is_contiguous_subsequence_true(self) -> None:
        assert _is_contiguous_subsequence(["a", "b"], ["x", "a", "b", "y"])

    def test_is_contiguous_subsequence_false(self) -> None:
        assert not _is_contiguous_subsequence(["a", "c"], ["a", "b", "c"])

    def test_is_contiguous_subsequence_empty_needle(self) -> None:
        assert not _is_contiguous_subsequence([], ["a", "b"])
