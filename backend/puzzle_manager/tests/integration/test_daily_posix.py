"""Integration tests for POSIX paths in daily challenge output.

Verifies that daily challenge JSON files use forward-slash paths,
regardless of the operating system that runs the generation.

Skip with: pytest -m "not posix"
"""

from datetime import datetime

import pytest

# Mark all tests in this module as POSIX path tests
pytestmark = pytest.mark.posix

from backend.puzzle_manager.daily._helpers import to_puzzle_ref as _to_puzzle_ref
from backend.puzzle_manager.daily.standard import generate_standard_daily
from backend.puzzle_manager.models.config import DailyConfig
from backend.puzzle_manager.tests.conftest import make_compact_entry


class TestDailyPosixPaths:
    """Integration tests for POSIX paths in daily challenge generation."""

    def test_puzzle_ref_path_uses_forward_slashes(self):
        """PuzzleRef path field uses forward slashes, not backslashes.

        Tests defensive normalization in _to_puzzle_ref() with compact format.
        """
        # Compact entry — path is always POSIX in compact format
        puzzle_dict = make_compact_entry(
            batch="0001",
            hash_id="abc123def456",
            level_id=140,
        )

        ref = _to_puzzle_ref(puzzle_dict)

        # Path should be reconstructed with forward slashes
        assert ref.path == "sgf/0001/abc123def456.sgf"
        assert "\\" not in ref.path

    def test_puzzle_ref_preserves_posix_paths(self):
        """PuzzleRef correctly handles compact format paths (always POSIX)."""
        puzzle_dict = make_compact_entry(
            batch="0002",
            hash_id="xyz789",
            level_id=120,
        )

        ref = _to_puzzle_ref(puzzle_dict)

        # Compact path should expand correctly
        assert ref.path == "sgf/0002/xyz789.sgf"
        assert ref.id == "xyz789"

    def test_standard_daily_puzzles_have_posix_paths(self):
        """Generated daily challenge has POSIX paths for all puzzles."""
        # Create pool with compact entries
        pool = [
            make_compact_entry(batch="0001", hash_id=f"puz{i:03d}", level_id=120)
            for i in range(5)
        ] + [
            make_compact_entry(batch="0001", hash_id=f"int{i:03d}", level_id=140)
            for i in range(10)
        ] + [
            make_compact_entry(batch="0001", hash_id=f"adv{i:03d}", level_id=160)
            for i in range(10)
        ]

        config = DailyConfig(puzzles_per_day=5)
        daily = generate_standard_daily(datetime(2026, 1, 29), pool, config)

        # All puzzle paths should use forward slashes
        for puzzle in daily.puzzles:
            assert "\\" not in puzzle.path, f"Backslash in path: {puzzle.path}"
            assert "/" in puzzle.path, f"No forward slash in path: {puzzle.path}"

    def test_mixed_path_pool_normalizes_consistently(self):
        """Pool with compact entries always produces POSIX paths."""
        pool = [
            make_compact_entry(batch="0001", hash_id="file1", level_id=120),
            make_compact_entry(batch="0001", hash_id="file2", level_id=120),
            make_compact_entry(batch="0001", hash_id="file3", level_id=140),
            make_compact_entry(batch="0001", hash_id="file4", level_id=160),
        ]

        config = DailyConfig(puzzles_per_day=4)
        daily = generate_standard_daily(datetime(2026, 1, 30), pool, config)

        for puzzle in daily.puzzles:
            assert "\\" not in puzzle.path, f"Backslash in path: {puzzle.path}"
