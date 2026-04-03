"""
Tests for inventory rebuild from publish logs.

Tests for T048: Test rebuild from publish logs produces accurate counts.

Performance plan: Rebuild uses ONLY publish log metadata (level, tags, quality).
No SGF file reads. Ghost-check via upfront rglob set.
"""

import json
from pathlib import Path

import pytest

from backend.puzzle_manager.core.fs_utils import extract_level_from_path
from backend.puzzle_manager.inventory.rebuild import (
    rebuild_and_save,
    rebuild_inventory,
)

# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def publish_log_dir(tmp_path) -> Path:
    """Create a publish-log directory with sample entries.

    All fields are mandatory (clean-slate migration).
    """
    ops_dir = tmp_path / ".puzzle-inventory-state"
    ops_dir.mkdir(exist_ok=True)
    log_dir = ops_dir / "publish-log"
    log_dir.mkdir()

    # Create a day's worth of publish log entries with all mandatory fields
    entries = [
        {"run_id": "20260130-abc12345", "puzzle_id": "puzzle-001", "source_id": "ogs", "path": "sgf/beginner/batch-0001/puzzle-001.sgf", "quality": 3, "tags": ["life-and-death", "tesuji"], "trace_id": "trace001", "level": "beginner", "collections": []},
        {"run_id": "20260130-abc12345", "puzzle_id": "puzzle-002", "source_id": "ogs", "path": "sgf/beginner/batch-0001/puzzle-002.sgf", "quality": 2, "tags": ["life-and-death"], "trace_id": "trace002", "level": "beginner", "collections": []},
        {"run_id": "20260130-abc12345", "puzzle_id": "puzzle-003", "source_id": "ogs", "path": "sgf/intermediate/batch-0001/puzzle-003.sgf", "quality": 4, "tags": ["ko", "ladder"], "trace_id": "trace003", "level": "intermediate", "collections": []},
    ]

    log_file = log_dir / "2026-01-30.jsonl"
    with open(log_file, "w", encoding="utf-8") as f:
        for entry in entries:
            f.write(json.dumps(entry) + "\n")

    return log_dir


@pytest.fixture
def output_dir_with_sgf(tmp_path, publish_log_dir) -> Path:
    """Create output directory with publish logs and SGF files."""
    output_dir = tmp_path

    # Create SGF files with tags
    for puzzle_id, level, tags in [
        ("puzzle-001", "beginner", ["life-and-death", "tesuji"]),
        ("puzzle-002", "beginner", ["life-and-death"]),
        ("puzzle-003", "intermediate", ["ko", "ladder"]),
    ]:
        sgf_dir = output_dir / "sgf" / level / "batch-0001"
        sgf_dir.mkdir(parents=True, exist_ok=True)

        sgf_content = f"(;FF[4]GM[1]GN[{puzzle_id}]YT[{','.join(tags)}])"
        (sgf_dir / f"{puzzle_id}.sgf").write_text(sgf_content, encoding="utf-8")

    return output_dir


# =============================================================================
# Test extract_level_from_path
# =============================================================================

class TestExtractLevelFromPath:
    """Tests for extract_level_from_path helper."""

    def test_extracts_beginner_level(self):
        """Extracts 'beginner' level from path."""
        path = "sgf/beginner/batch-0001/puzzle-001.sgf"
        assert extract_level_from_path(path) == "beginner"

    def test_extracts_intermediate_level(self):
        """Extracts 'intermediate' level from path."""
        path = "sgf/intermediate/batch-0001/puzzle-002.sgf"
        assert extract_level_from_path(path) == "intermediate"

    def test_returns_none_for_invalid_path(self):
        """Returns None for invalid path format."""
        path = "invalid/path/puzzle.sgf"
        assert extract_level_from_path(path) is None

    def test_returns_none_for_empty_path(self):
        """Returns None for empty path."""
        assert extract_level_from_path("") is None


# =============================================================================
# Test T048: Rebuild produces accurate counts
# =============================================================================

