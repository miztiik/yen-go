"""Collection name matching for GoProblems puzzles.

Thin wrapper around tools.core.collection_matcher.  Maintains the same
public API so existing callers are not affected.
"""

from __future__ import annotations

import logging
from pathlib import Path

from tools.core.collection_matcher import CollectionMatcher as _CoreMatcher

logger = logging.getLogger("go_problems.collections")


class CollectionMatcher:
    """Maps GoProblems collection names to YenGo collection slugs.

    Delegates to the shared ``tools.core.collection_matcher.CollectionMatcher``
    but returns a plain slug string from ``.match()`` for backward compatibility.
    """

    def __init__(self, collections_path: Path | None = None):
        self._core = _CoreMatcher(collections_path=collections_path)

    def match(self, collection_name: str) -> str | None:
        """Match a collection name to a YenGo collection slug.

        Returns:
            Collection slug string or None.
        """
        result = self._core.match(collection_name)
        return result.slug if result else None


# Singleton
_matcher: CollectionMatcher | None = None


def get_collection_matcher() -> CollectionMatcher:
    """Get the global CollectionMatcher instance."""
    global _matcher
    if _matcher is None:
        _matcher = CollectionMatcher()
    return _matcher


def reset_collection_matcher() -> None:
    """Reset the global CollectionMatcher singleton (e.g., after config update)."""
    global _matcher
    _matcher = None


def match_collection_name(collection_name: str) -> str | None:
    """Convenience function to match a collection name to slug.

    Args:
        collection_name: GoProblems collection name

    Returns:
        YenGo collection slug or None
    """
    return get_collection_matcher().match(collection_name)


def resolve_collection_slugs(
    collections: list[dict] | None,
) -> list[str]:
    """Resolve all YL[] slugs from GoProblems collections array.

    Args:
        collections: List of collection dicts with 'name' field

    Returns:
        Sorted deduplicated list of collection slugs
    """
    if not collections:
        return []

    matcher = get_collection_matcher()
    slugs: set[str] = set()

    for coll in collections:
        name = coll.get("name", "")
        if name:
            slug = matcher.match(name)
            if slug:
                slugs.add(slug)

    return sorted(slugs)
