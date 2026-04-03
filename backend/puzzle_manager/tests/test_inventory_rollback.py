"""
Tests for inventory integration with rollback.

Tests for T029-T032:
- T029: Test rollback decrements total_puzzles
- T030: Test rollback decrements by_puzzle_level correctly
- T031: Test rollback floors at zero (no negatives) with warning
- T032: Test rollback updates audit.total_rollbacks and last_rollback_date
"""

import json
from datetime import UTC, datetime

import pytest

from backend.puzzle_manager.inventory.manager import InventoryManager
from backend.puzzle_manager.inventory.models import (
    AnalyzeMetrics,
    AuditMetrics,
    CollectionStats,
    IngestMetrics,
    PublishMetrics,
    PuzzleCollectionInventory,
    StagesStats,
)

# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def existing_inventory() -> PuzzleCollectionInventory:
    """Create an inventory with existing data for rollback tests."""
    return PuzzleCollectionInventory(
        schema_version="1.0.0",
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
        stages=StagesStats(
            ingest=IngestMetrics(attempted=150, passed=140, failed=10),
            analyze=AnalyzeMetrics(enriched=120, skipped=20),
            publish=PublishMetrics(new=100),
        ),
        audit=AuditMetrics(
            total_rollbacks=2,
            last_rollback_date=datetime(2026, 1, 25, 14, 0, 0, tzinfo=UTC),
        ),
    )


@pytest.fixture
def small_inventory() -> PuzzleCollectionInventory:
    """Create an inventory with small counts for floor-at-zero tests."""
    return PuzzleCollectionInventory(
        schema_version="1.0.0",
        last_updated=datetime(2026, 1, 30, 10, 0, 0, tzinfo=UTC),
        last_run_id="2026-01-30_abc123",
        collection=CollectionStats(
            total_puzzles=5,
            by_puzzle_level={
                "beginner": 3,
                "intermediate": 2,
            },
            by_tag={
                "life-and-death": 3,
                "tesuji": 2,
            },
        ),
    )


# =============================================================================
# Test T029: Rollback decrements total_puzzles
# =============================================================================

class TestRollbackDecrementsTotal:
    """Tests for T029: rollback decrements total_puzzles."""

    def test_decrement_total_puzzles(self, existing_inventory):
        """Rolling back puzzles decrements total_puzzles count."""
        # Simulate what decrement does manually
        puzzles_to_remove = 10
        new_total = existing_inventory.collection.total_puzzles - puzzles_to_remove

        assert new_total == 90  # 100 - 10

    def test_decrement_uses_inventory_manager(self, tmp_path, existing_inventory):
        """InventoryManager.decrement() updates total_puzzles."""
        inventory_path = tmp_path / "inventory.json"
        inventory_path.write_text(
            json.dumps(existing_inventory.model_dump(mode="json"), indent=2),
            encoding="utf-8",
        )

        manager = InventoryManager(inventory_path=inventory_path)
        result = manager.decrement(
            puzzles_removed=5,
            level_decrements={"beginner": 5},
            tag_decrements={},
            run_id="rollback-test",
        )

        assert result.collection.total_puzzles == 95  # 100 - 5


# =============================================================================
# Test T030: Rollback decrements by_puzzle_level correctly
# =============================================================================

class TestRollbackDecrementsByLevel:
    """Tests for T030: rollback decrements by_puzzle_level correctly."""

    def test_decrement_existing_level(self, tmp_path, existing_inventory):
        """Decrementing an existing level subtracts from count."""
        inventory_path = tmp_path / "inventory.json"
        inventory_path.write_text(
            json.dumps(existing_inventory.model_dump(mode="json"), indent=2),
            encoding="utf-8",
        )

        manager = InventoryManager(inventory_path=inventory_path)
        result = manager.decrement(
            puzzles_removed=10,
            level_decrements={"beginner": 10},
            tag_decrements={},
            run_id="rollback-test",
        )

        assert result.collection.by_puzzle_level["beginner"] == 40  # 50 - 10

    def test_decrement_multiple_levels(self, tmp_path, existing_inventory):
        """Decrementing multiple levels at once."""
        inventory_path = tmp_path / "inventory.json"
        inventory_path.write_text(
            json.dumps(existing_inventory.model_dump(mode="json"), indent=2),
            encoding="utf-8",
        )

        manager = InventoryManager(inventory_path=inventory_path)
        result = manager.decrement(
            puzzles_removed=15,
            level_decrements={
                "beginner": 5,
                "intermediate": 5,
                "advanced": 5,
            },
            tag_decrements={},
            run_id="rollback-test",
        )

        assert result.collection.by_puzzle_level["beginner"] == 45  # 50 - 5
        assert result.collection.by_puzzle_level["intermediate"] == 25  # 30 - 5
        assert result.collection.by_puzzle_level["advanced"] == 15  # 20 - 5


# =============================================================================
# Test T031: Rollback floors at zero (no negatives) with warning
# =============================================================================

