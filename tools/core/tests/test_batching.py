"""
Tests for tools.core.batching module.

Comprehensive test coverage for:
- BatchInfo dataclass
- BatchState with schema evolution
- O(1) fast path (get_batch_for_file_fast)
- O(N) fallback (get_batch_for_file)
- Crash recovery (recover_from_filesystem)
- Edge cases and error handling
"""

import json
from datetime import datetime
from pathlib import Path

import pytest

from tools.core.batching import (
    BATCH_STATE_FILENAME,
    BATCH_STATE_SCHEMA_VERSION,
    BatchInfo,
    BatchState,
    count_total_files,
    find_existing_batches,
    get_batch_dir_number,
    get_batch_for_file,
    get_batch_for_file_fast,
    get_batch_summary,
)

# ==============================
# Fixtures
# ==============================

@pytest.fixture
def empty_dir(tmp_path: Path) -> Path:
    """Empty directory for batch operations."""
    sgf_dir = tmp_path / "sgf"
    sgf_dir.mkdir()
    return sgf_dir


@pytest.fixture
def dir_with_batches(tmp_path: Path) -> Path:
    """Directory with pre-populated batch directories."""
    sgf_dir = tmp_path / "sgf"

    # Create batch-001 with 500 files
    batch1 = sgf_dir / "batch-001"
    batch1.mkdir(parents=True)
    for i in range(500):
        (batch1 / f"puzzle-{i:04d}.sgf").write_text("(;GM[1]SZ[19])")

    # Create batch-002 with 250 files
    batch2 = sgf_dir / "batch-002"
    batch2.mkdir()
    for i in range(250):
        (batch2 / f"puzzle-{i:04d}.sgf").write_text("(;GM[1]SZ[19])")

    return sgf_dir


# ==============================
# BatchInfo Tests
# ==============================

class TestBatchInfo:
    """Tests for BatchInfo dataclass."""

    def test_name_property(self, tmp_path: Path):
        """T001a: name property returns zero-padded batch name."""
        info = BatchInfo(path=tmp_path / "batch-001", batch_number=1, file_count=0)
        assert info.name == "batch-001"

        info = BatchInfo(path=tmp_path / "batch-010", batch_number=10, file_count=0)
        assert info.name == "batch-010"

        info = BatchInfo(path=tmp_path / "batch-100", batch_number=100, file_count=0)
        assert info.name == "batch-100"

    def test_is_full_default_size(self, tmp_path: Path):
        """T001b: is_full checks against default batch size (1000)."""
        info = BatchInfo(path=tmp_path, batch_number=1, file_count=999)
        assert not info.is_full()

        info = BatchInfo(path=tmp_path, batch_number=1, file_count=1000)
        assert info.is_full()

    def test_is_full_custom_size(self, tmp_path: Path):
        """T001c: is_full checks against custom batch size."""
        info = BatchInfo(path=tmp_path, batch_number=1, file_count=499)
        assert not info.is_full(max_size=500)

        info = BatchInfo(path=tmp_path, batch_number=1, file_count=500)
        assert info.is_full(max_size=500)


# ==============================
# BatchState Tests
# ==============================

class TestBatchStateSave:
    """Tests for BatchState.save() method."""

    def test_save_creates_state_file(self, empty_dir: Path):
        """T002a: save() creates state file."""
        state = BatchState(current_batch=1, files_in_current_batch=0)
        state.save(empty_dir)

        state_path = empty_dir / BATCH_STATE_FILENAME
        assert state_path.exists()

    def test_save_includes_schema_version(self, empty_dir: Path):
        """T002b: save() includes schema version."""
        state = BatchState()
        state.save(empty_dir)

        data = json.loads((empty_dir / BATCH_STATE_FILENAME).read_text())
        assert data["schema_version"] == BATCH_STATE_SCHEMA_VERSION

    def test_save_updates_timestamp(self, empty_dir: Path):
        """T002c: save() updates last_updated timestamp."""
        state = BatchState()
        assert state.last_updated == ""

        state.save(empty_dir)

        data = json.loads((empty_dir / BATCH_STATE_FILENAME).read_text())
        assert data["last_updated"] != ""
        # Verify it's valid ISO format
        datetime.fromisoformat(data["last_updated"].replace("Z", "+00:00"))


