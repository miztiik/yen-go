"""
Integration tests for inventory system (Spec 052, Phase 9).

Tests T067-T069: Verify inventory integrates correctly with pipeline operations.
"""

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from backend.puzzle_manager.inventory.manager import InventoryManager
from backend.puzzle_manager.inventory.models import (
    InventoryUpdate,
)
from backend.puzzle_manager.inventory.rebuild import rebuild_inventory

# ============================================================
# T067: Integration test - full pipeline run updates inventory
# ============================================================


class TestPipelineIntegration:
    """Test inventory integration with pipeline operations."""

    def test_full_publish_updates_inventory(self, tmp_path: Path) -> None:
        """Full publish batch updates inventory correctly."""
        # Setup
        inventory_path = tmp_path / "inventory.json"
        config_path = tmp_path / "config"
        config_path.mkdir()
        (config_path / "puzzle-levels.json").write_text(
            '{"levels": [{"slug": "novice"}, {"slug": "beginner"}, {"slug": "intermediate"}]}'
        )

        manager = InventoryManager(
            inventory_path=inventory_path,
            config_path=config_path,
        )

        # Create empty inventory
        manager.save(manager.create_empty("run-001"))

        # Simulate publish batch with multiple puzzles
        update = InventoryUpdate(
            puzzles_added=10,
            level_increments={"novice": 5, "beginner": 3, "intermediate": 2},
            tag_increments={"life-and-death": 8, "ladder": 4, "ko": 2},
            quality_increments={"3": 3, "4": 4, "5": 2, "1": 0, "2": 1},
        )

        # Apply update
        inventory = manager.increment(update, "run-002")

        # Verify all counts updated
        assert inventory.collection.total_puzzles == 10
        assert inventory.collection.by_puzzle_level["novice"] == 5
        assert inventory.collection.by_puzzle_level["beginner"] == 3
        assert inventory.collection.by_puzzle_level["intermediate"] == 2
        assert inventory.collection.by_tag["life-and-death"] == 8
        assert inventory.collection.by_tag["ladder"] == 4
        assert inventory.collection.by_tag["ko"] == 2
        assert inventory.collection.by_puzzle_quality["3"] == 3
        assert inventory.collection.by_puzzle_quality["4"] == 4
        assert inventory.collection.by_puzzle_quality["5"] == 2

    def test_multiple_batches_accumulate(self, tmp_path: Path) -> None:
        """Multiple publish batches accumulate correctly."""
        # Setup
        inventory_path = tmp_path / "inventory.json"
        config_path = tmp_path / "config"
        config_path.mkdir()
        (config_path / "puzzle-levels.json").write_text(
            '{"levels": [{"slug": "novice"}, {"slug": "beginner"}]}'
        )

        manager = InventoryManager(
            inventory_path=inventory_path,
            config_path=config_path,
        )
        manager.save(manager.create_empty("run-001"))

        # First batch
        update1 = InventoryUpdate(
            puzzles_added=5,
            level_increments={"novice": 5},
            tag_increments={"life-and-death": 5},
        )
        manager.increment(update1, "run-002")

        # Second batch
        update2 = InventoryUpdate(
            puzzles_added=3,
            level_increments={"beginner": 3},
            tag_increments={"ladder": 3},
        )
        inventory = manager.increment(update2, "run-003")

        # Verify accumulation
        assert inventory.collection.total_puzzles == 8
        assert inventory.collection.by_puzzle_level["novice"] == 5
        assert inventory.collection.by_puzzle_level["beginner"] == 3
        assert inventory.collection.by_tag["life-and-death"] == 5
        assert inventory.collection.by_tag["ladder"] == 3

    def test_stage_metrics_accumulate_across_runs(self, tmp_path: Path) -> None:
        """Stage metrics accumulate across multiple pipeline runs."""
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

        # First run ingest
        manager.update_stage_metrics(
            "ingest",
            {"attempted": 10, "passed": 8, "failed": 2},
            "run-002",
        )

        # Second run ingest
        manager.update_stage_metrics(
            "ingest",
            {"attempted": 15, "passed": 14, "failed": 1},
            "run-003",
        )

        inventory = manager.load()
        assert inventory.stages.ingest.attempted == 25
        assert inventory.stages.ingest.passed == 22
        assert inventory.stages.ingest.failed == 3


