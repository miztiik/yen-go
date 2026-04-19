"""Tests for Pydantic models and telemetry infrastructure.

Tests model validation, event serialization, confidence scoring,
and the RunLogger JSONL output.

Run: pytest tools/pdf_to_sgf/tests/test_models_telemetry.py -q --no-header --tb=short
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))


# ---------------------------------------------------------------------------
# Model validation tests
# ---------------------------------------------------------------------------


class TestBoardConfidence:
    def test_valid_confidence(self):
        from tools.pdf_to_sgf.models import BoardConfidence

        bc = BoardConfidence(grid_completeness=0.8, stone_density=0.3, edge_fraction=1.0, overall=0.75)
        assert bc.overall == 0.75

    def test_clamps_to_bounds(self):
        from tools.pdf_to_sgf.models import BoardConfidence

        with pytest.raises(Exception):  # Pydantic validation error
            BoardConfidence(grid_completeness=1.5, overall=0.5)

    def test_serializes_to_json(self):
        from tools.pdf_to_sgf.models import BoardConfidence

        bc = BoardConfidence(grid_completeness=0.8, overall=0.7)
        data = json.loads(bc.model_dump_json())
        assert data["grid_completeness"] == 0.8
        assert data["overall"] == 0.7


class TestMatchConfidence:
    def test_all_fields_present(self):
        from tools.pdf_to_sgf.models import MatchConfidence

        mc = MatchConfidence(
            jaccard_similarity=0.6, stone_count_ratio=0.9,
            solution_plausibility=1.0, moves_ordered=0.5, overall=0.7,
        )
        data = mc.model_dump()
        assert "jaccard_similarity" in data
        assert "moves_ordered" in data


class TestPuzzleConfidence:
    def test_composite_structure(self):
        from tools.pdf_to_sgf.models import BoardConfidence, MatchConfidence, PuzzleConfidence

        bc = BoardConfidence(overall=0.8)
        mc = MatchConfidence(overall=0.6)
        pc = PuzzleConfidence(board=bc, match=mc, overall=0.7)
        assert pc.board.overall == 0.8
        assert pc.match.overall == 0.6


# ---------------------------------------------------------------------------
# Event serialization tests
# ---------------------------------------------------------------------------


class TestEvents:
    def test_run_start_serializes(self):
        from tools.pdf_to_sgf.models import RunStartEvent

        e = RunStartEvent(pdf_path="book.pdf", key_path="key.pdf", preset="pdf", command="convert")
        data = json.loads(e.model_dump_json())
        assert data["event_type"] == "run_start"
        assert data["pdf_path"] == "book.pdf"
        assert "timestamp" in data

    def test_error_event(self):
        from tools.pdf_to_sgf.models import ErrorEvent

        e = ErrorEvent(stage="recognition", detail="Grid detection failed", page_number=3, board_index=1)
        data = json.loads(e.model_dump_json())
        assert data["event_type"] == "error"
        assert data["stage"] == "recognition"

    def test_board_recognized_event(self):
        from tools.pdf_to_sgf.models import BoardConfidence, BoardRecognizedEvent

        e = BoardRecognizedEvent(
            page_number=3, board_index=0,
            grid_rows=7, grid_cols=6, black_stones=12, white_stones=14,
            confidence=BoardConfidence(overall=0.72),
        )
        data = json.loads(e.model_dump_json())
        assert data["black_stones"] == 12
        assert data["confidence"]["overall"] == 0.72

    def test_sgf_generated_event(self):
        from tools.pdf_to_sgf.models import BoardConfidence, PuzzleConfidence, SgfGeneratedEvent

        e = SgfGeneratedEvent(
            output_file="001_Problem_1.sgf", black_stones=5, white_stones=7,
            solution_moves=3, has_solution_tree=True, problem_label="Problem 1",
            yield_number=1, book_label="Problem_1",
            confidence=PuzzleConfidence(
                board=BoardConfidence(overall=0.8), overall=0.75,
            ),
        )
        data = json.loads(e.model_dump_json())
        assert data["has_solution_tree"] is True
        assert data["problem_label"] == "Problem 1"
        assert data["yield_number"] == 1
        assert data["book_label"] == "Problem_1"

    def test_run_summary_event(self):
        from tools.pdf_to_sgf.models import RunSummary

        s = RunSummary(
            pdf_path="book.pdf", pages_processed=5, boards_detected=15,
            sgf_generated=10, duration_seconds=12.5, avg_board_confidence=0.72,
        )
        data = json.loads(s.model_dump_json())
        assert data["event_type"] == "run_complete"
        assert data["sgf_generated"] == 10


# ---------------------------------------------------------------------------
# Telemetry RunLogger tests
# ---------------------------------------------------------------------------


class TestRunLogger:
    def test_emit_collects_events(self):
        from tools.pdf_to_sgf.models import RunStartEvent
        from tools.pdf_to_sgf.telemetry import RunLogger

        logger = RunLogger()
        logger.emit(RunStartEvent(pdf_path="test.pdf", command="convert"))
        assert len(logger.events) == 1

    def test_finalize_produces_summary(self):
        from tools.pdf_to_sgf.models import BoardConfidence, BoardRecognizedEvent, PageExtractedEvent, ExtractionSource
        from tools.pdf_to_sgf.telemetry import RunLogger

        logger = RunLogger()
        logger.emit(PageExtractedEvent(
            page_number=1, source=ExtractionSource.EMBEDDED, width=3168, height=2448,
        ))
        logger.emit(BoardRecognizedEvent(
            page_number=1, board_index=0, grid_rows=7, grid_cols=6,
            black_stones=5, white_stones=7,
            confidence=BoardConfidence(overall=0.8),
        ))
        summary = logger.finalize(pdf_path="test.pdf")
        assert summary.pages_processed == 1
        assert summary.boards_recognized == 1
        assert summary.avg_board_confidence == 0.8

    def test_jsonl_file_written(self, tmp_path):
        from tools.pdf_to_sgf.models import RunStartEvent
        from tools.pdf_to_sgf.telemetry import RunLogger

        logger = RunLogger(output_dir=tmp_path)
        logger.emit(RunStartEvent(pdf_path="test.pdf", command="extract"))
        summary = logger.finalize(pdf_path="test.pdf")

        jsonl_file = tmp_path / "run.jsonl"
        assert jsonl_file.exists()

        lines = jsonl_file.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 2  # RunStartEvent + RunSummary

        # Each line should be valid JSON
        for line in lines:
            data = json.loads(line)
            assert "event_type" in data
            assert "timestamp" in data

    def test_error_count(self):
        from tools.pdf_to_sgf.models import ErrorEvent
        from tools.pdf_to_sgf.telemetry import RunLogger

        logger = RunLogger()
        logger.emit(ErrorEvent(stage="detection", detail="fail1"))
        logger.emit(ErrorEvent(stage="recognition", detail="fail2"))
        assert logger.error_count == 2


# ---------------------------------------------------------------------------
# Confidence scoring tests
# ---------------------------------------------------------------------------


class TestConfidenceScoring:
    def _make_pos(self, board, top=0, left=0, edges=(True, True, True, True)):
        from tools.core.image_to_board import GridInfo, RecognizedPosition

        rows = len(board)
        cols = len(board[0]) if board else 0
        grid = GridInfo(
            x_lines=tuple(range(0, cols * 20, 20)),
            y_lines=tuple(range(0, rows * 20, 20)),
            x_spacing=20.0, y_spacing=20.0,
            width=cols * 20, height=rows * 20,
        )
        return RecognizedPosition(
            grid=grid, board=board, board_top=top, board_left=left,
            has_top_edge=edges[0], has_bottom_edge=edges[1],
            has_left_edge=edges[2], has_right_edge=edges[3],
        )

    def test_full_board_high_confidence(self):
        from tools.core.image_to_board import BLACK, WHITE, EMPTY
        from tools.pdf_to_sgf.problem_matcher import compute_board_confidence

        # 19x19 grid with some stones
        board = [[EMPTY] * 19 for _ in range(19)]
        board[0][0] = BLACK
        board[0][1] = WHITE
        pos = self._make_pos(board, edges=(True, True, True, True))
        conf = compute_board_confidence(pos)
        assert conf.grid_completeness == 1.0
        assert conf.edge_fraction == 1.0
        assert conf.overall > 0.8

    def test_partial_board_lower_confidence(self):
        from tools.core.image_to_board import BLACK, EMPTY
        from tools.pdf_to_sgf.problem_matcher import compute_board_confidence

        # 2x2 sub-board at top-left corner, 2 expected edges (top+left), both detected
        board = [[BLACK, EMPTY], [EMPTY, EMPTY]]
        pos = self._make_pos(board, edges=(True, False, True, False))
        conf = compute_board_confidence(pos)
        # grid_completeness: (2+2) / (2*2) = 1.0
        assert conf.grid_completeness == 1.0
        # edge_fraction: expected={top,left}=2, detected=2 → 1.0
        assert conf.edge_fraction == 1.0
        assert conf.overall > 0.8

    def test_partial_corner_crop_high_confidence(self):
        from tools.core.image_to_board import BLACK, WHITE, EMPTY
        from tools.pdf_to_sgf.problem_matcher import compute_board_confidence

        # 10x10 bottom-right corner on 19x19, both expected edges detected
        board = [[EMPTY] * 10 for _ in range(10)]
        board[8][8] = BLACK
        board[8][9] = WHITE
        board[9][8] = WHITE
        board[9][9] = BLACK
        pos = self._make_pos(board, top=9, left=9, edges=(False, True, False, True))
        conf = compute_board_confidence(pos)
        assert conf.grid_completeness == 1.0
        assert conf.edge_fraction == 1.0
        assert conf.overall > 0.8

    def test_missing_expected_edge_penalized(self):
        from tools.core.image_to_board import BLACK, EMPTY
        from tools.pdf_to_sgf.problem_matcher import compute_board_confidence

        # 10x10 at top-left corner, expects top+left edges, only top detected
        board = [[EMPTY] * 10 for _ in range(10)]
        board[0][0] = BLACK
        pos = self._make_pos(board, top=0, left=0, edges=(True, False, False, False))
        conf = compute_board_confidence(pos)
        assert conf.edge_fraction == 0.5  # 1 detected / 2 expected

    def test_center_crop_no_edge_penalty(self):
        from tools.core.image_to_board import BLACK, EMPTY
        from tools.pdf_to_sgf.problem_matcher import compute_board_confidence

        # 8x8 center crop, no edges expected, none detected
        board = [[EMPTY] * 8 for _ in range(8)]
        board[3][3] = BLACK
        pos = self._make_pos(board, top=5, left=5, edges=(False, False, False, False))
        conf = compute_board_confidence(pos)
        # No edges expected → edge_fraction = 1.0 (no penalty)
        assert conf.edge_fraction == 1.0
        assert conf.overall > 0.8

    def test_match_confidence_ideal_range(self):
        from tools.pdf_to_sgf.problem_matcher import compute_match_confidence, SolutionMove
        from tools.core.image_to_board import BLACK, EMPTY
        from tools.core.sgf_types import Color, Point

        board = [[BLACK, EMPTY], [EMPTY, EMPTY]]
        pos = self._make_pos(board)
        moves = [SolutionMove(color=Color.BLACK, point=Point(0, 0), order=1, confidence=0.9)]
        conf = compute_match_confidence(0.8, pos, pos, moves)
        assert conf.solution_plausibility == 1.0
        assert conf.moves_ordered == 1.0
        assert conf.overall > 0.5

    def test_match_confidence_no_moves(self):
        from tools.pdf_to_sgf.problem_matcher import compute_match_confidence
        from tools.core.image_to_board import BLACK, EMPTY

        board = [[BLACK, EMPTY], [EMPTY, EMPTY]]
        pos = self._make_pos(board)
        conf = compute_match_confidence(0.8, pos, pos, [])
        assert conf.solution_plausibility == 0.1
        assert conf.moves_ordered == 0.0


# ---------------------------------------------------------------------------
# Move ordering tests
# ---------------------------------------------------------------------------


class TestMoveOrdering:
    def test_ordered_moves_sort_by_digit(self):
        from tools.pdf_to_sgf.problem_matcher import _build_ordered_moves, SolutionMove
        from tools.core.image_to_board import BLACK, WHITE
        from tools.core.sgf_types import Color, Point

        stones = {(3, 5, BLACK), (4, 6, WHITE), (5, 7, BLACK)}
        digits = {(4, 6): (1, 0.9), (3, 5): (2, 0.8)}  # White=1, Black=2
        moves = _build_ordered_moves(stones, digits)
        assert len(moves) == 3
        # Numbered moves first, by digit order
        assert moves[0].order == 1
        assert moves[1].order == 2
        # Unnumbered last
        assert moves[2].order == 0

    def test_unnumbered_moves_sort_by_position(self):
        from tools.pdf_to_sgf.problem_matcher import _build_ordered_moves
        from tools.core.image_to_board import BLACK

        stones = {(3, 5, BLACK), (1, 2, BLACK), (3, 1, BLACK)}
        moves = _build_ordered_moves(stones, {})
        # All unnumbered, sorted by (y, x) = (row, col)
        assert moves[0].point.y == 1  # row 1
        assert moves[1].point.y == 3 and moves[1].point.x == 1  # row 3, col 1
        assert moves[2].point.y == 3 and moves[2].point.x == 5  # row 3, col 5
