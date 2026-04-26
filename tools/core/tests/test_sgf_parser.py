"""Tests for tools.core.sgf_parser.

Covers:
- Simple SGF parsing (no variations)
- Puzzle 6405 SGF (12 paths, max depth 15, RIGHT marker)
- Escaped brackets in property values
- Nested variations
- Empty / malformed SGF handling
- Setup-only SGF (no moves → depth 0)
- YenGo custom property parsing
- Root comment extraction
- Board size and initial stones
- read_sgf_file encoding fallback (UTF-8 → latin-1)
"""

import pytest

from tools.core.sgf_parser import (
    SGFParseError,
    escape_sgf_value,
    parse_sgf,
    read_sgf_file,
    unescape_sgf_value,
)
from tools.core.sgf_types import Color, Point

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

# Simple puzzle: B to play, one correct line of 2 moves
SIMPLE_SGF = "(;SZ[19]PL[B]AB[cd][de]AW[ce][df](;B[cf]C[Correct!])(;B[eg]C[Wrong]))"

# Puzzle 6405 from GoProblems — 9-dan net tesuji, 12 paths, correct path = 15 moves
PUZZLE_6405_SGF = (
    "(;AB[oc]AB[od]AB[oe]AB[pe]AB[pf]AB[qc]AB[qe]AB[qg]AB[qh]AB[qi]AB[qk]"
    "AB[rc]AB[rg]AB[ri]AB[rj]AW[nf]AW[pd]AW[pg]AW[ph]AW[pi]AW[pj]AW[qd]"
    "AW[qf]AW[qj]AW[rd]AW[re]AW[rf]AW[rk]AW[sh]SZ[19]PL[W]GM[1]FF[4]"
    "AP[Hibiscus:2.1]ST[3]"
    "(;W[sk]MN[2];B[sg]"
    "(;W[sj];B[rl];W[ql];B[pk]"
    "(;W[rm];B[pc];W[si];B[sd]"
    "(;W[ok];B[pl]"
    "(;W[sl];B[se]"
    "(;W[om]C[White captures 3 stones now. And if black doesn't play Q8 "
    "the capture is sente for white.RIGHT])"
    "(;W[pm]C[Black get's a ladder block this way. Playing at A would "
    "have captured Black unconditionally.]LB[pm:16]LB[om:A]))"
    "(;W[qm];B[ol]))"
    "(;W[sl];B[se]"
    "(;W[ok]C[Close, but a change in move order would give an even better result.])"
    "(;W[ol]C[Close, but a slight change would give an even better result.])))"
    "(;W[pl];B[ok];W[rm];B[pc];W[si];B[sd]))"
    "(;W[sf];B[pc])"
    "(;W[ql];B[pc]C[White has a better way of playing.]))"
    "(;W[ql];B[sg]C[White has a better way of playing])"
    "(;W[rl];B[sg]C[White has a better way of playing.])"
    "(;W[sj];B[rl];W[sk];B[sl];W[si];B[sg])"
    "(;W[sg];B[rl]C[White has a better way of playing]))"
)

# SGF with YenGo custom properties
YENGO_SGF = (
    "(;SZ[19]PL[B]FF[4]GM[1]"
    "YV[10]YG[beginner]YT[life-and-death,ko]"
    "YH[Focus on corner|Ladder pattern|First move at C5]"
    "YQ[q:3;rc:2;hc:1]YX[d:5;r:13;s:24;u:1]"
    "YS[sanderland]YL[net-problems,tesuji-training]"
    "YC[TL]YK[simple]YO[strict]YR[cd,de]"
    "YI[20260209-8a998bf0]"
    "AB[cd][de]AW[ce][df]"
    "(;B[cf]C[Correct!]))"
)

# SGF with escaped brackets in comments
ESCAPED_SGF = (
    r"(;SZ[19]PL[B]AB[cd]AW[ce]"
    r"(;B[cf]C[Avoid \] here and use \\ properly]))"
)


# ---------------------------------------------------------------------------
# Test: parse_sgf basics
# ---------------------------------------------------------------------------


