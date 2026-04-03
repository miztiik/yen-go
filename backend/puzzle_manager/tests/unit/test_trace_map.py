"""
Unit tests for core.trace_map module.

Tests the flat JSON trace map that replaces the heavy trace registry.
File: .pm-runtime/staging/.trace-map-{run_id}.json
Lifecycle: Written by ingest, read by analyze/publish, deleted after publish.
"""

import json
from pathlib import Path

from backend.puzzle_manager.core.trace_map import (
    delete_original_filenames_map,
    delete_trace_map,
    read_original_filenames_map,
    read_trace_map,
    write_original_filenames_map,
    write_trace_map,
)


class TestWriteTraceMap:
    """Tests for write_trace_map()."""

    def test_write_creates_file(self, tmp_path: Path) -> None:
        """write_trace_map creates .trace-map-{run_id}.json."""
        mapping = {"puzzle_001": "abcd1234abcd1234", "puzzle_002": "ef56ef56ef56ef56"}
        result = write_trace_map(tmp_path, "run-001", mapping)
        assert result.exists()
        assert result.name == ".trace-map-run-001.json"

    def test_write_content_is_valid_json(self, tmp_path: Path) -> None:
        """Written file contains valid JSON with correct mapping."""
        mapping = {"src_a": "trace_aaa", "src_b": "trace_bbb"}
        path = write_trace_map(tmp_path, "run-002", mapping)
        loaded = json.loads(path.read_text(encoding="utf-8"))
        assert loaded == mapping

    def test_write_empty_mapping_no_file(self, tmp_path: Path) -> None:
        """Writing empty mapping does not create a file."""
        result = write_trace_map(tmp_path, "run-empty", {})
        assert not result.exists()

    def test_write_creates_staging_dir(self, tmp_path: Path) -> None:
        """write_trace_map creates staging_dir if it doesn't exist."""
        staging = tmp_path / "nonexistent" / "staging"
        path = write_trace_map(staging, "run-mkdir", {"a": "b"})
        assert path.exists()

    def test_write_overwrites_existing(self, tmp_path: Path) -> None:
        """Writing again overwrites the previous trace map."""
        write_trace_map(tmp_path, "run-ow", {"old": "data"})
        write_trace_map(tmp_path, "run-ow", {"new": "data"})
        loaded = json.loads((tmp_path / ".trace-map-run-ow.json").read_text())
        assert loaded == {"new": "data"}

    def test_write_uses_compact_json(self, tmp_path: Path) -> None:
        """Written JSON uses compact separators (no spaces)."""
        path = write_trace_map(tmp_path, "run-compact", {"k": "v"})
        content = path.read_text(encoding="utf-8")
        assert " " not in content  # No extra whitespace


class TestReadTraceMap:
    """Tests for read_trace_map()."""

    def test_read_returns_written_mapping(self, tmp_path: Path) -> None:
        """read_trace_map returns the mapping that was written."""
        mapping = {"puzzle_x": "trace_x", "puzzle_y": "trace_y"}
        write_trace_map(tmp_path, "run-read", mapping)
        result = read_trace_map(tmp_path, "run-read")
        assert result == mapping

    def test_read_missing_file_returns_empty_dict(self, tmp_path: Path) -> None:
        """read_trace_map returns {} when file doesn't exist (backward compat)."""
        result = read_trace_map(tmp_path, "run-nonexistent")
        assert result == {}

    def test_read_corrupted_json_returns_empty_dict(self, tmp_path: Path) -> None:
        """read_trace_map returns {} for corrupted JSON files."""
        bad_file = tmp_path / ".trace-map-run-bad.json"
        bad_file.write_text("not valid json{{{", encoding="utf-8")
        result = read_trace_map(tmp_path, "run-bad")
        assert result == {}

    def test_read_different_run_ids_are_isolated(self, tmp_path: Path) -> None:
        """Each run_id has its own trace map file."""
        write_trace_map(tmp_path, "run-a", {"a": "trace_a"})
        write_trace_map(tmp_path, "run-b", {"b": "trace_b"})
        assert read_trace_map(tmp_path, "run-a") == {"a": "trace_a"}
        assert read_trace_map(tmp_path, "run-b") == {"b": "trace_b"}


