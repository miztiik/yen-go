"""Tests for 101weiqi puzzle data model parsing."""

from tools.weiqi101.models import PuzzleData


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
