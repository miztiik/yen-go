"""Instinct classifier — classify correct move intent from position geometry.

Clean-room implementation (C-5): patterns from Sensei's Library (public domain).
Classifies among 5 tsumego-relevant instincts: push, hane, cut, descent, extend.

Confidence is computed per-position from geometric evidence strength (HIGH/MEDIUM/LOW
tiers) — not fixed thresholds. See expert consultation (Cho Chikun / Lee Sedol)
for tier boundary rationale.
"""

from __future__ import annotations

import logging

try:
    from models.analysis_response import AnalysisResponse
    from models.instinct_result import INSTINCT_TYPES, InstinctResult
    from models.position import Color, Position, Stone
except ImportError:
    from ..models.instinct_result import InstinctResult
    from ..models.position import Color, Position, Stone

logger = logging.getLogger(__name__)

# Orthogonal neighbor offsets
_ORTHO = [(0, 1), (0, -1), (1, 0), (-1, 0)]
# Diagonal neighbor offsets
_DIAG = [(1, 1), (1, -1), (-1, 1), (-1, -1)]


def _gtp_to_xy(gtp_coord: str, board_size: int = 19) -> tuple[int, int] | None:
    """Convert GTP coordinate (e.g. 'D4') to 0-indexed (x, y)."""
    if not gtp_coord or gtp_coord.lower() == "pass":
        return None
    col_letter = gtp_coord[0].upper()
    row_str = gtp_coord[1:]
    if not row_str.isdigit():
        return None
    letters = "ABCDEFGHJKLMNOPQRST"
    if col_letter not in letters:
        return None
    x = letters.index(col_letter)
    y = board_size - int(row_str)
    return (x, y)


def _find_groups(stones: list[Stone], color: Color) -> list[set[tuple[int, int]]]:
    """Find connected groups of stones of the given color using BFS.

    DRY note (RC-2): Group BFS logic exists in multiple detectors.
    This implementation is minimal and focused on instinct classification needs.
    """
    color_stones = {(s.x, s.y) for s in stones if s.color == color}
    visited: set[tuple[int, int]] = set()
    groups: list[set[tuple[int, int]]] = []

    for pos in color_stones:
        if pos in visited:
            continue
        group: set[tuple[int, int]] = set()
        queue = [pos]
        while queue:
            current = queue.pop()
            if current in visited:
                continue
            visited.add(current)
            group.add(current)
            cx, cy = current
            for dx, dy in _ORTHO:
                nb = (cx + dx, cy + dy)
                if nb in color_stones and nb not in visited:
                    queue.append(nb)
        groups.append(group)

    return groups


def _nearest_edge_distance(x: int, y: int, board_size: int) -> int:
    """Return the minimum distance to any board edge."""
    return min(x, y, board_size - 1 - x, board_size - 1 - y)


def _is_l_shape(diag_xy: tuple[int, int], adj_xy: tuple[int, int]) -> bool:
    """Check if a diagonal own-stone and an adjacent opponent-stone form an L-shape.

    True when they are orthogonally adjacent to each other, meaning the three
    points (move, own_diagonal, opp_adjacent) form a tight wrap-around contact.
    """
    return abs(diag_xy[0] - adj_xy[0]) + abs(diag_xy[1] - adj_xy[1]) == 1


# ---------------------------------------------------------------------------
# Per-instinct detection with tiered confidence
# ---------------------------------------------------------------------------

