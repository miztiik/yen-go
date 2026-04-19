"""Tests for 101weiqi puzzle validation."""

from tools.weiqi101.models import PuzzleData
from tools.weiqi101.validator import validate_puzzle


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
            ["pd", "pe"],
            ["oc", "oe"],
        ],
        "andata": {
            "0": {"pt": "rd", "o": 1, "subs": []},
        },
        "taskresult": {"ok_total": 100, "fail_total": 50},
        "vote": 4.0,
    }


def test_valid_puzzle():
    """Valid puzzle passes validation."""
    puzzle = PuzzleData.from_qqdata(_sample_qqdata())
    assert validate_puzzle(puzzle) is None


def test_invalid_board_size_too_small():
    data = _sample_qqdata()
    data["boardsize"] = 2
    puzzle = PuzzleData.from_qqdata(data)
    error = validate_puzzle(puzzle)
    assert error is not None
    assert "Board size" in error


def test_invalid_board_size_too_large():
    data = _sample_qqdata()
    data["boardsize"] = 25
    puzzle = PuzzleData.from_qqdata(data)
    error = validate_puzzle(puzzle)
    assert error is not None
    assert "Board size" in error


def test_no_setup_stones():
    data = _sample_qqdata()
    data["prepos"] = [[], []]
    puzzle = PuzzleData.from_qqdata(data)
    error = validate_puzzle(puzzle)
    assert error is not None
    assert "setup stones" in error.lower()


def test_no_solution_tree():
    """Puzzle without solution tree is accepted (position-only)."""
    data = _sample_qqdata()
    data["andata"] = {}
    puzzle = PuzzleData.from_qqdata(data)
    error = validate_puzzle(puzzle)
    assert error is None  # Position-only puzzles are valid


def test_missing_root_node():
    """Puzzle with solution tree but no root node is accepted with warning."""
    data = _sample_qqdata()
    data["andata"] = {"1": {"pt": "pd", "o": 1, "subs": []}}
    puzzle = PuzzleData.from_qqdata(data)
    error = validate_puzzle(puzzle)
    assert error is None  # Warns but does not reject


def test_missing_board_size_inferred():
    """Puzzle with missing board size is inferred from stone coordinates."""
    data = _sample_qqdata()
    data["boardsize"] = None
    puzzle = PuzzleData.from_qqdata(data)
    error = validate_puzzle(puzzle)
    assert error is None
    assert puzzle.board_size is not None  # Should be inferred