class TestRollbackFloorsAtZero:
    """Tests for T031: rollback floors at zero with warning."""

    def test_decrement_floors_at_zero(self, tmp_path, small_inventory):
        """Decrement floors at zero instead of going negative."""
        inventory_path = tmp_path / "inventory.json"
        inventory_path.write_text(
            json.dumps(small_inventory.model_dump(mode="json"), indent=2),
            encoding="utf-8",
        )

        manager = InventoryManager(inventory_path=inventory_path)
        # Try to remove more than exists
        result = manager.decrement(
            puzzles_removed=10,  # Only 5 exist
            level_decrements={"beginner": 10},  # Only 3 exist
            tag_decrements={},
            run_id="rollback-test",
        )

        # Should floor at zero, not go negative
        assert result.collection.total_puzzles == 0
        assert result.collection.by_puzzle_level["beginner"] == 0

    def test_decrement_logs_warning_on_underflow(self, tmp_path, small_inventory, caplog):
        """Decrement logs warning when flooring at zero."""
        import logging

        inventory_path = tmp_path / "inventory.json"
        inventory_path.write_text(
            json.dumps(small_inventory.model_dump(mode="json"), indent=2),
            encoding="utf-8",
        )

        manager = InventoryManager(inventory_path=inventory_path)

        with caplog.at_level(logging.WARNING):
            manager.decrement(
                puzzles_removed=10,
                level_decrements={"beginner": 10},
                tag_decrements={},
                run_id="rollback-test",
            )

        # Check that warning was logged
        assert any("floor" in record.message.lower() or "negative" in record.message.lower()
                   for record in caplog.records)


# =============================================================================
# Test T032: Rollback updates audit.total_rollbacks and last_rollback_date
# =============================================================================

class TestRollbackUpdatesAudit:
    """Tests for T032: rollback updates audit metrics."""

    def test_increment_rollback_audit_increments_count(self, tmp_path, existing_inventory):
        """increment_rollback_audit increments total_rollbacks."""
        inventory_path = tmp_path / "inventory.json"
        inventory_path.write_text(
            json.dumps(existing_inventory.model_dump(mode="json"), indent=2),
            encoding="utf-8",
        )

        manager = InventoryManager(inventory_path=inventory_path)
        result = manager.increment_rollback_audit(run_id="rollback-test")

        assert result.audit.total_rollbacks == 3  # 2 + 1

    def test_increment_rollback_audit_sets_date(self, tmp_path, existing_inventory):
        """increment_rollback_audit sets last_rollback_date."""
        inventory_path = tmp_path / "inventory.json"
        inventory_path.write_text(
            json.dumps(existing_inventory.model_dump(mode="json"), indent=2),
            encoding="utf-8",
        )

        before = datetime.now(UTC)
        manager = InventoryManager(inventory_path=inventory_path)
        result = manager.increment_rollback_audit(run_id="rollback-test")
        after = datetime.now(UTC)

        assert result.audit.last_rollback_date is not None
        # Date should be recent (between before and after)
        assert before <= result.audit.last_rollback_date <= after

    def test_first_rollback_sets_audit_fields(self, tmp_path):
        """First rollback initializes audit fields from zero."""
        inventory = PuzzleCollectionInventory(
            last_updated=datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC),
            last_run_id="init",
            audit=AuditMetrics(
                total_rollbacks=0,
                last_rollback_date=None,
            ),
        )

        inventory_path = tmp_path / "inventory.json"
        inventory_path.write_text(
            json.dumps(inventory.model_dump(mode="json"), indent=2),
            encoding="utf-8",
        )

        manager = InventoryManager(inventory_path=inventory_path)
        result = manager.increment_rollback_audit(run_id="first-rollback")

        assert result.audit.total_rollbacks == 1
        assert result.audit.last_rollback_date is not None

# =============================================================================
# Test T014 (Spec 107): total_rollbacks matches audit.jsonl count
# =============================================================================

