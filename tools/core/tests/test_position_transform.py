"""Tests for tools.core.position_transform."""

import pytest

from tools.core.position_transform import (
    canonical_position_hash,
    find_transform,
    inverse_transform,
    transform_node,
    transform_point,
)
from tools.core.sgf_parser import SgfNode, parse_sgf
from tools.core.sgf_types import Point, PositionTransform


# ---------------------------------------------------------------------------
# transform_point — all 8 D4 symmetries
# ---------------------------------------------------------------------------


class TestTransformPoint:
    """Test point transformation through all 8 D4 symmetries on 19x19."""

    # Point (2, 3) on 19x19 board (n=18)
    P = Point(2, 3)
    BS = 19

    def test_identity(self):
        t = PositionTransform(rotation=0, reflect=False)
        assert transform_point(self.P, self.BS, t) == Point(2, 3)

    def test_rotate_90(self):
        t = PositionTransform(rotation=90, reflect=False)
        # (x,y) -> (n-y, x) = (18-3, 2) = (15, 2)
        assert transform_point(self.P, self.BS, t) == Point(15, 2)

    def test_rotate_180(self):
        t = PositionTransform(rotation=180, reflect=False)
        # (x,y) -> (n-x, n-y) = (16, 15)
        assert transform_point(self.P, self.BS, t) == Point(16, 15)

    def test_rotate_270(self):
        t = PositionTransform(rotation=270, reflect=False)
        # (x,y) -> (y, n-x) = (3, 16)
        assert transform_point(self.P, self.BS, t) == Point(3, 16)

    def test_reflect_only(self):
        t = PositionTransform(rotation=0, reflect=True)
        # (x,y) -> (n-x, y) = (16, 3)
        assert transform_point(self.P, self.BS, t) == Point(16, 3)

    def test_rotate_90_reflect(self):
        t = PositionTransform(rotation=90, reflect=True)
        # rotate 90: (15, 2), then reflect: (18-15, 2) = (3, 2)
        assert transform_point(self.P, self.BS, t) == Point(3, 2)

    def test_rotate_180_reflect(self):
        t = PositionTransform(rotation=180, reflect=True)
        # rotate 180: (16, 15), then reflect: (18-16, 15) = (2, 15)
        assert transform_point(self.P, self.BS, t) == Point(2, 15)

    def test_rotate_270_reflect(self):
        t = PositionTransform(rotation=270, reflect=True)
        # rotate 270: (3, 16), then reflect: (18-3, 16) = (15, 16)
        assert transform_point(self.P, self.BS, t) == Point(15, 16)

    def test_9x9_board(self):
        """Verify transforms work on smaller boards."""
        p = Point(1, 2)
        t = PositionTransform(rotation=90, reflect=False)
        # n=8: (8-2, 1) = (6, 1)
        assert transform_point(p, 9, t) == Point(6, 1)


# ---------------------------------------------------------------------------
# canonical_position_hash — rotation invariance
# ---------------------------------------------------------------------------


class TestCanonicalPositionHash:
    """Verify canonical hash is invariant under all 8 D4 symmetries."""

    BLACK = [Point(2, 3), Point(4, 5)]
    WHITE = [Point(10, 11)]
    BS = 19

    def _rotated_position(self, rotation: int, reflect: bool):
        """Apply a transform to the test position."""
        t = PositionTransform(rotation=rotation, reflect=reflect)
        b = [transform_point(p, self.BS, t) for p in self.BLACK]
        w = [transform_point(p, self.BS, t) for p in self.WHITE]
        return b, w

    def test_all_symmetries_same_hash(self):
        """All 8 rotations/reflections of the same position produce the same hash."""
        base_hash, _ = canonical_position_hash(self.BLACK, self.WHITE, self.BS)

        for rotation in (0, 90, 180, 270):
            for reflect in (False, True):
                b, w = self._rotated_position(rotation, reflect)
                h, _ = canonical_position_hash(b, w, self.BS)
                assert h == base_hash, (
                    f"Hash mismatch for rotation={rotation}, reflect={reflect}"
                )

    def test_different_position_different_hash(self):
        """Genuinely different positions produce different hashes."""
        h1, _ = canonical_position_hash(self.BLACK, self.WHITE, self.BS)
        h2, _ = canonical_position_hash(
            [Point(0, 0), Point(1, 1)], [Point(2, 2)], self.BS,
        )
        assert h1 != h2

    def test_returns_transform(self):
        """Canonical hash returns the transform that produced the minimum."""
        _, t = canonical_position_hash(self.BLACK, self.WHITE, self.BS)
        assert isinstance(t, PositionTransform)
        assert t.rotation in (0, 90, 180, 270)
        assert isinstance(t.reflect, bool)


# ---------------------------------------------------------------------------
# find_transform
# ---------------------------------------------------------------------------


