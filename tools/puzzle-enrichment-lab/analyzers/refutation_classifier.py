"""Wrong-move refutation classifier — classifies refutation outcomes.

Examines each wrong-move branch using engine PV data and solution tree
structure, classifying the outcome into one of 8 conditions ordered by
priority (first-match-wins, GOV-V2-03). Selects top 3 for causal
annotation (GOV-V2-04), ranked by refutation depth.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# Priority-ordered conditions (GOV-V2-03)
CONDITION_PRIORITY = [
    "immediate_capture",
    "opponent_escapes",
    "opponent_lives",
    "capturing_race_lost",
    "opponent_takes_vital",
    "opponent_reduces_liberties",
    "self_atari",
    "shape_death_alias",
    "ko_involved",
    "wrong_direction",
    "default",
]


@dataclass
class ClassifiedRefutation:
    """A wrong move with its classified refutation condition.

    The ``refutation_type`` field is propagated from the upstream
    ``RefutationEntry`` so that downstream consumers (e.g.
    ``teaching_comments.py``) can distinguish curated wrong moves
    (authored by the puzzle creator) from AI-generated ones.
    This is critical for the almost-correct gate: curated wrongs
    should never be labelled "Close" even when KataGo's delta
    is below the threshold — the puzzle author's judgment takes
    precedence.
    """
    wrong_move: str           # SGF coordinate
    condition: str            # One of CONDITION_PRIORITY
    refutation_depth: int     # Depth of refutation PV
    refutation_coord: str     # Key coordinate for template substitution
    alias: str                # Alias name for shape_death_alias condition
    delta: float              # Winrate delta
    refutation_type: str = ""  # "curated", "ai_generated", "score_based", or ""


@dataclass
class ClassificationResult:
    """Result of classifying all wrong moves for a puzzle."""
    causal: list[ClassifiedRefutation] = field(default_factory=list)  # Top N with non-default conditions
    default_moves: list[ClassifiedRefutation] = field(default_factory=list)  # Remaining with default


def _check_immediate_capture(ref: dict[str, Any]) -> bool:
    """PV depth ≤ 1 and capture verified."""
    depth = ref.get("refutation_depth", 0)
    pv_truncated = ref.get("pv_truncated", False)
    capture_verified = ref.get("capture_verified", False)
    return not pv_truncated and depth <= 1 and capture_verified


def _check_opponent_escapes(ref: dict[str, Any]) -> bool:
    """Refutation PV shows escape sequence."""
    return ref.get("escape_detected", False)


def _check_opponent_lives(ref: dict[str, Any]) -> bool:
    """Ownership flip: dead→alive in refutation."""
    return ref.get("opponent_lives", False)


def _check_capturing_race_lost(ref: dict[str, Any]) -> bool:
    """Liberty comparison in refutation."""
    return ref.get("capturing_race_lost", False)


def _check_opponent_takes_vital(
    ref: dict[str, Any], correct_first_coord: str
) -> bool:
    """Refutation PV[0] == correct first move coordinate."""
    pv = ref.get("refutation_pv", [])
    if pv and correct_first_coord:
        return pv[0] == correct_first_coord
    return False


def _check_shape_death_alias(
    ref: dict[str, Any], technique_tags: list[str], alias: str | None
) -> bool:
    """Tag = dead-shapes + alias match."""
    return "dead-shapes" in technique_tags and bool(alias)


def _check_ko_involved(ref: dict[str, Any]) -> bool:
    """Ko detected in PV."""
    refutation_type = ref.get("refutation_type", "")
    return "ko" in refutation_type.lower() or ref.get("ko_detected", False)


def _check_opponent_reduces_liberties(ref: dict[str, Any]) -> bool:
    """Refutation PV shows liberty reduction (but not immediate capture)."""
    return ref.get("liberty_reduction", False) and not ref.get("capture_verified", False)


def _check_self_atari(ref: dict[str, Any]) -> bool:
    """Wrong move puts own stones in atari."""
    return ref.get("self_atari", False)


def _check_wrong_direction(ref: dict[str, Any]) -> bool:
    """Move is far from the vital area."""
    return ref.get("wrong_direction", False)


def classify_refutation(
    ref: dict[str, Any],
    correct_first_coord: str,
    technique_tags: list[str],
    alias: str | None = None,
    min_depth_for_causal: int = 0,
) -> ClassifiedRefutation:
    """Classify a single wrong-move refutation.

    Args:
        ref: Refutation dict with engine PV data.
        correct_first_coord: SGF coordinate of the correct first move.
        technique_tags: List of technique tag slugs.
        alias: Alias name if applicable.
        min_depth_for_causal: Minimum refutation depth for non-default classification.

    Returns:
        ClassifiedRefutation with the highest-priority matching condition.
    """
    wrong_move = ref.get("wrong_move", "")
    depth = ref.get("refutation_depth", 0)
    delta = ref.get("delta", 0.0)
    pv = ref.get("refutation_pv", [])
    refutation_coord = pv[0] if pv else ""
    ref_type = ref.get("refutation_type", "")

    # Guard: too shallow for causal
    if depth < min_depth_for_causal and min_depth_for_causal > 0:
        return ClassifiedRefutation(
            wrong_move=wrong_move, condition="default",
            refutation_depth=depth, refutation_coord=refutation_coord,
            alias="", delta=delta, refutation_type=ref_type,
        )

    # Priority scan (GOV-V2-03)
    if _check_immediate_capture(ref):
        return ClassifiedRefutation(
            wrong_move=wrong_move, condition="immediate_capture",
            refutation_depth=depth, refutation_coord=refutation_coord,
            alias="", delta=delta, refutation_type=ref_type,
        )

    if _check_opponent_escapes(ref):
        return ClassifiedRefutation(
            wrong_move=wrong_move, condition="opponent_escapes",
            refutation_depth=depth, refutation_coord=refutation_coord,
            alias="", delta=delta, refutation_type=ref_type,
        )

    if _check_opponent_lives(ref):
        return ClassifiedRefutation(
            wrong_move=wrong_move, condition="opponent_lives",
            refutation_depth=depth, refutation_coord=refutation_coord,
            alias="", delta=delta, refutation_type=ref_type,
        )

    if _check_capturing_race_lost(ref):
        return ClassifiedRefutation(
            wrong_move=wrong_move, condition="capturing_race_lost",
            refutation_depth=depth, refutation_coord=refutation_coord,
            alias="", delta=delta, refutation_type=ref_type,
        )

    if _check_opponent_takes_vital(ref, correct_first_coord):
        return ClassifiedRefutation(
            wrong_move=wrong_move, condition="opponent_takes_vital",
            refutation_depth=depth, refutation_coord=correct_first_coord,
            alias="", delta=delta, refutation_type=ref_type,
        )

    if _check_opponent_reduces_liberties(ref):
        return ClassifiedRefutation(
            wrong_move=wrong_move, condition="opponent_reduces_liberties",
            refutation_depth=depth, refutation_coord=refutation_coord,
            alias="", delta=delta, refutation_type=ref_type,
        )

    if _check_self_atari(ref):
        return ClassifiedRefutation(
            wrong_move=wrong_move, condition="self_atari",
            refutation_depth=depth, refutation_coord=refutation_coord,
            alias="", delta=delta, refutation_type=ref_type,
        )

    if _check_shape_death_alias(ref, technique_tags, alias):
        return ClassifiedRefutation(
            wrong_move=wrong_move, condition="shape_death_alias",
            refutation_depth=depth, refutation_coord=refutation_coord,
            alias=alias or "", delta=delta, refutation_type=ref_type,
        )

    if _check_ko_involved(ref):
        return ClassifiedRefutation(
            wrong_move=wrong_move, condition="ko_involved",
            refutation_depth=depth, refutation_coord=refutation_coord,
            alias="", delta=delta, refutation_type=ref_type,
        )

    if _check_wrong_direction(ref):
        return ClassifiedRefutation(
            wrong_move=wrong_move, condition="wrong_direction",
            refutation_depth=depth, refutation_coord=refutation_coord,
            alias="", delta=delta, refutation_type=ref_type,
        )

    return ClassifiedRefutation(
        wrong_move=wrong_move, condition="default",
        refutation_depth=depth, refutation_coord=refutation_coord,
        alias="", delta=delta, refutation_type=ref_type,
    )


def classify_all_refutations(
    refutations: list[dict[str, Any]],
    correct_first_coord: str,
    technique_tags: list[str],
    alias: str | None = None,
    max_causal: int = 3,
    min_depth_for_causal: int = 0,
) -> ClassificationResult:
    """Classify all wrong moves and select top N for causal annotation.

    Args:
        refutations: List of refutation dicts from engine analysis.
        correct_first_coord: SGF coordinate of the correct first move.
        technique_tags: List of technique tag slugs.
        alias: Alias name if applicable.
        max_causal: Maximum number of causal (non-default) annotations (GOV-V2-04).
        min_depth_for_causal: Minimum depth for causal classification.

    Returns:
        ClassificationResult with causal (top N) and default_moves.
    """
    classified = [
        classify_refutation(
            ref, correct_first_coord, technique_tags, alias, min_depth_for_causal
        )
        for ref in refutations
    ]

    # Separate causal vs default
    causal_candidates = [c for c in classified if c.condition != "default"]
    default_list = [c for c in classified if c.condition == "default"]

    # Sort causal by refutation depth descending (GOV-V2-04)
    causal_candidates.sort(key=lambda c: c.refutation_depth, reverse=True)

    # Take top N
    causal = causal_candidates[:max_causal]
    # Overflow causal → default
    overflow = causal_candidates[max_causal:]
    for item in overflow:
        default_list.append(ClassifiedRefutation(
            wrong_move=item.wrong_move, condition="default",
            refutation_depth=item.refutation_depth,
            refutation_coord=item.refutation_coord,
            alias="", delta=item.delta,
            refutation_type=item.refutation_type,
        ))

    return ClassificationResult(causal=causal, default_moves=default_list)
