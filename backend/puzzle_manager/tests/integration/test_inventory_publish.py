"""
Tests for inventory integration with publish stage.

Tests for T019-T022:
- T019: Test publish increments total_puzzles
- T020: Test publish increments by_puzzle_level correctly
- T021: Test publish increments by_tag for multi-tag puzzles
- T022: Test atomic write prevents partial updates
"""

import json
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from backend.puzzle_manager.inventory.manager import InventoryManager
from backend.puzzle_manager.inventory.models import (
    CollectionStats,
    InventoryUpdate,
    PuzzleCollectionInventory,
)

# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def empty_inventory() -> PuzzleCollectionInventory:
    """Create an empty inventory for testing."""
    return PuzzleCollectionInventory(
        last_updated=datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC),
        last_run_id="init",
    )


@pytest.fixture
def existing_inventory() -> PuzzleCollectionInventory:
    """Create an inventory with existing data."""
    return PuzzleCollectionInventory(
        schema_version="2.0",
        last_updated=datetime(2026, 1, 30, 10, 0, 0, tzinfo=UTC),
        last_run_id="2026-01-30_abc123",
        collection=CollectionStats(
            total_puzzles=100,
            by_puzzle_level={
                "beginner": 50,
                "intermediate": 30,
                "advanced": 20,
            },
            by_tag={
                "life-and-death": 40,
                "tesuji": 30,
                "ko": 20,
            },
        ),
    )


@pytest.fixture
def inventory_file(tmp_path, existing_inventory) -> Path:
    """Create an inventory file on disk."""
    inventory_path = tmp_path / "puzzle-collection-inventory.json"
    inventory_path.write_text(
        json.dumps(existing_inventory.model_dump(mode="json"), indent=2),
        encoding="utf-8",
    )
    return inventory_path


# =============================================================================
# Test T019: Publish increments total_puzzles
# =============================================================================

class TestPublishIncrementsTotal:
    """Tests for T019: publish increments total_puzzles."""

    def test_increment_total_puzzles(self, existing_inventory):
        """Publishing puzzles increments total_puzzles count."""
        update = InventoryUpdate(
            puzzles_added=10,
            level_increments={"beginner": 10},
            tag_increments={},
        )

        new_stats = update.apply_to(existing_inventory.collection)

        assert new_stats.total_puzzles == 110  # 100 + 10

    def test_increment_from_zero(self, empty_inventory):
        """Publishing to empty inventory starts from zero."""
        update = InventoryUpdate(
            puzzles_added=5,
            level_increments={"novice": 5},
            tag_increments={},
        )

        new_stats = update.apply_to(empty_inventory.collection)

        assert new_stats.total_puzzles == 5

    def test_increment_uses_inventory_manager(self, tmp_path, existing_inventory):
        """InventoryManager.increment() updates total_puzzles."""
        inventory_path = tmp_path / "inventory.json"
        inventory_path.write_text(
            json.dumps(existing_inventory.model_dump(mode="json"), indent=2),
            encoding="utf-8",
        )

        manager = InventoryManager(inventory_path=inventory_path)
        update = InventoryUpdate(
            puzzles_added=5,
            level_increments={"beginner": 5},
            tag_increments={},
        )

        result = manager.increment(update, run_id="test-run")

        assert result.collection.total_puzzles == 105


# =============================================================================
# Test T020: Publish increments by_puzzle_level correctly
# =============================================================================

