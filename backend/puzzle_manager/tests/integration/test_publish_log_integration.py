"""
Integration tests for publish log functionality.

Verifies that the publish stage writes log entries correctly (T010).

NOTE: These tests no longer patch get_output_dir() since PublishStage
now uses context.output_dir exclusively (per Spec 040 - test isolation).
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

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


class TestPublishLogIntegration:
    """Integration tests for publish stage log writing."""

    def _make_context(
        self,
        staging_dir: Path,
        output_dir: Path,
        run_id: str = "test123456ab",
    ) -> StageContext:
        """Create a StageContext for testing."""
        config = PipelineConfig(
            batch=BatchConfig(size=2, max_files_per_dir=100),
            staging=StagingConfig(cleanup_policy=CleanupPolicy.NEVER),
            output=OutputConfig(root=str(output_dir)),
        )
        state = MagicMock(spec=RunState)
        state.run_id = run_id

        return StageContext(
            config=config,
            staging_dir=staging_dir,
            output_dir=output_dir,
            state=state,
            dry_run=False,
            skip_validation=True,  # Skip validation for this test
        )

    def _create_valid_sgf(self, puzzle_id: str, source: str = "test_source") -> str:
        """Create a valid SGF for testing with unique content and unique position."""
        # Extract trailing number from puzzle_id for deterministic unique positions
        import re
        m = re.search(r'(\d+)$', puzzle_id)
        idx = int(m.group(1)) if m else 0
        # 4 rows × 3 col-groups = 12 unique positions on 9x9 board
        r = idx % 4
        cg = (idx // 4) % 3
        co = cg * 3  # column offset: 0, 3, 6
        ra = chr(ord('a') + r)
        rb = chr(ord('a') + r + 4)  # white stones 4 rows below
        b1 = ra + chr(ord('a') + co)
        b2 = ra + chr(ord('a') + co + 1)
        b3 = ra + chr(ord('a') + co + 2)
        w1 = rb + chr(ord('a') + co)
        w2 = rb + chr(ord('a') + co + 1)
        return f"""(;FF[4]GM[1]SZ[9]
GN[Test Puzzle {puzzle_id}]
SO[{source}]
PL[B]
YV[5]
YG[beginner]
YQ[q:3;rc:2;hc:1;ac:0]
YX[d:3;r:5;s:12;u:1]
C[Puzzle: {puzzle_id}]
AB[{b1}][{b2}][{b3}]
AW[{w1}][{w2}]
;B[ab];W[ac])"""

    def test_publish_writes_log_entries(self, tmp_path):
        """Publish stage should write log entries for each puzzle via write-ahead (T010)."""
        # Setup directories
        staging_dir = tmp_path / "staging"
        analyzed_dir = staging_dir / "analyzed"
        output_dir = tmp_path / "output"

        analyzed_dir.mkdir(parents=True)
        output_dir.mkdir(parents=True)

        # Create 2 test puzzles (batch_size=2 per dev guidelines: "if it works for 2, it works for N")
        for i in range(2):
            sgf = self._create_valid_sgf(f"puzzle_{i}")
            (analyzed_dir / f"puzzle_{i}.sgf").write_text(sgf)

        # Run publish stage - no patches needed, context.output_dir is used
        with patch('backend.puzzle_manager.stages.publish.PublishLogWriter') as MockWriter:
            mock_writer = MagicMock()
            MockWriter.return_value = mock_writer

            context = self._make_context(staging_dir, output_dir)
            stage = PublishStage()
            result = stage.run(context)

        # Verify batch write: write_batch() called once with all entries
        assert result.processed == 2
        assert mock_writer.write_batch.call_count == 1
        entries = mock_writer.write_batch.call_args[0][0]
        assert len(entries) == 2

    def test_publish_log_contains_run_id(self, tmp_path):
        """Log entries should contain the run_id (T011)."""
        # Setup directories
        staging_dir = tmp_path / "staging"
        analyzed_dir = staging_dir / "analyzed"
        output_dir = tmp_path / "output"

        analyzed_dir.mkdir(parents=True)
        output_dir.mkdir(parents=True)

        # Create test puzzle
        sgf = self._create_valid_sgf("test_puzzle")
        (analyzed_dir / "test_puzzle.sgf").write_text(sgf)

        # Run publish stage with specific run_id
        run_id = "my_run_123456"
        with patch('backend.puzzle_manager.stages.publish.PublishLogWriter') as MockWriter:
            mock_writer = MagicMock()
            MockWriter.return_value = mock_writer

            context = self._make_context(staging_dir, output_dir, run_id=run_id)
            stage = PublishStage()
            stage.run(context)

        # Check the entries passed to write_batch() contain run_id
        assert mock_writer.write_batch.call_count == 1
        entries = mock_writer.write_batch.call_args[0][0]
        for entry in entries:
            assert entry.run_id == run_id

    def test_publish_log_contains_source(self, tmp_path):
        """Log entries should contain the source adapter name (T012)."""
        # Setup directories
        staging_dir = tmp_path / "staging"
        analyzed_dir = staging_dir / "analyzed"
        output_dir = tmp_path / "output"

        analyzed_dir.mkdir(parents=True)
        output_dir.mkdir(parents=True)

        # Create test puzzle with specific source
        source = "goproblems.com"
        sgf = self._create_valid_sgf("test_puzzle", source=source)
        (analyzed_dir / "test_puzzle.sgf").write_text(sgf)

        # Run publish stage
        with patch('backend.puzzle_manager.stages.publish.PublishLogWriter') as MockWriter:
            mock_writer = MagicMock()
            MockWriter.return_value = mock_writer

            context = self._make_context(staging_dir, output_dir)
            stage = PublishStage()
            stage.run(context)

        # Check the entries contain source_id
        assert mock_writer.write_batch.call_count == 1
        entries = mock_writer.write_batch.call_args[0][0]
        for entry in entries:
            # source_id should come from context.source_id
            assert entry.source_id is not None

    def test_publish_log_contains_path(self, tmp_path):
        """Log entries should contain the output path."""
        # Setup directories
        staging_dir = tmp_path / "staging"
        analyzed_dir = staging_dir / "analyzed"
        output_dir = tmp_path / "output"

        analyzed_dir.mkdir(parents=True)
        output_dir.mkdir(parents=True)

        # Create test puzzle
        sgf = self._create_valid_sgf("test_puzzle")
        (analyzed_dir / "test_puzzle.sgf").write_text(sgf)

        # Run publish stage
        with patch('backend.puzzle_manager.stages.publish.PublishLogWriter') as MockWriter:
            mock_writer = MagicMock()
            MockWriter.return_value = mock_writer

            context = self._make_context(staging_dir, output_dir)
            stage = PublishStage()
            stage.run(context)

        # Check entries have path
        assert mock_writer.write_batch.call_count == 1
        entries = mock_writer.write_batch.call_args[0][0]
        for entry in entries:
            assert entry.path is not None
            assert entry.path != ""

    def test_skipped_puzzles_not_logged(self, tmp_path):
        """Skipped puzzles (already exist) should not be logged."""
        # Setup directories
        staging_dir = tmp_path / "staging"
        analyzed_dir = staging_dir / "analyzed"
        output_dir = tmp_path / "output"
        sgf_output_dir = output_dir / "sgf"

        # Flat batch path (new format: sgf/{NNNN}/)
        sgf_output = sgf_output_dir / "0001"

        analyzed_dir.mkdir(parents=True)
        sgf_output.mkdir(parents=True)

        # Create test puzzle
        sgf = self._create_valid_sgf("test_puzzle")
        (analyzed_dir / "test_puzzle.sgf").write_text(sgf)

        # Pre-create the output file (simulate already published)
        from backend.puzzle_manager.core.naming import generate_content_hash
        content_hash = generate_content_hash(sgf)
        (sgf_output / f"{content_hash}.sgf").write_text(sgf)

        # Run publish stage
        with patch('backend.puzzle_manager.stages.publish.PublishLogWriter') as MockWriter:
            mock_writer = MagicMock()
            MockWriter.return_value = mock_writer

            context = self._make_context(staging_dir, output_dir)
            stage = PublishStage()
            result = stage.run(context)

        # Should be skipped, no log entries
        assert result.skipped == 1
        assert result.processed == 0
        # write_batch() should not have been called (no new puzzles published)
        assert not mock_writer.write_batch.called

    def test_publish_writes_log_entries_single_file(self, tmp_path):
        """Publish stage should write_batch() even for a single-file batch."""
        # Setup directories
        staging_dir = tmp_path / "staging"
        analyzed_dir = staging_dir / "analyzed"
        output_dir = tmp_path / "output"

        analyzed_dir.mkdir(parents=True)
        output_dir.mkdir(parents=True)

        # Create 1 test puzzle (single-file batch)
        sgf = self._create_valid_sgf("single_puzzle_0")
        (analyzed_dir / "single_puzzle_0.sgf").write_text(sgf)

        # Run publish stage
        with patch('backend.puzzle_manager.stages.publish.PublishLogWriter') as MockWriter:
            mock_writer = MagicMock()
            MockWriter.return_value = mock_writer

            context = self._make_context(staging_dir, output_dir)
            stage = PublishStage()
            result = stage.run(context)

        # Single file → write_batch() called once with 1 entry
        assert result.processed == 1
        assert mock_writer.write_batch.call_count == 1
        entries = mock_writer.write_batch.call_args[0][0]
        assert len(entries) == 1

    def test_publish_no_write_batch_on_dry_run(self, tmp_path):
        """Publish stage should NOT call write_batch() on dry run."""
        # Setup directories
        staging_dir = tmp_path / "staging"
        analyzed_dir = staging_dir / "analyzed"
        output_dir = tmp_path / "output"

        analyzed_dir.mkdir(parents=True)
        output_dir.mkdir(parents=True)

        # Create test puzzle
        sgf = self._create_valid_sgf("dry_run_puzzle")
        (analyzed_dir / "dry_run_puzzle.sgf").write_text(sgf)

        # Create context with dry_run=True
        config = PipelineConfig(
            batch=BatchConfig(size=2, max_files_per_dir=100),
            staging=StagingConfig(cleanup_policy=CleanupPolicy.NEVER),
            output=OutputConfig(root=str(output_dir)),
        )
        state = MagicMock(spec=RunState)
        state.run_id = "dry-run-test"

        with patch('backend.puzzle_manager.stages.publish.PublishLogWriter') as MockWriter:
            mock_writer = MagicMock()
            MockWriter.return_value = mock_writer

            context = StageContext(
                config=config,
                staging_dir=staging_dir,
                output_dir=output_dir,
                state=state,
                dry_run=True,
                skip_validation=True,
            )

            stage = PublishStage()
            stage.run(context)

        # Verify write_batch() was NOT called during dry run
        assert not mock_writer.write_batch.called
