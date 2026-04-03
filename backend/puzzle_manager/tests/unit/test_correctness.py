"""
Unit tests for move correctness inference (three-layer fallback).

Tests core/correctness.py: infer_correctness, infer_correctness_from_comment,
and count_structural_refutations.
"""


from backend.puzzle_manager.core.correctness import (
    _has_correctness_signal,
    count_structural_refutations,
    infer_correctness,
    infer_correctness_from_comment,
    mark_sibling_refutations,
)
from backend.puzzle_manager.core.sgf_parser import SolutionNode


class TestInferCorrectness:
    """Tests for infer_correctness (Layers 1 & 2 combined)."""

    # --- Layer 1: SGF markers ---

    def test_bm_marker_wrong(self):
        """BM (Bad Move) marker → wrong."""
        assert infer_correctness(None, {"BM": "1"}) is False

    def test_tr_marker_wrong(self):
        """TR (Triangle) marker → wrong."""
        assert infer_correctness(None, {"TR": ""}) is False

    def test_te_marker_correct(self):
        """TE (Tesuji) marker → correct."""
        assert infer_correctness(None, {"TE": "1"}) is True

    def test_it_marker_correct(self):
        """IT (Interesting) marker → correct."""
        assert infer_correctness(None, {"IT": ""}) is True

    def test_te_overrides_bm(self):
        """When both TE and BM present, correct wins."""
        assert infer_correctness(None, {"BM": "1", "TE": "1"}) is True

    def test_marker_overrides_comment(self):
        """SGF marker takes priority over comment text."""
        assert infer_correctness("Correct!", {"BM": "1"}) is False
        assert infer_correctness("Wrong", {"TE": "1"}) is True

    # --- Layer 2: Comment text ---

    def test_wrong_comment(self):
        """Comment starting with 'Wrong' → wrong."""
        assert infer_correctness("Wrong", {}) is False

    def test_wrong_with_explanation(self):
        """'Wrong' prefix with trailing text → wrong."""
        assert infer_correctness("Wrong This move fails.", {}) is False

    def test_wrong_with_period(self):
        """'Wrong.' → wrong."""
        assert infer_correctness("Wrong.", {}) is False

    def test_wrong_with_semicolon(self):
        """'Wrong; ko' pattern (kisvadim) → wrong."""
        assert infer_correctness("Wrong; disadvantageous ko.", {}) is False

    def test_incorrect_comment(self):
        """Comment starting with 'Incorrect' → wrong."""
        assert infer_correctness("Incorrect", {}) is False

    def test_correct_comment(self):
        """Comment starting with 'Correct' → correct."""
        assert infer_correctness("Correct!", {}) is True

    def test_correct_with_period(self):
        """'Correct.' (gotools) → correct."""
        assert infer_correctness("Correct.", {}) is True

    def test_correct_with_explanation(self):
        """'Correct! Good job...' → correct."""
        assert infer_correctness("Correct! Good you stopped white.", {}) is True

    def test_right_comment(self):
        """'RIGHT' (goproblems) → correct."""
        assert infer_correctness("RIGHT", {}) is True

    def test_right_with_explanation(self):
        """'RIGHT\\n\\nblack plays under' → correct."""
        assert infer_correctness("RIGHT\n\nblack plays under", {}) is True

    def test_plus_exact_correct(self):
        """'+' exact match (ambak-tsumego, t-hero) → correct."""
        assert infer_correctness("+", {}) is True

    def test_plus_with_text_not_matched(self):
        """'+1 is an aggressive bump' is NOT just '+', → None."""
        assert infer_correctness("+1 is an aggressive bump", {}) is None

    # --- No signal ---

    def test_no_comment_no_markers(self):
        """No comment, no markers → None."""
        assert infer_correctness(None, {}) is None

    def test_ambiguous_comment(self):
        """Ambiguous text → None (not matched)."""
        assert infer_correctness("Now white got two eyes.", {}) is None

    def test_pedagogical_comment(self):
        """Teaching explanation → None."""
        assert infer_correctness("Black to play: Elementary", {}) is None

    def test_empty_comment(self):
        """Empty/whitespace → None."""
        assert infer_correctness("", {}) is None
        assert infer_correctness("   ", {}) is None

    # --- Case insensitivity ---

    def test_case_insensitive_wrong(self):
        """Wrong matching is case-insensitive."""
        assert infer_correctness("WRONG", {}) is False
        assert infer_correctness("wrong", {}) is False
        assert infer_correctness("Wrong", {}) is False

    def test_case_insensitive_correct(self):
        """Correct matching is case-insensitive."""
        assert infer_correctness("CORRECT!", {}) is True
        assert infer_correctness("correct!", {}) is True

    # --- Non-English text ---

    def test_chinese_not_matched_by_layer2(self):
        """Chinese text not matched (Layer 2 is conservative)."""
        assert infer_correctness("连环劫，失败", {}) is None

    def test_wrong_with_html(self):
        """'Wrong <h1>Incorrect</h1>' → wrong (starts with 'wrong')."""
        assert infer_correctness("Wrong <h1>Incorrect</h1>\nWhite lives.", {}) is False


