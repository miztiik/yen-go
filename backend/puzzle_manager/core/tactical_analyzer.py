"""
Tactical pattern analysis for puzzle positions.

Analyzes Go puzzle positions to detect tactical patterns (ladder, snapback,
eye-shape, seki, etc.) for:
- Auto-tagging technique detection (YT)
- Position validation (flag broken puzzles)
- Difficulty scoring signals (complexity input)
- Enhanced hint generation (YH)

Reuses the existing Board/Group infrastructure.

Design principles:
- Pure functions: analyze_tactics() takes SGFGame, returns TacticalAnalysis
- No side effects, no state
- Same input → identical output
- Graceful degradation: individual detector failures don't block others

See docs/architecture/backend/tactical-analyzer.md for design rationale.
See TODO/puzzle-quality-scorer/implementation-plan.md for the full plan.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

from backend.puzzle_manager.core.board import Board, Group
from backend.puzzle_manager.core.primitives import Color, Move, Point

if TYPE_CHECKING:
    from backend.puzzle_manager.core.sgf_parser import SGFGame

logger = logging.getLogger("tactical_analyzer")


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


class GroupStatus(Enum):
    """Assessment of a group's viability."""

    ALIVE = "alive"
    DEAD = "dead"
    UNSETTLED = "unsettled"


class CaptureType(Enum):
    """Classification of capture pattern in the puzzle."""

    NONE = "none"
    TRIVIAL = "trivial"       # 1-liberty group, 1-move capture
    FORCED = "forced"         # Multi-move forced sequence
    LADDER = "ladder"         # Ladder capture
    SNAPBACK = "snapback"     # Snapback capture
    NET = "net"               # Net/geta capture


class InstinctType(Enum):
    """Named tactical instinct patterns detected via board simulation."""

    EXTEND_FROM_ATARI = "extend_from_atari"
    CONNECT_AGAINST_PEEP = "connect_against_peep"
    HANE_AT_HEAD_OF_TWO = "hane_at_head_of_two"
    BLOCK_THRUST = "block_thrust"


@dataclass
class WeakGroup:
    """A group that is tactically vulnerable."""

    color: Color
    stones: frozenset[Point]
    liberties: int
    status: GroupStatus
    can_escape: bool
    eye_count: int


@dataclass(frozen=True)
class LadderResult:
    """Result of ladder detection."""

    outcome: str          # "captured" | "escaped" | "breaker"
    depth: int            # Moves in the chase
    breaker_point: Point | None = None  # Location of ladder breaker (if any)


@dataclass
class TacticalAnalysis:
    """Complete tactical analysis of a puzzle position.

    Produced by analyze_tactics(). Consumed by:
    - tagger.py (auto-tagging via derive_auto_tags)
    - quality.py (tactical quality signals)
    - hints.py (tactic-aware hint generation)
    - classifier.py (difficulty scoring signals)
    """

    # Detected techniques (for auto-tagging)
    has_ladder: LadderResult | None = None
    has_snapback: bool = False
    capture_type: CaptureType = CaptureType.NONE
    has_seki: bool = False
    instinct: InstinctType | None = None

    # Group assessment (for validation and difficulty)
    player_weak_groups: list[WeakGroup] = field(default_factory=list)
    opponent_weak_groups: list[WeakGroup] = field(default_factory=list)

    # Derived metrics
    tactical_complexity: int = 0      # 0-6 scale (count of active features)
    position_valid: bool = True       # Does objective match position?
    validation_notes: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def analyze_tactics(game: SGFGame) -> TacticalAnalysis:
    """Run complete tactical analysis on a puzzle position.

    Builds a Board from the initial position (AB/AW), extracts the first
    correct move, and runs all tactical detectors.

    Args:
        game: Parsed SGF game with initial position and solution tree.

    Returns:
        TacticalAnalysis with all findings. On error, returns a default
        analysis with position_valid=True and no detected patterns.
    """
    analysis = TacticalAnalysis()

    if not game.has_solution:
        analysis.validation_notes.append("no solution tree")
        return analysis

    first_move_info = game.get_first_move()
    if not first_move_info:
        analysis.validation_notes.append("no first correct move")
        return analysis

    player_color, first_move_point = first_move_info

    try:
        board = _build_board(game)
    except Exception as e:
        logger.debug("Failed to build board for tactical analysis: %s", e)
        analysis.validation_notes.append(f"board build failed: {e}")
        return analysis

    # Run all detectors — each one is independent and failure-isolated
    analysis.has_ladder = _safe_detect(
        lambda: detect_ladder(board, first_move_point, player_color),
        "ladder",
    )

    analysis.has_snapback = _safe_detect(
        lambda: detect_snapback(board, first_move_point, player_color),
        "snapback",
    ) or False

    analysis.capture_type = _safe_detect(
        lambda: detect_capture_pattern(board, first_move_point, player_color),
        "capture_pattern",
    ) or CaptureType.NONE

    analysis.instinct = _safe_detect(
        lambda: detect_instinct_pattern(board, first_move_point, player_color),
        "instinct",
    )

    # Group assessment
    player_weak = _safe_detect(
        lambda: find_weak_groups(board, player_color),
        "player_weak_groups",
    ) or []
    opponent_weak = _safe_detect(
        lambda: find_weak_groups(board, player_color.opponent()),
        "opponent_weak_groups",
    ) or []
    analysis.player_weak_groups = player_weak
    analysis.opponent_weak_groups = opponent_weak

    # Seki detection (on initial position)
    analysis.has_seki = _safe_detect(
        lambda: detect_seki(board, player_color),
        "seki",
    ) or False

    # Compute derived metrics
    analysis.tactical_complexity = compute_tactical_complexity(analysis)

    # Position validation
    valid, notes = validate_position(board, game, analysis)
    analysis.position_valid = valid
    analysis.validation_notes = notes

    return analysis


