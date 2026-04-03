"""
Minimal Go legality engine for BTP wrong-move enumeration.

Self-contained implementation — tools/ must NOT import from backend/.
Provides board state management with move legality checking (ko, suicide,
occupied), capture detection via flood-fill, and undo via snapshots.

This is NOT a general-purpose Go engine. It exists solely to enumerate
legal moves on a BTP board position so that the node_parser can decode
BTP's compressed wrong_moves format (skip-count over legal moves).
"""

from __future__ import annotations

from typing import Final

# Board cell values
EMPTY: Final[int] = 0
BLACK: Final[int] = 1
WHITE: Final[int] = 2


def _opponent(color: int) -> int:
    """Return opponent color."""
    return WHITE if color == BLACK else BLACK


class GoEngine:
    """Minimal Go board with legality checks and capture handling.

    Board is a flat list of size*size ints (EMPTY/BLACK/WHITE).
    Coordinates are (x, y) where x=column, y=row, 0-indexed.

    Usage::

        engine = GoEngine(9)
        engine.load_position(decoded_rows, ko_point=None, to_play=BLACK)
        if engine.is_legal(3, 4, BLACK):
            engine.play(3, 4, BLACK)
        engine.undo()  # Restore previous state
    """

    __slots__ = ("size", "board", "ko_point", "_history")

    def __init__(self, size: int = 9) -> None:
        self.size = size
        self.board: list[int] = [EMPTY] * (size * size)
        self.ko_point: tuple[int, int] | None = None
        self._history: list[tuple[list[int], tuple[int, int] | None]] = []

    # --- Index helpers ---

    def _idx(self, x: int, y: int) -> int:
        return y * self.size + x

    def _in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.size and 0 <= y < self.size

    def _neighbors(self, x: int, y: int) -> list[tuple[int, int]]:
        result: list[tuple[int, int]] = []
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nx, ny = x + dx, y + dy
            if self._in_bounds(nx, ny):
                result.append((nx, ny))
        return result

    # --- Group / liberty helpers ---

    def _group(self, x: int, y: int) -> tuple[set[tuple[int, int]], set[tuple[int, int]]]:
        """Find the connected group containing (x,y) and its liberties.

        Returns:
            (group_set, liberty_set)
        """
        color = self.board[self._idx(x, y)]
        if color == EMPTY:
            return set(), set()

        group: set[tuple[int, int]] = set()
        liberties: set[tuple[int, int]] = set()
        stack = [(x, y)]

        while stack:
            cx, cy = stack.pop()
            if (cx, cy) in group:
                continue
            group.add((cx, cy))
            for nx, ny in self._neighbors(cx, cy):
                cell = self.board[self._idx(nx, ny)]
                if cell == EMPTY:
                    liberties.add((nx, ny))
                elif cell == color and (nx, ny) not in group:
                    stack.append((nx, ny))

        return group, liberties

    def _remove_group(self, group: set[tuple[int, int]]) -> None:
        """Remove all stones in a group (set them to EMPTY)."""
        for gx, gy in group:
            self.board[self._idx(gx, gy)] = EMPTY

    # --- Position loading ---

    def load_position(
        self,
        rows: list[str],
        ko_point: tuple[int, int] | None = None,
        to_play: int = BLACK,
    ) -> None:
        """Load a board position from decoded hash rows.

        Args:
            rows: List of row strings with '.', 'B', 'W' chars
                  (from hash_decoder.decode_hash).
            ko_point: Optional ko point as (x, y).
            to_play: Color to move (BLACK or WHITE).
        """
        size = len(rows)
        self.size = size
        self.board = [EMPTY] * (size * size)
        self.ko_point = ko_point
        self._history.clear()

        char_map = {".": EMPTY, "B": BLACK, "W": WHITE}
        for y, row in enumerate(rows):
            for x, ch in enumerate(row):
                if x < size:
                    self.board[self._idx(x, y)] = char_map.get(ch, EMPTY)

    # --- Move legality ---

    def is_legal(self, x: int, y: int, color: int) -> bool:
        """Check if placing color at (x,y) is a legal move.

        Checks:
        1. In bounds
        2. Point is empty
        3. Not a ko recapture
        4. Not suicide (has liberty after captures)
        """
        if not self._in_bounds(x, y):
            return False
        if self.board[self._idx(x, y)] != EMPTY:
            return False
        if self.ko_point and self.ko_point == (x, y):
            return False

        # Temporarily place stone
        self.board[self._idx(x, y)] = color
        opp = _opponent(color)

        # Check if any opponent neighbor group has zero liberties (captures)
        has_capture = False
        for nx, ny in self._neighbors(x, y):
            if self.board[self._idx(nx, ny)] == opp:
                _, libs = self._group(nx, ny)
                if not libs:
                    has_capture = True
                    break

        # Check if own group has liberties
        _, own_libs = self._group(x, y)
        legal = bool(own_libs) or has_capture

        # Undo temporary placement
        self.board[self._idx(x, y)] = EMPTY
        return legal

    def get_legal_moves(self, color: int) -> list[tuple[int, int]]:
        """Get all legal moves for color, in BTP enumeration order.

        BTP enumerates moves row-by-row, left-to-right (y=0..size-1, x=0..size-1).

        Returns:
            List of (x, y) tuples of legal moves.
        """
        moves: list[tuple[int, int]] = []
        for y in range(self.size):
            for x in range(self.size):
                if self.is_legal(x, y, color):
                    moves.append((x, y))
        return moves

    # --- Move execution ---

    def play(self, x: int, y: int, color: int) -> list[tuple[int, int]]:
        """Place a stone and handle captures.

        Saves board state for undo. Returns list of captured positions.

        Args:
            x, y: Coordinates.
            color: BLACK or WHITE.

        Returns:
            List of captured stone positions.

        Raises:
            ValueError: If move is illegal.
        """
        if not self.is_legal(x, y, color):
            raise ValueError(f"Illegal move: ({x},{y}) for color {color}")

        # Save state for undo
        self._history.append((list(self.board), self.ko_point))

        # Place stone
        self.board[self._idx(x, y)] = color
        opp = _opponent(color)

        # Capture opponent groups with no liberties
        captured: list[tuple[int, int]] = []
        for nx, ny in self._neighbors(x, y):
            if self.board[self._idx(nx, ny)] == opp:
                group, libs = self._group(nx, ny)
                if not libs:
                    captured.extend(group)
                    self._remove_group(group)

        # Detect ko: single stone captured, single stone placed with exactly 1 liberty
        new_ko: tuple[int, int] | None = None
        if len(captured) == 1:
            _, own_libs = self._group(x, y)
            if len(own_libs) == 1:
                cx, cy = captured[0]
                new_ko = (cx, cy)

        self.ko_point = new_ko
        return captured

    def undo(self) -> None:
        """Undo the last move, restoring board and ko state.

        Raises:
            IndexError: If no moves to undo.
        """
        if not self._history:
            raise IndexError("No moves to undo")
        self.board, self.ko_point = self._history.pop()

    def get(self, x: int, y: int) -> int:
        """Get cell value at (x, y)."""
        return self.board[self._idx(x, y)]

    def copy(self) -> GoEngine:
        """Create a deep copy of this engine."""
        new = GoEngine(self.size)
        new.board = list(self.board)
        new.ko_point = self.ko_point
        new._history = [(list(b), k) for b, k in self._history]
        return new