def _detect_cut(
    mx: int, my: int,
    own_adj: list[tuple[int, int]],
    opp_adj: list[tuple[int, int]],
    opp_groups: list[set[tuple[int, int]]],
    correct_move_gtp: str,
) -> InstinctResult | None:
    """Detect cut instinct with per-position confidence.

    HIGH (0.85): Separates 2+ groups, no own-stone adjacency (pure cutting point).
    MEDIUM (0.65): Separates 2+ groups, but own stones also adjacent.
    LOW (0.45): Separates 2+ groups, but smaller group is large (≥5 stones).
    """
    if len(opp_adj) < 2:
        return None

    adj_group_indices: set[int] = set()
    for ox, oy in opp_adj:
        for i, g in enumerate(opp_groups):
            if (ox, oy) in g:
                adj_group_indices.add(i)

    if len(adj_group_indices) < 2:
        return None

    # Determine tier based on geometric context
    smallest_group_size = min(len(opp_groups[i]) for i in adj_group_indices)

    if smallest_group_size >= 5:
        conf = 0.45
        evidence = f"Cut at {correct_move_gtp} separates {len(adj_group_indices)} groups (large groups — may be capturing race)"
    elif not own_adj:
        conf = 0.85
        evidence = f"Cut at {correct_move_gtp} separates {len(adj_group_indices)} opponent groups (pure cutting point)"
    else:
        conf = 0.65
        evidence = f"Cut at {correct_move_gtp} separates {len(adj_group_indices)} groups (also connects own stones)"

    return InstinctResult(instinct="cut", confidence=conf, evidence=evidence)


def _detect_push(
    mx: int, my: int,
    own_adj: list[tuple[int, int]],
    opp_adj: list[tuple[int, int]],
    own_set: set[tuple[int, int]],
    n: int,
    correct_move_gtp: str,
) -> InstinctResult | None:
    """Detect push instinct with per-position confidence.

    HIGH (0.80): Own behind, opponent ahead, move on 1st-3rd line.
    MEDIUM (0.60): Push pattern matches but move on 4th+ line.
    LOW (0.40): Push pattern but own-behind is from a different axis.
    """
    for ox, oy in opp_adj:
        dx, dy = mx - ox, my - oy
        behind = (ox - dx, oy - dy)
        if behind in own_set:
            move_edge_dist = _nearest_edge_distance(mx, my, n)
            opp_edge_dist = _nearest_edge_distance(ox, oy, n)

            if move_edge_dist <= 2 and opp_edge_dist <= 2:
                conf = 0.80
                evidence = f"Push at {correct_move_gtp} toward edge (line {move_edge_dist + 1})"
            elif move_edge_dist <= 3:
                conf = 0.60
                evidence = f"Push at {correct_move_gtp} toward opponent"
            else:
                conf = 0.40
                evidence = f"Push at {correct_move_gtp} (center area — weak directional signal)"

            return InstinctResult(instinct="push", confidence=conf, evidence=evidence)

    return None


def _detect_hane(
    mx: int, my: int,
    own_adj: list[tuple[int, int]],
    opp_adj: list[tuple[int, int]],
    own_diag: list[tuple[int, int]],
    opp_groups: list[set[tuple[int, int]]],
    correct_move_gtp: str,
) -> InstinctResult | None:
    """Detect hane instinct with L-shape verification and per-position confidence.

    The key fix: require the diagonal own-stone and adjacent opponent-stone to be
    orthogonally adjacent to each other (L-shape). Without this, cosmui near an
    opponent triggers false hane detection.

    HIGH (0.85): L-shape + no own orthogonal adj + opponent group small (2-3).
    MEDIUM (0.65): L-shape holds but own ortho neighbors exist or group large.
    LOW (0.45): No L-shape found — diagonal+adjacent exists but not wrapping.
    """
    if not own_diag or not opp_adj:
        return None

    # Check for L-shape: any (own_diag, opp_adj) pair that are ortho-adjacent
    l_shape_found = False
    l_shape_small_group = False
    for od in own_diag:
        for oa in opp_adj:
            if _is_l_shape(od, oa):
                l_shape_found = True
                # Check if opponent group at oa is small (classic head-of-two/three)
                for g in opp_groups:
                    if oa in g and 2 <= len(g) <= 3:
                        l_shape_small_group = True
                        break
                if l_shape_small_group:
                    break
        if l_shape_small_group:
            break

    if l_shape_found and l_shape_small_group and not own_adj:
        conf = 0.85
        evidence = f"Hane at {correct_move_gtp} wrapping around small group (L-shape confirmed)"
    elif l_shape_found:
        conf = 0.65
        evidence = f"Hane at {correct_move_gtp} wrapping around opponent (L-shape)"
    else:
        # No L-shape — diagonal + adjacent exist but not a true wrap-around
        conf = 0.45
        evidence = f"Possible hane at {correct_move_gtp} (diagonal + adjacent, no L-shape)"

    return InstinctResult(instinct="hane", confidence=conf, evidence=evidence)


