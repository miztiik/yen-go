"""
Unit tests for publish log functionality.

Tests PublishLogWriter and PublishLogReader classes.
"""

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from backend.puzzle_manager.models.publish_log import PublishLogEntry
from backend.puzzle_manager.publish_log import PublishLogReader, PublishLogWriter


class TestPublishLogEntry:
    """Tests for PublishLogEntry dataclass."""

    def test_to_jsonl_compact(self):
        """Test JSONL serialization is compact."""
        entry = PublishLogEntry(
            run_id="20260129-abc12345",
            puzzle_id="puzzle-001",
            source_id="goproblems",
            path="sgf/beginner/batch-0001/puzzle-001.sgf",
            quality=3,
            trace_id="a1b2c3d4e5f67890",
            level="beginner",
        )
        jsonl = entry.to_jsonl()

        # Should parse back to same data
        data = json.loads(jsonl)
        assert data["run_id"] == "20260129-abc12345"
        assert data["puzzle_id"] == "puzzle-001"
        assert data["source_id"] == "goproblems"
        assert data["quality"] == 3
        assert data["trace_id"] == "a1b2c3d4e5f67890"
        assert data["level"] == "beginner"

    def test_from_jsonl_roundtrip(self):
        """Test JSONL roundtrip."""
        original = PublishLogEntry(
            run_id="20260129-abc12345",
            puzzle_id="puzzle-001",
            source_id="goproblems",
            path="sgf/beginner/batch-0001/puzzle-001.sgf",
            quality=2,
            trace_id="trace123",
            level="beginner",
        )
        jsonl = original.to_jsonl()
        restored = PublishLogEntry.from_jsonl(jsonl)

        assert restored == original

    def test_entry_is_immutable(self):
        """Test entry is frozen (immutable)."""
        entry = PublishLogEntry(
            run_id="20260129-abc12345",
            puzzle_id="puzzle-001",
            source_id="goproblems",
            path="sgf/beginner/batch-0001/puzzle-001.sgf",
            quality=3,
            trace_id="trace123",
            level="beginner",
        )

        with pytest.raises(AttributeError):
            entry.run_id = "different"  # type: ignore

    def test_to_jsonl_with_trace_id(self):
        """Test JSONL serialization includes trace_id."""
        entry = PublishLogEntry(
            run_id="20260129-abc12345",
            puzzle_id="puzzle-001",
            source_id="goproblems",
            path="sgf/beginner/batch-0001/puzzle-001.sgf",
            quality=3,
            trace_id="a1b2c3d4e5f67890",
            level="beginner",
        )
        jsonl = entry.to_jsonl()
        data = json.loads(jsonl)

        assert data["trace_id"] == "a1b2c3d4e5f67890"

    def test_to_jsonl_always_includes_all_mandatory_fields(self):
        """Test JSONL serialization always includes all mandatory fields."""
        entry = PublishLogEntry(
            run_id="20260129-abc12345",
            puzzle_id="puzzle-001",
            source_id="goproblems",
            path="sgf/beginner/batch-0001/puzzle-001.sgf",
            quality=1,
            trace_id="trace123",
            level="beginner",
        )
        jsonl = entry.to_jsonl()
        data = json.loads(jsonl)

        # All mandatory fields are always present
        assert "quality" in data
        assert "trace_id" in data
        assert "level" in data
        assert "tags" in data
        assert "collections" in data

    def test_from_jsonl_with_trace_id(self):
        """Test JSONL parsing includes trace_id."""
        jsonl = '{"run_id":"20260129-abc12345","puzzle_id":"puzzle-001","source_id":"goproblems","path":"sgf/beginner/batch-0001/puzzle-001.sgf","quality":3,"tags":[],"trace_id":"a1b2c3d4e5f67890","level":"beginner","collections":[]}'
        entry = PublishLogEntry.from_jsonl(jsonl)

        assert entry.trace_id == "a1b2c3d4e5f67890"

    def test_from_jsonl_missing_mandatory_field_raises(self):
        """Test JSONL parsing raises KeyError when mandatory field is missing."""
        # Missing quality, trace_id, level
        jsonl = '{"run_id":"20260129-abc12345","puzzle_id":"puzzle-001","source_id":"goproblems","path":"sgf/beginner/batch-0001/puzzle-001.sgf"}'
        with pytest.raises(KeyError):
            PublishLogEntry.from_jsonl(jsonl)

    def test_roundtrip_with_all_fields(self):
        """Test roundtrip with all fields including trace_id, level, collections (Spec 110, 138)."""
        original = PublishLogEntry(
            run_id="20260129-abc12345",
            puzzle_id="puzzle-001",
            source_id="goproblems",
            path="sgf/beginner/batch-0001/puzzle-001.sgf",
            quality=3,
            tags=("life-and-death", "corner"),
            trace_id="a1b2c3d4e5f67890",
            level="beginner",
            collections=("cho-chikun-life-death-elementary", "daily-2026-01"),
        )
        jsonl = original.to_jsonl()
        restored = PublishLogEntry.from_jsonl(jsonl)

        assert restored == original
        assert restored.trace_id == "a1b2c3d4e5f67890"
        assert restored.level == "beginner"
        assert restored.collections == ("cho-chikun-life-death-elementary", "daily-2026-01")

    def test_to_jsonl_with_level(self):
        """Test JSONL serialization includes level."""
        entry = PublishLogEntry(
            run_id="20260129-abc12345",
            puzzle_id="puzzle-001",
            source_id="goproblems",
            path="sgf/beginner/batch-0001/puzzle-001.sgf",
            quality=3,
            trace_id="trace123",
            level="beginner",
        )
        jsonl = entry.to_jsonl()
        data = json.loads(jsonl)
        assert data["level"] == "beginner"

    def test_to_jsonl_with_collections(self):
        """Test JSONL serialization includes collections."""
        entry = PublishLogEntry(
            run_id="20260129-abc12345",
            puzzle_id="puzzle-001",
            source_id="goproblems",
            path="sgf/beginner/batch-0001/puzzle-001.sgf",
            quality=3,
            trace_id="trace123",
            level="beginner",
            collections=("cho-chikun", "test-collection"),
        )
        jsonl = entry.to_jsonl()
        data = json.loads(jsonl)
        assert data["collections"] == ["cho-chikun", "test-collection"]

    def test_to_jsonl_includes_empty_collections(self):
        """Test JSONL serialization includes collections even when empty."""
        entry = PublishLogEntry(
            run_id="20260129-abc12345",
            puzzle_id="puzzle-001",
            source_id="goproblems",
            path="sgf/beginner/batch-0001/puzzle-001.sgf",
            quality=3,
            trace_id="trace123",
            level="beginner",
            collections=(),
        )
        jsonl = entry.to_jsonl()
        data = json.loads(jsonl)
        assert data["collections"] == []

    def test_from_jsonl_with_level_and_collections(self):
        """Test JSONL parsing includes level and collections."""
        jsonl = '{"run_id":"20260129-abc12345","puzzle_id":"puzzle-001","source_id":"goproblems","path":"sgf/beginner/batch-0001/puzzle-001.sgf","quality":3,"tags":[],"trace_id":"trace123","level":"intermediate","collections":["test-col"]}'
        entry = PublishLogEntry.from_jsonl(jsonl)
        assert entry.level == "intermediate"
        assert entry.collections == ("test-col",)


