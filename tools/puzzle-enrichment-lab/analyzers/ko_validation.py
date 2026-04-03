"""Ko-aware validation for KataGo puzzle enrichment.

Task A.1.5: Validate ko puzzles using KataGo PV analysis.

Ko types (from YK SGF property):
- none: No ko involved
- direct: Direct ko capture/recapture
- approach: Approach move leads to ko

Detection strategy:
1. Read YK property to know the ko type
2. Analyze PV for repeated captures (same coordinate appearing 2+ times)
3. For direct ko: validate the ko capture is the correct first move
4. For approach ko: validate the approach sequence leads to ko
5. AI enhancement: detect ko from PV even when YK=none

All thresholds from config/katago-enrichment.json.
"""

from __future__ import annotations

import logging
from collections import Counter
from enum import Enum

from pydantic import BaseModel, Field

try:
    from config import EnrichmentConfig, load_enrichment_config
    from models.analysis_response import AnalysisResponse
    from models.validation import ValidationStatus
except ImportError:
    from ..config import EnrichmentConfig, load_enrichment_config
    from ..models.analysis_response import AnalysisResponse
    from ..models.validation import ValidationStatus

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Ko type enum (mirrors YK SGF property values)
# ---------------------------------------------------------------------------


class KoType(str, Enum):
    """Ko type from the YK SGF property."""
    NONE = "none"
    DIRECT = "direct"
    APPROACH = "approach"


# ---------------------------------------------------------------------------
# Ko detection result from PV analysis
# ---------------------------------------------------------------------------


class KoPvDetection(BaseModel):
    """Result of analyzing a PV sequence for ko patterns."""
    ko_detected: bool = False
    ko_type_hint: str | None = None
    repeated_moves: list[str] = Field(default_factory=list)
    repetition_count: int = 0


# ---------------------------------------------------------------------------
# Ko validation result
# ---------------------------------------------------------------------------


class KoValidationResult(BaseModel):
    """Result of ko-aware validation."""
    status: ValidationStatus = ValidationStatus.FLAGGED
    katago_agrees: bool = False
    ko_detected: bool = False
    correct_move_gtp: str = ""
    katago_top_move: str = ""
    correct_move_winrate: float = 0.0
    correct_move_policy: float = 0.0
    ko_type: KoType = KoType.NONE
    flags: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# PV ko detection (AI enhancement)
# ---------------------------------------------------------------------------


def _are_adjacent(coord1: str, coord2: str) -> bool:
    """Check if two GTP coordinates are orthogonally adjacent (Manhattan distance = 1).

    In Go, captures require shared liberties, which means orthogonal (not
    diagonal) adjacency. This is used to verify that a ko recapture involves
    an actual capture at an adjacent intersection.
    """
    def _parse_gtp(coord: str) -> tuple[int, int] | None:
        if not coord or len(coord) < 2:
            return None
        col_char = coord[0].upper()
        if col_char < 'A' or col_char > 'T' or col_char == 'I':
            return None
        col = ord(col_char) - ord('A')
        if col_char > 'I':
            col -= 1  # GTP skips 'I'
        try:
            row = int(coord[1:]) - 1
        except ValueError:
            return None
        return (col, row)

    p1 = _parse_gtp(coord1)
    p2 = _parse_gtp(coord2)
    if p1 is None or p2 is None:
        return False
    return abs(p1[0] - p2[0]) + abs(p1[1] - p2[1]) == 1


def _parse_gtp_coord(coord: str, board_size: int = 19) -> tuple[int, int] | None:
    """Parse GTP coordinate to (row, col) for board replay."""
    if not coord or len(coord) < 2:
        return None
    col_char = coord[0].upper()
    if col_char < 'A' or col_char > 'T' or col_char == 'I':
        return None
    col = ord(col_char) - ord('A')
    if col_char > 'I':
        col -= 1
    try:
        row = board_size - int(coord[1:])
    except ValueError:
        return None
    if 0 <= row < board_size and 0 <= col < board_size:
        return (row, col)
    return None


