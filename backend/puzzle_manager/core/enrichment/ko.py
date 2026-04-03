"""Ko context detection for puzzle enrichment.

Detects and classifies ko situations for the YK property.

YK Format:
----------
Ko type enum value:
  YK[none]      - No ko in the puzzle
  YK[direct]    - Direct ko (immediate recapture situation)
  YK[approach]  - Approach ko (needs extra move before ko)

Phase 1 (v6 Schema):
- none, direct, approach

Phase 2 (Spec 045 - not yet implemented):
- multi (multi-step ko)
- picnic (picnic ko / flower ko)
- unconditional (ten thousand year ko)
- eternal (eternal life / triple ko)

Detection Algorithm:
--------------------
1. Check puzzle tags for ko-related tags -> classify by tag
2. Scan solution tree comments for ko keywords -> direct
3. Check for immediate recapture patterns -> direct
4. Otherwise -> none

Timeout Protection:
-------------------
Ko detection has a 5-second timeout (configurable). This timeout exists as a
**fail-safe** for edge cases, NOT because ko detection is typically slow.

Why the timeout is necessary:
1. **Complex positions**: Some pathological board positions (e.g., 50+ stones
   in intricate shapes) could theoretically cause detection to take longer
2. **Phase 2 future-proofing**: Advanced ko types (eternal, multi) in spec-045
   require position simulation which could be expensive
3. **Pipeline reliability**: A single malformed puzzle should never block the
   entire batch processing

Expected behavior:
- Typical detection: < 50ms (tag/comment based)
- Worst case without timeout: theoretically unbounded for cyclic detection
- With timeout: guaranteed < 5s, falls back to KoContextType.NONE

The timeout is NOT a performance optimization - it's a circuit breaker.
If detection consistently approaches timeout, the algorithm should be
optimized rather than relying on the timeout.

Philosophy:
-----------
Ko is one of the most important concepts in Go. Understanding ko context
helps players:
1. Recognize when ko fighting applies
2. Know to look for ko threats
3. Understand why certain moves are necessary
"""

from __future__ import annotations

import logging
import re
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.puzzle_manager.core.sgf_parser import SGFGame, SolutionNode

logger = logging.getLogger("enrichment.ko")


class KoContextType(Enum):
    """Ko context classification (Phase 1)."""

    NONE = "none"  # No ko
    DIRECT = "direct"  # Direct/simple ko
    APPROACH = "approach"  # Approach ko (needs extra move)


def detect_ko_context(game: SGFGame) -> KoContextType:
    """Detect ko context from puzzle data.

    Uses multiple detection methods:
    1. Tag-based detection (fastest, most reliable)
    2. Comment-based detection (catches tagged puzzles)
    3. Solution tree analysis (catches unmarked ko)

    Args:
        game: Parsed SGF game.

    Returns:
        KoContextType enum value.
    """
    # Method 1: Check tags
    if game.yengo_props and game.yengo_props.tags:
        ko_type = _detect_from_tags(game.yengo_props.tags)
        if ko_type != KoContextType.NONE:
            logger.debug(f"Ko detected from tags: {ko_type.value}")
            return ko_type

    # Method 2: Check comments
    if game.has_solution:
        ko_type = _detect_from_comments(game.solution_tree)
        if ko_type != KoContextType.NONE:
            logger.debug(f"Ko detected from comments: {ko_type.value}")
            return ko_type

    # Method 3: Check root comment (prefer game.root_comment, fall back to solution_tree)
    root_comment = getattr(game, 'root_comment', '') or ''
    if not root_comment:
        root_comment = game.solution_tree.comment if game.solution_tree else ""
    if root_comment:
        ko_type = _detect_from_text(root_comment)
        if ko_type != KoContextType.NONE:
            logger.debug(f"Ko detected from root comment: {ko_type.value}")
            return ko_type

    return KoContextType.NONE


def _detect_from_tags(tags: list[str]) -> KoContextType:
    """Detect ko type from puzzle tags.

    Args:
        tags: List of puzzle tags.

    Returns:
        KoContextType based on tags.
    """
    tags_lower = [t.lower() for t in tags]

    # Approach ko tags
    approach_ko_tags = ["approach-ko", "approach_ko", "approachko"]
    for tag in approach_ko_tags:
        if tag in tags_lower:
            return KoContextType.APPROACH

    # Direct ko tags
    direct_ko_tags = ["ko", "ko-fight", "ko_fight", "kofight", "direct-ko", "direct_ko"]
    for tag in direct_ko_tags:
        if tag in tags_lower:
            return KoContextType.DIRECT

    return KoContextType.NONE


def _detect_from_comments(
    node: SolutionNode,
    depth: int = 0,
) -> KoContextType:
    """Detect ko type from solution tree comments.

    Args:
        node: Node to check (and descendants).
        depth: Current recursion depth.

    Returns:
        KoContextType based on comments.
    """
    if depth > 10:  # Limit depth for performance
        return KoContextType.NONE

    # Check this node's comment
    if node.comment:
        ko_type = _detect_from_text(node.comment)
        if ko_type != KoContextType.NONE:
            return ko_type

    # Check children
    for child in node.children:
        ko_type = _detect_from_comments(child, depth + 1)
        if ko_type != KoContextType.NONE:
            return ko_type

    return KoContextType.NONE


def _detect_from_text(text: str) -> KoContextType:
    """Detect ko type from free-form text.

    Uses word-boundary matching to avoid false positives from substrings
    (e.g., "korner" should not match "ko"). Also checks CJK ko terms
    for Japanese (コウ), Korean (패), and Chinese (劫) sources.

    Args:
        text: Text to analyze.

    Returns:
        KoContextType based on text analysis.
    """
    text_lower = text.lower()

    # Approach ko patterns (multi-word, checked as substrings — safe)
    approach_patterns = [
        "approach ko",
        "approach-ko",
        "needs ko threat",
        "require ko threat",
    ]
    for pattern in approach_patterns:
        if pattern in text_lower:
            return KoContextType.APPROACH

    # Direct ko patterns — use word boundaries
    # \bko\b prevents matching "korner", "kokeshi", etc.
    if re.search(r'\bko\b', text_lower):
        return KoContextType.DIRECT
    if re.search(r'\brecapture\b', text_lower):
        return KoContextType.DIRECT
    if "ko threat" in text_lower:
        return KoContextType.DIRECT
    if "ko fight" in text_lower:
        return KoContextType.DIRECT

    # CJK ko terms (no word boundaries needed — these are distinct characters)
    cjk_ko_terms = [
        "コウ",    # Japanese: kou
        "패",      # Korean: pae
        "劫",      # Chinese: jié
    ]
    for term in cjk_ko_terms:
        if term in text:
            return KoContextType.DIRECT

    return KoContextType.NONE
