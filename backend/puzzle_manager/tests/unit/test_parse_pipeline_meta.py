"""
Tests for parse_pipeline_meta() defensive parsing.

Verifies all edge cases: missing, malformed, empty, valid YM values.
"""

from backend.puzzle_manager.core.sgf_utils import unescape_sgf_value
from backend.puzzle_manager.core.trace_utils import (
    build_pipeline_meta,
    parse_pipeline_meta,
)


class TestBuildPipelineMeta:
    """Tests for build_pipeline_meta()."""

    def test_trace_id_only(self):
        """Build with trace_id only — no 'f' key in output."""
        result = build_pipeline_meta("a1b2c3d4e5f67890")
        assert result == '{"t":"a1b2c3d4e5f67890"}'

    def test_trace_id_and_filename(self):
        """Build with both trace_id and original_filename."""
        result = build_pipeline_meta("a1b2c3d4e5f67890", "puzzle_42.sgf")
        assert '"t":"a1b2c3d4e5f67890"' in result
        assert '"f":"puzzle_42.sgf"' in result

    def test_empty_filename_omitted(self):
        """Empty original_filename string should be omitted."""
        result = build_pipeline_meta("a1b2c3d4e5f67890", "")
        assert result == '{"t":"a1b2c3d4e5f67890"}'

    def test_v13_full_meta(self):
        """v13: Build with all fields (trace_id, filename, run_id)."""
        result = build_pipeline_meta("abc123", "file.sgf", run_id="20260220-abc12345")
        assert '"t":"abc123"' in result
        assert '"i":"20260220-abc12345"' in result
        assert '"f":"file.sgf"' in result
        assert '"s"' not in result  # Source not embedded in YM

    def test_v13_run_id_only(self):
        """v13: Build with run_id but no filename."""
        result = build_pipeline_meta("abc123", run_id="20260220-abc12345")
        assert '"i":"20260220-abc12345"' in result
        assert '"f"' not in result


class TestParsePipelineMeta:
    """Tests for parse_pipeline_meta() defensive parsing."""

    def test_valid_full(self):
        """Parse valid YM with all v13 fields (backward compat: old SGFs with s)."""
        trace_id, filename, source, run_id = parse_pipeline_meta(
            '{"t":"a1b2c3d4e5f67890","f":"puzzle.sgf","s":"sanderland","i":"20260220-abc12345"}'
        )
        assert trace_id == "a1b2c3d4e5f67890"
        assert filename == "puzzle.sgf"
        assert source == "sanderland"  # Old SGFs still parsed for backward compat
        assert run_id == "20260220-abc12345"

    def test_valid_without_source(self):
        """Parse YM without s key (new format)."""
        trace_id, filename, source, run_id = parse_pipeline_meta(
            '{"t":"a1b2c3d4e5f67890","f":"puzzle.sgf","i":"20260220-abc12345"}'
        )
        assert trace_id == "a1b2c3d4e5f67890"
        assert filename == "puzzle.sgf"
        assert source == ""  # No source in new YM format
        assert run_id == "20260220-abc12345"

    def test_valid_trace_only(self):
        """Parse valid YM with trace_id only."""
        trace_id, filename, source, run_id = parse_pipeline_meta('{"t":"fedcba9876543210"}')
        assert trace_id == "fedcba9876543210"
        assert filename == ""
        assert source == ""
        assert run_id == ""

    def test_none_input(self):
        """None input returns empty 4-tuple."""
        assert parse_pipeline_meta(None) == ("", "", "", "")

    def test_empty_string(self):
        """Empty string returns empty 4-tuple."""
        assert parse_pipeline_meta("") == ("", "", "", "")

    def test_malformed_json(self):
        """Malformed JSON returns empty 4-tuple (no raise)."""
        assert parse_pipeline_meta("not-json") == ("", "", "", "")

    def test_json_array(self):
        """JSON array (not object) returns empty 4-tuple."""
        assert parse_pipeline_meta("[1,2,3]") == ("", "", "", "")

    def test_missing_t_key(self):
        """Missing 't' key returns empty trace_id."""
        trace_id, filename, source, run_id = parse_pipeline_meta('{"f":"file.sgf"}')
        assert trace_id == ""
        assert filename == "file.sgf"

    def test_missing_f_key(self):
        """Missing 'f' key returns empty filename."""
        trace_id, filename, source, run_id = parse_pipeline_meta('{"t":"abc123"}')
        assert trace_id == "abc123"
        assert filename == ""

    def test_empty_object(self):
        """Empty JSON object returns empty strings."""
        assert parse_pipeline_meta("{}") == ("", "", "", "")

    def test_extra_fields_ignored(self):
        """Extra fields are harmlessly ignored."""
        trace_id, filename, source, run_id = parse_pipeline_meta(
            '{"t":"abc","f":"file.sgf","extra":"ignored"}'
        )
        assert trace_id == "abc"
        assert filename == "file.sgf"