def _detect_descent(
    mx: int, my: int,
    own_adj: list[tuple[int, int]],
    n: int,
    correct_move_gtp: str,
) -> InstinctResult | None:
    """Detect descent instinct with per-position confidence.

    HIGH (0.75): Move on 1st-2nd line, single own neighbor higher.
    MEDIUM (0.55): Move on 3rd line descending from 4th+.
    LOW (0.35): Marginal edge distance difference or mixed direction.
    """
    if not own_adj:
        return None

    move_edge_dist = _nearest_edge_distance(mx, my, n)
    descending_from = []

    for sx, sy in own_adj:
        stone_edge_dist = _nearest_edge_distance(sx, sy, n)
        if move_edge_dist < stone_edge_dist:
            descending_from.append((sx, sy, stone_edge_dist))

    if not descending_from:
        return None

    if move_edge_dist <= 1 and len(descending_from) == 1:
        conf = 0.75
        evidence = f"Descent at {correct_move_gtp} to line {move_edge_dist + 1}"
    elif move_edge_dist <= 2:
        conf = 0.55
        evidence = f"Descent at {correct_move_gtp} toward edge (line {move_edge_dist + 1})"
    else:
        conf = 0.35
        evidence = f"Descent at {correct_move_gtp} (marginal edge proximity)"

    return InstinctResult(instinct="descent", confidence=conf, evidence=evidence)


def _detect_extend(
    mx: int, my: int,
    own_adj: list[tuple[int, int]],
    opp_adj: list[tuple[int, int]],
    own_diag: list[tuple[int, int]],
    own_set: set[tuple[int, int]],
    opp_set: set[tuple[int, int]],
    n: int,
    correct_move_gtp: str,
) -> InstinctResult | None:
    """Detect extend instinct with per-position confidence.

    HIGH (0.65): Clean axis extension, no opponent contact, no diagonal own stones.
    MEDIUM (0.50): On axis but opponent also adjacent (contact extension).
    LOW (0.35): On axis but 2+ own neighbors (filling a gap / connecting, not extending).
    """
    if not own_adj:
        return None

    same_axis_neighbors = [(sx, sy) for sx, sy in own_adj if sx == mx or sy == my]
    if not same_axis_neighbors:
        return None

    # 2+ own orthogonal neighbors = connecting, not extending
    if len(own_adj) >= 2:
        conf = 0.35
        evidence = f"Extension at {correct_move_gtp} (connecting — multiple own neighbors)"
    elif opp_adj:
        conf = 0.50
        evidence = f"Extension at {correct_move_gtp} (contact — opponent adjacent)"
    elif not own_diag and not opp_adj:
        conf = 0.65
        evidence = f"Extension at {correct_move_gtp} along line (clean)"
    else:
        conf = 0.50
        evidence = f"Extension at {correct_move_gtp} along line"

    return InstinctResult(instinct="extend", confidence=conf, evidence=evidence)


# ---------------------------------------------------------------------------
# Primary selection
# ---------------------------------------------------------------------------

