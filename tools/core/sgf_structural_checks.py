"""
SGF structural validation checks.

Provides reusable structural correctness checks for SGF puzzle files:
  1. Parseability — well-formed brackets and ``(;`` start
  2. Required properties — SZ, FF, GM presence
  3. Board size bounds — within configurable min/max
  4. Setup stone extraction — AB/AW parsing, count validation
  5. Stone bounds — all setup stones within board
  6. Stone overlap — no black+white on same point
  7. Solution move extraction — move parsing, bounds, no-solution
  8. Player-to-move consistency — PL matches first move color
  9. Excessive moves — total move count threshold
  10. Consecutive same-point — branch-aware adjacent-move detection

Each check is a standalone public function that can be used individually
or composed via ``run_structural_checks()`` orchestrator.

Usage:
    from tools.core.sgf_structural_checks import (
        run_structural_checks,
        IssueCode,
        StructuralCheckResult,
    )

    result = run_structural_checks(sgf_content)
    if not result.is_valid:
        for issue in result.issues:
            print(f"  [{issue.severity.value}] {issue.code.name}: {issue.message}")
            print(f"    context: {issue.context}")

    # Individual checks:
    from tools.core.sgf_structural_checks import (
        StructuralCheckResult,
        check_parseability,
        extract_setup_stones,
    )
    result = StructuralCheckResult.empty()
    check_parseability(sgf, result)
    extract_setup_stones(sgf, result, min_stones=3)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum, IntEnum
from typing import Any

logger = logging.getLogger("tools.core.sgf_structural_checks")


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------


class StructuralIssueSeverity(str, Enum):
    """Severity level for a structural validation issue."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class IssueCode(IntEnum):
    """Machine-readable issue codes grouped by category.

    Numbering scheme:
      1xxx — Parseability
      2xxx — Required properties
      3xxx — Board size
      4xxx — Setup stones
      5xxx — Solution moves
      6xxx — Player to move
    """

    # Parseability (1xxx)
    EMPTY_SGF = 1001
    MALFORMED_START = 1002
    UNBALANCED_PARENS = 1003
    UNCLOSED_PARENS = 1004

    # Required properties (2xxx)
    MISSING_SZ = 2001
    MISSING_FF = 2002
    MISSING_GM = 2003

    # Board size (3xxx)
    BOARD_TOO_SMALL = 3001
    BOARD_TOO_LARGE = 3002

    # Setup stones (4xxx)
    NO_STONES = 4001
    FEW_STONES = 4002
    INVALID_COORD = 4003
    OUT_OF_BOUNDS = 4004
    STONE_OVERLAP = 4005

    # Solution moves (5xxx)
    INVALID_MOVE_COORD = 5001
    MOVE_OUT_OF_BOUNDS = 5002
    MOVE_ON_STONE = 5003
    CONSECUTIVE_SAME_POINT = 5004
    NO_SOLUTION = 5005
    EXCESSIVE_MOVES = 5006

    # Player to move (6xxx)
    PL_MISMATCH = 6001


@dataclass
class StructuralIssue:
    """A single structural validation issue.

    Attributes:
        severity: ERROR (structural problem), WARNING (quality concern),
            or INFO (informational).
        code: Machine-readable IntEnum code.
        message: Human-readable description.
        context: Machine-readable triggering values for programmatic use.
    """

    severity: StructuralIssueSeverity
    code: IssueCode
    message: str
    context: dict[str, Any] = field(default_factory=dict)