# ---------------------------------------------------------------------------
# Board construction (reuses pattern from hints.py / solution_tagger.py)
# ---------------------------------------------------------------------------


def _build_board(game: SGFGame) -> Board:
    """Build a Board from the initial position in an SGF game.

    Args:
        game: Parsed SGF game.

    Returns:
        Board with stones placed per AB/AW properties.
    """
    board = Board(game.board_size)
    board.setup_position(game.black_stones, game.white_stones)
    return board


# ---------------------------------------------------------------------------
# Detector: Ladder
# ---------------------------------------------------------------------------


def detect_ladder(
    board: Board,
    first_move: Point,
    player_color: Color,
) -> LadderResult | None:
    """Detect if the first move initiates or continues a ladder.

    Algorithm (board-simulation with 1-step lookahead):
    1. Play the first move on a copy
    2. Check if any adjacent opponent group is now in atari
    3. Simulate the chase: runner extends at single liberty, must get
       exactly 2 liberties (standard ladder shape)
    4. Chaser picks the atari move via 1-step lookahead: for each
       candidate, simulate the runner's next extension and prefer the
       move where the runner still gets exactly 2 liberties (correct
       ladder diagonal). This avoids picking a dead-end atari that
       lets the runner escape on the next iteration.
    5. If chase continues ≥3 steps → confirmed ladder

    Design note: A naive approach of picking the first sorted atari move
    fails when multiple moves produce atari but only one continues the
    ladder diagonal. The lookahead adds one extra Board.copy() per
    candidate per iteration but guarantees correct move selection.

    Also checks if the first move is a ladder breaker: an opponent group
    was in atari before the move and escapes after the move.

    Args:
        board: Board with initial position.
        first_move: The first correct move point.
        player_color: Color of the player making the move.

    Returns:
        LadderResult if ladder detected, None otherwise.
    """
    sim_board = board.copy()
    try:
        sim_board.play(Move.play(player_color, first_move))
    except ValueError:
        return None

    # Check if any adjacent opponent group is now in atari
    for neighbor in first_move.neighbors(sim_board.size):
        opp_color = sim_board.get(neighbor)
        if opp_color == player_color.opponent():
            group = sim_board.get_group(neighbor)
            if group and len(group.liberties) == 1:
                # Opponent group in atari — try to verify ladder chase
                depth = _trace_ladder_chase(
                    sim_board, group, player_color, max_depth=30,
                )
                if depth >= 3:
                    return LadderResult(outcome="captured", depth=depth)

    # Check for ladder breaker: before the move, was there an atari opponent
    # group that now has more liberties?
    for neighbor in first_move.neighbors(board.size):
        opp_color = board.get(neighbor)
        if opp_color == player_color.opponent():
            group_before = board.get_group(neighbor)
            if group_before and len(group_before.liberties) == 1:
                # Was in atari before — check after move
                group_after = sim_board.get_group(neighbor)
                if group_after and len(group_after.liberties) > 1:
                    return LadderResult(
                        outcome="breaker",
                        depth=0,
                        breaker_point=first_move,
                    )

    return None


