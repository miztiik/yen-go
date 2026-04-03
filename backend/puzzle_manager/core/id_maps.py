"""Numeric ID lookup maps for levels, tags, collections, and quality.

Builds bidirectional slug ↔ id maps from config files.
Used by publish stage to construct compact view entries.

Design decisions:
- Level IDs: sparse, Go-rank-aligned (110-230)
- Tag IDs: sparse by category (Obj 10-28, Tesuji 30-52, Tech 60-82)
- Collection IDs: sequential (1-159+)
- Quality IDs: 0 (unassigned), 1-5 (from puzzle-quality.json)
"""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path

from backend.puzzle_manager.paths import get_global_config_dir

logger = logging.getLogger("puzzle_manager.core.id_maps")


class IdMaps:
    """Bidirectional slug ↔ id maps for levels, tags, collections, and quality.

    Usage:
        maps = IdMaps.load()
        level_id = maps.level_slug_to_id("elementary")  # 130
        slug = maps.level_id_to_slug(130)                # "elementary"
        tag_id = maps.tag_slug_to_id("ladder")           # 34
        col_id = maps.collection_slug_to_id("cho-chikun-life-death-elementary")  # 6
        q_id = maps.quality_slug_to_id("standard")       # 3
    """

    def __init__(
        self,
        level_slug_to_id_map: dict[str, int],
        level_id_to_slug_map: dict[int, str],
        tag_slug_to_id_map: dict[str, int],
        tag_id_to_slug_map: dict[int, str],
        collection_slug_to_id_map: dict[str, int],
        collection_id_to_slug_map: dict[int, str],
        quality_slug_to_id_map: dict[str, int] | None = None,
        quality_id_to_slug_map: dict[int, str] | None = None,
    ) -> None:
        self._level_slug_to_id = level_slug_to_id_map
        self._level_id_to_slug = level_id_to_slug_map
        self._tag_slug_to_id = tag_slug_to_id_map
        self._tag_id_to_slug = tag_id_to_slug_map
        self._collection_slug_to_id = collection_slug_to_id_map
        self._collection_id_to_slug = collection_id_to_slug_map
        self._quality_slug_to_id = quality_slug_to_id_map or _default_quality_slug_to_id()
        self._quality_id_to_slug = quality_id_to_slug_map or _default_quality_id_to_slug()

        # Display name maps (id → human-readable name)
        self._level_id_to_name: dict[int, str] = {}
        self._tag_id_to_name: dict[int, str] = {}
        self._collection_id_to_name: dict[int, str] = {}
        self._quality_id_to_name: dict[int, str] = {}

    # --- Dimension label resolution ---

    _PREFIX_TO_DIMENSION = {"c": "collection", "l": "level", "q": "quality", "t": "tag"}

    def resolve_dimension_label(self, prefix: str, numeric_id: int) -> str:
        """Resolve a dimension prefix + numeric ID to a human-readable name.

        Falls back to '{prefix}{id}' if the ID is unknown.

        Args:
            prefix: Dimension prefix ('c', 'l', 'q', 't').
            numeric_id: Numeric ID within that dimension.

        Returns:
            Human-readable display name.
        """
        name_map: dict[int, str] = {
            "l": self._level_id_to_name,
            "t": self._tag_id_to_name,
            "c": self._collection_id_to_name,
            "q": self._quality_id_to_name,
        }.get(prefix, {})
        return name_map.get(numeric_id, f"{prefix}{numeric_id}")

    # --- Level lookups ---

    def level_slug_to_id(self, slug: str) -> int:
        """Convert level slug to sparse numeric ID.

        Raises:
            KeyError: If slug is not found.
        """
        return self._level_slug_to_id[slug]

    def level_id_to_slug(self, id_: int) -> str:
        """Convert sparse numeric ID to level slug.

        Raises:
            KeyError: If ID is not found.
        """
        return self._level_id_to_slug[id_]

    def level_slug_to_id_safe(self, slug: str) -> int | None:
        """Convert level slug to ID, returning None if not found."""
        return self._level_slug_to_id.get(slug)

    # --- Tag lookups ---

    def tag_slug_to_id_safe(self, slug: str) -> int | None:
        """Convert tag slug to ID, returning None if not found."""
        return self._tag_slug_to_id.get(slug)

    def tag_slug_to_id(self, slug: str) -> int:
        """Convert tag slug to sparse numeric ID.

        Raises:
            KeyError: If slug is not found.
        """
        return self._tag_slug_to_id[slug]

    def tag_id_to_slug(self, id_: int) -> str:
        """Convert sparse numeric ID to tag slug.

        Raises:
            KeyError: If ID is not found.
        """
        return self._tag_id_to_slug[id_]

    def tag_slugs_to_ids(self, slugs: list[str]) -> list[int]:
        """Convert list of tag slugs to sorted list of numeric IDs.

        Unknown slugs are logged and skipped.
        """
        ids: list[int] = []
        for slug in slugs:
            id_ = self._tag_slug_to_id.get(slug)
            if id_ is not None:
                ids.append(id_)
            else:
                logger.warning(f"Unknown tag slug: {slug}")
        return sorted(ids)

    # --- Collection lookups ---

    def collection_slug_to_id(self, slug: str) -> int:
        """Convert collection slug to sequential numeric ID.

        Raises:
            KeyError: If slug is not found.
        """
        return self._collection_slug_to_id[slug]

    def collection_id_to_slug(self, id_: int) -> str:
        """Convert sequential numeric ID to collection slug.

        Raises:
            KeyError: If ID is not found.
        """
        return self._collection_id_to_slug[id_]

    def collection_slug_to_id_safe(self, slug: str) -> int | None:
        """Convert collection slug to ID, returning None if not found."""
        return self._collection_slug_to_id.get(slug)

    def collection_slugs_to_ids(self, slugs: list[str]) -> list[int]:
        """Convert list of collection slugs to sorted list of numeric IDs.

        Unknown slugs are logged and skipped.
        """
        ids: list[int] = []
        for slug in slugs:
            id_ = self._collection_slug_to_id.get(slug)
            if id_ is not None:
                ids.append(id_)
            else:
                logger.warning(f"Unknown collection slug: {slug}")
        return sorted(ids)

    # --- Quality lookups ---

    def quality_slug_to_id(self, slug: str) -> int:
        """Convert quality slug to numeric ID.

        Raises:
            KeyError: If slug is not found.
        """
        return self._quality_slug_to_id[slug]

    def quality_id_to_slug(self, id_: int) -> str:
        """Convert numeric ID to quality slug.

        Raises:
            KeyError: If ID is not found.
        """
        return self._quality_id_to_slug[id_]

    def quality_slug_to_id_safe(self, slug: str) -> int | None:
        """Convert quality slug to ID, returning None if not found."""
        return self._quality_slug_to_id.get(slug)

    def quality_id_to_slug_safe(self, id_: int) -> str | None:
        """Convert quality ID to slug, returning None if not found."""
        return self._quality_id_to_slug.get(id_)

    # --- Factory ---

    @classmethod
    def load(cls, config_dir: Path | None = None) -> IdMaps:
        """Load ID maps from config files.

        Args:
            config_dir: Directory containing puzzle-levels.json, tags.json,
                       collections.json. Defaults to config/.

        Returns:
            IdMaps instance with all lookups ready.
        """
        config_dir = config_dir or get_global_config_dir()
        quality_path = config_dir / "puzzle-quality.json"
        quality_maps = _build_quality_maps(quality_path) if quality_path.exists() else (None, None, None)

        level_s2i, level_i2s, level_i2n = _build_level_maps(config_dir / "puzzle-levels.json")
        tag_s2i, tag_i2s, tag_i2n = _build_tag_maps(config_dir / "tags.json")
        col_s2i, col_i2s, col_i2n = _build_collection_maps(config_dir / "collections.json")

        instance = cls(
            level_slug_to_id_map=level_s2i,
            level_id_to_slug_map=level_i2s,
            tag_slug_to_id_map=tag_s2i,
            tag_id_to_slug_map=tag_i2s,
            collection_slug_to_id_map=col_s2i,
            collection_id_to_slug_map=col_i2s,
            quality_slug_to_id_map=quality_maps[0] if quality_maps else None,
            quality_id_to_slug_map=quality_maps[1] if quality_maps else None,
        )

        # Populate display name maps
        instance._level_id_to_name = level_i2n
        instance._tag_id_to_name = tag_i2n
        instance._collection_id_to_name = col_i2n
        instance._quality_id_to_name = quality_maps[2] if quality_maps and len(quality_maps) > 2 else {}

        return instance


