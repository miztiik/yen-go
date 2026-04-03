"""Constants and mappings for puzzle manager.

Single source of truth for level mappings and other shared constants.
This module has NO imports from puzzle_manager to avoid circular dependencies.

Usage:
    from backend.puzzle_manager.core.constants import (
        SLUG_TO_LEVEL, LEVEL_TO_SLUG, VALID_LEVEL_SLUGS, get_valid_level_slugs
    )

    # Convert slug to numeric level
    level = SLUG_TO_LEVEL.get("beginner")  # Returns 2

    # Convert level to slug
    slug = LEVEL_TO_SLUG.get(2)  # Returns "beginner"

    # Check validity
    if "beginner" in VALID_LEVEL_SLUGS:
        ...

    # Get cached set (for modules that lazy-load)
    valid_slugs = get_valid_level_slugs()
"""

from typing import Final

# Authoritative slug-to-level mapping
# Matches config/puzzle-levels.json structure
SLUG_TO_LEVEL: Final[dict[str, int]] = {
    "novice": 1,
    "beginner": 2,
    "elementary": 3,
    "intermediate": 4,
    "upper-intermediate": 5,
    "advanced": 6,
    "low-dan": 7,
    "high-dan": 8,
    "expert": 9,
}

# Reverse mapping: level number to slug
LEVEL_TO_SLUG: Final[dict[int, str]] = {v: k for k, v in SLUG_TO_LEVEL.items()}

# Valid level slugs as a frozenset for O(1) membership testing
VALID_LEVEL_SLUGS: Final[frozenset[str]] = frozenset(SLUG_TO_LEVEL.keys())

# Level bounds
MIN_LEVEL: Final[int] = 1
MAX_LEVEL: Final[int] = 9

# Board size bounds (matches config/puzzle-validation.json)
MIN_BOARD_SIZE: Final[int] = 5
MAX_BOARD_SIZE: Final[int] = 19

# Valid slugs as a list (for iteration where order matters)
VALID_LEVEL_SLUGS_ORDERED: Final[tuple[str, ...]] = (
    "novice", "beginner", "elementary", "intermediate",
    "upper-intermediate", "advanced", "low-dan", "high-dan", "expert",
)


def get_valid_level_slugs() -> frozenset[str]:
    """Get valid level slugs (for compatibility with lazy-loading patterns).

    This function exists for backward compatibility with code that used
    cached lazy-loading patterns. The return value is always VALID_LEVEL_SLUGS.

    Returns:
        Frozenset of valid level slugs.

    Example:
        >>> slugs = get_valid_level_slugs()
        >>> "beginner" in slugs
        True
    """
    return VALID_LEVEL_SLUGS
