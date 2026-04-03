"""Tests for Benson's unconditional life and interior-point death detection.

T12: Benson gate unit tests
T13: Interior-point check unit tests
"""

from analyzers.benson_check import (
    check_interior_point_death,
    find_unconditionally_alive_groups,
)


class TestBensonUnconditionalLife:
    """T12: Tests for find_unconditionally_alive_groups."""

    def test_empty_board_returns_empty(self):
        """No stones → no alive groups."""
        result = find_unconditionally_alive_groups({}, board_size=9)
        assert result == set()

    def test_single_stone_not_alive(self):
        """A single stone is never unconditionally alive."""
        stones = {(4, 4): "B"}
        result = find_unconditionally_alive_groups(stones, board_size=9)
        assert len(result) == 0

    def test_two_eye_group_alive(self):
        """A group with two clear eyes is unconditionally alive.

        Board (5x5):
           0 1 2 3 4
        0  . B B B .
        1  B . B . B
        2  B B B B B
        3  . . . . .
        4  . . . . .

        Black has a group surrounding two separate empty points (1,1) and (1,3).
        Each empty point is a vital region fully enclosed by the black group.
        """
        stones: dict[tuple[int, int], str] = {}
        # Top row
        for c in range(1, 4):
            stones[(0, c)] = "B"
        # Second row - black with two eyes
        stones[(1, 0)] = "B"
        stones[(1, 2)] = "B"
        stones[(1, 4)] = "B"
        # Third row - solid black
        for c in range(5):
            stones[(2, c)] = "B"

        result = find_unconditionally_alive_groups(stones, board_size=5)
        # The entire black group should be identified as alive
        assert len(result) >= 1
        # The alive group should contain the black stones
        black_positions = frozenset(pos for pos, c in stones.items() if c == "B")
        assert any(black_positions <= group for group in result)

    def test_framework_false_positive_rejection(self):
        """Framework groups being alive must NOT trigger the gate for contest group.

        In tsumego, surrounding/framework stones ARE unconditionally alive.
        The gate should only fire if the CONTEST group (the one being attacked)
        is alive. Framework groups being alive is expected.

        Test with a large enough board that the framework group has two
        clear external eyes (far from the contest group).
        """
        # 9x9 board: Black framework with two clear eyes at corners,
        # White contest group with only 1 eye in the center
        stones: dict[tuple[int, int], str] = {}

        # Black framework: L-shaped walls with two separated internal eyes
        # Eye 1 at (1,1), Eye 2 at (1,7) — far apart, both vital
        for c in range(9):
            stones[(0, c)] = "B"
            stones[(2, c)] = "B"
        stones[(1, 0)] = "B"
        stones[(1, 2)] = "B"
        stones[(1, 3)] = "B"
        stones[(1, 4)] = "B"
        stones[(1, 5)] = "B"
        stones[(1, 6)] = "B"
        stones[(1, 8)] = "B"
        # (1,1) and (1,7) are empty eyes for the black framework

        # White contest group in the middle rows with only 1 eye
        for c in range(2, 7):
            stones[(3, c)] = "W"
            stones[(5, c)] = "W"
        stones[(4, 2)] = "W"
        stones[(4, 6)] = "W"
        # (4,3), (4,4), (4,5) are empty but form one connected region → 1 eye

        result = find_unconditionally_alive_groups(stones, board_size=9)

        # Black framework should be alive (has 2 eyes at (1,1) and (1,7))
        black_positions = frozenset(pos for pos, c in stones.items() if c == "B")
        assert any(black_positions <= group for group in result), (
            "Black framework should be unconditionally alive"
        )

        # White contest group should NOT be alive (only 1 eye-space)
        white_positions = frozenset(pos for pos, c in stones.items() if c == "W")
        assert not any(white_positions <= group for group in result), (
            "White contest group with 1 eye should NOT be alive"
        )

    def test_ko_dependent_group_not_alive(self):
        """A group with only one vital region is NOT unconditionally alive.

        Board (7x7):
           0 1 2 3 4 5 6
        0  . . . . . . .
        1  . B B B B B .
        2  . B . B . B .
        3  . B B W B B .
        4  . B B B B B .
        5  . . . . . . .
        6  . . . . . . .

        Black has a connected group enclosing two interior spaces
        at (2,2) and (2,4). However, White at (3,3) is inside the
        group boundary. The empty region containing (2,4) includes
        neighbors (3,3)=W (via (3,4)=B? No — let me verify).

        Actually, a simpler analysis: the empty regions fully enclosed
        by Black are {(2,2)} and {(2,4)}. Region {(2,2)} has neighbors
        (1,2)=B, (2,1)=B, (2,3)=B, (3,2)=B — all Black → vital.
        Region {(2,4)} has neighbors (1,4)=B, (2,3)=B, (2,5)=B, (3,4)=B
        — all Black → vital.

        White at (3,3) is surrounded by Black, but it doesn't border
        either empty region. This means Black actually IS alive with 2
        vital regions. We need a different approach.

        Better: place White adjacent to one of the eye regions so that
        region is not vital (has a non-Black neighbor).

        Board (7x7):
           0 1 2 3 4 5 6
        0  . . . . . . .
        1  . B B B B . .
        2  . B . W B . .
        3  . B B B B . .
        4  . . . . . . .

        Black group: (1,1)-(1,4), (2,1), (2,4), (3,1)-(3,4)
        Eye at (2,2): neighbors (1,2)=B, (2,1)=B, (2,3)=W, (3,2)=B
        → NOT all Black (W at (2,3)) → NOT vital for Black.
        Only 1 vital region (none!) → Black NOT unconditionally alive.
        """
        stones: dict[tuple[int, int], str] = {}
        # Row 1: B wall
        for c in range(1, 5):
            stones[(1, c)] = "B"
        # Row 2: B sides + W inside
        stones[(2, 1)] = "B"
        stones[(2, 3)] = "W"
        stones[(2, 4)] = "B"
        # Row 3: B wall
        for c in range(1, 5):
            stones[(3, c)] = "B"

        result = find_unconditionally_alive_groups(stones, board_size=7)

        # The only interior empty cell is (2,2), but its neighbor (2,3)
        # is White, so it is NOT a vital region for Black. Black has
        # 0 vital regions → NOT unconditionally alive.
        black_positions = frozenset(pos for pos, c in stones.items() if c == "B")
        assert not any(black_positions <= group for group in result), (
            "Group with opponent stone breaking eye enclosure should NOT be alive"
        )

    def test_seki_not_classified_as_alive(self):
        """Seki groups should not be classified as unconditionally alive.

        Basic seki: both groups share liberties but neither can capture.
        Benson should NOT classify seki groups as alive.
        """
        # Simplified seki shape on 5x5 — two groups sharing liberties
        #   0 1 2 3 4
        # 0 B B . W W
        # 1 B . . . W
        # 2 B B . W W
        stones: dict[tuple[int, int], str] = {}
        stones[(0, 0)] = "B"
        stones[(0, 1)] = "B"
        stones[(0, 3)] = "W"
        stones[(0, 4)] = "W"
        stones[(1, 0)] = "B"
        stones[(1, 4)] = "W"
        stones[(2, 0)] = "B"
        stones[(2, 1)] = "B"
        stones[(2, 3)] = "W"
        stones[(2, 4)] = "W"

        result = find_unconditionally_alive_groups(stones, board_size=5)
        # In seki, neither group should be unconditionally alive
        # (they don't have 2 vital regions each — shared liberties mean
        # neither group fully encloses its eye regions)
        # Neither the black nor white group should be fully classified as alive
        black_positions = frozenset(pos for pos, c in stones.items() if c == "B")
        white_positions = frozenset(pos for pos, c in stones.items() if c == "W")
        assert not any(black_positions <= group for group in result)
        assert not any(white_positions <= group for group in result)


