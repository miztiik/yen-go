"""
Integration tests for analyze stage trace map flow.

Tests that analyze reads trace_id from the trace map (written by ingest)
and uses it for logging context.
"""

from pathlib import Path

import pytest

from backend.puzzle_manager.core.trace_map import write_trace_map
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


class TestAnalyzeTraceMapIntegration:
    """Integration tests for analyze stage trace map handling."""

    def test_analyze_looks_up_trace_id_from_map(
        self, tmp_path: Path, stage_context: StageContext
    ):
        """Analyze stage looks up trace_id from trace map written by ingest."""
        ingest_dir = stage_context.staging_dir / "ingest"
        analyzed_dir = stage_context.staging_dir / "analyzed"

        # Create a valid SGF file in ingest
        sgf_content = "(;FF[4]GM[1]SZ[9]PL[B]AB[dd];B[ee])"
        (ingest_dir / "test-puzzle.sgf").write_text(sgf_content)

        # Write trace map as ingest would
        trace_map = {"test-puzzle": "abcd123456785678"}
        write_trace_map(stage_context.staging_dir, stage_context.run_id, trace_map)

        # Run analyze stage
        stage = AnalyzeStage()
        result = stage.run(stage_context)

        # Analyze should succeed
        assert result.processed == 1
        assert (analyzed_dir / "test-puzzle.sgf").exists()

    def test_analyze_handles_missing_trace_map(
        self, tmp_path: Path, stage_context: StageContext
    ):
        """Analyze stage works without trace map (backward compat)."""
        ingest_dir = stage_context.staging_dir / "ingest"
        analyzed_dir = stage_context.staging_dir / "analyzed"

        # Create a valid SGF file but NO trace map
        sgf_content = "(;FF[4]GM[1]SZ[9]PL[B]AB[dd];B[ee])"
        (ingest_dir / "no-trace-puzzle.sgf").write_text(sgf_content)

        # Run analyze stage - should succeed without trace map
        stage = AnalyzeStage()
        result = stage.run(stage_context)

        assert result.processed == 1
        assert (analyzed_dir / "no-trace-puzzle.sgf").exists()

    def test_analyze_handles_missing_trace_entry(
        self, tmp_path: Path, stage_context: StageContext
    ):
        """Analyze handles files not in trace map gracefully."""
        ingest_dir = stage_context.staging_dir / "ingest"
        analyzed_dir = stage_context.staging_dir / "analyzed"

        # Create a valid SGF file
        sgf_content = "(;FF[4]GM[1]SZ[9]PL[B]AB[dd];B[ee])"
        (ingest_dir / "orphan-puzzle.sgf").write_text(sgf_content)

        # Write trace map WITHOUT this puzzle
        trace_map = {"other-puzzle": "1234567812345678"}
        write_trace_map(stage_context.staging_dir, stage_context.run_id, trace_map)

        # Run analyze stage - should succeed (trace_id will be None)
        stage = AnalyzeStage()
        result = stage.run(stage_context)

        assert result.processed == 1
        assert (analyzed_dir / "orphan-puzzle.sgf").exists()


class TestSelectiveRecomputation:
    """Test YQ/YX selective recomputation behavior.

    When a puzzle already has YQ or YX properties, they should be preserved
    rather than recomputed. Only missing properties are computed fresh.
    """

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
