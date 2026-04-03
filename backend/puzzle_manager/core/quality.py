"""
Quality metrics computation for SGF puzzles.

Computes YQ (quality) metrics per Spec 024 definitions.
Quality measures DATA RICHNESS - how well documented the puzzle is.

Refutation counting uses a three-layer fallback:
  Layer 1: SGF markers (BM/TR) — set during parsing
  Layer 2: Comment text ("Wrong"/"Correct") — set during parsing
  Layer 3: Tree structure heuristic — applied here as fallback

Quality scoring is config-driven: thresholds are loaded from
config/puzzle-quality.json (single source of truth, no hardcoded fallbacks).

See core/correctness.py for the inference logic.
"""

import json
import logging
from pathlib import Path
from typing import Any

from backend.puzzle_manager.core.correctness import count_structural_refutations
from backend.puzzle_manager.core.sgf_parser import SGFGame, SolutionNode
from backend.puzzle_manager.core.text_cleaner import is_teaching_comment

logger = logging.getLogger("puzzle_manager.quality")

# ---------------------------------------------------------------------------
# Config-driven quality thresholds (loaded lazily from puzzle-quality.json)
# ---------------------------------------------------------------------------

_quality_config: dict[str, Any] | None = None


def _load_quality_config() -> dict[str, Any]:
    """Load quality config from config/puzzle-quality.json.

    Cached after first load. Raises on missing or corrupt config.
    """
    global _quality_config
    if _quality_config is not None:
        return _quality_config

    config_path = Path(__file__).resolve().parents[3] / "config" / "puzzle-quality.json"
    if not config_path.exists():
        raise FileNotFoundError(f"Required config not found: {config_path}")

    _quality_config = json.loads(config_path.read_text(encoding="utf-8"))
    return _quality_config


def _get_quality_thresholds() -> list[tuple[int, dict[str, Any]]]:
    """Get quality level thresholds from config, sorted highest-first.

    Returns a list of (level_int, requirements_dict) tuples.
    """
    config = _load_quality_config()
    levels = config["levels"]

    thresholds: list[tuple[int, dict[str, Any]]] = []
    for level_str, level_data in levels.items():
        try:
            level_int = int(level_str)
            reqs = level_data.get("requirements", {})
            thresholds.append((level_int, reqs))
        except (ValueError, AttributeError):
            continue

    # Sort highest level first for early-return evaluation
    thresholds.sort(key=lambda x: x[0], reverse=True)
    return thresholds


def reset_quality_config() -> None:
    """Reset cached quality config. Used in testing."""
    global _quality_config
    _quality_config = None


def count_refutation_moves(node: SolutionNode) -> int:
    """Count total refutation (wrong move) branches in solution tree.

    Uses a three-layer approach:
      1. Traverses the tree counting nodes where is_correct=False
         (set by Layer 1 SGF markers and Layer 2 comment text in parser).
      2. If no refutations found via is_correct AND the root has >1 child,
         falls back to Layer 3: structural heuristic at the root level
         (assumes 1 correct first move, rest are refutations).

    Layer 3 only influences the refutation count (rc in YQ).
    It does NOT affect u (uniqueness), d (depth), or YR (refutation coords).

    Args:
        node: Root solution node.

    Returns:
        Number of refutation branches.
    """
    # First: count is_correct=False nodes (Layers 1 & 2)
    count = 0

    def traverse(n: SolutionNode) -> None:
        nonlocal count
        for child in n.children:
            if not child.is_correct:
                count += 1
            traverse(child)

    traverse(node)

    if count > 0:
        return count

    # Layer 3 fallback: structural heuristic at root level.
    # When all children have is_correct=True (default), it means no
    # correctness signal was found by Layers 1 or 2.
    # Estimate from tree structure: total children - 1 (assume 1 correct).
    if node.children:
        return count_structural_refutations(
            children_count=len(node.children),
            correct_count=0,  # No definitive signal — all are default True
        )

    return 0


def compute_comment_level(node: SolutionNode) -> int:
    """Compute the comment quality level of a solution tree.

    Returns a 3-level integer for the hc field in YQ:
      0 = no comments at all
      1 = correctness markers only (e.g., C[Correct!], C[Wrong], C[+])
      2 = genuine teaching text beyond correctness markers
          (e.g., C[Wrong — White escapes via ladder])

    Args:
        node: Root solution node.

    Returns:
        Comment level: 0, 1, or 2.
    """
    has_any_comment = False

    def traverse(n: SolutionNode) -> int:
        nonlocal has_any_comment
        if n.comment and n.comment.strip():
            has_any_comment = True
            if is_teaching_comment(n.comment):
                return 2  # Found genuine teaching text
        for child in n.children:
            result = traverse(child)
            if result == 2:
                return 2  # Short-circuit on first teaching comment
        return 0

    result = traverse(node)
    if result == 2:
        return 2
    if has_any_comment:
        return 1  # Has comments, but only correctness markers
    return 0


