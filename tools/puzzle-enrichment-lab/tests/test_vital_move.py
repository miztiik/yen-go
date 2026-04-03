"""Tests for vital move detector (T4)."""

from __future__ import annotations

from analyzers.vital_move import detect_vital_move


def _node(sgf_coord: str, correct_alternatives: int = 0, is_forced: bool = False) -> dict:
    return {
        "sgf_coord": sgf_coord,
        "correct_alternatives": correct_alternatives,
        "is_forced": is_forced,
    }


class TestVitalMoveDetector:
    """Test detect_vital_move function."""

    def test_strict_order_finds_vital_move(self):
        """Multi-move sequence, vital at branch point."""
        tree = [
            _node("cc"),                          # first move
            _node("dd", is_forced=True),          # forced response
            _node("ee", correct_alternatives=2),  # branch = vital
        ]
        result = detect_vital_move(tree, "strict", ["snapback"])
        assert result is not None
        assert result.move_index == 2
        assert result.sgf_coord == "ee"

    def test_flexible_order_returns_none(self):
        """YO=flexible → no vital move."""
        tree = [_node("cc"), _node("dd", correct_alternatives=2)]
        result = detect_vital_move(tree, "flexible", ["snapback"])
        assert result is None

    def test_miai_returns_none(self):
        """YO=miai → no vital move."""
        tree = [_node("cc"), _node("dd", correct_alternatives=2)]
        result = detect_vital_move(tree, "miai", ["snapback"])
        assert result is None

    def test_first_move_is_vital_skips(self):
        """Vital move == first move → None (only 1 move in tree)."""
        tree = [_node("cc", correct_alternatives=3)]
        result = detect_vital_move(tree, "strict", ["snapback"])
        assert result is None

    def test_no_branching_returns_none(self):
        """Forced sequence → no vital move."""
        tree = [
            _node("cc"),
            _node("dd", is_forced=True),
            _node("ee", is_forced=True),
        ]
        result = detect_vital_move(tree, "strict", ["snapback"])
        assert result is None

    def test_alias_selection_at_vital(self):
        """Dead-shapes puzzle → alias selected at vital move."""
        tree = [_node("cc"), _node("dd", correct_alternatives=1)]
        result = detect_vital_move(
            tree, "strict", ["dead-shapes"], alias="bent-four"
        )
        assert result is not None
        assert result.alias == "bent-four"
        assert result.technique_phrase == "bent-four"

    def test_ownership_change_confirmation(self):
        """Engine ownership confirms vital point."""
        tree = [
            _node("cc"),
            _node("dd"),  # no branching, but ownership shift
        ]
        ownership = [
            {"sgf_coord": "cc", "ownership_delta": 0.1},
            {"sgf_coord": "dd", "ownership_delta": 0.5},
        ]
        result = detect_vital_move(
            tree, "strict", ["life-and-death"],
            ownership_data=ownership, ownership_threshold=0.3,
        )
        assert result is not None
        assert result.sgf_coord == "dd"
        assert result.ownership_delta == 0.5

    def test_ownership_below_threshold_skips(self):
        """Ownership delta below threshold → no vital move."""
        tree = [
            _node("cc"),
            _node("dd"),  # no branching, low ownership
        ]
        ownership = [
            {"sgf_coord": "dd", "ownership_delta": 0.1},
        ]
        result = detect_vital_move(
            tree, "strict", ["life-and-death"],
            ownership_data=ownership, ownership_threshold=0.3,
        )
        assert result is None

    def test_no_alias_leaves_technique_phrase_empty(self):
        """No alias → technique_phrase empty (caller uses parent phrase)."""
        tree = [_node("cc"), _node("dd", correct_alternatives=1)]
        result = detect_vital_move(tree, "strict", ["snapback"])
        assert result is not None
        assert result.alias is None
        assert result.technique_phrase == ""
