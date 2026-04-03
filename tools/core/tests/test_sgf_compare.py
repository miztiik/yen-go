"""Tests for tools.core.sgf_compare."""


from tools.core.sgf_compare import (
    MATCH_LEVEL_NAMES,
    MatchLevel,
    classify_match,
    extract_move_paths,
    full_hash,
    make_error_result,
    make_filename_mismatch_result,
    make_unmatched_result,
    position_hash,
)
from tools.core.sgf_parser import parse_sgf

# ---------------------------------------------------------------------------
# Fixtures — minimal SGF strings
# ---------------------------------------------------------------------------

# Simple puzzle: Black to play, one correct move
SIMPLE_SGF = "(;SZ[19]AB[cd][ce]AW[dd][de]PL[B](;B[cf])(;B[df]))"

# Same position, different whitespace/header
SIMPLE_SGF_ALT = "(;SZ[19]AB[cd][ce]AW[dd][de]PL[B] (;B[cf]) (;B[df]))"

# Same position but different move order in SGF (stones listed differently)
SIMPLE_SGF_REORDER = "(;SZ[19]AB[ce][cd]AW[de][dd]PL[B](;B[cf])(;B[df]))"

# Same position, White to play
SIMPLE_SGF_WHITE = "(;SZ[19]AB[cd][ce]AW[dd][de]PL[W](;W[cf])(;W[df]))"

# Same position, no PL property
SIMPLE_SGF_NO_PL = "(;SZ[19]AB[cd][ce]AW[dd][de](;B[cf])(;B[df]))"

# Same position, different first move
SIMPLE_SGF_DIFF_MOVE = "(;SZ[19]AB[cd][ce]AW[dd][de]PL[B](;B[ee])(;B[df]))"

# Same position, superset tree (extra variation)
SIMPLE_SGF_SUPERSET = "(;SZ[19]AB[cd][ce]AW[dd][de]PL[B](;B[cf])(;B[df])(;B[ee]))"

# Divergent tree — same first move, different variations
SIMPLE_SGF_DIVERGENT = "(;SZ[19]AB[cd][ce]AW[dd][de]PL[B](;B[cf])(;B[ee]))"

# Different position entirely
DIFFERENT_SGF = "(;SZ[19]AB[aa][ab]AW[ba][bb]PL[B](;B[ac]))"

# Empty SGF (no stones)
EMPTY_SGF = "(;SZ[19](;B[cd]))"

# 9x9 board
SMALL_SGF = "(;SZ[9]AB[cd][ce]AW[dd][de]PL[B](;B[cf]))"


# ---------------------------------------------------------------------------
# position_hash tests
# ---------------------------------------------------------------------------


class TestPositionHash:
    def test_deterministic(self):
        tree = parse_sgf(SIMPLE_SGF)
        h1 = position_hash(tree)
        h2 = position_hash(tree)
        assert h1 == h2

    def test_length_16(self):
        tree = parse_sgf(SIMPLE_SGF)
        h = position_hash(tree)
        assert len(h) == 16
        assert all(c in "0123456789abcdef" for c in h)

    def test_same_position_same_hash(self):
        tree_a = parse_sgf(SIMPLE_SGF)
        tree_b = parse_sgf(SIMPLE_SGF_REORDER)
        assert position_hash(tree_a) == position_hash(tree_b)

    def test_different_position_different_hash(self):
        tree_a = parse_sgf(SIMPLE_SGF)
        tree_b = parse_sgf(DIFFERENT_SGF)
        assert position_hash(tree_a) != position_hash(tree_b)

    def test_ignores_pl(self):
        tree_b = parse_sgf(SIMPLE_SGF)
        tree_w = parse_sgf(SIMPLE_SGF_WHITE)
        assert position_hash(tree_b) == position_hash(tree_w)

    def test_different_board_size(self):
        tree_19 = parse_sgf(SIMPLE_SGF)
        tree_9 = parse_sgf(SMALL_SGF)
        assert position_hash(tree_19) != position_hash(tree_9)


# ---------------------------------------------------------------------------
# full_hash tests
# ---------------------------------------------------------------------------


class TestFullHash:
    def test_returns_hash_when_pl_present(self):
        tree = parse_sgf(SIMPLE_SGF)
        h = full_hash(tree)
        assert h is not None
        assert len(h) == 16

    def test_returns_none_when_pl_absent(self):
        tree = parse_sgf(SIMPLE_SGF_NO_PL)
        h = full_hash(tree)
        assert h is None

    def test_different_pl_different_hash(self):
        tree_b = parse_sgf(SIMPLE_SGF)
        tree_w = parse_sgf(SIMPLE_SGF_WHITE)
        h_b = full_hash(tree_b)
        h_w = full_hash(tree_w)
        assert h_b != h_w

    def test_full_hash_differs_from_position_hash(self):
        tree = parse_sgf(SIMPLE_SGF)
        assert position_hash(tree) != full_hash(tree)


# ---------------------------------------------------------------------------
# extract_move_paths tests
# ---------------------------------------------------------------------------


class TestExtractMovePaths:
    def test_returns_set(self):
        tree = parse_sgf(SIMPLE_SGF)
        paths = extract_move_paths(tree.solution_tree)
        assert isinstance(paths, set)

    def test_correct_path_count(self):
        tree = parse_sgf(SIMPLE_SGF)
        paths = extract_move_paths(tree.solution_tree)
        assert len(paths) == 2  # two variations

    def test_order_independent(self):
        tree_a = parse_sgf(SIMPLE_SGF)
        tree_b = parse_sgf(SIMPLE_SGF_REORDER)
        assert extract_move_paths(tree_a.solution_tree) == extract_move_paths(
            tree_b.solution_tree
        )


