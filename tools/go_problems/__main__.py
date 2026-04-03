"""
CLI entry point for GoProblems puzzle downloader.

Usage:
    python -m tools.go_problems --help
    python -m tools.go_problems --start-id 1 --end-id 5000 --resume
    python -m tools.go_problems --ids 100,200,300
    python -m tools.go_problems --list --max-puzzles 500
    python -m tools.go_problems --start-id 1 --end-id 50 --dry-run
"""

import argparse
import sys
import time
from pathlib import Path

from .config import (
    DEFAULT_BATCH_SIZE,
    DEFAULT_CANON_ONLY,
    DEFAULT_MAX_SOLUTION_DEPTH,
    DEFAULT_PUZZLE_DELAY,
    get_output_dir,
    to_relative_path,
)
from .logging_config import setup_logging
from .orchestrator import DownloadConfig, download_puzzles


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Download Go tsumego puzzles from goproblems.com",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Download puzzles by ID range
    python -m tools.go_problems --start-id 1 --end-id 5000

    # Download specific puzzle IDs
    python -m tools.go_problems --ids 42,100,250,999

    # Discover and download via paginated listing
    python -m tools.go_problems --list --max-puzzles 500

    # Resume interrupted download
    python -m tools.go_problems --start-id 1 --end-id 5000 --resume

    # Dry run (show what would be downloaded)
    python -m tools.go_problems --start-id 1 --end-id 100 --dry-run

    # Only canonical puzzles
    python -m tools.go_problems --start-id 1 --end-id 5000 --canon-only

Output Structure:
    external-sources/goproblems/
    +-- sgf/
    |   +-- batch-001/
    |   |   +-- 42.sgf
    |   |   +-- 100.sgf
    |   |   +-- ...
    |   +-- batch-002/
    |   +-- ...
    +-- logs/
    |   +-- 20260214-143022-goproblems.jsonl
    +-- sgf-index.txt
    +-- .checkpoint.json
        """,
    )

    # Fetch mode arguments
    mode_group = parser.add_argument_group("fetch mode (one required)")
    mode_group.add_argument(
        "--start-id",
        type=int,
        default=None,
        help="Start of puzzle ID range (inclusive)",
    )
    mode_group.add_argument(
        "--end-id",
        type=int,
        default=None,
        help="End of puzzle ID range (inclusive)",
    )
    mode_group.add_argument(
        "--ids",
        type=str,
        default=None,
        help="Comma-separated list of specific puzzle IDs (e.g., 42,100,250)",
    )
    mode_group.add_argument(
        "--list",
        action="store_true",
        dest="use_listing",
        help="Use paginated listing endpoint for puzzle discovery",
    )

    # Standard options
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
        help=f"Delay between requests in seconds (default: {DEFAULT_PUZZLE_DELAY})",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Output directory (default: external-sources/goproblems)",
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
        "--max-depth",
        type=int,
        default=DEFAULT_MAX_SOLUTION_DEPTH,
        help=f"Maximum solution depth (default: {DEFAULT_MAX_SOLUTION_DEPTH})",
    )

    # Filtering
    parser.add_argument(
        "--canon-only",
        action=argparse.BooleanOptionalAction,
        default=DEFAULT_CANON_ONLY,
        help="Only download canonical puzzles (default: enabled)",
    )

    # Feature flags
    parser.add_argument(
        "--match-collections",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Match collection names to YL[] slugs (default: enabled)",
    )
    parser.add_argument(
        "--resolve-intent",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Resolve root C[] comment to objective slug via puzzle_intent (default: enabled)",
    )
    parser.add_argument(
        "--intent-threshold",
        type=float,
        default=0.8,
        help="Minimum confidence for intent match (default: 0.8)",
    )

    # Logging
    parser.add_argument(
        "--no-log-file",
        action="store_true",
        help="Disable file logging (console only)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    # Validate fetch mode
    has_range = args.start_id is not None or args.end_id is not None
    has_ids = args.ids is not None
    has_list = args.use_listing

    mode_count = sum([has_range, has_ids, has_list])
    if mode_count == 0:
        parser.error(
            "One fetch mode required: --start-id/--end-id, --ids, or --list"
        )
    if mode_count > 1:
        parser.error(
            "Fetch modes are mutually exclusive: "
            "--start-id/--end-id, --ids, --list"
        )

    if has_range:
        if args.start_id is None or args.end_id is None:
            parser.error("--start-id and --end-id must be used together")
        if args.start_id > args.end_id:
            parser.error("--start-id must be <= --end-id")

    # Parse specific IDs
    puzzle_ids: list[int] | None = None
    if has_ids:
        try:
            puzzle_ids = [int(x.strip()) for x in args.ids.split(",")]
        except ValueError:
            parser.error("--ids must be comma-separated integers")

    # Determine output directory
    output_dir = get_output_dir(args.output_dir)

    # Setup structured logging
    slogger = setup_logging(
        output_dir=output_dir,
        verbose=args.verbose,
        log_to_file=not args.no_log_file,
    )

    # Log run start
    start_time = time.time()
    slogger.run_start(
        max_puzzles=args.max_puzzles,
        resume=args.resume,
        output_dir=to_relative_path(output_dir),
    )

    print(f"\n{'=' * 60}")
    print("GoProblems Puzzle Downloader")
    print(f"{'=' * 60}")
    print(f"Output directory: {to_relative_path(output_dir)}")
    print(f"Max puzzles: {args.max_puzzles}")
    print(f"Batch size: {args.batch_size}")
    if has_range:
        print(f"ID range: {args.start_id} - {args.end_id}")
    elif has_ids:
        print(f"Specific IDs: {len(puzzle_ids)} puzzles")  # type: ignore[arg-type]
    elif has_list:
        print("Mode: Paginated listing")
    print(f"Canon only: {args.canon_only}")
    print(f"Resume: {args.resume}")
    print(f"Dry run: {args.dry_run}")
    print(f"{'=' * 60}\n")

    # Build config
    config = DownloadConfig(
        max_puzzles=args.max_puzzles,
        resume=args.resume,
        dry_run=args.dry_run,
        output_dir=output_dir,
        start_id=args.start_id,
        end_id=args.end_id,
        puzzle_ids=puzzle_ids,
        use_listing=args.use_listing,
        puzzle_delay=args.puzzle_delay,
        batch_size=args.batch_size,
        max_solution_depth=args.max_depth,
        canon_only=args.canon_only,
        match_collections=args.match_collections,
        resolve_intent=args.resolve_intent,
        intent_confidence_threshold=args.intent_threshold,
    )

    # Run download
    stats = download_puzzles(config)

    # Log run end
    duration = time.time() - start_time
    slogger.run_end(
        downloaded=stats.downloaded,
        skipped=stats.skipped,
        errors=stats.errors,
        duration_sec=duration,
    )

    # Print summary
    print(f"\n{'=' * 60}")
    print("Download Summary")
    print(f"{'=' * 60}")
    print(f"Downloaded: {stats.downloaded}")
    print(f"Skipped: {stats.skipped}")
    print(f"Not found (404): {stats.not_found}")
    print(f"Errors: {stats.errors}")
    print(f"Duration: {duration:.1f}s ({duration / 60:.1f} minutes)")
    print(f"Output: {to_relative_path(output_dir)}")

    return 0 if stats.errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
