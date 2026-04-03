"""Unit tests for SGF builder module."""


from backend.puzzle_manager.core.primitives import Color, Point
from backend.puzzle_manager.core.sgf_builder import SGFBuilder
from backend.puzzle_manager.core.sgf_parser import parse_sgf


class TestSgfBuilder:
    """Tests for SGFBuilder class."""

    def test_minimal_build(self) -> None:
        """Builder should create minimal valid SGF."""
        builder = SGFBuilder()
        sgf = builder.build()

        assert "(;" in sgf
        assert "GM[1]" in sgf

    def test_custom_board_size(self) -> None:
        """Builder should support custom board size."""
        builder = SGFBuilder(board_size=9)
        sgf = builder.build()

        assert "SZ[9]" in sgf

    def test_add_black_stones(self) -> None:
        """Builder should add black stones."""
        builder = SGFBuilder()
        builder.add_black_stone(Point(2, 3))
        sgf = builder.build()

        assert "AB[cd]" in sgf

    def test_add_white_stones(self) -> None:
        """Builder should add white stones."""
        builder = SGFBuilder()
        builder.add_white_stone(Point(2, 3))
        sgf = builder.build()

        assert "AW[cd]" in sgf

    def test_set_player_to_move(self) -> None:
        """Builder should set player to move."""
        builder = SGFBuilder()
        builder.set_player_to_move(Color.WHITE)
        sgf = builder.build()

        assert "PL[W]" in sgf

    def test_set_level(self) -> None:
        """Builder should set YenGo level."""
        builder = SGFBuilder()
        builder.set_level(5)
        sgf = builder.build()

        assert "YG[5]" in sgf

    def test_add_tags(self) -> None:
        """Builder should add YenGo tags."""
        builder = SGFBuilder()
        builder.add_tag("life-and-death")
        builder.add_tag("ladder")
        sgf = builder.build()

        assert "YT[" in sgf
        assert "life-and-death" in sgf

    def test_add_hints(self) -> None:
        """Builder should add YenGo hints (compact pipe-delimited format)."""
        builder = SGFBuilder()
        builder.add_hints(["Focus on the corner", "Look for a tesuji"])
        sgf = builder.build()

        # v8 format: YH[hint1|hint2]
        assert "YH[Focus on the corner|Look for a tesuji]" in sgf


class TestSgfBuilderRoundtrip:
    """Tests for SGF round-trip parsing."""

    def test_roundtrip_basic(self) -> None:
        """Built SGF should be parseable."""
        builder = SGFBuilder(board_size=9)
        builder.set_player_to_move(Color.BLACK)
        builder.add_black_stone(Point(2, 3))
        builder.add_white_stone(Point(4, 4))

        sgf = builder.build()
        game = parse_sgf(sgf)

        assert game.board_size == 9
        assert game.player_to_move == Color.BLACK
        assert Point(2, 3) in game.black_stones
        assert Point(4, 4) in game.white_stones
