"""
Go board simulation for puzzle analysis.

Provides basic Go rules implementation for:
- Capturing stones
- Detecting liberties
- Checking for suicide
- Ko detection
"""

from dataclasses import dataclass, field
from typing import Self

from backend.puzzle_manager.core.constants import MAX_BOARD_SIZE, MIN_BOARD_SIZE
from backend.puzzle_manager.core.primitives import Color, Move, Point


@dataclass
class Group:
    """A connected group of stones."""

    color: Color
    stones: set[Point] = field(default_factory=set)
    liberties: set[Point] = field(default_factory=set)

    @property
    def is_captured(self) -> bool:
        """Check if group has no liberties."""
        return len(self.liberties) == 0


class Board:
    """Go board with basic rules implementation.

    Supports:
    - Stone placement
    - Capture detection
    - Suicide prevention
    - Ko detection
    - Board state queries
    """

    def __init__(self, size: int = 19) -> None:
        """Initialize empty board.

        Args:
            size: Board size (5–19 inclusive).
        """
        if not (MIN_BOARD_SIZE <= size <= MAX_BOARD_SIZE):
            raise ValueError(f"Invalid board size: {size}. Must be {MIN_BOARD_SIZE}–{MAX_BOARD_SIZE}.")

        self.size = size
        self._stones: dict[Point, Color] = {}
        self._ko_point: Point | None = None
        self._last_capture_count: int = 0

    def copy(self) -> Self:
        """Create a deep copy of the board."""
        new_board = Board(self.size)
        new_board._stones = dict(self._stones)
        new_board._ko_point = self._ko_point
        new_board._last_capture_count = self._last_capture_count
        return new_board  # type: ignore[return-value]

    def get(self, point: Point) -> Color | None:
        """Get stone color at point, or None if empty."""
        return self._stones.get(point)

    def is_empty(self, point: Point) -> bool:
        """Check if point is empty."""
        return point not in self._stones

    def is_valid_point(self, point: Point) -> bool:
        """Check if point is within board bounds."""
        return 0 <= point.x < self.size and 0 <= point.y < self.size

    def place_stone(self, color: Color, point: Point) -> None:
        """Place a stone on the board.

        Does not check game rules - use play() for rule checking.
        """
        if not self.is_valid_point(point):
            raise ValueError(f"Point {point} out of bounds for size {self.size}")
        self._stones[point] = color

    def remove_stone(self, point: Point) -> Color | None:
        """Remove stone from board, returning its color."""
        return self._stones.pop(point, None)

    def get_group(self, point: Point) -> Group | None:
        """Get the group containing the stone at point."""
        color = self.get(point)
        if color is None:
            return None

        stones: set[Point] = set()
        liberties: set[Point] = set()
        to_visit = [point]

        while to_visit:
            current = to_visit.pop()
            if current in stones:
                continue
            stones.add(current)

            for neighbor in current.neighbors(self.size):
                neighbor_color = self.get(neighbor)
                if neighbor_color is None:
                    liberties.add(neighbor)
                elif neighbor_color == color and neighbor not in stones:
                    to_visit.append(neighbor)

        return Group(color=color, stones=stones, liberties=liberties)

    def get_liberties(self, point: Point) -> set[Point]:
        """Get liberties of the group at point."""
        group = self.get_group(point)
        return group.liberties if group else set()

    def count_liberties(self, point: Point) -> int:
        """Count liberties of the group at point."""
        return len(self.get_liberties(point))

    def would_be_suicide(self, color: Color, point: Point) -> bool:
        """Check if playing at point would be suicide.

        A move is suicide if it has no liberties after placement
        and doesn't capture any opponent stones.
        """
        if not self.is_empty(point):
            return False

        # Temporarily place the stone
        test_board = self.copy()
        test_board.place_stone(color, point)

        # Check if we capture any opponent stones
        for neighbor in point.neighbors(self.size):
            if test_board.get(neighbor) == color.opponent():
                group = test_board.get_group(neighbor)
                if group and group.is_captured:
                    return False  # We capture, so not suicide

        # Check if our group has liberties
        our_group = test_board.get_group(point)
        return our_group is not None and our_group.is_captured

    @property
    def ko_point(self) -> Point | None:
        """Current ko point, or None if no ko restriction exists."""
        return self._ko_point

    def is_ko(self, point: Point) -> bool:
        """Check if playing at point would violate ko rule."""
        return self._ko_point == point

    def play(self, move: Move) -> list[Point]:
        """Play a move on the board.

        Args:
            move: Move to play.

        Returns:
            List of captured stone positions.

        Raises:
            ValueError: If move is illegal.
        """
        if move.is_pass:
            self._ko_point = None
            self._last_capture_count = 0
            return []

        point = move.point
        if point is None:
            return []

        if not self.is_valid_point(point):
            raise ValueError(f"Point {point} out of bounds")

        if not self.is_empty(point):
            raise ValueError(f"Point {point} is occupied")

        if self.is_ko(point):
            raise ValueError(f"Ko violation at {point}")

        if self.would_be_suicide(move.color, point):
            raise ValueError(f"Suicide at {point}")

        # Place the stone
        self.place_stone(move.color, point)

        # Capture opponent stones
        captured: list[Point] = []
        for neighbor in point.neighbors(self.size):
            if self.get(neighbor) == move.color.opponent():
                group = self.get_group(neighbor)
                if group and group.is_captured:
                    for stone in group.stones:
                        self.remove_stone(stone)
                        captured.append(stone)

        # Update ko point
        if len(captured) == 1:
            # Potential ko - check if we only have one liberty
            our_group = self.get_group(point)
            if our_group and len(our_group.liberties) == 1:
                self._ko_point = captured[0]
            else:
                self._ko_point = None
        else:
            self._ko_point = None

        self._last_capture_count = len(captured)
        return captured

    def setup_position(
        self,
        black_stones: list[Point],
        white_stones: list[Point],
    ) -> None:
        """Set up initial position.

        Args:
            black_stones: Positions for black stones.
            white_stones: Positions for white stones.
        """
        for point in black_stones:
            self.place_stone(Color.BLACK, point)
        for point in white_stones:
            self.place_stone(Color.WHITE, point)

    def get_all_stones(self, color: Color | None = None) -> list[Point]:
        """Get all stones on the board.

        Args:
            color: Filter by color, or None for all stones.

        Returns:
            List of stone positions.
        """
        if color is None:
            return list(self._stones.keys())
        return [p for p, c in self._stones.items() if c == color]

    def get_empty_points(self) -> list[Point]:
        """Get all empty points on the board."""
        empty = []
        for x in range(self.size):
            for y in range(self.size):
                point = Point(x, y)
                if self.is_empty(point):
                    empty.append(point)
        return empty

    def to_ascii(self) -> str:
        """Generate ASCII representation of the board."""
        lines = []
        for y in range(self.size):
            row = ""
            for x in range(self.size):
                point = Point(x, y)
                color = self.get(point)
                if color == Color.BLACK:
                    row += "X "
                elif color == Color.WHITE:
                    row += "O "
                else:
                    row += ". "
            lines.append(row.rstrip())
        return "\n".join(lines)

    def __str__(self) -> str:
        return self.to_ascii()

    def __repr__(self) -> str:
        return f"Board(size={self.size}, stones={len(self._stones)})"
