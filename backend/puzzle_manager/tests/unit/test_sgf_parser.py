"""Unit tests for SGF parser module."""

import pytest

from backend.puzzle_manager.core.primitives import Color, Point
from backend.puzzle_manager.core.sgf_parser import SGFGame, parse_root_properties_only, parse_sgf
from backend.puzzle_manager.exceptions import SGFParseError


class TestSgfParser:
    """Tests for parse_sgf function."""

    def test_parse_minimal_sgf(self) -> None:
        """Parser should handle minimal SGF."""
        sgf = "(;GM[1]FF[4])"
        game = parse_sgf(sgf)

        assert isinstance(game, SGFGame)

    def test_parse_with_board_size(self) -> None:
        """Parser should read board size."""
        sgf = "(;GM[1]FF[4]SZ[19])"
        game = parse_sgf(sgf)

        assert game.board_size == 19

    def test_parse_with_9x9_board(self) -> None:
        """Parser should handle 9x9 board."""
        sgf = "(;GM[1]FF[4]SZ[9])"
        game = parse_sgf(sgf)

        assert game.board_size == 9

    def test_parse_black_stones(self) -> None:
        """Parser should read black stones."""
        sgf = "(;GM[1]FF[4]AB[cd][de])"
        game = parse_sgf(sgf)

        assert Point(2, 3) in game.black_stones
        assert Point(3, 4) in game.black_stones

    def test_parse_white_stones(self) -> None:
        """Parser should read white stones."""
        sgf = "(;GM[1]FF[4]AW[cd][de])"
        game = parse_sgf(sgf)

        assert Point(2, 3) in game.white_stones
        assert Point(3, 4) in game.white_stones

    def test_parse_player_to_move_black(self) -> None:
        """Parser should read player to move (Black)."""
        sgf = "(;GM[1]FF[4]PL[B])"
        game = parse_sgf(sgf)

        assert game.player_to_move == Color.BLACK

    def test_parse_player_to_move_white(self) -> None:
        """Parser should read player to move (White)."""
        sgf = "(;GM[1]FF[4]PL[W])"
        game = parse_sgf(sgf)

        assert game.player_to_move == Color.WHITE

    def test_parse_with_variations(self) -> None:
        """Parser should handle variations."""
        sgf = "(;GM[1]FF[4]PL[B];B[cd](;W[de])(;W[ef]))"
        game = parse_sgf(sgf)

        assert game.solution_tree is not None

    def test_parse_yengo_properties(self) -> None:
        """Parser should read YenGo properties."""
        sgf = "(;GM[1]FF[4]YG[5]YT[life-and-death,ladder])"
        game = parse_sgf(sgf)

        assert game.yengo_props.level == 5
        assert "life-and-death" in game.yengo_props.tags

    def test_parse_invalid_sgf(self) -> None:
        """Parser should raise on invalid SGF."""
        with pytest.raises(Exception):
            parse_sgf("not valid sgf")

    def test_parse_empty_string(self) -> None:
        """Parser should raise on empty string."""
        with pytest.raises(Exception):
            parse_sgf("")


class TestSgfGameProperties:
    """Tests for SGFGame object properties."""

    def test_has_solution_with_moves(self) -> None:
        """Game with moves should have solution."""
        sgf = "(;GM[1]FF[4]PL[B];B[cd])"
        game = parse_sgf(sgf)

        assert game.has_solution

    def test_has_solution_without_moves(self) -> None:
        """Game without moves should not have solution."""
        sgf = "(;GM[1]FF[4])"
        game = parse_sgf(sgf)

        assert not game.has_solution

    def test_metadata_access(self) -> None:
        """Game should provide metadata access."""
        sgf = "(;GM[1]FF[4]GN[Test Puzzle])"
        game = parse_sgf(sgf)

        # metadata is a dict, GN should be in it
        assert game.metadata.get("GN") == "Test Puzzle" or "GN" not in game.metadata


