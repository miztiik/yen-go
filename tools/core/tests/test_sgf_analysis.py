"""Tests for tools.core.sgf_analysis.

Covers:
- max_branch_depth vs count_total_nodes (different for branching SGFs)
- compute_solution_depth (correct-line only)
- compute_main_line_depth
- is_unique_first_move
- get_all_paths
- count_stones
- classify_difficulty / get_level_name / level_from_name
- compute_complexity_metrics
- detect_move_order
"""


from tools.core.sgf_analysis import (
    MoveOrderFlexibility,
    classify_difficulty,
    classify_difficulty_with_slug,
    compute_complexity_metrics,
    compute_main_line_depth,
    compute_solution_depth,
    count_stones,
    count_total_nodes,
    detect_move_order,
    get_all_paths,
    get_level_name,
    is_unique_first_move,
    level_from_name,
    max_branch_depth,
)
from tools.core.sgf_parser import SgfNode, parse_sgf

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SIMPLE_SGF = "(;SZ[19]PL[B]AB[cd][de]AW[ce][df](;B[cf]C[Correct!])(;B[eg]C[Wrong]))"

# Puzzle 6405 from GoProblems
PUZZLE_6405_SGF = (
    "(;AB[oc]AB[od]AB[oe]AB[pe]AB[pf]AB[qc]AB[qe]AB[qg]AB[qh]AB[qi]AB[qk]"
    "AB[rc]AB[rg]AB[ri]AB[rj]AW[nf]AW[pd]AW[pg]AW[ph]AW[pi]AW[pj]AW[qd]"
    "AW[qf]AW[qj]AW[rd]AW[re]AW[rf]AW[rk]AW[sh]SZ[19]PL[W]GM[1]FF[4]"
    "AP[Hibiscus:2.1]ST[3]"
    "(;W[sk]MN[2];B[sg]"
    "(;W[sj];B[rl];W[ql];B[pk]"
    "(;W[rm];B[pc];W[si];B[sd]"
    "(;W[ok];B[pl]"
    "(;W[sl];B[se]"
    "(;W[om]C[White captures 3 stones now. And if black doesn't play Q8 "
    "the capture is sente for white.RIGHT])"
    "(;W[pm]C[Black get's a ladder block this way. Playing at A would "
    "have captured Black unconditionally.]LB[pm:16]LB[om:A]))"
    "(;W[qm];B[ol]))"
    "(;W[sl];B[se]"
    "(;W[ok]C[Close, but a change in move order would give an even better result.])"
    "(;W[ol]C[Close, but a slight change would give an even better result.])))"
    "(;W[pl];B[ok];W[rm];B[pc];W[si];B[sd]))"
    "(;W[sf];B[pc])"
    "(;W[ql];B[pc]C[White has a better way of playing.]))"
    "(;W[ql];B[sg]C[White has a better way of playing])"
    "(;W[rl];B[sg]C[White has a better way of playing.])"
    "(;W[sj];B[rl];W[sk];B[sl];W[si];B[sg])"
    "(;W[sg];B[rl]C[White has a better way of playing]))"
)

DEEP_LINEAR_SGF = "(;SZ[19]PL[B];B[aa];W[bb];B[cc];W[dd];B[ee];W[ff];B[gg])"


# ---------------------------------------------------------------------------
# Test: depth calculation — the critical bug fix
# ---------------------------------------------------------------------------


class TestMaxBranchDepth:
    """max_branch_depth returns the true maximum depth of any single path."""

    def test_simple_two_branches(self):
        tree = parse_sgf(SIMPLE_SGF)
        depth = max_branch_depth(tree.solution_tree)
        assert depth == 1  # Each branch is just 1 move

    def test_linear_sgf(self):
        tree = parse_sgf(DEEP_LINEAR_SGF)
        depth = max_branch_depth(tree.solution_tree)
        assert depth == 7

    def test_puzzle_6405_depth_is_15(self):
        """The critical test: puzzle 6405 has max depth 15, NOT 44.

        The old regex-based count_solution_moves_in_sgf() returned 44
        (summing ALL nodes across all branches). The tree-based
        max_branch_depth() correctly returns 15.
        """
        tree = parse_sgf(PUZZLE_6405_SGF)
        depth = max_branch_depth(tree.solution_tree)
        assert depth == 15

    def test_empty_tree(self):
        node = SgfNode()
        assert max_branch_depth(node) == 0

    def test_single_move(self):
        tree = parse_sgf("(;SZ[19](;B[cd]))")
        assert max_branch_depth(tree.solution_tree) == 1


class TestMaxBranchDepthVsTotalNodes:
    """max_branch_depth and count_total_nodes give different results for branching trees."""

    def test_different_for_branching(self):
        tree = parse_sgf(SIMPLE_SGF)
        depth = max_branch_depth(tree.solution_tree)
        total = count_total_nodes(tree.solution_tree)
        assert depth == 1          # Max path length
        assert total == 3          # Root + 2 children
        assert total != depth      # They differ for branching trees

    def test_puzzle_6405_significantly_different(self):
        tree = parse_sgf(PUZZLE_6405_SGF)
        depth = max_branch_depth(tree.solution_tree)
        total = count_total_nodes(tree.solution_tree)
        assert depth == 15
        assert total > depth       # Much larger due to many branches


# ---------------------------------------------------------------------------
# Test: solution depth (correct-line)
# ---------------------------------------------------------------------------