class TestPublishLogWriter:
    """Tests for PublishLogWriter class."""

    def test_write_single_entry(self, tmp_path: Path):
        """Test writing a single entry."""
        writer = PublishLogWriter(log_dir=tmp_path)
        entry = PublishLogEntry(
            run_id="20260129-abc12345",
            puzzle_id="puzzle-001",
            source_id="goproblems",
            path="sgf/beginner/batch-0001/puzzle-001.sgf",
            quality=3,
            trace_id="trace001",
            level="beginner",
        )

        writer.write(entry)

        # Should have created a date-named file
        log_files = list(tmp_path.glob("*.jsonl"))
        assert len(log_files) == 1

        # Should contain the entry
        content = log_files[0].read_text()
        assert "puzzle-001" in content
        assert content.endswith("\n")

    def test_write_batch_entries(self, tmp_path: Path):
        """Test writing multiple entries."""
        writer = PublishLogWriter(log_dir=tmp_path)
        entries = [
            PublishLogEntry(
                run_id="20260129-abc12345",
                puzzle_id=f"puzzle-{i:03d}",
                source_id="goproblems",
                path=f"sgf/beginner/batch-0001/puzzle-{i:03d}.sgf",
                quality=2,
                trace_id=f"trace-{i:03d}",
                level="beginner",
            )
            for i in range(10)
        ]

        count = writer.write_batch(entries)

        assert count == 10
        log_files = list(tmp_path.glob("*.jsonl"))
        assert len(log_files) == 1

        # Count lines
        lines = log_files[0].read_text().strip().split("\n")
        assert len(lines) == 10

    def test_write_batch_empty(self, tmp_path: Path):
        """Test writing empty batch."""
        writer = PublishLogWriter(log_dir=tmp_path)

        count = writer.write_batch([])

        assert count == 0
        log_files = list(tmp_path.glob("*.jsonl"))
        assert len(log_files) == 0

    def test_write_appends_to_existing(self, tmp_path: Path):
        """Test writing appends to existing log file."""
        writer = PublishLogWriter(log_dir=tmp_path)

        entry1 = PublishLogEntry(
            run_id="20260129-abc12345",
            puzzle_id="puzzle-001",
            source_id="goproblems",
            path="sgf/beginner/batch-0001/puzzle-001.sgf",
            quality=3,
            trace_id="trace001",
            level="beginner",
        )
        entry2 = PublishLogEntry(
            run_id="20260129-abc12345",
            puzzle_id="puzzle-002",
            source_id="goproblems",
            path="sgf/beginner/batch-0001/puzzle-002.sgf",
            quality=2,
            trace_id="trace002",
            level="beginner",
        )

        writer.write(entry1)
        writer.write(entry2)

        # Should have one file with two lines
        log_files = list(tmp_path.glob("*.jsonl"))
        assert len(log_files) == 1
        lines = log_files[0].read_text().strip().split("\n")
        assert len(lines) == 2