class TestDeleteTraceMap:
    """Tests for delete_trace_map()."""

    def test_delete_existing_file(self, tmp_path: Path) -> None:
        """delete_trace_map removes the file and returns True."""
        write_trace_map(tmp_path, "run-del", {"k": "v"})
        assert delete_trace_map(tmp_path, "run-del") is True
        assert not (tmp_path / ".trace-map-run-del.json").exists()

    def test_delete_missing_file_returns_false(self, tmp_path: Path) -> None:
        """delete_trace_map returns False when file doesn't exist."""
        assert delete_trace_map(tmp_path, "run-nope") is False

    def test_read_after_delete_returns_empty(self, tmp_path: Path) -> None:
        """After deletion, read returns empty dict."""
        write_trace_map(tmp_path, "run-cycle", {"k": "v"})
        delete_trace_map(tmp_path, "run-cycle")
        assert read_trace_map(tmp_path, "run-cycle") == {}


class TestTraceMapScale:
    """Test trace map at realistic scale."""

    def test_roundtrip_1000_entries(self, tmp_path: Path) -> None:
        """1000-entry trace map serializes and deserializes correctly."""
        mapping = {f"puzzle_{i:04d}": f"{i:016x}" for i in range(1000)}
        write_trace_map(tmp_path, "run-scale", mapping)
        loaded = read_trace_map(tmp_path, "run-scale")
        assert loaded == mapping
        assert len(loaded) == 1000


# --- Original Filenames Map Tests ---


class TestWriteOriginalFilenamesMap:
    """Tests for write_original_filenames_map()."""

    def test_write_creates_file(self, tmp_path: Path) -> None:
        """write_original_filenames_map creates .original-filenames-{run_id}.json."""
        mapping = {"puzzle_001": "45.sgf", "puzzle_002": "life-death-99.sgf"}
        result = write_original_filenames_map(tmp_path, "run-001", mapping)
        assert result.exists()
        assert result.name == ".original-filenames-run-001.json"

    def test_write_empty_mapping_no_file(self, tmp_path: Path) -> None:
        """Writing empty mapping does not create a file."""
        result = write_original_filenames_map(tmp_path, "run-empty", {})
        assert not result.exists()

    def test_write_content_is_valid_json(self, tmp_path: Path) -> None:
        """Written file contains valid JSON with correct mapping."""
        import json
        mapping = {"src_a": "original_a.sgf", "src_b": "original_b.sgf"}
        path = write_original_filenames_map(tmp_path, "run-002", mapping)
        loaded = json.loads(path.read_text(encoding="utf-8"))
        assert loaded == mapping


class TestReadOriginalFilenamesMap:
    """Tests for read_original_filenames_map()."""

    def test_read_returns_written_mapping(self, tmp_path: Path) -> None:
        """read_original_filenames_map returns the mapping that was written."""
        mapping = {"puzzle_x": "42.sgf", "puzzle_y": "ladder-15.sgf"}
        write_original_filenames_map(tmp_path, "run-read", mapping)
        result = read_original_filenames_map(tmp_path, "run-read")
        assert result == mapping

    def test_read_missing_file_returns_empty_dict(self, tmp_path: Path) -> None:
        """read_original_filenames_map returns {} when file doesn't exist."""
        result = read_original_filenames_map(tmp_path, "run-nonexistent")
        assert result == {}

    def test_read_corrupted_json_returns_empty_dict(self, tmp_path: Path) -> None:
        """read_original_filenames_map returns {} for corrupted JSON files."""
        bad_file = tmp_path / ".original-filenames-run-bad.json"
        bad_file.write_text("not valid json{{{", encoding="utf-8")
        result = read_original_filenames_map(tmp_path, "run-bad")
        assert result == {}


class TestDeleteOriginalFilenamesMap:
    """Tests for delete_original_filenames_map()."""

    def test_delete_existing_file(self, tmp_path: Path) -> None:
        """delete_original_filenames_map removes the file and returns True."""
        write_original_filenames_map(tmp_path, "run-del", {"k": "v.sgf"})
        assert delete_original_filenames_map(tmp_path, "run-del") is True
        assert not (tmp_path / ".original-filenames-run-del.json").exists()

    def test_delete_missing_file_returns_false(self, tmp_path: Path) -> None:
        """delete_original_filenames_map returns False when file doesn't exist."""
        assert delete_original_filenames_map(tmp_path, "run-nope") is False

    def test_read_after_delete_returns_empty(self, tmp_path: Path) -> None:
        """Reading after delete returns empty dict."""
        write_original_filenames_map(tmp_path, "run-del2", {"k": "v.sgf"})
        delete_original_filenames_map(tmp_path, "run-del2")
        assert read_original_filenames_map(tmp_path, "run-del2") == {}