class TestRebuildProducesAccurateCounts:
    """Tests for T048: rebuild from publish logs produces accurate counts."""

    def test_rebuild_counts_total_puzzles(self, output_dir_with_sgf):
        """Rebuild correctly counts total puzzles."""
        inventory = rebuild_inventory(output_dir=output_dir_with_sgf)

        assert inventory.collection.total_puzzles == 3

    def test_rebuild_counts_by_level(self, output_dir_with_sgf):
        """Rebuild correctly counts puzzles per level."""
        inventory = rebuild_inventory(output_dir=output_dir_with_sgf)

        assert inventory.collection.by_puzzle_level["beginner"] == 2
        assert inventory.collection.by_puzzle_level["intermediate"] == 1

    def test_rebuild_counts_by_tag(self, output_dir_with_sgf):
        """Rebuild correctly counts puzzles per tag from publish log metadata."""
        inventory = rebuild_inventory(output_dir=output_dir_with_sgf)

        # Tags come from publish log entries, not SGF files:
        # puzzle-001: life-and-death, tesuji
        # puzzle-002: life-and-death
        # puzzle-003: ko, ladder
        assert inventory.collection.by_tag["life-and-death"] == 2
        assert inventory.collection.by_tag["tesuji"] == 1
        assert inventory.collection.by_tag["ko"] == 1
        assert inventory.collection.by_tag["ladder"] == 1

    def test_rebuild_sets_run_id(self, output_dir_with_sgf):
        """Rebuild sets run_id."""
        inventory = rebuild_inventory(
            output_dir=output_dir_with_sgf,
            run_id="test-rebuild-123",
        )

        assert inventory.last_run_id == "test-rebuild-123"

    def test_rebuild_and_save_persists_inventory(self, output_dir_with_sgf, tmp_path):
        """rebuild_and_save persists inventory to file."""
        inventory_path = tmp_path / "inventory.json"

        rebuild_and_save(
            output_dir=output_dir_with_sgf,
            inventory_path=inventory_path,
        )

        assert inventory_path.exists()

        # Verify content
        data = json.loads(inventory_path.read_text(encoding="utf-8"))
        assert data["collection"]["total_puzzles"] == 3

    def test_rebuild_handles_empty_publish_log(self, tmp_path):
        """Rebuild handles empty publish log gracefully."""
        # Create empty publish-log directory under .puzzle-inventory-state/
        ops_dir = tmp_path / ".puzzle-inventory-state"
        ops_dir.mkdir()
        log_dir = ops_dir / "publish-log"
        log_dir.mkdir()

        inventory = rebuild_inventory(output_dir=tmp_path)

        assert inventory.collection.total_puzzles == 0
        assert inventory.collection.by_puzzle_level == {}
        assert inventory.collection.by_tag == {}

    def test_rebuild_handles_missing_sgf_files(self, publish_log_dir):
        """Rebuild skips entries with missing SGF files (ghost entries).

        Ghost entries (deleted files) are detected via upfront rglob.
        """
        # SGF files don't exist, but publish log does
        output_dir = publish_log_dir.parent.parent  # .puzzle-inventory-state is under output_dir

        inventory = rebuild_inventory(output_dir=output_dir)

        # Ghost entries (missing files) are skipped
        # Since all 3 entries have missing files, count should be 0
        assert inventory.collection.total_puzzles == 0
        assert inventory.collection.by_puzzle_level == {}

        # Tags should also be empty (entries skipped)
        assert inventory.collection.by_tag == {}


# =============================================================================
# Spec 102, T032: Test rebuild reconstructs quality breakdown
# =============================================================================