@dataclass
class StructuralCheckResult:
    """Aggregated result of structural validation checks.

    Populated incrementally by check functions. Use ``empty()`` factory
    to create a blank result for individual check composition.
    """

    issues: list[StructuralIssue] = field(default_factory=list)
    board_size: int = 0
    black_stones: set[tuple[int, int]] = field(default_factory=set)
    white_stones: set[tuple[int, int]] = field(default_factory=set)
    solution_moves: list[tuple[str, int, int]] = field(default_factory=list)
    player_to_move: str = ""

    @classmethod
    def empty(cls) -> StructuralCheckResult:
        """Create a blank result for individual check composition."""
        return cls()

    @property
    def is_valid(self) -> bool:
        """True if no ERROR-severity issues."""
        return not any(
            i.severity == StructuralIssueSeverity.ERROR for i in self.issues
        )

    @property
    def error_count(self) -> int:
        return sum(
            1 for i in self.issues
            if i.severity == StructuralIssueSeverity.ERROR
        )

    @property
    def warning_count(self) -> int:
        return sum(
            1 for i in self.issues
            if i.severity == StructuralIssueSeverity.WARNING
        )

    @property
    def black_stone_count(self) -> int:
        return len(self.black_stones)

    @property
    def white_stone_count(self) -> int:
        return len(self.white_stones)

    @property
    def total_stone_count(self) -> int:
        return self.black_stone_count + self.white_stone_count

    @property
    def solution_move_count(self) -> int:
        return len(self.solution_moves)

    @property
    def has_solution_tree(self) -> bool:
        return self.solution_move_count > 0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sgf_coord_to_tuple(coord: str) -> tuple[int, int]:
    """Convert SGF coordinate like 'cd' to (col=2, row=3).

    No bounds validation — callers check bounds separately.

    Raises:
        ValueError: If coord is not exactly 2 lowercase letters.
    """
    if len(coord) != 2:
        raise ValueError(f"Invalid SGF coordinate: {coord!r}")
    col = ord(coord[0]) - ord("a")
    row = ord(coord[1]) - ord("a")
    return col, row


def _emit(
    result: StructuralCheckResult,
    severity: StructuralIssueSeverity,
    code: IssueCode,
    message: str,
    context: dict[str, Any] | None = None,
) -> None:
    """Append an issue to the result."""
    result.issues.append(
        StructuralIssue(
            severity=severity,
            code=code,
            message=message,
            context=context or {},
        )
    )


# ---------------------------------------------------------------------------
# Check 1: Parseability
# ---------------------------------------------------------------------------

def check_parseability(sgf: str, result: StructuralCheckResult) -> None:
    """Check SGF is non-empty, starts with ``(;``, and has balanced brackets."""
    if not sgf or not sgf.strip():
        _emit(result, StructuralIssueSeverity.ERROR, IssueCode.EMPTY_SGF,
              "SGF content is empty")
        return

    if not sgf.strip().startswith("(;"):
        _emit(result, StructuralIssueSeverity.ERROR, IssueCode.MALFORMED_START,
              "SGF must start with '(;'")

    depth = 0
    for ch in sgf:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if depth < 0:
            _emit(result, StructuralIssueSeverity.ERROR,
                  IssueCode.UNBALANCED_PARENS,
                  "Unbalanced closing parenthesis")
            break
    if depth > 0:
        _emit(result, StructuralIssueSeverity.ERROR,
              IssueCode.UNCLOSED_PARENS,
              f"Unclosed parentheses: {depth} remaining",
              {"remaining": depth})


# ---------------------------------------------------------------------------
# Check 2: Required properties
# ---------------------------------------------------------------------------

def check_required_properties(sgf: str, result: StructuralCheckResult) -> None:
    """Check that SZ, FF, GM properties are present."""
    if not re.search(r"SZ\[\d+\]", sgf):
        _emit(result, StructuralIssueSeverity.ERROR, IssueCode.MISSING_SZ,
              "Missing SZ (board size) property")
    if not re.search(r"FF\[\d+\]", sgf):
        _emit(result, StructuralIssueSeverity.WARNING, IssueCode.MISSING_FF,
              "Missing FF (file format) property")
    if not re.search(r"GM\[\d+\]", sgf):
        _emit(result, StructuralIssueSeverity.WARNING, IssueCode.MISSING_GM,
              "Missing GM (game) property")


