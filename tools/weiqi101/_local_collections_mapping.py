"""
Local collection mapping: 101weiqi category → YenGo collection slug.

Loads mappings from _local_collections_mapping.json (category → slug)
and _book_slug_mapping.json (book_id → slug). Follows the t-dragon
pattern of static JSON mapping.
"""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger("101weiqi.collections")

_MAPPING_FILE = Path(__file__).parent / "_local_collections_mapping.json"
_BOOK_SLUG_FILE = Path(__file__).parent / "_book_slug_mapping.json"


@lru_cache(maxsize=1)
def _load_mappings() -> dict[str, str | None]:
    """Load collection mappings from JSON config."""
    if not _MAPPING_FILE.exists():
        logger.warning(f"Collection mapping file not found: {_MAPPING_FILE}")
        return {}

    with open(_MAPPING_FILE, encoding="utf-8") as f:
        data = json.load(f)

    return data.get("mappings", {})


@lru_cache(maxsize=1)
def _load_book_slugs() -> dict[str, str]:
    """Load book ID → slug mappings from JSON config.

    Returns:
        Dict mapping string book_id to collection slug.
    """
    if not _BOOK_SLUG_FILE.exists():
        logger.warning(f"Book slug mapping file not found: {_BOOK_SLUG_FILE}")
        return {}

    with open(_BOOK_SLUG_FILE, encoding="utf-8") as f:
        data = json.load(f)

    books = data.get("books", {})
    return {bid: entry["slug"] for bid, entry in books.items() if "slug" in entry}


def resolve_book_slug(book_id: int | str) -> str | None:
    """Resolve a 101weiqi book ID to a YenGo collection slug.

    Uses the curated mapping from _book_slug_mapping.json. Returns
    ``None`` for unknown book IDs (YL is books-only, no fallback).

    Args:
        book_id: Numeric book ID (int or string).

    Returns:
        Collection slug (e.g., "gokyo-shumyo") or None if unknown.
    """
    slugs = _load_book_slugs()
    slug = slugs.get(str(book_id))
    if slug:
        return slug
    logger.debug(f"Book {book_id} not in slug mapping, skipping")
    return None


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


def enrich_collections_from_bookinfos(
    collection_entries: list[str] | None,
    bookinfos: list[dict],
) -> list[str] | None:
    """Add book-based collection entries from bookinfos.

    Resolves each book_id to a proper collection slug via
    ``_book_slug_mapping.json``. Falls back to ``101weiqi-book-{id}``
    for unknown books.

    Args:
        collection_entries: Existing collection entries (may be None).
        bookinfos: List of book info dicts (may be empty).
            Each dict should have ``book_id`` or ``id`` key.

    Returns:
        Updated collection entries list, or None if unchanged.
    """
    if not bookinfos:
        return collection_entries

    for book_info in bookinfos:
        book_id = book_info.get("book_id") or book_info.get("id")
        if not book_id:
            continue
        book_slug = resolve_book_slug(book_id)
        if not book_slug:
            continue
        if collection_entries is None:
            collection_entries = []
        if book_slug not in collection_entries:
            collection_entries.append(book_slug)
            logger.debug(f"Book enrichment: {book_id} → '{book_slug}'")

    return collection_entries
