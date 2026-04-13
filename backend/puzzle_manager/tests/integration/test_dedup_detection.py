"""Integration tests for position-based duplicate detection with solution fingerprint.

Tests the dedup check in IngestStage against the content database
built by build_content_db().
"""

import sqlite3
from pathlib import Path

from backend.puzzle_manager.core.content_db import (
    build_content_db,
    compute_solution_fingerprint,
)
from backend.puzzle_manager.core.sgf_parser import parse_sgf
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


def _fingerprint(sgf: str) -> str:
    """Compute solution fingerprint from SGF string."""
    game = parse_sgf(sgf)
    return compute_solution_fingerprint(game.solution_tree)


class TestDedupDetection:
    """Position-based duplicate detection with solution fingerprint."""

    def test_dedup_detects_true_duplicate(self, tmp_path: Path) -> None:
        """Same position + same source + same fingerprint → true duplicate."""
        sgf_content = _make_sgf()
        db_path = tmp_path / "yengo-content.db"

        build_content_db(
            sgf_files={"existing_hash_abc": sgf_content},
            output_path=db_path,
            source="test",
        )

        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        try:
            result = IngestStage._check_dedup(
                conn, sgf_content,
                source_id="test",
                solution_fingerprint=_fingerprint(sgf_content),
            )
            assert result.is_duplicate is True
            assert result.existing_hash == "existing_hash_abc"
            assert result.event_type == "true_duplicate"
        finally:
            conn.close()

    def test_dedup_allows_different_position(self, tmp_path: Path) -> None:
        """Puzzle with a different position → no collision."""
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
            result = IngestStage._check_dedup(
                conn, new_sgf,
                source_id="test",
                solution_fingerprint=_fingerprint(new_sgf),
            )
            assert result.is_duplicate is False
            assert result.event_type == "no_collision"
        finally:
            conn.close()

    def test_dedup_skips_when_empty_db(self, tmp_path: Path) -> None:
        """Empty DB → no duplicates found."""
        db_path = tmp_path / "empty.db"
        conn = sqlite3.connect(str(db_path))
        conn.executescript(
            "CREATE TABLE IF NOT EXISTS sgf_files ("
            "content_hash TEXT PRIMARY KEY, sgf_content TEXT, position_hash TEXT, "
            "solution_fingerprint TEXT, fingerprint_version INTEGER DEFAULT 1, "
            "board_size INTEGER DEFAULT 19, black_stones TEXT, white_stones TEXT, "
            "first_player TEXT DEFAULT 'B', stone_count INTEGER DEFAULT 0, "
            "source TEXT, created_at TEXT);"
            "CREATE INDEX IF NOT EXISTS idx_sgf_position ON sgf_files(position_hash);"
        )
        conn.commit()

        sgf = _make_sgf()
        result = IngestStage._check_dedup(
            conn, sgf,
            source_id="test",
            solution_fingerprint=_fingerprint(sgf),
        )
        conn.close()

        assert result.is_duplicate is False
        assert result.event_type == "no_collision"

    def test_dedup_matches_by_position_not_content(self, tmp_path: Path) -> None:
        """Same position + same source + same solution but different comments → true duplicate."""
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
            result = IngestStage._check_dedup(
                conn, sgf_b,
                source_id="test",
                solution_fingerprint=_fingerprint(sgf_b),
            )
            assert result.is_duplicate is True
            assert result.existing_hash == "hash_a"
        finally:
            conn.close()


class TestDedupVariantDetection:
    """Solution-fingerprint-aware variant detection."""

    def test_variant_allowed_same_source_different_solution(self, tmp_path: Path) -> None:
        """Same position + same source + different solution → variant allowed."""
        # Both puzzles have same stones but different solution moves
        sgf_solution_a = (
            "(;FF[4]GM[1]SZ[19]AB[pd][qf]AW[qd][pe]"
            ";B[oe];W[of];B[ne])"
        )
        sgf_solution_b = (
            "(;FF[4]GM[1]SZ[19]AB[pd][qf]AW[qd][pe]"
            ";B[ne];W[oe];B[of])"
        )

        db_path = tmp_path / "yengo-content.db"
        build_content_db(
            sgf_files={"hash_a": sgf_solution_a},
            output_path=db_path,
            source="test",
        )

        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        try:
            result = IngestStage._check_dedup(
                conn, sgf_solution_b,
                source_id="test",
                solution_fingerprint=_fingerprint(sgf_solution_b),
            )
            assert result.is_duplicate is False
            assert result.event_type == "variant_allowed"
        finally:
            conn.close()

    def test_cross_source_allowed(self, tmp_path: Path) -> None:
        """Same position + different source → cross-source allowed."""
        sgf_content = _make_sgf()
        db_path = tmp_path / "yengo-content.db"

        build_content_db(
            sgf_files={"existing_hash": sgf_content},
            output_path=db_path,
            source="source_a",
        )

        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        try:
            result = IngestStage._check_dedup(
                conn, sgf_content,
                source_id="source_b",
                solution_fingerprint=_fingerprint(sgf_content),
            )
            assert result.is_duplicate is False
            assert result.event_type == "cross_source_allowed"
        finally:
            conn.close()

    def test_version_mismatch_allows(self, tmp_path: Path) -> None:
        """Same fingerprint string but different version → treat as non-match."""
        sgf_content = _make_sgf()
        db_path = tmp_path / "yengo-content.db"

        build_content_db(
            sgf_files={"existing_hash": sgf_content},
            output_path=db_path,
            source="test",
        )

        # Manually update the fingerprint_version to simulate a different version
        conn_rw = sqlite3.connect(str(db_path))
        conn_rw.execute("UPDATE sgf_files SET fingerprint_version = 99")
        conn_rw.commit()
        conn_rw.close()

        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        try:
            result = IngestStage._check_dedup(
                conn, sgf_content,
                source_id="test",
                solution_fingerprint=_fingerprint(sgf_content),
                fingerprint_version=1,  # Different from DB's 99
            )
            # Version mismatch → conservative, treat as non-match
            assert result.is_duplicate is False
            assert result.event_type == "variant_allowed"
        finally:
            conn.close()

    def test_dedup_result_has_collision_details(self, tmp_path: Path) -> None:
        """DedupResult includes full collision details for structured logging."""
        sgf_content = _make_sgf()
        db_path = tmp_path / "yengo-content.db"

        build_content_db(
            sgf_files={"existing_hash": sgf_content},
            output_path=db_path,
            source="test",
        )

        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        try:
            fp = _fingerprint(sgf_content)
            result = IngestStage._check_dedup(
                conn, sgf_content,
                source_id="test",
                solution_fingerprint=fp,
            )
            assert result.position_hash != ""
            assert result.solution_fingerprint == fp
            assert result.existing_hash is not None
            assert result.existing_source == "test"
            assert result.existing_fingerprint is not None
        finally:
            conn.close()
