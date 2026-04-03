"""
Content-type classification for puzzle quality tiers.

Classifies puzzles into three content types defined in config/content-types.json:
  curated: High-quality puzzles with unique first moves, deep refutations
  practice: Standard puzzles suitable for regular training
  training: Trivial captures, teaching examples, no-solution puzzles

All classification parameters — type IDs, thresholds, patterns — are loaded from
config/content-types.json (single source of truth). No hardcoded fallbacks.

Also provides trivial capture detection (reuses existing Board/liberty analysis).

Policy: ENRICH_IF_ABSENT — if source or prior run set content-type, preserve it.
"""

import json
import logging
import re
from pathlib import Path
from typing import Any

from backend.puzzle_manager.core.board import Board
from backend.puzzle_manager.core.primitives import Color, Move, Point
from backend.puzzle_manager.core.sgf_parser import SGFGame

logger = logging.getLogger("puzzle_manager.content_classifier")

# ---------------------------------------------------------------------------
# Config loading (fail-fast, no fallbacks)
# ---------------------------------------------------------------------------

_content_type_config: dict[str, Any] | None = None


def _load_content_type_config() -> dict[str, Any]:
    """Load content-type config from config/content-types.json.

    Cached after first load. Raises on missing or corrupt config.
    """
    global _content_type_config
    if _content_type_config is not None:
        return _content_type_config

    config_path = Path(__file__).resolve().parents[3] / "config" / "content-types.json"
    if not config_path.exists():
        raise FileNotFoundError(f"Required config not found: {config_path}")

    _content_type_config = json.loads(config_path.read_text(encoding="utf-8"))
    return _content_type_config


def get_content_type_id(name: str) -> int:
    """Get numeric content type ID by name from config.

    Args:
        name: Content type slug ('curated', 'practice', or 'training').

    Returns:
        Numeric content type ID.

    Raises:
        KeyError: If content type name not found in config.
    """
    config = _load_content_type_config()
    types = config["types"]
    for type_id, type_def in types.items():
        if type_def["name"] == name:
            return int(type_id)
    raise KeyError(f"Content type '{name}' not found in config/content-types.json")


# Module-level accessors (lazy-loaded from config)
CONTENT_TYPE_CURATED: int
CONTENT_TYPE_PRACTICE: int
CONTENT_TYPE_TRAINING: int


def _ensure_type_constants() -> None:
    """Load content type constants from config on first access."""
    global CONTENT_TYPE_CURATED, CONTENT_TYPE_PRACTICE, CONTENT_TYPE_TRAINING
    CONTENT_TYPE_CURATED = get_content_type_id("curated")
    CONTENT_TYPE_PRACTICE = get_content_type_id("practice")
    CONTENT_TYPE_TRAINING = get_content_type_id("training")


def _get_teaching_patterns() -> list[re.Pattern[str]]:
    """Get compiled teaching text regex patterns from config."""
    config = _load_content_type_config()
    raw_patterns = config["teaching_patterns"]

    compiled: list[re.Pattern[str]] = []
    for pat in raw_patterns:
        try:
            compiled.append(re.compile(pat, re.IGNORECASE))
        except re.error as e:
            logger.warning(f"Invalid teaching pattern '{pat}': {e}")
    return compiled


def _get_curated_thresholds() -> dict[str, Any]:
    """Get curated classification thresholds from config."""
    config = _load_content_type_config()
    return config["curated_thresholds"]


def _get_training_thresholds() -> dict[str, Any]:
    """Get training classification thresholds from config."""
    config = _load_content_type_config()
    return config["training_thresholds"]


def reset_content_type_config() -> None:
    """Reset cached config. Used in testing."""
    global _content_type_config
    _content_type_config = None


# ---------------------------------------------------------------------------
# Trivial capture detection (Phase 1)
# ---------------------------------------------------------------------------

def is_trivial_capture(game: SGFGame) -> bool:
    """Detect if a puzzle is a trivial capture (opponent at 1 liberty).

    Algorithm:
    1. Build board from initial position
    2. Find opponent groups at exactly 1 liberty
    3. Get first correct move from solution tree
    4. Check if that move captures the atari group

    A trivial capture is one where the opponent has a group at exactly 1
    liberty and the correct first move captures it. These are too easy
    for regular practice and get classified as training material.

    Args:
        game: Parsed SGF game.

    Returns:
        True if the puzzle is a trivial capture, False otherwise.
    """
    try:
        if not game.has_solution:
            return False

        if not (game.black_stones or game.white_stones):
            return False

        # Get first correct move
        first_move_point: Point | None = None
        player_color = game.player_to_move
        player_color.opponent()

        for child in game.solution_tree.children:
            if child.is_correct and child.move:
                first_move_point = child.move
                break

        if first_move_point is None:
            return False

        # Build board from initial position
        board = Board(game.board_size)
        board.setup_position(game.black_stones, game.white_stones)

        # Find opponent groups at exactly 1 liberty
        has_atari_group = False
        analyzed_points: set[Point] = set()

        opponent_stones = (
            game.white_stones if player_color == Color.BLACK else game.black_stones
        )

        for point in opponent_stones:
            if point in analyzed_points:
                continue
            group = board.get_group(point)
            if group is None:
                continue
            analyzed_points.update(group.stones)
            if len(group.liberties) == 1:
                has_atari_group = True
                break

        if not has_atari_group:
            return False

        # Check if the first move captures stones
        test_board = Board(game.board_size)
        test_board.setup_position(game.black_stones, game.white_stones)
        move = Move(color=player_color, point=first_move_point)
        captured = test_board.play(move)
        return len(captured) > 0

    except Exception as e:
        logger.debug(f"Trivial capture detection failed: {e}")
        return False


