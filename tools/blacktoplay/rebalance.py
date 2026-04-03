"""
BTP Batch Rebalancer and Gap Analyzer.

Analyzes BTP puzzles, finds missing numeric IDs, and rebalances files into
properly sorted batch directories.

BTP ID Types:
- Numeric (6-digit): 000001-999999 (Classic puzzles, type=0)
- Alphanumeric: e.g., "82q0Z4", "mcz1Dp" (AI/Endgame puzzles, type=1/2)

Sorting Strategy:
1. Numeric IDs first, sorted ascending (000001 < 000002 < 999999)
2. Alphanumeric IDs second, sorted lexicographically (10v0v1 < 1Ak208 < 82q0Z4)

Usage:
    # Analyze only (default):
    python -m tools.blacktoplay.rebalance

    # Execute rebalance:
    python -m tools.blacktoplay.rebalance --execute

    # Custom batch size:
    python -m tools.blacktoplay.rebalance --batch-size 500 --execute
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from .index import rebuild_index

# Regex patterns
_NUMERIC_PATTERN = re.compile(r"^btp-(\d{6})\.sgf$")
_ALPHANUMERIC_PATTERN = re.compile(r"^btp-([a-zA-Z0-9]+)\.sgf$")

# Defaults
DEFAULT_BATCH_SIZE = 1000
DEFAULT_PAD_WIDTH = 3

# Paths
BTP_ROOT = Path(__file__).parent.parent.parent / "external-sources" / "blacktoplay"
SGF_DIR = BTP_ROOT / "sgf"
INDEX_PATH = BTP_ROOT / "sgf-index.txt"
OUTPUT_DIR = Path(__file__).parent / "temp"


@dataclass(frozen=True)
class FileEntry:
    """A cataloged file with sort key and current location."""

    puzzle_id: str  # Raw ID (e.g., "000719" or "82q0Z4")
    is_numeric: bool
    numeric_value: int  # For numeric IDs, the int value; for alpha, a high number
    filename: str
    current_dir: str  # e.g., "batch-001"
    full_path: Path


@dataclass(frozen=True)
class Move:
    """A file move operation."""

    src: Path
    dst: Path
    filename: str


@dataclass
class RebalanceResult:
    """Summary of a rebalance operation."""

    total_files: int
    numeric_files: int
    alphanumeric_files: int
    batches_before: int
    batches_after: int
    moves_needed: int
    moves_executed: int
    empty_dirs_removed: int
    index_entries: int
    dry_run: bool
    missing_numeric_ids: list[int]

    def __str__(self) -> str:
        mode = "DRY RUN" if self.dry_run else "EXECUTED"
        return (
            f"[{mode}] BTP Rebalance Summary:\n"
            f"  Total files:          {self.total_files:,}\n"
            f"  Numeric IDs:          {self.numeric_files:,}\n"
            f"  Alphanumeric IDs:     {self.alphanumeric_files:,}\n"
            f"  Batches before:       {self.batches_before}\n"
            f"  Batches after:        {self.batches_after}\n"
            f"  Moves needed:         {self.moves_needed:,}\n"
            f"  Moves executed:       {self.moves_executed:,}\n"
            f"  Empty dirs removed:   {self.empty_dirs_removed}\n"
            f"  Index entries:        {self.index_entries:,}\n"
            f"  Missing numeric IDs:  {len(self.missing_numeric_ids)}"
        )


def catalog_files(sgf_dir: Path) -> list[FileEntry]:
    """Scan all batch-* directories and catalog every .sgf file.

    Returns a sorted list: numeric IDs first (ascending), then alphanumeric (lexicographic).
    """
    entries: list[FileEntry] = []

    if not sgf_dir.exists():
        return entries

    for batch_dir in sgf_dir.iterdir():
        if not batch_dir.is_dir() or not batch_dir.name.startswith("batch-"):
            continue

        for sgf_file in batch_dir.iterdir():
            if not sgf_file.is_file() or not sgf_file.name.endswith(".sgf"):
                continue

            # Try numeric pattern first
            m = _NUMERIC_PATTERN.match(sgf_file.name)
            if m:
                puzzle_id = m.group(1)
                entries.append(FileEntry(
                    puzzle_id=puzzle_id,
                    is_numeric=True,
                    numeric_value=int(puzzle_id),
                    filename=sgf_file.name,
                    current_dir=batch_dir.name,
                    full_path=sgf_file,
                ))
            else:
                # Try alphanumeric
                m = _ALPHANUMERIC_PATTERN.match(sgf_file.name)
                if m:
                    puzzle_id = m.group(1)
                    entries.append(FileEntry(
                        puzzle_id=puzzle_id,
                        is_numeric=False,
                        numeric_value=10_000_000,  # Sort after all numeric
                        filename=sgf_file.name,
                        current_dir=batch_dir.name,
                        full_path=sgf_file,
                    ))

    # Sort: numeric first by value, then alphanumeric lexicographically
    entries.sort(key=lambda e: (not e.is_numeric, e.numeric_value if e.is_numeric else 0, e.puzzle_id))
    return entries


def find_missing_numeric_ids(entries: list[FileEntry]) -> list[int]:
    """Find gaps in the numeric ID sequence.

    E.g., if we have [1, 2, 4, 5, 7], returns [3, 6].
    """
    numeric_ids = sorted(e.numeric_value for e in entries if e.is_numeric)

    if not numeric_ids:
        return []

    missing: list[int] = []
    min_id, max_id = min(numeric_ids), max(numeric_ids)

    id_set = set(numeric_ids)
    for i in range(min_id, max_id + 1):
        if i not in id_set:
            missing.append(i)

    return missing


def batch_name(batch_number: int, pad_width: int = DEFAULT_PAD_WIDTH) -> str:
    """Format a batch directory name."""
    return f"batch-{batch_number:0{pad_width}d}"


def compute_moves(
    catalog: list[FileEntry],
    batch_size: int,
    pad_width: int = DEFAULT_PAD_WIDTH,
) -> list[Move]:
    """Compute file moves to rebalance batches.

    Each file at index i goes to batch (i // batch_size) + 1.
    """
    moves: list[Move] = []

    for i, entry in enumerate(catalog):
        target_batch_num = (i // batch_size) + 1
        target_dir_name = batch_name(target_batch_num, pad_width)

        if entry.current_dir == target_dir_name:
            continue

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
    """Execute file moves using os.rename."""
    # Pre-create all target batch directories
    for bn in range(1, total_batches + 1):
        target = sgf_dir / batch_name(bn, pad_width)
        target.mkdir(exist_ok=True)

    executed = 0
    for move in moves:
        if move.dst.exists():
            raise FileExistsError(f"Destination exists: {move.dst}")

        move.dst.parent.mkdir(parents=True, exist_ok=True)
        os.rename(move.src, move.dst)
        executed += 1

    return executed


def remove_empty_batch_dirs(sgf_dir: Path) -> int:
    """Remove empty batch-* directories."""
    removed = 0
    for entry in sorted(sgf_dir.iterdir()):
        if (
            entry.is_dir()
            and entry.name.startswith("batch-")
            and not any(entry.iterdir())
        ):
            entry.rmdir()
            removed += 1
    return removed


def rebalance(
    sgf_dir: Path,
    index_path: Path,
    batch_size: int = DEFAULT_BATCH_SIZE,
    execute: bool = False,
) -> RebalanceResult:
    """Rebalance BTP SGF files into sorted batch directories.

    Args:
        sgf_dir: Directory containing batch-* subdirectories.
        index_path: Path to sgf-index.txt.
        batch_size: Max files per batch.
        execute: If False (default), dry-run only.

    Returns:
        RebalanceResult with operation summary.
    """
    print(f"\n{'='*60}")
    print("BTP BATCH REBALANCER")
    print(f"{'='*60}")
    print(f"SGF directory: {sgf_dir}")
    print(f"Index path: {index_path}")
    print(f"Batch size: {batch_size}")
    print(f"Mode: {'EXECUTE' if execute else 'DRY RUN'}")
    print(f"{'='*60}\n")

    # Catalog files
    print("[1] Cataloging files...")
    catalog = catalog_files(sgf_dir)
    numeric_count = sum(1 for e in catalog if e.is_numeric)
    alpha_count = len(catalog) - numeric_count
    print(f"    Total files: {len(catalog)}")
    print(f"    Numeric IDs: {numeric_count}")
    print(f"    Alphanumeric IDs: {alpha_count}")

    if not catalog:
        print("    No files found.")
        return RebalanceResult(
            total_files=0, numeric_files=0, alphanumeric_files=0,
            batches_before=0, batches_after=0, moves_needed=0,
            moves_executed=0, empty_dirs_removed=0, index_entries=0,
            dry_run=not execute, missing_numeric_ids=[],
        )

    # Find missing numeric IDs
    print("\n[2] Finding missing numeric IDs...")
    missing = find_missing_numeric_ids(catalog)
    print(f"    Missing IDs: {len(missing)}")
    if missing and len(missing) <= 20:
        print(f"    IDs: {missing}")
    elif missing:
        print(f"    First 10: {missing[:10]}")
        print(f"    Last 10: {missing[-10:]}")

    # Save missing IDs to file
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    missing_file = OUTPUT_DIR / "missing_numeric_ids.txt"
    with open(missing_file, "w") as f:
        f.write("# Missing numeric BTP puzzle IDs (gaps in sequence)\n")
        f.write(f"# Count: {len(missing)}\n\n")
        for mid in missing:
            f.write(f"{mid:06d}\n")
    print(f"    Saved to: {missing_file.name}")

    # Count batches before
    batches_before = len([d for d in sgf_dir.iterdir() if d.is_dir() and d.name.startswith("batch-")])

    # Compute moves
    print("\n[3] Computing file moves...")
    pad_width = DEFAULT_PAD_WIDTH
    moves = compute_moves(catalog, batch_size, pad_width)
    total_batches = (len(catalog) + batch_size - 1) // batch_size
    print(f"    Moves needed: {len(moves)}")
    print(f"    Target batches: {total_batches}")

    # Show sample moves
    if moves and len(moves) <= 10:
        print("    Moves:")
        for m in moves:
            print(f"      {m.src.parent.name}/{m.filename} -> {m.dst.parent.name}/")
    elif moves:
        print("    First 5 moves:")
        for m in moves[:5]:
            print(f"      {m.src.parent.name}/{m.filename} -> {m.dst.parent.name}/")

    # Execute or dry-run
    moves_executed = 0
    empty_removed = 0
    index_entries = 0

    if execute and moves:
        print("\n[4] Executing moves...")
        moves_executed = execute_moves(moves, sgf_dir, pad_width, total_batches)
        print(f"    Moved {moves_executed} files")

        print("\n[5] Removing empty directories...")
        empty_removed = remove_empty_batch_dirs(sgf_dir)
        print(f"    Removed {empty_removed} empty directories")

        print("\n[6] Rebuilding index...")
        # rebuild_index takes (output_dir, sgf_dir)
        output_dir = index_path.parent
        index_entries = rebuild_index(output_dir, sgf_dir)
        print(f"    Index entries: {index_entries}")
    elif execute:
        print("\n[4] No moves needed - files already balanced")
        # Still rebuild index in case it's out of sync
        print("[5] Rebuilding index...")
        output_dir = index_path.parent
        index_entries = rebuild_index(output_dir, sgf_dir)
        print(f"    Index entries: {index_entries}")
    else:
        print("\n[4] DRY RUN - no changes made")
        print("    Run with --execute to apply changes")
        # Count what index would have
        index_entries = len(catalog)

    batches_after = total_batches if execute else batches_before

    result = RebalanceResult(
        total_files=len(catalog),
        numeric_files=numeric_count,
        alphanumeric_files=alpha_count,
        batches_before=batches_before,
        batches_after=batches_after,
        moves_needed=len(moves),
        moves_executed=moves_executed,
        empty_dirs_removed=empty_removed,
        index_entries=index_entries,
        dry_run=not execute,
        missing_numeric_ids=missing,
    )

    print(f"\n{'='*60}")
    print(result)
    print(f"{'='*60}\n")

    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Rebalance BTP SGF files into sorted batch directories"
    )
    parser.add_argument(
        "--sgf-dir",
        type=Path,
        default=SGF_DIR,
        help=f"SGF directory (default: {SGF_DIR})",
    )
    parser.add_argument(
        "--index-path",
        type=Path,
        default=INDEX_PATH,
        help=f"Index file path (default: {INDEX_PATH})",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help=f"Files per batch (default: {DEFAULT_BATCH_SIZE})",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Execute changes (default: dry-run only)",
    )

    args = parser.parse_args()

    result = rebalance(
        sgf_dir=args.sgf_dir,
        index_path=args.index_path,
        batch_size=args.batch_size,
        execute=args.execute,
    )

    return 0 if result.moves_executed == result.moves_needed or result.dry_run else 1


if __name__ == "__main__":
    sys.exit(main())
