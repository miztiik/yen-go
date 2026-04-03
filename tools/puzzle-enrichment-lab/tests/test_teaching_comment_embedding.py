"""Integration tests for Phase 3: teaching comment embedding in SGF.

Tests that _embed_teaching_comments correctly writes C[] properties onto
solution tree nodes, and that enrich_sgf wires Phase 3.
"""

from __future__ import annotations

import pytest
from analyzers.sgf_enricher import (
    _append_node_comment,
    _embed_teaching_comments,
    _get_node_move_coord,
    _has_existing_refutation_branches,
    _is_terse_correctness_label,
    clear_enricher_cache,
    enrich_sgf,
)
from analyzers.validate_correct_move import ValidationStatus
from models.ai_analysis_result import AiAnalysisResult

from core.sgf_parser import SGF


@pytest.fixture(autouse=True)
def _clear_caches():
    clear_enricher_cache()
    yield


# ---------------------------------------------------------------------------
# Helper to parse and inspect SGF
# ---------------------------------------------------------------------------

def _get_comment(sgf_text: str, child_index: int) -> str:
    """Get C[] value from the nth child of root."""
    root = SGF.parse_sgf(sgf_text)
    node = root.children[child_index]
    return node.get_property("C", "")


# ---------------------------------------------------------------------------
# _embed_teaching_comments unit tests
# ---------------------------------------------------------------------------

class TestEmbedTeachingComments:
    """Test the _embed_teaching_comments function directly."""

    SGF_BASE = "(;FF[4]GM[1]SZ[19]AB[dd][de]AW[cd][ce](;B[cc])(;B[ef]))"

    def test_correct_comment_on_first_child(self):
        result = _embed_teaching_comments(
            self.SGF_BASE, "Snapback — recapture.", {}
        )
        comment = _get_comment(result, 0)
        assert "Snapback" in comment

    def test_wrong_comment_on_matching_branch(self):
        result = _embed_teaching_comments(
            self.SGF_BASE, "", {"ef": "Wrong. Strong response."}
        )
        comment = _get_comment(result, 1)
        assert "Wrong. Strong response." in comment

    def test_correct_and_wrong_together(self):
        result = _embed_teaching_comments(
            self.SGF_BASE,
            "Snapback — recapture.",
            {"ef": "Bad move."},
        )
        assert "Snapback" in _get_comment(result, 0)
        assert "Bad move." in _get_comment(result, 1)

    def test_noop_when_both_empty(self):
        result = _embed_teaching_comments(self.SGF_BASE, "", {})
        assert result == self.SGF_BASE

    def test_append_to_existing_comment(self):
        sgf = "(;FF[4]GM[1]SZ[19](;B[cc]C[Existing.]))"
        result = _embed_teaching_comments(sgf, "Teaching.", {})
        comment = _get_comment(result, 0)
        assert "Existing." in comment
        assert "Teaching." in comment
        assert "\n\n" in comment

    def test_wrong_comment_appends_to_existing(self):
        sgf = "(;FF[4]GM[1]SZ[19](;B[cc])(;B[ef]C[Wrong. Drops 50%.]))"
        result = _embed_teaching_comments(
            sgf, "", {"ef": "Captured immediately."}
        )
        comment = _get_comment(result, 1)
        assert "Wrong. Drops 50%." in comment
        assert "Captured immediately." in comment

    def test_no_children_noop(self):
        sgf = "(;FF[4]GM[1]SZ[19])"
        result = _embed_teaching_comments(sgf, "Comment.", {})
        # No children → return unchanged
        assert result == sgf

    def test_invalid_sgf_returns_original(self):
        bad_sgf = "not valid sgf"
        result = _embed_teaching_comments(bad_sgf, "Comment.", {})
        assert result == bad_sgf

    def test_unmatched_wrong_move_ignored(self):
        result = _embed_teaching_comments(
            self.SGF_BASE, "", {"zz": "No match."}
        )
        # No child has move "zz", so no comments added
        assert _get_comment(result, 0) == ""
        assert _get_comment(result, 1) == ""


# ---------------------------------------------------------------------------
# Helper function tests
# ---------------------------------------------------------------------------

class TestGetNodeMoveCoord:
    def test_black_move(self):
        root = SGF.parse_sgf("(;FF[4]GM[1]SZ[19](;B[cd]))")
        coord = _get_node_move_coord(root.children[0])
        assert coord == "cd"

    def test_white_move(self):
        root = SGF.parse_sgf("(;FF[4]GM[1]SZ[19](;W[qr]))")
        coord = _get_node_move_coord(root.children[0])
        assert coord == "qr"

    def test_no_move(self):
        root = SGF.parse_sgf("(;FF[4]GM[1]SZ[19])")
        coord = _get_node_move_coord(root)
        assert coord is None