def _trace_ladder_chase(
    board: Board,
    fleeing_group: Group,
    chaser_color: Color,
    max_depth: int = 30,
) -> int:
    """Simulate a ladder chase and return the depth (number of chase iterations).

    Algorithm:
    1. Runner extends at their single liberty
    2. After extension, runner should have exactly 2 liberties
    3. Chaser plays at one of those liberties to re-atari
    4. Repeat until captured, escaped, or max_depth reached

    Args:
        board: Board state after the initial atari move.
        fleeing_group: Opponent group currently in atari.
        chaser_color: Color of the chasing player.
        max_depth: Maximum chase iterations.

    Returns:
        Number of completed chase iterations. ≥3 means confirmed ladder.
    """
    sim = board.copy()
    runner_color = chaser_color.opponent()
    ref_stone = next(iter(fleeing_group.stones))
    chase_count = 0

    for _ in range(max_depth):
        current_group = sim.get_group(ref_stone)
        if current_group is None:
            break  # Group captured
        if len(current_group.liberties) != 1:
            break  # Not in atari — escaped

        # Runner extends at their single liberty
        escape_point = next(iter(current_group.liberties))
        try:
            sim.play(Move.play(runner_color, escape_point))
        except ValueError:
            break  # Can't extend

        # After extension, check runner's liberties
        extended_group = sim.get_group(escape_point)
        if extended_group is None or len(extended_group.liberties) != 2:
            break  # Not a standard ladder shape

        # Chaser must find a move that puts runner back in atari.
        # Multiple moves may produce atari; prefer the one that continues
        # the ladder shape (runner still has 2 libs after next extension).
        atari_candidates: list[Point] = []
        for lib in sorted(extended_group.liberties, key=lambda p: (p.x, p.y)):
            test_board = sim.copy()
            try:
                test_board.play(Move.play(chaser_color, lib))
            except ValueError:
                continue

            chased_group = test_board.get_group(escape_point)
            if chased_group and len(chased_group.liberties) == 1:
                atari_candidates.append(lib)

        if not atari_candidates:
            break

        # Pick the candidate whose 1-step lookahead continues the ladder
        chosen: Point | None = None
        for cand in atari_candidates:
            la_board = sim.copy()
            la_board.play(Move.play(chaser_color, cand))
            chased = la_board.get_group(escape_point)
            if chased is None:
                chosen = cand  # Runner captured = good
                break
            next_escape = next(iter(chased.liberties))
            try:
                la_board.play(Move.play(runner_color, next_escape))
                la_group = la_board.get_group(next_escape)
                if la_group and len(la_group.liberties) == 2:
                    chosen = cand  # Continues ladder shape
                    break
            except ValueError:
                chosen = cand  # Runner can't extend
                break

        if chosen is None:
            chosen = atari_candidates[0]  # Fallback to first candidate

        sim.play(Move.play(chaser_color, chosen))
        ref_stone = escape_point
        chase_count += 1

    return chase_count


# ---------------------------------------------------------------------------
# Detector: Snapback
# ---------------------------------------------------------------------------


def detect_snapback(
    board: Board,
    first_move: Point,
    player_color: Color,
) -> bool:
    """Detect if the first move creates a snapback pattern.

    Snapback: player sacrifices stone(s) that get captured, then recaptures
    a larger group.

    Algorithm (board-simulation with group-size comparison):
    1. Play the first move → check if our group has exactly 1 liberty (bait)
    2. Simulate opponent capturing our bait at that liberty
    3. Check if opponent's capturing group now has exactly 1 liberty
    4. Compare group sizes: opponent_group_size > sacrificed_stones → snapback

    Design note: We do NOT play the actual recapture move. The Board's ko
    detection treats the recapture as a ko violation (single stone captured
    into a single-liberty group triggers the ko check). Since we only need
    to confirm that the recapture would net more stones than sacrificed,
    comparing group sizes is equivalent and avoids the false ko. This is a
    deliberate design choice — fixing the Board's ko logic would be a
    higher-risk change with ripple effects across the codebase.

    Args:
        board: Board with initial position.
        first_move: The first correct move point.
        player_color: Color of the player making the move.

    Returns:
        True if snapback pattern detected.
    """
    sim_board = board.copy()
    try:
        sim_board.play(Move.play(player_color, first_move))
    except ValueError:
        return False

    # Check if the played stone's group has exactly 1 liberty (bait)
    our_group = sim_board.get_group(first_move)
    if our_group is None or len(our_group.liberties) != 1:
        return False

    our_stones_count = len(our_group.stones)
    atari_liberty = next(iter(our_group.liberties))

    # Simulate opponent capturing our bait
    capture_board = sim_board.copy()
    try:
        captured_by_opp = capture_board.play(
            Move.play(player_color.opponent(), atari_liberty)
        )
    except ValueError:
        return False

    if len(captured_by_opp) == 0:
        return False  # Opponent didn't actually capture

    # Check if opponent's capturing stone(s) now have 1 liberty
    opp_group = capture_board.get_group(atari_liberty)
    if opp_group is None or len(opp_group.liberties) != 1:
        return False

    # Snapback confirmed: opponent's group is larger than our sacrifice
    # and has only 1 liberty (will be recaptured). No need to play the
    # recapture — this avoids false ko detection by the Board.
    return len(opp_group.stones) > our_stones_count


