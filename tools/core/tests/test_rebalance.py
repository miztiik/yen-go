"""
Tests for tools.core.rebalance module.

Covers:
- File cataloging with gaps and non-sequential IDs
- Move computation (minimal moves, already-balanced case)
- Full rebalance end-to-end (dry-run and execute)
- Padding width auto-detection
- Checkpoint update preserving existing fields
- Edge cases: empty dir, single file, exact batch boundaries
"""

import json
from pathlib import Path

import pytest

from tools.core.rebalance import (
    Move,
    RebalanceResult,
    batch_name,
    catalog_files,
    compute_moves,
    detect_pad_width,
    execute_moves,
    rebalance,
    remove_empty_batch_dirs,
    update_checkpoint,
)

# ==============================
# Fixtures
# ==============================


def _create_sgf_files(
    sgf_dir: Path,
    batch_layout: dict[str, list[int]],
) -> int:
    """Helper: create batch directories with numbered .sgf files.

    Args:
        sgf_dir: Parent directory for batches.
        batch_layout: {batch_name: [puzzle_ids]} mapping.

    Returns:
        Total number of files created.
    """
    total = 0
    for bname, ids in batch_layout.items():
        batch_dir = sgf_dir / bname
        batch_dir.mkdir(parents=True, exist_ok=True)
        for pid in ids:
            (batch_dir / f"{pid}.sgf").write_text(f"(;GM[1]SZ[19]GN[{pid}])")
            total += 1
    return total


@pytest.fixture
def empty_sgf_dir(tmp_path: Path) -> Path:
    sgf_dir = tmp_path / "sgf"
    sgf_dir.mkdir()
    return sgf_dir


@pytest.fixture
def balanced_small(tmp_path: Path) -> Path:
    """3 files, batch_size=3 → all in batch-001, no moves needed."""
    sgf_dir = tmp_path / "sgf"
    _create_sgf_files(sgf_dir, {"batch-001": [10, 20, 30]})
    return sgf_dir


@pytest.fixture
def unbalanced(tmp_path: Path) -> Path:
    """6 files in one batch, batch_size=3 → should split to 2 batches."""
    sgf_dir = tmp_path / "sgf"
    _create_sgf_files(sgf_dir, {"batch-001": [5, 10, 15, 20, 25, 30]})
    return sgf_dir


@pytest.fixture
def multi_batch_unbalanced(tmp_path: Path) -> Path:
    """Files spread across 3 batches unevenly, needs rebalancing to 2."""
    sgf_dir = tmp_path / "sgf"
    _create_sgf_files(sgf_dir, {
        "batch-001": [1, 2, 3, 4, 5],  # 5 files
        "batch-002": [6],               # 1 file
        "batch-003": [7, 8, 9, 10],     # 4 files
    })
    return sgf_dir


@pytest.fixture
def gappy_ids(tmp_path: Path) -> Path:
    """Files with large gaps in IDs — simulates real goproblems data."""
    sgf_dir = tmp_path / "sgf"
    _create_sgf_files(sgf_dir, {
        "batch-001": [5, 100, 200, 500, 1000],
        "batch-002": [2000, 5000, 8000],
    })
    return sgf_dir


# ==============================
# detect_pad_width
# ==============================


class TestDetectPadWidth:
    def test_3digit_padding(self, tmp_path: Path) -> None:
        sgf_dir = tmp_path / "sgf"
        (sgf_dir / "batch-001").mkdir(parents=True)
        (sgf_dir / "batch-010").mkdir()
        assert detect_pad_width(sgf_dir) == 3

    def test_4digit_padding(self, tmp_path: Path) -> None:
        sgf_dir = tmp_path / "sgf"
        (sgf_dir / "batch-0001").mkdir(parents=True)
        (sgf_dir / "batch-0002").mkdir()
        assert detect_pad_width(sgf_dir) == 4

    def test_no_batches_returns_default(self, empty_sgf_dir: Path) -> None:
        assert detect_pad_width(empty_sgf_dir) == 3

    def test_mixed_padding_uses_max(self, tmp_path: Path) -> None:
        sgf_dir = tmp_path / "sgf"
        (sgf_dir / "batch-01").mkdir(parents=True)
        (sgf_dir / "batch-001").mkdir()
        assert detect_pad_width(sgf_dir) == 3


