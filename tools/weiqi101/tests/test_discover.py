"""Tests for 101weiqi discovery module (BFS book/category exploration)."""

import json

from tools.weiqi101.discover import (
    KNOWN_CATEGORIES,
    BookInfo,
    BookTag,
    CategoryInfo,
    DiscoveryCatalog,
    _extract_book_info_from_tag_page,
    _extract_book_tags_from_main,
    _extract_chapters_from_book_page,
    _extract_js_var,
    _extract_pagination,
    _extract_puzzle_count_from_status,
    _extract_puzzle_ids_from_chapter_page,
)

# ---------- _extract_pagination ----------


class TestExtractPagination:
    def test_single_page_returns_1(self):
        html = "<div>No pagination here</div>"
        assert _extract_pagination(html) == 1

    def test_numbered_pages_with_next(self):
        html = """
        <a href="?page=1">1</a>
        <a href="?page=2">2</a>
        <a href="?page=3">3</a>
        <a href="?page=74">74</a>
        \u4e0b\u4e00\u9875
        """
        assert _extract_pagination(html) == 74

    def test_page_numbers_fallback(self):
        """When next-page marker is absent, find max page number."""
        html = """
        <a href="?page=1">1</a>
        <a href="?page=5">5</a>
        <a href="?page=200">200</a>
        """
        assert _extract_pagination(html) == 200

    def test_ignores_huge_numbers(self):
        """Numbers >= 10000 are not page numbers."""
        html = """
        <a>78000</a>
        <a>3</a>
        """
        assert _extract_pagination(html) == 3


# ---------- _extract_js_var ----------


class TestExtractJsVar:
    def test_extracts_list(self):
        html = 'var books = [{"id": 1}, {"id": 2}];'
        result = _extract_js_var(html, "books")
        assert isinstance(result, list)
        assert len(result) == 2

    def test_extracts_dict(self):
        html = 'var config = {"key": "value"};'
        result = _extract_js_var(html, "config")
        assert isinstance(result, dict)
        assert result["key"] == "value"

    def test_returns_none_for_missing(self):
        html = "var other = [];"
        assert _extract_js_var(html, "books") is None

    def test_handles_nested_braces(self):
        html = 'var data = [{"ba": {"qcount": 120}}];'
        result = _extract_js_var(html, "data")
        assert result[0]["ba"]["qcount"] == 120

    def test_extracts_empty_list(self):
        html = "var items = [];"
        result = _extract_js_var(html, "items")
        assert result == []

    def test_matches_const_declaration(self):
        html = 'const settings = {"mode": "dark"};'
        result = _extract_js_var(html, "settings")
        assert isinstance(result, dict)
        assert result["mode"] == "dark"

    def test_matches_let_declaration(self):
        html = 'let items = [1, 2, 3];'
        result = _extract_js_var(html, "items")
        assert result == [1, 2, 3]

    def test_nodedata_wrapper_fallback(self):
        """Chapter pages use var nodedata = {"pagedata": {...}}."""
        html = 'var nodedata = {"pagedata": {"qs": [{"qid": 100}], "maxpage": 2}};'
        result = _extract_js_var(html, "pagedata")
        assert isinstance(result, dict)
        assert result["maxpage"] == 2
        assert result["qs"][0]["qid"] == 100

    def test_nodedata_direct_extraction(self):
        html = 'var nodedata = {"pagedata": {"qs": []}};'
        result = _extract_js_var(html, "nodedata")
        assert isinstance(result, dict)
        assert "pagedata" in result

    def test_prefers_direct_var_over_nodedata(self):
        """If both var pagedata and nodedata.pagedata exist, direct wins."""
        html = 'var pagedata = {"source": "direct"}; var nodedata = {"pagedata": {"source": "nested"}};'
        result = _extract_js_var(html, "pagedata")
        assert result["source"] == "direct"


# ---------- _extract_chapters_from_book_page ----------


class TestExtractChaptersFromBookPage:
    def test_bookdata_chapters(self):
        """Current site format: chapters inside bookdata."""
        chapters_data = [
            {"id": 90, "name": "\u89d2\u4e4b\u90e8"},
            {"id": 91, "name": "\u8fb9\u4e4b\u90e8"},
        ]
        html = f'var bookdata = {{"chapters": {json.dumps(chapters_data, ensure_ascii=False)}}};'
        result = _extract_chapters_from_book_page(html)
        assert len(result) == 2
        assert result[0]["id"] == 90
        assert result[0]["name"] == "\u89d2\u4e4b\u90e8"

    def test_pagedata_chapters(self):
        """Legacy format: chapters inside pagedata."""
        chapters_data = [{"id": 10, "name": "Ch1"}]
        html = f'var pagedata = {{"chapters": {json.dumps(chapters_data)}}};'
        result = _extract_chapters_from_book_page(html)
        assert len(result) == 1
        assert result[0]["id"] == 10

    def test_href_fallback(self):
        html = '<a href="/book/5/90/">Ch1</a><a href="/book/5/91/">Ch2</a>'
        result = _extract_chapters_from_book_page(html)
        assert len(result) == 2
        assert result[0]["id"] == 90


