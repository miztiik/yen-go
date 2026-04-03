"""Integration tests for batch transitions during publish.

Tests the O(1) fast path with BatchState across batch boundaries,
verifying correct file distribution when batches fill up.

Updated for flat sharding: sgf/{NNNN}/{hash}.sgf (global batch counter).
"""

from pathlib import Path

import pytest

from backend.puzzle_manager.core.batch_writer import BatchState, BatchWriter


class TestBatchTransitionIntegration:
    """Test batch transitions during simulated publish runs."""

    @pytest.fixture
    def sgf_root(self, tmp_path: Path) -> Path:
        """Create a temporary SGF root directory."""
        return tmp_path / "sgf"

    @pytest.fixture
    def batch_writer(self, sgf_root: Path) -> BatchWriter:
        """Create BatchWriter with small batch size for testing."""
        return BatchWriter(sgf_root, max_files_per_dir=10)

    def _create_mock_sgf(self, puzzle_id: str) -> str:
        """Create a minimal valid SGF for testing."""
        return f"(;GM[1]FF[4]SZ[19]GN[{puzzle_id}];B[pd];W[dd];B[pp])"

    def test_batch_transitions_across_boundary(
        self, sgf_root: Path, batch_writer: BatchWriter
    ) -> None:
        """Test files are distributed correctly across batch boundaries."""
        max_files = 10
        num_files = 25  # Should create 3 batches: 10, 10, 5

        state = BatchState.load_or_recover(sgf_root, max_files)

        files_per_batch: dict[int, int] = {}

        for i in range(num_files):
            batch_dir, batch_num = batch_writer.get_batch_dir_fast(
                state.current_batch, state.files_in_current_batch
            )

            files_per_batch[batch_num] = files_per_batch.get(batch_num, 0) + 1

            output_path = batch_dir / f"puzzle_{i:04d}.sgf"
            output_path.write_text(self._create_mock_sgf(f"puzzle_{i:04d}"))
            state.record_file_saved(max_files)

        state.save(sgf_root)

        assert files_per_batch[1] == 10
        assert files_per_batch[2] == 10
        assert files_per_batch[3] == 5

        # Verify actual files on disk (flat dirs)
        assert len(list((sgf_root / "0001").glob("*.sgf"))) == 10
        assert len(list((sgf_root / "0002").glob("*.sgf"))) == 10
        assert len(list((sgf_root / "0003").glob("*.sgf"))) == 5

    def test_state_persists_across_runs(
        self, sgf_root: Path, batch_writer: BatchWriter
    ) -> None:
        """Test that state persists correctly between publish runs."""
        max_files = 10

        # Run 1: Write 8 files
        state = BatchState.load_or_recover(sgf_root, max_files)
        for i in range(8):
            batch_dir, _ = batch_writer.get_batch_dir_fast(
                state.current_batch, state.files_in_current_batch
            )
            (batch_dir / f"run1_{i}.sgf").write_text(self._create_mock_sgf(f"run1_{i}"))
            state.record_file_saved(max_files)
        state.save(sgf_root)

        loaded_state = BatchState.load(sgf_root)
        assert loaded_state is not None
        assert loaded_state.current_batch == 1
        assert loaded_state.files_in_current_batch == 8

        # Run 2: Write 5 more files (should cross into batch 2)
        state2 = BatchState.load_or_recover(sgf_root, max_files)
        for i in range(5):
            batch_dir, batch_num = batch_writer.get_batch_dir_fast(
                state2.current_batch, state2.files_in_current_batch
            )
            (batch_dir / f"run2_{i}.sgf").write_text(self._create_mock_sgf(f"run2_{i}"))
            state2.record_file_saved(max_files)
        state2.save(sgf_root)

        loaded_state2 = BatchState.load(sgf_root)
        assert loaded_state2 is not None
        assert loaded_state2.current_batch == 2
        assert loaded_state2.files_in_current_batch == 3

        assert len(list((sgf_root / "0001").glob("*.sgf"))) == 10
        assert len(list((sgf_root / "0002").glob("*.sgf"))) == 3

    def test_recovery_after_interrupted_run(
        self, sgf_root: Path, batch_writer: BatchWriter
    ) -> None:
        """Test recovery works when state file is missing (crash scenario)."""
        max_files = 10

        # Simulate a previous run that crashed without saving state
        batch_1_dir = sgf_root / "0001"
        batch_1_dir.mkdir(parents=True)
        for i in range(10):
            (batch_1_dir / f"crash_{i}.sgf").write_text(self._create_mock_sgf(f"crash_{i}"))

        batch_2_dir = sgf_root / "0002"
        batch_2_dir.mkdir(parents=True)
        for i in range(7):
            (batch_2_dir / f"crash_1{i}.sgf").write_text(self._create_mock_sgf(f"crash_1{i}"))

        # No state file exists - simulate recovery
        recovered_state = BatchState.load_or_recover(sgf_root, max_files)

        assert recovered_state.current_batch == 2
        assert recovered_state.files_in_current_batch == 7
        assert recovered_state.recovery_timestamp is not None

        # Continue writing 5 more files
        for i in range(5):
            batch_dir, batch_num = batch_writer.get_batch_dir_fast(
                recovered_state.current_batch, recovered_state.files_in_current_batch
            )
            (batch_dir / f"resume_{i}.sgf").write_text(self._create_mock_sgf(f"resume_{i}"))
            recovered_state.record_file_saved(max_files)

        # 7 + 3 = 10 in batch 2, then 2 in batch 3
        assert recovered_state.current_batch == 3
        assert recovered_state.files_in_current_batch == 2

    def test_global_batch_counter_shared_across_levels(
        self, sgf_root: Path, batch_writer: BatchWriter
    ) -> None:
        """All levels share a single global batch counter."""
        max_files = 10

        state = BatchState.load_or_recover(sgf_root, max_files)

        # Write 5 "beginner" puzzles
        for i in range(5):
            batch_dir, _ = batch_writer.get_batch_dir_fast(
                state.current_batch, state.files_in_current_batch
            )
            (batch_dir / f"beginner_{i}.sgf").write_text("(;YG[beginner])")
            state.record_file_saved(max_files)

        # Write 5 "advanced" puzzles — same batch counter
        for i in range(5):
            batch_dir, _ = batch_writer.get_batch_dir_fast(
                state.current_batch, state.files_in_current_batch
            )
            (batch_dir / f"advanced_{i}.sgf").write_text("(;YG[advanced])")
            state.record_file_saved(max_files)

        state.save(sgf_root)

        # All 10 files should be in 0001 (batch full), next goes to 0002
        assert state.current_batch == 2
        assert state.files_in_current_batch == 0
        assert len(list((sgf_root / "0001").glob("*.sgf"))) == 10

    def test_exact_batch_boundary(
        self, sgf_root: Path, batch_writer: BatchWriter
    ) -> None:
        """Test behavior when exactly filling a batch."""
        max_files = 10

        state = BatchState.load_or_recover(sgf_root, max_files)

        for i in range(10):
            batch_dir, batch_num = batch_writer.get_batch_dir_fast(
                state.current_batch, state.files_in_current_batch
            )
            assert batch_num == 1
            (batch_dir / f"exact_{i}.sgf").write_text(self._create_mock_sgf(f"exact_{i}"))
            state.record_file_saved(max_files)

        assert state.current_batch == 2
        assert state.files_in_current_batch == 0

        # Next file should go to batch 2
        batch_dir, batch_num = batch_writer.get_batch_dir_fast(
            state.current_batch, state.files_in_current_batch
        )
        assert batch_num == 2
        assert batch_dir.name == "0002"
