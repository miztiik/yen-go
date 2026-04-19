"""Tests for tools.core.sgf_merge."""

from __future__ import annotations

import pytest

from tools.core.sgf_compare import CompareResult, MatchLevel
from tools.core.sgf_merge import (
    MergeDecision,
    build_merged_sgf,
    infer_correct_first_moves,
    merge_comments,
    merge_solution_trees,
    plan_merge,
)
from tools.core.sgf_parser import SgfNode, parse_sgf
from tools.core.sgf_types import Color, Point, PositionTransform


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_compare_result(**overrides) -> CompareResult:
    """Create a CompareResult with sensible defaults, overridden by kwargs."""
    defaults = dict(
        source_file="prob0001.sgf",
        target_file="prob0001.sgf",
        match_level=MatchLevel.TREE_IDENTICAL,
        position_hash="abc123",
        full_hash="def456",
        board_size=19,
        player_to_move_source="B",
        player_to_move_target="B",
        pl_status="confirmed",
        first_move_match=True,
        correct_line_match=True,
        source_nodes=10,
        target_nodes=10,
        source_depth=3,
        target_depth=3,
        comments_differ=False,
        markers_differ=False,
        detail="Test",
        error=None,
        match_method="identity",
        transform_rotation=None,
        transform_reflect=None,
    )
    defaults.update(overrides)
    return CompareResult(**defaults)


# ---------------------------------------------------------------------------
# plan_merge tests
# ---------------------------------------------------------------------------


class TestPlanMerge:
    """Test merge decision logic for each match level."""

    def test_unmatched_copies_primary(self):
        r = _make_compare_result(
            match_level=MatchLevel.UNMATCHED,
            target_file=None,
        )
        d = plan_merge(r)
        assert d.action == "copy_primary"

    def test_byte_identical_uses_primary(self):
        r = _make_compare_result(match_level=MatchLevel.BYTE_IDENTICAL)
        d = plan_merge(r)
        assert d.action == "use_primary"

    def test_tree_identical_same_comments_uses_primary(self):
        r = _make_compare_result(
            match_level=MatchLevel.TREE_IDENTICAL,
            comments_differ=False,
        )
        d = plan_merge(r)
        assert d.action == "use_primary"

    def test_tree_identical_different_comments_merges(self):
        r = _make_compare_result(
            match_level=MatchLevel.TREE_IDENTICAL,
            comments_differ=True,
        )
        d = plan_merge(r)
        assert d.action == "merge_trees"

    def test_superset_uses_secondary(self):
        r = _make_compare_result(
            match_level=MatchLevel.SUPERSET,
            source_nodes=5,
            target_nodes=12,
        )
        d = plan_merge(r)
        assert d.action == "use_secondary"

    def test_divergent_merges_trees(self):
        r = _make_compare_result(
            match_level=MatchLevel.DIVERGENT,
            source_nodes=8,
            target_nodes=10,
        )
        d = plan_merge(r)
        assert d.action == "merge_trees"

    def test_solution_differs_skips(self):
        r = _make_compare_result(match_level=MatchLevel.SOLUTION_DIFFERS)
        d = plan_merge(r)
        assert d.action == "skip"

    def test_position_only_skips(self):
        r = _make_compare_result(match_level=MatchLevel.POSITION_ONLY)
        d = plan_merge(r)
        assert d.action == "skip"

    def test_below_min_level_skips(self):
        r = _make_compare_result(match_level=MatchLevel.DIVERGENT)
        d = plan_merge(r, min_level=5)
        assert d.action == "skip"
        assert "below min_level" in d.reason

    def test_d4_transform_preserved(self):
        r = _make_compare_result(
            match_level=MatchLevel.DIVERGENT,
            match_method="d4_symmetry",
            transform_rotation=90,
            transform_reflect=False,
        )
        d = plan_merge(r)
        assert d.transform is not None
        assert d.transform.rotation == 90
        assert d.transform.reflect is False
        assert d.match_method == "d4_symmetry"


# ---------------------------------------------------------------------------
# merge_comments tests
# ---------------------------------------------------------------------------


