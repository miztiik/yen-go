"""Tests for GoProblems checkpoint management."""

import tempfile
from pathlib import Path

from tools.go_problems.checkpoint import (
    GoProblemsCheckpoint,
    clear_checkpoint,
    load_checkpoint,
    save_checkpoint,
)


class TestGoProblemsCheckpoint:
    """Tests for GoProblemsCheckpoint dataclass."""

    def test_default_values(self):
        cp = GoProblemsCheckpoint()
        assert cp.last_processed_id == 0
        assert cp.last_successful_id == 0
        assert cp.puzzles_downloaded == 0
        assert cp.puzzles_skipped == 0
        assert cp.puzzles_errors == 0
        assert cp.puzzles_not_found == 0
        assert cp.current_batch == 1
        assert cp.files_in_current_batch == 0

    def test_record_success(self):
        cp = GoProblemsCheckpoint()
        cp.record_success(puzzle_id=42, batch_size=1000)
        assert cp.last_processed_id == 42
        assert cp.last_successful_id == 42
        assert cp.puzzles_downloaded == 1
        assert cp.files_in_current_batch == 1

    def test_record_not_found(self):
        cp = GoProblemsCheckpoint()
        cp.record_not_found(puzzle_id=99)
        assert cp.last_processed_id == 99
        assert cp.puzzles_not_found == 1
        assert cp.puzzles_downloaded == 0

    def test_record_skip(self):
        cp = GoProblemsCheckpoint()
        cp.record_skip(puzzle_id=50, reason="not canon")
        assert cp.last_processed_id == 50
        assert cp.puzzles_skipped == 1

    def test_record_error(self):
        cp = GoProblemsCheckpoint()
        cp.record_error(puzzle_id=77, error="HTTP timeout")
        assert cp.last_processed_id == 77
        assert cp.puzzles_errors == 1
        assert len(cp.recent_errors) == 1
        assert "puzzle 77" in cp.recent_errors[0]

    def test_error_list_capped_at_100(self):
        cp = GoProblemsCheckpoint()
        for i in range(150):
            cp.record_error(puzzle_id=i, error=f"error {i}")
        assert len(cp.recent_errors) == 100

    def test_batch_advancement(self):
        cp = GoProblemsCheckpoint()
        for i in range(1001):
            cp.record_success(puzzle_id=i, batch_size=1000)
        assert cp.current_batch == 2


class TestCheckpointPersistence:
    """Tests for checkpoint save/load/clear cycle."""

    def test_save_and_load(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)

            # Save
            cp = GoProblemsCheckpoint()
            cp.record_success(puzzle_id=42, batch_size=1000)
            cp.record_success(puzzle_id=43, batch_size=1000)
            cp.record_not_found(puzzle_id=44)
            save_checkpoint(cp, output_dir)

            # Load
            loaded = load_checkpoint(output_dir)
            assert loaded is not None
            assert loaded.last_processed_id == 44
            assert loaded.puzzles_downloaded == 2
            assert loaded.puzzles_not_found == 1

    def test_load_nonexistent_returns_none(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            loaded = load_checkpoint(Path(tmpdir))
            assert loaded is None

    def test_clear(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            cp = GoProblemsCheckpoint()
            save_checkpoint(cp, output_dir)

            checkpoint_file = output_dir / ".checkpoint.json"
            assert checkpoint_file.exists()

            clear_checkpoint(output_dir)
            assert not checkpoint_file.exists()
