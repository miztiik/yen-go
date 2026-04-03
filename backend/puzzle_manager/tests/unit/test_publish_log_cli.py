"""
Unit tests for publish-log CLI commands (T043).
"""

import json
from unittest.mock import MagicMock

import pytest

from backend.puzzle_manager.cli import (
    _cmd_publish_log_list,
    _cmd_publish_log_search,
)
from backend.puzzle_manager.models.publish_log import PublishLogEntry
from backend.puzzle_manager.publish_log import PublishLogReader, PublishLogWriter


class TestPublishLogList:
    """Tests for publish-log list command (T040)."""

    @pytest.fixture
    def setup_logs(self, tmp_path):
        """Create test publish logs."""
        log_dir = tmp_path / "publish-log"
        log_dir.mkdir()

        # Write directly to files with specific dates (bypass writer's date logic)
        # Day 1: 2025-01-15
        day1_entries = []
        for i in range(3):
            entry = PublishLogEntry(
                run_id="run001",
                puzzle_id=f"puzzle-{i:03d}",
                source_id="source-a",
                path=f"sgf/test_{i}.sgf",
                quality=2,
                trace_id=f"trace-cli-{i:03d}",
                level="beginner",
            )
            day1_entries.append(entry.to_jsonl())
        (log_dir / "2025-01-15.jsonl").write_text("\n".join(day1_entries) + "\n")

        # Day 2: 2025-01-16
        day2_entries = []
        for i in range(5):
            entry = PublishLogEntry(
                run_id="run002",
                puzzle_id=f"puzzle-{i+100:03d}",
                source_id="source-b",
                path=f"sgf/test_{i+100}.sgf",
                quality=3,
                trace_id=f"trace-cli-{i+100:03d}",
                level="intermediate",
            )
            day2_entries.append(entry.to_jsonl())
        (log_dir / "2025-01-16.jsonl").write_text("\n".join(day2_entries) + "\n")

        return {"log_dir": log_dir}

    def test_list_shows_dates(self, setup_logs, capsys):
        """List command should show available dates."""
        reader = PublishLogReader(log_dir=setup_logs["log_dir"])

        args = MagicMock()
        args.date = None
        args.limit = 10

        result = _cmd_publish_log_list(args, reader)

        assert result == 0
        output = capsys.readouterr().out
        assert "2025-01-15" in output
        assert "2025-01-16" in output

    def test_list_with_date_shows_entries(self, setup_logs, capsys):
        """List with --date should show entries for that date."""
        reader = PublishLogReader(log_dir=setup_logs["log_dir"])

        args = MagicMock()
        args.date = "2025-01-15"
        args.limit = 10

        result = _cmd_publish_log_list(args, reader)

        assert result == 0
        output = capsys.readouterr().out
        assert "Entries for 2025-01-15: 3" in output
        assert "puzzle-000" in output

    def test_list_empty_returns_zero(self, tmp_path, capsys):
        """List with no logs should return 0."""
        log_dir = tmp_path / "empty-logs"
        log_dir.mkdir()
        reader = PublishLogReader(log_dir=log_dir)

        args = MagicMock()
        args.date = None
        args.limit = 10

        result = _cmd_publish_log_list(args, reader)

        assert result == 0
        assert "No publish logs found" in capsys.readouterr().out


