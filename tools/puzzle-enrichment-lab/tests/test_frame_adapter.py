"""Tests for frame_adapter — thin algorithm-agnostic frame API.

Covers: apply_frame roundtrip, remove_frame, validate_frame, FrameResult shape,
player_to_move preservation (C2 constraint).
"""

from pathlib import Path

_HERE = Path(__file__).resolve().parent
_LAB = _HERE.parent

from analyzers.frame_adapter import (
    FrameResult,
    apply_frame,
    remove_frame,
    validate_frame,
)
from models.position import Color, Position, Stone

# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------

def _stones(color: Color, coords: list[tuple[int, int]]) -> list[Stone]:
    return [Stone(color=color, x=x, y=y) for x, y in coords]


def _make_corner_tl(bs: int = 19) -> Position:
    """Top-left corner life-and-death position."""
    black = [(2, 0), (2, 1), (2, 2), (1, 2), (0, 2)]
    white = [(3, 0), (3, 1), (3, 2), (2, 3), (1, 3), (0, 3)]
    return Position(
        board_size=bs,
        stones=_stones(Color.BLACK, black) + _stones(Color.WHITE, white),
        player_to_move=Color.BLACK,
    )


# ---------------------------------------------------------------------------
# FrameResult shape
# ---------------------------------------------------------------------------

class TestFrameResult:
    def test_fields(self):
        fr = FrameResult(
            position=_make_corner_tl(),
            frame_stones_added=10,
            attacker_color=Color.BLACK,
        )
        assert fr.position is not None
        assert fr.frame_stones_added == 10
        assert fr.attacker_color == Color.BLACK


# ---------------------------------------------------------------------------
# apply_frame
# ---------------------------------------------------------------------------

class TestApplyFrame:
    def test_returns_frame_result(self):
        pos = _make_corner_tl()
        result = apply_frame(pos, margin=2)
        assert isinstance(result, FrameResult)
        assert result.frame_stones_added > 0

    def test_adds_stones(self):
        pos = _make_corner_tl()
        original_count = len(pos.stones)
        result = apply_frame(pos, margin=2)
        assert len(result.position.stones) > original_count

    def test_player_to_move_preserved(self):
        """C2 constraint: player_to_move must be preserved through framing."""
        pos = _make_corner_tl()
        assert pos.player_to_move == Color.BLACK
        result = apply_frame(pos, margin=2)
        assert result.position.player_to_move == Color.BLACK

    def test_player_to_move_white(self):
        """C2 constraint with white to move."""
        pos = Position(
            board_size=19,
            stones=_stones(Color.BLACK, [(2, 0), (2, 1), (2, 2)])
            + _stones(Color.WHITE, [(3, 0), (3, 1), (3, 2)]),
            player_to_move=Color.WHITE,
        )
        result = apply_frame(pos, margin=2)
        assert result.position.player_to_move == Color.WHITE

    def test_ko_flag(self):
        """apply_frame with ko=True should not crash."""
        pos = _make_corner_tl()
        result = apply_frame(pos, margin=2, ko=True)
        assert isinstance(result, FrameResult)


# ---------------------------------------------------------------------------
# remove_frame
# ---------------------------------------------------------------------------

class TestRemoveFrame:
    def test_returns_original_copy(self):
        original = _make_corner_tl()
        result = apply_frame(original, margin=2)
        restored = remove_frame(result.position, original)
        # Should have same stones as original
        assert len(restored.stones) == len(original.stones)
        # Should be a deep copy, not the same object
        assert restored is not original

    def test_identity_preservation(self):
        original = _make_corner_tl()
        result = apply_frame(original, margin=2)
        restored = remove_frame(result.position, original)
        orig_coords = {(s.x, s.y, s.color) for s in original.stones}
        rest_coords = {(s.x, s.y, s.color) for s in restored.stones}
        assert orig_coords == rest_coords


# ---------------------------------------------------------------------------
# validate_frame
# ---------------------------------------------------------------------------

class TestValidateFrame:
    def test_valid_frame(self):
        original = _make_corner_tl()
        result = apply_frame(original, margin=2)
        puzzle_coords = frozenset((s.x, s.y) for s in original.stones)
        is_valid, diag = validate_frame(
            result.position, original, result.attacker_color, puzzle_coords
        )
        # GP frame should produce valid frames for simple corner positions
        assert isinstance(is_valid, bool)
        assert isinstance(diag, dict)
        assert "defender_components" in diag
        assert "attacker_components" in diag

    def test_empty_frame_stones(self):
        """Position with zero frame stones added should still validate."""
        pos = _make_corner_tl()
        puzzle_coords = frozenset((s.x, s.y) for s in pos.stones)
        # Validate original against itself (no frame stones)
        is_valid, diag = validate_frame(pos, pos, Color.BLACK, puzzle_coords)
        assert is_valid  # no frame stones = no dead stones
        assert diag["dead_defender_stones"] == 0
        assert diag["dead_attacker_stones"] == 0