# ---------------------------------------------------------------------------
# Detector: Capture pattern classification
# ---------------------------------------------------------------------------


def detect_capture_pattern(
    board: Board,
    first_move: Point,
    player_color: Color,
) -> CaptureType:
    """Classify the type of capture pattern in the puzzle.

    Checks what happens when the first move is played:
    - Immediate single-liberty capture → TRIVIAL
    - Ladder capture → LADDER (defers to ladder detector)
    - Snapback → SNAPBACK (defers to snapback detector)
    - Net/geta: move reduces opponent to 1 liberty with no direct
      atari-escape sequence → NET
    - Multi-move forced → FORCED
    - No capture → NONE

    Args:
        board: Board with initial position.
        first_move: The first correct move point.
        player_color: Color of the player making the move.

    Returns:
        CaptureType classification.
    """
    # Check for immediate capture
    sim_board = board.copy()
    try:
        captured = sim_board.play(Move.play(player_color, first_move))
    except ValueError:
        return CaptureType.NONE

    if captured:
        # Check for trivial: captured a 1-liberty group in 1 move
        # We know it's trivial if the captured stones formed a group
        # with exactly 1 liberty before the move
        for neighbor in first_move.neighbors(board.size):
            if board.get(neighbor) == player_color.opponent():
                group_before = board.get_group(neighbor)
                if group_before and len(group_before.liberties) == 1:
                    # Was already in atari — trivial capture
                    return CaptureType.TRIVIAL

        # Non-trivial immediate capture
        return CaptureType.FORCED

    # No immediate capture — check if move creates atari (net/forced)
    for neighbor in first_move.neighbors(sim_board.size):
        if sim_board.get(neighbor) == player_color.opponent():
            group = sim_board.get_group(neighbor)
            if group and len(group.liberties) == 1:
                # Created atari — could be net or forced
                # Net: opponent can't escape by extending
                escape_point = next(iter(group.liberties))
                escape_board = sim_board.copy()
                try:
                    escape_board.play(
                        Move.play(player_color.opponent(), escape_point)
                    )
                except ValueError:
                    # Can't escape (suicide) → net/geta
                    return CaptureType.NET

                # Can extend — check resulting liberties
                escaped_group = escape_board.get_group(escape_point)
                if escaped_group and len(escaped_group.liberties) <= 2:
                    # Still very few liberties after escape → net
                    return CaptureType.NET
                else:
                    return CaptureType.FORCED

            elif group and len(group.liberties) == 2:
                # Two liberties — check if both are controlled → net
                controlled = 0
                for lib in group.liberties:
                    # Check if player controls (adjacent player stones)
                    adjacent_player = any(
                        sim_board.get(n) == player_color
                        for n in lib.neighbors(sim_board.size)
                    )
                    if adjacent_player:
                        controlled += 1
                if controlled >= 2:
                    return CaptureType.NET

    return CaptureType.NONE


# ---------------------------------------------------------------------------
# Detector: Eye counting
# ---------------------------------------------------------------------------


def count_eyes(board: Board, group: Group) -> int:
    """Count the number of true eyes in a group.

    Algorithm (adapted from gogamev4.0 _is_eye + _is_real_eye):
    - An eye is an empty point where:
      1. All orthogonal neighbors are same color or board edge
      2. At least 3 of 4 diagonal neighbors are same color or board edge
         (or all diagonals if the point is on the edge/corner)
      3. All orthogonal neighbors belong to the SAME group (real eye test)

    Args:
        board: Current board state.
        group: The group to count eyes for.

    Returns:
        Number of true eyes.
    """
    group_color = group.color
    eye_count = 0

    for liberty in group.liberties:
        if _is_true_eye(board, liberty, group_color, group.stones):
            eye_count += 1

    return eye_count


