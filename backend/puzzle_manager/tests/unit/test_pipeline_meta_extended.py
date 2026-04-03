"""
Unit tests for extended pipeline metadata (PipelineMeta, build_pipeline_meta with ct/tc).

Tests the extensions to trace_utils: content_type, trivial_capture
fields in YM property.
"""

import json

import pytest

from backend.puzzle_manager.core.trace_utils import (
    PipelineMeta,
    build_pipeline_meta,
    parse_pipeline_meta_extended,
)


class TestBuildPipelineMetaExtended:
    """Tests for build_pipeline_meta with extended kwargs."""

    def test_content_type_included(self):
        """Content type should appear as 'ct' in JSON output."""
        result = build_pipeline_meta("abcdef0123456789", content_type=1)
        data = json.loads(result)
        assert data["ct"] == 1

    def test_trivial_capture_included(self):
        """Trivial capture should appear as 'tc' in JSON output."""
        result = build_pipeline_meta("abcdef0123456789", trivial_capture=True)
        data = json.loads(result)
        assert data["tc"] is True

    def test_trivial_capture_false_omitted(self):
        """Trivial capture=False should be omitted from JSON (compact)."""
        result = build_pipeline_meta("abcdef0123456789", trivial_capture=False)
        data = json.loads(result)
        assert "tc" not in data

    def test_content_type_none_omitted(self):
        """Content type=None should be omitted from JSON."""
        result = build_pipeline_meta("abcdef0123456789", content_type=None)
        data = json.loads(result)
        assert "ct" not in data

    def test_all_fields_round_trip(self):
        """All extended fields should survive build → parse round-trip."""
        ym = build_pipeline_meta(
            "abcdef0123456789",
            original_filename="test.sgf",
            run_id="20260220-abc12345",
            content_type=2,
            trivial_capture=True,
        )
        meta = parse_pipeline_meta_extended(ym)
        assert meta.trace_id == "abcdef0123456789"
        assert meta.original_filename == "test.sgf"
        assert meta.run_id == "20260220-abc12345"
        assert meta.content_type == 2
        assert meta.trivial_capture is True

    def test_backward_compat_no_new_fields(self):
        """YM without new fields should parse with defaults."""
        ym = build_pipeline_meta("abcdef0123456789")
        meta = parse_pipeline_meta_extended(ym)
        assert meta.content_type is None
        assert meta.trivial_capture is False


class TestParsePipelineMetaExtended:
    """Tests for parse_pipeline_meta_extended function."""

    def test_none_input(self):
        """None input should return default PipelineMeta."""
        meta = parse_pipeline_meta_extended(None)
        assert meta.trace_id == ""
        assert meta.content_type is None

    def test_empty_string_input(self):
        """Empty string should return default PipelineMeta."""
        meta = parse_pipeline_meta_extended("")
        assert meta.trace_id == ""

    def test_invalid_json_returns_default(self):
        """Invalid JSON should return default PipelineMeta without raising."""
        meta = parse_pipeline_meta_extended("not json at all")
        assert meta.trace_id == ""

    def test_non_object_json_returns_default(self):
        """JSON array should return default PipelineMeta."""
        meta = parse_pipeline_meta_extended("[1, 2, 3]")
        assert meta.trace_id == ""

    def test_content_type_parsed_as_int(self):
        """Content type should be parsed as int even if stored as string."""
        ym = '{"t":"abc","ct":"2"}'
        meta = parse_pipeline_meta_extended(ym)
        assert meta.content_type == 2

    def test_legacy_ym_backward_compat(self):
        """Old-format YM without fp/ct/tc should still parse correctly."""
        ym = '{"t":"abcdef0123456789","f":"old.sgf","i":"20260101-deadbeef"}'
        meta = parse_pipeline_meta_extended(ym)
        assert meta.trace_id == "abcdef0123456789"
        assert meta.original_filename == "old.sgf"
        assert meta.run_id == "20260101-deadbeef"
        assert meta.content_type is None
        assert meta.trivial_capture is False


class TestPipelineMetaDataclass:
    """Tests for PipelineMeta frozen dataclass."""

    def test_frozen(self):
        """PipelineMeta should be immutable."""
        meta = PipelineMeta(trace_id="abc")
        with pytest.raises(AttributeError):
            meta.trace_id = "xyz"  # type: ignore[misc]

    def test_default_values(self):
        """Default values should be sensible."""
        meta = PipelineMeta()
        assert meta.trace_id == ""
        assert meta.original_filename == ""
        assert meta.source == ""
        assert meta.run_id == ""
        assert meta.content_type is None
        assert meta.trivial_capture is False
