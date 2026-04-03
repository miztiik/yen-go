"""Integration tests for the pipeline."""

from pathlib import Path
from unittest.mock import MagicMock

from backend.puzzle_manager.pipeline.coordinator import PipelineCoordinator
from backend.puzzle_manager.pipeline.executor import StageExecutor
from backend.puzzle_manager.stages.analyze import AnalyzeStage
from backend.puzzle_manager.stages.ingest import IngestStage
from backend.puzzle_manager.stages.publish import PublishStage


class TestIngestStage:
    """Tests for the ingest stage."""

    def test_ingest_stage_name(self) -> None:
        """Ingest stage should have correct name."""
        stage = IngestStage()
        assert stage.name == "ingest"

    def test_ingest_stage_is_stage_runner(self) -> None:
        """Ingest stage should implement stage runner protocol."""
        stage = IngestStage()
        assert hasattr(stage, "name")
        assert hasattr(stage, "run")


class TestAnalyzeStage:
    """Tests for the analyze stage."""

    def test_analyze_stage_name(self) -> None:
        """Analyze stage should have correct name."""
        stage = AnalyzeStage()
        assert stage.name == "analyze"

    def test_analyze_stage_is_stage_runner(self) -> None:
        """Analyze stage should implement stage runner protocol."""
        stage = AnalyzeStage()
        assert hasattr(stage, "name")
        assert hasattr(stage, "run")


class TestPublishStage:
    """Tests for the publish stage."""

    def test_publish_stage_name(self) -> None:
        """Publish stage should have correct name."""
        stage = PublishStage()
        assert stage.name == "publish"

    def test_publish_stage_is_stage_runner(self) -> None:
        """Publish stage should implement stage runner protocol."""
        stage = PublishStage()
        assert hasattr(stage, "name")
        assert hasattr(stage, "run")


class TestStageExecutor:
    """Tests for the stage executor."""

    def test_executor_has_execute_method(self) -> None:
        """Executor should have execute method."""
        mock_stage = MagicMock()
        mock_stage.name = "test"

        executor = StageExecutor(mock_stage)

        assert hasattr(executor, "execute")


class TestPipelineCoordinator:
    """Tests for the pipeline coordinator."""

    def test_coordinator_creates(self, tmp_path: Path) -> None:
        """Coordinator should be creatable with optional paths."""
        coordinator = PipelineCoordinator(
            staging_dir=tmp_path / "staging",
            state_dir=tmp_path / "state",
            output_dir=tmp_path / "output",
        )
        assert coordinator is not None

    def test_coordinator_has_run_method(self, tmp_path: Path) -> None:
        """Coordinator should have run method."""
        coordinator = PipelineCoordinator(
            staging_dir=tmp_path / "staging",
            state_dir=tmp_path / "state",
            output_dir=tmp_path / "output",
        )

        assert hasattr(coordinator, "run")
