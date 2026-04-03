"""Integration tests for POSIX paths in publish output.

Verifies that published puzzles have forward-slash paths in JSON index files,
regardless of the operating system that runs the pipeline.

Skip with: pytest -m "not posix"
"""

import json
import tempfile
from pathlib import Path

import pytest

# Mark all tests in this module as POSIX path tests
pytestmark = pytest.mark.posix

from backend.puzzle_manager.paths import to_posix_path


class TestPublishPosixPaths:
    """Integration tests for POSIX paths in publish stage output."""

    def test_path_field_uses_forward_slashes(self):
        """Published puzzle paths use forward slashes, not backslashes.

        This test validates the requirement that all 'path' values in
        JSON index files must use POSIX-style forward slashes.
        """
        # Simulate what publish stage creates
        puzzle_info = {
            "id": "abc123def456",
            "level": "beginner",
            "path": to_posix_path(
                Path("yengo-puzzle-collections/sgf/beginner/batch-0001/abc123def456.sgf"),
                relative_to=Path("yengo-puzzle-collections")
            ),
            "board_size": 19,
            "tags": ["life-and-death"],
        }

        # Verify path uses forward slashes
        assert puzzle_info["path"] == "sgf/beginner/batch-0001/abc123def456.sgf"
        assert "\\" not in puzzle_info["path"]

        # Verify JSON serialization doesn't reintroduce backslashes
        json_str = json.dumps(puzzle_info)
        assert "\\\\" not in json_str  # No escaped backslashes

    def test_view_index_json_has_posix_paths(self):
        """Simulated view index JSON file contains only forward-slash paths."""
        puzzles = [
            {
                "id": f"puzzle{i:03d}",
                "level": "beginner",
                "path": to_posix_path(f"sgf\\beginner\\batch-0001\\puzzle{i:03d}.sgf"),
            }
            for i in range(5)
        ]

        index_data = {"entries": puzzles, "count": len(puzzles)}

        # Write and read back from temp file (simulates actual publish)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(index_data, f)
            temp_path = f.name

        try:
            with open(temp_path) as f:
                loaded = json.load(f)

            for puzzle in loaded["entries"]:
                assert "\\" not in puzzle["path"], f"Backslash found in path: {puzzle['path']}"
                assert puzzle["path"].startswith("sgf/beginner/"), f"Path format incorrect: {puzzle['path']}"
        finally:
            Path(temp_path).unlink()

    def test_multiple_levels_have_posix_paths(self):
        """Puzzles from different levels all use forward-slash paths."""
        levels = ["beginner", "intermediate", "advanced"]

        for _level in levels:
            # Simulate flat path format (new: sgf/{NNNN}/test.sgf)
            flat_path = "sgf\\0001\\test.sgf"
            posix_path = to_posix_path(flat_path)

            assert posix_path == "sgf/0001/test.sgf"
            assert "\\" not in posix_path

    def test_publish_log_entry_path_posix(self):
        """PublishLogEntry path field uses POSIX format."""
        # Simulate PublishLogEntry creation with to_posix_path
        log_entry = {
            "run_id": "run-2026-01-29-001",
            "id": "abc123",
            "source": "test",
            "path": to_posix_path(
                Path("C:/project/output/sgf/beginner/file.sgf"),
                relative_to=Path("C:/project/output")
            ),
        }

        assert log_entry["path"] == "sgf/beginner/file.sgf"
        assert "\\" not in log_entry["path"]

    def test_batch_directory_paths_posix(self):
        """Batch directory paths in index files use forward slashes."""
        batch_paths = [
            "sgf\\beginner\\batch-0001",
            "sgf\\beginner\\batch-0002",
            "sgf\\intermediate\\batch-0001",
        ]

        for batch_path in batch_paths:
            posix = to_posix_path(batch_path)
            assert "\\" not in posix
            assert "/" in posix

    def test_compact_entry_path_is_posix(self):
        """Compact entry 'p' value never contains backslashes.

        In v4.0 compact format, the 'p' key stores 'batch/hash' (e.g.
        '0001/fc38f029205dde14').  Reconstructing the full path as
        ``sgf/{p}.sgf`` must yield a POSIX path.
        """
        compact_p = "0001/fc38f029205dde14"
        full_path = f"sgf/{compact_p}.sgf"
        assert "\\" not in full_path
        assert full_path == "sgf/0001/fc38f029205dde14.sgf"

        # Even if batch contains a backslash (defensive), to_posix_path fixes it
        bad_p = "0001\\fc38f029205dde14"
        assert "\\" not in to_posix_path(f"sgf/{bad_p}.sgf")