class TestInferCorrectnessFromComment:
    """Tests for infer_correctness_from_comment (Layer 2 only)."""

    def test_none_for_empty(self):
        assert infer_correctness_from_comment("") is None

    def test_wrong_prefix(self):
        assert infer_correctness_from_comment("Wrong") is False

    def test_correct_prefix(self):
        assert infer_correctness_from_comment("Correct!") is True

    def test_plus_exact(self):
        assert infer_correctness_from_comment("+") is True

    def test_unknown_text(self):
        assert infer_correctness_from_comment("Ko threat") is None


class TestCountStructuralRefutations:
    """Tests for count_structural_refutations (Layer 3)."""

    def test_no_children(self):
        """0 children → 0 refutations."""
        assert count_structural_refutations(0, 0) == 0

    def test_single_child(self):
        """1 child (assumed correct) → 0 refutations."""
        assert count_structural_refutations(1, 0) == 0

    def test_five_children_no_info(self):
        """5 children, no correctness info → 4 refutations (assume 1 correct)."""
        assert count_structural_refutations(5, 0) == 4

    def test_three_children_one_known_correct(self):
        """3 children, 1 known correct → 2 refutations."""
        assert count_structural_refutations(3, 1) == 2

    def test_miai_two_known_correct(self):
        """3 children, 2 known correct → 1 refutation."""
        assert count_structural_refutations(3, 2) == 1

    def test_all_correct(self):
        """3 children, all known correct → 0 refutations."""
        assert count_structural_refutations(3, 3) == 0


