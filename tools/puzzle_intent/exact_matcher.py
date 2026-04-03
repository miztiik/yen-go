"""Tier 1: Deterministic exact substring and token matching.

Matches cleaned text against curated aliases using:
1. Direct substring containment (fast path)
2. Contiguous token subsequence matching (handles word boundary issues)

Aliases are pre-sorted longest-first for greedy matching.
Confidence is always 1.0 for exact matches.
"""

from __future__ import annotations

import re

from .config_loader import build_alias_index, load_objectives
from .models import IntentResult, MatchTier, Objective


def _tokenize(text: str) -> list[str]:
    """Tokenize text into lowercase alphanumeric words.

    Pattern copied from backend/puzzle_manager/core/collection_assigner.py
    (architecture boundary: tools must not import from backend).
    """
    return [t for t in re.split(r"[^a-z0-9]+", text) if t]


def _is_contiguous_subsequence(needle: list[str], haystack: list[str]) -> bool:
    """Check if needle tokens appear contiguously in haystack.

    Copied from backend/puzzle_manager/core/collection_assigner.py.
    """
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


class ExactMatcher:
    """Deterministic keyword/substring matcher against curated aliases.

    Aliases are pre-sorted longest-first. The first matching alias wins,
    ensuring more specific matches take priority over shorter ones.
    """

    def __init__(self, objectives: tuple[Objective, ...] | None = None):
        if objectives is None:
            objectives = load_objectives()
        self._alias_index = build_alias_index(objectives)
        self._alias_tokens: dict[str, list[str]] = {
            alias: _tokenize(alias) for alias in self._alias_index
        }

    def match(self, cleaned_text: str, raw_text: str = "") -> IntentResult | None:
        """Try exact match against all aliases.

        Strategy:
        1. Direct substring: check if alias is contained in text
        2. Token subsequence: check if alias tokens appear contiguously

        Args:
            cleaned_text: Pre-cleaned, normalized text.
            raw_text: Original unprocessed text (for result metadata).

        Returns:
            IntentResult with confidence=1.0 if matched, None otherwise.
        """
        if not cleaned_text:
            return None

        text_tokens = _tokenize(cleaned_text)

        for alias, objective in self._alias_index.items():
            if alias in cleaned_text:
                return IntentResult(
                    objective_id=objective.objective_id,
                    objective=objective,
                    matched_alias=alias,
                    confidence=1.0,
                    match_tier=MatchTier.EXACT,
                    cleaned_text=cleaned_text,
                    raw_text=raw_text,
                )

            alias_tokens = self._alias_tokens[alias]
            if _is_contiguous_subsequence(alias_tokens, text_tokens):
                return IntentResult(
                    objective_id=objective.objective_id,
                    objective=objective,
                    matched_alias=alias,
                    confidence=1.0,
                    match_tier=MatchTier.EXACT,
                    cleaned_text=cleaned_text,
                    raw_text=raw_text,
                )

        return None