def _flood_fill_group(grid: list[list[str | None]], row: int, col: int, color: str, size: int) -> set[tuple[int, int]]:
    """Find connected group of same color via flood fill."""
    group: set[tuple[int, int]] = set()
    stack = [(row, col)]
    while stack:
        r, c = stack.pop()
        if (r, c) in group:
            continue
        if 0 <= r < size and 0 <= c < size and grid[r][c] == color:
            group.add((r, c))
            stack.extend([(r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)])
    return group


def _has_liberties(grid: list[list[str | None]], group: set[tuple[int, int]], size: int) -> bool:
    """Check if a group has at least one liberty."""
    for r, c in group:
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < size and 0 <= nc < size and grid[nr][nc] is None:
                return True
    return False


def _play_and_capture(grid: list[list[str | None]], row: int, col: int, color: str, size: int) -> int:
    """Place a stone and resolve captures. Returns number of stones captured."""
    grid[row][col] = color
    opponent = "W" if color == "B" else "B"
    captured = 0
    for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        nr, nc = row + dr, col + dc
        if 0 <= nr < size and 0 <= nc < size and grid[nr][nc] == opponent:
            group = _flood_fill_group(grid, nr, nc, opponent, size)
            if not _has_liberties(grid, group, size):
                for gr, gc in group:
                    grid[gr][gc] = None
                captured += len(group)
    return captured


def _verify_ko_capture_on_board(
    normalized_pv: list[str],
    initial_stones: dict[tuple[int, int], str],
    coord: str,
    first_idx: int,
    second_idx: int,
    first_player_color: str,
    board_size: int = 19,
) -> bool:
    """Replay PV on a board and verify a capture occurs at the recurrence coordinate.

    Returns True if between first_idx and second_idx, the stone at coord
    was captured (removed) and then re-placed — confirming a ko recapture.
    """
    grid: list[list[str | None]] = [[None] * board_size for _ in range(board_size)]
    # Set up initial stones
    for (r, c), color in initial_stones.items():
        if 0 <= r < board_size and 0 <= c < board_size:
            grid[r][c] = color

    target_rc = _parse_gtp_coord(coord, board_size)
    if target_rc is None:
        return False

    # Alternate colors starting from first_player_color
    colors = [first_player_color, "W" if first_player_color == "B" else "B"]

    # Replay PV up to second_idx
    for i in range(second_idx + 1):
        move = normalized_pv[i]
        rc = _parse_gtp_coord(move, board_size)
        if rc is None:
            continue
        move_color = colors[i % 2]
        captured = _play_and_capture(grid, rc[0], rc[1], move_color, board_size)

        # After the first placement of the coord, check if it gets captured
        # before the second placement
        if i > first_idx and i < second_idx and rc == target_rc:
            # Stone placed at target between occurrences — not a simple ko
            continue
        if first_idx < i < second_idx and captured > 0:
            # A capture happened between the two occurrences
            # Check if the target coordinate is now empty
            if grid[target_rc[0]][target_rc[1]] is None:
                return True

    return False