class TestParserIntegration:
    """Integration tests: parse SGF and verify is_correct is set correctly."""

    def test_comment_wrong_sets_is_correct_false(self):
        """Parser should set is_correct=False for C[Wrong] nodes."""
        from backend.puzzle_manager.core.sgf_parser import parse_sgf

        sgf = (
            "(;SZ[9]FF[4]GM[1]PL[B]"
            "AB[eb][fb]AW[db][da]"
            "(;B[ba]C[Correct!])"
            "(;B[ea]C[Wrong])"
            "(;B[ac]C[Wrong])"
            ")"
        )
        game = parse_sgf(sgf)

        assert len(game.solution_tree.children) == 3
        assert game.solution_tree.children[0].is_correct is True   # Correct!
        assert game.solution_tree.children[1].is_correct is False  # Wrong
        assert game.solution_tree.children[2].is_correct is False  # Wrong

    def test_bm_marker_still_works(self):
        """BM marker continues to work as before."""
        from backend.puzzle_manager.core.sgf_parser import parse_sgf

        sgf = (
            "(;SZ[9]FF[4]GM[1]PL[B]"
            "AB[eb]AW[db]"
            "(;B[ba]TE[1]C[Correct!])"
            "(;B[ea]BM[1]C[Wrong])"
            ")"
        )
        game = parse_sgf(sgf)

        assert game.solution_tree.children[0].is_correct is True   # TE marker
        assert game.solution_tree.children[1].is_correct is False  # BM marker

    def test_rc_count_with_comment_based_wrong(self):
        """count_refutation_moves should now find C[Wrong]-based refutations."""
        from backend.puzzle_manager.core.quality import count_refutation_moves
        from backend.puzzle_manager.core.sgf_parser import parse_sgf

        sgf = (
            "(;SZ[9]FF[4]GM[1]PL[B]"
            "AB[eb][fb][dc][cc][bc][be]AW[db][da][cb][ab][bb]"
            "(;B[ba]C[Correct! Good move.])"
            "(;B[ea]C[Wrong];W[ba]C[Now white got two eyes.])"
            "(;B[ac]C[Wrong];W[ba]C[Now white got two eyes.])"
            "(;B[ca]C[Wrong];W[ba]C[Now white got two eyes.])"
            "(;B[aa]C[Wrong];W[ba]C[Now white got two eyes.])"
            ")"
        )
        game = parse_sgf(sgf)
        rc = count_refutation_moves(game.solution_tree)
        assert rc == 4  # Previously was 0!

    def test_quality_metrics_reflect_refutations(self):
        """compute_quality_metrics should now produce correct rc value."""
        from backend.puzzle_manager.core.quality import compute_quality_metrics
        from backend.puzzle_manager.core.sgf_parser import parse_sgf

        sgf = (
            "(;SZ[9]FF[4]GM[1]PL[B]"
            "AB[eb][fb]AW[db][da]"
            "(;B[ba]C[Correct!])"
            "(;B[ea]C[Wrong])"
            "(;B[ac]C[Wrong])"
            "(;B[ca]C[Wrong])"
            ")"
        )
        game = parse_sgf(sgf)
        yq = compute_quality_metrics(game)

        # Should have rc:3 (3 wrong moves)
        assert "rc:3" in yq
        # Should have hc:1 (correctness markers only — no teaching text)
        assert "hc:1" in yq
        # Quality level 3 (has refutations + comments but ac=0 → doesn't meet
        # min_ac thresholds for levels 4/5)
        assert "q:3" in yq

    def test_layer3_fallback_no_comments(self):
        """Layer 3 structural fallback when no markers and no comments."""
        from backend.puzzle_manager.core.quality import count_refutation_moves
        from backend.puzzle_manager.core.sgf_parser import parse_sgf

        # Puzzle with 3 variations but NO comments and NO markers
        sgf = (
            "(;SZ[9]FF[4]GM[1]PL[B]"
            "AB[eb]AW[db]"
            "(;B[ba])"
            "(;B[ea])"
            "(;B[ac])"
            ")"
        )
        game = parse_sgf(sgf)

        # All children have is_correct=True (default), no signal
        # Layer 3 kicks in: 3 children - 1 = 2 estimated refutations
        rc = count_refutation_moves(game.solution_tree)
        assert rc == 2


# ============================================================================
# T5: Tests for _has_correctness_signal()
# ============================================================================


class TestHasCorrectnessSignal:
    """Tests for _has_correctness_signal() helper."""

    def _node(self, **kwargs) -> SolutionNode:
        return SolutionNode(**kwargs)

    def test_bm_marker(self):
        """BM marker → has signal."""
        node = self._node(properties={"BM": "1"})
        assert _has_correctness_signal(node) is True

    def test_te_marker(self):
        """TE marker → has signal."""
        node = self._node(properties={"TE": "1"})
        assert _has_correctness_signal(node) is True

    def test_it_marker(self):
        """IT marker → has signal."""
        node = self._node(properties={"IT": ""})
        assert _has_correctness_signal(node) is True

    def test_tr_marker(self):
        """TR marker → has signal."""
        node = self._node(properties={"TR": ""})
        assert _has_correctness_signal(node) is True

    def test_correct_comment(self):
        """Comment starting with 'Correct' → has signal."""
        node = self._node(comment="Correct! Good move.")
        assert _has_correctness_signal(node) is True

    def test_wrong_comment(self):
        """Comment starting with 'Wrong' → has signal."""
        node = self._node(comment="Wrong")
        assert _has_correctness_signal(node) is True

    def test_right_comment(self):
        """'RIGHT' comment → has signal."""
        node = self._node(comment="RIGHT")
        assert _has_correctness_signal(node) is True

    def test_no_signal(self):
        """No markers, no correctness comment → no signal."""
        node = self._node()
        assert _has_correctness_signal(node) is False

    def test_ambiguous_comment_no_signal(self):
        """Pedagogical comment without signal prefix → no signal."""
        node = self._node(comment="Black plays for territory.")
        assert _has_correctness_signal(node) is False

    def test_empty_comment_no_signal(self):
        """Empty comment → no signal."""
        node = self._node(comment="")
        assert _has_correctness_signal(node) is False


