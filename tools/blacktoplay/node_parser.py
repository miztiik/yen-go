"""
BTP node string parser — converts BTP's proprietary node format to SgfNode trees.

BTP node format (semicolon-delimited fields):
    ``id;parent;ko;correct_moves;wrong_moves;standard_response;move_categories``

Correct moves encoding:
    Variable-length groups: 2-char coord + (2-char response OR "-") + child_id + T/F.
    Example: ``ciAHaabF`` = one correct move:
    - "ci" = coord, "AH" (lowercased to "ah") = response, "aab" = child node ID, F = non-terminal

Wrong moves encoding:
    Compressed skip-counts over legal-move enumeration. Each char maps to a count of legal
    moves to skip (0=next legal is wrong, 1=skip 1, etc.). Requires GoEngine to enumerate
    legal moves at each state.

Coordinate system:
    BTP uses 2-char coordinates: column letter (a-s) + row letter (a-s), where 'a'=0.
    This is the same as SGF coordinates.
"""

from __future__ import annotations

import logging

from tools.core.sgf_parser import SgfNode
from tools.core.sgf_types import Color, Point

from .go_engine import BLACK, WHITE, GoEngine
from .models import BTPCorrectMove, BTPNode, BTPPuzzle, BTPWrongMove

logger = logging.getLogger("btp.node_parser")


# BTP coordinate → (x, y) — BTP uses same letter scheme as SGF
def _btp_coord_to_xy(coord: str) -> tuple[int, int]:
    """Convert 2-char BTP coordinate to (x, y).

    BTP: first char = column (a=0), second char = row (a=0).
    Same as SGF coordinate order.
    """
    if len(coord) != 2:
        raise ValueError(f"Invalid BTP coord: {coord!r}")
    x = ord(coord[0]) - ord("a")
    y = ord(coord[1]) - ord("a")
    return x, y


def _xy_to_btp_coord(x: int, y: int) -> str:
    """Convert (x, y) to 2-char BTP coordinate."""
    return chr(ord("a") + x) + chr(ord("a") + y)


def _btp_color_to_engine(color: str) -> int:
    """Convert BTP color string to engine constant."""
    return BLACK if color == "B" else WHITE


def _engine_color_to_sgf(color: int) -> Color:
    """Convert engine color constant to SGF Color enum."""
    return Color.BLACK if color == BLACK else Color.WHITE


# ============================================================================
# Node field parsing
# ============================================================================

def parse_correct_moves(raw: str) -> list[BTPCorrectMove]:
    """Parse correct_moves field from a BTP node string.

    Format: repeating groups of ``{coord:2}{response:2|"-"}{child_id:var}{T|F}``
    - coord: 2-char coordinate of the correct move
    - response: 2-char auto-response, OR single "-" if none
    - child_id: variable-length string node ID (terminated by T/F)
    - terminal: "T" (puzzle done) or "F" (continues)

    This matches the JavaScript parsing logic in btp-tsumego.js.

    Returns:
        List of BTPCorrectMove objects.
    """
    if not raw:
        return []

    moves: list[BTPCorrectMove] = []
    i = 0
    while i < len(raw):
        # Need at least coord (2) + response indicator (1) to continue
        if i + 3 > len(raw):
            break

        # Parse coord (2 chars)
        coord = raw[i : i + 2]
        i += 2

        # Parse response: single "-" OR 2-char coordinate
        if raw[i] == "-":
            response = "-"
            i += 1
        else:
            response = raw[i : i + 2].lower()
            i += 2

        # Parse child_node_id: variable-length string until T or F
        node_name = ""
        while i < len(raw) and raw[i] not in ("T", "F"):
            node_name += raw[i]
            i += 1

        # Parse terminal flag
        is_terminal = False
        if i < len(raw):
            is_terminal = raw[i] == "T"
            i += 1

        moves.append(
            BTPCorrectMove(
                coord=coord,
                response=response,
                child_node_id=node_name,
                is_terminal=is_terminal,
            )
        )

    return moves