def _build_level_maps(path: Path) -> tuple[dict[str, int], dict[int, str], dict[int, str]]:
    """Build level slug↔id maps and id→name map from puzzle-levels.json."""
    data = json.loads(path.read_text(encoding="utf-8"))
    slug_to_id: dict[str, int] = {}
    id_to_slug: dict[int, str] = {}
    id_to_name: dict[int, str] = {}
    for level in data["levels"]:
        slug_to_id[level["slug"]] = level["id"]
        id_to_slug[level["id"]] = level["slug"]
        id_to_name[level["id"]] = level.get("name", level["slug"])
    return slug_to_id, id_to_slug, id_to_name


def _build_tag_maps(path: Path) -> tuple[dict[str, int], dict[int, str], dict[int, str]]:
    """Build tag slug↔id maps and id→name map from tags.json."""
    data = json.loads(path.read_text(encoding="utf-8"))
    slug_to_id: dict[str, int] = {}
    id_to_slug: dict[int, str] = {}
    id_to_name: dict[int, str] = {}
    for slug, tag_data in data["tags"].items():
        tag_id = tag_data.get("id")
        if tag_id is not None:
            slug_to_id[slug] = tag_id
            id_to_slug[tag_id] = slug
            id_to_name[tag_id] = tag_data.get("name", slug)
        else:
            logger.warning(f"Tag {slug} missing id")
    return slug_to_id, id_to_slug, id_to_name