# ---------------------------------------------------------------------------
# Check 3: Board size
# ---------------------------------------------------------------------------

def check_board_size(
    sgf: str,
    result: StructuralCheckResult,
    *,
    min_board_size: int = 5,
    max_board_size: int = 19,
) -> None:
    """Extract SZ and check board size is within bounds.

    Sets ``result.board_size``. Defaults to 19 if SZ is absent.
    """
    sz_match = re.search(r"SZ\[(\d+)\]", sgf)
    if sz_match:
        result.board_size = int(sz_match.group(1))
    else:
        result.board_size = 19

    if result.board_size < min_board_size:
        _emit(result, StructuralIssueSeverity.ERROR, IssueCode.BOARD_TOO_SMALL,
              f"Board size {result.board_size} below minimum {min_board_size}",
              {"board_size": result.board_size, "limit": min_board_size})
    if result.board_size > max_board_size:
        _emit(result, StructuralIssueSeverity.ERROR, IssueCode.BOARD_TOO_LARGE,
              f"Board size {result.board_size} exceeds maximum {max_board_size}",
              {"board_size": result.board_size, "limit": max_board_size})


# ---------------------------------------------------------------------------
# Check 4: Setup stone extraction
# ---------------------------------------------------------------------------

# Matches multi-stone AB[aa][bb] or AW[cc][dd] blocks
_AB_AW_BLOCK_RE = re.compile(r"(A[BW])((?:\[[a-s]{2}\])+)")


def extract_setup_stones(
    sgf: str,
    result: StructuralCheckResult,
    *,
    min_stones: int = 2,
) -> None:
    """Parse AB/AW properties and populate ``result.black_stones``/``white_stones``.

    Emits NO_STONES if no setup stones found, FEW_STONES if below minimum,
    INVALID_COORD for malformed coordinates.
    """
    for match in _AB_AW_BLOCK_RE.finditer(sgf):
        color_prop = match.group(1)  # "AB" or "AW"
        coord_block = match.group(2)
        target = (
            result.black_stones if color_prop == "AB"
            else result.white_stones
        )
        for coord_match in re.finditer(r"\[([a-s]{2})\]", coord_block):
            coord_str = coord_match.group(1)
            try:
                point = _sgf_coord_to_tuple(coord_str)
                target.add(point)
            except ValueError:
                _emit(result, StructuralIssueSeverity.ERROR,
                      IssueCode.INVALID_COORD,
                      f"Invalid stone coordinate: {coord_str}",
                      {"coord": coord_str})

    total = result.total_stone_count
    if total == 0:
        _emit(result, StructuralIssueSeverity.ERROR, IssueCode.NO_STONES,
              "No initial stones (AB/AW) found")
    elif total < min_stones:
        _emit(result, StructuralIssueSeverity.WARNING, IssueCode.FEW_STONES,
              f"Only {total} initial stones (minimum {min_stones})",
              {"count": total, "minimum": min_stones})


# ---------------------------------------------------------------------------
# Check 5: Stone bounds
# ---------------------------------------------------------------------------

def check_stone_bounds(result: StructuralCheckResult) -> None:
    """Check all setup stones are within board bounds.

    Requires ``result.board_size`` and stone sets to be populated.
    """
    all_stones = result.black_stones | result.white_stones
    for col, row in all_stones:
        if col < 0 or col >= result.board_size or row < 0 or row >= result.board_size:
            coord_str = chr(col + ord("a")) + chr(row + ord("a"))
            _emit(result, StructuralIssueSeverity.ERROR, IssueCode.OUT_OF_BOUNDS,
                  f"Stone at ({col},{row}) is outside "
                  f"{result.board_size}x{result.board_size} board",
                  {"coord": coord_str, "col": col, "row": row,
                   "board_size": result.board_size})


# ---------------------------------------------------------------------------
# Check 6: Stone overlap
# ---------------------------------------------------------------------------

