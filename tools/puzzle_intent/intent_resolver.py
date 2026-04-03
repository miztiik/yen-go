"""Tiered intent resolver: exact -> keyword -> semantic.

Orchestrates the matching pipeline:
1. Clean text (strip HTML, URLs, CJK, boilerplate, normalize)
2. Try exact substring match (Tier 1 - deterministic, confidence=1.0)
3. Try keyword co-occurrence match (Tier 1.5 - regex, confidence=0.7)
4. If no match and semantic enabled, try sentence-transformer (Tier 2 - fuzzy)
5. Log result via structured logger

Module-level convenience functions use a lazy singleton resolver.
"""

from __future__ import annotations

import logging

from tools.core.logging import StructuredLogger
from tools.core.text_cleaner import clean_comment_text

from .config_loader import load_objectives
from .exact_matcher import ExactMatcher
from .keyword_matcher import KeywordMatcher
from .logging_config import get_intent_logger
from .models import IntentResult
from .semantic_matcher import SemanticMatcher

logger = logging.getLogger("puzzle_intent")


class IntentResolver:
    """Tiered intent resolver: exact -> keyword -> semantic.

    Args:
        enable_semantic: If True, falls back to sentence-transformer when
            exact matching fails. Set False for deterministic-only mode.
        similarity_threshold: Cosine similarity threshold for semantic matching.
        structured_logger: Optional StructuredLogger for structured event logging.
    """

    def __init__(
        self,
        enable_semantic: bool = True,
        similarity_threshold: float = 0.65,
        structured_logger: StructuredLogger | None = None,
    ):
        objectives = load_objectives()
        self._exact = ExactMatcher(objectives)
        self._keyword = KeywordMatcher(objectives)
        self._semantic: SemanticMatcher | None = None
        self._semantic_enabled = enable_semantic
        self._intent_logger = get_intent_logger(structured_logger)

        if enable_semantic:
            self._semantic = SemanticMatcher(
                objectives,
                similarity_threshold=similarity_threshold,
            )

    def resolve(self, raw_text: str) -> IntentResult:
        """Resolve puzzle intent from raw comment text.

        Args:
            raw_text: Raw SGF comment text (may contain CJK, HTML, preambles).

        Returns:
            IntentResult with objective_id, confidence, and match_tier.
        """
        cleaned = clean_comment_text(raw_text)

        if not cleaned:
            return IntentResult.no_match(raw_text=raw_text, cleaned_text=cleaned)

        # Tier 1: Exact match
        result = self._exact.match(cleaned, raw_text=raw_text)
        if result is not None:
            self._intent_logger.intent_match(
                result.objective_id or "",
                result.matched_alias or "",
                result.confidence,
                result.match_tier.value,
            )
            return result

        # Tier 1.5: Keyword co-occurrence match
        result = self._keyword.match(cleaned, raw_text=raw_text)
        if result is not None:
            self._intent_logger.intent_match(
                result.objective_id or "",
                result.matched_alias or "",
                result.confidence,
                result.match_tier.value,
            )
            return result

        # Tier 2: Semantic match (if enabled and available)
        if self._semantic is not None and self._semantic.is_available:
            result = self._semantic.match(cleaned, raw_text=raw_text)
            if result is not None:
                self._intent_logger.intent_match(
                    result.objective_id or "",
                    result.matched_alias or "",
                    result.confidence,
                    result.match_tier.value,
                )
                return result

        self._intent_logger.intent_no_match(cleaned)
        return IntentResult.no_match(raw_text=raw_text, cleaned_text=cleaned)

    def resolve_batch(self, texts: list[str]) -> list[IntentResult]:
        """Resolve intents for multiple texts.

        Uses exact matching first, then batches remaining texts
        for semantic matching (single model encode call).
        """
        results: list[IntentResult] = []
        semantic_pending: list[tuple[int, str, str]] = []  # (index, cleaned, raw)

        for i, raw_text in enumerate(texts):
            cleaned = clean_comment_text(raw_text)

            if not cleaned:
                results.append(
                    IntentResult.no_match(raw_text=raw_text, cleaned_text=cleaned)
                )
                continue

            result = self._exact.match(cleaned, raw_text=raw_text)
            if result is None:
                result = self._keyword.match(cleaned, raw_text=raw_text)
            if result is not None:
                results.append(result)
            else:
                results.append(
                    IntentResult.no_match(raw_text=raw_text, cleaned_text=cleaned)
                )
                if self._semantic is not None and self._semantic.is_available:
                    semantic_pending.append((i, cleaned, raw_text))

        # Batch semantic matching for unresolved texts
        if semantic_pending and self._semantic is not None:
            indices, cleaned_texts, raw_texts = zip(*semantic_pending, strict=False)
            semantic_results = self._semantic.match_batch(
                list(cleaned_texts), list(raw_texts)
            )
            for idx, sem_result in zip(indices, semantic_results, strict=False):
                if sem_result is not None:
                    results[idx] = sem_result

        return results


# --- Module-level convenience functions (lazy singleton) ---

_resolver: IntentResolver | None = None


def _get_resolver(enable_semantic: bool = True) -> IntentResolver:
    """Get or create the singleton resolver."""
    global _resolver
    if _resolver is None:
        _resolver = IntentResolver(enable_semantic=enable_semantic)
    return _resolver


def resolve_intent(
    text: str,
    enable_semantic: bool = True,
) -> IntentResult:
    """Resolve puzzle objective from noisy comment text.

    Args:
        text: Raw SGF comment text (may contain CJK, HTML, preambles).
        enable_semantic: If True, falls back to sentence-transformer when
            exact matching fails. Set False for deterministic-only mode.

    Returns:
        IntentResult with objective_id, confidence, and match_tier.
    """
    resolver = _get_resolver(enable_semantic)
    return resolver.resolve(text)


def resolve_intents_batch(
    texts: list[str],
    enable_semantic: bool = True,
) -> list[IntentResult]:
    """Batch resolve for efficiency (semantic model batching).

    Args:
        texts: List of raw comment texts.
        enable_semantic: Enable semantic fallback.

    Returns:
        List of IntentResult, one per input text.
    """
    resolver = _get_resolver(enable_semantic)
    return resolver.resolve_batch(texts)
