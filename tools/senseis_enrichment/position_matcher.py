"""Position matching using rotation/reflection-invariant canonical hashing.

Uses the D4 symmetry group (4 rotations x 2 reflections = 8 transforms) to
match positions that may be presented in different board orientations.

The generic D4 transform functions live in tools.core.position_transform.
This module provides the Senseis-specific match_positions() workflow and
re-exports the core functions for backward compatibility.
"""

from __future__ import annotations

import logging

from tools.core.position_transform import (
    canonical_position_hash,
    find_transform,
    inverse_transform,
    transform_point,
)
from tools.core.sgf_parser import SgfTree, parse_sgf
from tools.core.sgf_types import PositionTransform

from tools.senseis_enrichment.models import MatchResult

logger = logging.getLogger("senseis_enrichment.position_matcher")

# Re-exports for backward compatibility
__all__ = [
    "canonical_position_hash",
    "find_transform",
    "inverse_transform",
    "transform_point",
    "match_positions",
]


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
    local_hash, _ = canonical_position_hash(
        local_tree.black_stones, local_tree.white_stones, local_tree.board_size
    )
    senseis_hash, _ = canonical_position_hash(
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