def detect_ko_in_pv(
    pv: list[str],
    config: EnrichmentConfig | None = None,
    initial_stones: dict[tuple[int, int], str] | None = None,
    first_player_color: str = "B",
    board_size: int = 19,
) -> KoPvDetection:
    """Detect ko patterns in a principal variation sequence.

    Ko is characterized by repeated captures at the same coordinate.
    A move appearing 2+ times in the PV strongly suggests a ko fight.

    When ``initial_stones`` is provided, the function replays the PV on a
    board to verify that a stone is actually captured between the repeated
    coordinates (board replay verification). Without initial_stones, falls
    back to adjacency-only detection.

    Args:
        pv: List of GTP coordinates from KataGo's principal variation.
        config: Enrichment config for ko_detection thresholds.
        initial_stones: Optional board state as {(row, col): "B"|"W"} for
            capture verification via board replay.
        first_player_color: Color of the player making the first PV move.
        board_size: Board size for coordinate parsing.

    Returns:
        KoPvDetection with ko_detected, ko_type_hint, and repeated moves.
    """
    if config is None:
        config = load_enrichment_config()
    ko_cfg = config.ko_detection

    if len(pv) < ko_cfg.min_pv_length:
        return KoPvDetection(ko_detected=False)

    # Count occurrences of each coordinate (case-insensitive)
    normalized_pv = [m.upper() for m in pv if m and m.upper() != "PASS"]
    coord_counts = Counter(normalized_pv)

    def _has_recapture_pattern(coord: str) -> bool:
        """Check for ko-specific recapture: same coord appears with gap=2.

        A true ko recapture has the pattern: player plays at X, opponent
        plays adjacent to capture, player recaptures at X (gap of exactly 2).
        When initial_stones is provided, verifies via board replay that a
        stone is actually captured between the repeated coordinates.
        Larger even gaps (4, 6, ...) may indicate repeated atari sequences
        but are less reliable — we also accept them but with adjacency check.
        """
        indices = [i for i, move in enumerate(normalized_pv) if move == coord]
        if len(indices) < 2:
            return False
        logger.debug(
            "Ko recurrence: coord=%s appears at indices %s",
            coord, indices,
        )
        for i in range(len(indices) - 1):
            for j in range(i + 1, len(indices)):
                gap = indices[j] - indices[i]
                if gap == 2:
                    between_idx = indices[i] + 1
                    between_move = normalized_pv[between_idx]
                    adj = _are_adjacent(coord, between_move)
                    logger.debug(
                        "Ko adjacency check: coord=%s, between=%s, adjacent=%s",
                        coord, between_move, adj,
                    )
                    if adj:
                        # Board replay verification when initial_stones provided
                        if initial_stones is not None:
                            verified = _verify_ko_capture_on_board(
                                normalized_pv, initial_stones, coord,
                                indices[i], indices[j], first_player_color,
                                board_size,
                            )
                            logger.debug(
                                "Ko board verification: coord=%s, indices=(%d,%d), verified=%s",
                                coord, indices[i], indices[j], verified,
                            )
                            if verified:
                                return True
                        else:
                            return True
                elif gap >= 4 and gap % 2 == 0:
                    for mid in range(indices[i] + 1, indices[j]):
                        if _are_adjacent(coord, normalized_pv[mid]):
                            if initial_stones is not None:
                                verified = _verify_ko_capture_on_board(
                                    normalized_pv, initial_stones, coord,
                                    indices[i], indices[j], first_player_color,
                                    board_size,
                                )
                                if verified:
                                    return True
                            else:
                                return True
        return False

    # Find coordinates that appear multiple times (config-driven threshold)
    repeated = [
        (coord, count) for coord, count in coord_counts.items()
        if count >= ko_cfg.min_repeat_count and _has_recapture_pattern(coord)
    ]

    if not repeated:
        logger.debug("Ko verdict: no recapture pattern detected in PV")
        return KoPvDetection(ko_detected=False)

    # Sort by count descending
    repeated.sort(key=lambda x: x[1], reverse=True)
    top_coord, top_count = repeated[0]

    # Determine ko type hint (config-driven thresholds)
    if top_count >= ko_cfg.long_ko_threshold:
        ko_hint = "long_ko_fight"
    elif len(repeated) >= ko_cfg.double_ko_coords:
        ko_hint = "double_ko"
    else:
        ko_hint = "direct_ko"

    logger.debug(
        "Ko verdict: detected=%s, type=%s, repeated=%s, top_count=%d",
        True, ko_hint, [coord for coord, _ in repeated], top_count,
    )
    return KoPvDetection(
        ko_detected=True,
        ko_type_hint=ko_hint,
        repeated_moves=[coord for coord, _ in repeated],
        repetition_count=top_count,
    )


def _log_ko_detection(pv, result):
    """Log ko detection result."""
    logger.info(
        "Ko detection: ko_detected=%s, type_hint=%s, repeated=%s, "
        "pv_length=%d",
        result.ko_detected, result.ko_type_hint,
        result.repeated_moves, len(pv),
    )


