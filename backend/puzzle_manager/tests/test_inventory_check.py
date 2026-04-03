"""
Tests for inventory integrity check functionality.

Tests for T022-T027 (Spec 107 - US4):
- T022: Integrity check passes when all counts match
- T023: Detects total_puzzles mismatch
- T024: Detects level count mismatch
- T025: Detects orphan entries (log entries without files)
- T026: Detects orphan files (files without log entries)
- T027: --fix flag runs rebuild
"""

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from backend.puzzle_manager.inventory.models import (
    CollectionStats,
    PuzzleCollectionInventory,
)

# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def consistent_setup(tmp_path) -> tuple[Path, PuzzleCollectionInventory]:
    """Create a consistent setup where inventory matches actual files.

    Returns (output_dir, inventory) where all counts are consistent.
    Spec 107: Publish log is now under .puzzle-inventory-state/
    """
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    # Create ops dir and publish-log directory (Spec 107)
    ops_dir = output_dir / ".puzzle-inventory-state"
    ops_dir.mkdir()
    log_dir = ops_dir / "publish-log"
    log_dir.mkdir()

    # Create 3 publish log entries
    entries = [
        {"run_id": "test", "puzzle_id": "p1", "source_id": "ogs", "path": "sgf/beginner/2026/01/batch-001/p1.sgf", "tags": ["life-and-death"], "quality": 1, "trace_id": "t1", "level": "beginner", "collections": []},
        {"run_id": "test", "puzzle_id": "p2", "source_id": "ogs", "path": "sgf/beginner/2026/01/batch-001/p2.sgf", "tags": ["life-and-death"], "quality": 1, "trace_id": "t2", "level": "beginner", "collections": []},
        {"run_id": "test", "puzzle_id": "p3", "source_id": "ogs", "path": "sgf/intermediate/2026/01/batch-001/p3.sgf", "tags": ["ko"], "quality": 1, "trace_id": "t3", "level": "intermediate", "collections": []},
    ]

    log_file = log_dir / "2026-01-30.jsonl"
    with open(log_file, "w", encoding="utf-8") as f:
        for entry in entries:
            f.write(json.dumps(entry) + "\n")

    # Create SGF files matching the entries
    sgf_content = "(;FF[4]GM[1]SZ[19]YG[beginner]YT[life-and-death])"

    beginner_dir = output_dir / "sgf/beginner/2026/01/batch-001"
    beginner_dir.mkdir(parents=True)
    (beginner_dir / "p1.sgf").write_text(sgf_content, encoding="utf-8")
    (beginner_dir / "p2.sgf").write_text(sgf_content, encoding="utf-8")

    intermediate_dir = output_dir / "sgf/intermediate/2026/01/batch-001"
    intermediate_dir.mkdir(parents=True)
    (intermediate_dir / "p3.sgf").write_text(
        "(;FF[4]GM[1]SZ[19]YG[intermediate]YT[ko])",
        encoding="utf-8"
    )

    # Create matching inventory
    inventory = PuzzleCollectionInventory(
        last_updated=datetime.now(UTC),
        last_run_id="test",
        collection=CollectionStats(
            total_puzzles=3,
            by_puzzle_level={"beginner": 2, "intermediate": 1},
            by_tag={"life-and-death": 2, "ko": 1},
        ),
    )

    return output_dir, inventory


@pytest.fixture
def inconsistent_total_setup(consistent_setup) -> tuple[Path, PuzzleCollectionInventory]:
    """Setup where total_puzzles doesn't match actual count."""
    output_dir, inventory = consistent_setup

    # Corrupt the total (says 5 but only 3 files)
    corrupted = PuzzleCollectionInventory(
        last_updated=inventory.last_updated,
        last_run_id=inventory.last_run_id,
        collection=CollectionStats(
            total_puzzles=5,  # Wrong! Should be 3
            by_puzzle_level=inventory.collection.by_puzzle_level,
            by_tag=inventory.collection.by_tag,
        ),
    )

    return output_dir, corrupted


