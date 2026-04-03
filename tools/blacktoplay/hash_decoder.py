"""BTP hash decoding/encoding -- Python port of btp-tsumego.js position_from_hash / get_hash_from_position.

Converts BTP's base-59 encoded board hashes to/from 2D board positions.
"""

from __future__ import annotations

# Base-59 charset (missing: lowercase 'l', uppercase 'I', uppercase 'O')
CHARSET = "0123456789abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ"

# Index = board_size, value = hash string length
HASH_LENGTHS = [0, 2, 2, 4, 6, 8, 12, 14, 20, 24, 30, 36, 42, 50, 56, 66, 74, 84, 94, 104]

EMPTY, BLACK, WHITE = ".", "B", "W"


def decode_hash(hash_str: str, board_size: int) -> list[str]:
    """Decode a BTP hash string into a 2D board position.

    Args:
        hash_str: Base-59 encoded hash from BTP.
        board_size: Board size (e.g. 9, 19).

    Returns:
        List of strings, each representing a row. Characters: '.', 'B', 'W'.
    """
    expected_len = HASH_LENGTHS[board_size]
    if len(hash_str) > expected_len:
        hash_str = hash_str[-expected_len:]

    position_string = ""
    for n in range(0, len(hash_str), 2):
        if n + 1 >= len(hash_str):
            break
        c0 = CHARSET.index(hash_str[n])
        c1 = CHARSET.index(hash_str[n + 1])
        number = c1 * 59 + c0

        part = ""
        for i in range(6, -1, -1):
            power = 3 ** i
            if number >= power * 2:
                part = WHITE + part
                number -= power * 2
            elif number >= power:
                part = BLACK + part
                number -= power
            else:
                part = EMPTY + part

        position_string += part

    total = board_size * board_size
    if len(position_string) > total:
        position_string = position_string[:total]

    rows: list[str] = []
    for i in range(board_size):
        start = i * board_size
        end = start + board_size
        row = position_string[start:end]
        while len(row) < board_size:
            row += EMPTY
        rows.append(row)

    while len(rows) < board_size:
        rows.append(EMPTY * board_size)

    return rows


def encode_position(position: list[str], visible_size: int) -> str:
    """Encode a 2D board position into a BTP hash string."""
    chars = ".BW"
    flat = ""
    for y in range(visible_size):
        for x in range(visible_size):
            if y < len(position) and x < len(position[y]):
                flat += position[y][x]
            else:
                flat += EMPTY

    result = ""
    for i in range(0, len(flat), 7):
        number = 0
        for c in range(7):
            if (i + c) < len(flat):
                number += chars.index(flat[i + c]) * (3 ** c)
        result += CHARSET[number % 59] + CHARSET[number // 59]

    return result


def board_to_ascii(position: list[str]) -> str:
    """Pretty-print a board position with spaces between cells."""
    return "\n".join(" ".join(row) for row in position)


def count_stones(position: list[str]) -> tuple[int, int]:
    """Count (black_stones, white_stones) on the board."""
    flat = "".join(position)
    return flat.count("B"), flat.count("W")
