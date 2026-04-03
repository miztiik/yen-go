"""
Gap finder utility for Tsumego Hero downloads.

Analyzes downloaded puzzles to find missing puzzle IDs for targeted downloads.

Usage:
    python -m tools.tsumego_hero.gap_finder [--max-id N] [--output FILE]

    --max-id N      Maximum puzzle ID to check (default: 17500)
    --min-id N      Minimum puzzle ID to check (default: 1)
    --output FILE   Output file for missing IDs (default: missing-ids.txt)
    --sorted-index  Also write sorted index file

Output files:
    missing-ids.txt     - One ID per line, numerically sorted
    sorted-index.txt    - Downloaded IDs, numerically sorted (if --sorted-index)
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Base output directory
OUTPUT_DIR = Path("external-sources/t-hero")


def extract_puzzle_id(path_str: str) -> int | None:
    """Extract numeric puzzle ID from a path like 'sgf/batch-001/th-5225.sgf'.

    Args:
        path_str: Relative path string from index.

    Returns:
        Puzzle ID as integer, or None if not parseable.
    """
    # Match th-{number}.sgf pattern
    match = re.search(r'th-(\d+)\.sgf$', path_str)
    if match:
        return int(match.group(1))
    return None


def get_downloaded_ids_from_index(output_dir: Path) -> set[int]:
    """Get all puzzle IDs from the sgf-index.txt file.

    Args:
        output_dir: Base output directory.

    Returns:
        Set of downloaded puzzle IDs.
    """
    index_path = output_dir / "sgf-index.txt"

    if not index_path.exists():
        return set()

    ids: set[int] = set()
    with open(index_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                puzzle_id = extract_puzzle_id(line)
                if puzzle_id is not None:
                    ids.add(puzzle_id)

    return ids


def get_downloaded_ids_from_batches(output_dir: Path) -> set[int]:
    """Scan batch directories for puzzle IDs (fallback if no index).

    Args:
        output_dir: Base output directory.

    Returns:
        Set of downloaded puzzle IDs.
    """
    sgf_dir = output_dir / "sgf"

    if not sgf_dir.exists():
        return set()

    ids: set[int] = set()
    for batch_dir in sgf_dir.iterdir():
        if batch_dir.is_dir() and batch_dir.name.startswith("batch-"):
            for sgf_file in batch_dir.glob("th-*.sgf"):
                puzzle_id = extract_puzzle_id(sgf_file.name)
                if puzzle_id is not None:
                    ids.add(puzzle_id)

    return ids


def find_missing_ids(
    downloaded_ids: set[int],
    min_id: int = 1,
    max_id: int = 17500,
) -> list[int]:
    """Find missing puzzle IDs in the given range.

    Args:
        downloaded_ids: Set of already-downloaded IDs.
        min_id: Start of the ID range (inclusive).
        max_id: End of the ID range (inclusive).

    Returns:
        Sorted list of missing IDs.
    """
    all_ids = set(range(min_id, max_id + 1))
    missing = all_ids - downloaded_ids
    return sorted(missing)


def write_missing_ids(
    missing_ids: list[int],
    output_path: Path,
) -> int:
    """Write missing IDs to a file, one per line.

    Args:
        missing_ids: Sorted list of missing IDs.
        output_path: Path to output file.

    Returns:
        Number of IDs written.
    """
    with open(output_path, "w", encoding="utf-8") as f:
        for puzzle_id in missing_ids:
            f.write(f"{puzzle_id}\n")
    return len(missing_ids)


def write_sorted_index(
    downloaded_ids: set[int],
    output_path: Path,
) -> int:
    """Write sorted list of downloaded IDs to a file.

    Args:
        downloaded_ids: Set of downloaded IDs.
        output_path: Path to output file.

    Returns:
        Number of IDs written.
    """
    sorted_ids = sorted(downloaded_ids)
    with open(output_path, "w", encoding="utf-8") as f:
        for puzzle_id in sorted_ids:
            f.write(f"{puzzle_id}\n")
    return len(sorted_ids)


def print_id_stats(downloaded_ids: set[int], missing_ids: list[int]) -> None:
    """Print statistics about downloaded and missing IDs.

    Args:
        downloaded_ids: Set of downloaded IDs.
        missing_ids: List of missing IDs.
    """
    if not downloaded_ids:
        print("No downloaded puzzles found.")
        return

    sorted_downloaded = sorted(downloaded_ids)
    min_downloaded = sorted_downloaded[0]
    max_downloaded = sorted_downloaded[-1]

    print(f"Downloaded puzzles: {len(downloaded_ids)}")
    print(f"ID range in downloads: {min_downloaded} - {max_downloaded}")
    print(f"Missing puzzles: {len(missing_ids)}")

    if missing_ids:
        # Show some missing ranges
        ranges = []
        start = missing_ids[0]
        end = start

        for i in range(1, len(missing_ids)):
            if missing_ids[i] == end + 1:
                end = missing_ids[i]
            else:
                if start == end:
                    ranges.append(str(start))
                else:
                    ranges.append(f"{start}-{end}")
                start = missing_ids[i]
                end = start

        # Final range
        if start == end:
            ranges.append(str(start))
        else:
            ranges.append(f"{start}-{end}")

        # Show first 5 gaps
        preview = ranges[:5]
        print(f"First missing ranges: {', '.join(preview)}")
        if len(ranges) > 5:
            print(f"  ... and {len(ranges) - 5} more ranges")


def main() -> int:
    """Main entry point for gap finder utility."""
    parser = argparse.ArgumentParser(
        description="Find missing Tsumego Hero puzzle IDs for targeted downloads."
    )
    parser.add_argument(
        "--min-id",
        type=int,
        default=1,
        help="Minimum puzzle ID to check (default: 1)",
    )
    parser.add_argument(
        "--max-id",
        type=int,
        default=17500,
        help="Maximum puzzle ID to check (default: 17500)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="missing-ids.txt",
        help="Output file for missing IDs (default: missing-ids.txt)",
    )
    parser.add_argument(
        "--sorted-index",
        action="store_true",
        help="Also write sorted index of downloaded IDs",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=str(OUTPUT_DIR),
        help=f"Base output directory (default: {OUTPUT_DIR})",
    )

    args = parser.parse_args()
    output_dir = Path(args.output_dir)

    print(f"Scanning for downloaded puzzles in: {output_dir}")

    # Try index first, fall back to batch scan
    downloaded_ids = get_downloaded_ids_from_index(output_dir)
    if not downloaded_ids:
        print("No index found, scanning batch directories...")
        downloaded_ids = get_downloaded_ids_from_batches(output_dir)

    # Find missing IDs
    missing_ids = find_missing_ids(downloaded_ids, args.min_id, args.max_id)

    # Print stats
    print_id_stats(downloaded_ids, missing_ids)

    # Write missing IDs
    output_path = output_dir / args.output
    count = write_missing_ids(missing_ids, output_path)
    print(f"\nWrote {count} missing IDs to: {output_path}")

    # Optionally write sorted index
    if args.sorted_index:
        sorted_path = output_dir / "sorted-index.txt"
        count = write_sorted_index(downloaded_ids, sorted_path)
        print(f"Wrote {count} downloaded IDs to: {sorted_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
