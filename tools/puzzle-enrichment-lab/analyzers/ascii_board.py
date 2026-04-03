"""ASCII board renderer — converts a Position or SGF string to a text diagram.

Standard Go convention:
    X = Black stone
    O = White stone
    . = Empty intersection

Coordinate labels use GTP convention (A-T, skipping I; rows numbered
from bottom). The player to move is shown below the board.

Usage:
    from analyzers.ascii_board import render_ascii, render_sgf_ascii

    # From a Position object
    print(render_ascii(position))

    # From raw SGF text
    print(render_sgf_ascii(sgf_text))
"""

from __future__ import annotations

try:
    from core.tsumego_analysis import extract_position, parse_sgf
    from models.position import Color, Position
except ImportError:
    from ..core.tsumego_analysis import extract_position, parse_sgf
    from ..models.position import Color, Position

# GTP column letters (skip 'I')
_COL_LETTERS = "ABCDEFGHJKLMNOPQRST"


def render_ascii(position: Position, *, show_coords: bool = True) -> str:
    """Render a Position as an ASCII board string.

    Args:
        position: Board position to render.
        show_coords: If True, add column letters and row numbers.

    Returns:
        Multi-line string with the board diagram.
    """
    size = position.board_size

    # Build lookup: (x, y) -> Color
    stone_map: dict[tuple[int, int], Color] = {}
    for stone in position.stones:
        stone_map[(stone.x, stone.y)] = stone.color

    lines: list[str] = []

    # Column header
    if show_coords:
        col_labels = "   " + " ".join(_COL_LETTERS[c] for c in range(size))
        lines.append(col_labels)

    for y in range(size):
        row_num = size - y  # GTP row numbering (bottom = 1)
        cells: list[str] = []
        for x in range(size):
            color = stone_map.get((x, y))
            if color == Color.BLACK:
                cells.append("X")
            elif color == Color.WHITE:
                cells.append("O")
            else:
                cells.append(".")
        row_str = " ".join(cells)
        if show_coords:
            row_str = f"{row_num:2d} {row_str} {row_num}"
        lines.append(row_str)

    # Column footer
    if show_coords:
        lines.append(col_labels)

    # Player to move
    to_move = "Black (X)" if position.player_to_move == Color.BLACK else "White (O)"
    lines.append(f"To move: {to_move}")

    return "\n".join(lines)


def render_sgf_ascii(sgf_text: str, *, show_coords: bool = True) -> str:
    """Parse an SGF string and render the initial position as ASCII.

    Args:
        sgf_text: Raw SGF content.
        show_coords: If True, add column letters and row numbers.

    Returns:
        Multi-line ASCII board string.
    """
    root = parse_sgf(sgf_text)
    position = extract_position(root)
    return render_ascii(position, show_coords=show_coords)
