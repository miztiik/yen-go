"""
Unit tests for InventoryManager.

Tests inventory file operations including load, save, increment, decrement.
"""

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from backend.puzzle_manager.inventory.manager import (
    InventoryManager,
    load_level_slugs,
)
from backend.puzzle_manager.inventory.models import (
    CollectionStats,
    InventoryUpdate,
    PuzzleCollectionInventory,
)


@pytest.fixture
def config_path(tmp_path: Path) -> Path:
    """Create a temporary config directory with puzzle-levels.json."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()

    levels_data = {
        "levels": [
            {"slug": "novice", "name": "Novice"},
            {"slug": "beginner", "name": "Beginner"},
            {"slug": "elementary", "name": "Elementary"},
            {"slug": "intermediate", "name": "Intermediate"},
            {"slug": "upper-intermediate", "name": "Upper Intermediate"},
            {"slug": "advanced", "name": "Advanced"},
            {"slug": "low-dan", "name": "Low Dan"},
            {"slug": "high-dan", "name": "High Dan"},
            {"slug": "expert", "name": "Expert"},
        ]
    }
    levels_file = config_dir / "puzzle-levels.json"
    levels_file.write_text(json.dumps(levels_data))

    return config_dir


@pytest.fixture
def inventory_path(tmp_path: Path) -> Path:
    """Create a temporary inventory file path."""
    inventory_dir = tmp_path / "yengo-puzzle-collections"
    inventory_dir.mkdir()
    return inventory_dir / "puzzle-collection-inventory.json"


@pytest.fixture
def manager(inventory_path: Path, config_path: Path) -> InventoryManager:
    """Create an InventoryManager with temporary paths."""
    return InventoryManager(inventory_path=inventory_path, config_path=config_path)


class TestLoadLevelSlugs:
    """Tests for load_level_slugs function."""

    def test_loads_all_levels(self, config_path: Path) -> None:
        """Test loading all level slugs from config."""
        slugs = load_level_slugs(config_path)
        assert len(slugs) == 9
        assert "novice" in slugs
        assert "beginner" in slugs
        assert "expert" in slugs

    def test_preserves_order(self, config_path: Path) -> None:
        """Test that level order is preserved."""
        slugs = load_level_slugs(config_path)
        assert slugs[0] == "novice"
        assert slugs[-1] == "expert"


class TestInventoryManagerBasics:
    """Tests for InventoryManager basic operations."""

    def test_exists_false_when_no_file(self, manager: InventoryManager) -> None:
        """Test exists() returns False when file doesn't exist."""
        assert manager.exists() is False

    def test_exists_true_when_file_exists(
        self, manager: InventoryManager, inventory_path: Path
    ) -> None:
        """Test exists() returns True when file exists."""
        # Create a valid inventory file
        now = datetime.now(UTC)
        inventory = PuzzleCollectionInventory(
            last_updated=now,
            last_run_id="20260131-test1234",
        )
        inventory_path.write_text(json.dumps(inventory.model_dump(mode="json")))
        assert manager.exists() is True

    def test_level_slugs_property(self, manager: InventoryManager) -> None:
        """Test level_slugs property loads from config."""
        slugs = manager.level_slugs
        assert len(slugs) == 9
        assert "beginner" in slugs


class TestInventoryManagerCreateEmpty:
    """Tests for create_empty method."""

    def test_creates_with_all_levels_at_zero(self, manager: InventoryManager) -> None:
        """Test create_empty initializes all levels to 0."""
        inventory = manager.create_empty("20260131-test1234")

        assert inventory.collection.total_puzzles == 0
        assert len(inventory.collection.by_puzzle_level) == 9
        assert all(v == 0 for v in inventory.collection.by_puzzle_level.values())

    def test_sets_run_id(self, manager: InventoryManager) -> None:
        """Test create_empty sets the run_id."""
        run_id = "20260131-abcdef12"
        inventory = manager.create_empty(run_id)
        assert inventory.last_run_id == run_id

    def test_sets_timestamp(self, manager: InventoryManager) -> None:
        """Test create_empty sets last_updated to current time."""
        before = datetime.now(UTC)
        inventory = manager.create_empty("20260131-test1234")
        after = datetime.now(UTC)

        assert before <= inventory.last_updated <= after


