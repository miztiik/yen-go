"""Tests for teaching_comments module V2 (config-driven, T-10)."""

from __future__ import annotations

import pytest
from analyzers.teaching_comments import generate_teaching_comments
from config import clear_cache


@pytest.fixture(autouse=True)
def _clear_cfg():
    clear_cache()
    yield
    clear_cache()


# ---- Fixture helpers ----


def _make_analysis(
    *,
    correct_move_gtp: str = "C3",
    correct_move_policy: float = 0.3,
    correct_move_winrate: float = 0.95,
    suggested_level: str = "intermediate",
    refutations: list[dict] | None = None,
) -> dict:
    """Build a minimal AiAnalysisResult dict."""
    return {
        "validation": {
            "correct_move_gtp": correct_move_gtp,
            "correct_move_policy": correct_move_policy,
            "correct_move_winrate": correct_move_winrate,
            "status": "accepted",
        },
        "refutations": refutations or [],
        "difficulty": {
            "suggested_level": suggested_level,
        },
    }


# ---- generate_teaching_comments (config-driven) ----


class TestGenerateTeachingComments:
    """Test the main generate_teaching_comments function."""

    def test_returns_correct_structure(self):
        analysis = _make_analysis()
        result = generate_teaching_comments(analysis, ["life-and-death"])
        assert "correct_comment" in result
        assert "wrong_comments" in result
        assert "summary" in result
        assert isinstance(result["correct_comment"], str)
        assert isinstance(result["wrong_comments"], dict)
        assert isinstance(result["summary"], str)

    def test_correct_comment_uses_primary_tag(self):
        analysis = _make_analysis()
        result = generate_teaching_comments(analysis, ["ko", "life-and-death"])
        assert "ko" in result["correct_comment"].lower()

    def test_correct_comment_uses_snapback_template(self):
        analysis = _make_analysis()
        result = generate_teaching_comments(analysis, ["snapback"])
        assert "snapback" in result["correct_comment"].lower()

    def test_correct_comment_uses_ladder_template(self):
        analysis = _make_analysis()
        result = generate_teaching_comments(analysis, ["ladder"])
        assert "ladder" in result["correct_comment"].lower()

    def test_correct_comment_includes_japanese_term(self):
        analysis = _make_analysis()
        result = generate_teaching_comments(analysis, ["snapback"])
        assert "uttegaeshi" in result["correct_comment"].lower()

    def test_low_policy_adds_non_obvious_note(self):
        analysis = _make_analysis(correct_move_policy=0.02)
        result = generate_teaching_comments(analysis, ["life-and-death"])
        assert "surprising move" in result["correct_comment"].lower()

    def test_normal_policy_no_extra_note(self):
        analysis = _make_analysis(correct_move_policy=0.3)
        result = generate_teaching_comments(analysis, ["life-and-death"])
        assert "surprising move" not in result["correct_comment"].lower()

    def test_wrong_comments_generated_for_refutations(self):
        analysis = _make_analysis(
            refutations=[
                {
                    "wrong_move": "D4",
                    "delta": 0.6,
                    "refutation_depth": 3,
                    "refutation_type": "unclassified",
                },
                {
                    "wrong_move": "E5",
                    "delta": 0.3,
                    "refutation_depth": 1,
                    "refutation_type": "unclassified",
                    "pv_truncated": False,
                },
            ]
        )
        result = generate_teaching_comments(analysis, ["life-and-death"])
        wrong = result["wrong_comments"]
        assert "D4" in wrong
        assert "E5" in wrong

    def test_wrong_comment_large_delta_includes_percentage(self):
        analysis = _make_analysis(
            refutations=[
                {
                    "wrong_move": "D4",
                    "delta": 0.6,
                    "refutation_depth": 3,
                    "refutation_type": "unclassified",
                },
            ]
        )
        result = generate_teaching_comments(analysis, ["life-and-death"])
        assert "60%" in result["wrong_comments"]["D4"]

    def test_wrong_comment_moderate_delta(self):
        analysis = _make_analysis(
            refutations=[
                {
                    "wrong_move": "D4",
                    "delta": 0.25,
                    "refutation_depth": 3,
                    "refutation_type": "unclassified",
                },
            ]
        )
        result = generate_teaching_comments(analysis, ["life-and-death"])
        assert "disadvantage" in result["wrong_comments"]["D4"].lower()

    def test_wrong_comment_ko_refutation(self):
        analysis = _make_analysis(
            refutations=[
                {
                    "wrong_move": "D4",
                    "delta": 0.05,
                    "refutation_depth": 5,
                    "refutation_type": "ko",
                },
            ]
        )
        result = generate_teaching_comments(analysis, ["life-and-death"])
        assert "ko" in result["wrong_comments"]["D4"].lower()

    def test_wrong_comment_shallow_verified_uses_capture_template(self):
        """Depth ≤ 1 + pv_truncated=False + capture_verified=True → capture template (V2)."""
        analysis = _make_analysis(
            refutations=[
                {
                    "wrong_move": "D4",
                    "delta": 0.6,
                    "refutation_depth": 1,
                    "refutation_type": "unclassified",
                    "pv_truncated": False,
                    "capture_verified": True,
                    "refutation_pv": ["dd"],
                },
            ]
        )
        result = generate_teaching_comments(analysis, ["life-and-death"])
        assert "captured" in result["wrong_comments"]["D4"].lower()

    def test_pv_truncated_falls_back_to_default(self):
        """T-09: When PV is truncated, do NOT claim 'captured immediately'.

        Falls back to the default wrong-move template ("Opponent has a
        strong response.") instead of condition-specific text.
        """
        analysis = _make_analysis(
            refutations=[
                {
                    "wrong_move": "D4",
                    "delta": 0.6,
                    "refutation_depth": 1,
                    "refutation_type": "unclassified",
                    "pv_truncated": True,
                },
            ]
        )
        result = generate_teaching_comments(analysis, ["life-and-death"])
        assert "captured" not in result["wrong_comments"]["D4"].lower()
        assert "opponent" in result["wrong_comments"]["D4"].lower()

    def test_summary_includes_level(self):
        analysis = _make_analysis(suggested_level="elementary")
        result = generate_teaching_comments(analysis, ["life-and-death"])
        assert "elementary" in result["summary"].lower()

    def test_summary_includes_tag_name(self):
        analysis = _make_analysis()
        result = generate_teaching_comments(analysis, ["capture-race"])
        assert "capture" in result["summary"].lower()

    def test_empty_technique_tags_suppressed(self):
        analysis = _make_analysis()
        result = generate_teaching_comments(analysis, [])
        assert result["correct_comment"] == ""
        assert result["hc_level"] == 0

    def test_no_refutations_produces_empty_wrong_comments(self):
        analysis = _make_analysis(refutations=[])
        result = generate_teaching_comments(analysis, ["life-and-death"])
        assert result["wrong_comments"] == {}


