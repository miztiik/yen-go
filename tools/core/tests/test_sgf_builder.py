"""Tests for tools.core.sgf_builder.

Covers:
- Build simple SGF from scratch
- Round-trip: parse -> from_tree -> build -> parse (properties preserved)
- All YenGo properties serialized correctly
- Solution tree with variations
- publish_sgf shortcut
- Validation errors (bad board size, bad level, bad run_id)
"""

import pytest

from tools.core.sgf_builder import SGFBuilder, SGFBuildError, publish_sgf
from tools.core.sgf_parser import parse_sgf
from tools.core.sgf_types import Color, Point

# ---------------------------------------------------------------------------
# Test: build from scratch
# ---------------------------------------------------------------------------


class TestBuildFromScratch:
    """Building SGF strings from scratch."""

    def test_minimal_sgf(self):
        builder = SGFBuilder(board_size=19)
        sgf = builder.build()
        assert sgf.startswith("(;")
        assert sgf.endswith(")")
        assert "SZ[19]" in sgf
        assert "FF[4]" in sgf
        assert "GM[1]" in sgf

    def test_with_stones(self):
        builder = SGFBuilder(board_size=19)
        builder.add_black_stone(Point(2, 3))
        builder.add_white_stone(Point(3, 4))
        sgf = builder.build()
        assert "AB[cd]" in sgf
        assert "AW[de]" in sgf

    def test_multiple_stones(self):
        builder = SGFBuilder(board_size=19)
        builder.add_black_stones([Point(0, 0), Point(1, 1)])
        builder.add_white_stones([Point(2, 2), Point(3, 3)])
        sgf = builder.build()
        assert "AB[aa][bb]" in sgf
        assert "AW[cc][dd]" in sgf

    def test_player_to_move(self):
        builder = SGFBuilder(board_size=19)
        builder.set_player_to_move(Color.WHITE)
        sgf = builder.build()
        assert "PL[W]" in sgf

    def test_with_solution_move(self):
        builder = SGFBuilder(board_size=19)
        builder.set_player_to_move(Color.BLACK)
        builder.add_solution_move(Color.BLACK, Point(2, 3), "Correct!")
        sgf = builder.build()
        assert ";B[cd]C[Correct!]" in sgf

    def test_with_variations(self):
        builder = SGFBuilder(board_size=19)
        builder.add_solution_move(Color.BLACK, Point(2, 3), "Correct!", True)
        builder.add_variation()
        builder.add_solution_move(Color.BLACK, Point(4, 5), "Wrong", False)
        sgf = builder.build()
        assert "(;B[cd]C[Correct!])" in sgf
        assert "(;B[ef]C[Wrong]BM[1])" in sgf

    def test_board_size_9(self):
        builder = SGFBuilder(board_size=9)
        sgf = builder.build()
        assert "SZ[9]" in sgf

    def test_invalid_board_size(self):
        with pytest.raises(SGFBuildError, match="Invalid board size"):
            SGFBuilder(board_size=4)
        with pytest.raises(SGFBuildError, match="Invalid board size"):
            SGFBuilder(board_size=20)

    def test_root_comment(self):
        builder = SGFBuilder(board_size=19)
        builder.set_comment("Problem description")
        sgf = builder.build()
        assert "C[Problem description]" in sgf


# ---------------------------------------------------------------------------
# Test: YenGo properties
# ---------------------------------------------------------------------------