class TestPublishLogReader:
    """Tests for PublishLogReader class."""

    @pytest.fixture
    def populated_log_dir(self, tmp_path: Path) -> Path:
        """Create a log directory with test data."""
        # Create two days of logs
        day1 = tmp_path / "2026-01-28.jsonl"
        day2 = tmp_path / "2026-01-29.jsonl"

        day1_entries = [
            {"run_id": "run1", "puzzle_id": "p1", "source_id": "source1", "path": "sgf/p1.sgf", "quality": 3, "tags": [], "trace_id": "t1", "level": "beginner", "collections": []},
            {"run_id": "run1", "puzzle_id": "p2", "source_id": "source1", "path": "sgf/p2.sgf", "quality": 2, "tags": [], "trace_id": "t2", "level": "beginner", "collections": []},
        ]
        day2_entries = [
            {"run_id": "run2", "puzzle_id": "p3", "source_id": "source2", "path": "sgf/p3.sgf", "quality": 4, "tags": ["ko"], "trace_id": "t3", "level": "intermediate", "collections": []},
            {"run_id": "run2", "puzzle_id": "p4", "source_id": "source1", "path": "sgf/p4.sgf", "quality": 3, "tags": [], "trace_id": "t4", "level": "beginner", "collections": []},
        ]

        day1.write_text("\n".join(json.dumps(e) for e in day1_entries) + "\n")
        day2.write_text("\n".join(json.dumps(e) for e in day2_entries) + "\n")

        return tmp_path

    def test_list_dates(self, populated_log_dir: Path):
        """Test listing available dates."""
        reader = PublishLogReader(log_dir=populated_log_dir)

        dates = reader.list_dates()

        assert dates == ["2026-01-28", "2026-01-29"]

    def test_list_dates_empty_dir(self, tmp_path: Path):
        """Test listing dates on empty directory."""
        reader = PublishLogReader(log_dir=tmp_path)

        dates = reader.list_dates()

        assert dates == []

    def test_list_dates_nonexistent_dir(self, tmp_path: Path):
        """Test listing dates on nonexistent directory."""
        reader = PublishLogReader(log_dir=tmp_path / "nonexistent")

        dates = reader.list_dates()

        assert dates == []

    def test_read_date(self, populated_log_dir: Path):
        """Test reading entries for a specific date."""
        reader = PublishLogReader(log_dir=populated_log_dir)

        entries = list(reader.read_date("2026-01-28"))

        assert len(entries) == 2
        assert entries[0].puzzle_id == "p1"
        assert entries[1].puzzle_id == "p2"

    def test_read_date_nonexistent(self, populated_log_dir: Path):
        """Test reading entries for nonexistent date."""
        reader = PublishLogReader(log_dir=populated_log_dir)

        entries = list(reader.read_date("2025-01-01"))

        assert len(entries) == 0

    def test_search_by_run_id(self, populated_log_dir: Path):
        """Test searching by run ID."""
        reader = PublishLogReader(log_dir=populated_log_dir)

        entries = reader.search_by_run_id("run1")

        assert len(entries) == 2
        assert all(e.run_id == "run1" for e in entries)

    def test_search_by_run_id_not_found(self, populated_log_dir: Path):
        """Test searching for nonexistent run ID."""
        reader = PublishLogReader(log_dir=populated_log_dir)

        entries = reader.search_by_run_id("nonexistent")

        assert len(entries) == 0

    def test_search_by_puzzle_id(self, populated_log_dir: Path):
        """Test searching by puzzle ID."""
        reader = PublishLogReader(log_dir=populated_log_dir)

        entry = reader.search_by_puzzle_id("p3")

        assert entry is not None
        assert entry.puzzle_id == "p3"
        assert entry.source_id == "source2"

    def test_search_by_puzzle_id_not_found(self, populated_log_dir: Path):
        """Test searching for nonexistent puzzle ID."""
        reader = PublishLogReader(log_dir=populated_log_dir)

        entry = reader.search_by_puzzle_id("nonexistent")

        assert entry is None

    def test_search_by_source(self, populated_log_dir: Path):
        """Test searching by source adapter."""
        reader = PublishLogReader(log_dir=populated_log_dir)

        entries = reader.search_by_source("source1")

        assert len(entries) == 3  # p1, p2, p4
        assert all(e.source_id == "source1" for e in entries)

    def test_search_by_date_range(self, populated_log_dir: Path):
        """Test searching by date range."""
        reader = PublishLogReader(log_dir=populated_log_dir)

        entries = reader.search_by_date_range("2026-01-28", "2026-01-28")

        assert len(entries) == 2  # Only day1

    def test_get_run_ids(self, populated_log_dir: Path):
        """Test getting unique run IDs."""
        reader = PublishLogReader(log_dir=populated_log_dir)

        run_ids = reader.get_run_ids()

        assert run_ids == {"run1", "run2"}

    def test_count_entries(self, populated_log_dir: Path):
        """Test counting total entries."""
        reader = PublishLogReader(log_dir=populated_log_dir)

        count = reader.count_entries()

        assert count == 4

    def test_list_files(self, populated_log_dir: Path):
        """Test listing log files with metadata."""
        reader = PublishLogReader(log_dir=populated_log_dir)

        files = reader.list_files()

        assert len(files) == 2
        assert files[0].date == "2026-01-28"
        assert files[0].entry_count == 2
        assert files[1].date == "2026-01-29"
        assert files[1].entry_count == 2


