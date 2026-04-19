#!/usr/bin/env python3
"""
CLI entry point for Tsumego Hero downloader.

Usage:
    python -m tools.tsumego_hero --help
    python -m tools.tsumego_hero --max-puzzles 100 --resume
    python -m tools.tsumego_hero --list-collections
    python -m tools.tsumego_hero --collection 104 --max-puzzles 50
    python -m tools.tsumego_hero --from-ids missing-ids.txt --max-puzzles 500
"""

import argparse
import sys
import time
from pathlib import Path

from tools.core.paths import rel_path

from .batching import THERO_BATCH_SIZE
from .client import TsumegoHeroClient
from .logging_config import setup_logging
from .orchestrator import (
    DEFAULT_OUTPUT_DIR,
    TOOL_NAME,
    DownloadConfig,
    download_from_ids,
    download_puzzles,
)


def list_collections() -> int:
    """List available collections from Tsumego Hero."""
    print("\nFetching collections from tsumego.com...")

    with TsumegoHeroClient() as client:
        collections = client.fetch_collections()

    print(f"\nFound {len(collections)} collections:\n")
    print(f"{'ID':>6}  {'Name':<45} {'Puzzles':>8}")
    print("-" * 65)

    total_puzzles = 0
    for set_id, info in sorted(collections.items(), key=lambda x: int(x[0])):
        name = info.get("name", "Unknown")
        count = info.get("puzzle_count")
        count_str = str(count) if count else "?"
        print(f"{set_id:>6}  {name:<45} {count_str:>8}")
        if count:
            total_puzzles += count

    print("-" * 65)
    print(f"Total collections: {len(collections)}, puzzles: ~{total_puzzles}")
    print("\nTo download a specific collection:")
    print("  python -m tools.tsumego_hero --collection <ID> --max-puzzles 50")
    print("\nTo download all collections:")
    print("  python -m tools.tsumego_hero --max-puzzles 1000 --resume")

    return 0


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Download Go tsumego puzzles from Tsumego Hero (tsumego.com)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # List available collections
    python -m tools.tsumego_hero --list-collections

    # Download up to 100 puzzles
    python -m tools.tsumego_hero --max-puzzles 100

    # Resume interrupted download
    python -m tools.tsumego_hero --resume

    # Dry run (show what would be downloaded)
    python -m tools.tsumego_hero --max-puzzles 100 --dry-run

    # Download specific collection
    python -m tools.tsumego_hero --collection 104 --max-puzzles 50

    # Download ALL collections + automatically fill gaps (recommended for complete download)
    python -m tools.tsumego_hero --max-puzzles 15000 --fill-gaps

    # Same but resume if interrupted
    python -m tools.tsumego_hero --max-puzzles 15000 --fill-gaps --resume

    # Gap-fill: download from manually generated ID list
    python -m tools.tsumego_hero --from-ids missing-ids.txt --max-puzzles 500

