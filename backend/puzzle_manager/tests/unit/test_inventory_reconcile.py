"""
Tests for inventory reconciliation.
"""


import pytest

from backend.puzzle_manager.inventory.manager import InventoryManager
from backend.puzzle_manager.inventory.reconcile import reconcile_inventory


@pytest.fixture
def manager(tmp_path):
    # Setup inventory path
    ops_dir = tmp_path / ".puzzle-inventory-state"
    ops_dir.mkdir()
    inventory_path = ops_dir / "inventory.json"
    return InventoryManager(inventory_path=inventory_path)

def test_reconcile_from_disk(tmp_path):
    """Test full inventory reconciliation from SGF files."""
    # Setup SGF structure
    sgf_dir = tmp_path / "sgf"
    sgf_dir.mkdir()

    # 1. Beginner puzzle with tags and quality
    (sgf_dir / "beginner").mkdir()
    (sgf_dir / "beginner" / "puz1.sgf").write_text(
        "(;FF[4]GM[1]YT[ko,life-and-death]YQ[q:3;rc:0])",
        encoding="utf-8"
    )

    # 2. Intermediate puzzle with tags and quality
    (sgf_dir / "intermediate").mkdir()
    (sgf_dir / "intermediate" / "puz2.sgf").write_text(
        "(;FF[4]GM[1]YT[joseki]YQ[q:5])",
        encoding="utf-8"
    )

    # 3. Nested puzzle (should be found)
    (sgf_dir / "novice" / "batch1").mkdir(parents=True)
    (sgf_dir / "novice" / "batch1" / "puz3.sgf").write_text(
        "(;FF[4]GM[1]YT[atari])", # No quality -> default 1
        encoding="utf-8"
    )

    # Run reconcile
    final_inventory = reconcile_inventory(output_dir=tmp_path, run_id="test-reconcile")

    # Assertions
    collection = final_inventory.collection

    # Totals
    assert collection.total_puzzles == 3

    # Levels
    assert collection.by_puzzle_level["beginner"] == 1
    assert collection.by_puzzle_level["intermediate"] == 1
    assert collection.by_puzzle_level["novice"] == 1

    # Tags
    assert collection.by_tag["ko"] == 1
    assert collection.by_tag["joseki"] == 1
    assert collection.by_tag["atari"] == 1
    assert collection.by_tag["life-and-death"] == 1

    # Quality
    assert collection.by_puzzle_quality.get("3") == 1
    assert collection.by_puzzle_quality.get("5") == 1
    assert collection.by_puzzle_quality.get("1", 0) == 1 # Default

def test_reconcile_resets_metrics(manager, tmp_path):
    """Test that reconcile creates fresh inventory (metrics are reset)."""
    # Create valid inventory with existing metrics
    empty = manager.create_empty("setup")
    empty.stages.ingest.attempted = 100
    empty.audit.total_rollbacks = 5
    manager.save(empty)

    # Create dummy SGF dir so reconcile doesn't fail
    (tmp_path / "sgf").mkdir()

    # Reconcile rebuilds from scratch
    final = reconcile_inventory(output_dir=tmp_path, run_id="reconcile")

    # Reconcile creates fresh inventory — metrics are reset to defaults
    assert final.stages.ingest.attempted == 0
    assert final.audit.total_rollbacks == 0
    assert final.collection.total_puzzles == 0
