"""
CLI entry point for 101weiqi puzzle downloader.

Usage:
    python -m tools.weiqi101 --help
    python -m tools.weiqi101 daily --start-date 2026-01-01 --end-date 2026-01-31
    python -m tools.weiqi101 puzzle --start-id 1 --end-id 100 --resume
    python -m tools.weiqi101 puzzle --ids 78000,78001,78002
"""

import argparse
import sys
import time
from datetime import date, datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .discover import BookChapterIndex

from .config import (
    DEFAULT_BATCH_SIZE,
    DEFAULT_PUZZLE_DELAY,
    get_output_dir,
)
from tools.core.paths import rel_path as to_relative_path
from .logging_config import setup_logging
from .orchestrator import DownloadConfig, download_puzzles


def _ts() -> str:
    """Return a ``HH:MM:SS`` timestamp prefix for console output."""
    return datetime.now().strftime("%H:%M:%S")


def _parse_date(s: str) -> date:
    """Parse YYYY-MM-DD date string."""
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid date format: '{s}' (expected YYYY-MM-DD)") from None


def _parse_id_list(s: str) -> list[int]:
    """Parse comma-separated puzzle ID list."""
    try:
        return [int(x.strip()) for x in s.split(",") if x.strip()]
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid ID list: '{s}' (expected comma-separated integers)") from None


def _parse_cookies(s: str) -> dict[str, str]:
    """Parse 'Name=Value;Name2=Value2' cookie string into a dict."""
    result: dict[str, str] = {}
    for part in s.split(";"):
        part = part.strip()
        if not part:
            continue
        if "=" not in part:
            raise argparse.ArgumentTypeError(
                f"Invalid cookie '{part}': expected Name=Value format"
            )
        name, _, value = part.partition("=")
        result[name.strip()] = value.strip()
    if not result:
        raise argparse.ArgumentTypeError("--cookies value produced an empty cookie dict")
    return result


def _load_book_from_jsonl(book_id: int, output_dir: Path) -> "BookChapterIndex | None":
    """Try to load a book's chapter index from book-ids.jsonl.

    Returns a BookChapterIndex if the book is found with chapter data,
    or None if the file doesn't exist or the book isn't in it.
    """
    import json

    from .discover import BookChapter, BookChapterIndex

    jsonl_path = output_dir / "book-ids.jsonl"
    if not jsonl_path.exists():
        return None

    with jsonl_path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if int(entry.get("book_id", -1)) != book_id:
                continue
            # Found the book — build BookChapterIndex from the JSONL entry
            chapters_data = entry.get("chapters")
            if not chapters_data:
                return None  # No chapter structure — force network fetch
            chapters = [
                BookChapter(
                    chapter_id=ch.get("chapter_id", 0),
                    chapter_number=ch.get("chapter_number", i + 1),
                    name=ch.get("name", ""),
                    name_en=ch.get("name_en", ""),
                    puzzle_ids=ch.get("puzzle_ids", []),
                )
                for i, ch in enumerate(chapters_data)
            ]
            return BookChapterIndex(
                book_id=book_id,
                chapters=chapters,
                book_name=entry.get("book_name", ""),
                book_name_en=entry.get("book_name_en", ""),
                discovered_at=entry.get("discovered_at", ""),
            )
    return None  # Book not found in JSONL


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Download Go tsumego puzzles from 101weiqi.com",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Download daily puzzles for a date range
    python -m tools.101weiqi daily --start-date 2026-01-01 --end-date 2026-01-31

    # Download specific puzzles by ID
    python -m tools.101weiqi puzzle --ids 78000,78001,78002

    # Download a range of puzzle IDs
    python -m tools.101weiqi puzzle --start-id 1 --end-id 1000

    # Resume interrupted download
    python -m tools.101weiqi puzzle --start-id 1 --end-id 5000 --resume

    # Dry run
    python -m tools.101weiqi daily --start-date 2026-01-01 --end-date 2026-01-01 --dry-run

