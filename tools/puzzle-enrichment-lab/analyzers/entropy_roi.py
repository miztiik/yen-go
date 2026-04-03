"""Ownership entropy computation for puzzle region-of-interest detection.

Computes per-intersection entropy from KataGo ownership values to identify
the contested region of a tsumego puzzle. High-entropy intersections
indicate positions where ownership is uncertain — exactly where the
puzzle's action is.

Entropy formula: H(p) = -p·log₂(p) - (1-p)·log₂(1-p)
where p = (ownership + 1) / 2 maps KataGo ownership [-1,1] to [0,1].
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Default entropy threshold: intersections above this are "contested"
DEFAULT_ENTROPY_THRESHOLD = 0.5


@dataclass
class EntropyROI:
    """Contested region identified by ownership entropy analysis."""
    entropy_grid: list[list[float]]
    contested_region: list[str]  # GTP coordinates
    bounding_box: tuple[int, int, int, int]  # (min_row, min_col, max_row, max_col)
    mean_entropy: float


def _binary_entropy(p: float) -> float:
    """Compute binary entropy H(p) = -p·log₂(p) - (1-p)·log₂(1-p).

    Handles edge cases where p is 0 or 1 (entropy = 0).
    """
    if p <= 0.0 or p >= 1.0:
        return 0.0
    return -p * math.log2(p) - (1 - p) * math.log2(1 - p)


def compute_entropy_grid(
    ownership: list[float],
    board_size: int,
) -> list[list[float]]:
    """Convert flat KataGo ownership array to 2D entropy grid.

    Args:
        ownership: Flat array of ownership values [-1, 1], length board_size².
            KataGo convention: +1 = black owns, -1 = white owns, 0 = contested.
        board_size: Board dimension (e.g. 19).

    Returns:
        2D grid [row][col] of entropy values [0, 1].
    """
    grid: list[list[float]] = []
    for row in range(board_size):
        row_entropies: list[float] = []
        for col in range(board_size):
            idx = row * board_size + col
            if idx < len(ownership):
                own = ownership[idx]
                p = (own + 1.0) / 2.0  # Map [-1,1] to [0,1]
                p = max(0.0, min(1.0, p))  # Clamp
                row_entropies.append(_binary_entropy(p))
            else:
                row_entropies.append(0.0)
        grid.append(row_entropies)
    return grid


def compute_entropy_roi(
    ownership: list[float],
    board_size: int,
    threshold: float = DEFAULT_ENTROPY_THRESHOLD,
) -> EntropyROI:
    """Compute the region of interest from KataGo ownership entropy.

    Args:
        ownership: Flat ownership array from KataGo response.
        board_size: Board dimension.
        threshold: Entropy threshold for "contested" classification.

    Returns:
        EntropyROI with contested region coordinates and bounding box.
    """
    grid = compute_entropy_grid(ownership, board_size)

    letters = "ABCDEFGHJKLMNOPQRST"
    contested: list[str] = []
    contested_coords: list[tuple[int, int]] = []
    total_entropy = 0.0
    count = 0

    for row in range(board_size):
        for col in range(board_size):
            e = grid[row][col]
            total_entropy += e
            count += 1
            if e >= threshold:
                if col >= len(letters):
                    continue
                gtp_col = letters[col]
                gtp_row = board_size - row
                contested.append(f"{gtp_col}{gtp_row}")
                contested_coords.append((row, col))

    mean_entropy = total_entropy / count if count > 0 else 0.0

    if contested_coords:
        min_row = min(r for r, _ in contested_coords)
        min_col = min(c for _, c in contested_coords)
        max_row = max(r for r, _ in contested_coords)
        max_col = max(c for _, c in contested_coords)
        bbox = (min_row, min_col, max_row, max_col)
    else:
        bbox = (0, 0, board_size - 1, board_size - 1)

    logger.info(
        "entropy_roi: contested=%d/%d intersections, mean_entropy=%.3f, "
        "bbox=(%d,%d,%d,%d), threshold=%.2f",
        len(contested), board_size * board_size, mean_entropy,
        bbox[0], bbox[1], bbox[2], bbox[3], threshold,
    )

    return EntropyROI(
        entropy_grid=grid,
        contested_region=contested,
        bounding_box=bbox,
        mean_entropy=mean_entropy,
    )


def get_roi_allow_moves(
    roi: EntropyROI,
    board_size: int,
    margin: int = 1,
    occupied: frozenset[tuple[int, int]] | None = None,
) -> list[str]:
    """Expand ROI bounding box by margin and return empty GTP coordinates.

    Used as `allowMoves` for KataGo queries to focus analysis on the
    contested puzzle region.

    Args:
        roi: Computed entropy ROI.
        board_size: Board dimension.
        margin: Extra rows/cols around ROI bounding box.
        occupied: Set of (col, row) tuples for occupied intersections
            to exclude. KataGo silently ignores occupied coords, but
            filtering them avoids wasted policy mass.

    Returns:
        List of GTP coordinates within the expanded ROI (empty points only).
    """
    min_row, min_col, max_row, max_col = roi.bounding_box
    min_row = max(0, min_row - margin)
    min_col = max(0, min_col - margin)
    max_row = min(board_size - 1, max_row + margin)
    max_col = min(board_size - 1, max_col + margin)

    letters = "ABCDEFGHJKLMNOPQRST"
    moves: list[str] = []
    for row in range(min_row, max_row + 1):
        for col in range(min_col, max_col + 1):
            if occupied and (col, row) in occupied:
                continue
            gtp_col = letters[col] if col < len(letters) else "A"
            gtp_row = board_size - row
            moves.append(f"{gtp_col}{gtp_row}")

    return moves


def validate_frame_quality(
    ownership: list[float],
    board_size: int,
    variance_threshold: float = 0.15,
) -> tuple[bool, float]:
    """Validate frame quality by checking ownership variance.

    If ownership variance > threshold, frame may not have correctly
    identified the attacker — too much uncertainty remains.

    Args:
        ownership: Flat ownership array from KataGo (post-frame analysis).
        board_size: Board dimension.
        variance_threshold: Max acceptable ownership variance.

    Returns:
        (is_valid, variance) — True if frame quality is acceptable.
    """
    n = board_size * board_size
    values = ownership[:n] if len(ownership) >= n else ownership
    if not values:
        return True, 0.0

    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / len(values)

    if variance > variance_threshold:
        logger.info(
            "frame_quality_check: FAILED — ownership variance %.4f > threshold %.4f",
            variance, variance_threshold,
        )
        return False, variance

    return True, variance
