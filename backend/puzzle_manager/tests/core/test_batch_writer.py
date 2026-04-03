"""
Tests for backend.puzzle_manager.core.batch_writer module.

Comprehensive test coverage for:
- BatchState with schema evolution
- BatchWriter O(1) fast path and O(N) fallback (flat sgf/{NNNN}/ structure)
- Crash recovery (supports both flat and legacy layouts)
- Edge cases and error handling

Updated for flat sharding: sgf/{NNNN}/{hash}.sgf (no level nesting).
"""

import json
from datetime import datetime
from pathlib import Path

import pytest

from backend.puzzle_manager.core.batch_writer import (
    BATCH_STATE_FILENAME,
    BATCH_STATE_SCHEMA_VERSION,
    BatchState,
    BatchWriter,
)

# ==============================
# Fixtures
# ==============================

@pytest.fixture
def empty_sgf_root(tmp_path: Path) -> Path:
    """Empty SGF root directory."""
    sgf_root = tmp_path / "sgf"
    sgf_root.mkdir()
    return sgf_root


@pytest.fixture
def populated_sgf_root(tmp_path: Path) -> Path:
    """SGF root with pre-populated flat batch directories."""
    sgf_root = tmp_path / "sgf"

    # 0001 with 100 files (full)
    batch1 = sgf_root / "0001"
    batch1.mkdir(parents=True)
    for i in range(100):
        (batch1 / f"puzzle-{i:04d}.sgf").write_text("(;GM[1]SZ[19])")

    # 0002 with 50 files (not full)
    batch2 = sgf_root / "0002"
    batch2.mkdir()
    for i in range(50):
        (batch2 / f"puzzle-{i:04d}.sgf").write_text("(;GM[1]SZ[19])")

    return sgf_root


@pytest.fixture
def legacy_sgf_root(tmp_path: Path) -> Path:
    """SGF root with legacy sgf/{level}/batch-{NNNN}/ layout for migration tests."""
    sgf_root = tmp_path / "sgf"

    level_dir = sgf_root / "intermediate"
    batch1 = level_dir / "batch-0001"
    batch1.mkdir(parents=True)
    for i in range(100):
        (batch1 / f"puzzle-{i:04d}.sgf").write_text("(;GM[1]SZ[19])")

    batch2 = level_dir / "batch-0002"
    batch2.mkdir()
    for i in range(50):
        (batch2 / f"puzzle-{i:04d}.sgf").write_text("(;GM[1]SZ[19])")

    return sgf_root


# ==============================
# BatchState Tests
# ==============================

class TestBatchStateSave:
    """Tests for BatchState.save() method."""

    def test_save_creates_state_file(self, tmp_path: Path):
        state = BatchState(current_batch=1, files_in_current_batch=0)
        state.save(tmp_path)
        assert (tmp_path / BATCH_STATE_FILENAME).exists()

    def test_save_includes_schema_version(self, tmp_path: Path):
        state = BatchState()
        state.save(tmp_path)
        data = json.loads((tmp_path / BATCH_STATE_FILENAME).read_text())
        assert data["schema_version"] == BATCH_STATE_SCHEMA_VERSION

    def test_save_updates_timestamp(self, tmp_path: Path):
        state = BatchState()
        assert state.last_updated == ""
        state.save(tmp_path)
        data = json.loads((tmp_path / BATCH_STATE_FILENAME).read_text())
        assert data["last_updated"] != ""
        datetime.fromisoformat(data["last_updated"].replace("Z", "+00:00"))

    def test_save_overwrites_existing(self, tmp_path: Path):
        BatchState(current_batch=1, files_in_current_batch=10).save(tmp_path)
        BatchState(current_batch=5, files_in_current_batch=99).save(tmp_path)
        loaded = BatchState.load(tmp_path)
        assert loaded.current_batch == 5
        assert loaded.files_in_current_batch == 99


