"""
SGF tree analysis functions.

Provides tree-walking algorithms for computing solution depth, variation
counts, complexity metrics, difficulty classification, and move order
detection.

Ported from multiple backend modules:
  - backend/puzzle_manager/core/complexity.py
  - backend/puzzle_manager/core/classifier.py
  - backend/puzzle_manager/core/enrichment/move_order.py

Tools must NOT import from backend/ — this is a standalone implementation.

Usage:
    from tools.core.sgf_parser import parse_sgf
    from tools.core.sgf_analysis import (
        max_branch_depth,
        compute_solution_depth,
        count_total_nodes,
        get_all_paths,
    )

    tree = parse_sgf(sgf_content)
    depth = max_branch_depth(tree.solution_tree)       # True max depth
    correct_depth = compute_solution_depth(tree.solution_tree)  # Correct-line
    nodes = count_total_nodes(tree.solution_tree)       # Total reading load
    paths = get_all_paths(tree.solution_tree)            # All leaf paths
"""

from __future__ import annotations

import logging
from enum import Enum

from tools.core.sgf_parser import SgfNode, SgfTree

logger = logging.getLogger("tools.core.sgf_analysis")


# ---------------------------------------------------------------------------
# Tree depth & counting
# ---------------------------------------------------------------------------


def max_branch_depth(node: SgfNode, current_depth: int = 0) -> int:
    """Get the maximum depth of any branch in the tree.

    This measures the longest root-to-leaf path, which is the correct
    way to compute "solution depth" for validation purposes.

    Unlike the old regex-based ``count_solution_moves_in_sgf()`` (which
    summed ALL nodes across all branches), this walks the tree and returns
    the true maximum depth.

    Args:
        node: Node to measure from (usually ``tree.solution_tree``).
        current_depth: Accumulator for recursion (caller should leave as 0).

    Returns:
        Maximum depth from this node to any leaf.

    Example:
        tree = parse_sgf(sgf)
        depth = max_branch_depth(tree.solution_tree)
        # For puzzle 6405: returns 15 (not 44 as the old regex counted)
    """
    if not node.children:
        return current_depth

    max_child_depth = current_depth
    for child in node.children:
        child_depth = max_branch_depth(child, current_depth + 1)
        max_child_depth = max(max_child_depth, child_depth)

    return max_child_depth


def compute_solution_depth(node: SgfNode) -> int:
    """Compute depth of the main correct solution line.

    Follows the first correct child at each branch point. This gives the
    "intended" solution length — often shorter than ``max_branch_depth``.

    Args:
        node: Root solution node.

    Returns:
        Number of moves in the main correct line.
    """
    depth = 0
    current = node

    while current.children:
        # Find first correct child
        for child in current.children:
            if child.is_correct:
                depth += 1
                current = child
                break
        else:
            # No correct child found — stop
            break

    return depth


def compute_main_line_depth(node: SgfNode) -> int:
    """Compute depth following the first child at each node.

    Unlike ``compute_solution_depth``, this always follows the first child
    regardless of correctness marking. Useful for puzzles where correctness
    is not marked.

    Args:
        node: Root solution node.

    Returns:
        Number of moves in the main (first-child) line.
    """
    depth = 0
    current: SgfNode | None = node
    while current and current.children:
        depth += 1
        current = current.children[0]
    return depth


def count_total_nodes(node: SgfNode) -> int:
    """Count total nodes in solution tree (reading workload).

    This is identical to ``SgfNode.count_variations()`` but provided as a
    module-level function for consistency with the analysis API.

    Args:
        node: Root solution node.

    Returns:
        Total node count including the root.
    """
    count = 1
    for child in node.children:
        count += count_total_nodes(child)
    return count


def count_stones(tree: SgfTree) -> int:
    """Count total initial stones on board (position complexity).

    Args:
        tree: Parsed SGF tree.

    Returns:
        Total stone count (black + white).
    """
    return len(tree.black_stones) + len(tree.white_stones)


def is_unique_first_move(tree: SgfTree) -> bool:
    """Check if there is exactly one correct first move.

    Miai positions have multiple correct first moves.

    Args:
        tree: Parsed SGF tree.

    Returns:
        True if single correct first move, False if miai or no solution.
    """
    if not tree.has_solution:
        return True  # Default to unique if no solution

    correct_first_moves = [
        child
        for child in tree.solution_tree.children
        if child.is_correct
    ]

    return len(correct_first_moves) == 1


# ---------------------------------------------------------------------------
# Path enumeration
# ---------------------------------------------------------------------------


def get_all_paths(node: SgfNode) -> list[list[SgfNode]]:
    """Enumerate all root-to-leaf paths in the solution tree.

    Each path is a list of SgfNode objects from root to leaf,
    useful for detailed analysis of all variations.

    Args:
        node: Root solution node (usually ``tree.solution_tree``).

    Returns:
        List of paths, where each path is a list of SgfNode.

    Example:
        paths = get_all_paths(tree.solution_tree)
        for path in paths:
            moves = [(n.color, n.move) for n in path if n.move]
            is_correct = all(n.is_correct for n in path)
    """
    paths: list[list[SgfNode]] = []
    _collect_paths(node, [], paths)
    return paths


def _collect_paths(
    node: SgfNode,
    current_path: list[SgfNode],
    paths: list[list[SgfNode]],
) -> None:
    """Recursively collect all root-to-leaf paths."""
    path = current_path + [node]

    if not node.children:
        paths.append(path)
        return

    for child in node.children:
        _collect_paths(child, path, paths)


