"""
Puzzle validation for OGS downloads.

Uses shared core validation for universal rules (board size, initial stones)
and OGS-specific logic for move tree traversal (correct_answer detection).

The move tree traversal cannot be shared because it operates on OGS API
format (OGSMoveNode with correct_answer/wrong_answer fields), not SGF.
"""

from __future__ import annotations

import logging

from tools.core.validation import (
    PuzzleValidationConfig,
    PuzzleValidationResult,
)
from tools.core.validation import (
    validate_puzzle as core_validate_puzzle,
)

from .config import (
    DEFAULT_MAX_MOVE_TREE_DEPTH,
    MAX_BOARD_SIZE,
    MIN_BOARD_SIZE,
)
from .converter import get_move_tree_depth, has_correct_answer_in_tree
from .models import OGSPuzzleDetail

logger = logging.getLogger("ogs.validator")


# Re-export for backward compatibility
ValidationResult = PuzzleValidationResult

# OGS-specific config matching existing constants
_OGS_VALIDATION_CONFIG = PuzzleValidationConfig(
    min_board_size=MIN_BOARD_SIZE,
    max_board_size=MAX_BOARD_SIZE,
    min_stones=2,
    min_solution_depth=0,  # Depth checked separately via move tree traversal
    max_solution_depth=None,  # Depth checked separately via move tree traversal
)


def validate_puzzle_data_early(
    puzzle_data: dict,
    puzzle_id: str | int,
    max_depth: int = DEFAULT_MAX_MOVE_TREE_DEPTH,
) -> str | None:
    """Validate puzzle data BEFORE Pydantic parsing.

    This is OGS-specific: it traverses the raw JSON move tree to check
    for correct_answer nodes, since the OGS API 'has_solution' field
    is unreliable.

    Args:
        puzzle_data: Raw puzzle JSON data
        puzzle_id: Puzzle ID for error messages
        max_depth: Maximum allowed move tree depth

    Returns:
        Rejection reason string if puzzle should be rejected, None if OK
    """
    # Get the move tree
    move_tree = puzzle_data.get("puzzle", {}).get("move_tree", {})

    # FIX: Check if move tree actually contains a correct answer
    # This is the RELIABLE way to detect solutions, not 'has_solution' field
    if not has_correct_answer_in_tree(move_tree):
        return (
            f"Rejected puzzle {puzzle_id}: No solution found in move tree. "
            f"(Note: has_solution API field was {puzzle_data.get('has_solution')}, "
            f"but tree traversal found no correct_answer nodes.)"
        )

    # Check move tree depth (avoids Pydantic recursion errors)
    if move_tree:
        depth = get_move_tree_depth(move_tree)
        if depth > max_depth:
            return (
                f"Rejected puzzle {puzzle_id}: Solution too long ({depth} moves). "
                f"Max allowed is {max_depth} moves."
            )

    return None


def validate_puzzle(
    puzzle: OGSPuzzleDetail,
    puzzle_id: str | int,
) -> PuzzleValidationResult:
    """Validate a parsed OGS puzzle.

    Delegates universal checks (board size, initial stones) to the
    shared core validator, then applies OGS-specific checks (move tree
    traversal for correct_answer nodes).

    Args:
        puzzle: Parsed OGS puzzle detail
        puzzle_id: Puzzle ID for error messages

    Returns:
        PuzzleValidationResult indicating if puzzle is valid
    """
    p = puzzle.puzzle

    # Universal checks via core validator
    stone_count = len(p.initial_state.black or "") // 2 + len(p.initial_state.white or "") // 2
    core_result = core_validate_puzzle(
        board_width=p.width,
        board_height=p.height,
        stone_count=stone_count,
        config=_OGS_VALIDATION_CONFIG,
    )
    if not core_result.is_valid:
        return core_result

    # OGS-specific: Check move tree has valid content
    root = p.move_tree
    if root.x < 0 and root.y < 0 and not root.branches:
        return PuzzleValidationResult.invalid("Empty move tree (no solution moves)")

    # OGS-specific: RELIABLE solution check via tree traversal
    if not has_correct_answer_in_tree(root):
        return PuzzleValidationResult.invalid(
            f"No correct_answer found in move tree (has_solution={puzzle.has_solution})"
        )

    return PuzzleValidationResult.valid()
