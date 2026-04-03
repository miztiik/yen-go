"""
Integration tests for publish stage robustness improvements.

Tests write-ahead logging, JSONL corruption guard, progress reporting,
flush-interval config, drain flag, and publish log flush.
"""

import json
import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

from backend.puzzle_manager.models.config import (
    BatchConfig,
    CleanupPolicy,
    OutputConfig,
    PipelineConfig,
    StagingConfig,
)
from backend.puzzle_manager.models.publish_log import PublishLogEntry
from backend.puzzle_manager.pm_logging import DETAIL
from backend.puzzle_manager.publish_log import PublishLogReader, PublishLogWriter
from backend.puzzle_manager.stages.protocol import StageContext
from backend.puzzle_manager.stages.publish import PublishStage
from backend.puzzle_manager.state.models import RunState


def _make_context(
    staging_dir: Path,
    output_dir: Path,
    run_id: str = "test123456ab",
    batch_size: int = 100,
    cleanup_policy: CleanupPolicy = CleanupPolicy.NEVER,
    flush_interval: int | None = None,
    dry_run: bool = False,
) -> StageContext:
    """Create a StageContext for testing."""
    config = PipelineConfig(
        batch=BatchConfig(size=batch_size, max_files_per_dir=100),
        staging=StagingConfig(cleanup_policy=cleanup_policy),
        output=OutputConfig(root=str(output_dir)),
    )
    state = MagicMock(spec=RunState)
    state.run_id = run_id

    return StageContext(
        config=config,
        staging_dir=staging_dir,
        output_dir=output_dir,
        state=state,
        dry_run=dry_run,
        skip_validation=True,
        source_id="test_source",
        flush_interval=flush_interval,
    )