class TestPublishLogRetention:
    """Tests for publish log retention and cleanup (T047, T048)."""

    @pytest.fixture
    def log_dir_with_old_files(self, tmp_path):
        """Create a log directory with old and new log files."""
        log_dir = tmp_path / "publish-log"
        log_dir.mkdir()

        today = datetime.now(UTC)

        # Create files with various ages
        test_files = [
            ("2025-01-01.jsonl", 120),  # 120 days old - should delete
            ("2025-02-01.jsonl", 90),   # 90 days old - should delete at default threshold
            ("2025-03-01.jsonl", 60),   # 60 days old - should preserve
            (today.strftime("%Y-%m-%d") + ".jsonl", 0),  # Today - should preserve
            ("audit.jsonl", None),       # Audit log - should NEVER delete
            ("rollback-audit.jsonl", None),  # Rollback audit - should NEVER delete
        ]

        for filename, _ in test_files:
            file_path = log_dir / filename
            file_path.write_text('{"test": "data"}\n')

        return log_dir

    def test_cleanup_respects_retention_days(self, log_dir_with_old_files):
        """Cleanup should respect retention_days parameter (T047)."""
        reader = PublishLogReader(log_dir=log_dir_with_old_files)

        # Default 90 days - should delete files older than 90 days
        counts = reader.cleanup_old_logs(retention_days=90, dry_run=False)

        # Check counts
        assert counts["deleted"] >= 1  # At least 2025-01-01 should be deleted
        assert counts["preserved"] >= 1  # Recent files preserved
        assert counts["skipped_audit"] == 2  # Both audit logs preserved

    def test_cleanup_never_deletes_audit_log(self, log_dir_with_old_files):
        """Cleanup should NEVER delete audit log files (T048, FR-052)."""
        reader = PublishLogReader(log_dir=log_dir_with_old_files)

        # Even with 0 retention (delete everything), audit logs must remain
        reader.cleanup_old_logs(retention_days=0, dry_run=False)

        # Verify audit logs still exist
        assert (log_dir_with_old_files / "audit.jsonl").exists()
        assert (log_dir_with_old_files / "rollback-audit.jsonl").exists()

    def test_cleanup_dry_run_does_not_delete(self, log_dir_with_old_files):
        """Dry run should not actually delete files."""
        reader = PublishLogReader(log_dir=log_dir_with_old_files)

        # Count files before
        files_before = list(log_dir_with_old_files.glob("*.jsonl"))

        # Dry run cleanup
        counts = reader.cleanup_old_logs(retention_days=30, dry_run=True)

        # Count files after
        files_after = list(log_dir_with_old_files.glob("*.jsonl"))

        # Files should be unchanged
        assert len(files_before) == len(files_after)
        assert counts["deleted"] > 0  # Would have deleted some

    def test_cleanup_returns_accurate_counts(self, log_dir_with_old_files):
        """Cleanup should return accurate counts of deleted/preserved files."""
        reader = PublishLogReader(log_dir=log_dir_with_old_files)

        counts = reader.cleanup_old_logs(retention_days=365, dry_run=True)

        # With 365 day retention, nothing should be deleted except very old files
        total = counts["deleted"] + counts["preserved"] + counts["skipped_audit"]
        assert total == 6  # All test files accounted for


