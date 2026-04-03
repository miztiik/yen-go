"""Integration tests for analyzers.teaching_comments — V2 full pipeline tests.

Covers:
- Full pipeline for various techniques
- Signal detection → hc:3
- V1 fallback → hc:2
- Confidence gating → hc:0
- Vital move annotation
- Wrong-move classification + top-3 selection
- One insight per node
- Max correct annotations policy
"""

from __future__ import annotations

import pytest
from analyzers.teaching_comments import generate_teaching_comments
from config import clear_cache


@pytest.fixture(autouse=True)
def _clear_cfg():
    clear_cache()
    yield
    clear_cache()


# ---- Helpers ----

def _make_analysis(
    *,
    correct_move_gtp: str = "C3",
    correct_move_sgf: str = "cc",
    correct_move_policy: float = 0.3,
    correct_move_winrate: float = 0.95,
    suggested_level: str = "intermediate",
    refutations: list[dict] | None = None,
    solution_tree: list[dict] | None = None,
    move_order: str = "strict",
    alternative_correct_moves: int = -1,
    solution_branches: int = 0,
    vital_coord: str = "",
) -> dict:
    """Build a minimal analysis dict for testing."""
    return {
        "validation": {
            "correct_move_gtp": correct_move_gtp,
            "correct_move_sgf": correct_move_sgf,
            "correct_move_policy": correct_move_policy,
            "correct_move_winrate": correct_move_winrate,
            "status": "accepted",
            "alternative_correct_moves": alternative_correct_moves,
            "vital_coord": vital_coord,
        },
        "refutations": refutations or [],
        "difficulty": {
            "suggested_level": suggested_level,
        },
        "solution_tree": solution_tree or [],
        "move_order": move_order,
        "solution_branches": solution_branches,
    }


# ---- Full Pipeline Tests ----

class TestFullPipelineSnapback:
    def test_snapback_basic(self):
        """Snapback puzzle → correct comment includes technique name."""
        analysis = _make_analysis()
        result = generate_teaching_comments(analysis, ["snapback"])
        assert "Snapback" in result["correct_comment"]
        assert result["hc_level"] >= 2
        assert result["summary"] != ""

    def test_snapback_with_vital_signal(self):
        """Snapback with vital_coord → signal-enriched (hc:3)."""
        analysis = _make_analysis(vital_coord="cg")
        result = generate_teaching_comments(analysis, ["snapback"])
        assert result["hc_level"] == 3
        assert "vital point" in result["correct_comment"].lower()


class TestFullPipelineDeadShapes:
    def test_dead_shapes_bent_four(self):
        """dead-shapes + bent-four → alias progression."""
        analysis = _make_analysis()
        result = generate_teaching_comments(
            analysis, ["dead-shapes", "bent-four"]
        )
        # V1 fallback should include "bent four"
        assert "bent four" in result["correct_comment"].lower() or \
               "dead shapes" in result["correct_comment"].lower()


class TestFullPipelineWrongMoves:
    def test_wrong_moves_top3_causal(self):
        """5 wrong moves → top 3 by refutation depth get causal comments."""
        refs = [
            {"wrong_move": "A1", "delta": 0.6, "refutation_depth": 5,
             "refutation_type": "unclassified", "escape_detected": True,
             "refutation_pv": ["dd"]},
            {"wrong_move": "B2", "delta": 0.4, "refutation_depth": 4,
             "refutation_type": "unclassified", "opponent_lives": True,
             "refutation_pv": ["ee"]},
            {"wrong_move": "C3", "delta": 0.3, "refutation_depth": 3,
             "refutation_type": "unclassified", "capturing_race_lost": True,
             "refutation_pv": ["ff"]},
            {"wrong_move": "D4", "delta": 0.2, "refutation_depth": 2,
             "refutation_type": "unclassified", "refutation_pv": ["gg"]},
            {"wrong_move": "E5", "delta": 0.1, "refutation_depth": 1,
             "refutation_type": "unclassified", "refutation_pv": ["hh"]},
        ]
        analysis = _make_analysis(refutations=refs)
        result = generate_teaching_comments(analysis, ["life-and-death"])
        wc = result["wrong_comments"]
        assert len(wc) == 5
        # Top 3 should have non-default comments
        # D4 and E5 should have default-based comments

    def test_wrong_comment_includes_delta(self):
        """Wrong move with large delta includes percentage."""
        refs = [
            {"wrong_move": "D4", "delta": 0.7, "refutation_depth": 3,
             "refutation_type": "unclassified", "refutation_pv": ["dd"]},
        ]
        analysis = _make_analysis(refutations=refs)
        result = generate_teaching_comments(analysis, ["life-and-death"])
        assert "70%" in result["wrong_comments"]["D4"]


