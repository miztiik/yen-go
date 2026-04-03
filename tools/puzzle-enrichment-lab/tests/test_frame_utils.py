"""Tests for frame_utils — shared geometry utilities (algorithm-agnostic).

Covers: FrameRegions dataclass, detect_board_edge_sides, compute_regions.
"""

from pathlib import Path

import pytest

_HERE = Path(__file__).resolve().parent
_LAB = _HERE.parent

from analyzers.frame_utils import FrameRegions, compute_regions, detect_board_edge_sides
from models.position import Color, Position, Stone

# ---------------------------------------------------------------------------
# FrameRegions type checks
# ---------------------------------------------------------------------------

class TestFrameRegions:
    def test_frozen(self):
        fr = FrameRegions(
            puzzle_bbox=(0, 0, 5, 5),
            puzzle_region=frozenset(),
            occupied=frozenset(),
            board_edge_sides=frozenset(),
        )
        with pytest.raises(AttributeError):
            fr.puzzle_bbox = (1, 1, 6, 6)  # type: ignore[misc]

    def test_no_defense_offense_area(self):
        """FrameRegions must NOT have defense_area/offense_area (GP swap design)."""
        fr = FrameRegions(
            puzzle_bbox=(0, 0, 5, 5),
            puzzle_region=frozenset(),
            occupied=frozenset(),
            board_edge_sides=frozenset(),
        )
        assert not hasattr(fr, "defense_area")
        assert not hasattr(fr, "offense_area")


# ---------------------------------------------------------------------------
# detect_board_edge_sides
# ---------------------------------------------------------------------------

class TestDetectBoardEdgeSides:
    def test_corner_tl(self):
        sides = detect_board_edge_sides((0, 0, 3, 3), board_size=19, margin=2)
        assert "left" in sides
        assert "top" in sides
        assert "right" not in sides
        assert "bottom" not in sides

    def test_corner_br(self):
        sides = detect_board_edge_sides((15, 15, 18, 18), board_size=19, margin=2)
        assert "right" in sides
        assert "bottom" in sides

    def test_center(self):
        sides = detect_board_edge_sides((8, 8, 10, 10), board_size=19, margin=2)
        assert len(sides) == 0

    def test_full_board(self):
        sides = detect_board_edge_sides((0, 0, 18, 18), board_size=19, margin=2)
        assert sides == frozenset({"left", "top", "right", "bottom"})


# ---------------------------------------------------------------------------
# compute_regions
# ---------------------------------------------------------------------------

class TestComputeRegions:
    def test_empty_position(self):
        pos = Position(board_size=19, stones=[], player_to_move=Color.BLACK)
        regions = compute_regions(pos)
        assert regions.puzzle_bbox == (0, 0, 0, 0)
        assert regions.puzzle_region == frozenset()
        assert regions.occupied == frozenset()
        assert regions.board_edge_sides == frozenset()

    def test_single_stone(self):
        pos = Position(
            board_size=19,
            stones=[Stone(color=Color.BLACK, x=10, y=10)],
            player_to_move=Color.BLACK,
        )
        regions = compute_regions(pos)
        assert regions.puzzle_bbox == (10, 10, 10, 10)
        assert (10, 10) in regions.occupied
        # Puzzle region should expand by margin=2
        assert (8, 8) in regions.puzzle_region
        assert (12, 12) in regions.puzzle_region

    def test_puzzle_region_is_frozenset(self):
        """RC-2 verification: puzzle_region must be frozenset[tuple[int,int]]."""
        pos = Position(
            board_size=9,
            stones=[Stone(color=Color.BLACK, x=4, y=4)],
            player_to_move=Color.BLACK,
        )
        regions = compute_regions(pos)
        assert isinstance(regions.puzzle_region, frozenset)
        for coord in regions.puzzle_region:
            assert isinstance(coord, tuple)
            assert len(coord) == 2

    def test_margin_override(self):
        pos = Position(
            board_size=9,
            stones=[Stone(color=Color.BLACK, x=4, y=4)],
            player_to_move=Color.BLACK,
        )
        regions = compute_regions(pos, margin=1)
        assert (3, 3) in regions.puzzle_region
        assert (5, 5) in regions.puzzle_region
        assert (2, 2) not in regions.puzzle_region

    def test_board_size_override(self):
        pos = Position(
            board_size=19,
            stones=[Stone(color=Color.BLACK, x=4, y=4)],
            player_to_move=Color.BLACK,
        )
        regions = compute_regions(pos, board_size=9)
        # All coords should be clamped to 9×9
        for x, y in regions.puzzle_region:
            assert 0 <= x < 9
            assert 0 <= y < 9

    def test_edge_detection_integrated(self):
        pos = Position(
            board_size=9,
            stones=[
                Stone(color=Color.BLACK, x=0, y=0),
                Stone(color=Color.WHITE, x=1, y=1),
            ],
            player_to_move=Color.BLACK,
        )
        regions = compute_regions(pos)
        assert "left" in regions.board_edge_sides
        assert "top" in regions.board_edge_sides
