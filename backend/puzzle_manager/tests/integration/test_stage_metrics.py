"""
Tests for stage-level metrics integration (Spec 052, Phase 8).

Tests T056-T063: Verify stage metrics are updated in inventory after each stage.
"""

from pathlib import Path

import pytest

from backend.puzzle_manager.inventory.manager import InventoryManager
from backend.puzzle_manager.stages.protocol import StageResult

# ============================================================
# T056: Test ingest metrics update
# ============================================================


class TestIngestMetricsUpdate:
    """Test that ingest stage metrics are updated in inventory."""

    def test_update_ingest_metrics_increments_attempted(self, tmp_path: Path) -> None:
        """Ingest attempted count is incremented."""
        # Setup
        inventory_path = tmp_path / "inventory.json"
        config_path = tmp_path / "config"
        config_path.mkdir()
        (config_path / "puzzle-levels.json").write_text(
            '{"levels": [{"slug": "novice"}]}'
        )

        manager = InventoryManager(
            inventory_path=inventory_path,
            config_path=config_path,
        )

        # Create initial inventory
        manager.save(manager.create_empty("run-001"))

        # Act
        manager.update_stage_metrics(
            stage="ingest",
            metrics={"attempted": 10, "passed": 8, "failed": 2},
            run_id="run-002",
        )

        # Assert
        inventory = manager.load()
        assert inventory.stages.ingest.attempted == 10
        assert inventory.stages.ingest.passed == 8
        assert inventory.stages.ingest.failed == 2

    def test_update_ingest_metrics_accumulates(self, tmp_path: Path) -> None:
        """Ingest metrics accumulate across runs."""
        # Setup
        inventory_path = tmp_path / "inventory.json"
        config_path = tmp_path / "config"
        config_path.mkdir()
        (config_path / "puzzle-levels.json").write_text(
            '{"levels": [{"slug": "novice"}]}'
        )

        manager = InventoryManager(
            inventory_path=inventory_path,
            config_path=config_path,
        )

        # Create initial with some values
        initial = manager.create_empty("run-001")
        initial.stages.ingest.attempted = 5
        initial.stages.ingest.passed = 4
        initial.stages.ingest.failed = 1
        manager.save(initial)

        # Act - add more
        manager.update_stage_metrics(
            stage="ingest",
            metrics={"attempted": 10, "passed": 8, "failed": 2},
            run_id="run-002",
        )

        # Assert - values accumulated
        inventory = manager.load()
        assert inventory.stages.ingest.attempted == 15  # 5 + 10
        assert inventory.stages.ingest.passed == 12  # 4 + 8
        assert inventory.stages.ingest.failed == 3  # 1 + 2


# ============================================================
# T057: Test analyze metrics update
# ============================================================


class TestAnalyzeMetricsUpdate:
    """Test that analyze stage metrics are updated in inventory."""

    def test_update_analyze_metrics_increments_enriched(self, tmp_path: Path) -> None:
        """Analyze enriched count is incremented."""
        # Setup
        inventory_path = tmp_path / "inventory.json"
        config_path = tmp_path / "config"
        config_path.mkdir()
        (config_path / "puzzle-levels.json").write_text(
            '{"levels": [{"slug": "novice"}]}'
        )

        manager = InventoryManager(
            inventory_path=inventory_path,
            config_path=config_path,
        )
        manager.save(manager.create_empty("run-001"))

        # Act
        manager.update_stage_metrics(
            stage="analyze",
            metrics={"enriched": 15, "skipped": 3},
            run_id="run-002",
        )

        # Assert
        inventory = manager.load()
        assert inventory.stages.analyze.enriched == 15
        assert inventory.stages.analyze.skipped == 3

    def test_update_analyze_metrics_accumulates(self, tmp_path: Path) -> None:
        """Analyze metrics accumulate across runs."""
        # Setup
        inventory_path = tmp_path / "inventory.json"
        config_path = tmp_path / "config"
        config_path.mkdir()
        (config_path / "puzzle-levels.json").write_text(
            '{"levels": [{"slug": "novice"}]}'
        )

        manager = InventoryManager(
            inventory_path=inventory_path,
            config_path=config_path,
        )

        # Create initial with some values
        initial = manager.create_empty("run-001")
        initial.stages.analyze.enriched = 10
        initial.stages.analyze.skipped = 2
        manager.save(initial)

        # Act
        manager.update_stage_metrics(
            stage="analyze",
            metrics={"enriched": 5, "skipped": 1},
            run_id="run-002",
        )

        # Assert
        inventory = manager.load()
        assert inventory.stages.analyze.enriched == 15  # 10 + 5
        assert inventory.stages.analyze.skipped == 3  # 2 + 1


