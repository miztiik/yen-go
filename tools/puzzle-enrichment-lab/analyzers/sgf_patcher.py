"""Task A.5.2: SGF patcher — apply enrichment results to SGF properties.

Takes an original SGF string and an AiAnalysisResult, then patches
the SGF root node with enrichment properties:
  - YR: wrong-move SGF coords (comma-separated) from refutations
  - YG: difficulty level slug from difficulty estimation
  - YX: complexity metrics (d:depth;r:refutations;s:solution_length;u:unique)

Note: YQ (quality metrics) is deferred to Phase B.

Status-aware behavior:
  - ACCEPTED → overwrite all enrichment properties
  - FLAGGED → preserve existing human-curated properties (YG, YT, YH);
              still write engine-derived properties (YR, YX)
  - REJECTED → return original SGF unchanged

Uses core/sgf_parser.py (KaTrain-derived) for SGF parsing and property
manipulation — no regex for SGF property extraction or replacement.
"""

from __future__ import annotations

import logging

try:
    from core.sgf_parser import SGF as CoreSGF
    from models.ai_analysis_result import AiAnalysisResult

    from analyzers.sgf_parser import extract_solution_tree_moves, parse_sgf
    from analyzers.validate_correct_move import ValidationStatus
except ImportError:
    from ..core.sgf_parser import SGF as CoreSGF
    from ..analyzers.sgf_parser import extract_solution_tree_moves, parse_sgf
    from ..analyzers.validate_correct_move import ValidationStatus
    from ..models.ai_analysis_result import AiAnalysisResult

logger = logging.getLogger(__name__)

# Properties that are human-curated and should be preserved when FLAGGED
_HUMAN_CURATED_PROPS = {"YG", "YT", "YH"}

# Properties that are engine-derived and always written (even when FLAGGED)
_ENGINE_DERIVED_PROPS = {"YR", "YX"}


def patch_sgf(sgf_text: str, result: AiAnalysisResult) -> str:
    """Apply enrichment results to SGF root properties.

    Args:
        sgf_text: Original SGF string.
        result: AiAnalysisResult from enrichment pipeline.

    Returns:
        Patched SGF string with enrichment properties set.
        If status=REJECTED, returns the original SGF unchanged.
    """
    status = result.validation.status

    # REJECTED → return original unchanged
    if status == ValidationStatus.REJECTED:
        logger.info(
            "Skipping SGF patch for puzzle %s: status=REJECTED",
            result.puzzle_id,
        )
        return sgf_text

    # Parse the existing SGF to check for human-curated properties
    try:
        root = parse_sgf(sgf_text)
    except Exception as e:
        logger.error("Failed to parse SGF for patching: %s", e)
        return sgf_text

    # Determine existing human-curated properties
    existing_curated: dict[str, str] = {}
    for prop in _HUMAN_CURATED_PROPS:
        val = root.get(prop, "")
        if val:
            existing_curated[prop] = val

    # Extract solution tree for YX metrics
    solution_moves = extract_solution_tree_moves(root)

    # Build the patch properties
    patches: dict[str, str] = {}

    # YR — refutation wrong moves (always written, engine-derived)
    if result.refutations:
        yr_value = ",".join(ref.wrong_move for ref in result.refutations if ref.wrong_move)
        if yr_value:
            patches["YR"] = yr_value

    # YG — difficulty level
    if result.difficulty.suggested_level and result.difficulty.suggested_level != "unknown":
        if status == ValidationStatus.ACCEPTED:
            # ACCEPTED: always write YG
            patches["YG"] = result.difficulty.suggested_level
        elif status == ValidationStatus.FLAGGED:
            # FLAGGED: preserve existing, set only if absent
            if "YG" not in existing_curated:
                patches["YG"] = result.difficulty.suggested_level

    # YX — complexity metrics (always written, engine-derived)
    yx_value = _build_yx(result, solution_moves)
    if yx_value:
        patches["YX"] = yx_value

    if not patches:
        logger.debug("No properties to patch for puzzle %s", result.puzzle_id)
        return sgf_text

    # Apply patches to the SGF string
    patched = _apply_patches(sgf_text, patches)

    logger.info(
        "Patched SGF for puzzle %s: status=%s, properties=%s",
        result.puzzle_id,
        status.value,
        list(patches.keys()),
    )

    return patched


def _build_yx(result: AiAnalysisResult, solution_moves: list[str]) -> str:
    """Build YX complexity value from enrichment result.

    Format: d:{depth};r:{refutation_count};s:{solution_length};u:{unique_responses}
    where d = solution tree depth (number of moves in main line).
    """
    solution_length = len(solution_moves) if solution_moves else 0
    depth = solution_length  # d: solution tree depth (move count)
    refutation_count = len(result.refutations)

    # unique_responses: count of distinct refutation types
    # In Phase A all are 'unclassified', so use refutation_count as proxy
    unique_responses = len({
        ref.wrong_move for ref in result.refutations if ref.wrong_move
    })

    # Only emit if there's meaningful data
    if depth == 0 and refutation_count == 0 and solution_length == 0:
        return ""

    return f"d:{depth};r:{refutation_count};s:{solution_length};u:{unique_responses}"


def _apply_patches(sgf_text: str, patches: dict[str, str]) -> str:
    """Apply property patches to SGF string at the root node level.

    Uses core/sgf_parser.py to parse, modify root properties, then re-serialize.
    This ensures correct SGF grammar handling without regex.
    """
    try:
        root = CoreSGF.parse_sgf(sgf_text)
    except Exception as e:
        logger.error("Failed to parse SGF for patching: %s", e)
        return sgf_text

    for prop_key, prop_value in patches.items():
        root.set_property(prop_key, prop_value)

    return root.sgf()


def _insert_property(sgf_text: str, key: str, value: str) -> str:
    """Insert a new property into the SGF root node.

    Uses core/sgf_parser.py to parse, set the property, then re-serialize.
    Kept as a separate function for API compatibility, but delegates
    to core/sgf_parser just like _apply_patches.
    """
    try:
        root = CoreSGF.parse_sgf(sgf_text)
    except Exception as e:
        logger.warning("Could not parse SGF for property insertion %s: %s", key, e)
        return sgf_text

    root.set_property(key, value)
    return root.sgf()
