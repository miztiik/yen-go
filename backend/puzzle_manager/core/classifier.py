"""
Difficulty classifier for puzzles.

Classifies puzzles into 9 skill levels based on:
- Solution depth (number of moves)
- Variation count
- Technique complexity
- Board complexity

Collection-based level override (v5.0):
When a puzzle belongs to a collection with a level_hint, that hint
takes priority over the heuristic classifier. When multiple level-bearing
collections apply, the lowest (easiest) level wins.
"""

import logging

from backend.puzzle_manager.core.sgf_parser import SGFGame, SolutionNode
from backend.puzzle_manager.exceptions import ClassificationError

logger = logging.getLogger("classifier")


# Level definitions (from data-model.md)
LEVEL_NAMES = {
    1: "novice",
    2: "beginner",
    3: "elementary",
    4: "intermediate",
    5: "upper-intermediate",
    6: "advanced",
    7: "low-dan",
    8: "high-dan",
    9: "expert",
}


def classify_difficulty(game: SGFGame) -> int:
    """Classify puzzle difficulty.

    Args:
        game: Parsed SGFGame object.

    Returns:
        Difficulty level (1-9).

    Raises:
        ClassificationError: If classification fails.
    """
    try:
        # Gather features
        depth = _get_solution_depth(game.solution_tree)
        variations = game.solution_tree.count_variations()
        stones = len(game.black_stones) + len(game.white_stones)
        board_size = game.board_size

        # Simple heuristic classification
        # This is a placeholder - real implementation would use more sophisticated analysis

        score = 0

        # Depth score (more moves = harder)
        if depth <= 1:
            score += 1
        elif depth <= 2:
            score += 2
        elif depth <= 3:
            score += 3
        elif depth <= 5:
            score += 4
        elif depth <= 7:
            score += 5
        elif depth <= 10:
            score += 6
        else:
            score += 7

        # Variation score (more variations = harder to read)
        if variations <= 2:
            score += 0
        elif variations <= 5:
            score += 1
        elif variations <= 10:
            score += 2
        else:
            score += 3

        # Stone count score (more stones = more complex)
        if stones <= 10:
            score += 0
        elif stones <= 20:
            score += 1
        elif stones <= 40:
            score += 2
        else:
            score += 3

        # Board size adjustment
        if board_size == 9:
            score -= 1
        elif board_size == 13:
            score += 0
        else:  # 19x19
            score += 1

        # Map score to level (1-9)
        if score <= 2:
            return 1  # novice
        elif score <= 4:
            return 2  # beginner
        elif score <= 6:
            return 3  # elementary
        elif score <= 8:
            return 4  # intermediate
        elif score <= 10:
            return 5  # upper-intermediate
        elif score <= 12:
            return 6  # advanced
        elif score <= 14:
            return 7  # low-dan
        elif score <= 16:
            return 8  # high-dan
        else:
            return 9  # expert

    except Exception as e:
        raise ClassificationError(f"Failed to classify puzzle: {e}") from e


def _get_solution_depth(root: SolutionNode) -> int:
    """Get the depth of the main solution line."""
    depth = 0
    current: SolutionNode | None = root
    while current and current.children:
        depth += 1
        # Follow the first (correct) variation
        current = current.children[0]
    return depth


def get_level_name(level: int) -> str:
    """Get human-readable name for level.

    Args:
        level: Difficulty level (1-9).

    Returns:
        Level name string (slug format, e.g., "beginner").
    """
    return LEVEL_NAMES.get(level, "unknown")


def classify_difficulty_with_slug(game: SGFGame) -> tuple[int, str]:
    """Classify puzzle difficulty and return both level and slug.

    Args:
        game: Parsed SGFGame object.

    Returns:
        Tuple of (level: int, slug: str).

    Raises:
        ClassificationError: If classification fails.
    """
    level = classify_difficulty(game)
    slug = get_level_name(level)
    return level, slug


def level_from_name(name: str) -> int | None:
    """Get level number from name.

    Args:
        name: Level name (e.g., "beginner").

    Returns:
        Level number (1-9) or None if not found.
    """
    name_lower = name.lower().replace("_", "-")
    for level, level_name in LEVEL_NAMES.items():
        if level_name == name_lower:
            return level
    return None


def resolve_level_from_collections(
    collections: list[str],
    level_hint_map: dict[str, str],
    *,
    puzzle_id: str = "",
    heuristic_level: int | None = None,
) -> tuple[int, str] | None:
    """Resolve difficulty level from collection membership via level_hint config.

    When a puzzle belongs to one or more collections that have a level_hint
    in config/collections.json, the collection-based level takes priority
    over the heuristic classifier.

    Conflict resolution: when multiple level-bearing collections apply,
    the **lowest** (easiest) level wins. This is the conservative choice —
    better to present a puzzle as slightly easier than to frustrate a student.

    Args:
        collections: List of collection slugs the puzzle belongs to.
        level_hint_map: Mapping of collection slug → level slug (e.g., "novice").
            Built from collections with a level_hint field.
        puzzle_id: For logging (optional).
        heuristic_level: If provided, log when collection overrides heuristic.

    Returns:
        Tuple of (level_number, level_slug) if any collection has a hint,
        or None if no level-bearing collection found.
    """
    if not collections or not level_hint_map:
        return None

    matched_levels: list[tuple[int, str, str]] = []  # (level_num, slug, collection)

    for col_slug in collections:
        hint_slug = level_hint_map.get(col_slug)
        if hint_slug:
            level_num = level_from_name(hint_slug)
            if level_num is not None:
                matched_levels.append((level_num, hint_slug, col_slug))

    if not matched_levels:
        return None

    # Sort by level number ascending — lowest (easiest) wins
    matched_levels.sort(key=lambda x: x[0])
    chosen_level, chosen_slug, chosen_collection = matched_levels[0]

    # Log conflict if multiple level-bearing collections with different levels
    if len(matched_levels) > 1:
        unique_levels = {m[0] for m in matched_levels}
        if len(unique_levels) > 1:
            all_hints = ", ".join(
                f"'{m[2]}'→{m[1]}({m[0]})" for m in matched_levels
            )
            logger.warning(
                "Multiple conflicting level hints for %s: %s. "
                "Using lowest level: %s (%d) from '%s'",
                puzzle_id or "puzzle",
                all_hints,
                chosen_slug,
                chosen_level,
                chosen_collection,
            )

    # Log override when heuristic disagrees
    if heuristic_level is not None and heuristic_level != chosen_level:
        heuristic_slug = get_level_name(heuristic_level)
        logger.info(
            "Level override for %s: collection '%s' implies '%s' (%d), "
            "heuristic classified as '%s' (%d). Using collection level.",
            puzzle_id or "puzzle",
            chosen_collection,
            chosen_slug,
            chosen_level,
            heuristic_slug,
            heuristic_level,
        )

    return (chosen_level, chosen_slug)
