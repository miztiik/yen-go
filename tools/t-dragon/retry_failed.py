"""
Retry failed cursors from a previous TsumegoDragon download run.

This script reads the JSONL log file, extracts failed API cursors,
and retries them one by one.

Usage:
    python -m tools.t-dragon.retry_failed <log_file>
    python -m tools.t-dragon.retry_failed external-sources/tsumegodragon/logs/download-20260204-185653.jsonl

The script will:
1. Parse the log file for api_error events
2. Extract the cursor values from failed requests
3. Re-fetch puzzles at those cursors (already-downloaded puzzles will be skipped)
"""

import argparse
import json
import re
import sys
from pathlib import Path

from .logging_config import setup_logging
from .orchestrator import DownloadConfig, download_puzzles


def extract_failed_cursors(log_path: Path) -> list[int]:
    """Extract cursor values from api_error events in JSONL log.

    Args:
        log_path: Path to the JSONL log file.

    Returns:
        List of cursor values that had API errors.
    """
    cursors = []

    with open(log_path, encoding='utf-8') as f:
        for line in f:
            try:
                entry = json.loads(line.strip())
                if entry.get('event_type') == 'api_error':
                    # Extract cursor from URL in data
                    data = entry.get('data', {})
                    url = data.get('url', '')

                    # Parse cursor from URL like: ...?limit=100&cursor=5900
                    match = re.search(r'cursor=(\d+)', url)
                    if match:
                        cursor = int(match.group(1))
                        if cursor not in cursors:
                            cursors.append(cursor)
            except json.JSONDecodeError:
                continue

    return sorted(cursors)


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Retry failed cursors from TsumegoDragon download logs",
    )
    parser.add_argument(
        "log_file",
        type=Path,
        help="Path to the JSONL log file from a previous run",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=15.0,
        help="Delay between API requests in seconds (default: 15)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("external-sources/tsumegodragon"),
        help="Output directory (default: external-sources/tsumegodragon)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be retried without executing",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    if not args.log_file.exists():
        print(f"Error: Log file not found: {args.log_file}")
        return 1

    # Extract failed cursors from log
    print(f"Parsing log file: {args.log_file}")
    failed_cursors = extract_failed_cursors(args.log_file)

    if not failed_cursors:
        print("No failed cursors found in log file.")
        return 0

    print(f"\nFound {len(failed_cursors)} failed cursors:")
    for cursor in failed_cursors:
        print(f"  - cursor={cursor}")

    if args.dry_run:
        print("\n[DRY RUN] Would retry the above cursors.")
        print("Run without --dry-run to execute.")
        return 0

    # Setup logging
    setup_logging(
        output_dir=args.output_dir,
        verbose=args.verbose,
        log_to_file=True,
    )

    total_downloaded = 0
    total_skipped = 0
    total_errors = 0

    # Retry each cursor with a limited batch (100 puzzles per cursor)
    for cursor in failed_cursors:
        print(f"\n{'='*60}")
        print(f"Retrying cursor={cursor}")
        print(f"{'='*60}")

        config = DownloadConfig(
            exhaustive=True,
            max_puzzles=100,  # One batch per cursor
            request_delay=args.delay,
            batch_size=500,
            output_dir=args.output_dir,
            resume=False,
            dry_run=False,
            start_cursor=cursor,
        )

        stats = download_puzzles(config)

        total_downloaded += stats.downloaded
        total_skipped += stats.skipped
        total_errors += stats.errors

        print(f"Cursor {cursor}: downloaded={stats.downloaded}, skipped={stats.skipped}, errors={stats.errors}")

    # Print summary
    print(f"\n{'='*60}")
    print("Retry Summary")
    print(f"{'='*60}")
    print(f"Total cursors retried: {len(failed_cursors)}")
    print(f"Total downloaded: {total_downloaded}")
    print(f"Total skipped: {total_skipped}")
    print(f"Total errors: {total_errors}")

    return 0 if total_errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