Output Structure:
    external-sources/t-hero/
    +-- sgf/
    |   +-- batch-001/
    |   |   +-- th-5225.sgf
    |   |   +-- th-5226.sgf
    |   |   +-- ...
    |   +-- batch-002/
    |   +-- ...
    +-- logs/
    |   +-- tsumego-hero-YYYYMMDD_HHMMSS.jsonl
    +-- sgf-index.txt
    +-- .checkpoint.json
        """,
    )

    # Mode flags
    parser.add_argument(
        "--list-collections",
        action="store_true",
        help="List available collections and exit",
    )
    parser.add_argument(
        "--from-ids",
        type=Path,
        metavar="FILE",
        help="Download from a file of puzzle IDs (one per line, for gap-filling)",
    )

    # Download options
    parser.add_argument(
        "--collection",
        type=str,
        action="append",
        dest="collections",
        help="Download specific collection(s) by set ID (can be repeated)",
    )
    parser.add_argument(
        "--max-puzzles",
        type=int,
        default=100,
        help="Maximum puzzles to download (default: 100)",
    )
    parser.add_argument(
        "--max-per-collection",
        type=int,
        default=None,
        help="Maximum puzzles per collection (default: unlimited)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=THERO_BATCH_SIZE,
        help=f"Max files per batch directory (default: {THERO_BATCH_SIZE})",
    )

    # Rate limiting
    parser.add_argument(
        "--delay",
        type=float,
        default=2.5,
        help="Base delay between requests in seconds (default: 2.5)",
    )
    parser.add_argument(
        "--jitter",
        type=float,
        default=0.4,
        help="Jitter factor for delay randomization (default: 0.4)",
    )

    # Output options
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Output directory (default: {DEFAULT_OUTPUT_DIR})",
    )

    # Resume and dry-run
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from last checkpoint",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be downloaded without downloading",
    )

    # Enrichment flags
    parser.add_argument(
        "--match-collections",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Enable YL[] collection matching (default: enabled)",
    )
    parser.add_argument(
        "--resolve-intent",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Enable C[] intent resolution (default: enabled)",
    )
    parser.add_argument(
        "--min-stones",
        type=int,
        default=None,
        help="Minimum stones required on the board (overrides config default of 2)",
    )
    parser.add_argument(
        "--min-board-size",
        type=int,
        default=None,
        help="Minimum board dimension (overrides config default of 5)",
    )
    parser.add_argument(
        "--max-solution-depth",
        type=int,
        default=None,
        help="Maximum solution depth (0 = no cap, overrides config default of 30)",
    )
    parser.add_argument(
        "--min-solution-depth",
        type=int,
        default=None,
        help="Minimum solution depth (0 = allow no-solution puzzles, overrides config default of 1)",
    )

    # Logging
    # Gap fill
    parser.add_argument(
        "--fill-gaps",
        action="store_true",
        help=(
            "After collection download, automatically scan for out-of-collection "
            "puzzles and download them (repeats until no new puzzles found)"
        ),
    )
    parser.add_argument(
        "--fill-gaps-max-id",
        type=int,
        default=17500,
        help="Maximum puzzle ID to scan during gap fill (default: 17500)",
    )

    parser.add_argument(
        "--no-log-file",
        action="store_true",
        help="Disable file logging (console only)",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    # Handle --list-collections
    if args.list_collections:
        return list_collections()

    # Setup structured logging
    logger = setup_logging(
        output_dir=args.output_dir,
        verbose=args.verbose,
        log_to_file=not args.no_log_file,
    )

    # Console banner
    print(f"\n{'='*60}")
    print(f"{TOOL_NAME}")
    print(f"{'='*60}")
    print(f"Output directory: {rel_path(args.output_dir)}")
    print(f"Max puzzles: {args.max_puzzles}")
    print(f"Batch size: {args.batch_size}")
    print(f"Resume: {args.resume}")
    print(f"Dry run: {args.dry_run}")
    print(f"Match collections: {args.match_collections}")
    print(f"Resolve intent: {args.resolve_intent}")
    if not args.from_ids:
        print(f"Fill gaps:     {args.fill_gaps}" + (f" (max-id={args.fill_gaps_max_id})" if args.fill_gaps else ""))
    print(f"{'='*60}\n")

    # Handle --from-ids mode (gap-fill)
    if args.from_ids:
        logger.run_start(
            max_puzzles=args.max_puzzles,
            resume=args.resume,
        )

        config = DownloadConfig(
            max_puzzles=args.max_puzzles,
            resume=args.resume,
            dry_run=args.dry_run,
            output_dir=args.output_dir,
            batch_size=args.batch_size,
            request_delay=args.delay,
            jitter_factor=args.jitter,
            match_collections=args.match_collections,
            resolve_intent=args.resolve_intent,
            min_stones=args.min_stones,
            min_board_size=args.min_board_size,
            max_solution_depth=args.max_solution_depth,
            min_solution_depth=args.min_solution_depth,
        )

        try:
            stats = download_from_ids(args.from_ids, config)

            elapsed = time.time() - stats.start_time
            print(f"\n{'='*60}")
            print("Gap-Fill Summary")
            print(f"{'='*60}")
            print(f"Downloaded: {stats.downloaded}")
            print(f"Skipped:    {stats.skipped}")
            print(f"Not found:  {stats.errors}")
            print(f"Duration:   {elapsed:.1f}s ({elapsed/60:.1f} minutes)")
            print(f"Rate:       {stats.puzzles_per_minute():.1f} puzzles/min")
            print(f"Output:     {rel_path(args.output_dir)}")
            print(f"{'='*60}")

            return 0

        except KeyboardInterrupt:
            print("\nInterrupted by user")
            return 130

        except Exception as e:
            print(f"\nError: {e}", file=sys.stderr)
            return 1

    # Log run start
    start_time = time.time()
    logger.run_start(
        max_puzzles=args.max_puzzles,
        resume=args.resume,
    )

    # Build config
    config = DownloadConfig(
        collections=args.collections,
        max_puzzles=args.max_puzzles,
        max_per_collection=args.max_per_collection,
        resume=args.resume,
        dry_run=args.dry_run,
        output_dir=args.output_dir,
        batch_size=args.batch_size,
        request_delay=args.delay,
        jitter_factor=args.jitter,
        match_collections=args.match_collections,
        resolve_intent=args.resolve_intent,
        min_stones=args.min_stones,
        min_board_size=args.min_board_size,
        max_solution_depth=args.max_solution_depth,
        min_solution_depth=args.min_solution_depth,
        fill_gaps=args.fill_gaps,
        fill_gaps_max_id=args.fill_gaps_max_id,
    )

    # Run download
    try:
        stats = download_puzzles(config)

        # Print summary
        elapsed = time.time() - start_time
        print(f"\n{'='*60}")
        print("Download Summary")
        print(f"{'='*60}")
        print(f"Downloaded: {stats.downloaded}")
        print(f"Skipped:    {stats.skipped}")
        print(f"Errors:     {stats.errors}")
        print(f"Duration:   {elapsed:.1f}s ({elapsed/60:.1f} minutes)")
        print(f"Rate:       {stats.puzzles_per_minute():.1f} puzzles/min")
        print(f"Output:     {rel_path(args.output_dir)}")
        print(f"{'='*60}")

        return 0 if stats.errors == 0 else 1

    except KeyboardInterrupt:
        print("\nInterrupted by user")
        return 130

    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