# ---------------------------------------------------------------------------
# Main ko validation function
# ---------------------------------------------------------------------------


def validate_ko(
    response: AnalysisResponse,
    correct_move_gtp: str,
    ko_type: KoType = KoType.DIRECT,
    config: EnrichmentConfig | None = None,
    position: Position | None = None,  # noqa: F821
) -> KoValidationResult:
    """Validate a ko puzzle against KataGo analysis.

    Args:
        response: KataGo analysis response for the position.
        correct_move_gtp: GTP coordinate of the correct first move.
        ko_type: Ko type from YK property (direct, approach, none).
        config: Enrichment config (loaded from file if None).
        position: Optional Position for board-replay ko verification.

    Returns:
        KoValidationResult with status, ko detection, and flags.
    """
    if config is None:
        config = load_enrichment_config()

    # Derive board-replay inputs from position when available
    initial_stones: dict[tuple[int, int], str] | None = None
    first_player_color = "B"
    board_size = 19
    if position is not None:
        initial_stones = {(s.x, s.y): s.color.value for s in position.stones}
        first_player_color = position.player_to_move.value
        board_size = position.board_size

    flags: list[str] = [f"ko_type:{ko_type.value}"]

    # Get top move info
    top = response.top_move
    if top is None:
        return KoValidationResult(
            status=ValidationStatus.REJECTED,
            katago_agrees=False,
            ko_detected=False,
            correct_move_gtp=correct_move_gtp,
            ko_type=ko_type,
            flags=flags + ["no_moves_in_response"],
        )

    is_top = top.move.upper() == correct_move_gtp.upper()

    # Get correct move info
    correct_info = response.get_move(correct_move_gtp)
    winrate = correct_info.winrate if correct_info else 0.0
    policy = correct_info.policy_prior if correct_info else 0.0

    # Check top-N membership
    top_n = config.validation.rejected_not_in_top_n
    sorted_moves = sorted(response.move_infos, key=lambda m: m.visits, reverse=True)
    in_top_n = any(
        m.move.upper() == correct_move_gtp.upper()
        for m in sorted_moves[:top_n]
    )

    # Detect ko in PV
    top_pv = top.pv if top else []
    pv_detection = detect_ko_in_pv(
        top_pv, config=config, initial_stones=initial_stones,
        first_player_color=first_player_color, board_size=board_size,
    )
    _log_ko_detection(top_pv, pv_detection)
    ko_detected = pv_detection.ko_detected

    if ko_detected:
        flags.append("ko_detected_in_pv")
        if pv_detection.ko_type_hint:
            flags.append(pv_detection.ko_type_hint)

    # Also check PV of the correct move (if not the top move)
    if not ko_detected and correct_info and correct_info.pv:
        correct_pv_detection = detect_ko_in_pv(
            correct_info.pv, config=config, initial_stones=initial_stones,
            first_player_color=first_player_color, board_size=board_size,
        )
        if correct_pv_detection.ko_detected:
            ko_detected = True
            flags.append("ko_detected_in_correct_pv")

    # Determine validation status based on ko type
    if ko_type == KoType.DIRECT:
        status = _validate_direct_ko(
            is_top=is_top,
            in_top_n=in_top_n,
            winrate=winrate,
            ko_detected=ko_detected,
            config=config,
            flags=flags,
        )
    elif ko_type == KoType.APPROACH:
        status = _validate_approach_ko(
            is_top=is_top,
            in_top_n=in_top_n,
            winrate=winrate,
            ko_detected=ko_detected,
            config=config,
            flags=flags,
        )
    else:
        # YK=none but ko might still be detected from PV
        status = _validate_unknown_ko(
            is_top=is_top,
            in_top_n=in_top_n,
            winrate=winrate,
            ko_detected=ko_detected,
            config=config,
            flags=flags,
        )

    return KoValidationResult(
        status=status,
        katago_agrees=is_top,
        ko_detected=ko_detected,
        correct_move_gtp=correct_move_gtp,
        katago_top_move=top.move,
        correct_move_winrate=winrate,
        correct_move_policy=policy,
        ko_type=ko_type,
        flags=flags,
    )