def _is_true_eye(
    board: Board,
    point: Point,
    color: Color,
    group_stones: set[Point],
) -> bool:
    """Check if an empty point is a true eye for the given color.

    A true eye requires:
    1. All orthogonal neighbors are same-color stones or board edge
    2. Diagonal check: at most 1 diagonal is opponent (0 if point is on edge)
    3. All orthogonal stone neighbors belong to the same connected group

    Args:
        board: Current board state.
        point: The empty point to check.
        color: The color that would own this eye.
        group_stones: Stones in the owning group.

    Returns:
        True if the point is a true eye for color.
    """
    if not board.is_empty(point):
        return False

    # 1. All orthogonal neighbors must be same color or edge
    orthogonal = point.neighbors(board.size)
    for n in orthogonal:
        stone_color = board.get(n)
        if stone_color != color:
            return False  # Empty or opponent stone

    # 2. Diagonal check
    diagonals = _get_diagonals(point, board.size)
    max_opponent_diag = 0 if len(orthogonal) < 4 else 1  # Stricter on edge
    opponent_diag = 0
    for d in diagonals:
        stone_at_diag = board.get(d)
        if stone_at_diag == color.opponent():
            opponent_diag += 1

    if opponent_diag > max_opponent_diag:
        return False

    # 3. Real eye test: all orthogonal stone neighbors in same group
    for n in orthogonal:
        if n not in group_stones:
            return False

    return True


def _get_diagonals(point: Point, board_size: int) -> list[Point]:
    """Get diagonal neighbors within board bounds."""
    result = []
    for dx, dy in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
        nx, ny = point.x + dx, point.y + dy
        if 0 <= nx < board_size and 0 <= ny < board_size:
            result.append(Point(nx, ny))
    return result


# ---------------------------------------------------------------------------
# Detector: Group status assessment
# ---------------------------------------------------------------------------


def assess_group_status(board: Board, group: Group) -> GroupStatus:
    """Assess whether a group is alive, dead, or unsettled.

    Decision tree (adapted from gogamev4.0 _analyze_group):
    - 0 liberties → DEAD (already captured)
    - 2+ true eyes → ALIVE
    - 1 eye + ≥3 liberties → UNSETTLED (may live)
    - 0 eyes + ≥4 liberties → UNSETTLED (potential to make eyes)
    - 0 or 1 eye + ≤2 liberties → DEAD (can't make two eyes)
    - Otherwise → UNSETTLED

    Args:
        board: Current board state.
        group: The group to assess.

    Returns:
        GroupStatus classification.
    """
    if group.is_captured:
        return GroupStatus.DEAD

    lib_count = len(group.liberties)
    eye_count = count_eyes(board, group)

    if eye_count >= 2:
        return GroupStatus.ALIVE

    if eye_count == 1:
        if lib_count >= 3:
            return GroupStatus.UNSETTLED
        else:
            return GroupStatus.DEAD

    # 0 eyes
    if lib_count >= 4:
        return GroupStatus.UNSETTLED
    elif lib_count >= 2:
        # Check if group has internal space for eye-making
        internal_space = _count_internal_space(board, group)
        if internal_space >= 3:
            return GroupStatus.UNSETTLED
        return GroupStatus.DEAD
    else:
        return GroupStatus.DEAD


def _count_internal_space(board: Board, group: Group) -> int:
    """Count empty points that are completely surrounded by the group.

    Internal space indicates potential for eye formation.

    Args:
        board: Current board state.
        group: The group to analyze.

    Returns:
        Number of internal empty points.
    """
    internal = 0
    checked: set[Point] = set()

    for liberty in group.liberties:
        if liberty in checked:
            continue
        checked.add(liberty)

        # An internal liberty has all neighbors as same-color stones or edge
        all_surrounded = True
        for n in liberty.neighbors(board.size):
            if board.get(n) != group.color:
                if board.is_empty(n) and n in group.liberties:
                    continue  # Another liberty of the same group — still internal
                all_surrounded = False
                break

        if all_surrounded:
            internal += 1

    return internal


# ---------------------------------------------------------------------------
# Detector: Weak group finding
# ---------------------------------------------------------------------------


