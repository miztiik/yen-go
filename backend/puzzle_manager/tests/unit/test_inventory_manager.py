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
