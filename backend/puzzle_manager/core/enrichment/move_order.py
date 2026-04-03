"""
Move order flexibility detection for puzzle enrichment.

Determines whether a puzzle requires strict move order or allows
transpositions (flexible order) for the YO property.

YO Format:
----------
Simple enum value:
  YO[strict]    - Moves must be played in exact order
  YO[flexible]  - Some moves can be played in different order

Detection Algorithm:
--------------------
1. Check if multiple first moves are marked as correct → flexible
2. Check if sibling branches converge to same position → flexible
3. Check for transposition markers in comments → flexible
4. Otherwise → strict (default)

Philosophy:
-----------
Most tsumego have strict move order - there's ONE best move at each step.
But some puzzles have:
- Multiple valid first moves (miai situations)
- Transpositions (A→B→C equivalent to A→C→B)

Marking flexibility helps the UI provide better feedback and reduces
frustration when a "wrong" order is actually valid.
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.puzzle_manager.core.sgf_parser import SolutionNode

logger = logging.getLogger("enrichment.move_order")


class MoveOrderFlexibility(Enum):
    """Move order flexibility classification."""

    STRICT = "strict"  # Exact order required
    FLEXIBLE = "flexible"  # Some transpositions allowed


def detect_move_order(
    solution_tree: SolutionNode,
) -> MoveOrderFlexibility:
    """Detect move order flexibility from solution tree.

    Analyzes the solution tree structure to determine if the puzzle
    requires strict move order or allows transpositions.

    Args:
        solution_tree: Root of solution tree.

    Returns:
        MoveOrderFlexibility enum value.
    """
    # Check for multiple correct first moves
    correct_first_moves = sum(
        1 for child in solution_tree.children
        if child.is_correct
    )

    if correct_first_moves > 1:
        logger.debug(f"Found {correct_first_moves} correct first moves - flexible")
        return MoveOrderFlexibility.FLEXIBLE

    # Check for transposition markers in comments
    if _has_transposition_marker(solution_tree):
        logger.debug("Found transposition marker - flexible")
        return MoveOrderFlexibility.FLEXIBLE

    # Check sibling branch convergence (more expensive)
    if _has_convergent_branches(solution_tree):
        logger.debug("Found convergent branches - flexible")
        return MoveOrderFlexibility.FLEXIBLE

    # Default: strict
    return MoveOrderFlexibility.STRICT


def _has_transposition_marker(node: SolutionNode, depth: int = 0) -> bool:
    """Check if any node has transposition markers in comments.

    Looks for keywords that indicate move order flexibility:
    - "also correct"
    - "equally good"
    - "or", "order doesn't matter"
    - "transposition"
    - "miai"

    Args:
        node: Node to check (and descendants).
        depth: Current recursion depth (limit to prevent deep traversal).

    Returns:
        True if transposition marker found.
    """
    if depth > 5:  # Limit depth for performance
        return False

    TRANSPOSITION_MARKERS = [
        "also correct",
        "equally good",
        "order doesn't matter",
        "transposition",
        "miai",
        "both work",
        "either move",
    ]

    if node.comment:
        comment_lower = node.comment.lower()
        for marker in TRANSPOSITION_MARKERS:
            if marker in comment_lower:
                return True

    # Check children
    for child in node.children:
        if _has_transposition_marker(child, depth + 1):
            return True

    return False


def _has_convergent_branches(solution_tree: SolutionNode) -> bool:
    """Check if sibling branches converge to equivalent positions.

    This is a simplified check - we look for cases where:
    1. Two correct first moves exist
    2. Their continuation trees have similar structure

    Full convergence detection would require board simulation,
    which is expensive. This is a heuristic approximation.

    Args:
        solution_tree: Root of solution tree.

    Returns:
        True if convergent branches detected.
    """
    # Get correct first moves
    correct_branches = [
        child for child in solution_tree.children
        if child.is_correct
    ]

    if len(correct_branches) < 2:
        return False

    # Compare branch structures (simplified)
    # If two branches have similar depth and child count, might be transposition
    first_depth = _get_branch_depth(correct_branches[0])
    second_depth = _get_branch_depth(correct_branches[1])

    # If depths are similar (within 1), might indicate convergence
    if abs(first_depth - second_depth) <= 1:
        logger.debug(f"Similar branch depths ({first_depth}, {second_depth})")
        return True

    return False


def _get_branch_depth(node: SolutionNode, current_depth: int = 0) -> int:
    """Get the maximum depth of a branch.

    Args:
        node: Node to measure from.
        current_depth: Current depth.

    Returns:
        Maximum depth from this node.
    """
    if not node.children:
        return current_depth

    max_child_depth = current_depth
    for child in node.children:
        child_depth = _get_branch_depth(child, current_depth + 1)
        max_child_depth = max(max_child_depth, child_depth)

    return max_child_depth
