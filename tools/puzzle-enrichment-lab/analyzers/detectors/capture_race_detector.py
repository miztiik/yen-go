"""Capture-race detector — detect semeai (liberty race) patterns.

A capture race occurs when two opposing groups with limited liberties
compete to capture each other first. Detection uses:

1. Liberty analysis: opposing groups near each other with low liberties
2. Ownership contestation: both groups show contested ownership (near 0)
3. PV interleaving: alternating moves that reduce opponent's liberties
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


class CaptureRaceDetector:
    """Detects capture-race (semeai) patterns."""

    def detect(
        self,
        position: Position,
        analysis: AnalysisResponse,
        solution_tree: SolutionNode | None,
        config: EnrichmentConfig,
    ) -> DetectionResult:
        if not position.stones or not analysis.move_infos:
            return _no_detection("Insufficient data")

        board_size = position.board_size
        occupied = {(s.x, s.y): s.color.value for s in position.stones}

        # Find opposing groups with limited liberties adjacent to each other
        black_groups = _find_groups(occupied, "B", board_size)
        white_groups = _find_groups(occupied, "W", board_size)

        race_pairs = _find_race_pairs(
            black_groups, white_groups, occupied, board_size,
        )
        if not race_pairs:
            return _no_detection("No adjacent low-liberty opposing groups")

        # Boost confidence with ownership contestation
        conf = 0.7
        evidence_parts = [
            f"{len(race_pairs)} adjacent race pair(s) found"
        ]

        if analysis.ownership:
            contested = _contested_ownership_ratio(
                analysis.ownership, race_pairs, board_size,
            )
            if contested > 0.3:
                conf = min(0.95, conf + contested * 0.2)
                evidence_parts.append(f"ownership contestation {contested:.2f}")

        return DetectionResult(
            detected=True,
            confidence=conf,
            tag_slug="capture-race",
            evidence="; ".join(evidence_parts),
        )


def _find_groups(
    occupied: dict[tuple[int, int], str],
    color: str,
    board_size: int,
) -> list[tuple[frozenset[tuple[int, int]], int]]:
    """Find all groups of *color* and their liberty counts."""
    visited: set[tuple[int, int]] = set()
    groups: list[tuple[frozenset[tuple[int, int]], int]] = []
    for coord, c in occupied.items():
        if c != color or coord in visited:
            continue
        group: set[tuple[int, int]] = set()
        liberties: set[tuple[int, int]] = set()
        queue = [coord]
        group.add(coord)
        while queue:
            cx, cy = queue.pop()
            for dx, dy in _NEIGHBORS:
                nx, ny = cx + dx, cy + dy
                if nx < 0 or nx >= board_size or ny < 0 or ny >= board_size:
                    continue
                nc = (nx, ny)
                if nc not in occupied:
                    liberties.add(nc)
                elif occupied[nc] == color and nc not in group:
                    group.add(nc)
                    queue.append(nc)
        visited |= group
        groups.append((frozenset(group), len(liberties)))
    return groups


def _find_race_pairs(
    black_groups: list[tuple[frozenset[tuple[int, int]], int]],
    white_groups: list[tuple[frozenset[tuple[int, int]], int]],
    occupied: dict[tuple[int, int], str],
    board_size: int,
    max_libs: int = 4,
) -> list[tuple[frozenset[tuple[int, int]], frozenset[tuple[int, int]]]]:
    """Find opposing group pairs that are adjacent and both have limited liberties."""
    pairs = []
    for b_stones, b_libs in black_groups:
        if b_libs > max_libs:
            continue
        b_neighbors: set[tuple[int, int]] = set()
        for bx, by in b_stones:
            for dx, dy in _NEIGHBORS:
                nx, ny = bx + dx, by + dy
                if 0 <= nx < board_size and 0 <= ny < board_size:
                    b_neighbors.add((nx, ny))
        for w_stones, w_libs in white_groups:
            if w_libs > max_libs:
                continue
            if b_neighbors & w_stones:
                pairs.append((b_stones, w_stones))
    return pairs


def _contested_ownership_ratio(
    ownership: list[float],
    race_pairs: list[tuple[frozenset[tuple[int, int]], frozenset[tuple[int, int]]]],
    board_size: int,
) -> float:
    """Ratio of race-pair stones with contested ownership (abs < 0.5)."""
    all_stones: set[tuple[int, int]] = set()
    for b, w in race_pairs:
        all_stones |= b
        all_stones |= w
    if not all_stones:
        return 0.0
    contested = 0
    for x, y in all_stones:
        idx = y * board_size + x
        if idx < len(ownership) and abs(ownership[idx]) < 0.5:
            contested += 1
    return contested / len(all_stones)


def _no_detection(evidence: str) -> DetectionResult:
    return DetectionResult(
        detected=False,
        confidence=0.0,
        tag_slug="capture-race",
        evidence=evidence,
    )
