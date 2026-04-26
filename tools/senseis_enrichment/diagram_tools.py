"""Diagram SGF parsing, branch matching, and coordinate resolution.

Extracts move sequences, LB[] labels, and visual markup from Senseis
diagram SGFs, matches them against local solution tree branches, and
resolves label/move references in commentary text to SGF coordinates.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from tools.core.sgf_parser import SgfNode, parse_sgf
from tools.core.sgf_types import Point
from tools.senseis_enrichment.models import PositionTransform
from tools.senseis_enrichment.position_matcher import transform_point

logger = logging.getLogger("senseis_enrichment.diagram_tools")

# SGF markup properties that take a list of point coordinates.
_POINT_MARKERS = frozenset({"SQ", "TR", "CR", "MA", "SL"})

# SGF markup properties that take composed point:point pairs.
_COMPOSED_MARKERS = frozenset({"AR", "LN"})

# All visual markup properties (excluding LB, handled separately).
ALL_MARKER_PROPERTIES = _POINT_MARKERS | _COMPOSED_MARKERS


@dataclass
class DiagramMoveSequence:
    """Parsed move sequence, labels, and markers from a Senseis diagram SGF."""

    moves: list[tuple[str, str]] = field(default_factory=list)
    """[(color, sgf_coord), ...] e.g. [("B", "ap"), ("W", "bo")]"""

    labels: dict[str, str] = field(default_factory=dict)
    """letter -> sgf_coord, e.g. {"a": "an", "x": "bq"}"""

    move_comments: dict[int, str] = field(default_factory=dict)
    """move_index -> C[] comment text from that move node"""

    markers: dict[str, set[str]] = field(default_factory=dict)
    """SGF marker properties aggregated from all nodes.
    Maps property name (SQ, TR, CR, MA, SL, AR, LN) to set of raw values.
    Point markers: bare coords ("db", "fb").
    Composed markers: "coord:coord" pairs ("ab:cd")."""


def extract_labels_from_property(lb_value: str) -> dict[str, str]:
    """Parse LB property value into {letter: sgf_coord} map.

    LB is stored as comma-joined pairs: "an:a,ao:b,bo:c,bq:x"
    """
    labels: dict[str, str] = {}
    if not lb_value:
        return labels
    for pair in lb_value.split(","):
        pair = pair.strip()
        if ":" in pair:
            coord, letter = pair.split(":", 1)
            if len(coord) == 2 and letter:
                labels[letter] = coord
    return labels


def _collect_labels(root: SgfNode) -> dict[str, str]:
    """Collect all LB[] labels from root and all descendant nodes."""
    labels: dict[str, str] = {}

    # Root labels
    lb = root.properties.get("LB", "")
    labels.update(extract_labels_from_property(lb))

    # Walk all nodes
    node = root
    while node.children:
        node = node.children[0]
        lb = node.properties.get("LB", "")
        labels.update(extract_labels_from_property(lb))

    return labels


def _collect_markers_from_node(
    node: SgfNode, markers: dict[str, set[str]],
) -> None:
    """Collect visual markup properties (SQ/TR/CR/MA/SL/AR/LN) from a node."""
    for prop in ALL_MARKER_PROPERTIES:
        value = node.properties.get(prop, "")
        if not value:
            continue
        if prop not in markers:
            markers[prop] = set()
        for item in value.split(","):
            item = item.strip()
            if item:
                markers[prop].add(item)


def parse_diagram_sgf(sgf_content: str) -> DiagramMoveSequence:
    """Parse a Senseis diagram SGF into structured move data.

    Walks the linear diagram (no branching expected) to extract
    the move sequence, LB[] labels, visual markers, and per-move comments.
    """
    result = DiagramMoveSequence()

    if not sgf_content or not sgf_content.strip():
        return result

    try:
        tree = parse_sgf(sgf_content)
    except Exception as e:
        logger.warning("Failed to parse diagram SGF: %s", e)
        return result

    # Collect labels from all nodes (root + moves + trailing label nodes)
    result.labels = _collect_labels(tree.solution_tree)

    # Collect markers from root node
    markers: dict[str, set[str]] = {}
    _collect_markers_from_node(tree.solution_tree, markers)

    # Walk the linear move sequence
    node = tree.solution_tree
    move_index = 0
    while node.children:
        node = node.children[0]
        _collect_markers_from_node(node, markers)
        if node.move and node.color:
            result.moves.append((node.color.value, node.move.to_sgf()))
            if node.comment:
                result.move_comments[move_index] = node.comment
            move_index += 1

    result.markers = markers
    return result


def find_matching_branch(
    local_root: SgfNode,
    diagram_moves: list[tuple[str, str]],
    transform: PositionTransform | None,
    board_size: int,
) -> tuple[SgfNode | None, int]:
    """Walk local solution tree following the diagram's move sequence.

    Applies coordinate transform to diagram moves before comparing
    with local tree nodes. Handles branching in the local tree.

    Returns:
        (last_matching_node, match_depth): the deepest node where the
        diagram's moves still match the local tree. depth is 0-based
        count of matched moves. Returns (None, 0) if not even the
        first move matches.
    """
    if not diagram_moves:
        return local_root, 0

    current = local_root
    matched_depth = 0

    for color_str, sgf_coord in diagram_moves:
        # Transform diagram coordinate to local space
        if transform:
            p = Point.from_sgf(sgf_coord)
            p = transform_point(p, board_size, transform)
            local_coord = p.to_sgf()
        else:
            local_coord = sgf_coord

        # Search children for matching move
        found = False
        for child in current.children:
            if (
                child.color
                and child.color.value == color_str
                and child.move
                and child.move.to_sgf() == local_coord
            ):
                current = child
                matched_depth += 1
                found = True
                break

        if not found:
            break

    if matched_depth == 0:
        return None, 0
    return current, matched_depth


def _replace_move_refs(text: str, known: dict[str, str]) -> str:
    """Replace B1/W2/etc. move references in text.

    Known refs (in the diagram's move sequence) become coordinates.
    Unknown refs become 'Black' or 'White'.
    Only replaces at word boundaries to avoid mangling other text.
    """
    out: list[str] = []
    i = 0
    while i < len(text):
        if text[i] in ("B", "W") and (i == 0 or not text[i - 1].isalnum()):
            # Possibly a move ref — read digits after B/W
            j = i + 1
            while j < len(text) and text[j].isdigit():
                j += 1
            if j > i + 1 and (j >= len(text) or not text[j].isalnum()):
                ref = text[i:j]
                if ref in known:
                    out.append(known[ref])
                else:
                    out.append("Black" if text[i] == "B" else "White")
                i = j
                continue
        out.append(text[i])
        i += 1
    return "".join(out)


def resolve_label_references(
    commentary: str,
    labels: dict[str, str],
    moves: list[tuple[str, str]],
    transform: PositionTransform | None,
    board_size: int,
) -> str:
    """Resolve label and move references in commentary to board coordinates.

    Transforms:
    - 'a', 'b', 'x', 'y' etc. -> 'a'(A14) using LB[] label map
    - B1, W2, B3 etc. -> B1(A4) using move sequence coordinates

    Coordinates are transformed from Senseis to local space if needed.
    """
    if not commentary:
        return commentary

    result = commentary

    # --- Step 1: Resolve move number references FIRST (B1, W2, B3, etc.) ---
    # Must happen before label resolution, because labels resolve to
    # coordinates like "B5" which would be misinterpreted as move refs.
    move_ref_map: dict[str, str] = {}
    for i, (color_str, sgf_coord) in enumerate(moves):
        move_num = i + 1
        ref = f"{color_str}{move_num}"

        if transform:
            p = Point.from_sgf(sgf_coord)
            p = transform_point(p, board_size, transform)
            local_coord = p.to_sgf()
        else:
            local_coord = sgf_coord

        move_ref_map[ref] = local_coord

    result = _replace_move_refs(result, move_ref_map)

    # --- Step 2: Resolve label references ('a', 'b', 'x', 'y', etc.) ---
    for letter, sgf_coord in labels.items():
        if transform:
            p = Point.from_sgf(sgf_coord)
            p = transform_point(p, board_size, transform)
            local_coord = p.to_sgf()
        else:
            local_coord = sgf_coord

        result = result.replace(f"'{letter}'", local_coord)

    return result