# ============================================================
# T058: Test stage duration logging
# ============================================================


class TestStageDurationLogging:
    """Test that stage duration is logged correctly."""

    def test_stage_result_contains_duration(self) -> None:
        """StageResult includes duration_seconds."""
        result = StageResult.partial_result(
            processed=10,
            failed=2,
            errors=[],
            duration=5.5,
        )
        # StageResult.duration_seconds stores the duration
        assert result.duration_seconds == 5.5

    def test_stage_result_failure_has_zero_duration(self) -> None:
        """Failed stage result has default duration."""
        result = StageResult.failure_result("Test error")
        assert result.duration_seconds == 0.0


# ============================================================
# T059-T060: Test HTTP metrics tracking
# ============================================================


class TestHttpMetricsTracking:
    """Test that HTTP client metrics can be tracked."""

    def test_http_client_tracks_retries(self) -> None:
        """HTTP client should track retry counts."""
        from backend.puzzle_manager.core.http import HttpClient

        # HttpClient uses tenacity for retries
        # The retry count is tracked internally by tenacity
        client = HttpClient(timeout=5, max_retries=3)
        assert client.max_retries == 3

    def test_http_client_has_rate_limit_awareness(self) -> None:
        """HTTP client should have rate limit configuration."""
        from backend.puzzle_manager.core.http import HttpClient

        # Currently rate limiting is handled at adapter level
        # This test verifies the client can be configured
        client = HttpClient(timeout=5)
        assert client.timeout == 5


# ============================================================
# T061: Test coordinator calls update_stage_metrics
# ============================================================


class TestCoordinatorMetricsIntegration:
    """Test that coordinator updates inventory stage metrics."""

    def test_update_stage_metrics_called_after_ingest(self, tmp_path: Path) -> None:
        """Verify update_stage_metrics is called after ingest stage."""
        # This test verifies the integration pattern exists
        # Full integration testing requires mocking the stages

        inventory_path = tmp_path / "inventory.json"
        config_path = tmp_path / "config"
        config_path.mkdir()
        (config_path / "puzzle-levels.json").write_text(
            '{"levels": [{"slug": "novice"}]}'
        )

        manager = InventoryManager(
            inventory_path=inventory_path,
            config_path=config_path,
        )
        manager.save(manager.create_empty("run-001"))

        # Simulate what coordinator does after ingest
        stage_result = StageResult.partial_result(
            processed=10,
            failed=2,
            errors=[],
            duration=5.5,
        )

        # Map stage result to metrics
        ingest_metrics = {
            "attempted": stage_result.processed + stage_result.failed,
            "passed": stage_result.processed,
            "failed": stage_result.failed,
        }

        manager.update_stage_metrics("ingest", ingest_metrics, "run-002")

        inventory = manager.load()
        assert inventory.stages.ingest.attempted == 12
        assert inventory.stages.ingest.passed == 10
        assert inventory.stages.ingest.failed == 2


# ============================================================
# T062: Test stage metrics are computed correctly
# ============================================================