class TestPublishIncrementsByLevel:
    """Tests for T020: publish increments by_puzzle_level correctly."""

    def test_increment_existing_level(self, existing_inventory):
        """Incrementing an existing level adds to count."""
        update = InventoryUpdate(
            puzzles_added=10,
            level_increments={"beginner": 10},
            tag_increments={},
        )

        new_stats = update.apply_to(existing_inventory.collection)

        assert new_stats.by_puzzle_level["beginner"] == 60  # 50 + 10

    def test_increment_new_level(self, existing_inventory):
        """Incrementing a new level creates entry."""
        update = InventoryUpdate(
            puzzles_added=5,
            level_increments={"expert": 5},
            tag_increments={},
        )

        new_stats = update.apply_to(existing_inventory.collection)

        assert new_stats.by_puzzle_level["expert"] == 5
        assert "expert" in new_stats.by_puzzle_level

    def test_increment_multiple_levels(self, existing_inventory):
        """Incrementing multiple levels at once."""
        update = InventoryUpdate(
            puzzles_added=15,
            level_increments={
                "beginner": 5,
                "intermediate": 5,
                "advanced": 5,
            },
            tag_increments={},
        )

        new_stats = update.apply_to(existing_inventory.collection)

        assert new_stats.by_puzzle_level["beginner"] == 55
        assert new_stats.by_puzzle_level["intermediate"] == 35
        assert new_stats.by_puzzle_level["advanced"] == 25


# =============================================================================
# Test T021: Publish increments by_tag for multi-tag puzzles
# =============================================================================

class TestPublishIncrementsByTag:
    """Tests for T021: publish increments by_tag for multi-tag puzzles."""

    def test_increment_existing_tag(self, existing_inventory):
        """Incrementing an existing tag adds to count."""
        update = InventoryUpdate(
            puzzles_added=1,
            level_increments={"beginner": 1},
            tag_increments={"life-and-death": 1},
        )

        new_stats = update.apply_to(existing_inventory.collection)

        assert new_stats.by_tag["life-and-death"] == 41  # 40 + 1

    def test_increment_new_tag(self, existing_inventory):
        """Incrementing a new tag creates entry."""
        update = InventoryUpdate(
            puzzles_added=1,
            level_increments={"beginner": 1},
            tag_increments={"ladder": 1},
        )

        new_stats = update.apply_to(existing_inventory.collection)

        assert new_stats.by_tag["ladder"] == 1
        assert "ladder" in new_stats.by_tag

    def test_multi_tag_puzzle_increments_all_tags(self, existing_inventory):
        """A puzzle with multiple tags increments all tag counts."""
        # One puzzle with 3 tags
        update = InventoryUpdate(
            puzzles_added=1,
            level_increments={"beginner": 1},
            tag_increments={
                "life-and-death": 1,
                "tesuji": 1,
                "ko": 1,
            },
        )

        new_stats = update.apply_to(existing_inventory.collection)

        # Each tag should be incremented
        assert new_stats.by_tag["life-and-death"] == 41
        assert new_stats.by_tag["tesuji"] == 31
        assert new_stats.by_tag["ko"] == 21


# =============================================================================
# Test T022: Atomic write prevents partial updates
# =============================================================================