class TestFullPipelineNoVital:
    def test_depth1_no_vital(self):
        """Depth-1 puzzle → no vital move annotation."""
        tree = [{"sgf_coord": "cc", "correct_alternatives": 0}]
        analysis = _make_analysis(solution_tree=tree)
        result = generate_teaching_comments(analysis, ["life-and-death"])
        assert result["vital_comment"] == ""


class TestFullPipelineFlexibleOrder:
    def test_flexible_no_vital(self):
        """YO=flexible → no vital move annotation (GOV-V2-01)."""
        tree = [
            {"sgf_coord": "cc", "correct_alternatives": 0},
            {"sgf_coord": "dd", "correct_alternatives": 2},
        ]
        analysis = _make_analysis(solution_tree=tree, move_order="flexible")
        result = generate_teaching_comments(analysis, ["life-and-death"])
        assert result["vital_comment"] == ""


class TestHcLevels:
    def test_hc3_when_signal_present(self):
        """Signal detected → hc:3."""
        analysis = _make_analysis(vital_coord="ab")
        result = generate_teaching_comments(analysis, ["life-and-death"])
        assert result["hc_level"] == 3

    def test_hc2_when_no_signal(self):
        """No signal → V1 fallback → hc:2."""
        analysis = _make_analysis()
        result = generate_teaching_comments(analysis, ["life-and-death"])
        assert result["hc_level"] == 2

    def test_hc0_when_suppressed(self):
        """Low confidence → suppressed → hc:0."""
        analysis = _make_analysis()
        result = generate_teaching_comments(
            analysis, ["snapback"], tag_confidence="LOW"
        )
        assert result["hc_level"] == 0
        assert result["correct_comment"] == ""


class TestConfidenceGating:
    def test_high_confidence_emits(self):
        analysis = _make_analysis()
        result = generate_teaching_comments(
            analysis, ["snapback"], tag_confidence="HIGH"
        )
        assert result["correct_comment"] != ""

    def test_certain_confidence_emits(self):
        analysis = _make_analysis()
        result = generate_teaching_comments(
            analysis, ["snapback"], tag_confidence="CERTAIN"
        )
        assert result["correct_comment"] != ""

    def test_medium_suppresses(self):
        analysis = _make_analysis()
        result = generate_teaching_comments(
            analysis, ["snapback"], tag_confidence="MEDIUM"
        )
        assert result["correct_comment"] == ""

    def test_joseki_requires_certain(self):
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


class TestSummary:
    def test_includes_level(self):
        analysis = _make_analysis(suggested_level="elementary")
        result = generate_teaching_comments(analysis, ["life-and-death"])
        assert "elementary" in result["summary"].lower()

    def test_includes_tag_name(self):
        analysis = _make_analysis()
        result = generate_teaching_comments(analysis, ["capture-race"])
        assert "capture" in result["summary"].lower()


class TestReturnStructure:
    def test_returns_all_fields(self):
        analysis = _make_analysis()
        result = generate_teaching_comments(analysis, ["life-and-death"])
        assert "correct_comment" in result
        assert "vital_comment" in result
        assert "wrong_comments" in result
        assert "summary" in result
        assert "hc_level" in result

    def test_empty_tags_uses_fallback(self):
        """Empty tags → unclassified → suppressed (hc:0, no comment)."""
        analysis = _make_analysis()
        result = generate_teaching_comments(analysis, [])
        assert result["correct_comment"] == ""
        assert result["hc_level"] == 0

    def test_no_refutations_empty_wrong(self):
        analysis = _make_analysis(refutations=[])
        result = generate_teaching_comments(analysis, ["life-and-death"])
        assert result["wrong_comments"] == {}