class TestFindTransform:
    """Test exact transform discovery between two positions."""

    BLACK = [Point(2, 3), Point(4, 5), Point(6, 7)]
    WHITE = [Point(10, 11), Point(12, 13)]
    BS = 19

    def test_identity(self):
        """Same position → identity transform."""
        t = find_transform(self.BLACK, self.WHITE, self.BLACK, self.WHITE, self.BS)
        assert t is not None
        assert t.is_identity

    def test_rotated_90(self):
        """Position rotated 90° → finds the correct transform."""
        rot = PositionTransform(rotation=90, reflect=False)
        target_b = [transform_point(p, self.BS, rot) for p in self.BLACK]
        target_w = [transform_point(p, self.BS, rot) for p in self.WHITE]

        t = find_transform(self.BLACK, self.WHITE, target_b, target_w, self.BS)
        assert t is not None
        assert t.rotation == 90
        assert t.reflect is False

    def test_reflected(self):
        """Horizontally reflected position → finds the correct transform."""
        ref = PositionTransform(rotation=0, reflect=True)
        target_b = [transform_point(p, self.BS, ref) for p in self.BLACK]
        target_w = [transform_point(p, self.BS, ref) for p in self.WHITE]

        t = find_transform(self.BLACK, self.WHITE, target_b, target_w, self.BS)
        assert t is not None
        assert t.reflect is True

    def test_no_match(self):
        """Genuinely different positions → None."""
        other_b = [Point(0, 0), Point(1, 1), Point(2, 2)]
        other_w = [Point(15, 15), Point(16, 16)]
        t = find_transform(self.BLACK, self.WHITE, other_b, other_w, self.BS)
        assert t is None

    def test_different_stone_count_no_match(self):
        """Different number of stones → None."""
        t = find_transform(
            self.BLACK, self.WHITE,
            self.BLACK[:2], self.WHITE,
            self.BS,
        )
        assert t is None


# ---------------------------------------------------------------------------
# inverse_transform
# ---------------------------------------------------------------------------


class TestInverseTransform:
    """Test inverse transform round-trips."""

    P = Point(5, 7)
    BS = 19

    @pytest.mark.parametrize("rotation,reflect", [
        (0, False), (90, False), (180, False), (270, False),
        (0, True), (90, True), (180, True), (270, True),
    ])
    def test_round_trip(self, rotation, reflect):
        """Applying transform then its inverse returns the original point."""
        t = PositionTransform(rotation=rotation, reflect=reflect)
        inv = inverse_transform(t)

        transformed = transform_point(self.P, self.BS, t)
        restored = transform_point(transformed, self.BS, inv)
        assert restored == self.P, (
            f"Round-trip failed for rotation={rotation}, reflect={reflect}: "
            f"{self.P} → {transformed} → {restored}"
        )


# ---------------------------------------------------------------------------
# transform_node
# ---------------------------------------------------------------------------


class TestTransformNode:
    """Test solution tree coordinate transformation."""

    SGF = "(;SZ[19]AB[cd][ce]AW[dd][de]PL[B](;B[cf]C[correct])(;B[df]C[wrong]))"

    def test_identity_preserves_tree(self):
        """Identity transform produces a deep copy with same coordinates."""
        tree = parse_sgf(self.SGF)
        t = PositionTransform()
        result = transform_node(tree.solution_tree, 19, t)

        # Same structure
        assert len(result.children) == len(tree.solution_tree.children)
        for orig, copy in zip(tree.solution_tree.children, result.children):
            assert orig.move == copy.move
            assert orig.comment == copy.comment
            assert orig.is_correct == copy.is_correct

        # Deep copy — not the same object
        assert result is not tree.solution_tree

    def test_rotate_180_transforms_moves(self):
        """180° rotation transforms move coordinates."""
        tree = parse_sgf(self.SGF)
        t = PositionTransform(rotation=180, reflect=False)
        result = transform_node(tree.solution_tree, 19, t)

        # Original first move: B[cf] = Point(2, 5)
        # Rotated 180°: (18-2, 18-5) = (16, 13) = "qn"
        first_child = result.children[0]
        assert first_child.move == Point(16, 13)
        assert first_child.comment == "correct"
        assert first_child.color is not None

    def test_preserves_comments(self):
        """Comments are preserved verbatim (not coordinate-transformed)."""
        tree = parse_sgf(self.SGF)
        t = PositionTransform(rotation=90, reflect=True)
        result = transform_node(tree.solution_tree, 19, t)

        comments = [c.comment for c in result.children]
        assert "correct" in comments
        assert "wrong" in comments

    def test_preserves_correctness(self):
        """is_correct flags are preserved."""
        tree = parse_sgf(self.SGF)
        t = PositionTransform(rotation=90, reflect=False)
        result = transform_node(tree.solution_tree, 19, t)

        orig_flags = [c.is_correct for c in tree.solution_tree.children]
        new_flags = [c.is_correct for c in result.children]
        assert orig_flags == new_flags


# ---------------------------------------------------------------------------
# PositionTransform dataclass
# ---------------------------------------------------------------------------


class TestPositionTransformDataclass:
    """Test the PositionTransform value object."""

    def test_is_identity(self):
        assert PositionTransform().is_identity
        assert PositionTransform(0, False).is_identity
        assert not PositionTransform(90, False).is_identity
        assert not PositionTransform(0, True).is_identity

    def test_frozen(self):
        t = PositionTransform(90, True)
        with pytest.raises(AttributeError):
            t.rotation = 0  # type: ignore[misc]

    def test_round_trip_serialization(self):
        t = PositionTransform(270, True)
        d = t.to_dict()
        assert d == {"rotation": 270, "reflect": True}
        restored = PositionTransform.from_dict(d)
        assert restored == t