# ---------------------------------------------------------------------------
# Ko sub-validators
# ---------------------------------------------------------------------------


def _validate_direct_ko(
    is_top: bool,
    in_top_n: bool,
    winrate: float,
    ko_detected: bool,
    config: EnrichmentConfig,
    flags: list[str],
) -> ValidationStatus:
    """Validate a direct ko puzzle.

    Direct ko: the correct move IS the ko capture.
    KataGo should recognize this as the best or near-best move.
    Ko detection in PV strengthens confidence.
    """
    if is_top:
        # Top move + we know it's a ko puzzle → accepted
        return ValidationStatus.ACCEPTED

    if in_top_n:
        # In top-N — ko moves can be tricky for KataGo with few visits
        if ko_detected:
            # PV shows ko → KataGo sees the ko fight, just prefers another move
            return ValidationStatus.ACCEPTED
        elif winrate >= config.validation.flagged_value_high:
            return ValidationStatus.ACCEPTED
        else:
            return ValidationStatus.FLAGGED

    # Not in top-N.
    # NOTE: No general winrate rescue here (unlike _status_from_classification).
    # Ko puzzles use ko detection (PV pattern matching) as its rescue signal
    # instead, because a high winrate without ko detection suggests the
    # position may not actually involve a ko from KataGo's perspective.
    if ko_detected:
        # Ko detected but move not ranked → flag for review
        flags.append("ko_detected_but_not_ranked")
        return ValidationStatus.FLAGGED

    return ValidationStatus.REJECTED


def _validate_approach_ko(
    is_top: bool,
    in_top_n: bool,
    winrate: float,
    ko_detected: bool,
    config: EnrichmentConfig,
    flags: list[str],
) -> ValidationStatus:
    """Validate an approach ko puzzle.

    Approach ko: the correct first move is NOT the ko capture itself,
    but an approach move that sets up the ko fight. KataGo may not
    evaluate the approach as strongly since the ko hasn't started yet.

    We're more lenient with approach moves — they're harder for AI
    to evaluate because the ko fight is 1+ moves away.
    """
    if is_top:
        return ValidationStatus.ACCEPTED

    if in_top_n:
        # Approach moves in top-N are generally good
        if winrate >= config.validation.flagged_value_low:
            return ValidationStatus.ACCEPTED
        else:
            return ValidationStatus.FLAGGED

    # Not in top-N — approach moves are harder, be more lenient.
    # Unlike direct ko, approach moves are further from the ko fight
    # so AI evaluation is noisier.  We use flagged_value_low (not high)
    # as a rescue threshold, which is more lenient than the general
    # winrate rescue in validate_correct_move.py.
    if ko_detected:
        flags.append("approach_ko_detected")
        return ValidationStatus.FLAGGED

    if winrate >= config.validation.flagged_value_low:
        flags.append("approach_not_ranked")
        return ValidationStatus.FLAGGED

    return ValidationStatus.REJECTED


def _validate_unknown_ko(
    is_top: bool,
    in_top_n: bool,
    winrate: float,
    ko_detected: bool,
    config: EnrichmentConfig,
    flags: list[str],
) -> ValidationStatus:
    """Validate when YK=none but ko might be detected from PV.

    Falls back to standard validation with ko detection as bonus signal.
    No winrate rescue for not-in-top-N: without ko context (YK=none),
    we have no domain-specific reason to be lenient.
    """
    if is_top:
        if winrate >= config.validation.flagged_value_low:
            return ValidationStatus.ACCEPTED
        return ValidationStatus.FLAGGED

    if in_top_n:
        if winrate >= config.validation.flagged_value_high:
            return ValidationStatus.ACCEPTED
        return ValidationStatus.FLAGGED

    return ValidationStatus.REJECTED
