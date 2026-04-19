"""Tests for SGF structural validation checks.

Covers each individual check function and the ``run_structural_checks``
orchestrator. Verifies issue codes (IntEnum), severity levels, context
dicts, and result metadata population.

Run: pytest tools/core/tests/test_sgf_structural_checks.py -q --no-header --tb=short
"""

from __future__ import annotations

from tools.core.sgf_structural_checks import (
    IssueCode,
    StructuralCheckResult,
    StructuralIssueSeverity,
    check_board_size,
    check_consecutive_same_point,
    check_excessive_moves,
    check_parseability,
    check_player_to_move,
    check_required_properties,
    check_stone_bounds,
    check_stone_overlap,
    extract_setup_stones,
    extract_solution_moves,
    run_structural_checks,
)


# ====================================================================
# Helpers
# ====================================================================

def _result() -> StructuralCheckResult:
    """Create a blank result for individual check testing."""
    return StructuralCheckResult.empty()


def _has_code(result: StructuralCheckResult, code: IssueCode) -> bool:
    return any(i.code == code for i in result.issues)


def _issue_with_code(
    result: StructuralCheckResult, code: IssueCode,
) -> dict:
    """Return context dict for the first issue matching code."""
    for i in result.issues:
        if i.code == code:
            return i.context
    return {}


# ====================================================================
# Check 1: Parseability
# ====================================================================


class TestCheckParseability:
    def test_empty_sgf_emits_error(self) -> None:
        r = _result()
        check_parseability("", r)
        assert _has_code(r, IssueCode.EMPTY_SGF)

    def test_whitespace_only_emits_error(self) -> None:
        r = _result()
        check_parseability("   \n  ", r)
        assert _has_code(r, IssueCode.EMPTY_SGF)

    def test_missing_open_paren_emits_malformed_start(self) -> None:
        r = _result()
        check_parseability("SZ[19]AB[aa]", r)
        assert _has_code(r, IssueCode.MALFORMED_START)

    def test_unbalanced_close_paren(self) -> None:
        r = _result()
        check_parseability("(;SZ[19]))", r)
        assert _has_code(r, IssueCode.UNBALANCED_PARENS)

    def test_unclosed_paren(self) -> None:
        r = _result()
        check_parseability("(;SZ[19]FF[4]GM[1]AB[aa][bb]", r)
        assert _has_code(r, IssueCode.UNCLOSED_PARENS)

    def test_unclosed_paren_has_context(self) -> None:
        r = _result()
        check_parseability("(;SZ[19]FF[4]GM[1]AB[aa][bb]", r)
        ctx = _issue_with_code(r, IssueCode.UNCLOSED_PARENS)
        assert ctx["remaining"] == 1

    def test_well_formed_sgf_no_issues(self) -> None:
        r = _result()
        check_parseability("(;SZ[19]FF[4]GM[1]AB[aa]AW[bb];B[cc])", r)
        assert len(r.issues) == 0


# ====================================================================
# Check 2: Required properties
# ====================================================================


class TestCheckRequiredProperties:
    def test_missing_sz_is_error(self) -> None:
        r = _result()
        check_required_properties("(;FF[4]GM[1]AB[aa])", r)
        assert _has_code(r, IssueCode.MISSING_SZ)
        issue = [i for i in r.issues if i.code == IssueCode.MISSING_SZ][0]
        assert issue.severity == StructuralIssueSeverity.ERROR

    def test_missing_ff_is_warning(self) -> None:
        r = _result()
        check_required_properties("(;SZ[19]GM[1]AB[aa])", r)
        assert _has_code(r, IssueCode.MISSING_FF)
        issue = [i for i in r.issues if i.code == IssueCode.MISSING_FF][0]
        assert issue.severity == StructuralIssueSeverity.WARNING

    def test_missing_gm_is_warning(self) -> None:
        r = _result()
        check_required_properties("(;SZ[19]FF[4]AB[aa])", r)
        assert _has_code(r, IssueCode.MISSING_GM)

    def test_all_present_no_issues(self) -> None:
        r = _result()
        check_required_properties("(;SZ[19]FF[4]GM[1]AB[aa])", r)
        assert len(r.issues) == 0


