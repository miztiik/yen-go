"""Tests for centralized structured logging (log_config module).

Covers:
  - JSON formatter output shape
  - Human-readable formatter
  - RunIdFilter injection
  - ErrorToInfoFilter mirroring
  - setup_logging() configuration
  - set_run_id() / get_run_id() lifecycle
  - Verbose mode (DEBUG level, tracebacks)
  - File handler creation and rotation
  - .gitignore creation in log dir
  - LOG_LEVEL / LOG_FORMAT env var overrides
"""

from __future__ import annotations

import json
import logging
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

# Ensure puzzle-enrichment-lab root is importable
from log_config import (
    _DEFAULT_LOG_DIR,
    _ensure_gitignore,
    _ErrorToInfoFilter,
    _HumanReadableFormatter,
    _RunIdFilter,
    _StructuredJsonFormatter,
    _TraceIdFilter,
    clear_trace_context,
    get_run_id,
    log_with_context,
    set_run_id,
    set_trace_context,
    setup_logging,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_record(
    msg: str = "test message",
    level: int = logging.INFO,
    name: str = "test_logger",
    **kwargs,
) -> logging.LogRecord:
    """Create a LogRecord for formatter/filter testing."""
    record = logging.LogRecord(
        name=name,
        level=level,
        pathname="test.py",
        lineno=1,
        msg=msg,
        args=(),
        exc_info=None,
    )
    for k, v in kwargs.items():
        setattr(record, k, v)
    return record


# ---------------------------------------------------------------------------
# _StructuredJsonFormatter
# ---------------------------------------------------------------------------


class TestStructuredJsonFormatter:
    """JSON formatter emits single-line JSON with required fields."""

    def test_basic_fields(self):
        fmt = _StructuredJsonFormatter()
        record = _make_record("hello world", run_id="20260302-abc12345")
        output = fmt.format(record)
        payload = json.loads(output)

        assert payload["msg"] == "hello world"
        assert payload["level"] == "INFO"
        assert payload["logger"] == "test_logger"
        assert payload["run_id"] == "20260302-abc12345"
        assert "ts" in payload

    def test_extra_fields_propagated(self):
        fmt = _StructuredJsonFormatter()
        record = _make_record(
            "enriched",
            puzzle_id="YENGO-abc123",
            stage="analyze",
            collection="cho-elementary",
        )
        output = fmt.format(record)
        payload = json.loads(output)

        assert payload["puzzle_id"] == "YENGO-abc123"
        assert payload["stage"] == "analyze"
        assert payload["collection"] == "cho-elementary"

    def test_missing_extras_excluded(self):
        fmt = _StructuredJsonFormatter()
        record = _make_record("plain")
        output = fmt.format(record)
        payload = json.loads(output)

        assert "puzzle_id" not in payload
        assert "stage" not in payload

    def test_output_is_single_line(self):
        fmt = _StructuredJsonFormatter()
        record = _make_record("no newlines")
        output = fmt.format(record)
        assert "\n" not in output

    def test_exception_info_summary(self):
        """Exception type and message always appear."""
        fmt = _StructuredJsonFormatter()
        try:
            raise ValueError("test error")
        except ValueError:
            record = _make_record("fail", level=logging.ERROR)
            record.exc_info = sys.exc_info()

        output = fmt.format(record)
        payload = json.loads(output)
        assert payload["exc_type"] == "ValueError"
        assert payload["exc_msg"] == "test error"


# ---------------------------------------------------------------------------
# _HumanReadableFormatter
# ---------------------------------------------------------------------------


class TestHumanReadableFormatter:
    """Human formatter produces a concise, non-JSON line."""

    def test_format_contains_level_and_message(self):
        fmt = _HumanReadableFormatter()
        record = _make_record("readable output")
        output = fmt.format(record)

        assert "INFO" in output
        assert "readable output" in output

    def test_not_json(self):
        fmt = _HumanReadableFormatter()
        record = _make_record("not json")
        output = fmt.format(record)

        with pytest.raises(json.JSONDecodeError):
            json.loads(output)


# ---------------------------------------------------------------------------
# _RunIdFilter
# ---------------------------------------------------------------------------


class TestRunIdFilter:
    """RunIdFilter injects run_id into records."""

    def test_injects_run_id(self):
        set_run_id("20260302-deadbeef")
        f = _RunIdFilter()
        record = _make_record("msg")

        assert f.filter(record) is True
        assert record.run_id == "20260302-deadbeef"  # type: ignore[attr-defined]

    def test_does_not_overwrite_existing_run_id(self):
        set_run_id("global-id")
        f = _RunIdFilter()
        record = _make_record("msg", run_id="explicit-id")

        f.filter(record)
        assert record.run_id == "explicit-id"  # type: ignore[attr-defined]

    def teardown_method(self):
        set_run_id("")


# ---------------------------------------------------------------------------
# _TraceIdFilter
# ---------------------------------------------------------------------------


class TestTraceIdFilter:
    """TraceIdFilter injects trace_id and puzzle_id into records."""

    def test_injects_trace_id(self):
        set_trace_context(trace_id="abc123", puzzle_id="YENGO-test")
        f = _TraceIdFilter()
        record = _make_record("msg")

        assert f.filter(record) is True
        assert record.trace_id == "abc123"  # type: ignore[attr-defined]
        assert record.puzzle_id == "YENGO-test"  # type: ignore[attr-defined]

    def test_does_not_overwrite_existing_trace_id(self):
        set_trace_context(trace_id="global-trace", puzzle_id="global-puzzle")
        f = _TraceIdFilter()
        record = _make_record("msg", trace_id="explicit-trace", puzzle_id="explicit-puzzle")

        f.filter(record)
        assert record.trace_id == "explicit-trace"  # type: ignore[attr-defined]
        assert record.puzzle_id == "explicit-puzzle"  # type: ignore[attr-defined]

    def test_empty_when_not_set(self):
        clear_trace_context()
        f = _TraceIdFilter()
        record = _make_record("msg")

        f.filter(record)
        assert record.trace_id == ""  # type: ignore[attr-defined]
        assert record.puzzle_id == ""  # type: ignore[attr-defined]

    def teardown_method(self):
        clear_trace_context()


# ---------------------------------------------------------------------------
# _ErrorToInfoFilter
# ---------------------------------------------------------------------------


class TestErrorToInfoFilter:
    """ErrorToInfoFilter mirrors ERROR+ at INFO level."""

    def setup_method(self):
        _ErrorToInfoFilter._seen.clear()

    def test_error_passes_through(self):
        f = _ErrorToInfoFilter()
        record = _make_record("error msg", level=logging.ERROR)
        assert f.filter(record) is True

    def test_info_passes_through_without_mirroring(self):
        f = _ErrorToInfoFilter()
        record = _make_record("info msg", level=logging.INFO)
        assert f.filter(record) is True

    def test_dedup_prevents_infinite_loop(self):
        """Same record object is only mirrored once."""
        f = _ErrorToInfoFilter()
        record = _make_record("error msg", level=logging.ERROR)
        f.filter(record)
        # Second call with same record should not re-mirror
        f.filter(record)
        # No assertion needed — if infinite loop occurred, test would hang

    def teardown_method(self):
        _ErrorToInfoFilter._seen.clear()


# ---------------------------------------------------------------------------
# set_run_id / get_run_id
# ---------------------------------------------------------------------------


class TestRunIdLifecycle:
    """Run ID can be set and retrieved."""

    def test_set_and_get(self):
        set_run_id("20260302-a1b2c3d4")
        assert get_run_id() == "20260302-a1b2c3d4"

    def test_empty_by_default(self):
        set_run_id("")
        assert get_run_id() == ""

    def teardown_method(self):
        set_run_id("")


# ---------------------------------------------------------------------------
# set_trace_context / clear_trace_context
# ---------------------------------------------------------------------------


class TestTraceContextLifecycle:
    """Trace context can be set and cleared."""

    def test_set_and_clear(self):
        set_trace_context(trace_id="t1", puzzle_id="p1")
        f = _TraceIdFilter()
        record = _make_record("msg")
        f.filter(record)
        assert record.trace_id == "t1"  # type: ignore[attr-defined]
        assert record.puzzle_id == "p1"  # type: ignore[attr-defined]

        clear_trace_context()
        record2 = _make_record("msg2")
        f.filter(record2)
        assert record2.trace_id == ""  # type: ignore[attr-defined]
        assert record2.puzzle_id == ""  # type: ignore[attr-defined]

    def teardown_method(self):
        clear_trace_context()


# ---------------------------------------------------------------------------
# setup_logging()
# ---------------------------------------------------------------------------


class TestSetupLogging:
    """setup_logging() configures root logger correctly."""

    def teardown_method(self):
        """Clean up root logger handlers after each test."""
        root = logging.getLogger()
        for h in root.handlers[:]:
            root.removeHandler(h)
            h.close()
        root.setLevel(logging.WARNING)
        set_run_id("")

    def test_returns_root_logger(self, tmp_path):
        result = setup_logging(log_dir=tmp_path)
        assert result is logging.getLogger()

    def test_default_log_dir_is_lab_runtime(self):
        assert _DEFAULT_LOG_DIR.as_posix().endswith(".lab-runtime/logs")

    def test_sets_info_level_by_default(self, tmp_path):
        setup_logging(log_dir=tmp_path)
        assert logging.getLogger().level == logging.INFO

    def test_verbose_sets_debug_level(self, tmp_path):
        setup_logging(verbose=True, log_dir=tmp_path)
        assert logging.getLogger().level == logging.DEBUG

    def test_creates_stderr_handler(self, tmp_path):
        setup_logging(log_dir=tmp_path)
        root = logging.getLogger()
        stream_handlers = [
            h for h in root.handlers
            if isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler)
        ]
        assert len(stream_handlers) >= 1

    def test_creates_file_handler(self, tmp_path):
        setup_logging(log_dir=tmp_path)
        root = logging.getLogger()
        file_handlers = [
            h for h in root.handlers
            if isinstance(h, logging.FileHandler)
        ]
        assert len(file_handlers) >= 1
        assert (tmp_path / "enrichment.log").exists()

    def test_run_id_propagated(self, tmp_path):
        setup_logging(run_id="test-run-001", log_dir=tmp_path)
        assert get_run_id() == "test-run-001"

    def test_env_log_level_override(self, tmp_path):
        with patch.dict(os.environ, {"LOG_LEVEL": "DEBUG"}):
            setup_logging(log_dir=tmp_path)
            assert logging.getLogger().level == logging.DEBUG

    def test_env_log_format_override(self, tmp_path):
        with patch.dict(os.environ, {"LOG_FORMAT": "human"}):
            setup_logging(log_dir=tmp_path)
            root = logging.getLogger()
            stream_handlers = [
                h for h in root.handlers
                if isinstance(h, logging.StreamHandler)
                and not isinstance(h, logging.FileHandler)
            ]
            assert len(stream_handlers) >= 1
            assert isinstance(stream_handlers[0].formatter, _HumanReadableFormatter)

    def test_no_duplicate_handlers_on_repeated_calls(self, tmp_path):
        setup_logging(log_dir=tmp_path)
        handler_count_1 = len(logging.getLogger().handlers)
        setup_logging(log_dir=tmp_path)
        handler_count_2 = len(logging.getLogger().handlers)
        assert handler_count_2 == handler_count_1

    def test_human_console_format(self, tmp_path):
        setup_logging(log_dir=tmp_path, console_format="human")
        root = logging.getLogger()
        stream_handlers = [
            h for h in root.handlers
            if isinstance(h, logging.StreamHandler)
            and not isinstance(h, logging.FileHandler)
        ]
        assert isinstance(stream_handlers[0].formatter, _HumanReadableFormatter)


