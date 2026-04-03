"""
SGF converter — transforms BTP puzzle data into YenGo-compatible SGF strings.

Takes a BTPPuzzle, decodes the board position from the hash, builds the
solution tree from nodes, applies enrichment metadata, and produces a
complete SGF string via SGFBuilder.

Handles:
- Hash decode → board position → initial stones (AB/AW)
- Classic puzzles: 9×9 viewport on 19×19 board (offset detection)
- Solution tree construction via node_parser
- YenGo property enrichment (level, tags, collections, intent)
"""

from __future__ import annotations

import logging

from tools.core.sgf_builder import SGFBuilder
from tools.core.sgf_types import Color, Point

from .config import FULL_BOARD_SIZE, SOURCE_ID
from .enrichment import enrich_puzzle
from .hash_decoder import decode_hash
from .models import BTPPuzzle
from .node_parser import build_solution_tree

logger = logging.getLogger("btp.sgf_converter")


def convert_puzzle_to_sgf(
    puzzle: BTPPuzzle,
    *,
    match_collections: bool = True,
    resolve_intent: bool = True,
) -> str:
    """Convert a BTP puzzle to a YenGo-compatible SGF string.

    Pipeline:
    1. Decode position hash → board rows
    2. Determine board size and offsets (classic = viewport on 19×19)
    3. Extract initial stones (AB/AW)
    4. Build solution tree from BTP nodes
    5. Apply enrichment (level, tags, collections, intent)
    6. Build SGF via SGFBuilder

    Args:
        puzzle: Complete BTP puzzle data.
        match_collections: If True, map BTP categories to YL[] collections.
        resolve_intent: If True, derive C[] objective from categories+tags.

    Returns:
        SGF string.

    Raises:
        ValueError: If puzzle data is invalid.
    """
    # 1. Decode position hash using viewport size (the actual coordinate space)
    viewport_size = puzzle.viewport_size
    board_rows = decode_hash(puzzle.position_hash, viewport_size)

    # 2. Determine actual board size and offsets
    # Classic puzzles (type 0) use a viewport on 19×19
    # AI/Endgame puzzles use the board_size directly
    if puzzle.puzzle_type == 0 and viewport_size < FULL_BOARD_SIZE:
        actual_board_size = FULL_BOARD_SIZE
        # Default offset: place viewport in top-left corner
        # BTP doesn't expose viewport offset, so we assume (0, 0)
        offset_x = 0
        offset_y = 0
    else:
        actual_board_size = viewport_size
        offset_x = 0
        offset_y = 0

    # 3. Build SGF via builder
    builder = SGFBuilder(board_size=actual_board_size)

    # Set player to move
    to_play = Color.BLACK if puzzle.to_play == "B" else Color.WHITE
    builder.set_player_to_move(to_play)

    # 4. Extract initial stones from decoded position
    black_stones: list[Point] = []
    white_stones: list[Point] = []

    for row_idx, row in enumerate(board_rows):
        for col_idx, cell in enumerate(row):
            if cell == "B":
                black_stones.append(Point(x=col_idx + offset_x, y=row_idx + offset_y))
            elif cell == "W":
                white_stones.append(Point(x=col_idx + offset_x, y=row_idx + offset_y))

    builder.add_black_stones(black_stones)
    builder.add_white_stones(white_stones)

    # 5. Build solution tree
    solution_root = build_solution_tree(
        puzzle=puzzle,
        board_rows=board_rows,
        offset_x=offset_x,
        offset_y=offset_y,
    )
    builder.solution_tree = solution_root

    # 6. Apply enrichment
    enrichment = enrich_puzzle(
        rating=puzzle.rating,
        tag_string=puzzle.tags,
        category_letters=puzzle.categories,
    )

    builder.set_level_slug(enrichment["level_slug"])
    builder.set_source(SOURCE_ID)

    if enrichment["yengo_tags"]:
        builder.add_tags(enrichment["yengo_tags"])

    if match_collections and enrichment["collections"]:
        builder.set_collections(enrichment["collections"])

    if resolve_intent and enrichment["intent"]:
        builder.set_comment(enrichment["intent"])

    # Set source metadata as game name (will be overwritten by publish stage)
    builder.set_game_name(f"btp-{puzzle.puzzle_id}")

    return builder.build()


def get_sgf_filename(puzzle: BTPPuzzle) -> str:
    """Generate the SGF filename for a BTP puzzle.

    Uses the pattern ``btp-{puzzle_id}.sgf``.

    Args:
        puzzle: BTP puzzle data.

    Returns:
        Filename string (no directory).
    """
    return f"btp-{puzzle.puzzle_id}.sgf"
