"""Thin adapter: algorithm-agnostic frame API for consumers.

Wraps the active frame implementation (GP count-based fill) behind a
stable public interface.  Consumer code imports ``apply_frame``,
``remove_frame``, and ``validate_frame`` from this module without
coupling to a specific algorithm.

Created as part of the GP Frame Swap initiative
(20260313-1000-feature-gp-frame-swap, OPT-1).
"""

from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass

try:
    from models.position import Color, Position
except ImportError:
    from ..models.position import Color, Position

try:
    from analyzers.tsumego_frame_gp import apply_gp_frame
except ImportError:
    from .tsumego_frame_gp import apply_gp_frame

logger = logging.getLogger(__name__)


@dataclass
class FrameResult:
    """Algorithm-agnostic result of frame generation."""

    position: Position
    frame_stones_added: int
    attacker_color: Color


def apply_frame(
    position: Position,
    *,
    margin: int = 2,
    ko: bool = False,
    komi: float = 0.0,
    offence_to_win: int = 5,
) -> FrameResult:
    """Apply a tsumego frame to *position* using the active algorithm (GP).

    In tsumego, the player to move is typically the attacker — the one
    who needs a surrounding wall to prevent escape.  The GP algorithm
    uses a geometric heuristic to guess the attacker, but this fails for
    puzzles where the majority of stones belong to the defender (e.g.,
    a White chase puzzle with 5 Black stones and 1 White stone).

    When the heuristic disagrees with ``player_to_move``, we override
    the attacker to be ``player_to_move``.  This ensures the frame's
    solid outer wall belongs to the side that is attacking.

    Args:
        position: Board position with puzzle stones.
        margin: Padding around bounding box (default 2).
        ko: Whether the puzzle involves ko (default False).
        komi: Komi for territory balance calculation (default 0).
        offence_to_win: Extra offense advantage (default 5).

    Returns:
        FrameResult with framed position, stone count, and attacker color.
    """
    # In tsumego the player to move attacks — override the heuristic
    # when it disagrees with PL. This fixes White-to-move chase puzzles
    # where Black has more stones (making the heuristic pick Black as
    # attacker) but White is actually the one chasing/capturing.
    attacker_override = position.player_to_move

    gp_result = apply_gp_frame(
        position,
        margin=margin,
        komi=komi,
        ko=ko,
        offence_to_win=offence_to_win,
        attacker_override=attacker_override,
    )
    logger.info(
        "Frame result: attacker=%s, stones_added=%d, black_to_attack=%s, "
        "player_to_move=%s, total_stones=%d",
        gp_result.attacker_color.value, gp_result.frame_stones_added,
        gp_result.black_to_attack, position.player_to_move.value,
        len(gp_result.position.stones),
    )
    return FrameResult(
        position=gp_result.position,
        frame_stones_added=gp_result.frame_stones_added,
        attacker_color=gp_result.attacker_color,
    )


def remove_frame(framed: Position, original: Position) -> Position:
    """Remove the frame, restoring the original position."""
    return original.model_copy(deep=True)


def _opposite(color: Color) -> Color:
    return Color.WHITE if color == Color.BLACK else Color.BLACK


def validate_frame(
    framed_position: Position,
    original_position: Position,
    attacker_color: Color,
    puzzle_stone_coords: frozenset[tuple[int, int]],
) -> tuple[bool, dict]:
    """Validate frame correctness after assembly.

    Checks:
      1. Defender frame stones form a single connected component
      2. Attacker frame stones form a single connected component
      3. No dead frame stone (isolated with zero stone neighbors)

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
        """Count stones with zero same-color AND zero any-color neighbors."""
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

    is_valid = dead_def == 0 and dead_atk == 0

    if def_components > 1 or atk_components > 1:
        diagnostics["connectivity_warning"] = True
        logger.info(
            "Frame has %d defender + %d attacker components — "
            "puzzle geometry may split frameable area.",
            def_components, atk_components,
        )

    return is_valid, diagnostics


def get_allow_moves_with_fallback(
    position: Position,
    entropy_roi: object | None = None,
    margin: int = 2,
) -> list[str]:
    """Get allowMoves using entropy ROI with fallback to bounding box.

    Prefers entropy-based contested region when available, otherwise
    falls back to Position's rectangular bounding box approach.
    """
    if entropy_roi is not None and getattr(entropy_roi, "contested_region", None):
        from analyzers.entropy_roi import get_roi_allow_moves
        occupied = frozenset((s.x, s.y) for s in position.stones)
        return get_roi_allow_moves(entropy_roi, position.board_size, margin=margin, occupied=occupied)
    return position.get_puzzle_region_moves(margin=margin)
