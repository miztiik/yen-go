"""Tsumego analysis wrapper — extract position, moves, and branches from KaTrain SGFNode.

Thin wrapper over KaTrain's SGFNode tree, providing tsumego-specific
analysis functions needed by the enrichment pipeline.

Functions migrated from analyzers/sgf_parser.py and adapted for
KaTrain's SGFNode API.
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path

from core.sgf_parser import SGF, ParseError, SGFNode

try:
    from models.position import Color, Position, Stone
except ImportError:
    from ..models.position import Color, Position, Stone

# Import shared correctness inference from tools/core/sgf_correctness.py
_SGF_CORRECTNESS_PATH = (
    Path(__file__).resolve().parent.parent.parent / "core" / "sgf_correctness.py"
)
_spec = importlib.util.spec_from_file_location("sgf_correctness", _SGF_CORRECTNESS_PATH)
_sgf_correctness = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_sgf_correctness)
infer_correctness = _sgf_correctness.infer_correctness


def parse_sgf(sgf_text: str) -> SGFNode:
    """Parse an SGF string into a KaTrain SGFNode tree.

    Wraps SGF.parse_sgf() with a ValueError for consistency with the
    old parser interface.
    """
    sgf_text = sgf_text.strip()
    if not sgf_text:
        raise ValueError("Empty SGF string")
    try:
        return SGF.parse_sgf(sgf_text)
    except ParseError as e:
        raise ValueError(f"SGF parse error: {e}") from e


def extract_position(
    root: SGFNode,
    player_override: Color | None = None,
) -> Position:
    """Extract the initial board position from the root node."""
    bs = root.board_size
    board_size = bs[0]  # KaTrain returns tuple; use first dimension

    if player_override is not None:
        player = player_override
    else:
        player = Color.BLACK
        pl = root.get_property("PL")
        if pl == "W":
            player = Color.WHITE

    stones: list[Stone] = []
    for coord in root.get_list_property("AB"):
        if coord:
            stones.append(Stone.from_sgf(Color.BLACK, coord))
    for coord in root.get_list_property("AW"):
        if coord:
            stones.append(Stone.from_sgf(Color.WHITE, coord))

    return Position(
        board_size=board_size,
        stones=stones,
        player_to_move=player,
        komi=float(root.get_property("KM", "7.5") or "7.5"),
    )


_RIGHT_MARKER_RE = re.compile(r'\b(RIGHT|CHOICERIGHT)\b', re.IGNORECASE)
_MAX_MARKER_DEPTH = 100


def _subtree_has_right_marker(node: SGFNode, depth: int = 0) -> bool:
    if depth > _MAX_MARKER_DEPTH:
        return False
    if _RIGHT_MARKER_RE.search(node.comment):
        return True
    for child in node.children:
        if _subtree_has_right_marker(child, depth + 1):
            return True
    return False


def _find_correct_first_child(root: SGFNode) -> SGFNode | None:
    if not root.children:
        return None
    for child in root.children:
        if _subtree_has_right_marker(child):
            return child
    return root.children[0]


def extract_correct_first_move(root: SGFNode) -> str | None:
    """Extract the SGF coordinate of the correct first move."""
    child = _find_correct_first_child(root)
    if child is None:
        return None
    if child.move is None:
        return None
    return child.move.sgf(root.board_size)


def extract_correct_first_move_color(root: SGFNode) -> Color | None:
    """Extract the color of the correct first move."""
    child = _find_correct_first_child(root)
    if child is None:
        return None
    if child.move is None:
        return None
    player = child.move.player
    return Color.BLACK if player == "B" else Color.WHITE


def extract_wrong_move_branches(root: SGFNode) -> list[dict]:
    """Extract wrong first-move branches from the SGF solution tree.
    Uses three-layer correctness inference + structural fallback."""
    if not root.children:
        return []

    board_size = root.board_size

    children_info: list[dict] = []
    for child in root.children:
        if child.move is None:
            continue
        coord = child.move.sgf(board_size)
        comment = child.comment
        # Flatten properties for correctness inference
        flat_props = {k: v[0] for k, v in child.properties.items() if v}
        result = infer_correctness(comment, flat_props)

        source = ""
        if result is False:
            if "WV" in child.properties:
                source = "WV[]"
            elif "BM" in child.properties:
                source = "BM[]"
            elif "TR" in child.properties:
                source = "TR[]"
            elif comment:
                stripped = comment.strip()
                lower = stripped.lower()
                if lower.startswith("wrong"):
                    source = "C[Wrong...]"
                elif lower.startswith("incorrect"):
                    source = "C[Incorrect...]"
                elif stripped == "-":
                    source = "C[-]"
                else:
                    source = "comment"

        children_info.append({
            "child": child, "coord": coord, "comment": comment,
            "result": result, "source": source,
        })

    if not children_info:
        return []

    has_explicit_correct = any(c["result"] is True for c in children_info)
    unknowns = [c for c in children_info if c["result"] is None]

    for info in unknowns:
        if has_explicit_correct:
            info["result"] = False
            info["source"] = "fallback:non-correct"
        elif children_info[0] is not info:
            info["result"] = False
            info["source"] = "fallback:positional"
        else:
            info["result"] = True
            info["source"] = ""

    wrong_branches: list[dict] = []
    for info in children_info:
        if info["result"] is False:
            wrong_branches.append({
                "move": info["coord"], "source": info["source"],
                "comment": info["comment"],
            })
    return wrong_branches


def _pick_correct_child(node: SGFNode) -> SGFNode | None:
    return _find_correct_first_child(node)


def extract_solution_tree_moves(root: SGFNode) -> list[str]:
    """Extract the main correct line as a list of SGF coordinates."""
    board_size = root.board_size
    moves: list[str] = []
    node = root
    while node.children:
        node = _pick_correct_child(node) or node.children[0]
        if node.move:
            moves.append(node.move.sgf(board_size))
    return moves


def count_solution_branches(root: SGFNode) -> int:
    """Count branching points along the correct main line."""
    count = 0
    node = root
    while node.children:
        if len(node.children) > 1:
            count += 1
        node = _pick_correct_child(node) or node.children[0]
    return count


def compose_enriched_sgf(
    root: SGFNode,
    refutation_branches: list[dict] | None = None,
) -> str:
    """Compose enriched SGF from a KaTrain SGFNode tree with optional refutation branches."""
    return "(" + _compose_node(root, refutation_branches, is_root=True) + ")"


# ── Internal composition ──

def _compose_node(node: SGFNode, refutation_branches: list[dict] | None, is_root: bool = False) -> str:
    parts: list[str] = [";"]
    for key, values in node.properties.items():
        parts.append(key + "".join(f"[{val}]" for val in values))
    result = "".join(parts)

    if node.children:
        if len(node.children) == 1 and not (is_root and refutation_branches):
            result += _compose_node(node.children[0], None)
        else:
            for child in node.children:
                result += "(" + _compose_node(child, None) + ")"
            if is_root and refutation_branches:
                for ref in refutation_branches:
                    result += "(" + _compose_refutation(ref) + ")"
    elif is_root and refutation_branches:
        for ref in refutation_branches:
            result += "(" + _compose_refutation(ref) + ")"

    return result


def _compose_refutation(ref: dict) -> str:
    color = ref.get("color", "B")
    wrong_move = ref["wrong_move"]
    comment = ref.get("comment", "Wrong.")
    refutation = ref.get("refutation", [])
    parts = [f";{color}[{wrong_move}]C[{comment}]"]
    for move_color, move_coord in refutation:
        parts.append(f";{move_color}[{move_coord}]")
    return "".join(parts)
