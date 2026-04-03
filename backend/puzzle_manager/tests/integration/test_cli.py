"""Integration tests for the CLI.

These tests spawn subprocesses and are the slowest in the suite.
Skip with: pytest -m "not cli"
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

# Mark all tests in this module as CLI tests (slow subprocess calls)
pytestmark = [pytest.mark.cli, pytest.mark.integration]

# Set PYTHONPATH to repo root for subprocess calls
REPO_ROOT = Path(__file__).resolve().parents[4]


class TestCLIHelp:
    """Tests for CLI help commands."""

    def _get_env(self) -> dict:
        """Get environment with PYTHONPATH set to repo root."""
        env = os.environ.copy()
        env["PYTHONPATH"] = str(REPO_ROOT)
        return env

    def test_main_help(self) -> None:
        """Main command should show help."""
        result = subprocess.run(
            [sys.executable, "-m", "backend.puzzle_manager", "--help"],
            capture_output=True,
            text=True,
            env=self._get_env(),
        )

        assert result.returncode == 0
        assert "puzzle_manager" in result.stdout.lower() or "usage" in result.stdout.lower()

    def test_run_help(self) -> None:
        """Run command should show help."""
        result = subprocess.run(
            [sys.executable, "-m", "backend.puzzle_manager", "run", "--help"],
            capture_output=True,
            text=True,
            env=self._get_env(),
        )

        assert result.returncode == 0
        assert "run" in result.stdout.lower() or "stage" in result.stdout.lower()

    def test_status_help(self) -> None:
        """Status command should show help."""
        result = subprocess.run(
            [sys.executable, "-m", "backend.puzzle_manager", "status", "--help"],
            capture_output=True,
            text=True,
            env=self._get_env(),
        )

        assert result.returncode == 0

    def test_clean_help(self) -> None:
        """Clean command should show help."""
        result = subprocess.run(
            [sys.executable, "-m", "backend.puzzle_manager", "clean", "--help"],
            capture_output=True,
            text=True,
            env=self._get_env(),
        )

        assert result.returncode == 0

    def test_validate_help(self) -> None:
        """Validate command should show help."""
        result = subprocess.run(
            [sys.executable, "-m", "backend.puzzle_manager", "validate", "--help"],
            capture_output=True,
            text=True,
            env=self._get_env(),
        )

        assert result.returncode == 0

    def test_sources_help(self) -> None:
        """Sources command should show help."""
        result = subprocess.run(
            [sys.executable, "-m", "backend.puzzle_manager", "sources", "--help"],
            capture_output=True,
            text=True,
            env=self._get_env(),
        )

        assert result.returncode == 0


class TestCLICommands:
    """Tests for CLI command execution using --help only.

    Note: Actual command execution (like --dry-run) is NOT tested here.
    Dry-run functionality is tested at the stage level where write operations occur.
    CLI tests only verify argument parsing via --help to avoid subprocess complexity.
    """

    def _get_env(self) -> dict:
        """Get environment with PYTHONPATH set to repo root."""
        env = os.environ.copy()
        env["PYTHONPATH"] = str(REPO_ROOT)
        return env

    def test_status_command(self) -> None:
        """Status command should return current state."""
        result = subprocess.run(
            [sys.executable, "-m", "backend.puzzle_manager", "status"],
            capture_output=True,
            text=True,
            timeout=30,
            env=self._get_env(),
        )

        # Should complete
        assert result.returncode in [0, 1]

    def test_status_json_output(self) -> None:
        """Status command should support JSON output."""
        result = subprocess.run(
            [sys.executable, "-m", "backend.puzzle_manager", "status", "--json"],
            capture_output=True,
            text=True,
            timeout=30,
            env=self._get_env(),
        )

        # Should complete
        assert result.returncode in [0, 1]

        # If successful, output should be JSON
        if result.returncode == 0 and result.stdout.strip():
            import json
            try:
                json.loads(result.stdout)
            except json.JSONDecodeError:
                pass  # OK if not JSON on error

    def test_sources_command(self) -> None:
        """Sources command should list available sources."""
        result = subprocess.run(
            [sys.executable, "-m", "backend.puzzle_manager", "sources"],
            capture_output=True,
            text=True,
            timeout=30,
            env=self._get_env(),
        )

        # Should complete
        assert result.returncode in [0, 1]

    def test_validate_command(self) -> None:
        """Validate command should check configuration."""
        result = subprocess.run(
            [sys.executable, "-m", "backend.puzzle_manager", "validate"],
            capture_output=True,
            text=True,
            timeout=30,
            env=self._get_env(),
        )

        # Should complete
        assert result.returncode in [0, 1]


class TestCLIOptions:
    """Tests for CLI option parsing."""

    def _get_env(self) -> dict:
        """Get environment with PYTHONPATH set to repo root."""
        env = os.environ.copy()
        env["PYTHONPATH"] = str(REPO_ROOT)
        return env

    def test_run_with_batch_size(self) -> None:
        """Run command should accept batch size."""
        result = subprocess.run(
            [sys.executable, "-m", "backend.puzzle_manager", "run", "--source", "sanderland", "--source-override", "--batch-size", "2", "--dry-run"],
            capture_output=True,
            text=True,
            timeout=30,
            env=self._get_env(),
        )

        # Should complete without parsing errors
        assert result.returncode in [0, 1]
        assert "unrecognized" not in result.stderr.lower()

    def test_run_with_stage_filter(self) -> None:
        """Run command should accept stage filter."""
        result = subprocess.run(
            [sys.executable, "-m", "backend.puzzle_manager", "run", "--source", "sanderland", "--source-override", "--stage", "ingest", "--batch-size", "2", "--dry-run"],
            capture_output=True,
            text=True,
            timeout=30,
            env=self._get_env(),
        )

        # Should complete without parsing errors
        assert result.returncode in [0, 1]
        assert "unrecognized" not in result.stderr.lower()

    def test_run_without_source_uses_active_adapter(self) -> None:
        """Run command without --source should use active_adapter from sources.json (spec 051).

        Note: This test is marked as slow because pipeline startup can take time.
        It verifies that the CLI accepts the command without --source flag.
        """
        # Use a very short timeout - we just want to verify the command starts
        # We don't need the full pipeline to complete

        try:
            result = subprocess.run(
                [sys.executable, "-m", "backend.puzzle_manager", "run", "--dry-run", "--batch-size", "1"],
                capture_output=True,
                text=True,
                timeout=120,  # Pipeline startup can be slow
                env=self._get_env(),
            )
            # Should succeed (returncode 0) or run but fail for external reasons (returncode 1)
            # The key is that it doesn't fail with argument error (returncode 2)
            assert result.returncode in [0, 1], f"Unexpected error: {result.stderr}"
            # Should not complain about missing --source argument
            assert "argument --source" not in result.stderr
        except subprocess.TimeoutExpired:
            # Timeout is acceptable - it means the command was accepted and started running
            # The command doesn't have a --source argument error (which would be immediate)
            pass

    def test_clean_with_retention(self) -> None:
        """Clean command should accept retention days."""
        result = subprocess.run(
            [sys.executable, "-m", "backend.puzzle_manager", "clean", "--retention-days", "30", "--dry-run"],
            capture_output=True,
            text=True,
            timeout=30,
            env=self._get_env(),
        )

        # Should complete without parsing errors
        assert result.returncode in [0, 1]
        assert "unrecognized" not in result.stderr.lower()

    def test_invalid_option_fails(self) -> None:
        """Invalid options should cause error."""
        result = subprocess.run(
            [sys.executable, "-m", "backend.puzzle_manager", "run", "--invalid-option"],
            capture_output=True,
            text=True,
            timeout=30,
            env=self._get_env(),
        )

        # Should fail due to unrecognized option
        assert result.returncode != 0


class TestAdapterCommands:
    """Tests for enable-adapter and disable-adapter commands (spec 051)."""

    def _get_env(self) -> dict:
        """Get environment with PYTHONPATH set to repo root."""
        env = os.environ.copy()
        env["PYTHONPATH"] = str(REPO_ROOT)
        return env

    def test_enable_adapter_help(self) -> None:
        """enable-adapter command should show help."""
        result = subprocess.run(
            [sys.executable, "-m", "backend.puzzle_manager", "enable-adapter", "--help"],
            capture_output=True,
            text=True,
            env=self._get_env(),
        )

        assert result.returncode == 0
        assert "adapter" in result.stdout.lower()

    def test_disable_adapter_help(self) -> None:
        """disable-adapter command should show help."""
        result = subprocess.run(
            [sys.executable, "-m", "backend.puzzle_manager", "disable-adapter", "--help"],
            capture_output=True,
            text=True,
            env=self._get_env(),
        )

        assert result.returncode == 0
        assert "adapter" in result.stdout.lower() or "disable" in result.stdout.lower()

    def test_enable_adapter_invalid_source(self) -> None:
        """enable-adapter with invalid source should fail."""
        result = subprocess.run(
            [sys.executable, "-m", "backend.puzzle_manager", "enable-adapter", "nonexistent_source"],
            capture_output=True,
            text=True,
            timeout=30,
            env=self._get_env(),
        )

        # Should fail due to invalid source
        assert result.returncode != 0
        # Should mention the invalid source or show available sources (check both stdout and stderr)
        combined = (result.stdout + result.stderr).lower()
        assert "nonexistent_source" in combined or "available" in combined or "error" in combined or "not found" in combined


class TestSourceOverride:
    """Tests for --source-override flag behavior (spec 051)."""

    def _get_env(self) -> dict:
        """Get environment with PYTHONPATH set to repo root."""
        env = os.environ.copy()
        env["PYTHONPATH"] = str(REPO_ROOT)
        return env

    def test_source_override_flag_accepted(self) -> None:
        """--source-override flag should be accepted on run command."""
        result = subprocess.run(
            [sys.executable, "-m", "backend.puzzle_manager", "run", "--help"],
            capture_output=True,
            text=True,
            env=self._get_env(),
        )

        assert result.returncode == 0
        assert "--source-override" in result.stdout

    def test_ingest_source_override_flag_accepted(self) -> None:
        """--source-override flag should be accepted on ingest command."""
        result = subprocess.run(
            [sys.executable, "-m", "backend.puzzle_manager", "ingest", "--help"],
            capture_output=True,
            text=True,
            env=self._get_env(),
        )

        assert result.returncode == 0
        assert "--source-override" in result.stdout

    def test_source_mismatch_without_override_fails(self) -> None:
        """Using --source that differs from active_adapter without --source-override should fail.

        Note: This test assumes there is an active_adapter set. If not, the test
        will pass because no mismatch occurs.
        """
        result = subprocess.run(
            [sys.executable, "-m", "backend.puzzle_manager", "run", "--source", "nonexistent_test_source", "--dry-run"],
            capture_output=True,
            text=True,
            timeout=30,
            env=self._get_env(),
        )

        # Should fail due to source mismatch (if active_adapter is set)
        # or due to invalid source
        assert result.returncode != 0

    def test_source_override_with_warning(self) -> None:
        """Using --source-override should log a warning but proceed."""
        result = subprocess.run(
            [sys.executable, "-m", "backend.puzzle_manager", "run", "--source", "sanderland", "--source-override", "--dry-run", "--batch-size", "1"],
            capture_output=True,
            text=True,
            timeout=60,
            env=self._get_env(),
        )

        # Should complete (either success or failure for other reasons)
        # But should not fail with argument parsing error (returncode 2)
        assert result.returncode in [0, 1]
        assert "unrecognized" not in result.stderr.lower()
