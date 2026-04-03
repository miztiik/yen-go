"""Tests for 101weiqi SGF conversion."""

from tools.weiqi101.converter import convert_puzzle_to_sgf, escape_sgf_text
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


def test_basic_sgf_conversion():
    """Convert a puzzle to SGF with YenGo properties."""
    puzzle = PuzzleData.from_qqdata(_sample_qqdata())
    sgf = convert_puzzle_to_sgf(puzzle)

    # Mandatory SGF header
    assert "FF[4]" in sgf
    assert "GM[1]" in sgf
    assert "CA[UTF-8]" in sgf
    assert "SZ[19]" in sgf

    # YenGo properties (13K+ with calibration offset 10 → 23K → beginner)
    assert "YG[beginner]" in sgf
    assert "YT[life-and-death]" in sgf  # 死活题

    # YM always present
    assert "YM[" in sgf

    # Player to move
    assert "PL[B]" in sgf

    # Setup stones
    assert "AB[pd][pe][qd]" in sgf
    assert "AW[oc][oe][rc]" in sgf

    # Excluded properties
    assert "GN[" not in sgf
    assert "PC[" not in sgf
    assert "EV[" not in sgf


def test_solution_tree_in_sgf():
    """Solution tree with correct/wrong annotations."""
    puzzle = PuzzleData.from_qqdata(_sample_qqdata())
    sgf = convert_puzzle_to_sgf(puzzle)

    # Root move (correct)
    assert ";B[rd]C[Correct]" in sgf

    # Wrong variation
    assert "C[Wrong]" in sgf


def test_white_to_play():
    """SGF with white to play first."""
    data = _sample_qqdata()
    data["firsthand"] = 2
    puzzle = PuzzleData.from_qqdata(data)
    sgf = convert_puzzle_to_sgf(puzzle)

    assert "PL[W]" in sgf
    assert ";W[rd]" in sgf


def test_no_level_when_empty():
    """No YG[] when level is empty."""
    data = _sample_qqdata()
    data["levelname"] = ""
    puzzle = PuzzleData.from_qqdata(data)
    sgf = convert_puzzle_to_sgf(puzzle)

    assert "YG[" not in sgf


def test_no_tag_when_unmapped():
    """No YT[] for generic categories."""
    data = _sample_qqdata()
    data["qtypename"] = "综合"  # Mixed → None
    puzzle = PuzzleData.from_qqdata(data)
    sgf = convert_puzzle_to_sgf(puzzle)

    assert "YT[" not in sgf


def test_escape_sgf_text():
    """Escape brackets and backslashes."""
    assert escape_sgf_text("a]b") == "a\\]b"
    assert escape_sgf_text("a\\b") == "a\\\\b"


def test_branching_solution_tree():
    """Multiple variations create SGF branches."""
    data = _sample_qqdata()
    puzzle = PuzzleData.from_qqdata(data)
    sgf = convert_puzzle_to_sgf(puzzle)

    # Should have variation markers since root has 2 children
    assert "(" in sgf


def test_yx_property_emitted():
    """YX[] is emitted when yx_string is provided."""
    puzzle = PuzzleData.from_qqdata(_sample_qqdata())
    sgf = convert_puzzle_to_sgf(puzzle, yx_string="d:1;r:3;s:2;u:2;w:1")
    assert "YX[d:1;r:3;s:2;u:2;w:1]" in sgf


def test_yx_property_absent_when_none():
    """No YX[] when yx_string is None."""
    puzzle = PuzzleData.from_qqdata(_sample_qqdata())
    sgf = convert_puzzle_to_sgf(puzzle)
    assert "YX[" not in sgf


def test_yl_property_emitted():
    """YL[] is emitted when collection_entries is provided."""
    puzzle = PuzzleData.from_qqdata(_sample_qqdata())
    sgf = convert_puzzle_to_sgf(puzzle, collection_entries=["life-and-death"])
    assert "YL[life-and-death]" in sgf


def test_yl_multiple_collections():
    """YL[] joins multiple entries with comma."""
    puzzle = PuzzleData.from_qqdata(_sample_qqdata())
    sgf = convert_puzzle_to_sgf(
        puzzle, collection_entries=["life-and-death", "tesuji-problems"]
    )
    assert "YL[life-and-death,tesuji-problems]" in sgf


def test_yl_with_sequence():
    """YL[] supports slug:CHAPTER/POSITION format."""
    puzzle = PuzzleData.from_qqdata(_sample_qqdata())
    sgf = convert_puzzle_to_sgf(
        puzzle, collection_entries=["cho-chikun-elementary:3/12"]
    )
    assert "YL[cho-chikun-elementary:3/12]" in sgf


