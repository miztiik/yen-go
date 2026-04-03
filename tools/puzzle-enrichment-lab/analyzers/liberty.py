"""Legality validation helpers for tsumego frame placement.

Provides liberty counting, puzzle stone protection, eye detection,
and frameable space checks. Extracted from tsumego_frame.py per MH-1
governance constraint (helpers exceeded 120-line threshold).
"""

from __future__ import annotations

try:
    from models.position import Color
except ImportError:
    from ..models.position import Color

_NEIGHBORS = ((0, 1), (0, -1), (1, 0), (-1, 0))


def count_group_liberties(
    coord: tuple[int, int],
    color: Color,
    occupied: dict[tuple[int, int], Color],
    board_size: int,
) -> int:
    """Count liberties of the group at *coord* after hypothetical placement.

    BFS through same-color connected stones; count unique empty neighbors.
    *occupied* must already include all currently placed stones **plus** the
    candidate stone at *coord*.
    """
    liberties: set[tuple[int, int]] = set()
    visited: set[tuple[int, int]] = set()
    queue = [coord]
    visited.add(coord)
    while queue:
        cx, cy = queue.pop()
        for dx, dy in _NEIGHBORS:
            nx, ny = cx + dx, cy + dy
            if nx < 0 or nx >= board_size or ny < 0 or ny >= board_size:
                continue
            ncoord = (nx, ny)
            if ncoord not in occupied:
                liberties.add(ncoord)
            elif ncoord not in visited and occupied.get(ncoord) == color:
                visited.add(ncoord)
                queue.append(ncoord)
    return len(liberties)


def would_harm_puzzle_stones(
    coord: tuple[int, int],
    candidate_color: Color,
    puzzle_stone_coords: frozenset[tuple[int, int]],
    occupied: dict[tuple[int, int], Color],
    board_size: int,
) -> bool:
    """Return True if placing *candidate_color* at *coord* would reduce any
    adjacent puzzle-stone group to zero liberties."""
    occ = dict(occupied)
    occ[coord] = candidate_color
    checked: set[tuple[int, int]] = set()
    for dx, dy in _NEIGHBORS:
        nx, ny = coord[0] + dx, coord[1] + dy
        adj = (nx, ny)
        if adj in checked or adj not in puzzle_stone_coords:
            continue
        adj_color = occ.get(adj)
        if adj_color is None or adj_color == candidate_color:
            continue  # same color or empty — no concern
        # Opposing-color puzzle group — check if still has liberties
        libs = count_group_liberties(adj, adj_color, occ, board_size)
        if libs == 0:
            return True
        # Mark all stones in this group as checked to avoid re-scanning
        visited: set[tuple[int, int]] = set()
        q = [adj]
        visited.add(adj)
        while q:
            cx, cy = q.pop()
            for ddx, ddy in _NEIGHBORS:
                nnx, nny = cx + ddx, cy + ddy
                nn = (nnx, nny)
                if nn not in visited and occ.get(nn) == adj_color:
                    visited.add(nn)
                    q.append(nn)
        checked |= visited
    return False


def is_eye(
    coord: tuple[int, int],
    color: Color,
    occupied: dict[tuple[int, int], Color],
    board_size: int,
) -> bool:
    """Return True if *coord* is a single-point or two-point eye of *color*.

    Single-point eye: all orthogonal neighbours are *color* (or off-board),
    and ≥3 of 4 diagonals are *color* or off-board (all for edge/corner).

    Two-point eye: coord is empty, has exactly one empty orthogonal
    neighbour that also has all remaining neighbours == *color*.
    """
    x, y = coord

    # --- Single-point eye ---
    ortho_ok = True
    for dx, dy in _NEIGHBORS:
        nx, ny = x + dx, y + dy
        if 0 <= nx < board_size and 0 <= ny < board_size:
            if occupied.get((nx, ny)) != color:
                ortho_ok = False
                break
    if ortho_ok:
        diags = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
        diag_total = 0
        diag_ok = 0
        for dx, dy in diags:
            nx, ny = x + dx, y + dy
            if 0 <= nx < board_size and 0 <= ny < board_size:
                diag_total += 1
                if occupied.get((nx, ny)) == color:
                    diag_ok += 1
            else:
                diag_ok += 1  # off-board counts as friendly
                diag_total += 1
        # Edge/corner: all diags must be ok. Interior: at least 3/4.
        on_edge = x == 0 or x == board_size - 1 or y == 0 or y == board_size - 1
        if on_edge:
            if diag_ok == diag_total:
                return True
        else:
            if diag_ok >= 3:
                return True

    # --- Two-point eye ---
    empty_neighbors: list[tuple[int, int]] = []
    for dx, dy in _NEIGHBORS:
        nx, ny = x + dx, y + dy
        if 0 <= nx < board_size and 0 <= ny < board_size:
            if (nx, ny) not in occupied:
                empty_neighbors.append((nx, ny))
            elif occupied.get((nx, ny)) != color:
                return False  # Non-friendly neighbour → not a two-point eye
    if len(empty_neighbors) == 1:
        partner = empty_neighbors[0]
        # The partner must also have all non-shared neighbours == color
        px, py = partner
        for dx, dy in _NEIGHBORS:
            nx, ny = px + dx, py + dy
            if (nx, ny) == coord:
                continue  # skip back-link
            if 0 <= nx < board_size and 0 <= ny < board_size:
                if occupied.get((nx, ny)) != color:
                    return False
        return True

    return False


def has_frameable_space(
    occupied_count: int,
    puzzle_region_count: int,
    board_size: int,
    min_ratio: float = 0.05,
) -> bool:
    """Return False when frameable area is less than *min_ratio* of total board."""
    total = board_size * board_size
    frameable = total - occupied_count - puzzle_region_count
    return frameable / total >= min_ratio