# ==============================
# batch_name
# ==============================


class TestBatchName:
    def test_3_digit(self) -> None:
        assert batch_name(1, 3) == "batch-001"
        assert batch_name(99, 3) == "batch-099"
        assert batch_name(100, 3) == "batch-100"

    def test_4_digit(self) -> None:
        assert batch_name(1, 4) == "batch-0001"


# ==============================
# catalog_files
# ==============================


class TestCatalogFiles:
    def test_empty_dir(self, empty_sgf_dir: Path) -> None:
        result = catalog_files(empty_sgf_dir)
        assert result == []

    def test_sorted_by_numeric_id(self, unbalanced: Path) -> None:
        result = catalog_files(unbalanced)
        assert len(result) == 6
        ids = [e.numeric_id for e in result]
        assert ids == [5, 10, 15, 20, 25, 30]

    def test_multi_batch_sorted(self, multi_batch_unbalanced: Path) -> None:
        result = catalog_files(multi_batch_unbalanced)
        assert len(result) == 10
        ids = [e.numeric_id for e in result]
        assert ids == list(range(1, 11))

    def test_gappy_ids_sorted(self, gappy_ids: Path) -> None:
        result = catalog_files(gappy_ids)
        assert len(result) == 8
        ids = [e.numeric_id for e in result]
        assert ids == [5, 100, 200, 500, 1000, 2000, 5000, 8000]

    def test_ignores_non_sgf_files(self, tmp_path: Path) -> None:
        sgf_dir = tmp_path / "sgf"
        batch = sgf_dir / "batch-001"
        batch.mkdir(parents=True)
        (batch / "1.sgf").write_text("(;GM[1])")
        (batch / "readme.txt").write_text("not an sgf file")
        (batch / "data.json").write_text("{}")

        result = catalog_files(sgf_dir)
        assert len(result) == 1
        assert result[0].filename == "1.sgf"

    def test_ignores_non_batch_dirs(self, tmp_path: Path) -> None:
        sgf_dir = tmp_path / "sgf"
        (sgf_dir / "batch-001").mkdir(parents=True)
        (sgf_dir / "batch-001" / "1.sgf").write_text("(;GM[1])")
        (sgf_dir / "other-dir").mkdir()
        (sgf_dir / "other-dir" / "2.sgf").write_text("(;GM[1])")

        result = catalog_files(sgf_dir)
        assert len(result) == 1


# ==============================
# compute_moves
# ==============================


class TestComputeMoves:
    def test_no_moves_when_balanced(self, balanced_small: Path) -> None:
        catalog = catalog_files(balanced_small)
        moves = compute_moves(catalog, batch_size=3, pad_width=3)
        assert moves == []

    def test_splits_oversized_batch(self, unbalanced: Path) -> None:
        catalog = catalog_files(unbalanced)
        moves = compute_moves(catalog, batch_size=3, pad_width=3)
        # Files 5,10,15 stay in batch-001; 20,25,30 move to batch-002
        assert len(moves) == 3
        for move in moves:
            assert "batch-002" in str(move.dst)

    def test_minimal_moves(self, multi_batch_unbalanced: Path) -> None:
        """Should only move files that are in the wrong batch."""
        catalog = catalog_files(multi_batch_unbalanced)
        moves = compute_moves(catalog, batch_size=5, pad_width=3)
        # Files 1-5 in batch-001 (correct), 6-10 should be in batch-002
        # Currently: 6 in batch-002 (correct), 7-10 in batch-003 (need move)
        assert len(moves) == 4  # 7, 8, 9, 10 move from batch-003 to batch-002

    def test_single_file(self, tmp_path: Path) -> None:
        sgf_dir = tmp_path / "sgf"
        _create_sgf_files(sgf_dir, {"batch-001": [42]})
        catalog = catalog_files(sgf_dir)
        moves = compute_moves(catalog, batch_size=1000, pad_width=3)
        assert moves == []  # already in batch-001