Output Structure:
    external-sources/101weiqi/
    ├── sgf/
    │   ├── batch-001/
    │   │   ├── 78000.sgf
    │   │   └── ...
    │   └── batch-002/
    ├── logs/
    │   └── 101weiqi-YYYYMMDD_HHMMSS.jsonl
    ├── sgf-index.txt
    └── .checkpoint.json
        """,
    )

    # Common arguments
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Output directory (default: external-sources/101weiqi)",
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
        "--max-puzzles",
        type=int,
        default=10000,
        help="Maximum puzzles to download (default: 10000)",
    )
    # NOTE: --resume and --dry-run are on the subparsers (daily, puzzle),
    # not here, so they can appear after the subcommand name.
    parser.add_argument(
        "--cookies",
        type=str,
        default=None,
        metavar="COOKIE_STRING",
        help=(
            "Session cookies for authenticated access, in 'Name=Value;Name2=Value2' format. "
            "Required if the site shows a login page. "
            "Copy from browser DevTools → Network → request headers → Cookie."
        ),
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

    # Enrichment options
    parser.add_argument(
        "--match-collections",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Enable/disable YL[] collection matching (default: enabled)",
    )
    parser.add_argument(
        "--resolve-intent",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Enable/disable root C[] intent resolution (default: enabled)",
    )

    # Subcommands for source modes
    subparsers = parser.add_subparsers(dest="source_mode", help="Puzzle source mode")

    # Daily mode
    daily_parser = subparsers.add_parser(
        "daily",
        help="Download daily 8 puzzles",
    )
    daily_parser.add_argument(
        "--start-date",
        type=_parse_date,
        required=True,
        metavar="YYYY-MM-DD",
        help="Start date (inclusive)",
    )
    daily_parser.add_argument(
        "--end-date",
        type=_parse_date,
        required=True,
        metavar="YYYY-MM-DD",
        help="End date (inclusive)",
    )
    daily_parser.add_argument(
        "--resume",
        action="store_true",
        default=False,
        help="Resume from last checkpoint",
    )
    daily_parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Show what would be downloaded without downloading",
    )

    # Puzzle-by-ID mode
    puzzle_parser = subparsers.add_parser(
        "puzzle",
        help="Download puzzles by numeric ID",
    )
    puzzle_parser.add_argument(
        "--start-id",
        type=int,
        help="Start ID (inclusive) for range mode",
    )
    puzzle_parser.add_argument(
        "--end-id",
        type=int,
        help="End ID (inclusive) for range mode",
    )
    puzzle_parser.add_argument(
        "--ids",
        type=_parse_id_list,
        metavar="ID1,ID2,...",
        help="Comma-separated list of specific puzzle IDs",
    )
    puzzle_parser.add_argument(
        "--book-id",
        type=int,
        metavar="BOOK_ID",
        help="Download all puzzles from a specific book (fetches IDs automatically)",
    )
    puzzle_parser.add_argument(
        "--collection-slug",
        type=str,
        metavar="SLUG",
        help="Collection slug for --book-id mode (emits YL[slug:CHAPTER/POSITION])",
    )
    puzzle_parser.add_argument(
        "--resume",
        action="store_true",
        default=False,
        help="Resume from last checkpoint",
    )
    puzzle_parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Show what would be downloaded without downloading",
    )

    # Scan-tags utility
    subparsers.add_parser(
        "scan-tags",
        help="Show tag mapping coverage (Chinese → YenGo)",
    )

    # Scan-collections utility
    subparsers.add_parser(
        "scan-collections",
        help="Show collection mapping coverage (Chinese → YenGo slug)",
    )

    # Discover-books utility
    discover_parser = subparsers.add_parser(
        "discover-books",
        help="BFS discovery of books, tags, and categories from the website",
    )
    discover_parser.add_argument(
        "--output",
        type=Path,
        default=None,
        metavar="PATH",
        help=(
            "Save discovery catalog to JSON file "
            "(default: external-sources/101weiqi/discovery-catalog.json)"
        ),
    )
    discover_parser.add_argument(
        "--tag-id",
        type=int,
        default=None,
        metavar="ID",
        help="Discover books from a single tag ID only (e.g., 42 for 诘棋120系列)",
    )
    discover_parser.add_argument(
        "--delay",
        type=float,
        default=3.0,
        help="Polite delay between requests in seconds (default: 3.0)",
    )

    # Browser capture: receive mode
    receive_parser = subparsers.add_parser(
        "receive",
        help="Start HTTP receiver for browser-captured puzzle data",
    )
    receive_parser.add_argument(
        "--host",
        type=str,
        default=None,
        help="Bind host (default: 127.0.0.1)",
    )
    receive_parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Bind port (default: 8101)",
    )
    receive_parser.add_argument(
        "--book-id",
        type=int,
        default=None,
        metavar="BOOK_ID",
        help="Pre-load a book's puzzle IDs into the queue at startup",
    )

    # Browser capture: import-jsonl mode
    import_jsonl_parser = subparsers.add_parser(
        "import-jsonl",
        help="Import puzzles from a JSONL file of captured qqdata records",
    )
    import_jsonl_parser.add_argument(
        "jsonl_file",
        type=Path,
        metavar="JSONL_FILE",
        help="Path to a JSONL file (one JSON object per line with 'qqdata' key)",
    )

    # Discover-categories utility
    discover_cat_parser = subparsers.add_parser(
        "discover-categories",
        help="Probe puzzle category pages for pagination counts",
    )
    discover_cat_parser.add_argument(
        "--delay",
        type=float,
        default=3.0,
        help="Polite delay between requests in seconds (default: 3.0)",
    )

    # Discover-book-ids utility
    disc_ids_parser = subparsers.add_parser(
        "discover-book-ids",
        help="Discover puzzle IDs within one or more books (CLI-only legacy levelorder scraper)",
    )

    # Rebuild books-catalog.jsonl from inputs (idempotent, safe to run anytime)
    subparsers.add_parser(
        "rebuild-catalog",
        help="Rebuild books-catalog.jsonl from book-ids.jsonl + discovery-catalog.json + book-reviews.jsonl",
    )

    # Validate that books-catalog.jsonl matches what would be regenerated
    # from current inputs (catches drift if anyone bypassed the rebuild rule).
    subparsers.add_parser(
        "validate-catalog",
        help="Verify books-catalog.jsonl is up-to-date with its inputs (exit 1 on drift)",
    )

    # Backfill-yl utility
    backfill_parser = subparsers.add_parser(
        "backfill-yl",
        help="Backfill YL[] in qday SGFs from telemetry logs (books only)",
    )
    backfill_parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Show what would change without modifying files",
    )

    # Backfill-annotations utility
    backfill_ann_parser = subparsers.add_parser(
        "backfill-annotations",
        help="Fix solution tree annotations (TE[1]/BM[1] on first moves, strip from continuations)",
    )
    backfill_ann_parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Show what would change without modifying files",
    )

    # Backfill-capture-log utility
    backfill_caplog_parser = subparsers.add_parser(
        "backfill-capture-log",
        help="Rebuild capture-log.jsonl for books from existing SGF filenames",
    )
    backfill_caplog_parser.add_argument(
        "--book-id",
        type=int,
        default=None,
        metavar="BOOK_ID",
        help="Single book ID to backfill (default: all books)",
    )
    backfill_caplog_parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Show what would be written without modifying files",
    )
    # Enrich-capture-log utility (retrospective: add sgf_hash to existing entries)
    enrich_caplog_parser = subparsers.add_parser(
        "enrich-capture-log",
        help=(
            "Add sgf_hash (normalized SGF SHA256[:16]) to existing capture-log "
            "entries that lack it. Read-only on SGF files."
        ),
    )
    enrich_caplog_parser.add_argument(
        "--book-id",
        type=int,
        default=None,
        metavar="BOOK_ID",
        help="Single book ID to enrich (default: all books)",
    )
    enrich_caplog_parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Show what would change without modifying files",
    )

    # Inventory utility (corpus dedup view).
    inv_parser = subparsers.add_parser(
        "inventory",
        help=(
            "Show or refresh the 101weiqi corpus inventory "
            "(unique pids + per-book overlap, no pid lists)"
        ),
    )
    inv_parser.add_argument(
        "--refresh",
        action="store_true",
        default=False,
        help="Rescan the corpus and rewrite inventory.json + unique-sgf.txt",
    )
    inv_parser.add_argument(
        "--json",
        action="store_true",
        default=False,
        help="Print inventory.json to stdout instead of a human summary",
    )
    # Reconcile-books utility
    reconcile_parser = subparsers.add_parser(
        "reconcile-books",
        help="Reconcile per-book book.json with actual SGF files on disk",
    )
    reconcile_parser.add_argument(
        "--book-id",
        type=int,
        default=None,
        metavar="BOOK_ID",
        help="Single book ID to reconcile (default: all books)",
    )
    reconcile_parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Show what would change without modifying files",
    )

    # Manual chapter skip (Option 3 / schema v5)
    skip_chapter_parser = subparsers.add_parser(
        "skip-chapter",
        help=(
            "Mark a chapter as permanently skipped in book.json so the "
            "userscript stops re-visiting it. Useful when the site has "
            "broken/deleted chapters."
        ),
    )
    skip_chapter_parser.add_argument(
        "--book-id", type=int, required=True, metavar="BOOK_ID",
    )
    chapter_target = skip_chapter_parser.add_mutually_exclusive_group(
        required=True,
    )
    chapter_target.add_argument(
        "--chapter", type=int, metavar="CHAPTER_NUMBER",
        help="1-based chapter number (as it appears in book.json)",
    )
    chapter_target.add_argument(
        "--chapter-id", type=int, metavar="CHAPTER_ID",
        help="Internal chapter_id (101weiqi-side identifier)",
    )
    skip_chapter_parser.add_argument(
        "--reason", type=str, default=None,
        help="Freeform reason recorded with the skip flag",
    )

    unskip_chapter_parser = subparsers.add_parser(
        "unskip-chapter",
        help="Clear a chapter's skip flag and reset its empty-attempt counter.",
    )
    unskip_chapter_parser.add_argument(
        "--book-id", type=int, required=True, metavar="BOOK_ID",
    )
    unskip_target = unskip_chapter_parser.add_mutually_exclusive_group(
        required=True,
    )
    unskip_target.add_argument(
        "--chapter", type=int, metavar="CHAPTER_NUMBER",
    )
    unskip_target.add_argument(
        "--chapter-id", type=int, metavar="CHAPTER_ID",
    )

    disc_ids_parser.add_argument(
        "--book-id",
        type=int,
        metavar="BOOK_ID",
        help="Single book ID to scrape",
    )
    disc_ids_parser.add_argument(
        "--book-ids",
        type=_parse_id_list,
        metavar="ID1,ID2,...",
        help="Comma-separated list of book IDs to scrape",
    )
    disc_ids_parser.add_argument(
        "--tag-id",
        type=int,
        metavar="TAG_ID",
        help="Scrape all books belonging to a tag (reads discovery-catalog.json)",
    )
    disc_ids_parser.add_argument(
        "--output",
        type=Path,
        default=None,
        metavar="FILE",
        help=(
            "Path to save/merge JSONL output "
            "(default: external-sources/101weiqi/book-ids.jsonl)"
        ),
    )
    disc_ids_parser.add_argument(
        "--delay",
        type=float,
        default=3.0,
        help="Polite delay between requests in seconds (default: 3.0)",
    )
    disc_ids_parser.add_argument(
        "--by-chapter",
        action="store_true",
        default=False,
        help="Use chapter-aware discovery (preserves chapter structure in JSONL)",
    )

    args = parser.parse_args()

    if not args.source_mode:
        parser.print_help()
        return 0

    # Handle scan utilities (no download, just print mapping info)
    if args.source_mode == "scan-tags":
        return _run_scan_tags()
    if args.source_mode == "scan-collections":
        return _run_scan_collections()
    if args.source_mode == "discover-books":
        return _run_discover_books(args)
    if args.source_mode == "discover-categories":
        return _run_discover_categories(args)
    if args.source_mode == "discover-book-ids":
        return _run_discover_book_ids(args)
    if args.source_mode == "rebuild-catalog":
        return _run_rebuild_catalog(args)
    if args.source_mode == "validate-catalog":
        return _run_validate_catalog(args)
    if args.source_mode == "backfill-yl":
        return _run_backfill_yl(args)
    if args.source_mode == "backfill-annotations":
        return _run_backfill_annotations(args)
    if args.source_mode == "backfill-capture-log":
        return _run_backfill_capture_log(args)
    if args.source_mode == "enrich-capture-log":
        return _run_enrich_capture_log(args)
    if args.source_mode == "reconcile-books":
        return _run_reconcile_books(args)
    if args.source_mode == "inventory":
        return _run_inventory(args)
    if args.source_mode == "skip-chapter":
        return _run_skip_chapter(args)
    if args.source_mode == "unskip-chapter":
        return _run_unskip_chapter(args)
    if args.source_mode == "receive":
        return _run_receive(args)
    if args.source_mode == "import-jsonl":
        return _run_import_jsonl(args)

    # If downloading a book without an explicit output-dir, default to a
    # book-specific subdirectory so each book's SGFs stay isolated.
    if (
        args.source_mode == "puzzle"
        and getattr(args, "book_id", None) is not None
        and args.output_dir is None
    ):
        from .config import DEFAULT_OUTPUT_DIR
        args.output_dir = Path(DEFAULT_OUTPUT_DIR) / "books" / f"book-{args.book_id}"

    # Determine output directory
    output_dir = get_output_dir(args.output_dir)

    # Setup structured logging
    logger = setup_logging(
        output_dir=output_dir,
        verbose=args.verbose,
        log_to_file=not args.no_log_file,
    )

    # Print banner
    start_time = time.time()
    print(f"\n{'=' * 60}")
    print("101weiqi Puzzle Downloader")
    print(f"{'=' * 60}")
    print(f"Source mode: {args.source_mode}")
    print(f"Output directory: {to_relative_path(output_dir)}")
    print(f"Max puzzles: {args.max_puzzles}")
    print(f"Batch size: {args.batch_size}")
    print(f"Resume: {args.resume}")
    print(f"Dry run: {args.dry_run}")
    if args.source_mode == "daily":
        print(f"Date range: {args.start_date} → {args.end_date}")
    elif args.source_mode == "puzzle":
        if args.ids:
            print(f"Puzzle IDs: {args.ids}")
        elif getattr(args, "book_id", None) is not None:
            print(f"Book ID: {args.book_id} (will fetch puzzle IDs automatically)")
        else:
            print(f"ID range: {args.start_id} → {args.end_id}")
    print(f"{'=' * 60}\n")

    # Build config
    cookies = _parse_cookies(args.cookies) if args.cookies else None
    config = DownloadConfig(
        source_mode=args.source_mode,
        output_dir=output_dir,
        batch_size=args.batch_size,
        puzzle_delay=args.puzzle_delay,
        max_puzzles=args.max_puzzles,
        resume=args.resume,
        dry_run=args.dry_run,
        match_collections=args.match_collections,
        resolve_intent=args.resolve_intent,
        cookies=cookies,
    )

    if args.source_mode == "daily":
        config.start_date = args.start_date
        config.end_date = args.end_date
    elif args.source_mode == "puzzle":
        config.puzzle_ids = getattr(args, "ids", None)
        config.start_id = getattr(args, "start_id", None)
        config.end_id = getattr(args, "end_id", None)

        # Resolve puzzle IDs for --book-id mode (chapter-aware).
        # Prefer offline lookup from book-ids.jsonl (populated by discover-book-ids).
        # Fall back to live website scrape only if the book is not in the JSONL.
        book_id = getattr(args, "book_id", None)
        if book_id is not None:

            # book-ids.jsonl lives in the base output dir (external-sources/101weiqi/),
            # not the book-specific subdir (external-sources/101weiqi/books/book-N/).
            base_output_dir = get_output_dir(None)
            chapter_index = _load_book_from_jsonl(book_id, base_output_dir)
            if chapter_index is not None:
                logger.info(
                    f"Loaded book {book_id} from book-ids.jsonl "
                    f"({len(chapter_index.chapters)} chapters, "
                    f"{sum(len(c.puzzle_ids) for c in chapter_index.chapters)} puzzles)"
                )
                print(f"Loaded book {book_id} from book-ids.jsonl (offline)")
            else:
                from .client import WeiQiClient
                from .discover import fetch_book_puzzle_ids_by_chapter
                logger.info(f"Book {book_id} not in book-ids.jsonl, fetching from website...")
                print(
                    f"Book {book_id} not in book-ids.jsonl — fetching from website...\n"
                    f"  Tip: run 'discover-book-ids --book-id {book_id} --by-chapter' first for offline use."
                )
                with WeiQiClient(cookies=cookies) as client:
                    chapter_index = fetch_book_puzzle_ids_by_chapter(
                        book_id, client, args.puzzle_delay
                    )

            all_ids = chapter_index.all_puzzle_ids()
            if not all_ids:
                print(f"Error: no puzzle IDs found for book {book_id}")
                return 1
            config.puzzle_ids = all_ids

            # Build puzzle_id → (chapter_str, position) lookup for YL enrichment
            chapter_sequences: dict[int, tuple[str, int]] = {}
            for ch in chapter_index.chapters:
                ch_str = str(ch.chapter_number)
                for pos, pid in enumerate(ch.puzzle_ids, start=1):
                    chapter_sequences[pid] = (ch_str, pos)
            config.chapter_sequences = chapter_sequences
            config.book_collection_slug = getattr(args, "collection_slug", None)
            print(
                f"Book {book_id}: {len(all_ids)} puzzle IDs across "
                f"{len(chapter_index.chapters)} chapters"
            )

    # Validate puzzle mode args
    if args.source_mode == "puzzle" and not config.puzzle_ids:
        if config.start_id is None or config.end_id is None:
            print("Error: puzzle mode requires --ids, --book-id, or --start-id/--end-id")
            return 1

    # Run download
    stats = download_puzzles(config)

    # Print summary
    duration = time.time() - start_time
    print(f"\n{'=' * 60}")
    print("Download Summary")
    print(f"{'=' * 60}")
    print(f"Downloaded: {stats.downloaded}")
    print(f"Skipped: {stats.skipped}")
    print(f"Not found: {stats.not_found}")
    print(f"Errors: {stats.errors}")
    print(f"Duration: {duration:.1f}s ({duration / 60:.1f} minutes)")
    print(f"Output: {to_relative_path(output_dir)}")

    return 0 if stats.errors == 0 else 1


def _run_scan_tags() -> int:
    """Print tag mapping coverage."""
    from .tags import TAG_MAPPING

    print(f"\n{'=' * 50}")
    print("101weiqi Tag Mapping (Chinese → YenGo)")
    print(f"{'=' * 50}")
    for chinese, yengo_tag in sorted(TAG_MAPPING.items()):
        print(f"  {chinese:8s} → {yengo_tag}")
    print(f"\nTotal mappings: {len(TAG_MAPPING)}")
    return 0


def _run_scan_collections() -> int:
    """Print collection mapping coverage."""
    from ._local_collections_mapping import _load_mappings

    mappings = _load_mappings()
    print(f"\n{'=' * 50}")
    print("101weiqi Collection Mapping (Chinese → YenGo slug)")
    print(f"{'=' * 50}")
    for chinese, slug in sorted(mappings.items()):
        print(f"  {chinese:8s} → {slug}")
    print(f"\nTotal mappings: {len(mappings)}")
    return 0


def _run_discover_books(args: argparse.Namespace) -> int:
    """Run BFS book discovery."""
    from .client import WeiQiClient
    from .config import get_output_dir
    from .discover import (
        discover_books_by_tag,
        run_full_discovery,
    )

    output_dir = get_output_dir()
    setup_logging(
        output_dir=output_dir,
        verbose=getattr(args, "verbose", False),
        log_to_file=not getattr(args, "no_log_file", False),
    )

    if args.tag_id is not None:
        # Single tag mode
        with WeiQiClient() as client:
            books = discover_books_by_tag(client, args.tag_id, args.delay)
        print(f"\nBooks under tag {args.tag_id}:")
        for b in books:
            print(f"  [{b.book_id:6d}] {b.name} — {b.puzzle_count} puzzles, {b.difficulty}")
        print(f"\nTotal: {len(books)} books")
        return 0

    # Resolve output path — default to canonical location
    output_path: Path = (
        args.output
        if args.output is not None
        else output_dir / "discovery-catalog.json"
    )

    # Back up existing file with a timestamp before overwriting
    if output_path.exists():
        from datetime import datetime
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = output_path.with_suffix(f".{ts}.json")
        output_path.rename(backup)
        print(f"Backed up existing catalog \u2192 {backup.name}")

    # Full discovery
    catalog = run_full_discovery(
        output_path=output_path,
        delay=args.delay,
    )
    # Rebuild derived books-catalog.jsonl so /books and downstream
    # consumers see fresh metadata. Pure function — safe to call after
    # any write to discovery-catalog.json.
    from . import catalog as catalog_mod
    catalog_mod.rebuild_books_catalog(output_dir)
    return 0 if catalog.books or catalog.book_tags else 1


def _run_discover_categories(args: argparse.Namespace) -> int:
    """Run category page discovery."""
    from .client import WeiQiClient
    from .config import get_output_dir
    from .discover import discover_category_pages

    setup_logging(
        output_dir=get_output_dir(),
        verbose=getattr(args, "verbose", False),
        log_to_file=not getattr(args, "no_log_file", False),
    )

    with WeiQiClient() as client:
        categories = discover_category_pages(client, args.delay)

    print("\nCategory Page Analysis:")
    print(f"{'=' * 50}")
    for cat in categories:
        est = cat.page_count * 20
        print(f"  {cat.chinese_name:4s} ({cat.slug:10s}): {cat.page_count:4d} pages (~{est:,} puzzles)")
    return 0


def _run_discover_book_ids(args: argparse.Namespace) -> int:
    """Discover puzzle IDs within one or more books (CLI-only legacy scraper).

    Note: This is the standalone discover CLI — used for ad-hoc enumeration
    only. The browser capture flow does NOT use this and instead uses
    chapter-based discovery via the userscript.

    Output format: JSONL — one JSON record per book, appended/merged into
    ``external-sources/101weiqi/book-ids.jsonl`` (or the path given by --output).
    Subsequent runs merge new results with existing entries; same book_id is
    overwritten with fresher data.
    """
    import json

    from .client import WeiQiClient
    from .config import get_output_dir
    from .discover import fetch_book_puzzle_ids, fetch_book_puzzle_ids_by_chapter
    by_chapter = getattr(args, "by_chapter", False)
    output_dir = get_output_dir()
    setup_logging(
        output_dir=output_dir,
        verbose=getattr(args, "verbose", False),
        log_to_file=not getattr(args, "no_log_file", False),
    )
    # Resolve the list of book IDs to process
    book_ids: list[int] = []
    if getattr(args, "book_id", None) is not None:
        book_ids.append(args.book_id)
    for bid in getattr(args, "book_ids", None) or []:
        if bid not in book_ids:
            book_ids.append(bid)

    if getattr(args, "tag_id", None) is not None:
        catalog_path = get_output_dir() / "discovery-catalog.json"
        if not catalog_path.exists():
            print(f"Error: catalog not found at {catalog_path}. Run 'discover-books' first.")
            return 1
        with catalog_path.open(encoding="utf-8") as f:
            catalog = json.load(f)
        tag_name = None
        for tag in catalog.get("book_tags", []):
            if tag.get("tag_id") == args.tag_id:
                tag_name = tag.get("name")
                break
        if not tag_name:
            print(f"Error: tag_id {args.tag_id} not found in catalog")
            return 1
        for book in catalog.get("books", []):
            if tag_name in (book.get("tags") or []):
                bid = book.get("book_id")
                if bid and bid not in book_ids:
                    book_ids.append(bid)
        print(f"{_ts()} Tag {args.tag_id} ('{tag_name}'): {len(book_ids)} books to scrape")

    if not book_ids:
        print("Error: provide --book-id, --book-ids, or --tag-id")
        return 1

    # Resolve output path — default to canonical book-ids.jsonl in output dir
    output_path: Path = getattr(args, "output", None) or (output_dir / "book-ids.jsonl")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Load existing entries so we can merge (same book_id = fresher data wins)
    existing: dict[int, dict] = {}
    if output_path.exists():
        with output_path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    existing[int(entry["book_id"])] = entry
                except (json.JSONDecodeError, KeyError, ValueError):
                    pass
        print(f"{_ts()} Loaded {len(existing)} existing entries from {output_path}")

    # Scrape and merge — write incrementally after each book so no progress
    # is lost on crash.
    # Canonical priority order (best-first). Unknown values sort last.
    _PRIORITY_ORDER = {
        "editorial": 0,
        "premier": 1,
        "curated": 2,
        "community": 3,
        "skip": 4,
        "unrated": 5,
    }

    def _entry_puzzle_count(entry: dict) -> int:
        if "chapters" in entry:
            return sum(len(ch.get("puzzle_ids", [])) for ch in entry["chapters"])
        return len(entry.get("puzzle_ids") or [])

    def _sort_key(entry: dict):
        return (
            _PRIORITY_ORDER.get(entry.get("priority") or "unrated", 99),
            -_entry_puzzle_count(entry),  # larger first within tier
            int(entry.get("book_id", 0)),
        )

    def _flush_jsonl() -> None:
        with output_path.open("w", encoding="utf-8") as f:
            for entry in sorted(existing.values(), key=_sort_key):
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    with WeiQiClient() as client:
        for i, book_id in enumerate(book_ids):
            if by_chapter:
                ch_index = fetch_book_puzzle_ids_by_chapter(book_id, client, args.delay)
                entry = ch_index.to_dict()
                total_ids = sum(len(ch.puzzle_ids) for ch in ch_index.chapters)
                print(
                    f"{_ts()}   [{i + 1}/{len(book_ids)}] Book {book_id:>6}: "
                    f"{total_ids:>5} puzzle IDs in {len(ch_index.chapters)} chapters"
                )
            else:
                index = fetch_book_puzzle_ids(book_id, client, args.delay)
                entry = index.to_dict()
                meta_parts = []
                if entry.get("view_count"):
                    meta_parts.append(f"views={entry['view_count']:,}")
                if entry.get("like_count"):
                    meta_parts.append(f"likes={entry['like_count']}")
                if entry.get("finish_count"):
                    meta_parts.append(f"finishes={entry['finish_count']}")
                meta_str = f"  [{', '.join(meta_parts)}]" if meta_parts else ""
                print(
                    f"{_ts()}   [{i + 1}/{len(book_ids)}] Book {book_id:>6}: "
                    f"{len(index.puzzle_ids):>5} puzzle IDs{meta_str}"
                )
            # Preserve manually-curated fields from prior runs (e.g. priority,
            # which is set externally via book-reviews / hand edits and is not
            # re-discovered from the website).
            prior = existing.get(book_id)
            if prior:
                prior_priority = prior.get("priority")
                if prior_priority and prior_priority != "unrated":
                    entry["priority"] = prior_priority
            existing[book_id] = entry
            _flush_jsonl()  # <-- incremental save after every book
            if i < len(book_ids) - 1:
                time.sleep(args.delay)

    def _count_ids(entry: dict) -> int:
        if "chapters" in entry:
            return sum(len(ch.get("puzzle_ids", [])) for ch in entry["chapters"])
        return len(entry.get("puzzle_ids") or [])

    total_ids = sum(_count_ids(e) for e in existing.values())
    print(f"\n{_ts()} Saved {len(existing)} books ({total_ids:,} puzzle IDs total) → {output_path}")
    # Rebuild derived books-catalog.jsonl so /books reflects the new
    # puzzle_count / chapter changes immediately.
    from . import catalog as catalog_mod
    catalog_mod.rebuild_books_catalog(output_dir)
    return 0


def _run_rebuild_catalog(args: argparse.Namespace) -> int:
    """Rebuild books-catalog.jsonl from inputs."""
    from . import catalog as catalog_mod
    from .config import get_output_dir

    output_dir = get_output_dir()
    n = catalog_mod.rebuild_books_catalog(output_dir)
    print(f"{_ts()} Wrote {catalog_mod.CATALOG_FILE} with {n} entries")
    return 0


def _run_validate_catalog(args: argparse.Namespace) -> int:
    """Verify on-disk catalog matches what rebuild would produce."""
    import shutil
    import tempfile

    from . import catalog as catalog_mod
    from .config import get_output_dir

    output_dir = get_output_dir()
    on_disk = output_dir / catalog_mod.CATALOG_FILE
    if not on_disk.exists():
        print(f"Error: {on_disk} does not exist. Run 'rebuild-catalog' first.")
        return 1

    with tempfile.TemporaryDirectory() as td:
        tmp_dir = Path(td)
        # Copy inputs into temp dir, rebuild there, diff bytes
        for fname in (
            catalog_mod.BOOK_IDS_FILE,
            catalog_mod.DISCOVERY_CATALOG_FILE,
            catalog_mod.REVIEWS_FILE,
        ):
            src = output_dir / fname
            if src.exists():
                shutil.copy2(src, tmp_dir / fname)
        catalog_mod.rebuild_books_catalog(tmp_dir)
        expected = (tmp_dir / catalog_mod.CATALOG_FILE).read_bytes()
        actual = on_disk.read_bytes()

    if expected == actual:
        print(f"{_ts()} OK — {catalog_mod.CATALOG_FILE} is up-to-date")
        return 0
    print(
        f"{_ts()} DRIFT — {catalog_mod.CATALOG_FILE} differs from a fresh "
        f"rebuild. Run 'rebuild-catalog'."
    )
    return 1


def _run_backfill_yl(args: argparse.Namespace) -> int:
    """Backfill YL[] in qday SGFs from telemetry logs."""
    from .backfill import backfill_yl
    from .config import get_output_dir

    output_dir = get_output_dir(getattr(args, "output_dir", None))
    setup_logging(
        output_dir=output_dir,
        verbose=getattr(args, "verbose", False),
        log_to_file=not getattr(args, "no_log_file", False),
    )

    qday_dir = output_dir / "qday"
    log_dir = output_dir / "logs"

    if not qday_dir.exists():
        print(f"Error: qday directory not found: {qday_dir}")
        return 1
    if not log_dir.exists():
        print(f"Error: logs directory not found: {log_dir}")
        return 1

    dry_run = getattr(args, "dry_run", False)
    if dry_run:
        print("DRY RUN — no files will be modified\n")

    stats = backfill_yl(qday_dir=qday_dir, log_dir=log_dir, dry_run=dry_run)

    print(f"\n{'=' * 50}")
    print("Backfill Summary")
    print(f"{'=' * 50}")
    print(f"Total SGFs:  {stats['total']}")
    print(f"Updated:     {stats['updated']} (book slugs written)")
    print(f"Removed:     {stats['removed']} (YL stripped)")
    print(f"Unchanged:   {stats['unchanged']}")
    print(f"Errors:      {stats['errors']}")
    if dry_run:
        print("\n(dry run — no files were modified)")
    return 0 if stats["errors"] == 0 else 1


def _run_backfill_annotations(args: argparse.Namespace) -> int:
    """Fix solution tree annotations in existing SGFs."""
    from .backfill import backfill_annotations
    from .config import get_output_dir

    output_dir = get_output_dir(getattr(args, "output_dir", None))
    setup_logging(
        output_dir=output_dir,
        verbose=getattr(args, "verbose", False),
        log_to_file=not getattr(args, "no_log_file", False),
    )

    # Scan both qday and batch SGF directories
    sgf_dirs = [
        output_dir / "qday",
        output_dir / "sgf",
    ]
    # Also include book subdirectories
    books_dir = output_dir / "books"
    if books_dir.exists():
        for book_dir in sorted(books_dir.iterdir()):
            sgf_subdir = book_dir / "sgf"
            if sgf_subdir.exists():
                sgf_dirs.append(sgf_subdir)

    existing_dirs = [d for d in sgf_dirs if d.exists()]
    if not existing_dirs:
        print("Error: no SGF directories found")
        return 1

    dry_run = getattr(args, "dry_run", False)
    if dry_run:
        print("DRY RUN — no files will be modified\n")

    print(f"Scanning {len(existing_dirs)} directories...")
    for d in existing_dirs:
        print(f"  {d}")

    stats = backfill_annotations(sgf_dirs=existing_dirs, dry_run=dry_run)

    print(f"\n{'=' * 50}")
    print("Annotation Backfill Summary")
    print(f"{'=' * 50}")
    print(f"Total SGFs:  {stats['total']}")
    print(f"Fixed:       {stats['fixed']}")
    print(f"Unchanged:   {stats['unchanged']}")
    print(f"Errors:      {stats['errors']}")
    if dry_run:
        print("\n(dry run — no files were modified)")
    return 0 if stats["errors"] == 0 else 1


def _run_backfill_capture_log(args: argparse.Namespace) -> int:
    """Rebuild capture-log.jsonl for books from existing SGF filenames.

    Scans each book's sgf/ directory, parses filenames to extract puzzle metadata,
    and writes entries to capture-log.jsonl for any SGFs not already logged.
    """
    import json
    import re
    from datetime import datetime, timezone

    from .config import get_output_dir

    output_dir = get_output_dir(getattr(args, "output_dir", None))
    books_dir = output_dir / "books"
    dry_run = getattr(args, "dry_run", False)
    target_book_id = getattr(args, "book_id", None)

    if not books_dir.exists():
        print("Error: no books/ directory found")
        return 1

    if dry_run:
        print("DRY RUN — no files will be modified\n")

    total_added = 0
    total_books = 0

    for book_dir in sorted(books_dir.iterdir()):
        if not book_dir.is_dir():
            continue
        sgf_dir = book_dir / "sgf"
        if not sgf_dir.exists():
            continue

        # Extract book_id from directory name (e.g. "5121-叶老师围棋入门班")
        dir_book_id_match = re.match(r"^(\d+)-", book_dir.name)
        if not dir_book_id_match:
            continue
        book_id = int(dir_book_id_match.group(1))

        if target_book_id is not None and book_id != target_book_id:
            continue

        total_books += 1
        log_path = book_dir / "capture-log.jsonl"

        # Read existing log entries to find already-logged puzzle IDs
        existing_puzzle_ids: set[int] = set()
        existing_entries: list[dict] = []
        if log_path.exists():
            for line in log_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    existing_puzzle_ids.add(int(entry["puzzle_id"]))
                    existing_entries.append(entry)
                except (json.JSONDecodeError, KeyError, ValueError):
                    continue

        # Scan SGF filenames: {pos}_{label}_{chpos}_{puzzle_id}.sgf
        new_entries: list[dict] = []
        for f in sorted(sgf_dir.iterdir()):
            if f.suffix != ".sgf":
                continue
            # Parse filename: 0405_死活-3目4目5目6目_405_8537.sgf
            parts = f.stem.split("_", 2)  # split into [pos, ...rest]
            if len(parts) < 3:
                continue
            # Last segment after final underscore is puzzle_id
            last_parts = f.stem.rsplit("_", 1)
            if len(last_parts) != 2:
                continue
            try:
                puzzle_id = int(last_parts[1])
            except ValueError:
                continue
            if puzzle_id in existing_puzzle_ids:
                continue

            # Extract global position from first segment
            try:
                global_pos = int(parts[0])
            except ValueError:
                global_pos = 0

            # Middle part is chapter label, second-to-last is chapter position
            middle = f.stem[len(parts[0]) + 1 : f.stem.rfind("_")]
            # Middle: "死活-3目4目5目6目_405" → split on last _
            mid_parts = middle.rsplit("_", 1)
            chapter_name = mid_parts[0] if mid_parts else ""
            try:
                chapter_pos = int(mid_parts[1]) if len(mid_parts) > 1 else 0
            except ValueError:
                chapter_pos = 0

            # Use file modification time as captured_at (best available)
            mtime = f.stat().st_mtime
            captured_at = datetime.fromtimestamp(mtime, tz=timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )

            new_entries.append({
                "puzzle_id": puzzle_id,
                "global_position": global_pos,
                "chapter_name": chapter_name,
                "chapter_position": chapter_pos,
                "file": f.name,
                "captured_at": captured_at,
                "backfilled": True,
            })

        if not new_entries:
            print(f"  {book_dir.name}: {len(existing_entries)} logged, 0 new — already complete")
            continue

        print(
            f"  {book_dir.name}: {len(existing_entries)} logged, "
            f"{len(new_entries)} to backfill"
        )
        total_added += len(new_entries)

        if not dry_run:
            # Merge existing + new, sort all by global_position for human readability
            all_entries = existing_entries + new_entries
            all_entries.sort(key=lambda e: e.get("global_position", 0))
            with open(log_path, "w", encoding="utf-8") as f:
                for entry in all_entries:
                    f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    print(f"\n{'=' * 50}")
    print("Capture Log Backfill Summary")
    print(f"{'=' * 50}")
    print(f"Books scanned: {total_books}")
    print(f"Entries added: {total_added}")
    if dry_run:
        print("\n(dry run — no files were modified)")
    return 0


def _run_enrich_capture_log(args: argparse.Namespace) -> int:
    """Add sgf_hash to existing capture-log entries (retrospective)."""
    import json
    import re as _re

    from .config import get_output_dir
    from .sgf_identity import normalized_sgf_hash

    output_dir = get_output_dir(getattr(args, "output_dir", None))
    books_dir = output_dir / "books"
    dry_run = getattr(args, "dry_run", False)
    target_book_id = getattr(args, "book_id", None)

    if not books_dir.exists():
        print("Error: no books/ directory found")
        return 1

    if dry_run:
        print("DRY RUN — no files will be modified\n")

    total_books = 0
    total_enriched = 0
    total_skipped_no_file = 0
    collision_pids: dict[int, set[str]] = {}

    for book_dir in sorted(books_dir.iterdir()):
        if not book_dir.is_dir():
            continue
        m = _re.match(r"^(\d+)-", book_dir.name)
        book_id = int(m.group(1)) if m else None
        if target_book_id is not None and book_id != target_book_id:
            continue
        log_path = book_dir / "capture-log.jsonl"
        sgf_dir = book_dir / "sgf"
        if not log_path.exists() or not sgf_dir.exists():
            continue

        total_books += 1
        lines = log_path.read_text(encoding="utf-8").splitlines()
        out_lines: list[str] = []
        enriched_here = 0
        missing_here = 0

        for raw in lines:
            raw = raw.strip()
            if not raw:
                continue
            try:
                entry = json.loads(raw)
            except json.JSONDecodeError:
                out_lines.append(raw)
                continue

            # Enrich any captured-puzzle row that lacks sgf_hash. Older
            # capture-logs predate event_type, so accept rows that either
            # explicitly mark puzzle_captured OR simply carry puzzle_id + file.
            if entry.get("sgf_hash"):
                out_lines.append(json.dumps(entry, ensure_ascii=False))
                continue
            event_type = entry.get("event_type")
            looks_capture = (
                event_type == "puzzle_captured"
                or (event_type is None and entry.get("puzzle_id") and entry.get("file"))
            )
            if not looks_capture:
                out_lines.append(json.dumps(entry, ensure_ascii=False))
                continue

            fname = entry.get("file")
            sgf_path = sgf_dir / fname if fname else None
            if not sgf_path or not sgf_path.exists():
                missing_here += 1
                out_lines.append(json.dumps(entry, ensure_ascii=False))
                continue

            try:
                h = normalized_sgf_hash(sgf_path.read_text(encoding="utf-8"))
            except OSError:
                missing_here += 1
                out_lines.append(json.dumps(entry, ensure_ascii=False))
                continue

            entry["sgf_hash"] = h
            enriched_here += 1

            pid = entry.get("puzzle_id")
            if isinstance(pid, int):
                collision_pids.setdefault(pid, set()).add(book_dir.name)

            out_lines.append(json.dumps(entry, ensure_ascii=False))

        total_enriched += enriched_here
        total_skipped_no_file += missing_here

        status = f"enriched={enriched_here} missing-sgf={missing_here}"
        print(f"  {book_dir.name}: {status}")

        if not dry_run and enriched_here > 0:
            log_path.write_text("\n".join(out_lines) + "\n", encoding="utf-8")

    # Cross-book pid collision count (informational)
    cross_book = sum(1 for books in collision_pids.values() if len(books) > 1)

    print(f"\n{'=' * 50}")
    print("Capture Log Enrichment Summary")
    print(f"{'=' * 50}")
    print(f"Books scanned:              {total_books}")
    print(f"Entries enriched:           {total_enriched}")
    print(f"Entries skipped (no file):  {total_skipped_no_file}")
    print(f"Pids appearing in 2+ books: {cross_book}")
    if dry_run:
        print("(dry run — no files were modified)")
    return 0


def _run_reconcile_books(args: argparse.Namespace) -> int:
    """Reconcile per-book ``book.json`` state with actual SGF files on disk."""
    import re

    from .config import get_output_dir
    from .receiver import reconcile_book_index

    output_dir = get_output_dir(getattr(args, "output_dir", None))
    books_dir = output_dir / "books"
    dry_run = getattr(args, "dry_run", False)
    target_book_id = getattr(args, "book_id", None)

    if not books_dir.exists():
        print("Error: no books/ directory found")
        return 1

    if dry_run:
        print("DRY RUN — no files will be modified\n")

    results = []
    for book_dir in sorted(books_dir.iterdir()):
        if not book_dir.is_dir():
            continue
        dir_match = re.match(r"^(\d+)-", book_dir.name)
        if not dir_match:
            continue
        book_id = int(dir_match.group(1))
        if target_book_id is not None and book_id != target_book_id:
            continue

        summary = reconcile_book_index(book_dir, dry_run=dry_run)
        if "error" in summary:
            print(f"  {book_dir.name}: {summary['error']}")
            continue

        results.append(summary)
        changes = summary["newly_captured"] + summary["updated_pids"]
        dups = summary.get("duplicates_removed", 0)
        if changes == 0 and dups == 0:
            print(f"  {book_dir.name}: already consistent ({summary['already_correct']} files)")
        else:
            parts = []
            if summary["newly_captured"]:
                parts.append(f"{summary['newly_captured']} newly captured")
            if summary["updated_pids"]:
                parts.append(f"{summary['updated_pids']} pid updates")
            if dups:
                parts.append(f"{dups} duplicates removed")
            if summary["orphan_files"]:
                parts.append(f"{summary['orphan_files']} orphans")
            print(f"  {book_dir.name}: " + ", ".join(parts))
            print(
                f"    → captured={summary['final_captured']} "
                f"external={summary['final_external']} "
                f"pending={summary['final_pending']}"
            )

    if not results:
        print("No books found to reconcile")
        return 1

    total_changes = sum(r["newly_captured"] + r["updated_pids"] for r in results)
    print(f"\n{'=' * 50}")
    print("Reconciliation Summary")
    print(f"{'=' * 50}")
    print(f"Books processed: {len(results)}")
    print(f"Total changes: {total_changes}")
    if dry_run:
        print("\n(dry run — no files were modified)")
    return 0


def _run_inventory(args: argparse.Namespace) -> int:
    """Show or refresh the corpus inventory."""
    import json

    from .config import get_output_dir
    from . import inventory as inv_mod

    output_dir = get_output_dir(getattr(args, "output_dir", None))
    refresh = bool(getattr(args, "refresh", False))
    as_json = bool(getattr(args, "json", False))

    if refresh:
        print(f"Scanning {output_dir} ...")
        inv = inv_mod.refresh_blocking(output_dir)
    else:
        inv = inv_mod.load_inventory(output_dir)
        if inv is None:
            print(
                "No inventory.json found. "
                "Run with --refresh to generate one."
            )
            return 1

    if as_json:
        print(json.dumps(inv, indent=2, ensure_ascii=False))
        return 0

    totals = inv["totals"]
    print(f"\nInventory generated_at: {inv['generated_at']}")
    print(f"Scan duration:         {inv['scan_duration_ms']} ms")
    print(f"\n{'=' * 50}")
    print("Totals")
    print(f"{'=' * 50}")
    print(f"  Files scanned:       {totals['files']}")
    print(f"  Unparseable:         {totals['files_unparsable']}")
    print(f"  Unique pids:         {totals['unique_pids']}")
    print(f"  Duplicate files:     {totals['duplicate_files']}")
    print(f"  Overlap %:           {totals['overlap_pct']}%")

    print(f"\n{'=' * 50}")
    print("Per-location")
    print(f"{'=' * 50}")
    for name, loc in inv["locations"].items():
        print(
            f"  {name:6s}  files={loc['files']:>6}  "
            f"unique_pids={loc['unique_pids']:>6}  "
            f"shared_with_others={loc['shared_with_others_pct']}%"
        )

    books = inv.get("books", [])
    if books:
        print(f"\n{'=' * 50}")
        print(f"Per-book overlap (top 10 by overlap %, of {len(books)} books)")
        print(f"{'=' * 50}")
        top = sorted(books, key=lambda b: b["overlap_with_corpus_pct"], reverse=True)[:10]
        for b in top:
            # CJK in dir names crashes cp1252 stdout on Windows; ascii-fold
            # for display only (the JSON artifact preserves them).
            safe_dir = b["dir"].encode("ascii", "replace").decode("ascii")
            print(
                f"  {safe_dir[:50]:50s}  "
                f"pids={b['unique_pids']:>5}  "
                f"overlap={b['overlap_with_corpus_pct']}%"
            )
    return 0



def _resolve_book_dir_for_cli(book_id: int):
    """Locate ``books/{book_id}-*`` for the configured output dir.

    Used by the manual skip-chapter / unskip-chapter CLI commands.
    Returns the Path on success, prints an error and returns None on
    failure so the caller can exit with a clean non-zero code.
    """
    from .book_state import find_book_dir
    from .config import get_output_dir

    books_dir = get_output_dir() / "books"
    if not books_dir.exists():
        print(f"Error: no books/ directory at {books_dir}")
        return None
    book_dir = find_book_dir(books_dir, book_id)
    if book_dir is None:
        print(f"Error: no directory found for book_id={book_id} under {books_dir}")
        return None
    return book_dir


def _append_skip_event(book_dir, event_type: str, detail: dict) -> None:
    """Append a structured skip event to the book's capture-log.jsonl."""
    import json
    from datetime import UTC, datetime

    entry = {
        "event_type": event_type,
        "recorded_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "book_id": detail.get("book_id"),
        "detail": detail,
    }
    log_path = book_dir / "capture-log.jsonl"
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _run_skip_chapter(args: argparse.Namespace) -> int:
    """Manually flag a chapter so the userscript stops re-visiting it."""
    from . import book_state

    book_dir = _resolve_book_dir_for_cli(args.book_id)
    if book_dir is None:
        return 1

    data = book_state.load(book_dir)
    if not data:
        print(f"Error: no book.json under {book_dir}")
        return 1

    ch = book_state.mark_skip(
        data,
        chapter_id=getattr(args, "chapter_id", None),
        chapter_number=getattr(args, "chapter", None),
        status="manual",
        reason=args.reason,
    )
    if ch is None:
        target = (
            f"chapter_id={args.chapter_id}" if args.chapter_id is not None
            else f"chapter={args.chapter}"
        )
        print(f"Error: no matching chapter ({target}) in {book_dir.name}")
        return 1

    book_state.save(book_dir, data)
    _append_skip_event(book_dir, "chapter_skip_marked", {
        "book_id": args.book_id,
        "chapter_id": ch.get("chapter_id"),
        "chapter_number": ch.get("chapter_number"),
        "chapter_name": ch.get("name"),
        "skip_status": "manual",
        "skip_reason": args.reason,
        "source": "cli",
    })
    print(
        f"OK: book {args.book_id} ch{ch.get('chapter_number')} "
        f"({ch.get('name', '')!r}) flagged skip_status=manual"
        + (f" reason={args.reason!r}" if args.reason else "")
    )
    return 0


