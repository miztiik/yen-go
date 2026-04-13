"""Minimal SGF parser — extracts position, correct move, and solution tree.

Uses core/sgf_parser.py (KaTrain-derived, pure-Python) internally, exposing
a simplified SgfNode tree interface for the enrichment pipeline.

Consciously duplicated from backend/puzzle_manager for isolation.
This parser handles the subset of SGF needed for tsumego analysis.
"""

from __future__ import annotations

import importlib.util
import re
from dataclasses import dataclass, field
from pathlib import Path

try:
    from core.sgf_parser import SGF as CoreSGF
    from models.position import Color, Position, Stone
except ImportError:
    from ..core.sgf_parser import SGF as CoreSGF
    from ..models.position import Color, Position, Stone

# Import shared correctness inference from tools/core/sgf_correctness.py
# Direct spec-based import to avoid triggering tools/core/__init__.py
# (which depends on the full tools package).
_SGF_CORRECTNESS_PATH = (
    Path(__file__).resolve().parent.parent.parent / "core" / "sgf_correctness.py"
)
_spec = importlib.util.spec_from_file_location("sgf_correctness", _SGF_CORRECTNESS_PATH)
_sgf_correctness = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_sgf_correctness)
infer_correctness = _sgf_correctness.infer_correctness


@dataclass
class SgfNode:
    """A node in the SGF game tree."""
    properties: dict[str, list[str]] = field(default_factory=dict)
    children: list[SgfNode] = field(default_factory=list)
    parent: SgfNode | None = field(default=None, repr=False)

    def get(self, key: str, default: str = "") -> str:
        """Get first value for a property key."""
        vals = self.properties.get(key, [])
        return vals[0] if vals else default

    def get_all(self, key: str) -> list[str]:
        """Get all values for a property key."""
        return self.properties.get(key, [])

    @property
    def move(self) -> tuple[Color, str] | None:
        """Extract move from this node, if any. Returns (Color, sgf_coord)."""
        if "B" in self.properties:
            return (Color.BLACK, self.get("B"))
        if "W" in self.properties:
            return (Color.WHITE, self.get("W"))
        return None

    @property
    def comment(self) -> str:
        return self.get("C")


def parse_sgf(sgf_text: str) -> SgfNode:
    """Parse an SGF string into a tree of SgfNode objects.

    Uses core/sgf_parser.py (KaTrain-derived) as the underlying parser.
    Converts the core SGFNode tree into our SgfNode tree for a consistent
    interface across the enrichment pipeline.

    Handles nested variations: (;B[cd](;W[dc])(;W[dd]))
    """
    sgf_text = sgf_text.strip()
    if not sgf_text:
        raise ValueError("Empty SGF string")

    try:
        core_root = CoreSGF.parse_sgf(sgf_text)
    except Exception as e:
        raise ValueError(f"SGF parse error: {e}") from e

    return _convert_core_node(core_root)


def extract_position(
    root: SgfNode,
    player_override: Color | None = None,
) -> Position:
    """Extract the initial board position from the root node.

    Args:
        root: Root SgfNode of the parsed SGF.
        player_override: If provided, use this color instead of PL property.
            Useful when PL is absent and color is inferred from the first
            correct move (see extract_correct_first_move_color).
    """
    board_size = int(root.get("SZ", "19").split(":")[0])

    # Determine player to move
    if player_override is not None:
        player = player_override
    else:
        player = Color.BLACK
        pl = root.get("PL")
        if pl == "W":
            player = Color.WHITE

    stones: list[Stone] = []

    # Setup stones (AB, AW)
    for coord in root.get_all("AB"):
        if coord:
            stones.append(Stone.from_sgf(Color.BLACK, coord))
    for coord in root.get_all("AW"):
        if coord:
            stones.append(Stone.from_sgf(Color.WHITE, coord))

    return Position(
        board_size=board_size,
        stones=stones,
        player_to_move=player,
        komi=float(root.get("KM", "7.5") or "7.5"),
    )


_RIGHT_MARKER_RE = re.compile(r'\b(RIGHT|CHOICERIGHT)\b', re.IGNORECASE)
_MAX_MARKER_DEPTH = 100