class TestMergeComments:
    def test_both_empty(self):
        assert merge_comments("", "") == ""

    def test_primary_only(self):
        assert merge_comments("Hello", "") == "Hello"

    def test_secondary_only(self):
        assert merge_comments("", "World") == "World"

    def test_identical(self):
        assert merge_comments("Same text", "Same text") == "Same text"

    def test_different(self):
        result = merge_comments("Primary comment", "Secondary comment")
        assert "Primary comment" in result
        assert "Secondary comment" in result
        assert "---" in result
        # Primary should come first
        assert result.index("Primary") < result.index("Secondary")

    def test_strips_whitespace(self):
        assert merge_comments("  Hello  ", "  Hello  ") == "Hello"


# ---------------------------------------------------------------------------
# merge_solution_trees tests
# ---------------------------------------------------------------------------


class TestMergeSolutionTrees:
    # Primary: B[cd] correct, B[ef] wrong
    PRIMARY_SGF = "(;SZ[19]AB[cc][cd]AW[dc][dd]PL[B](;B[ce]C[correct])(;B[de]C[wrong]BM[1]))"
    # Secondary: B[cd] correct (same), B[df] wrong (different branch)
    SECONDARY_SGF = "(;SZ[19]AB[cc][cd]AW[dc][dd]PL[B](;B[ce]C[also correct])(;B[df]C[another wrong]BM[1]))"

    def test_identity_merge_grafts_new_branch(self):
        """Secondary has an extra branch (B[df]) not in primary."""
        primary = parse_sgf(self.PRIMARY_SGF)
        secondary = parse_sgf(self.SECONDARY_SGF)

        merged = merge_solution_trees(
            primary.solution_tree,
            secondary.solution_tree,
            19,
            None,
        )

        # Should have 3 children: B[ce], B[de] from primary, B[df] grafted from secondary
        assert len(merged.children) == 3

        moves = {c.move.to_sgf() if c.move else "?" for c in merged.children}
        assert moves == {"ce", "de", "df"}

    def test_shared_move_comments_merged(self):
        """B[ce] exists in both — comments should be merged."""
        primary = parse_sgf(self.PRIMARY_SGF)
        secondary = parse_sgf(self.SECONDARY_SGF)

        merged = merge_solution_trees(
            primary.solution_tree,
            secondary.solution_tree,
            19,
            None,
        )

        # Find the B[ce] child
        ce_node = next(c for c in merged.children if c.move and c.move.to_sgf() == "ce")
        assert "correct" in ce_node.comment
        assert "also correct" in ce_node.comment

    def test_primary_not_mutated(self):
        """Original primary tree should not be modified."""
        primary = parse_sgf(self.PRIMARY_SGF)
        original_count = len(primary.solution_tree.children)

        merge_solution_trees(
            primary.solution_tree,
            parse_sgf(self.SECONDARY_SGF).solution_tree,
            19,
            None,
        )

        assert len(primary.solution_tree.children) == original_count

    def test_secondary_not_mutated(self):
        """Original secondary tree should not be modified."""
        secondary = parse_sgf(self.SECONDARY_SGF)
        original_count = len(secondary.solution_tree.children)

        merge_solution_trees(
            parse_sgf(self.PRIMARY_SGF).solution_tree,
            secondary.solution_tree,
            19,
            None,
        )

        assert len(secondary.solution_tree.children) == original_count

    def test_with_d4_transform(self):
        """D4 transform: secondary's coordinates mapped to primary's space via inverse.

        find_transform returns T where T(source) = target. Merge uses inverse(T)
        to bring target coords into source space.
        """
        primary_sgf = "(;SZ[19]AB[cd]AW[dd]PL[B](;B[ce]C[primary]))"
        # Secondary is rotated 180: cd=(2,3)->(16,15)=qp, dd=(3,3)->(15,15)=pp, ce=(2,4)->(16,14)=qo
        secondary_sgf = "(;SZ[19]AB[qp]AW[pp]PL[B](;B[qo]C[secondary])(;B[po]C[new branch]))"

        primary = parse_sgf(primary_sgf)
        secondary = parse_sgf(secondary_sgf)
        # find_transform would return T where T(primary) = secondary, i.e. rot=180
        # merge_solution_trees internally applies inverse(T) = rot=180 (self-inverse)
        # to bring secondary coords back to primary space
        transform = PositionTransform(rotation=180, reflect=False)

        merged = merge_solution_trees(
            primary.solution_tree,
            secondary.solution_tree,
            19,
            transform,
        )

        # After inverse(180°) = 180° transform on secondary:
        # B[qo](16,14) -> B[ce](2,4), B[po](15,14) -> B[de](3,4)
        # B[ce] exists in primary, so comments merge
        # B[de] is new, grafted from secondary
        assert len(merged.children) == 2

        ce_node = next(c for c in merged.children if c.move and c.move.to_sgf() == "ce")
        assert "primary" in ce_node.comment
        assert "secondary" in ce_node.comment

    def test_correctness_union(self):
        """If secondary marks a move correct that primary marks wrong, use correct."""
        primary_sgf = "(;SZ[19]AB[cd]AW[dd]PL[B](;B[ce]BM[1]))"
        secondary_sgf = "(;SZ[19]AB[cd]AW[dd]PL[B](;B[ce]C[correct]))"

        primary = parse_sgf(primary_sgf)
        secondary = parse_sgf(secondary_sgf)

        merged = merge_solution_trees(
            primary.solution_tree,
            secondary.solution_tree,
            19,
            None,
        )

        ce_node = merged.children[0]
        assert ce_node.is_correct is True


