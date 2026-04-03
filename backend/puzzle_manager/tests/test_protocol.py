"""
Unit tests for stages/protocol.py - StageContext path methods.

These tests ensure staging directory naming consistency (SPEC 038).
"""

from unittest.mock import MagicMock

import pytest

from backend.puzzle_manager.stages.protocol import StageContext, StageResult


class TestStageContextPaths:
    """Test StageContext directory path methods."""

    @pytest.fixture
    def mock_config(self):
        """Create a minimal mock config."""
        config = MagicMock()
        config.batch.size = 2
        return config

    @pytest.fixture
    def mock_state(self):
        """Create a minimal mock state."""
        return MagicMock()

    @pytest.fixture
    def context(self, tmp_path, mock_config, mock_state):
        """Create a StageContext with temporary directories."""
        staging_dir = tmp_path / "staging"
        output_dir = tmp_path / "output"
        staging_dir.mkdir()
        output_dir.mkdir()

        return StageContext(
            config=mock_config,
            staging_dir=staging_dir,
            output_dir=output_dir,
            state=mock_state,
        )

    def test_get_ingest_dir_returns_ingest_suffix(self, context):
        """get_ingest_dir() must return path ending in 'ingest'.

        SPEC 038: Directory naming consistency - staging directories
        must match pipeline stage names (ingest → analyze → publish).
        """
        ingest_dir = context.get_ingest_dir()

        assert ingest_dir.name == "ingest", (
            f"Expected directory name 'ingest', got '{ingest_dir.name}'"
        )
        assert str(ingest_dir).endswith("ingest"), (
            f"Expected path to end with 'ingest', got '{ingest_dir}'"
        )

    def test_get_analyzed_dir_returns_analyzed_suffix(self, context):
        """get_analyzed_dir() must return path ending in 'analyzed'."""
        analyzed_dir = context.get_analyzed_dir()

        assert analyzed_dir.name == "analyzed", (
            f"Expected directory name 'analyzed', got '{analyzed_dir.name}'"
        )

    def test_get_failed_dir_returns_correct_structure(self, context):
        """get_failed_dir() must return path with 'failed/{stage}' structure."""
        failed_dir = context.get_failed_dir("analyze")

        assert failed_dir.parent.name == "failed", (
            f"Expected parent 'failed', got '{failed_dir.parent.name}'"
        )
        assert failed_dir.name == "analyze", (
            f"Expected directory name 'analyze', got '{failed_dir.name}'"
        )

    def test_staging_directories_are_under_staging_dir(self, context):
        """All staging directories must be children of staging_dir."""
        staging_dir = context.staging_dir

        assert context.get_ingest_dir().parent == staging_dir
        assert context.get_analyzed_dir().parent == staging_dir
        assert context.get_failed_dir("ingest").parent.parent == staging_dir

    def test_ingest_dir_does_not_contain_raw(self, context):
        """SPEC 038: No 'raw' in path - verify naming consistency.

        This is a regression test to prevent accidental reintroduction
        of 'raw' terminology in staging directory names.
        """
        ingest_dir = context.get_ingest_dir()

        assert "raw" not in str(ingest_dir).lower(), (
            f"Path should not contain 'raw': {ingest_dir}"
        )

    def test_source_id_filter_optional(self, tmp_path, mock_config, mock_state):
        """source_id parameter should be optional and default to None."""
        context = StageContext(
            config=mock_config,
            staging_dir=tmp_path / "staging",
            output_dir=tmp_path / "output",
            state=mock_state,
        )

        assert context.source_id is None

    def test_source_id_filter_can_be_set(self, tmp_path, mock_config, mock_state):
        """source_id parameter should accept a string value."""
        context = StageContext(
            config=mock_config,
            staging_dir=tmp_path / "staging",
            output_dir=tmp_path / "output",
            state=mock_state,
            source_id="sanderland",
        )

        assert context.source_id == "sanderland"


class TestStageResult:
    """Test StageResult dataclass."""

    def test_success_result_creation(self):
        """StageResult can be created with success=True."""
        result = StageResult(success=True, processed=5, failed=0)

        assert result.success is True
        assert result.processed == 5
        assert result.failed == 0

    def test_failure_result_creation(self):
        """StageResult can be created with success=False."""
        result = StageResult(success=False, processed=3, failed=2)

        assert result.success is False
        assert result.processed == 3
        assert result.failed == 2

    def test_default_values(self):
        """StageResult has sensible defaults."""
        result = StageResult(success=True)

        assert result.processed == 0
        assert result.failed == 0