def select_primary(
    results: list[InstinctResult],
    min_confidence: float = 0.65,
    clarity_threshold: float = 0.15,
    max_before_ambiguous: int = 4,
) -> list[InstinctResult]:
    """Select the primary instinct and mark it on the results list.

    Rules:
    1. If >= max_before_ambiguous instincts detected → ambiguous, no primary.
    2. Clarity = gap between #1 and #2. If < clarity_threshold → ambiguous.
    3. Top instinct must meet min_confidence to be eligible as primary.

    Returns the (possibly modified) results list with is_primary set.
    """
    if not results:
        return results

    if len(results) >= max_before_ambiguous:
        return results  # All is_primary remain False

    top = results[0]  # Already sorted by confidence desc

    if len(results) >= 2:
        clarity = top.confidence - results[1].confidence
    else:
        clarity = top.confidence

    if top.confidence >= min_confidence and clarity >= clarity_threshold:
        top.is_primary = True

    return results


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def classify_instinct(
    position: Position,
    correct_move_gtp: str,
    config: dict | None = None,
) -> list[InstinctResult]:
    """Classify the correct move's intent based on position geometry.

    Per-position confidence is computed from geometric evidence strength
    (HIGH/MEDIUM/LOW tiers). The config dict is used only for gating thresholds
    (min_confidence_to_log, clarity_threshold, etc.), not for per-instinct
    confidence values which are determined by geometric analysis.

    Args:
        position: Current board position.
        correct_move_gtp: GTP coordinate of the correct move.
        config: Optional config with gating thresholds.

    Returns:
        List of InstinctResult, sorted by confidence descending,
        with at most one result having is_primary=True.
        Empty list if move cannot be classified.
    """
    xy = _gtp_to_xy(correct_move_gtp, position.board_size)
    if xy is None:
        return []

    mx, my = xy
    n = position.board_size

    # Build lookup sets
    own_color = position.player_to_move
    opp_color = Color.WHITE if own_color == Color.BLACK else Color.BLACK
    own_set = {(s.x, s.y) for s in position.stones if s.color == own_color}
    opp_set = {(s.x, s.y) for s in position.stones if s.color == opp_color}

    # Orthogonal neighbors of the move
    own_adj = [(mx + dx, my + dy) for dx, dy in _ORTHO if (mx + dx, my + dy) in own_set]
    opp_adj = [(mx + dx, my + dy) for dx, dy in _ORTHO if (mx + dx, my + dy) in opp_set]

    # Diagonal neighbors of the move
    own_diag = [(mx + dx, my + dy) for dx, dy in _DIAG if (mx + dx, my + dy) in own_set]

    # Pre-compute opponent groups (needed by cut and hane)
    opp_groups = _find_groups(position.stones, opp_color)

    # --- Run all detectors ---
    candidates: list[InstinctResult] = []

    result = _detect_cut(mx, my, own_adj, opp_adj, opp_groups, correct_move_gtp)
    if result:
        candidates.append(result)

    result = _detect_push(mx, my, own_adj, opp_adj, own_set, n, correct_move_gtp)
    if result:
        candidates.append(result)

    result = _detect_hane(mx, my, own_adj, opp_adj, own_diag, opp_groups, correct_move_gtp)
    if result:
        candidates.append(result)

    result = _detect_descent(mx, my, own_adj, n, correct_move_gtp)
    if result:
        candidates.append(result)

    result = _detect_extend(mx, my, own_adj, opp_adj, own_diag, own_set, opp_set, n, correct_move_gtp)
    if result:
        candidates.append(result)

    # Filter by min_confidence_to_log
    cfg = config or {}
    min_log = cfg.get("min_confidence_to_log", 0.40)
    results = [r for r in candidates if r.confidence >= min_log]

    # Sort by confidence descending
    results.sort(key=lambda r: r.confidence, reverse=True)

    # Deduplicate by instinct type (keep highest confidence)
    seen: dict[str, InstinctResult] = {}
    for r in results:
        if r.instinct not in seen or r.confidence > seen[r.instinct].confidence:
            seen[r.instinct] = r
    results = sorted(seen.values(), key=lambda r: r.confidence, reverse=True)

    # Select primary
    min_surface = cfg.get("min_confidence_to_surface", 0.65)
    clarity = cfg.get("clarity_threshold", 0.15)
    max_ambig = cfg.get("max_instincts_before_ambiguous", 4)
    results = select_primary(results, min_surface, clarity, max_ambig)

    return results
