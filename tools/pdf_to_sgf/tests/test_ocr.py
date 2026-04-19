"""Tests for OCR utilities.

All tests mock pytesseract — no Tesseract installation required.
Run: pytest tools/pdf_to_sgf/tests/test_ocr.py -q --no-header --tb=short
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import numpy as np
import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

# Eager import so @patch("tools.pdf_to_sgf.ocr.xxx") can resolve the module
import tools.pdf_to_sgf.ocr as _ocr_mod  # noqa: F401, E402
from tools.pdf_to_sgf.ocr import (  # noqa: E402
    detect_answer_page,
    detect_player_to_move,
    detect_problem_label,
    ensure_tesseract,
    find_answer_start,
    ocr_line,
    ocr_region,
)


def _make_image(w: int = 400, h: int = 300) -> Image.Image:
    """Create a simple white test image."""
    return Image.fromarray(np.full((h, w, 3), 255, dtype=np.uint8))


# ---------------------------------------------------------------------------
# ensure_tesseract
# ---------------------------------------------------------------------------

class TestEnsureTesseract:
    @patch("tools.pdf_to_sgf.ocr._get_pytesseract")
    def test_returns_version_when_available(self, mock_get_pt):
        mock_pt = MagicMock()
        mock_get_pt.return_value = mock_pt
        mock_pt.get_tesseract_version.return_value = "5.3.0"
        assert ensure_tesseract() == "5.3.0"

    @patch("tools.pdf_to_sgf.ocr._get_pytesseract")
    def test_raises_on_missing_tesseract(self, mock_get_pt):
        # Use a custom exception instead of importing real pytesseract (which hangs
        # without Tesseract binary installed)
        class FakeTesseractNotFoundError(OSError):
            pass

        mock_pt = MagicMock()
        mock_get_pt.return_value = mock_pt
        mock_pt.get_tesseract_version.side_effect = FakeTesseractNotFoundError()
        mock_pt.TesseractNotFoundError = FakeTesseractNotFoundError
        with pytest.raises(RuntimeError, match="Tesseract OCR engine not found"):
            ensure_tesseract()


# ---------------------------------------------------------------------------
# ocr_region / ocr_line
# ---------------------------------------------------------------------------

class TestOcrBasics:
    @patch("tools.pdf_to_sgf.ocr._get_pytesseract")
    def test_ocr_region_returns_text(self, mock_get_pt):
        mock_pt = MagicMock()
        mock_get_pt.return_value = mock_pt
        mock_pt.image_to_string.return_value = "  Hello World  \n"
        result = ocr_region(_make_image())
        assert result == "Hello World"

    @patch("tools.pdf_to_sgf.ocr._get_pytesseract")
    def test_ocr_region_returns_empty_on_error(self, mock_get_pt):
        mock_pt = MagicMock()
        mock_get_pt.return_value = mock_pt
        mock_pt.image_to_string.side_effect = Exception("OCR failed")
        assert ocr_region(_make_image()) == ""

    @patch("tools.pdf_to_sgf.ocr._get_pytesseract")
    def test_ocr_line_uses_psm7(self, mock_get_pt):
        mock_pt = MagicMock()
        mock_get_pt.return_value = mock_pt
        mock_pt.image_to_string.return_value = "test"
        ocr_line(_make_image())
        call_args = mock_pt.image_to_string.call_args
        assert "--psm 7" in call_args.kwargs.get("config", call_args[1].get("config", ""))


# ---------------------------------------------------------------------------
# Player-to-move detection
# ---------------------------------------------------------------------------

class TestPlayerToMove:
    @patch("tools.pdf_to_sgf.ocr.ocr_line")
    def test_detect_black_english(self, mock_ocr):
        from tools.pdf_to_sgf.ocr import detect_player_to_move
        mock_ocr.return_value = "Black to play"
        result = detect_player_to_move(_make_image(400, 600), (50, 50, 300, 300))
        assert result == "B"

    @patch("tools.pdf_to_sgf.ocr.ocr_line")
    def test_detect_white_english(self, mock_ocr):
        from tools.pdf_to_sgf.ocr import detect_player_to_move
        mock_ocr.return_value = "White to move"
        result = detect_player_to_move(_make_image(400, 600), (50, 50, 300, 300))
        assert result == "W"

    @patch("tools.pdf_to_sgf.ocr.ocr_line")
    def test_detect_black_japanese(self, mock_ocr):
        from tools.pdf_to_sgf.ocr import detect_player_to_move
        mock_ocr.return_value = "黒先"
        result = detect_player_to_move(_make_image(400, 600), (50, 50, 300, 300))
        assert result == "B"

    @patch("tools.pdf_to_sgf.ocr.ocr_line")
    def test_detect_white_japanese(self, mock_ocr):
        from tools.pdf_to_sgf.ocr import detect_player_to_move
        mock_ocr.return_value = "白番"
        result = detect_player_to_move(_make_image(400, 600), (50, 50, 300, 300))
        assert result == "W"

    @patch("tools.pdf_to_sgf.ocr.ocr_line")
    def test_returns_none_on_gibberish(self, mock_ocr):
        from tools.pdf_to_sgf.ocr import detect_player_to_move
        mock_ocr.return_value = "some random text"
        assert detect_player_to_move(_make_image(400, 600), (50, 50, 300, 300)) is None

    @patch("tools.pdf_to_sgf.ocr.ocr_line")
    def test_returns_none_on_empty(self, mock_ocr):
        from tools.pdf_to_sgf.ocr import detect_player_to_move
        mock_ocr.return_value = ""
        assert detect_player_to_move(_make_image(400, 600), (50, 50, 300, 300)) is None


# ---------------------------------------------------------------------------
# Problem label detection
# ---------------------------------------------------------------------------

class TestProblemLabel:
    @patch("tools.pdf_to_sgf.ocr.ocr_line")
    def test_detect_english_label(self, mock_ocr):
        from tools.pdf_to_sgf.ocr import detect_problem_label
        mock_ocr.return_value = "Problem 42"
        result = detect_problem_label(_make_image(400, 600), (50, 100, 300, 300))
        assert result is not None
        assert "42" in result

    @patch("tools.pdf_to_sgf.ocr.ocr_line")
    def test_detect_japanese_label(self, mock_ocr):
        from tools.pdf_to_sgf.ocr import detect_problem_label
        mock_ocr.return_value = "第5問"
        result = detect_problem_label(_make_image(400, 600), (50, 100, 300, 300))
        assert result is not None

    @patch("tools.pdf_to_sgf.ocr.ocr_line")
    def test_detect_hash_label(self, mock_ocr):
        from tools.pdf_to_sgf.ocr import detect_problem_label
        mock_ocr.return_value = "#17"
        result = detect_problem_label(_make_image(400, 600), (50, 100, 300, 300))
        assert result is not None
        assert "17" in result

    @patch("tools.pdf_to_sgf.ocr.ocr_line")
    def test_returns_none_on_no_match(self, mock_ocr):
        from tools.pdf_to_sgf.ocr import detect_problem_label
        mock_ocr.return_value = "some diagram title"
        assert detect_problem_label(_make_image(400, 600), (50, 100, 300, 300)) is None

    @patch("tools.pdf_to_sgf.ocr.ocr_line")
    def test_returns_none_on_empty(self, mock_ocr):
        from tools.pdf_to_sgf.ocr import detect_problem_label
        mock_ocr.return_value = ""
        assert detect_problem_label(_make_image(400, 600), (50, 100, 300, 300)) is None


# ---------------------------------------------------------------------------
# Answer section detection
# ---------------------------------------------------------------------------

class TestAnswerSection:
    @patch("tools.pdf_to_sgf.ocr.ocr_region")
    def test_detect_english_answer(self, mock_ocr):
        from tools.pdf_to_sgf.ocr import detect_answer_page
        mock_ocr.return_value = "Chapter 5: Solutions"
        is_answer, marker = detect_answer_page(_make_image())
        assert is_answer
        assert marker.lower() == "solution"

    @patch("tools.pdf_to_sgf.ocr.ocr_region")
    def test_detect_japanese_answer(self, mock_ocr):
        from tools.pdf_to_sgf.ocr import detect_answer_page
        mock_ocr.return_value = "解答"
        is_answer, marker = detect_answer_page(_make_image())
        assert is_answer
        assert marker == "解答"

    @patch("tools.pdf_to_sgf.ocr.ocr_region")
    def test_no_marker_returns_false(self, mock_ocr):
        from tools.pdf_to_sgf.ocr import detect_answer_page
        mock_ocr.return_value = "Chapter 3: Advanced Problems"
        is_answer, marker = detect_answer_page(_make_image())
        assert not is_answer
        assert marker == ""

    @patch("tools.pdf_to_sgf.ocr.detect_answer_page")
    def test_find_answer_start_from_end(self, mock_detect):
        from tools.pdf_to_sgf.ocr import find_answer_start
        pages = [_make_image() for _ in range(5)]
        # Pages 1-3 are problems, pages 4-5 are answers
        # find_answer_start scans in REVERSE: page 5, 4, 3, 2, 1
        mock_detect.side_effect = [
            (True, "Answer"), (True, "Answer"),  # pages 5, 4
            (False, ""),                          # page 3 → stop
        ]
        page_num, marker = find_answer_start(pages, [1, 2, 3, 4, 5])
        assert page_num == 4
        assert marker == "Answer"

    @patch("tools.pdf_to_sgf.ocr.detect_answer_page")
    def test_find_answer_start_none_found(self, mock_detect):
        from tools.pdf_to_sgf.ocr import find_answer_start
        pages = [_make_image() for _ in range(3)]
        mock_detect.side_effect = [(False, "")] * 3
        page_num, marker = find_answer_start(pages)
        assert page_num is None