class TestParseBasics:
    """Basic parsing functionality."""

    def test_simple_sgf(self):
        tree = parse_sgf(SIMPLE_SGF)
        assert tree.board_size == 19
        assert tree.player_to_move == Color.BLACK
        assert len(tree.black_stones) == 2
        assert len(tree.white_stones) == 2
        assert tree.has_solution is True

    def test_board_size(self):
        tree = parse_sgf("(;SZ[9]PL[B](;B[cd]))")
        assert tree.board_size == 9

    def test_default_board_size(self):
        tree = parse_sgf("(;PL[B](;B[cd]))")
        assert tree.board_size == 19

    def test_player_to_move_white(self):
        tree = parse_sgf("(;SZ[19]PL[W](;W[cd]))")
        assert tree.player_to_move == Color.WHITE

    def test_player_to_move_black_default(self):
        tree = parse_sgf("(;SZ[19](;B[cd]))")
        assert tree.player_to_move is None

    def test_initial_stones(self):
        tree = parse_sgf("(;SZ[19]AB[aa][bb][cc]AW[dd][ee](;B[ff]))")
        assert len(tree.black_stones) == 3
        assert len(tree.white_stones) == 2
        assert Point(0, 0) in tree.black_stones
        assert Point(1, 1) in tree.black_stones
        assert Point(3, 3) in tree.white_stones

    def test_metadata_extraction(self):
        tree = parse_sgf('(;SZ[19]GN[Test]AP[MyApp:1.0](;B[cd]))')
        assert tree.metadata.get("GN") == "Test"
        assert tree.metadata.get("AP") == "MyApp:1.0"

    def test_root_comment(self):
        tree = parse_sgf("(;SZ[19]C[This is the problem](;B[cd]))")
        assert tree.root_comment == "This is the problem"

    def test_get_first_move(self):
        tree = parse_sgf(SIMPLE_SGF)
        first = tree.get_first_move()
        assert first is not None
        color, point = first
        assert color == Color.BLACK
        assert point == Point.from_sgf("cf")


# ---------------------------------------------------------------------------
# Test: variations and tree structure
# ---------------------------------------------------------------------------


class TestVariations:
    """Variation / tree structure parsing."""

    def test_single_variation(self):
        tree = parse_sgf("(;SZ[19]PL[B];B[cd];W[ef])")
        root = tree.solution_tree
        assert len(root.children) == 1
        assert root.children[0].color == Color.BLACK
        assert len(root.children[0].children) == 1
        assert root.children[0].children[0].color == Color.WHITE

    def test_two_variations(self):
        tree = parse_sgf(SIMPLE_SGF)
        root = tree.solution_tree
        assert len(root.children) == 2
        assert root.children[0].color == Color.BLACK
        assert root.children[1].color == Color.BLACK

    def test_nested_variations(self):
        sgf = "(;SZ[19]PL[B](;B[cd](;W[ef])(;W[gh]))(;B[ij]))"
        tree = parse_sgf(sgf)
        root = tree.solution_tree
        # Root has 2 first-level branches
        assert len(root.children) == 2
        # First branch (B[cd]) has 2 sub-variations
        first = root.children[0]
        assert first.move == Point.from_sgf("cd")
        assert len(first.children) == 2
        assert first.children[0].move == Point.from_sgf("ef")
        assert first.children[1].move == Point.from_sgf("gh")

    def test_deep_single_line(self):
        sgf = "(;SZ[19]PL[B];B[aa];W[bb];B[cc];W[dd];B[ee])"
        tree = parse_sgf(sgf)
        # Walk the single line
        node = tree.solution_tree
        depth = 0
        while node.children:
            node = node.children[0]
            depth += 1
        assert depth == 5

    def test_setup_only_no_moves(self):
        tree = parse_sgf("(;SZ[19]AB[cd]AW[de])")
        assert tree.has_solution is False
        assert len(tree.solution_tree.children) == 0


# ---------------------------------------------------------------------------
# Test: puzzle 6405
# ---------------------------------------------------------------------------


class TestPuzzle6405:
    """Full test of puzzle 6405 — the puzzle that exposed the depth bug."""

    def test_parse_succeeds(self):
        tree = parse_sgf(PUZZLE_6405_SGF)
        assert tree.board_size == 19
        assert tree.player_to_move == Color.WHITE

    def test_initial_stones_count(self):
        tree = parse_sgf(PUZZLE_6405_SGF)
        assert len(tree.black_stones) == 15
        assert len(tree.white_stones) == 14

    def test_first_level_variations(self):
        """Root should have 5 first-level branches (first moves)."""
        tree = parse_sgf(PUZZLE_6405_SGF)
        root = tree.solution_tree
        # W[sk], W[ql], W[rl], W[sj], W[sg]
        assert len(root.children) == 5

    def test_correct_path_has_right_marker(self):
        """The correct path ends with a comment containing 'RIGHT'."""
        tree = parse_sgf(PUZZLE_6405_SGF)
        # Walk the correct path: W[sk] -> B[sg] -> W[sj] -> ... -> W[om]
        from tools.core.sgf_analysis import get_all_paths

        paths = get_all_paths(tree.solution_tree)
        correct_paths = [
            p
            for p in paths
            if any("RIGHT" in n.comment for n in p if n.comment)
        ]
        assert len(correct_paths) == 1
        # The correct path should have 15 actual moves (+ root placeholder)
        correct_moves = [n for n in correct_paths[0] if n.move is not None]
        assert len(correct_moves) == 15

    def test_total_paths(self):
        """Puzzle 6405 has 12 leaf paths total."""
        from tools.core.sgf_analysis import get_all_paths

        tree = parse_sgf(PUZZLE_6405_SGF)
        paths = get_all_paths(tree.solution_tree)
        assert len(paths) == 12


