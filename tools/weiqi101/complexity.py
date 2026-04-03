"""
Complexity metrics computation from 101weiqi andata solution tree.

Computes YX[] sub-fields: d (depth), r (refutations/total nodes),
s (solution length), u (unique first moves), w (wrong first moves).
"""

from __future__ import annotations

from dataclasses import dataclass

from .models import SolutionNode


@dataclass
class ComplexityMetrics:
    """Complexity metrics for a puzzle solution tree."""

    depth: int = 0           # d: max path length from root to any leaf
    total_nodes: int = 0     # r: total reading nodes (all andata entries)
    solution_length: int = 0  # s: moves in the main correct line
    unique_first: int = 0    # u: unique first-move responses
    wrong_first: int = 0     # w: wrong first moves

    def to_yx_string(self) -> str:
        """Format as YX property value.

        Example: "d:3;r:12;s:5;u:3;w:2"
        """
        return f"d:{self.depth};r:{self.total_nodes};s:{self.solution_length};u:{self.unique_first};w:{self.wrong_first}"


def compute_complexity(
    nodes: dict[int, SolutionNode],
    root_id: int = 0,
) -> ComplexityMetrics:
    """Compute complexity metrics from a solution tree.

    Args:
        nodes: Solution nodes keyed by node ID.
        root_id: Root node ID (typically 0).

    Returns:
        ComplexityMetrics with all fields populated.
    """
    if not nodes or root_id not in nodes:
        return ComplexityMetrics()

    # Total reading nodes (exclude root if it has no coordinate)
    move_nodes = sum(1 for n in nodes.values() if n.coordinate)
    total_nodes = move_nodes

    # Unique first moves = children of root
    root = nodes[root_id]
    first_move_ids = root.children
    unique_first = len(first_move_ids)

    # Wrong first moves = first moves that lead to failure
    wrong_first = 0
    for child_id in first_move_ids:
        if child_id in nodes:
            child = nodes[child_id]
            if child.is_failure or (not child.is_correct and _subtree_is_wrong(nodes, child_id)):
                wrong_first += 1

    # Depth = max path length from root to any leaf
    depth = _max_depth(nodes, root_id, 0)

    # Solution length = length of the main correct line
    solution_length = _correct_line_length(nodes, root_id)

    return ComplexityMetrics(
        depth=depth,
        total_nodes=total_nodes,
        solution_length=solution_length,
        unique_first=unique_first,
        wrong_first=wrong_first,
    )


def _max_depth(nodes: dict[int, SolutionNode], node_id: int, current: int) -> int:
    """Compute maximum depth from a node to any leaf."""
    if node_id not in nodes:
        return current

    node = nodes[node_id]
    # Count this node as a move if it has a coordinate
    depth = current + (1 if node.coordinate else 0)

    if not node.children:
        return depth

    return max(_max_depth(nodes, child_id, depth) for child_id in node.children)


def _correct_line_length(nodes: dict[int, SolutionNode], node_id: int) -> int:
    """Count moves along the main correct line from root."""
    length = 0
    current_id = node_id

    while current_id in nodes:
        node = nodes[current_id]
        if node.coordinate:
            length += 1

        if not node.children:
            break

        # Follow the first correct child, or first child if none marked correct
        next_id: int | None = None
        for child_id in node.children:
            if child_id in nodes and nodes[child_id].is_correct:
                next_id = child_id
                break

        if next_id is None:
            # No explicitly correct child; follow first non-failure child
            for child_id in node.children:
                if child_id in nodes and not nodes[child_id].is_failure:
                    next_id = child_id
                    break

        if next_id is None:
            break

        current_id = next_id

    return length


def _subtree_is_wrong(nodes: dict[int, SolutionNode], node_id: int) -> bool:
    """Check if a subtree contains only wrong/failure nodes."""
    if node_id not in nodes:
        return True

    node = nodes[node_id]
    if node.is_correct:
        return False
    if node.is_failure:
        return True

    # If it has children, check them
    if not node.children:
        # Leaf with no correct/failure marker — assume wrong
        return True

    return all(_subtree_is_wrong(nodes, cid) for cid in node.children)