def find_weak_groups(board: Board, color: Color) -> list[WeakGroup]:
    """Find all weak/vulnerable groups of the given color.

    A group is weak if:
    - ≤1 liberty (critical — in atari or captured)
    - 2 liberties (weak — can be put in atari)
    - 3 liberties + 0 eyes (unsettled — may collapse)

    Args:
        board: Current board state.
        color: Color of groups to scan.

    Returns:
        List of WeakGroup assessments, sorted by liberty count (ascending).
    """
    all_stones = board.get_all_stones(color)
    visited: set[Point] = set()
    weak_groups: list[WeakGroup] = []

    for stone in all_stones:
        if stone in visited:
            continue

        group = board.get_group(stone)
        if group is None:
            continue
        visited.update(group.stones)

        lib_count = len(group.liberties)

        # Only assess groups with ≤3 liberties as potentially weak
        if lib_count > 3:
            continue

        status = assess_group_status(board, group)
        eye_ct = count_eyes(board, group)

        # Determine escape potential (can the group gain liberties by extending?)
        can_escape = _assess_escape_potential(board, group)

        if status != GroupStatus.ALIVE:
            weak_groups.append(WeakGroup(
                color=color,
                stones=frozenset(group.stones),
                liberties=lib_count,
                status=status,
                can_escape=can_escape,
                eye_count=eye_ct,
            ))

    # Sort by liberty count (most critical first)
    weak_groups.sort(key=lambda wg: wg.liberties)
    return weak_groups


def _assess_escape_potential(board: Board, group: Group) -> bool:
    """Assess if a group can escape by extending into open space.

    A group can escape if extending at any liberty would gain additional
    liberties (net liberty increase after the extension).

    Args:
        board: Current board state.
        group: The group to assess.

    Returns:
        True if the group has escape potential.
    """
    current_libs = len(group.liberties)
    color = group.color

    for liberty in group.liberties:
        test_board = board.copy()
        try:
            test_board.play(Move.play(color, liberty))
        except ValueError:
            continue  # Suicide or illegal — can't extend here

        extended = test_board.get_group(liberty)
        if extended and len(extended.liberties) > current_libs:
            return True

    return False


# ---------------------------------------------------------------------------
# Detector: Seki
# ---------------------------------------------------------------------------


def detect_seki(board: Board, player_color: Color) -> bool:
    """Detect if the position contains a seki (mutual life) situation.

    Seki: two groups of different colors share liberties such that
    neither side can capture the other without getting captured first.

    Simplified detection (from gogamev4.0):
    - Find adjacent opponent groups that share exactly 1-2 liberties
    - Both groups have exactly those shared liberties as their only liberties
    - Neither side can play at the shared liberties without self-atari

    Args:
        board: Current board state.
        player_color: Player's color.

    Returns:
        True if seki detected.
    """
    opponent_color = player_color.opponent()
    player_stones = board.get_all_stones(player_color)
    visited_pairs: set[tuple[frozenset[Point], frozenset[Point]]] = set()
    visited_groups: set[frozenset[Point]] = set()

    for stone in player_stones:
        player_group = board.get_group(stone)
        if player_group is None:
            continue

        p_stones = frozenset(player_group.stones)
        if p_stones in visited_groups:
            continue
        visited_groups.add(p_stones)

        # Find adjacent opponent groups
        for lib in player_group.liberties:
            for neighbor in lib.neighbors(board.size):
                if board.get(neighbor) == opponent_color:
                    opp_group = board.get_group(neighbor)
                    if opp_group is None:
                        continue

                    o_stones = frozenset(opp_group.stones)
                    pair_key = (
                        min(p_stones, o_stones),
                        max(p_stones, o_stones),
                    )
                    if pair_key in visited_pairs:
                        continue
                    visited_pairs.add(pair_key)

                    # Check shared liberties
                    shared_libs = player_group.liberties & opp_group.liberties
                    if len(shared_libs) < 1 or len(shared_libs) > 2:
                        continue

                    # Both groups' liberties are ONLY the shared ones
                    p_libs = player_group.liberties
                    o_libs = opp_group.liberties
                    if p_libs != shared_libs or o_libs != shared_libs:
                        continue

                    # Neither can play at shared liberties without
                    # ending up in self-atari or suicide
                    neither_can_play = True
                    for sl in shared_libs:
                        for c in (player_color, opponent_color):
                            test_board = board.copy()
                            try:
                                test_board.play(Move.play(c, sl))
                                # If move succeeded, check if the played
                                # group is now in atari or worse
                                played_group = test_board.get_group(sl)
                                if played_group and len(played_group.liberties) >= 2:
                                    neither_can_play = False
                                    break
                            except ValueError:
                                pass  # Suicide/illegal — good, confirms seki
                        if not neither_can_play:
                            break

                    if neither_can_play:
                        return True

    return False


# ---------------------------------------------------------------------------
# Detector: Instinct patterns
# ---------------------------------------------------------------------------