class TestAtomicWritePreventsPartialUpdates:
    """Tests for T022: atomic write prevents partial updates."""

    def test_atomic_write_on_success(self, tmp_path, existing_inventory):
        """Successful write uses atomic pattern (temp file + rename)."""
        inventory_path = tmp_path / "inventory.json"
        inventory_path.write_text(
            json.dumps(existing_inventory.model_dump(mode="json"), indent=2),
            encoding="utf-8",
        )

        manager = InventoryManager(inventory_path=inventory_path)
        update = InventoryUpdate(
            puzzles_added=5,
            level_increments={"beginner": 5},
            tag_increments={},
        )

        manager.increment(update, run_id="test-run")

        # Verify file was written
        assert inventory_path.exists()
        loaded = json.loads(inventory_path.read_text())
        assert loaded["collection"]["total_puzzles"] == 105

    def test_failed_write_preserves_original(self, tmp_path, existing_inventory):
        """Failed write leaves original file intact."""
        inventory_path = tmp_path / "inventory.json"
        original_content = json.dumps(existing_inventory.model_dump(mode="json"), indent=2)
        inventory_path.write_text(original_content, encoding="utf-8")

        manager = InventoryManager(inventory_path=inventory_path)

        # Mock save to raise during the single-lock increment
        with patch.object(manager, 'save', side_effect=OSError("Disk full")):
            update = InventoryUpdate(puzzles_added=5, level_increments={}, tag_increments={})

            with pytest.raises(IOError):
                manager.increment(update, run_id="test-run")

        # Original file should be unchanged
        assert inventory_path.read_text() == original_content

    def test_concurrent_access_uses_lock(self, tmp_path, existing_inventory):
        """Concurrent access should use file locking."""
        inventory_path = tmp_path / "inventory.json"
        inventory_path.write_text(
            json.dumps(existing_inventory.model_dump(mode="json"), indent=2),
            encoding="utf-8",
        )

        manager = InventoryManager(inventory_path=inventory_path)

        # First increment
        update1 = InventoryUpdate(puzzles_added=10, level_increments={"beginner": 10}, tag_increments={})
        manager.increment(update1, run_id="run-1")

        # Second increment
        update2 = InventoryUpdate(puzzles_added=5, level_increments={"beginner": 5}, tag_increments={})
        manager.increment(update2, run_id="run-2")

        # Verify both increments were applied
        loaded = manager.load()
        assert loaded.collection.total_puzzles == 115  # 100 + 10 + 5
        assert loaded.collection.by_puzzle_level["beginner"] == 65  # 50 + 10 + 5


# =============================================================================
# Test Inventory Update Application in Publish Context
# =============================================================================

class TestInventoryUpdateInPublishContext:
    """Tests for applying inventory updates in the publish context."""

    def test_batch_update_aggregates_correctly(self, existing_inventory):
        """Multiple puzzle publishes aggregate into single update."""
        # Simulate publishing 3 puzzles
        updates = []
        updates.append(InventoryUpdate(
            puzzles_added=1,
            level_increments={"beginner": 1},
            tag_increments={"life-and-death": 1, "tesuji": 1},
        ))
        updates.append(InventoryUpdate(
            puzzles_added=1,
            level_increments={"intermediate": 1},
            tag_increments={"ko": 1},
        ))
        updates.append(InventoryUpdate(
            puzzles_added=1,
            level_increments={"beginner": 1},
            tag_increments={"life-and-death": 1, "ladder": 1},
        ))

        # Aggregate all updates
        total_update = InventoryUpdate()
        for u in updates:
            total_update.puzzles_added += u.puzzles_added
            for level, count in u.level_increments.items():
                total_update.level_increments[level] = total_update.level_increments.get(level, 0) + count
            for tag, count in u.tag_increments.items():
                total_update.tag_increments[tag] = total_update.tag_increments.get(tag, 0) + count

        new_stats = total_update.apply_to(existing_inventory.collection)

        assert new_stats.total_puzzles == 103  # 100 + 3
        assert new_stats.by_puzzle_level["beginner"] == 52  # 50 + 2
        assert new_stats.by_puzzle_level["intermediate"] == 31  # 30 + 1
        assert new_stats.by_tag["life-and-death"] == 42  # 40 + 2
        assert new_stats.by_tag["ladder"] == 1  # new tag


# =============================================================================
# Test Spec 102: Publish increments by_puzzle_quality
# =============================================================================