def check_stone_overlap(result: StructuralCheckResult) -> None:
    """Check no intersection has both a black and white setup stone."""
    overlap = result.black_stones & result.white_stones
    for col, row in overlap:
        coord_str = chr(col + ord("a")) + chr(row + ord("a"))
        _emit(result, StructuralIssueSeverity.ERROR, IssueCode.STONE_OVERLAP,
              f"Black and white stone on same point ({col},{row})",
              {"coord": (col, row), "sgf_coord": coord_str})


# ---------------------------------------------------------------------------
# Check 7: Solution move extraction
# ---------------------------------------------------------------------------

# Matches ;B[xx] or ;W[xx] move nodes
_MOVE_RE = re.compile(r";([BW])\[([a-s]{2})\]")


def extract_solution_moves(
    sgf: str,
    result: StructuralCheckResult,
) -> None:
    """Parse solution moves and populate ``result.solution_moves``.

    Checks move coordinate validity and board bounds.
    """
    for match in _MOVE_RE.finditer(sgf):
        color = match.group(1)
        coord_str = match.group(2)
        try:
            col, row = _sgf_coord_to_tuple(coord_str)
        except ValueError:
            _emit(result, StructuralIssueSeverity.ERROR,
                  IssueCode.INVALID_MOVE_COORD,
                  f"Invalid solution move coordinate: {coord_str}",
                  {"coord": coord_str})
            continue

        if (result.board_size > 0
                and (col < 0 or col >= result.board_size
                     or row < 0 or row >= result.board_size)):
            _emit(result, StructuralIssueSeverity.ERROR,
                  IssueCode.MOVE_OUT_OF_BOUNDS,
                  f"Solution move {color}[{coord_str}] outside board",
                  {"color": color, "coord": coord_str,
                   "board_size": result.board_size})

        result.solution_moves.append((color, col, row))

    if not result.solution_moves:
        _emit(result, StructuralIssueSeverity.WARNING, IssueCode.NO_SOLUTION,
              "No solution moves found in SGF")


# ---------------------------------------------------------------------------
# Check 8: Player to move
# ---------------------------------------------------------------------------

def check_player_to_move(
    sgf: str,
    result: StructuralCheckResult,
) -> None:
    """Check PL[] matches first solution move color.

    Sets ``result.player_to_move``.
    """
    pl_match = re.search(r"PL\[([BW])\]", sgf)
    if pl_match:
        result.player_to_move = pl_match.group(1)

    if result.player_to_move and result.solution_moves:
        first_color = result.solution_moves[0][0]
        if result.player_to_move != first_color:
            _emit(result, StructuralIssueSeverity.WARNING,
                  IssueCode.PL_MISMATCH,
                  f"PL[{result.player_to_move}] but first move is "
                  f"{first_color}",
                  {"declared": result.player_to_move, "actual": first_color})


# ---------------------------------------------------------------------------
# Check 9: Excessive moves
# ---------------------------------------------------------------------------

def check_excessive_moves(
    result: StructuralCheckResult,
    *,
    threshold: int = 50,
) -> None:
    """Flag SGFs with suspiciously many solution moves."""
    count = result.solution_move_count
    if count > threshold:
        _emit(result, StructuralIssueSeverity.WARNING,
              IssueCode.EXCESSIVE_MOVES,
              f"Solution has {count} moves "
              f"(unusually long for tsumego)",
              {"count": count, "threshold": threshold})


# ---------------------------------------------------------------------------
# Check 10: Consecutive same-point (branch-aware)
# ---------------------------------------------------------------------------

