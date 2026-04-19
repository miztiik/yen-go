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
        help="Discover puzzle IDs within one or more books (scrapes /book/levelorder/)",
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
    if args.source_mode == "backfill-yl":
        return _run_backfill_yl(args)
    if args.source_mode == "backfill-annotations":
        return _run_backfill_annotations(args)
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
    """Discover puzzle IDs within one or more books by scraping /book/levelorder/.

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
    def _flush_jsonl() -> None:
        with output_path.open("w", encoding="utf-8") as f:
            for bid in sorted(existing):
                f.write(json.dumps(existing[bid], ensure_ascii=False) + "\n")

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
    return 0


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
