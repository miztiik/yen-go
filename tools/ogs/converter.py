"""
OGS coordinate and data conversion utilities.

Provides conversion functions for:
- OGS (x,y) coordinates to SGF letter format
- OGS initial_state strings to SGF AB[]/AW[] properties
- OGS move_tree to SGF variation format
- Japanese text translation in move comments
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from .models import OGSInitialState, OGSMark, OGSMoveNode
from .translator import get_translator

logger = logging.getLogger("ogs.converter")


# Maximum recursion depth for move tree conversion
MAX_TREE_DEPTH = 50

# Global translator instance (lazy initialized)
_translator = None


def _get_translator():
    """Get or initialize the Japanese translator."""
    global _translator
    if _translator is None:
        _translator = get_translator()
    return _translator


class ConversionError(Exception):
    """Raised when coordinate/data conversion fails."""
    pass


@dataclass
class ConversionResult:
    """Result of converting OGS puzzle to SGF components."""

    success: bool
    sgf_content: str | None = None
    error: str | None = None
    warnings: list[str] = field(default_factory=list)


def ogs_xy_to_sgf(x: int, y: int) -> str:
    """Convert OGS (x,y) coordinates to SGF letter pair.

    OGS uses 0-indexed integers, SGF uses letters 'a'-'s'.

    Args:
        x: Column (0-indexed, 0=left)
        y: Row (0-indexed, 0=top)

    Returns:
        Two-letter SGF coordinate (e.g., "ea" for x=4, y=0)

    Raises:
        ConversionError: If coordinates are out of bounds
    """
    if not (0 <= x <= 18 and 0 <= y <= 18):
        raise ConversionError(f"Coordinates out of bounds: ({x}, {y})")

    return chr(ord('a') + x) + chr(ord('a') + y)


def parse_initial_state(state: OGSInitialState) -> tuple[list[str], list[str]]:
    """Parse OGS initial_state into separate black and white stone lists.

    OGS stores stone positions as concatenated 2-letter pairs.
    Example: "bchcdccc" → ["bc", "hc", "dc", "cc"]

    Args:
        state: OGSInitialState with white and black position strings

    Returns:
        Tuple of (black_coords, white_coords) as lists of SGF coordinates

    Raises:
        ConversionError: If string has odd length (invalid pairs)
    """
    def split_pairs(s: str) -> list[str]:
        if len(s) % 2 != 0:
            raise ConversionError(f"Invalid state string length: {len(s)} (must be even)")
        return [s[i:i+2] for i in range(0, len(s), 2)] if s else []

    black_coords = split_pairs(state.black)
    white_coords = split_pairs(state.white)

    return black_coords, white_coords


def initial_state_to_sgf(state: OGSInitialState) -> str:
    """Convert OGS initial_state to SGF AB[]/AW[] properties.

    Args:
        state: OGSInitialState with stone positions

    Returns:
        SGF properties string (e.g., "AB[aa][bb]AW[cc][dd]")

    Raises:
        ConversionError: If state strings are invalid
    """
    black_coords, white_coords = parse_initial_state(state)

    parts = []

    if black_coords:
        coords_str = "".join(f"[{c}]" for c in black_coords)
        parts.append(f"AB{coords_str}")

    if white_coords:
        coords_str = "".join(f"[{c}]" for c in white_coords)
        parts.append(f"AW{coords_str}")

    return "\n".join(parts)


def escape_sgf_text(text: str) -> str:
    """Escape special characters for SGF text properties.

    SGF requires escaping of: ] \\ :

    Args:
        text: Raw text to escape

    Returns:
        Escaped text safe for SGF properties
    """
    if not text:
        return ""

    # Order matters: escape backslash first
    result = text.replace("\\", "\\\\")
    result = result.replace("]", "\\]")
    result = result.replace(":", "\\:")

    return result


def marks_to_sgf(marks: list[OGSMark]) -> str:
    """Convert OGS board markup annotations to SGF properties.

    Maps OGS mark types to standard SGF markup properties:
      - letter: "X" → LB[coord:X]  (label)
      - triangle: true → TR[coord]
      - square: true   → SQ[coord]
      - circle: true   → CR[coord]
      - cross: true    → MA[coord]

    Multiple marks of the same type are combined into a single property
    with multiple values (e.g., ``LB[ab:1][cd:2]``).

    Args:
        marks: List of OGSMark objects from the move tree node.

    Returns:
        SGF property string, e.g. ``LB[ab:1][cd:A]TR[ef]SQ[gh]``.
        Empty string if no marks.
    """
    if not marks:
        return ""

    labels: list[str] = []       # LB[coord:text]
    triangles: list[str] = []    # TR[coord]
    squares: list[str] = []      # SQ[coord]
    circles: list[str] = []      # CR[coord]
    crosses: list[str] = []      # MA[coord]

    for mark in marks:
        try:
            coord = ogs_xy_to_sgf(mark.x, mark.y)
        except ConversionError:
            logger.warning(f"Invalid mark coordinates ({mark.x}, {mark.y}), skipping")
            continue

        m = mark.marks
        if "letter" in m:
            labels.append(f"[{coord}:{m['letter']}]")
        if m.get("triangle"):
            triangles.append(f"[{coord}]")
        if m.get("square"):
            squares.append(f"[{coord}]")
        if m.get("circle"):
            circles.append(f"[{coord}]")
        if m.get("cross"):
            crosses.append(f"[{coord}]")

    parts: list[str] = []
    if labels:
        parts.append(f"LB{''.join(labels)}")
    if triangles:
        parts.append(f"TR{''.join(triangles)}")
    if squares:
        parts.append(f"SQ{''.join(squares)}")
    if circles:
        parts.append(f"CR{''.join(circles)}")
    if crosses:
        parts.append(f"MA{''.join(crosses)}")

    return "".join(parts)


def move_tree_to_sgf(
    tree: OGSMoveNode,
    player: str = "B",
    depth: int = 0,
) -> str:
    """Convert OGS move_tree to SGF variation format recursively.

    Args:
        tree: OGS move tree node
        player: Current player ("B" or "W")
        depth: Current recursion depth (for safety limit)

    Returns:
        SGF-formatted move string with variations

    Raises:
        ConversionError: If tree structure is invalid

    Note:
        Root node (x=-1, y=-1) is skipped; only branches are processed.
        Variations are wrapped in parentheses per SGF spec.
    """
    if depth > MAX_TREE_DEPTH:
        logger.warning(f"Move tree depth {depth} exceeds limit {MAX_TREE_DEPTH}, truncating")
        return ""

    # Root node has x=-1, y=-1 - skip and process branches directly
    if tree.x == -1 and tree.y == -1:
        branches = tree.branches
        if not branches:
            return ""

        # Root-level marks (board annotations visible before first move)
        root_marks = marks_to_sgf(tree.marks) if tree.marks else ""

        if len(branches) == 1:
            content = move_tree_to_sgf(branches[0], player, depth + 1)
            return root_marks + content
        else:
            # Multiple variations at root level
            variations = []
            for branch in branches:
                var_content = move_tree_to_sgf(branch, player, depth + 1)
                if var_content:
                    variations.append(f"({var_content})")
            return root_marks + "".join(variations)

    # Regular move node
    try:
        coord = ogs_xy_to_sgf(tree.x, tree.y)
    except ConversionError:
        logger.warning(f"Invalid coordinates ({tree.x}, {tree.y}), skipping node")
        return ""

    move = f";{player}[{coord}]"

    # Build comment from annotations
    comments = []
    if tree.correct_answer:
        comments.append("Correct!")
    elif tree.wrong_answer:
        comments.append("Wrong")
    if tree.text:
        # Translate Japanese text in move comments
        result = _get_translator().translate(tree.text)
        comments.append(escape_sgf_text(result.translated))

    if comments:
        move += f"C[{' '.join(comments)}]"

    # Emit board markup annotations (LB, TR, SQ, CR, MA)
    mark_props = marks_to_sgf(tree.marks) if tree.marks else ""
    if mark_props:
        move += mark_props

    # Process branches
    next_player = "W" if player == "B" else "B"
    branches = tree.branches

    if not branches:
        return move
    elif len(branches) == 1:
        # Single continuation - inline
        return move + move_tree_to_sgf(branches[0], next_player, depth + 1)
    else:
        # Multiple variations - wrap each in parentheses
        variations = []
        for branch in branches:
            var_content = move_tree_to_sgf(branch, next_player, depth + 1)
            if var_content:
                variations.append(f"({var_content})")
        return move + "".join(variations)


def has_correct_answer_in_tree(node: OGSMoveNode | dict, depth: int = 0) -> bool:
    """Check if move tree contains any correct_answer marker.

    This is the RELIABLE way to check if a puzzle has a solution,
    since the OGS API 'has_solution' field is unreliable.

    Args:
        node: Move tree node (OGSMoveNode or raw dict)
        depth: Current recursion depth

    Returns:
        True if any node in the tree has correct_answer=True
    """
    if depth > MAX_TREE_DEPTH:
        return False

    # Handle both Pydantic model and raw dict
    if isinstance(node, dict):
        if node.get("correct_answer", False):
            return True
        for branch in node.get("branches", []):
            if has_correct_answer_in_tree(branch, depth + 1):
                return True
    else:
        if node.correct_answer:
            return True
        for branch in node.branches:
            if has_correct_answer_in_tree(branch, depth + 1):
                return True

    return False


def get_move_tree_depth(node: dict | OGSMoveNode, current_depth: int = 0) -> int:
    """Calculate the maximum depth of a move tree.

    Args:
        node: Move tree node
        current_depth: Current recursion depth

    Returns:
        Maximum depth found in the tree
    """
    if isinstance(node, dict):
        branches = node.get("branches", [])
    else:
        branches = node.branches

    if not branches:
        return current_depth

    max_depth = current_depth
    for branch in branches:
        depth = get_move_tree_depth(branch, current_depth + 1)
        if depth > max_depth:
            max_depth = depth

    return max_depth