def _create_valid_sgf(puzzle_id: str) -> str:
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
PL[B]
YV[5]
YG[beginner]
YQ[q:3;rc:2;hc:1;ac:0]
YX[d:3;r:5;s:12;u:1]
C[Puzzle: {puzzle_id}]
AB[{b1}][{b2}][{b3}]
AW[{w1}][{w2}]
;B[ab];W[ac])"""


class TestWriteAheadPublishLog:
    """Tests for write-ahead publish log (Step 1)."""

    def test_publish_log_entries_written_per_file(self, tmp_path):
        """Each published puzzle should have its log entry written immediately."""
        staging_dir = tmp_path / "staging"
        analyzed_dir = staging_dir / "analyzed"
        output_dir = tmp_path / "output"
        analyzed_dir.mkdir(parents=True)
        output_dir.mkdir(parents=True)

        for i in range(3):
            sgf = _create_valid_sgf(f"write_ahead_{i}")
            (analyzed_dir / f"puzzle_{i}.sgf").write_text(sgf)

        context = _make_context(staging_dir, output_dir, batch_size=10)
        stage = PublishStage()
        result = stage.run(context)

        assert result.processed == 3

        # Verify publish log JSONL was written with 3 entries
        log_dir = output_dir / ".puzzle-inventory-state" / "publish-log"
        jsonl_files = list(log_dir.glob("*.jsonl"))
        assert len(jsonl_files) == 1

        lines = jsonl_files[0].read_text().strip().split("\n")
        assert len(lines) == 3

        # Each line should be valid JSON
        for line in lines:
            entry = json.loads(line)
            assert "puzzle_id" in entry
            assert "run_id" in entry

    def test_crash_mid_loop_preserves_logged_entries(self, tmp_path):
        """If publish crashes mid-loop, already-written log entries survive."""
        staging_dir = tmp_path / "staging"
        analyzed_dir = staging_dir / "analyzed"
        output_dir = tmp_path / "output"
        analyzed_dir.mkdir(parents=True)
        output_dir.mkdir(parents=True)

        for i in range(3):
            sgf = _create_valid_sgf(f"crash_test_{i}")
            (analyzed_dir / f"puzzle_{i}.sgf").write_text(sgf)

        context = _make_context(staging_dir, output_dir, batch_size=10)
        stage = PublishStage()

        # Patch SGFBuilder.from_game to raise on the 3rd call (simulating crash)
        call_count = [0]
        original_from_game = None

        def crash_on_third(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] >= 3:
                raise RuntimeError("Simulated crash")
            return original_from_game(*args, **kwargs)

        from backend.puzzle_manager.core.sgf_builder import SGFBuilder
        original_from_game = SGFBuilder.from_game

        with patch.object(SGFBuilder, 'from_game', side_effect=crash_on_third):
            result = stage.run(context)

        # 2 succeeded, 1 failed
        assert result.processed == 2
        assert result.failed == 1

        # Verify the 2 successful entries are in the publish log
        log_dir = output_dir / ".puzzle-inventory-state" / "publish-log"
        jsonl_files = list(log_dir.glob("*.jsonl"))
        assert len(jsonl_files) == 1
        lines = jsonl_files[0].read_text().strip().split("\n")
        assert len(lines) == 2


class TestJSONLCorruptionGuard:
    """Tests for JSONL corruption guard (Step 8)."""

    def test_read_date_skips_corrupted_lines(self, tmp_path):
        """Corrupted JSONL lines should be skipped, not crash the reader."""
        log_dir = tmp_path / "publish-log"
        log_dir.mkdir()

        valid_entry = PublishLogEntry(
            run_id="test-run",
            puzzle_id="abc123",
            source_id="test",
            path="sgf/0001/abc123.sgf",
            quality=3,
            trace_id="trace1",
            level="beginner",
        )
        valid_entry2 = PublishLogEntry(
            run_id="test-run", puzzle_id="def456", source_id="test",
            path="sgf/0001/def456.sgf", quality=3, trace_id="trace2", level="beginner",
        )

        log_file = log_dir / "2026-02-23.jsonl"
        with open(log_file, "w", encoding="utf-8") as f:
            f.write(valid_entry.to_jsonl() + "\n")
            f.write('{"truncated": true, "puzzle_id"\n')  # corrupted
            f.write(valid_entry2.to_jsonl() + "\n")

        reader = PublishLogReader(log_dir=log_dir)
        entries = list(reader.read_date("2026-02-23"))

        assert len(entries) == 2
        assert entries[0].puzzle_id == "abc123"
        assert entries[1].puzzle_id == "def456"

    def test_search_by_run_id_survives_corruption(self, tmp_path):
        """Search should work even with corrupted entries in the log."""
        log_dir = tmp_path / "publish-log"
        log_dir.mkdir()

        valid_entry = PublishLogEntry(
            run_id="target-run", puzzle_id="found123", source_id="test",
            path="sgf/0001/found123.sgf", quality=2, trace_id="t1", level="beginner",
        )

        log_file = log_dir / "2026-02-23.jsonl"
        with open(log_file, "w", encoding="utf-8") as f:
            f.write('{"broken json\n')
            f.write(valid_entry.to_jsonl() + "\n")

        reader = PublishLogReader(log_dir=log_dir)
        results = reader.search_by_run_id("target-run")
        assert len(results) == 1
        assert results[0].puzzle_id == "found123"


class TestProgressReporting:
    """Tests for structured progress reporting (Step 4)."""

    def test_per_file_log_is_detail_level(self, tmp_path, caplog):
        """Per-file 'Published puzzle' messages should be at DETAIL level."""
        staging_dir = tmp_path / "staging"
        analyzed_dir = staging_dir / "analyzed"
        output_dir = tmp_path / "output"
        analyzed_dir.mkdir(parents=True)
        output_dir.mkdir(parents=True)

        sgf = _create_valid_sgf("debug_level_test")
        (analyzed_dir / "puzzle_0.sgf").write_text(sgf)

        context = _make_context(staging_dir, output_dir, batch_size=10)
        stage = PublishStage()

        with caplog.at_level(logging.DEBUG, logger="publish"):
            result = stage.run(context)

        assert result.processed == 1

        # "Published puzzle" should appear at DETAIL level (not on console)
        published_records = [
            r for r in caplog.records
            if "Published puzzle" in r.message and r.name == "publish"
        ]
        for record in published_records:
            assert record.levelno == DETAIL

    def test_duplicate_skip_is_detail_level(self, tmp_path, caplog):
        """Duplicate skip messages should be at DETAIL level."""
        staging_dir = tmp_path / "staging"
        analyzed_dir = staging_dir / "analyzed"
        output_dir = tmp_path / "output"
        analyzed_dir.mkdir(parents=True)
        output_dir.mkdir(parents=True)

        sgf = _create_valid_sgf("dup_test")
        (analyzed_dir / "puzzle_0.sgf").write_text(sgf)

        # First run: publish the puzzle
        context = _make_context(staging_dir, output_dir, batch_size=10,
                                cleanup_policy=CleanupPolicy.NEVER)
        stage = PublishStage()
        result1 = stage.run(context)
        assert result1.processed == 1

        # Re-add the same puzzle
        (analyzed_dir / "puzzle_0.sgf").write_text(sgf)

        # Second run: should skip as duplicate
        with caplog.at_level(logging.DEBUG, logger="publish"):
            result2 = stage.run(context)

        assert result2.skipped >= 1

        skip_records = [
            r for r in caplog.records
            if "Skipping duplicate" in r.message
        ]
        for record in skip_records:
            assert record.levelno == DETAIL


class TestFlushIntervalConfig:
    """Tests for flush_interval configuration (Step 3)."""

    def test_flush_interval_in_batch_config(self):
        """BatchConfig should accept flush_interval."""
        config = BatchConfig(size=100, max_files_per_dir=100, flush_interval=200)
        assert config.flush_interval == 200

    def test_flush_interval_default(self):
        """Default flush_interval should be 500."""
        config = BatchConfig()
        assert config.flush_interval == 500

    def test_flush_interval_zero_disables(self):
        """flush_interval=0 should be valid (disables sub-batch flush)."""
        config = BatchConfig(flush_interval=0)
        assert config.flush_interval == 0


class TestDrainFlag:
    """Tests for --drain flag behavior (Step 7)."""

    def test_drain_processes_all_files(self, tmp_path):
        """With drain semantics (huge batch_size), all files should be processed."""
        staging_dir = tmp_path / "staging"
        analyzed_dir = staging_dir / "analyzed"
        output_dir = tmp_path / "output"
        analyzed_dir.mkdir(parents=True)
        output_dir.mkdir(parents=True)

        for i in range(10):
            sgf = _create_valid_sgf(f"drain_{i}")
            (analyzed_dir / f"puzzle_{i}.sgf").write_text(sgf)

        # Use config batch_size=10000 (within config max), override via context
        context = _make_context(staging_dir, output_dir, batch_size=10000,
                                cleanup_policy=CleanupPolicy.ON_SUCCESS)
        stage = PublishStage()
        result = stage.run(context)

        assert result.processed == 10
        assert result.remaining == 0


class TestPublishLogFlush:
    """Tests for publish log flush behavior."""

    def test_write_flushes_to_disk(self, tmp_path):
        """PublishLogWriter.write() should flush data to disk immediately."""
        log_dir = tmp_path / "publish-log"
        writer = PublishLogWriter(log_dir=log_dir)

        entry = PublishLogEntry(
            run_id="test-run",
            puzzle_id="flush_test",
            source_id="test",
            path="sgf/0001/flush_test.sgf",
            quality=3,
            trace_id="t1",
            level="beginner",
        )

        writer.write(entry)

        # File should exist and be readable immediately
        log_file = list(log_dir.glob("*.jsonl"))[0]
        content = log_file.read_text()
        assert "flush_test" in content


class TestInventoryUpdateResilience:
    """Tests that inventory/audit failures don't crash the publish stage."""

    def test_publish_succeeds_when_inventory_update_fails(self, tmp_path):
        """Files should be published even if _update_inventory throws."""
        staging_dir = tmp_path / "staging"
        analyzed = staging_dir / "analyzed"
        analyzed.mkdir(parents=True)
        output_dir = tmp_path / "output"
        (output_dir / "sgf").mkdir(parents=True)
        (output_dir / ".puzzle-inventory-state").mkdir(parents=True)

        # Write one valid SGF
        sgf = _create_valid_sgf("inv_fail_1")
        (analyzed / "test_inv.sgf").write_text(sgf, encoding="utf-8")

        ctx = _make_context(staging_dir, output_dir, batch_size=10)
        stage = PublishStage()

        # Patch _update_inventory to raise
        with patch.object(stage, "_update_inventory", side_effect=RuntimeError("boom")):
            result = stage.run(ctx)

        # Stage should still report processed files (not crash)
        assert result.processed >= 1
        # SGF files should exist on disk
        assert len(list((output_dir / "sgf").rglob("*.sgf"))) >= 1

    def test_audit_written_even_if_inventory_fails(self, tmp_path):
        """Audit entry should be written even when inventory update fails."""
        staging_dir = tmp_path / "staging"
        analyzed = staging_dir / "analyzed"
        analyzed.mkdir(parents=True)
        output_dir = tmp_path / "output"
        (output_dir / "sgf").mkdir(parents=True)
        ops_dir = output_dir / ".puzzle-inventory-state"
        ops_dir.mkdir(parents=True)

        sgf = _create_valid_sgf("audit_test_1")
        (analyzed / "test_audit.sgf").write_text(sgf, encoding="utf-8")

        ctx = _make_context(staging_dir, output_dir, batch_size=10)
        stage = PublishStage()

        with patch.object(stage, "_update_inventory", side_effect=RuntimeError("boom")):
            stage.run(ctx)

        # Audit entry should still exist
        audit_file = ops_dir / "audit.jsonl"
        assert audit_file.exists()
        content = audit_file.read_text()
        assert "publish" in content
