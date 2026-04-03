"""
CLI entry point for OGS puzzle downloader.

Usage:
    python -m tools.ogs --help
    python -m tools.ogs --max-puzzles 5000 --resume
    python -m tools.ogs --dry-run
    python -m tools.ogs embed-collections --source-dir external-sources/ogs/sgf-by-collection
"""

import argparse
import glob
import sys
import time
from pathlib import Path

from .config import (
    DEFAULT_BATCH_SIZE,
    DEFAULT_MAX_MOVE_TREE_DEPTH,
    DEFAULT_PAGE_DELAY,
    DEFAULT_PUZZLE_DELAY,
    get_output_dir,
    to_relative_path,
)
from .logging_config import setup_logging
from .orchestrator import DownloadConfig, download_puzzles


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Download Go tsumego puzzles from Online-Go.com (OGS)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Download up to 5000 puzzles
    python -m tools.ogs --max-puzzles 5000

    # Resume interrupted download
    python -m tools.ogs --resume

    # Dry run (show what would be downloaded)
    python -m tools.ogs --max-puzzles 100 --dry-run

    # Custom output directory
    python -m tools.ogs --output-dir external-sources/ogs-test

Output Structure:
    external-sources/ogs/
    ├── sgf/
    │   ├── batch-001/
    │   │   ├── ogs-45.sgf
    │   │   ├── ogs-1555.sgf
    │   │   └── ...
    │   ├── batch-002/
    │   └── ...
    ├── logs/
    │   └── ogs-download-YYYYMMDD_HHMMSS.jsonl
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
        "--page-delay",
        type=float,
        default=DEFAULT_PAGE_DELAY,
        help=f"Delay between page requests in seconds (default: {DEFAULT_PAGE_DELAY})",
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
        help="Output directory (default: external-sources/ogs)",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from last checkpoint",
    )
    parser.add_argument(
        "--start-page",
        type=int,
        default=None,
        help="Start from a specific page (overrides checkpoint)",
    )
    parser.add_argument(
        "--page",
        type=int,
        default=None,
        help="Download only a specific page (mutually exclusive with --start-page)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be downloaded without downloading",
    )
    parser.add_argument(
        "--max-depth",
        type=int,
        default=DEFAULT_MAX_MOVE_TREE_DEPTH,
        help=f"Maximum move tree depth (default: {DEFAULT_MAX_MOVE_TREE_DEPTH})",
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
        "--fetch-objective",
        action="store_true",
        help="Fetch puzzle HTML pages and parse objective text for extra YT[] tags (requires curl)",
    )
    parser.add_argument(
        "--match-collections",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Match OGS collection names to YL[] slugs from config/collections.json (default: enabled)",
    )
    parser.add_argument(
        "--collections-jsonl",
        type=Path,
        default=None,
        help="Path to sorted collections JSONL for reverse-index YL[] enrichment "
             "(default: auto-discover in output dir)",
    )
    parser.add_argument(
        "--resolve-intent",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Resolve puzzle_description to objective_id and write as root C[] comment (default: enabled)",
    )
    parser.add_argument(
        "--intent-threshold",
        type=float,
        default=0.8,
        help="Minimum confidence for intent resolution (default: 0.8)",
    )

    args = parser.parse_args()

    # Validate mutually exclusive options
    if args.page and args.start_page:
        parser.error("--page and --start-page are mutually exclusive")

    # Determine output directory
    output_dir = get_output_dir(args.output_dir)

    # Setup structured logging
    logger = setup_logging(
        output_dir=output_dir,
        verbose=args.verbose,
        log_to_file=not args.no_log_file,
    )

    # Log run start
    start_time = time.time()
    logger.run_start(
        max_puzzles=args.max_puzzles,
        resume=args.resume,
        output_dir=to_relative_path(output_dir),
    )

    print(f"\n{'='*60}")
    print("OGS Puzzle Downloader")
    print(f"{'='*60}")
    print(f"Output directory: {to_relative_path(output_dir)}")
    print(f"Max puzzles: {args.max_puzzles}")
    print(f"Batch size: {args.batch_size}")
    print(f"Resume: {args.resume}")
    print(f"Dry run: {args.dry_run}")
    print(f"{'='*60}\n")

    # Build config
    config = DownloadConfig(
        max_puzzles=args.max_puzzles,
        resume=args.resume,
        dry_run=args.dry_run,
        output_dir=output_dir,
        page_delay=args.page_delay,
        puzzle_delay=args.puzzle_delay,
        batch_size=args.batch_size,
        max_move_tree_depth=args.max_depth,
        start_page=args.start_page,
        single_page=args.page,
        fetch_objective=args.fetch_objective,
        match_collections=args.match_collections,
        collections_jsonl_path=args.collections_jsonl,
        resolve_intent=args.resolve_intent,
        intent_confidence_threshold=args.intent_threshold,
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
    print(f"Pages processed: {stats.pages_processed}")
    print(f"Duration: {duration:.1f}s ({duration/60:.1f} minutes)")
    print(f"Output: {to_relative_path(output_dir)}")

    return 0 if stats.errors == 0 else 1


# ---------------------------------------------------------------------------
# embed-collections subcommand
# ---------------------------------------------------------------------------

_DEFAULT_JSONL_GLOB = "external-sources/ogs/*-collections-sorted.jsonl"


def _find_default_jsonl() -> Path | None:
    """Auto-discover the sorted collections JSONL in external-sources/ogs/."""
    matches = sorted(glob.glob(_DEFAULT_JSONL_GLOB))
    return Path(matches[-1]) if matches else None


def embed_collections_cmd() -> int:
    """Embed YL[] into OGS SGF files using manifest-based lookup."""
    parser = argparse.ArgumentParser(
        prog="python -m tools.ogs embed-collections",
        description="Embed YL[slug:chapter/position] into OGS SGF files using JSONL manifest.",
    )
    parser.add_argument(
        "--source-dir",
        type=Path,
        required=True,
        help="Root directory of SGF files to process",
    )
    parser.add_argument(
        "--jsonl",
        type=Path,
        default=None,
        help="Path to sorted collections JSONL (default: auto-discover)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would change without writing",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from last checkpoint",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    parser.add_argument(
        "--no-log-file",
        action="store_true",
        help="Disable file logging (console only)",
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Skip creating .yl-backup files before writing",
    )

    args = parser.parse_args(sys.argv[2:])  # skip "embed-collections"

    # Resolve JSONL path
    jsonl_path = args.jsonl or _find_default_jsonl()
    if jsonl_path is None or not jsonl_path.exists():
        print(f"Error: JSONL manifest not found. Provide --jsonl or place in {_DEFAULT_JSONL_GLOB}")
        return 1

    source_dir: Path = args.source_dir
    if not source_dir.is_dir():
        print(f"Error: source directory not found: {source_dir}")
        return 1

    # Lazy imports to avoid circular / heavy imports for download subcommand
    from tools.core.checkpoint import load_checkpoint
    from tools.core.collection_embedder import (
        EmbedCheckpoint,
        ManifestLookupStrategy,
        embed_collections,
    )
    from tools.core.collection_matcher import CollectionMatcher
    from tools.core.logging import setup_logging as core_setup_logging

    log_dir = Path("external-sources/ogs")
    logger = core_setup_logging(
        log_dir,
        "ogs-embed",
        verbose=args.verbose,
        log_to_file=not args.no_log_file,
        log_suffix="embed-collections",
    )

    matcher = CollectionMatcher()
    strategy = ManifestLookupStrategy(jsonl_path, matcher)

    logger.info(
        f"Manifest: {jsonl_path} ({strategy.index_size} puzzle IDs indexed)"
    )
    logger.info(f"Source: {source_dir}  dry_run={args.dry_run}")

    checkpoint = None
    if args.resume:
        from tools.core.collection_embedder import CHECKPOINT_FILENAME
        checkpoint = load_checkpoint(source_dir, EmbedCheckpoint, CHECKPOINT_FILENAME)

    summary = embed_collections(
        source_dir,
        strategy,
        matcher,
        logger,
        dry_run=args.dry_run,
        backup=not args.no_backup,
        checkpoint=checkpoint,
    )

    print(f"\nEmbedded: {summary.embedded}  Updated: {summary.updated}  "
          f"Already: {summary.already_embedded}  Conflicts: {summary.conflicts}  "
          f"Skipped: {summary.skipped}  Errors: {summary.errors}  "
          f"Coverage: {summary.coverage_pct:.1f}%")

    return 0 if summary.errors == 0 else 1


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "embed-collections":
        sys.exit(embed_collections_cmd())
    sys.exit(main())