# ---------------------------------------------------------------------------
# Complexity metrics (YX)
# ---------------------------------------------------------------------------


def compute_complexity_metrics(tree: SgfTree) -> str:
    """Compute full YX complexity metrics string.

    Format: ``d:{depth};r:{reading_count};s:{stone_count};u:{uniqueness}``

    Args:
        tree: Parsed SGF tree.

    Returns:
        YX string (e.g., ``"d:5;r:13;s:24;u:1"``).
    """
    depth = (
        compute_solution_depth(tree.solution_tree)
        if tree.has_solution
        else 0
    )
    reading_count = (
        count_total_nodes(tree.solution_tree)
        if tree.has_solution
        else 1
    )
    stone_count = count_stones(tree)
    uniqueness = 1 if is_unique_first_move(tree) else 0

    return f"d:{depth};r:{reading_count};s:{stone_count};u:{uniqueness}"


# ---------------------------------------------------------------------------
# Difficulty classification
# ---------------------------------------------------------------------------

LEVEL_NAMES: dict[int, str] = {
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


def classify_difficulty(tree: SgfTree) -> int:
    """Classify puzzle difficulty using heuristic scoring.

    Combines solution depth, variation count, stone count, and board size
    into a score mapped to levels 1–9.

    Args:
        tree: Parsed SGF tree.

    Returns:
        Difficulty level (1–9).
    """
    depth = compute_main_line_depth(tree.solution_tree)
    variations = tree.solution_tree.count_variations()
    stones = count_stones(tree)
    board_size = tree.board_size

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
        return 1
    elif score <= 4:
        return 2
    elif score <= 6:
        return 3
    elif score <= 8:
        return 4
    elif score <= 10:
        return 5
    elif score <= 12:
        return 6
    elif score <= 14:
        return 7
    elif score <= 16:
        return 8
    else:
        return 9


def classify_difficulty_with_slug(tree: SgfTree) -> tuple[int, str]:
    """Classify puzzle difficulty and return both level and slug.

    Args:
        tree: Parsed SGF tree.

    Returns:
        Tuple of (level: int, slug: str).
    """
    level = classify_difficulty(tree)
    slug = get_level_name(level)
    return level, slug


def get_level_name(level: int) -> str:
    """Get slug name for a level number.

    Args:
        level: Difficulty level (1–9).

    Returns:
        Level slug (e.g., ``"beginner"``), or ``"unknown"`` if invalid.
    """
    return LEVEL_NAMES.get(level, "unknown")


def level_from_name(name: str) -> int | None:
    """Get level number from slug name.

    Args:
        name: Level slug (e.g., ``"beginner"``).

    Returns:
        Level number (1–9) or None if not found.
    """
    name_lower = name.lower().replace("_", "-")
    for level, level_name in LEVEL_NAMES.items():
        if level_name == name_lower:
            return level
    return None


# ---------------------------------------------------------------------------
# Move order detection
# ---------------------------------------------------------------------------


class MoveOrderFlexibility(Enum):
    """Move order flexibility classification."""

    STRICT = "strict"
    FLEXIBLE = "flexible"


def detect_move_order(solution_tree: SgfNode) -> MoveOrderFlexibility:
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
        1 for child in solution_tree.children if child.is_correct
    )

    if correct_first_moves > 1:
        logger.debug(
            f"Found {correct_first_moves} correct first moves - flexible"
        )
        return MoveOrderFlexibility.FLEXIBLE

    # Check for transposition markers in comments
    if _has_transposition_marker(solution_tree):
        logger.debug("Found transposition marker - flexible")
        return MoveOrderFlexibility.FLEXIBLE

    # Check sibling branch convergence (more expensive)
    if _has_convergent_branches(solution_tree):
        logger.debug("Found convergent branches - flexible")
        return MoveOrderFlexibility.FLEXIBLE

    return MoveOrderFlexibility.STRICT


_TRANSPOSITION_MARKERS = [
    "also correct",
    "equally good",
    "order doesn't matter",
    "transposition",
    "miai",
    "both work",
    "either move",
]


def _has_transposition_marker(node: SgfNode, depth: int = 0) -> bool:
    """Check if any node has transposition markers in comments.

    Args:
        node: Node to check (and descendants).
        depth: Current recursion depth (limited to 5).

    Returns:
        True if transposition marker found.
    """
    if depth > 5:
        return False

    if node.comment:
        comment_lower = node.comment.lower()
        for marker in _TRANSPOSITION_MARKERS:
            if marker in comment_lower:
                return True

    for child in node.children:
        if _has_transposition_marker(child, depth + 1):
            return True

    return False


def _has_convergent_branches(solution_tree: SgfNode) -> bool:
    """Check if sibling correct branches have similar structure.

    Heuristic approximation — full convergence detection would require
    board simulation. This checks whether two correct first-move branches
    have similar depth, which suggests transposition.

    Args:
        solution_tree: Root of solution tree.

    Returns:
        True if convergent branches detected.
    """
    correct_branches = [
        child for child in solution_tree.children if child.is_correct
    ]

    if len(correct_branches) < 2:
        return False

    first_depth = max_branch_depth(correct_branches[0])
    second_depth = max_branch_depth(correct_branches[1])

    if abs(first_depth - second_depth) <= 1:
        logger.debug(
            f"Similar branch depths ({first_depth}, {second_depth})"
        )
        return True

    return False
