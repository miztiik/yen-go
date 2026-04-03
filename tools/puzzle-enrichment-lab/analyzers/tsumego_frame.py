"""Tsumego frame: wrap puzzle positions for KataGo neural net evaluation.

Fills empty areas outside the puzzle region with attacker/defender stones
so that KataGo's ownership network sees a realistic tactical context:
  1. Policy concentrates on the puzzle area
  2. Ownership values distinguish alive/dead groups
  3. Score-neutral territory split (50/50) — puzzle outcome alone
     determines the winning margin

Algorithm: BFS flood-fill from seed points (V3 rewrite).
  - Normalize with flip + axis-swap → puzzle always in TL corner
  - BFS-from-seed guarantees connected defender/attacker zones
  - Post-fill validation asserts connectivity and no dead stones
  - Attacker BFS seeded from border wall cells for one connected blob
"""

from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass

try:
    from models.position import Color, Position, Stone
except ImportError:
    from ..models.position import Color, Position, Stone

try:
    from analyzers.liberty import (
        count_group_liberties,
        has_frameable_space,
        is_eye,
        would_harm_puzzle_stones,
    )
except ImportError:
    from .liberty import (
        count_group_liberties,
        has_frameable_space,
        is_eye,
        would_harm_puzzle_stones,
    )

logger = logging.getLogger(__name__)

_MIN_FRAME_BOARD_SIZE = 5


# ---------------------------------------------------------------------------
# Data types (T2-T5)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class FrameConfig:
    """Configuration for frame generation — all tunables."""
    margin: int = 2
    ko_type: str = "none"
    board_size: int = 19
    synthetic_komi: bool = False


@dataclass(frozen=True)
class NormalizedPosition:
    """Position normalized to top-left corner with transformation metadata."""
    position: Position
    flip_x: bool
    flip_y: bool
    swap_xy: bool
    original_board_size: int


@dataclass(frozen=True)
class FrameRegions:
    """Computed regions for frame placement."""
    puzzle_bbox: tuple[int, int, int, int]  # (min_x, min_y, max_x, max_y)
    puzzle_region: frozenset[tuple[int, int]]
    occupied: frozenset[tuple[int, int]]
    board_edge_sides: frozenset[str]
    defense_area: int
    offense_area: int


@dataclass
class FrameResult:
    """Result of frame generation — new stones + metadata."""
    position: Position
    frame_stones_added: int
    attacker_color: Color
    normalized: bool
    stones_skipped_illegal: int = 0
    stones_skipped_puzzle_protect: int = 0
    stones_skipped_eye: int = 0
    fill_density: float = 0.0


# ---------------------------------------------------------------------------
# Core functions (T6-T13)
# ---------------------------------------------------------------------------

def _opposite(color: Color) -> Color:
    return Color.WHITE if color == Color.BLACK else Color.BLACK


def _cover_side_score(position: Position) -> int:
    """Return >0 if Black's bbox covers more sides than White's, <0 vice-versa.

    Lizzie-style heuristic: compare per-color bounding boxes. The colour
    whose bbox extends further on more sides is the attacker (enclosure).
    """
    blacks = position.black_stones
    whites = position.white_stones
    if not blacks or not whites:
        return 0

    b_min_x = min(s.x for s in blacks)
    b_max_x = max(s.x for s in blacks)
    b_min_y = min(s.y for s in blacks)
    b_max_y = max(s.y for s in blacks)

    w_min_x = min(s.x for s in whites)
    w_max_x = max(s.x for s in whites)
    w_min_y = min(s.y for s in whites)
    w_max_y = max(s.y for s in whites)

    black_covers = 0
    white_covers = 0
    if b_min_x < w_min_x:
        black_covers += 1
    if b_max_x > w_max_x:
        black_covers += 1
    if b_min_y < w_min_y:
        black_covers += 1
    if b_max_y > w_max_y:
        black_covers += 1
    if w_min_x < b_min_x:
        white_covers += 1
    if w_max_x > b_max_x:
        white_covers += 1
    if w_min_y < b_min_y:
        white_covers += 1
    if w_max_y > b_max_y:
        white_covers += 1

    return black_covers - white_covers


