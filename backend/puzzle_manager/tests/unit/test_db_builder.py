from __future__ import annotations

import sqlite3

from backend.puzzle_manager.core.db_builder import build_search_db
from backend.puzzle_manager.core.db_models import CollectionMeta, DbVersionInfo, PuzzleEntry


def _make_entry(
    hash: str = "abc123def456789a",
    batch: str = "0001",
    level: int = 120,
    tags: list[int] | None = None,
    cols: list[int] | None = None,
    quality: int = 0,
) -> PuzzleEntry:
    return PuzzleEntry(
        content_hash=hash,
        batch=batch,
        level_id=level,
        tag_ids=tags or [],
        collection_ids=cols or [],
        quality=quality,
    )


def _make_collection(
    id: int = 1,
    slug: str = "test-col",
    name: str = "Test Collection",
) -> CollectionMeta:
    return CollectionMeta(collection_id=id, slug=slug, name=name)


def _build(tmp_path, entries=None, collections=None, **kwargs):
    db_path = tmp_path / "test.db"
    info = build_search_db(
        entries=entries or [],
        collections=collections or [],
        output_path=db_path,
        **kwargs,
    )
    return db_path, info


# ── T6-1 ────────────────────────────────────────────────
class TestBuildCreatesDbFile:
    def test_build_creates_db_file(self, tmp_path):
        db_path, _ = _build(tmp_path, entries=[_make_entry()])
        assert db_path.exists()
        assert db_path.stat().st_size > 0


# ── T6-2 ────────────────────────────────────────────────
class TestSchemaHasAllTables:
    def test_schema_has_all_tables(self, tmp_path):
        db_path, _ = _build(tmp_path)
        conn = sqlite3.connect(db_path)
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        conn.close()
        table_names = {r[0] for r in rows}
        expected = {"puzzles", "puzzle_tags", "puzzle_collections",
                    "collections", "collections_fts"}
        # FTS5 creates auxiliary tables; check our logical tables exist
        assert expected.issubset(table_names)


# ── T6-3 ────────────────────────────────────────────────
class TestSchemaHasAllIndexes:
    EXPECTED_INDEXES = {
        "idx_puzzles_level",
        "idx_puzzles_quality",
        "idx_puzzles_ctype",
        "idx_puzzles_depth",
        "idx_puzzles_ac",
        "idx_tags_tag",
        "idx_tags_hash",
        "idx_cols_col",
        "idx_cols_hash",
    }

    def test_schema_has_all_indexes(self, tmp_path):
        db_path, _ = _build(tmp_path)
        conn = sqlite3.connect(db_path)
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index'"
        ).fetchall()
        conn.close()
        index_names = {r[0] for r in rows}
        assert self.EXPECTED_INDEXES.issubset(index_names)


# ── T6-4 ────────────────────────────────────────────────
class TestPuzzleInsertion:
    def test_puzzle_insertion(self, tmp_path):
        entries = [
            _make_entry(hash="aaa1111111111111", level=100),
            _make_entry(hash="bbb2222222222222", level=120, batch="0002"),
            _make_entry(hash="ccc3333333333333", level=140, quality=3),
        ]
        db_path, _ = _build(tmp_path, entries=entries)
        conn = sqlite3.connect(db_path)
        count = conn.execute("SELECT COUNT(*) FROM puzzles").fetchone()[0]
        assert count == 3

        row = conn.execute(
            "SELECT batch, level_id, quality FROM puzzles WHERE content_hash=?",
            ("ccc3333333333333",),
        ).fetchone()
        conn.close()
        assert row == ("0001", 140, 3)


# ── T6-5 ────────────────────────────────────────────────
class TestTagAssociation:
    def test_tag_association(self, tmp_path):
        entry = _make_entry(tags=[10, 36])
        db_path, _ = _build(tmp_path, entries=[entry])
        conn = sqlite3.connect(db_path)
        rows = conn.execute(
            "SELECT tag_id FROM puzzle_tags WHERE content_hash=? ORDER BY tag_id",
            (entry.content_hash,),
        ).fetchall()
        conn.close()
        assert [r[0] for r in rows] == [10, 36]


# ── T6-6 ────────────────────────────────────────────────
class TestCollectionAssociation:
    def test_collection_association(self, tmp_path):
        entry = _make_entry(cols=[5])
        col = _make_collection(id=5, slug="col-five", name="Col Five")
        db_path, _ = _build(tmp_path, entries=[entry], collections=[col])
        conn = sqlite3.connect(db_path)
        row = conn.execute(
            "SELECT collection_id, sequence_number FROM puzzle_collections "
            "WHERE content_hash=?",
            (entry.content_hash,),
        ).fetchone()
        conn.close()
        assert row[0] == 5
        assert row[1] is None  # no sequence_map provided

    def test_collection_association_with_sequence(self, tmp_path):
        entry = _make_entry(hash="seq1111111111111", cols=[7])
        col = _make_collection(id=7, slug="col-seven", name="Col Seven")
        seq_map = {("seq1111111111111", 7): 42}
        db_path, _ = _build(
            tmp_path, entries=[entry], collections=[col], sequence_map=seq_map,
        )
        conn = sqlite3.connect(db_path)
        row = conn.execute(
            "SELECT sequence_number FROM puzzle_collections WHERE content_hash=?",
            (entry.content_hash,),
        ).fetchone()
        conn.close()
        assert row[0] == 42