# ---------------------------------------------------------------------------
# _ensure_gitignore
# ---------------------------------------------------------------------------


class TestEnsureGitignore:
    """Gitignore file is created in log directory."""

    def test_creates_gitignore(self, tmp_path):
        _ensure_gitignore(tmp_path)
        gi = tmp_path / ".gitignore"
        assert gi.exists()
        content = gi.read_text()
        assert "*" in content
        assert "!.gitignore" in content

    def test_does_not_overwrite_existing(self, tmp_path):
        gi = tmp_path / ".gitignore"
        gi.write_text("custom content")
        _ensure_gitignore(tmp_path)
        assert gi.read_text() == "custom content"


# ---------------------------------------------------------------------------
# log_with_context
# ---------------------------------------------------------------------------


class TestLogWithContext:
    """log_with_context() attaches structured extra fields."""

    def test_extra_fields_attached(self, tmp_path):
        setup_logging(log_dir=tmp_path, console_format="json")
        test_logger = logging.getLogger("test.context")

        # Capture output via a custom handler
        records: list[logging.LogRecord] = []

        class _Capture(logging.Handler):
            def emit(self, record: logging.LogRecord) -> None:
                records.append(record)

        capture = _Capture()
        test_logger.addHandler(capture)

        log_with_context(
            test_logger,
            logging.INFO,
            "puzzle processed",
            puzzle_id="YENGO-abc123",
            stage="publish",
        )

        assert len(records) >= 1
        rec = records[0]
        assert rec.puzzle_id == "YENGO-abc123"  # type: ignore[attr-defined]
        assert rec.stage == "publish"  # type: ignore[attr-defined]

        test_logger.removeHandler(capture)

    def teardown_method(self):
        root = logging.getLogger()
        for h in root.handlers[:]:
            root.removeHandler(h)
            h.close()
        set_run_id("")
        clear_trace_context()


