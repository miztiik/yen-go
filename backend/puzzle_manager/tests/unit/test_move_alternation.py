"""
Unit tests for MoveAlternationDetector.

Spec 117: Solution Move Alternation Detection

Tests cover:
- Basic alternation patterns (B-W-B-W)
- Miai patterns (B-B-B, W-W-W)
- Edge cases (empty, single, invalid)
- Helper methods (is_miai, is_valid_sequence)
"""

import pytest

from backend.puzzle_manager.core.move_alternation import (
    MoveAlternationAnalysis,
    MoveAlternationDetector,
    MoveAlternationResult,
)


class TestMoveAlternationResult:
    """Test MoveAlternationResult enum values."""

    def test_enum_values_exist(self):
        """Verify all expected enum values exist."""
        assert MoveAlternationResult.ALTERNATING
        assert MoveAlternationResult.MIAI
        assert MoveAlternationResult.NON_ALTERNATING
        assert MoveAlternationResult.SINGLE_MOVE
        assert MoveAlternationResult.EMPTY
        assert MoveAlternationResult.INVALID


class TestMoveAlternationAnalysis:
    """Test MoveAlternationAnalysis dataclass."""

    def test_is_valid_sequence_alternating(self):
        """Alternating is a valid sequence."""
        analysis = MoveAlternationAnalysis(
            result=MoveAlternationResult.ALTERNATING,
            move_count=3,
            colors=["B", "W", "B"],
            violation_indices=[],
        )
        assert analysis.is_valid_sequence is True

    def test_is_valid_sequence_single(self):
        """Single move is a valid sequence."""
        analysis = MoveAlternationAnalysis(
            result=MoveAlternationResult.SINGLE_MOVE,
            move_count=1,
            colors=["B"],
            violation_indices=[],
        )
        assert analysis.is_valid_sequence is True

    def test_is_valid_sequence_empty(self):
        """Empty is a valid sequence."""
        analysis = MoveAlternationAnalysis(
            result=MoveAlternationResult.EMPTY,
            move_count=0,
            colors=[],
            violation_indices=[],
        )
        assert analysis.is_valid_sequence is True

    def test_is_valid_sequence_miai_false(self):
        """Miai is NOT a valid sequence (should be variations)."""
        analysis = MoveAlternationAnalysis(
            result=MoveAlternationResult.MIAI,
            move_count=2,
            colors=["B", "B"],
            violation_indices=[1],
        )
        assert analysis.is_valid_sequence is False

    def test_is_miai_true(self):
        """Test is_miai property returns True for miai."""
        analysis = MoveAlternationAnalysis(
            result=MoveAlternationResult.MIAI,
            move_count=2,
            colors=["B", "B"],
            violation_indices=[1],
        )
        assert analysis.is_miai is True

    def test_is_miai_false(self):
        """Test is_miai property returns False for non-miai."""
        analysis = MoveAlternationAnalysis(
            result=MoveAlternationResult.ALTERNATING,
            move_count=2,
            colors=["B", "W"],
            violation_indices=[],
        )
        assert analysis.is_miai is False

    def test_first_violation_index(self):
        """Test first_violation_index property."""
        analysis = MoveAlternationAnalysis(
            result=MoveAlternationResult.NON_ALTERNATING,
            move_count=4,
            colors=["B", "W", "W", "B"],
            violation_indices=[2, 3],  # W-W at index 2
        )
        assert analysis.first_violation_index == 2

    def test_first_violation_index_none_when_valid(self):
        """Test first_violation_index is None for valid sequences."""
        analysis = MoveAlternationAnalysis(
            result=MoveAlternationResult.ALTERNATING,
            move_count=3,
            colors=["B", "W", "B"],
            violation_indices=[],
        )
        assert analysis.first_violation_index is None


