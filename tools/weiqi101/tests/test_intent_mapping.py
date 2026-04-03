"""Tests for local intent mapping."""

from tools.weiqi101._local_intent_mapping import CATEGORY_TO_INTENT, resolve_intent


def test_life_and_death_black():
    result = resolve_intent("死活题", "B")
    assert result == "Black to live or kill"


def test_life_and_death_white():
    result = resolve_intent("死活题", "W")
    assert result == "White to live or kill"


def test_tesuji():
    result = resolve_intent("手筋", "B")
    assert result == "Black to find the tesuji"


def test_joseki():
    result = resolve_intent("定式", "W")
    assert result == "White to find the correct joseki"


def test_capture_race_variants():
    """Both 对杀 and 对杀题 map to capture race."""
    r1 = resolve_intent("对杀", "B")
    r2 = resolve_intent("对杀题", "B")
    assert r1 == r2 == "Black to win the capturing race"


def test_all_categories_mapped():
    """All categories in the mapping produce non-None results."""
    for cat in CATEGORY_TO_INTENT:
        result = resolve_intent(cat, "B")
        assert result is not None, f"Category {cat} returned None"
        assert "Black" in result


def test_unknown_category():
    result = resolve_intent("未知类型", "B")
    assert result is None


def test_empty_category():
    result = resolve_intent("", "B")
    assert result is None


# Additional categories (discovered from /questionlib/ URL paths)

def test_chizi_intent():
    result = resolve_intent("吃子", "B")
    assert result == "Black to capture the stones"


def test_pianzhao_intent():
    result = resolve_intent("骗招", "W")
    assert result == "White to find the trap move"


def test_shizhan_intent():
    result = resolve_intent("实战", "B")
    assert result == "Black to find the best move"


def test_qili_intent():
    result = resolve_intent("棋理", "B")
    assert result == "Black to find the correct move"


def test_mofang_not_mapped():
    """Imitation puzzles need sampling before committing intent."""
    result = resolve_intent("模仿", "B")
    assert result is None
