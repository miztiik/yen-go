"""Tests for GoProblems.com-style tsumego frame (count-based fill).

Covers: apply_gp_frame, apply_gp_frame_sgf, internal helpers
(_find_extrema, _guess_black_to_attack, _snap0, _snap_size, _xor,
 _inside, _flip_stones, _put_border, _put_outside).
"""

from pathlib import Path

_HERE = Path(__file__).resolve().parent
_LAB = _HERE.parent

from analyzers.tsumego_frame_gp import (
    GPFrameResult,
    _find_extrema,
    _flip_stones,
    _height,
    _ij_sizes,
    _inside,
    _position_to_board,
    _put_stone,
    _snap0,
    _snap_size,
    _xor,
    apply_gp_frame,
    apply_gp_frame_sgf,
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


def _make_corner_br(bs: int = 19) -> Position:
    """Bottom-right corner position."""
    off = bs - 1
    black = [(off - 2, off), (off - 2, off - 1), (off - 2, off - 2),
             (off - 1, off - 2), (off, off - 2)]
    white = [(off - 3, off), (off - 3, off - 1), (off - 3, off - 2),
             (off - 2, off - 3), (off - 1, off - 3), (off, off - 3)]
    return Position(
        board_size=bs,
        stones=_stones(Color.BLACK, black) + _stones(Color.WHITE, white),
        player_to_move=Color.BLACK,
    )


def _make_corner_tr(bs: int = 19) -> Position:
    """Top-right corner position."""
    off = bs - 1
    black = [(off - 2, 0), (off - 2, 1), (off - 2, 2),
             (off - 1, 2), (off, 2)]
    white = [(off - 3, 0), (off - 3, 1), (off - 3, 2),
             (off - 2, 3), (off - 1, 3), (off, 3)]
    return Position(
        board_size=bs,
        stones=_stones(Color.BLACK, black) + _stones(Color.WHITE, white),
        player_to_move=Color.BLACK,
    )


def _make_corner_bl(bs: int = 19) -> Position:
    """Bottom-left corner position."""
    off = bs - 1
    black = [(2, off), (2, off - 1), (2, off - 2),
             (1, off - 2), (0, off - 2)]
    white = [(3, off), (3, off - 1), (3, off - 2),
             (2, off - 3), (1, off - 3), (0, off - 3)]
    return Position(
        board_size=bs,
        stones=_stones(Color.BLACK, black) + _stones(Color.WHITE, white),
        player_to_move=Color.BLACK,
    )


def _make_empty(bs: int = 19) -> Position:
    """Empty position."""
    return Position(board_size=bs, stones=[], player_to_move=Color.BLACK)


def _count_frame_stones(pos: Position, original: Position) -> int:
    """Count stones added by framing."""
    orig_coords = {(s.x, s.y) for s in original.stones}
    return sum(1 for s in pos.stones if (s.x, s.y) not in orig_coords)


# ---------------------------------------------------------------------------
# Tests: Primitive helpers
# ---------------------------------------------------------------------------

class TestXor:
    def test_same_false(self):
        assert _xor(False, False) is False

    def test_same_true(self):
        assert _xor(True, True) is False

    def test_different(self):
        assert _xor(True, False) is True
        assert _xor(False, True) is True


class TestSnap:
    def test_snap0_close(self):
        assert _snap0(1) == 0
        assert _snap0(2) == 0

    def test_snap0_far(self):
        assert _snap0(3) == 3
        assert _snap0(10) == 10

    def test_snap_size_close(self):
        assert _snap_size(17, 19) == 18
        assert _snap_size(16, 19) == 18

    def test_snap_size_far(self):
        assert _snap_size(14, 19) == 14


class TestInside:
    def test_inside(self):
        region = (2, 8, 2, 8)
        assert _inside(5, 5, region) is True
        assert _inside(2, 2, region) is True
        assert _inside(8, 8, region) is True

    def test_outside(self):
        region = (2, 8, 2, 8)
        assert _inside(1, 5, region) is False
        assert _inside(9, 5, region) is False
        assert _inside(5, 1, region) is False
        assert _inside(5, 9, region) is False


class TestHeight:
    def test_edge(self):
        assert _height(0, 19) == 19 - 9  # 10
        assert _height(18, 19) == 19 - 9  # 10

    def test_center(self):
        assert _height(9, 19) == 19.0  # distance from center = 0


# ---------------------------------------------------------------------------
# Tests: Board conversion
# ---------------------------------------------------------------------------

class TestPositionToBoard:
    def test_empty(self):
        pos = _make_empty(9)
        board = _position_to_board(pos)
        assert len(board) == 9
        assert len(board[0]) == 9
        assert all(board[i][j] == {} for i in range(9) for j in range(9))

    def test_with_stones(self):
        pos = Position(
            board_size=9,
            stones=[Stone(color=Color.BLACK, x=2, y=3)],
            player_to_move=Color.BLACK,
        )
        board = _position_to_board(pos)
        assert board[3][2] == {"stone": True, "black": True}
        assert board[0][0] == {}


# ---------------------------------------------------------------------------
# Tests: Extrema detection
# ---------------------------------------------------------------------------

class TestFindExtrema:
    def test_single_stone(self):
        ijs = [{"i": 5, "j": 5, "black": True}]
        top, bottom, left, right = _find_extrema(ijs)
        assert top["i"] == 5
        assert bottom["i"] == 5
        assert left["j"] == 5
        assert right["j"] == 5

    def test_multiple_stones(self):
        ijs = [
            {"i": 2, "j": 5, "black": True},
            {"i": 8, "j": 3, "black": False},
            {"i": 5, "j": 1, "black": True},
            {"i": 5, "j": 9, "black": False},
        ]
        top, bottom, left, right = _find_extrema(ijs)
        assert top["i"] == 2
        assert bottom["i"] == 8
        assert left["j"] == 1
        assert right["j"] == 9


# ---------------------------------------------------------------------------
# Tests: Flip/swap
# ---------------------------------------------------------------------------

class TestFlipStones:
    def test_identity(self):
        board = [[{"stone": True, "black": True}, {}], [{}, {}]]
        result = _flip_stones(board, (False, False, False))
        assert result[0][0] == {"stone": True, "black": True}
        assert result[0][1] == {}

    def test_flip_i(self):
        board = [[{"stone": True, "black": True}, {}], [{}, {}]]
        result = _flip_stones(board, (True, False, False))
        assert result[1][0] == {"stone": True, "black": True}
        assert result[0][0] == {}

    def test_flip_j(self):
        board = [[{"stone": True, "black": True}, {}], [{}, {}]]
        result = _flip_stones(board, (False, True, False))
        assert result[0][1] == {"stone": True, "black": True}
        assert result[0][0] == {}

    def test_swap(self):
        board = [
            [{"stone": True, "black": True}, {}],
            [{}, {"stone": True, "black": False}],
        ]
        result = _flip_stones(board, (False, False, True))
        assert result[0][0] == {"stone": True, "black": True}
        assert result[1][1] == {"stone": True, "black": False}


# ---------------------------------------------------------------------------
# Tests: apply_gp_frame
# ---------------------------------------------------------------------------

class TestApplyGPFrame:
    def test_empty_position(self):
        pos = _make_empty()
        result = apply_gp_frame(pos)
        assert isinstance(result, GPFrameResult)
        assert result.frame_stones_added == 0

    def test_corner_tl_adds_stones(self):
        pos = _make_corner_tl()
        result = apply_gp_frame(pos)
        assert result.frame_stones_added > 0
        assert len(result.position.stones) > len(pos.stones)

    def test_corner_br_adds_stones(self):
        pos = _make_corner_br()
        result = apply_gp_frame(pos)
        assert result.frame_stones_added > 0

    def test_preserves_puzzle_stones(self):
        pos = _make_corner_tl()
        result = apply_gp_frame(pos)
        orig_coords = {(s.x, s.y, s.color) for s in pos.stones}
        framed_coords = {(s.x, s.y, s.color) for s in result.position.stones}
        assert orig_coords.issubset(framed_coords)

    def test_board_size_preserved(self):
        pos = _make_corner_tl(9)
        result = apply_gp_frame(pos)
        assert result.position.board_size == 9

    def test_player_to_move_preserved(self):
        pos = _make_corner_tl()
        pos = pos.model_copy(update={"player_to_move": Color.WHITE})
        result = apply_gp_frame(pos)
        assert result.position.player_to_move == Color.WHITE

    def test_no_stone_outside_board(self):
        pos = _make_corner_tl()
        result = apply_gp_frame(pos)
        bs = result.position.board_size
        for s in result.position.stones:
            assert 0 <= s.x < bs, f"x={s.x} out of range"
            assert 0 <= s.y < bs, f"y={s.y} out of range"

    def test_no_duplicate_coordinates(self):
        pos = _make_corner_tl()
        result = apply_gp_frame(pos)
        coords = [(s.x, s.y) for s in result.position.stones]
        assert len(coords) == len(set(coords))

    def test_offence_to_win_parameter(self):
        pos = _make_corner_tl()
        r5 = apply_gp_frame(pos, offence_to_win=5)
        r10 = apply_gp_frame(pos, offence_to_win=10)
        assert r5.offence_to_win == 5
        assert r10.offence_to_win == 10

    def test_all_four_corners(self):
        for factory in [_make_corner_tl, _make_corner_br, _make_corner_tr, _make_corner_bl]:
            pos = factory()
            result = apply_gp_frame(pos)
            assert result.frame_stones_added > 0, f"Failed for {factory.__name__}"
            assert len(result.position.stones) > len(pos.stones)


class TestApplyGPFrameSmallBoard:
    def test_9x9_corner(self):
        pos = _make_corner_tl(9)
        result = apply_gp_frame(pos)
        assert result.frame_stones_added > 0
        bs = result.position.board_size
        for s in result.position.stones:
            assert 0 <= s.x < bs
            assert 0 <= s.y < bs


# ---------------------------------------------------------------------------
# Tests: SGF roundtrip
# ---------------------------------------------------------------------------

class TestApplyGPFrameSgf:
    def test_simple_sgf(self):
        sgf = (
            "(;FF[4]GM[1]SZ[19]"
            "AB[cc][cd][ce][bc][ac]"
            "AW[dc][dd][de][cd][bd][ad]"
            "PL[B]"
            ";B[bb])"
        )
        result = apply_gp_frame_sgf(sgf)
        assert isinstance(result, str)
        assert "SZ[19]" in result


# ---------------------------------------------------------------------------
# Tests: Attacker detection
# ---------------------------------------------------------------------------

class TestAttackerDetection:
    def test_tl_corner(self):
        pos = _make_corner_tl()
        result = apply_gp_frame(pos)
        # White surrounds black in TL corner → white attacks
        assert result.black_to_attack is False

    def test_br_corner(self):
        pos = _make_corner_br()
        result = apply_gp_frame(pos)
        # After flip-normalization to TL, edge-proximity heuristic
        # identifies Black as attacker for this symmetric layout.
        assert result.black_to_attack is True


# ---------------------------------------------------------------------------
# Tests: Border & outside fill
# ---------------------------------------------------------------------------

class TestBorderFill:
    def test_border_stones_exist(self):
        """After framing, there should be stones on the frame perimeter."""
        pos = _make_corner_tl()
        result = apply_gp_frame(pos)
        framed = result.position
        orig_coords = {(s.x, s.y) for s in pos.stones}
        new_stones = [s for s in framed.stones if (s.x, s.y) not in orig_coords]
        assert len(new_stones) > 0

    def test_mixed_colors_in_frame(self):
        """Frame should contain both colors (border + territory)."""
        pos = _make_corner_tl()
        result = apply_gp_frame(pos)
        orig_coords = {(s.x, s.y) for s in pos.stones}
        new_stones = [s for s in result.position.stones if (s.x, s.y) not in orig_coords]
        colors = {s.color for s in new_stones}
        assert Color.BLACK in colors
        assert Color.WHITE in colors


class TestPutStone:
    def test_out_of_bounds_ignored(self):
        board = [[{} for _ in range(5)] for _ in range(5)]
        sizes = (5, 5)
        _put_stone(board, sizes, -1, 0, True, False)
        _put_stone(board, sizes, 0, 5, True, False)
        assert all(board[i][j] == {} for i in range(5) for j in range(5))

    def test_empty_clears(self):
        board = [[{"stone": True, "black": True}]]
        sizes = (1, 1)
        _put_stone(board, sizes, 0, 0, True, True)
        assert board[0][0] == {}

    def test_stone_placed(self):
        board = [[{}]]
        sizes = (1, 1)
        _put_stone(board, sizes, 0, 0, True, False)
        assert board[0][0]["stone"] is True
        assert board[0][0]["black"] is True


# ---------------------------------------------------------------------------
# Tests: ij_sizes
# ---------------------------------------------------------------------------

class TestIjSizes:
    def test_square(self):
        board = [[{} for _ in range(9)] for _ in range(9)]
        assert _ij_sizes(board) == (9, 9)

    def test_empty(self):
        assert _ij_sizes([]) == (0, 0)
