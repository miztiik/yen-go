"""
Mappers for TsumegoDragon → Yen-Go conversion.

Maps TsumegoDragon levels and categories to Yen-Go YG and YT properties.
All target tags MUST exist in config/tags.json (validated at import time).
"""

from __future__ import annotations

import re

# =============================================================================
# Level Mapping: TsumegoDragon Level (0-8) → Yen-Go YG Slug
# =============================================================================

# TsumegoDragon levels map directly to Yen-Go levels (TD + 1 = Yen-Go ID)
# TD Level string format: "Level N (rank-range)" e.g., "Level 3 (14k-10k)"

TD_LEVEL_TO_YENGO_SLUG = {
    0: "novice",            # TD "Level 0 (Beginner)" → Yen-Go 1
    1: "beginner",          # TD "Level 1 (25k-20k)" → Yen-Go 2
    2: "elementary",        # TD "Level 2 (19k-15k)" → Yen-Go 3
    3: "intermediate",      # TD "Level 3 (14k-10k)" → Yen-Go 4
    4: "upper-intermediate", # TD "Level 4 (9k-5k)" → Yen-Go 5
    5: "advanced",          # TD "Level 5 (4k-1k)" → Yen-Go 6
    6: "low-dan",           # TD "Level 6 (1D-4D)" → Yen-Go 7
    7: "high-dan",          # TD "Level 7 (5D-6D)" → Yen-Go 8
    8: "expert",            # TD "Level 8 (7D+)" → Yen-Go 9
}


def parse_level_string(level_str: str | None) -> int | None:
    """Extract level number from TsumegoDragon level string.

    Args:
        level_str: Level string like "Level 3 (14k-10k)" or None.

    Returns:
        Level number (0-8) or None if not parseable.

    Examples:
        >>> parse_level_string("Level 3 (14k-10k)")
        3
        >>> parse_level_string("Level 0 (Beginner)")
        0
        >>> parse_level_string(None)
        None
    """
    if not level_str:
        return None

    match = re.match(r"Level\s+(\d+)", level_str, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None


def level_to_yg_slug(level_str: str | None) -> str | None:
    """Convert TsumegoDragon level to Yen-Go YG slug.

    Args:
        level_str: TsumegoDragon level string.

    Returns:
        Yen-Go level slug or None if level unknown/missing.

    Examples:
        >>> level_to_yg_slug("Level 3 (14k-10k)")
        'intermediate'
        >>> level_to_yg_slug("Level 0 (Beginner)")
        'novice'
        >>> level_to_yg_slug(None)
        None
    """
    level_num = parse_level_string(level_str)
    if level_num is None:
        return None
    return TD_LEVEL_TO_YENGO_SLUG.get(level_num)


# =============================================================================
# Category Mapping: TsumegoDragon Category Slug → Yen-Go YT Tags
# =============================================================================

# All target tags MUST exist in config/tags.json
# Verified tags (v6.0): life-and-death, living, ko, seki, capture-race, escape,
# snapback, throw-in, ladder, net, liberty-shortage, connect-and-die,
# under-the-stones, double-atari, vital-point, clamp, eye-shape, dead-shapes,
# nakade, connection, cutting, corner, sacrifice, shape, endgame, tesuji,
# joseki, fuseki (28 total)

TD_CATEGORY_TO_YENGO_TAGS: dict[str, list[str] | None] = {
    # === DIRECT TESUJI MATCHES ===
    "ladder": ["ladder"],
    "net": ["net"],
    "snapback": ["snapback"],
    "bamboo-snapback": ["snapback"],
    "throw-in-tactic": ["throw-in"],
    "double-threatatari": ["double-atari"],
    "connect--die": ["connect-and-die"],
    "vital-wedge": ["vital-point"],

    # === LIBERTY/CAPTURE ===
    "capture-race": ["capture-race"],
    "liberty-shortage": ["liberty-shortage"],
    "squeeze-tactic": ["liberty-shortage"],
    "bonus-liberty": ["liberty-shortage"],

    # === KO ===
    "loopko": ["ko"],
    "double-loopko": ["ko"],

    # === SEKI ===
    "mutual-life": ["seki"],

    # === LIFE AND DEATH OBJECTIVES ===
    "capture": [],  # Too broad — let tagger.py detect technique
    "corner-life--death": ["corner", "life-and-death"],
    "making-eyes": ["living", "eye-shape"],
    "taking-eyes": ["life-and-death", "eye-shape"],

    # === CONNECTION/CUTTING ===
    "connecting": ["connection"],
    "disconnect": ["cutting"],
    "discovered-cut": ["cutting"],

    # === EYE SHAPE PATTERNS ===
    "three-point-eye": ["dead-shapes", "eye-shape"],
    "four-point-eye": ["eye-shape"],
    "five-point-eye": ["eye-shape", "vital-point"],
    "six-point-eye": ["eye-shape"],
    "nine-space-eye": ["eye-shape"],
    "false-eye": ["eye-shape"],
    "eye-vs-no-eye": ["capture-race", "eye-shape"],

    # === SHAPE/PATTERN RECOGNITION ===
    "corner-pattern": ["corner", "dead-shapes"],
    "shape": ["shape"],

    # === ENDGAME ===
    "endgame-yose": ["endgame"],
    "endgame-traps": ["endgame"],

    # === SKIP (Not tsumego - return None to filter out) ===
    "opening-basics": None,

    # === UNSORTED (No tags - let tagger.py detect later) ===
    "unsorted": [],
}


def category_to_yt_tags(category_slug: str) -> list[str] | None:
    """Convert TsumegoDragon category to Yen-Go YT tags.

    Args:
        category_slug: TsumegoDragon category slug (e.g., "making-eyes").

    Returns:
        List of Yen-Go tag IDs, sorted alphabetically.
        Empty list if category is "unsorted" (no tags, let tagger.py detect).
        None if category should be skipped (not tsumego).

    Examples:
        >>> category_to_yt_tags("making-eyes")
        ['eye-shape', 'living']
        >>> category_to_yt_tags("ladder")
        ['ladder']
        >>> category_to_yt_tags("unsorted")
        []
        >>> category_to_yt_tags("endgame-yose")
        ['endgame']
    """
    # Normalize slug (handle double dashes from API)
    normalized = re.sub(r"-+", "-", category_slug.lower().strip())

    tags = TD_CATEGORY_TO_YENGO_TAGS.get(normalized)

    if tags is None:
        # Check if it's an unknown category
        if normalized not in TD_CATEGORY_TO_YENGO_TAGS:
            # Unknown category - return empty (let tagger.py handle)
            return []
        # Explicitly None = skip this puzzle
        return None

    # Sort alphabetically for consistent YT property
    return sorted(tags)


def should_skip_category(category_slug: str) -> bool:
    """Check if a category should be skipped (not downloaded).

    Args:
        category_slug: TsumegoDragon category slug.

    Returns:
        True if category should be skipped.
    """
    return category_to_yt_tags(category_slug) is None
