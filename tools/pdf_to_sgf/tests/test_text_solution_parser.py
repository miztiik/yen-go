"""Tests for text_solution_parser and Point.from_gtp()."""

from __future__ import annotations

import pytest

from tools.core.sgf_types import Point
from tools.pdf_to_sgf.text_solution_parser import (
    TextSolution,
    parse_solution_line,
    parse_text_solutions,
)


# ---------------------------------------------------------------------------
# Point.from_gtp() tests
# ---------------------------------------------------------------------------


class TestPointFromGtp:
    def test_a1_bottom_left(self):
        pt = Point.from_gtp("A1")
        assert pt == Point(0, 18)

    def test_d1(self):
        pt = Point.from_gtp("D1")
        assert pt == Point(3, 18)

    def test_t19_top_right(self):
        pt = Point.from_gtp("T19")
        assert pt == Point(18, 0)

    def test_j10_center_skips_i(self):
        """J is column index 8 because I is skipped."""
        pt = Point.from_gtp("J10")
        assert pt == Point(8, 9)

    def test_h8_before_skip(self):
        """H is column index 7, just before the I skip."""
        pt = Point.from_gtp("H8")
        assert pt == Point(7, 11)

    def test_lowercase(self):
        pt = Point.from_gtp("d4")
        assert pt == Point(3, 15)

    def test_roundtrip(self):
        pt = Point.from_gtp("Q16")
        assert pt.to_gtp() == "Q16"

    def test_roundtrip_a1(self):
        pt = Point.from_gtp("A1")
        assert pt.to_gtp() == "A1"

    def test_invalid_column_i(self):
        with pytest.raises(ValueError, match="column letter"):
            Point.from_gtp("I5")

    def test_invalid_too_short(self):
        with pytest.raises(ValueError, match="Invalid GTP"):
            Point.from_gtp("A")

    def test_invalid_row_zero(self):
        with pytest.raises(ValueError, match="out of range"):
            Point.from_gtp("A0")

    def test_invalid_row_20(self):
        with pytest.raises(ValueError, match="out of range"):
            Point.from_gtp("A20")


# ---------------------------------------------------------------------------
# parse_solution_line() tests
# ---------------------------------------------------------------------------


class TestParseSolutionLine:
    def test_simple_3_moves(self):
        sol = parse_solution_line("(1) D1 F1 G1")
        assert sol is not None
        assert sol.problem_number == 1
        assert len(sol.moves) == 3
        assert sol.moves[0] == Point.from_gtp("D1")
        assert sol.moves[1] == Point.from_gtp("F1")
        assert sol.moves[2] == Point.from_gtp("G1")

    def test_longer_sequence(self):
        sol = parse_solution_line("(2) D1 C1 A2 A4 E1 A5 D2")
        assert sol is not None
        assert sol.problem_number == 2
        assert len(sol.moves) == 7

    def test_large_problem_number(self):
        sol = parse_solution_line("(288) F1 G1 F1")
        assert sol is not None
        assert sol.problem_number == 288
        assert len(sol.moves) == 3

    def test_non_matching_returns_none(self):
        assert parse_solution_line("Just some text") is None
        assert parse_solution_line("") is None
        assert parse_solution_line("42. D1 F1") is None  # no parentheses

    def test_preserves_raw_text(self):
        sol = parse_solution_line("(5) A1 B2 C3")
        assert sol is not None
        assert "(5)" in sol.raw_text


# ---------------------------------------------------------------------------
# parse_text_solutions() tests
# ---------------------------------------------------------------------------


class TestParseTextSolutions:
    def test_multi_line_block(self):
        text = """(1) D1 F1 G1
(2) D1 C1 A2 A4 E1 A5 D2
(3) B1 C2 B2"""
        result = parse_text_solutions(text)
        assert len(result) == 3
        assert 1 in result
        assert 2 in result
        assert 3 in result
        assert len(result[1].moves) == 3
        assert len(result[2].moves) == 7
        assert len(result[3].moves) == 3

    def test_with_surrounding_text(self):
        text = """Solutions
(1) D1 F1 G1
(2) A1 B1"""
        result = parse_text_solutions(text)
        assert len(result) == 2

    def test_empty_text(self):
        assert parse_text_solutions("") == {}
        assert parse_text_solutions("no solutions here") == {}

    def test_non_sequential_numbers(self):
        text = "(10) A1 B1 (20) C3 D4 E5"
        result = parse_text_solutions(text)
        assert len(result) == 2
        assert 10 in result
        assert 20 in result
