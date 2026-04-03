"""
File storage for downloaded puzzles.

Saves SGF files with whitelist-only rebuild: parses source SGF,
reconstructs from scratch with only approved properties using
SGFBuilder.from_tree().

Directory structure:
    external-sources/tsumegodragon/
    +-- sgf/
    |   +-- batch-001/
    |   |   +-- {puzzle_id}.sgf
    |   +-- batch-002/
    |   +-- ...
    +-- .checkpoint.json
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from tools.core.sgf_builder import SGFBuilder
from tools.core.sgf_parser import parse_sgf

from .batching import DEFAULT_BATCH_SIZE, get_batch_for_file, get_batch_for_file_fast
from .config import SOURCE_ID
from .index import add_to_index
from .mappers import category_to_yt_tags, level_to_yg_slug
from .models import TDPuzzle

if TYPE_CHECKING:
    from .checkpoint import TDragonCheckpoint


def get_sgf_dir(output_dir: Path) -> Path:
    """Get the sgf/ subdirectory for storing puzzle files.

    Args:
        output_dir: Base output directory (e.g., external-sources/tsumegodragon/).

    Returns:
        Path to sgf/ subdirectory.
    """
    return output_dir / "sgf"


def rebuild_sgf(
    sgf_text: str,
    level_str: str | None,
    category_slug: str,
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
        level_str: TsumegoDragon level string (e.g., "Level 3 (14k-10k)").
        category_slug: TsumegoDragon category slug for tag mapping.
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
    yg_slug = level_to_yg_slug(level_str)
    if yg_slug:
        builder.set_level_slug(yg_slug)

    yt_tags = category_to_yt_tags(category_slug)
    if yt_tags:
        builder.add_tags(yt_tags)

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
    puzzle: TDPuzzle,
    category_slug: str,
    output_dir: Path,
    batch_size: int = DEFAULT_BATCH_SIZE,
    checkpoint: TDragonCheckpoint | None = None,
    collection_slugs: list[str] | None = None,
    root_comment: str | None = None,
) -> Path:
    """Save puzzle SGF with whitelist-only rebuild.

    Args:
        puzzle: Puzzle data from API.
        category_slug: Category slug for tag mapping.
        output_dir: Base output directory.
        batch_size: Max files per batch directory (default: 500).
        checkpoint: Optional checkpoint for O(1) batch tracking.
        collection_slugs: Optional YL[] collection slugs.
        root_comment: Optional C[] root comment (puzzle intent).

    Returns:
        Path to saved SGF file.
    """
    sgf_dir = get_sgf_dir(output_dir)

    # Get appropriate batch directory (O(1) fast path if checkpoint available)
    if checkpoint:
        save_dir, _batch_num = get_batch_for_file_fast(
            sgf_dir,
            checkpoint.current_batch,
            checkpoint.files_in_current_batch,
            batch_size,
        )
    else:
        save_dir = get_batch_for_file(sgf_dir, batch_size)

    save_dir.mkdir(parents=True, exist_ok=True)

    # Rebuild SGF with whitelist-only properties
    clean_sgf = rebuild_sgf(
        sgf_text=puzzle.sgf_text,
        level_str=puzzle.level,
        category_slug=category_slug,
        collection_slugs=collection_slugs,
        root_comment=root_comment,
    )

    # Save SGF file
    filename = f"{puzzle.id}.sgf"
    sgf_path = save_dir / filename
    sgf_path.write_text(clean_sgf, encoding="utf-8")

    # Add to index for O(1) dedup on next run
    add_to_index(output_dir, save_dir.name, filename)

    return sgf_path


def count_files_in_sgf_dir(output_dir: Path) -> int:
    """Count total SGF files across all batches.

    Args:
        output_dir: Base output directory.

    Returns:
        Total count of .sgf files.
    """
    sgf_dir = get_sgf_dir(output_dir)

    if not sgf_dir.exists():
        return 0

    count = 0
    for batch_dir in sgf_dir.iterdir():
        if batch_dir.is_dir() and batch_dir.name.startswith("batch-"):
            count += len(list(batch_dir.glob("*.sgf")))

    return count
