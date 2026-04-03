"""
File storage for downloaded GoProblems puzzles.

Saves enriched SGF files in batch directories with index tracking.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from tools.core.paths import rel_path

from .batching import get_batch_for_file, get_batch_for_file_fast
from .collections import resolve_collection_slugs
from .config import DEFAULT_BATCH_SIZE, get_sgf_dir
from .converter import enrich_sgf
from .index import add_to_index
from .levels import map_rank_to_level
from .models import GoProblemsDetail
from .quality import compute_quality_score, format_yq
from .tags import map_collections_to_tags, map_genre_to_tags

if TYPE_CHECKING:
    from .checkpoint import GoProblemsCheckpoint


logger = logging.getLogger("go_problems.storage")


def generate_puzzle_filename(puzzle_id: int | str) -> str:
    """Generate filename for puzzle.

    Format: {puzzle_id}.sgf

    Args:
        puzzle_id: GoProblems puzzle ID

    Returns:
        Filename string (e.g., '12345.sgf')
    """
    return f"{puzzle_id}.sgf"


def save_puzzle(
    puzzle: GoProblemsDetail,
    output_dir: Path,
    batch_size: int = DEFAULT_BATCH_SIZE,
    checkpoint: GoProblemsCheckpoint | None = None,
    match_collections: bool = True,
    root_comment: str | None = None,
) -> tuple[Path, int]:
    """Process and save a GoProblems puzzle as an enriched SGF file.

    Performs all mapping (level, tags, collections, quality) and saves
    the enriched SGF to the appropriate batch directory.

    Args:
        puzzle: Parsed GoProblems puzzle detail
        output_dir: Base output directory
        batch_size: Maximum files per batch
        checkpoint: Optional checkpoint for O(1) batch lookup
        match_collections: Whether to resolve collection slugs
        root_comment: Optional resolved objective slug for root C[]

    Returns:
        Tuple of (saved file path, batch number)
    """
    # Map genre to tags
    tags = map_genre_to_tags(puzzle.genre)

    # Add collection-derived tags
    if puzzle.collections:
        coll_tags = map_collections_to_tags(
            [c.model_dump() for c in puzzle.collections]
        )
        tags.extend(coll_tags)

    # Deduplicate tags
    tags = sorted(set(tags))

    # Map rank to level
    rank_dict = puzzle.rank.model_dump() if puzzle.rank else None
    level = map_rank_to_level(rank_dict, puzzle.problemLevel)

    # Resolve collection slugs for YL[]
    collection_slugs: list[str] | None = None
    if match_collections and puzzle.collections:
        collection_slugs = resolve_collection_slugs(
            [c.model_dump() for c in puzzle.collections]
        )
        # Log collection matching results
        if collection_slugs:
            logger.info(
                f"Puzzle {puzzle.id}: YL matched {collection_slugs}"
            )
        else:
            # Puzzle belongs to collections on GoProblems but none matched
            unmatched = [c.name for c in puzzle.collections]
            logger.warning(
                f"Puzzle {puzzle.id}: has {len(unmatched)} collections "
                f"but none matched config: {unmatched}"
            )

    # Compute YQ quality score
    q_score = compute_quality_score(puzzle.rating, puzzle.isCanon)
    yq_value = format_yq(q_score)

    # Determine player to move (handle None from legacy puzzles)
    player_color = (puzzle.playerColor or "black").lower()
    pl_value = "B" if player_color == "black" else "W"

    # Enrich SGF
    enriched_sgf = enrich_sgf(
        sgf_content=puzzle.sgf,
        puzzle_id=puzzle.id,
        level=level,
        tags=tags,
        pl_value=pl_value,
        collection_slugs=collection_slugs,
        yq_value=yq_value,
        root_comment=root_comment,
    )

    # Get batch directory
    sgf_dir = get_sgf_dir(output_dir)
    if checkpoint is not None:
        batch_dir = get_batch_for_file_fast(sgf_dir, checkpoint, batch_size)
    else:
        batch_dir = get_batch_for_file(sgf_dir, batch_size)

    # Extract batch number
    batch_num = int(batch_dir.name.split("-")[1])

    # Generate filename and save
    filename = generate_puzzle_filename(puzzle.id)
    file_path = batch_dir / filename

    file_path.write_text(enriched_sgf, encoding="utf-8")

    # Add to index file
    add_to_index(output_dir, batch_dir.name, filename)

    logger.debug(f"Saved {rel_path(file_path)}")

    return file_path, batch_num
