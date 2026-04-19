"""Tests for 101weiqi puzzle data model parsing."""

from tools.weiqi101.models import PuzzleData, decode_content_field, decode_qqdata_fields


def _sample_qqdata():
    """Return a minimal valid qqdata dict."""
    return {
        "publicid": 78000,
        "boardsize": 19,
        "firsthand": 1,
        "levelname": "13K+",
        "qtypename": "死活题",
        "qtype": 1,
        "prepos": [
            ["pd", "pe", "qd"],
            ["oc", "oe", "rc"],
        ],
        "andata": {
            "0": {"pt": "rd", "o": 1, "subs": [1, 2]},
            "1": {"pt": "pe", "f": 1, "subs": []},
            "2": {"pt": "qe", "o": 1, "subs": []},
        },
        "taskresult": {"ok_total": 1000, "fail_total": 500},
        "vote": 4.5,
    }


def test_parse_basic():
    """Parse a standard qqdata dict."""
    data = _sample_qqdata()
    puzzle = PuzzleData.from_qqdata(data)

    assert puzzle.puzzle_id == 78000
    assert puzzle.board_size == 19
    assert puzzle.first_hand == 1
    assert puzzle.player_to_move == "B"
    assert puzzle.level_name == "13K+"
    assert puzzle.type_name == "死活题"
    assert len(puzzle.black_stones) == 3
    assert len(puzzle.white_stones) == 3
    assert len(puzzle.solution_nodes) == 3
    assert puzzle.correct_count == 1000
    assert puzzle.wrong_count == 500
    assert puzzle.total_answers == 1500
    assert puzzle.vote_score == 4.5


def test_player_white():
    """White to play when firsthand=2."""
    data = _sample_qqdata()
    data["firsthand"] = 2
    puzzle = PuzzleData.from_qqdata(data)
    assert puzzle.player_to_move == "W"


def test_blackfirst_fallback():
    """Use blackfirst boolean when firsthand missing."""
    data = _sample_qqdata()
    del data["firsthand"]
    data["blackfirst"] = False
    puzzle = PuzzleData.from_qqdata(data)
    assert puzzle.player_to_move == "W"


def test_psm_prepos_fallback():
    """Fallback to psm.prepos when prepos is empty."""
    data = _sample_qqdata()
    data["prepos"] = [[], []]
    data["psm"] = {
        "prepos": [["aa", "bb"], ["cc"]],
    }
    puzzle = PuzzleData.from_qqdata(data)
    assert puzzle.black_stones == ["aa", "bb"]
    assert puzzle.white_stones == ["cc"]


def test_solution_node_parsing():
    """Solution nodes preserve correct/failure flags."""
    data = _sample_qqdata()
    puzzle = PuzzleData.from_qqdata(data)

    assert 0 in puzzle.solution_nodes
    root = puzzle.solution_nodes[0]
    assert root.coordinate == "rd"
    assert root.is_correct is True
    assert root.children == [1, 2]

    wrong_node = puzzle.solution_nodes[1]
    assert wrong_node.is_failure is True


def test_empty_taskresult():
    """Handle missing or non-dict taskresult."""
    data = _sample_qqdata()
    data["taskresult"] = None
    puzzle = PuzzleData.from_qqdata(data)
    assert puzzle.correct_count == 0
    assert puzzle.wrong_count == 0


def test_missing_prepos():
    """Handle missing prepos gracefully."""
    data = _sample_qqdata()
    del data["prepos"]
    puzzle = PuzzleData.from_qqdata(data)
    assert puzzle.black_stones == []
    assert puzzle.white_stones == []


# -- content field decoder tests -------------------------------------------
# Mirrors the site's JS decode chain: test123 → test202
# Key derivation: "101" + str(ru+1) * 3

# encode [["pd","qd","rd"],["pc","qc","rc"]] with key "101222" (ru=1)
_CONTENT_RU1 = "amsTQlYQHRATQ1YQHRATQFYQbBwRaRBCUhIdEhBDUhIdEhBAUhJsbw=="
# encode same payload with key "101333" (ru=2)
_CONTENT_RU2 = "amsTQ1cRHRATQlcRHRATQVcRbBwRaBFDUhIdExFCUhIdExFBUhJsbg=="


def test_decode_content_ru1():
    """Decode content field with ru=1 key (101222)."""
    result = decode_content_field(_CONTENT_RU1, ru=1)
    assert result is not None
    black, white = result
    assert black == ["pd", "qd", "rd"]
    assert white == ["pc", "qc", "rc"]


def test_decode_content_ru2():
    """Decode content field with ru=2 key (101333)."""
    result = decode_content_field(_CONTENT_RU2, ru=2)
    assert result is not None
    black, white = result
    assert black == ["pd", "qd", "rd"]
    assert white == ["pc", "qc", "rc"]