class TestPublishIncrementsByQuality:
    """Tests for Spec 102: publish increments by_puzzle_quality breakdown."""

    def test_increment_quality_counts(self):
        """Quality increments should update by_puzzle_quality counts."""
        # Start with inventory that has by_puzzle_quality
        initial_stats = CollectionStats(
            total_puzzles=10,
            by_puzzle_level={"beginner": 10},
            by_tag={},
            by_puzzle_quality={"1": 2, "2": 3, "3": 3, "4": 1, "5": 1},
        )

        update = InventoryUpdate(
            puzzles_added=5,
            level_increments={"beginner": 5},
            tag_increments={},
            quality_increments={"1": 1, "2": 1, "3": 2, "4": 1, "5": 0},
        )

        new_stats = update.apply_to(initial_stats)

        assert new_stats.by_puzzle_quality["1"] == 3  # 2 + 1
        assert new_stats.by_puzzle_quality["2"] == 4  # 3 + 1
        assert new_stats.by_puzzle_quality["3"] == 5  # 3 + 2
        assert new_stats.by_puzzle_quality["4"] == 2  # 1 + 1
        assert new_stats.by_puzzle_quality["5"] == 1  # 1 + 0

    def test_quality_with_empty_initial(self):
        """Quality increments to empty inventory starts from zero."""
        initial_stats = CollectionStats(
            total_puzzles=0,
            by_puzzle_level={},
            by_tag={},
            by_puzzle_quality={"1": 0, "2": 0, "3": 0, "4": 0, "5": 0},
        )

        update = InventoryUpdate(
            puzzles_added=3,
            level_increments={"novice": 3},
            tag_increments={},
            quality_increments={"3": 2, "4": 1},
        )

        new_stats = update.apply_to(initial_stats)

        assert new_stats.by_puzzle_quality["3"] == 2
        assert new_stats.by_puzzle_quality["4"] == 1
        assert new_stats.by_puzzle_quality["1"] == 0  # unchanged

    def test_quality_via_inventory_manager(self, tmp_path):
        """InventoryManager.increment() updates by_puzzle_quality."""
        # Create inventory with quality tracking
        inventory_data = {
            "schema_version": "2.0",
            "last_updated": "2026-01-01T00:00:00Z",
            "last_run_id": "init",
            "collection": {
                "total_puzzles": 10,
                "by_puzzle_level": {"beginner": 10},
                "by_tag": {},
                "by_puzzle_quality": {"1": 2, "2": 2, "3": 3, "4": 2, "5": 1},
            },
        }

        inventory_path = tmp_path / "inventory.json"
        inventory_path.write_text(json.dumps(inventory_data), encoding="utf-8")

        manager = InventoryManager(inventory_path=inventory_path)
        update = InventoryUpdate(
            puzzles_added=5,
            level_increments={"beginner": 5},
            tag_increments={},
            quality_increments={"2": 2, "3": 2, "5": 1},
        )

        result = manager.increment(update, run_id="test-run")

        assert result.collection.by_puzzle_quality["2"] == 4  # 2 + 2
        assert result.collection.by_puzzle_quality["3"] == 5  # 3 + 2
        assert result.collection.by_puzzle_quality["5"] == 2  # 1 + 1
        assert result.collection.by_puzzle_quality["1"] == 2  # unchanged

    def test_quality_preserved_when_not_incremented(self, tmp_path):
        """Quality values preserved when update has no quality_increments."""
        inventory_data = {
            "schema_version": "2.0",
            "last_updated": "2026-01-01T00:00:00Z",
            "last_run_id": "init",
            "collection": {
                "total_puzzles": 5,
                "by_puzzle_level": {"beginner": 5},
                "by_tag": {},
                "by_puzzle_quality": {"1": 1, "2": 1, "3": 1, "4": 1, "5": 1},
            },
        }

        inventory_path = tmp_path / "inventory.json"
        inventory_path.write_text(json.dumps(inventory_data), encoding="utf-8")

        manager = InventoryManager(inventory_path=inventory_path)
        # Update with no quality_increments
        update = InventoryUpdate(
            puzzles_added=2,
            level_increments={"beginner": 2},
            tag_increments={},
        )

        result = manager.increment(update, run_id="test-run")

        # Quality unchanged
        assert result.collection.by_puzzle_quality == {"1": 1, "2": 1, "3": 1, "4": 1, "5": 1}
        assert result.collection.total_puzzles == 7  # 5 + 2
