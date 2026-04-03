"""
Tests for inventory file protection during cleanup operations.

Tests for T039-T041:
- T039: Test log cleanup preserves inventory file
- T040: Test staging cleanup preserves inventory file
- T041: Test runtime cleanup preserves inventory file
"""

import json
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from backend.puzzle_manager.inventory.models import (
    AuditMetrics,
    CollectionStats,
    PuzzleCollectionInventory,
)
from backend.puzzle_manager.pipeline.cleanup import (
    PROTECTED_FILES,
    cleanup_old_files,
    cleanup_target,
)

# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def inventory_data() -> dict:
    """Create inventory data for testing."""
    inventory = PuzzleCollectionInventory(
        schema_version="1.0.0",
        last_updated=datetime(2026, 1, 30, 10, 0, 0, tzinfo=UTC),
        last_run_id="2026-01-30_abc123",
        collection=CollectionStats(
            total_puzzles=100,
            by_puzzle_level={"beginner": 50, "intermediate": 50},
            by_tag={"life-and-death": 100},
        ),
        audit=AuditMetrics(total_rollbacks=0),
    )
    return inventory.model_dump(mode="json")


@pytest.fixture
def output_dir_with_inventory(tmp_path, inventory_data) -> Path:
    """Create output directory with inventory file."""
    output_dir = tmp_path / "yengo-puzzle-collections"
    output_dir.mkdir(parents=True)

    # Create inventory file
    inventory_path = output_dir / "puzzle-collection-inventory.json"
    inventory_path.write_text(
        json.dumps(inventory_data, indent=2),
        encoding="utf-8",
    )

    # Create some other files that should be cleaned
    sgf_dir = output_dir / "sgf" / "beginner" / "2026" / "01"
    sgf_dir.mkdir(parents=True)
    (sgf_dir / "test-puzzle.sgf").write_text("(;FF[4]GM[1])")

    views_dir = output_dir / "views" / "by-level"
    views_dir.mkdir(parents=True)
    (views_dir / "beginner.json").write_text("[]")

    return output_dir


# =============================================================================
# Test PROTECTED_FILES constant exists
# =============================================================================

class TestProtectedFilesConstant:
    """Tests for PROTECTED_FILES constant."""

    def test_protected_files_exists(self):
        """PROTECTED_FILES constant should exist."""
        assert hasattr(__import__("backend.puzzle_manager.pipeline.cleanup", fromlist=["PROTECTED_FILES"]), "PROTECTED_FILES")

    def test_inventory_file_in_protected_list(self):
        """Inventory file should be in PROTECTED_FILES."""
        assert "puzzle-collection-inventory.json" in PROTECTED_FILES


# =============================================================================
# Test T039: Log cleanup preserves inventory file
# =============================================================================

class TestLogCleanupPreservesInventory:
    """Tests for T039: log cleanup preserves inventory file."""

    def test_cleanup_old_files_preserves_inventory(
        self, tmp_path, output_dir_with_inventory
    ):
        """cleanup_old_files does not delete inventory file."""
        inventory_path = output_dir_with_inventory / "puzzle-collection-inventory.json"
        assert inventory_path.exists()

        # Mock the output_dir to use our test directory
        with patch(
            "backend.puzzle_manager.pipeline.cleanup.get_output_dir",
            return_value=output_dir_with_inventory,
        ), patch(
            "backend.puzzle_manager.pipeline.cleanup.get_logs_dir",
            return_value=tmp_path / "logs",
        ), patch(
            "backend.puzzle_manager.pipeline.cleanup.get_pm_state_dir",
            return_value=tmp_path / "state",
        ), patch(
            "backend.puzzle_manager.pipeline.cleanup.get_pm_staging_dir",
            return_value=tmp_path / "staging",
        ), patch(
            "backend.puzzle_manager.pipeline.cleanup.get_pm_raw_dir",
            return_value=tmp_path / "raw",
        ):
            cleanup_old_files(retention_days=0)

        # Inventory should still exist
        assert inventory_path.exists()


# =============================================================================
# Test T040: Staging cleanup preserves inventory file
# =============================================================================

class TestStagingCleanupPreservesInventory:
    """Tests for T040: staging cleanup preserves inventory file."""

    def test_cleanup_target_staging_preserves_inventory(
        self, tmp_path, output_dir_with_inventory
    ):
        """cleanup_target('staging') does not delete inventory file."""
        inventory_path = output_dir_with_inventory / "puzzle-collection-inventory.json"
        assert inventory_path.exists()

        # Create a staging dir with some files
        staging_dir = tmp_path / "staging"
        staging_dir.mkdir()
        (staging_dir / "temp.sgf").write_text("(;FF[4])")

        with patch(
            "backend.puzzle_manager.pipeline.cleanup.get_pm_staging_dir",
            return_value=staging_dir,
        ):
            cleanup_target("staging")

        # Staging file should be deleted
        assert not (staging_dir / "temp.sgf").exists()
        # But inventory should still exist
        assert inventory_path.exists()


# =============================================================================
# Test T041: Runtime/collection cleanup preserves inventory file
# =============================================================================

class TestRuntimeCleanupPreservesInventory:
    """Tests for T041: runtime cleanup preserves inventory file."""

    def test_cleanup_target_puzzles_collection_preserves_inventory(
        self, output_dir_with_inventory
    ):
        """cleanup_target('puzzles-collection') preserves inventory file."""
        inventory_path = output_dir_with_inventory / "puzzle-collection-inventory.json"
        sgf_path = output_dir_with_inventory / "sgf" / "beginner" / "2026" / "01" / "test-puzzle.sgf"

        assert inventory_path.exists()
        assert sgf_path.exists()

        with patch(
            "backend.puzzle_manager.pipeline.cleanup.get_output_dir",
            return_value=output_dir_with_inventory,
        ):
            cleanup_target("puzzles-collection", dry_run=False)

        # SGF file should be deleted
        assert not sgf_path.exists()
        # But inventory should still exist
        assert inventory_path.exists()

    def test_cleanup_preserves_inventory_even_in_dry_run(
        self, output_dir_with_inventory
    ):
        """Dry run should still show inventory as protected."""
        inventory_path = output_dir_with_inventory / "puzzle-collection-inventory.json"

        with patch(
            "backend.puzzle_manager.pipeline.cleanup.get_output_dir",
            return_value=output_dir_with_inventory,
        ):
            cleanup_target("puzzles-collection", dry_run=True)

        # Inventory should NOT be counted in files to delete
        # (implementation detail: inventory is protected)
        assert inventory_path.exists()