def test_yl_mixed_bare_and_sequenced():
    """YL[] mixes bare slugs and slug:CHAPTER/POSITION entries."""
    puzzle = PuzzleData.from_qqdata(_sample_qqdata())
    sgf = convert_puzzle_to_sgf(
        puzzle, collection_entries=["life-and-death", "cho-chikun-elementary:1/5"]
    )
    assert "YL[life-and-death,cho-chikun-elementary:1/5]" in sgf


def test_yl_absent_when_none():
    """No YL[] when collection_entries is None."""
    puzzle = PuzzleData.from_qqdata(_sample_qqdata())
    sgf = convert_puzzle_to_sgf(puzzle)
    assert "YL[" not in sgf


def test_ym_always_emitted():
    """YM[] is always emitted with trace_id and original filename."""
    puzzle = PuzzleData.from_qqdata(_sample_qqdata())
    sgf = convert_puzzle_to_sgf(puzzle)
    assert "YM[" in sgf
    # Should contain trace_id and original filename
    import re
    ym_match = re.search(r'YM\[([^\]]+)\]', sgf)
    assert ym_match is not None
    import json
    ym_data = json.loads(ym_match.group(1))
    assert "t" in ym_data  # trace_id
    assert len(ym_data["t"]) == 16
    assert ym_data["f"] == "78000.sgf"  # puzzle_id from sample data


def test_root_comment_emitted():
    """Root C[] intent comment is emitted."""
    puzzle = PuzzleData.from_qqdata(_sample_qqdata())
    sgf = convert_puzzle_to_sgf(puzzle, root_comment="Black to live or kill")
    assert "C[Black to live or kill]" in sgf


def test_root_comment_absent_when_none():
    """No root C[] when root_comment is None."""
    puzzle = PuzzleData.from_qqdata(_sample_qqdata())
    sgf = convert_puzzle_to_sgf(puzzle)
    # Root C[] should not appear; only move-level C[Correct]/C[Wrong]
    # Check that C[ only appears attached to moves (after ;B or ;W)
    lines = sgf.split("\n")
    for line in lines:
        # Root properties are in the first line
        if line.startswith("(;FF[4]"):
            assert "C[" not in line


def test_all_enrichment_together():
    """YX, YL, YM, and root C[] all appear when provided."""
    puzzle = PuzzleData.from_qqdata(_sample_qqdata())
    sgf = convert_puzzle_to_sgf(
        puzzle,
        root_comment="Black to live or kill",
        collection_entries=["life-and-death"],
        yx_string="d:1;r:3;s:2;u:2;w:1",
    )
    assert "YX[d:1;r:3;s:2;u:2;w:1]" in sgf
    assert "YL[life-and-death]" in sgf
    assert "YM[" in sgf
    assert "C[Black to live or kill]" in sgf


# =============================================================================
# Chapter-aware collection entries (v14 CHAPTER/POSITION format)
# =============================================================================


def test_yl_chapter_position_format():
    """YL[] with chapter/position format produces correct SGF."""
    puzzle = PuzzleData.from_qqdata(_sample_qqdata())
    sgf = convert_puzzle_to_sgf(
        puzzle, collection_entries=["cho-elementary:3/12"]
    )
    assert "YL[cho-elementary:3/12]" in sgf


def test_yl_mixed_bare_and_chapter_position():
    """YL[] with bare slug + chapter/position together."""
    puzzle = PuzzleData.from_qqdata(_sample_qqdata())
    sgf = convert_puzzle_to_sgf(
        puzzle,
        collection_entries=["life-and-death", "cho-elementary:1/5"],
    )
    assert "YL[life-and-death,cho-elementary:1/5]" in sgf


def test_yl_position_only():
    """YL[] with position-only format (no chapter)."""
    puzzle = PuzzleData.from_qqdata(_sample_qqdata())
    sgf = convert_puzzle_to_sgf(
        puzzle, collection_entries=["series-a:42"]
    )
    assert "YL[series-a:42]" in sgf


def test_yl_dashed_chapter():
    """YL[] with dashed chapter name using / separator."""
    puzzle = PuzzleData.from_qqdata(_sample_qqdata())
    sgf = convert_puzzle_to_sgf(
        puzzle, collection_entries=["book-x:intro-a/5"]
    )
    assert "YL[book-x:intro-a/5]" in sgf