# ---------- _extract_puzzle_ids_from_chapter_page ----------


class TestExtractPuzzleIdsFromChapterPage:
    def test_nodedata_qs(self):
        """Chapter pages embed puzzle IDs in nodedata.pagedata.qs[].qid."""
        qs = [{"qid": 100, "publicid": 100}, {"qid": 200, "publicid": 200}]
        html = f'var nodedata = {{"pagedata": {{"qs": {json.dumps(qs)}}}}};'
        result = _extract_puzzle_ids_from_chapter_page(html)
        assert result == [100, 200]

    def test_direct_pagedata_qs(self):
        """Levelorder pages embed puzzle IDs in var pagedata.qs[]."""
        qs = [{"qid": 50}]
        html = f'var pagedata = {{"qs": {json.dumps(qs)}}};'
        result = _extract_puzzle_ids_from_chapter_page(html)
        assert result == [50]

    def test_empty_page(self):
        html = "<div>No puzzles</div>"
        result = _extract_puzzle_ids_from_chapter_page(html)
        assert result == []


# ---------- _extract_book_info_from_tag_page ----------


class TestExtractBookInfoFromTagPage:
    def test_parses_standard_entry(self):
        books_data = [{"id": 26378, "name": "\u6b7b\u6d3b\u5999\u6a5f",
            "booktype": 0, "ba": {"qcount": 120, "qlevelname": "2D"},
            "username": "user1", "tags": [{"id": 1, "name": "\u53e4\u5178\u68cb\u66f8"}]}]
        html = f"var books = {json.dumps(books_data, ensure_ascii=False)};"
        books = _extract_book_info_from_tag_page(html)
        assert len(books) == 1
        assert books[0].book_id == 26378
        assert books[0].name == "\u6b7b\u6d3b\u5999\u6a5f"
        assert books[0].puzzle_count == 120
        assert books[0].difficulty == "2D"
        assert books[0].name_en != ""  # Translator should populate this

    def test_parses_multiple_entries(self):
        books_data = [
            {"id": 100, "name": "\u68cb\u7d4c\u8846\u5999",
             "ba": {"qcount": 200, "qlevelname": "3D"}, "tags": []},
            {"id": 200, "name": "\u767a\u967d\u8ad6",
             "ba": {"qcount": 180, "qlevelname": "4D"}, "tags": []},
        ]
        html = f"var books = {json.dumps(books_data, ensure_ascii=False)};"
        books = _extract_book_info_from_tag_page(html)
        assert len(books) == 2
        assert books[0].book_id == 100
        assert books[1].book_id == 200
        # Both should have translated names
        for book in books:
            assert book.name_en != ""

    def test_empty_page(self):
        html = "<div>No books here</div>"
        books = _extract_book_info_from_tag_page(html)
        assert books == []

    def test_missing_ba_field(self):
        books_data = [{"id": 65, "name": "Test Book", "tags": []}]
        html = f"var books = {json.dumps(books_data)};"
        books = _extract_book_info_from_tag_page(html)
        assert len(books) == 1
        assert books[0].puzzle_count == 0
        assert books[0].difficulty == ""

    def test_extracts_sharer(self):
        books_data = [{"id": 1, "name": "Book", "username": "testuser",
                        "ba": {"qcount": 10, "qlevelname": "1K"}, "tags": []}]
        html = f"var books = {json.dumps(books_data)};"
        books = _extract_book_info_from_tag_page(html)
        assert books[0].sharer == "testuser"


# ---------- _extract_book_tags_from_main ----------


class TestExtractBookTagsFromMain:
    def test_parses_tag_with_count(self):
        tags_data = [{"id": 42, "name": "\u8be8\u68cb120\u7cfb\u5217", "bookcount": 10}]
        html = f"var tags = {json.dumps(tags_data, ensure_ascii=False)};"
        tags = _extract_book_tags_from_main(html)
        assert len(tags) == 1
        assert tags[0].tag_id == 42
        assert tags[0].name == "\u8be8\u68cb120\u7cfb\u5217"
        assert tags[0].book_count == 10
        assert tags[0].name_en != ""  # Translator should populate this

    def test_parses_tag_without_count(self):
        tags_data = [{"id": 1, "name": "\u53e4\u5178\u68cb\u4e66"}]
        html = f"var tags = {json.dumps(tags_data, ensure_ascii=False)};"
        tags = _extract_book_tags_from_main(html)
        assert len(tags) == 1
        assert tags[0].tag_id == 1
        assert tags[0].book_count == 0
        assert tags[0].name_en != ""

    def test_empty_tags(self):
        html = "<div>No tags</div>"
        tags = _extract_book_tags_from_main(html)
        assert tags == []

    def test_multiple_tags(self):
        tags_data = [
            {"id": 1, "name": "Classical", "bookcount": 11},
            {"id": 2, "name": "Original", "bookcount": 23},
            {"id": 42, "name": "Series", "bookcount": 10},
        ]
        html = f"var tags = {json.dumps(tags_data)};"
        tags = _extract_book_tags_from_main(html)
        assert len(tags) == 3
        ids = {t.tag_id for t in tags}
        assert ids == {1, 2, 42}


