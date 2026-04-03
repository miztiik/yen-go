"""
Unit tests for quality and complexity computation modules.

Tests compute_quality_metrics() and compute_complexity_metrics().
"""

from unittest.mock import MagicMock

from backend.puzzle_manager.core.complexity import (
    compute_complexity_metrics,
    compute_solution_depth,
    count_stones,
    count_total_nodes,
    is_unique_first_move,
)
from backend.puzzle_manager.core.quality import (
    compute_comment_level,
    compute_puzzle_quality_level,
    compute_quality_metrics,
    count_refutation_moves,
    has_teaching_comments,
    parse_ac_level,
    parse_quality_level,  # Spec 102
)
from backend.puzzle_manager.core.sgf_parser import SGFGame, SolutionNode

# --- Quality Module Tests ---


class TestComputeQualityMetrics:
    """Tests for compute_quality_metrics function."""

    def test_returns_formatted_string(self):
        """Should return properly formatted YQ string."""
        game = self._make_game(refutation_count=2, has_comments=True)
        result = compute_quality_metrics(game)

        assert result.startswith("q:")
        assert ";rc:" in result
        assert ";hc:" in result
        assert ";ac:" in result

    def test_quality_level_in_range(self):
        """Quality level should be 1-5."""
        game = self._make_game(refutation_count=3, has_comments=False)
        result = compute_quality_metrics(game)

        # Extract level
        level = int(result.split(";")[0].split(":")[1])
        assert 1 <= level <= 5

    def test_refutation_count_included(self):
        """Refutation count should be in output."""
        game = self._make_game(refutation_count=5, has_comments=False)
        result = compute_quality_metrics(game)

        # Extract rc value
        parts = result.split(";")
        rc_part = [p for p in parts if p.startswith("rc:")][0]
        rc_value = int(rc_part.split(":")[1])
        assert rc_value == 5

    def test_has_comments_flag(self):
        """Comment level should reflect comment content."""
        game_with_teaching = self._make_game(refutation_count=0, has_comments=True)
        game_without = self._make_game(refutation_count=0, has_comments=False)
        game_with_markers = self._make_game_with_markers_only()

        result_teaching = compute_quality_metrics(game_with_teaching)
        result_without = compute_quality_metrics(game_without)
        result_markers = compute_quality_metrics(game_with_markers)

        assert "hc:2" in result_teaching
        assert "hc:0" in result_without
        assert "hc:1" in result_markers

    def _make_game_with_markers_only(self):
        """Create a mock game with only correctness markers (no teaching text)."""
        game = MagicMock()
        game.has_solution = True
        game.yengo_props.quality = None

        root = MagicMock()
        root.comment = None
        root.is_correct = True

        correct = MagicMock()
        correct.is_correct = True
        correct.children = []
        correct.comment = "Correct!"

        wrong = MagicMock()
        wrong.is_correct = False
        wrong.children = []
        wrong.comment = "Wrong"

        root.children = [correct, wrong]
        game.solution_tree = root

        return game

    def _make_game(self, refutation_count: int, has_comments: bool):
        """Create a mock game for testing."""
        game = MagicMock()
        game.has_solution = True
        game.yengo_props.quality = None

        # Build solution tree with refutation moves
        root = MagicMock()
        root.comment = "Teaching comment" if has_comments else None
        root.is_correct = True
        children = []

        # Add correct child
        correct = MagicMock()
        correct.is_correct = True
        correct.children = []
        correct.comment = None
        children.append(correct)

        # Add refutation children
        for _ in range(refutation_count):
            wrong = MagicMock()
            wrong.is_correct = False
            wrong.children = []
            wrong.comment = None
            children.append(wrong)

        root.children = children
        game.solution_tree = root

        return game


class TestCountRefutationMoves:
    """Tests for count_refutation_moves function."""

    def test_counts_incorrect_children(self):
        """Should count only incorrect children."""
        root = MagicMock()

        correct = MagicMock()
        correct.is_correct = True
        correct.children = []

        wrong1 = MagicMock()
        wrong1.is_correct = False
        wrong1.children = []

        wrong2 = MagicMock()
        wrong2.is_correct = False
        wrong2.children = []

        root.children = [correct, wrong1, wrong2]

        count = count_refutation_moves(root)
        assert count == 2

    def test_counts_nested_refutations(self):
        """Should count refutations at all levels."""
        root = MagicMock()

        # First level correct
        correct = MagicMock()
        correct.is_correct = True

        # Second level has refutation
        correct_child = MagicMock()
        correct_child.is_correct = True
        correct_child.children = []

        wrong_child = MagicMock()
        wrong_child.is_correct = False
        wrong_child.children = []

        correct.children = [correct_child, wrong_child]
        root.children = [correct]

        count = count_refutation_moves(root)
        assert count == 1  # Only the nested wrong child


