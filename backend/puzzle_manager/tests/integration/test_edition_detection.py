"""Integration tests for edition detection (T14).

Tests create_editions() via both publish and rollback paths.
"""

from pathlib import Path

from backend.puzzle_manager.core.content_db import build_content_db
from backend.puzzle_manager.core.db_models import CollectionMeta, PuzzleEntry
from backend.puzzle_manager.core.edition_detection import _edition_id, create_editions


def _make_sgf(
    black: str = "AB[pd]", white: str = "AW[qd]",
    collection: str | None = None,
) -> str:
    yl = f"YL[{collection}]" if collection else ""
    return f"(;FF[4]GM[1]SZ[19]{yl}{black}{white};B[oe])"


def _build_db(tmp_path: Path, entries: dict[str, tuple[str, str]]) -> Path:
    """Build a content DB with entries: {hash: (sgf, source)}."""
    db_path = tmp_path / "yengo-content.db"
    for content_hash, (sgf, source) in entries.items():
        build_content_db(
            sgf_files={content_hash: sgf},
            output_path=db_path,
            source=source,
        )
    return db_path


class TestEditionDetection:
    """Tests for create_editions()."""

    def test_two_sources_creates_two_editions(self, tmp_path: Path) -> None:
        """2-source collection → 2 editions."""
        db_path = _build_db(tmp_path, {
            "h1": (_make_sgf(black="AB[pd]", white="AW[qd]", collection="cho-elementary"), "source_a"),
            "h2": (_make_sgf(black="AB[dd]", white="AW[cd]", collection="cho-elementary"), "source_a"),
            "h3": (_make_sgf(black="AB[pp]", white="AW[qp]", collection="cho-elementary"), "source_b"),
        })

        parent = CollectionMeta(
            collection_id=10, slug="cho-elementary", name="Cho Elementary", category="author",
        )
        entries = [
            PuzzleEntry(content_hash="h1", batch="0001", level_id=130, collection_ids=[10]),
            PuzzleEntry(content_hash="h2", batch="0001", level_id=130, collection_ids=[10]),
            PuzzleEntry(content_hash="h3", batch="0001", level_id=130, collection_ids=[10]),
        ]

        editions = create_editions(entries, [parent], db_path)

        assert len(editions) == 2
        assert parent.attrs["is_parent"] is True
        assert len(parent.attrs["edition_ids"]) == 2

    def test_single_source_no_editions(self, tmp_path: Path) -> None:
        """1-source collection → no editions."""
        db_path = _build_db(tmp_path, {
            "h1": (_make_sgf(collection="test-col"), "source_a"),
            "h2": (_make_sgf(black="AB[dd]", white="AW[cd]", collection="test-col"), "source_a"),
        })

        parent = CollectionMeta(
            collection_id=20, slug="test-col", name="Test", category="technique",
        )
        entries = [
            PuzzleEntry(content_hash="h1", batch="0001", level_id=130, collection_ids=[20]),
            PuzzleEntry(content_hash="h2", batch="0001", level_id=130, collection_ids=[20]),
        ]

        editions = create_editions(entries, [parent], db_path)
        assert len(editions) == 0
        assert "is_parent" not in parent.attrs

    def test_parent_has_is_parent_flag(self, tmp_path: Path) -> None:
        """Parent collection gets is_parent=true after edition creation."""
        db_path = _build_db(tmp_path, {
            "h1": (_make_sgf(collection="test-parent"), "src_a"),
            "h2": (_make_sgf(black="AB[dd]", white="AW[cd]", collection="test-parent"), "src_b"),
        })

        parent = CollectionMeta(
            collection_id=30, slug="test-parent", name="Test Parent", category="graded",
        )
        entries = [
            PuzzleEntry(content_hash="h1", batch="0001", level_id=130, collection_ids=[30]),
            PuzzleEntry(content_hash="h2", batch="0001", level_id=130, collection_ids=[30]),
        ]

        create_editions(entries, [parent], db_path)
        assert parent.attrs["is_parent"] is True

    def test_edition_independent_sequences(self, tmp_path: Path) -> None:
        """Each edition has independent puzzle membership."""
        db_path = _build_db(tmp_path, {
            "h1": (_make_sgf(collection="seq-test"), "src_a"),
            "h2": (_make_sgf(black="AB[dd]", white="AW[cd]", collection="seq-test"), "src_a"),
            "h3": (_make_sgf(black="AB[pp]", white="AW[qp]", collection="seq-test"), "src_b"),
        })

        parent = CollectionMeta(
            collection_id=40, slug="seq-test", name="Seq Test", category="author",
        )
        entries = [
            PuzzleEntry(content_hash="h1", batch="0001", level_id=130, collection_ids=[40]),
            PuzzleEntry(content_hash="h2", batch="0001", level_id=130, collection_ids=[40]),
            PuzzleEntry(content_hash="h3", batch="0001", level_id=130, collection_ids=[40]),
        ]

        create_editions(entries, [parent], db_path)

        # h1, h2 should be in source_a edition; h3 in source_b edition
        eid_a = _edition_id("seq-test", "src_a")
        eid_b = _edition_id("seq-test", "src_b")

        h1_entry = next(e for e in entries if e.content_hash == "h1")
        h3_entry = next(e for e in entries if e.content_hash == "h3")

        assert eid_a in h1_entry.collection_ids
        assert 40 not in h1_entry.collection_ids  # Remapped away from parent
        assert eid_b in h3_entry.collection_ids
        assert 40 not in h3_entry.collection_ids

    def test_edition_id_deterministic(self) -> None:
        """Same slug+source always produces same edition ID."""
        id1 = _edition_id("cho-elementary", "source_a")
        id2 = _edition_id("cho-elementary", "source_a")
        assert id1 == id2
        assert 100_000 <= id1 <= 10_100_000

    def test_missing_content_db_returns_empty(self, tmp_path: Path) -> None:
        """No content DB → returns empty list."""
        missing_path = tmp_path / "nonexistent.db"
        entries: list[PuzzleEntry] = []
        collections: list[CollectionMeta] = []
        result = create_editions(entries, collections, missing_path)
        assert result == []