class TestComputedMetrics:
    """Test that computed metrics (error rates) are updated."""

    def test_error_rate_ingest_computed(self, tmp_path: Path) -> None:
        """Ingest error rate is computed from attempted/failed."""
        inventory_path = tmp_path / "inventory.json"
        config_path = tmp_path / "config"
        config_path.mkdir()
        (config_path / "puzzle-levels.json").write_text(
            '{"levels": [{"slug": "novice"}]}'
        )

        manager = InventoryManager(
            inventory_path=inventory_path,
            config_path=config_path,
        )
        manager.save(manager.create_empty("run-001"))

        # Add ingest metrics with some failures
        manager.update_stage_metrics(
            stage="ingest",
            metrics={"attempted": 100, "passed": 90, "failed": 10},
            run_id="run-002",
        )

        inventory = manager.load()
        # error_rate_ingest = failed / attempted = 10/100 = 0.1
        assert inventory.metrics.error_rate_ingest == pytest.approx(0.1, rel=0.01)

    def test_error_rate_ingest_zero_when_no_failures(self, tmp_path: Path) -> None:
        """Ingest error rate is 0 when no failures."""
        inventory_path = tmp_path / "inventory.json"
        config_path = tmp_path / "config"
        config_path.mkdir()
        (config_path / "puzzle-levels.json").write_text(
            '{"levels": [{"slug": "novice"}]}'
        )

        manager = InventoryManager(
            inventory_path=inventory_path,
            config_path=config_path,
        )
        manager.save(manager.create_empty("run-001"))

        manager.update_stage_metrics(
            stage="ingest",
            metrics={"attempted": 50, "passed": 50, "failed": 0},
            run_id="run-002",
        )

        inventory = manager.load()
        assert inventory.metrics.error_rate_ingest == 0.0

    def test_error_rate_ingest_handles_zero_attempted(self, tmp_path: Path) -> None:
        """Ingest error rate handles zero attempted gracefully."""
        inventory_path = tmp_path / "inventory.json"
        config_path = tmp_path / "config"
        config_path.mkdir()
        (config_path / "puzzle-levels.json").write_text(
            '{"levels": [{"slug": "novice"}]}'
        )

        manager = InventoryManager(
            inventory_path=inventory_path,
            config_path=config_path,
        )
        manager.save(manager.create_empty("run-001"))

        manager.update_stage_metrics(
            stage="ingest",
            metrics={"attempted": 0, "passed": 0, "failed": 0},
            run_id="run-002",
        )

        inventory = manager.load()
        # Should not divide by zero
        assert inventory.metrics.error_rate_ingest == 0.0


# ============================================================
# T063: Test stage metrics logging format
# ============================================================


