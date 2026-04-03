"""
Unit tests for compute_avg_refutation_depth and the 'a' field in YX complexity.

Phase 1 enrichment metric: average depth of wrong-move subtrees.
"""


from backend.puzzle_manager.core.complexity import (
    compute_avg_refutation_depth,
    compute_complexity_metrics,
)
from backend.puzzle_manager.core.primitives import Color, Point
from backend.puzzle_manager.core.sgf_parser import SGFGame, SolutionNode


class TestComputeAvgRefutationDepth:
    """Tests for compute_avg_refutation_depth function."""

    def test_no_wrong_moves_returns_zero(self):
        """Tree with no wrong moves should return 0."""
        root = SolutionNode()
        correct = SolutionNode(move=Point(3, 3), is_correct=True)
        root.children.append(correct)

        assert compute_avg_refutation_depth(root) == 0

    def test_single_wrong_leaf(self):
        """Single wrong child (leaf) should return depth 1."""
        root = SolutionNode()
        wrong = SolutionNode(move=Point(3, 3), is_correct=False, children=[])
        root.children.append(wrong)

        assert compute_avg_refutation_depth(root) == 1

    def test_wrong_branch_with_depth(self):
        """Wrong branch with children should measure full depth."""
        root = SolutionNode()
        wrong_child = SolutionNode(move=Point(4, 4), is_correct=True, children=[])
        wrong = SolutionNode(
            move=Point(3, 3), is_correct=False,
            children=[wrong_child],
        )
        root.children.append(wrong)

        # Wrong branch: wrong -> wrong_child (depth = 1 + 1 = 2)
        assert compute_avg_refutation_depth(root) == 2

    def test_multiple_wrong_branches_averaged(self):
        """Multiple wrong branches should be averaged."""
        root = SolutionNode()
        # Wrong branch 1: just a leaf (depth 1)
        wrong1 = SolutionNode(move=Point(3, 3), is_correct=False, children=[])
        # Wrong branch 2: wrong -> child -> grandchild (depth 3)
        grandchild = SolutionNode(move=Point(6, 6), children=[])
        child = SolutionNode(move=Point(5, 5), children=[grandchild])
        wrong2 = SolutionNode(
            move=Point(4, 4), is_correct=False,
            children=[child],
        )
        root.children.extend([wrong1, wrong2])

        # Average: (1 + 3) / 2 = 2.0
        assert compute_avg_refutation_depth(root) == 2

    def test_wrong_under_correct_collected(self):
        """Wrong moves nested under correct branches should be collected."""
        root = SolutionNode()
        # Correct branch with a wrong sub-branch
        wrong_leaf = SolutionNode(move=Point(5, 5), is_correct=False, children=[])
        correct = SolutionNode(
            move=Point(3, 3), is_correct=True,
            children=[wrong_leaf],
        )
        root.children.append(correct)

        # The wrong leaf under correct has depth 1
        assert compute_avg_refutation_depth(root) == 1

    def test_empty_root_returns_zero(self):
        """Root with no children returns 0."""
        root = SolutionNode()
        assert compute_avg_refutation_depth(root) == 0


class TestComplexityMetricsWithAvgRefDepth:
    """Tests for compute_complexity_metrics output including 'a' field."""

    def test_a_field_in_output(self):
        """YX string should contain 'a:' field."""
        game = self._make_game_with_solution()
        result = compute_complexity_metrics(game)
        assert ";a:" in result

    def test_five_fields_in_output(self):
        """YX should have exactly 5 semicolon-separated fields."""
        game = self._make_game_with_solution()
        result = compute_complexity_metrics(game)
        fields = result.split(";")
        assert len(fields) == 5
        keys = [f.split(":")[0] for f in fields]
        assert keys == ["d", "r", "s", "u", "a"]

    def test_no_solution_a_is_zero(self):
        """Game without solution should have a:0."""
        game = SGFGame(
            board_size=9,
            black_stones=[Point(3, 3)],
            white_stones=[Point(6, 6)],
        )
        result = compute_complexity_metrics(game)
        assert result.endswith(";a:0")

    def _make_game_with_solution(self):
        """Create a game with a simple solution tree."""
        root = SolutionNode()
        correct = SolutionNode(move=Point(4, 4), color=Color.BLACK, is_correct=True)
        wrong = SolutionNode(move=Point(5, 5), color=Color.BLACK, is_correct=False)
        root.children = [correct, wrong]

        return SGFGame(
            board_size=9,
            black_stones=[Point(3, 3)],
            white_stones=[Point(6, 6)],
            player_to_move=Color.BLACK,
            solution_tree=root,
        )
