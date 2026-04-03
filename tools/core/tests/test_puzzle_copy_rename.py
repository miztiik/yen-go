"""Tests for tools.puzzle_copy_rename — copy and rename SGF files."""

from __future__ import annotations

from pathlib import Path

import pytest

from tools.puzzle_copy_rename import copy_and_rename

# Minimal valid SGF content for test fixtures
_MINIMAL_SGF = b"(;FF[4]GM[1]SZ[9];B[ee])"
_MINIMAL_SGF_2 = b"(;FF[4]GM[1]SZ[9];B[cc])"
_MINIMAL_SGF_3 = b"(;FF[4]GM[1]SZ[9];B[gg])"


def _create_sgf(directory: Path, name: str, content: bytes = _MINIMAL_SGF) -> Path:
    """Create a minimal SGF file in *directory*."""
    f = directory / name
    f.write_bytes(content)
    return f


class TestSingleFileCopy:
    def test_single_file_copy(self, tmp_path: Path) -> None:
        src_dir = tmp_path / "source"
        src_dir.mkdir()
        tgt_dir = tmp_path / "target"
        tgt_dir.mkdir()

        src = _create_sgf(src_dir, "original.sgf")

        results = copy_and_rename(
            input_paths=[src],
            target_dir=tgt_dir,
            instinct="cut",
            level="intermediate",
            serial_start=1,
        )

        assert len(results) == 1
        _, dest = results[0]
        assert dest.name == "cut_intermediate_001.sgf"
        assert dest.exists()
        assert dest.read_bytes() == _MINIMAL_SGF


class TestBatchCopy:
    def test_batch_copy_serial_start(self, tmp_path: Path) -> None:
        src_dir = tmp_path / "source"
        src_dir.mkdir()
        tgt_dir = tmp_path / "target"
        tgt_dir.mkdir()

        src_a = _create_sgf(src_dir, "alpha.sgf", _MINIMAL_SGF)
        src_b = _create_sgf(src_dir, "beta.sgf", _MINIMAL_SGF_2)
        src_c = _create_sgf(src_dir, "gamma.sgf", _MINIMAL_SGF_3)

        results = copy_and_rename(
            input_paths=[src_c, src_a, src_b],  # unsorted on purpose
            target_dir=tgt_dir,
            instinct="hane",
            level="advanced",
            serial_start=5,
        )

        assert len(results) == 3
        names = [dest.name for _, dest in results]
        assert names == [
            "hane_advanced_005.sgf",
            "hane_advanced_006.sgf",
            "hane_advanced_007.sgf",
        ]
        # Verify all files exist and content matches sorted order
        assert results[0][1].read_bytes() == _MINIMAL_SGF      # alpha
        assert results[1][1].read_bytes() == _MINIMAL_SGF_2    # beta
        assert results[2][1].read_bytes() == _MINIMAL_SGF_3    # gamma


class TestDryRun:
    def test_dry_run_no_writes(self, tmp_path: Path) -> None:
        src_dir = tmp_path / "source"
        src_dir.mkdir()
        tgt_dir = tmp_path / "target"
        tgt_dir.mkdir()

        src = _create_sgf(src_dir, "puzzle.sgf")

        results = copy_and_rename(
            input_paths=[src],
            target_dir=tgt_dir,
            instinct="push",
            level="beginner",
            serial_start=1,
            dry_run=True,
        )

        assert len(results) == 1
        _, dest = results[0]
        assert dest.name == "push_beginner_001.sgf"
        # File must NOT be created
        assert not dest.exists()
        assert list(tgt_dir.iterdir()) == []


class TestOverwrite:
    def test_overwrite_prevention(self, tmp_path: Path) -> None:
        src_dir = tmp_path / "source"
        src_dir.mkdir()
        tgt_dir = tmp_path / "target"
        tgt_dir.mkdir()

        src = _create_sgf(src_dir, "puzzle.sgf")
        # Pre-create target file
        (tgt_dir / "extend_elementary_001.sgf").write_bytes(b"existing")

        with pytest.raises(FileExistsError, match="use --force"):
            copy_and_rename(
                input_paths=[src],
                target_dir=tgt_dir,
                instinct="extend",
                level="elementary",
                serial_start=1,
            )

    def test_force_overwrite(self, tmp_path: Path) -> None:
        src_dir = tmp_path / "source"
        src_dir.mkdir()
        tgt_dir = tmp_path / "target"
        tgt_dir.mkdir()

        src = _create_sgf(src_dir, "puzzle.sgf")
        existing = tgt_dir / "extend_elementary_001.sgf"
        existing.write_bytes(b"old content")

        results = copy_and_rename(
            input_paths=[src],
            target_dir=tgt_dir,
            instinct="extend",
            level="elementary",
            serial_start=1,
            force=True,
        )

        assert len(results) == 1
        assert results[0][1].read_bytes() == _MINIMAL_SGF