# ---------------------------------------------------------------------------
# build_merged_sgf tests
# ---------------------------------------------------------------------------


class TestBuildMergedSgf:
    def test_round_trip(self):
        """Parse -> merge -> build -> re-parse produces valid SGF."""
        sgf = "(;SZ[19]AB[cd][ce]AW[dd][de]PL[B](;B[cf]C[correct])(;B[df]C[wrong]BM[1]))"
        tree = parse_sgf(sgf)

        # Merge with itself (should produce identical tree)
        merged = merge_solution_trees(
            tree.solution_tree,
            tree.solution_tree,
            19,
            None,
        )

        result_sgf = build_merged_sgf(tree, merged)

        # Re-parse should succeed
        result_tree = parse_sgf(result_sgf)
        assert result_tree.board_size == 19
        assert len(result_tree.black_stones) == 2
        assert len(result_tree.white_stones) == 2
        assert len(result_tree.solution_tree.children) == 2

    def test_merged_root_comment(self):
        """Merged root comment is applied to output SGF."""
        sgf = "(;SZ[19]AB[cd]AW[dd]PL[B]C[Original])"
        tree = parse_sgf(sgf)
        merged = merge_solution_trees(
            tree.solution_tree, tree.solution_tree, 19, None,
        )

        result_sgf = build_merged_sgf(tree, merged, "Merged from two sources")
        result_tree = parse_sgf(result_sgf)
        assert result_tree.root_comment == "Merged from two sources"

    def test_preserves_yengo_properties(self):
        """YenGo properties from primary tree are preserved."""
        sgf = "(;SZ[19]AB[cd]AW[dd]PL[B]YG[intermediate]YT[life-and-death](;B[ce]))"
        tree = parse_sgf(sgf)
        merged = merge_solution_trees(
            tree.solution_tree, tree.solution_tree, 19, None,
        )

        result_sgf = build_merged_sgf(tree, merged)
        result_tree = parse_sgf(result_sgf)
        assert result_tree.yengo_props.level_slug == "intermediate"
        assert "life-and-death" in result_tree.yengo_props.tags


# ---------------------------------------------------------------------------
# infer_correct_first_moves tests
# ---------------------------------------------------------------------------