class TestBatchStateLoad:
    """Tests for BatchState.load() method."""

    def test_load_returns_saved_state(self, tmp_path: Path):
        BatchState(current_batch=5, files_in_current_batch=42).save(tmp_path)
        loaded = BatchState.load(tmp_path)
        assert loaded is not None
        assert loaded.current_batch == 5
        assert loaded.files_in_current_batch == 42

    def test_load_returns_none_when_not_found(self, tmp_path: Path):
        assert BatchState.load(tmp_path) is None

    def test_load_handles_corrupted_json(self, tmp_path: Path):
        state_path = tmp_path / BATCH_STATE_FILENAME
        state_path.write_text("{ not valid json }")
        assert BatchState.load(tmp_path) is None
        assert not state_path.exists()

    def test_load_handles_empty_file(self, tmp_path: Path):
        state_path = tmp_path / BATCH_STATE_FILENAME
        state_path.write_text("")
        assert BatchState.load(tmp_path) is None
        assert not state_path.exists()

    def test_load_handles_invalid_structure(self, tmp_path: Path):
        (tmp_path / BATCH_STATE_FILENAME).write_text('"just a string"')
        assert BatchState.load(tmp_path) is None


class TestBatchStateSchemaMigration:
    """Tests for schema migration."""

    def test_migrate_v1_to_v2(self, tmp_path: Path):
        v1_data = {
            "schema_version": 1, "current_batch": 3,
            "files_in_current_batch": 75, "last_updated": "2025-01-01T00:00:00Z",
        }
        (tmp_path / BATCH_STATE_FILENAME).write_text(json.dumps(v1_data))
        loaded = BatchState.load(tmp_path)
        assert loaded is not None
        assert loaded.current_batch == 3
        assert loaded.last_error is None
        assert loaded.retry_count == 0

    def test_old_schema_without_version_field(self, tmp_path: Path):
        old_data = {"current_batch": 7, "files_in_current_batch": 25, "last_updated": "2025-06-01T00:00:00Z"}
        (tmp_path / BATCH_STATE_FILENAME).write_text(json.dumps(old_data))
        loaded = BatchState.load(tmp_path)
        assert loaded is not None
        assert loaded.current_batch == 7


class TestBatchStateRecordFileSaved:
    """Tests for record_file_saved() method."""

    def test_increments_file_count(self):
        state = BatchState(current_batch=1, files_in_current_batch=0)
        state.record_file_saved(batch_size=100)
        assert state.files_in_current_batch == 1

    def test_advances_batch_when_full(self):
        state = BatchState(current_batch=1, files_in_current_batch=99)
        state.record_file_saved(batch_size=100)
        assert state.current_batch == 2
        assert state.files_in_current_batch == 0

    def test_clears_error_on_success(self):
        state = BatchState(current_batch=1, files_in_current_batch=0)
        state.last_error = "Previous error"
        state.retry_count = 3
        state.record_file_saved(batch_size=100)
        assert state.last_error is None
        assert state.retry_count == 0

    def test_multiple_files_across_batch_boundary(self):
        state = BatchState(current_batch=1, files_in_current_batch=98)
        state.record_file_saved(batch_size=100)
        assert state.current_batch == 1
        assert state.files_in_current_batch == 99
        state.record_file_saved(batch_size=100)
        assert state.current_batch == 2
        assert state.files_in_current_batch == 0
        state.record_file_saved(batch_size=100)
        assert state.current_batch == 2
        assert state.files_in_current_batch == 1

    def test_batch_size_2000(self):
        """Default config batch size of 2000."""
        state = BatchState(current_batch=1, files_in_current_batch=1999)
        state.record_file_saved(batch_size=2000)
        assert state.current_batch == 2
        assert state.files_in_current_batch == 0


