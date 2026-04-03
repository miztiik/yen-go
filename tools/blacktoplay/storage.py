"""
File storage for downloaded BTP puzzles.

Saves SGF files in batch directories using shared batching infrastructure.
Maintains an sgf-index.txt for O(1) duplicate detection on resume.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from tools.core.atomic_write import atomic_write_text
from tools.core.batching import get_batch_for_file_fast
from tools.core.index import add_entry, load_index
from tools.core.paths import rel_path

from .btp_checkpoint import BTPCheckpoint
from .config import DEFAULT_BATCH_SIZE, get_sgf_dir
from .models import BTPPuzzle
from .sgf_converter import get_sgf_filename

if TYPE_CHECKING:
    pass


logger = logging.getLogger("btp.storage")

# Index filename
INDEX_FILENAME = "sgf-index.txt"


def load_known_ids(output_dir: Path) -> set[str]:
    """Load set of known puzzle filenames from index.

    Handles both legacy (stem-only) and new (batch/file) formats.

    Returns:
        Set of filename stems (e.g., {"btp-123", "btp-456"}).
    """
    index_path = output_dir / INDEX_FILENAME
    if not index_path.exists():
        return set()

    entries = load_index(index_path)

    # Extract stems from entries (handle both formats)
    stems: set[str] = set()
    for entry in entries:
        # New format: batch-NNN/btp-123.sgf
        if "/" in entry:
            filename = entry.rsplit("/", 1)[-1]
            stems.add(Path(filename).stem)
        else:
            # Legacy format: btp-123 or btp-123.sgf
            stems.add(Path(entry).stem if entry.endswith(".sgf") else entry)
    return stems


def save_puzzle(
    puzzle: BTPPuzzle,
    sgf_content: str,
    output_dir: Path,
    checkpoint: BTPCheckpoint,
    batch_size: int = DEFAULT_BATCH_SIZE,
    dry_run: bool = False,
) -> Path | None:
    """Save a puzzle SGF to the appropriate batch directory.

    Creates batch directories as needed. Updates the index file and
    checkpoint batch tracking.

    Args:
        puzzle: The BTP puzzle data.
        sgf_content: Pre-built SGF string.
        output_dir: Base output directory.
        checkpoint: Active checkpoint for batch tracking.
        batch_size: Max files per batch directory.
        dry_run: If True, log but don't write.

    Returns:
        Path to saved file, or None if dry_run.
    """
    filename = get_sgf_filename(puzzle)
    sgf_dir = get_sgf_dir(output_dir)

    # Determine batch directory
    batch_dir, _ = get_batch_for_file_fast(
        parent_dir=sgf_dir,
        current_batch=checkpoint.current_batch,
        files_in_current_batch=checkpoint.files_in_current_batch,
        batch_size=batch_size,
    )

    file_path = batch_dir / filename

    if dry_run:
        logger.info("[DRY RUN] Would save: %s", rel_path(file_path))
        return None

    # Ensure batch directory exists
    batch_dir.mkdir(parents=True, exist_ok=True)

    # Write SGF file atomically
    atomic_write_text(file_path, sgf_content)

    # Update index with batch path (format: batch-NNN/filename.sgf)
    index_path = output_dir / INDEX_FILENAME
    entry = f"{batch_dir.name}/{filename}"
    add_entry(index_path, entry)

    # Update checkpoint batch tracking
    checkpoint.record_file_saved(batch_size)

    logger.debug("Saved: %s", rel_path(file_path))
    return file_path
