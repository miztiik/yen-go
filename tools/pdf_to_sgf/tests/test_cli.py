"""Tests for the pdf_to_sgf CLI tool.

Tests CLI argument parsing and basic subcommand execution.

Run: pytest tools/pdf_to_sgf/tests/test_cli.py -q --no-header --tb=short
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

SAMPLES_DIR = Path(__file__).resolve().parents[1] / "_test_samples"
PROBLEM_PDF = SAMPLES_DIR / "demo-a.pdf"
KEY_PDF = SAMPLES_DIR / "demo-a-key.pdf"

skip_no_samples = pytest.mark.skipif(
    not PROBLEM_PDF.exists(),
    reason="Sample PDFs not downloaded.",
)


# ---------------------------------------------------------------------------
# Helper function tests (pure logic, no sample PDFs needed)
# ---------------------------------------------------------------------------


class TestHelpers:
    def test_sanitize_label_spaces(self):
        from tools.pdf_to_sgf.__main__ import _sanitize_label
        assert _sanitize_label("Problem 5") == "Problem_5"

    def test_sanitize_label_special_chars(self):
        from tools.pdf_to_sgf.__main__ import _sanitize_label
        assert _sanitize_label("A:3/test") == "A_3_test"

    def test_sanitize_label_empty(self):
        from tools.pdf_to_sgf.__main__ import _sanitize_label
        assert _sanitize_label("") == "unknown"

    def test_sanitize_label_only_unsafe(self):
        from tools.pdf_to_sgf.__main__ import _sanitize_label
        assert _sanitize_label(":::") == "unknown"

    def test_sanitize_label_unicode(self):
        from tools.pdf_to_sgf.__main__ import _sanitize_label
        assert _sanitize_label("第5問") == "第5問"

    def test_sanitize_label_consecutive_underscores(self):
        from tools.pdf_to_sgf.__main__ import _sanitize_label
        assert _sanitize_label("A  B  C") == "A_B_C"

    def test_make_output_stem(self):
        from tools.pdf_to_sgf.__main__ import _make_output_stem
        assert _make_output_stem(1, "Problem 5") == "001_Problem_5"

    def test_make_output_stem_numeric_label(self):
        from tools.pdf_to_sgf.__main__ import _make_output_stem
        assert _make_output_stem(12, "42") == "012_42"

    def test_player_comment_black(self):
        from tools.pdf_to_sgf.__main__ import _player_comment
        assert _player_comment("B") == "Black to play"

    def test_player_comment_white(self):
        from tools.pdf_to_sgf.__main__ import _player_comment
        assert _player_comment("W") == "White to play"

    def test_page_as_single_board(self):
        from PIL import Image
        from tools.pdf_to_sgf.__main__ import _page_as_single_board
        img = Image.new("RGB", (800, 600))
        boards = _page_as_single_board(img)
        assert len(boards) == 1
        assert boards[0].bbox == (0, 0, 800, 600)
        assert boards[0].detection_confidence == 1.0
        assert boards[0].index == 0


class TestPageRangeParsing:
    def test_single_page(self):
        from tools.pdf_to_sgf.__main__ import _parse_page_range
        assert _parse_page_range("3") == (3, 3)

    def test_range(self):
        from tools.pdf_to_sgf.__main__ import _parse_page_range
        assert _parse_page_range("3-5") == (3, 5)

    def test_none(self):
        from tools.pdf_to_sgf.__main__ import _parse_page_range
        assert _parse_page_range(None) is None


class TestCliPreview:
    @skip_no_samples
    def test_preview_returns_zero(self):
        """Preview command should return 0 on valid PDF."""
        import argparse
        from tools.pdf_to_sgf.__main__ import cmd_preview

        args = argparse.Namespace(pdf=str(PROBLEM_PDF), pages="3-3")
        result = cmd_preview(args)
        assert result == 0


class TestCliExtract:
    @skip_no_samples
    def test_extract_returns_zero(self, tmp_path):
        """Extract command should return 0 and detect boards."""
        import argparse
        from tools.pdf_to_sgf.__main__ import cmd_extract

        args = argparse.Namespace(
            pdf=str(PROBLEM_PDF),
            pages="3-3",
            output_dir=str(tmp_path),
            preset="default",
            verbose=False,
        )
        result = cmd_extract(args)
        assert result == 0

    @skip_no_samples
    def test_extract_saves_crops(self, tmp_path):
        """Extract with output_dir should save board crop images."""
        import argparse
        from tools.pdf_to_sgf.__main__ import cmd_extract

        args = argparse.Namespace(
            pdf=str(PROBLEM_PDF),
            pages="3-3",
            output_dir=str(tmp_path),
            preset="default",
            verbose=False,
        )
        cmd_extract(args)
        pngs = list(tmp_path.glob("*.png"))
        assert len(pngs) >= 1, "Expected at least 1 board crop saved"


class TestCliConvert:
    @skip_no_samples
    def test_convert_with_key_produces_sgf(self, tmp_path):
        """Convert with problem+key PDFs should produce SGF files."""
        import argparse
        from tools.pdf_to_sgf.__main__ import cmd_convert

        args = argparse.Namespace(
            pdf=str(PROBLEM_PDF),
            key=str(KEY_PDF),
            output_dir=str(tmp_path),
            pages="3-3",
            preset="default",
            player="B",
            collection=None,
            single_board_per_page=False,
            save_crops=False,
            key_pages=None,
            auto_detect_solution=False,
        )
        result = cmd_convert(args)
        assert result == 0
        sgf_files = list(tmp_path.glob("sgf/*.sgf"))
        assert len(sgf_files) >= 1, "Expected at least 1 SGF file"

    @skip_no_samples
    def test_convert_without_key_produces_sgf(self, tmp_path):
        """Convert without key should produce position-only SGF files."""
        import argparse
        from tools.pdf_to_sgf.__main__ import cmd_convert

        args = argparse.Namespace(
            pdf=str(PROBLEM_PDF),
            key=None,
            output_dir=str(tmp_path),
            pages="3-3",
            preset="default",
            player="B",
            collection=None,
            single_board_per_page=False,
            save_crops=False,
            key_pages=None,
            auto_detect_solution=False,
        )
        result = cmd_convert(args)
        assert result == 0
        sgf_files = list(tmp_path.glob("sgf/*.sgf"))
        assert len(sgf_files) >= 1

    @skip_no_samples
    def test_generated_sgf_starts_with_paren(self, tmp_path):
        """All generated SGF files should start with '(;'."""
        import argparse
        from tools.pdf_to_sgf.__main__ import cmd_convert

        args = argparse.Namespace(
            pdf=str(PROBLEM_PDF),
            key=str(KEY_PDF),
            output_dir=str(tmp_path),
            pages="3-3",
            preset="default",
            player="B",
            collection=None,
            single_board_per_page=False,
            save_crops=False,
            key_pages=None,
            auto_detect_solution=False,
        )
        cmd_convert(args)
        for sgf_file in tmp_path.glob("sgf/*.sgf"):
            content = sgf_file.read_text(encoding="utf-8")
            assert content.startswith("(;"), f"{sgf_file.name} doesn't start with '(;'"