def parse_wrong_moves(raw: str, engine: GoEngine, to_play: int) -> list[BTPWrongMove]:
    """Parse wrong_moves field using legal-move enumeration.

    BTP's wrong_moves is a compressed string where each character represents
    a skip count in the enumeration of legal moves. The encoding:
    - Get all legal moves in BTP order (row-by-row, left-to-right)
    - Remove correct moves from the enumeration
    - Each char = skip count: '0'=0, '1'=1, ..., 'A'=10, 'B'=11, etc.
    - After skipping N legal moves, the next legal move is wrong.

    Args:
        raw: The wrong_moves encoded string.
        engine: GoEngine with the current board position loaded.
        to_play: Color to play (BLACK or WHITE engine constant).

    Returns:
        List of BTPWrongMove objects.
    """
    if not raw:
        return []

    # Get all legal moves for the player
    legal_moves = engine.get_legal_moves(to_play)
    if not legal_moves:
        return []

    wrong: list[BTPWrongMove] = []
    move_idx = 0

    for ch in raw:
        skip = _parse_skip_count(ch)
        move_idx += skip

        if move_idx < len(legal_moves):
            x, y = legal_moves[move_idx]
            coord = _xy_to_btp_coord(x, y)
            wrong.append(BTPWrongMove(coord=coord))
            move_idx += 1  # Advance past the wrong move itself
        else:
            break

    return wrong


def _parse_skip_count(ch: str) -> int:
    """Parse a skip-count character from wrong_moves encoding.

    BTP uses: '0'-'9' → 0-9, 'A'-'Z' → 10-35, 'a'-'z' → 36-61
    """
    if "0" <= ch <= "9":
        return ord(ch) - ord("0")
    if "A" <= ch <= "Z":
        return ord(ch) - ord("A") + 10
    if "a" <= ch <= "z":
        return ord(ch) - ord("a") + 36
    return 0


def parse_node_string(raw: str) -> BTPNode:
    """Parse a single BTP node string into a BTPNode.

    Format: ``id;parent;ko;correct_moves;wrong_moves;standard_response;move_categories``

    Node IDs are strings (e.g., "start", "aaa", "aab").

    Args:
        raw: The raw node string from the API.

    Returns:
        BTPNode with parsed fields.
    """
    parts = raw.split(";")
    if len(parts) < 5:
        logger.warning("Node string has fewer than 5 fields: %r", raw)
        return BTPNode(raw=raw)

    node_id = parts[0] if parts[0] else ""
    parent_id = parts[1] if parts[1] else ""
    ko_point = parts[2] if len(parts) > 2 else ""
    correct_raw = parts[3] if len(parts) > 3 else ""
    parts[4] if len(parts) > 4 else ""
    std_response = parts[5] if len(parts) > 5 else ""
    move_cats = parts[6] if len(parts) > 6 else ""

    # Parse correct moves (doesn't need engine)
    correct_moves = parse_correct_moves(correct_raw)

    return BTPNode(
        node_id=node_id,
        parent_id=parent_id,
        ko_point=ko_point,
        correct_moves=correct_moves,
        wrong_moves=[],  # Parsed separately with engine context
        standard_response=std_response,
        move_categories=move_cats,
        raw=raw,
    )


# ============================================================================
# Solution tree building
# ============================================================================


def build_solution_tree(
    puzzle: BTPPuzzle,
    board_rows: list[str],
    offset_x: int = 0,
    offset_y: int = 0,
) -> SgfNode:
    """Build an SgfNode solution tree from BTP puzzle nodes.

    Parses all nodes from the puzzle, then recursively constructs the
    solution tree with correct moves (is_correct=True) and wrong moves
    (is_correct=False with "Wrong" comment).

    Args:
        puzzle: The complete BTP puzzle data.
        board_rows: Decoded board position rows (from hash_decoder).
        offset_x: X offset for coordinate translation (classic viewport).
        offset_y: Y offset for coordinate translation (classic viewport).

    Returns:
        Root SgfNode of the solution tree.
    """
    if not puzzle.nodes:
        return SgfNode()

    to_play_engine = _btp_color_to_engine(puzzle.to_play)
    to_play_sgf = _engine_color_to_sgf(to_play_engine)

    # Parse all nodes - IDs are strings like "start", "aaa", "aab"
    parsed_nodes: dict[str, BTPNode] = {}
    for raw_node in puzzle.nodes:
        node = parse_node_string(raw_node)
        parsed_nodes[node.node_id] = node

    # Initialize engine with board position
    # Use viewport_size (the actual coordinate space used by the puzzle)
    engine = GoEngine(puzzle.viewport_size)
    engine.load_position(board_rows)

    # Build tree recursively from the root node (id="start")
    root = SgfNode()
    if "start" in parsed_nodes:
        _build_subtree(
            root=root,
            btp_node=parsed_nodes["start"],
            all_nodes=parsed_nodes,
            engine=engine,
            current_color=to_play_engine,
            to_play_sgf=to_play_sgf,
            offset_x=offset_x,
            offset_y=offset_y,
            depth=0,
            puzzle_id=puzzle.puzzle_id,
        )

    return root


