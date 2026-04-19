"""Tests for problem-solution matcher and SGF generation.

Tests both unit-level functions (Jaccard, board stone sets) and
integration-level matching with sample PDFs.

Run: pytest tools/pdf_to_sgf/tests/test_matcher.py -q --no-header --tb=short
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.core.image_to_board import EMPTY, BLACK, WHITE, RecognizedPosition, GridInfo
from tools.core.sgf_types import Color, Point
from tools.pdf_to_sgf.problem_matcher import (
    MatchResult,
    SolutionMove,
    _board_stone_set,
    _detect_wrong_moves,
    _jaccard_similarity,
    compute_board_confidence,
    match_problems,
    position_to_sgf,
)
from tools.pdf_to_sgf.models import BoardConfidence, MatchConfidence, MatchStrategy

SAMPLES_DIR = Path(__file__).resolve().parents[1] / "_test_samples"
PROBLEM_PDF = SAMPLES_DIR / "demo-a.pdf"
KEY_PDF = SAMPLES_DIR / "demo-a-key.pdf"

skip_no_samples = pytest.mark.skipif(
    not PROBLEM_PDF.exists(),
    reason="Sample PDFs not downloaded.",
)


# ---------------------------------------------------------------------------
# Unit Tests — helper functions
# ---------------------------------------------------------------------------


class TestJaccardSimilarity:
    def test_identical_sets(self):
        s = {(0, 0), (1, 1), (2, 2)}
        assert _jaccard_similarity(s, s) == 1.0

    def test_empty_sets(self):
        assert _jaccard_similarity(set(), set()) == 0.0

    def test_disjoint_sets(self):
        a = {(0, 0), (1, 1)}
        b = {(2, 2), (3, 3)}
        assert _jaccard_similarity(a, b) == 0.0

    def test_partial_overlap(self):
        a = {1, 2, 3}
        b = {2, 3, 4}
        # intersection=2, union=4 → 0.5
        assert _jaccard_similarity(a, b) == 0.5

    def test_subset(self):
        a = {1, 2}
        b = {1, 2, 3, 4}
        # intersection=2, union=4 → 0.5
        assert _jaccard_similarity(a, b) == 0.5


class TestBoardStoneSet:
    def _make_grid(self, rows: int, cols: int) -> GridInfo:
        return GridInfo(
            x_lines=tuple(range(cols)),
            y_lines=tuple(range(rows)),
            x_spacing=10.0,
            y_spacing=10.0,
            width=cols * 10,
            height=rows * 10,
        )

    def _make_pos(self, board: list[list[str]], top: int = 0, left: int = 0) -> RecognizedPosition:
        rows = len(board)
        cols = len(board[0]) if board else 0
        return RecognizedPosition(
            grid=self._make_grid(rows, cols),
            board=board,
            board_top=top,
            board_left=left,
            has_top_edge=True,
            has_bottom_edge=True,
            has_left_edge=True,
            has_right_edge=True,
        )

    def test_empty_board(self):
        pos = self._make_pos([[EMPTY, EMPTY], [EMPTY, EMPTY]])
        stones, occupied = _board_stone_set(pos)
        assert len(stones) == 0
        assert len(occupied) == 0

    def test_stones_extracted_with_offset(self):
        board = [[BLACK, EMPTY], [EMPTY, WHITE]]
        pos = self._make_pos(board, top=3, left=5)
        stones, occupied = _board_stone_set(pos)
        assert (3, 5, BLACK) in stones
        assert (4, 6, WHITE) in stones
        assert (3, 5) in occupied
        assert (4, 6) in occupied
        assert len(stones) == 2


# ---------------------------------------------------------------------------
# Unit Tests — SGF generation
# ---------------------------------------------------------------------------


class TestPositionToSgf:
    def _make_match(self) -> MatchResult:
        board = [[BLACK, EMPTY, WHITE], [EMPTY, EMPTY, EMPTY]]
        grid = GridInfo(
            x_lines=(0, 10, 20),
            y_lines=(0, 10),
            x_spacing=10.0,
            y_spacing=10.0,
            width=30,
            height=20,
        )
        pos = RecognizedPosition(
            grid=grid,
            board=board,
            board_top=0,
            board_left=0,
            has_top_edge=True,
            has_bottom_edge=True,
            has_left_edge=True,
            has_right_edge=True,
        )
        return MatchResult(
            problem_index=0,
            answer_index=0,
            similarity=0.9,
            problem_pos=pos,
            answer_pos=pos,
            solution_moves=[
                SolutionMove(color=Color.BLACK, point=Point(1, 0), order=1),
            ],
            problem_label="Problem 1",
            strategy=MatchStrategy.JACCARD,
            board_confidence=BoardConfidence(overall=0.8),
            match_confidence=MatchConfidence(overall=0.7),
        )

    def test_sgf_is_valid_string(self):
        sgf = position_to_sgf(self._make_match())
        assert sgf.startswith("(;")
        assert "SZ[19]" in sgf
        assert "AB[" in sgf
        assert "AW[" in sgf

    def test_sgf_contains_player_to_move(self):
        sgf = position_to_sgf(self._make_match())
        assert "PL[B]" in sgf

    def test_sgf_contains_solution_move(self):
        sgf = position_to_sgf(self._make_match())
        # Solution move at Point(1, 0) → SGF coord "ba"
        assert ";B[ba]" in sgf

    def test_empty_solution_still_produces_sgf(self):
        match = self._make_match()
        match.solution_moves = []
        sgf = position_to_sgf(match)
        assert sgf.startswith("(;")
        assert "AB[" in sgf

    def test_sgf_contains_root_comment_with_player(self):
        sgf = position_to_sgf(self._make_match())
        assert "Black to play" in sgf

    def test_sgf_does_not_contain_confidence_in_comment(self):
        sgf = position_to_sgf(self._make_match())
        assert "Match confidence:" not in sgf
        assert "Board confidence:" not in sgf


# ---------------------------------------------------------------------------
# Integration Tests — with sample PDFs
# ---------------------------------------------------------------------------


class TestMatcherIntegration:
    @skip_no_samples
    def test_match_single_page_produces_results(self):
        """Match page 3 problems against page 3 answers."""
        from tools.pdf_to_sgf.pdf_extractor import extract_pages
        from tools.pdf_to_sgf.board_detector import detect_boards

        problem_pages = extract_pages(PROBLEM_PDF, page_range=(3, 3))
        answer_pages = extract_pages(KEY_PDF, page_range=(3, 3))

        problem_boards = []
        for page in problem_pages:
            for board in detect_boards(page.image):
                problem_boards.append(board.image)

        answer_boards = []
        for page in answer_pages:
            for board in detect_boards(page.image):
                answer_boards.append(board.image)

        matches = match_problems(problem_boards, answer_boards, min_similarity=0.2)
        assert len(matches) >= 1, "Expected at least 1 matched pair"

    @skip_no_samples
    def test_matched_pairs_have_solution_moves(self):
        """Matched pairs should have at least one solution move."""
        from tools.pdf_to_sgf.pdf_extractor import extract_pages
        from tools.pdf_to_sgf.board_detector import detect_boards

        problem_pages = extract_pages(PROBLEM_PDF, page_range=(3, 3))
        answer_pages = extract_pages(KEY_PDF, page_range=(3, 3))

        problem_boards = [b.image for p in problem_pages for b in detect_boards(p.image)]
        answer_boards = [b.image for p in answer_pages for b in detect_boards(p.image)]

        matches = match_problems(problem_boards, answer_boards, min_similarity=0.2)
        for m in matches:
            # After diffing, there should be at least one new stone
            assert len(m.solution_moves) >= 1, (
                f"Match p{m.problem_index}→a{m.answer_index} has no solution moves"
            )

    @skip_no_samples
    def test_generated_sgf_is_parseable(self):
        """Generated SGF from matches should be parseable."""
        from tools.pdf_to_sgf.pdf_extractor import extract_pages
        from tools.pdf_to_sgf.board_detector import detect_boards

        problem_pages = extract_pages(PROBLEM_PDF, page_range=(3, 3))
        answer_pages = extract_pages(KEY_PDF, page_range=(3, 3))

        problem_boards = [b.image for p in problem_pages for b in detect_boards(p.image)]
        answer_boards = [b.image for p in answer_pages for b in detect_boards(p.image)]

        matches = match_problems(problem_boards, answer_boards, min_similarity=0.2)
        assert len(matches) >= 1

        for m in matches:
            sgf = position_to_sgf(m)
            assert sgf.startswith("(;")
            assert "SZ[19]" in sgf
            assert "FF[4]" in sgf


class TestPositionalFallback:
    """Test the positional matching fallback when similarity fails."""

    def test_fallback_with_equal_board_counts(self):
        """When Jaccard fails but counts match, use positional ordering."""
        from PIL import Image
        import numpy as np

        # Create two distinct synthetic images: 100x100, all white
        # They'll produce empty boards → neither can match by Jaccard
        # But with same count (2 each) the fallback should pair them
        img1 = Image.fromarray(np.full((100, 100, 3), 200, dtype=np.uint8))
        img2 = Image.fromarray(np.full((100, 100, 3), 200, dtype=np.uint8))

        matches = match_problems(
            [img1, img2],
            [img1, img2],
            min_similarity=0.0,  # allow any similarity
        )
        # Should get 2 positional matches
        assert len(matches) == 2
        assert matches[0].problem_index == 0
        assert matches[1].problem_index == 1


# ---------------------------------------------------------------------------
# Wrong-move variation tests
# ---------------------------------------------------------------------------


class TestWrongMoveDetection:
    """Tests for wrong-move detection and variation extraction."""

    def _make_pos(self, stones: dict[tuple[int, int], str]) -> RecognizedPosition:
        """Create a minimal RecognizedPosition for testing."""
        board = [["." for _ in range(9)] for _ in range(9)]
        for (r, c), color in stones.items():
            board[r][c] = color
        grid = GridInfo(
            x_lines=tuple(range(0, 180, 20)),
            y_lines=tuple(range(0, 180, 20)),
            x_spacing=20.0, y_spacing=20.0,
            width=180, height=180,
        )
        return RecognizedPosition(
            grid=grid, board=board,
            board_top=0, board_left=0,
            has_top_edge=True, has_bottom_edge=True,
            has_left_edge=True, has_right_edge=True,
        )

    def test_no_removed_stones(self):
        # Same stones in problem and answer
        stones = {(2, 3): "X", (3, 3): "O"}
        p = self._make_pos(stones)
        a = self._make_pos(stones)
        result = _detect_wrong_moves(p, a)
        assert result == []

    def test_removed_stone_detected(self):
        p = self._make_pos({(2, 3): "X", (3, 3): "O", (4, 4): "X"})
        a = self._make_pos({(2, 3): "X", (3, 3): "O"})  # (4,4) removed
        result = _detect_wrong_moves(p, a)
        assert len(result) == 1
        assert result[0].point.x == 4
        assert result[0].point.y == 4

    def test_multiple_removed_stones(self):
        p = self._make_pos({(1, 1): "X", (2, 2): "O", (3, 3): "X"})
        a = self._make_pos({(2, 2): "O"})  # (1,1) and (3,3) removed
        result = _detect_wrong_moves(p, a)
        assert len(result) == 2

    def test_variation_in_sgf_output(self):
        from tools.pdf_to_sgf.problem_matcher import position_to_sgf, MatchResult, SolutionMove

        board = [["." for _ in range(9)] for _ in range(9)]
        board[2][3] = "X"
        board[3][3] = "O"
        grid = GridInfo(
            x_lines=tuple(range(0, 180, 20)),
            y_lines=tuple(range(0, 180, 20)),
            x_spacing=20.0, y_spacing=20.0,
            width=180, height=180,
        )
        pos = RecognizedPosition(
            grid=grid, board=board,
            board_top=0, board_left=0,
            has_top_edge=True, has_bottom_edge=True,
            has_left_edge=True, has_right_edge=True,
        )

        match = MatchResult(
            problem_index=0, answer_index=0, similarity=0.9,
            problem_pos=pos, answer_pos=pos,
            solution_moves=[SolutionMove(Color.BLACK, Point(5, 5), order=1)],
            wrong_moves=[SolutionMove(Color.BLACK, Point(6, 6), order=0)],
        )
        sgf = position_to_sgf(match, board_size=9)
        # Should contain BM[1] for wrong move
        assert "BM[1]" in sgf
        # Should contain the correct move too
        assert "B[ff]" in sgf  # Point(5,5) = ff in SGF coords

    def test_refutation_branch_in_sgf(self):
        from tools.pdf_to_sgf.problem_matcher import position_to_sgf, MatchResult, SolutionMove

        board = [["." for _ in range(9)] for _ in range(9)]
        board[2][3] = "X"
        grid = GridInfo(
            x_lines=tuple(range(0, 180, 20)),
            y_lines=tuple(range(0, 180, 20)),
            x_spacing=20.0, y_spacing=20.0,
            width=180, height=180,
        )
        pos = RecognizedPosition(
            grid=grid, board=board,
            board_top=0, board_left=0,
            has_top_edge=True, has_bottom_edge=True,
            has_left_edge=True, has_right_edge=True,
        )

        match = MatchResult(
            problem_index=0, answer_index=0, similarity=0.9,
            problem_pos=pos, answer_pos=pos,
            solution_moves=[SolutionMove(Color.BLACK, Point(4, 4), order=1)],
            variations=[
                [
                    SolutionMove(Color.BLACK, Point(6, 6), order=0),
                    SolutionMove(Color.WHITE, Point(7, 7), order=0),
                ],
            ],
        )
        sgf = position_to_sgf(match, board_size=9)
        assert "BM[1]" in sgf
        # Should have variation parentheses for multi-branch
        assert "(" in sgf