# ---------------------------------------------------------------------------
# Content-type classification (Phase 2)
# ---------------------------------------------------------------------------

def _has_teaching_root_comment(game: SGFGame) -> bool:
    """Check if root comment matches teaching patterns.

    Args:
        game: Parsed SGF game.

    Returns:
        True if root comment contains teaching-like text.
    """
    comment = game.root_comment
    if not comment:
        return False

    patterns = _get_teaching_patterns()
    for pattern in patterns:
        if pattern.search(comment):
            return True
    return False


def _get_solution_depth(game: SGFGame) -> int:
    """Get solution depth from YX or compute from tree.

    Args:
        game: Parsed SGF game.

    Returns:
        Solution depth (0 if no solution).
    """
    if not game.has_solution:
        return 0

    # Try to parse from existing YX
    yx = game.yengo_props.complexity
    if yx:
        for part in yx.split(";"):
            if part.startswith("d:"):
                try:
                    return int(part[2:])
                except ValueError:
                    pass

    # Compute from tree
    from backend.puzzle_manager.core.complexity import compute_solution_depth
    return compute_solution_depth(game.solution_tree)


def _get_comment_level(game: SGFGame) -> int:
    """Get comment level from YQ or compute from tree.

    Args:
        game: Parsed SGF game.

    Returns:
        Comment level (0, 1, or 2).
    """
    # Try to parse from existing YQ
    yq = game.yengo_props.quality
    if yq:
        for part in yq.split(";"):
            if part.startswith("hc:"):
                try:
                    return int(part[3:])
                except ValueError:
                    pass

    # Compute from tree
    if game.has_solution:
        from backend.puzzle_manager.core.quality import compute_comment_level
        return compute_comment_level(game.solution_tree)
    return 0


def _get_quality_level(game: SGFGame) -> int:
    """Get quality level from YQ or compute.

    Args:
        game: Parsed SGF game.

    Returns:
        Quality level 1-5.
    """
    from backend.puzzle_manager.core.quality import (
        compute_puzzle_quality_level,
        parse_quality_level,
    )
    existing = parse_quality_level(game.yengo_props.quality)
    if existing is not None:
        return existing
    return compute_puzzle_quality_level(game)


def _get_refutation_count(game: SGFGame) -> int:
    """Get refutation count from YQ or compute.

    Args:
        game: Parsed SGF game.

    Returns:
        Number of refutation moves.
    """
    yq = game.yengo_props.quality
    if yq:
        for part in yq.split(";"):
            if part.startswith("rc:"):
                try:
                    return int(part[3:])
                except ValueError:
                    pass

    if game.has_solution:
        from backend.puzzle_manager.core.quality import count_refutation_moves
        return count_refutation_moves(game.solution_tree)
    return 0


def _is_unique_first(game: SGFGame) -> bool:
    """Check if puzzle has unique first move from YX or compute."""
    yx = game.yengo_props.complexity
    if yx:
        for part in yx.split(";"):
            if part.startswith("u:"):
                try:
                    return int(part[2:]) == 1
                except ValueError:
                    pass

    from backend.puzzle_manager.core.complexity import is_unique_first_move
    return is_unique_first_move(game)


def classify_content_type(game: SGFGame) -> int:
    """Classify puzzle into content type (curated/practice/training).

    All thresholds and type IDs are loaded from config/content-types.json.

    Decision tree (evaluated in order):
    1. Trivial capture → training
    2. No solution tree → training
    3. Root comment matches teaching patterns → training
    4. Solution depth ≤ max_depth AND hc ≥ min_comment_level → training
    5. Unique first move AND refutations ≥ threshold AND quality ≥ threshold → curated
    6. Everything else → practice

    Args:
        game: Parsed SGF game.

    Returns:
        Content type ID from config (1=curated, 2=practice, 3=training).
    """
    _ensure_type_constants()

    # 1. Trivial capture
    if is_trivial_capture(game):
        return CONTENT_TYPE_TRAINING

    # 2. No solution tree
    if not game.has_solution:
        return CONTENT_TYPE_TRAINING

    # 3. Root comment matches teaching patterns
    if _has_teaching_root_comment(game):
        return CONTENT_TYPE_TRAINING

    # 4. Single-move with teaching explanation = tutorial
    training = _get_training_thresholds()
    depth = _get_solution_depth(game)
    comment_level = _get_comment_level(game)
    if depth <= training["max_depth"] and comment_level >= training["min_comment_level"]:
        return CONTENT_TYPE_TRAINING

    # 5. Curated check
    thresholds = _get_curated_thresholds()
    min_quality = thresholds["min_quality"]
    min_refutations = thresholds["min_refutations"]
    require_unique = thresholds["require_unique_first_move"]

    quality = _get_quality_level(game)
    refutation_count = _get_refutation_count(game)
    unique_first = _is_unique_first(game)

    if quality >= min_quality and refutation_count >= min_refutations:
        if not require_unique or unique_first:
            return CONTENT_TYPE_CURATED

    # 6. Default
    return CONTENT_TYPE_PRACTICE