class TestRoundtrip:
    """Test build → parse round-trip."""

    def test_roundtrip_with_filename(self):
        """Build then parse recovers original values."""
        meta = build_pipeline_meta("a1b2c3d4e5f67890", "puzzle.sgf")
        trace_id, filename, source, run_id = parse_pipeline_meta(meta)
        assert trace_id == "a1b2c3d4e5f67890"
        assert filename == "puzzle.sgf"

    def test_roundtrip_without_filename(self):
        """Build then parse without filename."""
        meta = build_pipeline_meta("fedcba9876543210")
        trace_id, filename, source, run_id = parse_pipeline_meta(meta)
        assert trace_id == "fedcba9876543210"
        assert filename == ""

    def test_roundtrip_sgf_special_chars_in_filename(self):
        """Filenames with SGF-special ] char survive round-trip."""
        meta = build_pipeline_meta("a1b2c3d4e5f67890", "file]name.sgf")
        trace_id, filename, source, run_id = parse_pipeline_meta(meta)
        assert trace_id == "a1b2c3d4e5f67890"
        assert filename == "file]name.sgf"

    def test_roundtrip_v13_full(self):
        """v13: Full round-trip with run_id (source not in YM)."""
        meta = build_pipeline_meta("abc123", "file.sgf", run_id="20260220-abc12345")
        trace_id, filename, source, run_id = parse_pipeline_meta(meta)
        assert trace_id == "abc123"
        assert filename == "file.sgf"
        assert source == ""  # Source not embedded in YM
        assert run_id == "20260220-abc12345"

    def test_parse_sgf_escaped_input(self):
        """Simulate SGF parser output — escaped \\] from an SGF property value."""
        # The SGF parser preserves \] in parsed values when ] appears inside brackets
        sgf_escaped = '{"t":"abc","f":"file\\]name.sgf"}'
        trace_id, filename, source, run_id = parse_pipeline_meta(sgf_escaped)
        assert trace_id == "abc"
        assert filename == "file]name.sgf"


class TestUnescapeSgfValue:
    """Tests for unescape_sgf_value() (P1-6 coverage)."""

    def test_unescape_bracket(self):
        """Escaped bracket is unescaped."""
        assert unescape_sgf_value("test\\]value") == "test]value"

    def test_unescape_backslash(self):
        """Escaped backslash is unescaped."""
        assert unescape_sgf_value("test\\\\value") == "test\\value"

    def test_unescape_both(self):
        """Both bracket and backslash escape sequences."""
        assert unescape_sgf_value("a\\\\b\\]c") == "a\\b]c"

    def test_unescape_empty(self):
        """Empty string passes through."""
        assert unescape_sgf_value("") == ""

    def test_unescape_no_escapes(self):
        """String without escape sequences passes through."""
        assert unescape_sgf_value("plain text") == "plain text"

    def test_unescape_multiple_brackets(self):
        """Multiple escaped brackets."""
        assert unescape_sgf_value("a\\]b\\]c") == "a]b]c"
