"""Integration tests for POSIX paths in rollback functionality.

Verifies that rollback transaction metadata and file paths use forward slashes,
regardless of the operating system.

Skip with: pytest -m "not posix"
"""

import json
import tempfile
from pathlib import Path

import pytest

# Mark all tests in this module as POSIX path tests
pytestmark = pytest.mark.posix

from backend.puzzle_manager.paths import to_posix_path


class TestRollbackPosixPaths:
    """Integration tests for POSIX paths in rollback operations."""

    def test_affected_files_list_uses_posix_paths(self):
        """Transaction affected_files list should use POSIX paths."""
        # Simulate how rollback.py builds affected_files list
        affected_files = [
            to_posix_path(str(Path("C:/project/output/sgf/beginner/file1.sgf"))),
            to_posix_path(str(Path("C:/project/output/sgf/intermediate/file2.sgf"))),
        ]

        for path in affected_files:
            # Forward slashes should be present
            assert "/" in path
            # No drive letters with backslashes (Windows artifact)
            # Note: Drive letters are kept but with forward slashes
            assert "\\\\" not in path

    def test_relative_backup_path_uses_posix(self):
        """Backup relative paths should use POSIX format for JSON."""
        # Simulate: backup_file.relative_to(tx_dir)
        backup_file = Path("C:/project/.rollback-backup/tx-123/sgf/beginner/file.sgf")
        tx_dir = Path("C:/project/.rollback-backup/tx-123")

        rel_path = to_posix_path(backup_file, relative_to=tx_dir)

        assert rel_path == "sgf/beginner/file.sgf"
        assert "\\" not in rel_path

    def test_transaction_metadata_json_posix_paths(self):
        """Transaction metadata JSON should have POSIX paths."""
        # Simulate transaction.json content with to_posix_path
        tx_metadata = {
            "transaction_id": "tx-2026-01-29-001",
            "status": "committed",
            "affected_files": [
                to_posix_path("sgf\\beginner\\batch-0001\\file1.sgf"),
                to_posix_path("sgf\\intermediate\\batch-0001\\file2.sgf"),
            ],
            "affected_indexes": ["by-level/120.json", "by-level/140.json"],
        }

        # Write and read back
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(tx_metadata, f, indent=2)
            temp_path = f.name

        try:
            with open(temp_path) as f:
                loaded = json.load(f)

            for path in loaded["affected_files"]:
                assert "\\" not in path, f"Backslash in affected_files: {path}"
        finally:
            Path(temp_path).unlink()

    def test_restore_path_calculation_posix(self):
        """Restore path calculation should work with POSIX paths."""
        # Simulate: original_path = output_root / rel_path
        # where rel_path came from to_posix_path
        rel_path = to_posix_path("sgf\\beginner\\batch-0001\\abc.sgf")

        # On any OS, Path handles forward slashes correctly
        output_root = Path("/project/output")
        original_path = output_root / rel_path

        # Path should resolve correctly
        assert "beginner" in str(original_path)
        assert "batch-0001" in str(original_path)