class TestInferCorrectFirstMoves:
    """Test leaf-outcome correctness inference."""

    def test_single_correct_leaf(self):
        """One path ends with C[+], that first move is inferred correct."""
        sgf = "(;SZ[19]AB[cd]AW[dd]PL[B](;B[ce](;W[cf](;B[cg]C[+])))(;B[de](;W[df](;B[dg]C[wrong]))))"
        tree = parse_sgf(sgf)
        result = infer_correct_first_moves(tree.solution_tree)
        assert result == {("B", "ce")}

    def test_multiple_correct_leaves(self):
        """Two paths end with C[+], both first moves inferred correct."""
        sgf = "(;SZ[19]AB[cd]AW[dd]PL[B](;B[ce](;W[cf](;B[cg]C[correct])))(;B[de](;W[df](;B[dg]C[+]))))"
        tree = parse_sgf(sgf)
        result = infer_correct_first_moves(tree.solution_tree)
        assert result == {("B", "ce"), ("B", "de")}

    def test_no_correct_leaves(self):
        """No C[+] leaves — returns empty set."""
        sgf = "(;SZ[19]AB[cd]AW[dd]PL[B](;B[ce](;W[cf](;B[cg]C[a comment]))))"
        tree = parse_sgf(sgf)
        result = infer_correct_first_moves(tree.solution_tree)
        assert result == set()

    def test_deep_correct_leaf(self):
        """C[+] on a deeply nested leaf still traces back to first move."""
        sgf = "(;SZ[19]AB[cd]AW[dd]PL[B](;B[ce](;W[cf](;B[cg](;W[ch](;B[ci]C[+])))))))"
        tree = parse_sgf(sgf)
        result = infer_correct_first_moves(tree.solution_tree)
        assert result == {("B", "ce")}

    def test_mixed_branches_same_first_move(self):
        """One first move has both correct and wrong leaves — still inferred correct."""
        sgf = "(;SZ[19]AB[cd]AW[dd]PL[B](;B[ce](;W[cf](;B[cg]C[+]))(;W[df](;B[dg]C[wrong])))))"
        tree = parse_sgf(sgf)
        result = infer_correct_first_moves(tree.solution_tree)
        assert result == {("B", "ce")}

    def test_empty_tree(self):
        """No children at all — returns empty set."""
        sgf = "(;SZ[19]AB[cd]AW[dd]PL[B])"
        tree = parse_sgf(sgf)
        result = infer_correct_first_moves(tree.solution_tree)
        assert result == set()


# ---------------------------------------------------------------------------
# Level 3 rescue tests
# ---------------------------------------------------------------------------


class TestLevel3Rescue:
    """Test plan_merge Level 3 rescue via leaf-outcome inference."""

    def _make_tree(self, sgf: str):
        return parse_sgf(sgf)

    def test_rescue_when_convention_mismatch(self):
        """Level 3 skip is rescued when secondary has C[+] leaf convention."""
        # Primary: B[ce] correct, B[de] wrong
        primary_sgf = "(;SZ[19]AB[cd]AW[dd]PL[B](;B[ce]C[correct])(;B[de]C[wrong]BM[1]))"
        # Secondary: same position, all first moves is_correct=True (default),
        # but only B[ce] leads to C[+] leaf
        secondary_sgf = "(;SZ[19]AB[cd]AW[dd]PL[B](;B[ce](;W[cf](;B[cg]C[+])))(;B[de](;W[df](;B[dg]))))"

        pri_tree = self._make_tree(primary_sgf)
        sec_tree = self._make_tree(secondary_sgf)

        r = _make_compare_result(
            match_level=MatchLevel.SOLUTION_DIFFERS,
            source_nodes=2,
            target_nodes=6,
        )

        d = plan_merge(r, primary_tree=pri_tree, secondary_tree=sec_tree)
        assert d.action == "merge_trees_inferred"

    def test_no_rescue_when_genuine_disagreement(self):
        """Level 3 stays skipped when inferred correct moves don't match."""
        # Primary: B[ce] correct
        primary_sgf = "(;SZ[19]AB[cd]AW[dd]PL[B](;B[ce]C[correct])(;B[de]BM[1]))"
        # Secondary: only B[de] leads to C[+] (different correct move)
        secondary_sgf = "(;SZ[19]AB[cd]AW[dd]PL[B](;B[ce](;W[cf](;B[cg])))(;B[de](;W[df](;B[dg]C[+]))))"

        pri_tree = self._make_tree(primary_sgf)
        sec_tree = self._make_tree(secondary_sgf)

        r = _make_compare_result(
            match_level=MatchLevel.SOLUTION_DIFFERS,
            source_nodes=2,
            target_nodes=6,
        )

        d = plan_merge(r, primary_tree=pri_tree, secondary_tree=sec_tree)
        assert d.action == "skip"

    def test_no_rescue_when_no_correct_leaves(self):
        """Level 3 stays skipped when secondary has no C[+] leaves."""
        primary_sgf = "(;SZ[19]AB[cd]AW[dd]PL[B](;B[ce]C[correct]))"
        secondary_sgf = "(;SZ[19]AB[cd]AW[dd]PL[B](;B[ce](;W[cf](;B[cg]C[a move]))))"

        pri_tree = self._make_tree(primary_sgf)
        sec_tree = self._make_tree(secondary_sgf)

        r = _make_compare_result(
            match_level=MatchLevel.SOLUTION_DIFFERS,
            source_nodes=1,
            target_nodes=3,
        )

        d = plan_merge(r, primary_tree=pri_tree, secondary_tree=sec_tree)
        assert d.action == "skip"

    def test_no_rescue_without_trees(self):
        """Level 3 stays skipped when trees not provided (backward compat)."""
        r = _make_compare_result(match_level=MatchLevel.SOLUTION_DIFFERS)
        d = plan_merge(r)
        assert d.action == "skip"


