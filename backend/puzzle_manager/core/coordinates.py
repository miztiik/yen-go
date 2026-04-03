"""
SGF coordinate conversion utilities.

SGF uses letter-based coordinates (a-s for 1-19).
"""

from backend.puzzle_manager.core.primitives import Point


def sgf_to_point(sgf: str) -> Point:
    """Convert SGF coordinate string to Point.

    Args:
        sgf: Two-character SGF coordinate (e.g., 'ab', 'cd').

    Returns:
        Point with 0-indexed coordinates.

    Raises:
        ValueError: If SGF coordinate is invalid.
    """
    return Point.from_sgf(sgf)


def point_to_sgf(point: Point) -> str:
    """Convert Point to SGF coordinate string.

    Args:
        point: Point with 0-indexed coordinates.

    Returns:
        Two-character SGF coordinate string.
    """
    return point.to_sgf()


def sgf_coord_to_tuple(sgf: str) -> tuple[int, int]:
    """Convert SGF coordinate to (x, y) tuple.

    Args:
        sgf: Two-character SGF coordinate.

    Returns:
        Tuple of (x, y) 0-indexed coordinates.
    """
    point = sgf_to_point(sgf)
    return (point.x, point.y)


def tuple_to_sgf_coord(x: int, y: int) -> str:
    """Convert (x, y) tuple to SGF coordinate.

    Args:
        x: Column (0-indexed).
        y: Row (0-indexed).

    Returns:
        Two-character SGF coordinate string.
    """
    return Point(x, y).to_sgf()


def is_valid_sgf_coord(sgf: str) -> bool:
    """Check if a string is a valid SGF coordinate.

    Args:
        sgf: String to check.

    Returns:
        True if valid SGF coordinate (a-s for each character).
    """
    if len(sgf) != 2:
        return False
    return all(ord("a") <= ord(c) <= ord("s") for c in sgf)


def is_pass_move(sgf: str) -> bool:
    """Check if SGF coordinate represents a pass move.

    Args:
        sgf: SGF coordinate string.

    Returns:
        True if this is a pass (empty string or 'tt').
    """
    return sgf == "" or sgf == "tt"
