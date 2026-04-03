"""Unit tests for path utilities.

Tests to_posix_path() utility function for cross-platform path normalization.
Also tests runtime directory functions like get_pm_raw_dir().
"""

from pathlib import Path, PurePosixPath

import pytest

from backend.puzzle_manager.paths import get_pm_raw_dir, get_runtime_dir, to_posix_path


class TestToPosixPath:
    """Tests for to_posix_path() utility function."""

    # === Basic functionality ===

    def test_path_object_posix_style(self):
        """Path with forward slashes remains unchanged."""
        path = PurePosixPath("a/b/c")
        result = to_posix_path(path)
        assert result == "a/b/c"

    def test_path_object_native(self):
        """Native Path object converts correctly."""
        path = Path("a") / "b" / "c"
        result = to_posix_path(path)
        assert result == "a/b/c"

    def test_string_with_forward_slashes(self):
        """String with forward slashes passes through."""
        result = to_posix_path("a/b/c")
        assert result == "a/b/c"

    def test_string_with_backslashes(self):
        """String with backslashes converts to forward slashes."""
        result = to_posix_path("a\\b\\c")
        assert result == "a/b/c"

    def test_string_with_mixed_slashes(self):
        """String with mixed slashes normalizes to forward slashes."""
        result = to_posix_path("a\\b/c\\d")
        assert result == "a/b/c/d"

    # === Edge cases ===

    def test_empty_string(self):
        """Empty string returns empty string."""
        result = to_posix_path("")
        assert result == ""

    def test_none_raises_type_error(self):
        """None input raises TypeError."""
        with pytest.raises(TypeError, match="path cannot be None"):
            to_posix_path(None)  # type: ignore

    def test_idempotent_path_object(self):
        """Calling twice produces same result (Path object)."""
        path = Path("a") / "b" / "c"
        first = to_posix_path(path)
        second = to_posix_path(first)  # Pass result string back in
        assert first == second == "a/b/c"

    def test_idempotent_string(self):
        """Calling twice produces same result (string input)."""
        original = "a\\b\\c"
        first = to_posix_path(original)
        second = to_posix_path(first)  # Pass result back in
        assert first == second == "a/b/c"

    # === relative_to parameter ===

    def test_relative_to_valid(self):
        """Valid relative_to computes relative path."""
        path = Path("/root/sub/file.txt")
        base = Path("/root")
        result = to_posix_path(path, relative_to=base)
        assert result == "sub/file.txt"

    def test_relative_to_invalid_raises_value_error(self):
        """Invalid relative_to raises ValueError."""
        path = Path("/other/sub/file.txt")
        base = Path("/root")
        with pytest.raises(ValueError):
            to_posix_path(path, relative_to=base)

    def test_relative_to_same_path(self):
        """Relative to same path returns '.'."""
        path = Path("/root")
        result = to_posix_path(path, relative_to=path)
        assert result == "."

    def test_relative_to_with_nested_path(self):
        """Nested relative path works correctly."""
        path = Path("/project/output/sgf/beginner/2026/01/file.sgf")
        base = Path("/project/output")
        result = to_posix_path(path, relative_to=base)
        assert result == "sgf/beginner/2026/01/file.sgf"

    # === Windows-specific paths (simulated) ===

    def test_windows_path_string(self):
        """Windows-style path string converts correctly."""
        # Simulates what str(Path) produces on Windows
        windows_path = "sgf\\beginner\\2026\\01\\batch-001\\abc123.sgf"
        result = to_posix_path(windows_path)
        assert result == "sgf/beginner/2026/01/batch-001/abc123.sgf"

    def test_windows_absolute_path_string(self):
        """Windows absolute path string converts correctly."""
        windows_path = "C:\\Users\\test\\project\\file.txt"
        result = to_posix_path(windows_path)
        assert result == "C:/Users/test/project/file.txt"

    # === Real-world scenarios from spec ===

    def test_publish_path_scenario(self):
        """Test scenario from publish.py - relative path for JSON index."""
        # Simulates: output_path.relative_to(output_root) on Windows
        output_path = Path("C:/project/yengo-puzzle-collections/sgf/beginner/2026/01/batch-001/abc.sgf")
        output_root = Path("C:/project/yengo-puzzle-collections")
        result = to_posix_path(output_path, relative_to=output_root)
        assert result == "sgf/beginner/2026/01/batch-001/abc.sgf"
        assert "\\" not in result  # No backslashes

    def test_daily_puzzle_ref_scenario(self):
        """Test scenario from daily/standard.py - puzzle path from index."""
        # Path read from JSON might have backslashes if generated on Windows
        puzzle_path = "sgf\\intermediate\\2026\\01\\batch-002\\xyz789.sgf"
        result = to_posix_path(puzzle_path)
        assert result == "sgf/intermediate/2026/01/batch-002/xyz789.sgf"


class TestGetPmRawDir:
    """Tests for get_pm_raw_dir() function."""

    def test_returns_path_under_runtime_dir(self):
        """Raw directory is under runtime directory."""
        raw_dir = get_pm_raw_dir()
        runtime_dir = get_runtime_dir()
        assert raw_dir.parent == runtime_dir
        assert raw_dir.name == "raw"

    def test_returns_path_object(self):
        """Returns a Path object, not string."""
        raw_dir = get_pm_raw_dir()
        assert isinstance(raw_dir, Path)

    def test_path_ends_with_raw(self):
        """Path ends with 'raw' directory name."""
        raw_dir = get_pm_raw_dir()
        assert raw_dir.name == "raw"
        assert str(raw_dir).endswith("raw") or str(raw_dir).endswith("raw/") or str(raw_dir).endswith("raw\\")

    def test_consistent_with_other_runtime_dirs(self):
        """Raw dir follows same pattern as staging dir."""
        from backend.puzzle_manager.paths import get_pm_staging_dir

        raw_dir = get_pm_raw_dir()
        staging_dir = get_pm_staging_dir()

        # Both should be siblings under runtime_dir
        assert raw_dir.parent == staging_dir.parent
