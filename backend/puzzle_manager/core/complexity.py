"""
Complexity metrics computation for SGF puzzles.

Computes YX (complexity) metrics per Spec 024 definitions.
Complexity measures PUZZLE DIFFICULTY - how hard to solve.
All metrics computable from tree analysis - NO AI required.
"""

from backend.puzzle_manager.core.sgf_parser import SGFGame, SolutionNode


def compute_solution_depth(node: SolutionNode) -> int:
    """Compute solution depth (moves in main correct line).

    Main line is the first correct move at each branch.

    Args:
        node: Root solution node.

    Returns:
        Number of moves in main line.
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
            # No correct child found
            break

    return depth


def count_total_nodes(node: SolutionNode) -> int:
    """Count total nodes in solution tree (reading workload).

    Args:
        node: Root solution node.

    Returns:
        Total node count including root.
    """
    count = 1  # Count this node

    for child in node.children:
        count += count_total_nodes(child)

    return count


def count_stones(game: SGFGame) -> int:
    """Count total stones on board (position complexity).

    Args:
        game: Parsed SGF game.

    Returns:
        Total stone count.
    """
    return len(game.black_stones) + len(game.white_stones)


def is_unique_first_move(game: SGFGame) -> bool:
    """Check if there's exactly one correct first move.

    Miai positions have multiple correct first moves.

    Args:
        game: Parsed SGF game.

    Returns:
        True if single correct first move, False if miai.
    """
    if not game.has_solution:
        return True  # Default to unique if no solution

    correct_first_moves = [
        child for child in game.solution_tree.children
        if child.is_correct
    ]

    return len(correct_first_moves) == 1


def compute_avg_refutation_depth(node: SolutionNode) -> int:
    """Compute average depth of wrong-move (refutation) subtrees.

    Walks the solution tree and for each wrong-move branch, measures
    the depth from the wrong move node to its deepest leaf. Returns
    the rounded mean across all wrong-move branches.

    Args:
        node: Root solution node.

    Returns:
        Average refutation depth (rounded integer). 0 if no wrong branches.
    """
    wrong_depths: list[int] = []

    def _subtree_depth(n: SolutionNode) -> int:
        """Compute max depth from this node to its deepest leaf."""
        if not n.children:
            return 0
        return 1 + max(_subtree_depth(c) for c in n.children)

    def _collect_wrong_depths(n: SolutionNode) -> None:
        """Traverse tree collecting depths of wrong-move subtrees."""
        for child in n.children:
            if not child.is_correct:
                # Measure depth of this wrong subtree
                wrong_depths.append(1 + _subtree_depth(child))
            else:
                _collect_wrong_depths(child)

    _collect_wrong_depths(node)

    if not wrong_depths:
        return 0

    return round(sum(wrong_depths) / len(wrong_depths))


def compute_complexity_metrics(game: SGFGame) -> str:
    """Compute full YX complexity metrics string.

    Format: "d:{depth};r:{reading_count};s:{stone_count};u:{uniqueness};a:{avg_refutation_depth}"

    Args:
        game: Parsed SGF game.

    Returns:
        YX string (e.g., "d:5;r:13;s:24;u:1;a:3").
    """
    depth = compute_solution_depth(game.solution_tree) if game.has_solution else 0
    reading_count = count_total_nodes(game.solution_tree) if game.has_solution else 1
    stone_count = count_stones(game)
    uniqueness = 1 if is_unique_first_move(game) else 0
    avg_ref_depth = compute_avg_refutation_depth(game.solution_tree) if game.has_solution else 0

    return f"d:{depth};r:{reading_count};s:{stone_count};u:{uniqueness};a:{avg_ref_depth}"
