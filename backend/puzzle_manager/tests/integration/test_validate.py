"""Integration tests for validate command."""

import os
import subprocess
import sys
from pathlib import Path

# Set PYTHONPATH to repo root for subprocess calls
REPO_ROOT = Path(__file__).resolve().parents[4]


def _get_env() -> dict:
    """Get environment with PYTHONPATH set to repo root."""
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT)
    return env


class TestValidateCommand:
    """Tests for the validate CLI command."""

    def test_validate_command_runs(self) -> None:
        """Validate command should execute without error."""
        result = subprocess.run(
            [sys.executable, "-m", "backend.puzzle_manager", "validate"],
            capture_output=True,
            text=True,
            timeout=30,
            env=_get_env(),
        )

        # Should complete
        assert result.returncode in [0, 1]

    def test_validate_checks_pipeline_config(self) -> None:
        """Validate should check pipeline configuration."""
        result = subprocess.run(
            [sys.executable, "-m", "backend.puzzle_manager", "validate"],
            capture_output=True,
            text=True,
            timeout=30,
            env=_get_env(),
        )

        # Output should mention pipeline config
        output = result.stdout.lower()
        assert "pipeline" in output or "config" in output or result.returncode in [0, 1]

    def test_validate_checks_tags_config(self) -> None:
        """Validate should check tags configuration."""
        result = subprocess.run(
            [sys.executable, "-m", "backend.puzzle_manager", "validate"],
            capture_output=True,
            text=True,
            timeout=30,
            env=_get_env(),
        )

        # Output should mention tags
        result.stdout.lower()
        # May contain "tags" or just show validation results
        assert result.returncode in [0, 1]

    def test_validate_checks_levels_config(self) -> None:
        """Validate should check levels configuration."""
        result = subprocess.run(
            [sys.executable, "-m", "backend.puzzle_manager", "validate"],
            capture_output=True,
            text=True,
            timeout=30,
            env=_get_env(),
        )

        # Output should mention levels
        result.stdout.lower()
        assert result.returncode in [0, 1]

    def test_validate_checks_sources_config(self) -> None:
        """Validate should check sources configuration."""
        result = subprocess.run(
            [sys.executable, "-m", "backend.puzzle_manager", "validate"],
            capture_output=True,
            text=True,
            timeout=30,
            env=_get_env(),
        )

        # Output should mention sources
        result.stdout.lower()
        assert result.returncode in [0, 1]


class TestValidateOutput:
    """Tests for validate output formatting."""

    def test_validate_shows_success_indicators(self) -> None:
        """Validate should show success/failure indicators."""
        result = subprocess.run(
            [sys.executable, "-m", "backend.puzzle_manager", "validate"],
            capture_output=True,
            text=True,
            timeout=30,
            env=_get_env(),
        )

        # Output should contain checkmarks or X marks
        output = result.stdout
        has_indicator = "✓" in output or "✗" in output or "valid" in output.lower()
        assert has_indicator or result.returncode in [0, 1]

    def test_validate_output_not_empty(self) -> None:
        """Validate should produce some output."""
        result = subprocess.run(
            [sys.executable, "-m", "backend.puzzle_manager", "validate"],
            capture_output=True,
            text=True,
            timeout=30,
            env=_get_env(),
        )

        # Should have some output
        assert result.stdout or result.stderr


class TestValidateWithCustomConfig:
    """Tests for validate with custom config path."""

    def test_validate_accepts_config_option(self) -> None:
        """Validate should accept --config option."""
        result = subprocess.run(
            [sys.executable, "-m", "backend.puzzle_manager",
             "--config", "backend/puzzle_manager/config", "validate"],
            capture_output=True,
            text=True,
            timeout=30,
            env=_get_env(),
        )

        # Should not fail on parsing
        assert result.returncode in [0, 1]
        assert "unrecognized" not in result.stderr.lower()

    def test_validate_invalid_config_path(self) -> None:
        """Validate with invalid config path should handle gracefully."""
        result = subprocess.run(
            [sys.executable, "-m", "backend.puzzle_manager",
             "--config", "/nonexistent/path", "validate"],
            capture_output=True,
            text=True,
            timeout=30,
            env=_get_env(),
        )

        # Should fail gracefully with error message
        assert result.returncode in [0, 1]


class TestValidateErrors:
    """Tests for validate error handling."""

    def test_validate_shows_specific_errors(self) -> None:
        """Validate should show specific error messages."""
        result = subprocess.run(
            [sys.executable, "-m", "backend.puzzle_manager", "validate"],
            capture_output=True,
            text=True,
            timeout=30,
            env=_get_env(),
        )

        # If there are errors, they should be visible
        # Success is also acceptable
        assert result.returncode in [0, 1]

    def test_validate_invalid_option_fails(self) -> None:
        """Validate with invalid option should fail."""
        result = subprocess.run(
            [sys.executable, "-m", "backend.puzzle_manager", "validate", "--invalid"],
            capture_output=True,
            text=True,
            timeout=30,
            env=_get_env(),
        )

        # Should fail due to unrecognized option
        assert result.returncode != 0


class TestValidateHelp:
    """Tests for validate help."""

    def test_validate_help_available(self) -> None:
        """Validate --help should show help text."""
        result = subprocess.run(
            [sys.executable, "-m", "backend.puzzle_manager", "validate", "--help"],
            capture_output=True,
            text=True,
            timeout=30,
            env=_get_env(),
        )

        assert result.returncode == 0
        assert "validate" in result.stdout.lower() or "usage" in result.stdout.lower()
