"""
Level and tag mappers for Tsumego Hero puzzles.

Maps site-specific difficulty ratings and tags to YenGo canonical formats.
Uses sources.json for mapping definitions.
"""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger("tsumego_hero.mappers")


# Load mappings from sources.json
@lru_cache(maxsize=1)
def _load_sources() -> dict:
    """Load sources.json configuration."""
    sources_path = Path(__file__).parent / "sources.json"
    with open(sources_path, encoding="utf-8") as f:
        return json.load(f)


# ============================================================================
# Level Mapping
# ============================================================================

# Difficulty rank to YenGo level mapping
# Based on sources.json difficulty_mapping
# Extended to handle Tsumego Hero's wider difficulty range (30k-9d)
DIFFICULTY_TO_LEVEL: dict[str, str] = {
    # Very beginner levels (30k-16k) -> novice
    "30k": "novice",
    "29k": "novice",
    "28k": "novice",
    "27k": "novice",
    "26k": "novice",
    "25k": "novice",
    "24k": "novice",
    "23k": "novice",
    "22k": "novice",
    "21k": "novice",
    "20k": "novice",
    "19k": "novice",
    "18k": "novice",
    "17k": "novice",
    "16k": "novice",
    # Standard mapping (15k-9d)
    "15k": "novice",
    "14k": "novice",
    "13k": "novice",
    "12k": "novice",
    "11k": "beginner",
    "10k": "beginner",
    "9k": "beginner",
    "8k": "elementary",
    "7k": "elementary",
    "6k": "elementary",
    "5k": "intermediate",
    "4k": "intermediate",
    "3k": "upper-intermediate",
    "2k": "upper-intermediate",
    "1k": "upper-intermediate",
    "1d": "advanced",
    "2d": "advanced",
    "3d": "low-dan",
    "4d": "low-dan",
    "5d": "high-dan",
    "6d": "high-dan",
    "7d": "high-dan",
    "8d": "expert",
    "9d": "expert",
}


def difficulty_to_level(difficulty: str | None) -> str | None:
    """Map Tsumego Hero difficulty to YenGo level slug.

    Args:
        difficulty: Rank string like "15k", "3d", etc.

    Returns:
        YenGo level slug or None if unmapped.
    """
    if not difficulty:
        return None

    # Normalize to lowercase
    difficulty = difficulty.lower().strip()

    level = DIFFICULTY_TO_LEVEL.get(difficulty)
    if level:
        logger.debug(f"Mapped difficulty {difficulty} → {level}")
    else:
        logger.debug(f"No mapping for difficulty: {difficulty}")

    return level


# ============================================================================
# Tag Mapping
# ============================================================================

@lru_cache(maxsize=1)
def _load_tag_mapping() -> dict[str, str | None]:
    """Load tag mapping from sources.json."""
    sources = _load_sources()
    mapping = sources.get("tag_mapping", {})

    # Filter out metadata keys starting with "_"
    return {k: v for k, v in mapping.items() if not k.startswith("_")}


def tag_to_yengo(tag_name: str) -> str | None:
    """Map a single Tsumego Hero tag to YenGo canonical tag.

    Args:
        tag_name: Tag name from Tsumego Hero (e.g., "Snapback", "Ko").

    Returns:
        YenGo canonical tag or None if unmapped.
    """
    mapping = _load_tag_mapping()
    return mapping.get(tag_name)


def tags_to_yengo(tags: list[dict]) -> list[str]:
    """Map Tsumego Hero tags to YenGo canonical tags.

    Args:
        tags: List of tag objects from puzzle, e.g. [{"name": "Ko", "isHint": 1}, ...]

    Returns:
        Sorted, deduplicated list of YenGo canonical tags.
    """
    mapping = _load_tag_mapping()
    yengo_tags: set[str] = set()

    for tag_obj in tags:
        tag_name = tag_obj.get("name", "")
        yengo_tag = mapping.get(tag_name)
        if yengo_tag:
            yengo_tags.add(yengo_tag)
            logger.debug(f"Mapped tag '{tag_name}' → '{yengo_tag}'")

    # Return sorted for consistency
    return sorted(yengo_tags)


def get_hint_tags(tags: list[dict]) -> list[str]:
    """Extract tags marked as hints (isHint=1).

    Args:
        tags: List of tag objects from puzzle.

    Returns:
        List of tag names where isHint=1.
    """
    return [
        tag_obj.get("name", "")
        for tag_obj in tags
        if tag_obj.get("isHint") == 1
    ]


# ============================================================================
# Collection Mapping
# ============================================================================

@lru_cache(maxsize=1)
def _load_collections() -> dict[str, dict]:
    """Load collection definitions from sources.json."""
    sources = _load_sources()
    return sources.get("collections", {})


def get_collection_yengo_level(set_id: int) -> str | None:
    """Get YenGo level for a collection.

    Args:
        set_id: Collection/set ID.

    Returns:
        YenGo level slug or None if not defined.
    """
    collections = _load_collections()
    collection = collections.get(str(set_id), {})
    return collection.get("yengo_level")


def get_collection_info(set_id: int) -> dict | None:
    """Get collection metadata.

    Args:
        set_id: Collection/set ID.

    Returns:
        Collection dict or None if not found.
    """
    collections = _load_collections()
    return collections.get(str(set_id))


def get_enabled_collections() -> dict[str, dict]:
    """Get all enabled collections.

    Returns:
        Dict of set_id -> collection info for enabled collections.
    """
    collections = _load_collections()
    return {
        set_id: info
        for set_id, info in collections.items()
        if info.get("enabled", True)
    }
