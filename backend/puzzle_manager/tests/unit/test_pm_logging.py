"""
Unit tests for trace-aware logging.

Tests for create_trace_logger and trace_id in log output.
Spec 110: Per-file trace ID for end-to-end observability.
"""

import json
import logging

import pytest

from backend.puzzle_manager.pm_logging import (
    RunContextAdapter,
    StageFormatter,
    create_run_logger,
    create_trace_logger,
)


class TestRunContextAdapter:
    """Tests for RunContextAdapter with trace_id support."""

    def test_adapter_includes_run_context(self) -> None:
        """Test adapter includes run_id and source_id in log extra."""
        logger = logging.getLogger("test.run_context")
        adapter = RunContextAdapter(
            logger,
            extra={"run_id": "run_001", "source_id": "sanderland"},
        )

        # Process should add extra fields
        msg, kwargs = adapter.process("test message", {})

        assert kwargs["extra"]["run_id"] == "run_001"
        assert kwargs["extra"]["source_id"] == "sanderland"

    def test_adapter_includes_trace_id(self) -> None:
        """Test adapter includes trace_id when provided."""
        logger = logging.getLogger("test.trace_context")
        adapter = RunContextAdapter(
            logger,
            extra={
                "run_id": "run_001",
                "source_id": "sanderland",
                "trace_id": "a1b2c3d4e5f67890",
            },
        )

        msg, kwargs = adapter.process("test message", {})

        assert kwargs["extra"]["trace_id"] == "a1b2c3d4e5f67890"

    def test_adapter_merges_extra_fields(self) -> None:
        """Test adapter merges existing extra fields."""
        logger = logging.getLogger("test.merge")
        adapter = RunContextAdapter(
            logger,
            extra={"run_id": "run_001", "source_id": "test"},
        )

        # Call with existing extra
        msg, kwargs = adapter.process(
            "test",
            {"extra": {"puzzle_id": "abc123"}},
        )

        # Should have both context and passed extra
        assert kwargs["extra"]["run_id"] == "run_001"
        assert kwargs["extra"]["puzzle_id"] == "abc123"


class TestCreateTraceLogger:
    """Tests for create_trace_logger factory function."""

    def test_creates_adapter_with_trace_id(self) -> None:
        """Test factory creates adapter with all context fields."""
        logger = create_trace_logger(
            run_id="20260129-abc12345",
            source_id="sanderland",
            trace_id="a1b2c3d4e5f67890",
        )

        assert isinstance(logger, RunContextAdapter)
        assert logger.extra["run_id"] == "20260129-abc12345"
        assert logger.extra["source_id"] == "sanderland"
        assert logger.extra["trace_id"] == "a1b2c3d4e5f67890"

    def test_trace_logger_logs_with_context(self, caplog: pytest.LogCaptureFixture) -> None:
        """Test trace logger includes context in log records."""
        logger = create_trace_logger(
            run_id="run_001",
            source_id="ogs",
            trace_id="1234567890abcdef",
        )

        with caplog.at_level(logging.INFO):
            logger.info("Processing file")

        # Check the log record has extra fields
        assert len(caplog.records) == 1
        record = caplog.records[0]
        assert record.run_id == "run_001"  # type: ignore
        assert record.source_id == "ogs"  # type: ignore
        assert record.trace_id == "1234567890abcdef"  # type: ignore


class TestTraceIdInFormattedOutput:
    """Tests for trace_id appearing in formatted log output."""

    def test_stage_formatter_includes_trace_id(self) -> None:
        """Test StageFormatter includes trace_id in JSON output."""
        formatter = StageFormatter()

        # Create a log record with trace_id in extra
        record = logging.LogRecord(
            name="puzzle_manager.pipeline",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Processing file",
            args=(),
            exc_info=None,
        )
        record.run_id = "run_001"  # type: ignore
        record.source_id = "sanderland"  # type: ignore
        record.trace_id = "a1b2c3d4e5f67890"  # type: ignore

        output = formatter.format(record)
        data = json.loads(output)

        assert data["trace_id"] == "a1b2c3d4e5f67890"
        assert data["run_id"] == "run_001"
        assert data["source_id"] == "sanderland"
        assert data["msg"] == "Processing file"

    def test_trace_id_absent_when_not_provided(self) -> None:
        """Test trace_id is absent when not in the record."""
        formatter = StageFormatter()

        record = logging.LogRecord(
            name="puzzle_manager.pipeline",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="No trace context",
            args=(),
            exc_info=None,
        )
        record.run_id = "run_001"  # type: ignore
        record.source_id = "sanderland"  # type: ignore

        output = formatter.format(record)
        data = json.loads(output)

        assert "trace_id" not in data
        assert data["run_id"] == "run_001"


class TestCreateRunLoggerBackwardCompat:
    """Tests for backward compatibility with create_run_logger."""

    def test_run_logger_still_works(self) -> None:
        """Test create_run_logger still works without trace_id."""
        logger = create_run_logger(
            run_id="20260129-abc12345",
            source_id="sanderland",
        )

        assert isinstance(logger, RunContextAdapter)
        assert logger.extra["run_id"] == "20260129-abc12345"
        assert logger.extra["source_id"] == "sanderland"
        assert "trace_id" not in logger.extra

    def test_run_logger_logs_without_trace_id(self, caplog: pytest.LogCaptureFixture) -> None:
        """Test run logger works without trace_id."""
        logger = create_run_logger(
            run_id="run_001",
            source_id="ogs",
        )

        with caplog.at_level(logging.INFO):
            logger.info("Processing batch")

        assert len(caplog.records) == 1
        record = caplog.records[0]
        assert record.run_id == "run_001"  # type: ignore
        assert record.source_id == "ogs"  # type: ignore
        assert not hasattr(record, "trace_id") or record.trace_id is None  # type: ignore