class TestValidation:
    def test_invalid_instinct(self, tmp_path: Path) -> None:
        tgt_dir = tmp_path / "target"
        tgt_dir.mkdir()

        with pytest.raises(ValueError, match="Invalid instinct 'zap'"):
            copy_and_rename(
                input_paths=[],
                target_dir=tgt_dir,
                instinct="zap",
                level="beginner",
            )

    def test_invalid_level(self, tmp_path: Path) -> None:
        tgt_dir = tmp_path / "target"
        tgt_dir.mkdir()

        with pytest.raises(ValueError, match="Invalid level 'super'"):
            copy_and_rename(
                input_paths=[],
                target_dir=tgt_dir,
                instinct="cut",
                level="super",
            )


class TestNameFormat:
    @pytest.mark.parametrize(
        "instinct,level,serial,expected",
        [
            ("push", "novice", 1, "push_novice_001.sgf"),
            ("hane", "upper-intermediate", 12, "hane_upper-intermediate_012.sgf"),
            ("null", "expert", 100, "null_expert_100.sgf"),
            ("descent", "low-dan", 999, "descent_low-dan_999.sgf"),
        ],
    )
    def test_name_format(
        self,
        tmp_path: Path,
        instinct: str,
        level: str,
        serial: int,
        expected: str,
    ) -> None:
        src_dir = tmp_path / "source"
        src_dir.mkdir()
        tgt_dir = tmp_path / "target"
        tgt_dir.mkdir()

        src = _create_sgf(src_dir, "any.sgf")

        results = copy_and_rename(
            input_paths=[src],
            target_dir=tgt_dir,
            instinct=instinct,
            level=level,
            serial_start=serial,
        )

        assert results[0][1].name == expected


class TestDeterministicOrdering:
    def test_deterministic_ordering(self, tmp_path: Path) -> None:
        """Files are sorted alphabetically before serial assignment."""
        src_dir = tmp_path / "source"
        src_dir.mkdir()
        tgt_dir = tmp_path / "target"
        tgt_dir.mkdir()

        # Create in reverse alphabetical order
        src_z = _create_sgf(src_dir, "z-puzzle.sgf", b"(;FF[4]GM[1]SZ[9];B[aa])")
        src_a = _create_sgf(src_dir, "a-puzzle.sgf", b"(;FF[4]GM[1]SZ[9];B[bb])")
        src_m = _create_sgf(src_dir, "m-puzzle.sgf", b"(;FF[4]GM[1]SZ[9];B[cc])")

        results = copy_and_rename(
            input_paths=[src_z, src_a, src_m],
            target_dir=tgt_dir,
            instinct="cut",
            level="intermediate",
            serial_start=1,
        )

        # Serial 1 -> a-puzzle, serial 2 -> m-puzzle, serial 3 -> z-puzzle
        sources = [src for src, _ in results]
        assert sources[0].name == "a-puzzle.sgf"
        assert sources[1].name == "m-puzzle.sgf"
        assert sources[2].name == "z-puzzle.sgf"

        assert results[0][1].name == "cut_intermediate_001.sgf"
        assert results[1][1].name == "cut_intermediate_002.sgf"
        assert results[2][1].name == "cut_intermediate_003.sgf"

        # Verify content tracks the sorted order
        assert results[0][1].read_bytes() == b"(;FF[4]GM[1]SZ[9];B[bb])"  # a-puzzle
        assert results[1][1].read_bytes() == b"(;FF[4]GM[1]SZ[9];B[cc])"  # m-puzzle
        assert results[2][1].read_bytes() == b"(;FF[4]GM[1]SZ[9];B[aa])"  # z-puzzle