class TestBatchStateRecovery:
    """Tests for crash recovery functionality."""

    def test_recover_from_empty_directory(self, tmp_path: Path):
        state = BatchState.recover_from_filesystem(tmp_path, batch_size=100)
        assert state.current_batch == 1
        assert state.files_in_current_batch == 0
        assert state.recovery_timestamp is not None

    def test_recover_from_flat_directory(self, populated_sgf_root: Path):
        """Recovery with flat {NNNN} dirs."""
        state = BatchState.recover_from_filesystem(populated_sgf_root, batch_size=100)
        assert state.current_batch == 2
        assert state.files_in_current_batch == 50

    def test_recover_from_legacy_directory(self, legacy_sgf_root: Path):
        """Recovery falls back to legacy batch-{NNNN} dirs inside level subdirs."""
        state = BatchState.recover_from_filesystem(legacy_sgf_root, batch_size=100)
        assert state.current_batch == 2
        assert state.files_in_current_batch == 50

    def test_recover_when_last_batch_full(self, tmp_path: Path):
        sgf_root = tmp_path / "sgf"
        batch1 = sgf_root / "0001"
        batch1.mkdir(parents=True)
        for i in range(100):
            (batch1 / f"puzzle-{i:04d}.sgf").write_text("(;GM[1])")
        state = BatchState.recover_from_filesystem(sgf_root, batch_size=100)
        assert state.current_batch == 2
        assert state.files_in_current_batch == 0

    def test_load_or_recover_prefers_file(self, populated_sgf_root: Path):
        BatchState(current_batch=99, files_in_current_batch=42).save(populated_sgf_root)
        loaded = BatchState.load_or_recover(populated_sgf_root, batch_size=100)
        assert loaded.current_batch == 99
        assert loaded.files_in_current_batch == 42

    def test_load_or_recover_falls_back_to_recovery(self, populated_sgf_root: Path):
        loaded = BatchState.load_or_recover(populated_sgf_root, batch_size=100)
        assert loaded.current_batch == 2
        assert loaded.files_in_current_batch == 50


class TestBatchStateRecordError:
    """Tests for error recording."""

    def test_record_error_tracks_message(self):
        state = BatchState()
        state.record_error("Connection timeout")
        assert state.last_error == "Connection timeout"
        assert state.retry_count == 1

    def test_record_error_increments_retry_count(self):
        state = BatchState()
        state.record_error("Error 1")
        state.record_error("Error 2")
        state.record_error("Error 3")
        assert state.retry_count == 3
        assert state.last_error == "Error 3"


# ==============================
# BatchWriter Tests (flat sgf/{NNNN}/ structure)
# ==============================

class TestBatchWriterInit:
    """Tests for BatchWriter initialization."""

    def test_init_stores_config(self, empty_sgf_root: Path):
        writer = BatchWriter(empty_sgf_root, max_files_per_dir=500)
        assert writer.sgf_root == empty_sgf_root
        assert writer.max_files_per_dir == 500

    def test_max_files_per_dir_is_required(self, empty_sgf_root: Path):
        """max_files_per_dir has no default — callers must supply from config."""
        with pytest.raises(TypeError):
            BatchWriter(empty_sgf_root)  # type: ignore[call-arg]


class TestBatchWriterGetNextBatchNumber:
    """Tests for get_next_batch_number() — global, no level param."""

    def test_returns_1_for_empty_dir(self, empty_sgf_root: Path):
        writer = BatchWriter(empty_sgf_root, max_files_per_dir=100)
        assert writer.get_next_batch_number() == 1

    def test_returns_current_batch_with_space(self, populated_sgf_root: Path):
        writer = BatchWriter(populated_sgf_root, max_files_per_dir=100)
        assert writer.get_next_batch_number() == 2

    def test_returns_next_batch_when_full(self, tmp_path: Path):
        sgf_root = tmp_path / "sgf"
        batch1 = sgf_root / "0001"
        batch1.mkdir(parents=True)
        for i in range(100):
            (batch1 / f"puzzle-{i:04d}.sgf").write_text("(;)")
        writer = BatchWriter(sgf_root, max_files_per_dir=100)
        assert writer.get_next_batch_number() == 2

    def test_caches_result(self, empty_sgf_root: Path):
        writer = BatchWriter(empty_sgf_root, max_files_per_dir=100)
        n1 = writer.get_next_batch_number()
        n2 = writer.get_next_batch_number()
        assert n1 == n2 == 1
        assert writer._cached_batch_num == 1