def detect_instinct_pattern(
    board: Board,
    first_move: Point,
    player_color: Color,
) -> InstinctType | None:
    """Detect named tactical instinct patterns at the first move.

    Checks 4 key patterns via board-state inspection:
    - Extend from atari: first move extends a player group that was in atari
    - Connect against peep: first move connects two player groups
    - Hane at head of two: first move continues the line of 2 opponent stones
    - Block thrust: first move blocks an opponent's invasion/cut

    Design note on hane detection: the move must be adjacent to one endpoint
    of a 2-stone opponent line AND be on the directional extension of that
    line (endpoint + direction_vector == first_move). Checking
    len(opponent_neighbors) == 2 does NOT work because a single point can
    be orthogonally adjacent to at most one stone of a 2-stone line.

    Args:
        board: Board with initial position.
        first_move: The first correct move point.
        player_color: Color of the player.

    Returns:
        InstinctType if a pattern is detected, None otherwise.
    """
    opponent_color = player_color.opponent()
    neighbors = first_move.neighbors(board.size)

    # 1. Extend from atari: player group adjacent to first_move is in atari
    for n in neighbors:
        if board.get(n) == player_color:
            group = board.get_group(n)
            if group and len(group.liberties) == 1:
                # This group is in atari and our move extends it
                if first_move in group.liberties:
                    return InstinctType.EXTEND_FROM_ATARI

    # 2. Connect against peep: first move connects 2+ player groups
    player_neighbors: list[Group] = []
    seen_groups: set[frozenset[Point]] = set()
    for n in neighbors:
        if board.get(n) == player_color:
            group = board.get_group(n)
            if group:
                key = frozenset(group.stones)
                if key not in seen_groups:
                    seen_groups.add(key)
                    player_neighbors.append(group)

    if len(player_neighbors) >= 2:
        # Check if an opponent stone is peeping (adjacent to the move point)
        has_peep = any(board.get(n) == opponent_color for n in neighbors)
        if has_peep:
            return InstinctType.CONNECT_AGAINST_PEEP

    # 3. Hane at head of two: move extends the line of exactly 2 opponent stones
    #    The move is adjacent to the END stone of a 2-stone line, on the
    #    extension axis (same row or column).
    for n in neighbors:
        if board.get(n) == opponent_color:
            group = board.get_group(n)
            if group and len(group.stones) == 2:
                other = (group.stones - {n}).pop()
                # Direction from other toward n
                dx = n.x - other.x
                dy = n.y - other.y
                # Move should be at the head: n + (dx, dy)
                if first_move.x == n.x + dx and first_move.y == n.y + dy:
                    return InstinctType.HANE_AT_HEAD_OF_TWO

    # 4. Block thrust: opponent group adjacent, move blocks the cut/invasion point
    for n in neighbors:
        if board.get(n) == opponent_color:
            opp_group = board.get_group(n)
            if opp_group and len(opp_group.liberties) <= 3:
                # Check if the move point was also adjacent to player stones
                # (blocking the cut between player groups)
                adjacent_player = any(
                    board.get(nn) == player_color
                    for nn in first_move.neighbors(board.size)
                    if nn != n
                )
                if adjacent_player:
                    # Move is between player and opponent groups → block
                    return InstinctType.BLOCK_THRUST

    return None


# ---------------------------------------------------------------------------
# Position validation
# ---------------------------------------------------------------------------


def validate_position(
    board: Board,
    game: SGFGame,
    analysis: TacticalAnalysis,
) -> tuple[bool, list[str]]:
    """Check if puzzle objective makes sense given the board position.

    Validates that tagged objectives match the actual board state.
    This flags potentially broken puzzles without rejecting them.

    Args:
        board: Board with initial position.
        game: Parsed SGF game.
        analysis: Tactical analysis results.

    Returns:
        Tuple of (is_valid, validation_notes).
    """
    notes: list[str] = []
    tags = set(game.yengo_props.tags or [])

    # Life-and-death puzzle: should have at least one threatened group
    if tags & {"life-and-death", "living"}:
        all_weak = analysis.player_weak_groups + analysis.opponent_weak_groups
        has_threatened = any(
            g.status in (GroupStatus.DEAD, GroupStatus.UNSETTLED)
            for g in all_weak
        )
        if not has_threatened:
            notes.append(
                "life-and-death tagged but no threatened groups found"
            )

    # Kill objective: opponent should have vulnerable groups
    root_comment = (game.root_comment or "").lower()
    if "kill" in root_comment:
        if not analysis.opponent_weak_groups:
            notes.append("kill objective but no weak opponent groups")

    # Capture puzzle: opponent should have low-liberty groups
    if "capture" in tags:
        has_low_lib = any(
            g.liberties <= 2 for g in analysis.opponent_weak_groups
        )
        if not has_low_lib:
            notes.append("capture tagged but no low-liberty opponent groups")

    return len(notes) == 0, notes