class TestAppendNodeComment:
    def test_new_comment(self):
        root = SGF.parse_sgf("(;FF[4]GM[1]SZ[19](;B[cd]))")
        node = root.children[0]
        _append_node_comment(node, "Hello.")
        assert node.get_property("C", "") == "Hello."

    def test_append_existing(self):
        root = SGF.parse_sgf("(;FF[4]GM[1]SZ[19](;B[cd]C[First.]))")
        node = root.children[0]
        _append_node_comment(node, "Second.")
        result = node.get_property("C", "")
        assert result == "First.\n\nSecond."


# ---------------------------------------------------------------------------
# _is_terse_correctness_label — canonical correctness marker detection
# ---------------------------------------------------------------------------

class TestIsTerseCorrectnessLabel:
    """Tests for _is_terse_correctness_label using canonical sgf_correctness.

    Terse labels are correctness markers with no pedagogical text beyond the
    marker itself. They are safe to replace with richer teaching comments.
    Uses the canonical infer_correctness_from_comment() from
    tools/core/sgf_correctness.py which recognises markers found across
    80,000+ SGF files from 9 sources.
    """

    @pytest.mark.parametrize("comment", [
        "Wrong",
        "Wrong.",
        "Wrong!",
        "wrong",
        "WRONG",
        "Incorrect",
        "Incorrect.",
        "incorrect",
        "Correct",
        "Correct!",
        "correct.",
        "Right",
        "right",
        "+",
        "-",
    ])
    def test_terse_markers_detected(self, comment):
        assert _is_terse_correctness_label(comment) is True

    @pytest.mark.parametrize("comment", [
        "Wrong — this loses the corner",
        "Incorrect, the opponent can capture",
        "Wrong. Drops 50%.",
        "Correct. Snapback recapture.",
        "Right choice — captures the group",
        "This move fails",
        "Good move",
        "",
        "A random comment",
        "The opponent captures",
    ])
    def test_substantive_or_non_marker_not_detected(self, comment):
        assert _is_terse_correctness_label(comment) is False


# ---------------------------------------------------------------------------
# _has_existing_refutation_branches — canonical marker detection
# ---------------------------------------------------------------------------

class TestHasExistingRefutationBranches:
    """Tests for _has_existing_refutation_branches using canonical correctness.

    Ensures detection works for all established conventions: WV/BM markers,
    wrong/incorrect prefixes, and the minimalist '-' marker.
    """

    def test_detects_wrong_comment_prefix(self):
        root = SGF.parse_sgf("(;FF[4]GM[1]SZ[19](;B[cc])(;B[ef]C[Wrong]))")
        assert _has_existing_refutation_branches(root) is True

    def test_detects_incorrect_comment_prefix(self):
        root = SGF.parse_sgf("(;FF[4]GM[1]SZ[19](;B[cc])(;B[ef]C[Incorrect]))")
        assert _has_existing_refutation_branches(root) is True

    def test_detects_minus_marker(self):
        root = SGF.parse_sgf("(;FF[4]GM[1]SZ[19](;B[cc])(;B[ef]C[-]))")
        assert _has_existing_refutation_branches(root) is True

    def test_detects_bm_property(self):
        root = SGF.parse_sgf("(;FF[4]GM[1]SZ[19](;B[cc])(;B[ef]BM[1]))")
        assert _has_existing_refutation_branches(root) is True

    def test_no_markers_returns_false(self):
        root = SGF.parse_sgf("(;FF[4]GM[1]SZ[19](;B[cc])(;B[ef]))")
        assert _has_existing_refutation_branches(root) is False

    def test_correct_marker_not_detected_as_wrong(self):
        root = SGF.parse_sgf("(;FF[4]GM[1]SZ[19](;B[cc]C[Correct])(;B[ef]))")
        assert _has_existing_refutation_branches(root) is False


# ---------------------------------------------------------------------------
# Terse label replacement in _embed_teaching_comments
# ---------------------------------------------------------------------------

