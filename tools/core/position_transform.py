"""D4 symmetry transforms for Go board positions.

Provides rotation/reflection-invariant canonical hashing using the D4
symmetry group (4 rotations x 2 reflections = 8 transforms).

Promoted from tools/senseis_enrichment/position_matcher.py to be a shared
core capability available to all tools.

Usage:
    from tools.core.sgf_types import Point, PositionTransform
    from tools.core.position_transform import (
        transform_point,
        canonical_position_hash,
        find_transform,
        transform_node,
    )

    # Find if two positions are the same modulo rotation/reflection
    hash_a, _ = canonical_position_hash(black_a, white_a, 19)
    hash_b, _ = canonical_position_hash(black_b, white_b, 19)
    if hash_a == hash_b:
        t = find_transform(black_a, white_a, black_b, white_b, 19)
        # t maps source A coords → target B coords
"""

from __future__ import annotations

import hashlib
from copy import deepcopy

from tools.core.sgf_parser import SgfNode
from tools.core.sgf_types import Point, PositionTransform


# ---------------------------------------------------------------------------
# Point transform
# ---------------------------------------------------------------------------


def _transform_point(
    p: Point, board_size: int, rotation: int, reflect: bool,
) -> Point:
    """Apply rotation then optional horizontal reflection.

    Args:
        p: Original point.
        board_size: Board size (e.g. 19).
        rotation: Degrees clockwise (0, 90, 180, 270).
        reflect: If True, reflect horizontally after rotation.

    Returns:
        Transformed point.
    """
    n = board_size - 1
    x, y = p.x, p.y

    if rotation == 90:
        x, y = n - y, x
    elif rotation == 180:
        x, y = n - x, n - y
    elif rotation == 270:
        x, y = y, n - x

    if reflect:
        x = n - x

    return Point(x, y)


def transform_point(
    p: Point, board_size: int, transform: PositionTransform,
) -> Point:
    """Apply a PositionTransform to a single point.

    Args:
        p: Original point.
        board_size: Board size.
        transform: D4 transform to apply.

    Returns:
        Transformed point.
    """
    return _transform_point(p, board_size, transform.rotation, transform.reflect)


# ---------------------------------------------------------------------------
# Inverse transform
# ---------------------------------------------------------------------------


def inverse_transform(transform: PositionTransform) -> PositionTransform:
    """Compute the inverse of a D4 transform.

    Applying the original transform then its inverse yields the identity.

    In the D4 group, all reflective elements (s·r^k) are involutions
    (self-inverse), so their inverse is themselves. Pure rotations
    invert to the opposite rotation.

    Args:
        transform: Transform to invert.

    Returns:
        The inverse PositionTransform.
    """
    if transform.reflect:
        # All reflective transforms are self-inverse (order 2 in D4).
        # Proof: T(x,y) applies rotation then horizontal flip.
        # Applying T twice returns to the original point.
        return transform
    else:
        # Inverse of rotation-only is the opposite rotation
        return PositionTransform(
            rotation=(360 - transform.rotation) % 360,
            reflect=False,
        )


# ---------------------------------------------------------------------------
# Canonical position hashing
# ---------------------------------------------------------------------------


def _position_canonical_string(
    black_stones: list[Point],
    white_stones: list[Point],
    board_size: int,
    rotation: int,
    reflect: bool,
) -> str:
    """Compute a canonical string for a position under a specific transform."""
    b_transformed = sorted(
        _transform_point(p, board_size, rotation, reflect).to_sgf()
        for p in black_stones
    )
    w_transformed = sorted(
        _transform_point(p, board_size, rotation, reflect).to_sgf()
        for p in white_stones
    )
    return f"SZ{board_size}:B[{','.join(b_transformed)}]:W[{','.join(w_transformed)}]"


def canonical_position_hash(
    black_stones: list[Point],
    white_stones: list[Point],
    board_size: int,
) -> tuple[str, PositionTransform]:
    """Compute the canonical (minimum) position hash across all 8 D4 symmetries.

    The canonical hash is the lexicographically smallest SHA256 prefix across
    all 8 transforms. Two positions that differ only by rotation/reflection
    will produce the same canonical hash.

    Args:
        black_stones: Black setup stones.
        white_stones: White setup stones.
        board_size: Board size.

    Returns:
        (hash_hex_16, transform) — the hash and the transform that produced
        the minimum.
    """
    best_hash: str | None = None
    best_transform = PositionTransform()

    for rotation in (0, 90, 180, 270):
        for reflect in (False, True):
            canonical = _position_canonical_string(
                black_stones, white_stones, board_size, rotation, reflect,
            )
            h = hashlib.sha256(canonical.encode()).hexdigest()[:16]

            if best_hash is None or h < best_hash:
                best_hash = h
                best_transform = PositionTransform(rotation=rotation, reflect=reflect)

    return best_hash or "", best_transform