# ---------------------------------------------------------------------------
# primary_correctness_wins tests
# ---------------------------------------------------------------------------


class TestPrimaryCorrectnessWins:
    """Test that primary_correctness_wins keeps primary's markers on shared moves."""

    def test_shared_move_keeps_primary_wrong(self):
        """Primary marks B[ce] as wrong — should stay wrong even if secondary says correct."""
        primary_sgf = "(;SZ[19]AB[cd]AW[dd]PL[B](;B[ce]BM[1]))"
        secondary_sgf = "(;SZ[19]AB[cd]AW[dd]PL[B](;B[ce]C[+]))"

        primary = parse_sgf(primary_sgf)
        secondary = parse_sgf(secondary_sgf)

        merged = merge_solution_trees(
            primary.solution_tree,
            secondary.solution_tree,
            19,
            None,
            primary_correctness_wins=True,
        )

        ce_node = merged.children[0]
        assert ce_node.is_correct is False  # Primary says wrong, should stay wrong

    def test_union_mode_promotes_to_correct(self):
        """Without primary_correctness_wins, union promotes to correct."""
        primary_sgf = "(;SZ[19]AB[cd]AW[dd]PL[B](;B[ce]BM[1]))"
        secondary_sgf = "(;SZ[19]AB[cd]AW[dd]PL[B](;B[ce]C[correct]))"

        primary = parse_sgf(primary_sgf)
        secondary = parse_sgf(secondary_sgf)

        merged = merge_solution_trees(
            primary.solution_tree,
            secondary.solution_tree,
            19,
            None,
            primary_correctness_wins=False,
        )

        ce_node = merged.children[0]
        assert ce_node.is_correct is True  # Union: secondary says correct → promote

    def test_grafted_branches_keep_secondary_markers(self):
        """New branches from secondary keep their own correctness flags."""
        primary_sgf = "(;SZ[19]AB[cd]AW[dd]PL[B](;B[ce]))"
        # Secondary has B[de] marked wrong (BM[1])
        secondary_sgf = "(;SZ[19]AB[cd]AW[dd]PL[B](;B[ce])(;B[de]BM[1]))"

        primary = parse_sgf(primary_sgf)
        secondary = parse_sgf(secondary_sgf)

        merged = merge_solution_trees(
            primary.solution_tree,
            secondary.solution_tree,
            19,
            None,
            primary_correctness_wins=True,
        )

        assert len(merged.children) == 2
        de_node = next(c for c in merged.children if c.move and c.move.to_sgf() == "de")
        assert de_node.is_correct is False  # Grafted from secondary, keeps its marker
