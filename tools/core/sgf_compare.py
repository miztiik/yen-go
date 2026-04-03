"""
SGF comparison library for directory-level duplicate detection.

Provides position hashing, tree comparison, and match classification
for tsumego puzzle files. Used by the compare_dirs CLI script.

Design reference: docs/architecture/tools/sgf-directory-comparison.md (D1-D18)

Usage:
    from tools.core.sgf_parser import parse_sgf
    from tools.core.sgf_compare import (
        MatchLevel, CompareResult,
        position_hash, full_hash,
        classify_match,
    )

    tree_a = parse_sgf(sgf_a)
    tree_b = parse_sgf(sgf_b)
    result = classify_match(tree_a, tree_b, "prob0001.sgf", "prob0001.sgf")
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import IntEnum

from tools.core.sgf_analysis import compute_solution_depth, count_total_nodes, get_all_paths
from tools.core.sgf_parser import SgfNode, SgfTree
from tools.core.sgf_types import Color


class MatchLevel(IntEnum):
    """Numeric match level (0=no match, 7=byte-identical)."""

    UNMATCHED = 0
    FILENAME_MISMATCH = 1
    POSITION_ONLY = 2
    SOLUTION_DIFFERS = 3
    DIVERGENT = 4
    SUPERSET = 5
    TREE_IDENTICAL = 6
    BYTE_IDENTICAL = 7


MATCH_LEVEL_NAMES: dict[int, str] = {
    0: "Unmatched",
    1: "Filename-Mismatch",
    2: "Position-Only",
    3: "Solution-Differs",
    4: "Divergent",
    5: "Superset",
    6: "Tree-Identical",
    7: "Byte-Identical",
}


@dataclass
class CompareResult:
    """Result of comparing two SGF files."""

    source_file: str
    target_file: str | None
    match_level: int
    position_hash: str | None
    full_hash: str | None
    board_size: int | None
    player_to_move_source: str | None
    player_to_move_target: str | None
    pl_status: str | None
    first_move_match: bool | None
    correct_line_match: bool | None
    source_nodes: int | None
    target_nodes: int | None
    source_depth: int | None
    target_depth: int | None
    comments_differ: bool = False
    markers_differ: bool = False
    detail: str = ""
    error: str | None = None

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        return {
            "source_file": self.source_file,
            "target_file": self.target_file,
            "match_level": self.match_level,
            "position_hash": self.position_hash,
            "full_hash": self.full_hash,
            "board_size": self.board_size,
            "player_to_move_source": self.player_to_move_source,
            "player_to_move_target": self.player_to_move_target,
            "pl_status": self.pl_status,
            "first_move_match": self.first_move_match,
            "correct_line_match": self.correct_line_match,
            "source_nodes": self.source_nodes,
            "target_nodes": self.target_nodes,
            "source_depth": self.source_depth,
            "target_depth": self.target_depth,
            "comments_differ": self.comments_differ,
            "markers_differ": self.markers_differ,
            "detail": self.detail,
            "error": self.error,
        }


def position_hash(tree: SgfTree) -> str:
    """Compute position-only hash (without PL). Always computed.

    Formula: SHA256("SZ{n}:B[sorted_ab]:W[sorted_aw]")[:16]
    """
    b_sorted = ",".join(sorted(p.to_sgf() for p in tree.black_stones))
    w_sorted = ",".join(sorted(p.to_sgf() for p in tree.white_stones))
    canonical = f"SZ{tree.board_size}:B[{b_sorted}]:W[{w_sorted}]"
    return hashlib.sha256(canonical.encode()).hexdigest()[:16]


def full_hash(tree: SgfTree) -> str | None:
    """Compute full hash including PL. Only when PL is explicitly present.

    Formula: SHA256("SZ{n}:B[sorted_ab]:W[sorted_aw]:PL[X]")[:16]
    Returns None if PL was not explicitly set (defaulted).
    """
    if not _has_explicit_pl(tree):
        return None
    b_sorted = ",".join(sorted(p.to_sgf() for p in tree.black_stones))
    w_sorted = ",".join(sorted(p.to_sgf() for p in tree.white_stones))
    pl = tree.player_to_move.value
    canonical = f"SZ{tree.board_size}:B[{b_sorted}]:W[{w_sorted}]:PL[{pl}]"
    return hashlib.sha256(canonical.encode()).hexdigest()[:16]


def _has_explicit_pl(tree: SgfTree) -> bool:
    """Check if PL was explicitly set in the SGF (not defaulted to BLACK).

    The parser doesn't store PL in metadata, so we check the raw SGF
    for the PL property in the root node.
    """
    import re

    raw = tree.raw_sgf
    if not raw:
        # Fallback: if WHITE, it must have been set explicitly (default is BLACK)
        return tree.player_to_move == Color.WHITE
    # Match PL[ that is NOT preceded by another uppercase letter
    return bool(re.search(r"(?<![A-Z])PL\[", raw))


def extract_move_paths(node: SgfNode) -> set[str]:
    """Extract all root-to-leaf move paths as a set of strings.

    Each path is encoded as "B[cd]->W[de]->B[ef]" for comparison.
    Variation ordering does not affect the result (set comparison).
    """
    paths: set[str] = set()
    _collect_move_paths(node, [], paths)
    return paths


def _collect_move_paths(
    node: SgfNode,
    current: list[str],
    paths: set[str],
) -> None:
    """Recursively collect move path strings."""
    if not node.children:
        if current:
            paths.add("->".join(current))
        return

    for child in node.children:
        move_str = _node_to_move_str(child)
        _collect_move_paths(child, current + [move_str], paths)


def _node_to_move_str(node: SgfNode) -> str:
    """Convert a node to a move string like 'B[cd]'."""
    color = node.color.value if node.color else "?"
    coord = node.move.to_sgf() if node.move else "pass"
    return f"{color}[{coord}]"


def _extract_correct_line(node: SgfNode) -> list[str]:
    """Extract the main correct line as a list of move strings."""
    moves: list[str] = []
    current = node
    while current.children:
        found = False
        for child in current.children:
            if child.is_correct:
                moves.append(_node_to_move_str(child))
                current = child
                found = True
                break
        if not found:
            break
    return moves


def _check_comments_differ(node_a: SgfNode, node_b: SgfNode) -> bool:
    """Check if any move-level comments differ between two trees."""
    paths_a = get_all_paths(node_a)
    paths_b = get_all_paths(node_b)

    comments_a: dict[str, str] = {}
    for path in paths_a:
        for n in path:
            if n.move and n.comment:
                key = _node_to_move_str(n)
                comments_a[key] = n.comment

    comments_b: dict[str, str] = {}
    for path in paths_b:
        for n in path:
            if n.move and n.comment:
                key = _node_to_move_str(n)
                comments_b[key] = n.comment

    return comments_a != comments_b


def _check_markers_differ(node_a: SgfNode, node_b: SgfNode) -> bool:
    """Check if correctness markers (is_correct flags) differ between trees."""
    paths_a = get_all_paths(node_a)
    paths_b = get_all_paths(node_b)

    markers_a: dict[str, bool] = {}
    for path in paths_a:
        for n in path:
            if n.move:
                key = _node_to_move_str(n)
                markers_a[key] = n.is_correct

    markers_b: dict[str, bool] = {}
    for path in paths_b:
        for n in path:
            if n.move:
                key = _node_to_move_str(n)
                markers_b[key] = n.is_correct

    return markers_a != markers_b


def _determine_pl_status(
    tree_a: SgfTree, tree_b: SgfTree
) -> str:
    """Determine PL status between two trees."""
    a_has_pl = _has_explicit_pl(tree_a)
    b_has_pl = _has_explicit_pl(tree_b)

    if a_has_pl and b_has_pl:
        if tree_a.player_to_move == tree_b.player_to_move:
            return "confirmed"
        return "conflict"
    if not a_has_pl and not b_has_pl:
        return "absent_both"
    if not a_has_pl:
        return "absent_source"
    return "absent_target"


def classify_match(
    tree_a: SgfTree,
    tree_b: SgfTree,
    source_file: str,
    target_file: str,
    *,
    raw_a: str = "",
    raw_b: str = "",
) -> CompareResult:
    """Classify the match level between two parsed SGF trees.

    Implements the Level 7→0 cascade from the design doc (D7).
    """
    pl_status = _determine_pl_status(tree_a, tree_b)
    pos_hash = position_hash(tree_a)
    f_hash = full_hash(tree_a)

    source_pl = tree_a.player_to_move.value if _has_explicit_pl(tree_a) else None
    target_pl = tree_b.player_to_move.value if _has_explicit_pl(tree_b) else None

    source_nodes = count_total_nodes(tree_a.solution_tree)
    target_nodes = count_total_nodes(tree_b.solution_tree)
    source_depth = compute_solution_depth(tree_a.solution_tree)
    target_depth = compute_solution_depth(tree_b.solution_tree)

    base = CompareResult(
        source_file=source_file,
        target_file=target_file,
        position_hash=pos_hash,
        full_hash=f_hash,
        board_size=tree_a.board_size,
        player_to_move_source=source_pl,
        player_to_move_target=target_pl,
        pl_status=pl_status,
        first_move_match=None,
        correct_line_match=None,
        source_nodes=source_nodes,
        target_nodes=target_nodes,
        source_depth=source_depth,
        target_depth=target_depth,
        match_level=0,
    )

    # Level 7: Byte-identical
    if raw_a and raw_b and raw_a == raw_b:
        base.match_level = MatchLevel.BYTE_IDENTICAL
        base.first_move_match = True
        base.correct_line_match = True
        base.detail = "Byte-identical"
        return base

    # PL conflict caps at Level 2
    if pl_status == "conflict":
        base.match_level = MatchLevel.POSITION_ONLY
        base.detail = "Position matches but PL values conflict"
        return base

    # PL absent caps at Level 2
    if pl_status in ("absent_source", "absent_target", "absent_both"):
        base.match_level = MatchLevel.POSITION_ONLY
        base.detail = f"Position matches but PL status: {pl_status}"
        return base

    # From here, PL is confirmed matching. Proceed with tree comparison.

    # Extract move paths for tree comparison
    paths_a = extract_move_paths(tree_a.solution_tree)
    paths_b = extract_move_paths(tree_b.solution_tree)

    # Level 6: Tree-identical
    if paths_a == paths_b:
        base.match_level = MatchLevel.TREE_IDENTICAL
        base.first_move_match = True
        base.correct_line_match = True
        base.comments_differ = _check_comments_differ(
            tree_a.solution_tree, tree_b.solution_tree
        )
        base.markers_differ = _check_markers_differ(
            tree_a.solution_tree, tree_b.solution_tree
        )
        base.detail = "Tree-identical (same moves, different formatting)"
        return base

    # Check first correct move (D9: fast discriminator)
    first_a = _get_first_correct_move(tree_a)
    first_b = _get_first_correct_move(tree_b)

    if first_a is not None and first_b is not None:
        base.first_move_match = first_a == first_b
    elif first_a is None and first_b is None:
        base.first_move_match = True  # both have no solution
    else:
        base.first_move_match = False

    # Level 3: First move differs
    if not base.first_move_match:
        base.match_level = MatchLevel.SOLUTION_DIFFERS
        base.correct_line_match = False
        base.detail = "Position matches but first correct move differs"
        return base

    # Check correct main line
    correct_a = _extract_correct_line(tree_a.solution_tree)
    correct_b = _extract_correct_line(tree_b.solution_tree)
    base.correct_line_match = correct_a == correct_b

    if not base.correct_line_match:
        base.match_level = MatchLevel.SOLUTION_DIFFERS
        base.detail = "Position matches, first move matches, but correct line diverges"
        return base

    # Correct line matches. Check subset/superset relationship.
    # Level 5: Superset (target contains all source paths + more)
    if paths_a < paths_b:
        base.match_level = MatchLevel.SUPERSET
        base.comments_differ = _check_comments_differ(
            tree_a.solution_tree, tree_b.solution_tree
        )
        base.markers_differ = _check_markers_differ(
            tree_a.solution_tree, tree_b.solution_tree
        )
        base.detail = (
            f"Target is superset of source "
            f"({len(paths_b)} paths vs {len(paths_a)})"
        )
        return base

    # Level 4: Divergent (neither is a subset)
    base.match_level = MatchLevel.DIVERGENT
    base.comments_differ = _check_comments_differ(
        tree_a.solution_tree, tree_b.solution_tree
    )
    base.markers_differ = _check_markers_differ(
        tree_a.solution_tree, tree_b.solution_tree
    )
    base.detail = (
        f"Same correct line but variation branches diverge "
        f"(source={len(paths_a)} paths, target={len(paths_b)} paths)"
    )
    return base


def _get_first_correct_move(tree: SgfTree) -> str | None:
    """Get the first correct move as a string, or None if no solution."""
    if not tree.solution_tree.children:
        return None
    for child in tree.solution_tree.children:
        if child.is_correct and child.move:
            return _node_to_move_str(child)
    return None


def make_error_result(source_file: str, error_msg: str) -> CompareResult:
    """Create a CompareResult for a file that failed to parse."""
    return CompareResult(
        source_file=source_file,
        target_file=None,
        match_level=MatchLevel.UNMATCHED,
        position_hash=None,
        full_hash=None,
        board_size=None,
        player_to_move_source=None,
        player_to_move_target=None,
        pl_status=None,
        first_move_match=None,
        correct_line_match=None,
        source_nodes=None,
        target_nodes=None,
        source_depth=None,
        target_depth=None,
        detail="Parse error",
        error=error_msg,
    )


def make_unmatched_result(
    source_file: str, tree: SgfTree
) -> CompareResult:
    """Create a CompareResult for a source file with no target match."""
    return CompareResult(
        source_file=source_file,
        target_file=None,
        match_level=MatchLevel.UNMATCHED,
        position_hash=position_hash(tree),
        full_hash=full_hash(tree),
        board_size=tree.board_size,
        player_to_move_source=(
            tree.player_to_move.value if _has_explicit_pl(tree) else None
        ),
        player_to_move_target=None,
        pl_status=None,
        first_move_match=None,
        correct_line_match=None,
        source_nodes=count_total_nodes(tree.solution_tree),
        target_nodes=None,
        source_depth=compute_solution_depth(tree.solution_tree),
        target_depth=None,
        detail="No position match in target directory.",
    )


def make_filename_mismatch_result(
    source_file: str, tree_a: SgfTree, tree_b: SgfTree, target_file: str
) -> CompareResult:
    """Create a CompareResult for filename match with different positions."""
    return CompareResult(
        source_file=source_file,
        target_file=target_file,
        match_level=MatchLevel.FILENAME_MISMATCH,
        position_hash=position_hash(tree_a),
        full_hash=full_hash(tree_a),
        board_size=tree_a.board_size,
        player_to_move_source=(
            tree_a.player_to_move.value if _has_explicit_pl(tree_a) else None
        ),
        player_to_move_target=(
            tree_b.player_to_move.value if _has_explicit_pl(tree_b) else None
        ),
        pl_status=_determine_pl_status(tree_a, tree_b),
        first_move_match=None,
        correct_line_match=None,
        source_nodes=count_total_nodes(tree_a.solution_tree),
        target_nodes=count_total_nodes(tree_b.solution_tree),
        source_depth=compute_solution_depth(tree_a.solution_tree),
        target_depth=compute_solution_depth(tree_b.solution_tree),
        detail="Same filename but different board positions",
    )