class TestInventoryManagerSaveLoad:
    """Tests for save and load methods."""

    def test_save_creates_file(
        self, manager: InventoryManager, inventory_path: Path
    ) -> None:
        """Test save creates the inventory file."""
        inventory = manager.create_empty("20260131-test1234")
        manager.save(inventory)

        assert inventory_path.exists()

    def test_save_writes_valid_json(
        self, manager: InventoryManager, inventory_path: Path
    ) -> None:
        """Test save writes valid JSON."""
        inventory = manager.create_empty("20260131-test1234")
        manager.save(inventory)

        # Should be valid JSON
        data = json.loads(inventory_path.read_text())
        assert data["schema_version"] == "2.0"
        assert data["last_run_id"] == "20260131-test1234"

    def test_load_returns_inventory(self, manager: InventoryManager) -> None:
        """Test load returns the saved inventory."""
        original = manager.create_empty("20260131-test1234")
        original = original.model_copy(
            update={
                "collection": CollectionStats(
                    total_puzzles=100,
                    by_puzzle_level={"beginner": 50, "intermediate": 50},
                )
            }
        )
        manager.save(original)

        loaded = manager.load()

        assert loaded.collection.total_puzzles == 100
        assert loaded.collection.by_puzzle_level["beginner"] == 50

    def test_load_raises_on_missing_file(self, manager: InventoryManager) -> None:
        """Test load raises FileNotFoundError when file doesn't exist."""
        with pytest.raises(FileNotFoundError):
            manager.load()

    def test_load_or_create_creates_new(self, manager: InventoryManager) -> None:
        """Test load_or_create creates new file when missing."""
        inventory = manager.load_or_create("20260131-test1234")

        assert inventory.collection.total_puzzles == 0
        assert manager.exists()

    def test_load_or_create_loads_existing(self, manager: InventoryManager) -> None:
        """Test load_or_create loads existing file."""
        original = manager.create_empty("20260131-first")
        original = original.model_copy(
            update={
                "collection": CollectionStats(total_puzzles=500),
            }
        )
        manager.save(original)

        loaded = manager.load_or_create("20260131-second")

        # Should load existing, not create new
        assert loaded.collection.total_puzzles == 500


class TestInventoryManagerIncrement:
    """Tests for increment method."""

    def test_increment_total(self, manager: InventoryManager) -> None:
        """Test increment increases total_puzzles."""
        update = InventoryUpdate(puzzles_added=10)
        inventory = manager.increment(update, "20260131-test1234")

        assert inventory.collection.total_puzzles == 10

    def test_increment_levels(self, manager: InventoryManager) -> None:
        """Test increment increases level counts."""
        update = InventoryUpdate(
            puzzles_added=10,
            level_increments={"beginner": 5, "intermediate": 5},
        )
        inventory = manager.increment(update, "20260131-test1234")

        assert inventory.collection.by_puzzle_level["beginner"] == 5
        assert inventory.collection.by_puzzle_level["intermediate"] == 5

    def test_increment_tags(self, manager: InventoryManager) -> None:
        """Test increment increases tag counts."""
        update = InventoryUpdate(
            puzzles_added=10,
            tag_increments={"life-and-death": 6, "tesuji": 4},
        )
        inventory = manager.increment(update, "20260131-test1234")

        assert inventory.collection.by_tag["life-and-death"] == 6
        assert inventory.collection.by_tag["tesuji"] == 4

    def test_increment_cumulative(self, manager: InventoryManager) -> None:
        """Test multiple increments are cumulative."""
        update1 = InventoryUpdate(puzzles_added=10)
        manager.increment(update1, "20260131-first")

        update2 = InventoryUpdate(puzzles_added=5)
        inventory = manager.increment(update2, "20260131-second")

        assert inventory.collection.total_puzzles == 15

    def test_increment_updates_publish_metrics(self, manager: InventoryManager) -> None:
        """Test increment updates stages.publish.new."""
        update = InventoryUpdate(puzzles_added=10)
        inventory = manager.increment(update, "20260131-test1234")

        assert inventory.stages.publish.new == 10

    def test_increment_preserves_daily_throughput(self, manager: InventoryManager) -> None:
        """Test increment preserves daily_publish_throughput (FR-018)."""
        # Set an initial throughput value
        inventory = manager.load_or_create("20260131-setup")
        inventory = inventory.model_copy(
            update={"metrics": inventory.metrics.model_copy(update={"daily_publish_throughput": 150})}
        )
        manager.save(inventory)

        # Increment puzzles
        update = InventoryUpdate(puzzles_added=10)
        inventory = manager.increment(update, "20260131-test1234")

        # Throughput should be preserved
        assert inventory.metrics.daily_publish_throughput == 150