def guess_attacker(position: Position) -> Color:
    """Infer the attacker color using stone-count + edge-proximity heuristic.

    1. If stone counts are heavily skewed (≥3:1 ratio), the color with
       MORE stones is the attacker (it forms the surrounding enclosure).
    2. Otherwise, the color whose stones are, on average, closer to the
       board edges is the DEFENDER (living in the corner/edge).
    Tie-break: Black is attacker (convention).
    """
    bs = position.board_size
    nb = len(position.black_stones)
    nw = len(position.white_stones)

    # Heavy imbalance: majority forms the enclosure → attacker
    if nb > 0 and nw > 0:
        ratio = max(nb, nw) / min(nb, nw)
        if ratio >= 3.0:
            return Color.BLACK if nb > nw else Color.WHITE

    def avg_edge_dist(stones: list[Stone]) -> float:
        if not stones:
            return float("inf")
        total = 0.0
        for s in stones:
            total += min(s.x, s.y, bs - 1 - s.x, bs - 1 - s.y)
        return total / len(stones)

    black_dist = avg_edge_dist(position.black_stones)
    white_dist = avg_edge_dist(position.white_stones)

    if black_dist < white_dist:
        return Color.WHITE  # Black closer to edge → Black defends → White attacks
    if white_dist < black_dist:
        return Color.BLACK  # White closer to edge → White defends → Black attacks

    # Cover-side tie-breaker (Lizzie heuristic): the colour whose bbox
    # extends further on more sides is the attacker (enclosing the other).
    if nb > 0 and nw > 0:
        cover = _cover_side_score(position)
        if cover > 0:
            return Color.BLACK
        if cover < 0:
            return Color.WHITE

    # PL tie-breaker: in tsumego, player_to_move is typically the defender.
    # Using opposite(PL) is strictly better than arbitrary Color.BLACK.
    if position.player_to_move:
        pl_attacker = _opposite(position.player_to_move)
        if pl_attacker != Color.BLACK:
            logger.info(
                "Attacker heuristic tie-break (BLACK) disagrees with "
                "PL-based inference (%s); using PL.",
                pl_attacker.value,
            )
        return pl_attacker
    return Color.BLACK  # Ultimate fallback when PL is absent


def normalize_to_tl(position: Position) -> NormalizedPosition:
    """Flip and optionally swap axes so puzzle stones are in the top-left corner.

    1. Flip x/y so centroid moves to TL quadrant (existing).
    2. After flip, if the stones' bounding-box minimum x > minimum y the
       puzzle sits on an edge rather than a corner.  Swap x↔y to rotate
       it into a true corner — this guarantees the linear/BFS fill can
       produce two contiguous zones without wrapping around the puzzle.
    """
    bs = position.board_size
    if not position.stones:
        return NormalizedPosition(
            position=position.model_copy(deep=True),
            flip_x=False, flip_y=False, swap_xy=False,
            original_board_size=bs,
        )

    cx = sum(s.x for s in position.stones) / len(position.stones)
    cy = sum(s.y for s in position.stones) / len(position.stones)
    mid = (bs - 1) / 2.0

    flip_x = cx > mid
    flip_y = cy > mid

    # Apply flips
    new_stones: list[Stone] = []
    for s in position.stones:
        nx = (bs - 1 - s.x) if flip_x else s.x
        ny = (bs - 1 - s.y) if flip_y else s.y
        new_stones.append(Stone(color=s.color, x=nx, y=ny))

    # Detect edge (non-corner) puzzle: if min_x > min_y after flip,
    # the puzzle is on a horizontal edge — swap axes to move it to corner.
    min_x = min(s.x for s in new_stones)
    min_y = min(s.y for s in new_stones)
    swap_xy = min_x > min_y

    if swap_xy:
        new_stones = [
            Stone(color=s.color, x=s.y, y=s.x) for s in new_stones
        ]

    return NormalizedPosition(
        position=Position(
            board_size=bs,
            stones=new_stones,
            player_to_move=position.player_to_move,
            komi=position.komi,
        ),
        flip_x=flip_x,
        flip_y=flip_y,
        swap_xy=swap_xy,
        original_board_size=bs,
    )


def denormalize(position: Position, norm: NormalizedPosition) -> Position:
    """Reverse the transformations applied by normalize_to_tl.

    Order: undo swap first, then undo flips (reverse of normalize order).
    """
    if not norm.flip_x and not norm.flip_y and not norm.swap_xy:
        return position.model_copy(deep=True)

    bs = norm.original_board_size
    new_stones: list[Stone] = []
    for s in position.stones:
        sx, sy = s.x, s.y
        # Undo swap first
        if norm.swap_xy:
            sx, sy = sy, sx
        # Then undo flips
        if norm.flip_x:
            sx = bs - 1 - sx
        if norm.flip_y:
            sy = bs - 1 - sy
        new_stones.append(Stone(color=s.color, x=sx, y=sy))

    return Position(
        board_size=bs,
        stones=new_stones,
        player_to_move=position.player_to_move,
        komi=position.komi,
    )