def test_decode_content_wrong_ru_fails():
    """Wrong ru produces garbage — decode returns None."""
    # ru=1 encoded data decoded with ru=2 key should fail
    result = decode_content_field(_CONTENT_RU1, ru=2)
    assert result is None


def test_content_encoded_overrides_prepos():
    """Encoded content field takes priority over prepos."""
    data = _sample_qqdata()
    data["content"] = _CONTENT_RU1
    data["ru"] = 1
    data["prepos"] = [["aa"], ["bb"]]
    puzzle = PuzzleData.from_qqdata(data)
    assert puzzle.black_stones == ["pd", "qd", "rd"]
    assert puzzle.white_stones == ["pc", "qc", "rc"]


def test_content_already_decoded_array():
    """Content already decoded to array (browser capture path)."""
    data = _sample_qqdata()
    data["content"] = [["aa", "bb"], ["cc", "dd"]]
    puzzle = PuzzleData.from_qqdata(data)
    assert puzzle.black_stones == ["aa", "bb"]
    assert puzzle.white_stones == ["cc", "dd"]


def test_content_invalid_falls_back_to_prepos():
    """Invalid content string falls back to prepos."""
    data = _sample_qqdata()
    data["content"] = "not-valid-base64!!!"
    data["ru"] = 1
    puzzle = PuzzleData.from_qqdata(data)
    # Falls back to prepos from _sample_qqdata
    assert len(puzzle.black_stones) == 3
    assert len(puzzle.white_stones) == 3


def test_boardsize_lu_fallback():
    """Board size falls back to lu field when boardsize missing."""
    data = _sample_qqdata()
    del data["boardsize"]
    data["lu"] = 13
    puzzle = PuzzleData.from_qqdata(data)
    assert puzzle.board_size == 13


# -- decode_qqdata_fields tests --------------------------------------------


def test_decode_qqdata_fields_all():
    """decode_qqdata_fields decodes all 6 encoded fields."""
    data = {
        "ru": 1,
        "content": _CONTENT_RU1,
        "ok_answers": _CONTENT_RU1,   # reuse same encoded payload
        "fail_answers": _CONTENT_RU1,
        "change_answers": _CONTENT_RU1,
        "clone_pos": _CONTENT_RU1,
        "clone_prepos": _CONTENT_RU1,
    }
    decode_qqdata_fields(data)
    # All fields should now be decoded arrays
    for field in ("content", "ok_answers", "fail_answers",
                  "change_answers", "clone_pos", "clone_prepos"):
        assert isinstance(data[field], list), f"{field} not decoded"
        assert data[field][0] == ["pd", "qd", "rd"]


def test_decode_qqdata_fields_skips_already_decoded():
    """decode_qqdata_fields skips fields that are already decoded."""
    original = [["aa"], ["bb"]]
    data = {
        "ru": 1,
        "content": original,
        "ok_answers": _CONTENT_RU1,
    }
    decode_qqdata_fields(data)
    assert data["content"] is original  # untouched
    assert isinstance(data["ok_answers"], list)  # decoded


def test_decode_qqdata_fields_no_ru():
    """decode_qqdata_fields is a no-op when ru is missing or not 1/2."""
    data = {"content": _CONTENT_RU1}
    decode_qqdata_fields(data)
    assert data["content"] == _CONTENT_RU1  # still encoded string


def test_from_qqdata_does_not_mutate_input():
    """from_qqdata does not modify the caller's dict."""
    data = _sample_qqdata()
    data["content"] = _CONTENT_RU1
    data["ru"] = 1
    original_content = data["content"]
    PuzzleData.from_qqdata(data)
    assert data["content"] == original_content  # unchanged


# -- andata comment (tip vs c) tests ---------------------------------------


def test_andata_tip_preferred_over_c():
    """tip field is preferred over c for solution node comment."""
    data = _sample_qqdata()
    data["andata"]["0"]["tip"] = "好棋！"
    data["andata"]["0"]["c"] = 0
    puzzle = PuzzleData.from_qqdata(data)
    assert puzzle.solution_nodes[0].comment == "好棋！"


def test_andata_numeric_c_ignored():
    """Numeric c field produces empty comment (not '0')."""
    data = _sample_qqdata()
    data["andata"]["0"]["c"] = 0
    puzzle = PuzzleData.from_qqdata(data)
    assert puzzle.solution_nodes[0].comment == ""


def test_andata_string_c_used_when_no_tip():
    """String c field used as comment when tip is absent."""
    data = _sample_qqdata()
    data["andata"]["0"]["c"] = "此处是急所"
    puzzle = PuzzleData.from_qqdata(data)
    assert puzzle.solution_nodes[0].comment == "此处是急所"


def test_andata_tip_empty_falls_back_to_c():
    """Empty tip falls back to string c."""
    data = _sample_qqdata()
    data["andata"]["0"]["tip"] = ""
    data["andata"]["0"]["c"] = "试试看"
    puzzle = PuzzleData.from_qqdata(data)
    assert puzzle.solution_nodes[0].comment == "试试看"
