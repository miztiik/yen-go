"""Tests for SGF correctness checker.

Tests the validate_sgf function and its various checks:
- Parseability (brackets, structure)
- Required properties (SZ, FF, GM)
- Initial stone validation (bounds, overlap)
- Solution move validation (bounds, occupied)
- Player-to-move consistency
- Edge cases (empty, no solution, excessive moves)

Run: pytest tools/pdf_to_sgf/tests/test_sgf_checker.py -q --no-header --tb=short
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.pdf_to_sgf.sgf_checker import (
    validate_sgf,
    IssueSeverity,
    SgfCheckResult,
    SgfIssue,
)


class TestParseability:
    def test_empty_sgf_is_invalid(self):
        result = validate_sgf("")
        assert not result.is_valid
        assert any(i.code == "EMPTY_SGF" for i in result.issues)

    def test_whitespace_only_is_invalid(self):
        result = validate_sgf("   \n  ")
        assert not result.is_valid

    def test_malformed_start_detected(self):
        result = validate_sgf("SZ[19]AB[aa]")
        assert any(i.code == "MALFORMED_START" for i in result.issues)

    def test_unbalanced_parens_detected(self):
        result = validate_sgf("(;SZ[19]FF[4]GM[1]AB[aa][bb]")
        assert any(i.code == "UNCLOSED_PARENS" for i in result.issues)

    def test_valid_minimal_sgf(self):
        sgf = "(;SZ[19]FF[4]GM[1]PL[B]AB[aa][bb]AW[cc];B[dd])"
        result = validate_sgf(sgf)
        assert result.is_valid
        assert result.board_size == 19
        assert result.black_stone_count == 2
        assert result.white_stone_count == 1
        assert result.solution_move_count == 1
        assert result.player_to_move == "B"


class TestRequiredProperties:
    def test_missing_sz_is_error(self):
        sgf = "(;FF[4]GM[1]AB[aa]AW[bb];B[cc])"
        result = validate_sgf(sgf)
        assert any(i.code == "MISSING_SZ" for i in result.issues)

    def test_missing_ff_is_warning(self):
        sgf = "(;SZ[19]GM[1]AB[aa]AW[bb];B[cc])"
        result = validate_sgf(sgf)
        assert any(i.code == "MISSING_FF" and i.severity == IssueSeverity.WARNING for i in result.issues)
        # Should still be valid (warning, not error)
        assert result.is_valid

    def test_missing_gm_is_warning(self):
        sgf = "(;SZ[19]FF[4]AB[aa]AW[bb];B[cc])"
        result = validate_sgf(sgf)
        assert any(i.code == "MISSING_GM" and i.severity == IssueSeverity.WARNING for i in result.issues)


class TestBoardSize:
    def test_board_too_small(self):
        sgf = "(;SZ[3]FF[4]GM[1]AB[aa]AW[ab];B[ba])"
        result = validate_sgf(sgf)
        assert any(i.code == "BOARD_TOO_SMALL" for i in result.issues)

    def test_board_too_large(self):
        sgf = "(;SZ[25]FF[4]GM[1]AB[aa]AW[bb];B[cc])"
        result = validate_sgf(sgf)
        assert any(i.code == "BOARD_TOO_LARGE" for i in result.issues)

    def test_valid_9x9_board(self):
        sgf = "(;SZ[9]FF[4]GM[1]PL[B]AB[aa][bb]AW[cc];B[dd])"
        result = validate_sgf(sgf)
        assert result.board_size == 9
        assert result.is_valid


class TestStoneValidation:
    def test_no_stones_is_error(self):
        sgf = "(;SZ[19]FF[4]GM[1];B[aa])"
        result = validate_sgf(sgf)
        assert any(i.code == "NO_STONES" for i in result.issues)

    def test_few_stones_is_warning(self):
        # Only 1 stone, default min is 2
        sgf = "(;SZ[19]FF[4]GM[1]AB[aa];B[bb])"
        result = validate_sgf(sgf)
        assert any(i.code == "FEW_STONES" for i in result.issues)

    def test_stone_out_of_bounds(self):
        # 't' = 19 in 0-indexed, but board is 0-18 for size 19
        sgf = "(;SZ[9]FF[4]GM[1]AB[aa][jj]AW[bb])"
        result = validate_sgf(sgf)
        assert any(i.code == "OUT_OF_BOUNDS" for i in result.issues)

    def test_overlapping_stones(self):
        # Same point for black and white
        sgf = "(;SZ[19]FF[4]GM[1]AB[cc]AW[cc];B[dd])"
        result = validate_sgf(sgf)
        assert any(i.code == "STONE_OVERLAP" for i in result.issues)


class TestSolutionMoves:
    def test_no_solution_is_warning(self):
        sgf = "(;SZ[19]FF[4]GM[1]AB[aa][bb]AW[cc])"
        result = validate_sgf(sgf)
        assert any(i.code == "NO_SOLUTION" for i in result.issues)
        # No solution is a warning, not an error
        assert result.is_valid

    def test_move_on_existing_stone_is_warning(self):
        # Move B[aa] on a point where there's already AB[aa]
        sgf = "(;SZ[19]FF[4]GM[1]AB[aa][bb]AW[cc];B[aa])"
        result = validate_sgf(sgf)
        assert any(i.code == "MOVE_ON_STONE" for i in result.issues)

    def test_valid_solution_moves_counted(self):
        sgf = "(;SZ[19]FF[4]GM[1]PL[B]AB[aa][bb]AW[cc];B[dd];W[ee];B[ff])"
        result = validate_sgf(sgf)
        assert result.solution_move_count == 3
        assert result.has_solution_tree

    def test_excessive_moves_warning(self):
        # 51 solution moves
        moves = "".join(f";B[{chr(ord('a') + i % 19)}{chr(ord('a') + i // 19)}]"
                        for i in range(51))
        sgf = f"(;SZ[19]FF[4]GM[1]PL[B]AB[aa]AW[bb]{moves})"
        result = validate_sgf(sgf)
        assert any(i.code == "EXCESSIVE_MOVES" for i in result.issues)


class TestPlayerToMove:
    def test_pl_matches_first_move(self):
        sgf = "(;SZ[19]FF[4]GM[1]PL[B]AB[aa][bb]AW[cc];B[dd])"
        result = validate_sgf(sgf)
        assert not any(i.code == "PL_MISMATCH" for i in result.issues)

    def test_pl_mismatch_detected(self):
        # PL says white but first move is black
        sgf = "(;SZ[19]FF[4]GM[1]PL[W]AB[aa][bb]AW[cc];B[dd])"
        result = validate_sgf(sgf)
        assert any(i.code == "PL_MISMATCH" for i in result.issues)


class TestResultMetadata:
    def test_result_has_metadata(self):
        sgf = "(;SZ[19]FF[4]GM[1]PL[B]AB[aa][bb][cc]AW[dd][ee];B[ff];W[gg])"
        result = validate_sgf(sgf)
        assert result.board_size == 19
        assert result.black_stone_count == 3
        assert result.white_stone_count == 2
        assert result.solution_move_count == 2
        assert result.player_to_move == "B"
        assert result.has_solution_tree

    def test_error_count_property(self):
        sgf = ""
        result = validate_sgf(sgf)
        assert result.error_count >= 1

    def test_warning_count_property(self):
        sgf = "(;SZ[19]GM[1]AB[aa][bb]AW[cc];B[dd])"  # missing FF
        result = validate_sgf(sgf)
        assert result.warning_count >= 1