def detect_board_edge_sides(
    bbox: tuple[int, int, int, int],
    board_size: int,
    margin: int = 2,
) -> frozenset[str]:
    """Return which sides of the puzzle bbox are within margin of the board edge."""
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


def compute_regions(position: Position, config: FrameConfig) -> FrameRegions:
    """Compute bounding box, puzzle region, and territory areas."""
    occupied = frozenset((s.x, s.y) for s in position.stones)
    bs = config.board_size

    if not occupied:
        return FrameRegions(
            puzzle_bbox=(0, 0, 0, 0),
            puzzle_region=frozenset(),
            occupied=occupied,
            board_edge_sides=frozenset(),
            defense_area=0,
            offense_area=0,
        )

    xs = [x for x, _ in occupied]
    ys = [y for _, y in occupied]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    bbox = (min_x, min_y, max_x, max_y)

    # Puzzle region = bbox + margin (no-place zone)
    p_min_x = max(0, min_x - config.margin)
    p_max_x = min(bs - 1, max_x + config.margin)
    p_min_y = max(0, min_y - config.margin)
    p_max_y = min(bs - 1, max_y + config.margin)
    puzzle_region = frozenset(
        (x, y)
        for x in range(p_min_x, p_max_x + 1)
        for y in range(p_min_y, p_max_y + 1)
    )

    edge_sides = detect_board_edge_sides(bbox, bs, config.margin)

    # Score-neutral 50/50 territory split (V3).
    # Puzzle outcome alone determines the winning margin.
    total_area = bs * bs
    frameable = total_area - len(puzzle_region)
    defense_area = max(0, frameable // 2)
    offense_area = max(0, frameable - defense_area)

    return FrameRegions(
        puzzle_bbox=bbox,
        puzzle_region=puzzle_region,
        occupied=occupied,
        board_edge_sides=edge_sides,
        defense_area=defense_area,
        offense_area=offense_area,
    )


def _choose_flood_seeds(
    regions: FrameRegions,
    board_size: int,
) -> tuple[tuple[int, int], tuple[int, int]]:
    """Choose BFS seed points for defender and attacker fill.

    After normalize-to-TL-corner, the puzzle is always in the top-left.
    - Defender seed: top-right corner (bs-1, 0) — farthest from puzzle
    - Attacker far seed: bottom-right corner (bs-1, bs-1)

    Returns:
        (defender_seed, attacker_far_seed)
    """
    bs = board_size
    return (bs - 1, 0), (bs - 1, bs - 1)


_EYE_INTERVAL = 7  # leave hole every N placed stones for eye space


def _bfs_fill(
    seeds: list[tuple[int, int]],
    frameable: set[tuple[int, int]],
    quota: int,
    color: Color,
    occupied: dict[tuple[int, int], Color],
    puzzle_stone_coords: frozenset[tuple[int, int]],
    defender_color: Color,
    board_size: int,
    border_coords: frozenset[tuple[int, int]] | None = None,
    puzzle_region: frozenset[tuple[int, int]] | None = None,
) -> tuple[list[Stone], dict[str, int]]:
    """Connectivity-preserving BFS fill from seed points up to quota cells.

    Spine/chain growth algorithm (V3.2):
      - BFS explores from seeds, but ONLY enqueues neighbors from cells
        where a stone was actually PLACED (or pre-existing same-color).
        This guarantees all placed stones form a single connected component.
      - Every ``_EYE_INTERVAL`` placed stones, one cell is left empty
        (counter-based eye hole) to create living-group eye space.
      - Cells within Manhattan distance 1 of border/puzzle-region are
        always filled (no eye holes) for wall integrity.
      - Legality guards (eye, suicide, puzzle-protect) still apply.

    Returns:
        (stones, skip_stats)
    """
    bs = board_size
    if border_coords is None:
        border_coords = frozenset()
    if puzzle_region is None:
        puzzle_region = frozenset()

    # Pre-compute the set of cells near border/puzzle for dense fill
    _near_boundary: set[tuple[int, int]] = set()
    for bx, by in border_coords | puzzle_region:
        for dx in range(-1, 2):
            for dy in range(-1, 2):
                if abs(dx) + abs(dy) <= 1:
                    _near_boundary.add((bx + dx, by + dy))

    queue: deque[tuple[int, int]] = deque()
    visited: set[tuple[int, int]] = set()
    for seed in seeds:
        if seed in frameable and seed not in occupied:
            queue.append(seed)
            visited.add(seed)
        elif seed in occupied and occupied[seed] == color:
            # Pre-existing same-color stone: enqueue neighbors for expansion
            visited.add(seed)
            for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0)):
                nc = (seed[0] + dx, seed[1] + dy)
                if 0 <= nc[0] < bs and 0 <= nc[1] < bs and nc not in visited:
                    visited.add(nc)
                    queue.append(nc)

    stones: list[Stone] = []
    skip_illegal = 0
    skip_puzzle = 0
    skip_eye = 0
    stones_since_eye = 0

    def _enqueue_neighbors(x: int, y: int) -> None:
        for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            nc = (x + dx, y + dy)
            if 0 <= nc[0] < bs and 0 <= nc[1] < bs and nc not in visited:
                visited.add(nc)
                queue.append(nc)

    while queue and len(stones) < quota:
        x, y = queue.popleft()
        coord = (x, y)

        # Skip non-frameable or already-occupied cells.
        # If same-color occupied, expand from it (it's part of our chain).
        if coord in occupied:
            if occupied[coord] == color:
                _enqueue_neighbors(x, y)
            continue
        if coord not in frameable:
            continue

        # Counter-based eye hole: leave empty every _EYE_INTERVAL stones
        # unless near border/puzzle-region where density is needed.
        if (
            stones_since_eye >= _EYE_INTERVAL
            and coord not in _near_boundary
        ):
            stones_since_eye = 0
            # Do NOT enqueue neighbors — preserve connectivity
            continue

        # Guard 1: eye detection
        if is_eye(coord, defender_color, occupied, bs):
            skip_eye += 1
            # Do NOT enqueue — preserve connectivity
            continue

        # Guard 2: self-legality
        test_occ = dict(occupied)
        test_occ[coord] = color
        if count_group_liberties(coord, color, test_occ, bs) == 0:
            skip_illegal += 1
            continue

        # Guard 3: puzzle stone protection
        if puzzle_stone_coords and would_harm_puzzle_stones(
            coord, color, puzzle_stone_coords, occupied, bs
        ):
            skip_puzzle += 1
            continue

        # Place stone and expand BFS from this cell
        stones.append(Stone(color=color, x=x, y=y))
        occupied[coord] = color
        stones_since_eye += 1
        _enqueue_neighbors(x, y)

    skip_stats = {
        "illegal": skip_illegal,
        "puzzle_protect": skip_puzzle,
        "eye": skip_eye,
    }
    return stones, skip_stats


