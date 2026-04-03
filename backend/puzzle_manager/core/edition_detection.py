"""Edition detection: create sub-collections for multi-source collections.

When multiple sources contribute puzzles to the same collection,
this module splits them into edition sub-collections so each source's
pedagogical order is preserved.

Called by:
- publish.py._build_search_database()
- rollback.py._rebuild_search_db()
"""

from __future__ import annotations

import hashlib
import logging
import sqlite3
from collections import defaultdict
from pathlib import Path

from backend.puzzle_manager.core.db_models import CollectionMeta, PuzzleEntry

logger = logging.getLogger(__name__)


def _edition_id(parent_slug: str, source_id: str) -> int:
    """Deterministic, stable edition ID across publishes.

    Range 100K–10.1M. Config IDs are 1-200.
    """
    digest = hashlib.sha256(f"{parent_slug}:{source_id}".encode()).hexdigest()
    return int(digest[:8], 16) % 10_000_000 + 100_000


def create_editions(
    all_entries: list[PuzzleEntry],
    collections: list[CollectionMeta],
    content_db_path: Path,
) -> list[CollectionMeta]:
    """Detect multi-source collections and create edition sub-collections.

    Queries yengo-content.db for collection_slug grouping.
    Mutates all_entries (remaps collection_ids) and parent collections (sets attrs).
    Returns new CollectionMeta edition entries to extend into collections.
    """
    if not content_db_path.exists():
        return []

    conn = sqlite3.connect(f"file:{content_db_path}?mode=ro", uri=True)
    try:
        rows = conn.execute(
            "SELECT collection_slug, source, GROUP_CONCAT(content_hash) "
            "FROM sgf_files "
            "WHERE collection_slug IS NOT NULL AND source IS NOT NULL "
            "GROUP BY collection_slug, source"
        ).fetchall()
    finally:
        conn.close()

    if not rows:
        return []

    # Build slug → {source → [content_hashes]}
    col_sources: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    for slug, source, hashes in rows:
        col_sources[slug][source] = hashes.split(",")

    # Find collections with 2+ sources
    edition_parents = {
        slug: sources for slug, sources in col_sources.items()
        if len(sources) >= 2
    }

    if not edition_parents:
        return []

    # Build slug → CollectionMeta lookup
    slug_to_collection = {c.slug: c for c in collections}

    # Build config ID set for collision assertion
    config_ids = {c.collection_id for c in collections}

    edition_collections: list[CollectionMeta] = []

    for slug, source_map in edition_parents.items():
        parent = slug_to_collection.get(slug)
        if parent is None:
            logger.debug("No collection config for slug %s, skipping editions", slug)
            continue

        parent_id = parent.collection_id
        parent.attrs["is_parent"] = True
        parent.attrs["edition_ids"] = []

        # Sort sources by puzzle count descending for consistent ordering
        sorted_sources = sorted(source_map.items(), key=lambda x: len(x[1]), reverse=True)

        for idx, (source_id, puzzle_hashes) in enumerate(sorted_sources):
            eid = _edition_id(slug, source_id)
            assert eid not in config_ids, (
                f"Edition ID {eid} collides with config ID for {slug}:{source_id}"
            )
            parent.attrs["edition_ids"].append(eid)

            edition = CollectionMeta(
                collection_id=eid,
                slug=f"{slug}--{source_id}",
                name=parent.name,
                category=parent.category,
                puzzle_count=len(puzzle_hashes),
                attrs={
                    "parent_id": parent_id,
                    "label": f"Edition {idx + 1} ({len(puzzle_hashes)} puzzles)",
                    "type": parent.category or "",
                },
            )
            edition_collections.append(edition)

            # Remap puzzles from parent to edition
            hash_set = set(puzzle_hashes)
            for entry in all_entries:
                if entry.content_hash in hash_set:
                    if parent_id in entry.collection_ids:
                        entry.collection_ids.remove(parent_id)
                    if eid not in entry.collection_ids:
                        entry.collection_ids.append(eid)

        logger.info(
            "Collection %s: %d editions from %d sources",
            slug, len(sorted_sources), len(sorted_sources),
        )

    logger.info(
        "Edition detection: %d parent collections, %d editions created",
        len(edition_parents), len(edition_collections),
    )
    return edition_collections
