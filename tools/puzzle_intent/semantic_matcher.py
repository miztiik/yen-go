"""Tier 2: Sentence-transformer based semantic similarity matching.

Uses all-MiniLM-L6-v2 for cosine similarity between input text and
curated objective aliases. Optional dependency - gracefully degrades
if sentence-transformers is not installed.

Model is lazy-loaded on first match() call. Alias embeddings are
pre-computed and cached to .npy files for fast subsequent loads.
Cache is keyed by SHA-256 of model name + sorted aliases, so any
change to puzzle-objectives.json aliases or model version
automatically invalidates the cache.
"""

from __future__ import annotations

import hashlib
import logging
import re
import time
from pathlib import Path
from typing import Any

import numpy as np

from .config_loader import load_objectives
from .models import IntentResult, MatchTier, Objective

logger = logging.getLogger("puzzle_intent.semantic")

DEFAULT_MODEL_NAME = "all-MiniLM-L6-v2"
DEFAULT_SIMILARITY_THRESHOLD = 0.65

# Split on sentence-ending punctuation followed by whitespace,
# or on comma/semicolon/colon followed by whitespace (clause boundaries).
# This prevents compound sentences from diluting embeddings.
_CLAUSE_SPLIT = re.compile(r"(?<=[.!?;])\s+|,\s+")

# Cache directory for precomputed alias embeddings (.npy files)
_CACHE_DIR = Path(__file__).parent / ".embedding_cache"


def _check_available() -> bool:
    """Check if sentence-transformers is importable."""
    try:
        import sentence_transformers  # noqa: F401

        return True
    except ImportError:
        return False


def _compute_cache_key(model_name: str, alias_texts: list[str]) -> str:
    """Compute SHA-256 hash of model name + sorted aliases.

    Any change to the model or aliases invalidates the cache.
    """
    key_material = model_name + "\n" + "\n".join(sorted(alias_texts))
    return hashlib.sha256(key_material.encode("utf-8")).hexdigest()[:16]


def _load_cached_embeddings(cache_key: str) -> np.ndarray | None:
    """Load embeddings from .npy cache if available."""
    cache_file = _CACHE_DIR / f"{cache_key}.npy"
    if cache_file.exists():
        try:
            embeddings = np.load(str(cache_file))
            logger.info("Loaded cached embeddings: %s", cache_file.name)
            return embeddings
        except Exception as exc:
            logger.warning("Failed to load embedding cache %s: %s", cache_file, exc)
    return None


def _save_cached_embeddings(cache_key: str, embeddings: np.ndarray) -> None:
    """Save embeddings to .npy cache."""
    try:
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache_file = _CACHE_DIR / f"{cache_key}.npy"
        np.save(str(cache_file), embeddings)
        logger.info("Saved embedding cache: %s (%d aliases)", cache_file.name, len(embeddings))
    except Exception as exc:
        logger.warning("Failed to save embedding cache: %s", exc)


def rebuild_embedding_cache(
    model_name: str = DEFAULT_MODEL_NAME,
    objectives: tuple[Objective, ...] | None = None,
) -> Path:
    """Force-rebuild the .npy embedding cache.

    Loads the model, encodes all aliases, saves to .npy, and returns
    the cache file path. Call this after modifying puzzle-objectives.json
    or changing the model.

    Returns:
        Path to the saved .npy cache file.
    """
    if objectives is None:
        objectives = load_objectives()

    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        raise ImportError(
            "sentence-transformers is required. "
            "Install with: pip install sentence-transformers"
        ) from None

    alias_texts = [alias for obj in objectives for alias in obj.aliases]
    cache_key = _compute_cache_key(model_name, alias_texts)

    logger.info("Rebuilding embedding cache (model=%s, %d aliases)...", model_name, len(alias_texts))
    model = SentenceTransformer(model_name)
    embeddings = model.encode(alias_texts, show_progress_bar=False)
    embeddings_np = np.array(embeddings)

    _CACHE_DIR.mkdir(parents=True, exist_ok=True)

    # Remove stale cache files for this model
    for old_file in _CACHE_DIR.glob("*.npy"):
        old_file.unlink()
        logger.debug("Removed stale cache: %s", old_file.name)

    cache_file = _CACHE_DIR / f"{cache_key}.npy"
    np.save(str(cache_file), embeddings_np)
    logger.info("Cache rebuilt: %s (%d aliases, %d dims)", cache_file.name, len(alias_texts), embeddings_np.shape[1])
    return cache_file