class TestBatchStateLoad:
    """Tests for BatchState.load() method."""

    def test_load_returns_saved_state(self, empty_dir: Path):
        """T002d: load() returns previously saved state."""
        state = BatchState(current_batch=5, files_in_current_batch=123)
        state.save(empty_dir)

        loaded = BatchState.load(empty_dir)

        assert loaded is not None
        assert loaded.current_batch == 5
        assert loaded.files_in_current_batch == 123

    def test_load_returns_none_when_not_found(self, empty_dir: Path):
        """T002e: load() returns None if file doesn't exist."""
        result = BatchState.load(empty_dir)
        assert result is None

    def test_load_handles_corrupted_json(self, empty_dir: Path):
        """T002f: load() handles corrupted JSON gracefully."""
        state_path = empty_dir / BATCH_STATE_FILENAME
        state_path.write_text("{ not valid json }")

        result = BatchState.load(empty_dir)

        assert result is None
        assert not state_path.exists()  # Should delete corrupted file

    def test_load_handles_empty_file(self, empty_dir: Path):
        """T002g: load() handles empty file."""
        state_path = empty_dir / BATCH_STATE_FILENAME
        state_path.write_text("")

        result = BatchState.load(empty_dir)

        assert result is None
        assert not state_path.exists()


class TestBatchStateSchemaMigration:
    """Tests for schema migration."""

    def test_migrate_v1_to_v2(self, empty_dir: Path):
        """T003a: v1 schema migrates to v2 automatically."""
        # Write v1 checkpoint (without new v2 fields)
        v1_data = {
            "schema_version": 1,
            "current_batch": 3,
            "files_in_current_batch": 100,
            "last_updated": "2025-01-01T00:00:00Z",
        }
        state_path = empty_dir / BATCH_STATE_FILENAME
        state_path.write_text(json.dumps(v1_data))

        loaded = BatchState.load(empty_dir)

        assert loaded is not None
        assert loaded.current_batch == 3
        assert loaded.files_in_current_batch == 100
        # v2 fields should have defaults
        assert loaded.last_error is None
        assert loaded.retry_count == 0
        assert loaded.recovery_timestamp is None

    def test_migration_preserves_data(self, empty_dir: Path):
        """T003b: Migration preserves existing data."""
        v1_data = {
            "current_batch": 10,
            "files_in_current_batch": 499,
            "last_updated": "2025-06-15T12:00:00Z",
        }
        state_path = empty_dir / BATCH_STATE_FILENAME
        state_path.write_text(json.dumps(v1_data))

        loaded = BatchState.load(empty_dir)

        assert loaded.current_batch == 10
        assert loaded.files_in_current_batch == 499


class TestBatchStateRecordFileSaved:
    """Tests for record_file_saved() method."""

    def test_increments_file_count(self, empty_dir: Path):
        """T004a: record_file_saved() increments file count."""
        state = BatchState(current_batch=1, files_in_current_batch=0)

        state.record_file_saved(batch_size=500)

        assert state.files_in_current_batch == 1

    def test_advances_batch_when_full(self, empty_dir: Path):
        """T004b: Advances to next batch when current is full."""
        state = BatchState(current_batch=1, files_in_current_batch=499)

        state.record_file_saved(batch_size=500)  # 499 -> 500 -> advance

        assert state.current_batch == 2
        assert state.files_in_current_batch == 0

    def test_clears_error_on_success(self, empty_dir: Path):
        """T004c: Clears last_error on successful save."""
        state = BatchState(current_batch=1, files_in_current_batch=0)
        state.last_error = "Previous error"
        state.retry_count = 3

        state.record_file_saved(batch_size=500)

        assert state.last_error is None
        assert state.retry_count == 0