# ==============================
# execute_moves
# ==============================


class TestExecuteMoves:
    def test_basic_move(self, tmp_path: Path) -> None:
        sgf_dir = tmp_path / "sgf"
        src_batch = sgf_dir / "batch-001"
        src_batch.mkdir(parents=True)
        src_file = src_batch / "42.sgf"
        src_file.write_text("(;GM[1])")

        dst_file = sgf_dir / "batch-002" / "42.sgf"
        moves = [Move(src=src_file, dst=dst_file, filename="42.sgf")]
        count = execute_moves(moves, sgf_dir, pad_width=3, total_batches=2)

        assert count == 1
        assert not src_file.exists()
        assert dst_file.exists()
        assert dst_file.read_text() == "(;GM[1])"

    def test_collision_aborts(self, tmp_path: Path) -> None:
        sgf_dir = tmp_path / "sgf"
        src_batch = sgf_dir / "batch-001"
        dst_batch = sgf_dir / "batch-002"
        src_batch.mkdir(parents=True)
        dst_batch.mkdir(parents=True)

        src_file = src_batch / "42.sgf"
        src_file.write_text("source")
        dst_file = dst_batch / "42.sgf"
        dst_file.write_text("destination")

        moves = [Move(src=src_file, dst=dst_file, filename="42.sgf")]
        with pytest.raises(FileExistsError, match="Destination already exists"):
            execute_moves(moves, sgf_dir, pad_width=3, total_batches=2)


# ==============================
# remove_empty_batch_dirs
# ==============================


class TestRemoveEmptyBatchDirs:
    def test_removes_empty(self, tmp_path: Path) -> None:
        sgf_dir = tmp_path / "sgf"
        (sgf_dir / "batch-001").mkdir(parents=True)
        (sgf_dir / "batch-002").mkdir()
        (sgf_dir / "batch-002" / "1.sgf").write_text("(;)")

        removed = remove_empty_batch_dirs(sgf_dir)
        assert removed == 1
        assert not (sgf_dir / "batch-001").exists()
        assert (sgf_dir / "batch-002").exists()

    def test_ignores_non_batch_dirs(self, tmp_path: Path) -> None:
        sgf_dir = tmp_path / "sgf"
        (sgf_dir / "other-empty").mkdir(parents=True)
        (sgf_dir / "batch-001").mkdir()

        removed = remove_empty_batch_dirs(sgf_dir)
        assert removed == 1  # only batch-001, not other-empty
        assert (sgf_dir / "other-empty").exists()


# ==============================
# update_checkpoint
# ==============================


class TestUpdateCheckpoint:
    def test_creates_new_checkpoint(self, tmp_path: Path) -> None:
        cp_path = tmp_path / ".checkpoint.json"
        update_checkpoint(cp_path, current_batch=5, files_in_last_batch=200)

        data = json.loads(cp_path.read_text())
        assert data["current_batch"] == 5
        assert data["files_in_current_batch"] == 200
        assert "last_updated" in data

    def test_preserves_existing_fields(self, tmp_path: Path) -> None:
        cp_path = tmp_path / ".checkpoint.json"
        original = {
            "current_batch": 30,
            "files_in_current_batch": 209,
            "version": "1.0.0",
            "last_processed_id": 60381,
            "last_successful_id": 55836,
            "puzzles_downloaded": 29209,
            "custom_field": "preserved",
        }
        cp_path.write_text(json.dumps(original))

        update_checkpoint(cp_path, current_batch=52, files_in_last_batch=497)

        data = json.loads(cp_path.read_text())
        assert data["current_batch"] == 52
        assert data["files_in_current_batch"] == 497
        assert data["version"] == "1.0.0"
        assert data["last_processed_id"] == 60381
        assert data["last_successful_id"] == 55836
        assert data["puzzles_downloaded"] == 29209
        assert data["custom_field"] == "preserved"
        assert "last_updated" in data


# ==============================
# rebalance (end-to-end)
# ==============================


