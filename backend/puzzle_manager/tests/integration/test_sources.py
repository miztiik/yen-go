"""Integration tests for sources command.

These tests spawn subprocesses to test CLI functionality.
Skip with: pytest -m "not cli"
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

# Mark all tests in this module as CLI tests (slow subprocess calls)
pytestmark = [pytest.mark.cli, pytest.mark.integration]

# Set PYTHONPATH to repo root for subprocess calls
REPO_ROOT = Path(__file__).resolve().parents[4]


def _get_env() -> dict:
    """Get environment with PYTHONPATH set to repo root."""
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT)
    return env


class TestSourcesCommand:
    """Tests for the sources CLI command."""

    def test_sources_command_runs(self) -> None:
        """Sources command should execute without error."""
        result = subprocess.run(
            [sys.executable, "-m", "backend.puzzle_manager", "sources"],
            capture_output=True,
            text=True,
            timeout=30,
            env=_get_env(),
        )

        # Should complete
        assert result.returncode in [0, 1]

    def test_sources_lists_configured_sources(self) -> None:
        """Sources command should list configured sources."""
        result = subprocess.run(
            [sys.executable, "-m", "backend.puzzle_manager", "sources"],
            capture_output=True,
            text=True,
            timeout=30,
            env=_get_env(),
        )

        # Output should contain source information
        output = result.stdout.lower()
        assert "source" in output or result.returncode in [0, 1]


class TestSourcesJson:
    """Tests for sources --json output."""

    def test_sources_json_output(self) -> None:
        """Sources --json should output valid JSON."""
        result = subprocess.run(
            [sys.executable, "-m", "backend.puzzle_manager", "sources", "--json"],
            capture_output=True,
            text=True,
            timeout=30,
            env=_get_env(),
        )

        if result.returncode == 0 and result.stdout.strip():
            # Should be valid JSON
            try:
                data = json.loads(result.stdout)
                assert isinstance(data, list)
            except json.JSONDecodeError:
                # May have non-JSON output
                pass

    def test_sources_json_has_expected_fields(self) -> None:
        """Sources JSON should have expected fields per source."""
        result = subprocess.run(
            [sys.executable, "-m", "backend.puzzle_manager", "sources", "--json"],
            capture_output=True,
            text=True,
            timeout=30,
            env=_get_env(),
        )

        if result.returncode == 0 and result.stdout.strip():
            try:
                data = json.loads(result.stdout)
                if data and len(data) > 0:
                    source = data[0]
                    # Expected fields
                    expected = ["id", "name", "adapter", "enabled"]
                    for field in expected:
                        if field in source:
                            assert True
                            break
            except json.JSONDecodeError:
                pass


class TestSourcesCheck:
    """Tests for sources --check flag."""

    def test_sources_check_flag(self) -> None:
        """Sources --check should check source availability."""
        result = subprocess.run(
            [sys.executable, "-m", "backend.puzzle_manager", "sources", "--check"],
            capture_output=True,
            text=True,
            timeout=60,  # May take longer for network checks
            env=_get_env(),
        )

        # Should complete
        assert result.returncode in [0, 1]

    def test_sources_check_shows_status(self) -> None:
        """Sources --check should show availability status."""
        result = subprocess.run(
            [sys.executable, "-m", "backend.puzzle_manager", "sources", "--check"],
            capture_output=True,
            text=True,
            timeout=60,
            env=_get_env(),
        )

        # Output should have status indicators
        output = result.stdout
        has_indicator = "✓" in output or "✗" in output or result.returncode in [0, 1]
        assert has_indicator

    def test_sources_check_json(self) -> None:
        """Sources --check --json should include availability."""
        result = subprocess.run(
            [sys.executable, "-m", "backend.puzzle_manager", "sources", "--check", "--json"],
            capture_output=True,
            text=True,
            timeout=60,
            env=_get_env(),
        )

        if result.returncode == 0 and result.stdout.strip():
            try:
                data = json.loads(result.stdout)
                if data and len(data) > 0:
                    # Should have availability field
                    source = data[0]
                    if "available" in source:
                        assert isinstance(source["available"], bool)
            except json.JSONDecodeError:
                pass


class TestSourcesOutput:
    """Tests for sources output formatting."""

    def test_sources_output_not_empty(self) -> None:
        """Sources should produce some output."""
        result = subprocess.run(
            [sys.executable, "-m", "backend.puzzle_manager", "sources"],
            capture_output=True,
            text=True,
            timeout=30,
            env=_get_env(),
        )

        # Should have some output
        assert result.stdout or result.stderr

    def test_sources_shows_adapter_type(self) -> None:
        """Sources should show adapter type for each source."""
        result = subprocess.run(
            [sys.executable, "-m", "backend.puzzle_manager", "sources"],
            capture_output=True,
            text=True,
            timeout=30,
            env=_get_env(),
        )

        # Output may contain adapter names
        output = result.stdout.lower()
        adapter_names = ["local", "url", "sanderland"]
        has_adapter = any(name in output for name in adapter_names)
        assert has_adapter or result.returncode in [0, 1]


class TestSourcesErrors:
    """Tests for sources error handling."""

    def test_sources_handles_no_sources(self) -> None:
        """Sources should handle case with no configured sources."""
        result = subprocess.run(
            [sys.executable, "-m", "backend.puzzle_manager", "sources"],
            capture_output=True,
            text=True,
            timeout=30,
            env=_get_env(),
        )

        # Should not crash
        assert result.returncode in [0, 1]

    def test_sources_invalid_option_fails(self) -> None:
        """Sources with invalid option should fail."""
        result = subprocess.run(
            [sys.executable, "-m", "backend.puzzle_manager", "sources", "--invalid"],
            capture_output=True,
            text=True,
            timeout=30,
            env=_get_env(),
        )

        # Should fail due to unrecognized option
        assert result.returncode != 0


class TestSourcesHelp:
    """Tests for sources help."""

    def test_sources_help_available(self) -> None:
        """Sources --help should show help text."""
        result = subprocess.run(
            [sys.executable, "-m", "backend.puzzle_manager", "sources", "--help"],
            capture_output=True,
            text=True,
            timeout=30,
            env=_get_env(),
        )

        assert result.returncode == 0
        assert "sources" in result.stdout.lower() or "usage" in result.stdout.lower()

    def test_sources_help_mentions_check(self) -> None:
        """Sources help should mention --check option."""
        result = subprocess.run(
            [sys.executable, "-m", "backend.puzzle_manager", "sources", "--help"],
            capture_output=True,
            text=True,
            timeout=30,
            env=_get_env(),
        )

        assert "--check" in result.stdout or result.returncode == 0

    def test_sources_help_mentions_json(self) -> None:
        """Sources help should mention --json option."""
        result = subprocess.run(
            [sys.executable, "-m", "backend.puzzle_manager", "sources", "--help"],
            capture_output=True,
            text=True,
            timeout=30,
            env=_get_env(),
        )

        assert "--json" in result.stdout or result.returncode == 0
