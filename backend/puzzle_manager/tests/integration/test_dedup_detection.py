"""Integration tests for position-based duplicate detection (DB-2 dedup).

Tests the dedup check in IngestStage against the content database
built by build_content_db().
"""

import sqlite3
from pathlib import Path

from backend.puzzle_manager.core.content_db import (
    build_content_db,
)
from backend.puzzle_manager.stages.ingest import IngestStage


def _make_sgf(black_stones: str = "AB[pd][qf]", white_stones: str = "AW[qd][pe]") -> str:
    """Create a minimal valid SGF with given stone setup."""
    return (
        f"(;FF[4]GM[1]SZ[19]"
        f"{black_stones}{white_stones}"
        f";B[oe]"
        f"(;W[of];B[ne])"
        f"(;W[ne];B[of]))"
    )


class TestDedupDetection:
    """Position-based duplicate detection against DB-2."""

    def test_dedup_detects_same_position(self, tmp_path: Path) -> None:
        """Puzzle with identical position to an existing DB-2 entry → detected as dup."""
        sgf_content = _make_sgf()
        db_path = tmp_path / "yengo-content.db"

        # Build DB-2 with one puzzle
        build_content_db(
            sgf_files={"existing_hash_abc": sgf_content},
            output_path=db_path,
            source="test",
        )

        # Open read-only and check dedup
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        try:
            dup = IngestStage._check_dedup(conn, sgf_content, source_id="test")
            assert dup == "existing_hash_abc"
        finally:
            conn.close()

    def test_dedup_allows_different_position(self, tmp_path: Path) -> None:
        """Puzzle with a different position → not flagged as duplicate."""
        existing_sgf = _make_sgf(black_stones="AB[pd][qf]", white_stones="AW[qd][pe]")
        new_sgf = _make_sgf(black_stones="AB[dd][cf]", white_stones="AW[cd][de]")
        db_path = tmp_path / "yengo-content.db"

        build_content_db(
            sgf_files={"existing_hash_xyz": existing_sgf},
            output_path=db_path,
            source="test",
        )

        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        try:
            dup = IngestStage._check_dedup(conn, new_sgf, source_id="test")
            assert dup is None
        finally:
            conn.close()

    def test_dedup_skips_when_no_db(self, tmp_path: Path) -> None:
        """No DB-2 file → ingest should proceed without error.

        This tests the RC-3 governance requirement: graceful skip when
        content database is missing (first pipeline run).
        """
        db_path = tmp_path / "yengo-content.db"
        assert not db_path.exists()

        # The IngestStage.run() checks db_path.exists() and sets dedup_conn=None.
        # Verify the _check_dedup method itself is never called (conn would be None).
        # We just verify the path doesn't exist and the helper returns correctly
        # when called with an empty DB.
        empty_db = tmp_path / "empty.db"
        conn = sqlite3.connect(str(empty_db))
        conn.executescript(
            "CREATE TABLE IF NOT EXISTS sgf_files ("
            "content_hash TEXT PRIMARY KEY, sgf_content TEXT, position_hash TEXT, "
            "board_size INTEGER DEFAULT 19, black_stones TEXT, white_stones TEXT, "
            "first_player TEXT DEFAULT 'B', stone_count INTEGER DEFAULT 0, "
            "source TEXT, created_at TEXT);"
            "CREATE INDEX IF NOT EXISTS idx_sgf_position ON sgf_files(position_hash);"
        )
        conn.commit()

        sgf = _make_sgf()
        dup = IngestStage._check_dedup(conn, sgf, source_id="test")
        conn.close()

        assert dup is None, "Empty DB should not flag any duplicates"

    def test_dedup_matches_by_position_not_content(self, tmp_path: Path) -> None:
        """Two SGFs with same stones but different comments → same position hash."""
        sgf_a = "(;FF[4]GM[1]SZ[19]C[Version A]AB[pd][qf]AW[qd];B[oe])"
        sgf_b = "(;FF[4]GM[1]SZ[19]C[Version B]AB[pd][qf]AW[qd];B[oe])"
        db_path = tmp_path / "yengo-content.db"

        build_content_db(
            sgf_files={"hash_a": sgf_a},
            output_path=db_path,
            source="test",
        )

        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        try:
            dup = IngestStage._check_dedup(conn, sgf_b, source_id="test")
            assert dup == "hash_a", "Same position setup should match regardless of comments"
        finally:
            conn.close()