# ---------------------------------------------------------------------------
# Test: correctness inference
# ---------------------------------------------------------------------------


class TestCorrectness:
    """Correctness marking from comments and SGF markers."""

    def test_correct_from_comment(self):
        tree = parse_sgf("(;SZ[19](;B[cd]C[Correct!]))")
        node = tree.solution_tree.children[0]
        assert node.is_correct is True

    def test_wrong_from_comment(self):
        tree = parse_sgf("(;SZ[19](;B[cd]C[Wrong move]))")
        node = tree.solution_tree.children[0]
        assert node.is_correct is False

    def test_right_prefix(self):
        tree = parse_sgf(
            "(;SZ[19](;B[cd]C[RIGHT - good move]))"
        )
        node = tree.solution_tree.children[0]
        assert node.is_correct is True

    def test_incorrect_prefix(self):
        tree = parse_sgf(
            "(;SZ[19](;B[cd]C[Incorrect]))"
        )
        node = tree.solution_tree.children[0]
        assert node.is_correct is False

    def test_plus_marker(self):
        tree = parse_sgf("(;SZ[19](;B[cd]C[+]))")
        node = tree.solution_tree.children[0]
        assert node.is_correct is True

    def test_no_comment_defaults_correct(self):
        tree = parse_sgf("(;SZ[19](;B[cd]))")
        node = tree.solution_tree.children[0]
        assert node.is_correct is True

    def test_ambiguous_comment_defaults_correct(self):
        tree = parse_sgf("(;SZ[19](;B[cd]C[Good try]))")
        node = tree.solution_tree.children[0]
        assert node.is_correct is True  # No signal → default

    def test_sgf_marker_bm(self):
        tree = parse_sgf("(;SZ[19](;B[cd]BM[1]))")
        node = tree.solution_tree.children[0]
        assert node.is_correct is False

    def test_sgf_marker_te(self):
        tree = parse_sgf("(;SZ[19](;B[cd]TE[1]))")
        node = tree.solution_tree.children[0]
        assert node.is_correct is True


# ---------------------------------------------------------------------------
# Test: escaped characters
# ---------------------------------------------------------------------------


class TestEscaping:
    """Escaped bracket handling in SGF values."""

    def test_escaped_bracket_in_comment(self):
        tree = parse_sgf(ESCAPED_SGF)
        node = tree.solution_tree.children[0]
        assert "]" in node.comment
        assert "\\" in node.comment

    def test_escape_sgf_value(self):
        assert escape_sgf_value("test]value") == "test\\]value"
        assert escape_sgf_value("back\\slash") == "back\\\\slash"
        assert escape_sgf_value("") == ""
        assert escape_sgf_value("no special") == "no special"

    def test_unescape_sgf_value(self):
        assert unescape_sgf_value("test\\]value") == "test]value"
        assert unescape_sgf_value("back\\\\slash") == "back\\slash"
        assert unescape_sgf_value("") == ""


# ---------------------------------------------------------------------------
# Test: YenGo custom properties
# ---------------------------------------------------------------------------


class TestYenGoProperties:
    """YenGo custom property parsing."""

    def test_full_yengo_properties(self):
        tree = parse_sgf(YENGO_SGF)
        yp = tree.yengo_props

        assert yp.version == 10
        assert yp.level_slug == "beginner"
        assert yp.level == 2  # beginner -> 2
        assert yp.tags == ["life-and-death", "ko"]
        assert yp.hint_texts == [
            "Focus on corner",
            "Ladder pattern",
            "First move at C5",
        ]
        assert yp.quality == "q:3;rc:2;hc:1"
        assert yp.complexity == "d:5;r:13;s:24;u:1"
        assert yp.source == "sanderland"
        assert yp.collections == ["net-problems", "tesuji-training"]
        assert yp.corner == "TL"
        assert yp.ko_context == "simple"
        assert yp.move_order == "strict"
        assert yp.refutation_count == "cd,de"
        assert yp.run_id == "20260209-8a998bf0"

    def test_no_yengo_properties(self):
        tree = parse_sgf("(;SZ[19](;B[cd]))")
        yp = tree.yengo_props
        assert yp.version is None
        assert yp.level is None
        assert yp.tags == []
        assert yp.collections == []


