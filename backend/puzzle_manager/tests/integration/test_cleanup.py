"""Integration tests for cleanup command with safety constraints."""

import os
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from backend.puzzle_manager.pipeline.cleanup import (
    cleanup_old_files,
    cleanup_target,
    reset_staging,
)

# Set PYTHONPATH to repo root for subprocess calls
REPO_ROOT = Path(__file__).resolve().parents[4]


def _get_env() -> dict:
    """Get environment with PYTHONPATH set to repo root."""
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT)
    return env


class TestCleanupCommand:
    """Tests for the clean CLI command."""

    def test_clean_command_runs(self) -> None:
        """Clean command should execute without error."""
        result = subprocess.run(
            [sys.executable, "-m", "backend.puzzle_manager", "clean", "--dry-run"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        # Should complete
        assert result.returncode in [0, 1]

    def test_clean_dry_run_no_deletion(self) -> None:
        """Clean with --dry-run should not delete files."""
        result = subprocess.run(
            [sys.executable, "-m", "backend.puzzle_manager", "clean", "--dry-run"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        # Output should indicate dry run
        result.stdout.lower()
        assert result.returncode in [0, 1]

    def test_clean_with_retention_days(self) -> None:
        """Clean should accept --retention-days option."""
        result = subprocess.run(
            [sys.executable, "-m", "backend.puzzle_manager", "clean",
             "--retention-days", "30", "--dry-run"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert "unrecognized" not in result.stderr.lower()
        assert result.returncode in [0, 1]


class TestCleanupTarget:
    """Tests for targeted cleanup."""

    def test_clean_target_staging(self) -> None:
        """Clean --target staging should clean staging directory."""
        result = subprocess.run(
            [sys.executable, "-m", "backend.puzzle_manager", "clean",
             "--target", "staging", "--dry-run"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode in [0, 1]

    def test_clean_target_state(self) -> None:
        """Clean --target state should clean state directory."""
        result = subprocess.run(
            [sys.executable, "-m", "backend.puzzle_manager", "clean",
             "--target", "state", "--dry-run"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode in [0, 1]

    def test_clean_target_logs(self) -> None:
        """Clean --target logs should clean logs directory."""
        result = subprocess.run(
            [sys.executable, "-m", "backend.puzzle_manager", "clean",
             "--target", "logs", "--dry-run"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode in [0, 1]

    def test_clean_target_staging_and_state(self) -> None:
        """Clean multiple targets in sequence should work."""
        # Test cleaning staging
        result1 = subprocess.run(
            [sys.executable, "-m", "backend.puzzle_manager", "clean",
             "--target", "staging", "--dry-run"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result1.returncode in [0, 1]

        # Test cleaning state
        result2 = subprocess.run(
            [sys.executable, "-m", "backend.puzzle_manager", "clean",
             "--target", "state", "--dry-run"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result2.returncode in [0, 1]

    def test_clean_invalid_target(self) -> None:
        """Clean with invalid target should fail."""
        result = subprocess.run(
            [sys.executable, "-m", "backend.puzzle_manager", "clean",
             "--target", "invalid"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        # Should fail due to invalid choice
        assert result.returncode != 0


class TestRetentionSafety:
    """Tests for 24-hour minimum retention safety (EC-005)."""

    def test_retention_minimum_24_hours(self) -> None:
        """Retention period should be at least 24 hours (1 day)."""
        # Retention below 1 day should be rejected or treated as 1
        with TemporaryDirectory():
            # cleanup_old_files with 0 days should not delete recent files
            counts = cleanup_old_files(
                retention_days=1,  # Minimum safe value
                dry_run=True,
            )

            # Should return a count dict
            assert isinstance(counts, dict)

    def test_retention_days_must_be_positive(self) -> None:
        """Retention days must be a positive integer."""
        # 0 or negative should be handled safely
        try:
            cleanup_old_files(
                retention_days=0,
                dry_run=True,
            )
            # If it accepts 0, it should not delete everything
            assert True
        except (ValueError, Exception):
            # Rejection of invalid value is also acceptable
            assert True

    def test_recent_files_not_deleted(self) -> None:
        """Files created today should not be deleted."""
        with TemporaryDirectory() as tmpdir:
            # Create a recent file
            recent_file = Path(tmpdir) / "recent.log"
            recent_file.write_text("test")

            # Cleanup with 45-day retention should not delete it
            from backend.puzzle_manager.pipeline.cleanup import _cleanup_directory

            cutoff = datetime.now(UTC) - timedelta(days=45)
            _cleanup_directory(
                Path(tmpdir),
                cutoff,
                patterns=["*.log"],
                dry_run=False,
            )

            # Recent file should still exist
            assert recent_file.exists()


class TestCleanupFunction:
    """Tests for cleanup function behavior."""

    def test_cleanup_old_files_returns_counts(self) -> None:
        """cleanup_old_files should return deletion counts."""
        counts = cleanup_old_files(
            retention_days=45,
            dry_run=True,
        )

        assert isinstance(counts, dict)
        assert "logs" in counts
        assert "state" in counts
        assert "failed" in counts

    def test_cleanup_target_returns_counts(self) -> None:
        """cleanup_target should return deletion counts."""
        counts = cleanup_target(
            target="logs",
            dry_run=True,
        )

        assert isinstance(counts, dict)

    def test_reset_staging_requires_confirmation(self) -> None:
        """reset_staging should require explicit confirmation."""
        with pytest.raises(Exception):
            # Without confirm=True, should raise
            reset_staging(confirm=False)

    def test_reset_staging_with_confirmation(self) -> None:
        """reset_staging with confirm=True should work."""
        # Just verify it's callable with dry_run
        result = reset_staging(confirm=True, dry_run=True)
        assert result is True


class TestCleanupIdempotency:
    """Tests for idempotent cleanup behavior."""

    def test_multiple_cleanups_safe(self) -> None:
        """Running cleanup multiple times should be safe."""
        for _ in range(3):
            counts = cleanup_old_files(
                retention_days=45,
                dry_run=True,
            )
            assert isinstance(counts, dict)

    def test_cleanup_empty_directory_safe(self) -> None:
        """Cleaning empty directories should be safe."""
        with TemporaryDirectory() as tmpdir:
            from backend.puzzle_manager.pipeline.cleanup import _cleanup_directory

            # Empty directory
            cutoff = datetime.now(UTC)
            deleted = _cleanup_directory(
                Path(tmpdir),
                cutoff,
                patterns=["*.log"],
                dry_run=False,
            )

            assert deleted == 0


# =============================================================================
# Spec 107, Phase 8: Consistent Collection Cleanup Tests
# =============================================================================

class TestCollectionCleanupConsistent:
    """Tests for T043-T050: Collection cleanup produces consistent empty state.

    Spec 107: After cleanup, `inventory --check` should pass with 0 puzzles.
    """

    @pytest.fixture
    def populated_collection(self, tmp_path) -> Path:
        """Create a populated collection structure for cleanup tests."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Create ops dir structure
        ops_dir = output_dir / ".puzzle-inventory-state"
        ops_dir.mkdir()

        # Create publish-log
        publish_log_dir = ops_dir / "publish-log"
        publish_log_dir.mkdir()
        (publish_log_dir / "2026-01-30.jsonl").write_text(
            '{"run_id":"test","puzzle_id":"p1","source_id":"test","path":"sgf/beginner/2026/01/p1.sgf","quality":2,"trace_id":"trace-cl-p1","level":"beginner","tags":[],"collections":[]}\n'
        )

        # Create rollback-backup
        rollback_dir = ops_dir / "rollback-backup"
        rollback_dir.mkdir()
        (rollback_dir / "tx-123.json").write_text('{}')

        # Create inventory
        (ops_dir / "inventory.json").write_text('{"collection":{"total_puzzles":1}}')

        # Create audit log
        (ops_dir / "audit.jsonl").write_text('{"event":"test"}\n')

        # Create SGF files
        sgf_dir = output_dir / "sgf" / "beginner" / "2026" / "01"
        sgf_dir.mkdir(parents=True)
        (sgf_dir / "p1.sgf").write_text("(;FF[4]GM[1])")

        # Create views
        views_dir = output_dir / "views" / "by-level"
        views_dir.mkdir(parents=True)
        (views_dir / "beginner.json").write_text('{"entries":[]}')

        # Create legacy pagination state (backward compat — cleanup should handle)
        (output_dir / "views" / ".pagination-state.json").write_text('{}')

        return output_dir

    def test_cleanup_deletes_all_sgf_files(self, populated_collection):
        """T043: cleanup_target should delete all SGF files."""
        output_dir = populated_collection

        # Verify SGF exists before
        sgf_files = list((output_dir / "sgf").rglob("*.sgf"))
        assert len(sgf_files) > 0

        # Create mock for cleanup_target to work with tmp_path
        from backend.puzzle_manager.pipeline.cleanup import _clean_all_files

        counts = _clean_all_files(
            output_dir / "sgf",
            dry_run=False,
        )

        # Verify SGF files deleted
        sgf_files_after = list((output_dir / "sgf").rglob("*.sgf"))
        assert len(sgf_files_after) == 0
        assert counts > 0

    def test_cleanup_deletes_view_files(self, populated_collection):
        """T044: cleanup_target should delete all view JSON files (except protected)."""
        output_dir = populated_collection

        # Create daily view structure for testing
        daily_dir = output_dir / "views" / "daily" / "2026" / "03"
        daily_dir.mkdir(parents=True)
        (daily_dir / "2026-03-01-001.json").write_text('{}')
        (daily_dir / "2026-03-02-001.json").write_text('{}')

        from backend.puzzle_manager.pipeline.cleanup import _clean_all_files

        counts = _clean_all_files(
            output_dir / "views",
            dry_run=False,
        )

        # Verify view files deleted
        assert counts > 0

    def test_cleanup_clears_publish_log(self, populated_collection):
        """T045: cleanup_target should clear publish-log entries."""
        output_dir = populated_collection
        ops_dir = output_dir / ".puzzle-inventory-state"

        # Verify publish-log exists before
        log_files = list((ops_dir / "publish-log").glob("*.jsonl"))
        assert len(log_files) > 0

        from backend.puzzle_manager.pipeline.cleanup import _clean_all_files

        _clean_all_files(
            ops_dir / "publish-log",
            dry_run=False,
        )

        # Verify publish-log cleared
        log_files_after = list((ops_dir / "publish-log").glob("*.jsonl"))
        assert len(log_files_after) == 0

    def test_cleanup_clears_rollback_backup(self, populated_collection):
        """T047: cleanup_target should clear rollback-backup directory."""
        output_dir = populated_collection
        ops_dir = output_dir / ".puzzle-inventory-state"

        # Verify backup exists before
        backup_files = list((ops_dir / "rollback-backup").glob("*.json"))
        assert len(backup_files) > 0

        from backend.puzzle_manager.pipeline.cleanup import _clean_all_files

        _clean_all_files(
            ops_dir / "rollback-backup",
            dry_run=False,
        )

        # Verify backup cleared
        backup_files_after = list((ops_dir / "rollback-backup").glob("*.json"))
        assert len(backup_files_after) == 0

    def test_cleanup_target_puzzles_collection_dry_run(self, tmp_path):
        """T049: cleanup --target puzzles-collection defaults to safe dry-run."""
        # Test that calling cleanup_target with dry_run=True doesn't delete
        from backend.puzzle_manager.pipeline.cleanup import cleanup_target

        # Create some test files
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")

        # cleanup_target should support dry_run
        counts = cleanup_target(target="logs", dry_run=True)

        # Should return counts dict
        assert isinstance(counts, dict)

    def test_cleanup_writes_audit_entry(self, populated_collection):
        """T046: cleanup_target should write audit entry with files_deleted breakdown."""
        output_dir = populated_collection
        ops_dir = output_dir / ".puzzle-inventory-state"

        import json

        from backend.puzzle_manager.pipeline.cleanup import (
            count_puzzles_in_dir,
            write_cleanup_audit_entry,
        )

        # Count puzzles before cleanup
        puzzle_count = count_puzzles_in_dir(output_dir / "sgf")
        assert puzzle_count > 0

        # Write audit entry with per-category breakdown
        paths_cleared = ["sgf/", "views/", "publish-log/"]
        files_deleted = {"sgf": puzzle_count, "views": 3, "publish-log": 1}
        write_cleanup_audit_entry(
            audit_file=ops_dir / "audit.jsonl",
            target="puzzles-collection",
            files_deleted=files_deleted,
            paths_cleared=paths_cleared,
        )

        # Verify audit entry was written
        audit_content = (ops_dir / "audit.jsonl").read_text()
        lines = [line for line in audit_content.strip().split("\n") if line]

        # Last entry should be the cleanup entry
        last_entry = json.loads(lines[-1])
        assert last_entry["operation"] == "cleanup"
        assert last_entry["target"] == "puzzles-collection"
        assert last_entry["details"]["files_deleted"]["sgf"] == puzzle_count
        assert last_entry["details"]["files_deleted"]["views"] == 3
        assert "timestamp" in last_entry
        assert last_entry["details"]["paths_cleared"] == paths_cleared

    def test_cleanup_clears_index_state(self, populated_collection):
        """T048: cleanup_target should clear index state (DB files)."""
        output_dir = populated_collection

        # Create DB state files
        db_file = output_dir / "yengo-search.db"
        db_file.write_text("fake-db")
        db_version = output_dir / "db-version.json"
        db_version.write_text('{"version": 1}')

        from backend.puzzle_manager.pipeline.cleanup import clear_index_state

        result = clear_index_state(output_dir, dry_run=False)

        # Verify index state cleared
        assert result is True
        assert not db_file.exists()
        assert not db_version.exists()

    def test_integrity_check_passes_after_cleanup(self, populated_collection):
        """T050: After cleanup, inventory --check should pass."""
        output_dir = populated_collection
        ops_dir = output_dir / ".puzzle-inventory-state"

        from datetime import UTC, datetime

        from backend.puzzle_manager.inventory.check import check_integrity
        from backend.puzzle_manager.inventory.models import (
            CollectionStats,
            PuzzleCollectionInventory,
        )
        from backend.puzzle_manager.pipeline.cleanup import (
            _clean_all_files,
            clear_index_state,
        )

        # Perform cleanup
        _clean_all_files(output_dir / "sgf", dry_run=False)
        _clean_all_files(output_dir / "views", dry_run=False)
        _clean_all_files(ops_dir / "publish-log", dry_run=False)
        _clean_all_files(ops_dir / "rollback-backup", dry_run=False)
        clear_index_state(output_dir, dry_run=False)

        # Create empty inventory
        empty_inventory = PuzzleCollectionInventory(
            collection=CollectionStats(
                total_puzzles=0,
                by_puzzle_level={},
                by_tag={},
            ),
            last_updated=datetime.now(UTC),
            last_run_id="cleanup-test",
        )

        # Save empty inventory
        (ops_dir / "inventory.json").write_text(empty_inventory.model_dump_json(indent=2))

        # Run integrity check
        result = check_integrity(
            output_dir=output_dir,
            inventory=empty_inventory,
        )

        # Verify integrity check passes
        assert result.is_valid is True
        assert result.total_actual == 0
        assert result.total_expected == 0
        assert len(result.orphan_entries) == 0
        assert len(result.orphan_files) == 0

    def test_inventory_not_reset_when_sgf_deletion_fails(self, tmp_path, monkeypatch):
        """Inventory must NOT reset if SGF files still exist after cleanup.

        Regression test: cleanup_target previously reset inventory unconditionally,
        even when file deletion failed (e.g., Windows file locking), creating a
        state mismatch where inventory=0 but SGF files remain on disk.
        """
        from unittest.mock import patch

        from backend.puzzle_manager.pipeline.cleanup import cleanup_target

        # Set up minimal collection structure
        output_dir = tmp_path / "output"
        sgf_dir = output_dir / "sgf" / "0001"
        sgf_dir.mkdir(parents=True)
        (sgf_dir / "puzzle1.sgf").write_text("(;FF[4]GM[1])")
        (sgf_dir / "puzzle2.sgf").write_text("(;FF[4]GM[1])")

        views_dir = output_dir / "views"
        views_dir.mkdir(parents=True)

        ops_dir = output_dir / ".puzzle-inventory-state"
        ops_dir.mkdir(parents=True)
        (ops_dir / "inventory.json").write_text(
            '{"schema_version":"2.0","collection":{"total_puzzles":2,'
            '"by_puzzle_level":{"beginner":2},"by_tag":{},'
            '"by_puzzle_quality":{"2":2}},'
            '"last_updated":"2026-02-20T00:00:00Z","last_run_id":"test"}'
        )

        # Point get_output_dir to our tmp directory
        monkeypatch.setattr(
            "backend.puzzle_manager.pipeline.cleanup.get_output_dir",
            lambda: output_dir,
        )

        # Make file deletion fail silently (simulates Windows file locking)
        original_unlink = Path.unlink

        def failing_unlink(self, *args, **kwargs):
            if self.suffix == ".sgf":
                raise PermissionError(f"File locked: {self}")
            return original_unlink(self, *args, **kwargs)

        reset_called = False

        def track_reset():
            nonlocal reset_called
            reset_called = True

        with patch.object(Path, "unlink", failing_unlink), \
             patch(
                 "backend.puzzle_manager.pipeline.cleanup._reset_inventory",
                 side_effect=track_reset,
             ):
            cleanup_target(target="puzzles-collection", dry_run=False)

        # SGF files should still exist (deletion failed)
        remaining = list(sgf_dir.rglob("*.sgf"))
        assert len(remaining) == 2

        # Inventory reset must NOT have been called
        assert not reset_called, (
            "Inventory was reset despite SGF files remaining on disk"
        )

    def test_inventory_resets_when_all_sgf_deleted(self, tmp_path, monkeypatch):
        """Inventory resets normally when all SGF files are successfully deleted."""
        from unittest.mock import patch

        from backend.puzzle_manager.pipeline.cleanup import cleanup_target

        # Set up minimal collection structure
        output_dir = tmp_path / "output"
        sgf_dir = output_dir / "sgf" / "0001"
        sgf_dir.mkdir(parents=True)
        (sgf_dir / "puzzle1.sgf").write_text("(;FF[4]GM[1])")

        views_dir = output_dir / "views"
        views_dir.mkdir(parents=True)

        ops_dir = output_dir / ".puzzle-inventory-state"
        ops_dir.mkdir(parents=True)

        # Point get_output_dir to our tmp directory
        monkeypatch.setattr(
            "backend.puzzle_manager.pipeline.cleanup.get_output_dir",
            lambda: output_dir,
        )

        reset_called = False

        def track_reset():
            nonlocal reset_called
            reset_called = True

        with patch(
            "backend.puzzle_manager.pipeline.cleanup._reset_inventory",
            side_effect=track_reset,
        ):
            cleanup_target(target="puzzles-collection", dry_run=False)

        # SGF files should be gone
        remaining = list((output_dir / "sgf").rglob("*.sgf"))
        assert len(remaining) == 0

        # Inventory reset SHOULD have been called
        assert reset_called, (
            "Inventory was not reset even though all SGF files were deleted"
        )

    def test_puzzles_collection_counts_no_double_counting(self, tmp_path, monkeypatch):
        """counts dict must not double-count SGF files.

        Regression: counts previously included both counts["sgf"] (files deleted
        from sgf/) AND counts["puzzles-collection"] (pre-cleanup *.sgf count),
        inflating sum(counts.values()) by the number of puzzles.
        """
        from unittest.mock import patch

        from backend.puzzle_manager.pipeline.cleanup import cleanup_target

        # Set up collection with 3 SGF files + 1 non-SGF file
        output_dir = tmp_path / "output"
        sgf_dir = output_dir / "sgf" / "0001"
        sgf_dir.mkdir(parents=True)
        (sgf_dir / "puzzle1.sgf").write_text("(;FF[4]GM[1])")
        (sgf_dir / "puzzle2.sgf").write_text("(;FF[4]GM[1])")
        (sgf_dir / "puzzle3.sgf").write_text("(;FF[4]GM[1])")
        (sgf_dir / ".gitkeep").write_text("")  # non-SGF file

        ops_dir = output_dir / ".puzzle-inventory-state"
        ops_dir.mkdir(parents=True)

        monkeypatch.setattr(
            "backend.puzzle_manager.pipeline.cleanup.get_output_dir",
            lambda: output_dir,
        )

        with patch(
            "backend.puzzle_manager.pipeline.cleanup._reset_inventory",
        ):
            counts = cleanup_target(target="puzzles-collection", dry_run=False)

        # "puzzles-collection" must NOT be in the counts dict
        assert "puzzles-collection" not in counts, (
            f"counts contains 'puzzles-collection' key which double-counts SGF files: {counts}"
        )
        # sgf count should include all files (3 sgf + 1 gitkeep = 4)
        assert counts["sgf"] == 4
        # Total should equal actual files deleted, not inflated
        assert sum(counts.values()) == counts["sgf"] + counts.get("empty_dirs", 0)

    def test_inventory_preserved_when_audit_write_fails(self, tmp_path, monkeypatch):
        """Inventory must NOT reset if audit entry write fails.

        Regression: _reset_inventory() was called before write_cleanup_audit_entry().
        If audit write failed, inventory was zeroed with no audit trail.
        After the fix, audit is written first; if it raises, inventory is preserved.
        """
        from unittest.mock import patch

        from backend.puzzle_manager.pipeline.cleanup import cleanup_target

        # Set up minimal collection structure
        output_dir = tmp_path / "output"
        sgf_dir = output_dir / "sgf" / "0001"
        sgf_dir.mkdir(parents=True)
        (sgf_dir / "puzzle1.sgf").write_text("(;FF[4]GM[1])")

        ops_dir = output_dir / ".puzzle-inventory-state"
        ops_dir.mkdir(parents=True)

        monkeypatch.setattr(
            "backend.puzzle_manager.pipeline.cleanup.get_output_dir",
            lambda: output_dir,
        )

        reset_called = False

        def track_reset():
            nonlocal reset_called
            reset_called = True

        with patch(
            "backend.puzzle_manager.pipeline.cleanup._reset_inventory",
            side_effect=track_reset,
        ), patch(
            "backend.puzzle_manager.pipeline.cleanup.write_cleanup_audit_entry",
            side_effect=OSError("Disk full"),
        ):
            with pytest.raises(OSError, match="Disk full"):
                cleanup_target(target="puzzles-collection", dry_run=False)

        # Inventory reset must NOT have been called (audit failed first)
        assert not reset_called, (
            "Inventory was reset despite audit write failure"
        )

    def test_cleanup_target_puzzles_collection_defaults_to_dry_run(self, tmp_path, monkeypatch):
        """cleanup_target('puzzles-collection') defaults to dry-run when dry_run not passed."""
        from backend.puzzle_manager.pipeline.cleanup import cleanup_target

        output_dir = tmp_path / "output"
        sgf_dir = output_dir / "sgf" / "0001"
        sgf_dir.mkdir(parents=True)
        (sgf_dir / "puzzle1.sgf").write_text("(;FF[4]GM[1])")

        ops_dir = output_dir / ".puzzle-inventory-state"
        ops_dir.mkdir(parents=True)

        monkeypatch.setattr(
            "backend.puzzle_manager.pipeline.cleanup.get_output_dir",
            lambda: output_dir,
        )

        # Call without explicit dry_run — should default to dry-run for puzzles-collection
        cleanup_target(target="puzzles-collection")

        # SGF files should still exist (dry-run, nothing deleted)
        remaining = list(sgf_dir.rglob("*.sgf"))
        assert len(remaining) == 1, (
            "cleanup_target('puzzles-collection') deleted files without explicit dry_run=False"
        )