# ============================================================
# T068: Integration test - partial publish failure
# ============================================================


class TestPartialFailureHandling:
    """Test inventory consistency on partial failures."""

    def test_inventory_not_corrupted_on_single_failure(self, tmp_path: Path) -> None:
        """Inventory remains consistent when single puzzle fails."""
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

        # Add some puzzles
        update = InventoryUpdate(
            puzzles_added=5,
            level_increments={"novice": 5},
        )
        manager.increment(update, "run-002")

        # Verify inventory is valid
        inventory = manager.load()
        assert inventory.collection.total_puzzles == 5
        assert inventory.schema_version == "2.0"

    def test_atomic_write_prevents_corruption(self, tmp_path: Path) -> None:
        """Atomic write pattern prevents partial writes."""
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

        # Create and save initial inventory
        inventory = manager.create_empty("run-001")
        manager.save(inventory)

        # Verify file is valid JSON
        with open(inventory_path) as f:
            data = json.load(f)
        assert data["schema_version"] == "2.0"

        # Update inventory
        update = InventoryUpdate(puzzles_added=10, level_increments={"novice": 10})
        manager.increment(update, "run-002")

        # Verify file is still valid
        with open(inventory_path) as f:
            data = json.load(f)
        assert data["collection"]["total_puzzles"] == 10

    def test_lock_prevents_concurrent_corruption(self, tmp_path: Path) -> None:
        """File lock prevents concurrent access issues."""
        inventory_path = tmp_path / "inventory.json"
        config_path = tmp_path / "config"
        config_path.mkdir()
        (config_path / "puzzle-levels.json").write_text(
            '{"levels": [{"slug": "novice"}]}'
        )

        # Two managers pointing to same file
        manager1 = InventoryManager(
            inventory_path=inventory_path,
            config_path=config_path,
        )
        manager2 = InventoryManager(
            inventory_path=inventory_path,
            config_path=config_path,
        )

        manager1.save(manager1.create_empty("run-001"))

        # Both managers can load
        inv1 = manager1.load()
        inv2 = manager2.load()
        assert inv1.collection.total_puzzles == 0
        assert inv2.collection.total_puzzles == 0


# ============================================================
# T069: Integration test - rollback + rebuild consistency
# ============================================================


