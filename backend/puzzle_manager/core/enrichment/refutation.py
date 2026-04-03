"""
Refutation move extraction for puzzle enrichment.

Extracts and formats wrong-move refutation branches from the solution tree
for the YR property.

YR Format:
----------
Comma-separated SGF coordinates of common wrong first moves:
  YR[cd,de,ef]

Purpose:
--------
Refutation moves allow the frontend to show "what happens if you play here"
when the user makes a common mistake. This is pedagogically valuable because:
1. Players learn from mistakes, not just correct moves
2. Understanding WHY a move is wrong deepens understanding
3. Reduces frustration by showing the refutation path
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from backend.puzzle_manager.core.primitives import Point

if TYPE_CHECKING:
    from backend.puzzle_manager.core.sgf_parser import SolutionNode

logger = logging.getLogger("enrichment.refutation")


def extract_refutations(
    solution_tree: SolutionNode,
    max_refutations: int = 5,
) -> list[Point]:
    """Extract refutation (wrong) moves from solution tree.

    Finds the first-level wrong moves (not marked as correct) that have
    refutation continuations showing why they're wrong.

    Args:
        solution_tree: Root of solution tree.
        max_refutations: Maximum number of refutations to extract.

    Returns:
        List of wrong move Points (first moves that are incorrect).
    """
    refutations: list[Point] = []

    for child in solution_tree.children:
        if len(refutations) >= max_refutations:
            break

        # Check if this is a wrong move
        if not child.is_correct and child.move:
            refutations.append(child.move)
            logger.debug(f"Found refutation at {child.move}")

    return refutations


def format_refutations(refutations: list[Point]) -> str | None:
    """Format refutation moves as comma-separated SGF coordinates.

    Args:
        refutations: List of refutation move Points.

    Returns:
        Comma-separated SGF coordinate string, or None if empty.

    Example:
        [Point(2,3), Point(4,5)] -> "cd,ef"
    """
    if not refutations:
        return None

    sgf_coords = [point_to_sgf(point) for point in refutations]
    return ",".join(sgf_coords)


def point_to_sgf(point: Point) -> str:
    """Convert Point to SGF coordinate.

    SGF uses 'a'-'s' (or beyond for large boards) for 0-18.

    Args:
        point: Board point.

    Returns:
        SGF coordinate string (e.g., "cd" for Point(2,3)).
    """
    return chr(ord("a") + point.x) + chr(ord("a") + point.y)


def sgf_to_point(sgf_coord: str) -> Point:
    """Convert SGF coordinate to Point.

    Args:
        sgf_coord: SGF coordinate string (e.g., "cd").

    Returns:
        Point corresponding to the coordinate.

    Raises:
        ValueError: If coordinate is invalid.
    """
    if len(sgf_coord) != 2:
        raise ValueError(f"Invalid SGF coordinate: {sgf_coord}")

    x = ord(sgf_coord[0]) - ord("a")
    y = ord(sgf_coord[1]) - ord("a")

    return Point(x, y)