class TestAliasAwareLookup:
    """Test alias-resolution in correct_comment lookup."""

    def test_alias_bent_four_gets_specific_comment(self):
        analysis = _make_analysis()
        result = generate_teaching_comments(analysis, ["dead-shapes", "bent-four"])
        assert "bent four" in result["correct_comment"].lower()

    def test_alias_hane_gets_specific_comment(self):
        analysis = _make_analysis()
        result = generate_teaching_comments(analysis, ["tesuji", "hane"])
        assert "hane" in result["correct_comment"].lower()

    def test_alias_only_tag_resolves(self):
        """When technique_tags has only an alias (no canonical), still resolves."""
        analysis = _make_analysis()
        result = generate_teaching_comments(analysis, ["bent-four"])
        assert "bent four" in result["correct_comment"].lower()

    def test_canonical_without_alias_match_uses_generic(self):
        analysis = _make_analysis()
        result = generate_teaching_comments(analysis, ["dead-shapes"])
        assert "dead shapes" in result["correct_comment"].lower()


class TestConfidenceGating:
    """Test confidence-based suppression of teaching comments."""

    def test_high_confidence_emits_comment(self):
        analysis = _make_analysis()
        result = generate_teaching_comments(
            analysis, ["snapback"], tag_confidence="HIGH"
        )
        assert result["correct_comment"] != ""

    def test_certain_confidence_emits_comment(self):
        analysis = _make_analysis()
        result = generate_teaching_comments(
            analysis, ["snapback"], tag_confidence="CERTAIN"
        )
        assert result["correct_comment"] != ""

    def test_medium_confidence_suppresses_comment(self):
        analysis = _make_analysis()
        result = generate_teaching_comments(
            analysis, ["snapback"], tag_confidence="MEDIUM"
        )
        assert result["correct_comment"] == ""

    def test_low_confidence_suppresses_comment(self):
        analysis = _make_analysis()
        result = generate_teaching_comments(
            analysis, ["snapback"], tag_confidence="LOW"
        )
        assert result["correct_comment"] == ""

    def test_joseki_requires_certain(self):
        """Joseki has min_confidence=CERTAIN, so HIGH is insufficient."""
        analysis = _make_analysis()
        result = generate_teaching_comments(
            analysis, ["joseki"], tag_confidence="HIGH"
        )
        assert result["correct_comment"] == ""

    def test_joseki_certain_emits(self):
        analysis = _make_analysis()
        result = generate_teaching_comments(
            analysis, ["joseki"], tag_confidence="CERTAIN"
        )
        assert result["correct_comment"] != ""


