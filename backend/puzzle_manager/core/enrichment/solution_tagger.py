"""
Solution-aware technique tagger for hint generation fallback.

When the primary tagger (core/tagger.py) assigns zero tags, this module
infers technique from what the correct move actually DOES on the board.

Design principles (Cho Chikun / Lee Changho):
- This is a TAGGER, not a hint generator — it returns tags, not hint text
- Only infer when confidence is HIGH or above
- "Do No Harm": if the move effect is ambiguous, return None (no tag)
- Coordinate-only hints are acceptable when technique is uncertain

Confidence model:
    CERTAIN  — ko_created (definitional, from Board ko detection)
    HIGH     — connects (group count decrease is verifiable)
    MEDIUM   — captures (could be tactical, life-and-death, or incidental)
    LOW      — unknown (no detectable effect)

Only CERTAIN and HIGH produce tags. MEDIUM and LOW return None,
allowing the hint generator to emit coordinate-only hints instead
of guessing.

See docs/architecture/backend/hint-architecture.md for full design.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import IntEnum
from typing import TYPE_CHECKING

from backend.puzzle_manager.core.board import Board
from backend.puzzle_manager.core.primitives import Color, Move, Point

if TYPE_CHECKING:
    from backend.puzzle_manager.core.sgf_parser import SGFGame, SolutionNode

logger = logging.getLogger("enrichment.solution_tagger")


class InferenceConfidence(IntEnum):
    """Confidence level for solution-inferred technique."""

    LOW = 0       # No detectable effect — do not emit hint
    MEDIUM = 1    # Captures stones — too ambiguous for specific tag
    HIGH = 2      # Connects groups — verifiable from group count
    CERTAIN = 3   # Ko created — definitional from Board rules


# Minimum confidence required to emit an inferred tag
_EMIT_THRESHOLD = InferenceConfidence.HIGH


@dataclass(frozen=True)
class InferenceResult:
    """Result of solution-aware technique inference.

    Attributes:
        tag: Inferred technique tag, or None if confidence too low.
        effect: Description of the move's observed effect.
        confidence: Confidence level of the inference.
    """

    tag: str | None
    effect: str
    confidence: InferenceConfidence


# Mapping from move effect → (tag, confidence)
# Only effects at HIGH+ confidence produce a tag.
_EFFECT_TO_TAG: dict[str, tuple[str, InferenceConfidence]] = {
    "ko_created": ("ko", InferenceConfidence.CERTAIN),
    "connects": ("connection", InferenceConfidence.HIGH),
    "captures": (None, InferenceConfidence.MEDIUM),   # too ambiguous
    "unknown": (None, InferenceConfidence.LOW),         # no detectable effect
}


def infer_technique_from_solution(game: SGFGame) -> InferenceResult:
    """Infer technique tag by analyzing what the correct move does.

    Plays the correct move on a board copy and classifies the effect:
    - Creates ko → "ko" (CERTAIN)
    - Connects player groups → "connection" (HIGH)
    - Captures stones → None (MEDIUM — too ambiguous for specific tag)
    - No clear effect → None (LOW)

    Args:
        game: Parsed SGF game with solution tree.

    Returns:
        InferenceResult with tag (or None), effect description, and confidence.
    """
    if not game.has_solution:
        return InferenceResult(tag=None, effect="no_solution", confidence=InferenceConfidence.LOW)

    first_move = _get_first_correct_move(game.solution_tree)
    if not first_move:
        return InferenceResult(tag=None, effect="no_move", confidence=InferenceConfidence.LOW)

    try:
        board = Board(game.board_size)
        board.setup_position(game.black_stones, game.white_stones)

        player_color = game.player_to_move
        groups_before = _count_groups(board, player_color)

        board_after = board.copy()
        move = Move(color=player_color, point=first_move)
        captured = board_after.play(move)

        # Classify move effect (ordered by confidence, highest first)
        # Ko > connects > captures > unknown
        # Connects checked before captures: a move that both connects
        # and captures is a connection play (HIGH confidence).
        if board_after.ko_point is not None:
            effect = "ko_created"
        else:
            groups_after = _count_groups(board_after, player_color)
            if groups_after < groups_before:
                effect = "connects"
            elif len(captured) > 0:
                effect = "captures"
            else:
                effect = "unknown"

        tag, confidence = _EFFECT_TO_TAG[effect]

        logger.debug(
            f"Solution-inferred: {effect} → tag={tag}, confidence={confidence.name}"
        )

        return InferenceResult(tag=tag, effect=effect, confidence=confidence)

    except Exception as e:
        logger.debug(f"Solution-aware inference failed: {e}")
        return InferenceResult(tag=None, effect="error", confidence=InferenceConfidence.LOW)


def move_captures_stones(
    game: SGFGame,
    move_point: Point,
    player_color: Color,
) -> bool:
    """Check if playing at move_point captures any opponent stones.

    Builds a board from the initial position, plays the move, and
    checks whether any opponent stones were captured.

    Args:
        game: Parsed SGF game.
        move_point: The candidate move point.
        player_color: Color of the player making the move.

    Returns:
        True if the move captures at least one opponent stone.
    """
    try:
        board = Board(game.board_size)
        board.setup_position(game.black_stones, game.white_stones)
        move = Move(color=player_color, point=move_point)
        captured = board.play(move)
        return len(captured) > 0
    except Exception as e:
        logger.debug(f"Capture check failed: {e}")
        return False


# --- Internal helpers ---


def _get_first_correct_move(solution_tree: SolutionNode) -> Point | None:
    """Get the first correct move from solution tree."""
    for child in solution_tree.children:
        if child.is_correct and child.move:
            return child.move
    return None


def _count_groups(board: Board, color: Color) -> int:
    """Count distinct groups of the given color on the board.

    Uses public Board API (get_all_stones + get_group) to avoid
    accessing private attributes.
    """
    all_points = board.get_all_stones(color)
    visited: set[Point] = set()
    group_count = 0

    for point in all_points:
        if point not in visited:
            group = board.get_group(point)
            if group:
                visited.update(group.stones)
                group_count += 1

    return group_count
