"""
CLI entry point for TsumegoDragon downloader.

Usage:
    python -m tools.t_dragon --help
    python -m tools.t_dragon --exhaustive --max-puzzles 100
"""

import argparse
import sys
import time
from pathlib import Path

from .config import DEFAULT_BATCH_SIZE, DEFAULT_REQUEST_DELAY, TOOL_NAME, to_relative_path
from .logging_config import setup_logging
from .orchestrator import DownloadConfig, download_puzzles


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Download Go tsumego puzzles from TsumegoDragon.com",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--exhaustive",
        action="store_true",
        help="Download ALL puzzles without category/level filtering",
    )
    parser.add_argument(
        "--max-puzzles",
        type=int,
        default=None,
        help="Maximum puzzles to download (default: 100, unlimited if --exhaustive)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=DEFAULT_REQUEST_DELAY,
        help=f"Delay between API requests in seconds (default: {DEFAULT_REQUEST_DELAY})",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help=f"Max files per batch directory (default: {DEFAULT_BATCH_SIZE})",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("external-sources/tsumegodragon"),
        help="Output directory (default: external-sources/tsumegodragon)",
    )
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
    parser.add_argument(
        "--start-cursor",
        type=int,
        default=None,
        help="Start from a specific cursor position (for retrying failed batches)",
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

    args = parser.parse_args()

    # Set max_puzzles default based on mode
    if args.max_puzzles is None:
        # Exhaustive mode: no limit; normal mode: 100
        args.max_puzzles = 1_000_000 if args.exhaustive else 100

    # Setup structured logging (console + JSON file)
    logger = setup_logging(
        output_dir=args.output_dir,
        verbose=args.verbose,
        log_to_file=not args.no_log_file,
    )

    # Console banner
    print(f"\n{'='*60}")
    print(f"{TOOL_NAME}")
    print(f"{'='*60}")
    print(f"Output directory: {to_relative_path(args.output_dir)}")
    print(f"Max puzzles: {args.max_puzzles}")
    print(f"Batch size: {args.batch_size}")
    print(f"Resume: {args.resume}")
    print(f"Dry run: {args.dry_run}")
    print(f"Match collections: {args.match_collections}")
    print(f"Resolve intent: {args.resolve_intent}")
    print(f"{'='*60}\n")

    # Log run start
    start_time = time.time()
    logger.run_start(
        max_puzzles=args.max_puzzles,
        exhaustive=args.exhaustive,
        resume=args.resume,
    )

    # Build config
    config = DownloadConfig(
        exhaustive=args.exhaustive,
        max_puzzles=args.max_puzzles,
        request_delay=args.delay,
        batch_size=args.batch_size,
        output_dir=args.output_dir,
        resume=args.resume,
        dry_run=args.dry_run,
        start_cursor=args.start_cursor,
        match_collections=args.match_collections,
        resolve_intent=args.resolve_intent,
        min_stones=args.min_stones,
    )

    # Run download
    stats = download_puzzles(config)

    # Log run end
    duration = time.time() - start_time
    logger.run_end(
        downloaded=stats.downloaded,
        skipped=stats.skipped,
        errors=stats.errors,
        duration_sec=duration,
    )

    # Print summary
    print(f"\n{'='*60}")
    print("Download Summary")
    print(f"{'='*60}")
    print(f"Downloaded: {stats.downloaded}")
    print(f"Skipped: {stats.skipped}")
    print(f"Errors: {stats.errors}")
    print(f"Duration: {duration:.1f}s ({duration/60:.1f} minutes)")
    print(f"Output: {to_relative_path(args.output_dir)}")
    print(f"{'='*60}")

    return 0 if stats.errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