class TestInventoryManagerDecrement:
    """Tests for decrement method."""

    def test_decrement_total(self, manager: InventoryManager) -> None:
        """Test decrement decreases total_puzzles."""
        # First add some puzzles
        update = InventoryUpdate(puzzles_added=100)
        manager.increment(update, "20260131-first")

        # Then decrement
        inventory = manager.decrement(
            puzzles_removed=30,
            level_decrements={},
            tag_decrements={},
            run_id="20260131-second",
        )

        assert inventory.collection.total_puzzles == 70

    def test_decrement_levels(self, manager: InventoryManager) -> None:
        """Test decrement decreases level counts."""
        # First add some puzzles
        update = InventoryUpdate(
            puzzles_added=100,
            level_increments={"beginner": 50, "intermediate": 50},
        )
        manager.increment(update, "20260131-first")

        # Then decrement
        inventory = manager.decrement(
            puzzles_removed=30,
            level_decrements={"beginner": 20, "intermediate": 10},
            tag_decrements={},
            run_id="20260131-second",
        )

        assert inventory.collection.by_puzzle_level["beginner"] == 30
        assert inventory.collection.by_puzzle_level["intermediate"] == 40

    def test_decrement_floors_at_zero(self, manager: InventoryManager) -> None:
        """Test decrement floors at zero (no negatives)."""
        # First add some puzzles
        update = InventoryUpdate(puzzles_added=10)
        manager.increment(update, "20260131-first")

        # Try to decrement more than exists
        inventory = manager.decrement(
            puzzles_removed=20,  # More than 10
            level_decrements={},
            tag_decrements={},
            run_id="20260131-second",
        )

        assert inventory.collection.total_puzzles == 0  # Floored at zero

    def test_decrement_quality(self, manager: InventoryManager) -> None:
        """Test decrement decreases quality counts (Spec 102, T027)."""
        # First add puzzles with quality
        update = InventoryUpdate(
            puzzles_added=20,
            level_increments={"beginner": 20},
            quality_increments={"3": 10, "4": 5, "5": 5},
        )
        manager.increment(update, "20260131-first")

        # Then decrement
        inventory = manager.decrement(
            puzzles_removed=10,
            level_decrements={"beginner": 10},
            tag_decrements={},
            run_id="20260131-second",
            quality_decrements={"3": 6, "4": 2, "5": 2},
        )

        assert inventory.collection.by_puzzle_quality["3"] == 4  # 10 - 6
        assert inventory.collection.by_puzzle_quality["4"] == 3  # 5 - 2
        assert inventory.collection.by_puzzle_quality["5"] == 3  # 5 - 2

    def test_decrement_quality_floors_at_zero(self, manager: InventoryManager) -> None:
        """Test quality decrement floors at zero (Spec 102, T028)."""
        # First add some puzzles with quality
        update = InventoryUpdate(
            puzzles_added=5,
            level_increments={"beginner": 5},
            quality_increments={"3": 3, "4": 2},
        )
        manager.increment(update, "20260131-first")

        # Try to decrement more quality than exists
        inventory = manager.decrement(
            puzzles_removed=5,
            level_decrements={"beginner": 5},
            tag_decrements={},
            run_id="20260131-second",
            quality_decrements={"3": 10, "4": 5},  # More than exists
        )

        assert inventory.collection.by_puzzle_quality["3"] == 0  # Floored at zero
        assert inventory.collection.by_puzzle_quality["4"] == 0  # Floored at zero

    def test_decrement_quality_none_parameter(self, manager: InventoryManager) -> None:
        """Test decrement with quality_decrements=None preserves quality."""
        # First add puzzles with quality
        update = InventoryUpdate(
            puzzles_added=10,
            level_increments={"beginner": 10},
            quality_increments={"3": 5, "4": 5},
        )
        manager.increment(update, "20260131-first")

        # Decrement without quality_decrements (default None)
        inventory = manager.decrement(
            puzzles_removed=5,
            level_decrements={"beginner": 5},
            tag_decrements={},
            run_id="20260131-second",
        )

        # Quality counts should be preserved
        assert inventory.collection.by_puzzle_quality["3"] == 5
        assert inventory.collection.by_puzzle_quality["4"] == 5