def _subtree_has_right_marker(node: SgfNode, depth: int = 0) -> bool:
    """Check if a node or any descendant contains a RIGHT/CHOICERIGHT comment.

    Some SGF sources (e.g., goproblems.com) mark the correct variation
    with 'RIGHT' in the comment text rather than placing it first.
    Uses word-boundary matching to avoid false positives from 'copyright',
    'upright', etc.
    """
    if depth > _MAX_MARKER_DEPTH:
        return False
    if _RIGHT_MARKER_RE.search(node.comment):
        return True
    for child in node.children:
        if _subtree_has_right_marker(child, depth + 1):
            return True
    return False


def _find_correct_first_child(root: SgfNode) -> SgfNode | None:
    """Find the correct first child, preferring RIGHT-marked subtrees.

    Returns the first child whose subtree contains a RIGHT/CHOICERIGHT marker,
    or root.children[0] as fallback (standard SGF convention).
    Returns None if no children exist.
    """
    if not root.children:
        return None
    for child in root.children:
        if _subtree_has_right_marker(child):
            return child
    return root.children[0]


def extract_correct_first_move(root: SgfNode) -> str | None:
    """Extract the correct first move from the solution tree.

    Priority:
    1. If any child variation contains a RIGHT/CHOICERIGHT marker in its
       subtree, pick that child as the correct line.
    2. Otherwise, fall back to children[0] (standard SGF convention where
       the first variation is the main/correct line).

    Returns SGF coordinate of the first correct move, or None if no move.
    """
    child = _find_correct_first_child(root)
    if child is None:
        return None
    move = child.move
    return move[1] if move else None


def extract_correct_first_move_color(root: SgfNode) -> Color | None:
    """Extract the color of the first correct move.

    Useful for inferring player_to_move when PL property is absent.
    Uses the same RIGHT-marker priority as extract_correct_first_move.
    Returns None if no move found.
    """
    child = _find_correct_first_child(root)
    if child is None:
        return None
    move = child.move
    return move[0] if move else None


def extract_wrong_move_branches(root: SgfNode) -> list[dict]:
    """Extract wrong first-move branches from the SGF solution tree.

    Uses the three-layer correctness inference system from
    ``tools/core/sgf_correctness.py`` plus a structural fallback:

      Layer 1: SGF markers — WV[], BM[], TR[] → wrong; TE[], IT[] → correct
      Layer 2: Comment text — C[Wrong...], C[Incorrect...], C[-] → wrong;
               C[Correct...], C[Right...], C[+] → correct
      Layer 3: Structural fallback — if ≥1 sibling is explicitly correct,
               remaining unknowns are wrong. Else children[0] = correct,
               rest = wrong. (Only applied when Layers 1-2 are silent.)

    Walk root.children to identify branches. Each child must have a B[] or
    W[] move property (non-move nodes like setup nodes are skipped).

    Returns:
        List of dicts, each: {"move": "ab", "source": "WV[]", "comment": "Wrong."}
        ``source`` indicates which detection layer fired:
          - "WV[]", "BM[]", "TR[]" (Layer 1 markers)
          - "C[Wrong...]", "C[Incorrect...]", "C[-]" (Layer 2 comment)
          - "fallback:non-correct" (Layer 3 — sibling was explicitly correct)
          - "fallback:positional" (Layer 3 — no explicit signals, children[0] assumed correct)
    """
    if not root.children:
        return []

    # First pass: classify every child using Layers 1-2
    children_info: list[dict] = []
    for child in root.children:
        move = child.move
        if move is None:
            continue  # skip non-move nodes

        coord = move[1]
        comment = child.comment
        props = child.properties

        # Build a flat property dict for infer_correctness (expects dict[str, str])
        flat_props = {k: v[0] for k, v in props.items() if v}
        result = infer_correctness(comment, flat_props)

        # Determine source label for wrong moves
        source = ""
        if result is False:
            if "WV" in props:
                source = "WV[]"
            elif "BM" in props:
                source = "BM[]"
            elif "TR" in props:
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
            "child": child,
            "coord": coord,
            "comment": comment,
            "result": result,  # True/False/None
            "source": source,
        })

    if not children_info:
        return []

    # Count explicit correct / wrong
    has_explicit_correct = any(c["result"] is True for c in children_info)
    unknowns = [c for c in children_info if c["result"] is None]

    # Second pass: Layer 3 fallback for unknown children
    for info in unknowns:
        if has_explicit_correct:
            # At least one sibling is explicitly correct → unknowns are wrong
            info["result"] = False
            info["source"] = "fallback:non-correct"
        elif children_info[0] is not info:
            # No explicit correct signals anywhere → children[0] = correct, rest = wrong
            info["result"] = False
            info["source"] = "fallback:positional"
        else:
            # This IS children[0] and no explicit signals → assume correct
            info["result"] = True
            info["source"] = ""

    # Collect wrong branches
    wrong_branches: list[dict] = []
    for info in children_info:
        if info["result"] is False:
            wrong_branches.append({
                "move": info["coord"],
                "source": info["source"],
                "comment": info["comment"],
            })

    return wrong_branches


