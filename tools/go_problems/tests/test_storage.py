"""Tests for GoProblems storage module."""

import tempfile
from pathlib import Path

from tools.go_problems.checkpoint import GoProblemsCheckpoint
from tools.go_problems.models import GoProblemsDetail, GoProblemsRating
from tools.go_problems.storage import generate_puzzle_filename, save_puzzle


class TestGeneratePuzzleFilename:
    """Tests for filename generation."""

    def test_integer_id(self):
        assert generate_puzzle_filename(42) == "42.sgf"

    def test_large_id(self):
        assert generate_puzzle_filename(99999) == "99999.sgf"

    def test_string_id(self):
        assert generate_puzzle_filename("123") == "123.sgf"


class TestSavePuzzle:
    """Tests for saving puzzles to disk."""

    def _make_puzzle(self, puzzle_id: int = 42) -> GoProblemsDetail:
        """Create a test puzzle."""
        return GoProblemsDetail(
            id=puzzle_id,
            sgf="(;FF[4]GM[1]SZ[9]AB[cc][cd]AW[dc][dd];B[bc])",
            genre="life and death",
            rank=None,
            problemLevel=10,
            rating=GoProblemsRating(stars=3.5, votes=10),
            isCanon=True,
            playerColor="black",
            collections=None,
        )

    def test_save_creates_file(self):
        """Saving a puzzle should create an SGF file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            checkpoint = GoProblemsCheckpoint()
            puzzle = self._make_puzzle()

            file_path, batch_num = save_puzzle(
                puzzle,
                output_dir,
                batch_size=1000,
                checkpoint=checkpoint,
            )

            assert file_path.exists()
            assert file_path.name == "42.sgf"
            assert batch_num == 1

    def test_saved_sgf_contains_yengo_properties(self):
        """Saved SGF should contain YenGo custom properties."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            checkpoint = GoProblemsCheckpoint()
            puzzle = self._make_puzzle()

            file_path, _ = save_puzzle(
                puzzle,
                output_dir,
                batch_size=1000,
                checkpoint=checkpoint,
            )

            content = file_path.read_text(encoding="utf-8")
            assert "YG[" in content  # Level
            assert "YT[" in content  # Tags
            assert "YQ[" in content  # Quality
            assert "YV[" in content  # Version
            assert "GM[1]" in content
            assert "FF[4]" in content

    def test_index_updated(self):
        """Saving should update sgf-index.txt."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            checkpoint = GoProblemsCheckpoint()
            puzzle = self._make_puzzle()

            save_puzzle(
                puzzle,
                output_dir,
                batch_size=1000,
                checkpoint=checkpoint,
            )

            index_path = output_dir / "sgf-index.txt"
            assert index_path.exists()
            content = index_path.read_text()
            assert "42.sgf" in content
