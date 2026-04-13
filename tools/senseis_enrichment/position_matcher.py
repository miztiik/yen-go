"""Position matching using rotation/reflection-invariant canonical hashing.

Uses the D4 symmetry group (4 rotations x 2 reflections = 8 transforms) to
match positions that may be presented in different board orientations.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass

from tools.core.sgf_parser import SgfTree, parse_sgf
from tools.core.sgf_types import Point

from tools.senseis_enrichment.models import MatchResult, PositionTransform

logger = logging.getLogger("senseis_enrichment.position_matcher")


def _transform_point(
    p: Point, board_size: int, rotation: int, reflect: bool
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
) -> tuple[str, int, bool]:
    """Compute the canonical (minimum) position hash across all 8 D4 symmetries.

    Returns:
        (hash_hex_16, rotation_degrees, reflected) — the hash and the transform
        that produced the minimum.
    """
    best_hash: str | None = None
    best_rotation = 0
    best_reflect = False

    for rotation in (0, 90, 180, 270):
        for reflect in (False, True):
            canonical = _position_canonical_string(
                black_stones, white_stones, board_size, rotation, reflect
            )
            h = hashlib.sha256(canonical.encode()).hexdigest()[:16]

            if best_hash is None or h < best_hash:
                best_hash = h
                best_rotation = rotation
                best_reflect = reflect

    return best_hash or "", best_rotation, best_reflect


def _inverse_transform(rotation: int, reflect: bool) -> tuple[int, bool]:
    """Compute the inverse of a (rotation, reflect) transform.

    For D4 group: if we applied (rot, ref) to get canonical form,
    the inverse maps canonical back to original.
    """
    if reflect:
        # Reflect is self-inverse, but combined with rotation:
        # (rot, reflect) inverse = (rot, reflect) because:
        # reflect . rot^-1 = reflect . rot(360-rot)
        # Actually: inverse of "rotate then reflect" = "reflect then rotate_inverse"
        # = "reflect then rotate(360-rotation)"
        # Since reflect.reflect = identity and we need to express as (rot', ref'):
        # The inverse of (R, reflect) in standard form (rotate then reflect):
        # T = reflect . R   =>  T^-1 = R^-1 . reflect = R(360-rotation) . reflect
        # To express as (rot', reflect'): rot' = (360-rotation) % 360, reflect' = True
        return (360 - rotation) % 360, True
    else:
        # Inverse of rotation only is simply the opposite rotation
        return (360 - rotation) % 360, False


def find_transform(
    source_black: list[Point],
    source_white: list[Point],
    target_black: list[Point],
    target_white: list[Point],
    board_size: int,
) -> PositionTransform | None:
    """Find the transform that maps source position to target position.

    Tries all 8 D4 symmetries of the source and checks if any matches target.

    Returns:
        PositionTransform if found, None if positions don't match.
    """
    # Compute target canonical string (identity transform)
    target_canonical = _position_canonical_string(
        target_black, target_white, board_size, 0, False
    )

    for rotation in (0, 90, 180, 270):
        for reflect in (False, True):
            source_canonical = _position_canonical_string(
                source_black, source_white, board_size, rotation, reflect
            )
            if source_canonical == target_canonical:
                return PositionTransform(rotation=rotation, reflect=reflect)

    return None


def transform_point(
    p: Point, board_size: int, transform: PositionTransform
) -> Point:
    """Apply a PositionTransform to a point."""
    return _transform_point(p, board_size, transform.rotation, transform.reflect)


def match_positions(
    local_tree: SgfTree,
    senseis_sgf_content: str,
    problem_number: int,
) -> MatchResult:
    """Match a local SGF against a Senseis diagram SGF.

    Determines if the positions are the same (modulo D4 symmetry) and
    returns the transform needed to map Senseis coords to local coords.
    """
    result = MatchResult(problem_number=problem_number)

    # Parse the Senseis SGF
    try:
        senseis_tree = parse_sgf(senseis_sgf_content)
    except Exception as e:
        result.detail = f"Failed to parse Senseis SGF: {e}"
        return result

    # Compute canonical hashes
    local_hash, _, _ = canonical_position_hash(
        local_tree.black_stones, local_tree.white_stones, local_tree.board_size
    )
    senseis_hash, _, _ = canonical_position_hash(
        senseis_tree.black_stones, senseis_tree.white_stones, senseis_tree.board_size
    )

    result.local_hash = local_hash
    result.senseis_hash = senseis_hash

    if local_hash != senseis_hash:
        result.detail = (
            f"Position hash mismatch: local={local_hash}, senseis={senseis_hash}"
        )
        return result

    # Positions match — find the specific transform (Senseis → Local)
    transform = find_transform(
        source_black=senseis_tree.black_stones,
        source_white=senseis_tree.white_stones,
        target_black=local_tree.black_stones,
        target_white=local_tree.white_stones,
        board_size=local_tree.board_size,
    )

    if transform is None:
        result.detail = "Canonical hashes match but exact transform not found (unexpected)"
        return result

    result.matched = True
    result.transform = transform
    result.detail = f"Matched with rotation={transform.rotation}, reflect={transform.reflect}"
    return result