# ====================================================================
# Check 3: Board size
# ====================================================================


class TestCheckBoardSize:
    def test_board_too_small(self) -> None:
        r = _result()
        check_board_size("(;SZ[3]FF[4]GM[1])", r)
        assert _has_code(r, IssueCode.BOARD_TOO_SMALL)
        ctx = _issue_with_code(r, IssueCode.BOARD_TOO_SMALL)
        assert ctx["board_size"] == 3

    def test_board_too_large(self) -> None:
        r = _result()
        check_board_size("(;SZ[25]FF[4]GM[1])", r)
        assert _has_code(r, IssueCode.BOARD_TOO_LARGE)

    def test_valid_size_sets_result(self) -> None:
        r = _result()
        check_board_size("(;SZ[9]FF[4]GM[1])", r)
        assert r.board_size == 9
        assert len(r.issues) == 0

    def test_missing_sz_defaults_to_19(self) -> None:
        r = _result()
        check_board_size("(;FF[4]GM[1])", r)
        assert r.board_size == 19


# ====================================================================
# Check 4: Setup stone extraction
# ====================================================================


class TestExtractSetupStones:
    def test_no_stones_emits_error(self) -> None:
        r = _result()
        extract_setup_stones("(;SZ[19]FF[4]GM[1])", r)
        assert _has_code(r, IssueCode.NO_STONES)

    def test_few_stones_emits_warning(self) -> None:
        r = _result()
        extract_setup_stones("(;SZ[19]FF[4]GM[1]AB[aa])", r, min_stones=2)
        assert _has_code(r, IssueCode.FEW_STONES)
        ctx = _issue_with_code(r, IssueCode.FEW_STONES)
        assert ctx["count"] == 1
        assert ctx["minimum"] == 2

    def test_multi_stone_ab_format(self) -> None:
        r = _result()
        extract_setup_stones("(;SZ[19]AB[aa][bb][cc]AW[dd])", r)
        assert r.black_stone_count == 3
        assert r.white_stone_count == 1

    def test_populates_stone_sets(self) -> None:
        r = _result()
        extract_setup_stones("(;AB[cd]AW[ef])", r, min_stones=1)
        assert (2, 3) in r.black_stones
        assert (4, 5) in r.white_stones

    def test_sufficient_stones_no_issues(self) -> None:
        r = _result()
        extract_setup_stones("(;AB[aa][bb]AW[cc])", r, min_stones=2)
        assert not _has_code(r, IssueCode.NO_STONES)
        assert not _has_code(r, IssueCode.FEW_STONES)


# ====================================================================
# Check 5: Stone bounds
# ====================================================================


class TestCheckStoneBounds:
    def test_stone_in_bounds_no_issue(self) -> None:
        r = _result()
        r.board_size = 19
        r.black_stones = {(0, 0), (18, 18)}
        check_stone_bounds(r)
        assert len(r.issues) == 0

    def test_stone_out_of_bounds_emits_error(self) -> None:
        r = _result()
        r.board_size = 9
        r.black_stones = {(9, 9)}  # 0-indexed, size 9 means max index 8
        check_stone_bounds(r)
        assert _has_code(r, IssueCode.OUT_OF_BOUNDS)
        ctx = _issue_with_code(r, IssueCode.OUT_OF_BOUNDS)
        assert ctx["board_size"] == 9


# ====================================================================
# Check 6: Stone overlap
# ====================================================================


