"""Unit tests for primitives module."""


from backend.puzzle_manager.core.primitives import Color, Move, Point


class TestPoint:
    """Tests for Point class."""

    def test_point_creation(self) -> None:
        """Point should be created with coordinates."""
        p = Point(3, 4)
        assert p.x == 3
        assert p.y == 4

    def test_point_equality(self) -> None:
        """Points with same coordinates should be equal."""
        p1 = Point(3, 4)
        p2 = Point(3, 4)
        assert p1 == p2

    def test_point_hash(self) -> None:
        """Points should be hashable for use in sets."""
        p1 = Point(3, 4)
        p2 = Point(3, 4)
        assert hash(p1) == hash(p2)
        assert {p1, p2} == {p1}

    def test_point_repr(self) -> None:
        """Point should have useful string representation."""
        p = Point(3, 4)
        assert "3" in str(p) or "de" in str(p)  # Either numeric or SGF

    def test_point_from_sgf(self) -> None:
        """Point should be creatable from SGF coordinate."""
        p = Point.from_sgf("cd")
        assert p.x == 2
        assert p.y == 3

    def test_point_to_sgf(self) -> None:
        """Point should convert to SGF coordinate."""
        p = Point(2, 3)
        assert p.to_sgf() == "cd"

    def test_point_neighbors(self) -> None:
        """Point should return valid neighbors."""
        p = Point(5, 5)
        neighbors = p.neighbors()
        assert len(neighbors) == 4
        assert Point(4, 5) in neighbors
        assert Point(6, 5) in neighbors
        assert Point(5, 4) in neighbors
        assert Point(5, 6) in neighbors

    def test_point_corner_neighbors(self) -> None:
        """Corner point should have fewer neighbors."""
        p = Point(0, 0)
        neighbors = p.neighbors()
        assert len(neighbors) == 2


class TestColor:
    """Tests for Color enum."""

    def test_color_values(self) -> None:
        """Colors should have correct values."""
        assert Color.BLACK.value == "B"
        assert Color.WHITE.value == "W"

    def test_color_opponent(self) -> None:
        """Colors should know their opponent."""
        assert Color.BLACK.opponent() == Color.WHITE
        assert Color.WHITE.opponent() == Color.BLACK


class TestMove:
    """Tests for Move class."""

    def test_move_creation(self) -> None:
        """Move should be created with color and point."""
        p = Point(3, 4)
        m = Move(color=Color.BLACK, point=p)
        assert m.color == Color.BLACK
        assert m.point == p

    def test_pass_move(self) -> None:
        """Pass move should have no point."""
        m = Move.pass_move(Color.BLACK)
        assert m.is_pass
        assert m.point is None

    def test_play_move(self) -> None:
        """Play move should create stone placement."""
        p = Point(3, 4)
        m = Move.play(Color.BLACK, p)
        assert not m.is_pass
        assert m.point == p

    def test_move_from_sgf(self) -> None:
        """Move should be creatable from SGF."""
        m = Move.from_sgf(Color.BLACK, "cd")
        assert m.color == Color.BLACK
        assert m.point == Point(2, 3)

    def test_move_from_sgf_pass(self) -> None:
        """Empty SGF should create pass move."""
        m = Move.from_sgf(Color.BLACK, "")
        assert m.is_pass