def has_teaching_comments(node: SolutionNode) -> bool:
    """Check if solution tree has any comments (correctness markers or teaching).

    Returns True if the tree has any non-empty comment at any level
    (comment level >= 1). This is used by compute_puzzle_quality_level()
    for the tier threshold (hc >= 1 qualifies for tier 4/5).

    For finer granularity, use compute_comment_level() which distinguishes
    bare correctness markers (level 1) from genuine teaching text (level 2).

    Args:
        node: Root solution node.

    Returns:
        True if any node has a non-empty comment.
    """
    return compute_comment_level(node) >= 1


def compute_puzzle_quality_level(game: SGFGame) -> int:
    """Compute puzzle quality level (1-5) based on puzzle data richness.

    Scale: 1=worst, 5=best (matches source-quality.json and puzzle-quality.json).

    Thresholds are loaded from config/puzzle-quality.json. Falls back to
    hardcoded defaults if the config file is missing.

    Quality levels:
    - 5 (Premium): solution tree + ≥3 refutations + comments
    - 4 (High): solution tree + ≥2 refutations + comments
    - 3 (Standard): solution tree + ≥1 refutation
    - 2 (Basic): solution tree only, no refutations
    - 1 (Unverified): no solution tree

    Args:
        game: Parsed SGF game.

    Returns:
        Quality level 1-5 (1=worst, 5=best).
    """
    if not game.has_solution:
        return 1  # Unverified (worst)

    refutation_count = count_refutation_moves(game.solution_tree)
    comment_level = compute_comment_level(game.solution_tree)
    ac = parse_ac_level(game.yengo_props.quality) if game.yengo_props else 0

    thresholds = _get_quality_thresholds()

    for level, reqs in thresholds:
        if not reqs:
            # Empty requirements = catch-all (level 1)
            continue

        # Check has_solution_tree requirement
        if reqs.get("has_solution_tree") and not game.has_solution:
            continue

        # Check refutation_count_min
        min_rc = reqs.get("refutation_count_min")
        if min_rc is not None and refutation_count < min_rc:
            continue

        # Check min_comment_level
        min_hc = reqs.get("min_comment_level")
        if min_hc is not None and comment_level < min_hc:
            continue

        # Check min_ac (analysis completeness)
        min_ac = reqs.get("min_ac")
        if min_ac is not None and ac < min_ac:
            continue

        return level

    # Default: Basic (has solution tree but nothing else matched)
    return 2


# Backwards compatibility alias
compute_quality_tier = compute_puzzle_quality_level


def compute_quality_metrics(game: SGFGame) -> str:
    """Compute full YQ quality metrics string.

    Format: "q:{level};rc:{refutation_count};hc:{comment_level};ac:{analysis_completeness}"

    The hc field is a 3-level integer:
      0 = no comments
      1 = correctness markers only (Correct!/Wrong/+)
      2 = genuine teaching text beyond markers

    The ac field tracks analysis completeness (pipeline processing state):
      0 = untouched (AI pipeline has not processed this puzzle)
      1 = enriched (AI enriched metadata, existing solution used as-is)
      2 = ai_solved (AI built or extended the solution tree)
      3 = verified (AI-solved puzzle confirmed by human expert)

    Args:
        game: Parsed SGF game.

    Returns:
        YQ string (e.g., "q:3;rc:2;hc:1;ac:0").
    """
    level = compute_puzzle_quality_level(game)
    refutation_count = count_refutation_moves(game.solution_tree) if game.has_solution else 0
    comment_level = compute_comment_level(game.solution_tree) if game.has_solution else 0
    ac = parse_ac_level(game.yengo_props.quality) if game.yengo_props else 0

    return f"q:{level};rc:{refutation_count};hc:{comment_level};ac:{ac}"


def parse_quality_level(yq_string: str | None) -> int | None:
    """Parse quality level (1-5) from YQ property string.

    Args:
        yq_string: YQ property value (e.g., "q:3;rc:2;hc:1") or None.

    Returns:
        Quality level 1-5, or None if parsing fails or input is None.

    Examples:
        >>> parse_quality_level("q:3;rc:2;hc:1")
        3
        >>> parse_quality_level(None)
        None
        >>> parse_quality_level("invalid")
        None
    """
    if not yq_string:
        return None

    # Parse "q:{level}" from YQ string format
    import re
    match = re.match(r"q:(\d+)", yq_string)
    if match:
        level = int(match.group(1))
        if 1 <= level <= 5:
            return level
    return None


def parse_ac_level(yq_string: str | None) -> int:
    """Parse analysis completeness (ac) from YQ property string.

    Args:
        yq_string: YQ property value (e.g., "q:3;rc:2;hc:1;ac:1") or None.

    Returns:
        AC level 0-3, defaulting to 0 (untouched) if absent or unparseable.

    Examples:
        >>> parse_ac_level("q:3;rc:2;hc:1;ac:1")
        1
        >>> parse_ac_level("q:3;rc:2;hc:1")
        0
        >>> parse_ac_level(None)
        0
    """
    if not yq_string:
        return 0

    import re
    match = re.search(r"ac:(\d+)", yq_string)
    if match:
        val = int(match.group(1))
        if 0 <= val <= 3:
            return val
    return 0