class TestComputeSolutionDepth:
    """compute_solution_depth follows correct children only."""

    def test_simple_correct_line(self):
        tree = parse_sgf(SIMPLE_SGF)
        depth = compute_solution_depth(tree.solution_tree)
        assert depth == 1  # Only B[cf] is correct

    def test_deep_linear(self):
        tree = parse_sgf(DEEP_LINEAR_SGF)
        # All moves default to is_correct=True
        depth = compute_solution_depth(tree.solution_tree)
        assert depth == 7

    def test_empty_tree(self):
        assert compute_solution_depth(SgfNode()) == 0


class TestComputeMainLineDepth:
    """compute_main_line_depth follows first child regardless of correctness."""

    def test_follows_first_child(self):
        tree = parse_sgf(SIMPLE_SGF)
        depth = compute_main_line_depth(tree.solution_tree)
        assert depth == 1

    def test_deep_linear(self):
        tree = parse_sgf(DEEP_LINEAR_SGF)
        assert compute_main_line_depth(tree.solution_tree) == 7


# ---------------------------------------------------------------------------
# Test: path enumeration
# ---------------------------------------------------------------------------


class TestGetAllPaths:
    """get_all_paths enumerates all root-to-leaf paths."""

    def test_simple_two_paths(self):
        tree = parse_sgf(SIMPLE_SGF)
        paths = get_all_paths(tree.solution_tree)
        assert len(paths) == 2

    def test_single_linear_path(self):
        tree = parse_sgf(DEEP_LINEAR_SGF)
        paths = get_all_paths(tree.solution_tree)
        assert len(paths) == 1
        assert len(paths[0]) == 8  # Root + 7 moves

    def test_puzzle_6405_twelve_paths(self):
        tree = parse_sgf(PUZZLE_6405_SGF)
        paths = get_all_paths(tree.solution_tree)
        assert len(paths) == 12


# ---------------------------------------------------------------------------
# Test: stones and first move
# ---------------------------------------------------------------------------


class TestStonesAndFirstMove:
    """count_stones and is_unique_first_move."""

    def test_count_stones(self):
        tree = parse_sgf(SIMPLE_SGF)
        assert count_stones(tree) == 4  # 2 black + 2 white

    def test_unique_first_move_with_two_branches(self):
        tree = parse_sgf(SIMPLE_SGF)
        # Both branches exist but only one is correct
        assert is_unique_first_move(tree) is True

    def test_multiple_correct_first_moves(self):
        sgf = "(;SZ[19](;B[cd]C[Correct!])(;B[ef]C[Correct!]))"
        tree = parse_sgf(sgf)
        assert is_unique_first_move(tree) is False

    def test_no_solution(self):
        tree = parse_sgf("(;SZ[19]AB[cd])")
        assert is_unique_first_move(tree) is True  # Default


# ---------------------------------------------------------------------------
# Test: complexity metrics
# ---------------------------------------------------------------------------


class TestComplexityMetrics:
    """compute_complexity_metrics produces YX string."""

    def test_format(self):
        tree = parse_sgf(SIMPLE_SGF)
        yx = compute_complexity_metrics(tree)
        assert yx.startswith("d:")
        assert ";r:" in yx
        assert ";s:" in yx
        assert ";u:" in yx

    def test_values(self):
        tree = parse_sgf(SIMPLE_SGF)
        yx = compute_complexity_metrics(tree)
        # d:1 (1 correct move), r:3 (root+2 children), s:4 (4 stones), u:1
        assert yx == "d:1;r:3;s:4;u:1"


# ---------------------------------------------------------------------------
# Test: difficulty classification
# ---------------------------------------------------------------------------


class TestClassification:
    """classify_difficulty and level name mapping."""

    def test_simple_puzzle_is_easy(self):
        tree = parse_sgf(SIMPLE_SGF)
        level = classify_difficulty(tree)
        assert 1 <= level <= 4

    def test_level_name_mapping(self):
        assert get_level_name(1) == "novice"
        assert get_level_name(5) == "upper-intermediate"
        assert get_level_name(9) == "expert"
        assert get_level_name(99) == "unknown"

    def test_level_from_name(self):
        assert level_from_name("beginner") == 2
        assert level_from_name("expert") == 9
        assert level_from_name("nonexistent") is None
        assert level_from_name("upper-intermediate") == 5

    def test_classify_with_slug(self):
        tree = parse_sgf(SIMPLE_SGF)
        level, slug = classify_difficulty_with_slug(tree)
        assert slug == get_level_name(level)


# ---------------------------------------------------------------------------
# Test: move order detection
# ---------------------------------------------------------------------------


class TestMoveOrderDetection:
    """detect_move_order classifies strict vs flexible."""

    def test_single_correct_is_strict(self):
        tree = parse_sgf(SIMPLE_SGF)
        order = detect_move_order(tree.solution_tree)
        assert order == MoveOrderFlexibility.STRICT

    def test_multiple_correct_is_flexible(self):
        sgf = "(;SZ[19](;B[cd]C[Correct!])(;B[ef]C[Correct!]))"
        tree = parse_sgf(sgf)
        order = detect_move_order(tree.solution_tree)
        assert order == MoveOrderFlexibility.FLEXIBLE

    def test_transposition_marker(self):
        sgf = "(;SZ[19](;B[cd]C[also correct]))"
        tree = parse_sgf(sgf)
        order = detect_move_order(tree.solution_tree)
        assert order == MoveOrderFlexibility.FLEXIBLE

    def test_empty_tree_is_strict(self):
        order = detect_move_order(SgfNode())
        assert order == MoveOrderFlexibility.STRICT