# ============================================================================
# T6: Tests for mark_sibling_refutations() — core cases
# ============================================================================


class TestMarkSiblingRefutations:
    """Tests for mark_sibling_refutations() core cases."""

    def _node(self, move=None, is_correct=True, comment="",
              children=None, properties=None) -> SolutionNode:
        from backend.puzzle_manager.core.primitives import Point
        pt = Point(0, 0) if move else None
        return SolutionNode(
            move=pt,
            is_correct=is_correct,
            comment=comment,
            children=children or [],
            properties=properties or {},
        )

    def test_puzzle_14_net_topology(self):
        """3 unmarked wrong siblings of 1 correct leaf → all 3 marked wrong."""
        # B[mf]C[RIGHT] — the correct leaf
        correct = self._node(move=True, is_correct=True, comment="RIGHT")
        # B[me] — unmarked wrong (no comment)
        wrong1 = self._node(move=True, is_correct=True, comment="")
        # B[nf] — unmarked wrong (no comment)
        wrong2 = self._node(move=True, is_correct=True, comment="")
        # Parent: W[rf] node with 3 children
        parent = self._node(children=[correct, wrong1, wrong2])
        # Root
        root = self._node(children=[parent])

        count = mark_sibling_refutations(root)

        assert count == 2
        assert correct.is_correct is True
        assert wrong1.is_correct is False
        assert wrong2.is_correct is False

    def test_single_child_no_change(self):
        """Single child (no siblings) → no change."""
        child = self._node(move=True, is_correct=True, comment="RIGHT")
        root = self._node(children=[child])

        count = mark_sibling_refutations(root)
        assert count == 0
        assert child.is_correct is True

    def test_all_children_already_marked(self):
        """All children already have signals → no change."""
        c1 = self._node(move=True, is_correct=True, comment="Correct!")
        c2 = self._node(move=True, is_correct=False, comment="Wrong")
        root = self._node(children=[c1, c2])

        count = mark_sibling_refutations(root)
        assert count == 0

    def test_empty_tree(self):
        """Root with no children → returns 0."""
        root = self._node()
        assert mark_sibling_refutations(root) == 0

    def test_no_markers_at_all(self):
        """All children unmarked (no signal anywhere) → no change."""
        c1 = self._node(move=True, is_correct=True, comment="")
        c2 = self._node(move=True, is_correct=True, comment="")
        root = self._node(children=[c1, c2])

        count = mark_sibling_refutations(root)
        assert count == 0
        assert c1.is_correct is True
        assert c2.is_correct is True

    def test_opponent_only_nodes_not_marked(self):
        """Nodes without a move (setup/pass) are not marked even if unmarked."""
        correct = self._node(move=True, is_correct=True, comment="RIGHT")
        setup_node = self._node(move=None, is_correct=True, comment="")
        root = self._node(children=[correct, setup_node])

        count = mark_sibling_refutations(root)
        # setup_node has move=None, so it should NOT be marked
        assert count == 0
        assert setup_node.is_correct is True

    def test_recursive_deep_marking(self):
        """Heuristic works at deeper levels, not just first children."""
        # Depth 2: B[og] → W[rf] → { B[mf]C[RIGHT], B[me](unmarked) }
        right_leaf = self._node(move=True, is_correct=True, comment="RIGHT")
        wrong_leaf = self._node(move=True, is_correct=True, comment="")
        w_rf = self._node(children=[right_leaf, wrong_leaf])
        b_og = self._node(move=True, children=[w_rf])
        root = self._node(children=[b_og])

        count = mark_sibling_refutations(root)
        assert count == 1
        assert wrong_leaf.is_correct is False
        assert right_leaf.is_correct is True