@pytest.fixture
def inconsistent_level_setup(consistent_setup) -> tuple[Path, PuzzleCollectionInventory]:
    """Setup where by_puzzle_level doesn't match actual files."""
    output_dir, inventory = consistent_setup

    # Corrupt level counts (says 4 beginner but only 2 files)
    corrupted = PuzzleCollectionInventory(
        last_updated=inventory.last_updated,
        last_run_id=inventory.last_run_id,
        collection=CollectionStats(
            total_puzzles=3,
            by_puzzle_level={"beginner": 4, "intermediate": 1},  # beginner is wrong!
            by_tag=inventory.collection.by_tag,
        ),
    )

    return output_dir, corrupted


@pytest.fixture
def orphan_entry_setup(tmp_path) -> tuple[Path, PuzzleCollectionInventory]:
    """Setup with a publish log entry but missing SGF file (ghost/orphan entry)."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    ops_dir = output_dir / ".puzzle-inventory-state"
    ops_dir.mkdir()
    log_dir = ops_dir / "publish-log"
    log_dir.mkdir()

    # Entry for file that doesn't exist
    entries = [
        {"run_id": "test", "puzzle_id": "ghost", "source_id": "ogs", "path": "sgf/beginner/2026/01/batch-001/ghost.sgf", "tags": [], "quality": 1, "trace_id": "t1", "level": "beginner", "collections": []},
    ]

    log_file = log_dir / "2026-01-30.jsonl"
    with open(log_file, "w", encoding="utf-8") as f:
        for entry in entries:
            f.write(json.dumps(entry) + "\n")

    # DON'T create the SGF file (ghost entry)

    inventory = PuzzleCollectionInventory(
        last_updated=datetime.now(UTC),
        last_run_id="test",
        collection=CollectionStats(
            total_puzzles=1,  # Claims 1 but file doesn't exist
            by_puzzle_level={"beginner": 1},
        ),
    )

    return output_dir, inventory


@pytest.fixture
def orphan_file_setup(tmp_path) -> tuple[Path, PuzzleCollectionInventory]:
    """Setup with SGF file but no publish log entry (orphan file)."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    ops_dir = output_dir / ".puzzle-inventory-state"
    ops_dir.mkdir()
    log_dir = ops_dir / "publish-log"
    log_dir.mkdir()

    # Empty publish log (no entries)
    log_file = log_dir / "2026-01-30.jsonl"
    log_file.touch()

    # But create an SGF file anyway (orphan)
    orphan_dir = output_dir / "sgf/beginner/2026/01/batch-001"
    orphan_dir.mkdir(parents=True)
    (orphan_dir / "orphan.sgf").write_text(
        "(;FF[4]GM[1]SZ[19]YG[beginner]YT[tesuji])",
        encoding="utf-8"
    )

    inventory = PuzzleCollectionInventory(
        last_updated=datetime.now(UTC),
        last_run_id="test",
        collection=CollectionStats(
            total_puzzles=0,  # No log entries
            by_puzzle_level={},
        ),
    )

    return output_dir, inventory


# =============================================================================
# Test T022: Integrity check passes when all counts match
# =============================================================================

class TestIntegrityCheckPassing:
    """Tests for T022: check_integrity() returns valid when consistent."""

    def test_integrity_passes_with_consistent_data(self, consistent_setup):
        """T022: Integrity check should pass when inventory matches files.

        FR-018: Check operation MUST verify total_puzzles matches actual file count.
        FR-019: Check operation MUST verify by_puzzle_level matches files.
        """
        from backend.puzzle_manager.inventory.check import check_integrity

        output_dir, inventory = consistent_setup

        result = check_integrity(output_dir=output_dir, inventory=inventory)

        assert result.is_valid is True
        assert len(result.discrepancies) == 0
        assert result.total_expected == 3
        assert result.total_actual == 3


# =============================================================================
# Test T023: Detecting total_puzzles mismatch
# =============================================================================

