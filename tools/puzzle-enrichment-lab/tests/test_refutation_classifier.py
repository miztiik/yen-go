"""Tests for wrong-move refutation classifier (T5)."""

from __future__ import annotations

from analyzers.refutation_classifier import (
    classify_all_refutations,
    classify_refutation,
)


def _ref(
    wrong_move: str = "dd",
    refutation_depth: int = 3,
    delta: float = -0.5,
    refutation_pv: list[str] | None = None,
    refutation_type: str = "unclassified",
    pv_truncated: bool = False,
    capture_verified: bool = False,
    escape_detected: bool = False,
    opponent_lives: bool = False,
    capturing_race_lost: bool = False,
    ko_detected: bool = False,
    liberty_reduction: bool = False,
    self_atari: bool = False,
    wrong_direction: bool = False,
) -> dict:
    return {
        "wrong_move": wrong_move,
        "refutation_depth": refutation_depth,
        "delta": delta,
        "refutation_pv": refutation_pv or [],
        "refutation_type": refutation_type,
        "pv_truncated": pv_truncated,
        "capture_verified": capture_verified,
        "escape_detected": escape_detected,
        "opponent_lives": opponent_lives,
        "capturing_race_lost": capturing_race_lost,
        "ko_detected": ko_detected,
        "liberty_reduction": liberty_reduction,
        "self_atari": self_atari,
        "wrong_direction": wrong_direction,
    }


class TestClassifyRefutation:
    """Unit tests for single refutation classification."""

    def test_immediate_capture_classified(self):
        ref = _ref(refutation_depth=1, capture_verified=True)
        result = classify_refutation(ref, "cc", ["snapback"])
        assert result.condition == "immediate_capture"

    def test_opponent_escapes_classified(self):
        ref = _ref(escape_detected=True)
        result = classify_refutation(ref, "cc", ["escape"])
        assert result.condition == "opponent_escapes"

    def test_opponent_lives_classified(self):
        ref = _ref(opponent_lives=True)
        result = classify_refutation(ref, "cc", ["life-and-death"])
        assert result.condition == "opponent_lives"

    def test_capturing_race_classified(self):
        ref = _ref(capturing_race_lost=True)
        result = classify_refutation(ref, "cc", ["capture-race"])
        assert result.condition == "capturing_race_lost"

    def test_opponent_takes_vital_classified(self):
        ref = _ref(refutation_pv=["cc", "dd"])
        result = classify_refutation(ref, "cc", ["life-and-death"])
        assert result.condition == "opponent_takes_vital"
        assert result.refutation_coord == "cc"

    def test_shape_death_alias_classified(self):
        ref = _ref()
        result = classify_refutation(
            ref, "xx", ["dead-shapes"], alias="bent-four"
        )
        assert result.condition == "shape_death_alias"
        assert result.alias == "bent-four"

    def test_ko_classified(self):
        ref = _ref(ko_detected=True)
        result = classify_refutation(ref, "cc", ["ko"])
        assert result.condition == "ko_involved"

    def test_default_fallback(self):
        ref = _ref()
        result = classify_refutation(ref, "cc", ["life-and-death"])
        assert result.condition == "default"

    def test_priority_order(self):
        """Overlapping conditions → highest priority wins."""
        ref = _ref(
            refutation_depth=1,
            capture_verified=True,
            escape_detected=True,  # lower priority
        )
        result = classify_refutation(ref, "cc", ["snapback"])
        assert result.condition == "immediate_capture"

    def test_shallow_tree_guard(self):
        """Refutation depth < threshold → default."""
        ref = _ref(refutation_depth=1, capture_verified=True)
        result = classify_refutation(
            ref, "cc", ["snapback"], min_depth_for_causal=2
        )
        assert result.condition == "default"


class TestClassifyAllRefutations:
    """Tests for full classification pipeline."""

    def test_top3_selection(self):
        """5 wrong moves → top 3 by depth get causal, rest get default."""
        refs = [
            _ref("a1", refutation_depth=5, escape_detected=True),
            _ref("b2", refutation_depth=4, opponent_lives=True),
            _ref("c3", refutation_depth=3, capturing_race_lost=True),
            _ref("d4", refutation_depth=2, ko_detected=True),
            _ref("e5", refutation_depth=1, escape_detected=True),
        ]
        result = classify_all_refutations(refs, "cc", ["life-and-death"], max_causal=3)
        assert len(result.causal) == 3
        assert result.causal[0].wrong_move == "a1"  # depth 5
        assert result.causal[1].wrong_move == "b2"  # depth 4
        assert result.causal[2].wrong_move == "c3"  # depth 3
        # Overflow → default
        assert len(result.default_moves) == 2
        assert all(d.condition == "default" for d in result.default_moves)

    def test_all_default_when_no_conditions(self):
        """No conditions match → all default."""
        refs = [_ref("a1"), _ref("b2")]
        result = classify_all_refutations(refs, "cc", ["life-and-death"])
        assert len(result.causal) == 0
        assert len(result.default_moves) == 2

    def test_fewer_than_max_causal(self):
        """Only 1 causal → 1 causal, rest default."""
        refs = [
            _ref("a1", capture_verified=True, refutation_depth=1),
            _ref("b2"),
        ]
        result = classify_all_refutations(refs, "cc", ["snapback"], max_causal=3)
        assert len(result.causal) == 1
        assert result.causal[0].condition == "immediate_capture"
        assert len(result.default_moves) == 1

    def test_empty_refutations(self):
        result = classify_all_refutations([], "cc", ["life-and-death"])
        assert len(result.causal) == 0
        assert len(result.default_moves) == 0


