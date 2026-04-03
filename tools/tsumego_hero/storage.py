"""
File storage for downloaded Tsumego Hero puzzles.

Saves SGF files with whitelist-only rebuild: parses source SGF,
reconstructs from scratch with only approved properties using
SGFBuilder.from_tree().

Directory structure:
    external-sources/t-hero/
    +-- sgf/
    |   +-- batch-001/
    |   |   +-- th-5225.sgf
    |   +-- batch-002/
    |   +-- ...
    +-- .checkpoint.json
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from tools.core.sgf_builder import SGFBuilder
from tools.core.sgf_parser import parse_sgf

from .batching import (
    THERO_BATCH_SIZE,
    get_batch_for_file,
    get_batch_for_file_fast,
    get_sgf_dir,
)
from .client import PuzzleData
from .index import add_to_index
from .mappers import difficulty_to_level, tags_to_yengo

if TYPE_CHECKING:
    from .checkpoint import THeroCheckpoint


# Source identifier for YS[] property
SOURCE_ID = "th"


def rebuild_sgf(
    sgf_text: str,
    level_slug: str | None,
    tags: list[str],
    collection_slugs: list[str] | None = None,
    root_comment: str | None = None,
) -> str:
    """Rebuild SGF from scratch with only approved properties.

    Parses the source SGF, creates a clean rebuild via SGFBuilder.from_tree(),
    then sets YenGo properties. This strips ALL non-whitelisted properties
    (AP, RU, KM, PW, PB, DT, ST, GN, PC, EV, SO, etc.).

    Approved root properties (from builder):
        FF[4], GM[1], SZ[N], PL[B/W], AB[...], AW[...]

    YenGo properties set:
        YG[level], YT[tags], YS[source], YL[collections], C[intent]

    Move comments (C[...] on solution nodes) are preserved from source.

    Args:
        sgf_text: Original SGF string from source.
        level_slug: YenGo level slug (e.g., "intermediate").
        tags: List of YenGo canonical tags.
        collection_slugs: Optional list of YenGo collection slugs for YL[].
        root_comment: Optional root comment for C[] (puzzle intent).

    Returns:
        Clean SGF string with only whitelisted properties.
    """
    # Parse source SGF
    tree = parse_sgf(sgf_text)

    # Create builder from parsed tree (preserves stones, moves, solution tree)
    builder = SGFBuilder.from_tree(tree)

    # Clear any metadata that from_tree() preserved (we want whitelist-only)
    builder.metadata.clear()

    # Set YenGo properties
    if level_slug:
        builder.set_level_slug(level_slug)

    if tags:
        builder.add_tags(tags)

    # Source ID
    builder.yengo_props.source = SOURCE_ID

    # Collections (YL)
    if collection_slugs:
        builder.set_collections(collection_slugs)

    # Root comment / intent (C[])
    if root_comment:
        builder.set_comment(root_comment)

    return builder.build()


def save_puzzle(
    puzzle: PuzzleData,
    output_dir: Path,
    batch_size: int = THERO_BATCH_SIZE,
    checkpoint: THeroCheckpoint | None = None,
    collection_slugs: list[str] | None = None,
    root_comment: str | None = None,
) -> Path:
    """Save puzzle SGF with whitelist-only rebuild.

    Args:
        puzzle: Puzzle data from client.
        output_dir: Base output directory.
        batch_size: Max files per batch directory.
        checkpoint: Optional checkpoint for O(1) batch tracking.
        collection_slugs: Optional YL[] collection slugs.
        root_comment: Optional C[] root comment (puzzle intent).

    Returns:
        Path to saved SGF file.
    """
    sgf_dir = get_sgf_dir(output_dir)

    # Map difficulty to YenGo level
    level_slug = difficulty_to_level(puzzle.difficulty)

    # Map tags to YenGo tags
    yengo_tags: list[str] = []
    if puzzle.tags:
        yengo_tags = tags_to_yengo(puzzle.tags)

    # Rebuild SGF with whitelist-only properties
    clean_sgf = rebuild_sgf(
        sgf_text=puzzle.sgf,
        level_slug=level_slug,
        tags=yengo_tags,
        collection_slugs=collection_slugs,
        root_comment=root_comment,
    )

    # Get batch directory
    if checkpoint:
        batch_dir, _batch_num = get_batch_for_file_fast(
            sgf_dir,
            checkpoint.current_batch,
            checkpoint.files_in_current_batch,
            batch_size,
        )
    else:
        batch_dir = get_batch_for_file(sgf_dir, batch_size)

    batch_dir.mkdir(parents=True, exist_ok=True)

    # Generate filename: th-{url_id}.sgf
    filename = f"th-{puzzle.url_id}.sgf"
    sgf_path = batch_dir / filename

    # Write SGF file
    sgf_path.write_text(clean_sgf, encoding="utf-8")

    # Add to index for O(1) dedup on next run
    add_to_index(output_dir, batch_dir.name, filename)

    return sgf_path


def get_index_entries(output_dir: Path) -> list[str]:
    """Read all entries from the SGF index.

    Args:
        output_dir: Base output directory.

    Returns:
        List of relative paths from index file.
    """
    index_path = output_dir / "sgf-index.txt"

    if not index_path.exists():
        return []

    with open(index_path, encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def count_indexed_puzzles(output_dir: Path) -> int:
    """Count puzzles in the index.

    Args:
        output_dir: Base output directory.

    Returns:
        Number of indexed puzzles.
    """
    return len(get_index_entries(output_dir))