class TestRebuildQualityBreakdown:
    """Tests for quality breakdown reconstruction during rebuild (Spec 102)."""

    @pytest.fixture
    def publish_log_with_quality(self, tmp_path) -> Path:
        """Create publish log with quality field AND corresponding SGF files."""
        ops_dir = tmp_path / ".puzzle-inventory-state"
        ops_dir.mkdir()
        log_dir = ops_dir / "publish-log"
        log_dir.mkdir()

        entries = [
            {"run_id": "test", "puzzle_id": "p1", "source_id": "ogs", "path": "sgf/beginner/batch-0001/p1.sgf", "quality": 3, "tags": ["life-and-death"], "trace_id": "t1", "level": "beginner", "collections": []},
            {"run_id": "test", "puzzle_id": "p2", "source_id": "ogs", "path": "sgf/beginner/batch-0001/p2.sgf", "quality": 4, "tags": ["tesuji"], "trace_id": "t2", "level": "beginner", "collections": []},
            {"run_id": "test", "puzzle_id": "p3", "source_id": "ogs", "path": "sgf/beginner/batch-0001/p3.sgf", "quality": 3, "tags": ["ko"], "trace_id": "t3", "level": "beginner", "collections": []},
            {"run_id": "test", "puzzle_id": "p4", "source_id": "ogs", "path": "sgf/beginner/batch-0001/p4.sgf", "quality": 5, "tags": [], "trace_id": "t4", "level": "beginner", "collections": []},
            {"run_id": "test", "puzzle_id": "p5", "source_id": "ogs", "path": "sgf/beginner/batch-0001/p5.sgf", "quality": 2, "tags": [], "trace_id": "t5", "level": "beginner", "collections": []},
        ]

        log_file = log_dir / "2026-01-30.jsonl"
        with open(log_file, "w", encoding="utf-8") as f:
            for entry in entries:
                f.write(json.dumps(entry) + "\n")

        # Spec 107: Create corresponding SGF files so entries aren't skipped as ghosts
        sgf_dir = tmp_path / "sgf/beginner/batch-0001"
        sgf_dir.mkdir(parents=True)
        sgf_content = "(;FF[4]GM[1]SZ[19]YG[beginner]YT[life-and-death])"
        for entry in entries:
            (tmp_path / entry["path"]).write_text(sgf_content, encoding="utf-8")

        return tmp_path

    def test_rebuild_reconstructs_quality_breakdown(self, publish_log_with_quality):
        """Rebuild correctly aggregates quality from publish log entries."""
        inventory = rebuild_inventory(output_dir=publish_log_with_quality)

        assert inventory.collection.by_puzzle_quality["2"] == 1
        assert inventory.collection.by_puzzle_quality["3"] == 2
        assert inventory.collection.by_puzzle_quality["4"] == 1
        assert inventory.collection.by_puzzle_quality["5"] == 1
        assert inventory.collection.by_puzzle_quality["1"] == 0  # None had quality 1

    def test_rebuild_uses_quality_from_publish_log(self, tmp_path):
        """Rebuild uses mandatory quality field from publish log entries."""
        ops_dir = tmp_path / ".puzzle-inventory-state"
        ops_dir.mkdir()
        log_dir = ops_dir / "publish-log"
        log_dir.mkdir()

        entries = [
            {"run_id": "test", "puzzle_id": "p1", "source_id": "ogs", "path": "sgf/beginner/batch-0001/p1.sgf", "quality": 1, "tags": [], "trace_id": "t1", "level": "beginner", "collections": []},
            {"run_id": "test", "puzzle_id": "p2", "source_id": "ogs", "path": "sgf/beginner/batch-0001/p2.sgf", "quality": 1, "tags": [], "trace_id": "t2", "level": "beginner", "collections": []},
            {"run_id": "test", "puzzle_id": "p3", "source_id": "ogs", "path": "sgf/beginner/batch-0001/p3.sgf", "quality": 3, "tags": [], "trace_id": "t3", "level": "beginner", "collections": []},
        ]

        log_file = log_dir / "2026-01-30.jsonl"
        with open(log_file, "w", encoding="utf-8") as f:
            for entry in entries:
                f.write(json.dumps(entry) + "\n")

        sgf_dir = tmp_path / "sgf/beginner/batch-0001"
        sgf_dir.mkdir(parents=True)
        sgf_content = "(;FF[4]GM[1]SZ[19]YG[beginner])"
        for entry in entries:
            (tmp_path / entry["path"]).write_text(sgf_content, encoding="utf-8")

        inventory = rebuild_inventory(output_dir=tmp_path)

        assert inventory.collection.by_puzzle_quality["1"] == 2
        assert inventory.collection.by_puzzle_quality["3"] == 1

    def test_rebuild_initializes_all_quality_keys(self, tmp_path):
        """Rebuild initializes all quality keys 1-5 even if some are zero."""
        ops_dir = tmp_path / ".puzzle-inventory-state"
        ops_dir.mkdir()
        log_dir = ops_dir / "publish-log"
        log_dir.mkdir()

        # Only one entry with quality 3
        entries = [
            {"run_id": "test", "puzzle_id": "p1", "source_id": "ogs", "path": "sgf/beginner/batch-0001/p1.sgf", "quality": 3, "tags": [], "trace_id": "t1", "level": "beginner", "collections": []},
        ]

        log_file = log_dir / "2026-01-30.jsonl"
        with open(log_file, "w", encoding="utf-8") as f:
            for entry in entries:
                f.write(json.dumps(entry) + "\n")

        # Spec 107: Create corresponding SGF file
        sgf_dir = tmp_path / "sgf/beginner/batch-0001"
        sgf_dir.mkdir(parents=True)
        (sgf_dir / "p1.sgf").write_text("(;FF[4]GM[1]SZ[19]YG[beginner])", encoding="utf-8")

        inventory = rebuild_inventory(output_dir=tmp_path)

        # All keys should be present
        assert "1" in inventory.collection.by_puzzle_quality
        assert "2" in inventory.collection.by_puzzle_quality
        assert "3" in inventory.collection.by_puzzle_quality
        assert "4" in inventory.collection.by_puzzle_quality
        assert "5" in inventory.collection.by_puzzle_quality

        # Only quality 3 should have count
        assert inventory.collection.by_puzzle_quality["3"] == 1
        assert inventory.collection.by_puzzle_quality["1"] == 0
        assert inventory.collection.by_puzzle_quality["2"] == 0
        assert inventory.collection.by_puzzle_quality["4"] == 0
        assert inventory.collection.by_puzzle_quality["5"] == 0