class TestCheckStoneOverlap:
    def test_no_overlap_no_issue(self) -> None:
        r = _result()
        r.black_stones = {(0, 0)}
        r.white_stones = {(1, 1)}
        check_stone_overlap(r)
        assert len(r.issues) == 0

    def test_overlap_emits_error(self) -> None:
        r = _result()
        r.black_stones = {(2, 3)}
        r.white_stones = {(2, 3)}
        check_stone_overlap(r)
        assert _has_code(r, IssueCode.STONE_OVERLAP)
        ctx = _issue_with_code(r, IssueCode.STONE_OVERLAP)
        assert ctx["coord"] == (2, 3)


# ====================================================================
# Check 7: Solution move extraction
# ====================================================================


class TestExtractSolutionMoves:
    def test_no_moves_emits_no_solution(self) -> None:
        r = _result()
        extract_solution_moves("(;SZ[19]AB[aa]AW[bb])", r)
        assert _has_code(r, IssueCode.NO_SOLUTION)

    def test_moves_extracted_and_counted(self) -> None:
        r = _result()
        r.board_size = 19
        extract_solution_moves("(;SZ[19]AB[aa]AW[bb];B[cc];W[dd];B[ee])", r)
        assert r.solution_move_count == 3
        assert r.has_solution_tree

    def test_move_out_of_bounds(self) -> None:
        r = _result()
        r.board_size = 9
        extract_solution_moves("(;SZ[9]AB[aa]AW[bb];B[jj])", r)
        assert _has_code(r, IssueCode.MOVE_OUT_OF_BOUNDS)

    def test_populates_solution_moves_list(self) -> None:
        r = _result()
        r.board_size = 19
        extract_solution_moves("(;AB[aa];B[cd];W[ef])", r)
        assert r.solution_moves == [("B", 2, 3), ("W", 4, 5)]


# ====================================================================
# Check 8: Player to move
# ====================================================================


class TestCheckPlayerToMove:
    def test_pl_matches_first_move_no_issue(self) -> None:
        r = _result()
        r.solution_moves = [("B", 2, 3)]
        check_player_to_move("(;PL[B]AB[aa]AW[bb];B[cd])", r)
        assert not _has_code(r, IssueCode.PL_MISMATCH)

    def test_pl_mismatch_emits_warning(self) -> None:
        r = _result()
        r.solution_moves = [("B", 2, 3)]
        check_player_to_move("(;PL[W]AB[aa]AW[bb];B[cd])", r)
        assert _has_code(r, IssueCode.PL_MISMATCH)
        ctx = _issue_with_code(r, IssueCode.PL_MISMATCH)
        assert ctx["declared"] == "W"
        assert ctx["actual"] == "B"

    def test_no_pl_property_no_issue(self) -> None:
        r = _result()
        r.solution_moves = [("B", 2, 3)]
        check_player_to_move("(;SZ[19]AB[aa]AW[bb];B[cd])", r)
        assert not _has_code(r, IssueCode.PL_MISMATCH)


# ====================================================================
# Check 9: Excessive moves
# ====================================================================


