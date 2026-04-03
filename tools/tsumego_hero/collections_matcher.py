"""Collection matching for Tsumego Hero puzzles.

Thin wrapper around tools.core.collection_matcher.  Maintains the same
public API so existing callers are not affected.

Maps TH collection names to YenGo collection slugs using two sources:
1. Local overrides in collections_local.json (exact match, highest priority)
2. Global config/collections.json via phrase matching (fallback)

Usage:
    from tools.tsumego_hero.collections_matcher import resolve_collection_slug

    slug = resolve_collection_slug("Easy Capture")  # -> "capture-problems"
    slug = resolve_collection_slug("Cho Chikun Elementary")  # -> "cho-chikun-life-death-elementary"
"""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path

from tools.core.collection_matcher import CollectionMatcher as _CoreMatcher

logger = logging.getLogger("tsumego_hero.collections")

_LOCAL_FILE = Path(__file__).parent / "collections_local.json"
_GLOBAL_FILE = Path(__file__).parent.parent.parent / "config" / "collections.json"


@lru_cache(maxsize=1)
def _load_local_overrides() -> dict[str, str]:
    """Load local collection name -> slug overrides."""
    if not _LOCAL_FILE.exists():
        return {}
    with open(_LOCAL_FILE, encoding="utf-8") as f:
        data = json.load(f)
    return {k: v for k, v in data.get("mappings", {}).items() if v is not None}


@lru_cache(maxsize=1)
def _get_matcher() -> _CoreMatcher:
    """Build a CoreMatcher with local overrides."""
    return _CoreMatcher(
        collections_path=_GLOBAL_FILE,
        local_overrides=_load_local_overrides(),
    )


def resolve_collection_slug(collection_name: str) -> str | None:
    """Resolve a TH collection name to a YenGo collection slug.

    Matching strategy (priority order):
    1. Exact normalized match against local overrides
    2. Exact normalized match against global aliases
    3. Phrase matching (tokenized contiguous subsequence) against global aliases

    Args:
        collection_name: Tsumego Hero collection name.

    Returns:
        YenGo collection slug or None.
    """
    result = _get_matcher().match(collection_name)
    return result.slug if result else None


def get_all_local_slugs() -> list[str]:
    """Get all YenGo collection slugs from local overrides.

    Returns:
        Sorted list of unique collection slugs.
    """
    local = _load_local_overrides()
    return sorted(set(local.values()))