class TestPublishLogSearch:
    """Tests for publish-log search command (T041, T042)."""

    @pytest.fixture
    def setup_logs(self, tmp_path):
        """Create test publish logs."""
        log_dir = tmp_path / "publish-log"
        log_dir.mkdir()

        writer = PublishLogWriter(log_dir=log_dir)

        entries = [
            PublishLogEntry(run_id="run001", puzzle_id="p001", source_id="source-a", path="a/1.sgf", quality=2, trace_id="t001", level="beginner"),
            PublishLogEntry(run_id="run001", puzzle_id="p002", source_id="source-a", path="a/2.sgf", quality=2, trace_id="t002", level="beginner"),
            PublishLogEntry(run_id="run002", puzzle_id="p003", source_id="source-b", path="b/1.sgf", quality=3, trace_id="t003", level="intermediate"),
            PublishLogEntry(run_id="run002", puzzle_id="p004", source_id="source-b", path="b/2.sgf", quality=3, trace_id="t004", level="intermediate"),
        ]

        for entry in entries:
            writer.write(entry)

        return {"log_dir": log_dir, "entries": entries}

    def test_search_by_run_id(self, setup_logs, capsys):
        """Search by run ID should find matching entries."""
        reader = PublishLogReader(log_dir=setup_logs["log_dir"])

        args = MagicMock()
        args.run_id = "run001"
        args.puzzle_id = None
        args.source = None
        args.trace_id = None
        args.date = None
        args.from_date = None
        args.to_date = None
        args.json = False
        args.format = "table"
        args.limit = 50

        result = _cmd_publish_log_search(args, reader)

        assert result == 0
        output = capsys.readouterr().out
        assert "Found 2 entries" in output
        assert "p001" in output
        assert "p002" in output

    def test_search_by_source(self, setup_logs, capsys):
        """Search by source should find matching entries."""
        reader = PublishLogReader(log_dir=setup_logs["log_dir"])

        args = MagicMock()
        args.run_id = None
        args.puzzle_id = None
        args.source = "source-b"
        args.trace_id = None
        args.date = None
        args.from_date = None
        args.to_date = None
        args.json = False
        args.format = "table"
        args.limit = 50

        result = _cmd_publish_log_search(args, reader)

        assert result == 0
        output = capsys.readouterr().out
        assert "Found 2 entries" in output
        assert "p003" in output
        assert "p004" in output

    def test_search_json_format(self, setup_logs, capsys):
        """Search with --json should output JSON."""
        reader = PublishLogReader(log_dir=setup_logs["log_dir"])

        args = MagicMock()
        args.run_id = "run001"
        args.puzzle_id = None
        args.source = None
        args.trace_id = None
        args.date = None
        args.from_date = None
        args.to_date = None
        args.json = True
        args.format = "table"  # --json overrides
        args.limit = 50

        result = _cmd_publish_log_search(args, reader)

        assert result == 0
        output = capsys.readouterr().out
        data = json.loads(output)
        assert len(data) == 2
        assert data[0]["puzzle_id"] == "p001"

    def test_search_jsonl_format(self, setup_logs, capsys):
        """Search with --format jsonl should output JSONL."""
        reader = PublishLogReader(log_dir=setup_logs["log_dir"])

        args = MagicMock()
        args.run_id = "run001"
        args.puzzle_id = None
        args.source = None
        args.trace_id = None
        args.date = None
        args.from_date = None
        args.to_date = None
        args.json = False
        args.format = "jsonl"
        args.limit = 50

        result = _cmd_publish_log_search(args, reader)

        assert result == 0
        output = capsys.readouterr().out
        lines = output.strip().split("\n")
        assert len(lines) == 2

        # Each line should be valid JSON
        for line in lines:
            data = json.loads(line)
            assert "puzzle_id" in data
            assert "run_id" in data

    def test_search_by_puzzle_id(self, setup_logs, capsys):
        """Search by puzzle ID should find matching entry."""
        reader = PublishLogReader(log_dir=setup_logs["log_dir"])

        args = MagicMock()
        args.run_id = None
        args.puzzle_id = "p003"
        args.source = None
        args.trace_id = None
        args.date = None
        args.from_date = None
        args.to_date = None
        args.json = False
        args.format = "table"
        args.limit = 50

        result = _cmd_publish_log_search(args, reader)

        assert result == 0
        output = capsys.readouterr().out
        assert "p003" in output
        assert "source-b" in output

    def test_search_no_criteria_shows_help(self, setup_logs, capsys):
        """Search with no criteria should show help."""
        reader = PublishLogReader(log_dir=setup_logs["log_dir"])

        args = MagicMock()
        args.run_id = None
        args.puzzle_id = None
        args.source = None
        args.trace_id = None
        args.date = None
        args.from_date = None
        args.to_date = None
        args.json = False
        args.format = "table"
        args.limit = 50

        result = _cmd_publish_log_search(args, reader)

        assert result == 0
        output = capsys.readouterr().out
        assert "Use one of" in output

    def test_search_limit_truncates(self, setup_logs, capsys):
        """Search with --limit should truncate results."""
        reader = PublishLogReader(log_dir=setup_logs["log_dir"])

        args = MagicMock()
        args.run_id = "run001"
        args.puzzle_id = None
        args.source = None
        args.trace_id = None
        args.date = None
        args.from_date = None
        args.to_date = None
        args.json = False
        args.format = "table"
        args.limit = 1  # Only show 1

        result = _cmd_publish_log_search(args, reader)

        assert result == 0
        output = capsys.readouterr().out
        assert "(truncated)" in output

    def test_search_not_found(self, setup_logs, capsys):
        """Search with no results should show message."""
        reader = PublishLogReader(log_dir=setup_logs["log_dir"])

        args = MagicMock()
        args.run_id = "nonexistent"
        args.puzzle_id = None
        args.source = None
        args.trace_id = None
        args.date = None
        args.from_date = None
        args.to_date = None
        args.json = False
        args.format = "table"
        args.limit = 50

        result = _cmd_publish_log_search(args, reader)

        assert result == 0
        output = capsys.readouterr().out
        assert "No matching entries found" in output

    def test_search_by_trace_id(self, setup_logs, capsys):
        """Search by trace ID should find matching entry."""
        reader = PublishLogReader(log_dir=setup_logs["log_dir"])

        args = MagicMock()
        args.run_id = None
        args.puzzle_id = None
        args.source = None
        args.trace_id = "t001"
        args.date = None
        args.from_date = None
        args.to_date = None
        args.json = False
        args.format = "table"
        args.limit = 50

        result = _cmd_publish_log_search(args, reader)

        assert result == 0
        output = capsys.readouterr().out
        assert "Found 1 entries" in output
        assert "p001" in output

    def test_search_by_trace_id_not_found(self, setup_logs, capsys):
        """Search by nonexistent trace ID should show no results."""
        reader = PublishLogReader(log_dir=setup_logs["log_dir"])

        args = MagicMock()
        args.run_id = None
        args.puzzle_id = None
        args.source = None
        args.trace_id = "nonexistent"
        args.date = None
        args.from_date = None
        args.to_date = None
        args.json = False
        args.format = "table"
        args.limit = 50

        result = _cmd_publish_log_search(args, reader)

        assert result == 0
        output = capsys.readouterr().out
        assert "No matching entries found" in output

    def test_search_json_includes_trace_id(self, setup_logs, capsys):
        """JSON output should include trace_id, quality, level fields."""
        reader = PublishLogReader(log_dir=setup_logs["log_dir"])

        args = MagicMock()
        args.run_id = None
        args.puzzle_id = "p001"
        args.source = None
        args.trace_id = None
        args.date = None
        args.from_date = None
        args.to_date = None
        args.json = True
        args.format = "table"
        args.limit = 50

        result = _cmd_publish_log_search(args, reader)

        assert result == 0
        output = capsys.readouterr().out
        data = json.loads(output)
        assert len(data) == 1
        assert data[0]["trace_id"] == "t001"
        assert data[0]["quality"] == 2
        assert data[0]["level"] == "beginner"

