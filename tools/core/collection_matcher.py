"""Shared collection phrase matcher for tool adapters.

Consolidates matching logic from tools/ogs, tools/go_problems, and
tools/tsumego_hero into a single reusable module.

Does NOT import from backend/ (architecture boundary).
"""

from __future__ import annotations

import json
import logging
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger("tools.core.collection_matcher")

# English stop words (articles, prepositions, conjunctions)
ENGLISH_STOP_WORDS = frozenset({"a", "an", "the", "of", "for", "in", "on", "to", "and"})

# Domain stop words: game names and generic terms that don't help distinguish
# collections.  Opt-in — pass stop_words=ENGLISH_STOP_WORDS | DOMAIN_STOP_WORDS
# to the constructor to enable.
DOMAIN_STOP_WORDS = frozenset({"go", "baduk", "weiqi", "problem"})

# Default: English-only (matches existing OGS/go_problems/tsumego_hero behavior)
DEFAULT_STOP_WORDS = ENGLISH_STOP_WORDS

# Regex for splitting: non-alphanumeric AND non-CJK/non-script characters
# CJK Unified Ideographs: U+4E00-U+9FFF
# Cyrillic: U+0400-U+04FF
# Thai: U+0E00-U+0E7F
# CJK Extension A: U+3400-U+4DBF
# Hiragana: U+3040-U+309F
# Katakana: U+30A0-U+30FF
# Hangul: U+AC00-U+D7AF
_SPLIT_RE = re.compile(
    r"[^a-z0-9\u0400-\u04ff\u0e00-\u0e7f\u3040-\u309f\u30a0-\u30ff"
    r"\u3400-\u4dbf\u4e00-\u9fff\uac00-\ud7af]+"
)


@dataclass(frozen=True)
class MatchResult:
    """Result of a collection name match."""

    slug: str
    confidence: float
    matched_alias: str


def _normalize(text: str) -> str:
    """Normalize text: NFKC + lowercase."""
    return unicodedata.normalize("NFKC", text).lower()


def _tokenize(text: str, stop_words: frozenset[str] | None = None) -> list[str]:
    """Tokenize text, splitting on non-alphanumeric (preserving CJK).

    Args:
        text: Normalized (lowered) text.
        stop_words: Set of stop words to remove. None means no removal.
    """
    tokens = [t for t in _SPLIT_RE.split(text) if t]
    if stop_words:
        tokens = [t for t in tokens if t not in stop_words]
    return tokens


def _is_contiguous_subsequence(needle: list[str], haystack: list[str]) -> bool:
    """Check if needle tokens appear contiguously in haystack."""
    if not needle:
        return False
    n_len = len(needle)
    h_len = len(haystack)
    if n_len > h_len:
        return False
    for i in range(h_len - n_len + 1):
        if haystack[i : i + n_len] == needle:
            return True
    return False


