"""GoProblems.com-style tsumego frame — count-based fill algorithm.

Pure Python port of the KaTrain/ghostban tsumego frame algorithm.
Reference: KaTrain ``tsumego_frame.py`` (MIT, SHA 877684f9…).

This is an ALTERNATIVE frame implementation to the BFS-based
``tsumego_frame.py`` in the same package.  It faithfully reproduces
the goproblems.com framing logic:

* Count-based half-and-half territory fill (NOT BFS)
* Solid attacker wall at frame_range (bbox + margin) boundary
* ``(i+j)%2 == 0`` checkerboard holes only far from the seam
* Flip/normalize to canonical position before fill
* Optional ko-threat placement

Key constants (from KaTrain):
  ``near_to_edge = 2``  — snap bbox to board edge when within 2 pts
  ``offence_to_win = 5`` — give offense an extra 5-point advantage

The ghostban variant uses ``offence_to_win = 10``; callers can override
via the ``offence_to_win`` parameter.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

try:
    from models.position import Color, Position, Stone
except ImportError:
    from ..models.position import Color, Position, Stone

try:
    from analyzers.sgf_parser import extract_position, parse_sgf
except ImportError:
    from .sgf_parser import extract_position, parse_sgf

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants (from KaTrain — MIT)
# ---------------------------------------------------------------------------
NEAR_TO_EDGE = 2
DEFAULT_OFFENCE_TO_WIN = 5
DEFAULT_MARGIN = 2

BLACK = "B"
WHITE = "W"
EMPTY = "-"

# Ko-threat ASCII patterns  (from KaTrain)
# Each tuple: (pattern_string, top_p, left_p)
_OFFENSE_KO_THREAT = (
    "....OOOX.\n.....XXXX",
    True,
    False,
)
_DEFENSE_KO_THREAT = (
    "..\n..\nX.\nXO\nOO\n.O",
    False,
    True,
)


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass
class GPFrameResult:
    """Result of the GoProblems-style frame generation."""

    position: Position
    frame_stones_added: int
    attacker_color: Color
    black_to_attack: bool
    offence_to_win: int


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def apply_gp_frame(
    position: Position,
    *,
    margin: int = DEFAULT_MARGIN,
    komi: float = 0.0,
    ko: bool = False,
    offence_to_win: int = DEFAULT_OFFENCE_TO_WIN,
) -> GPFrameResult:
    """Apply the GoProblems.com-style tsumego frame to a position.

    Args:
        position: Board position with puzzle stones.
        margin: Padding around bounding box (default 2).
        komi: Komi for territory balance calculation (default 0).
        ko: Whether the puzzle involves ko.
        offence_to_win: Extra points for offense (5 = KaTrain, 10 = ghostban).

    Returns:
        GPFrameResult with the framed position.
    """
    if not position.stones:
        return GPFrameResult(
            position=position.model_copy(deep=True),
            frame_stones_added=0,
            attacker_color=Color.BLACK,
            black_to_attack=True,
            offence_to_win=offence_to_win,
        )

    board_size = position.board_size
    black_to_play = position.player_to_move == Color.BLACK

    # Build the internal board representation (2D grid of dicts)
    board = _position_to_board(position)
    sizes = (board_size, board_size)

    # Run the core algorithm
    filled = _tsumego_frame_stones(
        board, komi, black_to_play, ko, margin, offence_to_win
    )

    # Extract new frame stones
    new_stones = list(position.stones)
    occupied = {(s.x, s.y) for s in position.stones}
    frame_count = 0
    black_to_attack = True  # will be set properly below

    for i in range(board_size):
        for j in range(board_size):
            cell = filled[i][j] if i < len(filled) and j < len(filled[i]) else {}
            if cell.get("tsumego_frame") and cell.get("stone"):
                coord = (j, i)  # j=x (col), i=y (row)
                if coord not in occupied:
                    color = Color.BLACK if cell["black"] else Color.WHITE
                    new_stones.append(Stone(color=color, x=j, y=i))
                    frame_count += 1

    # Determine attacker color from the algorithm
    ijs = [
        {"i": i, "j": j, "black": h.get("black")}
        for i, row in enumerate(board)
        for j, h in enumerate(row)
        if h.get("stone")
    ]
    if ijs:
        extrema = _find_extrema(ijs)
        black_to_attack = _guess_black_to_attack(extrema, sizes)

    framed_position = Position(
        board_size=board_size,
        stones=new_stones,
        player_to_move=position.player_to_move,
        komi=position.komi,
    )

    return GPFrameResult(
        position=framed_position,
        frame_stones_added=frame_count,
        attacker_color=Color.BLACK if black_to_attack else Color.WHITE,
        black_to_attack=black_to_attack,
        offence_to_win=offence_to_win,
    )


def apply_gp_frame_sgf(
    sgf_text: str,
    *,
    margin: int = DEFAULT_MARGIN,
    komi: float = 0.0,
    ko: bool = False,
    offence_to_win: int = DEFAULT_OFFENCE_TO_WIN,
) -> str:
    """Apply the GoProblems.com-style tsumego frame to an SGF string.

    Parses the SGF, extracts the position, applies the frame,
    and returns the framed position as an SGF string.
    """
    root = parse_sgf(sgf_text)
    position = extract_position(root)
    result = apply_gp_frame(
        position,
        margin=margin,
        komi=komi,
        ko=ko,
        offence_to_win=offence_to_win,
    )
    return result.position.to_sgf()


# ---------------------------------------------------------------------------
# Internal board representation
# ---------------------------------------------------------------------------

def _position_to_board(position: Position) -> list[list[dict]]:
    """Convert Position model to internal 2D grid of dicts.

    Grid is [row][col] = [i][j] where i=row (y), j=col (x).
    Each cell is {} (empty) or {"stone": True, "black": bool}.
    """
    bs = position.board_size
    board: list[list[dict]] = [
        [{} for _ in range(bs)] for _ in range(bs)
    ]
    for stone in position.stones:
        board[stone.y][stone.x] = {
            "stone": True,
            "black": stone.color == Color.BLACK,
        }
    return board


# ---------------------------------------------------------------------------
# Core algorithm (ported from KaTrain — MIT)
# ---------------------------------------------------------------------------

def _tsumego_frame_stones(
    stones: list[list[dict]],
    komi: float,
    black_to_play: bool,
    ko: bool,
    margin: int,
    offence_to_win: int,
) -> list[list[dict]]:
    """Core frame fill algorithm (KaTrain port).

    Operates on the internal 2D grid in-place and returns it.
    """
    sizes = _ij_sizes(stones)
    isize, jsize = sizes

    # Collect all stone positions
    ijs = [
        {"i": i, "j": j, "black": h.get("black")}
        for i, row in enumerate(stones)
        for j, h in enumerate(row)
        if h.get("stone")
    ]

    if not ijs:
        return stones

    # Find extrema
    extrema = _find_extrema(ijs)
    top, bottom, left, right = extrema

    # Snap to board edges
    imin = _snap0(top["i"])
    jmin = _snap0(left["j"])
    imax = _snap_size(bottom["i"], isize)
    jmax = _snap_size(right["j"], jsize)

    # Flip/rotate to canonical position
    flip_spec = _compute_flip_spec(imin, jmin, imax, jmax, isize, jsize)

    if any(flip_spec):
        flipped = _flip_stones(stones, flip_spec)
        filled = _tsumego_frame_stones(
            flipped, komi, black_to_play, ko, margin, offence_to_win
        )
        return _flip_stones(filled, flip_spec)

    # Compute frame_range (puzzle bbox + margin)
    i0 = imin - margin
    i1 = imax + margin
    j0 = jmin - margin
    j1 = jmax + margin
    frame_range = (i0, i1, j0, j1)

    # Determine attacker
    black_to_attack = _guess_black_to_attack(extrema, sizes)

    # Step 1: Border wall (solid attacker ring)
    _put_border(stones, sizes, frame_range, black_to_attack)

    # Step 2: Outside fill (count-based half+half)
    _put_outside(
        stones, sizes, frame_range,
        black_to_attack, black_to_play, komi, offence_to_win,
    )

    # Step 3: Ko-threat (if applicable)
    if ko:
        _put_ko_threat(
            stones, sizes, frame_range,
            black_to_attack, black_to_play, ko,
        )

    return stones


# ---------------------------------------------------------------------------
# Extrema & attacker detection
# ---------------------------------------------------------------------------

def _find_extrema(ijs: list[dict]) -> tuple[dict, dict, dict, dict]:
    """Find the top/bottom/left/right extreme stones."""
    top = _min_by(ijs, "i", +1)
    bottom = _min_by(ijs, "i", -1)
    left = _min_by(ijs, "j", +1)
    right = _min_by(ijs, "j", -1)
    return top, bottom, left, right


def _min_by(ary: list[dict], key: str, sign: int) -> dict:
    """Find element with min value of sign * element[key]."""
    values = [sign * z[key] for z in ary]
    return ary[values.index(min(values))]


def _guess_black_to_attack(
    extrema: tuple[dict, dict, dict, dict],
    sizes: tuple[int, int],
) -> bool:
    """Guess whether Black is the attacker using edge-proximity weighting.

    For each extremal stone (top/bottom/left/right), multiplies
    sign (+1 for Black, -1 for White) by combined row+col distance
    from board center. If the weighted sum > 0, Black is attacker.
    """
    return sum(
        _sign_of_color(z) * _height2(z, sizes) for z in extrema
    ) > 0


def _sign_of_color(z: dict) -> int:
    return 1 if z["black"] else -1


def _height2(z: dict, sizes: tuple[int, int]) -> float:
    isize, jsize = sizes
    return _height(z["i"], isize) + _height(z["j"], jsize)


def _height(k: int, size: int) -> float:
    """Distance from board center — higher means closer to edge."""
    return size - abs(k - (size - 1) / 2)


# ---------------------------------------------------------------------------
# Edge snapping & normalization
# ---------------------------------------------------------------------------

def _snap(k: int, to: int) -> int:
    """Snap k to board edge ``to`` if within NEAR_TO_EDGE points."""
    return to if abs(k - to) <= NEAR_TO_EDGE else k


def _snap0(k: int) -> int:
    return _snap(k, 0)


def _snap_size(k: int, size: int) -> int:
    return _snap(k, size - 1)


def _need_flip(kmin: int, kmax: int, size: int) -> bool:
    return kmin < size - kmax - 1


def _compute_flip_spec(
    imin: int, jmin: int, imax: int, jmax: int,
    isize: int, jsize: int,
) -> tuple[bool, bool, bool]:
    """Compute (flip_i, flip_j, swap_ij) for canonical orientation.

    If imin < jmin, swap axes first (no flip). Otherwise flip each axis
    independently if needed.
    """
    if imin < jmin:
        return (False, False, True)
    return (
        _need_flip(imin, imax, isize),
        _need_flip(jmin, jmax, jsize),
        False,
    )


# ---------------------------------------------------------------------------
# Flip utilities
# ---------------------------------------------------------------------------

def _flip_stones(
    stones: list[list[dict]],
    flip_spec: tuple[bool, bool, bool],
) -> list[list[dict]]:
    """Flip/swap the board grid according to flip_spec = (flip_i, flip_j, swap)."""
    flip_i, flip_j, swap = flip_spec
    isize, jsize = _ij_sizes(stones)
    new_isize = jsize if swap else isize
    new_jsize = isize if swap else jsize
    new_stones: list[list[dict]] = [
        [{} for _ in range(new_jsize)] for _ in range(new_isize)
    ]
    for i, row in enumerate(stones):
        for j, cell in enumerate(row):
            ni, nj = _flip_ij(i, j, isize, jsize, flip_spec)
            new_stones[ni][nj] = cell
    return new_stones


def _flip_ij(
    i: int, j: int,
    isize: int, jsize: int,
    flip_spec: tuple[bool, bool, bool],
) -> tuple[int, int]:
    flip_i, flip_j, swap = flip_spec
    fi = (isize - 1 - i) if flip_i else i
    fj = (jsize - 1 - j) if flip_j else j
    return (fj, fi) if swap else (fi, fj)


# ---------------------------------------------------------------------------
# Border fill — solid attacker ring
# ---------------------------------------------------------------------------

def _put_border(
    stones: list[list[dict]],
    sizes: tuple[int, int],
    frame_range: tuple[int, int, int, int],
    is_black: bool,
) -> None:
    """Place a solid ring of attacker stones on the frame_range perimeter."""
    i0, i1, j0, j1 = frame_range
    _put_twin(stones, sizes, i0, i1, j0, j1, is_black, False)
    _put_twin(stones, sizes, j0, j1, i0, i1, is_black, True)


def _put_twin(
    stones: list[list[dict]],
    sizes: tuple[int, int],
    beg: int, end: int,
    at0: int, at1: int,
    is_black: bool,
    reverse: bool,
) -> None:
    for at in (at0, at1):
        for k in range(beg, end + 1):
            i, j = (at, k) if reverse else (k, at)
            _put_stone(stones, sizes, i, j, is_black, False, True)


# ---------------------------------------------------------------------------
# Outside fill — count-based half+half
# ---------------------------------------------------------------------------

def _put_outside(
    stones: list[list[dict]],
    sizes: tuple[int, int],
    frame_range: tuple[int, int, int, int],
    black_to_attack: bool,
    black_to_play: bool,
    komi: float,
    offence_to_win: int,
) -> None:
    """Fill outside the frame_range with count-based defense/offense split.

    Iterates row-major. First ~half of non-puzzle cells → defense,
    remainder → offense. Cells with (i+j)%2==0 are left empty when
    far from the color-transition seam.
    """
    isize, jsize = sizes
    count = 0
    offense_komi = (+1 if black_to_attack else -1) * komi
    defense_area = (isize * jsize - offense_komi - offence_to_win) / 2

    for i in range(isize):
        for j in range(jsize):
            if _inside(i, j, frame_range):
                continue
            count += 1
            black_p = _xor(black_to_attack, count <= defense_area)
            empty_p = (
                (i + j) % 2 == 0
                and abs(count - defense_area) > isize
            )
            _put_stone(stones, sizes, i, j, black_p, empty_p)


# ---------------------------------------------------------------------------
# Ko-threat placement
# ---------------------------------------------------------------------------

def _put_ko_threat(
    stones: list[list[dict]],
    sizes: tuple[int, int],
    frame_range: tuple[int, int, int, int],
    black_to_attack: bool,
    black_to_play: bool,
    ko: bool,
) -> None:
    """Place fixed ko-threat patterns at far corners."""
    isize, jsize = sizes
    for_offense = _xor(ko, _xor(black_to_attack, black_to_play))
    pattern_str, top_p, left_p = (
        _OFFENSE_KO_THREAT if for_offense else _DEFENSE_KO_THREAT
    )
    rows = [list(line) for line in pattern_str.strip().splitlines() if line]
    height = len(rows)
    width = len(rows[0]) if rows else 0

    for pi, row in enumerate(rows):
        for pj, ch in enumerate(row):
            ai = pi + (0 if top_p else isize - height)
            aj = pj + (0 if left_p else jsize - width)
            if _inside(ai, aj, frame_range):
                return
            black = _xor(black_to_attack, ch == "O")
            empty = ch == "."
            _put_stone(stones, sizes, ai, aj, black, empty)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _put_stone(
    stones: list[list[dict]],
    sizes: tuple[int, int],
    i: int, j: int,
    black: bool,
    empty: bool,
    tsumego_frame_region_mark: bool = False,
) -> None:
    """Place a single cell on the board grid."""
    isize, jsize = sizes
    if i < 0 or i >= isize or j < 0 or j >= jsize:
        return
    if empty:
        stones[i][j] = {}
    else:
        stones[i][j] = {
            "stone": True,
            "tsumego_frame": True,
            "black": black,
            "tsumego_frame_region_mark": tsumego_frame_region_mark,
        }


def _inside(i: int, j: int, region: tuple[int, int, int, int]) -> bool:
    """Check if (i, j) is inside the frame_range region."""
    i0, i1, j0, j1 = region
    return i0 <= i <= i1 and j0 <= j <= j1


def _xor(a: bool, b: bool) -> bool:
    return bool(a) != bool(b)


def _ij_sizes(stones: list[list[dict]]) -> tuple[int, int]:
    return (len(stones), len(stones[0]) if stones else 0)