class TestInteriorPointDeath:
    """T13: Tests for check_interior_point_death."""

    def test_empty_puzzle_region_returns_false(self):
        """No puzzle region → uncertain (False)."""
        assert check_interior_point_death({}, "B", frozenset(), 9) is False

    def test_zero_interior_empty_points_returns_true(self):
        """0 empty points in puzzle region → dead (True).

        All cells in puzzle_region are occupied — no room for eyes.
        """
        stones = {(0, 0): "B", (0, 1): "B", (1, 0): "B", (1, 1): "B"}
        region = frozenset([(0, 0), (0, 1), (1, 0), (1, 1)])
        assert check_interior_point_death(stones, "B", region, 5) is True

    def test_one_interior_empty_point_returns_true(self):
        """1 empty point in puzzle region → dead (only 1 eye possible)."""
        stones = {(0, 0): "B", (0, 1): "B", (1, 0): "B"}
        region = frozenset([(0, 0), (0, 1), (1, 0), (1, 1)])
        # (1,1) is the only empty point
        assert check_interior_point_death(stones, "B", region, 5) is True

    def test_two_non_adjacent_empty_returns_true(self):
        """2 non-adjacent empty points → dead (cannot form connected eye)."""
        # Region has empties at (0,0) and (2,2) — not adjacent
        stones = {(0, 1): "B", (1, 0): "B", (1, 1): "B", (2, 0): "B", (2, 1): "B", (0, 2): "B", (1, 2): "B"}
        region = frozenset([(0, 0), (0, 1), (0, 2), (1, 0), (1, 1), (1, 2), (2, 0), (2, 1), (2, 2)])
        assert check_interior_point_death(stones, "B", region, 5) is True

    def test_two_adjacent_empty_returns_false(self):
        """2 adjacent empty points → uncertain (could form connected space)."""
        # Region has empties at (0,0) and (0,1) — adjacent
        stones = {(1, 0): "B", (1, 1): "B"}
        region = frozenset([(0, 0), (0, 1), (1, 0), (1, 1)])
        assert check_interior_point_death(stones, "B", region, 5) is False

    def test_three_empty_returns_false(self):
        """3+ empty points → uncertain (False)."""
        stones = {(1, 0): "B"}
        region = frozenset([(0, 0), (0, 1), (0, 2), (1, 0)])
        assert check_interior_point_death(stones, "B", region, 5) is False

    def test_opponent_stones_not_counted(self):
        """Only empty cells count — opponent stones are irrelevant to eye formation."""
        # Region has 1 empty and 1 opponent stone
        stones = {(0, 0): "B", (0, 1): "W", (1, 0): "B"}
        region = frozenset([(0, 0), (0, 1), (1, 0), (1, 1)])
        # Empty points for "B" defender: (0,1) has W stone, (1,1) is empty
        # Only (1,1) is truly empty → 1 empty point → dead
        # Wait — (0,1) has a W stone, so it's not empty. Only (1,1) is empty.
        assert check_interior_point_death(stones, "B", region, 5) is True
