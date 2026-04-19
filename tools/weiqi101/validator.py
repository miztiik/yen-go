"""
Puzzle validation for 101weiqi downloads.

Validates puzzle data before converting to SGF:
- Board size within range (or inferrable)
- Has setup stones
- Solution tree is optional (position-only puzzles are saved without moves)
"""

from __future__ import annotations

import logging

from .config import MAX_BOARD_SIZE, MIN_BOARD_SIZE
from .models import PuzzleData

logger = logging.getLogger("101weiqi.validator")


def validate_puzzle(puzzle: PuzzleData) -> str | None:
    """Validate a parsed puzzle.

    Puzzles without a solution tree are accepted — they are saved
    as position-only SGFs. A warning is logged but they are not rejected.

    Args:
        puzzle: Parsed puzzle data.

    Returns:
        None if valid, error message string if invalid.
    """
    # Board size check — infer from stones if missing
    if puzzle.board_size is None or puzzle.board_size == 0:
        inferred = _infer_board_size(puzzle)
        if inferred is not None:
            logger.info(
                f"Puzzle {puzzle.puzzle_id}: board size missing, inferred {inferred} from stones"
            )
            puzzle.board_size = inferred
        else:
            return "Board size missing and cannot be inferred from stones"

    if not (MIN_BOARD_SIZE <= puzzle.board_size <= MAX_BOARD_SIZE):
        return f"Board size {puzzle.board_size} outside range [{MIN_BOARD_SIZE}, {MAX_BOARD_SIZE}]"

    # Must have setup stones
    if not puzzle.black_stones and not puzzle.white_stones:
        return "No setup stones (empty position)"

    # Solution tree is optional — warn but don't reject
    if not puzzle.solution_nodes:
        logger.warning(f"Puzzle {puzzle.puzzle_id}: no solution tree (position-only)")
    elif 0 not in puzzle.solution_nodes:
        logger.warning(f"Puzzle {puzzle.puzzle_id}: solution tree missing root node")
    else:
        root = puzzle.solution_nodes[0]
        if not root.coordinate and not root.children:
            logger.warning(f"Puzzle {puzzle.puzzle_id}: solution tree has no moves (position-only)")

    return None


def _infer_board_size(puzzle: PuzzleData) -> int | None:
    """Infer board size from the maximum stone coordinate.

    SGF coordinates use 'a'-'s' for columns/rows on a 19x19 board.
    The board size is at least max(coord) + 1.

    Returns:
        Inferred board size (clamped to standard sizes), or None if no stones.
    """
    all_stones = puzzle.black_stones + puzzle.white_stones
    if not all_stones:
        return None

    max_ord = 0
    for coord in all_stones:
        if len(coord) >= 2:
            max_ord = max(max_ord, ord(coord[0]) - ord('a'), ord(coord[1]) - ord('a'))

    # Snap to standard board sizes
    needed = max_ord + 1
    for standard in (9, 13, 19):
        if needed <= standard:
            return standard
    return 19