def check_consecutive_same_point(
    sgf: str,
    result: StructuralCheckResult,
) -> None:
    """Branch-aware check for consecutive moves on the same intersection.

    Uses ``parse_sgf()`` + ``get_all_paths()`` to enumerate every
    root-to-leaf branch and checks adjacent moves pairwise.

    - Consecutive same-point (move N and N+1) -> ERROR
    - Non-consecutive same-point on a setup stone -> MOVE_ON_STONE WARNING

    Skips gracefully if the SGF fails to parse (parseability issues are
    already caught by ``check_parseability``).
    """
    try:
        from tools.core.sgf_analysis import get_all_paths
        from tools.core.sgf_parser import SGFParseError, parse_sgf
    except ImportError:
        logger.debug("sgf_parser/sgf_analysis not available, skipping "
                     "consecutive-move check")
        return

    try:
        tree = parse_sgf(sgf)
    except SGFParseError:
        logger.debug("SGF parse failed, skipping consecutive-move check")
        return
    except Exception:
        logger.debug("Unexpected parse error, skipping consecutive-move check")
        return

    paths = get_all_paths(tree.solution_tree)
    setup_points = result.black_stones | result.white_stones
    seen_consecutive: set[tuple[int, str]] = set()
    seen_on_stone: set[str] = set()

    for branch_idx, path in enumerate(paths):
        move_nodes = [n for n in path if n.move is not None]
        for i, node in enumerate(move_nodes):
            assert node.move is not None
            coord = (node.move.x, node.move.y)
            coord_str = node.move.to_sgf()

            # Check consecutive same-point in this branch
            if i > 0:
                prev = move_nodes[i - 1]
                assert prev.move is not None
                prev_coord = (prev.move.x, prev.move.y)
                if coord == prev_coord:
                    dedup_key = (branch_idx, coord_str)
                    if dedup_key not in seen_consecutive:
                        seen_consecutive.add(dedup_key)
                        _emit(
                            result,
                            StructuralIssueSeverity.ERROR,
                            IssueCode.CONSECUTIVE_SAME_POINT,
                            f"Consecutive moves on same point "
                            f"[{coord_str}] in branch {branch_idx + 1}",
                            {"coord": coord_str, "move_index": i,
                             "branch": branch_idx + 1},
                        )

            # Check non-consecutive move on setup stone
            if coord in setup_points and coord_str not in seen_on_stone:
                seen_on_stone.add(coord_str)
                color_str = node.color.value if node.color else "?"
                _emit(
                    result,
                    StructuralIssueSeverity.WARNING,
                    IssueCode.MOVE_ON_STONE,
                    f"Solution move {color_str}[{coord_str}] on occupied "
                    f"intersection (may be capture)",
                    {"color": color_str, "coord": coord_str},
                )


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def run_structural_checks(
    sgf: str,
    *,
    min_stones: int = 2,
    min_board_size: int = 5,
    max_board_size: int = 19,
    excessive_move_threshold: int = 50,
) -> StructuralCheckResult:
    """Run all structural checks on an SGF string.

    This is the primary public API. Runs checks 1-10 in order and
    returns a ``StructuralCheckResult`` with all issues collected.

    Short-circuits after ``check_parseability`` if SGF is empty.

    Args:
        sgf: Raw SGF string.
        min_stones: Minimum initial stones required (default 2).
        min_board_size: Minimum board dimension (default 5).
        max_board_size: Maximum board dimension (default 19).
        excessive_move_threshold: Flag SGFs with more moves than this
            (default 50).

    Returns:
        StructuralCheckResult with all issues and extracted metadata.
    """
    result = StructuralCheckResult.empty()

    # Check 1: Parseability (short-circuit if empty)
    check_parseability(sgf, result)
    if any(i.code == IssueCode.EMPTY_SGF for i in result.issues):
        return result

    # Check 2-9: Property and content checks
    check_required_properties(sgf, result)
    check_board_size(sgf, result,
                     min_board_size=min_board_size,
                     max_board_size=max_board_size)
    extract_setup_stones(sgf, result, min_stones=min_stones)
    check_stone_bounds(result)
    check_stone_overlap(result)
    extract_solution_moves(sgf, result)
    check_player_to_move(sgf, result)
    check_excessive_moves(result, threshold=excessive_move_threshold)

    # Check 10: Branch-aware consecutive same-point
    check_consecutive_same_point(sgf, result)

    return result
