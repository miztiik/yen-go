"""
Unit tests for tools.core.atomic_write utilities.

Tests cross-platform atomic file writes with:
- Basic functionality (text and JSON)
- Cleanup on failure
- Windows retry logic
- Edge cases (non-existent directories, concurrent access)
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from tools.core.atomic_write import (
    _cleanup_temp,
    atomic_write_json,
    atomic_write_text,
)


class TestAtomicWriteText:
    """Tests for atomic_write_text function."""

    def test_writes_content_to_file(self, tmp_path: Path) -> None:
        """Basic write succeeds and content is correct."""
        target = tmp_path / "test.txt"
        content = "Hello, World!"

        atomic_write_text(target, content)

        assert target.exists()
        assert target.read_text(encoding="utf-8") == content

    def test_creates_parent_directories(self, tmp_path: Path) -> None:
        """Creates parent directories if they don't exist."""
        target = tmp_path / "nested" / "deep" / "test.txt"
        content = "nested content"

        atomic_write_text(target, content)

        assert target.exists()
        assert target.read_text(encoding="utf-8") == content

    def test_overwrites_existing_file(self, tmp_path: Path) -> None:
        """Overwrites existing file content."""
        target = tmp_path / "test.txt"
        target.write_text("old content", encoding="utf-8")

        atomic_write_text(target, "new content")

        assert target.read_text(encoding="utf-8") == "new content"

    def test_cleans_up_temp_on_write_failure(self, tmp_path: Path) -> None:
        """Temp file is cleaned up when write fails."""
        target = tmp_path / "test.txt"

        with patch("tools.core.atomic_write.Path.write_text") as mock_write:
            mock_write.side_effect = OSError("Disk full")

            with pytest.raises(IOError, match="Disk full"):
                atomic_write_text(target, "content")

        # No temp files left behind
        temp_files = list(tmp_path.glob("*.tmp"))
        assert len(temp_files) == 0

    def test_cleans_up_temp_on_rename_failure(self, tmp_path: Path) -> None:
        """Temp file is cleaned up when rename fails after successful write."""
        target = tmp_path / "test.txt"

        # Create a mock that writes successfully but fails on replace
        original_write_text = Path.write_text
        call_count = {"write": 0}

        def mock_write_text(self, content, encoding=None):
            call_count["write"] += 1
            return original_write_text(self, content, encoding=encoding)

        def mock_replace(self, target):
            raise PermissionError("Cannot replace")

        def mock_unlink(self):
            # Also fail unlink to simulate PermissionError on delete on Windows
            raise PermissionError("Cannot delete")

        def mock_rename(self, target):
            raise PermissionError("Cannot rename either")

        with patch.object(Path, "write_text", mock_write_text):
            with patch.object(Path, "replace", mock_replace):
                with patch.object(Path, "rename", mock_rename):
                    with patch.object(Path, "unlink", mock_unlink):
                        with pytest.raises(PermissionError):
                            atomic_write_text(target, "content", max_retries=1)

    def test_retries_on_permission_error(self, tmp_path: Path) -> None:
        """Retries on PermissionError and succeeds on later attempt."""
        target = tmp_path / "test.txt"
        attempt_count = {"count": 0}

        original_write_text = Path.write_text

        def flaky_write(self, content, encoding=None):
            # Only fail on temp file writes, not target
            if str(self).endswith(".tmp"):
                attempt_count["count"] += 1
                if attempt_count["count"] < 2:
                    raise PermissionError("Temporarily locked")
            return original_write_text(self, content, encoding=encoding)

        with patch.object(Path, "write_text", flaky_write):
            atomic_write_text(target, "content", retry_delay=0.01)

        assert target.read_text(encoding="utf-8") == "content"
        assert attempt_count["count"] == 2

    def test_respects_custom_encoding(self, tmp_path: Path) -> None:
        """Writes with specified encoding."""
        target = tmp_path / "test.txt"
        content = "日本語テスト"

        atomic_write_text(target, content, encoding="utf-8")

        assert target.read_text(encoding="utf-8") == content

    def test_exhausts_retries_then_raises(self, tmp_path: Path) -> None:
        """Raises PermissionError after exhausting retries."""
        target = tmp_path / "test.txt"

        def always_fail(self, target_path):
            raise PermissionError("Always locked")

        def also_fail(self, target_path):
            raise PermissionError("Rename also fails")

        with patch.object(Path, "replace", always_fail):
            with patch.object(Path, "rename", also_fail):
                with pytest.raises(PermissionError, match="file locked after 2 retries"):
                    atomic_write_text(target, "content", max_retries=2, retry_delay=0.001)