class TestCheckExcessiveMoves:
    def test_below_threshold_no_issue(self) -> None:
        r = _result()
        r.solution_moves = [("B", i, 0) for i in range(10)]
        check_excessive_moves(r, threshold=50)
        assert not _has_code(r, IssueCode.EXCESSIVE_MOVES)

    def test_above_threshold_emits_warning(self) -> None:
        r = _result()
        r.solution_moves = [("B", i % 19, i // 19) for i in range(51)]
        check_excessive_moves(r, threshold=50)
        assert _has_code(r, IssueCode.EXCESSIVE_MOVES)
        ctx = _issue_with_code(r, IssueCode.EXCESSIVE_MOVES)
        assert ctx["count"] == 51
        assert ctx["threshold"] == 50


# ====================================================================
# Check 10: Consecutive same-point
# ====================================================================


class TestCheckConsecutiveSamePoint:
    def test_consecutive_same_point_is_error(self) -> None:
        # B[cc] followed immediately by W[cc] = consecutive same-point
        sgf = "(;SZ[19]FF[4]GM[1]PL[B]AB[aa][bb]AW[dd];B[cc];W[cc])"
        r = _result()
        r.black_stones = {(0, 0), (1, 1)}
        r.white_stones = {(3, 3)}
        check_consecutive_same_point(sgf, r)
        assert _has_code(r, IssueCode.CONSECUTIVE_SAME_POINT)

    def test_non_consecutive_on_setup_is_move_on_stone(self) -> None:
        # B[aa] where aa is an existing setup stone
        sgf = "(;SZ[19]FF[4]GM[1]PL[B]AB[aa][bb]AW[cc];B[aa])"
        r = _result()
        r.black_stones = {(0, 0), (1, 1)}
        r.white_stones = {(2, 2)}
        check_consecutive_same_point(sgf, r)
        assert _has_code(r, IssueCode.MOVE_ON_STONE)

    def test_distinct_moves_no_issue(self) -> None:
        sgf = "(;SZ[19]FF[4]GM[1]PL[B]AB[aa][bb]AW[cc];B[dd];W[ee])"
        r = _result()
        r.black_stones = {(0, 0), (1, 1)}
        r.white_stones = {(2, 2)}
        check_consecutive_same_point(sgf, r)
        assert not _has_code(r, IssueCode.CONSECUTIVE_SAME_POINT)
        assert not _has_code(r, IssueCode.MOVE_ON_STONE)

    def test_malformed_sgf_skips_gracefully(self) -> None:
        r = _result()
        check_consecutive_same_point("not valid sgf at all", r)
        assert not _has_code(r, IssueCode.CONSECUTIVE_SAME_POINT)


# ====================================================================
# Orchestrator: run_structural_checks
# ====================================================================


class TestRunStructuralChecks:
    def test_valid_minimal_sgf(self) -> None:
        sgf = "(;SZ[19]FF[4]GM[1]PL[B]AB[aa][bb]AW[cc];B[dd])"
        result = run_structural_checks(sgf)
        assert result.is_valid

    def test_empty_sgf_returns_invalid(self) -> None:
        result = run_structural_checks("")
        assert not result.is_valid
        assert _has_code(result, IssueCode.EMPTY_SGF)

    def test_result_metadata_populated(self) -> None:
        sgf = "(;SZ[19]FF[4]GM[1]PL[B]AB[aa][bb][cc]AW[dd][ee];B[ff];W[gg])"
        result = run_structural_checks(sgf)
        assert result.board_size == 19
        assert result.black_stone_count == 3
        assert result.white_stone_count == 2
        assert result.solution_move_count == 2
        assert result.player_to_move == "B"
        assert result.has_solution_tree

    def test_custom_min_stones(self) -> None:
        sgf = "(;SZ[19]FF[4]GM[1]AB[aa];B[bb])"
        result = run_structural_checks(sgf, min_stones=1)
        assert not _has_code(result, IssueCode.FEW_STONES)
        result2 = run_structural_checks(sgf, min_stones=3)
        assert _has_code(result2, IssueCode.FEW_STONES)

    def test_custom_board_size_bounds(self) -> None:
        sgf = "(;SZ[5]FF[4]GM[1]AB[aa][bb]AW[cc];B[dd])"
        result = run_structural_checks(sgf, min_board_size=5)
        assert not _has_code(result, IssueCode.BOARD_TOO_SMALL)
        result2 = run_structural_checks(sgf, min_board_size=7)
        assert _has_code(result2, IssueCode.BOARD_TOO_SMALL)

    def test_context_dicts_present(self) -> None:
        sgf = "(;SZ[19]FF[4]GM[1]PL[W]AB[aa]AW[bb];B[cc])"
        result = run_structural_checks(sgf)
        ctx = _issue_with_code(result, IssueCode.PL_MISMATCH)
        assert ctx["declared"] == "W"
        assert ctx["actual"] == "B"

    def test_issue_codes_are_intenum(self) -> None:
        result = run_structural_checks("")
        for issue in result.issues:
            assert isinstance(issue.code, IssueCode)
            assert isinstance(issue.code, int)