def _run_unskip_chapter(args: argparse.Namespace) -> int:
    """Clear a chapter's skip flag (reverse of skip-chapter)."""
    from . import book_state

    book_dir = _resolve_book_dir_for_cli(args.book_id)
    if book_dir is None:
        return 1

    data = book_state.load(book_dir)
    if not data:
        print(f"Error: no book.json under {book_dir}")
        return 1

    ch = book_state.clear_skip(
        data,
        chapter_id=getattr(args, "chapter_id", None),
        chapter_number=getattr(args, "chapter", None),
    )
    if ch is None:
        target = (
            f"chapter_id={args.chapter_id}" if args.chapter_id is not None
            else f"chapter={args.chapter}"
        )
        print(f"Error: no matching chapter ({target}) in {book_dir.name}")
        return 1

    book_state.save(book_dir, data)
    _append_skip_event(book_dir, "chapter_skip_cleared", {
        "book_id": args.book_id,
        "chapter_id": ch.get("chapter_id"),
        "chapter_number": ch.get("chapter_number"),
        "chapter_name": ch.get("name"),
        "source": "cli",
    })
    print(
        f"OK: book {args.book_id} ch{ch.get('chapter_number')} "
        f"({ch.get('name', '')!r}) skip flag cleared"
    )
    return 0


