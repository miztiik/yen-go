"""Unit tests for cross-source dedup bypass (T7)."""

import sqlite3
from pathlib import Path

from backend.puzzle_manager.core.content_db import build_content_db, compute_solution_fingerprint
from backend.puzzle_manager.core.sgf_parser import parse_sgf
from backend.puzzle_manager.stages.ingest import IngestStage


def _make_sgf(black_stones: str = "AB[pd][qf]", white_stones: str = "AW[qd][pe]") -> str:
    return (
        f"(;FF[4]GM[1]SZ[19]"
        f"{black_stones}{white_stones}"
        f";B[oe]"
        f"(;W[of];B[ne])"
        f"(;W[ne];B[of]))"
    )


def _fingerprint(sgf: str) -> str:
    game = parse_sgf(sgf)
    return compute_solution_fingerprint(game.solution_tree)


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
            result = IngestStage._check_dedup(
                conn, new_sgf,
                source_id="source_b",
                solution_fingerprint=_fingerprint(new_sgf),
            )
            assert result.is_duplicate is False
        finally:
            conn.close()

    def test_same_source_match_rejects(self, tmp_path: Path) -> None:
        """Same source + same position + same solution → reject."""
        db_path = tmp_path / "content.db"
        sgf = _make_sgf()
        build_content_db(
            sgf_files={"hash_dup": sgf},
            output_path=db_path,
            source="source_a",
        )

        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        try:
            result = IngestStage._check_dedup(
                conn, sgf,
                source_id="source_a",
                solution_fingerprint=_fingerprint(sgf),
            )
            assert result.is_duplicate is True
            assert result.existing_hash == "hash_dup"
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
            result = IngestStage._check_dedup(
                conn, sgf,
                source_id="source_b",
                solution_fingerprint=_fingerprint(sgf),
            )
            assert result.is_duplicate is False
        finally:
            conn.close()

    def test_three_sources_one_matches_rejects(self, tmp_path: Path) -> None:
        """3 entries, one from same source with same fingerprint → reject."""
        db_path = tmp_path / "content.db"
        sgf = _make_sgf()
        fp = _fingerprint(sgf)

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
            "solution_fingerprint, fingerprint_version, "
            "board_size, black_stones, white_stones, first_player, stone_count, source) "
            "VALUES (?, ?, ?, ?, 1, 19, 'pd,qf', 'pe,qd', 'B', 4, ?)",
            ("hash_s2", sgf, pos_hash, fp, "source_b"),
        )
        conn.commit()
        conn.close()

        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        try:
            # source_a already has an entry with same fingerprint → reject
            result = IngestStage._check_dedup(
                conn, sgf,
                source_id="source_a",
                solution_fingerprint=fp,
            )
            assert result.is_duplicate is True
            assert result.existing_hash == "hash_s1"
        finally:
            conn.close()

    def test_three_sources_none_matches_allows(self, tmp_path: Path) -> None:
        """3 entries from other sources → allow through."""
        db_path = tmp_path / "content.db"
        sgf = _make_sgf()
        fp = _fingerprint(sgf)

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
            "solution_fingerprint, fingerprint_version, "
            "board_size, black_stones, white_stones, first_player, stone_count, source) "
            "VALUES (?, ?, ?, ?, 1, 19, 'pd,qf', 'pe,qd', 'B', 4, ?)",
            ("hash_s2", sgf, pos_hash, fp, "source_b"),
        )
        conn.commit()
        conn.close()

        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        try:
            # source_c has no entries → allow
            result = IngestStage._check_dedup(
                conn, sgf,
                source_id="source_c",
                solution_fingerprint=fp,
            )
            assert result.is_duplicate is False
        finally:
            conn.close()
