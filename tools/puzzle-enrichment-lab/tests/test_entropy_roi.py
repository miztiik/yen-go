"""Tests for ownership entropy ROI computation (T15)."""

from __future__ import annotations

import pytest
from analyzers.entropy_roi import (
    EntropyROI,
    _binary_entropy,
    compute_entropy_grid,
    compute_entropy_roi,
    get_roi_allow_moves,
    validate_frame_quality,
)
from analyzers.frame_adapter import get_allow_moves_with_fallback

# ---------------------------------------------------------------------------
# T15.1: _binary_entropy edge cases
# ---------------------------------------------------------------------------


class TestBinaryEntropy:
    def test_entropy_zero_at_p0(self) -> None:
        assert _binary_entropy(0.0) == 0.0

    def test_entropy_zero_at_p1(self) -> None:
        assert _binary_entropy(1.0) == 0.0

    def test_entropy_max_at_p05(self) -> None:
        assert _binary_entropy(0.5) == pytest.approx(1.0)

    def test_entropy_symmetric(self) -> None:
        assert _binary_entropy(0.3) == pytest.approx(_binary_entropy(0.7))

    def test_entropy_between_0_and_1(self) -> None:
        for p in [0.1, 0.2, 0.4, 0.6, 0.8, 0.9]:
            h = _binary_entropy(p)
            assert 0.0 < h < 1.0, f"entropy at p={p} should be in (0,1), got {h}"


# ---------------------------------------------------------------------------
# T15.2: compute_entropy_grid with uniform ownership
# ---------------------------------------------------------------------------


class TestComputeEntropyGrid:
    def test_uniform_black_ownership(self) -> None:
        """All +1 (black owns) -> all p=1 -> all entropy=0."""
        board_size = 5
        ownership = [1.0] * (board_size * board_size)
        grid = compute_entropy_grid(ownership, board_size)
        assert len(grid) == board_size
        for row in grid:
            assert len(row) == board_size
            for val in row:
                assert val == pytest.approx(0.0)

    def test_uniform_white_ownership(self) -> None:
        """All -1 (white owns) -> all p=0 -> all entropy=0."""
        board_size = 5
        ownership = [-1.0] * (board_size * board_size)
        grid = compute_entropy_grid(ownership, board_size)
        for row in grid:
            for val in row:
                assert val == pytest.approx(0.0)

    def test_uniform_contested(self) -> None:
        """All 0 (contested) -> all p=0.5 -> all entropy=1.0."""
        board_size = 3
        ownership = [0.0] * (board_size * board_size)
        grid = compute_entropy_grid(ownership, board_size)
        for row in grid:
            for val in row:
                assert val == pytest.approx(1.0)

    def test_grid_dimensions(self) -> None:
        board_size = 9
        ownership = [0.5] * (board_size * board_size)
        grid = compute_entropy_grid(ownership, board_size)
        assert len(grid) == 9
        assert all(len(row) == 9 for row in grid)


# ---------------------------------------------------------------------------
# T15.3: compute_entropy_roi with mixed ownership
# ---------------------------------------------------------------------------


class TestComputeEntropyRoi:
    def test_identifies_contested_region(self) -> None:
        """Board with a contested corner and clear rest."""
        board_size = 5
        # All black-owned except top-left 2x2 which is contested
        ownership = [1.0] * (board_size * board_size)
        for r in range(2):
            for c in range(2):
                ownership[r * board_size + c] = 0.0  # contested

        roi = compute_entropy_roi(ownership, board_size, threshold=0.5)
        assert isinstance(roi, EntropyROI)
        assert len(roi.contested_region) == 4  # 2x2 area
        assert roi.bounding_box == (0, 0, 1, 1)

    def test_no_contested_region(self) -> None:
        """Fully decided board -> no contested intersections."""
        board_size = 3
        ownership = [1.0] * (board_size * board_size)
        roi = compute_entropy_roi(ownership, board_size, threshold=0.5)
        assert len(roi.contested_region) == 0
        # Fallback bbox is full board
        assert roi.bounding_box == (0, 0, 2, 2)

    def test_mean_entropy(self) -> None:
        """All contested -> mean entropy = 1.0."""
        board_size = 3
        ownership = [0.0] * 9
        roi = compute_entropy_roi(ownership, board_size)
        assert roi.mean_entropy == pytest.approx(1.0)

    def test_gtp_coordinates_format(self) -> None:
        """Contested coords should be GTP format like 'A5'."""
        board_size = 5
        ownership = [1.0] * 25
        ownership[0] = 0.0  # row=0, col=0 -> A5
        roi = compute_entropy_roi(ownership, board_size, threshold=0.5)
        assert "A5" in roi.contested_region


# ---------------------------------------------------------------------------
# T15.4: get_roi_allow_moves expansion
# ---------------------------------------------------------------------------


