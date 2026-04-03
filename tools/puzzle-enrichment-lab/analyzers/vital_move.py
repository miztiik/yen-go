"""Vital move detector — identifies the decisive tesuji in the solution tree.

Walks the correct-move path beyond the first move to find the node where
the technique takes effect (branching decision point or ownership-change
inflection). Returns the node info with alias selection for comment placement.

GOV-V2-01: Suppressed when move_order != 'strict'.
GOV-V2-02: Alias at vital move, parent phrase at first move.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class VitalMoveResult:
    """Result of vital move detection."""
    move_index: int          # 0-based index in correct move path (beyond first move)
    sgf_coord: str           # SGF coordinate of the vital move (e.g. "cc")
    alias: str | None        # Alias name if dead-shapes/tesuji alias applies
    technique_phrase: str     # Phrase to use at this node (alias phrase or parent phrase)
    ownership_delta: float   # Ownership change at this move (if available)


def detect_vital_move(
    solution_tree: list[dict[str, Any]],
    move_order: str,
    technique_tags: list[str],
    alias: str | None = None,
    ownership_data: list[dict[str, Any]] | None = None,
    ownership_threshold: float = 0.3,
) -> VitalMoveResult | None:
    """Detect the vital (decisive) move in a puzzle's solution tree.

    Args:
        solution_tree: List of correct-move nodes, each with at minimum:
            - 'sgf_coord': SGF coordinate (e.g. 'cc')
            - 'correct_alternatives': int (number of alternative correct moves)
            Optional:
            - 'is_forced': bool (forced response with no alternatives)
        move_order: Puzzle move order: 'strict', 'flexible', or 'miai'.
        technique_tags: List of technique tag slugs for this puzzle.
        alias: Specific alias name if applicable (e.g. 'bent-four').
        ownership_data: Optional per-move ownership deltas from engine.
            Each entry: {'sgf_coord': str, 'ownership_delta': float}
        ownership_threshold: Minimum ownership delta to confirm vital point.

    Returns:
        VitalMoveResult if a vital move is found, None otherwise.
    """
    # GOV-V2-01: Only annotate vital moves for strict move order
    if move_order != "strict":
        return None

    # Need at least 2 moves (first move + vital move)
    if len(solution_tree) < 2:
        return None

    # Build ownership lookup
    ownership_map: dict[str, float] = {}
    if ownership_data:
        for entry in ownership_data:
            ownership_map[entry["sgf_coord"]] = entry.get("ownership_delta", 0.0)

    # Walk correct-move path beyond the first move
    for i, node in enumerate(solution_tree[1:], start=1):
        sgf_coord = node.get("sgf_coord", "")
        correct_alternatives = node.get("correct_alternatives", 0)
        is_forced = node.get("is_forced", False)

        # Skip forced intermediate moves (no decision)
        if is_forced and correct_alternatives == 0:
            continue

        # Condition 1: Branching decision point
        is_branch = correct_alternatives > 0

        # Condition 2: Ownership change confirmation
        delta = ownership_map.get(sgf_coord, 0.0)
        is_ownership_shift = abs(delta) > ownership_threshold

        if is_branch or is_ownership_shift:
            # GOV-V2-02: Use alias phrase at vital move if available
            technique_phrase = alias if alias else ""

            return VitalMoveResult(
                move_index=i,
                sgf_coord=sgf_coord,
                alias=alias,
                technique_phrase=technique_phrase,
                ownership_delta=delta,
            )

    return None