# ---------------------------------------------------------------------------
# JSON field ordering
# ---------------------------------------------------------------------------


class TestJsonFieldOrdering:
    """JSON payload field order: ts, run_id, [puzzle_id, trace_id, stage], msg, ..., level, logger."""

    def test_level_and_logger_at_end(self):
        fmt = _StructuredJsonFormatter()
        record = _make_record("test", run_id="run-1")
        output = fmt.format(record)
        payload = json.loads(output)
        keys = list(payload.keys())

        # level and logger should be the last two fields
        assert keys[-2] == "level"
        assert keys[-1] == "logger"

    def test_ts_is_first_field(self):
        fmt = _StructuredJsonFormatter()
        record = _make_record("test")
        output = fmt.format(record)
        payload = json.loads(output)
        keys = list(payload.keys())

        assert keys[0] == "ts"

    def test_puzzle_context_fields_before_msg(self):
        fmt = _StructuredJsonFormatter()
        record = _make_record(
            "test",
            puzzle_id="YENGO-abc",
            trace_id="t1",
            stage="analyze",
        )
        output = fmt.format(record)
        payload = json.loads(output)
        keys = list(payload.keys())

        msg_idx = keys.index("msg")
        assert keys.index("puzzle_id") < msg_idx
        assert keys.index("trace_id") < msg_idx
        assert keys.index("stage") < msg_idx


