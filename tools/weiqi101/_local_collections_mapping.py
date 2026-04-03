"""
Local collection mapping: 101weiqi category → YenGo collection slug.

Loads mappings from _local_collections_mapping.json. Follows the
t-dragon pattern of static JSON mapping.
"""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger("101weiqi.collections")

_MAPPING_FILE = Path(__file__).parent / "_local_collections_mapping.json"


@lru_cache(maxsize=1)
def _load_mappings() -> dict[str, str | None]:
    """Load collection mappings from JSON config."""
    if not _MAPPING_FILE.exists():
        logger.warning(f"Collection mapping file not found: {_MAPPING_FILE}")
        return {}

    with open(_MAPPING_FILE, encoding="utf-8") as f:
        data = json.load(f)

    return data.get("mappings", {})


def resolve_collection_slug(type_name: str) -> str | None:
    """Resolve a 101weiqi category to a YenGo collection slug.

    Args:
        type_name: Chinese category string (e.g., "死活题").

    Returns:
        Collection slug (e.g., "life-and-death") or None.
    """
    if not type_name:
        return None

    mappings = _load_mappings()
    slug = mappings.get(type_name)

    if slug:
        logger.debug(f"Collection '{type_name}' → '{slug}'")
    else:
        logger.debug(f"Collection '{type_name}' → no match")

    return slug
