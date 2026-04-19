"""Tests for 101weiqi tag mapping."""

from tools.weiqi101.tags import map_tag


def test_life_and_death():
    assert map_tag("死活题") == "life-and-death"


def test_tesuji():
    assert map_tag("手筋") == "tesuji"


def test_fuseki():
    assert map_tag("布局") == "fuseki"


def test_joseki():
    assert map_tag("定式") == "joseki"


def test_endgame():
    assert map_tag("官子") == "endgame"


def test_capture_race():
    assert map_tag("对杀") == "capture-race"


def test_mixed_is_none():
    """Mixed/comprehensive type intentionally unmapped."""
    assert map_tag("综合") is None


def test_middle_game_is_none():
    """Middle game type intentionally unmapped."""
    assert map_tag("中盘") is None


def test_empty_string():
    assert map_tag("") is None


def test_unknown():
    assert map_tag("未知") is None


# Additional categories (discovered from /questionlib/ URL paths)

def test_chizi_is_none():
    """Capture-stones is NOT capture-race; pipeline detects technique."""
    assert map_tag("吃子") is None


def test_pianzhao_maps_to_tesuji():
    """Trick moves map to tesuji (closest available)."""
    assert map_tag("骗招") == "tesuji"


def test_shizhan_is_none():
    """Real game positions are too broad for a single tag."""
    assert map_tag("实战") is None


def test_qili_is_none():
    """Go theory is conceptual, not a technique tag."""
    assert map_tag("棋理") is None


def test_mofang_is_none():
    """Imitation puzzles deferred until sampled."""
    assert map_tag("模仿") is None


# English aliases (from qday sweep, 2015+ daily puzzles)

def test_english_life_and_death():
    assert map_tag("Life & Death") == "life-and-death"


def test_english_fight():
    assert map_tag("Fight") == "capture-race"


def test_english_tesuji():
    assert map_tag("Tesuji") == "tesuji"


def test_english_opening():
    assert map_tag("Opening") == "fuseki"


def test_english_joseki():
    assert map_tag("Joseki") == "joseki"


def test_english_endgame():
    assert map_tag("Endgame") == "endgame"


def test_english_comprehensive_is_none():
    assert map_tag("Comprehensive") is None


def test_english_middle_game_is_none():
    assert map_tag("Middle Game") is None


def test_english_principles_is_none():
    assert map_tag("Principles") is None