# ---------------------------------------------------------------------------
# Test: error handling
# ---------------------------------------------------------------------------


class TestErrorHandling:
    """Invalid SGF handling."""

    def test_empty_content(self):
        with pytest.raises(SGFParseError, match="Empty SGF"):
            parse_sgf("")

    def test_whitespace_only(self):
        with pytest.raises(SGFParseError, match="Empty SGF"):
            parse_sgf("   \n\t  ")

    def test_no_opening_paren(self):
        with pytest.raises(SGFParseError, match="must start with"):
            parse_sgf(";SZ[19]")

    def test_malformed_recoverable(self):
        """Parser should handle minor malformations gracefully."""
        # Missing closing paren — parser reads what it can
        tree = parse_sgf("(;SZ[19]PL[B](;B[cd])")
        assert tree.board_size == 19


# ---------------------------------------------------------------------------
# Test: read_sgf_file encoding fallback
# ---------------------------------------------------------------------------


class TestReadSgfFile:
    """Encoding fallback: UTF-8 → latin-1."""

    def test_utf8_file(self, tmp_path):
        """Pure UTF-8 file is read as utf-8."""
        sgf = "(;SZ[19]PL[B]AB[cd]AW[ef](;B[gh]))"
        p = tmp_path / "test.sgf"
        p.write_text(sgf, encoding="utf-8")
        text, enc = read_sgf_file(p)
        assert enc == "utf-8"
        assert text == sgf

    def test_utf8_with_cjk(self, tmp_path):
        """UTF-8 file with CJK comments is read as utf-8."""
        sgf = "(;SZ[19]PL[B]C[\u6b63\u89e3]AB[cd]AW[ef](;B[gh]))"
        p = tmp_path / "test.sgf"
        p.write_text(sgf, encoding="utf-8")
        text, enc = read_sgf_file(p)
        assert enc == "utf-8"
        assert "\u6b63\u89e3" in text

    def test_euc_kr_falls_back_to_latin1(self, tmp_path):
        """EUC-KR encoded file falls back to latin-1, preserving SGF structure."""
        # Korean text "\uc815\ud574" (correct answer) in EUC-KR = bytes b'\xc1\xa4\xc7\xd8'
        sgf_text = "(;SZ[19]PL[B]C[\uc815\ud574]AB[cd]AW[ef](;B[gh]))"
        p = tmp_path / "test.sgf"
        p.write_bytes(sgf_text.encode("euc-kr"))
        text, enc = read_sgf_file(p)
        assert enc == "latin-1"
        # SGF structure is preserved — can still parse positions
        assert "AB[cd]" in text
        assert "AW[ef]" in text
        assert ";B[gh]" in text

    def test_latin1_result_is_parseable(self, tmp_path):
        """SGF decoded via latin-1 fallback still parses correctly."""
        # Build a real EUC-KR SGF similar to kisvadim-goproblems files
        sgf_bytes = (
            b"(;GM[1]AB[br][bq][cp]AW[aq][bp][cq]"
            b"C[1-1]AP[StoneBase:SGFParser.2.8]SZ[19]"
            b"EV[\xc0\xcc\xc3\xa2\xc8\xa3 1-60]HA[0]MULTIGOGM[1]"
            b";B[ds];W[dr];B[fr])"
        )
        p = tmp_path / "test.sgf"
        p.write_bytes(sgf_bytes)
        text, enc = read_sgf_file(p)
        assert enc == "latin-1"
        tree = parse_sgf(text)
        assert tree.board_size == 19
        assert len(tree.black_stones) == 3
        assert len(tree.white_stones) == 3
        assert tree.has_solution is True

    def test_pure_ascii_reads_as_utf8(self, tmp_path):
        """Pure ASCII SGF is decoded as utf-8 (not latin-1)."""
        sgf = "(;SZ[19]AB[cd]AW[ef])"
        p = tmp_path / "test.sgf"
        p.write_bytes(sgf.encode("ascii"))
        text, enc = read_sgf_file(p)
        assert enc == "utf-8"  # ASCII is valid UTF-8