def _build_collection_maps(path: Path) -> tuple[dict[str, int], dict[int, str], dict[int, str]]:
    """Build collection slug↔id maps and id→name map from collections.json."""
    data = json.loads(path.read_text(encoding="utf-8"))
    slug_to_id: dict[str, int] = {}
    id_to_slug: dict[int, str] = {}
    id_to_name: dict[int, str] = {}
    for col in data["collections"]:
        col_id = col.get("id")
        if col_id is not None:
            slug_to_id[col["slug"]] = col_id
            id_to_slug[col_id] = col["slug"]
            id_to_name[col_id] = col.get("name", col["slug"])
    return slug_to_id, id_to_slug, id_to_name


def _build_quality_maps(path: Path) -> tuple[dict[str, int], dict[int, str], dict[int, str]]:
    """Build quality slug↔id maps and id→name map from puzzle-quality.json.

    Quality levels use integer keys (1-5) with slug = name field.
    ID 0 is reserved for 'unassigned' (none bucket).
    """
    data = json.loads(path.read_text(encoding="utf-8"))
    slug_to_id: dict[str, int] = {"unassigned": 0}
    id_to_slug: dict[int, str] = {0: "unassigned"}
    id_to_name: dict[int, str] = {0: "Unassigned"}
    for key_str, level_data in data.get("levels", {}).items():
        try:
            quality_id = int(key_str)
        except ValueError:
            logger.warning(f"Non-integer quality key: {key_str}")
            continue
        slug = level_data.get("name", key_str)
        display_name = level_data.get("display_label", slug.title())
        slug_to_id[slug] = quality_id
        id_to_slug[quality_id] = slug
        id_to_name[quality_id] = display_name
    return slug_to_id, id_to_slug, id_to_name


def _default_quality_slug_to_id() -> dict[str, int]:
    """Default quality slug→id map when config is unavailable."""
    return {
        "unassigned": 0, "unverified": 1, "basic": 2,
        "standard": 3, "high": 4, "premium": 5,
    }


def _default_quality_id_to_slug() -> dict[int, str]:
    """Default quality id→slug map when config is unavailable."""
    return {v: k for k, v in _default_quality_slug_to_id().items()}


@lru_cache(maxsize=1)
def get_default_id_maps() -> IdMaps:
    """Get the default singleton IdMaps (cached).

    Returns:
        IdMaps loaded from config/ directory.
    """
    return IdMaps.load()


def parse_yx(yx_string: str | None) -> list[int]:
    """Parse YX complexity string into positional array [d, r, s, u].

    The ``a`` (avg_refutation_depth) sub-field is parsed but NOT included
    in the returned array — it is only used for quality scoring, not in
    puzzle entries. Use ``parse_yx_full()`` to access all fields including ``a``.

    Args:
        yx_string: String like "d:3;r:2;s:19;u:1" or "d:3;r:2;s:19;u:1;a:2".

    Returns:
        List of 4 integers [depth, responses, size, unique].
        Returns [0, 0, 0, 0] if input is None or unparseable.
    """
    if not yx_string:
        return [0, 0, 0, 0]

    result = {"d": 0, "r": 0, "s": 0, "u": 0}
    try:
        for part in yx_string.split(";"):
            key, value = part.split(":")
            key = key.strip()
            if key in result:
                result[key] = int(value.strip())
    except (ValueError, IndexError):
        logger.warning(f"Failed to parse YX string: {yx_string}")
        return [0, 0, 0, 0]

    return [result["d"], result["r"], result["s"], result["u"]]


def parse_yx_full(yx_string: str | None) -> dict[str, int]:
    """Parse YX complexity string into a full dict including all sub-fields.

    Returns all known fields: d (depth), r (reading count), s (stone count),
    u (unique first move), a (avg refutation depth).

    Args:
        yx_string: String like "d:3;r:2;s:19;u:1;a:2" or None.

    Returns:
        Dict with keys d, r, s, u, a. Missing fields default to 0.
    """
    result = {"d": 0, "r": 0, "s": 0, "u": 0, "a": 0}
    if not yx_string:
        return result

    try:
        for part in yx_string.split(";"):
            key, value = part.split(":")
            key = key.strip()
            if key in result:
                result[key] = int(value.strip())
    except (ValueError, IndexError):
        logger.warning(f"Failed to parse YX string: {yx_string}")

    return result


def build_batch_ref(rel_path: str) -> str:
    """Build compact batch reference from a relative SGF path.

    Transforms: "sgf/0001/fc38f029205dde14.sgf" -> "0001/fc38f029205dde14"

    Also handles legacy paths:
        "sgf/level/batch-0001/hash.sgf" -> "0001/hash" (strips level + batch- prefix)

    Args:
        rel_path: Relative path like "sgf/0001/hash.sgf"
                  or "sgf/level/batch-0001/hash.sgf" (legacy).

    Returns:
        Batch reference string like "0001/fc38f029205dde14".
    """
    from pathlib import PurePosixPath

    p = PurePosixPath(rel_path)
    stem = p.stem  # content hash (no .sgf)
    parent = p.parent.name  # batch dir name (0001 or batch-0001)

    # Strip "batch-" prefix if present (legacy format)
    if parent.startswith("batch-"):
        parent = parent[6:]

    return f"{parent}/{stem}"