class TestBatchStateRecovery:
    """Tests for crash recovery functionality."""

    def test_recover_from_empty_directory(self, empty_dir: Path):
        """T005a: Recovery from empty directory starts at batch 1."""
        state = BatchState.recover_from_filesystem(empty_dir)

        assert state.current_batch == 1
        assert state.files_in_current_batch == 0
        assert state.recovery_timestamp is not None

    def test_recover_from_populated_directory(self, dir_with_batches: Path):
        """T005b: Recovery correctly identifies current batch."""
        state = BatchState.recover_from_filesystem(
            dir_with_batches, batch_size=500
        )

        # batch-001 has 500 (full), batch-002 has 250
        assert state.current_batch == 2
        assert state.files_in_current_batch == 250

    def test_recover_when_last_batch_full(self, tmp_path: Path):
        """T005c: Recovery creates new batch when last is full."""
        sgf_dir = tmp_path / "sgf"
        batch1 = sgf_dir / "batch-001"
        batch1.mkdir(parents=True)

        # Fill batch-001 exactly to batch_size
        for i in range(500):
            (batch1 / f"puzzle-{i:04d}.sgf").write_text("(;GM[1])")

        state = BatchState.recover_from_filesystem(sgf_dir, batch_size=500)

        assert state.current_batch == 2
        assert state.files_in_current_batch == 0

    def test_load_or_recover_prefers_file(self, dir_with_batches: Path):
        """T005d: load_or_recover uses file when available."""
        # Save a state that differs from filesystem
        state = BatchState(current_batch=99, files_in_current_batch=42)
        state.save(dir_with_batches)

        loaded = BatchState.load_or_recover(dir_with_batches)

        # Should use saved state, not recovered
        assert loaded.current_batch == 99
        assert loaded.files_in_current_batch == 42

    def test_load_or_recover_falls_back_to_recovery(self, dir_with_batches: Path):
        """T005e: load_or_recover recovers when no file exists."""
        # No state file saved
        loaded = BatchState.load_or_recover(dir_with_batches, batch_size=500)

        # Should recover from filesystem
        assert loaded.current_batch == 2
        assert loaded.files_in_current_batch == 250


class TestBatchStateValidation:
    """Tests for state validation."""

    def test_validate_consistent_state(self, dir_with_batches: Path):
        """T006a: Validation passes for consistent state."""
        state = BatchState(current_batch=2, files_in_current_batch=250)

        assert state.validate_against_filesystem(dir_with_batches) is True

    def test_validate_detects_file_count_mismatch(self, dir_with_batches: Path):
        """T006b: Validation detects file count mismatch."""
        state = BatchState(current_batch=2, files_in_current_batch=999)

        assert state.validate_against_filesystem(dir_with_batches) is False

    def test_validate_detects_missing_directory(self, empty_dir: Path):
        """T006c: Validation detects when directory doesn't exist."""
        state = BatchState(current_batch=5, files_in_current_batch=100)

        assert state.validate_against_filesystem(empty_dir) is False


# ==============================
# get_batch_for_file_fast Tests
# ==============================

class TestGetBatchForFileFast:
    """Tests for O(1) fast batch lookup."""

    def test_returns_current_batch_when_not_full(self, empty_dir: Path):
        """T007a: Returns current batch when space available."""
        batch_dir, batch_num = get_batch_for_file_fast(
            empty_dir, current_batch=1, files_in_current_batch=0, batch_size=500
        )

        assert batch_num == 1
        assert batch_dir == empty_dir / "batch-001"

    def test_returns_current_batch_at_boundary_minus_one(self, empty_dir: Path):
        """T007b: Returns current batch at size-1 (room for one more)."""
        batch_dir, batch_num = get_batch_for_file_fast(
            empty_dir, current_batch=1, files_in_current_batch=499, batch_size=500
        )

        assert batch_num == 1

    def test_returns_next_batch_when_full(self, empty_dir: Path):
        """T007c: Returns next batch when current is full."""
        batch_dir, batch_num = get_batch_for_file_fast(
            empty_dir, current_batch=1, files_in_current_batch=500, batch_size=500
        )

        assert batch_num == 2
        assert batch_dir == empty_dir / "batch-002"

    def test_creates_directory(self, empty_dir: Path):
        """T007d: Creates batch directory if it doesn't exist."""
        assert not (empty_dir / "batch-001").exists()

        batch_dir, _ = get_batch_for_file_fast(
            empty_dir, current_batch=1, files_in_current_batch=0, batch_size=500
        )

        assert batch_dir.exists()

    def test_handles_large_batch_numbers(self, empty_dir: Path):
        """T007e: Handles large batch numbers with proper padding."""
        batch_dir, batch_num = get_batch_for_file_fast(
            empty_dir, current_batch=99, files_in_current_batch=500, batch_size=500
        )

        assert batch_num == 100
        assert batch_dir.name == "batch-100"


# ==============================
# get_batch_for_file Tests (O(N))
# ==============================

