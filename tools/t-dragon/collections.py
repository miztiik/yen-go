"""
Local collection mapping for TsumegoDragon.

Maps TD category slugs to YenGo collection slugs from config/collections.json.
Uses a static local JSON config for deterministic, auditable mapping.

Usage:
    from tools.t_dragon.collections import resolve_collection_slug

    slug = resolve_collection_slug("ladder")  # -> "ladder-problems"
    slug = resolve_collection_slug("unsorted")  # -> None
"""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger("t-dragon.collections")

_COLLECTIONS_FILE = Path(__file__).parent / "collections.json"


@lru_cache(maxsize=1)
def _load_mappings() -> dict[str, str | None]:
    """Load category-slug -> collection-slug mappings from local JSON.

    Returns:
        Dict mapping TD category slugs to YenGo collection slugs.
        Values may be None for categories with no collection mapping.
    """
    if not _COLLECTIONS_FILE.exists():
        logger.warning(f"Collections config not found: {_COLLECTIONS_FILE}")
        return {}

    with open(_COLLECTIONS_FILE, encoding="utf-8") as f:
        data = json.load(f)

    mappings = data.get("mappings", {})
    logger.debug(f"Loaded {len(mappings)} collection mappings from {_COLLECTIONS_FILE.name}")
    return mappings


def resolve_collection_slug(category_slug: str) -> str | None:
    """Resolve a TD category slug to a YenGo collection slug.

    Args:
        category_slug: TsumegoDragon category slug (e.g., "ladder", "capture-race").

    Returns:
        YenGo collection slug (e.g., "ladder-problems") or None if unmapped.
    """
    mappings = _load_mappings()
    return mappings.get(category_slug)


def get_all_mapped_slugs() -> list[str]:
    """Get all YenGo collection slugs referenced by this tool.

    Returns:
        Sorted list of unique non-None collection slugs.
    """
    mappings = _load_mappings()
    return sorted({v for v in mappings.values() if v is not None})


def get_unmapped_categories() -> list[str]:
    """Get categories with no collection mapping (mapped to null).

    Returns:
        Sorted list of category slugs mapped to None.
    """
    mappings = _load_mappings()
    return sorted(k for k, v in mappings.items() if v is None)
