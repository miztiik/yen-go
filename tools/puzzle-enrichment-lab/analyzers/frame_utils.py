"""Shared frame-geometry utilities (algorithm-agnostic).

Provides ``FrameRegions`` dataclass and ``compute_regions()`` helper used
by both the GP frame implementation and consumer code (enrich_single, etc.).

Extracted from ``tsumego_frame.py`` as part of the GP Frame Swap initiative
(20260313-1000-feature-gp-frame-swap).
"""

from __future__ import annotations

from dataclasses import dataclass

try:
    from models.position import Position
except ImportError:
    from ..models.position import Position


@dataclass(frozen=True)
class FrameRegions:
    """Computed regions for frame placement (algorithm-agnostic)."""

    puzzle_bbox: tuple[int, int, int, int]  # (min_x, min_y, max_x, max_y)
    puzzle_region: frozenset[tuple[int, int]]
    occupied: frozenset[tuple[int, int]]
    board_edge_sides: frozenset[str]


def detect_board_edge_sides(
    bbox: tuple[int, int, int, int],
    board_size: int,
    margin: int = 2,
) -> frozenset[str]:
    """Return which sides of the puzzle bbox are within *margin* of the board edge."""
    min_x, min_y, max_x, max_y = bbox
    sides: set[str] = set()
    if min_x <= margin:
        sides.add("left")
    if min_y <= margin:
        sides.add("top")
    if max_x >= board_size - 1 - margin:
        sides.add("right")
    if max_y >= board_size - 1 - margin:
        sides.add("bottom")
    return frozenset(sides)


def compute_regions(
    position: Position,
    *,
    margin: int = 2,
    board_size: int | None = None,
) -> FrameRegions:
    """Compute bounding box, puzzle region, occupied set, and edge sides.

    Args:
        position: Board position with puzzle stones.
        margin: Padding around bounding box (default 2).
        board_size: Override board size (default: ``position.board_size``).
    """
    bs = board_size if board_size is not None else position.board_size
    occupied = frozenset((s.x, s.y) for s in position.stones)

    if not occupied:
        return FrameRegions(
            puzzle_bbox=(0, 0, 0, 0),
            puzzle_region=frozenset(),
            occupied=occupied,
            board_edge_sides=frozenset(),
        )

    xs = [x for x, _ in occupied]
    ys = [y for _, y in occupied]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    bbox = (min_x, min_y, max_x, max_y)

    # Puzzle region = bbox + margin (clamped to board edges)
    p_min_x = max(0, min_x - margin)
    p_max_x = min(bs - 1, max_x + margin)
    p_min_y = max(0, min_y - margin)
    p_max_y = min(bs - 1, max_y + margin)
    puzzle_region = frozenset(
        (x, y)
        for x in range(p_min_x, p_max_x + 1)
        for y in range(p_min_y, p_max_y + 1)
    )

    edge_sides = detect_board_edge_sides(bbox, bs, margin)

    return FrameRegions(
        puzzle_bbox=bbox,
        puzzle_region=puzzle_region,
        occupied=occupied,
        board_edge_sides=edge_sides,
    )
