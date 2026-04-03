"""
Move correctness inference for SGF solution nodes.

Three-layer fallback system to determine whether a move is correct or wrong:

  Layer 1: SGF markers (BM/TR → wrong, TE/IT → correct)
  Layer 2: Comment text prefix matching (Wrong/Incorrect → wrong, Correct/Right/+ → correct)
  Layer 3: Tree structure heuristic (for refutation counting ONLY)

Layer 1 is the gold standard (explicit, unambiguous machine-readable SGF properties).
Layer 2 catches ~99% of puzzles that lack SGF markers but use comment conventions.
Layer 3 is a fallback for puzzles with no markers AND no comments.

Used by:
  - sgf_parser._props_to_node() — Layers 1 & 2, sets SolutionNode.is_correct
  - quality.count_refutation_moves() — Layer 3 fallback for rc in YQ
  - stages/analyze.py — mark_sibling_refutations() to fix unmarked wrong siblings
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from backend.puzzle_manager.core.text_cleaner import clean_for_correctness

if TYPE_CHECKING:
    from backend.puzzle_manager.core.sgf_parser import SolutionNode


def infer_correctness(
    comment: str | None,
    properties: dict[str, str],
) -> bool | None:
    """Infer move correctness from SGF markers and comment text.

    Three-layer inference:
      Layer 1: Explicit SGF markers (always wins)
        - BM (Bad Move) or TR (Triangle) → False (wrong)
        - TE (Tesuji) or IT (Interesting) → True (correct)
      Layer 2: Comment text prefix matching (fallback when no markers)
        - Starts with "wrong" or "incorrect" → False
        - Starts with "correct", "right", or is exactly "+" → True

    Args:
        comment: The C[] property text, or None.
        properties: Raw SGF properties dict for the node.

    Returns:
        True if correct, False if wrong, None if unknown (no signal from
        either markers or comments).
    """
    # Layer 1: Explicit SGF markers (gold standard)
    has_wrong_marker = "BM" in properties or "TR" in properties
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

    Correct prefixes (case-insensitive):
      - "correct"   — covers Correct!, Correct., Correct; ko
      - "right"     — covers RIGHT, CHOICERIGHT

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
    # Clean HTML tags and decode entities before prefix matching
    cleaned = clean_for_correctness(comment)
    if not cleaned:
        return None

    lower = cleaned.lower()

    # Wrong prefixes
    if lower.startswith("wrong") or lower.startswith("incorrect"):
        return False

    # Correct prefixes
    if lower.startswith("correct") or lower.startswith("right"):
        return True

    # Exact match: "+" is a minimalist correct marker
    if cleaned == "+":
        return True

    return None


def count_structural_refutations(children_count: int, correct_count: int) -> int:
    """Estimate refutation count from tree structure (Layer 3 fallback).

    When neither SGF markers nor comment text provide correctness signals,
    we can still estimate refutation count from The tree structure:

      - In a well-formed tsumego, typically 1 branch is correct
        and the rest are refutations.
      - This heuristic: rc = total_first_children - max(correct_count, 1)

    This is ONLY used for the `rc` field in YQ quality metrics.
    It does NOT influence `u` (uniqueness), `d` (depth), or `YR` (refutation coords),
    which require definitive correctness knowledge.

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


def _has_correctness_signal(node: SolutionNode) -> bool:
    """Check if a node has an explicit correctness signal (marker or comment).

    Detects Layer 1 (SGF markers: BM, TR, TE, IT) and Layer 2
    (comment text with Correct/Wrong/Right/Incorrect prefix).

    Args:
        node: A SolutionNode from the parsed solution tree.

    Returns:
        True if the node carries any explicit correctness signal.
    """
    # Layer 1: SGF markers
    if any(k in node.properties for k in ("BM", "TR", "TE", "IT")):
        return True
    # Layer 2: Comment with correctness prefix
    if node.comment:
        result = infer_correctness_from_comment(node.comment)
        if result is not None:
            return True
    return False


def mark_sibling_refutations(root: SolutionNode) -> int:
    """Walk solution tree and mark unmarked siblings as wrong.

    At each set of sibling player-move nodes, if exactly 1 sibling has
    an explicit correct marker, all unmarked siblings are marked as
    wrong (``is_correct=False``).  This fixes the common convention
    where only the correct leaf carries ``C[RIGHT]`` and wrong
    siblings are left without any marker.

    **Miai guard**: when 2+ siblings are explicitly correct, unmarked
    siblings are left unchanged (could be alternative correct moves).

    Args:
        root: Root ``SolutionNode`` of the parsed solution tree.

    Returns:
        Count of nodes newly marked as wrong.
    """
    marked = 0

    def _walk(node: SolutionNode) -> None:
        nonlocal marked
        if not node.children:
            return

        # Partition children by correctness status
        explicitly_correct: list[SolutionNode] = []
        unmarked: list[SolutionNode] = []

        for child in node.children:
            if not child.is_correct:
                pass  # already wrong — skip
            elif _has_correctness_signal(child):
                explicitly_correct.append(child)
            else:
                unmarked.append(child)

        # Only mark when exactly 1 sibling is explicitly correct
        if len(explicitly_correct) == 1 and unmarked:
            for child in unmarked:
                if child.move is not None:
                    child.is_correct = False
                    marked += 1

        # Recurse into all children
        for child in node.children:
            _walk(child)

    _walk(root)
    return marked
