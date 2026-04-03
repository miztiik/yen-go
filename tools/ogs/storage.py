"""
File storage for downloaded OGS puzzles.

Saves SGF files with proper formatting in batch directories.

SGF Properties (per YenGo spec):
- FF[4], GM[1], CA[UTF-8], SZ[] (mandatory SGF)
- PL[] (player to move)
- AB[], AW[] (initial stones)
- YG[] (level slug from puzzle_rank mapping)
- YT[] (tags from puzzle_type)
- YL[] (collection slugs, comma-separated, from --match-collections)
- Root C[] (objective from puzzle_intent, optional, from --resolve-intent)
- Move C[] comments preserved for correct/wrong feedback

Excluded (per project spec):
- GN[], PC[], EV[] (not needed for tsumego)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from tools.core.paths import rel_path

from .batching import get_batch_for_file, get_batch_for_file_fast
from .config import DEFAULT_BATCH_SIZE, get_sgf_dir
from .converter import (
    escape_sgf_text,
    initial_state_to_sgf,
    move_tree_to_sgf,
)
from .index import add_to_index
from .levels import map_puzzle_rank_to_level
from .models import OGSPuzzleDetail
from .tags import map_puzzle_type_to_tag

if TYPE_CHECKING:
    from .checkpoint import OGSCheckpoint


logger = logging.getLogger("ogs.storage")


def convert_puzzle_to_sgf(
    puzzle: OGSPuzzleDetail,
    extra_tags: list[str] | None = None,
    collection_slugs: list[str] | None = None,
    root_comment: str | None = None,
) -> str:
    """Convert OGS puzzle to SGF format.

    Generates SGF with YenGo custom properties:
    - FF[4], GM[1], CA[UTF-8], SZ[] (mandatory SGF)
    - YG[] (level slug from puzzle_rank)
    - YT[] (tags from puzzle_type + extra_tags, deduplicated & sorted)
    - YL[] (collection slugs, when --match-collections enabled)
    - PL[] (player to move)
    - AB[], AW[] (initial stones)
    - Root C[] (puzzle objective, when --resolve-intent enabled)

    Excluded properties (per project spec):
    - GN[] (game name)
    - PC[] (place/source)
    - EV[] (event/name)

    Move comments (C[Correct!], C[Wrong]) are preserved.

    Args:
        puzzle: Parsed OGS puzzle detail
        extra_tags: Optional additional tags (e.g. from objective parsing)
            to merge with puzzle_type tag in YT[]
        collection_slugs: Optional list of collection slugs for YL[]
            property (comma-separated, sorted alphabetically)
        root_comment: Optional objective text for root C[] comment

    Returns:
        Complete SGF string
    """
    p = puzzle.puzzle

    # Build SGF header - only mandatory properties
    parts = [
        "(;FF[4]GM[1]CA[UTF-8]",
        f"SZ[{p.width}]",
    ]

    # Add YG[] level from puzzle_rank
    if hasattr(p, 'puzzle_rank'):
        level_slug = map_puzzle_rank_to_level(p.puzzle_rank)
        parts.append(f"YG[{level_slug}]")
        logger.debug(f"Puzzle {puzzle.id}: rank {p.puzzle_rank} → YG[{level_slug}]")

    # Build YT[] from puzzle_type + extra_tags, deduplicated & sorted
    all_tags: list[str] = []
    puzzle_type = p.puzzle_type if hasattr(p, 'puzzle_type') else None
    if puzzle_type:
        tag = map_puzzle_type_to_tag(puzzle_type)
        if tag:
            all_tags.append(tag)
            logger.debug(f"Puzzle {puzzle.id}: '{puzzle_type}' → tag '{tag}'")

    if extra_tags:
        all_tags.extend(extra_tags)

    if all_tags:
        unique_sorted = sorted(set(all_tags))
        parts.append(f"YT[{','.join(unique_sorted)}]")
        logger.debug(f"Puzzle {puzzle.id}: YT[{','.join(unique_sorted)}]")

    # Add YL[] collection membership (multi-slug, comma-separated)
    if collection_slugs:
        yl_value = ",".join(collection_slugs)
        parts.append(f"YL[{yl_value}]")
        logger.debug(f"Puzzle {puzzle.id}: YL[{yl_value}]")

    # Player to move
    first_player = "B" if p.initial_player.lower() == "black" else "W"
    parts.append(f"PL[{first_player}]")

    # Add initial stones
    stone_props = initial_state_to_sgf(p.initial_state)
    if stone_props:
        parts.append(stone_props)

    # Root C[] comment with puzzle objective (from intent resolution)
    if root_comment:
        escaped = escape_sgf_text(root_comment)
        parts.append(f"C[{escaped}]")
        logger.debug(f"Puzzle {puzzle.id}: C[{root_comment}]")

    # Add move tree (solution variations) - includes move comments
    move_sgf = move_tree_to_sgf(p.move_tree, first_player)
    if move_sgf:
        parts.append(move_sgf)

    # Close SGF
    parts.append(")")

    return "\n".join(parts)


def generate_puzzle_filename(puzzle: OGSPuzzleDetail) -> str:
    """Generate filename for puzzle.

    Format: {puzzle_id}.sgf (no 'ogs-' prefix)

    Note: Earlier versions used 'ogs-{id}.sgf' format. The index rebuild
    handles both formats for backwards compatibility.

    Args:
        puzzle: Parsed puzzle detail

    Returns:
        Filename string (e.g., '20508.sgf')
    """
    return f"{puzzle.id}.sgf"


def save_puzzle(
    puzzle: OGSPuzzleDetail,
    output_dir: Path,
    batch_size: int = DEFAULT_BATCH_SIZE,
    checkpoint: OGSCheckpoint | None = None,
    extra_tags: list[str] | None = None,
    collection_slugs: list[str] | None = None,
    root_comment: str | None = None,
) -> tuple[Path, int]:
    """Save puzzle as SGF file.

    Args:
        puzzle: Parsed puzzle detail
        output_dir: Base output directory
        batch_size: Maximum files per batch
        checkpoint: Optional checkpoint for O(1) batch lookup (avoids filesystem scan)
        extra_tags: Optional additional tags to merge into YT[]
        collection_slugs: Optional list of collection slugs for YL[] property
        root_comment: Optional objective text for root C[] comment

    Returns:
        Tuple of (saved file path, batch number)
    """
    # Convert to SGF
    sgf_content = convert_puzzle_to_sgf(
        puzzle,
        extra_tags=extra_tags,
        collection_slugs=collection_slugs,
        root_comment=root_comment,
    )

    # Get batch directory - use fast path if checkpoint available
    sgf_dir = get_sgf_dir(output_dir)
    if checkpoint is not None:
        batch_dir = get_batch_for_file_fast(sgf_dir, checkpoint, batch_size)
    else:
        batch_dir = get_batch_for_file(sgf_dir, batch_size)

    # Extract batch number from directory name
    batch_num = int(batch_dir.name.split("-")[1])

    # Generate filename and save
    filename = generate_puzzle_filename(puzzle)
    file_path = batch_dir / filename

    file_path.write_text(sgf_content, encoding="utf-8")

    # Add to index file (for duplicate prevention)
    add_to_index(output_dir, batch_dir.name, filename)

    logger.debug(f"Saved {rel_path(file_path)}")

    return file_path, batch_num
