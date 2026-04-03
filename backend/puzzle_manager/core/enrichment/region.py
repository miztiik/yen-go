"""
Board region detection for puzzle enrichment.

Detects which region of the board the puzzle occupies (YC property).
Used for UI cropping and puzzle categorization.

Internal detection uses 10 fine-grained values (TL, TR, BL, BR, T, B, L, R, C, FULL).
The SGF output uses 6 canonical values: TL, TR, BL, BR, C, E.
  - T/B/L/R (edge regions) -> E (edge)
  - FULL (whole board) -> C (center/full board, no zoom)
"""

from enum import Enum

from backend.puzzle_manager.core.primitives import Point

# --------------------------------------------------------------------------
# Constants: proportional threshold ratios (calibrated on 19x19)
# --------------------------------------------------------------------------
_CORNER_RATIO = 6 / 19   # ~31.6% -- lines from edge for corner zone
_EDGE_RATIO = 2 / 19     # ~10.5% -- lines from edge for center-vs-edge split

# Minimum thresholds for very small boards (<=5x5)
_MIN_CORNER_THRESHOLD = 2
_MIN_EDGE_THRESHOLD = 1


def _compute_corner_threshold(board_size: int) -> int:
    """Compute corner threshold proportional to board size.

    Returns at least _MIN_CORNER_THRESHOLD so tiny boards still have
    a valid corner zone.
    """
    return max(_MIN_CORNER_THRESHOLD, round(board_size * _CORNER_RATIO))


def _compute_edge_threshold(board_size: int) -> int:
    """Compute edge threshold proportional to board size.

    Returns at least _MIN_EDGE_THRESHOLD so tiny boards still have
    a valid center zone.
    """
    return max(_MIN_EDGE_THRESHOLD, round(board_size * _EDGE_RATIO))


class BoardRegion(Enum):
    """Board region classification (internal 10-value enum).

    Use ``region_to_sgf()`` to convert to canonical 6-value output
    for the YC SGF property.
    """

    TL = "TL"    # Top-left corner
    TR = "TR"    # Top-right corner
    BL = "BL"    # Bottom-left corner
    BR = "BR"    # Bottom-right corner
    T = "T"      # Top edge
    B = "B"      # Bottom edge
    L = "L"      # Left edge
    R = "R"      # Right edge
    C = "C"      # Center
    FULL = "FULL"    # Whole board


# Canonical 6-value YC vocabulary for SGF output.
# T/B/L/R -> E (edge, no quadrant zoom), FULL -> C (show full board).
_CANONICAL_YC: dict[BoardRegion, str] = {
    BoardRegion.TL: "TL",
    BoardRegion.TR: "TR",
    BoardRegion.BL: "BL",
    BoardRegion.BR: "BR",
    BoardRegion.T: "E",
    BoardRegion.B: "E",
    BoardRegion.L: "E",
    BoardRegion.R: "E",
    BoardRegion.C: "C",
    BoardRegion.FULL: "C",
}


# Transform-invariant region descriptions for hint generation.
# Board transforms (flip/rotate) change which corner/edge the stones
# appear in, so hints use tactical categories (corner/edge/center)
# rather than specific positions (top-left, bottom-right).
REGION_DESCRIPTIONS: dict[BoardRegion, str] = {
    BoardRegion.TL: "the corner",
    BoardRegion.TR: "the corner",
    BoardRegion.BL: "the corner",
    BoardRegion.BR: "the corner",
    BoardRegion.T: "the edge",
    BoardRegion.B: "the edge",
    BoardRegion.L: "the edge",
    BoardRegion.R: "the edge",
    BoardRegion.C: "the center",
    BoardRegion.FULL: "the whole board",
}


def detect_region(
    stones: list[Point],
    board_size: int = 19,
) -> BoardRegion:
    """Detect board region from stone positions.

    Thresholds are computed proportionally from ``board_size`` so the
    algorithm works correctly on any board from 4×4 to 25×25.

    Algorithm:
    1. Calculate bounding box of all stones
    2. Apply proportional thresholds to determine corner/edge/center/full

    Args:
        stones: List of stone positions (0-indexed).
        board_size: Board size (4–25).

    Returns:
        Detected BoardRegion.
    """
    if not stones:
        return BoardRegion.FULL

    # Proportional thresholds
    corner_threshold = _compute_corner_threshold(board_size)
    edge_threshold = _compute_edge_threshold(board_size)

    # Calculate bounding box
    min_x = min(p.x for p in stones)
    max_x = max(p.x for p in stones)
    min_y = min(p.y for p in stones)
    max_y = max(p.y for p in stones)

    # Calculate spread
    width = max_x - min_x + 1
    height = max_y - min_y + 1

    # Check if puzzle spans most of the board
    board_mid = board_size // 2
    span_threshold = board_size * 0.6  # 60% of board

    if width > span_threshold and height > span_threshold:
        return BoardRegion.FULL

    # Determine vertical position (for center fallback)
    is_top = max_y < board_mid - edge_threshold
    is_bottom = min_y > board_mid + edge_threshold
    is_vertical_center = not is_top and not is_bottom

    # Determine horizontal position (for center fallback)
    is_left = max_x < board_mid - edge_threshold
    is_right = min_x > board_mid + edge_threshold
    is_horizontal_center = not is_left and not is_right

    # Near-edge flags: is the bounding box within corner_threshold of an edge?
    near_top = min_y < corner_threshold
    near_bottom = max_y >= board_size - corner_threshold
    near_left = min_x < corner_threshold
    near_right = max_x >= board_size - corner_threshold

    # Corner detection
    if near_top and near_left and not near_right and not near_bottom:
        return BoardRegion.TL
    if near_top and near_right and not near_left and not near_bottom:
        return BoardRegion.TR
    if near_bottom and near_left and not near_right and not near_top:
        return BoardRegion.BL
    if near_bottom and near_right and not near_left and not near_top:
        return BoardRegion.BR

    # Edge detection
    if near_top and not near_bottom:
        return BoardRegion.T
    if near_bottom and not near_top:
        return BoardRegion.B
    if near_left and not near_right:
        return BoardRegion.L
    if near_right and not near_left:
        return BoardRegion.R

    # Center detection
    if is_vertical_center and is_horizontal_center:
        return BoardRegion.C

    # Default to FULL if can't determine
    return BoardRegion.FULL


def region_to_description(region: BoardRegion) -> str:
    """Convert region enum to human-readable description for hints.

    Args:
        region: Board region.

    Returns:
        Human-readable description.
    """
    return REGION_DESCRIPTIONS.get(region, "this area")


def region_to_sgf(region: BoardRegion) -> str:
    """Convert region enum to canonical YC SGF property value.

    Maps internal 10-value ``BoardRegion`` to 6 canonical output values:
    TL, TR, BL, BR, C, E.

    Args:
        region: Board region.

    Returns:
        Canonical SGF property value (e.g., "TL", "BR", "E", "C").
    """
    return _CANONICAL_YC.get(region, "C")
