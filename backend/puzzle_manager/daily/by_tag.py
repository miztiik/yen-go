"""
Tag-based challenge generator.

Generates challenges focused on specific techniques (tags).
Supports both compact {p, l, t, c, x} entries and legacy {id, path, level, tags} dicts.

Tag rotation and related-tag fallback are **fully config-driven**: all slugs,
categories, and ordering are loaded exclusively from ``config/tags.json`` via
:mod:`backend.puzzle_manager.daily._helpers`.  No tag slugs are hardcoded here.
Adding or renaming a tag in the config file is immediately reflected in the
daily rotation without any code change.
"""

import logging
from collections.abc import Sequence
from datetime import datetime

from backend.puzzle_manager.config.loader import ConfigLoader
from backend.puzzle_manager.daily._helpers import (
    build_tag_category_map as _build_tag_category_map,
)
from backend.puzzle_manager.daily._helpers import (
    build_tag_rotation as _build_tag_rotation,
)
from backend.puzzle_manager.daily._helpers import (
    build_tag_slug_to_id_map as _build_tag_slug_to_id_map,
)
from backend.puzzle_manager.daily._helpers import (
    date_seed as _date_seed,
)
from backend.puzzle_manager.daily._helpers import (
    puzzle_hash as _puzzle_hash_impl,
)
from backend.puzzle_manager.daily._helpers import (
    to_puzzle_ref as _to_puzzle_ref,
)
from backend.puzzle_manager.models.config import DailyConfig
from backend.puzzle_manager.models.daily import PuzzleRef, TagChallenge

logger = logging.getLogger("puzzle_manager.daily.by_tag")


def generate_tag_challenge(
    date: datetime,
    pool: Sequence[dict],
    config: DailyConfig,
) -> TagChallenge:
    """Generate tag-focused challenge for the day.

    The tag is chosen by rotating through **all tags defined in
    ``config/tags.json``**, ordered by their numeric ``id`` field.  This
    means every new tag added to the config is automatically included in the
    rotation — no code change required.

    Fallback strategy when the primary tag pool is too small:
    1. Related tags (siblings in the same config ``category``) are tried.
    2. If still insufficient, the full puzzle pool is used.

    Supports both compact entries (numeric tag IDs in ``"t"`` key) and
    legacy entries (slug strings in ``"tags"`` key).

    Args:
        date: Date for the challenge.
        pool: Available puzzle pool.
        config: Daily configuration.

    Returns:
        TagChallenge focused on a specific technique.
    """
    # Determine tag for the day (rotate through ALL config tags by ID order)
    rotation = _build_tag_rotation()
    if not rotation:
        logger.error("Tag rotation is empty — config/tags.json has no tags with 'id' fields")
        return TagChallenge()
    day_of_year = date.timetuple().tm_yday
    tag_index = day_of_year % len(rotation)
    selected_tag = rotation[tag_index]

    # Use tag_puzzle_count for tag-specific threshold (L5 fix: not the standard 30-puzzle count)
    target_count = config.tag_puzzle_count

    # Filter puzzles by tag (supports both compact and legacy formats)
    tagged_puzzles = [p for p in pool if _has_tag(p, selected_tag)]

    # If not enough puzzles with tag, use related tags
    if len(tagged_puzzles) < target_count:
        logger.warning(
            f"Tag '{selected_tag}': {len(tagged_puzzles)} puzzles (target: {target_count}) - using related tags"
        )
        related_tags = _get_related_tags(selected_tag)
        for related in related_tags:
            additional = [p for p in pool if _has_tag(p, related)]
            tagged_puzzles.extend(additional)
            if len(tagged_puzzles) >= target_count * 2:
                break

    # If still not enough, fall back to any puzzles
    if len(tagged_puzzles) < target_count:
        logger.warning(
            f"Tag '{selected_tag}': {len(tagged_puzzles)} puzzles after related tags - falling back to full pool"
        )
        tagged_puzzles = list(pool)

    # Select puzzles deterministically; salt by tag slug for cross-module differentiation (M8 fix)
    seed = _date_seed(date, f"tag-{selected_tag}")
    puzzles = _select_puzzles(tagged_puzzles, config.puzzles_per_day, seed, salt=selected_tag)

    # Get tag info
    tag_info = _get_tag_info(selected_tag)

    return TagChallenge(
        tag=selected_tag,
        tag_display_name=tag_info.get("display_name", selected_tag.replace("-", " ").title()),
        tag_description=tag_info.get("description", ""),
        puzzles=puzzles,
        total=len(puzzles),  # T051: Set total = len(puzzles)
    )


def _get_related_tags(tag: str) -> list[str]:
    """Return tags in the same config category as *tag*, excluding *tag* itself.

    Fully config-driven: reads ``category`` from each entry in
    ``config/tags.json`` via :func:`~backend.puzzle_manager.daily._helpers.build_tag_category_map`.
    Adding a new tag to the config automatically makes it eligible as a
    fallback without any code change.

    Args:
        tag: The primary tag slug whose siblings we want.

    Returns:
        List of sibling tag slugs (same category, sorted by config ID for
        determinism), or empty list if the tag is unknown.
    """
    category_map = _build_tag_category_map()
    tag_category = category_map.get(tag, "")
    if not tag_category:
        logger.debug(f"_get_related_tags: unknown tag '{tag}' — no category in config")
        return []
    # Return siblings in the same category, preserving config-ID order via tag rotation
    rotation = _build_tag_rotation()
    return [
        slug for slug in rotation
        if category_map.get(slug) == tag_category and slug != tag
    ]


def _has_tag(puzzle: dict, tag_slug: str) -> bool:
    """Check if a puzzle has a given tag.

    Uses compact format: numeric tag IDs in ``"t"`` key.
    """
    tag_ids = puzzle.get("t") or []
    if tag_ids:
        slug_to_id = _build_tag_slug_to_id_map()
        target_id = slug_to_id.get(tag_slug)
        if target_id is not None:
            return target_id in tag_ids
    return False


def _get_tag_info(tag: str) -> dict:
    """Get tag display info from config.

    Tags config structure: ``{"tags": {"slug": {"id": N, "name": "...", ...}, ...}}``.
    """
    try:
        loader = ConfigLoader()  # M1 fix: use module-level import, not deferred
        tags_config = loader.load_tags()
        tag_entry = tags_config.get("tags", {}).get(tag, {})
        if isinstance(tag_entry, dict) and tag_entry:
            return {
                "display_name": tag_entry.get("name", tag.replace("-", " ").title()),
                "description": tag_entry.get("description", ""),
            }
        return {}
    except Exception:
        return {}


def _select_puzzles(
    pool: Sequence[dict],
    count: int,
    seed: int,
    salt: str = "",
) -> list[PuzzleRef]:
    """Select ``count`` puzzles deterministically from *pool*.

    Args:
        pool: Candidate puzzles.
        count: Maximum number of puzzles to return.
        seed: Deterministic seed from :func:`date_seed`.
        salt: Additional salt string for per-module differentiation (M8 fix).
    """
    if not pool:
        return []

    ordered = sorted(pool, key=lambda p: _puzzle_hash_impl(p, seed, salt=salt))

    seen: set[str] = set()
    selected: list[PuzzleRef] = []
    for puzzle in ordered:
        ref = _to_puzzle_ref(puzzle)
        if ref.id not in seen:
            seen.add(ref.id)
            selected.append(ref)
        if len(selected) >= count:
            break

    return selected