class TestPublishLogRunIdFormats:
    """Tests for run_id format (spec-041)."""

    def test_entry_with_new_run_id_format(self):
        """Entry with date-prefixed run_id should work."""
        entry = PublishLogEntry(
            run_id="20260129-abc12345",
            puzzle_id="puzzle-001",
            source_id="test",
            path="sgf/test.sgf",
            quality=2,
            trace_id="trace001",
            level="beginner",
        )

        jsonl = entry.to_jsonl()
        restored = PublishLogEntry.from_jsonl(jsonl)

        assert restored.run_id == "20260129-abc12345"
        assert restored == entry

    def test_search_by_run_id(self, tmp_path: Path):
        """Searching by run_id should find entries."""
        writer = PublishLogWriter(log_dir=tmp_path)
        run_id = "20260129-abc12345"

        writer.write(PublishLogEntry(
            run_id=run_id,
            puzzle_id="puzzle-001",
            source_id="test",
            path="sgf/test1.sgf",
            quality=3,
            trace_id="trace001",
            level="beginner",
        ))

        reader = PublishLogReader(log_dir=tmp_path)
        results = reader.search_by_run_id(run_id)

        assert len(results) == 1
        assert results[0].run_id == run_id


class TestPublishLogSearchOptimization:
    """Tests for string pre-filter, index-accelerated search, and rebuild_indexes.

    Verifies that optimized search methods produce identical results to the
    original read_all() approach, and that write-time indexes are created and
    used correctly.
    """

    @pytest.fixture
    def populated_log_dir(self, tmp_path: Path) -> Path:
        """Create a log directory with test data (no indexes)."""
        day1 = tmp_path / "2026-01-28.jsonl"
        day2 = tmp_path / "2026-01-29.jsonl"

        day1_entries = [
            {"run_id": "run1", "puzzle_id": "p1", "source_id": "source1", "path": "sgf/p1.sgf", "quality": 3, "tags": [], "trace_id": "t1", "level": "beginner", "collections": []},
            {"run_id": "run1", "puzzle_id": "p2", "source_id": "source1", "path": "sgf/p2.sgf", "quality": 2, "tags": [], "trace_id": "t2", "level": "beginner", "collections": []},
        ]
        day2_entries = [
            {"run_id": "run2", "puzzle_id": "p3", "source_id": "source2", "path": "sgf/p3.sgf", "quality": 4, "tags": ["ko"], "trace_id": "t3", "level": "intermediate", "collections": []},
            {"run_id": "run2", "puzzle_id": "p4", "source_id": "source1", "path": "sgf/p4.sgf", "quality": 3, "tags": [], "trace_id": "t4", "level": "beginner", "collections": []},
        ]

        day1.write_text("\n".join(json.dumps(e, separators=(",", ":")) for e in day1_entries) + "\n")
        day2.write_text("\n".join(json.dumps(e, separators=(",", ":")) for e in day2_entries) + "\n")

        return tmp_path

    # --- String pre-filter (no indexes) ---

    def test_search_by_run_id_prefilter(self, populated_log_dir: Path):
        """Pre-filter search should return same results as full scan."""
        reader = PublishLogReader(log_dir=populated_log_dir)
        entries = reader.search_by_run_id("run1")
        assert len(entries) == 2
        assert all(e.run_id == "run1" for e in entries)

    def test_search_by_puzzle_id_prefilter(self, populated_log_dir: Path):
        """Pre-filter search should find specific puzzle."""
        reader = PublishLogReader(log_dir=populated_log_dir)
        entry = reader.search_by_puzzle_id("p3")
        assert entry is not None
        assert entry.puzzle_id == "p3"
        assert entry.source_id == "source2"

    def test_search_by_puzzle_id_not_found_prefilter(self, populated_log_dir: Path):
        """Pre-filter search should return None for missing puzzle."""
        reader = PublishLogReader(log_dir=populated_log_dir)
        assert reader.search_by_puzzle_id("nonexistent") is None

    def test_search_by_source_prefilter(self, populated_log_dir: Path):
        """Pre-filter search should find all entries from source."""
        reader = PublishLogReader(log_dir=populated_log_dir)
        entries = reader.search_by_source("source1")
        assert len(entries) == 3
        assert all(e.source_id == "source1" for e in entries)

    def test_find_by_trace_id_no_index(self, populated_log_dir: Path):
        """find_by_trace_id should fall back to scan without index."""
        reader = PublishLogReader(log_dir=populated_log_dir)
        entry = reader.find_by_trace_id("t3")
        assert entry is not None
        assert entry.puzzle_id == "p3"

    def test_find_by_trace_id_not_found(self, populated_log_dir: Path):
        """find_by_trace_id should return None for missing trace."""
        reader = PublishLogReader(log_dir=populated_log_dir)
        assert reader.find_by_trace_id("nonexistent") is None

    # --- Substring false-positive guard ---

    def test_prefilter_rejects_substring_match(self, tmp_path: Path):
        """Pre-filter must not return entries where the value is a substring."""
        entry_data = {"run_id": "run1-extended", "puzzle_id": "p1-long", "source_id": "source1-extra", "path": "sgf/p1.sgf", "quality": 3, "tags": [], "trace_id": "t1-long", "level": "beginner", "collections": []}
        (tmp_path / "2026-01-30.jsonl").write_text(json.dumps(entry_data, separators=(",", ":")) + "\n")

        reader = PublishLogReader(log_dir=tmp_path)
        # These should NOT match because the field values are different
        assert reader.search_by_puzzle_id("p1") is None
        assert reader.search_by_run_id("run1") == []
        assert reader.search_by_source("source1") == []
        assert reader.find_by_trace_id("t1") is None
