"""SGF correctness checker for generated puzzle SGFs.

Thin wrapper around ``tools.core.sgf_structural_checks`` that preserves
the original public API (``validate_sgf``, ``SgfCheckResult``, ``SgfIssue``,
``IssueSeverity``) for backward compatibility.

All structural validation logic lives in ``tools.core.sgf_structural_checks``.

Usage:
    from tools.pdf_to_sgf.sgf_checker import validate_sgf, SgfCheckResult

    result = validate_sgf(sgf_string)
    if not result.is_valid:
        for issue in result.issues:
            print(f"  [{issue.severity}] {issue.code}: {issue.message}")
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from tools.core.sgf_structural_checks import (
    StructuralCheckResult,
    StructuralIssue,
    StructuralIssueSeverity,
    run_structural_checks,
)

log = logging.getLogger(__name__)

# Backward-compatible alias
IssueSeverity = StructuralIssueSeverity


@dataclass
class SgfIssue:
    """A single validation issue (backward-compatible wrapper).

    Maps ``IssueCode`` IntEnum to string ``code`` for consumers that
    compare against bare strings like ``i.code == "EMPTY_SGF"``.
    """

    severity: IssueSeverity
    code: str
    message: str

    @classmethod
    def from_structural(cls, si: StructuralIssue) -> SgfIssue:
        return cls(
            severity=si.severity,
            code=si.code.name,
            message=si.message,
        )


@dataclass
class SgfCheckResult:
    """Result of SGF correctness validation (backward-compatible wrapper)."""

    is_valid: bool
    issues: list[SgfIssue] = field(default_factory=list)

    board_size: int = 0
    black_stone_count: int = 0
    white_stone_count: int = 0
    solution_move_count: int = 0
    has_solution_tree: bool = False
    player_to_move: str = ""

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == IssueSeverity.ERROR)

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == IssueSeverity.WARNING)

    @classmethod
    def from_structural(cls, r: StructuralCheckResult) -> SgfCheckResult:
        """Build from a core ``StructuralCheckResult``."""
        return cls(
            is_valid=r.is_valid,
            issues=[SgfIssue.from_structural(si) for si in r.issues],
            board_size=r.board_size,
            black_stone_count=r.black_stone_count,
            white_stone_count=r.white_stone_count,
            solution_move_count=r.solution_move_count,
            has_solution_tree=r.has_solution_tree,
            player_to_move=r.player_to_move,
        )


def validate_sgf(
    sgf: str,
    *,
    min_stones: int = 2,
    max_board_size: int = 19,
    min_board_size: int = 5,
) -> SgfCheckResult:
    """Validate an SGF string for correctness.

    Delegates to ``tools.core.sgf_structural_checks.run_structural_checks``
    and wraps the result in ``SgfCheckResult`` for backward compatibility.

    Parameters
    ----------
    sgf : str
        SGF content string.
    min_stones : int
        Minimum initial stones required.
    max_board_size : int
        Maximum allowed board size.
    min_board_size : int
        Minimum allowed board size.

    Returns
    -------
    SgfCheckResult
        Validation result with issues list.
    """
    core_result = run_structural_checks(
        sgf,
        min_stones=min_stones,
        min_board_size=min_board_size,
        max_board_size=max_board_size,
    )
    return SgfCheckResult.from_structural(core_result)
