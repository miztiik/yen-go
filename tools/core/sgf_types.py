"""
Primitive value objects for Go board representation.

Standalone types for use across all tools. These mirror the backend's
primitives (backend/puzzle_manager/core/primitives.py) but are fully
independent — tools must NOT import from backend/.

Types:
    Color: Stone color enum (BLACK='B', WHITE='W')
    Point: Immutable board coordinate (0-indexed, 0-18)
    Move: A stone placement or pass
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Final


class Color(str, Enum):
    """Stone color."""

    BLACK = "B"
    WHITE = "W"

    def opponent(self) -> Color:
        """Get the opponent's color."""
        return Color.WHITE if self == Color.BLACK else Color.BLACK

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class Point:
    """A point on the Go board.

    Coordinates are 0-indexed, with (0, 0) at top-left.
    x is column (left to right), y is row (top to bottom).
    """

    x: int
    y: int

    def __post_init__(self) -> None:
        """Validate coordinates."""
        if not (0 <= self.x <= 18 and 0 <= self.y <= 18):
            raise ValueError(
                f"Point coordinates must be 0-18, got ({self.x}, {self.y})"
            )

    def neighbors(self, board_size: int = 19) -> list[Point]:
        """Get orthogonally adjacent points within board bounds."""
        result = []
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nx, ny = self.x + dx, self.y + dy
            if 0 <= nx < board_size and 0 <= ny < board_size:
                result.append(Point(nx, ny))
        return result

    @classmethod
    def from_sgf(cls, sgf: str) -> Point:
        """Create Point from SGF coordinate string (e.g., 'ab', 'cd').

        Args:
            sgf: Two-character SGF coordinate string.

        Returns:
            Point instance.

        Raises:
            ValueError: If coordinate string is invalid.
        """
        if len(sgf) != 2:
            raise ValueError(f"Invalid SGF coordinate: {sgf!r}")
        x = ord(sgf[0]) - ord("a")
        y = ord(sgf[1]) - ord("a")
        return cls(x, y)

    def to_sgf(self) -> str:
        """Convert to SGF coordinate string."""
        return chr(ord("a") + self.x) + chr(ord("a") + self.y)

    def __str__(self) -> str:
        return self.to_sgf()


@dataclass(frozen=True, slots=True)
class Move:
    """A move in the game.

    Represents either a stone placement or a pass.
    """

    color: Color
    point: Point | None  # None for pass

    @property
    def is_pass(self) -> bool:
        """Check if this is a pass move."""
        return self.point is None

    @classmethod
    def pass_move(cls, color: Color) -> Move:
        """Create a pass move."""
        return cls(color=color, point=None)

    @classmethod
    def play(cls, color: Color, point: Point) -> Move:
        """Create a stone placement move."""
        return cls(color=color, point=point)

    @classmethod
    def from_sgf(cls, color: Color, sgf: str) -> Move:
        """Create Move from SGF coordinate.

        Args:
            color: Stone color.
            sgf: SGF coordinate string, or empty string for pass.
        """
        if not sgf or sgf == "tt":  # tt is pass in SGF
            return cls.pass_move(color)
        return cls.play(color, Point.from_sgf(sgf))

    def to_sgf(self) -> str:
        """Convert to SGF property value."""
        if self.is_pass:
            return ""
        return self.point.to_sgf() if self.point else ""

    def __str__(self) -> str:
        if self.is_pass:
            return f"{self.color}[pass]"
        return f"{self.color}[{self.point}]"


# --- Level constants (mirrored from backend/puzzle_manager/core/constants.py) ---

SLUG_TO_LEVEL: Final[dict[str, int]] = {
    "novice": 1,
    "beginner": 2,
    "elementary": 3,
    "intermediate": 4,
    "upper-intermediate": 5,
    "advanced": 6,
    "low-dan": 7,
    "high-dan": 8,
    "expert": 9,
}

LEVEL_TO_SLUG: Final[dict[int, str]] = {v: k for k, v in SLUG_TO_LEVEL.items()}

VALID_LEVEL_SLUGS: Final[frozenset[str]] = frozenset(SLUG_TO_LEVEL.keys())

VALID_LEVEL_SLUGS_ORDERED: Final[tuple[str, ...]] = (
    "novice", "beginner", "elementary", "intermediate",
    "upper-intermediate", "advanced", "low-dan", "high-dan", "expert",
)