class TestHasTeachingComments:
    """Tests for has_teaching_comments function."""

    def test_detects_root_comment(self):
        """Should detect teaching comment on root node."""
        root = MagicMock()
        root.comment = "This teaches something"
        root.children = []

        assert has_teaching_comments(root) is True

    def test_detects_nested_comment(self):
        """Should detect teaching comment in child nodes."""
        root = MagicMock()
        root.comment = None

        child = MagicMock()
        child.comment = "Explanation here"
        child.children = []

        root.children = [child]

        assert has_teaching_comments(root) is True

    def test_no_comments(self):
        """Should return False when no comments."""
        root = MagicMock()
        root.comment = None
        root.children = []

        assert has_teaching_comments(root) is False

    def test_bare_correct_marker_counts_as_comment(self):
        """Bare 'Correct!' marker should count (hc >= 1)."""
        root = MagicMock()
        root.comment = "Correct!"
        root.children = []

        assert has_teaching_comments(root) is True

    def test_bare_wrong_marker_counts_as_comment(self):
        """Bare 'Wrong' marker should count (hc >= 1)."""
        root = MagicMock()
        root.comment = "Wrong"
        root.children = []

        assert has_teaching_comments(root) is True


class TestComputeCommentLevel:
    """Tests for compute_comment_level function (3-level hc)."""

    def test_no_comments_returns_0(self):
        """No comments at all → level 0."""
        root = MagicMock()
        root.comment = None
        root.children = []

        assert compute_comment_level(root) == 0

    def test_empty_comment_returns_0(self):
        """Empty string comment → level 0."""
        root = MagicMock()
        root.comment = ""
        root.children = []

        assert compute_comment_level(root) == 0

    def test_bare_correct_marker_returns_1(self):
        """'Correct!' is a correctness marker only → level 1."""
        root = MagicMock()
        root.comment = "Correct!"
        root.children = []

        assert compute_comment_level(root) == 1

    def test_bare_wrong_marker_returns_1(self):
        """'Wrong' is a correctness marker only → level 1."""
        root = MagicMock()
        root.comment = "Wrong"
        root.children = []

        assert compute_comment_level(root) == 1

    def test_bare_plus_marker_returns_1(self):
        """'+' is a minimalist correctness marker → level 1."""
        root = MagicMock()
        root.comment = "+"
        root.children = []

        assert compute_comment_level(root) == 1

    def test_bare_right_marker_returns_1(self):
        """'RIGHT' is a correctness marker only → level 1."""
        root = MagicMock()
        root.comment = "RIGHT"
        root.children = []

        assert compute_comment_level(root) == 1

    def test_teaching_text_returns_2(self):
        """Genuine teaching text → level 2."""
        root = MagicMock()
        root.comment = "This creates two eyes"
        root.children = []

        assert compute_comment_level(root) == 2

    def test_correct_with_teaching_suffix_returns_2(self):
        """'Correct! Good tesuji' has teaching content → level 2."""
        root = MagicMock()
        root.comment = "Correct! Good tesuji here"
        root.children = []

        assert compute_comment_level(root) == 2

    def test_wrong_with_explanation_returns_2(self):
        """'Wrong — White escapes via ladder' has teaching content → level 2."""
        root = MagicMock()
        root.comment = "Wrong \u2014 White escapes via ladder"
        root.children = []

        assert compute_comment_level(root) == 2

    def test_nested_teaching_comment_returns_2(self):
        """Teaching comment in child node → level 2."""
        root = MagicMock()
        root.comment = "Wrong"

        child = MagicMock()
        child.comment = "Only ko."
        child.children = []

        root.children = [child]

        assert compute_comment_level(root) == 2

    def test_mixed_markers_and_teaching_returns_2(self):
        """Some nodes have markers, one has teaching → level 2."""
        root = MagicMock()
        root.comment = None

        marker_child = MagicMock()
        marker_child.comment = "Correct!"
        marker_child.children = []

        teaching_child = MagicMock()
        teaching_child.comment = "White is captured due to shortage of liberties"
        teaching_child.children = []

        root.children = [marker_child, teaching_child]

        assert compute_comment_level(root) == 2

    def test_all_markers_no_teaching_returns_1(self):
        """All nodes have only bare markers → level 1."""
        root = MagicMock()
        root.comment = None

        c1 = MagicMock()
        c1.comment = "Correct!"
        c1.children = []

        c2 = MagicMock()
        c2.comment = "Wrong"
        c2.children = []

        root.children = [c1, c2]

        assert compute_comment_level(root) == 1


