"""
Move correctness inference for SGF solution nodes.

Three-layer fallback system to determine whether a move is correct or wrong:

  Layer 1: SGF markers (WV/BM/TR -> wrong, TE/IT -> correct)
  Layer 2: Comment text prefix matching (Wrong/Incorrect/- -> wrong, Correct/Right/+ -> correct)
  Layer 3: Tree structure heuristic (for refutation counting ONLY)

Ported from backend/puzzle_manager/core/correctness.py for use across all tools.
Tools must NOT import from backend/ — this is a standalone copy.
"""

from __future__ import annotations


def infer_correctness(
    comment: str | None,
    properties: dict[str, str],
) -> bool | None:
    """Infer move correctness from SGF markers and comment text.

    Three-layer inference:
      Layer 1: Explicit SGF markers (always wins)
        - WV (Wrong Variation), BM (Bad Move), or TR (Triangle) -> False (wrong)
        - TE (Tesuji) or IT (Interesting) -> True (correct)
      Layer 2: Comment text prefix matching (fallback when no markers)
        - Starts with "wrong" or "incorrect", or is exactly "-" -> False
        - Starts with "correct", "right", or is exactly "+" -> True

    Args:
        comment: The C[] property text, or None.
        properties: Raw SGF properties dict for the node.

    Returns:
        True if correct, False if wrong, None if unknown (no signal from
        either markers or comments).
    """
    # Layer 1: Explicit SGF markers (gold standard)
    has_wrong_marker = "WV" in properties or "BM" in properties or "TR" in properties
    has_correct_marker = "TE" in properties or "IT" in properties

    if has_wrong_marker or has_correct_marker:
        # When both present, correct marker wins (TE/IT override BM/TR)
        if has_correct_marker:
            return True
        return False

    # Layer 2: Comment text prefix matching (silver standard)
    if comment:
        return infer_correctness_from_comment(comment)

    # No signal from either layer
    return None


def infer_correctness_from_comment(comment: str) -> bool | None:
    """Infer correctness from comment text using prefix matching.

    Conservative matching — only matches well-established conventions
    found across 80,000+ SGF files from 9 different sources.

    Wrong prefixes (case-insensitive):
      - "wrong"     — covers Wrong, Wrong., Wrong; ko, Wrong This move...
      - "incorrect" — covers Incorrect, <h1>Incorrect</h1>

    Wrong exact match:
      - "-"         — minimalist wrong marker (symmetric with "+")

    Correct prefixes (case-insensitive):
      - "correct"   — covers Correct!, Correct., Correct; ko
      - "right"     — covers RIGHT, CHOICERIGHT (goproblems)

    Correct exact match:
      - "+"         — minimalist marker (ambak-tsumego, t-hero)

    NOT matched (too ambiguous for reliable inference):
      - bad, fail, lose, dead, kill, oops, close
      - good, nice, win, live

    Args:
        comment: Non-empty comment text from C[] property.

    Returns:
        True if correct, False if wrong, None if ambiguous/unknown.
    """
    stripped = comment.strip()
    if not stripped:
        return None

    lower = stripped.lower()

    # Wrong prefixes
    if lower.startswith("wrong") or lower.startswith("incorrect"):
        return False

    # Wrong exact match: "-" is a minimalist wrong marker
    if stripped == "-":
        return False

    # Correct prefixes
    if lower.startswith("correct") or lower.startswith("right"):
        return True

    # Correct exact match: "+" is a minimalist correct marker
    if stripped == "+":
        return True

    return None


def count_structural_refutations(children_count: int, correct_count: int) -> int:
    """Estimate refutation count from tree structure (Layer 3 fallback).

    When neither SGF markers nor comment text provide correctness signals,
    we can still estimate refutation count from the tree structure:

      - In a well-formed tsumego, typically 1 branch is correct
        and the rest are refutations.
      - This heuristic: rc = total_first_children - max(correct_count, 1)

    This is ONLY used for the ``rc`` field in YQ quality metrics.
    It does NOT influence ``u`` (uniqueness), ``d`` (depth), or ``YR``
    (refutation coords), which require definitive correctness knowledge.

    Args:
        children_count: Total number of first-level children (branches).
        correct_count: Number of children known to be correct (from Layers 1 & 2).

    Returns:
        Estimated refutation count (0 or positive).
    """
    if children_count <= 0:
        return 0

    if correct_count > 0:
        # We know some are correct — the rest are refutations
        return max(0, children_count - correct_count)

    # No correctness info at all — assume 1 correct, rest are refutations
    # This is conservative: most tsumego have exactly 1 correct first move
    if children_count <= 1:
        return 0
    return children_count - 1