class TestGetBatchForFile:
    """Tests for O(N) filesystem-scanning batch lookup."""

    def test_creates_first_batch_in_empty_dir(self, empty_dir: Path):
        """T008a: Creates batch-001 in empty directory."""
        batch_dir = get_batch_for_file(empty_dir, batch_size=500)

        assert batch_dir == empty_dir / "batch-001"
        assert batch_dir.exists()

    def test_returns_existing_batch_with_space(self, dir_with_batches: Path):
        """T008b: Returns existing batch that has space."""
        batch_dir = get_batch_for_file(dir_with_batches, batch_size=500)

        # batch-002 has 250 files, room for more
        assert batch_dir == dir_with_batches / "batch-002"

    def test_creates_new_batch_when_last_full(self, tmp_path: Path):
        """T008c: Creates new batch when last is full."""
        sgf_dir = tmp_path / "sgf"
        batch1 = sgf_dir / "batch-001"
        batch1.mkdir(parents=True)

        for i in range(500):
            (batch1 / f"puzzle-{i:04d}.sgf").write_text("(;GM[1])")

        batch_dir = get_batch_for_file(sgf_dir, batch_size=500)

        assert batch_dir == sgf_dir / "batch-002"


# ==============================
# Utility Function Tests
# ==============================

class TestUtilityFunctions:
    """Tests for utility functions."""

    def test_get_batch_dir_number_valid(self):
        """T009a: Extracts batch number from valid path."""
        assert get_batch_dir_number(Path("/path/to/batch-001")) == 1
        assert get_batch_dir_number(Path("/path/to/batch-010")) == 10
        assert get_batch_dir_number(Path("/path/to/batch-999")) == 999

    def test_get_batch_dir_number_invalid(self):
        """T009b: Returns None for non-batch paths."""
        assert get_batch_dir_number(Path("/path/to/other")) is None
        assert get_batch_dir_number(Path("/path/to/batch-")) is None
        assert get_batch_dir_number(Path("/path/to/batch-abc")) is None

    def test_find_existing_batches_sorted(self, dir_with_batches: Path):
        """T009c: Finds batches sorted by number."""
        batches = find_existing_batches(dir_with_batches)

        assert len(batches) == 2
        assert batches[0].batch_number == 1
        assert batches[1].batch_number == 2

    def test_count_total_files(self, dir_with_batches: Path):
        """T009d: Counts files across all batches."""
        total = count_total_files(dir_with_batches)

        assert total == 750  # 500 + 250

    def test_get_batch_summary(self, dir_with_batches: Path):
        """T009e: Returns complete batch summary."""
        summary = get_batch_summary(dir_with_batches)

        assert summary["batch_count"] == 2
        assert summary["total_files"] == 750
        assert len(summary["batches"]) == 2


# ==============================
# Edge Case Tests
# ==============================

class TestEdgeCases:
    """Tests for edge cases."""

    def test_empty_batch_in_middle(self, tmp_path: Path):
        """T010a: Handles gap in batch numbering."""
        sgf_dir = tmp_path / "sgf"

        # Create batch-001 and batch-003 (skip batch-002)
        (sgf_dir / "batch-001").mkdir(parents=True)
        (sgf_dir / "batch-001" / "file.sgf").write_text("(;)")
        (sgf_dir / "batch-003").mkdir()
        (sgf_dir / "batch-003" / "file.sgf").write_text("(;)")

        batches = find_existing_batches(sgf_dir)

        # Should find both
        assert len(batches) == 2
        assert batches[0].batch_number == 1
        assert batches[1].batch_number == 3

    def test_non_batch_directories_ignored(self, tmp_path: Path):
        """T010b: Ignores non-batch directories."""
        sgf_dir = tmp_path / "sgf"

        (sgf_dir / "batch-001").mkdir(parents=True)
        (sgf_dir / "batch-001" / "file.sgf").write_text("(;)")
        (sgf_dir / "other-dir").mkdir()
        (sgf_dir / "other-dir" / "file.sgf").write_text("(;)")

        batches = find_existing_batches(sgf_dir)

        assert len(batches) == 1
        assert batches[0].batch_number == 1

    def test_files_at_root_not_counted(self, tmp_path: Path):
        """T010c: Files at root level not counted."""
        sgf_dir = tmp_path / "sgf"
        sgf_dir.mkdir()

        # File at root, not in batch
        (sgf_dir / "orphan.sgf").write_text("(;)")

        total = count_total_files(sgf_dir)

        assert total == 0

    def test_concurrent_access_safe(self, empty_dir: Path):
        """T010d: Multiple saves don't corrupt state."""
        state1 = BatchState(current_batch=1, files_in_current_batch=0)
        state2 = BatchState(current_batch=2, files_in_current_batch=100)

        # Save both (simulating concurrent access)
        state1.save(empty_dir)
        state2.save(empty_dir)

        # Last write wins
        loaded = BatchState.load(empty_dir)
        assert loaded is not None
        assert loaded.current_batch == 2