# ---------------------------------------------------------------------------
# Transform discovery
# ---------------------------------------------------------------------------


def find_transform(
    source_black: list[Point],
    source_white: list[Point],
    target_black: list[Point],
    target_white: list[Point],
    board_size: int,
) -> PositionTransform | None:
    """Find the D4 transform that maps source position to target position.

    Tries all 8 D4 symmetries of the source and checks if any matches the
    target's identity canonical string.

    Args:
        source_black: Source black stones.
        source_white: Source white stones.
        target_black: Target black stones.
        target_white: Target white stones.
        board_size: Board size.

    Returns:
        PositionTransform if an exact match is found, None otherwise.
    """
    target_canonical = _position_canonical_string(
        target_black, target_white, board_size, 0, False,
    )

    for rotation in (0, 90, 180, 270):
        for reflect in (False, True):
            source_canonical = _position_canonical_string(
                source_black, source_white, board_size, rotation, reflect,
            )
            if source_canonical == target_canonical:
                return PositionTransform(rotation=rotation, reflect=reflect)

    return None


# ---------------------------------------------------------------------------
# Node tree transform
# ---------------------------------------------------------------------------


def transform_node(
    node: SgfNode, board_size: int, transform: PositionTransform,
) -> SgfNode:
    """Deep-copy an SgfNode tree, transforming all move coordinates.

    Recursively copies the node tree, applying the transform to every move
    Point and to coordinate-bearing properties (LB, TR, SQ, CR, MA, AB, AW).

    Comments are preserved verbatim (coordinate references in text are NOT
    transformed — that would be fragile and error-prone).

    Args:
        node: Root node to transform (not mutated).
        board_size: Board size.
        transform: D4 transform to apply.

    Returns:
        A new SgfNode tree with transformed coordinates.
    """
    if transform.is_identity:
        return deepcopy(node)

    return _transform_node_recursive(node, board_size, transform)


_COORDINATE_PROPERTIES = frozenset({
    "AB", "AW", "AE",  # setup stones
    "TR", "SQ", "CR", "MA",  # markup
    "TB", "TW",  # territory
    "DD", "VW",  # dim/view
})

_LABEL_PROPERTIES = frozenset({"LB"})


def _transform_node_recursive(
    node: SgfNode, board_size: int, transform: PositionTransform,
) -> SgfNode:
    """Recursively transform a node and all its children."""
    # Transform move coordinate
    new_move = None
    if node.move is not None:
        new_move = transform_point(node.move, board_size, transform)

    # Transform coordinate-bearing properties
    new_props: dict[str, str] = {}
    for key, value in node.properties.items():
        if key in _COORDINATE_PROPERTIES:
            new_props[key] = _transform_coord_property(value, board_size, transform)
        elif key in _LABEL_PROPERTIES:
            new_props[key] = _transform_label_property(value, board_size, transform)
        else:
            new_props[key] = value

    new_node = SgfNode(
        move=new_move,
        color=node.color,
        comment=node.comment,
        is_correct=node.is_correct,
        children=[],
        properties=new_props,
    )

    for child in node.children:
        new_node.children.append(
            _transform_node_recursive(child, board_size, transform)
        )

    return new_node


def _transform_coord_property(
    value: str, board_size: int, transform: PositionTransform,
) -> str:
    """Transform a comma-separated coordinate property value.

    E.g., "cd,ef,gh" → transformed coordinates.
    """
    if not value:
        return value
    parts = value.split(",")
    transformed = []
    for part in parts:
        part = part.strip()
        if len(part) == 2 and part.isalpha():
            p = Point.from_sgf(part)
            tp = transform_point(p, board_size, transform)
            transformed.append(tp.to_sgf())
        else:
            transformed.append(part)
    return ",".join(transformed)


def _transform_label_property(
    value: str, board_size: int, transform: PositionTransform,
) -> str:
    """Transform a label property value.

    Labels have format "coord:text" (e.g., "cd:A,ef:B").
    """
    if not value:
        return value
    parts = value.split(",")
    transformed = []
    for part in parts:
        if ":" in part:
            coord, label = part.split(":", 1)
            coord = coord.strip()
            if len(coord) == 2 and coord.isalpha():
                p = Point.from_sgf(coord)
                tp = transform_point(p, board_size, transform)
                transformed.append(f"{tp.to_sgf()}:{label}")
            else:
                transformed.append(part)
        else:
            transformed.append(part)
    return ",".join(transformed)
