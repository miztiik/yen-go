"""
GoProblems genre to YenGo tag mapping.

Maps GoProblems API genre field to canonical YenGo tags from config/tags.json.
Follows OGS tags.py singleton pattern.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger("go_problems.tags")


# GoProblems genre -> YenGo tag mapping
# All mapped tags MUST exist in config/tags.json
GENRE_TO_TAG: dict[str, str] = {
    "life and death": "life-and-death",
    "life-and-death": "life-and-death",
    "tesuji": "tesuji",
    "best move": "tesuji",
    "endgame": "endgame",
    "joseki": "joseki",
    "fuseki": "fuseki",
    "opening": "fuseki",
}

# Default collection -> tag mapping for well-known GoProblems collections
DEFAULT_COLLECTION_TAG_MAPPING: dict[str, str] = {
    "Nakade": "nakade",
    "Connect": "connection",
}


class TagMapper:
    """Maps GoProblems genre to YenGo tags.

    Singleton pattern: use get_tag_mapper() for the global instance.
    """

    def __init__(self, tags_path: Path | None = None):
        self._valid_tags: set[str] = set()
        if tags_path is None:
            tags_path = Path(__file__).parent.parent.parent / "config" / "tags.json"
        self._load_tags(tags_path)

    def _load_tags(self, path: Path) -> None:
        """Load valid tags from config/tags.json."""
        if not path.exists():
            logger.warning(f"Tags config not found: {path}")
            return
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            tags = data.get("tags", {})
            if isinstance(tags, dict):
                # tags.json uses dict keyed by tag ID
                for tag_id in tags:
                    self._valid_tags.add(tag_id)
            elif isinstance(tags, list):
                for tag in tags:
                    self._valid_tags.add(tag["id"])
            logger.debug(f"Loaded {len(self._valid_tags)} valid tags")
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to load tags.json: {e}")

    def map_genre(self, genre: str | None) -> list[str]:
        """Map GoProblems genre to YenGo tags.

        Precision over recall: only exact matches are mapped.
        Returns empty list for unknown/missing genres — let the
        pipeline tagger detect techniques from puzzle content.

        Args:
            genre: Genre string from API (e.g., "life and death", "tesuji")

        Returns:
            List of YenGo tag IDs. Empty if genre is unknown/missing.
        """
        if not genre:
            return []

        normalized = genre.lower().strip()

        if normalized in GENRE_TO_TAG:
            return [GENRE_TO_TAG[normalized]]

        logger.debug(f"Unknown genre '{genre}' — returning empty tags")
        return []

    def map_collections_to_tags(
        self,
        collections: list[dict] | None,
        mapping: dict[str, str] | None = None,
    ) -> list[str]:
        """Map GoProblems collection memberships to YenGo tags.

        Args:
            collections: List of collection dicts with 'id' and 'name'
            mapping: Optional collection name to tag mapping.
                     If None, uses DEFAULT_COLLECTION_TAG_MAPPING.

        Returns:
            List of YenGo tag IDs (deduplicated)
        """
        if not collections:
            return []

        if mapping is None:
            mapping = DEFAULT_COLLECTION_TAG_MAPPING

        tags: list[str] = []
        for collection in collections:
            name = collection.get("name", "")
            if name in mapping:
                tag = mapping[name]
                if tag not in tags:
                    tags.append(tag)

        return tags


# Singleton
_tag_mapper: TagMapper | None = None


def get_tag_mapper() -> TagMapper:
    """Get the global TagMapper instance."""
    global _tag_mapper
    if _tag_mapper is None:
        _tag_mapper = TagMapper()
    return _tag_mapper


def map_genre_to_tags(genre: str | None) -> list[str]:
    """Convenience function to map genre to tags.

    Args:
        genre: Genre string from API

    Returns:
        List of YenGo tag IDs
    """
    return get_tag_mapper().map_genre(genre)


def map_collections_to_tags(
    collections: list[dict] | None,
    mapping: dict[str, str] | None = None,
) -> list[str]:
    """Convenience function to map collections to tags.

    Args:
        collections: List of collection dicts
        mapping: Optional mapping override

    Returns:
        List of YenGo tag IDs
    """
    return get_tag_mapper().map_collections_to_tags(collections, mapping)
