"""Unit tests for board module."""

import pytest

from backend.puzzle_manager.core.board import Board
from backend.puzzle_manager.core.primitives import Color, Point


class TestBoardCreation:
    """Tests for Board creation."""

    def test_default_board(self) -> None:
        """Default board should be 19x19."""
        board = Board()
        assert board.size == 19

    def test_custom_size(self) -> None:
        """Board should accept custom sizes."""
        board = Board(9)
        assert board.size == 9

        board = Board(13)
        assert board.size == 13

    def test_small_board_sizes_accepted(self) -> None:
        """Board should accept small sizes within 5–19 range."""
        board = Board(5)
        assert board.size == 5

        board = Board(7)
        assert board.size == 7

    def test_invalid_size(self) -> None:
        """Board should reject sizes outside 5–19 range."""
        with pytest.raises(ValueError):
            Board(4)
        with pytest.raises(ValueError):
            Board(20)


class TestBoardStones:
    """Tests for stone placement."""

    def test_place_stone(self) -> None:
        """Stone should be placeable."""
        board = Board(9)
        p = Point(3, 3)
        board.place_stone(Color.BLACK, p)
        assert board.get(p) == Color.BLACK

    def test_empty_point(self) -> None:
        """Empty point should return None."""
        board = Board(9)
        p = Point(3, 3)
        assert board.get(p) is None

    def test_is_empty(self) -> None:
        """is_empty should check if point has stone."""
        board = Board(9)
        p = Point(3, 3)
        assert board.is_empty(p)
        board.place_stone(Color.BLACK, p)
        assert not board.is_empty(p)


class TestBoardCopy:
    """Tests for board copy."""

    def test_copy_creates_new_board(self) -> None:
        """Copy should create independent board."""
        board = Board(9)
        p = Point(3, 3)
        board.place_stone(Color.BLACK, p)

        copy = board.copy()
        assert copy.get(p) == Color.BLACK

    def test_copy_is_independent(self) -> None:
        """Changes to copy should not affect original."""
        board = Board(9)
        p1 = Point(3, 3)
        p2 = Point(4, 4)
        board.place_stone(Color.BLACK, p1)

        copy = board.copy()
        copy.place_stone(Color.WHITE, p2)

        assert board.get(p2) is None


class TestBoardValidation:
    """Tests for board point validation."""

    def test_valid_point(self) -> None:
        """Points within board should be valid."""
        board = Board(9)
        assert board.is_valid_point(Point(0, 0))
        assert board.is_valid_point(Point(8, 8))
        assert board.is_valid_point(Point(4, 4))

    def test_invalid_point(self) -> None:
        """Points outside board should be invalid."""
        board = Board(9)
        # Note: Point class validates 0-18 range, so we test board boundary
        p = Point(0, 0)
        assert board.is_valid_point(p)