class TestComputePuzzleQualityLevel:
    """Tests for compute_puzzle_quality_level function."""

    def _make_game(self, refutation_count: int = 0, has_comments: bool = False) -> SGFGame:
        """Create mock SGFGame with specified refutations and comments."""
        game = MagicMock(spec=SGFGame)
        game.has_solution = refutation_count > 0 or has_comments
        game.yengo_props = MagicMock()
        game.yengo_props.quality = None

        # Create solution tree with refutations
        root = SolutionNode(move=None, is_correct=True, comment="")
        for i in range(refutation_count):
            root.children.append(SolutionNode(move=("B", (i, i)), is_correct=False, comment=""))
        if has_comments:
            root.comment = "Teaching comment here"

        game.solution_tree = root
        return game

    def test_level_1_no_solution(self):
        """No solution tree → level 1 (unverified, worst)."""
        game = MagicMock(spec=SGFGame)
        game.has_solution = False
        game.yengo_props = MagicMock()
        game.yengo_props.quality = None
        level = compute_puzzle_quality_level(game)
        assert level == 1

    def test_level_2_solution_no_refutations(self):
        """Solution but no refutations → level 2 (basic)."""
        game = self._make_game(refutation_count=0, has_comments=False)
        game.has_solution = True  # Override
        game.solution_tree = SolutionNode(move=None, is_correct=True, comment="")
        game.yengo_props = MagicMock()
        game.yengo_props.quality = None
        level = compute_puzzle_quality_level(game)
        assert level == 2

    def test_level_3_with_refutations(self):
        """1+ refutations → level 3 (standard)."""
        game = self._make_game(refutation_count=1, has_comments=False)
        level = compute_puzzle_quality_level(game)
        assert level == 3

    def test_level_4_refutations_and_comments(self):
        """2+ refutations + comments + ac≥1 → level 4 (high)."""
        game = self._make_game(refutation_count=2, has_comments=True)
        game.yengo_props.quality = "q:0;rc:0;hc:0;ac:1"  # ac=1 (enriched)
        level = compute_puzzle_quality_level(game)
        assert level == 4

    def test_level_5_premium(self):
        """3+ refutations + comments + ac≥2 → level 5 (premium, best)."""
        game = self._make_game(refutation_count=3, has_comments=True)
        game.yengo_props.quality = "q:0;rc:0;hc:0;ac:2"  # ac=2 (ai_solved)
        level = compute_puzzle_quality_level(game)
        assert level == 5


class TestParseQualityLevel:
    """Tests for parse_quality_level function (Spec 102)."""

    def test_parses_valid_yq_string(self):
        """Should extract quality level from valid YQ string."""
        assert parse_quality_level("q:3;rc:2;hc:1") == 3
        assert parse_quality_level("q:5;rc:5;hc:1") == 5
        assert parse_quality_level("q:1;rc:0;hc:0") == 1

    def test_returns_none_for_none_input(self):
        """Should return None when input is None."""
        assert parse_quality_level(None) is None

    def test_returns_none_for_empty_string(self):
        """Should return None for empty string."""
        assert parse_quality_level("") is None

    def test_returns_none_for_invalid_format(self):
        """Should return None for invalid format."""
        assert parse_quality_level("invalid") is None
        assert parse_quality_level("abc:xyz") is None
        assert parse_quality_level("q:abc") is None

    def test_returns_none_for_out_of_range(self):
        """Should return None for quality level outside 1-5."""
        assert parse_quality_level("q:0;rc:0;hc:0") is None
        assert parse_quality_level("q:6;rc:0;hc:0") is None
        assert parse_quality_level("q:10;rc:0;hc:0") is None

    def test_handles_minimal_format(self):
        """Should parse just q:{level} without other components."""
        assert parse_quality_level("q:4") == 4


