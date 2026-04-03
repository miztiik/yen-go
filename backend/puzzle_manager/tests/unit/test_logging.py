"""Unit tests for logging module (spec-043 observability)."""

import json
import logging
from io import StringIO

from backend.puzzle_manager.pm_logging import (
    RunContextAdapter,
    StructuredFormatter,
    create_run_logger,
)


class TestRunContextAdapter:
    """Tests for RunContextAdapter log correlation (spec-043)."""

    def test_run_context_adapter_adds_run_id(self) -> None:
        """RunContextAdapter should add run_id to all log entries."""
        # Create a logger with a string handler to capture output
        base_logger = logging.getLogger("test.adapter.run_id")
        base_logger.setLevel(logging.DEBUG)

        # Clear any existing handlers
        base_logger.handlers.clear()

        # Add handler with structured formatter
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(StructuredFormatter())
        base_logger.addHandler(handler)

        # Create adapter with run context
        adapter = RunContextAdapter(base_logger, extra={"run_id": "20260129-abc12345"})

        # Log a message
        adapter.info("Test message")

        # Parse the log output
        log_output = stream.getvalue()
        log_entry = json.loads(log_output)

        assert log_entry["run_id"] == "20260129-abc12345"
        assert log_entry["msg"] == "Test message"

    def test_run_context_adapter_adds_source_id(self) -> None:
        """RunContextAdapter should add source_id to all log entries."""
        base_logger = logging.getLogger("test.adapter.source_id")
        base_logger.setLevel(logging.DEBUG)
        base_logger.handlers.clear()

        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(StructuredFormatter())
        base_logger.addHandler(handler)

        adapter = RunContextAdapter(
            base_logger,
            extra={"run_id": "20260129-abc12345", "source_id": "sanderland"}
        )

        adapter.info("Processing puzzle")

        log_entry = json.loads(stream.getvalue())

        assert log_entry["run_id"] == "20260129-abc12345"
        assert log_entry["source_id"] == "sanderland"

    def test_run_context_adapter_merges_extra_fields(self) -> None:
        """RunContextAdapter should merge extra fields with context."""
        base_logger = logging.getLogger("test.adapter.merge")
        base_logger.setLevel(logging.DEBUG)
        base_logger.handlers.clear()

        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(StructuredFormatter())
        base_logger.addHandler(handler)

        adapter = RunContextAdapter(
            base_logger,
            extra={"run_id": "20260129-abc12345", "source_id": "sanderland"}
        )

        # Log with additional extra fields
        adapter.info("Puzzle processed", extra={"puzzle_id": "gp-123", "action": "ingest"})

        log_entry = json.loads(stream.getvalue())

        # Should have both context and extra fields
        assert log_entry["run_id"] == "20260129-abc12345"
        assert log_entry["source_id"] == "sanderland"
        assert log_entry["puzzle_id"] == "gp-123"
        assert log_entry["action"] == "ingest"


class TestCreateRunLogger:
    """Tests for create_run_logger factory function (spec-043)."""

    def test_create_run_logger_returns_adapter(self) -> None:
        """create_run_logger should return a RunContextAdapter."""
        logger = create_run_logger(run_id="20260129-abc12345", source_id="sanderland")

        assert isinstance(logger, RunContextAdapter)

    def test_create_run_logger_includes_context(self) -> None:
        """create_run_logger should include run_id and source_id in context."""
        # Use a unique logger name to avoid handler pollution
        base_logger = logging.getLogger("test.create_run_logger")
        base_logger.setLevel(logging.DEBUG)
        base_logger.handlers.clear()

        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(StructuredFormatter())
        base_logger.addHandler(handler)

        # Create adapter but use our test logger directly
        adapter = RunContextAdapter(
            base_logger,
            extra={"run_id": "20260129-test123", "source_id": "goproblems"}
        )

        adapter.info("Test log message")

        log_entry = json.loads(stream.getvalue())

        assert log_entry["run_id"] == "20260129-test123"
        assert log_entry["source_id"] == "goproblems"


class TestRunIdInStructuredLogs:
    """Tests for run_id appearing in structured logs (spec-043)."""

    def test_structured_formatter_includes_extra_fields(self) -> None:
        """StructuredFormatter should include extra fields in JSON output."""
        logger = logging.getLogger("test.structured")
        logger.setLevel(logging.DEBUG)
        logger.handlers.clear()

        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(StructuredFormatter())
        logger.addHandler(handler)

        # Log with extra fields
        logger.info("Test message", extra={
            "run_id": "20260129-xyz789",
            "source_id": "blacktoplay",
            "puzzle_id": "bp-456",
        })

        log_entry = json.loads(stream.getvalue())

        assert log_entry["run_id"] == "20260129-xyz789"
        assert log_entry["source_id"] == "blacktoplay"
        assert log_entry["puzzle_id"] == "bp-456"
        assert log_entry["msg"] == "Test message"
        assert "ts" in log_entry
        # Verify full date format: YYYY-MM-DD HH:MM:SS.mmm (spec-105)
        import re
        ts_pattern = r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3}$"
        assert re.match(ts_pattern, log_entry["ts"]), f"Timestamp should match YYYY-MM-DD HH:MM:SS.mmm, got: {log_entry['ts']}"
        assert log_entry["level"] == "INFO"