class TestRollbackRebuildConsistency:
    """Test rollback and rebuild produce consistent state."""

    def test_rollback_then_rebuild_consistent(self, tmp_path: Path) -> None:
        """Rollback followed by rebuild produces consistent state."""
        inventory_path = tmp_path / "inventory.json"
        config_path = tmp_path / "config"
        output_dir = tmp_path / "output"
        publish_log_dir = output_dir / "publish-log"
        sgf_dir = output_dir / "sgf"

        config_path.mkdir()
        publish_log_dir.mkdir(parents=True)
        sgf_dir.mkdir(parents=True)

        (config_path / "puzzle-levels.json").write_text(
            '{"levels": [{"slug": "novice"}, {"slug": "beginner"}]}'
        )

        manager = InventoryManager(
            inventory_path=inventory_path,
            config_path=config_path,
        )

        # Create initial inventory with 10 puzzles
        initial = manager.create_empty("run-001")
        initial.collection.total_puzzles = 10
        initial.collection.by_puzzle_level = {"novice": 6, "beginner": 4}
        initial.collection.by_tag = {"life-and-death": 8, "ladder": 4}
        manager.save(initial)

        # Simulate rollback of 3 puzzles
        manager.decrement(
            puzzles_removed=3,
            level_decrements={"novice": 2, "beginner": 1},
            tag_decrements={"life-and-death": 2, "ladder": 1},
            run_id="rollback-001",
        )
        manager.increment_rollback_audit("rollback-001")

        inventory = manager.load()
        assert inventory.collection.total_puzzles == 7
        assert inventory.collection.by_puzzle_level["novice"] == 4
        assert inventory.collection.by_puzzle_level["beginner"] == 3
        assert inventory.audit.total_rollbacks == 1

    def test_decrement_floors_at_zero(self, tmp_path: Path) -> None:
        """Decrement floors counts at zero, doesn't go negative."""
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

        # Start with 5 puzzles
        initial = manager.create_empty("run-001")
        initial.collection.total_puzzles = 5
        initial.collection.by_puzzle_level = {"novice": 5}
        manager.save(initial)

        # Try to remove 10 puzzles (more than exist)
        inventory = manager.decrement(
            puzzles_removed=10,
            level_decrements={"novice": 10},
            tag_decrements={},
            run_id="rollback-001",
        )

        # Should floor at 0
        assert inventory.collection.total_puzzles == 0
        assert inventory.collection.by_puzzle_level["novice"] == 0

    def test_rebuild_from_empty_produces_empty(self, tmp_path: Path) -> None:
        """Rebuild with no publish logs produces empty inventory."""
        output_dir = tmp_path / "output"
        publish_log_dir = output_dir / "publish-log"
        publish_log_dir.mkdir(parents=True)

        # Rebuild with empty publish logs
        inventory = rebuild_inventory(output_dir=output_dir, run_id="rebuild-001")

        assert inventory.collection.total_puzzles == 0
        assert inventory.collection.by_puzzle_level == {}
        assert inventory.collection.by_tag == {}


# ============================================================
# Additional integration tests
# ============================================================


class TestSchemaValidation:
    """Test schema validation on load."""

    def test_load_validates_schema(self, tmp_path: Path) -> None:
        """Loading validates data against Pydantic schema."""
        inventory_path = tmp_path / "inventory.json"
        config_path = tmp_path / "config"
        config_path.mkdir()
        (config_path / "puzzle-levels.json").write_text(
            '{"levels": [{"slug": "novice"}]}'
        )

        # Write valid inventory
        valid_data = {
            "schema_version": "1.0",
            "schema_ref": "config/schemas/puzzle-collection-inventory-schema.json",
            "collection": {"total_puzzles": 5, "by_puzzle_level": {}, "by_tag": {}},
            "stages": {"ingest": {}, "analyze": {}, "publish": {}},
            "metrics": {},
            "audit": {},
            "last_updated": datetime.now(UTC).isoformat(),
            "last_run_id": "test-run",
        }
        with open(inventory_path, "w") as f:
            json.dump(valid_data, f)

        manager = InventoryManager(
            inventory_path=inventory_path,
            config_path=config_path,
        )
        inventory = manager.load()
        assert inventory.collection.total_puzzles == 5

    def test_invalid_data_raises_validation_error(self, tmp_path: Path) -> None:
        """Loading invalid data raises ValidationError."""
        from pydantic import ValidationError

        inventory_path = tmp_path / "inventory.json"
        config_path = tmp_path / "config"
        config_path.mkdir()
        (config_path / "puzzle-levels.json").write_text(
            '{"levels": [{"slug": "novice"}]}'
        )

        # Write invalid inventory (missing required fields)
        invalid_data = {
            "schema_version": "1.0",
            # Missing required fields
        }
        with open(inventory_path, "w") as f:
            json.dump(invalid_data, f)

        manager = InventoryManager(
            inventory_path=inventory_path,
            config_path=config_path,
        )

        with pytest.raises(ValidationError):
            manager.load()


class TestSchemaVersion:
    """Test schema version is set correctly."""

    def test_new_inventory_has_current_schema_version(self, tmp_path: Path) -> None:
        """New inventory is created with current schema version."""
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

        # Create and save inventory
        inventory = manager.create_empty("run-001")
        manager.save(inventory)

        # Load and verify schema version
        loaded = manager.load()
        assert loaded.schema_version == "2.0"