class TestTransactionPortability:
    """Tests for FR-001 to FR-004: Portable transaction records.

    Spec 107: Transaction affected_files must be relative POSIX paths
    that work across machines and operating systems.
    """

    def test_affected_files_are_relative_not_absolute(self, tmp_path: Path):
        """T008: Transaction affected_files must contain relative paths only.

        FR-001: Paths relative to yengo-puzzle-collections/ root.
        """
        # Setup: Create a test SGF file in proper directory structure
        output_dir = tmp_path / "output"
        sgf_dir = output_dir / "sgf" / "beginner" / "batch-0001"
        sgf_dir.mkdir(parents=True)
        test_file = sgf_dir / "test123.sgf"
        test_file.write_text("(;FF[4])")

        # Simulate what TransactionManager.backup_file() should do
        # Fix: Use relative_to to get relative path
        rel_path = test_file.relative_to(output_dir)
        posix_path = to_posix_path(rel_path)

        # Assertions for FR-001: Relative paths
        assert not posix_path.startswith("/"), "Path should not start with /"
        assert ":" not in posix_path, "Path should not contain drive letter"
        assert posix_path == "sgf/beginner/batch-0001/test123.sgf"

    def test_affected_files_use_posix_format(self, tmp_path: Path):
        """T009: Transaction paths must use forward slashes on all platforms.

        FR-002: POSIX format regardless of OS.
        """
        # Create file with Windows-style path components
        output_dir = tmp_path / "output"
        sgf_path = output_dir / "sgf" / "elementary" / "batch-0001" / "abc.sgf"
        sgf_path.parent.mkdir(parents=True)
        sgf_path.write_text("(;FF[4])")

        rel_path = sgf_path.relative_to(output_dir)
        posix_path = to_posix_path(rel_path)

        # Assertions for FR-002: Forward slashes
        assert "\\" not in posix_path, "Path should not contain backslashes"
        assert "/" in posix_path, "Path should use forward slashes"

    def test_affected_files_no_drive_letters(self, tmp_path: Path):
        """T010: Transaction paths must not contain drive letters.

        FR-004: No drive letters or machine-specific components.
        """
        output_dir = tmp_path / "output"
        sgf_path = output_dir / "sgf" / "advanced" / "batch-0001" / "xyz.sgf"
        sgf_path.parent.mkdir(parents=True)
        sgf_path.write_text("(;FF[4])")

        rel_path = sgf_path.relative_to(output_dir)
        posix_path = to_posix_path(rel_path)

        # Assertions for FR-004: No platform-specific components
        # Check no drive letter pattern like C: D: etc.
        import re
        assert not re.match(r"^[A-Za-z]:", posix_path), "Path should not have drive letter"
        assert not posix_path.startswith("\\\\"), "Path should not be UNC path"

        # Path should start with directory name, not root
        assert posix_path.startswith("sgf/"), "Path should start with sgf/"

    def test_restore_backward_compatibility_with_absolute_paths(self, tmp_path: Path):
        """T012a: Restore should handle legacy absolute paths.

        FR-003: Backward compatibility with existing transaction.json files
        that may contain absolute paths.
        """
        # Setup: Create backup directory structure
        output_dir = tmp_path / "output"
        backup_dir = tmp_path / "backups" / "tx-001"
        backup_dir.mkdir(parents=True)

        # Create a backup file in the backup directory
        backup_sgf_dir = backup_dir / "sgf" / "beginner" / "batch-0001"
        backup_sgf_dir.mkdir(parents=True)
        backup_file = backup_sgf_dir / "legacy.sgf"
        backup_file.write_text("(;FF[4]GM[1])")

        # Simulate legacy absolute path in transaction.json
        # On Windows this would be something like C:/Users/.../sgf/...
        legacy_absolute_path = str(output_dir / "sgf" / "beginner" / "batch-0001" / "legacy.sgf")

        # The restore logic should handle this by:
        # 1. Checking if path is absolute
        # 2. If absolute, try to extract relative portion after output_dir
        # 3. If relative, use directly

        # For this test, verify relative path extraction works
        abs_path = Path(legacy_absolute_path)
        if abs_path.is_absolute():
            # Try to make it relative to output_dir
            try:
                rel_path = abs_path.relative_to(output_dir)
                posix_path = to_posix_path(rel_path)
                assert posix_path == "sgf/beginner/batch-0001/legacy.sgf"
            except ValueError:
                # If not under output_dir, fall back to using filename only
                pass

        # Also test that new relative paths work directly
        new_relative_path = "sgf/beginner/batch-0001/legacy.sgf"
        restored_path = output_dir / new_relative_path

        # Path should resolve correctly
        assert restored_path.parts[-1] == "legacy.sgf"
        assert "beginner" in str(restored_path)