# ---------------------------------------------------------------------------
# classify_match tests
# ---------------------------------------------------------------------------


class TestClassifyMatch:
    def test_byte_identical(self):
        tree_a = parse_sgf(SIMPLE_SGF)
        tree_b = parse_sgf(SIMPLE_SGF)
        result = classify_match(
            tree_a, tree_b, "a.sgf", "b.sgf",
            raw_a=SIMPLE_SGF, raw_b=SIMPLE_SGF,
        )
        assert result.match_level == MatchLevel.BYTE_IDENTICAL

    def test_tree_identical(self):
        tree_a = parse_sgf(SIMPLE_SGF)
        tree_b = parse_sgf(SIMPLE_SGF_ALT)
        result = classify_match(
            tree_a, tree_b, "a.sgf", "b.sgf",
            raw_a=SIMPLE_SGF, raw_b=SIMPLE_SGF_ALT,
        )
        assert result.match_level == MatchLevel.TREE_IDENTICAL

    def test_superset(self):
        tree_a = parse_sgf(SIMPLE_SGF)
        tree_b = parse_sgf(SIMPLE_SGF_SUPERSET)
        result = classify_match(
            tree_a, tree_b, "a.sgf", "b.sgf",
            raw_a=SIMPLE_SGF, raw_b=SIMPLE_SGF_SUPERSET,
        )
        assert result.match_level == MatchLevel.SUPERSET

    def test_divergent(self):
        tree_a = parse_sgf(SIMPLE_SGF)
        tree_b = parse_sgf(SIMPLE_SGF_DIVERGENT)
        result = classify_match(
            tree_a, tree_b, "a.sgf", "b.sgf",
            raw_a=SIMPLE_SGF, raw_b=SIMPLE_SGF_DIVERGENT,
        )
        assert result.match_level == MatchLevel.DIVERGENT

    def test_solution_differs(self):
        tree_a = parse_sgf(SIMPLE_SGF)
        tree_b = parse_sgf(SIMPLE_SGF_DIFF_MOVE)
        result = classify_match(
            tree_a, tree_b, "a.sgf", "b.sgf",
            raw_a=SIMPLE_SGF, raw_b=SIMPLE_SGF_DIFF_MOVE,
        )
        assert result.match_level == MatchLevel.SOLUTION_DIFFERS

    def test_pl_conflict(self):
        tree_a = parse_sgf(SIMPLE_SGF)
        tree_b = parse_sgf(SIMPLE_SGF_WHITE)
        result = classify_match(
            tree_a, tree_b, "a.sgf", "b.sgf",
            raw_a=SIMPLE_SGF, raw_b=SIMPLE_SGF_WHITE,
        )
        assert result.match_level == MatchLevel.POSITION_ONLY
        assert result.pl_status == "conflict"

    def test_pl_absent(self):
        tree_a = parse_sgf(SIMPLE_SGF)
        tree_b = parse_sgf(SIMPLE_SGF_NO_PL)
        result = classify_match(
            tree_a, tree_b, "a.sgf", "b.sgf",
            raw_a=SIMPLE_SGF, raw_b=SIMPLE_SGF_NO_PL,
        )
        assert result.match_level == MatchLevel.POSITION_ONLY
        assert result.pl_status == "absent_target"

    def test_to_dict_keys(self):
        tree = parse_sgf(SIMPLE_SGF)
        result = classify_match(
            tree, tree, "a.sgf", "b.sgf",
            raw_a=SIMPLE_SGF, raw_b=SIMPLE_SGF,
        )
        d = result.to_dict()
        assert "source_file" in d
        assert "match_level" in d
        assert "position_hash" in d
        assert "error" in d


# ---------------------------------------------------------------------------
# Helper result constructors
# ---------------------------------------------------------------------------


class TestMakeResults:
    def test_error_result(self):
        result = make_error_result("bad.sgf", "parse failed")
        assert result.match_level == MatchLevel.UNMATCHED
        assert result.error == "parse failed"
        assert result.target_file is None

    def test_unmatched_result(self):
        tree = parse_sgf(SIMPLE_SGF)
        result = make_unmatched_result("orphan.sgf", tree)
        assert result.match_level == MatchLevel.UNMATCHED
        assert result.position_hash is not None
        assert result.source_nodes is not None

    def test_filename_mismatch_result(self):
        tree_a = parse_sgf(SIMPLE_SGF)
        tree_b = parse_sgf(DIFFERENT_SGF)
        result = make_filename_mismatch_result(
            "prob01.sgf", tree_a, tree_b, "prob01.sgf"
        )
        assert result.match_level == MatchLevel.FILENAME_MISMATCH


# ---------------------------------------------------------------------------
# MatchLevel enum
# ---------------------------------------------------------------------------


class TestMatchLevel:
    def test_ordering(self):
        assert MatchLevel.UNMATCHED < MatchLevel.BYTE_IDENTICAL
        assert MatchLevel.POSITION_ONLY < MatchLevel.TREE_IDENTICAL

    def test_all_names_defined(self):
        for level in MatchLevel:
            assert level.value in MATCH_LEVEL_NAMES