# ============================================================================
# T7: Miai edge case test
# ============================================================================


class TestMarkSiblingRefutationsMiai:
    """Tests for miai guard: 2+ correct siblings → leave unmarked alone."""

    def _node(self, move=None, is_correct=True, comment="",
              children=None, properties=None) -> SolutionNode:
        from backend.puzzle_manager.core.primitives import Point
        pt = Point(0, 0) if move else None
        return SolutionNode(
            move=pt,
            is_correct=is_correct,
            comment=comment,
            children=children or [],
            properties=properties or {},
        )

    def test_two_correct_siblings_leaves_unmarked(self):
        """2 correct siblings + 1 unmarked → unmarked is NOT marked wrong."""
        c1 = self._node(move=True, is_correct=True, comment="Correct!")
        c2 = self._node(move=True, is_correct=True, comment="RIGHT")
        c3 = self._node(move=True, is_correct=True, comment="")  # unmarked
        root = self._node(children=[c1, c2, c3])

        count = mark_sibling_refutations(root)
        assert count == 0
        assert c3.is_correct is True  # left unchanged

    def test_three_correct_siblings(self):
        """3 correct siblings, no unmarked → no change, no crash."""
        c1 = self._node(move=True, is_correct=True, comment="Correct!")
        c2 = self._node(move=True, is_correct=True, comment="RIGHT")
        c3 = self._node(move=True, is_correct=True, properties={"TE": "1"})
        root = self._node(children=[c1, c2, c3])

        count = mark_sibling_refutations(root)
        assert count == 0


# ============================================================================
# T8: Integration test — metrics improvement after marking
# ============================================================================


class TestSiblingRefutationMetrics:
    """Verify downstream metrics improve after mark_sibling_refutations."""

    def test_refutation_count_increases(self):
        """count_refutation_moves returns higher count after marking."""
        from backend.puzzle_manager.core.quality import count_refutation_moves

        # Build SGF with 1 correct + 2 unmarked siblings (no comments)
        sgf = (
            "(;SZ[9]FF[4]GM[1]PL[B]"
            "AB[eb][fb]AW[db][da]"
            "(;B[ba]C[Correct!])"
            "(;B[ea])"
            "(;B[ac])"
            ")"
        )
        from backend.puzzle_manager.core.sgf_parser import parse_sgf
        game = parse_sgf(sgf)

        # Before marking: only Layer 3 heuristic can estimate refutations
        # (no explicit wrong markers → Layer 3 guesses children-1)
        # After marking: both ea and ac should be is_correct=False
        marked = mark_sibling_refutations(game.solution_tree)
        assert marked == 2

        rc = count_refutation_moves(game.solution_tree)
        assert rc == 2  # Now accurately counted via is_correct=False

    def test_parsed_sgf_with_right_marker(self):
        """Real parse: siblings of C[RIGHT] get marked and metrics work."""
        from backend.puzzle_manager.core.quality import count_refutation_moves

        sgf = (
            "(;SZ[9]FF[4]GM[1]PL[B]"
            "AB[eb][fb]AW[db][da]"
            "(;B[ba]C[RIGHT])"
            "(;B[ea])"
            "(;B[ac])"
            "(;B[ca])"
            ")"
        )
        from backend.puzzle_manager.core.sgf_parser import parse_sgf
        game = parse_sgf(sgf)

        marked = mark_sibling_refutations(game.solution_tree)
        assert marked == 3

        rc = count_refutation_moves(game.solution_tree)
        assert rc == 3
