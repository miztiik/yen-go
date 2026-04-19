"""Tests for local collections mapping."""

from tools.weiqi101._local_collections_mapping import (
    enrich_collections_from_bookinfos,
    resolve_book_slug,
    resolve_collection_slug,
)


def test_life_and_death():
    slug = resolve_collection_slug("死活题")
    assert slug == "life-and-death"


def test_tesuji():
    slug = resolve_collection_slug("手筋")
    assert slug == "tesuji-problems"


def test_joseki():
    slug = resolve_collection_slug("定式")
    assert slug == "joseki-problems"


def test_endgame():
    slug = resolve_collection_slug("官子")
    assert slug == "endgame-problems"


def test_capture_race():
    slug = resolve_collection_slug("对杀")
    assert slug == "capturing-race"


def test_capture_race_variant():
    slug = resolve_collection_slug("对杀题")
    assert slug == "capturing-race"


def test_unknown_category():
    slug = resolve_collection_slug("未知")
    assert slug is None


def test_empty_string():
    slug = resolve_collection_slug("")
    assert slug is None


# Additional categories

def test_chizi_collection():
    slug = resolve_collection_slug("吃子")
    assert slug == "capture-problems"


def test_pianzhao_collection():
    slug = resolve_collection_slug("骗招")
    assert slug == "tesuji-problems"


def test_shizhan_collection():
    slug = resolve_collection_slug("实战")
    assert slug == "general-practice"


def test_qili_collection():
    slug = resolve_collection_slug("棋理")
    assert slug == "general-practice"


def test_mofang_collection():
    slug = resolve_collection_slug("模仿")
    assert slug == "general-practice"


# English aliases (from qday sweep, 2015+ daily puzzles)

def test_english_life_and_death():
    assert resolve_collection_slug("Life & Death") == "life-and-death"


def test_english_fight():
    assert resolve_collection_slug("Fight") == "capturing-race"


def test_english_tesuji():
    assert resolve_collection_slug("Tesuji") == "tesuji-problems"


def test_english_opening():
    assert resolve_collection_slug("Opening") == "opening-problems"


def test_english_joseki():
    assert resolve_collection_slug("Joseki") == "joseki-problems"


def test_english_endgame():
    assert resolve_collection_slug("Endgame") == "endgame-problems"


def test_english_comprehensive():
    assert resolve_collection_slug("Comprehensive") == "general-practice"


def test_english_middle_game():
    assert resolve_collection_slug("Middle Game") == "general-practice"


def test_english_principles():
    assert resolve_collection_slug("Principles") == "general-practice"


# bookinfos enrichment

def test_bookinfos_empty_returns_unchanged():
    assert enrich_collections_from_bookinfos(["life-and-death"], []) == ["life-and-death"]


def test_bookinfos_none_input_empty_list():
    assert enrich_collections_from_bookinfos(None, []) is None


def test_bookinfos_adds_book_slug():
    result = enrich_collections_from_bookinfos(None, [{"book_id": 65, "name": "Test"}])
    assert result == ["gokyo-shumyo"]


def test_bookinfos_appends_to_existing():
    result = enrich_collections_from_bookinfos(["life-and-death"], [{"book_id": 197}])
    assert result == ["life-and-death", "go-seigen-tsumego"]


def test_bookinfos_multiple_books():
    result = enrich_collections_from_bookinfos(None, [{"book_id": 2}, {"book_id": 190}])
    assert result == ["tenryuzu", "kuwabara-hatsuyoron"]


def test_bookinfos_no_duplicate():
    result = enrich_collections_from_bookinfos(
        ["gokyo-shumyo"], [{"book_id": 65}],
    )
    assert result.count("gokyo-shumyo") == 1


def test_bookinfos_skips_missing_id():
    result = enrich_collections_from_bookinfos(None, [{"name": "No ID"}])
    assert result is None


def test_bookinfos_uses_id_fallback():
    """Accepts 'id' key as fallback when 'book_id' is absent."""
    result = enrich_collections_from_bookinfos(None, [{"id": 65}])
    assert result == ["gokyo-shumyo"]


def test_bookinfos_unknown_book_skipped():
    """Unknown book IDs are silently skipped, not added to YL."""
    result = enrich_collections_from_bookinfos(None, [{"book_id": 999999}])
    assert result is None


# book slug resolution

def test_resolve_known_book_slug():
    """Known book IDs resolve to curated slugs."""
    assert resolve_book_slug(65) == "gokyo-shumyo"


def test_resolve_known_book_slug_string():
    """String book IDs work too."""
    assert resolve_book_slug("197") == "go-seigen-tsumego"


def test_resolve_unknown_book_slug_fallback():
    """Unknown book IDs return None (no fallback pattern)."""
    assert resolve_book_slug(999999) is None


def test_bookinfos_known_book_resolves_slug():
    """A known book ID produces a curated slug."""
    result = enrich_collections_from_bookinfos(None, [{"book_id": 65}])
    assert result == ["gokyo-shumyo"]


def test_bookinfos_multiple_known_books():
    """Multiple known books each get their curated slug."""
    result = enrich_collections_from_bookinfos(
        None, [{"book_id": 2}, {"book_id": 190}],
    )
    assert result == ["tenryuzu", "kuwabara-hatsuyoron"]