# ---------------------------------------------------------------------------
# Test Remediation: New classifier conditions (T9a-T9c / F15)
# ---------------------------------------------------------------------------

class TestNewClassifierConditions:
    """Tests for F15 classifier conditions: opponent_reduces_liberties, self_atari, wrong_direction."""

    # --- T9a: opponent_reduces_liberties ---

    def test_opponent_reduces_liberties_classified(self):
        """F15: liberty_reduction=True fires the condition."""
        ref = _ref(liberty_reduction=True)
        result = classify_refutation(ref, "cc", ["life-and-death"])
        assert result.condition == "opponent_reduces_liberties"

    def test_opponent_reduces_liberties_not_without_data(self):
        """F15: Without liberty_reduction flag, condition does not fire."""
        ref = _ref()  # liberty_reduction defaults to False
        # No other conditions match either (wrong_move="dd", correct="xx")
        result = classify_refutation(ref, "xx", ["life-and-death"])
        assert result.condition == "default"

    def test_liberty_reduction_with_capture_uses_capture(self):
        """F15: capture_verified=True is higher priority than liberty_reduction."""
        ref = _ref(liberty_reduction=True, capture_verified=True, refutation_depth=1)
        result = classify_refutation(ref, "cc", ["life-and-death"])
        assert result.condition == "immediate_capture"

    # --- T9b: self_atari ---

    def test_self_atari_classified(self):
        """F15: self_atari=True fires the condition."""
        ref = _ref(self_atari=True)
        result = classify_refutation(ref, "cc", ["life-and-death"])
        assert result.condition == "self_atari"

    def test_self_atari_not_without_data(self):
        """F15: Without self_atari flag, condition does not fire."""
        ref = _ref()
        result = classify_refutation(ref, "xx", ["life-and-death"])
        assert result.condition == "default"

    # --- T9c: wrong_direction ---

    def test_wrong_direction_classified(self):
        """F15: wrong_direction=True fires the condition."""
        ref = _ref(wrong_direction=True)
        result = classify_refutation(ref, "cc", ["life-and-death"])
        assert result.condition == "wrong_direction"

    def test_wrong_direction_not_without_data(self):
        """F15: Without wrong_direction flag, condition does not fire."""
        ref = _ref()
        result = classify_refutation(ref, "xx", ["life-and-death"])
        assert result.condition == "default"


# ---------------------------------------------------------------------------
# refutation_type propagation
# ---------------------------------------------------------------------------

class TestRefutationTypePropagation:
    """Tests that refutation_type flows through classification unchanged.

    The refutation_type field (\"curated\", \"ai_generated\", \"score_based\")
    is set upstream by generate_refutations.py and must survive classification
    so that teaching_comments.py can respect the puzzle author's judgment for
    curated wrongs (e.g. never labelling a curated 'Wrong' as 'Good move').
    """

    def test_curated_type_preserved_on_classify(self):
        ref = _ref(refutation_type="curated")
        result = classify_refutation(ref, "cc", ["life-and-death"])
        assert result.refutation_type == "curated"

    def test_ai_generated_type_preserved(self):
        ref = _ref(refutation_type="ai_generated", escape_detected=True)
        result = classify_refutation(ref, "cc", ["escape"])
        assert result.refutation_type == "ai_generated"

    def test_unclassified_type_preserved(self):
        ref = _ref(refutation_type="unclassified")
        result = classify_refutation(ref, "xx", ["life-and-death"])
        assert result.refutation_type == "unclassified"

    def test_classify_all_preserves_curated_on_causal(self):
        refs = [_ref("a1", refutation_type="curated", escape_detected=True)]
        result = classify_all_refutations(refs, "cc", ["escape"])
        assert result.causal[0].refutation_type == "curated"

    def test_classify_all_preserves_type_on_overflow_to_default(self):
        """When causal overflows to default, refutation_type is preserved."""
        refs = [
            _ref("a1", refutation_depth=5, escape_detected=True, refutation_type="curated"),
            _ref("b2", refutation_depth=4, opponent_lives=True, refutation_type="ai_generated"),
        ]
        result = classify_all_refutations(refs, "cc", ["life-and-death"], max_causal=1)
        assert result.causal[0].refutation_type == "curated"
        # b2 overflowed to default but keeps its type
        assert result.default_moves[0].refutation_type == "ai_generated"
