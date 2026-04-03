"""Escape detector — detect moves that save a weak group.

An escape move saves a group in danger by increasing its liberties,
connecting it to a safe group, or running it out. Detection checks:

1. Player has a group near the move with few liberties (danger)
2. After the move, that group gains liberties or connects to safety
3. Config thresholds from technique_detection.escape
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


class EscapeDetector:
    """Detects escape (saving a weak group) patterns."""

    def detect(
        self,
        position: Position,
        analysis: AnalysisResponse,
        solution_tree: SolutionNode | None,
        config: EnrichmentConfig,
    ) -> DetectionResult:
        tc = config.technique_detection
        min_gain = tc.escape.min_liberty_gain if tc else 2
        max_init = tc.escape.max_initial_liberties if tc else 2
        wr_thresh = tc.escape.winrate_threshold if tc else 0.7

        top = analysis.top_move
        if not top:
            return _no_detection("No top move available")

        move_xy = _gtp_to_xy(top.move, position.board_size)
        if move_xy is None:
            return _no_detection(f"Cannot parse move {top.move}")

        if top.winrate < wr_thresh:
            return _no_detection(
                f"Winrate {top.winrate:.3f} < threshold {wr_thresh}"
            )

        board_size = position.board_size
        player_color = position.player_to_move.value
        occupied_before = {(s.x, s.y): s.color.value for s in position.stones}

        # Find player groups adjacent to the move point with few liberties
        adj_groups = _adjacent_friendly_groups(
            move_xy, player_color, occupied_before, board_size,
        )

        weak_groups = [
            (g, libs) for g, libs in adj_groups if libs <= max_init
        ]
        if not weak_groups:
            return _no_detection(
                f"No weak friendly group (≤{max_init} libs) near {top.move}"
            )

        # Simulate placing the stone and recount liberties
        occupied_after = dict(occupied_before)
        occupied_after[move_xy] = player_color

        for group_stones, libs_before in weak_groups:
            # The group now includes the new stone; recount
            expanded = group_stones | {move_xy}
            libs_after = _count_group_liberties(expanded, occupied_after, board_size)
            gain = libs_after - libs_before
            if gain >= min_gain:
                confidence = min(0.90, 0.65 + gain * 0.05 + top.winrate * 0.1)
                return DetectionResult(
                    detected=True,
                    confidence=confidence,
                    tag_slug="escape",
                    evidence=(
                        f"Escape: {top.move} gains {gain} liberties "
                        f"({libs_before}→{libs_after}), winrate={top.winrate:.3f}"
                    ),
                )

        return _no_detection(
            f"No sufficient liberty gain (need +{min_gain}) near {top.move}"
        )


def _adjacent_friendly_groups(
    point: tuple[int, int],
    color: str,
    occupied: dict[tuple[int, int], str],
    board_size: int,
) -> list[tuple[frozenset[tuple[int, int]], int]]:
    """Find distinct friendly groups adjacent to *point* with their liberty counts."""
    groups: list[tuple[frozenset[tuple[int, int]], int]] = []
    seen: set[tuple[int, int]] = set()
    px, py = point
    for dx, dy in _NEIGHBORS:
        nx, ny = px + dx, py + dy
        if nx < 0 or nx >= board_size or ny < 0 or ny >= board_size:
            continue
        nc = (nx, ny)
        if nc in seen or occupied.get(nc) != color:
            continue
        group: set[tuple[int, int]] = set()
        queue = [nc]
        group.add(nc)
        while queue:
            cx, cy = queue.pop()
            for ddx, ddy in _NEIGHBORS:
                nnx, nny = cx + ddx, cy + ddy
                nn = (nnx, nny)
                if (
                    0 <= nnx < board_size
                    and 0 <= nny < board_size
                    and nn not in group
                    and occupied.get(nn) == color
                ):
                    group.add(nn)
                    queue.append(nn)
        seen |= group
        libs = _count_group_liberties(frozenset(group), occupied, board_size)
        groups.append((frozenset(group), libs))
    return groups


def _count_group_liberties(
    group: frozenset[tuple[int, int]],
    occupied: dict[tuple[int, int], str],
    board_size: int,
) -> int:
    """Count unique liberties of a group."""
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
        tag_slug="escape",
        evidence=evidence,
    )
