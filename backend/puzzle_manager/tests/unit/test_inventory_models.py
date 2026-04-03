"""
Unit tests for inventory models.

Tests Pydantic models for puzzle collection inventory.
"""

from datetime import UTC, datetime

from backend.puzzle_manager.inventory.models import (
    CollectionStats,
    InventoryUpdate,
    PuzzleCollectionInventory,
)

# NOTE: PublishLogEntry is in models/rollback.py (dataclass, not Pydantic)


class TestCollectionStats:
    """Tests for CollectionStats model."""

    def test_default_values(self) -> None:
        """Test default values."""
        stats = CollectionStats()
        assert stats.total_puzzles == 0
        assert stats.by_puzzle_level == {}
        assert stats.by_tag == {}

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
            last_updated=now,
            last_run_id="20260131-abc12345",
        )
        assert inventory.collection.total_puzzles == 12500

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

    def test_apply_to_empty_stats(self) -> None:
        """Test applying update to empty stats."""
        stats = CollectionStats()
        update = InventoryUpdate(
            puzzles_added=10,
            level_increments={"beginner": 5, "intermediate": 5},
            tag_increments={"life-and-death": 6, "tesuji": 4},
        )

        new_stats = update.apply_to(stats)

        assert new_stats.total_puzzles == 10
        assert new_stats.by_puzzle_level["beginner"] == 5
        assert new_stats.by_puzzle_level["intermediate"] == 5
        assert new_stats.by_tag["life-and-death"] == 6

    def test_apply_to_existing_stats(self) -> None:
        """Test applying update to existing stats."""
        stats = CollectionStats(
            total_puzzles=100,
            by_puzzle_level={"beginner": 30, "intermediate": 70},
            by_tag={"life-and-death": 50},
        )
        update = InventoryUpdate(
            puzzles_added=10,
            level_increments={"beginner": 5, "advanced": 5},
            tag_increments={"life-and-death": 6, "ko": 4},
        )

        new_stats = update.apply_to(stats)

        assert new_stats.total_puzzles == 110
        assert new_stats.by_puzzle_level["beginner"] == 35
        assert new_stats.by_puzzle_level["intermediate"] == 70
        assert new_stats.by_puzzle_level["advanced"] == 5
        assert new_stats.by_tag["life-and-death"] == 56
        assert new_stats.by_tag["ko"] == 4


# NOTE: Tests for PublishLogEntry are in test_publish_log.py
# The canonical PublishLogEntry is a dataclass in models/rollback.py