class TestMinAcQualityScoring:
    """Tests for min_ac quality scoring integration (AC-6, AC-7, AC-10)."""

    def _make_game(self, refutation_count: int, has_comments: bool, ac: int = 0) -> MagicMock:
        """Create mock game with specified refutations, comments, and ac level."""
        game = MagicMock(spec=SGFGame)
        game.has_solution = True
        game.yengo_props = MagicMock()
        game.yengo_props.quality = f"q:0;rc:0;hc:0;ac:{ac}" if ac > 0 else None

        root = SolutionNode(move=None, is_correct=True, comment="")
        for i in range(refutation_count):
            root.children.append(SolutionNode(move=("B", (i, i)), is_correct=False, comment=""))
        if has_comments:
            root.comment = "Teaching comment here"

        game.solution_tree = root
        return game

    def test_level_4_requires_min_ac_1(self):
        """Level 4 not reachable without ac >= 1 (min_ac requirement)."""
        game = self._make_game(refutation_count=2, has_comments=True, ac=0)
        level = compute_puzzle_quality_level(game)
        assert level == 3  # Falls back to level 3 (no ac)

    def test_level_4_with_ac_1(self):
        """Level 4 reachable with ac=1 (enriched)."""
        game = self._make_game(refutation_count=2, has_comments=True, ac=1)
        level = compute_puzzle_quality_level(game)
        assert level == 4

    def test_level_5_requires_min_ac_2(self):
        """Level 5 not reachable without ac >= 2 (min_ac requirement)."""
        game = self._make_game(refutation_count=3, has_comments=True, ac=1)
        level = compute_puzzle_quality_level(game)
        assert level == 4  # Falls to level 4 (ac=1 meets level 4 but not 5)

    def test_level_5_with_ac_2(self):
        """Level 5 reachable with ac=2 (ai_solved)."""
        game = self._make_game(refutation_count=3, has_comments=True, ac=2)
        level = compute_puzzle_quality_level(game)
        assert level == 5

    def test_level_5_with_ac_3(self):
        """Level 5 reachable with ac=3 (verified) — exceeds minimum."""
        game = self._make_game(refutation_count=3, has_comments=True, ac=3)
        level = compute_puzzle_quality_level(game)
        assert level == 5

    def test_levels_1_to_3_no_regression(self):
        """Levels 1-3 have no min_ac requirement — scores identical to before.

        AC-7: quality filter continues to work (no regression for lower levels).
        """
        # Level 1: no solution
        game1 = MagicMock(spec=SGFGame)
        game1.has_solution = False
        game1.yengo_props = MagicMock()
        game1.yengo_props.quality = None
        assert compute_puzzle_quality_level(game1) == 1

        # Level 2: solution, no refutations
        game2 = self._make_game(refutation_count=0, has_comments=False, ac=0)
        game2.solution_tree = SolutionNode(move=None, is_correct=True, comment="")
        assert compute_puzzle_quality_level(game2) == 2

        # Level 3: 1+ refutations
        game3 = self._make_game(refutation_count=1, has_comments=False, ac=0)
        assert compute_puzzle_quality_level(game3) == 3

    def test_compute_quality_metrics_preserves_ac(self):
        """compute_quality_metrics() should preserve existing ac, not hardcode ac:0."""
        game = self._make_game(refutation_count=2, has_comments=True, ac=1)
        result = compute_quality_metrics(game)
        assert "ac:1" in result

    def test_compute_quality_metrics_ac_0_when_no_yq(self):
        """compute_quality_metrics() outputs ac:0 when no existing YQ."""
        game = self._make_game(refutation_count=1, has_comments=False, ac=0)
        result = compute_quality_metrics(game)
        assert "ac:0" in result

    def test_parse_ac_level_integration(self):
        """parse_ac_level correctly extracts ac from YQ strings."""
        assert parse_ac_level("q:3;rc:2;hc:1;ac:1") == 1
        assert parse_ac_level("q:3;rc:2;hc:1;ac:2") == 2
        assert parse_ac_level("q:3;rc:2;hc:1;ac:0") == 0
        assert parse_ac_level("q:3;rc:2;hc:1") == 0  # missing ac → 0
        assert parse_ac_level(None) == 0


# --- Complexity Module Tests ---


