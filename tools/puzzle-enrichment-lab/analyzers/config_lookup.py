"""Centralized config lookup for tag/level resolution (Phase 1 DRY consolidation).

Single source of truth for loading and caching config/tags.json and
config/puzzle-levels.json data. Replaces duplicate loaders in
enrich_single.py, estimate_difficulty.py, sgf_enricher.py, and
validate_correct_move.py.

All caches can be reset via ``clear_config_caches()`` for test isolation (MH-1).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Project root detection (MH-2)
# ---------------------------------------------------------------------------


def _find_project_root() -> Path:
    """Walk up from this file until we find the ``config/`` directory.

    Returns the project root (parent of ``config/``).
    Distinguishes the project config dir (contains tags.json) from
    the Python config package by checking for tags.json.
    """
    current = Path(__file__).resolve().parent
    for _ in range(10):  # safety limit
        if (current / "config" / "tags.json").is_file():
            return current
        current = current.parent
    # Fallback: assume tools/puzzle-enrichment-lab/analyzers → 3 parents up
    return Path(__file__).resolve().parents[3]


# ---------------------------------------------------------------------------
# Module-level caches
# ---------------------------------------------------------------------------

_TAG_SLUG_TO_ID: dict[str, int] | None = None
_TAG_ID_TO_NAME: dict[int, str] | None = None
_LEVEL_ID_MAP: dict[int, tuple[str, str]] | None = None
_LEVEL_SLUG_TO_ID: dict[str, int] | None = None


def clear_config_caches() -> None:
    """Reset all module-level caches (MH-1: test isolation)."""
    global _TAG_SLUG_TO_ID, _TAG_ID_TO_NAME, _LEVEL_ID_MAP, _LEVEL_SLUG_TO_ID
    _TAG_SLUG_TO_ID = None
    _TAG_ID_TO_NAME = None
    _LEVEL_ID_MAP = None
    _LEVEL_SLUG_TO_ID = None


# ---------------------------------------------------------------------------
# Tag loaders
# ---------------------------------------------------------------------------


def load_tag_slug_map() -> dict[str, int]:
    """Load and cache tag slug → numeric ID mapping from config/tags.json.

    Includes aliases so that e.g. ``load_tag_slug_map()["living"]`` resolves
    to the same ID as ``"life-and-death"``.
    """
    global _TAG_SLUG_TO_ID
    if _TAG_SLUG_TO_ID is not None:
        return _TAG_SLUG_TO_ID

    tags_path = _find_project_root() / "config" / "tags.json"
    slug_to_id: dict[str, int] = {}
    if tags_path.exists():
        data = json.loads(tags_path.read_text(encoding="utf-8"))
        tags_section = data.get("tags", {})
        for slug, tag_obj in tags_section.items():
            tag_id = tag_obj.get("id") if isinstance(tag_obj, dict) else None
            if tag_id is not None:
                slug_to_id[slug] = tag_id
                for alias in tag_obj.get("aliases", []):
                    slug_to_id[alias] = tag_id
    else:
        logger.warning("tags.json not found: %s", tags_path)

    _TAG_SLUG_TO_ID = slug_to_id
    return _TAG_SLUG_TO_ID


def load_tag_id_to_name() -> dict[int, str]:
    """Load and cache tag numeric ID → human-readable name mapping."""
    global _TAG_ID_TO_NAME
    if _TAG_ID_TO_NAME is not None:
        return _TAG_ID_TO_NAME

    tags_path = _find_project_root() / "config" / "tags.json"
    id_to_name: dict[int, str] = {}
    if tags_path.exists():
        data = json.loads(tags_path.read_text(encoding="utf-8"))
        tags_section = data.get("tags", {})
        for _slug, tag_obj in tags_section.items():
            if isinstance(tag_obj, dict):
                tag_id = tag_obj.get("id")
                tag_name = tag_obj.get("name", _slug)
                if tag_id is not None:
                    id_to_name[tag_id] = tag_name

    _TAG_ID_TO_NAME = id_to_name
    return _TAG_ID_TO_NAME


# ---------------------------------------------------------------------------
# Level loaders
# ---------------------------------------------------------------------------


def load_level_id_map() -> dict[int, tuple[str, str]]:
    """Load and cache level ID → (name, rank_range) mapping from puzzle-levels.json."""
    global _LEVEL_ID_MAP
    if _LEVEL_ID_MAP is not None:
        return _LEVEL_ID_MAP

    levels_path = _find_project_root() / "config" / "puzzle-levels.json"
    id_map: dict[int, tuple[str, str]] = {}
    if levels_path.exists():
        data = json.loads(levels_path.read_text(encoding="utf-8"))
        for level in data.get("levels", []):
            level_id = level.get("id")
            name = level.get("name", "")
            rank_range = level.get("rankRange", {})
            range_str = f"{rank_range.get('min', '')}\u2013{rank_range.get('max', '')}" if rank_range else ""
            if level_id is not None:
                id_map[level_id] = (name, range_str)
    else:
        logger.warning("puzzle-levels.json not found: %s", levels_path)

    _LEVEL_ID_MAP = id_map
    return _LEVEL_ID_MAP


def load_level_slug_to_id() -> dict[str, int]:
    """Load and cache level slug → numeric ID mapping from puzzle-levels.json.

    Returns dict like {"novice": 110, "beginner": 120, ..., "expert": 230}.
    Used by sgf_enricher and estimate_difficulty.
    """
    global _LEVEL_SLUG_TO_ID
    if _LEVEL_SLUG_TO_ID is not None:
        return _LEVEL_SLUG_TO_ID

    levels_path = _find_project_root() / "config" / "puzzle-levels.json"
    slug_map: dict[str, int] = {}
    if levels_path.exists():
        data = json.loads(levels_path.read_text(encoding="utf-8"))
        for level in data.get("levels", []):
            slug = level.get("slug", "")
            level_id = level.get("id", 0)
            if slug and level_id:
                slug_map[slug] = level_id

    _LEVEL_SLUG_TO_ID = slug_map
    return _LEVEL_SLUG_TO_ID


# ---------------------------------------------------------------------------
# Resolver helpers
# ---------------------------------------------------------------------------


def resolve_tag_names(tag_ids: list[int]) -> list[str]:
    """Resolve numeric tag IDs to human-readable names."""
    id_to_name = load_tag_id_to_name()
    return [id_to_name.get(tid, f"tag-{tid}") for tid in tag_ids]


def resolve_level_info(level_id: int) -> tuple[str, str]:
    """Resolve numeric level ID to (name, rank_range) tuple."""
    level_map = load_level_id_map()
    return level_map.get(level_id, ("", ""))


# ---------------------------------------------------------------------------
# Tag parsing
# ---------------------------------------------------------------------------


def parse_tag_ids(yt_value: str) -> list[int]:
    """Parse YT property value into numeric tag IDs.

    Handles both formats:
    - Numeric comma-separated: "10,12,34"
    - Slug comma-separated: "life-and-death,ko,ladder"

    For slug format, looks up IDs from config/tags.json (cached after first load).
    Returns empty list if parsing fails.
    """
    parts = [p.strip() for p in yt_value.split(",") if p.strip()]
    if not parts:
        return []

    # Try numeric first
    try:
        return [int(p) for p in parts]
    except ValueError:
        pass

    # Fall back to cached slug lookup
    try:
        slug_to_id = load_tag_slug_map()
        result = []
        for part in parts:
            tag_id = slug_to_id.get(part)
            if tag_id is not None:
                result.append(tag_id)
            else:
                logger.warning("Unknown tag slug '%s' in YT property", part)
        return result
    except Exception as e:
        logger.warning("Failed to parse tag slugs from YT='%s': %s", yt_value, e)

    return []


# ---------------------------------------------------------------------------
# Metadata extraction
# ---------------------------------------------------------------------------


def extract_metadata(root) -> dict:
    """Extract puzzle metadata from SGF root node properties.

    Returns dict with keys: puzzle_id, tags, corner, move_order, ko_type, collection.
    """
    puzzle_id = root.get("GN", "")

    tags: list[int] = []
    yt_raw = root.get("YT", "")
    if yt_raw:
        tags = parse_tag_ids(yt_raw)

    corner = root.get("YC", "TL")
    if corner not in ("TL", "TR", "BL", "BR", "C", "E"):
        corner = "TL"

    move_order = root.get("YO", "strict")
    if move_order not in ("strict", "flexible", "miai"):
        move_order = "strict"

    ko_type = root.get("YK", "none")
    if ko_type not in ("none", "direct", "approach"):
        ko_type = "none"

    collection_raw = root.get("YL", "")
    collection = collection_raw if collection_raw else ""

    return {
        "puzzle_id": puzzle_id,
        "tags": tags,
        "corner": corner,
        "move_order": move_order,
        "ko_type": ko_type,
        "collection": collection,
    }


def extract_level_slug(root) -> str | None:
    """Extract level slug from SGF YG property.

    Returns None if YG is not set.
    """
    try:
        yg = root.get("YG")
        if yg and isinstance(yg, str):
            return yg.strip("[]").strip()
    except Exception:
        pass
    return None