def fill_territory(
    position: Position,
    regions: FrameRegions,
    attacker_color: Color,
    puzzle_stone_coords: frozenset[tuple[int, int]] | None = None,
    border_coords: frozenset[tuple[int, int]] | None = None,
) -> tuple[list[Stone], dict[str, int]]:
    """Fill frameable area with attacker/defender stones using BFS flood-fill.

    BFS from seed points guarantees connected zones by construction.
    Defender fills from the top-right corner (after normalize); attacker
    fills from border wall cells + bottom-right corner.

    Returns:
        (stones, skip_stats) where skip_stats has counts of skipped placements.
    """
    bs = position.board_size
    defender_color = _opposite(attacker_color)
    if puzzle_stone_coords is None:
        puzzle_stone_coords = frozenset()
    if border_coords is None:
        border_coords = frozenset()

    # Compute frameable cells
    frameable: set[tuple[int, int]] = set()
    for x in range(bs):
        for y in range(bs):
            coord = (x, y)
            if coord not in regions.occupied and coord not in regions.puzzle_region:
                frameable.add(coord)

    # Build mutable occupied dict
    occupied: dict[tuple[int, int], Color] = {}
    for s in position.stones:
        occupied[(s.x, s.y)] = s.color

    defender_seed, attacker_far_seed = _choose_flood_seeds(regions, bs)

    # BFS defender fill — spine/chain growth with periodic eye holes
    def_stones, def_skips = _bfs_fill(
        [defender_seed], frameable, regions.defense_area,
        defender_color, occupied, puzzle_stone_coords, defender_color, bs,
        border_coords=border_coords,
        puzzle_region=regions.puzzle_region,
    )

    # BFS attacker fill — seed from border cells + far corner
    attacker_seeds = list(border_coords) + [attacker_far_seed]
    atk_stones, atk_skips = _bfs_fill(
        attacker_seeds, frameable, regions.offense_area,
        attacker_color, occupied, puzzle_stone_coords, defender_color, bs,
        border_coords=border_coords,
        puzzle_region=regions.puzzle_region,
    )

    all_stones = def_stones + atk_stones
    skip_stats = {
        "illegal": def_skips["illegal"] + atk_skips["illegal"],
        "puzzle_protect": def_skips["puzzle_protect"] + atk_skips["puzzle_protect"],
        "eye": def_skips["eye"] + atk_skips["eye"],
    }
    return all_stones, skip_stats


