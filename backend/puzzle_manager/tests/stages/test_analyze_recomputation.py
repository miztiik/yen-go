"""
Tests for analyze stage YQ/YX selective recomputation behavior.

Relocated from test_analyze_trace.py during v12 trace elimination.
"""

from pathlib import Path

import pytest

from backend.puzzle_manager.models.config import BatchConfig, PipelineConfig
from backend.puzzle_manager.stages.analyze import AnalyzeStage
from backend.puzzle_manager.stages.protocol import StageContext
from backend.puzzle_manager.state.models import RunState, StageState


@pytest.fixture
def stage_context(tmp_path: Path) -> StageContext:
    """Create a stage context for testing."""
    staging_dir = tmp_path / "staging"
    output_dir = tmp_path / "output"
    staging_dir.mkdir(parents=True)
    (staging_dir / "ingest").mkdir()
    (staging_dir / "analyzed").mkdir()
    output_dir.mkdir(parents=True)

    config = PipelineConfig(
        batch=BatchConfig(size=10),
    )

    run_state = RunState(
        run_id="test_run_001",
        source_id="test_source",
        stages=[
            StageState(name="ingest", status="completed", processed=2, failed=0),
            StageState(name="analyze", status="pending", processed=0, failed=0),
            StageState(name="publish", status="pending", processed=0, failed=0),
        ],
    )

    return StageContext(
        config=config,
        staging_dir=staging_dir,
        output_dir=output_dir,
        state=run_state,
        source_id="test_source",
    )


class TestSelectiveRecomputation:
    """Test YQ/YX selective recomputation behavior.

    When a puzzle already has YQ or YX properties, they should be preserved
    rather than recomputed. Only missing properties are computed fresh.
    """

    def test_existing_yq_preserved(self, stage_context: StageContext):
        """Existing YQ should be preserved, not recomputed."""
        ingest_dir = stage_context.staging_dir / "ingest"
        analyzed_dir = stage_context.staging_dir / "analyzed"

        # SGF with existing YQ (custom value that wouldn't be computed)
        sgf = "(;FF[4]GM[1]SZ[9]PL[B]YQ[q:5;rc:99;hc:1;ac:0]AB[dd];B[ee])"
        (ingest_dir / "yq-puzzle.sgf").write_text(sgf)

        stage = AnalyzeStage()
        result = stage.run(stage_context)

        assert result.processed == 1
        output = (analyzed_dir / "yq-puzzle.sgf").read_text()
        # Original YQ with rc:99 should be preserved (computed value would differ)
        assert "YQ[q:5;rc:99;hc:1;ac:0]" in output

    def test_existing_yx_preserved(self, stage_context: StageContext):
        """Existing YX should be preserved, not recomputed."""
        ingest_dir = stage_context.staging_dir / "ingest"
        analyzed_dir = stage_context.staging_dir / "analyzed"

        # SGF with existing YX (custom value that wouldn't be computed)
        sgf = "(;FF[4]GM[1]SZ[9]PL[B]YX[d:99;r:999;s:88;u:1]AB[dd];B[ee])"
        (ingest_dir / "yx-puzzle.sgf").write_text(sgf)

        stage = AnalyzeStage()
        result = stage.run(stage_context)

        assert result.processed == 1
        output = (analyzed_dir / "yx-puzzle.sgf").read_text()
        # Original YX with extreme values should be preserved
        assert "YX[d:99;r:999;s:88;u:1]" in output

    def test_missing_yq_computed_fresh(self, stage_context: StageContext):
        """Missing YQ should be computed fresh."""
        ingest_dir = stage_context.staging_dir / "ingest"
        analyzed_dir = stage_context.staging_dir / "analyzed"

        # SGF without YQ
        sgf = "(;FF[4]GM[1]SZ[9]PL[B]AB[dd];B[ee])"
        (ingest_dir / "no-yq-puzzle.sgf").write_text(sgf)

        stage = AnalyzeStage()
        result = stage.run(stage_context)

        assert result.processed == 1
        output = (analyzed_dir / "no-yq-puzzle.sgf").read_text()
        # YQ should be computed and present
        assert "YQ[" in output

    def test_missing_yx_computed_fresh(self, stage_context: StageContext):
        """Missing YX should be computed fresh."""
        ingest_dir = stage_context.staging_dir / "ingest"
        analyzed_dir = stage_context.staging_dir / "analyzed"

        # SGF without YX but with YQ
        sgf = "(;FF[4]GM[1]SZ[9]PL[B]YQ[q:5;rc:10;hc:1;ac:0]AB[dd];B[ee])"
        (ingest_dir / "no-yx-puzzle.sgf").write_text(sgf)

        stage = AnalyzeStage()
        result = stage.run(stage_context)

        assert result.processed == 1
        output = (analyzed_dir / "no-yx-puzzle.sgf").read_text()
        # YX should be computed and present
        assert "YX[" in output
        # YQ should be preserved
        assert "YQ[q:5;rc:10;hc:1;ac:0]" in output
