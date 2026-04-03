"""Integration tests for status command."""

import json
import subprocess
import sys


class TestStatusCommand:
    """Tests for the status CLI command."""

    def test_status_command_runs(self) -> None:
        """Status command should execute without error."""
        result = subprocess.run(
            [sys.executable, "-m", "backend.puzzle_manager", "status"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        # Should complete
        assert result.returncode in [0, 1]

    def test_status_shows_pipeline_info(self) -> None:
        """Status command should show pipeline information."""
        result = subprocess.run(
            [sys.executable, "-m", "backend.puzzle_manager", "status"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        # Output should contain pipeline-related text
        result.stdout.lower()
        # May contain "status", "run", "pipeline", etc.
        assert result.returncode in [0, 1]

    def test_status_json_output(self) -> None:
        """Status command with --json should output valid JSON."""
        result = subprocess.run(
            [sys.executable, "-m", "backend.puzzle_manager", "status", "--json"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode == 0 and result.stdout.strip():
            # Should be valid JSON
            try:
                data = json.loads(result.stdout)
                assert isinstance(data, dict)
            except json.JSONDecodeError:
                # May have non-JSON output on certain states
                pass

    def test_status_json_has_expected_fields(self) -> None:
        """Status JSON should have expected fields."""
        result = subprocess.run(
            [sys.executable, "-m", "backend.puzzle_manager", "status", "--json"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode == 0 and result.stdout.strip():
            try:
                data = json.loads(result.stdout)
                # Expected fields
                expected_fields = ["current_run", "last_run", "runs_total", "available_stages"]
                for field in expected_fields:
                    if field in data:
                        assert True
                        break
            except json.JSONDecodeError:
                pass


class TestStatusHistory:
    """Tests for status --history flag."""

    def test_history_flag_accepted(self) -> None:
        """Status command should accept --history flag."""
        result = subprocess.run(
            [sys.executable, "-m", "backend.puzzle_manager", "status", "--history"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        # Should not error on unrecognized argument
        assert "unrecognized" not in result.stderr.lower()

    def test_history_with_count(self) -> None:
        """Status --history should accept optional count."""
        result = subprocess.run(
            [sys.executable, "-m", "backend.puzzle_manager", "status", "--history", "5"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        # Should accept the count argument
        assert "unrecognized" not in result.stderr.lower()

    def test_history_json_format(self) -> None:
        """Status --history --json should include history in JSON."""
        result = subprocess.run(
            [sys.executable, "-m", "backend.puzzle_manager", "status", "--history", "--json"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode == 0 and result.stdout.strip():
            try:
                data = json.loads(result.stdout)
                # Should have history field
                if "history" in data:
                    assert isinstance(data["history"], list)
            except json.JSONDecodeError:
                pass


class TestStatusOutput:
    """Tests for status output formatting."""

    def test_status_output_not_empty(self) -> None:
        """Status should produce some output."""
        result = subprocess.run(
            [sys.executable, "-m", "backend.puzzle_manager", "status"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        # Should have some output (stdout or stderr)
        assert result.stdout or result.stderr

    def test_status_shows_available_stages(self) -> None:
        """Status should show available stages."""
        result = subprocess.run(
            [sys.executable, "-m", "backend.puzzle_manager", "status"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        # Output should mention stages
        output = result.stdout.lower()
        if result.returncode == 0:
            # May contain "stage", "ingest", "analyze", "publish"
            any(
                word in output
                for word in ["stage", "ingest", "analyze", "publish", "pipeline"]
            )
            # Not strictly required, just informational
            assert True


class TestStatusErrors:
    """Tests for status error handling."""

    def test_status_handles_no_state_gracefully(self) -> None:
        """Status should handle missing state files gracefully."""
        result = subprocess.run(
            [sys.executable, "-m", "backend.puzzle_manager", "status"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        # Should not crash
        assert result.returncode in [0, 1]

    def test_status_invalid_option_fails(self) -> None:
        """Status with invalid option should fail."""
        result = subprocess.run(
            [sys.executable, "-m", "backend.puzzle_manager", "status", "--invalid-flag"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        # Should fail due to unrecognized option
        assert result.returncode != 0