def place_border(
    position: Position,
    regions: FrameRegions,
    attacker_color: Color,
    puzzle_stone_coords: frozenset[tuple[int, int]] | None = None,
) -> tuple[list[Stone], dict[str, int]]:
    """Place attacker-colored border on non-board-edge sides of puzzle region.

    ghostban approach: border only where the puzzle does NOT touch the
    board edge — a TL corner puzzle gets border on right + bottom only.

    Returns:
        (stones, skip_stats) where skip_stats has counts of skipped placements.
    """
    bs = position.board_size
    min_x, min_y, max_x, max_y = regions.puzzle_bbox
    occupied_set = set(regions.occupied)
    if puzzle_stone_coords is None:
        puzzle_stone_coords = frozenset()

    border_cells: list[tuple[int, int]] = []

    # Right border (one column right of puzzle region)
    if "right" not in regions.board_edge_sides:
        p_max_x = max(px for px, _ in regions.puzzle_region) if regions.puzzle_region else max_x
        col = p_max_x + 1
        if col < bs:
            for y in range(bs):
                if (col, y) not in occupied_set and (col, y) not in regions.puzzle_region:
                    border_cells.append((col, y))

    # Bottom border
    if "bottom" not in regions.board_edge_sides:
        p_max_y = max(py for _, py in regions.puzzle_region) if regions.puzzle_region else max_y
        row = p_max_y + 1
        if row < bs:
            for x in range(bs):
                if (x, row) not in occupied_set and (x, row) not in regions.puzzle_region:
                    border_cells.append((x, row))

    # Left border
    if "left" not in regions.board_edge_sides:
        p_min_x = min(px for px, _ in regions.puzzle_region) if regions.puzzle_region else min_x
        col = p_min_x - 1
        if col >= 0:
            for y in range(bs):
                if (col, y) not in occupied_set and (col, y) not in regions.puzzle_region:
                    border_cells.append((col, y))

    # Top border
    if "top" not in regions.board_edge_sides:
        p_min_y = min(py for _, py in regions.puzzle_region) if regions.puzzle_region else min_y
        row = p_min_y - 1
        if row >= 0:
            for x in range(bs):
                if (x, row) not in occupied_set and (x, row) not in regions.puzzle_region:
                    border_cells.append((x, row))

    # Deduplicate and apply legality guards
    seen: set[tuple[int, int]] = set()
    stones: list[Stone] = []
    skip_illegal = 0
    skip_puzzle = 0
    skip_eye = 0

    # Build occupied dict for legality checks
    occ: dict[tuple[int, int], Color] = {}
    for s in position.stones:
        occ[(s.x, s.y)] = s.color
    defender_color = _opposite(attacker_color)

    for x, y in border_cells:
        coord = (x, y)
        if coord in seen:
            continue
        seen.add(coord)

        # Guard: eye detection
        if is_eye(coord, defender_color, occ, bs):
            skip_eye += 1
            continue

        # Guard: self-legality
        test_occ = dict(occ)
        test_occ[coord] = attacker_color
        if count_group_liberties(coord, attacker_color, test_occ, bs) == 0:
            skip_illegal += 1
            continue

        # Guard: puzzle stone protection
        if puzzle_stone_coords and would_harm_puzzle_stones(
            coord, attacker_color, puzzle_stone_coords, occ, bs
        ):
            skip_puzzle += 1
            continue

        stones.append(Stone(color=attacker_color, x=x, y=y))
        occ[coord] = attacker_color

    skip_stats = {
        "illegal": skip_illegal,
        "puzzle_protect": skip_puzzle,
        "eye": skip_eye,
    }
    return stones, skip_stats


# KaTrain ko-threat patterns: 2 fixed 4-stone groups
_KO_THREAT_PATTERN_OFFENSE = [
    # Pattern: X . X    (attacker stones at relative offsets)
    #          . X .
    (0, 0), (2, 0), (1, 1), (0, 2),
]
_KO_THREAT_PATTERN_DEFENSE = [
    (0, 0), (1, 0), (0, 1), (2, 1),
]


