"""
Puzzle validation for 101weiqi downloads.

Validates puzzle data before converting to SGF:
- Board size within range
- Has setup stones
- Has a solution tree
"""

from __future__ import annotations

import logging

from .config import MAX_BOARD_SIZE, MIN_BOARD_SIZE
from .models import PuzzleData

logger = logging.getLogger("101weiqi.validator")


def validate_puzzle(puzzle: PuzzleData) -> str | None:
    """Validate a parsed puzzle.

    Args:
        puzzle: Parsed puzzle data.

    Returns:
        None if valid, error message string if invalid.
    """
    # Board size check
    if not (MIN_BOARD_SIZE <= puzzle.board_size <= MAX_BOARD_SIZE):
        return f"Board size {puzzle.board_size} outside range [{MIN_BOARD_SIZE}, {MAX_BOARD_SIZE}]"

    # Must have setup stones
    if not puzzle.black_stones and not puzzle.white_stones:
        return "No setup stones (empty position)"

    # Must have a solution tree with at least one node
    if not puzzle.solution_nodes:
        return "No solution tree (empty andata)"

    # Root node (0) must exist
    if 0 not in puzzle.solution_nodes:
        return "Solution tree missing root node (ID 0)"

    # Root node must have a coordinate (a move)
    root = puzzle.solution_nodes[0]
    if not root.coordinate:
        # Check if root has children with coordinates
        has_move = False
        for child_id in root.children:
            if child_id in puzzle.solution_nodes and puzzle.solution_nodes[child_id].coordinate:
                has_move = True
                break
        if not has_move:
            return "Solution tree has no moves"

    return None
