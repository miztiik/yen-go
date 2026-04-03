"""
Puzzle validation for GoProblems downloads.

Uses shared core validation for SGF-based checks (board size, initial stones,
solution depth) since GoProblems provides raw SGF in API responses.
"""

from __future__ import annotations

import logging

from tools.core.validation import (
    PuzzleValidationConfig,
    PuzzleValidationResult,
    validate_sgf_puzzle,
)

from .config import DEFAULT_MAX_SOLUTION_DEPTH, MAX_BOARD_SIZE, MIN_BOARD_SIZE

logger = logging.getLogger("go_problems.validator")


# GoProblems-specific validation config
_GP_VALIDATION_CONFIG = PuzzleValidationConfig(
    min_board_size=MIN_BOARD_SIZE,
    max_board_size=MAX_BOARD_SIZE,
    min_stones=2,
    min_solution_depth=1,
    max_solution_depth=DEFAULT_MAX_SOLUTION_DEPTH,
)


def validate_puzzle_early(
    raw_data: dict,
    puzzle_id: int | str,
    canon_only: bool = True,
) -> str | None:
    """Validate puzzle data BEFORE full parsing.

    Quick checks on raw API response to reject obviously invalid puzzles
    before spending time on full parsing and conversion.

    Args:
        raw_data: Raw API response dict
        puzzle_id: Puzzle ID for error messages
        canon_only: If True, reject non-canonical puzzles

    Returns:
        Rejection reason string if puzzle should be rejected, None if OK
    """
    # Canon filter
    if canon_only and not raw_data.get("isCanon", False):
        return f"Puzzle {puzzle_id}: not canonical (filtered by --canon-only)"

    # SGF content check
    sgf = raw_data.get("sgf", "")
    if not sgf:
        return f"Puzzle {puzzle_id}: missing SGF content"

    if not sgf.startswith("(;") and "(;" not in sgf:
        return f"Puzzle {puzzle_id}: invalid SGF format (no '(;' found)"

    return None


def validate_puzzle(
    sgf_content: str,
    puzzle_id: int | str,
    max_solution_depth: int | None = None,
) -> PuzzleValidationResult:
    """Validate a GoProblems puzzle from its SGF content.

    Delegates to the shared core SGF validator which extracts board size,
    initial stones, and solution depth from the raw SGF string.

    Args:
        sgf_content: Raw SGF string from GoProblems API
        puzzle_id: Puzzle ID for error messages
        max_solution_depth: Override default max depth (from --max-depth CLI).
            If None, uses the default from _GP_VALIDATION_CONFIG.

    Returns:
        PuzzleValidationResult indicating if puzzle is valid
    """
    if max_solution_depth is not None:
        config = PuzzleValidationConfig(
            min_board_size=MIN_BOARD_SIZE,
            max_board_size=MAX_BOARD_SIZE,
            min_stones=2,
            min_solution_depth=1,
            max_solution_depth=max_solution_depth,
        )
    else:
        config = _GP_VALIDATION_CONFIG

    result = validate_sgf_puzzle(sgf_content, config=config)

    if not result.is_valid:
        logger.debug(f"Puzzle {puzzle_id} rejected: {result.rejection_reason}")

    return result