def place_ko_threats(
    position: Position,
    regions: FrameRegions,
    attacker_color: Color,
    ko_type: str,
    player_to_move: Color,
) -> list[Stone]:
    """Place ko-threat stone patterns near the puzzle (KaTrain approach).

    Only activated when ko_type != "none". Places 2 threat groups
    of 4 stones each to ensure ko-fight material exists.
    """
    if ko_type == "none":
        return []

    bs = position.board_size
    occupied = set(regions.occupied)
    # Add puzzle region to avoid set
    avoid = occupied | set(regions.puzzle_region)

    # Determine threat colors: offense vs defense threats
    defender_color = _opposite(attacker_color)
    black_attacks = (attacker_color == Color.BLACK)
    black_plays = (player_to_move == Color.BLACK)
    # KaTrain formula: for_offense = xor(ko, xor(black_attacks, black_plays))
    ko_p = ko_type == "direct"
    for_offense = ko_p ^ (black_attacks ^ black_plays)

    if for_offense:
        pattern1 = _KO_THREAT_PATTERN_OFFENSE
        color1 = attacker_color
        pattern2 = _KO_THREAT_PATTERN_DEFENSE
        color2 = defender_color
    else:
        pattern1 = _KO_THREAT_PATTERN_DEFENSE
        color1 = defender_color
        pattern2 = _KO_THREAT_PATTERN_OFFENSE
        color2 = attacker_color

    stones: list[Stone] = []

    def _try_place(
        pattern: list[tuple[int, int]],
        color: Color,
        start_x: int,
        start_y: int,
    ) -> bool:
        """Try to place a pattern at (start_x, start_y). Returns True if placed."""
        cells = [(start_x + dx, start_y + dy) for dx, dy in pattern]
        # Check all cells are valid and unoccupied
        for cx, cy in cells:
            if cx < 0 or cx >= bs or cy < 0 or cy >= bs:
                return False
            if (cx, cy) in avoid:
                return False
        for cx, cy in cells:
            stones.append(Stone(color=color, x=cx, y=cy))
            avoid.add((cx, cy))
        return True

    # Try placing patterns in far corners (away from puzzle)
    _, _, max_x, max_y = regions.puzzle_bbox
    far_starts = [
        (bs - 4, bs - 4),
        (bs - 4, 0),
        (0, bs - 4),
        (bs - 7, bs - 4),
        (bs - 4, bs - 7),
    ]

    placed1 = False
    placed2 = False
    for sx, sy in far_starts:
        if not placed1 and _try_place(pattern1, color1, sx, sy):
            placed1 = True
        elif not placed2 and _try_place(pattern2, color2, sx, sy):
            placed2 = True
        if placed1 and placed2:
            break

    # C1: Warn when ko threats were requested but couldn't be placed
    if not placed1 or not placed2:
        logger.warning(
            "Ko threats requested (ko_type=%s) but insufficient room on "
            "%dx%d board: placed=%d/2",
            ko_type, bs, bs, int(placed1) + int(placed2),
        )

    return stones


# ---------------------------------------------------------------------------
# Post-fill validation (T9)
# ---------------------------------------------------------------------------

def validate_frame(
    framed_position: Position,
    original_position: Position,
    attacker_color: Color,
    puzzle_stone_coords: frozenset[tuple[int, int]],
) -> tuple[bool, dict]:
    """Validate frame correctness after assembly.

    Checks:
      1. Defender frame stones form a single connected component (MH-2)
      2. Attacker frame stones form a single connected component
      3. No dead frame stone (each has ≥1 same-color ortho neighbor) (MH-3)

    Returns:
        (is_valid, diagnostics_dict)
    """
    bs = framed_position.board_size
    defender_color = _opposite(attacker_color)

    # Separate frame stones by color (exclude puzzle stones)
    defender_frame: set[tuple[int, int]] = set()
    attacker_frame: set[tuple[int, int]] = set()
    for s in framed_position.stones:
        coord = (s.x, s.y)
        if coord in puzzle_stone_coords:
            continue
        if s.color == defender_color:
            defender_frame.add(coord)
        else:
            attacker_frame.add(coord)

    def _count_components(coords: set[tuple[int, int]]) -> int:
        if not coords:
            return 0
        remaining = set(coords)
        components = 0
        while remaining:
            components += 1
            seed = next(iter(remaining))
            q: deque[tuple[int, int]] = deque([seed])
            remaining.discard(seed)
            while q:
                cx, cy = q.popleft()
                for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0)):
                    nc = (cx + dx, cy + dy)
                    if nc in remaining:
                        remaining.discard(nc)
                        q.append(nc)
        return components

    def _count_dead_stones(
        coords: set[tuple[int, int]],
        all_stones_by_coord: dict[tuple[int, int], Color],
        color: Color,
    ) -> int:
        """Count stones with zero same-color orthogonal neighbors.

        Stones at the zone boundary between defender and attacker fill
        may legitimately have only opposite-color neighbors — these are
        seam stones, not truly dead.  We only count a stone as dead if
        it has NO same-color neighbor AND NO opposite-color neighbor
        (i.e., truly isolated with only empty neighbors), which would
        indicate a placement error.
        """
        dead = 0
        for x, y in coords:
            has_friend = False
            has_any_neighbor = False
            for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0)):
                nc = (x + dx, y + dy)
                if 0 <= nc[0] < bs and 0 <= nc[1] < bs:
                    nc_color = all_stones_by_coord.get(nc)
                    if nc_color is not None:
                        has_any_neighbor = True
                    if nc_color == color:
                        has_friend = True
                        break
            # Only dead if no same-color friend AND no stone neighbor at all
            if not has_friend and not has_any_neighbor:
                dead += 1
        return dead

    stone_map = {(s.x, s.y): s.color for s in framed_position.stones}

    def_components = _count_components(defender_frame)
    atk_components = _count_components(attacker_frame)
    dead_def = _count_dead_stones(defender_frame, stone_map, defender_color)
    dead_atk = _count_dead_stones(attacker_frame, stone_map, attacker_color)

    diagnostics = {
        "defender_components": def_components,
        "attacker_components": atk_components,
        "dead_defender_stones": dead_def,
        "dead_attacker_stones": dead_atk,
    }

    is_valid = (
        dead_def == 0
        and dead_atk == 0
    )

    # Connectivity check: single component required unless the puzzle
    # region geometrically prevents it (e.g., 9×9 with large puzzle
    # where the puzzle region splits the board into separate pockets).
    if def_components > 1 or atk_components > 1:
        diagnostics["connectivity_warning"] = True
        logger.info(
            "Frame has %d defender + %d attacker components — "
            "puzzle geometry may split frameable area.",
            def_components, atk_components,
        )

    return is_valid, diagnostics


