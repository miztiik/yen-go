"""Unit tests for cross-source dedup bypass (T7)."""

import sqlite3
from pathlib import Path

from backend.puzzle_manager.core.content_db import build_content_db
from backend.puzzle_manager.stages.ingest import IngestStage


def _make_sgf(black_stones: str = "AB[pd][qf]", white_stones: str = "AW[qd][pe]") -> str:
    return (
        f"(;FF[4]GM[1]SZ[19]"
        f"{black_stones}{white_stones}"
        f";B[oe]"
        f"(;W[of];B[ne])"
        f"(;W[ne];B[of]))"
    )


class TestDedupBypass:
    """Cross-source dedup bypass tests."""

    def test_no_match_allows(self, tmp_path: Path) -> None:
        """No position match → allow through."""
        db_path = tmp_path / "content.db"
        existing_sgf = _make_sgf(black_stones="AB[dd]", white_stones="AW[ee]")
        build_content_db(
            sgf_files={"hash_existing": existing_sgf},
            output_path=db_path,
            source="source_a",
        )

        new_sgf = _make_sgf(black_stones="AB[pp]", white_stones="AW[qq]")
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        try:
            result = IngestStage._check_dedup(conn, new_sgf, source_id="source_b")
            assert result is None
        finally:
            conn.close()

    def test_same_source_match_rejects(self, tmp_path: Path) -> None:
        """Same source + same position → reject."""
        db_path = tmp_path / "content.db"
        sgf = _make_sgf()
        build_content_db(
            sgf_files={"hash_dup": sgf},
            output_path=db_path,
            source="source_a",
        )

        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        try:
            result = IngestStage._check_dedup(conn, sgf, source_id="source_a")
            assert result == "hash_dup"
        finally:
            conn.close()

    def test_different_source_match_allows(self, tmp_path: Path) -> None:
        """Different source + same position → allow through."""
        db_path = tmp_path / "content.db"
        sgf = _make_sgf()
        build_content_db(
            sgf_files={"hash_orig": sgf},
            output_path=db_path,
            source="source_a",
        )

        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        try:
            result = IngestStage._check_dedup(conn, sgf, source_id="source_b")
            assert result is None
        finally:
            conn.close()

    def test_three_sources_one_matches_rejects(self, tmp_path: Path) -> None:
        """3 entries, one from same source → reject."""
        db_path = tmp_path / "content.db"
        sgf = _make_sgf()

        # Build DB with entries from 3 sources (same position)
        build_content_db(
            sgf_files={"hash_s1": sgf},
            output_path=db_path,
            source="source_a",
        )
        # Add second entry with same position but different hash
        conn = sqlite3.connect(str(db_path))
        pos_hash = conn.execute(
            "SELECT position_hash FROM sgf_files WHERE content_hash='hash_s1'"
        ).fetchone()[0]
        conn.execute(
            "INSERT INTO sgf_files (content_hash, sgf_content, position_hash, "
            "board_size, black_stones, white_stones, first_player, stone_count, source) "
            "VALUES (?, ?, ?, 19, 'pd,qf', 'pe,qd', 'B', 4, ?)",
            ("hash_s2", sgf, pos_hash, "source_b"),
        )
        conn.commit()
        conn.close()

        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        try:
            # source_a already has an entry → reject
            result = IngestStage._check_dedup(conn, sgf, source_id="source_a")
            assert result == "hash_s1"
        finally:
            conn.close()

    def test_three_sources_none_matches_allows(self, tmp_path: Path) -> None:
        """3 entries from other sources → allow through."""
        db_path = tmp_path / "content.db"
        sgf = _make_sgf()

        build_content_db(
            sgf_files={"hash_s1": sgf},
            output_path=db_path,
            source="source_a",
        )
        conn = sqlite3.connect(str(db_path))
        pos_hash = conn.execute(
            "SELECT position_hash FROM sgf_files WHERE content_hash='hash_s1'"
        ).fetchone()[0]
        conn.execute(
            "INSERT INTO sgf_files (content_hash, sgf_content, position_hash, "
            "board_size, black_stones, white_stones, first_player, stone_count, source) "
            "VALUES (?, ?, ?, 19, 'pd,qf', 'pe,qd', 'B', 4, ?)",
            ("hash_s2", sgf, pos_hash, "source_b"),
        )
        conn.commit()
        conn.close()

        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        try:
            # source_c has no entries → allow
            result = IngestStage._check_dedup(conn, sgf, source_id="source_c")
            assert result is None
        finally:
            conn.close()