class TestBatchWriterAdvanceBatch:
    """Tests for advance_batch() method."""

    def test_increments_batch_number(self, empty_sgf_root: Path):
        writer = BatchWriter(empty_sgf_root, max_files_per_dir=100)
        writer.get_next_batch_number()
        assert writer.advance_batch() == 2
        assert writer._cached_batch_num == 2


class TestBatchWriterGetBatchDir:
    """Tests for get_batch_dir() — flat {NNNN} dirs."""

    def test_creates_batch_directory(self, empty_sgf_root: Path):
        writer = BatchWriter(empty_sgf_root, max_files_per_dir=100)
        batch_dir = writer.get_batch_dir()
        assert batch_dir.exists()
        assert batch_dir.name == "0001"

    def test_uses_provided_batch_number(self, empty_sgf_root: Path):
        writer = BatchWriter(empty_sgf_root, max_files_per_dir=100)
        batch_dir = writer.get_batch_dir(batch_num=5)
        assert batch_dir.name == "0005"

    def test_zero_pads_batch_number(self, empty_sgf_root: Path):
        writer = BatchWriter(empty_sgf_root, max_files_per_dir=100)
        batch_dir = writer.get_batch_dir(batch_num=42)
        assert batch_dir.name == "0042"


class TestBatchWriterGetBatchDirFast:
    """Tests for get_batch_dir_fast() — O(1) fast path, flat dirs."""

    def test_returns_current_batch_when_not_full(self, empty_sgf_root: Path):
        writer = BatchWriter(empty_sgf_root, max_files_per_dir=100)
        batch_dir, batch_num = writer.get_batch_dir_fast(current_batch=1, files_in_current_batch=0)
        assert batch_num == 1
        assert batch_dir.name == "0001"

    def test_returns_current_at_boundary_minus_one(self, empty_sgf_root: Path):
        writer = BatchWriter(empty_sgf_root, max_files_per_dir=100)
        _, batch_num = writer.get_batch_dir_fast(current_batch=1, files_in_current_batch=99)
        assert batch_num == 1

    def test_returns_next_batch_when_full(self, empty_sgf_root: Path):
        writer = BatchWriter(empty_sgf_root, max_files_per_dir=100)
        batch_dir, batch_num = writer.get_batch_dir_fast(current_batch=1, files_in_current_batch=100)
        assert batch_num == 2
        assert batch_dir.name == "0002"

    def test_creates_directory(self, empty_sgf_root: Path):
        writer = BatchWriter(empty_sgf_root, max_files_per_dir=100)
        batch_dir, _ = writer.get_batch_dir_fast(current_batch=1, files_in_current_batch=0)
        assert batch_dir.exists()

    def test_handles_large_batch_numbers(self, empty_sgf_root: Path):
        writer = BatchWriter(empty_sgf_root, max_files_per_dir=100)
        batch_dir, batch_num = writer.get_batch_dir_fast(current_batch=99, files_in_current_batch=100)
        assert batch_num == 100
        assert batch_dir.name == "0100"

    def test_with_2000_batch_size(self, empty_sgf_root: Path):
        writer = BatchWriter(empty_sgf_root, max_files_per_dir=2000)
        _, bn = writer.get_batch_dir_fast(current_batch=1, files_in_current_batch=1999)
        assert bn == 1
        _, bn = writer.get_batch_dir_fast(current_batch=1, files_in_current_batch=2000)
        assert bn == 2


