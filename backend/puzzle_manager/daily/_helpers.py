"""Shared helpers for daily challenge modules.

Centralises puzzle identity resolution, path expansion, level/tag lookups,
deterministic seeding, and **config-driven tag rotation** used by
standard.py, timed.py, and by_tag.py.

All tag and level data is loaded exclusively from configuration files
(``config/tags.json``, ``config/puzzle-levels.json``) and cached via
``@lru_cache``.  No slugs, IDs, or category names are hardcoded here.

These are internal helpers — not part of the public API.
"""

import hashlib
import logging
from datetime import datetime
from functools import lru_cache

from backend.puzzle_manager.config.loader import ConfigLoader
from backend.puzzle_manager.models.daily import PuzzleRef
from backend.puzzle_manager.paths import to_posix_path

logger = logging.getLogger("puzzle_manager.daily")


# ---------------------------------------------------------------------------
# Level classification (config-driven, cached)
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def get_level_slug_categories() -> tuple[frozenset[str], frozenset[str], frozenset[str]]:
    """Load and categorize level slugs from config.

    Uses sparse Go-rank-aligned IDs (kyu=100s, dan=200s):
    - Beginner/easy: IDs < 140 (novice, beginner, elementary)
    - Intermediate/medium: IDs 140-159 (intermediate, upper-intermediate)
    - Advanced/hard: IDs >= 160 (advanced, low-dan, high-dan, expert)

    Returns:
        Tuple of (beginner_slugs, intermediate_slugs, advanced_slugs) as frozen sets.
    """
    loader = ConfigLoader()
    levels_data = loader.load_levels()
    levels = levels_data.get("levels", [])

    beginner = frozenset(lvl["slug"] for lvl in levels if lvl.get("id", 0) < 140)
    intermediate = frozenset(lvl["slug"] for lvl in levels if 140 <= lvl.get("id", 0) < 160)
    advanced = frozenset(lvl["slug"] for lvl in levels if lvl.get("id", 0) >= 160)

    return beginner, intermediate, advanced


@lru_cache(maxsize=1)
def get_level_numeric_categories() -> tuple[frozenset[int], frozenset[int], frozenset[int]]:
    """Load and categorize numeric level IDs from config.

    Supports compact entries where level is stored as numeric ID in ``l`` key.
    Uses sparse Go-rank-aligned IDs (kyu=100s, dan=200s):
    - Beginner/easy: 110, 120, 130 (novice, beginner, elementary)
    - Intermediate/medium: 140, 150 (intermediate, upper-intermediate)
    - Advanced/hard: 160, 210, 220, 230 (advanced through expert)

    Returns:
        Tuple of (beginner_ids, intermediate_ids, advanced_ids) as frozen sets.
    """
    loader = ConfigLoader()
    levels_data = loader.load_levels()
    levels = levels_data.get("levels", [])

    beginner = frozenset(lvl["id"] for lvl in levels if lvl.get("id", 0) < 140)
    intermediate = frozenset(lvl["id"] for lvl in levels if 140 <= lvl.get("id", 0) < 160)
    advanced = frozenset(lvl["id"] for lvl in levels if lvl.get("id", 0) >= 160)

    return beginner, intermediate, advanced


@lru_cache(maxsize=1)
def build_level_id_to_slug_map() -> dict[int, str]:
    """Build a mapping from numeric level ID to slug."""
    loader = ConfigLoader()
    levels_data = loader.load_levels()
    return {lvl["id"]: lvl["slug"] for lvl in levels_data.get("levels", [])}


@lru_cache(maxsize=1)
def build_level_slug_to_id_map() -> dict[str, int]:
    """Build a mapping from level slug to numeric ID."""
    return {v: k for k, v in build_level_id_to_slug_map().items()}


def resolve_level_slug(level_id: int | None) -> str:
    """Resolve a numeric level ID to its slug string.

    Returns empty string if *level_id* is ``None`` or unknown.
    """
    if level_id is None:
        return ""
    return build_level_id_to_slug_map().get(level_id, "")


# ---------------------------------------------------------------------------
# Tag lookups (config-driven, cached)
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def build_tag_slug_to_id_map() -> dict[str, int]:
    """Build a mapping from tag slug to numeric ID.

    Tags config structure: ``{"tags": {"slug": {"id": N, ...}, ...}}``.
    """
    loader = ConfigLoader()
    tags_data = loader.load_tags()
    slug_to_id: dict[str, int] = {}
    tags = tags_data.get("tags", {})
    for slug, info in tags.items():
        if isinstance(info, dict):
            tag_id = info.get("id")
            if tag_id is not None:
                slug_to_id[slug] = tag_id
    return slug_to_id