class TestMoveAlternationDetectorAnalyze:
    """Test MoveAlternationDetector.analyze() method."""

    @pytest.fixture
    def detector(self):
        return MoveAlternationDetector()

    # Alternating patterns
    def test_alternating_bwb(self, detector):
        """B-W-B is properly alternating."""
        moves = [("B", "aa"), ("W", "bb"), ("B", "cc")]
        assert detector.analyze(moves) == MoveAlternationResult.ALTERNATING

    def test_alternating_wbw(self, detector):
        """W-B-W is properly alternating."""
        moves = [("W", "aa"), ("B", "bb"), ("W", "cc")]
        assert detector.analyze(moves) == MoveAlternationResult.ALTERNATING

    def test_alternating_bw(self, detector):
        """B-W is properly alternating."""
        moves = [("B", "aa"), ("W", "bb")]
        assert detector.analyze(moves) == MoveAlternationResult.ALTERNATING

    def test_alternating_long_sequence(self, detector):
        """Long alternating sequence passes."""
        moves = [("B", "a"), ("W", "b"), ("B", "c"), ("W", "d"), ("B", "e")]
        assert detector.analyze(moves) == MoveAlternationResult.ALTERNATING

    # Miai patterns (all same color)
    def test_miai_bb(self, detector):
        """B-B is miai."""
        moves = [("B", "aa"), ("B", "bb")]
        assert detector.analyze(moves) == MoveAlternationResult.MIAI

    def test_miai_bbb(self, detector):
        """B-B-B is miai."""
        moves = [("B", "aa"), ("B", "bb"), ("B", "cc")]
        assert detector.analyze(moves) == MoveAlternationResult.MIAI

    def test_miai_ww(self, detector):
        """W-W is miai."""
        moves = [("W", "aa"), ("W", "bb")]
        assert detector.analyze(moves) == MoveAlternationResult.MIAI

    def test_miai_www(self, detector):
        """W-W-W is miai."""
        moves = [("W", "aa"), ("W", "bb"), ("W", "cc")]
        assert detector.analyze(moves) == MoveAlternationResult.MIAI

    def test_miai_six_moves_same_color(self, detector):
        """Six same-color moves is miai."""
        moves = [("B", str(i)) for i in range(6)]
        assert detector.analyze(moves) == MoveAlternationResult.MIAI

    # Non-alternating (mixed violations)
    def test_non_alternating_bww(self, detector):
        """B-W-W is non-alternating (not pure miai)."""
        moves = [("B", "aa"), ("W", "bb"), ("W", "cc")]
        assert detector.analyze(moves) == MoveAlternationResult.NON_ALTERNATING

    def test_non_alternating_wbb(self, detector):
        """W-B-B is non-alternating."""
        moves = [("W", "aa"), ("B", "bb"), ("B", "cc")]
        assert detector.analyze(moves) == MoveAlternationResult.NON_ALTERNATING

    def test_non_alternating_bwwb(self, detector):
        """B-W-W-B is non-alternating."""
        moves = [("B", "aa"), ("W", "bb"), ("W", "cc"), ("B", "dd")]
        assert detector.analyze(moves) == MoveAlternationResult.NON_ALTERNATING

    # Edge cases
    def test_single_move_b(self, detector):
        """Single B move is SINGLE_MOVE."""
        moves = [("B", "aa")]
        assert detector.analyze(moves) == MoveAlternationResult.SINGLE_MOVE

    def test_single_move_w(self, detector):
        """Single W move is SINGLE_MOVE."""
        moves = [("W", "aa")]
        assert detector.analyze(moves) == MoveAlternationResult.SINGLE_MOVE

    def test_empty_sequence(self, detector):
        """Empty sequence is EMPTY."""
        moves = []
        assert detector.analyze(moves) == MoveAlternationResult.EMPTY

    def test_invalid_color(self, detector):
        """Invalid color is INVALID."""
        moves = [("X", "aa"), ("B", "bb")]
        assert detector.analyze(moves) == MoveAlternationResult.INVALID

    def test_invalid_move_format(self, detector):
        """Invalid move format is INVALID."""
        moves = [("B",)]  # Missing coord
        assert detector.analyze(moves) == MoveAlternationResult.INVALID

    def test_none_move(self, detector):
        """None move is INVALID."""
        moves = [None, ("B", "aa")]
        assert detector.analyze(moves) == MoveAlternationResult.INVALID

    # List format (Sanderland style)
    def test_list_format_alternating(self, detector):
        """List format [color, coord, comment] works."""
        moves = [["B", "aa", "comment"], ["W", "bb", ""]]
        assert detector.analyze(moves) == MoveAlternationResult.ALTERNATING

    def test_list_format_miai(self, detector):
        """List format detects miai."""
        moves = [["B", "oa", "First"], ["B", "ra", "Second"]]
        assert detector.analyze(moves) == MoveAlternationResult.MIAI


