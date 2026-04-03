"""Unit tests for collection_slug schema change and slug extraction (T1-T3)."""

import sqlite3
from pathlib import Path

from backend.puzzle_manager.core.content_db import (
    _ensure_collection_slug_column,
    _extract_collection_slug,
    build_content_db,
)


class TestExtractCollectionSlug:
    """Tests for _extract_collection_slug()."""

    def test_basic_slug(self) -> None:
        sgf = "(;FF[4]GM[1]SZ[19]YL[cho-elementary]AB[pd]AW[qd];B[oe])"
        assert _extract_collection_slug(sgf) == "cho-elementary"

    def test_slug_with_chapter_position_suffix(self) -> None:
        sgf = "(;FF[4]GM[1]SZ[19]YL[cho-elementary:3/12]AB[pd]AW[qd];B[oe])"
        assert _extract_collection_slug(sgf) == "cho-elementary"

    def test_no_yl_property(self) -> None:
        sgf = "(;FF[4]GM[1]SZ[19]AB[pd]AW[qd];B[oe])"
        assert _extract_collection_slug(sgf) is None

    def test_multi_slug_returns_first(self) -> None:
        sgf = "(;FF[4]GM[1]SZ[19]YL[alpha,beta,gamma]AB[pd]AW[qd];B[oe])"
        assert _extract_collection_slug(sgf) == "alpha"

    def test_empty_yl(self) -> None:
        sgf = "(;FF[4]GM[1]SZ[19]YL[]AB[pd]AW[qd];B[oe])"
        assert _extract_collection_slug(sgf) is None


class TestEnsureCollectionSlugColumn:
    """Tests for _ensure_collection_slug_column() idempotency."""

    def test_adds_column_to_old_schema(self, tmp_path: Path) -> None:
        db_path = tmp_path / "test.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute(
            "CREATE TABLE sgf_files ("
            "content_hash TEXT PRIMARY KEY, sgf_content TEXT, source TEXT)"
        )
        conn.commit()

        _ensure_collection_slug_column(conn)

        cols = {row[1] for row in conn.execute("PRAGMA table_info(sgf_files)")}
        assert "collection_slug" in cols
        conn.close()

    def test_idempotent(self, tmp_path: Path) -> None:
        db_path = tmp_path / "test.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute(
            "CREATE TABLE sgf_files ("
            "content_hash TEXT PRIMARY KEY, sgf_content TEXT, "
            "collection_slug TEXT)"
        )
        conn.commit()

        # Should not raise even though column already exists
        _ensure_collection_slug_column(conn)
        _ensure_collection_slug_column(conn)

        cols = {row[1] for row in conn.execute("PRAGMA table_info(sgf_files)")}
        assert "collection_slug" in cols
        conn.close()


class TestBuildContentDbCollectionSlug:
    """Tests for collection_slug population in build_content_db()."""

    def test_writes_collection_slug(self, tmp_path: Path) -> None:
        db_path = tmp_path / "yengo-content.db"
        sgf = "(;FF[4]GM[1]SZ[19]YL[cho-elementary:0/42]AB[pd]AW[qd];B[oe])"
        build_content_db(
            sgf_files={"hash1": sgf},
            output_path=db_path,
            source="test",
        )

        conn = sqlite3.connect(str(db_path))
        row = conn.execute(
            "SELECT collection_slug FROM sgf_files WHERE content_hash = 'hash1'"
        ).fetchone()
        conn.close()
        assert row[0] == "cho-elementary"

    def test_null_when_no_yl(self, tmp_path: Path) -> None:
        db_path = tmp_path / "yengo-content.db"
        sgf = "(;FF[4]GM[1]SZ[19]AB[pd]AW[qd];B[oe])"
        build_content_db(
            sgf_files={"hash2": sgf},
            output_path=db_path,
            source="test",
        )

        conn = sqlite3.connect(str(db_path))
        row = conn.execute(
            "SELECT collection_slug FROM sgf_files WHERE content_hash = 'hash2'"
        ).fetchone()
        conn.close()
        assert row[0] is None