class TestGetRoiAllowMoves:
    def test_basic_expansion(self) -> None:
        roi = EntropyROI(
            entropy_grid=[],
            contested_region=["C3"],
            bounding_box=(2, 2, 2, 2),  # single point: row=2, col=2
            mean_entropy=0.8,
        )
        moves = get_roi_allow_moves(roi, board_size=5, margin=1)
        # Expanded from (2,2,2,2) to (1,1,3,3) -> 3x3 = 9 moves
        assert len(moves) == 9

    def test_margin_zero(self) -> None:
        roi = EntropyROI(
            entropy_grid=[],
            contested_region=["C3"],
            bounding_box=(2, 2, 2, 2),
            mean_entropy=0.8,
        )
        moves = get_roi_allow_moves(roi, board_size=5, margin=0)
        assert len(moves) == 1

    def test_clamps_to_board(self) -> None:
        """Expansion should not go beyond board edges."""
        roi = EntropyROI(
            entropy_grid=[],
            contested_region=["A5"],
            bounding_box=(0, 0, 0, 0),
            mean_entropy=0.8,
        )
        moves = get_roi_allow_moves(roi, board_size=5, margin=3)
        # Clamped: (0,0) to (3,3) -> 4x4 = 16 moves
        assert len(moves) == 16

    def test_larger_roi(self) -> None:
        roi = EntropyROI(
            entropy_grid=[],
            contested_region=["A5", "B5", "A4", "B4"],
            bounding_box=(0, 0, 1, 1),
            mean_entropy=0.9,
        )
        moves = get_roi_allow_moves(roi, board_size=5, margin=1)
        # Expanded from (0,0,1,1) to (0,0,2,2) -> 3x3 = 9
        assert len(moves) == 9

    def test_occupied_coords_excluded(self) -> None:
        """Occupied intersections should be omitted from allowMoves."""
        roi = EntropyROI(
            entropy_grid=[],
            contested_region=["C3"],
            bounding_box=(2, 2, 2, 2),
            mean_entropy=0.8,
        )
        # Without occupied: 3x3 = 9 moves (margin=1)
        all_moves = get_roi_allow_moves(roi, board_size=5, margin=1)
        assert len(all_moves) == 9
        # Occupy 2 intersections within the expanded ROI
        occupied = frozenset({(2, 2), (1, 1)})
        filtered_moves = get_roi_allow_moves(
            roi, board_size=5, margin=1, occupied=occupied,
        )
        assert len(filtered_moves) == 7
        # GTP coords for (col=2,row=2)=C3 and (col=1,row=1)=B4 should be absent
        assert "C3" not in filtered_moves
        assert "B4" not in filtered_moves


# ---------------------------------------------------------------------------
# T15.5: validate_frame_quality
# ---------------------------------------------------------------------------


class TestValidateFrameQuality:
    def test_low_variance_valid(self) -> None:
        """Uniform ownership -> variance ~0 -> valid."""
        ownership = [0.9] * 25
        is_valid, var = validate_frame_quality(ownership, board_size=5)
        assert is_valid is True
        assert var == pytest.approx(0.0, abs=0.01)

    def test_high_variance_invalid(self) -> None:
        """Mixed ownership -> high variance -> invalid."""
        # Half at +1, half at -1 -> variance = 1.0
        ownership = [1.0] * 13 + [-1.0] * 12
        is_valid, var = validate_frame_quality(
            ownership, board_size=5, variance_threshold=0.15,
        )
        assert is_valid is False
        assert var > 0.15

    def test_custom_threshold(self) -> None:
        ownership = [0.8] * 10 + [-0.8] * 15
        _, var = validate_frame_quality(ownership, board_size=5)
        # With a very high threshold, should pass
        is_valid_high, _ = validate_frame_quality(
            ownership, board_size=5, variance_threshold=2.0,
        )
        assert is_valid_high is True

    def test_empty_ownership(self) -> None:
        is_valid, var = validate_frame_quality([], board_size=5)
        assert is_valid is True
        assert var == 0.0


# ---------------------------------------------------------------------------
# T15.6: get_allow_moves_with_fallback
# ---------------------------------------------------------------------------


class TestGetAllowMovesWithFallback:
    def _make_position(self) -> Position:  # noqa: F821
        """Create a minimal Position with a few stones for testing."""
        from models.position import Color, Position, Stone
        return Position(
            board_size=9,
            stones=[
                Stone(x=2, y=2, color=Color.BLACK),
                Stone(x=3, y=3, color=Color.WHITE),
            ],
            player_to_move=Color.BLACK,
        )

    def test_with_entropy_roi(self) -> None:
        pos = self._make_position()
        roi = EntropyROI(
            entropy_grid=[],
            contested_region=["C7", "D7"],
            bounding_box=(2, 2, 2, 3),
            mean_entropy=0.8,
        )
        moves = get_allow_moves_with_fallback(pos, entropy_roi=roi, margin=1)
        # Should use ROI, not bounding box
        assert len(moves) > 0
        # All moves should be GTP format
        assert all(isinstance(m, str) and len(m) >= 2 for m in moves)

    def test_without_roi_uses_fallback(self) -> None:
        pos = self._make_position()
        moves = get_allow_moves_with_fallback(pos, entropy_roi=None, margin=2)
        # Should use position's bounding box fallback
        assert len(moves) > 0

    def test_empty_contested_region_uses_fallback(self) -> None:
        pos = self._make_position()
        roi = EntropyROI(
            entropy_grid=[],
            contested_region=[],
            bounding_box=(0, 0, 8, 8),
            mean_entropy=0.1,
        )
        moves = get_allow_moves_with_fallback(pos, entropy_roi=roi, margin=2)
        # Empty contested_region should trigger fallback
        assert len(moves) > 0
