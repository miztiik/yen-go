"""Liberty-shortage detector — detect puzzles involving groups with few liberties.

Checks whether groups adjacent to the correct move have very few
liberties (≤3), indicating a capturing race or liberty-sensitive fight.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from models.detection import DetectionResult

if TYPE_CHECKING:
    from config import EnrichmentConfig
    from models.analysis_response import AnalysisResponse
    from models.position import Position
    from models.solve_result import SolutionNode

logger = logging.getLogger(__name__)

_NEIGHBORS = ((0, 1), (0, -1), (1, 0), (-1, 0))
_GTP_LETTERS = "ABCDEFGHJKLMNOPQRST"

# Maximum liberties to qualify as "shortage"
_MAX_LIBERTIES = 3


class LibertyShortageDetector:
    """Detects positions where adjacent groups have very few liberties."""

    def detect(
        self,
        position: Position,
        analysis: AnalysisResponse,
        solution_tree: SolutionNode | None,
        config: EnrichmentConfig,
    ) -> DetectionResult:
        top = analysis.top_move
        if not top:
            return _no_detection("No top move available")

        move_xy = _gtp_to_xy(top.move, position.board_size)
        if move_xy is None:
            return _no_detection(f"Cannot parse move {top.move}")

        board_size = position.board_size
        occupied = {(s.x, s.y): s.color.value for s in position.stones}
        mx, my = move_xy

        # Find all groups adjacent to the move point
        seen_roots: set[tuple[int, int]] = set()
        low_liberty_groups = 0
        min_libs_found = board_size * board_size  # large sentinel

        for dx, dy in _NEIGHBORS:
            nx, ny = mx + dx, my + dy
            if not (0 <= nx < board_size and 0 <= ny < board_size):
                continue
            if (nx, ny) not in occupied:
                continue
            # Flood-fill to find group
            group = _flood_fill((nx, ny), occupied, board_size)
            root = min(group)  # canonical representative
            if root in seen_roots:
                continue
            seen_roots.add(root)
            libs = _count_liberties(group, occupied, board_size)
            min_libs_found = min(min_libs_found, libs)
            if libs <= _MAX_LIBERTIES:
                low_liberty_groups += 1

        if low_liberty_groups >= 1:
            confidence = min(0.85, 0.50 + low_liberty_groups * 0.12)
            return DetectionResult(
                detected=True,
                confidence=confidence,
                tag_slug="liberty-shortage",
                evidence=(
                    f"{low_liberty_groups} group(s) near {top.move} with ≤{_MAX_LIBERTIES} "
                    f"liberties (min={min_libs_found})"
                ),
            )

        return _no_detection(
            f"No group near {top.move} with ≤{_MAX_LIBERTIES} liberties"
        )


def _flood_fill(
    start: tuple[int, int],
    occupied: dict[tuple[int, int], str],
    board_size: int,
) -> frozenset[tuple[int, int]]:
    """Flood-fill to find all stones in the same group."""
    color = occupied.get(start)
    if color is None:
        return frozenset()
    stack = [start]
    group: set[tuple[int, int]] = set()
    while stack:
        pt = stack.pop()
        if pt in group:
            continue
        group.add(pt)
        for dx, dy in _NEIGHBORS:
            nx, ny = pt[0] + dx, pt[1] + dy
            if 0 <= nx < board_size and 0 <= ny < board_size:
                if occupied.get((nx, ny)) == color and (nx, ny) not in group:
                    stack.append((nx, ny))
    return frozenset(group)


def _count_liberties(
    group: frozenset[tuple[int, int]],
    occupied: dict[tuple[int, int], str],
    board_size: int,
) -> int:
    """Count unique empty points adjacent to a group."""
    liberties: set[tuple[int, int]] = set()
    for gx, gy in group:
        for dx, dy in _NEIGHBORS:
            nx, ny = gx + dx, gy + dy
            if 0 <= nx < board_size and 0 <= ny < board_size:
                if (nx, ny) not in occupied:
                    liberties.add((nx, ny))
    return len(liberties)


def _gtp_to_xy(gtp: str, board_size: int) -> tuple[int, int] | None:
    """Convert GTP coord to (x, y) 0-indexed."""
    if not gtp or gtp.lower() == "pass":
        return None
    gtp = gtp.upper()
    if len(gtp) < 2 or gtp[0] not in _GTP_LETTERS:
        return None
    try:
        col = _GTP_LETTERS.index(gtp[0])
        row = int(gtp[1:])
    except (ValueError, IndexError):
        return None
    x = col
    y = board_size - row
    if x < 0 or x >= board_size or y < 0 or y >= board_size:
        return None
    return (x, y)


def _no_detection(evidence: str) -> DetectionResult:
    return DetectionResult(
        detected=False,
        confidence=0.0,
        tag_slug="liberty-shortage",
        evidence=evidence,
    )