# ---------------------------------------------------------------------------
# Orchestration (T14-T16)
# ---------------------------------------------------------------------------

def _compute_synthetic_komi(
    regions: FrameRegions,
    attacker_color: Color,
) -> float:
    """Compute synthetic komi from filled territory areas (Lizzie approach).

    Formula: komi = 2 * (attacker_area - board_area/2), clamped to [-150, 150].
    Sign convention: positive komi favours Black.
    """
    total = regions.defense_area + regions.offense_area + len(regions.puzzle_region)
    komi = 2.0 * (regions.offense_area - total / 2.0)
    if attacker_color == Color.WHITE:
        komi = -komi
    return max(-150.0, min(150.0, komi))


def build_frame(
    position: Position,
    config: FrameConfig,
    offense_color: Color | None = None,
) -> FrameResult:
    """Orchestrate: guess attacker → normalize → regions → border → ko → fill → validate → denormalize."""
    attacker = offense_color if offense_color is not None else guess_attacker(position)

    # Normalize to TL corner for consistent framing (with axis-swap)
    norm = normalize_to_tl(position)
    norm_config = FrameConfig(
        margin=config.margin,
        ko_type=config.ko_type,
        board_size=norm.position.board_size,
        synthetic_komi=config.synthetic_komi,
    )

    regions = compute_regions(norm.position, norm_config)

    # F11: Nearly-full board — skip frame if insufficient space
    if not has_frameable_space(
        len(regions.occupied), len(regions.puzzle_region),
        norm.position.board_size,
    ):
        logger.warning(
            "Insufficient frameable space on %dx%d board — skipping frame.",
            norm.position.board_size, norm.position.board_size,
        )
        return FrameResult(
            position=position,
            frame_stones_added=0,
            attacker_color=attacker,
            normalized=False,
        )

    # Compute puzzle stone coordinates for protection guards
    puzzle_stone_coords = frozenset(
        (s.x, s.y) for s in norm.position.stones
    )

    # Border FIRST: solid attacker wall before fill, so fill flows around it
    # (prevents alternating attacker/defender atari in the border zone)
    border_stones, border_skips = place_border(
        norm.position, regions, attacker, puzzle_stone_coords,
    )

    # Ko threats BEFORE fill: the defense ko-threat pattern has mixed x+y
    # parities and cannot be placed once checkerboard fill occupies most
    # cells.  Placing ko patterns while the board is mostly empty guarantees
    # both offense and defense threats find room.
    border_occupied = regions.occupied | frozenset((s.x, s.y) for s in border_stones)
    ko_regions = FrameRegions(
        puzzle_bbox=regions.puzzle_bbox,
        puzzle_region=regions.puzzle_region,
        occupied=border_occupied,
        board_edge_sides=regions.board_edge_sides,
        defense_area=regions.defense_area,
        offense_area=regions.offense_area,
    )
    ko_stones = place_ko_threats(
        norm.position, ko_regions, attacker,
        config.ko_type, norm.position.player_to_move,
    )

    # Fill territory with BFS flood-fill, passing border coords as attacker seeds
    pre_fill_occupied = border_occupied | frozenset((s.x, s.y) for s in ko_stones)
    fill_regions = FrameRegions(
        puzzle_bbox=regions.puzzle_bbox,
        puzzle_region=regions.puzzle_region,
        occupied=pre_fill_occupied,
        board_edge_sides=regions.board_edge_sides,
        defense_area=regions.defense_area,
        offense_area=regions.offense_area,
    )
    border_coord_set = frozenset((s.x, s.y) for s in border_stones)
    fill_stones, fill_skips = fill_territory(
        norm.position, fill_regions, attacker, puzzle_stone_coords,
        border_coords=border_coord_set,
    )

    # Assemble framed position in normalized space
    all_frame_stones = fill_stones + border_stones + ko_stones

    # Aggregate skip counters from fill + border
    total_skipped_illegal = fill_skips["illegal"] + border_skips["illegal"]
    total_skipped_puzzle = fill_skips["puzzle_protect"] + border_skips["puzzle_protect"]
    total_skipped_eye = fill_skips["eye"] + border_skips["eye"]

    # Compute density metric (MH-4)
    bs = norm.position.board_size
    total_area = bs * bs
    frameable_area = total_area - len(regions.occupied) - len(regions.puzzle_region)
    fill_density = len(all_frame_stones) / frameable_area if frameable_area > 0 else 0.0

    # C4: Optional synthetic komi — recompute from filled territory areas
    komi = norm.position.komi
    if config.synthetic_komi:
        komi = _compute_synthetic_komi(regions, attacker)

    # INVIOLATE RULE: player_to_move is preserved from the original SGF PL property.
    # It must NEVER be altered by the framing process. KataGo's policy head
    # conditions on player_to_move; altering it changes the AI's move recommendations.
    framed_norm = Position(
        board_size=norm.position.board_size,
        stones=list(norm.position.stones) + all_frame_stones,
        player_to_move=norm.position.player_to_move,
        komi=komi,
    )

    # Post-fill validation (G4, MH-2, MH-3, MH-6)
    is_valid, diag = validate_frame(
        framed_norm, norm.position, attacker, puzzle_stone_coords,
    )
    if not is_valid:
        logger.warning(
            "Frame validation FAILED — returning original position. "
            "Diagnostics: %s", diag,
        )
        logger.warning("Failed frame SGF: %s", framed_norm.to_sgf())
        return FrameResult(
            position=position,
            frame_stones_added=0,
            attacker_color=attacker,
            normalized=False,
        )

    # Denormalize back to original orientation
    framed = denormalize(framed_norm, norm)

    logger.debug(
        "Frame applied: %dB + %dW (added %d stones, skipped: %d illegal, "
        "%d puzzle-protect, %d eye, density=%.2f)",
        len(framed.black_stones), len(framed.white_stones),
        len(all_frame_stones),
        total_skipped_illegal, total_skipped_puzzle, total_skipped_eye,
        fill_density,
    )

    return FrameResult(
        position=framed,
        frame_stones_added=len(all_frame_stones),
        attacker_color=attacker,
        normalized=norm.flip_x or norm.flip_y or norm.swap_xy,
        stones_skipped_illegal=total_skipped_illegal,
        stones_skipped_puzzle_protect=total_skipped_puzzle,
        stones_skipped_eye=total_skipped_eye,
        fill_density=fill_density,
    )


