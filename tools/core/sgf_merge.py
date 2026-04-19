"""
SGF merge library for combining solution trees from matched puzzle files.

Provides merge planning (deciding what action to take for each matched pair)
and tree merging (combining solution branches and comments from two sources).

Used by the merge_dirs CLI script.

Design reference: docs/architecture/tools/sgf-directory-comparison.md

Usage:
    from tools.core.sgf_merge import (
        MergeDecision, plan_merge, merge_solution_trees,
        merge_comments, build_merged_sgf, infer_correct_first_moves,
    )
    from tools.core.sgf_compare import CompareResult

    decision = plan_merge(compare_result)
    if decision.action == "merge_trees":
        merged = merge_solution_trees(primary_node, secondary_node, 19, transform)
        sgf = build_merged_sgf(primary_tree, merged, merged_root_comment)
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass

import re

from tools.core.position_transform import inverse_transform, transform_node
from tools.core.sgf_builder import SGFBuilder
from tools.core.sgf_compare import CompareResult, MatchLevel
from tools.core.sgf_parser import SgfNode, SgfTree
from tools.core.sgf_types import PositionTransform


# ---------------------------------------------------------------------------
# Merge decision
# ---------------------------------------------------------------------------

COMMENT_SEPARATOR = "\n---\n"


@dataclass
class MergeDecision:
    """Per-puzzle merge decision based on comparison result."""

    source_file: str
    target_file: str | None
    action: str  # "use_primary", "use_secondary", "merge_trees", "copy_primary", "skip"
    reason: str
    match_level: int | None
    match_method: str  # "identity" or "d4_symmetry"
    transform: PositionTransform | None

    def to_dict(self) -> dict:
        return {
            "source_file": self.source_file,
            "target_file": self.target_file,
            "action": self.action,
            "reason": self.reason,
            "match_level": self.match_level,
            "match_method": self.match_method,
            "transform": self.transform.to_dict() if self.transform else None,
        }


# ---------------------------------------------------------------------------
# Leaf-outcome correctness inference
# ---------------------------------------------------------------------------

# Patterns that indicate a correct outcome in leaf comments (Layer 2 of
# sgf_correctness.py). These are the same signals used by infer_correctness()
# but applied to leaf nodes where the outcome is determined.
_CORRECT_LEAF_RE = re.compile(
    r"^(?:correct|right|\+|yes)\s*$",
    re.IGNORECASE,
)


def _is_correct_leaf(node: SgfNode) -> bool:
    """Check if a leaf node indicates a correct outcome via C[+] or similar."""
    if not node.comment:
        return False
    return bool(_CORRECT_LEAF_RE.match(node.comment.strip()))


def infer_correct_first_moves(root: SgfNode) -> set[tuple[str, str]]:
    """Infer which first moves are correct by tracing leaf outcomes.

    Walks the entire solution tree. For each leaf with a correct-outcome
    marker (C[+], C[correct], etc.), traces back to identify which first
    move (direct child of root) leads to that leaf.

    Returns set of move keys like {("B", "ab"), ("B", "cd")}.
    Returns empty set if no correct-outcome leaves found (cannot infer).
    """
    correct_first: set[tuple[str, str]] = set()

    for first_child in root.children:
        key = _move_key(first_child)
        if _subtree_has_correct_leaf(first_child):
            correct_first.add(key)

    return correct_first


def _subtree_has_correct_leaf(node: SgfNode) -> bool:
    """Check if any leaf in this subtree has a correct-outcome marker."""
    if not node.children:
        # Leaf node — check for correct outcome marker
        return _is_correct_leaf(node)

    # Internal node — recurse into children
    return any(_subtree_has_correct_leaf(child) for child in node.children)


def _all_first_moves_correct(root: SgfNode) -> bool:
    """Check if ALL first moves are marked is_correct=True (convention mismatch indicator)."""
    if not root.children:
        return False
    return all(child.is_correct for child in root.children)


def plan_merge(
    result: CompareResult,
    *,
    min_level: int = 4,
    primary_tree: SgfTree | None = None,
    secondary_tree: SgfTree | None = None,
) -> MergeDecision:
    """Decide merge action based on comparison result.

    Level 7 (Byte-Identical): use_primary (no benefit merging)
    Level 6 (Tree-Identical): use_secondary if it has more comments, else use_primary
    Level 5 (Superset):       use_secondary (it has all primary paths + more)
    Level 4 (Divergent):      merge_trees (union both sets of variations)
    Level 3 (Solution-Differs): skip OR merge_trees_inferred (see below)
    Level 2 (Position-Only):  skip
    Level 1 (Filename-Mismatch): skip
    Level 0 (Unmatched):      copy_primary (no target match)

    Level 3 rescue: When secondary marks ALL first moves as is_correct=True
    (convention mismatch, e.g. t-hero), we trace leaf outcomes (C[+]) to
    infer which first moves are truly correct. If inferred correct moves
    include all of primary's correct moves, we reclassify as merge_trees_inferred.

    Args:
        result: CompareResult from classify_match.
        min_level: Minimum match level to merge (default 4).
        primary_tree: Primary SgfTree (needed for Level 3 rescue).
        secondary_tree: Secondary SgfTree (needed for Level 3 rescue).
    """
    transform = None
    if result.transform_rotation is not None:
        transform = PositionTransform(
            rotation=result.transform_rotation,
            reflect=result.transform_reflect or False,
        )

    base = MergeDecision(
        source_file=result.source_file,
        target_file=result.target_file,
        match_level=result.match_level,
        match_method=result.match_method,
        transform=transform,
        action="skip",
        reason="",
    )

    # Unmatched source
    if result.target_file is None or result.match_level == MatchLevel.UNMATCHED:
        base.action = "copy_primary"
        base.reason = "No target match"
        return base

    # Below minimum merge level — but attempt Level 3 rescue first
    if result.match_level < min_level:
        # Level 3 rescue: convention mismatch detection
        if (
            result.match_level == MatchLevel.SOLUTION_DIFFERS
            and primary_tree is not None
            and secondary_tree is not None
        ):
            rescue = _attempt_level3_rescue(
                result, base, primary_tree, secondary_tree, transform,
            )
            if rescue is not None:
                return rescue

        base.action = "skip"
        base.reason = (
            f"Match level {result.match_level} below min_level {min_level}: "
            f"{result.detail}"
        )
        return base

    if result.match_level == MatchLevel.BYTE_IDENTICAL:
        base.action = "use_primary"
        base.reason = "Byte-identical, no merge needed"
        return base

    if result.match_level == MatchLevel.TREE_IDENTICAL:
        # Choose the one with more comments
        if result.comments_differ:
            base.action = "merge_trees"
            base.reason = "Tree-identical but comments differ, merging comments"
        else:
            base.action = "use_primary"
            base.reason = "Tree-identical, same comments"
        return base

    if result.match_level == MatchLevel.SUPERSET:
        base.action = "use_secondary"
        base.reason = (
            f"Target is superset ({result.target_nodes} nodes "
            f"vs {result.source_nodes} source nodes)"
        )
        return base

    if result.match_level == MatchLevel.DIVERGENT:
        base.action = "merge_trees"
        base.reason = (
            f"Divergent trees, merging variations "
            f"(source={result.source_nodes}, target={result.target_nodes})"
        )
        return base

    # Fallback for any other level >= min_level
    base.action = "merge_trees"
    base.reason = f"Level {result.match_level}: {result.detail}"
    return base


def _attempt_level3_rescue(
    result: CompareResult,
    base: MergeDecision,
    primary_tree: SgfTree,
    secondary_tree: SgfTree,
    transform: PositionTransform | None,
) -> MergeDecision | None:
    """Attempt to rescue a Level 3 skip via leaf-outcome correctness inference.

    Returns a MergeDecision if rescue succeeds, None if it should stay skipped.

    Safety guardrails (ALL must pass):
    1. Secondary marks ALL first moves as is_correct=True
    2. infer_correct_first_moves() finds at least one C[+] leaf in secondary
    3. Primary's correct first moves are a subset of secondary's inferred correct moves
    """
    sec_solution = secondary_tree.solution_tree

    # Transform secondary to primary's orientation for comparison
    if transform is not None and not transform.is_identity:
        inv = inverse_transform(transform)
        sec_aligned = transform_node(sec_solution, secondary_tree.board_size, inv)
    else:
        sec_aligned = sec_solution

    # Guardrail 1: Secondary marks ALL first moves as correct (convention mismatch)
    if not _all_first_moves_correct(sec_aligned):
        return None

    # Guardrail 2: Infer correct first moves from leaf outcomes
    sec_inferred = infer_correct_first_moves(sec_aligned)
    if not sec_inferred:
        return None

    # Guardrail 3: Primary's correct first moves must be a subset
    pri_correct: set[tuple[str, str]] = set()
    for child in primary_tree.solution_tree.children:
        if child.is_correct:
            pri_correct.add(_move_key(child))

    if not pri_correct:
        return None

    if not pri_correct <= sec_inferred:
        return None

    # All guardrails passed — rescue as merge_trees_inferred
    base.action = "merge_trees_inferred"
    base.reason = (
        f"Level 3 rescued: secondary convention mismatch detected "
        f"(all {len(sec_aligned.children)} first moves marked correct, "
        f"leaf-outcome inference confirms {len(sec_inferred)} correct). "
        f"Primary correct moves {len(pri_correct)} are subset of inferred."
    )
    return base


# ---------------------------------------------------------------------------
# Comment merging
# ---------------------------------------------------------------------------


def merge_comments(primary: str, secondary: str) -> str:
    """Merge comments from two sources.

    - Both empty -> empty
    - One empty -> take the other
    - Both identical -> keep one
    - Both different -> primary + separator + secondary
    """
    primary = primary.strip()
    secondary = secondary.strip()

    if not primary and not secondary:
        return ""
    if not primary:
        return secondary
    if not secondary:
        return primary
    if primary == secondary:
        return primary
    return primary + COMMENT_SEPARATOR + secondary


# ---------------------------------------------------------------------------
# Tree merging
# ---------------------------------------------------------------------------


def merge_solution_trees(
    primary: SgfNode,
    secondary: SgfNode,
    board_size: int,
    transform: PositionTransform | None,
    *,
    primary_correctness_wins: bool = False,
) -> SgfNode:
    """Merge two solution trees into one.

    Primary tree structure is the base. Secondary branches not in primary
    are grafted in. Comments are merged (primary preferred, secondary added
    where primary has none).

    Algorithm:
    1. If transform is non-identity, transform_node(secondary)
    2. Recursive parallel walk from root:
       - Match children by (color, move_coordinate)
       - Matching: recurse deeper, merge comments
       - Secondary-only: graft entire subtree as new variation
       - Primary-only: keep as-is

    Args:
        primary: Primary solution tree root (orientation preserved).
        secondary: Secondary solution tree root (may be rotated).
        board_size: Board size.
        transform: D4 transform to apply to secondary coordinates.
        primary_correctness_wins: If True, primary's is_correct flags are
            authoritative for shared moves (used for Level 3 rescue where
            secondary's correctness convention differs).

    Returns:
        New merged SgfNode tree (neither input is mutated).
    """
    # Transform secondary to primary's orientation if needed.
    # find_transform() returns T where T(source) = target, so we need
    # inverse(T) to map target coordinates back to source space.
    if transform is not None and not transform.is_identity:
        inv = inverse_transform(transform)
        secondary_aligned = transform_node(secondary, board_size, inv)
    else:
        secondary_aligned = deepcopy(secondary)

    # Deep-copy primary as our base
    merged = deepcopy(primary)

    # Merge root comments
    merged.comment = merge_comments(merged.comment, secondary_aligned.comment)

    # Recursive merge of children
    _merge_children(merged, secondary_aligned, primary_correctness_wins=primary_correctness_wins)

    return merged


def _move_key(node: SgfNode) -> tuple[str, str]:
    """Create a key for matching nodes by (color, coordinate)."""
    color = node.color.value if node.color else "?"
    coord = node.move.to_sgf() if node.move else "pass"
    return (color, coord)


def _merge_children(
    primary: SgfNode,
    secondary: SgfNode,
    *,
    primary_correctness_wins: bool = False,
) -> None:
    """Recursively merge secondary's children into primary (in-place).

    For each secondary child:
    - If a primary child has the same (color, move): recurse deeper, merge comments
    - If no match: graft the entire secondary subtree as a new variation

    When primary_correctness_wins=True (Level 3 rescue):
    - Shared moves: primary's is_correct flag is kept (curated source)
    - Grafted branches: secondary's is_correct flags are kept as-is
    """
    # Build index of primary children by move key
    primary_by_key: dict[tuple[str, str], SgfNode] = {}
    for child in primary.children:
        key = _move_key(child)
        if key not in primary_by_key:
            primary_by_key[key] = child

    for sec_child in secondary.children:
        key = _move_key(sec_child)
        if key in primary_by_key:
            # Matching move exists — recurse and merge comments
            pri_child = primary_by_key[key]
            pri_child.comment = merge_comments(pri_child.comment, sec_child.comment)

            # Correctness handling depends on mode
            if not primary_correctness_wins:
                # Union (existing behavior for Level 4/5/6)
                if sec_child.is_correct and not pri_child.is_correct:
                    pri_child.is_correct = True

            _merge_children(
                pri_child, sec_child,
                primary_correctness_wins=primary_correctness_wins,
            )
        else:
            # New branch from secondary — graft entire subtree
            primary.children.append(deepcopy(sec_child))


# ---------------------------------------------------------------------------
# SGF output
# ---------------------------------------------------------------------------


def build_merged_sgf(
    primary_tree: SgfTree,
    merged_solution: SgfNode,
    merged_root_comment: str = "",
) -> str:
    """Build final SGF from merged components using SGFBuilder.from_tree().

    Primary tree provides stone positions, metadata, and YenGo properties.
    The solution tree is replaced with the merged result.

    Args:
        primary_tree: Primary SgfTree (board position source).
        merged_solution: Merged solution tree root.
        merged_root_comment: Merged root comment (empty = use primary's).

    Returns:
        SGF string.
    """
    builder = SGFBuilder.from_tree(primary_tree)
    builder.solution_tree = merged_solution

    if merged_root_comment:
        builder.root_comment = merged_root_comment

    return builder.build()