class CollectionMatcher:
    """Maps collection names to YenGo collection slugs.

    Loads config/collections.json and builds a lookup from names, slugs,
    and aliases to their canonical slug.  Matching uses NFKC-normalized,
    lowercased text with phrase matching as fallback.

    Supports optional local overrides that take priority over global aliases.
    """

    def __init__(
        self,
        collections_path: Path | None = None,
        local_overrides: dict[str, str] | None = None,
        stop_words: frozenset[str] | None = None,
    ):
        self._alias_map: dict[str, str] = {}
        self._local_overrides: dict[str, str] = {}
        self._stop_words = stop_words if stop_words is not None else DEFAULT_STOP_WORDS

        if collections_path is None:
            collections_path = self._get_default_path()
        self._load(collections_path)

        if local_overrides:
            self._local_overrides = {
                _normalize(k): v for k, v in local_overrides.items()
            }

    @staticmethod
    def _get_default_path() -> Path:
        """Path to config/collections.json from tools/core/collection_matcher.py."""
        return Path(__file__).parent.parent.parent / "config" / "collections.json"

    def _load(self, path: Path) -> None:
        """Load collections and build alias map."""
        if not path.exists():
            logger.warning("Collections config not found: %s", path)
            return
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            for coll in data.get("collections", []):
                slug = coll["slug"]

                # Register the slug itself
                self._alias_map[slug] = slug

                # Register the display name
                name = coll.get("name", "")
                if name:
                    self._alias_map[name] = slug

                # Register explicit aliases
                for alias in coll.get("aliases", []):
                    self._alias_map[alias] = slug

            logger.debug(
                "Loaded %d collections with %d alias entries",
                len(set(self._alias_map.values())),
                len(self._alias_map),
            )
        except (json.JSONDecodeError, KeyError) as e:
            logger.error("Failed to load collections.json: %s", e)

    def match(self, text: str) -> MatchResult | None:
        """Match a collection name to a YenGo collection slug.

        Matching strategy (priority order):
        1. Exact normalized match against local overrides
        2. Exact normalized match against any registered alias/name/slug
        3. Phrase matching (tokenized contiguous subsequence) — longest match wins

        Returns:
            MatchResult with slug, confidence, and matched_alias, or None.
        """
        if not text or not text.strip():
            return None

        norm_input = _normalize(text)

        # 1. Local overrides (exact normalized match)
        if norm_input in self._local_overrides:
            return MatchResult(
                slug=self._local_overrides[norm_input],
                confidence=1.0,
                matched_alias=text,
            )

        # 2. Exact normalized match against global aliases
        # (runs before tokenization so non-Latin scripts that don't tokenize
        #  still match via aliases)
        for alias, slug in self._alias_map.items():
            if _normalize(alias) == norm_input:
                return MatchResult(slug=slug, confidence=1.0, matched_alias=alias)

        # 3. Phrase matching — longest match wins
        input_tokens = _tokenize(norm_input, self._stop_words)
        if not input_tokens:
            return None

        best: MatchResult | None = None
        best_length = 0

        for alias, slug in self._alias_map.items():
            needle = _tokenize(_normalize(alias), self._stop_words)
            if not needle:
                continue
            if _is_contiguous_subsequence(needle, input_tokens):
                if len(needle) > best_length:
                    best_length = len(needle)
                    best = MatchResult(
                        slug=slug,
                        confidence=len(needle) / len(input_tokens),
                        matched_alias=alias,
                    )

        return best

    def match_all(self, text: str) -> list[MatchResult]:
        """Match a collection name against all aliases, returning all matches.

        Returns all matching aliases (exact + phrase), sorted by confidence
        descending.  Each slug appears at most once (best alias wins).
        """
        if not text or not text.strip():
            return []

        norm_input = _normalize(text)
        results: list[MatchResult] = []
        seen_slugs: set[str] = set()

        # 1. Local overrides (exact normalized)
        if norm_input in self._local_overrides:
            slug = self._local_overrides[norm_input]
            results.append(MatchResult(slug=slug, confidence=1.0, matched_alias=text))
            seen_slugs.add(slug)

        # 2. Exact match against global aliases
        for alias, slug in self._alias_map.items():
            if slug in seen_slugs:
                continue
            if _normalize(alias) == norm_input:
                results.append(
                    MatchResult(slug=slug, confidence=1.0, matched_alias=alias)
                )
                seen_slugs.add(slug)

        # 3. Phrase matching
        input_tokens = _tokenize(norm_input, self._stop_words)
        if input_tokens:
            slug_best: dict[str, tuple[int, str]] = {}
            for alias, slug in self._alias_map.items():
                if slug in seen_slugs:
                    continue
                needle = _tokenize(_normalize(alias), self._stop_words)
                if not needle:
                    continue
                if _is_contiguous_subsequence(needle, input_tokens):
                    prev = slug_best.get(slug)
                    if prev is None or len(needle) > prev[0]:
                        slug_best[slug] = (len(needle), alias)

            for slug, (length, alias) in slug_best.items():
                results.append(
                    MatchResult(
                        slug=slug,
                        confidence=length / len(input_tokens),
                        matched_alias=alias,
                    )
                )

        results.sort(key=lambda r: r.confidence, reverse=True)
        return results