# =============================================================================
# Test T020 (Spec 107): Rebuild skips ghost entries
# =============================================================================

class TestRebuildSkipsGhostEntries:
    """Tests for T020: Rebuild skips publish log entries without corresponding SGF.

    Spec 107: FR-012 - Rebuild operation MUST skip publish log entries
    where the referenced SGF file doesn't exist (ghost entries from rollbacks).
    """

    def test_rebuild_skips_missing_sgf_files(self, tmp_path):
        """T020: Rebuild should skip entries where SGF file doesn't exist.

        FR-012: Ghost entries (deleted files) MUST NOT be counted.
        """
        # Setup: Create publish log dir with entries under .puzzle-inventory-state/
        ops_dir = tmp_path / ".puzzle-inventory-state"
        ops_dir.mkdir()
        log_dir = ops_dir / "publish-log"
        log_dir.mkdir()

        # Two entries: one with file, one without (ghost)
        entries = [
            {"run_id": "test", "puzzle_id": "p1", "source_id": "ogs", "path": "sgf/beginner/batch-0001/p1.sgf", "quality": 2, "tags": ["life-and-death"], "trace_id": "t1", "level": "beginner", "collections": []},
            {"run_id": "test", "puzzle_id": "p2", "source_id": "ogs", "path": "sgf/beginner/batch-0001/p2.sgf", "quality": 2, "tags": [], "trace_id": "t2", "level": "beginner", "collections": []},  # Ghost
            {"run_id": "test", "puzzle_id": "p3", "source_id": "ogs", "path": "sgf/intermediate/batch-0001/p3.sgf", "quality": 3, "tags": ["ko"], "trace_id": "t3", "level": "intermediate", "collections": []},
        ]

        log_file = log_dir / "2026-01-30.jsonl"
        with open(log_file, "w", encoding="utf-8") as f:
            for entry in entries:
                f.write(json.dumps(entry) + "\n")

        # Create SGF files for p1 and p3 ONLY (p2 is ghost)
        sgf_content = "(;FF[4]GM[1]SZ[19]YG[beginner]YT[life-and-death])"

        p1_path = tmp_path / "sgf/beginner/batch-0001"
        p1_path.mkdir(parents=True)
        (p1_path / "p1.sgf").write_text(sgf_content, encoding="utf-8")

        p3_path = tmp_path / "sgf/intermediate/batch-0001"
        p3_path.mkdir(parents=True)
        (p3_path / "p3.sgf").write_text("(;FF[4]GM[1]SZ[19]YG[intermediate]YT[ko])", encoding="utf-8")

        # Rebuild
        inventory = rebuild_inventory(output_dir=tmp_path)

        # Should count only existing files (p1 and p3, not ghost p2)
        assert inventory.collection.total_puzzles == 2
        assert inventory.collection.by_puzzle_level.get("beginner") == 1  # p1 only
        assert inventory.collection.by_puzzle_level.get("intermediate") == 1  # p3 only

    def test_rebuild_with_all_ghost_entries(self, tmp_path):
        """Rebuild with ALL ghost entries should produce zero counts."""
        ops_dir = tmp_path / ".puzzle-inventory-state"
        ops_dir.mkdir()
        log_dir = ops_dir / "publish-log"
        log_dir.mkdir()

        # All entries are ghosts (no corresponding files)
        entries = [
            {"run_id": "test", "puzzle_id": "ghost1", "source_id": "ogs", "path": "sgf/beginner/batch-0001/ghost1.sgf", "quality": 2, "tags": [], "trace_id": "tg1", "level": "beginner", "collections": []},
            {"run_id": "test", "puzzle_id": "ghost2", "source_id": "ogs", "path": "sgf/beginner/batch-0001/ghost2.sgf", "quality": 2, "tags": [], "trace_id": "tg2", "level": "beginner", "collections": []},
        ]

        log_file = log_dir / "2026-01-30.jsonl"
        with open(log_file, "w", encoding="utf-8") as f:
            for entry in entries:
                f.write(json.dumps(entry) + "\n")

        # Don't create any SGF files
        inventory = rebuild_inventory(output_dir=tmp_path)

        # All are ghosts, so counts should be zero
        assert inventory.collection.total_puzzles == 0
        assert inventory.collection.by_puzzle_level == {}
        assert inventory.collection.by_tag == {}
