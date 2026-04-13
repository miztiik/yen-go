"""Convert recognised board positions to SGF format.

Uses tools.core.sgf_builder.SGFBuilder for SGF construction
and tools.core.sgf_types for coordinate primitives.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from tools.core.sgf_builder import SGFBuilder
from tools.core.sgf_types import Color, Point

from tools.core.image_to_board import (
    BLACK,
    WHITE,
    RecognizedPosition,
    detect_digit,
)


def _order_moves(
    entries: list[tuple[int, Color, Point]],
    player_to_move: Color = Color.BLACK,
    setup_stones: frozenset[tuple[int, int]] | None = None,
    bbox: tuple[int, int, int, int] | None = None,
) -> list[tuple[Color, Point]]:
    """Order extracted moves, enforcing color alternation.

    Strategy (in priority order):

    1. **All digits detected + unique + alternating** — use digit order directly.
    2. **Hybrid** — sort known-digit entries by digit, insert unknown-digit
       entries at gaps where alternation would break.
    3. **Fallback** — interleave by color starting with *player_to_move*.

    Pre-filtering (applied before ordering):
    - Drops moves on already-occupied setup positions
    - Drops moves far outside the setup stone bounding box (noise)

    Args:
        entries: List of (digit_order, color, point) tuples.
        player_to_move: Who plays first (fallback ordering).
        setup_stones: Optional set of (x, y) occupied by setup stones.
        bbox: Optional (min_x, min_y, max_x, max_y) bounding box
            of setup stones. Moves outside bbox+margin are dropped.
    """
    if not entries:
        return []

    # --- Pre-filter: remove noise moves ---
    filtered = list(entries)

    if setup_stones:
        filtered = [
            (o, c, p) for o, c, p in filtered
            if (p.x, p.y) not in setup_stones
        ]

    if bbox:
        margin = 3
        min_x, min_y, max_x, max_y = bbox
        filtered = [
            (o, c, p) for o, c, p in filtered
            if (min_x - margin <= p.x <= max_x + margin and
                min_y - margin <= p.y <= max_y + margin)
        ]

    if not filtered:
        return []

    # --- Partition into known (digit > 0) and unknown (digit == 0) ---
    known = sorted(
        [(o, c, p) for o, c, p in filtered if o > 0],
        key=lambda e: e[0],
    )
    unknown = [(o, c, p) for o, c, p in filtered if o <= 0]

    # --- Fast path: all digits detected + unique + alternating ---
    if not unknown and len({o for o, _, _ in known}) == len(known):
        result = [(c, p) for _, c, p in known]
        if all(result[i][0] != result[i + 1][0] for i in range(len(result) - 1)):
            return result

    # --- Hybrid: merge known anchors + unknown stones via gap-filling ---
    if known:
        ordered = [(c, p) for _, c, p in known]
        remaining = list(unknown)
        merged: list[tuple[Color, Point]] = []

        for color, point in ordered:
            # Before placing this known stone, check if we need to insert
            # an unknown stone to maintain alternation
            if merged and merged[-1][0] == color and remaining:
                needed = Color.WHITE if color == Color.BLACK else Color.BLACK
                match = next(
                    (j for j, (_, c, _) in enumerate(remaining) if c == needed),
                    None,
                )
                if match is not None:
                    merged.append((remaining[match][1], remaining[match][2]))
                    remaining.pop(match)
            merged.append((color, point))

        # Append remaining unknowns at the end, alternation-constrained
        for _, c, p in remaining:
            if not merged or merged[-1][0] != c:
                merged.append((c, p))

        # Accept if strictly alternating
        if all(merged[i][0] != merged[i + 1][0] for i in range(len(merged) - 1)):
            return merged

    # --- Fallback: strict interleaving by color ---
    second_color = Color.WHITE if player_to_move == Color.BLACK else Color.BLACK
    pool_first = [(c, p) for _, c, p in filtered if c == player_to_move]
    pool_second = [(c, p) for _, c, p in filtered if c == second_color]

    result: list[tuple[Color, Point]] = []
    fi, si = 0, 0
    while fi < len(pool_first) or si < len(pool_second):
        if len(result) % 2 == 0:
            if fi < len(pool_first):
                result.append(pool_first[fi])
                fi += 1
            else:
                break
        else:
            if si < len(pool_second):
                result.append(pool_second[si])
                si += 1
            else:
                break

    return result


def position_to_sgf(
    pos: RecognizedPosition,
    player_to_move: Color = Color.BLACK,
    board_size: int = 19,
    comment: str = "",
) -> str:
    """Build SGF with AB[] / AW[] setup from a recognised position.

    Args:
        pos: Recognised board position.
        player_to_move: Which colour moves first.
        board_size: Full board size.
        comment: Optional root comment.

    Returns:
        Complete SGF string.
    """
    builder = SGFBuilder(board_size=board_size)
    builder.set_player_to_move(player_to_move)

    if comment:
        builder.set_comment(comment)

    for iy, row in enumerate(pos.board):
        for ix, cell in enumerate(row):
            x = pos.board_left + ix
            y = pos.board_top + iy
            if cell == BLACK:
                builder.add_black_stone(Point(x, y))
            elif cell == WHITE:
                builder.add_white_stone(Point(x, y))

    return builder.build()


def extract_solution_moves(
    problem: RecognizedPosition,
    answer: RecognizedPosition,
    answer_image: str | Path | None = None,
    player_to_move: Color = Color.BLACK,
) -> list[tuple[Color, Point]]:
    """Diff problem and answer images to find solution moves.

    Compares two recognized positions and returns new stones that
    appeared in the answer but not the problem.  When *answer_image*
    is provided, numbered stones are read via ``detect_digit()`` and
    moves are returned in correct sequence order.

    When digit detection is unreliable (missing or duplicate digits),
    moves are interleaved by color to enforce strict alternation
    starting with *player_to_move*.

    Args:
        problem: Recognised problem position.
        answer: Recognised answer position.
        answer_image: Optional path to the answer GIF.  When given,
            digit detection determines move order.
        player_to_move: Who plays first; used as fallback ordering
            when digit detection fails.

    Returns:
        List of (colour, point) for each new stone, ordered by
        move number when answer_image is provided.
    """
    # Collect raw new-stone positions.
    raw: list[tuple[int, int, str]] = []  # (iy, ix, color_char)

    n_rows = min(len(problem.board), len(answer.board))
    for iy in range(n_rows):
        n_cols = min(len(problem.board[iy]), len(answer.board[iy]))
        for ix in range(n_cols):
            p_cell = problem.board[iy][ix]
            a_cell = answer.board[iy][ix]

            if p_cell != a_cell and a_cell in (BLACK, WHITE):
                raw.append((iy, ix, a_cell))

    if not raw:
        return []

    # Detect digits when answer image is available.
    digits: dict[tuple[int, int], int] = {}
    if answer_image is not None:
        img = Image.open(str(answer_image)).convert("RGB")
        for iy, ix, color_char in raw:
            cx = answer.grid.x_lines[ix]
            cy = answer.grid.y_lines[iy]
            digit = detect_digit(img, cx, cy, color_char).digit
            digits[(iy, ix)] = digit

    # Build move list, ordered by digit when available.
    entries: list[tuple[int, Color, Point]] = []
    for iy, ix, color_char in raw:
        color = Color.BLACK if color_char == BLACK else Color.WHITE
        point = Point(problem.board_left + ix, problem.board_top + iy)
        order = digits.get((iy, ix), 0)
        entries.append((order, color, point))

    # Compute setup stone positions and bounding box for noise filtering
    setup_stones: set[tuple[int, int]] = set()
    xs: list[int] = []
    ys: list[int] = []
    for iy, row in enumerate(problem.board):
        for ix, cell in enumerate(row):
            if cell in (BLACK, WHITE):
                sx = problem.board_left + ix
                sy = problem.board_top + iy
                setup_stones.add((sx, sy))
                xs.append(sx)
                ys.append(sy)

    bbox = (min(xs), min(ys), max(xs), max(ys)) if xs else None

    return _order_moves(
        entries, player_to_move,
        setup_stones=frozenset(setup_stones),
        bbox=bbox,
    )