def _pick_correct_child(node: SgfNode) -> SgfNode | None:
    """Pick the correct child variation, preferring RIGHT-marked subtrees.

    Delegates to _find_correct_first_child for consistent behavior.
    """
    return _find_correct_first_child(node)


def extract_solution_tree_moves(root: SgfNode) -> list[str]:
    """Extract the main-line solution sequence (SGF coords).

    Follows RIGHT-marked variations when available, otherwise first child.
    """
    moves: list[str] = []
    node = root
    while node.children:
        node = _pick_correct_child(node) or node.children[0]
        move = node.move
        if move:
            moves.append(move[1])
    return moves


def count_solution_branches(root: SgfNode) -> int:
    """Count branching points in the correct solution tree (Phase R.3.2).

    A branching point is a node in the correct variation where >1 child exists.
    This measures reading complexity: more branches = more variations to read.

    Walks the correct path (RIGHT-marked or first child) and counts nodes
    where len(children) > 1 along that path.

    Returns:
        Number of branching points in the correct solution tree.
    """
    count = 0
    node = root
    while node.children:
        if len(node.children) > 1:
            count += 1
        node = _pick_correct_child(node) or node.children[0]
    return count


def compose_enriched_sgf(
    root: SgfNode,
    refutation_branches: list[dict] | None = None,
) -> str:
    """Compose an enriched SGF string from the tree + new branches.

    refutation_branches: list of {"wrong_move": "cd", "color": "B",
        "refutation": [("W","dc"),("B","dd")], "comment": "..."}
    """
    return "(" + _compose_node(root, refutation_branches, is_root=True) + ")"


# ── Internal parsing (core/sgf_parser-based) ──


def _convert_core_node(core_node) -> SgfNode:
    """Recursively convert a core SGFNode to our SgfNode."""
    props = dict(core_node.properties)
    node = SgfNode(properties=props)

    for child in core_node.children:
        child_node = _convert_core_node(child)
        child_node.parent = node
        node.children.append(child_node)

    return node


# ── Internal composition ──

def _compose_node(
    node: SgfNode,
    refutation_branches: list[dict] | None,
    is_root: bool = False,
) -> str:
    """Recursively compose a node and its children into SGF string."""
    parts: list[str] = [";"]

    # Properties — use canonical SGF format: KEY[val1][val2] (not KEY[val1]KEY[val2])
    for key, values in node.properties.items():
        parts.append(key + "".join(f"[{val}]" for val in values))

    result = "".join(parts)

    if node.children:
        if len(node.children) == 1 and not (is_root and refutation_branches):
            # Single child — continue sequence
            result += "\n" + _compose_node(node.children[0], None)
        else:
            # Multiple children — each in parentheses
            for child in node.children:
                result += "\n(" + _compose_node(child, None) + ")"

            # Add refutation branches at root level
            if is_root and refutation_branches:
                for ref in refutation_branches:
                    result += "\n(" + _compose_refutation(ref) + ")"
    elif is_root and refutation_branches:
        # Root has no existing children but we're adding refutations
        for ref in refutation_branches:
            result += "\n(" + _compose_refutation(ref) + ")"

    return result


def _compose_refutation(ref: dict) -> str:
    """Compose a refutation branch into SGF."""
    color = ref.get("color", "B")
    wrong_move = ref["wrong_move"]
    comment = ref.get("comment", "Wrong.")
    refutation = ref.get("refutation", [])

    parts = [f";{color}[{wrong_move}]C[{comment}]"]
    for move_color, move_coord in refutation:
        parts.append(f";{move_color}[{move_coord}]")

    return "\n".join(parts)
