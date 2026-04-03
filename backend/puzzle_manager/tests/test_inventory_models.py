"""
Unit tests for inventory models.

Tests Pydantic models for puzzle collection inventory.
"""

from datetime import UTC, datetime

import pytest

from backend.puzzle_manager.inventory.models import (
    AnalyzeMetrics,
    AuditMetrics,
    CollectionStats,
    ComputedMetrics,
    IngestMetrics,
    InventoryUpdate,
    PublishMetrics,
    PuzzleCollectionInventory,
    StagesStats,
)

# NOTE: PublishLogEntry is in models/rollback.py (dataclass, not Pydantic)


class TestIngestMetrics:
    """Tests for IngestMetrics model."""

    def test_default_values(self) -> None:
        """Test default values are zero."""
        metrics = IngestMetrics()
        assert metrics.attempted == 0
        assert metrics.passed == 0
        assert metrics.failed == 0

    def test_custom_values(self) -> None:
        """Test setting custom values."""
        metrics = IngestMetrics(attempted=100, passed=90, failed=10)
        assert metrics.attempted == 100
        assert metrics.passed == 90
        assert metrics.failed == 10

    def test_rejects_negative_values(self) -> None:
        """Test that negative values are rejected."""
        with pytest.raises(ValueError):
            IngestMetrics(attempted=-1)


class TestAnalyzeMetrics:
    """Tests for AnalyzeMetrics model."""

    def test_default_values(self) -> None:
        """Test default values are zero."""
        metrics = AnalyzeMetrics()
        assert metrics.enriched == 0
        assert metrics.skipped == 0

    def test_custom_values(self) -> None:
        """Test setting custom values."""
        metrics = AnalyzeMetrics(enriched=500, skipped=50)
        assert metrics.enriched == 500
        assert metrics.skipped == 50


class TestPublishMetrics:
    """Tests for PublishMetrics model."""

    def test_default_values(self) -> None:
        """Test default values are zero."""
        metrics = PublishMetrics()
        assert metrics.new == 0

    def test_custom_values(self) -> None:
        """Test setting custom values."""
        metrics = PublishMetrics(new=1000)
        assert metrics.new == 1000


class TestStagesStats:
    """Tests for StagesStats model."""

    def test_default_factories(self) -> None:
        """Test default factories create empty metrics."""
        stats = StagesStats()
        assert stats.ingest.attempted == 0
        assert stats.analyze.enriched == 0
        assert stats.publish.new == 0

    def test_nested_metrics(self) -> None:
        """Test nested metrics can be set."""
        stats = StagesStats(
            ingest=IngestMetrics(attempted=100, passed=80, failed=20),
            analyze=AnalyzeMetrics(enriched=75, skipped=5),
            publish=PublishMetrics(new=70),
        )
        assert stats.ingest.attempted == 100
        assert stats.analyze.enriched == 75
        assert stats.publish.new == 70


class TestComputedMetrics:
    """Tests for ComputedMetrics model."""

    def test_default_values(self) -> None:
        """Test default values are zero."""
        metrics = ComputedMetrics()
        assert metrics.daily_publish_throughput == 0
        assert metrics.error_rate_ingest == 0.0
        assert metrics.error_rate_publish == 0.0

    def test_error_rate_bounds(self) -> None:
        """Test error rates must be between 0 and 1."""
        # Valid
        metrics = ComputedMetrics(error_rate_ingest=0.5, error_rate_publish=1.0)
        assert metrics.error_rate_ingest == 0.5

        # Invalid - above 1
        with pytest.raises(ValueError):
            ComputedMetrics(error_rate_ingest=1.5)


class TestAuditMetrics:
    """Tests for AuditMetrics model."""

    def test_default_values(self) -> None:
        """Test default values."""
        audit = AuditMetrics()
        assert audit.total_rollbacks == 0
        assert audit.last_rollback_date is None

    def test_with_rollback_date(self) -> None:
        """Test setting rollback date."""
        now = datetime.now(UTC)
        audit = AuditMetrics(total_rollbacks=3, last_rollback_date=now)
        assert audit.total_rollbacks == 3
        assert audit.last_rollback_date == now


class TestCollectionStats:
    """Tests for CollectionStats model."""

    def test_default_values(self) -> None:
        """Test default values."""
        stats = CollectionStats()
        assert stats.total_puzzles == 0
        assert stats.by_puzzle_level == {}
        assert stats.by_tag == {}
        assert stats.by_puzzle_quality == {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0}

    def test_by_puzzle_level(self) -> None:
        """Test by_puzzle_level dictionary."""
        stats = CollectionStats(
            total_puzzles=100,
            by_puzzle_level={"beginner": 30, "intermediate": 50, "advanced": 20},
        )
        assert stats.by_puzzle_level["beginner"] == 30
        assert stats.by_puzzle_level["intermediate"] == 50




