"""Match problem diagrams with their solution diagrams.

Given a list of problem board crops and a list of answer/key board
crops, pairs them via stone-position similarity and extracts solution
moves by diffing the problem and answer positions.

Strategy:
  1. Recognize all boards (problem + answer) via image_to_board.
  2. For each answer board, find the problem board with highest
     stone-position overlap (Jaccard similarity on occupied cells).
  3. Extract new stones in the answer that aren't in the problem
     — these are the solution moves.
  4. Detect digits on answer stones to order solution moves.
  5. Compute confidence scores at board and match level.

Usage:
    from tools.pdf_to_sgf.problem_matcher import match_problems

    matches = match_problems(problem_boards, answer_boards)
    for m in matches:
        print(f"Problem {m.problem_index} → Answer {m.answer_index}")
        print(f"  Moves: {m.solution_moves}")
        print(f"  Confidence: {m.confidence.overall:.2f}")
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from PIL import Image

from tools.core.image_to_board import (
    BLACK,
    WHITE,
    EMPTY,
    RecognitionConfig,
    RecognizedPosition,
    recognize_position,
    detect_digit,
)
from tools.core.sgf_types import Color, Point
from tools.pdf_to_sgf.models import (
    BoardConfidence,
    MatchConfidence,
    MatchStrategy,
    PuzzleConfidence,
)

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data classes (kept as dataclasses for backward compat with tests)
# ---------------------------------------------------------------------------


@dataclass
class SolutionMove:
    """A single move in a solution sequence."""

    color: Color
    point: Point
    order: int = 0  # 0 = unknown order, 1+ = detected digit
    confidence: float = 0.0  # digit detection confidence


@dataclass
class MatchResult:
    """Result of matching a problem board to its answer board."""

    problem_index: int
    answer_index: int
    similarity: float  # Jaccard similarity of shared stone positions
    problem_pos: RecognizedPosition
    answer_pos: RecognizedPosition
    solution_moves: list[SolutionMove] = field(default_factory=list)
    problem_label: str = ""  # e.g. "Problem 490" if detected
    strategy: MatchStrategy = MatchStrategy.JACCARD
    board_confidence: BoardConfidence = field(default_factory=BoardConfidence)
    match_confidence: MatchConfidence = field(default_factory=MatchConfidence)
    wrong_moves: list[SolutionMove] = field(default_factory=list)
    variations: list[list[SolutionMove]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Confidence scoring
# ---------------------------------------------------------------------------


def compute_board_confidence(
    pos: RecognizedPosition,
    expected_size: int = 19,
) -> BoardConfidence:
    """Compute confidence metrics for a recognized board position."""
    # Grid completeness: compare actual lines against the detected board
    # dimensions (not the full expected_size) so partial boards aren't penalized.
    actual_lines = pos.n_rows + pos.n_cols
    detected_size = max(pos.n_rows, pos.n_cols)
    max_expected = detected_size * 2
    grid_completeness = min(1.0, actual_lines / max_expected) if max_expected > 0 else 0.0

    # Edge fraction: normalize by how many edges are *expected* based on
    # the board's position on the full grid, not a fixed 4.
    expected_edges = 0
    if pos.board_top == 0:
        expected_edges += 1
    if pos.board_top + pos.n_rows >= expected_size:
        expected_edges += 1
    if pos.board_left == 0:
        expected_edges += 1
    if pos.board_left + pos.n_cols >= expected_size:
        expected_edges += 1

    detected_edges = sum([pos.has_top_edge, pos.has_bottom_edge,
                          pos.has_left_edge, pos.has_right_edge])
    edge_fraction = min(1.0, detected_edges / expected_edges) if expected_edges > 0 else 1.0

    # Stone density: occupied cells / total cells
    total_cells = pos.n_rows * pos.n_cols
    bc, wc = pos.stone_count()
    stone_density = (bc + wc) / total_cells if total_cells > 0 else 0.0

    # Weighted composite
    overall = 0.5 * grid_completeness + 0.3 * edge_fraction + 0.2 * min(stone_density * 5, 1.0)

    return BoardConfidence(
        grid_completeness=round(grid_completeness, 3),
        stone_density=round(stone_density, 3),
        edge_fraction=round(edge_fraction, 3),
        overall=round(overall, 3),
    )


def compute_match_confidence(
    similarity: float,
    problem_pos: RecognizedPosition,
    answer_pos: RecognizedPosition,
    solution_moves: list[SolutionMove],
) -> MatchConfidence:
    """Compute confidence metrics for a problem-answer match."""
    # Stone count ratio
    p_total = sum(problem_pos.stone_count())
    a_total = sum(answer_pos.stone_count())
    if max(p_total, a_total) > 0:
        stone_count_ratio = min(p_total, a_total) / max(p_total, a_total)
    else:
        stone_count_ratio = 0.0

    # Solution plausibility: 1-10 moves is ideal range
    n_moves = len(solution_moves)
    if 1 <= n_moves <= 10:
        solution_plausibility = 1.0
    elif n_moves == 0:
        solution_plausibility = 0.1
    else:
        solution_plausibility = max(0.2, 1.0 - (n_moves - 10) * 0.05)

    # Move ordering: fraction with digit-detected order
    ordered = sum(1 for m in solution_moves if m.order > 0)
    moves_ordered = ordered / n_moves if n_moves > 0 else 0.0

    # Weighted composite
    overall = (
        0.4 * similarity
        + 0.2 * stone_count_ratio
        + 0.2 * solution_plausibility
        + 0.2 * moves_ordered
    )

    return MatchConfidence(
        jaccard_similarity=round(similarity, 3),
        stone_count_ratio=round(stone_count_ratio, 3),
        solution_plausibility=round(solution_plausibility, 3),
        moves_ordered=round(moves_ordered, 3),
        overall=round(overall, 3),
    )


# ---------------------------------------------------------------------------
# Core helpers
# ---------------------------------------------------------------------------


def _board_stone_set(
    pos: RecognizedPosition,
) -> tuple[set[tuple[int, int, str]], set[tuple[int, int]]]:
    """Extract stone positions as sets for comparison.

    Returns:
        (stones_with_color, occupied_positions)
        stones_with_color: {(row, col, color), ...}
        occupied_positions: {(row, col), ...}
    """
    stones: set[tuple[int, int, str]] = set()
    occupied: set[tuple[int, int]] = set()

    for iy, row in enumerate(pos.board):
        for ix, cell in enumerate(row):
            if cell != EMPTY:
                abs_row = pos.board_top + iy
                abs_col = pos.board_left + ix
                stones.add((abs_row, abs_col, cell))
                occupied.add((abs_row, abs_col))

    return stones, occupied


def _jaccard_similarity(set_a: set, set_b: set) -> float:
    """Compute Jaccard similarity between two sets."""
    if not set_a and not set_b:
        return 0.0
    intersection = len(set_a & set_b)
    union = len(set_a | set_b)
    return intersection / union if union > 0 else 0.0


def _detect_move_digits(
    answer_image: Image.Image,
    answer_pos: RecognizedPosition,
    new_stones: set[tuple[int, int, str]],
    config: RecognitionConfig,
) -> dict[tuple[int, int], tuple[int, float]]:
    """Detect move-number digits on new stones in the answer board.

    Returns:
        {(abs_row, abs_col): (digit, confidence), ...}
    """
    digits: dict[tuple[int, int], tuple[int, float]] = {}

    for abs_row, abs_col, cell_color in new_stones:
        # Convert absolute coords back to board-local indices
        local_iy = abs_row - answer_pos.board_top
        local_ix = abs_col - answer_pos.board_left

        # Bounds check
        if not (0 <= local_iy < answer_pos.n_rows and 0 <= local_ix < answer_pos.n_cols):
            continue

        # Get pixel coordinates from grid lines
        if local_ix >= len(answer_pos.grid.x_lines) or local_iy >= len(answer_pos.grid.y_lines):
            continue

        cx = answer_pos.grid.x_lines[local_ix]
        cy = answer_pos.grid.y_lines[local_iy]

        # Compute radius from grid spacing
        radius = max(5, int(min(answer_pos.grid.x_spacing, answer_pos.grid.y_spacing) * 0.4))

        result = detect_digit(answer_image, cx, cy, cell_color, radius=radius, config=config)
        if result.digit > 0:
            digits[(abs_row, abs_col)] = (result.digit, result.confidence)
            log.debug("Digit %d (conf=%.2f) at (%d,%d)", result.digit, result.confidence, abs_row, abs_col)

    return digits


# ---------------------------------------------------------------------------
# Main matching
# ---------------------------------------------------------------------------


def match_problems(
    problem_boards: list[Image.Image],
    answer_boards: list[Image.Image],
    config: RecognitionConfig | None = None,
    *,
    min_similarity: float = 0.3,
) -> list[MatchResult]:
    """Match problem board images to their answer board images.

    Parameters
    ----------
    problem_boards : list[Image.Image]
        Cropped problem board images.
    answer_boards : list[Image.Image]
        Cropped answer/key board images.
    config : RecognitionConfig or None
        Recognition config (defaults to standard config).
    min_similarity : float
        Minimum Jaccard similarity to consider a match.

    Returns
    -------
    list[MatchResult]
        Matched pairs with extracted solution moves, sorted by problem index.
    """
    cfg = config or RecognitionConfig()

    # Recognize all boards
    log.info("Recognizing %d problem boards...", len(problem_boards))
    problem_positions = [recognize_position(img, config=cfg) for img in problem_boards]

    log.info("Recognizing %d answer boards...", len(answer_boards))
    answer_positions = [recognize_position(img, config=cfg) for img in answer_boards]

    # Extract stone sets
    problem_stone_sets = [_board_stone_set(p) for p in problem_positions]
    answer_stone_sets = [_board_stone_set(a) for a in answer_positions]

    # Match by similarity
    used_problems: set[int] = set()
    matches: list[MatchResult] = []

    for ai, (a_stones, a_occ) in enumerate(answer_stone_sets):
        best_pi = -1
        best_sim = 0.0

        for pi, (p_stones, p_occ) in enumerate(problem_stone_sets):
            if pi in used_problems:
                continue

            # Compare occupied positions (ignoring color for robustness)
            sim = _jaccard_similarity(p_occ, a_occ)
            if sim > best_sim:
                best_sim = sim
                best_pi = pi

        if best_pi >= 0 and best_sim >= min_similarity:
            used_problems.add(best_pi)

            # Extract solution moves: stones in answer but not in problem
            p_stones, _ = problem_stone_sets[best_pi]
            a_stones_c, _ = answer_stone_sets[ai]
            new_stones = a_stones_c - p_stones

            # Detect digits on new stones for move ordering
            digit_map = _detect_move_digits(answer_boards[ai], answer_positions[ai], new_stones, cfg)

            moves = _build_ordered_moves(new_stones, digit_map)

            # Detect wrong moves (removed stones = captured)
            wrong = _detect_wrong_moves(problem_positions[best_pi], answer_positions[ai])
            refutations = _detect_refutation_sequences(
                problem_positions[best_pi], answer_positions[ai], moves, wrong,
            )

            board_conf = compute_board_confidence(problem_positions[best_pi])
            match_conf = compute_match_confidence(
                best_sim, problem_positions[best_pi], answer_positions[ai], moves,
            )

            # Generate problem label from index
            problem_label = f"Problem {best_pi + 1}"

            match = MatchResult(
                problem_index=best_pi,
                answer_index=ai,
                similarity=best_sim,
                problem_pos=problem_positions[best_pi],
                answer_pos=answer_positions[ai],
                solution_moves=moves,
                problem_label=problem_label,
                strategy=MatchStrategy.JACCARD,
                board_confidence=board_conf,
                match_confidence=match_conf,
                wrong_moves=wrong,
                variations=refutations,
            )

            log.debug("Matched problem %d → answer %d (sim=%.2f, %d moves, conf=%.2f)",
                       best_pi, ai, best_sim, len(moves), match_conf.overall)
            matches.append(match)
        else:
            log.warning("Answer board %d: no match found (best sim=%.2f)", ai, best_sim)

    # Positional fallback: if no Jaccard matches and same board count
    if not matches and len(problem_boards) == len(answer_boards):
        log.info("Falling back to positional matching (same board count)")
        for idx in range(len(problem_boards)):
            p_stones, _ = problem_stone_sets[idx]
            a_stones, _ = answer_stone_sets[idx]
            new_stones = a_stones - p_stones

            digit_map = _detect_move_digits(answer_boards[idx], answer_positions[idx], new_stones, cfg)
            moves = _build_ordered_moves(new_stones, digit_map)

            # Detect wrong moves (removed stones = captured)
            wrong = _detect_wrong_moves(problem_positions[idx], answer_positions[idx])
            refutations = _detect_refutation_sequences(
                problem_positions[idx], answer_positions[idx], moves, wrong,
            )

            sim = _jaccard_similarity(
                {(r, c) for r, c, _ in p_stones},
                {(r, c) for r, c, _ in a_stones},
            )
            board_conf = compute_board_confidence(problem_positions[idx])
            match_conf = compute_match_confidence(sim, problem_positions[idx], answer_positions[idx], moves)

            matches.append(MatchResult(
                problem_index=idx,
                answer_index=idx,
                similarity=sim,
                problem_pos=problem_positions[idx],
                answer_pos=answer_positions[idx],
                solution_moves=moves,
                problem_label=f"Problem {idx + 1}",
                strategy=MatchStrategy.POSITIONAL,
                board_confidence=board_conf,
                match_confidence=match_conf,
                wrong_moves=wrong,
                variations=refutations,
            ))

    matches.sort(key=lambda m: m.problem_index)
    log.info("Matched %d problem-answer pairs", len(matches))
    return matches


def _build_ordered_moves(
    new_stones: set[tuple[int, int, str]],
    digit_map: dict[tuple[int, int], tuple[int, float]],
) -> list[SolutionMove]:
    """Build solution moves list, ordered by digit when available."""
    moves: list[SolutionMove] = []
    for row, col, cell_color in new_stones:
        color = Color.BLACK if cell_color == BLACK else Color.WHITE
        try:
            pt = Point(col, row)
        except ValueError:
            continue

        digit_info = digit_map.get((row, col))
        order = digit_info[0] if digit_info else 0
        confidence = digit_info[1] if digit_info else 0.0

        moves.append(SolutionMove(color=color, point=pt, order=order, confidence=confidence))

    # Sort: numbered moves first (by digit), then unnumbered by position
    moves.sort(key=lambda m: (m.order == 0, m.order, m.point.y, m.point.x))
    return moves


def _detect_wrong_moves(
    problem_pos: RecognizedPosition,
    answer_pos: RecognizedPosition,
) -> list[SolutionMove]:
    """Detect stones that were removed (captured) — these are wrong first moves.

    Stones present in the problem but absent in the answer were likely
    captured during the opponent's refutation, indicating a wrong move
    was played on that intersection.

    Returns wrong moves as SolutionMove with is_correct semantics
    (these should be passed to SGFBuilder with is_correct=False).
    """
    p_stones, _ = _board_stone_set(problem_pos)
    a_stones, _ = _board_stone_set(answer_pos)

    # Removed stones = in problem but not in answer (captured)
    removed = p_stones - a_stones

    if not removed:
        return []

    moves = []
    for row, col, cell_color in removed:
        color = Color.BLACK if cell_color == BLACK else Color.WHITE
        try:
            pt = Point(col, row)
        except ValueError:
            continue
        moves.append(SolutionMove(color=color, point=pt, order=0, confidence=0.0))

    # Sort by position for deterministic output
    moves.sort(key=lambda m: (m.point.y, m.point.x))
    log.debug("[WRONG_MOVES] Detected %d removed stones as wrong moves", len(moves))
    return moves


def _detect_refutation_sequences(
    problem_pos: RecognizedPosition,
    answer_pos: RecognizedPosition,
    correct_moves: list[SolutionMove],
    wrong_moves: list[SolutionMove],
) -> list[list[SolutionMove]]:
    """Build refutation branches for wrong first moves.

    For each wrong move (removed stone), construct a variation:
      1. Wrong first move (the removed stone)
      2. Opponent's response (new stones near the captured area)

    Each variation is a list of SolutionMoves representing a wrong path.
    Returns list of variation branches.
    """
    if not wrong_moves:
        return []

    p_stones, _ = _board_stone_set(problem_pos)
    a_stones, a_occ = _board_stone_set(answer_pos)

    # New stones in answer that aren't correct solution moves
    correct_positions = {(m.point.y, m.point.x) for m in correct_moves}

    variations: list[list[SolutionMove]] = []

    for wrong in wrong_moves:
        branch: list[SolutionMove] = [wrong]

        # Look for opponent responses near the wrong move
        # (stones in answer that are near the wrong move but not in correct solution)
        wr, wc = wrong.point.y, wrong.point.x
        for row, col, cell_color in a_stones - p_stones:
            if (row, col) in correct_positions:
                continue
            # Within 2 intersections of the wrong move = likely response
            if abs(row - wr) <= 2 and abs(col - wc) <= 2:
                resp_color = Color.BLACK if cell_color == BLACK else Color.WHITE
                try:
                    pt = Point(col, row)
                except ValueError:
                    continue
                # Response should be opposite color
                if resp_color != wrong.color:
                    branch.append(SolutionMove(
                        color=resp_color, point=pt, order=0, confidence=0.0,
                    ))

        if len(branch) >= 1:  # At minimum the wrong move itself
            variations.append(branch)

    log.debug("[REFUTATIONS] Built %d variation branches", len(variations))
    return variations


# ---------------------------------------------------------------------------
# SGF generation
# ---------------------------------------------------------------------------


def position_to_sgf(
    match: MatchResult,
    board_size: int = 19,
    player_to_move: str | None = None,
    comment: str | None = None,
    collection: str | None = None,
) -> str:
    """Convert a matched problem-answer pair to SGF format.

    Uses SgfBuilder to create a valid SGF file with initial stones,
    a root comment, and a solution tree with ordered moves.

    Parameters
    ----------
    match : MatchResult
        A matched problem-answer pair.
    board_size : int
        Board size (default 19).
    player_to_move : str | None
        ``"B"`` or ``"W"`` override for player to move.
    comment : str | None
        Root comment text. Defaults to ``"Black to play"``.
    collection : str | None
        Collection slug for ``YL[]`` property.

    Returns
    -------
    str
        SGF string.
    """
    from tools.core.sgf_builder import SGFBuilder

    builder = SGFBuilder(board_size=board_size)

    pos = match.problem_pos

    # Add initial stones
    for iy, row in enumerate(pos.board):
        for ix, cell in enumerate(row):
            abs_row = pos.board_top + iy
            abs_col = pos.board_left + ix
            try:
                pt = Point(abs_col, abs_row)
            except ValueError:
                continue
            if cell == BLACK:
                builder.add_black_stone(pt)
            elif cell == WHITE:
                builder.add_white_stone(pt)

    # Root comment — clean, no debug info
    builder.set_comment(comment if comment is not None else "Black to play")

    # Log diagnostic info instead of embedding in SGF
    ordered_count = sum(1 for m in match.solution_moves if m.order > 0)
    log.info("Match: label=%r, match_conf=%.0f%%, board_conf=%.0f%%, "
             "strategy=%s, ordering=%d/%d",
             match.problem_label,
             match.match_confidence.overall * 100,
             match.board_confidence.overall * 100,
             match.strategy.value,
             ordered_count, len(match.solution_moves))

    # Collection membership
    if collection:
        builder.add_collection(collection)

    # Determine player to move from first solution move (or override)
    if player_to_move:
        ptm_color = Color.BLACK if player_to_move == "B" else Color.WHITE
        builder.set_player_to_move(ptm_color)
    elif match.solution_moves:
        builder.set_player_to_move(match.solution_moves[0].color)

        # Add solution moves (already sorted by _build_ordered_moves)
        for move in match.solution_moves:
            builder.add_solution_move(move.color, move.point)

    # Add wrong-move variations (incorrect first moves with BM[1])
    if match.variations:
        for branch in match.variations:
            builder.back_to_root()
            for i, move in enumerate(branch):
                builder.add_solution_move(
                    move.color, move.point,
                    comment="Wrong" if i == 0 else "",
                    is_correct=(i != 0),  # First move is wrong, responses are correct refutations
                )
    elif match.wrong_moves:
        # Simple wrong moves without full refutation sequences
        for wrong in match.wrong_moves:
            builder.back_to_root()
            builder.add_solution_move(
                wrong.color, wrong.point,
                comment="Wrong",
                is_correct=False,
            )

    return builder.build()
