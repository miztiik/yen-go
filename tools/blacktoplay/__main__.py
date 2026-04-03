"""
CLI entry point for BlackToPlay (BTP) puzzle downloader.

Usage:
    python -m tools.blacktoplay --help
    python -m tools.blacktoplay --max-puzzles 100 --dry-run
    python -m tools.blacktoplay --resume
    python -m tools.blacktoplay --types classic ai
"""

import argparse
import sys
from pathlib import Path

from .config import (
    ALL_PUZZLE_TYPES,
    DEFAULT_BATCH_SIZE,
    DEFAULT_PUZZLE_DELAY,
    PUZZLE_TYPE_NAMES,
    get_logs_dir,
    get_output_dir,
)
from .logging_config import setup_logging
from .orchestrator import DownloadConfig, download_puzzles

# Map CLI type names to constants
_TYPE_NAME_TO_INT = {v: k for k, v in PUZZLE_TYPE_NAMES.items()}


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Download Go tsumego puzzles from BlackToPlay.com",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Enrichment (applied by default):
    YG[]  Level mapping     BTP rating -> 9-level slug (--match-collections has no effect)
    YT[]  Tag mapping       BTP tags -> YenGo tags (always applied)
    YL[]  Collections       BTP categories -> YenGo collections (--match-collections/--no-match-collections)
    C[]   Intent/objective  Derived from categories+tags (--resolve-intent/--no-resolve-intent)

Examples:
    # Download up to 100 puzzles (dry run)
    python -m tools.blacktoplay --max-puzzles 100 --dry-run

    # Download all classic puzzles
    python -m tools.blacktoplay --types classic

    # Resume interrupted download
    python -m tools.blacktoplay --resume

    # Download without collection or intent enrichment
    python -m tools.blacktoplay --no-match-collections --no-resolve-intent

    # Download all types with verbose logging
    python -m tools.blacktoplay --max-puzzles 5000 -v

Output Structure:
    external-sources/blacktoplay/
    ├── sgf/
    │   ├── batch-001/
    │   │   ├── btp-1.sgf
    │   │   ├── btp-42.sgf
    │   │   └── ...
    │   ├── batch-002/
    │   └── ...
    ├── logs/
    │   └── btp-download-YYYYMMDD_HHMMSS.jsonl
    └── .checkpoint.json
        """,
    )

    parser.add_argument(
        "--max-puzzles",
        type=int,
        default=10000,
        help="Maximum puzzles to download (default: 10000)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help=f"Max files per batch directory (default: {DEFAULT_BATCH_SIZE})",
    )
    parser.add_argument(
        "--puzzle-delay",
        type=float,
        default=DEFAULT_PUZZLE_DELAY,
        help=f"Delay between puzzle requests in seconds (default: {DEFAULT_PUZZLE_DELAY})",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Output directory (default: external-sources/blacktoplay)",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from last checkpoint",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be downloaded without writing files",
    )
    parser.add_argument(
        "--types",
        nargs="+",
        choices=["classic", "ai", "endgame"],
        default=None,
        help="Puzzle types to download (default: all)",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable cached puzzle list fallback",
    )
    parser.add_argument(
        "--no-log-file",
        action="store_true",
        help="Disable file logging (console only)",
    )
    parser.add_argument(
        "--match-collections",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Enable YL[] collection matching from BTP categories (default: enabled)",
    )
    parser.add_argument(
        "--resolve-intent",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Enable C[] intent/objective resolution from categories+tags (default: enabled)",
    )
    parser.add_argument(
        "--intent-threshold",
        type=float,
        default=0.8,
        help="Minimum confidence for intent match (default: 0.8)",
    )
    parser.add_argument(
        "--min-stones",
        type=int,
        default=None,
        help="Minimum stones required on board (overrides config default of 2)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose (DEBUG) logging",
    )

    args = parser.parse_args()

    # Resolve output directory
    output_dir = get_output_dir(args.output_dir)
    logs_dir = get_logs_dir(output_dir)

    # Set up logging
    logger = setup_logging(
        logs_dir=logs_dir if not args.dry_run and not args.no_log_file else None,
        verbose=args.verbose,
    )

    # Resolve puzzle types
    if args.types:
        puzzle_types = [_TYPE_NAME_TO_INT[t] for t in args.types]
    else:
        puzzle_types = list(ALL_PUZZLE_TYPES)

    type_names = [PUZZLE_TYPE_NAMES[t] for t in puzzle_types]
    logger.info(
        "BTP Downloader: max=%d, types=%s, resume=%s, dry_run=%s",
        args.max_puzzles,
        type_names,
        args.resume,
        args.dry_run,
    )

    # Build config
    config = DownloadConfig(
        max_puzzles=args.max_puzzles,
        resume=args.resume,
        dry_run=args.dry_run,
        output_dir=output_dir,
        puzzle_types=puzzle_types,
        puzzle_delay=args.puzzle_delay,
        batch_size=args.batch_size,
        use_cache=not args.no_cache,
        match_collections=args.match_collections,
        resolve_intent=args.resolve_intent,
        min_stones=args.min_stones,
    )

    # Run download
    stats = download_puzzles(config)

    # Summary
    elapsed = stats.elapsed_seconds()
    print(f"\n{'=' * 60}")
    print("BTP Download Complete")
    print(f"  Downloaded: {stats.downloaded}")
    print(f"  Skipped:    {stats.skipped}")
    print(f"  Errors:     {stats.errors}")
    print(f"  Time:       {elapsed:.1f}s")
    if stats.downloaded > 0:
        print(f"  Avg:        {stats.avg_seconds_per_puzzle():.2f}s/puzzle")
    print(f"{'=' * 60}")

    return 0 if stats.errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