class TestPuzzleCollectionInventory:
    """Tests for PuzzleCollectionInventory model."""

    def test_required_fields(self) -> None:
        """Test that required fields must be provided."""
        now = datetime.now(UTC)
        inventory = PuzzleCollectionInventory(
            last_updated=now,
            last_run_id="20260131-abc12345",
        )
        assert inventory.schema_version == "2.0"
        assert inventory.last_updated == now
        assert inventory.last_run_id == "20260131-abc12345"

    def test_full_inventory(self) -> None:
        """Test creating a full inventory."""
        now = datetime.now(UTC)
        inventory = PuzzleCollectionInventory(
            collection=CollectionStats(
                total_puzzles=12500,
                by_puzzle_level={"beginner": 1200, "intermediate": 2500},
                by_tag={"life-and-death": 3400, "tesuji": 2800},
            ),
            stages=StagesStats(
                ingest=IngestMetrics(attempted=15000, passed=14200, failed=800),
                analyze=AnalyzeMetrics(enriched=14000, skipped=200),
                publish=PublishMetrics(new=12500),
            ),
            metrics=ComputedMetrics(
                daily_publish_throughput=150,
                error_rate_ingest=0.053,
                error_rate_publish=0.002,
            ),
            audit=AuditMetrics(total_rollbacks=3, last_rollback_date=now),
            last_updated=now,
            last_run_id="20260131-abc12345",
        )
        assert inventory.collection.total_puzzles == 12500
        assert inventory.stages.ingest.failed == 800
        assert inventory.metrics.error_rate_ingest == 0.053
        assert inventory.audit.total_rollbacks == 3

    def test_json_serialization(self) -> None:
        """Test JSON serialization."""
        now = datetime(2026, 1, 31, 10, 30, 0, tzinfo=UTC)
        inventory = PuzzleCollectionInventory(
            last_updated=now,
            last_run_id="20260131-abc12345",
        )
        data = inventory.model_dump(mode="json")
        assert data["schema_version"] == "2.0"
        # Accept both Z and +00:00 UTC representations
        assert data["last_updated"] in [
            "2026-01-31T10:30:00+00:00",
            "2026-01-31T10:30:00Z",
        ]


class TestInventoryUpdate:
    """Tests for InventoryUpdate model."""

    def test_default_values(self) -> None:
        """Test default values."""
        update = InventoryUpdate()
        assert update.puzzles_added == 0
        assert update.level_increments == {}
        assert update.tag_increments == {}
        assert update.quality_increments == {}

    def test_apply_to_empty_stats(self) -> None:
        """Test applying update to empty stats."""
        stats = CollectionStats()
        update = InventoryUpdate(
            puzzles_added=10,
            level_increments={"beginner": 5, "intermediate": 5},
            tag_increments={"life-and-death": 6, "tesuji": 4},
            quality_increments={"3": 2, "4": 2, "5": 1},
        )

        new_stats = update.apply_to(stats)

        assert new_stats.total_puzzles == 10
        assert new_stats.by_puzzle_level["beginner"] == 5
        assert new_stats.by_puzzle_level["intermediate"] == 5
        assert new_stats.by_tag["life-and-death"] == 6
        assert new_stats.by_puzzle_quality["3"] == 2
        assert new_stats.by_puzzle_quality["4"] == 2
        assert new_stats.by_puzzle_quality["5"] == 1

    def test_apply_to_existing_stats(self) -> None:
        """Test applying update to existing stats."""
        stats = CollectionStats(
            total_puzzles=100,
            by_puzzle_level={"beginner": 30, "intermediate": 70},
            by_tag={"life-and-death": 50},
            by_puzzle_quality={"1": 10, "2": 20, "3": 30, "4": 30, "5": 10},
        )
        update = InventoryUpdate(
            puzzles_added=10,
            level_increments={"beginner": 5, "advanced": 5},
            tag_increments={"life-and-death": 6, "ko": 4},
            quality_increments={"4": 5},
        )

        new_stats = update.apply_to(stats)

        assert new_stats.total_puzzles == 110
        assert new_stats.by_puzzle_level["beginner"] == 35
        assert new_stats.by_puzzle_level["intermediate"] == 70
        assert new_stats.by_puzzle_level["advanced"] == 5
        assert new_stats.by_tag["life-and-death"] == 56
        assert new_stats.by_tag["ko"] == 4
        assert new_stats.by_puzzle_quality["4"] == 35


# NOTE: Tests for PublishLogEntry are in test_publish_log.py
# The canonical PublishLogEntry is a dataclass in models/rollback.py
