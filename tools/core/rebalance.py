"""
Batch rebalancer: redistribute files evenly across batch directories.

When batch sizes drift (e.g., mid-crawl size changes, interrupted runs),
this utility rebalances files so each batch has exactly `batch_size` files,
rebuilds the index, and updates the checkpoint.

Algorithm:
    1. Catalog all files across all batch-* directories, sorted by numeric ID.
    2. Compute target batch assignment for each file (index // batch_size).
    3. Diff current vs target location — only files that need to move are touched.
    4. Execute moves via os.rename() (atomic on same filesystem, no copy).
    5. Remove empty batch directories.
    6. Rebuild the index file from the new filesystem state.
    7. Update checkpoint to reflect the new batch count.

Safety:
    - Dry-run is the DEFAULT. Pass --execute to apply changes.
    - Pre/post file counts are verified (assertion aborts if mismatch).
    - Destination collision detection (aborts if target file already exists).
    - Uses os.rename() only — no copy-then-delete, no data duplication.

Usage:
    # Preview (dry-run, default):
    python -m tools.core.rebalance \\
        --sgf-dir external-sources/goproblems/sgf \\
        --index-path external-sources/goproblems/sgf-index.txt

    # Execute:
    python -m tools.core.rebalance \\
        --sgf-dir external-sources/goproblems/sgf \\
        --index-path external-sources/goproblems/sgf-index.txt \\
        --execute

    # Custom batch size:
    python -m tools.core.rebalance \\
        --sgf-dir external-sources/ogs/sgf \\
        --index-path external-sources/ogs/sgf-index.txt \\
        --batch-size 500 \\
        --execute
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from tools.core.atomic_write import atomic_write_json
from tools.core.index import rebuild_from_filesystem

logger = logging.getLogger("tools.core.rebalance")

# Regex: extract numeric ID from filename (last number before .sgf)
_ID_PATTERN = re.compile(r"(\d+)\.sgf$")

# Default batch size
DEFAULT_BATCH_SIZE = 1000


@dataclass(frozen=True)
class FileEntry:
    """A cataloged file with its numeric sort key and current location."""

    numeric_id: int
    filename: str
    current_dir: str  # batch directory name, e.g. "batch-001"
    full_path: Path


@dataclass(frozen=True)
class Move:
    """A file move operation from source to destination."""

    src: Path
    dst: Path
    filename: str


@dataclass
class RebalanceResult:
    """Summary of a rebalance operation."""

    total_files: int
    batches_before: int
    batches_after: int
    moves_needed: int
    moves_executed: int
    empty_dirs_removed: int
    index_entries: int
    dry_run: bool

    def __str__(self) -> str:
        mode = "DRY RUN" if self.dry_run else "EXECUTED"
        return (
            f"[{mode}] Rebalance summary:\n"
            f"  Total files:          {self.total_files:,}\n"
            f"  Batches before:       {self.batches_before}\n"
            f"  Batches after:        {self.batches_after}\n"
            f"  Moves needed:         {self.moves_needed:,}\n"
            f"  Moves executed:       {self.moves_executed:,}\n"
            f"  Empty dirs removed:   {self.empty_dirs_removed}\n"
            f"  Index entries:        {self.index_entries:,}"
        )


def detect_pad_width(sgf_dir: Path) -> int:
    """Auto-detect zero-padding width from existing batch directory names.

    Scans batch-* directories and returns the padding width of the numeric
    portion. E.g., batch-001 → 3, batch-0001 → 4.

    Falls back to 3 if no batch directories exist.
    """
    max_width = 0
    found = False
    for entry in sgf_dir.iterdir():
        if entry.is_dir() and entry.name.startswith("batch-"):
            found = True
            numeric_part = entry.name[len("batch-"):]
            max_width = max(max_width, len(numeric_part))

    if not found:
        return 3  # default

    return max_width


def catalog_files(sgf_dir: Path) -> list[FileEntry]:
    """Scan all batch-* directories and catalog every .sgf file.

    Returns a sorted list of FileEntry objects ordered by numeric puzzle ID.
    Files whose names don't match the numeric ID pattern are sorted to the end
    with a synthetic high ID.
    """
    entries: list[FileEntry] = []

    for batch_dir in sgf_dir.iterdir():
        if not batch_dir.is_dir() or not batch_dir.name.startswith("batch-"):
            continue
        for sgf_file in batch_dir.iterdir():
            if not sgf_file.is_file() or not sgf_file.name.endswith(".sgf"):
                continue

            m = _ID_PATTERN.search(sgf_file.name)
            numeric_id = int(m.group(1)) if m else 0
            entries.append(
                FileEntry(
                    numeric_id=numeric_id,
                    filename=sgf_file.name,
                    current_dir=batch_dir.name,
                    full_path=sgf_file,
                )
            )

    # Stable sort by numeric ID, then filename for ties
    entries.sort(key=lambda e: (e.numeric_id, e.filename))
    return entries


def batch_name(batch_number: int, pad_width: int) -> str:
    """Format a batch directory name with zero-padded number."""
    return f"batch-{batch_number:0{pad_width}d}"


def compute_moves(
    catalog: list[FileEntry],
    batch_size: int,
    pad_width: int,
) -> list[Move]:
    """Compute the minimal set of file moves to rebalance batches.

    Each file at index i in the sorted catalog is assigned to batch
    (i // batch_size) + 1. Only files not already in their target batch
    produce a Move. This is O(N) in catalog size but the number of actual
    moves is typically much smaller.
    """
    moves: list[Move] = []

    for i, entry in enumerate(catalog):
        target_batch_num = (i // batch_size) + 1
        target_dir_name = batch_name(target_batch_num, pad_width)

        if entry.current_dir == target_dir_name:
            continue  # already in the right place

        src = entry.full_path
        dst = src.parent.parent / target_dir_name / entry.filename
        moves.append(Move(src=src, dst=dst, filename=entry.filename))

    return moves


def execute_moves(
    moves: list[Move],
    sgf_dir: Path,
    pad_width: int,
    total_batches: int,
) -> int:
    """Execute file moves using os.rename (atomic on same filesystem).

    Creates target batch directories as needed. Aborts on collision.

    Returns the number of moves executed.
    """
    # Pre-create all target batch directories
    for bn in range(1, total_batches + 1):
        target = sgf_dir / batch_name(bn, pad_width)
        target.mkdir(exist_ok=True)

    executed = 0
    for move in moves:
        # Safety: abort if destination already exists (would overwrite)
        if move.dst.exists():
            raise FileExistsError(
                f"Destination already exists, aborting to prevent data loss: "
                f"{move.dst}"
            )

        # Ensure parent directory exists (handles edge cases)
        move.dst.parent.mkdir(parents=True, exist_ok=True)
        os.rename(move.src, move.dst)
        executed += 1

    return executed


def remove_empty_batch_dirs(sgf_dir: Path) -> int:
    """Remove empty batch-* directories after rebalancing.

    Only removes directories that are truly empty (no files, no subdirs).
    Returns the count of removed directories.
    """
    removed = 0
    for entry in sorted(sgf_dir.iterdir()):
        if (
            entry.is_dir()
            and entry.name.startswith("batch-")
            and not any(entry.iterdir())
        ):
            entry.rmdir()
            removed += 1
            logger.debug(f"Removed empty directory: {entry.name}")
    return removed


def rebuild_index(sgf_dir: Path, index_path: Path) -> int:
    """Rebuild the index file from the current filesystem state.

    Delegates to the existing rebuild_from_filesystem() in tools.core.index.
    Returns the number of entries written.
    """
    return rebuild_from_filesystem(
        scan_dir=sgf_dir,
        index_path=index_path,
        file_pattern="*.sgf",
        dir_prefix="batch-",
    )


def update_checkpoint(
    checkpoint_path: Path,
    current_batch: int,
    files_in_last_batch: int,
) -> None:
    """Update checkpoint file with new batch state after rebalancing.

    Uses atomic_write_json for cross-platform safety.
    Preserves all existing fields (last_processed_id, etc.) and only
    updates current_batch, files_in_current_batch, and last_updated.
    """
    data = {}
    if checkpoint_path.exists():
        try:
            data = json.loads(checkpoint_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Could not read checkpoint {checkpoint_path}: {e}")

    data["current_batch"] = current_batch
    data["files_in_current_batch"] = files_in_last_batch
    data["last_updated"] = datetime.now(UTC).isoformat()

    # Atomic write with cross-platform safety
    atomic_write_json(checkpoint_path, data, ensure_ascii=False)

    logger.info(
        f"Updated checkpoint: batch={current_batch}, "
        f"files_in_batch={files_in_last_batch}"
    )


def rebalance(
    sgf_dir: Path,
    index_path: Path,
    batch_size: int = DEFAULT_BATCH_SIZE,
    dry_run: bool = True,
    checkpoint_path: Path | None = None,
) -> RebalanceResult:
    """Rebalance files across batch directories.

    Args:
        sgf_dir: Directory containing batch-* subdirectories.
        index_path: Path to the index .txt file to rebuild.
        batch_size: Maximum files per batch directory.
        dry_run: If True (default), only print summary without moving files.
        checkpoint_path: Path to .checkpoint.json. Auto-detected if None.

    Returns:
        RebalanceResult with operation summary.

    Raises:
        FileExistsError: If a move would overwrite an existing file.
        AssertionError: If file count changes during rebalance (data loss).
    """
    # Auto-detect checkpoint
    if checkpoint_path is None:
        candidate = sgf_dir.parent / ".checkpoint.json"
        if candidate.exists():
            checkpoint_path = candidate

    # Step 1: Catalog all files
    logger.info(f"Cataloging files in {sgf_dir}...")
    catalog = catalog_files(sgf_dir)
    total_files = len(catalog)
    logger.info(f"Found {total_files:,} files")

    if total_files == 0:
        logger.warning("No files found. Nothing to rebalance.")
        return RebalanceResult(
            total_files=0,
            batches_before=0,
            batches_after=0,
            moves_needed=0,
            moves_executed=0,
            empty_dirs_removed=0,
            index_entries=0,
            dry_run=dry_run,
        )

    # Count existing batches
    existing_batches = [
        d for d in sgf_dir.iterdir()
        if d.is_dir() and d.name.startswith("batch-")
    ]
    batches_before = len(existing_batches)

    # Step 2: Detect padding width
    pad_width = detect_pad_width(sgf_dir)
    logger.info(f"Detected batch padding width: {pad_width}")

    # Step 3: Compute target assignments
    total_batches = (total_files + batch_size - 1) // batch_size
    # Check if pad_width needs to grow for new batch count
    needed_width = len(str(total_batches))
    if needed_width > pad_width:
        logger.info(
            f"Increasing pad width from {pad_width} to {needed_width} "
            f"to accommodate {total_batches} batches"
        )
        pad_width = needed_width

    moves = compute_moves(catalog, batch_size, pad_width)
    files_in_last_batch = total_files - (total_batches - 1) * batch_size

    logger.info(
        f"Plan: {total_files:,} files → {total_batches} batches "
        f"of {batch_size} ({files_in_last_batch} in last batch), "
        f"{len(moves):,} moves needed"
    )

    # Print per-batch breakdown in dry-run
    if dry_run:
        # Show current batch sizes
        print(f"\n{'='*60}")
        print("REBALANCE PLAN (dry-run)")
        print(f"{'='*60}")
        print(f"  SGF directory:   {sgf_dir}")
        print(f"  Index path:      {index_path}")
        print(f"  Batch size:      {batch_size}")
        print(f"  Pad width:       {pad_width}")
        print(f"  Total files:     {total_files:,}")
        print(f"  Batches before:  {batches_before}")
        print(f"  Batches after:   {total_batches}")
        print(f"  Moves needed:    {len(moves):,}")
        print()

        # Current batch sizes
        print("Current batch sizes:")
        batch_counts: dict[str, int] = {}
        for entry in catalog:
            batch_counts[entry.current_dir] = (
                batch_counts.get(entry.current_dir, 0) + 1
            )
        for bname in sorted(batch_counts.keys()):
            count = batch_counts[bname]
            marker = " ← OVERSIZED" if count > batch_size else ""
            print(f"  {bname}: {count:,}{marker}")

        # Target batch sizes
        print(f"\nTarget batch sizes (all {batch_size} except last):")
        for bn in range(1, total_batches + 1):
            start = (bn - 1) * batch_size
            end = min(bn * batch_size, total_files)
            count = end - start
            target_name = batch_name(bn, pad_width)
            print(f"  {target_name}: {count:,}")

        print("\nPass --execute to apply these changes.")
        print(f"{'='*60}\n")

        return RebalanceResult(
            total_files=total_files,
            batches_before=batches_before,
            batches_after=total_batches,
            moves_needed=len(moves),
            moves_executed=0,
            empty_dirs_removed=0,
            index_entries=0,
            dry_run=True,
        )

    # Step 4: Execute moves
    logger.info(f"Executing {len(moves):,} moves...")
    executed = execute_moves(moves, sgf_dir, pad_width, total_batches)
    logger.info(f"Executed {executed:,} moves")

    # Step 5: Verify file count (safety assertion)
    post_catalog = catalog_files(sgf_dir)
    assert len(post_catalog) == total_files, (
        f"FILE COUNT MISMATCH after rebalance! "
        f"Before: {total_files}, After: {len(post_catalog)}. "
        f"This indicates data loss — investigate immediately."
    )
    logger.info(f"Verified: {len(post_catalog):,} files (matches pre-move count)")

    # Step 6: Remove empty batch directories
    removed = remove_empty_batch_dirs(sgf_dir)
    logger.info(f"Removed {removed} empty directories")

    # Step 7: Rebuild index
    logger.info(f"Rebuilding index at {index_path}...")
    index_entries = rebuild_index(sgf_dir, index_path)
    logger.info(f"Index rebuilt with {index_entries:,} entries")

    # Step 8: Update checkpoint
    if checkpoint_path is not None:
        update_checkpoint(checkpoint_path, total_batches, files_in_last_batch)
    else:
        logger.info("No checkpoint file found — skipping checkpoint update")

    result = RebalanceResult(
        total_files=total_files,
        batches_before=batches_before,
        batches_after=total_batches,
        moves_needed=len(moves),
        moves_executed=executed,
        empty_dirs_removed=removed,
        index_entries=index_entries,
        dry_run=False,
    )
    logger.info(str(result))
    return result


def main() -> None:
    """CLI entry point for batch rebalancer."""
    parser = argparse.ArgumentParser(
        description=(
            "Rebalance SGF files across batch directories. "
            "Dry-run by default — pass --execute to apply changes."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  # Preview (dry-run):\n"
            "  python -m tools.core.rebalance \\\n"
            "    --sgf-dir external-sources/goproblems/sgf \\\n"
            "    --index-path external-sources/goproblems/sgf-index.txt\n"
            "\n"
            "  # Execute:\n"
            "  python -m tools.core.rebalance \\\n"
            "    --sgf-dir external-sources/goproblems/sgf \\\n"
            "    --index-path external-sources/goproblems/sgf-index.txt \\\n"
            "    --execute\n"
            "\n"
            "  # Custom batch size:\n"
            "  python -m tools.core.rebalance \\\n"
            "    --sgf-dir external-sources/ogs/sgf \\\n"
            "    --index-path external-sources/ogs/sgf-index.txt \\\n"
            "    --batch-size 500 --execute\n"
        ),
    )

    parser.add_argument(
        "--sgf-dir",
        type=Path,
        required=True,
        help="Directory containing batch-* subdirectories with .sgf files.",
    )
    parser.add_argument(
        "--index-path",
        type=Path,
        required=True,
        help="Path to the index .txt file to rebuild.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help=f"Files per batch directory (default: {DEFAULT_BATCH_SIZE}).",
    )
    parser.add_argument(
        "--checkpoint",
        type=Path,
        default=None,
        help=(
            "Path to .checkpoint.json to update. "
            "Auto-detected as {sgf-dir}/../.checkpoint.json if not specified."
        ),
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        default=False,
        help="Actually move files. Without this flag, only a dry-run summary is shown.",
    )

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    # Validate inputs
    if not args.sgf_dir.is_dir():
        parser.error(f"SGF directory does not exist: {args.sgf_dir}")
    if args.batch_size < 1:
        parser.error(f"Batch size must be >= 1, got {args.batch_size}")

    dry_run = not args.execute

    result = rebalance(
        sgf_dir=args.sgf_dir,
        index_path=args.index_path,
        batch_size=args.batch_size,
        dry_run=dry_run,
        checkpoint_path=args.checkpoint,
    )

    print(result)

    if dry_run and result.moves_needed > 0:
        sys.exit(2)  # Non-zero to indicate changes are pending
    sys.exit(0)


if __name__ == "__main__":
    main()
