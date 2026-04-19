"""Tests for PDF extraction and board detection pipeline.

These tests use sample PDFs downloaded from travisgk/tsumego-pdf
(computer-generated Cho Chikun life-and-death puzzles).

Run: pytest tools/pdf_to_sgf/tests/test_pdf_pipeline.py -q --no-header --tb=short
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from PIL import Image

# Ensure tools/ is importable
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

SAMPLES_DIR = Path(__file__).resolve().parents[1] / "_test_samples"
PROBLEM_PDF = SAMPLES_DIR / "demo-a.pdf"
KEY_PDF = SAMPLES_DIR / "demo-a-key.pdf"

skip_no_samples = pytest.mark.skipif(
    not PROBLEM_PDF.exists(),
    reason="Sample PDFs not downloaded. Run the download script first.",
)


# ---------------------------------------------------------------------------
# PDF Extraction Tests
# ---------------------------------------------------------------------------


class TestPdfExtractor:
    """Test PDF page extraction."""

    @skip_no_samples
    def test_extract_all_pages(self):
        from tools.pdf_to_sgf.pdf_extractor import extract_pages

        pages = extract_pages(PROBLEM_PDF)
        assert len(pages) == 8, f"Expected 8 pages, got {len(pages)}"

    @skip_no_samples
    def test_extract_page_range(self):
        from tools.pdf_to_sgf.pdf_extractor import extract_pages

        pages = extract_pages(PROBLEM_PDF, page_range=(3, 5))
        assert len(pages) == 3
        assert pages[0].page_number == 3
        assert pages[-1].page_number == 5

    @skip_no_samples
    def test_embedded_images_are_preferred(self):
        from tools.pdf_to_sgf.pdf_extractor import extract_pages

        pages = extract_pages(PROBLEM_PDF)
        # tsumego-pdf embeds large images as PNGs; page 2 has a tiny
        # placeholder (10×10) that falls back to rendered.
        large_pages = [p for p in pages if p.width >= 3000]
        assert len(large_pages) >= 6  # pages 3-8 have large embedded images
        assert all(p.source == "embedded" for p in large_pages)

    @skip_no_samples
    def test_extracted_image_dimensions(self):
        from tools.pdf_to_sgf.pdf_extractor import extract_pages

        pages = extract_pages(PROBLEM_PDF, page_range=(3, 3))
        page = pages[0]
        assert page.width >= 1000
        assert page.height >= 1000
        assert isinstance(page.image, Image.Image)
        assert page.image.mode == "RGB"

    def test_nonexistent_pdf_raises(self):
        from tools.pdf_to_sgf.pdf_extractor import extract_pages

        with pytest.raises(FileNotFoundError):
            extract_pages("/nonexistent/path.pdf")


# ---------------------------------------------------------------------------
# Board Detection Tests
# ---------------------------------------------------------------------------


class TestBoardDetector:
    """Test board region detection on page images."""

    @skip_no_samples
    def test_detect_3_boards_on_puzzle_page(self):
        from tools.pdf_to_sgf.pdf_extractor import extract_pages
        from tools.pdf_to_sgf.board_detector import detect_boards

        pages = extract_pages(PROBLEM_PDF, page_range=(3, 3))
        assert len(pages) == 1

        boards = detect_boards(pages[0].image)
        assert len(boards) == 3, f"Expected 3 boards, got {len(boards)}"

    @skip_no_samples
    def test_boards_sorted_top_to_bottom(self):
        from tools.pdf_to_sgf.pdf_extractor import extract_pages
        from tools.pdf_to_sgf.board_detector import detect_boards

        pages = extract_pages(PROBLEM_PDF, page_range=(3, 3))
        boards = detect_boards(pages[0].image)

        for i in range(len(boards) - 1):
            assert boards[i].bbox[1] <= boards[i + 1].bbox[1]

    @skip_no_samples
    def test_board_crops_are_rgb(self):
        from tools.pdf_to_sgf.pdf_extractor import extract_pages
        from tools.pdf_to_sgf.board_detector import detect_boards

        pages = extract_pages(PROBLEM_PDF, page_range=(3, 3))
        boards = detect_boards(pages[0].image)

        for board in boards:
            assert isinstance(board.image, Image.Image)
            assert board.image.mode == "RGB"
            assert board.image.width > 100
            assert board.image.height > 100

    @skip_no_samples
    def test_board_recognition_produces_stones(self):
        """End-to-end: PDF -> page -> board crops -> stone recognition."""
        from tools.pdf_to_sgf.pdf_extractor import extract_pages
        from tools.pdf_to_sgf.board_detector import detect_boards
        from tools.core.image_to_board import recognize_position

        pages = extract_pages(PROBLEM_PDF, page_range=(3, 3))
        boards = detect_boards(pages[0].image)

        total_stones = 0
        for board in boards:
            pos = recognize_position(board.image)
            b, w = pos.stone_count()
            total_stones += b + w

        assert total_stones > 0, "No stones detected on any board"

    @skip_no_samples
    def test_answer_key_has_boards(self):
        """Verify answer key PDF also yields board regions."""
        from tools.pdf_to_sgf.pdf_extractor import extract_pages
        from tools.pdf_to_sgf.board_detector import detect_boards

        pages = extract_pages(KEY_PDF, page_range=(2, 2))
        boards = detect_boards(pages[0].image)
        assert len(boards) >= 2, f"Expected >= 2 boards in key, got {len(boards)}"
