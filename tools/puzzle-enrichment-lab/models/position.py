"""Board position model — stones, size, player to move."""

from __future__ import annotations

import logging
from enum import Enum

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class Color(str, Enum):
    BLACK = "B"
    WHITE = "W"


class Stone(BaseModel):
    """A single stone on the board."""
    color: Color
    x: int = Field(ge=0, le=18, description="Column (0-indexed, 0=left)")
    y: int = Field(ge=0, le=18, description="Row (0-indexed, 0=top)")

    @property
    def sgf_coord(self) -> str:
        """Convert to SGF coordinate (e.g., 'cd')."""
        return chr(ord('a') + self.x) + chr(ord('a') + self.y)

    @property
    def gtp_coord(self) -> str:
        """Convert to GTP coordinate (e.g., 'D16'). Skips 'I'.

        Note: Assumes 19×19 board. For non-19×19 boards, use
        ``gtp_coord_for(board_size)`` instead.
        """
        return self.gtp_coord_for(19)

    def gtp_coord_for(self, board_size: int) -> str:
        """Convert to GTP coordinate for the given board size."""
        letters = "ABCDEFGHJKLMNOPQRST"
        col = letters[self.x] if self.x < len(letters) else '?'
        row = board_size - self.y  # GTP rows count from bottom
        return f"{col}{row}"

    @classmethod
    def from_sgf(cls, color: Color, sgf_coord: str) -> Stone:
        """Create from SGF coordinate like 'cd'."""
        x = ord(sgf_coord[0]) - ord('a')
        y = ord(sgf_coord[1]) - ord('a')
        return cls(color=color, x=x, y=y)