def apply_tsumego_frame(
    position: Position,
    *,
    margin: int = 2,
    offense_color: Color | None = None,
    ko_type: str = "none",
    synthetic_komi: bool = False,
) -> Position:
    """Public entry point — apply a tsumego frame to a puzzle position.

    Args:
        position: Original puzzle position.
        margin: Empty margin around puzzle stones (default 2).
        offense_color: Override attacker color. If None, inferred via
            edge-proximity heuristic.
        ko_type: Ko context: "none", "direct", or "approach".
        synthetic_komi: If True, recompute komi from filled territory
            areas instead of preserving the original (experimental).

    Returns:
        New Position with frame stones added. Original stones preserved.
    """
    if position.board_size < _MIN_FRAME_BOARD_SIZE:
        logger.debug("Board %dx%d too small for frame, skipping",
                      position.board_size, position.board_size)
        return position.model_copy(deep=True)

    if not position.stones:
        logger.debug("No stones on board, skipping frame")
        return position.model_copy(deep=True)

    config = FrameConfig(
        margin=margin,
        ko_type=ko_type,
        board_size=position.board_size,
        synthetic_komi=synthetic_komi,
    )
    result = build_frame(position, config, offense_color=offense_color)
    return result.position


def remove_tsumego_frame(
    framed_position: Position,
    original_position: Position,
) -> Position:
    """Remove the tsumego frame, restoring the original position."""
    return original_position.model_copy(deep=True)