# ---------------------------------------------------------------------------
# File handler writes structured JSON
# ---------------------------------------------------------------------------


class TestFileHandlerOutput:
    """Verify the log file contains valid JSON records."""

    def test_log_file_contains_json(self, tmp_path):
        run_id = "file-test-001"
        setup_logging(run_id=run_id, log_dir=tmp_path)
        # Must use puzzle_enrichment_lab.* namespace so _LabNamespaceFilter passes the record
        test_logger = logging.getLogger("puzzle_enrichment_lab.test_file_output")
        test_logger.info("file log entry")

        # Force flush
        root = logging.getLogger()
        for h in root.handlers:
            if isinstance(h, logging.FileHandler):
                h.flush()

        # Plan 010, P3.1: per-run log uses dash separator when per_run_files=True
        log_file = tmp_path / f"{run_id}-enrichment.log"
        assert log_file.exists()

        lines = log_file.read_text(encoding="utf-8").strip().splitlines()
        # Find our test message (skip the "Logging initialised" line)
        test_lines = [line for line in lines if "file log entry" in line]
        assert len(test_lines) >= 1

        payload = json.loads(test_lines[0])
        assert payload["msg"] == "file log entry"
        assert payload["run_id"] == "file-test-001"
        assert payload["logger"] == "puzzle_enrichment_lab.test_file_output"

    def teardown_method(self):
        root = logging.getLogger()
        for h in root.handlers[:]:
            root.removeHandler(h)
            h.close()
        set_run_id("")


# --- Migrated from test_sprint5_fixes.py ---


@pytest.mark.unit
class TestPerRunLogFiles:
    """P2.6: Log files should include run_id in filename when provided."""

    def test_log_with_run_id_creates_named_file(self):
        """setup_logging(run_id='test-abc') creates test-abc_enrichment.log."""
        from log_config import setup_logging

        with tempfile.TemporaryDirectory() as tmp:
            setup_logging(
                run_id="test-abc",
                verbose=False,
                console_format="human",
                log_dir=tmp,
            )
            log_file = Path(tmp) / "test-abc-enrichment.log"  # dash separator (per plan)
            assert log_file.exists(), (
                f"Expected {log_file} but found: {list(Path(tmp).iterdir())}"
            )
            # Close and remove handlers to release file locks (Windows)
            root = logging.getLogger()
            for h in root.handlers[:]:
                h.close()
                root.removeHandler(h)

    def test_log_without_run_id_uses_default(self):
        """setup_logging(run_id='') uses enrichment.log (no run_id prefix)."""
        from log_config import setup_logging

        with tempfile.TemporaryDirectory() as tmp:
            setup_logging(
                run_id="",
                verbose=False,
                console_format="human",
                log_dir=tmp,
            )
            log_file = Path(tmp) / "enrichment.log"
            assert log_file.exists(), (
                f"Expected {log_file} but found: {list(Path(tmp).iterdir())}"
            )
            root = logging.getLogger()
            for h in root.handlers[:]:
                h.close()
                root.removeHandler(h)
