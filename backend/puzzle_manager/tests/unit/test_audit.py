"""Unit tests for the unified audit log module."""

import json
from pathlib import Path

from backend.puzzle_manager.audit import AuditEntry, write_audit_entry


class TestAuditEntry:
    """Tests for AuditEntry dataclass."""

    def test_audit_entry_fields(self):
        """AuditEntry should hold operation, target, and details."""
        entry = AuditEntry(
            timestamp="2026-02-22T14:00:00+00:00",
            operation="publish",
            target="puzzles-collection",
            details={"files_published": 10, "source": "sanderland"},
        )
        assert entry.operation == "publish"
        assert entry.target == "puzzles-collection"
        assert entry.details["files_published"] == 10

    def test_audit_entry_cleanup_with_files_deleted(self):
        """AuditEntry should support files_deleted dict for cleanup."""
        entry = AuditEntry(
            timestamp="2026-02-22T14:00:00+00:00",
            operation="cleanup",
            target="puzzles-collection",
            details={
                "files_deleted": {"sgf": 100, "database": 20, "publish-log": 5},
                "paths_cleared": ["sgf/", "yengo-search.db"],
            },
        )
        assert entry.details["files_deleted"]["sgf"] == 100
        assert entry.details["files_deleted"]["database"] == 20


class TestWriteAuditEntry:
    """Tests for write_audit_entry function."""

    def test_write_creates_file(self, tmp_path: Path):
        """write_audit_entry should create audit.jsonl if it doesn't exist."""
        audit_file = tmp_path / "ops" / "audit.jsonl"
        assert not audit_file.exists()

        write_audit_entry(
            audit_file=audit_file,
            operation="publish",
            target="puzzles-collection",
            details={"files_published": 5},
        )

        assert audit_file.exists()

    def test_write_appends_jsonl(self, tmp_path: Path):
        """write_audit_entry should append, not overwrite."""
        audit_file = tmp_path / "audit.jsonl"

        # Write two entries
        write_audit_entry(audit_file, "publish", "puzzles-collection", {"files_published": 5})
        write_audit_entry(audit_file, "cleanup", "puzzles-collection", {"files_deleted": {"sgf": 10}})

        lines = [line for line in audit_file.read_text().strip().split("\n") if line]
        assert len(lines) == 2

        first = json.loads(lines[0])
        second = json.loads(lines[1])
        assert first["operation"] == "publish"
        assert second["operation"] == "cleanup"

    def test_write_includes_timestamp(self, tmp_path: Path):
        """Entries should have ISO 8601 timestamps."""
        audit_file = tmp_path / "audit.jsonl"

        write_audit_entry(audit_file, "publish", "puzzles-collection", {"files_published": 1})

        entry = json.loads(audit_file.read_text().strip())
        assert "timestamp" in entry
        # ISO 8601 format check (contains T separator and timezone)
        assert "T" in entry["timestamp"]

    def test_write_cleanup_entry(self, tmp_path: Path):
        """Cleanup entries should have files_deleted and paths_cleared in details."""
        audit_file = tmp_path / "audit.jsonl"
        files_deleted = {"sgf": 100, "database": 20, "publish-log": 5}
        paths_cleared = ["sgf/", "yengo-search.db", "publish-log/"]

        write_audit_entry(
            audit_file=audit_file,
            operation="cleanup",
            target="puzzles-collection",
            details={
                "files_deleted": files_deleted,
                "paths_cleared": paths_cleared,
            },
        )

        entry = json.loads(audit_file.read_text().strip())
        assert entry["operation"] == "cleanup"
        assert entry["details"]["files_deleted"]["sgf"] == 100
        assert entry["details"]["paths_cleared"] == paths_cleared

    def test_write_publish_entry(self, tmp_path: Path):
        """Publish entries should have files_published, source, and run_id."""
        audit_file = tmp_path / "audit.jsonl"

        write_audit_entry(
            audit_file=audit_file,
            operation="publish",
            target="puzzles-collection",
            details={
                "files_published": 42,
                "files_failed": 3,
                "files_skipped": 1,
                "source": "sanderland",
                "run_id": "20260222-abc12345",
            },
        )

        entry = json.loads(audit_file.read_text().strip())
        assert entry["operation"] == "publish"
        assert entry["details"]["files_published"] == 42
        assert entry["details"]["source"] == "sanderland"
        assert entry["details"]["run_id"] == "20260222-abc12345"
