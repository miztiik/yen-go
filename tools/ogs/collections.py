"""Collection name matching for OGS puzzles.

Thin wrapper around tools.core.collection_matcher.  Maintains the same
public API so existing callers are not affected.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from tools.core.collection_matcher import CollectionMatcher as _CoreMatcher

if TYPE_CHECKING:
    from tools.ogs.collection_index import CollectionIndex

logger = logging.getLogger("ogs.collections")


class CollectionMatcher:
    """Maps OGS collection names to YenGo collection slugs.

    Delegates to the shared ``tools.core.collection_matcher.CollectionMatcher``
    but returns a plain slug string from ``.match()`` for backward compatibility.
    """

    def __init__(self, collections_path: Path | None = None):
        self._core = _CoreMatcher(collections_path=collections_path)

    def match(self, collection_name: str) -> str | None:
        """Match an OGS collection name to a YenGo collection slug.

        Returns:
            Collection slug string or None.
        """
        result = self._core.match(collection_name)
        return result.slug if result else None


# ---------------------------------------------------------------------------
# Singleton + convenience function
# ---------------------------------------------------------------------------

_matcher: CollectionMatcher | None = None


def get_collection_matcher() -> CollectionMatcher:
    """Get the global CollectionMatcher instance."""
    global _matcher
    if _matcher is None:
        _matcher = CollectionMatcher()
    return _matcher


def match_collection_name(collection_name: str) -> str | None:
    """Convenience function to match OGS collection name to slug.

    Args:
        collection_name: OGS collection name

    Returns:
        YenGo collection slug or None
    """
    return get_collection_matcher().match(collection_name)


def resolve_all_collection_slugs(
    puzzle_id: int,
    api_collection_name: str | None,
    collection_index: CollectionIndex | None,
    matcher: CollectionMatcher | None = None,
) -> list[str]:
    """Resolve all YL[] slugs for a puzzle from multiple sources.

    Sources:
    1. Puzzle's own collection.name from the OGS API response
    2. Reverse index: all OGS collections whose ``puzzles`` array
       contains this puzzle_id

    For each OGS collection name, tries CollectionMatcher.match()
    to resolve to a YenGo slug.  Collects all non-None slugs,
    deduplicates, and sorts alphabetically (per YL[] spec).

    Args:
        puzzle_id: OGS puzzle ID.
        api_collection_name: collection.name from API (may be None).
        collection_index: Reverse index from JSONL (may be None for
            graceful fallback to API-only matching).
        matcher: CollectionMatcher instance (default: global singleton).

    Returns:
        Sorted deduplicated list of collection slugs (may be empty).
    """

    if matcher is None:
        matcher = get_collection_matcher()

    slugs: set[str] = set()

    # Source 1: API collection name
    if api_collection_name:
        slug = matcher.match(api_collection_name)
        if slug:
            slugs.add(slug)

    # Source 2: Reverse index lookup
    if collection_index is not None:
        for coll_name, _coll_id in collection_index.get_collections(puzzle_id):
            slug = matcher.match(coll_name)
            if slug:
                slugs.add(slug)

    return sorted(slugs)