# ---------------------------------------------------------------------------
# Test Remediation: Delta Gate (T10a-T10b / F17)
# ---------------------------------------------------------------------------

class TestDeltaGate:
    """Tests for F17/F23 delta gate — almost-correct threshold at 0.05."""

    def test_delta_below_threshold_produces_almost_correct(self):
        """F17: abs(delta) < 0.05 → almost_correct template."""
        analysis = _make_analysis(
            refutations=[{
                "wrong_move": "D4",
                "delta": 0.03,
                "refutation_depth": 3,
                "refutation_type": "unclassified",
            }]
        )
        result = generate_teaching_comments(analysis, ["life-and-death"])
        assert "D4" in result["wrong_comments"]
        assert "Close" in result["wrong_comments"]["D4"]
        # No coordinate should leak (defense-in-depth against spoilers)
        assert "{!" not in result["wrong_comments"]["D4"]

    def test_delta_above_threshold_passes_through(self):
        """F17: abs(delta) >= 0.05 → normal wrong-move comment (not 'Good move')."""
        analysis = _make_analysis(
            refutations=[{
                "wrong_move": "D4",
                "delta": 0.06,
                "refutation_depth": 3,
                "refutation_type": "unclassified",
            }]
        )
        result = generate_teaching_comments(analysis, ["life-and-death"])
        assert "D4" in result["wrong_comments"]
        assert "Close" not in result["wrong_comments"]["D4"]


# ---------------------------------------------------------------------------
# Test Remediation: Vital Move Placement (T11a-T11b / F16 / MH-6)
# ---------------------------------------------------------------------------

class TestVitalMovePlacement:
    """Tests for F16/MH-6 vital move root suppression."""

    def test_vital_suppresses_root_when_certain(self):
        """F16/MH-6: CERTAIN confidence + vital_node_index > 0 → root comment suppressed."""
        from unittest.mock import patch

        from analyzers.vital_move import VitalMoveResult

        analysis = _make_analysis()
        # Patch detect_vital_move to return a result with move_index > 0
        mock_vital = VitalMoveResult(
            move_index=2,
            sgf_coord="dd",
            alias=None,
            technique_phrase="Snapback (uttegaeshi)",
            ownership_delta=0.5,
        )
        with patch("analyzers.teaching_comments.detect_vital_move", return_value=mock_vital):
            result = generate_teaching_comments(
                analysis, ["snapback"], tag_confidence="CERTAIN"
            )
        assert result["correct_comment"] == "", "Root comment should be suppressed"
        assert result["vital_node_index"] is not None
        assert result["vital_node_index"] > 0

    def test_vital_non_certain_preserves_root(self):
        """MH-6: non-CERTAIN confidence keeps root comment even if vital detected."""
        from unittest.mock import patch

        from analyzers.vital_move import VitalMoveResult

        analysis = _make_analysis()
        mock_vital = VitalMoveResult(
            move_index=2,
            sgf_coord="dd",
            alias=None,
            technique_phrase="Snapback (uttegaeshi)",
            ownership_delta=0.5,
        )
        with patch("analyzers.teaching_comments.detect_vital_move", return_value=mock_vital):
            result = generate_teaching_comments(
                analysis, ["snapback"], tag_confidence="HIGH"  # NOT CERTAIN
            )
        assert result["correct_comment"] != "", "Root comment should be preserved for non-CERTAIN"
        assert result.get("vital_node_index") is None
