"""
Tests for rebuild-centric rollback (v12).

Tests the simplified RollbackManager which uses delete + rebuild
instead of surgical index updates.
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from backend.puzzle_manager.models.publish_log import PublishLogEntry
from backend.puzzle_manager.publish_log import PublishLogReader, PublishLogWriter
from backend.puzzle_manager.rollback import RollbackManager, RollbackResult


def _make_entry(idx: int, run_id: str = "20260220-abc12345") -> PublishLogEntry:
    """Create a test publish log entry."""
    return PublishLogEntry(
        run_id=run_id,
        puzzle_id=f"puzzle{idx:04x}",
        source_id="test",
        path=f"sgf/0001/puzzle{idx:04x}.sgf",
        quality=2,
        trace_id=f"{idx:016x}",
        level="beginner",
        tags=("life-and-death",),
        collections=(),
    )


def _write_entries(log_dir: Path, entries: list[PublishLogEntry]) -> None:
    """Write entries to a publish log file."""
    writer = PublishLogWriter(log_dir=log_dir)
    writer.write_batch(entries)


def _create_sgf_files(output_dir: Path, entries: list[PublishLogEntry]) -> None:
    """Create dummy SGF files matching the publish log entries."""
    for entry in entries:
        sgf_path = output_dir / entry.path
        sgf_path.parent.mkdir(parents=True, exist_ok=True)
        sgf_path.write_text("(;FF[4]GM[1]SZ[9]PL[B]AB[dd];B[ee])", encoding="utf-8")


@pytest.fixture
def rollback_setup(tmp_path: Path):
    """Set up a rollback test environment."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    log_dir = output_dir / ".puzzle-inventory-state" / "publish-log"
    log_dir.mkdir(parents=True)

    entries = [_make_entry(i) for i in range(5)]
    _write_entries(log_dir, entries)
    _create_sgf_files(output_dir, entries)

    reader = PublishLogReader(log_dir=log_dir)
    manager = RollbackManager(output_dir=output_dir, log_reader=reader)

    return manager, entries, output_dir


class TestRollbackDryRun:
    """Tests for dry-run rollback."""

    def test_dry_run_does_not_delete(self, rollback_setup):
        manager, entries, output_dir = rollback_setup

        result = manager.rollback_by_run("20260220-abc12345", dry_run=True)

        assert result.success is True
        assert result.dry_run is True
        assert result.puzzles_affected == 5
        assert result.files_deleted == 0

        # Files should still exist
        for entry in entries:
            assert (output_dir / entry.path).exists()


class TestRollbackExecution:
    """Tests for actual rollback execution."""

    @patch("backend.puzzle_manager.rollback.PipelineLock")
    def test_deletes_sgf_files(self, mock_lock_cls, rollback_setup):
        manager, entries, output_dir = rollback_setup

        result = manager.rollback_by_run("20260220-abc12345", dry_run=False)

        assert result.success is True
        assert result.files_deleted == 5

        # Files should be gone
        for entry in entries:
            assert not (output_dir / entry.path).exists()

    @patch("backend.puzzle_manager.rollback.PipelineLock")
    def test_no_entries_found(self, mock_lock_cls, rollback_setup):
        manager, _, _ = rollback_setup

        result = manager.rollback_by_run("nonexistent-run", dry_run=False)

        assert result.success is True
        assert result.puzzles_affected == 0

    @patch("backend.puzzle_manager.rollback.PipelineLock")
    def test_handles_missing_files(self, mock_lock_cls, rollback_setup):
        manager, entries, output_dir = rollback_setup

        # Delete 2 files manually first
        (output_dir / entries[0].path).unlink()
        (output_dir / entries[1].path).unlink()

        result = manager.rollback_by_run("20260220-abc12345", dry_run=False)

        assert result.success is True
        assert result.files_deleted == 3  # Only 3 of 5 existed


class TestRollbackResult:
    """Tests for RollbackResult dataclass."""

    def test_summary_dry_run(self):
        result = RollbackResult(
            success=True, dry_run=True, puzzles_affected=10, files_deleted=0
        )
        summary = result.summary()
        assert "Would affect" in summary

    def test_summary_real_run(self):
        result = RollbackResult(
            success=True, dry_run=False, puzzles_affected=10, files_deleted=10
        )
        summary = result.summary()
        assert "Affected" in summary

    @patch("backend.puzzle_manager.rollback.PipelineLock")
    def test_batch_too_large(self, mock_lock_cls, tmp_path: Path):
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        log_dir = output_dir / ".puzzle-inventory-state" / "publish-log"
        log_dir.mkdir(parents=True)

        entries = [_make_entry(i) for i in range(20)]
        _write_entries(log_dir, entries)
        _create_sgf_files(output_dir, entries)

        reader = PublishLogReader(log_dir=log_dir)
        manager = RollbackManager(output_dir=output_dir, log_reader=reader, max_batch_size=10)

        result = manager.rollback_by_run("20260220-abc12345", dry_run=False)

        assert result.success is False
        assert "max=" in result.errors[0]
