"""Unit tests for coordinates module."""


from backend.puzzle_manager.core.coordinates import (
    point_to_sgf,
    sgf_coord_to_tuple,
    sgf_to_point,
    tuple_to_sgf_coord,
)
from backend.puzzle_manager.core.primitives import Point


class TestSgfToPoint:
    """Tests for SGF to Point conversion."""

    def test_aa_is_origin(self) -> None:
        """'aa' should be top-left corner (0, 0)."""
        point = sgf_to_point("aa")
        assert point.x == 0
        assert point.y == 0

    def test_standard_coordinates(self) -> None:
        """Standard SGF coordinates should convert correctly."""
        assert sgf_to_point("ab") == Point(0, 1)
        assert sgf_to_point("ba") == Point(1, 0)
        assert sgf_to_point("cd") == Point(2, 3)

    def test_full_board_coordinates(self) -> None:
        """Full 19x19 board coordinates should work."""
        # ss is the corner for 19x19 (letter 's' = 18)
        point = sgf_to_point("ss")
        assert point.x == 18
        assert point.y == 18


class TestPointToSgf:
    """Tests for Point to SGF conversion."""

    def test_origin_is_aa(self) -> None:
        """Point(0, 0) should be 'aa'."""
        assert point_to_sgf(Point(0, 0)) == "aa"

    def test_standard_points(self) -> None:
        """Standard points should convert correctly."""
        assert point_to_sgf(Point(0, 1)) == "ab"
        assert point_to_sgf(Point(1, 0)) == "ba"
        assert point_to_sgf(Point(2, 3)) == "cd"


class TestRoundTrip:
    """Tests for round-trip conversion."""

    def test_sgf_roundtrip(self) -> None:
        """SGF -> Point -> SGF should be identity."""
        coords = ["aa", "ab", "cd", "jj", "ss"]
        for coord in coords:
            point = sgf_to_point(coord)
            assert point_to_sgf(point) == coord

    def test_point_roundtrip(self) -> None:
        """Point -> SGF -> Point should be identity."""
        points = [Point(0, 0), Point(5, 10), Point(18, 18)]
        for point in points:
            sgf = point_to_sgf(point)
            assert sgf_to_point(sgf) == point


class TestTupleConversions:
    """Tests for tuple conversion functions."""

    def test_sgf_to_tuple(self) -> None:
        """SGF coordinate should convert to tuple."""
        assert sgf_coord_to_tuple("aa") == (0, 0)
        assert sgf_coord_to_tuple("cd") == (2, 3)

    def test_tuple_to_sgf(self) -> None:
        """Tuple should convert to SGF coordinate."""
        assert tuple_to_sgf_coord(0, 0) == "aa"
        assert tuple_to_sgf_coord(2, 3) == "cd"

    def test_tuple_roundtrip(self) -> None:
        """Tuple conversions should round-trip."""
        x, y = 5, 10
        sgf = tuple_to_sgf_coord(x, y)
        result = sgf_coord_to_tuple(sgf)
        assert result == (x, y)
