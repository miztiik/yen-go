"""Tests for complexity metrics computation."""

from tools.weiqi101.complexity import ComplexityMetrics, compute_complexity
from tools.weiqi101.models import SolutionNode


def _make_node(node_id, coord="", correct=False, failure=False, children=None):
    """Helper to create a SolutionNode."""
    return SolutionNode(
        node_id=node_id,
        coordinate=coord,
        is_correct=correct,
        is_failure=failure,
        comment="",
        children=children or [],
    )


def test_empty_tree():
    """Empty node dict returns zero metrics."""
    cx = compute_complexity({})
    assert cx.depth == 0
    assert cx.total_nodes == 0
    assert cx.solution_length == 0
    assert cx.unique_first == 0
    assert cx.wrong_first == 0


def test_single_correct_move():
    """Root → single correct child."""
    nodes = {
        0: _make_node(0, children=[1]),
        1: _make_node(1, coord="pd", correct=True),
    }
    cx = compute_complexity(nodes)
    assert cx.depth == 1
    assert cx.total_nodes == 1
    assert cx.solution_length == 1
    assert cx.unique_first == 1
    assert cx.wrong_first == 0


def test_correct_and_wrong_first_moves():
    """Root → 2 children: one correct, one failure."""
    nodes = {
        0: _make_node(0, children=[1, 2]),
        1: _make_node(1, coord="pd", correct=True),
        2: _make_node(2, coord="qd", failure=True),
    }
    cx = compute_complexity(nodes)
    assert cx.unique_first == 2
    assert cx.wrong_first == 1
    assert cx.depth == 1
    assert cx.solution_length == 1


def test_deeper_tree():
    """Root → correct → response → correct (3-move line)."""
    nodes = {
        0: _make_node(0, children=[1]),
        1: _make_node(1, coord="pd", children=[2]),
        2: _make_node(2, coord="pe", children=[3]),
        3: _make_node(3, coord="qd", correct=True),
    }
    cx = compute_complexity(nodes)
    assert cx.depth == 3
    assert cx.total_nodes == 3
    assert cx.solution_length == 3
    assert cx.unique_first == 1


def test_branching_tree():
    """Root with 3 first-move options, one correct line with depth 2."""
    nodes = {
        0: _make_node(0, children=[1, 2, 3]),
        1: _make_node(1, coord="pd", children=[4]),  # correct line
        2: _make_node(2, coord="qd", failure=True),   # wrong
        3: _make_node(3, coord="rd", failure=True),   # wrong
        4: _make_node(4, coord="pe", correct=True),
    }
    cx = compute_complexity(nodes)
    assert cx.unique_first == 3
    assert cx.wrong_first == 2
    assert cx.depth == 2
    assert cx.total_nodes == 4
    assert cx.solution_length == 2


def test_to_yx_string_format():
    """YX string matches expected format."""
    cx = ComplexityMetrics(
        depth=3, total_nodes=12, solution_length=5,
        unique_first=3, wrong_first=2,
    )
    assert cx.to_yx_string() == "d:3;r:12;s:5;u:3;w:2"


def test_to_yx_string_zeros():
    cx = ComplexityMetrics()
    assert cx.to_yx_string() == "d:0;r:0;s:0;u:0;w:0"