class TestBatchWriterIsBatchFull:
    """Tests for is_batch_full() method."""

    def test_returns_false_for_nonexistent(self, empty_sgf_root: Path):
        writer = BatchWriter(empty_sgf_root, max_files_per_dir=100)
        assert writer.is_batch_full(1) is False

    def test_returns_false_when_not_full(self, populated_sgf_root: Path):
        writer = BatchWriter(populated_sgf_root, max_files_per_dir=100)
        assert writer.is_batch_full(2) is False

    def test_returns_true_when_full(self, populated_sgf_root: Path):
        writer = BatchWriter(populated_sgf_root, max_files_per_dir=100)
        assert writer.is_batch_full(1) is True


class TestBatchWriterClearCache:
    """Tests for clear_cache() method."""

    def test_clears_cached_batch_num(self, empty_sgf_root: Path):
        writer = BatchWriter(empty_sgf_root, max_files_per_dir=100)
        writer.get_next_batch_number()
        assert writer._cached_batch_num is not None
        writer.clear_cache()
        assert writer._cached_batch_num is None


class TestBatchWriterGetBatchSummary:
    """Tests for get_batch_summary() method."""

    def test_returns_empty_for_nonexistent(self, tmp_path: Path):
        writer = BatchWriter(tmp_path / "nonexistent", max_files_per_dir=100)
        summary = writer.get_batch_summary()
        assert summary == {"batch_count": 0, "total_files": 0, "batches": []}

    def test_returns_correct_summary(self, populated_sgf_root: Path):
        writer = BatchWriter(populated_sgf_root, max_files_per_dir=100)
        summary = writer.get_batch_summary()
        assert summary["batch_count"] == 2
        assert summary["total_files"] == 150
        assert summary["batches"][0] == {"number": 1, "files": 100}
        assert summary["batches"][1] == {"number": 2, "files": 50}


# ==============================
# Edge Cases
# ==============================

class TestEdgeCases:
    """Tests for edge cases (flat sharding)."""

    def test_gap_in_batch_numbering(self, tmp_path: Path):
        sgf_root = tmp_path / "sgf"
        (sgf_root / "0001").mkdir(parents=True)
        (sgf_root / "0001" / "file.sgf").write_text("(;)")
        (sgf_root / "0003").mkdir()
        (sgf_root / "0003" / "file.sgf").write_text("(;)")
        writer = BatchWriter(sgf_root, max_files_per_dir=100)
        assert writer.get_next_batch_number() == 3

    def test_non_batch_directories_ignored(self, tmp_path: Path):
        sgf_root = tmp_path / "sgf"
        (sgf_root / "0001").mkdir(parents=True)
        (sgf_root / "0001" / "file.sgf").write_text("(;)")
        (sgf_root / "other-dir").mkdir()
        (sgf_root / ".batch-state.json").write_text("{}")
        writer = BatchWriter(sgf_root, max_files_per_dir=100)
        summary = writer.get_batch_summary()
        assert summary["batch_count"] == 1

    def test_four_digit_batch_rollover(self, tmp_path: Path):
        sgf_root = tmp_path / "sgf"
        writer = BatchWriter(sgf_root, max_files_per_dir=100)
        batch_dir = writer.get_batch_dir(batch_num=9999)
        assert batch_dir.name == "9999"
        assert batch_dir.exists()

    def test_global_batching_mixes_levels(self, empty_sgf_root: Path):
        """All levels share global batch counter (no per-level dirs)."""
        writer = BatchWriter(empty_sgf_root, max_files_per_dir=2)
        batch_dir = writer.get_batch_dir(batch_num=1)
        (batch_dir / "beginner-puzzle.sgf").write_text("(;YG[beginner])")
        (batch_dir / "advanced-puzzle.sgf").write_text("(;YG[advanced])")
        assert len(list(batch_dir.glob("*.sgf"))) == 2
        assert writer.is_batch_full(1)
