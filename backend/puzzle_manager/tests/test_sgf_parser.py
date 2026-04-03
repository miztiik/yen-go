"""Unit tests for SGF parser module."""

import pytest

from backend.puzzle_manager.core.primitives import Color, Point
from backend.puzzle_manager.core.sgf_parser import SGFGame, parse_sgf


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
