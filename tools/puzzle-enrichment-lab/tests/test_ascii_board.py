"""Tests for ASCII board renderer."""

from pathlib import Path

import pytest

_HERE = Path(__file__).resolve().parent
_LAB = _HERE.parent

from analyzers.ascii_board import render_ascii, render_sgf_ascii
from models.position import Color, Position, Stone

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _stones(color: Color, coords: list[tuple[int, int]]) -> list[Stone]:
    return [Stone(color=color, x=x, y=y) for x, y in coords]


# ---------------------------------------------------------------------------
# render_ascii
# ---------------------------------------------------------------------------

class TestRenderAscii:
    def test_empty_9x9(self):
        pos = Position(board_size=9, stones=[])
        result = render_ascii(pos)
        assert "To move: Black (X)" in result
        # 9 row lines + 2 header/footer + 1 to-move
        lines = result.strip().split("\n")
        assert len(lines) == 12  # header + 9 rows + footer + to-move

    def test_single_black_stone(self):
        pos = Position(board_size=9, stones=[Stone(color=Color.BLACK, x=2, y=2)])
        result = render_ascii(pos)
        assert "X" in result
        # +1 for the X in "Black (X)" on the to-move line
        assert result.count("X") == 2

    def test_single_white_stone(self):
        pos = Position(board_size=9, stones=[Stone(color=Color.WHITE, x=4, y=4)])
        result = render_ascii(pos)
        assert "O" in result
        assert result.count("O") == 1

    def test_black_and_white(self):
        stones = (
            _stones(Color.BLACK, [(0, 0), (1, 0)]) +
            _stones(Color.WHITE, [(0, 1), (1, 1)])
        )
        pos = Position(board_size=9, stones=stones)
        result = render_ascii(pos)
        # +1 for the X in "Black (X)" on the to-move line
        assert result.count("X") == 3
        assert result.count("O") == 2

    def test_player_to_move_white(self):
        pos = Position(board_size=9, player_to_move=Color.WHITE)
        result = render_ascii(pos)
        assert "To move: White (O)" in result

    def test_no_coords(self):
        pos = Position(board_size=9, stones=[Stone(color=Color.BLACK, x=0, y=0)])
        result = render_ascii(pos, show_coords=False)
        # Should not have column letters or row numbers
        assert "A" not in result
        assert "9" not in result

    def test_coords_present_by_default(self):
        pos = Position(board_size=9)
        result = render_ascii(pos)
        assert "A" in result
        assert "9" in result


# ---------------------------------------------------------------------------
# render_sgf_ascii (end-to-end from raw SGF)
# ---------------------------------------------------------------------------

class TestRenderSgfAscii:
    # A minimal 9×9 tsumego: Black at c7, d7; White at c6, d6
    _SGF_9x9 = "(;GM[1]FF[4]SZ[9]AB[cc][dc]AW[cd][dd])"

    def test_basic_sgf(self):
        result = render_sgf_ascii(self._SGF_9x9)
        assert result.count("X") == 3  # 2 stones + 1 in "Black (X)"
        assert result.count("O") == 2

    def test_round_trip_preserves_board_size(self):
        result = render_sgf_ascii(self._SGF_9x9)
        lines = result.strip().split("\n")
        # header + 9 rows + footer + to-move = 12
        assert len(lines) == 12

    def test_invalid_sgf_raises(self):
        with pytest.raises(ValueError):
            render_sgf_ascii("not valid sgf")

    def test_19x19_sgf(self):
        sgf = "(;GM[1]FF[4]SZ[19]AB[dp][pp]AW[dd][pd]PL[B])"
        result = render_sgf_ascii(sgf)
        assert result.count("X") == 3  # 2 stones + 1 in "Black (X)"
        # 2 white stones + 2 column-header "O"s (top+bottom)
        assert result.count("O") == 4
        # header + 19 rows + footer + to-move = 22
        lines = result.strip().split("\n")
        assert len(lines) == 22
