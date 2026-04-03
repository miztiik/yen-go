"""
SGF file saving for 101weiqi puzzles.

Converts puzzle data to SGF, saves to batch directories, maintains index.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from tools.core.paths import rel_path

from .batching import get_batch_for_file, get_batch_for_file_fast
from .config import DEFAULT_BATCH_SIZE, get_sgf_dir
from .converter import convert_puzzle_to_sgf
from .index import add_to_index
from .models import PuzzleData

if TYPE_CHECKING:
    from .checkpoint import WeiQiCheckpoint

logger = logging.getLogger("101weiqi.storage")


def generate_puzzle_filename(puzzle: PuzzleData) -> str:
    """Generate filename for a puzzle.

    Format: {puzzle_id}.sgf

    Args:
        puzzle: Parsed puzzle data.

    Returns:
        Filename string (e.g., "78000.sgf").
    """
    return f"{puzzle.puzzle_id}.sgf"


def save_puzzle(
    puzzle: PuzzleData,
    output_dir: Path,
    batch_size: int = DEFAULT_BATCH_SIZE,
    checkpoint: WeiQiCheckpoint | None = None,
    *,
    root_comment: str | None = None,
    collection_entries: list[str] | None = None,
    yx_string: str | None = None,
) -> tuple[Path, int]:
    """Convert puzzle to SGF and save to batch directory.

    Args:
        puzzle: Parsed and validated puzzle data.
        output_dir: Base output directory.
        batch_size: Maximum files per batch.
        checkpoint: Optional checkpoint for O(1) batch lookup.
        root_comment: Optional intent text for root C[].
        collection_entries: Optional list of YL entries (bare slugs or
            slug:CHAPTER/POSITION format for chapter+position sequences).
        yx_string: Optional pre-formatted YX[] value string.

    Returns:
        Tuple of (saved file path, batch number).
    """
    # Convert to SGF with YenGo properties
    sgf_content = convert_puzzle_to_sgf(
        puzzle,
        root_comment=root_comment,
        collection_entries=collection_entries,
        yx_string=yx_string,
    )

    # Get batch directory
    sgf_dir = get_sgf_dir(output_dir)
    if checkpoint is not None:
        batch_dir = get_batch_for_file_fast(sgf_dir, checkpoint, batch_size)
    else:
        batch_dir = get_batch_for_file(sgf_dir, batch_size)

    batch_num = int(batch_dir.name.split("-")[1])

    # Save file
    filename = generate_puzzle_filename(puzzle)
    file_path = batch_dir / filename
    file_path.write_text(sgf_content, encoding="utf-8")

    # Add to index
    add_to_index(output_dir, batch_dir.name, filename)

    logger.debug(f"Saved {rel_path(file_path)}")

    return file_path, batch_num