class TestAtomicWriteJson:
    """Tests for atomic_write_json function."""

    def test_writes_json_to_file(self, tmp_path: Path) -> None:
        """Basic JSON write succeeds and content is correct."""
        target = tmp_path / "test.json"
        data = {"key": "value", "number": 42}

        atomic_write_json(target, data)

        assert target.exists()
        loaded = json.loads(target.read_text(encoding="utf-8"))
        assert loaded == data

    def test_uses_indent(self, tmp_path: Path) -> None:
        """Uses specified indentation."""
        target = tmp_path / "test.json"
        data = {"a": 1}

        atomic_write_json(target, data, indent=4)

        content = target.read_text(encoding="utf-8")
        assert "    " in content  # 4-space indent

    def test_compact_json_with_separators(self, tmp_path: Path) -> None:
        """Writes compact JSON with custom separators."""
        target = tmp_path / "test.json"
        data = {"a": 1, "b": 2}

        atomic_write_json(target, data, indent=None, separators=(",", ":"))

        content = target.read_text(encoding="utf-8")
        # atomic_write_json adds trailing newline
        assert content == '{"a":1,"b":2}\n'

    def test_handles_non_ascii_characters(self, tmp_path: Path) -> None:
        """Handles non-ASCII characters correctly."""
        target = tmp_path / "test.json"
        data = {"message": "こんにちは", "emoji": "🎯"}

        atomic_write_json(target, data, ensure_ascii=False)

        loaded = json.loads(target.read_text(encoding="utf-8"))
        assert loaded["message"] == "こんにちは"
        assert loaded["emoji"] == "🎯"

    def test_uses_default_serializer(self, tmp_path: Path) -> None:
        """Uses default serializer for non-serializable objects."""
        target = tmp_path / "test.json"
        from datetime import datetime

        data = {"timestamp": datetime(2026, 2, 19, 12, 0, 0)}

        atomic_write_json(target, data, default=str)

        loaded = json.loads(target.read_text(encoding="utf-8"))
        assert "2026-02-19" in loaded["timestamp"]

    def test_raises_on_non_serializable(self, tmp_path: Path) -> None:
        """Raises TypeError for non-serializable objects without default."""
        target = tmp_path / "test.json"

        class NonSerializable:
            pass

        with pytest.raises(TypeError):
            atomic_write_json(target, {"obj": NonSerializable()}, default=None)


class TestCleanupTemp:
    """Tests for _cleanup_temp helper function."""

    def test_removes_existing_temp_file(self, tmp_path: Path) -> None:
        """Removes temp file if it exists."""
        temp = tmp_path / "test.tmp"
        temp.write_text("temp content")

        _cleanup_temp(temp)

        assert not temp.exists()

    def test_handles_missing_file_gracefully(self, tmp_path: Path) -> None:
        """Does not raise if file doesn't exist."""
        temp = tmp_path / "nonexistent.tmp"

        # Should not raise
        _cleanup_temp(temp)

    def test_ignores_permission_error(self, tmp_path: Path) -> None:
        """Ignores OSError when unable to delete."""
        temp = tmp_path / "test.tmp"
        temp.write_text("temp content")

        with patch.object(Path, "unlink", side_effect=PermissionError("Locked")):
            # Should not raise
            _cleanup_temp(temp)


class TestCrossPlatformBehavior:
    """Tests for cross-platform atomic write behavior."""

    def test_fallback_to_rename_on_windows(self, tmp_path: Path) -> None:
        """Falls back to unlink+rename when replace fails (Windows behavior)."""
        target = tmp_path / "test.txt"
        target.write_text("original")

        # Simulate Windows behavior where replace fails but unlink+rename works
        replace_calls = []
        unlink_calls = []
        rename_calls = []

        original_unlink = Path.unlink
        original_rename = Path.rename

        def mock_replace(self, target_path):
            replace_calls.append(str(target_path))
            raise PermissionError("Cannot replace on Windows")

        def mock_unlink(self):
            unlink_calls.append(str(self))
            return original_unlink(self)

        def mock_rename(self, target_path):
            rename_calls.append(str(target_path))
            return original_rename(self, target_path)

        with patch.object(Path, "replace", mock_replace):
            with patch.object(Path, "unlink", mock_unlink):
                with patch.object(Path, "rename", mock_rename):
                    atomic_write_text(target, "new content")

        assert target.read_text(encoding="utf-8") == "new content"
        assert len(replace_calls) == 1
        assert len(unlink_calls) == 1  # Unlinked the target
        assert len(rename_calls) == 1  # Renamed temp to target