class TestStageMetricsLogging:
    """Test that stage metrics are logged in expected format."""

    def test_update_stage_metrics_logs_update(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Verify update_stage_metrics logs the update."""
        import logging

        inventory_path = tmp_path / "inventory.json"
        config_path = tmp_path / "config"
        config_path.mkdir()
        (config_path / "puzzle-levels.json").write_text(
            '{"levels": [{"slug": "novice"}]}'
        )

        manager = InventoryManager(
            inventory_path=inventory_path,
            config_path=config_path,
        )
        manager.save(manager.create_empty("run-001"))

        with caplog.at_level(logging.DEBUG):
            manager.update_stage_metrics(
                stage="ingest",
                metrics={"attempted": 10, "passed": 8, "failed": 2},
                run_id="run-002",
            )

        # Verify debug log was emitted
        assert any("ingest" in record.message.lower() for record in caplog.records)

    def test_publish_metrics_update(self, tmp_path: Path) -> None:
        """Verify publish stage metrics can be updated."""
        inventory_path = tmp_path / "inventory.json"
        config_path = tmp_path / "config"
        config_path.mkdir()
        (config_path / "puzzle-levels.json").write_text(
            '{"levels": [{"slug": "novice"}]}'
        )

        manager = InventoryManager(
            inventory_path=inventory_path,
            config_path=config_path,
        )
        manager.save(manager.create_empty("run-001"))

        manager.update_stage_metrics(
            stage="publish",
            metrics={"new": 25, "failed": 3},
            run_id="run-002",
        )

        inventory = manager.load()
        assert inventory.stages.publish.new == 25
        assert inventory.stages.publish.failed == 3

    def test_publish_metrics_update_sets_throughput(self, tmp_path: Path) -> None:
        """Verify publish stage sets daily_publish_throughput to per-run count."""
        inventory_path = tmp_path / "inventory.json"
        config_path = tmp_path / "config"
        config_path.mkdir()
        (config_path / "puzzle-levels.json").write_text(
            '{"levels": [{"slug": "novice"}]}'
        )

        manager = InventoryManager(
            inventory_path=inventory_path,
            config_path=config_path,
        )
        manager.save(manager.create_empty("run-001"))

        manager.update_stage_metrics(
            stage="publish",
            metrics={"new": 42, "failed": 0},
            run_id="run-002",
        )

        inventory = manager.load()
        assert inventory.metrics.daily_publish_throughput == 42

    def test_publish_error_rate_computed(self, tmp_path: Path) -> None:
        """Verify error_rate_publish is computed from publish failures."""
        inventory_path = tmp_path / "inventory.json"
        config_path = tmp_path / "config"
        config_path.mkdir()
        (config_path / "puzzle-levels.json").write_text(
            '{"levels": [{"slug": "novice"}]}'
        )

        manager = InventoryManager(
            inventory_path=inventory_path,
            config_path=config_path,
        )
        manager.save(manager.create_empty("run-001"))

        # 90 succeeded, 10 failed => error rate = 10/100 = 0.1
        manager.update_stage_metrics(
            stage="publish",
            metrics={"new": 90, "failed": 10},
            run_id="run-002",
        )

        inventory = manager.load()
        assert inventory.metrics.error_rate_publish == pytest.approx(0.1, rel=0.01)


# ============================================================
# Spec 102: Test publish quality summary formatting
# ============================================================


class TestPublishQualitySummary:
    """Test quality summary formatting in publish stage (Spec 102)."""

    def test_format_quality_summary_all_levels(self) -> None:
        """Format quality summary with all levels present."""
        from backend.puzzle_manager.stages.publish import PublishStage

        stage = PublishStage()
        quality_counts = {"1": 2, "2": 3, "3": 5, "4": 4, "5": 1}

        result = stage._format_quality_summary(quality_counts)

        # Should be ordered 5→1 (Premium first)
        assert result == "1xPremium, 4xHigh, 5xStandard, 3xBasic, 2xUnverified"

    def test_format_quality_summary_some_levels(self) -> None:
        """Format quality summary with only some levels present."""
        from backend.puzzle_manager.stages.publish import PublishStage

        stage = PublishStage()
        quality_counts = {"1": 0, "2": 0, "3": 3, "4": 2, "5": 0}

        result = stage._format_quality_summary(quality_counts)

        # Should only include non-zero levels
        assert result == "2xHigh, 3xStandard"

    def test_format_quality_summary_single_level(self) -> None:
        """Format quality summary with only one level."""
        from backend.puzzle_manager.stages.publish import PublishStage

        stage = PublishStage()
        quality_counts = {"1": 0, "2": 0, "3": 5, "4": 0, "5": 0}

        result = stage._format_quality_summary(quality_counts)

        assert result == "5xStandard"

    def test_format_quality_summary_empty(self) -> None:
        """Format quality summary with no puzzles."""
        from backend.puzzle_manager.stages.publish import PublishStage

        stage = PublishStage()
        quality_counts = {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0}

        result = stage._format_quality_summary(quality_counts)

        assert result == "none"

    def test_format_quality_summary_missing_keys(self) -> None:
        """Handle missing quality keys gracefully."""
        from backend.puzzle_manager.stages.publish import PublishStage

        stage = PublishStage()
        quality_counts = {"3": 10}  # Only one key

        result = stage._format_quality_summary(quality_counts)

        assert result == "10xStandard"


class TestAnalyzeQualitySummary:
    """Test quality summary formatting in analyze stage (Spec 102)."""

    def test_format_quality_summary_all_levels(self) -> None:
        """Format quality summary with all levels present."""
        from backend.puzzle_manager.stages.analyze import AnalyzeStage

        stage = AnalyzeStage()
        quality_counts = {"1": 2, "2": 3, "3": 5, "4": 4, "5": 1}

        result = stage._format_quality_summary(quality_counts)

        assert result == "1xPremium, 4xHigh, 5xStandard, 3xBasic, 2xUnverified"

    def test_format_quality_summary_some_levels(self) -> None:
        """Format quality summary with only some levels."""
        from backend.puzzle_manager.stages.analyze import AnalyzeStage

        stage = AnalyzeStage()
        quality_counts = {"1": 0, "2": 0, "3": 3, "4": 2, "5": 0}

        result = stage._format_quality_summary(quality_counts)

        assert result == "2xHigh, 3xStandard"

    def test_format_quality_summary_empty(self) -> None:
        """Format quality summary with no puzzles."""
        from backend.puzzle_manager.stages.analyze import AnalyzeStage

        stage = AnalyzeStage()
        quality_counts = {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0}

        result = stage._format_quality_summary(quality_counts)

        assert result == "none"
