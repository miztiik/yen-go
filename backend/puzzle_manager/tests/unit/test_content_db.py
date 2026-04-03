"""Tests for backend.puzzle_manager.core.content_db — DB-2 content database."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from backend.puzzle_manager.core.content_db import (
    backfill_batch_column,
    build_content_db,
    canonical_position_hash,
    delete_entries,
    extract_position_data,
    read_all_entries,
    vacuum_orphans,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SIMPLE_SGF = "(;GM[1]FF[4]SZ[19]PL[B]AB[pd][qd][rd]AW[oc][pc][qc];B[sc])"
SIMPLE_SGF_REORDERED = "(;GM[1]FF[4]SZ[19]PL[B]AB[rd][pd][qd]AW[qc][oc][pc];B[sc])"
DIFFERENT_PLAYER = "(;GM[1]FF[4]SZ[19]PL[W]AB[pd][qd][rd]AW[oc][pc][qc];W[sc])"


# ---------------------------------------------------------------------------
# canonical_position_hash
# ---------------------------------------------------------------------------


class TestCanonicalPositionHash:
    def test_deterministic(self) -> None:
        h1 = canonical_position_hash(19, ["pd", "qd"], ["oc", "pc"], "B")
        h2 = canonical_position_hash(19, ["pd", "qd"], ["oc", "pc"], "B")
        assert h1 == h2
        assert len(h1) == 16

    def test_order_independent(self) -> None:
        h1 = canonical_position_hash(19, ["pd", "rd", "qd"], ["oc", "pc", "qc"], "B")
        h2 = canonical_position_hash(19, ["rd", "pd", "qd"], ["qc", "oc", "pc"], "B")
        assert h1 == h2

    def test_includes_first_player(self) -> None:
        h_b = canonical_position_hash(19, ["pd"], ["oc"], "B")
        h_w = canonical_position_hash(19, ["pd"], ["oc"], "W")
        assert h_b != h_w


# ---------------------------------------------------------------------------
# extract_position_data
# ---------------------------------------------------------------------------


class TestExtractPositionData:
    def test_basic(self) -> None:
        result = extract_position_data(SIMPLE_SGF)
        assert result["board_size"] == 19
        assert sorted(result["black_stones"]) == ["pd", "qd", "rd"]
        assert sorted(result["white_stones"]) == ["oc", "pc", "qc"]
        assert result["first_player"] == "B"
        assert result["stone_count"] == 6

    def test_default_board_size(self) -> None:
        sgf = "(;GM[1]FF[4]PL[B]AB[pd]AW[oc];B[qd])"
        result = extract_position_data(sgf)
        assert result["board_size"] == 19

    def test_default_player(self) -> None:
        sgf = "(;GM[1]FF[4]SZ[9]AB[dd]AW[ee];B[ff])"
        result = extract_position_data(sgf)
        assert result["first_player"] == "B"

    def test_reordered_stones_same_set(self) -> None:
        r1 = extract_position_data(SIMPLE_SGF)
        r2 = extract_position_data(SIMPLE_SGF_REORDERED)
        assert sorted(r1["black_stones"]) == sorted(r2["black_stones"])
        assert sorted(r1["white_stones"]) == sorted(r2["white_stones"])


# ---------------------------------------------------------------------------
# build_content_db
# ---------------------------------------------------------------------------


class TestBuildContentDb:
    def test_creates_file(self, tmp_path: Path) -> None:
        db_path = tmp_path / "test.db"
        build_content_db({"abc123": SIMPLE_SGF}, db_path)
        assert db_path.exists()

    def test_schema(self, tmp_path: Path) -> None:
        db_path = tmp_path / "test.db"
        build_content_db({"abc123": SIMPLE_SGF}, db_path)

        conn = sqlite3.connect(str(db_path))
        try:
            # Table exists
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
            table_names = [t[0] for t in tables]
            assert "sgf_files" in table_names

            # Indexes exist
            indexes = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index'"
            ).fetchall()
            index_names = [i[0] for i in indexes]
            assert "idx_sgf_position" in index_names
            assert "idx_sgf_stones" in index_names
            assert "idx_sgf_source" in index_names
        finally:
            conn.close()

    def test_sgf_round_trip(self, tmp_path: Path) -> None:
        db_path = tmp_path / "test.db"
        build_content_db({"abc123": SIMPLE_SGF}, db_path)

        conn = sqlite3.connect(str(db_path))
        try:
            row = conn.execute(
                "SELECT sgf_content FROM sgf_files WHERE content_hash = ?",
                ("abc123",),
            ).fetchone()
            assert row is not None
            assert row[0] == SIMPLE_SGF
        finally:
            conn.close()

    def test_dedup_detection(self, tmp_path: Path) -> None:
        """Two SGFs with same position but different raw content share position_hash."""
        db_path = tmp_path / "test.db"
        build_content_db(
            {"hash_a": SIMPLE_SGF, "hash_b": SIMPLE_SGF_REORDERED},
            db_path,
        )

        conn = sqlite3.connect(str(db_path))
        try:
            rows = conn.execute(
                "SELECT position_hash FROM sgf_files ORDER BY content_hash"
            ).fetchall()
            assert len(rows) == 2
            assert rows[0][0] == rows[1][0]  # same position hash
        finally:
            conn.close()

    def test_source_tag(self, tmp_path: Path) -> None:
        db_path = tmp_path / "test.db"
        build_content_db({"abc123": SIMPLE_SGF}, db_path, source="sanderland")

        conn = sqlite3.connect(str(db_path))
        try:
            row = conn.execute(
                "SELECT source FROM sgf_files WHERE content_hash = ?",
                ("abc123",),
            ).fetchone()
            assert row is not None
            assert row[0] == "sanderland"
        finally:
            conn.close()


# ---------------------------------------------------------------------------
# read_all_entries
# ---------------------------------------------------------------------------


class TestReadAllEntries:
    """Tests for read_all_entries()."""

    def test_returns_empty_for_missing_db(self, tmp_path: Path) -> None:
        result = read_all_entries(tmp_path / "nonexistent.db")
        assert result == []

    def test_returns_all_rows(self, tmp_path: Path) -> None:
        db_path = tmp_path / "test.db"
        sgf_files = {
            "hash1": "(;GM[1]FF[4]SZ[9]AB[dd][de]AW[ee])",
            "hash2": "(;GM[1]FF[4]SZ[9]AB[cc][cd]AW[dc])",
        }
        build_content_db(sgf_files, db_path, source="test")

        entries = read_all_entries(db_path)
        assert len(entries) == 2
        hashes = {e["content_hash"] for e in entries}
        assert hashes == {"hash1", "hash2"}
        for e in entries:
            assert "content_hash" in e
            assert "sgf_content" in e
            assert "position_hash" in e
            assert "board_size" in e
            assert "source" in e

    def test_preserves_sgf_content(self, tmp_path: Path) -> None:
        db_path = tmp_path / "test.db"
        sgf = "(;GM[1]FF[4]SZ[9]AB[dd]AW[ee])"
        build_content_db({"h1": sgf}, db_path)

        entries = read_all_entries(db_path)
        assert len(entries) == 1
        assert entries[0]["sgf_content"] == sgf


# ---------------------------------------------------------------------------
# delete_entries
# ---------------------------------------------------------------------------


class TestDeleteEntries:
    """Tests for delete_entries()."""

    def test_deletes_by_hash(self, tmp_path: Path) -> None:
        db_path = tmp_path / "test.db"
        sgf_files = {
            "hash1": "(;GM[1]FF[4]SZ[9]AB[dd]AW[ee])",
            "hash2": "(;GM[1]FF[4]SZ[9]AB[cc]AW[dc])",
            "hash3": "(;GM[1]FF[4]SZ[9]AB[ff]AW[gg])",
        }
        build_content_db(sgf_files, db_path)

        deleted = delete_entries(db_path, ["hash1", "hash3"])
        assert deleted == 2

        remaining = read_all_entries(db_path)
        assert len(remaining) == 1
        assert remaining[0]["content_hash"] == "hash2"

    def test_returns_zero_for_empty_list(self, tmp_path: Path) -> None:
        db_path = tmp_path / "test.db"
        build_content_db({"h1": "(;GM[1]FF[4]SZ[9]AB[dd]AW[ee])"}, db_path)

        deleted = delete_entries(db_path, [])
        assert deleted == 0

    def test_returns_zero_for_missing_db(self, tmp_path: Path) -> None:
        deleted = delete_entries(tmp_path / "nonexistent.db", ["hash1"])
        assert deleted == 0

    def test_handles_nonexistent_hashes(self, tmp_path: Path) -> None:
        db_path = tmp_path / "test.db"
        build_content_db({"h1": "(;GM[1]FF[4]SZ[9]AB[dd]AW[ee])"}, db_path)

        deleted = delete_entries(db_path, ["nonexistent"])
        assert deleted == 0


# ---------------------------------------------------------------------------
# vacuum_orphans
# ---------------------------------------------------------------------------


class TestVacuumOrphans:
    """Tests for vacuum_orphans()."""

    def test_removes_orphaned_entries(self, tmp_path: Path) -> None:
        db_path = tmp_path / "test.db"
        sgf_files = {
            "published1": "(;GM[1]FF[4]SZ[9]AB[dd]AW[ee])",
            "published2": "(;GM[1]FF[4]SZ[9]AB[cc]AW[dc])",
            "orphan1": "(;GM[1]FF[4]SZ[9]AB[ff]AW[gg])",
        }
        build_content_db(sgf_files, db_path)

        removed = vacuum_orphans(db_path, {"published1", "published2"})
        assert removed == 1

        remaining = read_all_entries(db_path)
        assert len(remaining) == 2
        remaining_hashes = {e["content_hash"] for e in remaining}
        assert remaining_hashes == {"published1", "published2"}

    def test_returns_zero_when_no_orphans(self, tmp_path: Path) -> None:
        db_path = tmp_path / "test.db"
        build_content_db({"h1": "(;GM[1]FF[4]SZ[9]AB[dd]AW[ee])"}, db_path)

        removed = vacuum_orphans(db_path, {"h1"})
        assert removed == 0

    def test_returns_zero_for_missing_db(self, tmp_path: Path) -> None:
        removed = vacuum_orphans(tmp_path / "nonexistent.db", {"h1"})
        assert removed == 0


# ---------------------------------------------------------------------------
# batch column
# ---------------------------------------------------------------------------


class TestBatchColumn:
    """Tests for batch column in DB-2 (RC-3)."""

    def test_batch_stored_and_retrieved(self, tmp_path: Path) -> None:
        """batch column round-trips through build → read."""
        db_path = tmp_path / "test.db"
        sgf_files = {"hash1": "(;GM[1]FF[4]SZ[9]AB[dd]AW[ee])"}
        build_content_db(sgf_files, db_path, batch="0042")

        entries = read_all_entries(db_path)
        assert len(entries) == 1
        assert entries[0]["batch"] == "0042"

    def test_batch_defaults_to_none(self, tmp_path: Path) -> None:
        """Without batch param, column is NULL."""
        db_path = tmp_path / "test.db"
        sgf_files = {"hash1": "(;GM[1]FF[4]SZ[9]AB[dd]AW[ee])"}
        build_content_db(sgf_files, db_path)

        entries = read_all_entries(db_path)
        assert entries[0]["batch"] is None

    def test_backfill_from_filesystem(self, tmp_path: Path) -> None:
        """backfill_batch_column resolves batch from filesystem."""
        db_path = tmp_path / "test.db"
        sgf_files = {"hash1": "(;GM[1]FF[4]SZ[9]AB[dd]AW[ee])"}
        build_content_db(sgf_files, db_path)  # no batch

        # Create filesystem structure
        sgf_dir = tmp_path / "sgf"
        batch_dir = sgf_dir / "0003"
        batch_dir.mkdir(parents=True)
        (batch_dir / "hash1.sgf").write_text("(;GM[1]FF[4]SZ[9]AB[dd]AW[ee])")

        updated = backfill_batch_column(db_path, sgf_dir)
        assert updated == 1

        entries = read_all_entries(db_path)
        assert entries[0]["batch"] == "0003"

    def test_backfill_skips_missing_files(self, tmp_path: Path) -> None:
        """Entries without matching filesystem files are left NULL."""
        db_path = tmp_path / "test.db"
        sgf_files = {"hash1": "(;GM[1]FF[4]SZ[9]AB[dd]AW[ee])"}
        build_content_db(sgf_files, db_path)

        sgf_dir = tmp_path / "sgf"
        sgf_dir.mkdir()

        updated = backfill_batch_column(db_path, sgf_dir)
        assert updated == 0

    def test_schema_migration_adds_batch_column(self, tmp_path: Path) -> None:
        """Existing DB without batch column gets migrated."""
        db_path = tmp_path / "test.db"
        # Create old-schema DB without batch column
        conn = sqlite3.connect(str(db_path))
        conn.execute("""CREATE TABLE sgf_files (
            content_hash TEXT PRIMARY KEY,
            sgf_content TEXT NOT NULL,
            position_hash TEXT,
            board_size INTEGER NOT NULL DEFAULT 19,
            black_stones TEXT NOT NULL,
            white_stones TEXT NOT NULL,
            first_player TEXT NOT NULL DEFAULT 'B',
            stone_count INTEGER NOT NULL DEFAULT 0,
            source TEXT,
            created_at TEXT
        )""")
        conn.execute(
            "INSERT INTO sgf_files (content_hash, sgf_content, board_size, black_stones, "
            "white_stones, first_player, stone_count) "
            "VALUES ('h1', '(;GM[1]FF[4]SZ[9]AB[dd]AW[ee])', 9, 'dd', 'ee', 'B', 2)"
        )
        conn.commit()
        conn.close()

        # Now build_content_db should handle migration
        sgf_files = {"h2": "(;GM[1]FF[4]SZ[9]AB[cc]AW[dc])"}
        build_content_db(sgf_files, db_path, batch="0001")

        entries = read_all_entries(db_path)
        hashes = {e["content_hash"]: e["batch"] for e in entries}
        assert hashes["h2"] == "0001"
        # Old row should have NULL batch
        assert hashes["h1"] is None
