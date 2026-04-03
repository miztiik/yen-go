"""Tests for chapter-aware download wiring (v14 YL CHAPTER/POSITION)."""

from tools.weiqi101.discover import BookChapter, BookChapterIndex
from tools.weiqi101.orchestrator import DownloadConfig


class TestDownloadConfigChapterSequences:
    """DownloadConfig stores chapter sequence lookup."""

    def test_defaults_to_none(self) -> None:
        config = DownloadConfig()
        assert config.chapter_sequences is None
        assert config.book_collection_slug is None

    def test_stores_chapter_lookup(self) -> None:
        config = DownloadConfig(
            chapter_sequences={100: ("1", 3), 200: ("2", 1)},
            book_collection_slug="cho-elementary",
        )
        assert config.chapter_sequences[100] == ("1", 3)
        assert config.chapter_sequences[200] == ("2", 1)
        assert config.book_collection_slug == "cho-elementary"


class TestBuildChapterSequencesFromIndex:
    """Build puzzle_id → (chapter_str, position) from BookChapterIndex."""

    def test_builds_lookup_from_chapter_index(self) -> None:
        """Same logic as __main__.py book-id mode."""
        index = BookChapterIndex(
            book_id=42,
            chapters=[
                BookChapter(chapter_id=10, chapter_number=1, puzzle_ids=[100, 101, 102]),
                BookChapter(chapter_id=20, chapter_number=2, puzzle_ids=[200, 201]),
            ],
        )
        sequences: dict[int, tuple[str, int]] = {}
        for ch in index.chapters:
            ch_str = str(ch.chapter_number)
            for pos, pid in enumerate(ch.puzzle_ids, start=1):
                sequences[pid] = (ch_str, pos)

        assert sequences == {
            100: ("1", 1),
            101: ("1", 2),
            102: ("1", 3),
            200: ("2", 1),
            201: ("2", 2),
        }

    def test_all_puzzle_ids_preserves_chapter_order(self) -> None:
        """all_puzzle_ids() returns IDs in chapter order."""
        index = BookChapterIndex(
            book_id=42,
            chapters=[
                BookChapter(chapter_id=10, chapter_number=1, puzzle_ids=[100, 101]),
                BookChapter(chapter_id=20, chapter_number=2, puzzle_ids=[200]),
            ],
        )
        assert index.all_puzzle_ids() == [100, 101, 200]


class TestChapterAwareCollectionEntries:
    """Test the enrichment logic that builds collection_entries with chapter/position."""

    def _build_entries(
        self,
        puzzle_id: int,
        config: DownloadConfig,
        type_slug: str | None = None,
    ) -> list[str] | None:
        """Simulate the collection_entries logic from _process_html."""
        collection_entries: list[str] | None = None
        if config.match_collections and type_slug:
            collection_entries = [type_slug]

        if config.chapter_sequences and puzzle_id in config.chapter_sequences:
            chapter_str, position = config.chapter_sequences[puzzle_id]
            book_slug = config.book_collection_slug
            if book_slug:
                entry = f"{book_slug}:{chapter_str}/{position}"
                if collection_entries is None:
                    collection_entries = [entry]
                elif book_slug not in [e.split(":")[0] for e in collection_entries]:
                    collection_entries.append(entry)
        return collection_entries

    def test_chapter_position_entry_emitted(self) -> None:
        config = DownloadConfig(
            chapter_sequences={100: ("1", 3)},
            book_collection_slug="cho-elementary",
        )
        entries = self._build_entries(100, config)
        assert entries == ["cho-elementary:1/3"]

    def test_bare_slug_plus_chapter_position(self) -> None:
        config = DownloadConfig(
            chapter_sequences={100: ("2", 5)},
            book_collection_slug="cho-elementary",
        )
        entries = self._build_entries(100, config, type_slug="life-and-death")
        assert entries == ["life-and-death", "cho-elementary:2/5"]

    def test_no_duplicate_when_same_slug(self) -> None:
        """If type-based mapping resolves to same slug as book, don't add twice."""
        config = DownloadConfig(
            chapter_sequences={100: ("1", 1)},
            book_collection_slug="life-and-death",
        )
        entries = self._build_entries(100, config, type_slug="life-and-death")
        # type-based gives "life-and-death", chapter-aware would also give
        # "life-and-death:1/1" — but slug matches, so it shouldn't add
        assert entries == ["life-and-death"]

    def test_puzzle_not_in_lookup_no_chapter_entry(self) -> None:
        config = DownloadConfig(
            chapter_sequences={100: ("1", 1)},
            book_collection_slug="cho-elementary",
        )
        entries = self._build_entries(999, config, type_slug="life-and-death")
        assert entries == ["life-and-death"]

    def test_no_slug_no_chapter_entry(self) -> None:
        config = DownloadConfig(
            chapter_sequences={100: ("1", 1)},
            book_collection_slug=None,
        )
        entries = self._build_entries(100, config)
        assert entries is None

    def test_no_chapter_sequences_no_effect(self) -> None:
        config = DownloadConfig()
        entries = self._build_entries(100, config, type_slug="tesuji")
        assert entries == ["tesuji"]