class TestRebalanceE2E:
    def test_dry_run_no_changes(self, unbalanced: Path, tmp_path: Path) -> None:
        index_path = tmp_path / "sgf-index.txt"
        result = rebalance(
            sgf_dir=unbalanced,
            index_path=index_path,
            batch_size=3,
            dry_run=True,
        )
        assert result.dry_run is True
        assert result.total_files == 6
        assert result.moves_needed == 3
        assert result.moves_executed == 0
        # Files should NOT have moved
        assert len(list((unbalanced / "batch-001").iterdir())) == 6
        assert not index_path.exists()

    def test_execute_splits_batch(self, unbalanced: Path, tmp_path: Path) -> None:
        index_path = tmp_path / "sgf-index.txt"
        result = rebalance(
            sgf_dir=unbalanced,
            index_path=index_path,
            batch_size=3,
            dry_run=False,
        )
        assert result.dry_run is False
        assert result.total_files == 6
        assert result.moves_executed == 3
        assert result.batches_after == 2
        assert result.index_entries == 6

        # Verify batch contents
        batch1_files = sorted(f.name for f in (unbalanced / "batch-001").iterdir())
        batch2_files = sorted(f.name for f in (unbalanced / "batch-002").iterdir())
        assert len(batch1_files) == 3
        assert len(batch2_files) == 3
        assert batch1_files == ["10.sgf", "15.sgf", "5.sgf"]
        assert batch2_files == ["20.sgf", "25.sgf", "30.sgf"]

        # Verify index
        lines = index_path.read_text().strip().split("\n")
        assert len(lines) == 6
        assert lines[0] == "batch-001/5.sgf"
        assert lines[-1] == "batch-002/30.sgf"

    def test_rebalance_uneven_multi(
        self, multi_batch_unbalanced: Path, tmp_path: Path
    ) -> None:
        index_path = tmp_path / "sgf-index.txt"
        result = rebalance(
            sgf_dir=multi_batch_unbalanced,
            index_path=index_path,
            batch_size=5,
            dry_run=False,
        )
        assert result.total_files == 10
        assert result.batches_after == 2

        # All files present — no data loss
        all_files = []
        for batch_dir in sorted(multi_batch_unbalanced.iterdir()):
            if batch_dir.is_dir() and batch_dir.name.startswith("batch-"):
                all_files.extend(f.name for f in batch_dir.iterdir())
        assert len(all_files) == 10

        # batch-001: 5 files, batch-002: 5 files
        assert len(list((multi_batch_unbalanced / "batch-001").iterdir())) == 5
        assert len(list((multi_batch_unbalanced / "batch-002").iterdir())) == 5

        # batch-003 should be removed (was emptied)
        assert not (multi_batch_unbalanced / "batch-003").exists()

    def test_already_balanced_no_moves(self, balanced_small: Path, tmp_path: Path) -> None:
        index_path = tmp_path / "sgf-index.txt"
        result = rebalance(
            sgf_dir=balanced_small,
            index_path=index_path,
            batch_size=3,
            dry_run=False,
        )
        assert result.moves_needed == 0
        assert result.moves_executed == 0
        assert result.total_files == 3
        assert result.index_entries == 3

    def test_empty_dir(self, empty_sgf_dir: Path, tmp_path: Path) -> None:
        index_path = tmp_path / "sgf-index.txt"
        result = rebalance(
            sgf_dir=empty_sgf_dir,
            index_path=index_path,
            batch_size=1000,
            dry_run=False,
        )
        assert result.total_files == 0
        assert result.moves_needed == 0

    def test_single_file(self, tmp_path: Path) -> None:
        sgf_dir = tmp_path / "sgf"
        _create_sgf_files(sgf_dir, {"batch-001": [42]})
        index_path = tmp_path / "sgf-index.txt"

        result = rebalance(
            sgf_dir=sgf_dir,
            index_path=index_path,
            batch_size=1000,
            dry_run=False,
        )
        assert result.total_files == 1
        assert result.moves_needed == 0
        assert result.index_entries == 1

    def test_checkpoint_updated(self, unbalanced: Path, tmp_path: Path) -> None:
        cp_path = tmp_path / ".checkpoint.json"
        cp_path.write_text(json.dumps({
            "current_batch": 1,
            "files_in_current_batch": 6,
            "version": "1.0.0",
            "last_processed_id": 30,
        }))
        index_path = tmp_path / "sgf-index.txt"

        rebalance(
            sgf_dir=unbalanced,
            index_path=index_path,
            batch_size=3,
            dry_run=False,
            checkpoint_path=cp_path,
        )

        data = json.loads(cp_path.read_text())
        assert data["current_batch"] == 2
        assert data["files_in_current_batch"] == 3
        assert data["version"] == "1.0.0"  # preserved
        assert data["last_processed_id"] == 30  # preserved

    def test_gappy_ids_rebalanced(self, gappy_ids: Path, tmp_path: Path) -> None:
        """Files with large ID gaps are still packed densely into batches."""
        index_path = tmp_path / "sgf-index.txt"
        result = rebalance(
            sgf_dir=gappy_ids,
            index_path=index_path,
            batch_size=3,
            dry_run=False,
        )
        assert result.total_files == 8
        assert result.batches_after == 3  # 3+3+2

        batch1 = sorted(f.name for f in (gappy_ids / "batch-001").iterdir())
        batch2 = sorted(f.name for f in (gappy_ids / "batch-002").iterdir())
        batch3 = sorted(f.name for f in (gappy_ids / "batch-003").iterdir())

        assert len(batch1) == 3
        assert len(batch2) == 3
        assert len(batch3) == 2

    def test_large_batch_rebalance(self, tmp_path: Path) -> None:
        """Simulates a scenario like goproblems: 20 files in 1 batch, batch_size=5."""
        sgf_dir = tmp_path / "sgf"
        ids = list(range(1, 21))
        _create_sgf_files(sgf_dir, {"batch-001": ids})
        index_path = tmp_path / "sgf-index.txt"

        result = rebalance(
            sgf_dir=sgf_dir,
            index_path=index_path,
            batch_size=5,
            dry_run=False,
        )
        assert result.total_files == 20
        assert result.batches_after == 4
        assert result.moves_executed == 15  # 5 stay in batch-001, 15 move

        # Verify each batch has exactly 5 files
        for bn in range(1, 5):
            bdir = sgf_dir / f"batch-00{bn}"
            assert len(list(bdir.iterdir())) == 5

    def test_file_content_preserved(self, tmp_path: Path) -> None:
        """Verify files are not corrupted by moves."""
        sgf_dir = tmp_path / "sgf"
        batch = sgf_dir / "batch-001"
        batch.mkdir(parents=True)

        # Create files with unique content
        for i in range(1, 7):
            (batch / f"{i}.sgf").write_text(f"(;GM[1]GN[puzzle-{i}])")

        index_path = tmp_path / "sgf-index.txt"
        rebalance(
            sgf_dir=sgf_dir,
            index_path=index_path,
            batch_size=3,
            dry_run=False,
        )

        # Verify content of moved files
        for i in range(1, 7):
            target_batch = "batch-001" if i <= 3 else "batch-002"
            content = (sgf_dir / target_batch / f"{i}.sgf").read_text()
            assert content == f"(;GM[1]GN[puzzle-{i}])"


# ==============================
# RebalanceResult
# ==============================


class TestRebalanceResult:
    def test_str_dry_run(self) -> None:
        result = RebalanceResult(
            total_files=51497,
            batches_before=30,
            batches_after=52,
            moves_needed=22000,
            moves_executed=0,
            empty_dirs_removed=0,
            index_entries=0,
            dry_run=True,
        )
        s = str(result)
        assert "DRY RUN" in s
        assert "51,497" in s
        assert "22,000" in s

    def test_str_executed(self) -> None:
        result = RebalanceResult(
            total_files=100,
            batches_before=1,
            batches_after=1,
            moves_needed=0,
            moves_executed=0,
            empty_dirs_removed=0,
            index_entries=100,
            dry_run=False,
        )
        s = str(result)
        assert "EXECUTED" in s