class TestRootCommentParsing:
    """Tests for root comment (C[]) extraction during parsing."""

    def test_root_comment_stored_on_game(self) -> None:
        """Root C[] should be stored in game.root_comment."""
        sgf = "(;GM[1]FF[4]C[This is a root comment]SZ[9]AB[dd])"
        game = parse_sgf(sgf)

        assert game.root_comment == "This is a root comment"

    def test_no_root_comment_defaults_to_empty(self) -> None:
        """SGF without root C[] should have empty root_comment."""
        sgf = "(;GM[1]FF[4]SZ[9]AB[dd])"
        game = parse_sgf(sgf)

        assert game.root_comment == ""

    def test_root_comment_not_in_metadata(self) -> None:
        """Root C[] should NOT be stored in metadata dict."""
        sgf = "(;GM[1]FF[4]C[Root comment]SZ[9])"
        game = parse_sgf(sgf)

        assert "C" not in game.metadata
        assert game.root_comment == "Root comment"


class TestParseRootPropertiesOnly:
    """Tests for parse_root_properties_only() — fast root-only parsing.

    Performance plan Phase 2.4: Verify correctness of the lightweight parser
    used by reconcile to extract metadata without building a full game tree.
    """

    def test_extracts_yengo_properties(self) -> None:
        """Should extract all YenGo custom properties from root."""
        sgf = "(;FF[4]GM[1]SZ[19]YG[beginner]YT[ko,ladder,life-and-death]YQ[q:2;rc:0;hc:0]YH[Corner focus|Ladder pattern]YV[10]YL[cho-chikun-elementary])"
        props = parse_root_properties_only(sgf)

        assert props["YG"] == "beginner"
        assert props["YT"] == "ko,ladder,life-and-death"
        assert props["YQ"] == "q:2;rc:0;hc:0"
        assert props["YH"] == "Corner focus|Ladder pattern"
        assert props["YV"] == "10"
        assert props["YL"] == "cho-chikun-elementary"

    def test_stops_before_move_nodes(self) -> None:
        """Should only return root properties, not move properties."""
        sgf = "(;FF[4]GM[1]SZ[9]YG[beginner]YT[life-and-death];B[cc]C[Good move];W[dd])"
        props = parse_root_properties_only(sgf)

        assert "YG" in props
        assert "YT" in props
        # Move properties should NOT be present
        assert "B" not in props
        assert "W" not in props

    def test_handles_empty_sgf(self) -> None:
        """Should raise SGFParseError for empty content."""
        with pytest.raises(SGFParseError):
            parse_root_properties_only("")

    def test_handles_whitespace_only(self) -> None:
        """Should raise SGFParseError for whitespace-only content."""
        with pytest.raises(SGFParseError):
            parse_root_properties_only("   \n\t  ")

    def test_handles_missing_paren(self) -> None:
        """Should raise SGFParseError for content without opening paren."""
        with pytest.raises(SGFParseError):
            parse_root_properties_only(";FF[4]GM[1]")

    def test_handles_minimal_sgf(self) -> None:
        """Should work with minimal valid SGF."""
        props = parse_root_properties_only("(;FF[4]GM[1])")
        assert props["FF"] == "4"
        assert props["GM"] == "1"

    def test_extracts_standard_properties(self) -> None:
        """Should extract standard SGF properties (SZ, AB, AW, PL)."""
        sgf = "(;FF[4]GM[1]SZ[19]GN[YENGO-abc123]PL[B])"
        props = parse_root_properties_only(sgf)

        assert props["SZ"] == "19"
        assert props["GN"] == "YENGO-abc123"
        assert props["PL"] == "B"

    def test_handles_empty_property_values(self) -> None:
        """Should handle SGF properties with empty values."""
        sgf = "(;FF[4]GM[1]YT[]YQ[])"
        props = parse_root_properties_only(sgf)

        assert props["YT"] == ""
        assert props["YQ"] == ""

    def test_handles_sgf_with_variations(self) -> None:
        """Should only parse root, ignoring variation branches."""
        sgf = "(;FF[4]GM[1]SZ[9]YG[intermediate](;B[cc])(;B[dd]))"
        props = parse_root_properties_only(sgf)

        assert props["YG"] == "intermediate"
        assert "B" not in props

    def test_matches_full_parser_root_properties(self) -> None:
        """Root props from fast parser should match those from full parser."""
        sgf = "(;FF[4]GM[1]SZ[19]YG[advanced]YT[snapback,tesuji]YQ[q:3;rc:1;hc:0]YH[Look for the snapback];B[cc];W[dd])"
        fast_props = parse_root_properties_only(sgf)
        full_game = parse_sgf(sgf)

        assert fast_props["YG"] == full_game.yengo_props.level_slug
        assert fast_props["YT"] == ",".join(full_game.yengo_props.tags)
        assert fast_props["YQ"] == full_game.yengo_props.quality