@lru_cache(maxsize=1)
def build_tag_id_to_slug_map() -> dict[int, str]:
    """Build a mapping from numeric tag ID to slug."""
    return {v: k for k, v in build_tag_slug_to_id_map().items()}


@lru_cache(maxsize=1)
def build_tag_rotation() -> tuple[str, ...]:
    """Return the full ordered tag rotation from ``config/tags.json``.

    Reads every tag entry from the canonical config and sorts them by their
    numeric ``id`` field.  This guarantees a stable, deterministic rotation
    order that automatically includes any tag added to the config — **no
    code change is ever required**.

    Returns a ``tuple`` (immutable + hashable) so that ``@lru_cache`` can
    cache the result correctly.

    Example (abridged, actual order determined by config IDs)::

        ("life-and-death", "living", "ko", ..., "tesuji", "joseki", "fuseki")
    """
    loader = ConfigLoader()
    tags_data = loader.load_tags()
    tags = tags_data.get("tags", {})
    # Sort by numeric ID for stable, deterministic ordering
    id_slug_pairs = sorted(
        (info["id"], slug)
        for slug, info in tags.items()
        if isinstance(info, dict) and "id" in info
    )
    return tuple(slug for _, slug in id_slug_pairs)


@lru_cache(maxsize=1)
def build_tag_category_map() -> dict[str, str]:
    """Build a mapping from tag slug to its category string.

    Category values come directly from ``config/tags.json`` (e.g.
    ``"objective"``, ``"tesuji"``, ``"technique"``).  Used by
    :mod:`~backend.puzzle_manager.daily.by_tag` to find thematically
    related tags when the primary tag pool is too small.

    Returns:
        Dict of ``{slug: category}`` for every tag in config.
    """
    loader = ConfigLoader()
    tags_data = loader.load_tags()
    tags = tags_data.get("tags", {})
    return {
        slug: info.get("category", "")
        for slug, info in tags.items()
        if isinstance(info, dict)
    }


# ---------------------------------------------------------------------------
# Puzzle identity & path expansion
# ---------------------------------------------------------------------------


def extract_puzzle_id(puzzle: dict) -> str:
    """Extract puzzle ID from compact format.

    Compact: ``"0001/hash"`` → ``"hash"``
    """
    p = puzzle.get("p", "")
    if p:
        return p.split("/")[-1] if "/" in p else p
    return ""


def to_puzzle_ref(puzzle: dict) -> PuzzleRef:
    """Convert compact puzzle dict to ``PuzzleRef`` with POSIX path normalization.

    Compact path ``"0001/hash"`` is expanded to ``"sgf/0001/hash.sgf"``.
    """
    compact_path = puzzle.get("p", "")
    puzzle_id = compact_path.split("/")[-1] if "/" in compact_path else compact_path
    full_path = f"sgf/{compact_path}.sgf" if compact_path else ""
    level_slug = resolve_level_slug(puzzle.get("l"))
    return PuzzleRef(
        id=puzzle_id,
        path=to_posix_path(full_path),
        level=level_slug,
    )


# ---------------------------------------------------------------------------
# Deterministic seeding
# ---------------------------------------------------------------------------


def date_seed(date: datetime, salt: str = "") -> int:
    """Generate deterministic seed from *date* and optional *salt*.

    Uses MD5 for speed (not security). Produces a 32-bit unsigned int.
    """
    date_str = f"{date.strftime('%Y-%m-%d')}-{salt}"
    hash_bytes = hashlib.md5(date_str.encode()).digest()
    return int.from_bytes(hash_bytes[:4], byteorder="big")


# ---------------------------------------------------------------------------
# Puzzle hash for deterministic ordering
# ---------------------------------------------------------------------------


def puzzle_hash(puzzle: dict, seed: int, salt: str = "") -> str:
    """Generate hash for puzzle ordering (deterministic selection).

    Uses puzzle ID + seed + salt for differentiation between modules.
    """
    pid = extract_puzzle_id(puzzle)
    hash_input = f"{pid}-{seed}-{salt}"
    return hashlib.md5(hash_input.encode()).hexdigest()