def _build_subtree(
    root: SgfNode,
    btp_node: BTPNode,
    all_nodes: dict[str, BTPNode],
    engine: GoEngine,
    current_color: int,
    to_play_sgf: Color,
    offset_x: int,
    offset_y: int,
    depth: int,
    puzzle_id: int,
) -> None:
    """Recursively build solution subtree from a BTP node.

    For each correct move at this node:
    1. Create an SgfNode for the player's move (is_correct=True)
    2. If there's an auto-response, create a child node for it
    3. Recurse into the child BTP node

    For wrong moves:
    1. Parse wrong_moves using engine's legal move enumeration
    2. Add each as a leaf SgfNode (is_correct=False)

    Args:
        root: Parent SgfNode to attach children to.
        btp_node: Current BTP node.
        all_nodes: All parsed BTP nodes by ID.
        engine: GoEngine with current board state.
        current_color: Engine color constant for the move to make.
        to_play_sgf: Original player-to-move SGF Color.
        offset_x: X offset for coords.
        offset_y: Y offset for coords.
        depth: Current recursion depth (for safety).
        puzzle_id: BTP puzzle ID for logging.
    """
    if depth > 50:
        logger.warning("Solution tree depth exceeded 50, truncating")
        return

    opp_color = WHITE if current_color == BLACK else BLACK
    opp_sgf = to_play_sgf.opponent()
    player_sgf = _engine_color_to_sgf(current_color)

    # Parse wrong moves with engine context
    wrong_moves = parse_wrong_moves(
        btp_node.raw.split(";")[4] if len(btp_node.raw.split(";")) > 4 else "",
        engine,
        current_color,
    )

    # Add wrong moves as leaf nodes
    for wm in wrong_moves:
        wx, wy = _btp_coord_to_xy(wm.coord)
        sgf_point = Point(x=wx + offset_x, y=wy + offset_y)
        wrong_node = SgfNode(
            move=sgf_point,
            color=player_sgf,
            comment="Wrong",
            is_correct=False,
        )
        root.add_child(wrong_node)

    # Add correct moves (with responses and recursion)
    for cm in btp_node.correct_moves:
        cx, cy = _btp_coord_to_xy(cm.coord)
        sgf_point = Point(x=cx + offset_x, y=cy + offset_y)

        # Create correct move node
        is_leaf = cm.is_terminal and cm.response == "-"
        correct_node = SgfNode(
            move=sgf_point,
            color=player_sgf,
            comment="Correct" if is_leaf else "",
            is_correct=True,
        )
        root.add_child(correct_node)

        if cm.is_terminal:
            # Terminal: mark as correct endpoint
            if not correct_node.comment:
                correct_node.comment = "Correct"
            continue

        # Play the move on engine for subsequent analysis
        engine_copy = engine.copy()
        try:
            engine_copy.play(cx, cy, current_color)
        except ValueError:
            logger.warning(
                "Puzzle %s: Could not play correct move (%d,%d) on engine",
                puzzle_id, cx, cy,
            )
            continue

        # Add auto-response if present
        if cm.response and cm.response != "-":
            rx, ry = _btp_coord_to_xy(cm.response)
            resp_point = Point(x=rx + offset_x, y=ry + offset_y)
            resp_node = SgfNode(
                move=resp_point,
                color=opp_sgf,
                is_correct=True,
            )
            correct_node.add_child(resp_node)

            # Play response on engine
            try:
                engine_copy.play(rx, ry, opp_color)
            except ValueError:
                logger.warning(
                    "Puzzle %s: Could not play response (%d,%d) on engine",
                    puzzle_id, rx, ry,
                )
                continue

            # Recurse into child node
            child_btp = all_nodes.get(cm.child_node_id)
            if child_btp:
                _build_subtree(
                    root=resp_node,
                    btp_node=child_btp,
                    all_nodes=all_nodes,
                    engine=engine_copy,
                    current_color=current_color,
                    to_play_sgf=to_play_sgf,
                    offset_x=offset_x,
                    offset_y=offset_y,
                    depth=depth + 1,
                    puzzle_id=puzzle_id,
                )
        else:
            # No response — recurse directly into child node
            child_btp = all_nodes.get(cm.child_node_id)
            if child_btp:
                _build_subtree(
                    root=correct_node,
                    btp_node=child_btp,
                    all_nodes=all_nodes,
                    engine=engine_copy,
                    current_color=current_color,
                    to_play_sgf=to_play_sgf,
                    offset_x=offset_x,
                    offset_y=offset_y,
                    depth=depth + 1,
                    puzzle_id=puzzle_id,
                )