class TestYenGoProperties:
    """YenGo custom properties in built SGF."""

    def test_level_slug(self):
        builder = SGFBuilder()
        builder.set_level_slug("beginner")
        sgf = builder.build()
        assert "YG[beginner]" in sgf

    def test_level_slug_with_sublevel(self):
        builder = SGFBuilder()
        builder.set_level_slug("beginner", sublevel=2)
        sgf = builder.build()
        assert "YG[beginner:2]" in sgf

    def test_invalid_level_slug(self):
        builder = SGFBuilder()
        with pytest.raises(SGFBuildError, match="Invalid level slug"):
            builder.set_level_slug("grandmaster")

    def test_version(self):
        builder = SGFBuilder()
        builder.set_version(10)
        sgf = builder.build()
        assert "YV[10]" in sgf

    def test_tags(self):
        builder = SGFBuilder()
        builder.add_tags(["ko", "life-and-death", "tesuji"])
        sgf = builder.build()
        assert "YT[ko,life-and-death,tesuji]" in sgf

    def test_tags_deduplicated_sorted(self):
        builder = SGFBuilder()
        builder.add_tag("ko")
        builder.add_tag("tesuji")
        builder.add_tag("ko")  # duplicate
        sgf = builder.build()
        assert "YT[ko,tesuji]" in sgf

    def test_quality(self):
        builder = SGFBuilder()
        builder.set_quality("q:3;rc:2;hc:1")
        sgf = builder.build()
        assert "YQ[q:3;rc:2;hc:1]" in sgf

    def test_complexity(self):
        builder = SGFBuilder()
        builder.set_complexity("d:5;r:13;s:24;u:1")
        sgf = builder.build()
        assert "YX[d:5;r:13;s:24;u:1]" in sgf

    def test_source(self):
        builder = SGFBuilder()
        builder.set_source("sanderland")
        sgf = builder.build()
        assert "YS[sanderland]" in sgf

    def test_collections(self):
        builder = SGFBuilder()
        builder.add_collection("net-problems")
        builder.add_collection("tesuji-training")
        sgf = builder.build()
        assert "YL[net-problems,tesuji-training]" in sgf

    def test_set_collections_replaces(self):
        builder = SGFBuilder()
        builder.add_collection("old-collection")
        builder.set_collections(["new-a", "new-b"])
        sgf = builder.build()
        assert "old-collection" not in sgf
        assert "YL[new-a,new-b]" in sgf

    def test_hints(self):
        builder = SGFBuilder()
        builder.add_hints(["Focus on corner", "Ladder pattern"])
        sgf = builder.build()
        assert "YH[Focus on corner|Ladder pattern]" in sgf

    def test_corner(self):
        builder = SGFBuilder()
        builder.set_corner("TL")
        sgf = builder.build()
        assert "YC[TL]" in sgf

    def test_ko_context(self):
        builder = SGFBuilder()
        builder.set_ko_context("simple")
        sgf = builder.build()
        assert "YK[simple]" in sgf

    def test_move_order(self):
        builder = SGFBuilder()
        builder.set_move_order("strict")
        sgf = builder.build()
        assert "YO[strict]" in sgf

    def test_refutation_count(self):
        builder = SGFBuilder()
        builder.set_refutation_count("cd,de,ef")
        sgf = builder.build()
        assert "YR[cd,de,ef]" in sgf

    def test_run_id(self):
        builder = SGFBuilder()
        builder.set_run_id("20260209-8a998bf0")
        sgf = builder.build()
        assert "YI[20260209-8a998bf0]" in sgf

    def test_invalid_run_id(self):
        builder = SGFBuilder()
        with pytest.raises(SGFBuildError, match="YYYYMMDD"):
            builder.set_run_id("bad-format")

    def test_game_name(self):
        builder = SGFBuilder()
        builder.set_game_name("YENGO-abcdef1234567890")
        sgf = builder.build()
        assert "GN[YENGO-abcdef1234567890]" in sgf

    def test_yengo_game_name(self):
        builder = SGFBuilder()
        builder.set_yengo_game_name("abcdef1234567890")
        sgf = builder.build()
        assert "GN[YENGO-abcdef1234567890]" in sgf

    def test_invalid_yengo_game_name(self):
        builder = SGFBuilder()
        with pytest.raises(SGFBuildError, match="16 hex"):
            builder.set_yengo_game_name("short")


# ---------------------------------------------------------------------------
# Test: round-trip
# ---------------------------------------------------------------------------