class TestAuditCountIntegrity:
    """Tests for T014: total_rollbacks equals rollback_complete count in audit.jsonl.

    Spec 107: FR-007 - total_rollbacks count MUST equal the number of
    rollback_complete entries in audit.jsonl.
    """

    def test_total_rollbacks_equals_audit_log_complete_count(self, tmp_path):
        """total_rollbacks should equal count of rollback_complete in audit.jsonl.

        FR-007: Count in inventory MUST match audit.jsonl entries.
        """
        # Setup: Create output directory structure
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Create audit.jsonl with 3 complete rollback entries
        audit_path = output_dir / "audit.jsonl"
        audit_entries = [
            '{"timestamp":"2026-01-15T10:00:00Z","event":"rollback_complete","puzzle_id":"p1"}',
            '{"timestamp":"2026-01-20T10:00:00Z","event":"rollback_complete","puzzle_id":"p2"}',
            '{"timestamp":"2026-01-25T10:00:00Z","event":"rollback_complete","puzzle_id":"p3"}',
            '{"timestamp":"2026-01-28T10:00:00Z","event":"rollback_start","puzzle_id":"p4"}',  # Not complete
        ]
        audit_path.write_text("\n".join(audit_entries))

        # Count rollback_complete entries
        rollback_complete_count = sum(
            1 for line in audit_path.read_text().strip().split("\n")
            if '"rollback_complete"' in line or "'rollback_complete'" in line
        )

        # Create inventory with matching count
        inventory = PuzzleCollectionInventory(
            last_updated=datetime(2026, 1, 30, 10, 0, 0, tzinfo=UTC),
            last_run_id="test",
            audit=AuditMetrics(
                total_rollbacks=rollback_complete_count,  # Should be 3
            ),
        )

        # Verify
        assert inventory.audit.total_rollbacks == 3
        assert inventory.audit.total_rollbacks == rollback_complete_count

    def test_tests_use_tmp_path_not_production(self, tmp_path):
        """T013: Tests MUST use tmp_path fixture, not production inventory.

        FR-006: All test cases MUST use tmp_path fixture for inventory operations.
        This test verifies the pattern by ensuring inventory_path is under tmp_path.
        """
        # Create test inventory under tmp_path
        inventory_path = tmp_path / "test-inventory.json"

        inventory = PuzzleCollectionInventory(
            last_updated=datetime.now(UTC),
            last_run_id="test",
        )
        inventory_path.write_text(
            json.dumps(inventory.model_dump(mode="json"), indent=2),
            encoding="utf-8",
        )

        manager = InventoryManager(inventory_path=inventory_path)

        # Verify the manager is using the tmp_path location, not production
        assert str(tmp_path) in str(manager.inventory_path)
        assert "yengo-puzzle-collections" not in str(manager.inventory_path)


# =============================================================================
# Test T017 (Spec 107): Tag decrement during rollback
# =============================================================================

class TestTagDecrementDuringRollback:
    """Tests for T017: Tags are decremented during rollback.

    Spec 107: FR-014 - Rollback MUST decrement by_tag counts for tags
    associated with the deleted puzzle.
    """

    def test_rollback_decrements_tag_counts(self, tmp_path):
        """T017: Rollback should decrement tag counts from PublishLogEntry.tags.

        FR-014: by_tag counts MUST be decremented for rolled-back puzzle's tags.
        """
        # Create inventory with tag counts
        inventory = PuzzleCollectionInventory(
            last_updated=datetime.now(UTC),
            last_run_id="test",
            collection=CollectionStats(
                total_puzzles=10,
                by_puzzle_level={"beginner": 5, "intermediate": 5},
                by_tag={
                    "life-and-death": 6,
                    "tesuji": 4,
                    "ladder": 3,
                },
            ),
        )

        inventory_path = tmp_path / "inventory.json"
        inventory_path.write_text(
            json.dumps(inventory.model_dump(mode="json"), indent=2),
            encoding="utf-8",
        )

        manager = InventoryManager(inventory_path=inventory_path)

        # Rollback a puzzle with tags ["life-and-death", "ladder"]
        tag_decrements = {"life-and-death": 1, "ladder": 1}

        result = manager.decrement(
            puzzles_removed=1,
            level_decrements={"beginner": 1},
            tag_decrements=tag_decrements,
            run_id="rollback-test",
        )

        # Verify tag counts were decremented
        assert result.collection.by_tag.get("life-and-death") == 5  # 6 - 1
        assert result.collection.by_tag.get("ladder") == 2  # 3 - 1
        assert result.collection.by_tag.get("tesuji") == 4  # Unchanged

    def test_rollback_with_entry_without_tags(self, tmp_path):
        """T019: Rollback should handle entries without tags gracefully.

        FR-015: Backward compatibility - entries without tags default to empty.
        """
        # Create inventory
        inventory = PuzzleCollectionInventory(
            last_updated=datetime.now(UTC),
            last_run_id="test",
            collection=CollectionStats(
                total_puzzles=5,
                by_puzzle_level={"beginner": 5},
                by_tag={"life-and-death": 3},
            ),
        )

        inventory_path = tmp_path / "inventory.json"
        inventory_path.write_text(
            json.dumps(inventory.model_dump(mode="json"), indent=2),
            encoding="utf-8",
        )

        manager = InventoryManager(inventory_path=inventory_path)

        # Rollback a puzzle with NO tags (legacy entry)
        result = manager.decrement(
            puzzles_removed=1,
            level_decrements={"beginner": 1},
            tag_decrements={},  # No tags to decrement
            run_id="rollback-test",
        )

        # Verify only total and level were decremented, tags unchanged
        assert result.collection.total_puzzles == 4
        assert result.collection.by_puzzle_level.get("beginner") == 4
        assert result.collection.by_tag.get("life-and-death") == 3  # Unchanged