# ---------------------------------------------------------------------------
# Tactical complexity scoring
# ---------------------------------------------------------------------------


def compute_tactical_complexity(analysis: TacticalAnalysis) -> int:
    """Compute tactical complexity as count of active features (0-6 scale).

    Each detected pattern adds 1 to the complexity score.

    Args:
        analysis: Tactical analysis results.

    Returns:
        Integer 0-6 representing tactical complexity.
    """
    score = 0

    if analysis.has_ladder is not None:
        score += 1
    if analysis.has_snapback:
        score += 1
    if analysis.capture_type not in (CaptureType.NONE, CaptureType.TRIVIAL):
        score += 1
    if analysis.has_seki:
        score += 1
    if analysis.instinct is not None:
        score += 1

    # Weak group count contributes
    total_weak = len(analysis.player_weak_groups) + len(analysis.opponent_weak_groups)
    if total_weak >= 3:
        score += 1

    return min(score, 6)


# ---------------------------------------------------------------------------
# Auto-tag derivation (Phase 2 integration)
# ---------------------------------------------------------------------------


def derive_auto_tags(analysis: TacticalAnalysis) -> list[str]:
    """Derive technique tags from tactical analysis.

    Maps detected patterns to YT tag slugs. Uses ENRICH_IF_ABSENT policy
    at the call site — this function just returns candidate tags.

    Args:
        analysis: Complete tactical analysis.

    Returns:
        Sorted list of unique tag slugs to merge into YT.
    """
    tags: set[str] = set()

    # Ladder: confirmed capture with depth ≥ 3
    if (
        analysis.has_ladder is not None
        and analysis.has_ladder.outcome == "captured"
        and analysis.has_ladder.depth >= 3
    ):
        tags.add("ladder")

    # Snapback
    if analysis.has_snapback:
        tags.add("snapback")

    # Net/geta
    if analysis.capture_type == CaptureType.NET:
        tags.add("net")

    # Seki
    if analysis.has_seki:
        tags.add("seki")

    # Instinct-to-tag mapping
    instinct_tags = {
        InstinctType.EXTEND_FROM_ATARI: "escape",
        InstinctType.CONNECT_AGAINST_PEEP: "connection",
        InstinctType.HANE_AT_HEAD_OF_TWO: "tesuji",
    }
    if analysis.instinct in instinct_tags:
        tags.add(instinct_tags[analysis.instinct])

    # Weak groups → life-and-death if not already covered
    all_weak = analysis.player_weak_groups + analysis.opponent_weak_groups
    has_unsettled = any(g.status == GroupStatus.UNSETTLED for g in all_weak)
    if has_unsettled:
        tags.add("life-and-death")

    # Capture tag if there's a non-trivial capture and no more specific tag
    if analysis.capture_type not in (CaptureType.NONE, CaptureType.TRIVIAL):
        if not tags & {"ladder", "snapback", "net"}:
            tags.add("life-and-death")

    return sorted(tags)


# ---------------------------------------------------------------------------
# Tactic-aware hint generation (Phase 4 integration)
# ---------------------------------------------------------------------------


def generate_tactical_hint(analysis: TacticalAnalysis) -> str | None:
    """Generate a tactic-aware conceptual hint from tactical analysis.

    Returns a hint string suitable for YH[1] (technique hint). Returns None
    if no specific pattern was detected.

    Args:
        analysis: Complete tactical analysis.

    Returns:
        Hint text or None.
    """
    if analysis.has_ladder and analysis.has_ladder.outcome == "captured":
        return "This begins the chase."

    if analysis.has_snapback:
        return "Let them capture — then take back more."

    if analysis.has_seki:
        return "Neither side can capture — find the balance."

    if analysis.instinct == InstinctType.EXTEND_FROM_ATARI:
        return "A group is in danger — extend to gain liberties."

    if analysis.instinct == InstinctType.CONNECT_AGAINST_PEEP:
        return "Two groups need to join forces."

    if analysis.instinct == InstinctType.HANE_AT_HEAD_OF_TWO:
        return "Strike at the head of the stones."

    if analysis.capture_type == CaptureType.NET:
        return "Surround the stones — they cannot escape."

    return None


# ---------------------------------------------------------------------------
# Internal: safe detector wrapper
# ---------------------------------------------------------------------------


def _safe_detect(func, name: str):
    """Run a detector function safely, logging errors without failing.

    Args:
        func: Zero-argument callable that returns the detector result.
        name: Detector name for logging.

    Returns:
        Detector result, or None on failure.
    """
    try:
        return func()
    except Exception as e:
        logger.debug("Detector %s failed: %s", name, e)
        return None