class TestRoundTrip:
    """Parse -> from_tree -> build -> parse preserves data."""

    def test_round_trip_simple(self):
        original = "(;SZ[19]PL[B]AB[cd][de]AW[ce][df](;B[cf]C[Correct!])(;B[eg]C[Wrong]))"
        tree1 = parse_sgf(original)
        rebuilt = SGFBuilder.from_tree(tree1).build()
        tree2 = parse_sgf(rebuilt)

        assert tree2.board_size == tree1.board_size
        assert tree2.player_to_move == tree1.player_to_move
        assert len(tree2.black_stones) == len(tree1.black_stones)
        assert len(tree2.white_stones) == len(tree1.white_stones)
        assert tree2.has_solution == tree1.has_solution
        assert len(tree2.solution_tree.children) == len(
            tree1.solution_tree.children
        )

    def test_round_trip_yengo_properties(self):
        original = (
            "(;SZ[19]PL[B]FF[4]GM[1]"
            "YV[10]YG[beginner]YT[ko,life-and-death]"
            "YQ[q:3;rc:2;hc:1]YS[sanderland]"
            "AB[cd]AW[ce](;B[cf]C[Correct!]))"
        )
        tree1 = parse_sgf(original)
        rebuilt = SGFBuilder.from_tree(tree1).build()
        tree2 = parse_sgf(rebuilt)

        assert tree2.yengo_props.version == 10
        assert tree2.yengo_props.level_slug == "beginner"
        assert tree2.yengo_props.tags == ["ko", "life-and-death"]
        assert tree2.yengo_props.quality == "q:3;rc:2;hc:1"
        assert tree2.yengo_props.source == "sanderland"

    def test_publish_sgf_shortcut(self):
        original = "(;SZ[19]PL[B]AB[cd]AW[ce](;B[cf]))"
        tree = parse_sgf(original)
        rebuilt = publish_sgf(tree)
        tree2 = parse_sgf(rebuilt)
        assert tree2.board_size == 19
        assert tree2.has_solution is True

    def test_round_trip_preserves_lb_labels(self):
        """LB[] label properties on move nodes must survive round-trip."""
        original = (
            "(;SZ[19]PL[W]AB[cd]AW[de]"
            "(;W[om]C[Correct!]LB[pm:16]LB[om:A]))"
        )
        tree = parse_sgf(original)
        rebuilt = SGFBuilder.from_tree(tree).build()
        # LB properties must be present in rebuilt SGF
        assert "LB[pm:16]" in rebuilt
        assert "LB[om:A]" in rebuilt

    def test_round_trip_preserves_mn_move_number(self):
        """MN[] move number override must survive round-trip."""
        original = "(;SZ[19]PL[W](;W[sk]MN[2];B[sg]))"
        tree = parse_sgf(original)
        rebuilt = SGFBuilder.from_tree(tree).build()
        assert "MN[2]" in rebuilt

    def test_round_trip_preserves_markup_properties(self):
        """TR, SQ, CR, MA markup properties must survive round-trip."""
        original = "(;SZ[19]PL[B](;B[cd]TR[ef]SQ[gh]CR[ij]MA[kl]))"
        tree = parse_sgf(original)
        rebuilt = SGFBuilder.from_tree(tree).build()
        assert "TR[ef]" in rebuilt
        assert "SQ[gh]" in rebuilt
        assert "CR[ij]" in rebuilt
        assert "MA[kl]" in rebuilt

    def test_round_trip_puzzle_6405_preserves_all(self):
        """Full puzzle 6405 round-trip preserves LB and MN."""
        from tools.core.tests.test_sgf_parser import PUZZLE_6405_SGF

        tree = parse_sgf(PUZZLE_6405_SGF)
        rebuilt = SGFBuilder.from_tree(tree).build()
        tree2 = parse_sgf(rebuilt)

        # Structure preserved
        assert tree2.board_size == 19
        assert len(tree2.black_stones) == 15
        assert len(tree2.white_stones) == 14
        assert len(tree2.solution_tree.children) == 5

        # Annotations preserved
        assert "MN[2]" in rebuilt
        assert "LB[pm:16]" in rebuilt
        assert "LB[om:A]" in rebuilt

        # Move comments preserved
        assert "RIGHT" in rebuilt
        assert "ladder block" in rebuilt


# ---------------------------------------------------------------------------
# Test: to_tree
# ---------------------------------------------------------------------------


class TestToTree:
    """SGFBuilder.to_tree() conversion."""

    def test_to_tree(self):
        builder = SGFBuilder(board_size=9)
        builder.set_player_to_move(Color.WHITE)
        builder.set_level_slug("novice")
        builder.add_tag("life-and-death")
        builder.add_solution_move(Color.WHITE, Point(2, 3))
        tree = builder.to_tree()

        assert tree.board_size == 9
        assert tree.player_to_move == Color.WHITE
        assert tree.yengo_props.level_slug == "novice"
        assert tree.yengo_props.tags == ["life-and-death"]
        assert tree.has_solution is True