class Position(BaseModel):
    """A complete board position for analysis."""
    board_size: int = Field(default=19, ge=5, le=19)
    stones: list[Stone] = Field(default_factory=list)
    player_to_move: Color = Color.BLACK
    komi: float = Field(default=7.5)

    @property
    def black_stones(self) -> list[Stone]:
        return [s for s in self.stones if s.color == Color.BLACK]

    @property
    def white_stones(self) -> list[Stone]:
        return [s for s in self.stones if s.color == Color.WHITE]

    def to_katago_initial_stones(self) -> list[list[str]]:
        """Convert to KataGo analysis format [["B","D4"],["W","C5"],...]."""
        letters = "ABCDEFGHJKLMNOPQRST"
        result = []
        for stone in self.stones:
            col = letters[stone.x] if stone.x < len(letters) else "?"
            row = self.board_size - stone.y  # GTP rows count from bottom
            result.append([stone.color.value, f"{col}{row}"])
        return result

    def to_sgf(self) -> str:
        """Serialize position to a minimal SGF string for diagnostic logging.

        Produces a single-node SGF with SZ, PL, AB, and AW properties.
        """
        parts = [f"(;SZ[{self.board_size}]FF[4]GM[1]PL[{self.player_to_move.value}]"]
        black_coords = [s.sgf_coord for s in self.black_stones]
        white_coords = [s.sgf_coord for s in self.white_stones]
        if black_coords:
            parts.append("AB" + "".join(f"[{c}]" for c in black_coords))
        if white_coords:
            parts.append("AW" + "".join(f"[{c}]" for c in white_coords))
        parts.append(")")
        return "".join(parts)

    def get_puzzle_region_moves(self, margin: int = 2) -> list[str]:
        """Get all empty intersections within the puzzle region (bounding box of stones + margin).

        This restricts KataGo's analysis to moves near existing stones,
        preventing it from suggesting moves on the far side of an empty board.

        Args:
            margin: Extra rows/cols around the bounding box (default 2)

        Returns:
            List of GTP coordinates for all empty points in the region.
            Empty list if no stones (don't restrict).
        """
        if not self.stones:
            return []

        # Find bounding box of all stones
        min_x = min(s.x for s in self.stones)
        max_x = max(s.x for s in self.stones)
        min_y = min(s.y for s in self.stones)
        max_y = max(s.y for s in self.stones)

        # Expand by margin
        min_x = max(0, min_x - margin)
        max_x = min(self.board_size - 1, max_x + margin)
        min_y = max(0, min_y - margin)
        max_y = min(self.board_size - 1, max_y + margin)

        # Collect occupied positions
        occupied = {(s.x, s.y) for s in self.stones}

        # Generate GTP coords for all empty points in region
        letters = "ABCDEFGHJKLMNOPQRST"
        moves = []
        for y in range(min_y, max_y + 1):
            for x in range(min_x, max_x + 1):
                if (x, y) not in occupied:
                    col = letters[x] if x < len(letters) else 'A'
                    row = self.board_size - y
                    moves.append(f"{col}{row}")

        return moves

    def get_nearby_moves(self, max_distance: int = 2) -> list[str]:
        """Get empty intersections within Chebyshev distance of any existing stone.

        Unlike get_puzzle_region_moves() which uses a rectangular bounding box,
        this uses per-stone Chebyshev (chessboard) distance — tighter for
        L-shaped, diagonal, or scattered stone formations.

        Chebyshev distance: max(|dx|, |dy|) between candidate point and
        nearest stone. A point is included if distance ≤ max_distance.

        Args:
            max_distance: Maximum Chebyshev distance from any stone (default 2).

        Returns:
            List of GTP coordinates for all empty points near stones.
            Empty list if no stones.
        """
        if not self.stones:
            return []

        occupied = {(s.x, s.y) for s in self.stones}
        nearby: set[tuple[int, int]] = set()

        for stone in self.stones:
            for dy in range(-max_distance, max_distance + 1):
                for dx in range(-max_distance, max_distance + 1):
                    nx, ny = stone.x + dx, stone.y + dy
                    if (
                        0 <= nx < self.board_size
                        and 0 <= ny < self.board_size
                        and (nx, ny) not in occupied
                    ):
                        nearby.add((nx, ny))

        letters = "ABCDEFGHJKLMNOPQRST"
        moves = []
        for x, y in sorted(nearby):
            col = letters[x] if x < len(letters) else 'A'
            row = self.board_size - y
            moves.append(f"{col}{row}")

        return moves

    # ---------------------------------------------------------------
    # S.1.1 — bounding box
    # ---------------------------------------------------------------

    def get_bounding_box(self) -> tuple[int, int, int, int]:
        """Return (min_x, min_y, max_x, max_y) of all stones.

        Raises:
            ValueError: If the position has no stones.
        """
        if not self.stones:
            raise ValueError("Cannot compute bounding box: no stones on board")
        min_x = min(s.x for s in self.stones)
        min_y = min(s.y for s in self.stones)
        max_x = max(s.x for s in self.stones)
        max_y = max(s.y for s in self.stones)
        return (min_x, min_y, max_x, max_y)

    # ---------------------------------------------------------------
    # S.1.2 — symmetry transforms
    # ---------------------------------------------------------------

    def rotate(self, degrees: int) -> Position:
        """Rotate all stone coordinates by the given degrees (0/90/180/270).

        Rotation is clockwise around the center of the board.
        For a board of size N: (x, y) → rotated coordinates.
        - 0°: (x, y) → (x, y)
        - 90°: (x, y) → (N-1-y, x)
        - 180°: (x, y) → (N-1-x, N-1-y)
        - 270°: (x, y) → (y, N-1-x)

        Args:
            degrees: Rotation angle, must be 0, 90, 180, or 270.

        Returns:
            New Position with rotated stone coordinates.

        Raises:
            ValueError: If degrees is not 0, 90, 180, or 270.
        """
        if degrees not in (0, 90, 180, 270):
            raise ValueError(f"degrees must be 0, 90, 180, or 270, got {degrees}")

        if degrees == 0:
            return self.model_copy(deep=True)

        n = self.board_size - 1
        rotated_stones: list[Stone] = []
        for s in self.stones:
            if degrees == 90:
                nx, ny = n - s.y, s.x
            elif degrees == 180:
                nx, ny = n - s.x, n - s.y
            else:  # 270
                nx, ny = s.y, n - s.x
            rotated_stones.append(Stone(color=s.color, x=nx, y=ny))

        return Position(
            board_size=self.board_size,
            stones=rotated_stones,
            player_to_move=self.player_to_move,
            komi=self.komi,
        )

    def reflect(self, axis: str) -> Position:
        """Reflect all stone coordinates across the given axis.

        - "x": Reflect horizontally (left/right): (x, y) → (N-1-x, y)
        - "y": Reflect vertically (top/bottom): (x, y) → (x, N-1-y)

        Args:
            axis: "x" for horizontal reflection, "y" for vertical reflection.

        Returns:
            New Position with reflected stone coordinates.

        Raises:
            ValueError: If axis is not "x" or "y".
        """
        if axis not in ("x", "y"):
            raise ValueError(f"axis must be 'x' or 'y', got '{axis}'")

        n = self.board_size - 1
        reflected_stones: list[Stone] = []
        for s in self.stones:
            if axis == "x":
                nx, ny = n - s.x, s.y
            else:  # "y"
                nx, ny = s.x, n - s.y
            reflected_stones.append(Stone(color=s.color, x=nx, y=ny))

        return Position(
            board_size=self.board_size,
            stones=reflected_stones,
            player_to_move=self.player_to_move,
            komi=self.komi,
        )


