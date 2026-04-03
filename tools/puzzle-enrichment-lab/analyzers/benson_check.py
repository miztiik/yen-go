"""Benson's unconditional life and interior-point death detection.

Pre-query terminal detection gates for tsumego solution tree building.
These algorithms identify board positions where the outcome is already
determined, allowing the solver to skip expensive KataGo queries.

Gate G1: Benson's unconditional life — contest group is provably alive.
Gate G2: Interior-point two-eye exit — defender cannot form two eyes.

References:
- Benson, D.B. (1976) "Life in the game of Go"
- Integration: solve_position.py → _build_tree_recursive()
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def _find_connected_groups(
    stones: dict[tuple[int, int], str],
    board_size: int,
) -> list[tuple[str, frozenset[tuple[int, int]]]]:
    """Find all connected groups of stones on the board.

    Returns list of (color, frozenset_of_positions) for each group.
    """
    visited: set[tuple[int, int]] = set()
    groups: list[tuple[str, frozenset[tuple[int, int]]]] = []

    for pos, color in stones.items():
        if pos in visited:
            continue
        # Flood fill to find the connected group
        group: set[tuple[int, int]] = set()
        stack = [pos]
        while stack:
            p = stack.pop()
            if p in group:
                continue
            if p in stones and stones[p] == color:
                group.add(p)
                r, c = p
                for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < board_size and 0 <= nc < board_size:
                        if (nr, nc) not in group:
                            stack.append((nr, nc))
        visited.update(group)
        groups.append((color, frozenset(group)))

    return groups


def _find_empty_regions(
    stones: dict[tuple[int, int], str],
    board_size: int,
) -> list[frozenset[tuple[int, int]]]:
    """Find all connected empty regions on the board."""
    occupied = set(stones.keys())
    visited: set[tuple[int, int]] = set()
    regions: list[frozenset[tuple[int, int]]] = []

    for r in range(board_size):
        for c in range(board_size):
            pos = (r, c)
            if pos in occupied or pos in visited:
                continue
            # Flood fill empty region
            region: set[tuple[int, int]] = set()
            stack = [pos]
            while stack:
                p = stack.pop()
                if p in region:
                    continue
                pr, pc = p
                if 0 <= pr < board_size and 0 <= pc < board_size and p not in occupied:
                    region.add(p)
                    for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                        nr, nc = pr + dr, pc + dc
                        if (nr, nc) not in region:
                            stack.append((nr, nc))
            visited.update(region)
            if region:
                regions.append(frozenset(region))

    return regions


def _region_neighbors(
    region: frozenset[tuple[int, int]],
    board_size: int,
) -> set[tuple[int, int]]:
    """Find all positions adjacent to a region that are not in the region."""
    neighbors: set[tuple[int, int]] = set()
    for r, c in region:
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < board_size and 0 <= nc < board_size:
                if (nr, nc) not in region:
                    neighbors.add((nr, nc))
    return neighbors


def find_unconditionally_alive_groups(
    stones: dict[tuple[int, int], str],
    board_size: int = 19,
) -> set[frozenset[tuple[int, int]]]:
    """Return all unconditionally alive groups on the board.

    Implements Benson's algorithm (1976): a group is unconditionally alive
    if it has at least 2 "vital regions" — empty connected regions whose
    every adjacent stone belongs to that group.

    Each returned element is a frozenset of (row, col) coordinates
    representing one alive group. The caller must check whether the
    contest group is among the returned set.

    Ko-dependent groups are inherently NOT unconditionally alive — they
    won't have 2 unconditionally vital regions because the ko fight
    means the region is not fully enclosed.

    Seki groups are NOT classified as alive (seki is not unconditional life).

    Args:
        stones: Board state as {(row, col): "B"|"W"}.
        board_size: Board dimension.

    Returns:
        Set of frozensets, each being the positions of an unconditionally
        alive group.
    """
    if not stones:
        return set()

    groups = _find_connected_groups(stones, board_size)
    empty_regions = _find_empty_regions(stones, board_size)

    # For each empty region, determine which groups are adjacent
    # A region is "vital" to a group if ALL adjacent stones belong to that group
    # (i.e., the region is fully enclosed by one group)

    # Build group membership lookup: position -> group index
    pos_to_group: dict[tuple[int, int], int] = {}
    for idx, (_color, group_positions) in enumerate(groups):
        for pos in group_positions:
            pos_to_group[pos] = idx

    # Iterative Benson's algorithm
    # Start with all groups as potentially alive
    alive_candidates: set[int] = set(range(len(groups)))

    changed = True
    while changed:
        changed = False
        for group_idx in list(alive_candidates):
            # Count vital regions for this group
            vital_count = 0
            for region in empty_regions:
                neighbors = _region_neighbors(region, board_size)
                # Check that ALL neighbors of this region are stones
                # belonging to this specific group AND the group is still alive
                stone_neighbors = {n for n in neighbors if n in stones}
                if not stone_neighbors:
                    continue
                # Every stone neighbor must belong to this group
                all_belong = all(
                    pos_to_group.get(n) == group_idx
                    for n in stone_neighbors
                )
                if all_belong:
                    vital_count += 1

            if vital_count < 2:
                # Group is not unconditionally alive — remove from candidates
                if group_idx in alive_candidates:
                    alive_candidates.discard(group_idx)
                    changed = True

    result: set[frozenset[tuple[int, int]]] = set()
    for idx in alive_candidates:
        _, group_positions = groups[idx]
        result.add(group_positions)

    if result:
        logger.debug(
            "Benson: found %d unconditionally alive group(s) on %dx%d board",
            len(result), board_size, board_size,
        )

    return result


def check_interior_point_death(
    stones: dict[tuple[int, int], str],
    target_color: str,
    puzzle_region: frozenset[tuple[int, int]],
    board_size: int = 19,
) -> bool:
    """Return True if target_color cannot form two eyes within puzzle_region.

    Checks whether the defender (target_color) has ≤ 2 empty interior points
    within the puzzle_region, and no two are orthogonally adjacent. If so,
    the defender cannot form two eyes and the attacker wins.

    Args:
        stones: Board state as {(row, col): "B"|"W"}.
        target_color: "B" or "W" (defender).
        puzzle_region: Set of (row, col) positions from compute_regions().
        board_size: Board dimension.

    Returns:
        True if defender cannot form two eyes (attacker wins).
        False if uncertain (fall through to KataGo).
    """
    if not puzzle_region:
        return False

    # Find empty cells within puzzle_region
    empty_interior: list[tuple[int, int]] = []
    for pos in puzzle_region:
        if pos not in stones:
            empty_interior.append(pos)

    # More than 2 empty points → uncertain
    if len(empty_interior) > 2:
        return False

    # 0 empty points → dead (no room)
    if len(empty_interior) == 0:
        logger.debug(
            "Interior-point death: 0 empty interior points for %s",
            target_color,
        )
        return True

    # 1 empty point → can only form 1 eye at most
    if len(empty_interior) == 1:
        logger.debug(
            "Interior-point death: 1 empty interior point for %s at %s",
            target_color, empty_interior[0],
        )
        return True

    # 2 empty points → dead only if NOT orthogonally adjacent
    # (adjacent empties can potentially be combined into one eye space)
    p1, p2 = empty_interior
    adjacent = abs(p1[0] - p2[0]) + abs(p1[1] - p2[1]) == 1
    if not adjacent:
        logger.debug(
            "Interior-point death: 2 non-adjacent empty points for %s at %s, %s",
            target_color, p1, p2,
        )
        return True

    return False