def _run_receive(args: argparse.Namespace) -> int:
    """Start the HTTP receiver for browser-captured qqdata."""
    from .config import RECEIVER_HOST, RECEIVER_PORT, get_output_dir
    from .receiver import run_receiver

    output_dir = get_output_dir(getattr(args, "output_dir", None))
    host = getattr(args, "host", None) or RECEIVER_HOST
    port = getattr(args, "port", None) or RECEIVER_PORT
    batch_size = getattr(args, "batch_size", None) or DEFAULT_BATCH_SIZE

    setup_logging(
        output_dir=output_dir,
        verbose=getattr(args, "verbose", False),
        log_to_file=not getattr(args, "no_log_file", False),
    )

    run_receiver(
        output_dir=output_dir,
        host=host,
        port=port,
        batch_size=batch_size,
        match_collections=getattr(args, "match_collections", True),
        resolve_intent=getattr(args, "resolve_intent", True),
        book_id=getattr(args, "book_id", None),
    )
    return 0


def _run_import_jsonl(args: argparse.Namespace) -> int:
    """Import puzzles from a JSONL file of captured qqdata records."""
    from .config import get_output_dir
    from .receiver import import_jsonl

    jsonl_path: Path = args.jsonl_file
    if not jsonl_path.exists():
        print(f"Error: file not found: {jsonl_path}")
        return 1

    output_dir = get_output_dir(getattr(args, "output_dir", None))
    batch_size = getattr(args, "batch_size", None) or DEFAULT_BATCH_SIZE

    setup_logging(
        output_dir=output_dir,
        verbose=getattr(args, "verbose", False),
        log_to_file=not getattr(args, "no_log_file", False),
    )

    stats = import_jsonl(
        jsonl_path=jsonl_path,
        output_dir=output_dir,
        batch_size=batch_size,
        match_collections=getattr(args, "match_collections", True),
        resolve_intent=getattr(args, "resolve_intent", True),
    )
    print(f"\nImport complete: {stats['ok']} saved, {stats['skipped']} skipped, {stats['error']} errors")
    return 0 if stats["error"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