class TestComputeComplexityMetrics:
    """Tests for compute_complexity_metrics function."""

    def test_returns_formatted_string(self):
        """Should return properly formatted YX string."""
        game = self._make_game(depth=3, nodes=5, stones=10, unique=True)
        result = compute_complexity_metrics(game)

        assert result.startswith("d:")
        assert ";r:" in result
        assert ";s:" in result
        assert ";u:" in result

    def test_depth_extracted(self):
        """Depth should match solution line."""
        game = self._make_game(depth=5, nodes=10, stones=15, unique=True)
        result = compute_complexity_metrics(game)

        # Extract depth
        depth = int(result.split(";")[0].split(":")[1])
        assert depth == 5

    def test_stones_counted(self):
        """Stone count should be accurate."""
        game = self._make_game(depth=2, nodes=3, stones=24, unique=True)
        result = compute_complexity_metrics(game)

        # Extract stones
        parts = result.split(";")
        s_part = [p for p in parts if p.startswith("s:")][0]
        stone_count = int(s_part.split(":")[1])
        assert stone_count == 24

    def test_uniqueness_flag(self):
        """Uniqueness flag should be 0 or 1."""
        game_unique = self._make_game(depth=2, nodes=3, stones=10, unique=True)
        game_miai = self._make_game(depth=2, nodes=3, stones=10, unique=False)

        result_unique = compute_complexity_metrics(game_unique)
        result_miai = compute_complexity_metrics(game_miai)

        assert "u:1" in result_unique
        assert "u:0" in result_miai

    def _make_game(self, depth: int, nodes: int, stones: int, unique: bool):
        """Create a mock game for testing."""
        game = MagicMock()
        game.has_solution = True
        game.black_stones = [MagicMock() for _ in range(stones // 2)]
        game.white_stones = [MagicMock() for _ in range(stones - stones // 2)]

        # Build solution tree with specified depth
        root = MagicMock()
        current = root

        # First level children for uniqueness testing
        if unique:
            correct = MagicMock()
            correct.is_correct = True
            root.children = [correct]
        else:
            # Multiple correct first moves (miai)
            correct1 = MagicMock()
            correct1.is_correct = True
            correct2 = MagicMock()
            correct2.is_correct = True
            root.children = [correct1, correct2]

        # Build depth chain
        for i in range(depth):
            if current.children:
                child = current.children[0]
            else:
                child = MagicMock()
                child.is_correct = True
                current.children = [child]

            if i < depth - 1:
                next_child = MagicMock()
                next_child.is_correct = True
                next_child.children = []
                child.children = [next_child]
                current = child
            else:
                child.children = []

        game.solution_tree = root

        return game


class TestComputeSolutionDepth:
    """Tests for compute_solution_depth function."""

    def test_empty_tree_depth_zero(self):
        """Empty tree has depth 0."""
        root = MagicMock()
        root.children = []

        depth = compute_solution_depth(root)
        assert depth == 0

    def test_single_move_depth_one(self):
        """Single correct move has depth 1."""
        root = MagicMock()
        child = MagicMock()
        child.is_correct = True
        child.children = []
        root.children = [child]

        depth = compute_solution_depth(root)
        assert depth == 1

    def test_follows_correct_path(self):
        """Should only follow correct moves."""
        root = MagicMock()

        wrong = MagicMock()
        wrong.is_correct = False
        wrong.children = []

        correct = MagicMock()
        correct.is_correct = True

        next_correct = MagicMock()
        next_correct.is_correct = True
        next_correct.children = []

        correct.children = [next_correct]
        root.children = [wrong, correct]  # Wrong first, correct second

        depth = compute_solution_depth(root)
        # Should find correct and go 2 deep
        assert depth == 2


class TestCountTotalNodes:
    """Tests for count_total_nodes function."""

    def test_single_node(self):
        """Single node returns 1."""
        root = MagicMock()
        root.children = []

        count = count_total_nodes(root)
        assert count == 1

    def test_counts_all_children(self):
        """Should count all nodes in tree."""
        root = MagicMock()
        child1 = MagicMock()
        child1.children = []
        child2 = MagicMock()
        child2.children = []
        root.children = [child1, child2]

        count = count_total_nodes(root)
        assert count == 3  # root + 2 children


class TestCountStones:
    """Tests for count_stones function."""

    def test_counts_both_colors(self):
        """Should count black and white stones."""
        game = MagicMock()
        game.black_stones = [1, 2, 3, 4, 5]  # 5 black
        game.white_stones = [6, 7, 8]  # 3 white

        count = count_stones(game)
        assert count == 8


class TestIsUniqueFirstMove:
    """Tests for is_unique_first_move function."""

    def test_unique_single_correct(self):
        """Single correct first move → unique."""
        game = MagicMock()
        game.has_solution = True

        root = MagicMock()
        correct = MagicMock()
        correct.is_correct = True
        wrong = MagicMock()
        wrong.is_correct = False
        root.children = [correct, wrong]

        game.solution_tree = root

        assert is_unique_first_move(game) is True

    def test_miai_multiple_correct(self):
        """Multiple correct first moves → not unique."""
        game = MagicMock()
        game.has_solution = True

        root = MagicMock()
        correct1 = MagicMock()
        correct1.is_correct = True
        correct2 = MagicMock()
        correct2.is_correct = True
        root.children = [correct1, correct2]

        game.solution_tree = root

        assert is_unique_first_move(game) is False

    def test_no_solution_defaults_unique(self):
        """No solution → defaults to unique."""
        game = MagicMock()
        game.has_solution = False

        assert is_unique_first_move(game) is True
