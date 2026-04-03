"""
Integration tests for publish stage validation.

Verifies that the publish stage correctly rejects SGF files
that don't meet the YenGo schema requirements.

NOTE: These tests no longer patch get_output_dir() since PublishStage
now uses context.output_dir exclusively (per Spec 040 - test isolation).
"""

from pathlib import Path
from unittest.mock import MagicMock

from backend.puzzle_manager.models.config import (
    BatchConfig,
    CleanupPolicy,
    OutputConfig,
    PipelineConfig,
    StagingConfig,
)
from backend.puzzle_manager.stages.protocol import StageContext
from backend.puzzle_manager.stages.publish import PublishStage
from backend.puzzle_manager.state.models import RunState


class TestPublishStageValidation:
    """Integration tests for SGF validation during publish."""

    def _make_context(
        self,
        staging_dir: Path,
        output_dir: Path,
        skip_validation: bool = False,
    ) -> StageContext:
        """Create a StageContext for testing."""
        config = PipelineConfig(
            batch=BatchConfig(size=2, max_files_per_dir=100),
            staging=StagingConfig(cleanup_policy=CleanupPolicy.NEVER),
            output=OutputConfig(root=str(output_dir)),
        )
        state = MagicMock(spec=RunState)
        state.run_id = "test123456ab"

        return StageContext(
            config=config,
            staging_dir=staging_dir,
            output_dir=output_dir,
            state=state,
            dry_run=False,
            skip_validation=skip_validation,
        )

    def test_publish_rejects_missing_required_properties(self, tmp_path):
        """SGF missing required properties should fail validation."""
        # Setup directories
        staging_dir = tmp_path / "staging"
        analyzed_dir = staging_dir / "analyzed"
        output_dir = tmp_path / "output"

        analyzed_dir.mkdir(parents=True)
        output_dir.mkdir(parents=True)

        # Create SGF without required YenGo properties (no YV, YI, YQ, YX)
        invalid_sgf = """(;FF[4]GM[1]SZ[9]
AB[aa][ba][ca]
AW[bb][cb][db]
;B[ab];W[ac])"""

        (analyzed_dir / "invalid.sgf").write_text(invalid_sgf)

        # Run publish stage - no patches needed, context.output_dir is used
        context = self._make_context(staging_dir, output_dir)
        stage = PublishStage()
        result = stage.run(context)

        # Should fail with validation error
        assert result.failed > 0
        assert result.processed == 0

    def test_publish_accepts_valid_sgf(self, tmp_path):
        """SGF with all required properties should pass validation."""
        # Setup directories
        staging_dir = tmp_path / "staging"
        analyzed_dir = staging_dir / "analyzed"
        output_dir = tmp_path / "output"

        analyzed_dir.mkdir(parents=True)
        output_dir.mkdir(parents=True)

        # Create valid SGF with all required properties
        valid_sgf = """(;FF[4]GM[1]SZ[9]
YV[5]
YG[beginner]
YQ[q:3;rc:2;hc:1;ac:0]
YX[d:3;r:5;s:12;u:1]
YT[capture-race]
AB[aa][ba][ca]
AW[bb][cb][db]
;B[ab];W[ac])"""

        (analyzed_dir / "valid.sgf").write_text(valid_sgf)

        # Run publish stage - no patches needed, context.output_dir is used
        context = self._make_context(staging_dir, output_dir)
        stage = PublishStage()
        result = stage.run(context)

        # Should succeed
        assert result.failed == 0
        assert result.processed == 1

    def test_publish_skip_validation_bypasses_checks(self, tmp_path):
        """skip_validation=True should bypass validation."""
        # Setup directories
        staging_dir = tmp_path / "staging"
        analyzed_dir = staging_dir / "analyzed"
        output_dir = tmp_path / "output"

        analyzed_dir.mkdir(parents=True)
        output_dir.mkdir(parents=True)

        # Create SGF without required properties
        invalid_sgf = """(;FF[4]GM[1]SZ[9]
YG[beginner]
AB[aa][ba][ca]
AW[bb][cb][db]
;B[ab];W[ac])"""

        (analyzed_dir / "bypass.sgf").write_text(invalid_sgf)

        # Run publish stage with skip_validation=True
        context = self._make_context(staging_dir, output_dir, skip_validation=True)
        stage = PublishStage()
        result = stage.run(context)

        # Should succeed despite missing properties
        assert result.processed == 1
        assert result.failed == 0

    def test_publish_rejects_invalid_quality_format(self, tmp_path):
        """SGF with invalid YQ format should fail validation."""
        # Setup directories
        staging_dir = tmp_path / "staging"
        analyzed_dir = staging_dir / "analyzed"
        output_dir = tmp_path / "output"

        analyzed_dir.mkdir(parents=True)
        output_dir.mkdir(parents=True)

        # Create SGF with invalid quality format
        invalid_sgf = """(;FF[4]GM[1]SZ[9]
YV[5]
YG[beginner]
YQ[quality:high]
YX[d:3;r:5;s:12;u:1]
AB[aa][ba][ca]
AW[bb][cb][db]
;B[ab];W[ac])"""

        (analyzed_dir / "invalid_yq.sgf").write_text(invalid_sgf)

        # Run publish stage
        context = self._make_context(staging_dir, output_dir)
        stage = PublishStage()
        result = stage.run(context)

        # Should fail
        assert result.failed > 0

    def test_publish_rejects_invalid_complexity_format(self, tmp_path):
        """SGF with invalid YX format should fail validation."""
        # Setup directories
        staging_dir = tmp_path / "staging"
        analyzed_dir = staging_dir / "analyzed"
        output_dir = tmp_path / "output"

        analyzed_dir.mkdir(parents=True)
        output_dir.mkdir(parents=True)

        # Create SGF with invalid complexity format
        invalid_sgf = """(;FF[4]GM[1]SZ[9]
YV[5]
YG[beginner]
YQ[q:3;rc:2;hc:1;ac:0]
YX[depth=5]
AB[aa][ba][ca]
AW[bb][cb][db]
;B[ab];W[ac])"""

        (analyzed_dir / "invalid_yx.sgf").write_text(invalid_sgf)

        # Run publish stage
        context = self._make_context(staging_dir, output_dir)
        stage = PublishStage()
        result = stage.run(context)

        # Should fail
        assert result.failed > 0

    def test_publish_rejects_invalid_level_slug(self, tmp_path):
        """SGF with invalid level slug should fail validation."""
        # Setup directories
        staging_dir = tmp_path / "staging"
        analyzed_dir = staging_dir / "analyzed"
        output_dir = tmp_path / "output"

        analyzed_dir.mkdir(parents=True)
        output_dir.mkdir(parents=True)

        # Create SGF with invalid level slug
        invalid_sgf = """(;FF[4]GM[1]SZ[9]
YV[5]
YG[super-expert]
YQ[q:3;rc:2;hc:1;ac:0]
YX[d:3;r:5;s:12;u:1]
AB[aa][ba][ca]
AW[bb][cb][db]
;B[ab];W[ac])"""

        (analyzed_dir / "invalid_yg.sgf").write_text(invalid_sgf)

        # Run publish stage
        context = self._make_context(staging_dir, output_dir)
        stage = PublishStage()
        result = stage.run(context)

        # Should fail
        assert result.failed > 0
