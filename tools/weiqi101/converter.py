"""
qqdata → SGF conversion for 101weiqi puzzles.

Converts parsed PuzzleData into SGF format with YenGo custom properties.
Builds the solution tree from the hierarchical `andata` structure.
Chinese text in solution comments is translated via ChineseTranslator.
"""

from __future__ import annotations

import json
import logging
import uuid

from tools.core.chinese_translator import translate_chinese_text

from .levels import map_level
from .models import PuzzleData, SolutionNode
from .tags import map_tag

logger = logging.getLogger("101weiqi.converter")


def escape_sgf_text(text: str) -> str:
    """Escape special SGF characters in text."""
    return text.replace("\\", "\\\\").replace("]", "\\]")


def _stones_to_sgf(color_prefix: str, stones: list[str]) -> str:
    """Convert a list of SGF coordinates to AB[] or AW[] property.

    Args:
        color_prefix: "AB" or "AW"
        stones: List of SGF coordinates (e.g., ["pd", "qd"])

    Returns:
        SGF property string, e.g., "AB[pd][qd]"
    """
    if not stones:
        return ""
    coords = "][".join(stones)
    return f"{color_prefix}[{coords}]"


def _build_solution_tree(
    nodes: dict[int, SolutionNode],
    node_id: int,
    is_black: bool,
) -> str:
    """Recursively build the SGF solution tree from andata nodes.

    Single-child paths are inlined. Multiple children create SGF
    variation branches with `()`.

    Args:
        nodes: All solution nodes keyed by ID.
        node_id: Current node ID to process.
        is_black: Whether the current move is black.

    Returns:
        SGF string fragment for this subtree.
    """
    if node_id not in nodes:
        return ""

    node = nodes[node_id]
    coord = node.coordinate

    move_sgf = ""
    if coord:
        color = "B" if is_black else "W"
        move_sgf = f";{color}[{coord}]"

        if node.is_correct:
            move_sgf += "C[Correct]"
        elif node.is_failure:
            move_sgf += "C[Wrong]"
        elif node.comment:
            translated = translate_chinese_text(node.comment)
            move_sgf += f"C[{escape_sgf_text(translated)}]"

    children = node.children
    if children:
        next_black = not is_black if coord else is_black

        if len(children) == 1:
            child_sgf = _build_solution_tree(nodes, children[0], next_black)
            return move_sgf + child_sgf
        else:
            parts = [move_sgf] if move_sgf else []
            for child_id in children:
                child_sgf = _build_solution_tree(nodes, child_id, next_black)
                if child_sgf:
                    parts.append(f"({child_sgf})")
            return "\n".join(parts)

    return move_sgf


def convert_puzzle_to_sgf(
    puzzle: PuzzleData,
    *,
    root_comment: str | None = None,
    collection_entries: list[str] | None = None,
    yx_string: str | None = None,
) -> str:
    """Convert a PuzzleData to a complete SGF string.

    Generates SGF with YenGo custom properties:
    - FF[4], GM[1], CA[UTF-8], SZ[] (mandatory)
    - YG[] (level slug from levelname, calibrated)
    - YT[] (tag from qtypename)
    - YX[] (complexity metrics)
    - YL[] (collection membership, with optional :CHAPTER/POSITION sequence)
    - YM[] (pipeline metadata: trace_id + original filename)
    - PL[] (player to move)
    - C[] (root comment / intent)
    - AB[], AW[] (setup stones)
    - Move C[] comments (Correct/Wrong)

    Excluded (per spec): GN[], PC[], EV[], SO[], YQ[] (pipeline job)

    Args:
        puzzle: Parsed puzzle data.
        root_comment: Optional intent text for root C[].
        collection_entries: Optional list of YL entries. Each entry is either
            a bare slug ("life-and-death") or slug with sequence
            ("cho-chikun-elementary:3/12").
        yx_string: Optional pre-formatted YX[] value string.

    Returns:
        Complete SGF string.
    """
    parts = [
        "(;FF[4]GM[1]CA[UTF-8]",
        f"SZ[{puzzle.board_size}]",
    ]

    # YG[] level from Chinese rank (with calibration)
    level_slug = map_level(puzzle.level_name)
    if level_slug:
        parts.append(f"YG[{level_slug}]")

    # YT[] tag from Chinese category
    tag = map_tag(puzzle.type_name)
    if tag:
        parts.append(f"YT[{tag}]")

    # YX[] complexity metrics
    if yx_string:
        parts.append(f"YX[{yx_string}]")

    # YL[] collection membership (v14: supports slug:CHAPTER/POSITION)
    if collection_entries:
        parts.append(f"YL[{','.join(collection_entries)}]")

    # YM[] pipeline metadata (trace_id + original filename for traceability)
    trace_id = uuid.uuid4().hex[:16]
    ym_meta: dict[str, str] = {"t": trace_id}
    ym_meta["f"] = f"{puzzle.puzzle_id}.sgf"
    parts.append(f"YM[{json.dumps(ym_meta, separators=(',', ':'))}]")

    # Player to move
    parts.append(f"PL[{puzzle.player_to_move}]")

    # Root C[] intent comment
    if root_comment:
        parts.append(f"C[{escape_sgf_text(root_comment)}]")

    # Setup stones
    ab = _stones_to_sgf("AB", puzzle.black_stones)
    if ab:
        parts.append(ab)

    aw = _stones_to_sgf("AW", puzzle.white_stones)
    if aw:
        parts.append(aw)

    # Solution tree
    if puzzle.solution_nodes:
        is_black = puzzle.first_hand == 1
        solution_sgf = _build_solution_tree(
            puzzle.solution_nodes, 0, is_black
        )
        if solution_sgf:
            parts.append(solution_sgf)

    parts.append(")")
    return "\n".join(parts)