class TestInventoryManagerRollbackAudit:
    """Tests for increment_rollback_audit method."""

    def test_increments_rollback_count(self, manager: InventoryManager) -> None:
        """Test increment_rollback_audit increases total_rollbacks."""
        manager.increment_rollback_audit("20260131-first")
        manager.increment_rollback_audit("20260131-second")
        inventory = manager.increment_rollback_audit("20260131-third")

        assert inventory.audit.total_rollbacks == 3

    def test_sets_rollback_date(self, manager: InventoryManager) -> None:
        """Test increment_rollback_audit sets last_rollback_date."""
        before = datetime.now(UTC)
        inventory = manager.increment_rollback_audit("20260131-test1234")
        after = datetime.now(UTC)

        assert inventory.audit.last_rollback_date is not None
        assert before <= inventory.audit.last_rollback_date <= after


class TestInventoryManagerStageMetrics:
    """Tests for update_stage_metrics method."""

    def test_update_ingest_metrics(self, manager: InventoryManager) -> None:
        """Test updating ingest stage metrics."""
        inventory = manager.update_stage_metrics(
            stage="ingest",
            metrics={"attempted": 100, "passed": 90, "failed": 10},
            run_id="20260131-test1234",
        )

        assert inventory.stages.ingest.attempted == 100
        assert inventory.stages.ingest.passed == 90
        assert inventory.stages.ingest.failed == 10

    def test_update_analyze_metrics(self, manager: InventoryManager) -> None:
        """Test updating analyze stage metrics."""
        inventory = manager.update_stage_metrics(
            stage="analyze",
            metrics={"enriched": 85, "skipped": 5},
            run_id="20260131-test1234",
        )

        assert inventory.stages.analyze.enriched == 85
        assert inventory.stages.analyze.skipped == 5

    def test_computes_error_rate(self, manager: InventoryManager) -> None:
        """Test that error rate is computed from stage metrics."""
        inventory = manager.update_stage_metrics(
            stage="ingest",
            metrics={"attempted": 100, "passed": 90, "failed": 10},
            run_id="20260131-test1234",
        )

        assert inventory.metrics.error_rate_ingest == 0.1


class TestInventoryManagerValidation:
    """Tests for validate_levels method."""

    def test_valid_levels(self, manager: InventoryManager) -> None:
        """Test valid levels return no errors."""
        errors = manager.validate_levels({"beginner": 10, "intermediate": 20})
        assert errors == []

    def test_invalid_levels(self, manager: InventoryManager) -> None:
        """Test invalid levels return errors."""
        errors = manager.validate_levels({"beginner": 10, "invalid-level": 20})
        assert len(errors) == 1
        assert "invalid-level" in errors[0]