class TestTerseLabelReplacement:
    """Tests for smart replace vs append logic in _embed_teaching_comments.

    When a node has a terse correctness label (e.g. 'Wrong', 'Incorrect.',
    '-'), the teaching comment REPLACES it because terse labels carry no
    pedagogical value. Substantive comments are preserved via append.
    """

    def test_terse_wrong_replaced_with_teaching_comment(self):
        """C[Wrong] + teaching → C[Wrong. {teaching}] (replaced, not appended)."""
        sgf = "(;FF[4]GM[1]SZ[19](;B[cc])(;B[ef]C[Wrong]))"
        result = _embed_teaching_comments(sgf, "", {"ef": "Strong response."})
        comment = _get_comment(result, 1)
        assert comment == "Wrong. Strong response."
        assert "\n\n" not in comment  # replaced, not appended

    def test_terse_incorrect_replaced(self):
        """C[Incorrect.] + teaching → C[Wrong. {teaching}] (replaced)."""
        sgf = "(;FF[4]GM[1]SZ[19](;B[cc])(;B[ef]C[Incorrect.]))"
        result = _embed_teaching_comments(sgf, "", {"ef": "Captured immediately."})
        comment = _get_comment(result, 1)
        assert "Captured immediately." in comment
        assert "\n\n" not in comment

    def test_terse_minus_marker_replaced(self):
        """C[-] + teaching → C[Wrong. {teaching}] (replaced)."""
        sgf = "(;FF[4]GM[1]SZ[19](;B[cc])(;B[ef]C[-]))"
        result = _embed_teaching_comments(sgf, "", {"ef": "Bad shape."})
        comment = _get_comment(result, 1)
        assert "Bad shape." in comment
        assert "-" not in comment

    def test_substantive_comment_preserved_via_append(self):
        """C[Wrong. Drops 50%.] + teaching → append (substantive preserved)."""
        sgf = "(;FF[4]GM[1]SZ[19](;B[cc])(;B[ef]C[Wrong. Drops 50%.]))"
        result = _embed_teaching_comments(
            sgf, "", {"ef": "Captured immediately."}
        )
        comment = _get_comment(result, 1)
        assert "Wrong. Drops 50%." in comment
        assert "Captured immediately." in comment

    def test_almost_correct_replaces_terse_wrong(self):
        """C[Wrong] + 'Good move...' → C[Good move...] (replaced)."""
        sgf = "(;FF[4]GM[1]SZ[19](;B[cc])(;B[ef]C[Wrong]))"
        result = _embed_teaching_comments(
            sgf, "", {"ef": "Good move, but there's a slightly better option."}
        )
        comment = _get_comment(result, 1)
        assert "Good move" in comment
        assert "\n\n" not in comment

    def test_no_existing_comment_sets_directly(self):
        """No C[] + teaching → C[Wrong. {teaching}] (set directly)."""
        sgf = "(;FF[4]GM[1]SZ[19](;B[cc])(;B[ef]))"
        result = _embed_teaching_comments(sgf, "", {"ef": "Strong response."})
        comment = _get_comment(result, 1)
        assert comment == "Wrong. Strong response."


# ---------------------------------------------------------------------------
# enrich_sgf integration: Phase 3 wiring
# ---------------------------------------------------------------------------

class TestEnrichSgfPhase3:
    """Test that enrich_sgf wires teaching_comments into Phase 3."""

    SGF = "(;FF[4]GM[1]SZ[19]PL[B]AB[dd][de]AW[cd][ce](;B[cc])(;B[ef]))"

    def _make_result(self, teaching_comments: dict) -> AiAnalysisResult:
        return AiAnalysisResult(
            puzzle_id="test-001",
            teaching_comments=teaching_comments,
        )

    def test_teaching_comments_embedded(self):
        result = self._make_result({
            "correct_comment": "Snapback — recapture.",
            "wrong_comments": {"ef": "Bad move."},
            "summary": "Snapback problem.",
        })
        enriched = enrich_sgf(self.SGF, result)
        assert "Snapback" in _get_comment(enriched, 0)
        assert "Bad move." in _get_comment(enriched, 1)

    def test_empty_teaching_comments_noop(self):
        result = self._make_result({})
        enriched = enrich_sgf(self.SGF, result)
        assert _get_comment(enriched, 0) == ""

    def test_suppressed_correct_comment(self):
        """Confidence gate upstream → empty correct_comment, still embeds wrong."""
        result = self._make_result({
            "correct_comment": "",
            "wrong_comments": {"ef": "Wrong response."},
            "summary": "Problem.",
        })
        enriched = enrich_sgf(self.SGF, result)
        assert _get_comment(enriched, 0) == ""
        assert "Wrong response." in _get_comment(enriched, 1)

    def test_rejected_skips_all_phases(self):
        result = self._make_result({
            "correct_comment": "Should not appear.",
            "wrong_comments": {},
        })
        result.validation.status = ValidationStatus.REJECTED
        enriched = enrich_sgf(self.SGF, result)
        # REJECTED → return original unchanged
        assert "Should not appear" not in enriched