# ── T6-7 ────────────────────────────────────────────────
class TestCollectionCatalog:
    def test_collection_catalog(self, tmp_path):
        cols = [
            _make_collection(id=1, slug="alpha", name="Alpha Collection"),
            _make_collection(id=2, slug="beta", name="Beta Collection"),
        ]
        db_path, _ = _build(tmp_path, collections=cols)
        conn = sqlite3.connect(db_path)
        rows = conn.execute(
            "SELECT collection_id, slug, name FROM collections ORDER BY collection_id"
        ).fetchall()
        conn.close()
        assert len(rows) == 2
        assert rows[0] == (1, "alpha", "Alpha Collection")
        assert rows[1] == (2, "beta", "Beta Collection")


# ── T6-8 ────────────────────────────────────────────────
class TestFts5Search:
    def test_fts5_search(self, tmp_path):
        cols = [
            _make_collection(id=1, slug="cho-chikun-elementary", name="Cho Chikun Elementary"),
            _make_collection(id=2, slug="graded-problems", name="Graded Go Problems"),
        ]
        db_path, _ = _build(tmp_path, collections=cols)
        conn = sqlite3.connect(db_path)
        rows = conn.execute(
            "SELECT slug FROM collections_fts WHERE collections_fts MATCH ?",
            ("cho",),
        ).fetchall()
        conn.close()
        assert len(rows) == 1
        assert rows[0][0] == "cho-chikun-elementary"


# ── T6-9 ────────────────────────────────────────────────
class TestReturnsDbVersionInfo:
    def test_returns_db_version_info(self, tmp_path):
        entries = [_make_entry(hash="aaa0000000000000"), _make_entry(hash="bbb0000000000000")]
        _, info = _build(tmp_path, entries=entries)
        assert isinstance(info, DbVersionInfo)
        assert info.puzzle_count == 2
        assert info.db_version  # non-empty
        assert info.generated_at  # non-empty


# ── T6-10 ───────────────────────────────────────────────
class TestEmptyEntries:
    def test_empty_entries(self, tmp_path):
        db_path, info = _build(tmp_path)
        assert db_path.exists()
        assert info.puzzle_count == 0
        conn = sqlite3.connect(db_path)
        count = conn.execute("SELECT COUNT(*) FROM puzzles").fetchone()[0]
        conn.close()
        assert count == 0


# ── GAP-8 verify ────────────────────────────────────────
class TestPuzzleCountComputed:
    """Verify collections.puzzle_count is non-zero after build (RC-4)."""

    def test_puzzle_count_nonzero(self, tmp_path):
        col = _make_collection(id=3, slug="abc", name="ABC")
        entries = [
            _make_entry(hash="aaa0000000000001", cols=[3]),
            _make_entry(hash="bbb0000000000002", cols=[3]),
            _make_entry(hash="ccc0000000000003", cols=[3]),
        ]
        db_path, _ = _build(tmp_path, entries=entries, collections=[col])
        conn = sqlite3.connect(db_path)
        row = conn.execute(
            "SELECT puzzle_count FROM collections WHERE collection_id=?", (3,)
        ).fetchone()
        conn.close()
        assert row[0] == 3

    def test_puzzle_count_zero_when_no_members(self, tmp_path):
        col = _make_collection(id=4, slug="empty", name="Empty")
        db_path, _ = _build(tmp_path, collections=[col])
        conn = sqlite3.connect(db_path)
        row = conn.execute(
            "SELECT puzzle_count FROM collections WHERE collection_id=?", (4,)
        ).fetchone()
        conn.close()
        assert row[0] == 0


# ── GAP-9 verify ────────────────────────────────────────
class TestSequenceNumberPopulated:
    """Verify sequence_number is populated via sequence_map."""

    def test_multiple_entries_ordered(self, tmp_path):
        col = _make_collection(id=5, slug="seq-col", name="Seq Col")
        entries = [
            _make_entry(hash="aaa0000000000010", cols=[5]),
            _make_entry(hash="bbb0000000000020", cols=[5]),
            _make_entry(hash="ccc0000000000030", cols=[5]),
        ]
        seq_map = {
            ("aaa0000000000010", 5): 1,
            ("bbb0000000000020", 5): 2,
            ("ccc0000000000030", 5): 3,
        }
        db_path, _ = _build(
            tmp_path, entries=entries, collections=[col], sequence_map=seq_map
        )
        conn = sqlite3.connect(db_path)
        rows = conn.execute(
            "SELECT content_hash, sequence_number FROM puzzle_collections "
            "WHERE collection_id=5 ORDER BY sequence_number"
        ).fetchall()
        conn.close()
        assert len(rows) == 3
        assert rows[0] == ("aaa0000000000010", 1)
        assert rows[1] == ("bbb0000000000020", 2)
        assert rows[2] == ("ccc0000000000030", 3)