class SemanticMatcher:
    """Sentence-transformer based fuzzy matcher for puzzle objectives.

    Lazy-loads the model on first use. Pre-computes alias embeddings
    and caches them as .npy files for fast subsequent loads.
    Returns the best match above the similarity threshold.
    """

    def __init__(
        self,
        objectives: tuple[Objective, ...] | None = None,
        model_name: str = DEFAULT_MODEL_NAME,
        similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
    ):
        if objectives is None:
            objectives = load_objectives()
        self._objectives = objectives
        self._model_name = model_name
        self._threshold = similarity_threshold
        self._model: Any = None
        self._alias_embeddings: Any = None
        self._alias_lookup: list[tuple[str, Objective]] = []

    @property
    def is_available(self) -> bool:
        """Check if sentence-transformers is importable."""
        return _check_available()

    def _ensure_model_loaded(self) -> None:
        """Lazy-load the sentence transformer model and pre-compute embeddings."""
        if self._model is not None:
            return

        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            raise ImportError(
                "sentence-transformers is required for semantic matching. "
                "Install with: pip install sentence-transformers"
            ) from None

        start = time.monotonic()
        self._model = SentenceTransformer(self._model_name)
        load_time = time.monotonic() - start
        logger.info(
            "Model loaded: %s (%.1fs)",
            self._model_name,
            load_time,
        )

        self._precompute_embeddings()

    def _precompute_embeddings(self) -> None:
        """Load alias embeddings from .npy cache, or compute and save."""
        import torch

        alias_texts: list[str] = []
        self._alias_lookup = []

        for obj in self._objectives:
            for alias in obj.aliases:
                alias_texts.append(alias)
                self._alias_lookup.append((alias, obj))

        cache_key = _compute_cache_key(self._model_name, alias_texts)
        cached = _load_cached_embeddings(cache_key)

        if cached is not None and cached.shape[0] == len(alias_texts):
            self._alias_embeddings = torch.tensor(cached)
            logger.debug("Using cached embeddings for %d aliases", len(alias_texts))
            return

        start = time.monotonic()
        self._alias_embeddings = self._model.encode(
            alias_texts,
            convert_to_tensor=True,
            show_progress_bar=False,
        )
        encode_time = time.monotonic() - start
        logger.debug("Encoded %d alias embeddings (%.1fs)", len(alias_texts), encode_time)

        # Save to cache for next time
        _save_cached_embeddings(cache_key, self._alias_embeddings.cpu().numpy())

    def match(self, cleaned_text: str, raw_text: str = "") -> IntentResult | None:
        """Find best semantic match above threshold.

        Splits multi-clause text on sentence boundaries and commas,
        encoding each clause independently. Returns the best match
        across all clauses. This prevents hints, instructions, or
        compound clauses from diluting the objective embedding.

        Args:
            cleaned_text: Pre-cleaned, normalized text.
            raw_text: Original unprocessed text (for result metadata).

        Returns:
            IntentResult with confidence=similarity_score if matched, None otherwise.
        """
        if not cleaned_text:
            return None

        self._ensure_model_loaded()

        from sentence_transformers import util

        # Split into clauses; encode all at once for efficiency
        clauses = [s.strip() for s in _CLAUSE_SPLIT.split(cleaned_text) if s.strip()]
        if not clauses:
            return None

        query_embeddings = self._model.encode(
            clauses,
            convert_to_tensor=True,
            show_progress_bar=False,
        )

        # For a single sentence, encode returns 1-D; reshape to 2-D
        if query_embeddings.dim() == 1:
            query_embeddings = query_embeddings.unsqueeze(0)

        all_scores = util.cos_sim(query_embeddings, self._alias_embeddings)

        best_score = -1.0
        best_alias_idx = -1
        for row in all_scores:
            idx = int(row.argmax().item())
            score = float(row[idx].item())
            if score > best_score:
                best_score = score
                best_alias_idx = idx

        if best_score < self._threshold:
            return None

        alias, objective = self._alias_lookup[best_alias_idx]
        return IntentResult(
            objective_id=objective.objective_id,
            objective=objective,
            matched_alias=alias,
            confidence=round(best_score, 4),
            match_tier=MatchTier.SEMANTIC,
            cleaned_text=cleaned_text,
            raw_text=raw_text,
        )

    def match_batch(
        self, cleaned_texts: list[str], raw_texts: list[str]
    ) -> list[IntentResult | None]:
        """Batch match for efficiency (single model encode call).

        Args:
            cleaned_texts: List of pre-cleaned texts.
            raw_texts: Corresponding original texts.

        Returns:
            List of IntentResult or None, one per input.
        """
        if not cleaned_texts:
            return []

        self._ensure_model_loaded()

        from sentence_transformers import util

        # Filter out empty texts, track indices
        valid_indices: list[int] = []
        valid_texts: list[str] = []
        for i, text in enumerate(cleaned_texts):
            if text:
                valid_indices.append(i)
                valid_texts.append(text)

        results: list[IntentResult | None] = [None] * len(cleaned_texts)

        if not valid_texts:
            return results

        query_embeddings = self._model.encode(
            valid_texts,
            convert_to_tensor=True,
            show_progress_bar=False,
        )
        all_scores = util.cos_sim(query_embeddings, self._alias_embeddings)

        for j, orig_idx in enumerate(valid_indices):
            scores = all_scores[j]
            best_idx = int(scores.argmax().item())
            best_score = float(scores[best_idx].item())

            if best_score >= self._threshold:
                alias, objective = self._alias_lookup[best_idx]
                results[orig_idx] = IntentResult(
                    objective_id=objective.objective_id,
                    objective=objective,
                    matched_alias=alias,
                    confidence=round(best_score, 4),
                    match_tier=MatchTier.SEMANTIC,
                    cleaned_text=cleaned_texts[orig_idx],
                    raw_text=raw_texts[orig_idx],
                )

        return results