class TestMoveAlternationDetectorAnalyzeDetailed:
    """Test MoveAlternationDetector.analyze_detailed() method."""

    @pytest.fixture
    def detector(self):
        return MoveAlternationDetector()

    def test_detailed_colors_captured(self, detector):
        """Colors are captured in analysis."""
        moves = [("B", "aa"), ("W", "bb"), ("B", "cc")]
        analysis = detector.analyze_detailed(moves)
        assert analysis.colors == ["B", "W", "B"]

    def test_detailed_move_count(self, detector):
        """Move count is accurate."""
        moves = [("B", "aa"), ("W", "bb"), ("B", "cc")]
        analysis = detector.analyze_detailed(moves)
        assert analysis.move_count == 3

    def test_detailed_violation_indices_empty_for_valid(self, detector):
        """No violations for valid sequence."""
        moves = [("B", "aa"), ("W", "bb")]
        analysis = detector.analyze_detailed(moves)
        assert analysis.violation_indices == []

    def test_detailed_violation_indices_for_miai(self, detector):
        """Violations captured for miai."""
        moves = [("B", "aa"), ("B", "bb"), ("B", "cc")]
        analysis = detector.analyze_detailed(moves)
        # Violations at index 1 and 2 (where same color repeats)
        assert analysis.violation_indices == [1, 2]

    def test_detailed_violation_indices_for_non_alternating(self, detector):
        """Violations captured for non-alternating."""
        moves = [("B", "aa"), ("W", "bb"), ("W", "cc")]
        analysis = detector.analyze_detailed(moves)
        assert analysis.violation_indices == [2]


class TestMoveAlternationDetectorHelpers:
    """Test helper methods is_valid_sequence and is_miai."""

    @pytest.fixture
    def detector(self):
        return MoveAlternationDetector()

    def test_is_valid_sequence_true(self, detector):
        """is_valid_sequence returns True for alternating."""
        assert detector.is_valid_sequence([("B", "aa"), ("W", "bb")]) is True

    def test_is_valid_sequence_false_miai(self, detector):
        """is_valid_sequence returns False for miai."""
        assert detector.is_valid_sequence([("B", "aa"), ("B", "bb")]) is False

    def test_is_valid_sequence_single(self, detector):
        """is_valid_sequence returns True for single move."""
        assert detector.is_valid_sequence([("B", "aa")]) is True

    def test_is_miai_true(self, detector):
        """is_miai returns True for same-color moves."""
        assert detector.is_miai([("B", "aa"), ("B", "bb")]) is True

    def test_is_miai_false(self, detector):
        """is_miai returns False for alternating."""
        assert detector.is_miai([("B", "aa"), ("W", "bb")]) is False

    def test_is_miai_false_single(self, detector):
        """is_miai returns False for single move."""
        assert detector.is_miai([("B", "aa")]) is False


class TestRealWorldSanderlandCases:
    """Test cases from actual Sanderland puzzles."""

    @pytest.fixture
    def detector(self):
        return MoveAlternationDetector()

    def test_sanderland_prob0009_miai(self, detector):
        """Prob0009.json: B plays ba or ea (miai)."""
        sol = [["B", "ba", ""], ["B", "ea", ""]]
        assert detector.is_miai(sol) is True
        assert detector.analyze(sol) == MoveAlternationResult.MIAI

    def test_sanderland_prob0019_three_way_miai(self, detector):
        """Prob0019.json: B plays ba or ea or ac (3-way miai)."""
        sol = [["B", "ba", ""], ["B", "ea", ""], ["B", "ac", ""]]
        assert detector.is_miai(sol) is True
        assert detector.analyze(sol) == MoveAlternationResult.MIAI

    def test_sanderland_prob0168_six_way_miai(self, detector):
        """Prob0168.json: 6 possible first moves."""
        sol = [
            ["B", "ab", ""], ["B", "bb", ""], ["B", "cb", ""],
            ["B", "ca", ""], ["B", "aa", ""], ["B", "ba", ""]
        ]
        assert detector.is_miai(sol) is True
        analysis = detector.analyze_detailed(sol)
        assert analysis.move_count == 6
        assert all(c == "B" for c in analysis.colors)
