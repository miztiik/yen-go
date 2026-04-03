"""Unit tests for core.fs_utils module."""

from pathlib import Path

from backend.puzzle_manager.core.fs_utils import (
    is_directory_empty,
    remove_empty_directories,
)


class TestRemoveEmptyDirectories:
    """Tests for remove_empty_directories function."""

    def test_removes_empty_directory(self, tmp_path: Path) -> None:
        """Empty directory should be removed."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        assert empty_dir.exists()
        count = remove_empty_directories(tmp_path)

        assert count == 1
        assert not empty_dir.exists()

    def test_preserves_non_empty_directory(self, tmp_path: Path) -> None:
        """Directory with files should NOT be removed."""
        dir_with_file = tmp_path / "has_file"
        dir_with_file.mkdir()
        (dir_with_file / "test.txt").write_text("content")

        count = remove_empty_directories(tmp_path)

        assert count == 0
        assert dir_with_file.exists()
        assert (dir_with_file / "test.txt").exists()

    def test_removes_nested_empty_directories(self, tmp_path: Path) -> None:
        """Nested empty directories should all be removed."""
        nested = tmp_path / "a" / "b" / "c"
        nested.mkdir(parents=True)

        count = remove_empty_directories(tmp_path)

        # All three nested directories should be removed
        assert count == 3
        assert not (tmp_path / "a").exists()

    def test_preserves_base_directory(self, tmp_path: Path) -> None:
        """Base directory itself should never be removed."""
        count = remove_empty_directories(tmp_path)

        assert count == 0
        assert tmp_path.exists()

    def test_dry_run_does_not_delete(self, tmp_path: Path) -> None:
        """Dry run should count but not delete."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        count = remove_empty_directories(tmp_path, dry_run=True)

        assert count == 1  # Would be removed
        assert empty_dir.exists()  # But still exists

    def test_handles_nonexistent_directory(self, tmp_path: Path) -> None:
        """Non-existent directory should return 0."""
        nonexistent = tmp_path / "does_not_exist"

        count = remove_empty_directories(nonexistent)

        assert count == 0

    def test_handles_file_instead_of_directory(self, tmp_path: Path) -> None:
        """Passing a file should return 0 with warning."""
        file_path = tmp_path / "file.txt"
        file_path.write_text("content")

        count = remove_empty_directories(file_path)

        assert count == 0
        assert file_path.exists()

    def test_partial_cleanup_scenario(self, tmp_path: Path) -> None:
        """Mix of empty and non-empty directories."""
        # Create structure:
        # base/
        #   empty1/
        #   empty2/nested_empty/
        #   has_file/
        #     test.txt
        #   mixed/
        #     empty_child/
        #     file.txt

        (tmp_path / "empty1").mkdir()
        (tmp_path / "empty2" / "nested_empty").mkdir(parents=True)
        (tmp_path / "has_file").mkdir()
        (tmp_path / "has_file" / "test.txt").write_text("x")
        (tmp_path / "mixed" / "empty_child").mkdir(parents=True)
        (tmp_path / "mixed" / "file.txt").write_text("x")

        count = remove_empty_directories(tmp_path)

        # empty1, empty2, nested_empty, empty_child = 4 removed
        assert count == 4
        assert not (tmp_path / "empty1").exists()
        assert not (tmp_path / "empty2").exists()
        assert (tmp_path / "has_file").exists()
        assert (tmp_path / "mixed").exists()
        assert not (tmp_path / "mixed" / "empty_child").exists()


class TestIsDirectoryEmpty:
    """Tests for is_directory_empty function."""

    def test_empty_directory_returns_true(self, tmp_path: Path) -> None:
        """Empty directory should return True."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        assert is_directory_empty(empty_dir) is True

    def test_directory_with_file_returns_false(self, tmp_path: Path) -> None:
        """Directory with file should return False."""
        dir_with_file = tmp_path / "has_file"
        dir_with_file.mkdir()
        (dir_with_file / "test.txt").write_text("content")

        assert is_directory_empty(dir_with_file) is False

    def test_directory_with_subdir_returns_false(self, tmp_path: Path) -> None:
        """Directory with subdirectory should return False."""
        parent = tmp_path / "parent"
        (parent / "child").mkdir(parents=True)

        assert is_directory_empty(parent) is False

    def test_nonexistent_returns_false(self, tmp_path: Path) -> None:
        """Non-existent path should return False."""
        nonexistent = tmp_path / "does_not_exist"

        assert is_directory_empty(nonexistent) is False

    def test_file_returns_false(self, tmp_path: Path) -> None:
        """File (not directory) should return False."""
        file_path = tmp_path / "file.txt"
        file_path.write_text("content")

        assert is_directory_empty(file_path) is False