class TestTotalPuzzlesMismatch:
    """Tests for T023: check_integrity() detects total_puzzles mismatch."""

    def test_detects_total_mismatch(self, inconsistent_total_setup):
        """T023: Should detect when total_puzzles is wrong.

        FR-018: total_puzzles mismatch MUST be reported.
        """
        from backend.puzzle_manager.inventory.check import check_integrity

        output_dir, inventory = inconsistent_total_setup

        result = check_integrity(output_dir=output_dir, inventory=inventory)

        assert result.is_valid is False
        assert result.total_expected == 5  # What inventory claims
        assert result.total_actual == 3    # What actually exists

        # Should have a discrepancy for total
        total_discrepancies = [d for d in result.discrepancies if "total" in d.lower()]
        assert len(total_discrepancies) >= 1


# =============================================================================
# Test T024: Detecting level count mismatch
# =============================================================================

class TestLevelCountMismatch:
    """Tests for T024: check_integrity() detects level count mismatch."""

    def test_detects_level_mismatch(self, inconsistent_level_setup):
        """T024: Should detect when by_puzzle_level count is wrong.

        FR-019: Level count mismatch MUST be reported.
        """
        from backend.puzzle_manager.inventory.check import check_integrity

        output_dir, inventory = inconsistent_level_setup

        result = check_integrity(output_dir=output_dir, inventory=inventory)

        assert result.is_valid is False

        # Should detect beginner level mismatch
        level_discrepancies = [d for d in result.discrepancies if "beginner" in d.lower()]
        assert len(level_discrepancies) >= 1


# =============================================================================
# Test T025: Detecting orphan entries
# =============================================================================

class TestOrphanEntryDetection:
    """Tests for T025: check_integrity() detects orphan publish log entries."""

    def test_detects_orphan_entries(self, orphan_entry_setup):
        """T025: Should detect publish log entries without corresponding files.

        FR-020: Orphan entries (log entries without files) MUST be reported.
        """
        from backend.puzzle_manager.inventory.check import check_integrity

        output_dir, inventory = orphan_entry_setup

        result = check_integrity(output_dir=output_dir, inventory=inventory)

        assert result.is_valid is False
        assert len(result.orphan_entries) >= 1
        assert "ghost" in result.orphan_entries[0] or "ghost.sgf" in result.orphan_entries[0]


# =============================================================================
# Test T026: Detecting orphan files
# =============================================================================

class TestOrphanFileDetection:
    """Tests for T026: check_integrity() detects orphan SGF files."""

    def test_detects_orphan_files(self, orphan_file_setup):
        """T026: Should detect SGF files without publish log entries.

        FR-021: Orphan files (files without log entries) MUST be reported.
        """
        from backend.puzzle_manager.inventory.check import check_integrity

        output_dir, inventory = orphan_file_setup

        result = check_integrity(output_dir=output_dir, inventory=inventory)

        # Note: orphan files may not invalidate integrity check
        # (they just indicate unpublished files), but should be reported
        assert len(result.orphan_files) >= 1
        # The orphan file should be in the list
        orphan_paths = [str(p) for p in result.orphan_files]
        assert any("orphan.sgf" in p for p in orphan_paths)


# =============================================================================
# Test T027: --fix flag runs rebuild
# =============================================================================

class TestFixFlagRunsRebuild:
    """Tests for T027: --fix flag triggers rebuild_inventory()."""

    def test_fix_flag_calls_rebuild(self, inconsistent_total_setup):
        """T027: --fix flag should run rebuild_inventory to fix discrepancies.

        FR-024: --fix flag MUST trigger rebuild operation.
        """
        from backend.puzzle_manager.inventory.check import check_integrity, fix_integrity

        output_dir, inventory = inconsistent_total_setup

        # First verify it's broken
        result = check_integrity(output_dir=output_dir, inventory=inventory)
        assert result.is_valid is False

        # Now fix it
        fixed_inventory = fix_integrity(output_dir=output_dir, run_id="fix-test")

        # Verify it's now correct
        assert fixed_inventory.collection.total_puzzles == 3  # Actual file count

        # Re-check should pass
        result_after = check_integrity(output_dir=output_dir, inventory=fixed_inventory)
        assert result_after.is_valid is True
