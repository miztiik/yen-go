"""
SGF file saving for 101weiqi puzzles.

Converts puzzle data to SGF, saves to batch directories, maintains index.
Daily puzzles (qday) get their own year/month directory structure.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING

from tools.core.paths import rel_path

from .batching import get_batch_for_file, get_batch_for_file_fast
from .config import DEFAULT_BATCH_SIZE, get_qday_dir, get_sgf_dir
from .converter import convert_puzzle_to_sgf
from .index import add_to_index
from .models import PuzzleData

if TYPE_CHECKING:
    from .checkpoint import WeiQiCheckpoint

logger = logging.getLogger("101weiqi.storage")

# Regex: /qday/2026/4/14/3/ — note month/day may be 1 or 2 digits
_QDAY_URL_RE = re.compile(r"/qday/(\d{4})/(\d{1,2})/(\d{1,2})/(\d{1,2})/?")


def parse_qday_url(url: str | None) -> tuple[int, int, int, int] | None:
    """Extract (year, month, day, number) from a qday URL.

    Returns None if the URL is not a qday URL.
    """
    if not url:
        return None
    m = _QDAY_URL_RE.search(url)
    if not m:
        return None
    return int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4))


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


def save_puzzle_qday(
    puzzle: PuzzleData,
    output_dir: Path,
    year: int,
    month: int,
    day: int,
    number: int,
    *,
    root_comment: str | None = None,
    collection_entries: list[str] | None = None,
    yx_string: str | None = None,
) -> Path:
    """Save a daily puzzle to the qday directory structure.

    Directory: qday/YYYY/MM/YYYYMMDD-N-PUZZLEID.sgf
    Example:   qday/2026/04/20260414-3-354411.sgf

    The puzzle ID is still tracked in sgf-index.txt for dedup.

    Returns:
        Saved file path.
    """
    sgf_content = convert_puzzle_to_sgf(
        puzzle,
        root_comment=root_comment,
        collection_entries=collection_entries,
        yx_string=yx_string,
    )

    # Build path: qday/YYYY/MM/YYYYMMDD-N.sgf
    qday_dir = get_qday_dir(output_dir)
    month_dir = qday_dir / str(year) / f"{month:02d}"
    month_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{year}{month:02d}{day:02d}-{number}-{puzzle.puzzle_id}.sgf"
    file_path = month_dir / filename
    file_path.write_text(sgf_content, encoding="utf-8")

    # Add to index with puzzle ID suffix for dedup on reload:
    # qday/2026/04/20260414-3.sgf:354411
    index_dir = f"qday/{year}/{month:02d}"
    index_entry = f"{index_dir}/{filename}:{puzzle.puzzle_id}"
    add_to_index(output_dir, index_dir, f"{filename}:{puzzle.puzzle_id}")

    logger.debug(f"Saved qday {rel_path(file_path)}")

    return file_path
