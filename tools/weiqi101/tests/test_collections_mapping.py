"""Tests for local collections mapping."""

from tools.weiqi101._local_collections_mapping import resolve_collection_slug


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