# ---------- _extract_puzzle_count_from_status ----------


class TestExtractPuzzleCountFromStatus:
    def test_parses_standard_format(self):
        html = "\u6b63\u5f0f\u4f7f\u7528\u9898\u76ee : 181098\u9053"
        assert _extract_puzzle_count_from_status(html) == 181098

    def test_colon_variant(self):
        html = "\u6b63\u5f0f\u4f7f\u7528\u9898\u76ee\uff1a200000"
        assert _extract_puzzle_count_from_status(html) == 200000

    def test_statusnum_div_format(self):
        html = '<div class="statusnum">:  181101\u9053</div>'
        assert _extract_puzzle_count_from_status(html) == 181101

    def test_not_found(self):
        html = "<div>No puzzle count here</div>"
        assert _extract_puzzle_count_from_status(html) == 0


# ---------- Data model tests ----------


class TestBookInfo:
    def test_to_dict(self):
        book = BookInfo(
            book_id=190,
            name="\u767a\u967d\u8ad6",
            puzzle_count=180,
            difficulty="4D",
            tags=["\u53e4\u5178\u68cb\u4e66"],
        )
        d = book.to_dict()
        assert d["book_id"] == 190
        assert d["name"] == "\u767a\u967d\u8ad6"
        assert d["puzzle_count"] == 180
        assert d["difficulty"] == "4D"
        assert d["tags"] == ["\u53e4\u5178\u68cb\u4e66"]
        assert "name_en" in d

    def test_default_values(self):
        book = BookInfo(book_id=1, name="Test")
        d = book.to_dict()
        assert d["puzzle_count"] == 0
        assert d["difficulty"] == ""
        assert d["tags"] == []
        assert d["name_en"] == ""

    def test_name_en_in_dict(self):
        book = BookInfo(book_id=1, name="Test", name_en="Test Book")
        d = book.to_dict()
        assert d["name_en"] == "Test Book"


class TestBookTag:
    def test_to_dict(self):
        tag = BookTag(tag_id=42, name="\u8be8\u68cb120\u7cfb\u5217", book_count=10)
        d = tag.to_dict()
        assert d["tag_id"] == 42
        assert d["name"] == "\u8be8\u68cb120\u7cfb\u5217"
        assert d["book_count"] == 10
        assert "name_en" in d


class TestCategoryInfo:
    def test_to_dict(self):
        cat = CategoryInfo(slug="chizi", chinese_name="\u5403\u5b50", page_count=200)
        d = cat.to_dict()
        assert d["slug"] == "chizi"
        assert d["chinese_name"] == "\u5403\u5b50"
        assert d["page_count"] == 200
        assert "name_en" in d


class TestDiscoveryCatalog:
    def test_to_dict_empty(self):
        catalog = DiscoveryCatalog()
        d = catalog.to_dict()
        assert d["total_active_puzzles"] == 0
        assert d["books_count"] == 0
        assert d["book_tags_count"] == 0
        assert d["categories_count"] == 0

    def test_to_dict_with_data(self):
        catalog = DiscoveryCatalog(
            total_active_puzzles=181098,
            books=[BookInfo(book_id=1, name="Test", puzzle_count=120)],
            book_tags=[BookTag(tag_id=1, name="Classical", book_count=11)],
            categories=[CategoryInfo(slug="chizi", chinese_name="\u5403\u5b50", page_count=200)],
        )
        d = catalog.to_dict()
        assert d["total_active_puzzles"] == 181098
        assert d["books_count"] == 1
        assert d["book_tags_count"] == 1
        assert d["categories_count"] == 1

    def test_save_creates_json(self, tmp_path):
        catalog = DiscoveryCatalog(total_active_puzzles=42)
        out = tmp_path / "catalog.json"
        catalog.save(out)
        assert out.exists()
        data = json.loads(out.read_text(encoding="utf-8"))
        assert data["total_active_puzzles"] == 42


# ---------- KNOWN_CATEGORIES ----------


class TestKnownCategories:
    def test_has_expected_slugs(self):
        slugs = [slug for slug, _ in KNOWN_CATEGORIES]
        assert "chizi" in slugs
        assert "pianzhao" in slugs
        assert "buju" in slugs
        assert "guanzi" in slugs
        assert "zhongpan" in slugs
        assert "shizhan" in slugs
        assert "qili" in slugs

    def test_each_has_chinese_name(self):
        for slug, name in KNOWN_CATEGORIES:
            assert len(name) > 0, f"Empty Chinese name for slug '{slug}'"
