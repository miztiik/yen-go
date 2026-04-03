"""
Download orchestrator for OGS puzzles.

Coordinates fetching, validation, and saving puzzles with progress tracking,
checkpointing, and resume support.
"""

from __future__ import annotations

import math
import signal
import time
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import ValidationError

from tools.core.rate_limit import RateLimiter, wait_with_jitter

from .batching import count_total_files
from .checkpoint import (
    OGSCheckpoint,
    load_checkpoint,
    save_checkpoint,
)
from .client import OGSClient, OGSClientError
from .collection_index import CollectionIndex, find_sorted_jsonl
from .collections import resolve_all_collection_slugs
from .config import (
    DEFAULT_BATCH_SIZE,
    DEFAULT_MAX_MOVE_TREE_DEPTH,
    DEFAULT_PAGE_DELAY,
    DEFAULT_PAGE_SIZE,
    DEFAULT_PUZZLE_DELAY,
    get_output_dir,
    get_sgf_dir,
)
from .index import load_puzzle_ids, rebuild_index, sort_index
from .logging_config import StructuredLogger, get_logger
from .models import OGSPuzzleDetail, OGSPuzzleList
from .objective import parse_objective_from_html
from .storage import save_puzzle
from .validator import validate_puzzle, validate_puzzle_data_early


@dataclass
class DownloadConfig:
    """Configuration for download operation."""

    max_puzzles: int = 10000
    resume: bool = False
    dry_run: bool = False
    output_dir: Path = field(default_factory=lambda: get_output_dir())

    # Rate limiting
    page_delay: float = DEFAULT_PAGE_DELAY
    puzzle_delay: float = DEFAULT_PUZZLE_DELAY

    # Batching
    batch_size: int = DEFAULT_BATCH_SIZE
    page_size: int = DEFAULT_PAGE_SIZE

    # Validation
    max_move_tree_depth: int = DEFAULT_MAX_MOVE_TREE_DEPTH

    # Pagination control
    start_page: int | None = None  # For resuming from specific page
    single_page: int | None = None  # Download only this page

    # Objective parsing
    fetch_objective: bool = False  # Fetch puzzle HTML to parse objective tags

    # Collection matching
    match_collections: bool = True  # Match OGS collection names to YL[] slugs
    collections_jsonl_path: Path | None = None  # Path to sorted collections JSONL for reverse-index enrichment

    # Intent resolution
    resolve_intent: bool = True  # Resolve puzzle_description to C[] objective
    intent_confidence_threshold: float = 0.8  # Minimum confidence for intent match


@dataclass
class DownloadStats:
    """Statistics from download operation."""

    downloaded: int = 0
    skipped: int = 0
    errors: int = 0
    pages_processed: int = 0
    start_time: float = 0.0  # Start timestamp for timing

    def elapsed_seconds(self) -> float:
        """Get elapsed time in seconds."""
        import time
        if self.start_time == 0:
            return 0.0
        return time.time() - self.start_time

    def avg_seconds_per_puzzle(self) -> float:
        """Get average seconds per downloaded puzzle."""
        if self.downloaded == 0:
            return 0.0
        return self.elapsed_seconds() / self.downloaded

    def estimate_batch_time(self, batch_size: int) -> float:
        """Estimate time to complete a batch in seconds."""
        return self.avg_seconds_per_puzzle() * batch_size


class GracefulExit(Exception):
    """Raised on SIGINT to trigger graceful shutdown."""
    pass


def download_puzzles(config: DownloadConfig) -> DownloadStats:
    """Download puzzles from OGS.

    Args:
        config: Download configuration

    Returns:
        Download statistics
    """
    stats = DownloadStats()
    stats.start_time = time.time()  # Start timing
    checkpoint: OGSCheckpoint | None = None
    logger = get_logger()

    # Set up signal handler for graceful exit
    def signal_handler(signum, frame):
        logger.warning("\nReceived interrupt signal. Saving checkpoint...")
        raise GracefulExit()

    original_handler = signal.signal(signal.SIGINT, signal_handler)

    try:
        # Ensure output directory exists
        config.output_dir.mkdir(parents=True, exist_ok=True)
        sgf_dir = get_sgf_dir(config.output_dir)
        sgf_dir.mkdir(parents=True, exist_ok=True)

        # Track session downloads separately from total (for --max-puzzles limit)
        session_downloaded = 0

        # Load checkpoint if resuming
        if config.resume:
            checkpoint = load_checkpoint(config.output_dir)
            if checkpoint:
                stats.downloaded = checkpoint.puzzles_downloaded
                stats.skipped = checkpoint.puzzles_skipped
                stats.errors = checkpoint.puzzles_errors
                logger.info(
                    f"Resuming from checkpoint: {stats.downloaded} downloaded, "
                    f"page {checkpoint.last_page}, batch {checkpoint.current_batch}"
                )

        # Create new checkpoint if needed
        if checkpoint is None:
            checkpoint = OGSCheckpoint()

        # Load index for O(1) skip detection
        known_ids = load_puzzle_ids(config.output_dir)

        # Rebuild index if it's stale (e.g., files from before index was introduced)
        file_count = count_total_files(sgf_dir) if sgf_dir.exists() else 0
        if file_count > 0 and len(known_ids) < file_count:
            logger.info(
                f"Index has {len(known_ids)} entries but {file_count} files exist, rebuilding..."
            )
            rebuild_index(config.output_dir, sgf_dir)
            known_ids = load_puzzle_ids(config.output_dir)

        if len(known_ids) > 0:
            logger.info(f"Found {len(known_ids)} indexed puzzles")

        # Load collection reverse index for multi-collection YL[] matching
        collection_index: CollectionIndex | None = None
        if config.match_collections:
            jsonl_path = config.collections_jsonl_path or find_sorted_jsonl()
            if jsonl_path is not None:
                collection_index = CollectionIndex.from_jsonl(jsonl_path)
                logger.info(
                    f"Collection reverse index: {collection_index.total_puzzle_ids} "
                    f"puzzle IDs across {collection_index.total_collections} collections"
                )
            else:
                logger.info(
                    "No collections JSONL found; YL[] will use API collection name only"
                )

        # Initialize HTTP client
        with OGSClient() as client:
            # Check curl availability if objective parsing requested
            if config.fetch_objective:
                if client._curl_available():
                    logger.info("Objective parsing enabled (--fetch-objective): will fetch puzzle HTML for extra tags")
                else:
                    logger.warning(
                        "Objective parsing requested but curl is not available on this system. "
                        "Proceeding without objective tags."
                    )

            # Initialize rate limiter for puzzle delays
            # Uses timestamp-based limiting: only waits remaining time after processing
            puzzle_limiter = RateLimiter(
                min_delay=config.puzzle_delay,
                jitter_factor=0.2,
            )

            # Fetch first page to get total count
            logger.info("Fetching puzzle count from OGS...")
            first_response = client.get_puzzles_page(page=1, page_size=config.page_size)
            first_page = OGSPuzzleList.model_validate(first_response)

            total_puzzles = first_page.count
            total_pages = math.ceil(total_puzzles / config.page_size)

            logger.info(f"Total puzzles available: {total_puzzles} ({total_pages} pages)")
            logger.info(f"Will download up to {config.max_puzzles} new puzzles this session")

            # Determine starting and ending page
            start_page = 1
            end_page = total_pages

            if config.single_page:
                # Single page mode: download only this page
                start_page = config.single_page
                end_page = config.single_page
                logger.info(f"Single page mode: downloading page {start_page} only")
            elif config.start_page:
                start_page = config.start_page
            elif checkpoint and checkpoint.last_page > 0:
                # Resume from last completed page + 1
                if checkpoint.puzzle_index_in_page == -1:
                    start_page = checkpoint.last_page + 1
                else:
                    start_page = checkpoint.last_page

            # Process pages
            for page_num in range(start_page, end_page + 1):
                if session_downloaded >= config.max_puzzles:
                    logger.info(f"Reached max puzzles limit ({config.max_puzzles})")
                    break

                page_url = f"https://online-go.com/api/v1/puzzles/?page={page_num}&page_size={config.page_size}"
                logger.page_start(page_num, total_pages, url=page_url)

                try:
                    page_stats = _process_page(
                        client=client,
                        page_num=page_num,
                        config=config,
                        checkpoint=checkpoint,
                        logger=logger,
                        max_remaining=config.max_puzzles - session_downloaded,
                        total_pages=total_pages,
                        global_stats=stats,
                        puzzle_limiter=puzzle_limiter,
                        known_ids=known_ids,
                        collection_index=collection_index,
                    )

                    stats.downloaded += page_stats.downloaded
                    session_downloaded += page_stats.downloaded
                    stats.skipped += page_stats.skipped
                    stats.errors += page_stats.errors
                    stats.pages_processed += 1

                    # Update checkpoint
                    checkpoint.last_page = page_num
                    checkpoint.puzzle_index_in_page = -1  # Page complete
                    checkpoint.puzzles_downloaded = stats.downloaded
                    checkpoint.puzzles_skipped = stats.skipped
                    checkpoint.puzzles_errors = stats.errors

                    save_checkpoint(checkpoint, config.output_dir)
                    logger.checkpoint_save(stats.downloaded, page_num)

                except OGSClientError as e:
                    logger.error(f"Failed to fetch page {page_num}: {e}")
                    stats.errors += 1
                    continue

                # Delay between pages
                if page_num < total_pages and session_downloaded < config.max_puzzles:
                    logger.api_wait(config.page_delay, reason="page_delay")
                    wait_with_jitter(config.page_delay)

    except GracefulExit:
        # Save checkpoint on interrupt
        if checkpoint:
            checkpoint.puzzles_downloaded = stats.downloaded
            checkpoint.puzzles_skipped = stats.skipped
            checkpoint.puzzles_errors = stats.errors
            save_checkpoint(checkpoint, config.output_dir)
            logger.info("Checkpoint saved. Run with --resume to continue.")

    finally:
        # Restore original signal handler
        signal.signal(signal.SIGINT, original_handler)

    # Sort index for readability and clean git diffs
    if stats.downloaded > 0:
        sort_index(config.output_dir)

    return stats


def _process_page(
    client: OGSClient,
    page_num: int,
    config: DownloadConfig,
    checkpoint: OGSCheckpoint,
    logger: StructuredLogger,
    max_remaining: int,
    total_pages: int,
    global_stats: DownloadStats,
    puzzle_limiter: RateLimiter,
    known_ids: set[int],
    collection_index: CollectionIndex | None = None,
) -> DownloadStats:
    """Process a single page of puzzles.

    Args:
        client: OGS HTTP client
        page_num: Page number to process
        config: Download configuration
        checkpoint: Current checkpoint state
        logger: Structured logger
        max_remaining: Maximum puzzles still allowed to download
        total_pages: Total pages available
        global_stats: Global download statistics (for running totals)
        puzzle_limiter: Rate limiter for puzzle fetches (overlaps wait with processing)
        known_ids: In-memory set of already-downloaded puzzle IDs for O(1) skip
        collection_index: Optional reverse index for multi-collection YL[] matching

    Returns:
        Statistics for this page
    """
    stats = DownloadStats()

    # Fetch page
    page_url = f"https://online-go.com/api/v1/puzzles/?page={page_num}&page_size={config.page_size}"
    response = client.get_puzzles_page(page=page_num, page_size=config.page_size)
    page = OGSPuzzleList.model_validate(response)

    # Log page fetch with URL and puzzle count
    logger.page_fetch(page_num, page_url, len(page.results))

    # Determine starting index within page (for resume)
    start_idx = 0
    if checkpoint.last_page == page_num and checkpoint.puzzle_index_in_page >= 0:
        start_idx = checkpoint.puzzle_index_in_page + 1

    # Process each puzzle in the page
    for idx, puzzle_item in enumerate(page.results[start_idx:], start=start_idx):
        if stats.downloaded >= max_remaining:
            break

        puzzle_id = puzzle_item.id
        puzzle_url = f"https://online-go.com/api/v1/puzzles/{puzzle_id}/"

        # Skip if already downloaded (O(1) index lookup)
        if puzzle_id in known_ids:
            logger.puzzle_skip(puzzle_id, "Already downloaded")
            stats.skipped += 1
            continue

        # Rate limit between puzzles (timestamp-based: only waits remaining time)
        # If processing took longer than min_delay, no wait needed
        wait_time = puzzle_limiter.wait_if_needed()
        if wait_time > 0:
            logger.api_wait(wait_time, reason="puzzle_delay")

        # Log puzzle fetch with URL
        logger.puzzle_fetch(puzzle_id, puzzle_url)

        try:
            # Fetch full puzzle details
            puzzle_data = client.get_puzzle(puzzle_id)

            # Early validation (before Pydantic parsing)
            rejection = validate_puzzle_data_early(
                puzzle_data,
                puzzle_id,
                max_depth=config.max_move_tree_depth,
            )
            if rejection:
                logger.puzzle_skip(puzzle_id, rejection)
                stats.skipped += 1
                checkpoint.record_skip(rejection)
                continue

            # Parse with Pydantic
            puzzle = OGSPuzzleDetail.model_validate(puzzle_data)

            # Full validation
            validation = validate_puzzle(puzzle, puzzle_id)
            if not validation.is_valid:
                logger.puzzle_skip(puzzle_id, validation.rejection_reason or "Invalid")
                stats.skipped += 1
                checkpoint.record_skip(validation.rejection_reason or "Invalid")
                continue

            # Dry run: don't save
            if config.dry_run:
                logger.info(f"[DRY RUN] Would save puzzle {puzzle_id}")
                stats.downloaded += 1
                continue

            # Fetch objective tags from HTML if enabled
            extra_tags: list[str] | None = None
            if config.fetch_objective:
                html = client.get_puzzle_page_html(puzzle_id)
                if html:
                    extra_tags = parse_objective_from_html(html) or None
                    if extra_tags:
                        logger.info(
                            f"Puzzle {puzzle_id}: objective tags: {extra_tags}"
                        )
                    else:
                        logger.debug(
                            f"Puzzle {puzzle_id}: no objective tags parsed from HTML"
                        )
                else:
                    logger.debug(
                        f"Puzzle {puzzle_id}: objective HTML fetch skipped or failed"
                    )

            # Resolve collection membership -> YL[] slugs (multi-collection)
            collection_slugs: list[str] = []
            if config.match_collections:
                api_coll_name = puzzle.collection.name if puzzle.collection else None
                collection_slugs = resolve_all_collection_slugs(
                    puzzle_id=puzzle_id,
                    api_collection_name=api_coll_name,
                    collection_index=collection_index,
                )
                if collection_slugs:
                    logger.info(
                        f"Puzzle {puzzle_id}: YL[{','.join(collection_slugs)}] "
                        f"({len(collection_slugs)} collection(s))"
                    )
                elif api_coll_name:
                    logger.warning(
                        f"Puzzle {puzzle_id}: unmatched collection "
                        f"'{api_coll_name}'"
                    )

            # Resolve puzzle_description to objective via puzzle_intent
            root_comment: str | None = None
            if config.resolve_intent and puzzle.puzzle_description:
                root_comment = _resolve_puzzle_intent(
                    puzzle_id=puzzle_id,
                    description=puzzle.puzzle_description,
                    threshold=config.intent_confidence_threshold,
                    logger=logger,
                )

            # Save puzzle (pass checkpoint for O(1) batch lookup)
            file_path, batch_num = save_puzzle(
                puzzle,
                config.output_dir,
                config.batch_size,
                checkpoint=checkpoint,
                extra_tags=extra_tags,
                collection_slugs=collection_slugs or None,
                root_comment=root_comment,
            )

            stats.downloaded += 1
            known_ids.add(puzzle_id)
            total_downloaded = global_stats.downloaded + stats.downloaded
            total_skipped = global_stats.skipped + stats.skipped
            total_errors = global_stats.errors + stats.errors

            logger.puzzle_save(
                puzzle_id=puzzle_id,
                path=file_path.name,
                downloaded=total_downloaded,
                skipped=total_skipped,
                errors=total_errors,
            )

            # Update checkpoint AFTER successful save (includes batch advancement)
            checkpoint.record_success(config.batch_size)

            # Per-file checkpoint: save after each successful file
            checkpoint.puzzle_index_in_page = idx
            checkpoint.last_puzzle_id = puzzle_id
            # Note: puzzles_downloaded already incremented in record_success()
            save_checkpoint(checkpoint, config.output_dir)

        except OGSClientError as e:
            if "not found" in str(e).lower():
                logger.puzzle_skip(puzzle_id, "Not found (404)")
                stats.skipped += 1
            else:
                logger.puzzle_error(puzzle_id, str(e))
                stats.errors += 1
                checkpoint.record_error(puzzle_id, str(e))

        except ValidationError as e:
            logger.puzzle_error(puzzle_id, f"Validation error: {e}")
            stats.errors += 1
            checkpoint.record_error(puzzle_id, str(e))

        except Exception as e:
            logger.puzzle_error(puzzle_id, f"Unexpected error: {e}")
            stats.errors += 1
            checkpoint.record_error(puzzle_id, str(e))

        # Update checkpoint with current progress (for errors/skips)
        checkpoint.puzzle_index_in_page = idx
        checkpoint.last_puzzle_id = puzzle_id

    return stats


def _resolve_puzzle_intent(
    puzzle_id: int,
    description: str,
    threshold: float,
    logger: StructuredLogger,
) -> str | None:
    """Resolve puzzle description to an objective slug via puzzle_intent.

    Strategy:
    1. Try with semantic matching enabled (enable_semantic=True)
    2. If that fails (ImportError, model error, etc.), fall back to deterministic
    3. Apply confidence threshold

    Args:
        puzzle_id: OGS puzzle ID (for logging)
        description: Puzzle description text
        threshold: Minimum confidence to accept
        logger: Structured logger

    Returns:
        Objective slug string (e.g. "life-and-death-black-kill") or None
    """
    try:
        from tools.puzzle_intent import resolve_intent
    except ImportError as e:
        logger.warning(f"Puzzle {puzzle_id}: puzzle_intent not available: {e}")
        return None

    # Try semantic matching first, fall back to deterministic
    try:
        result = resolve_intent(description, enable_semantic=True)
    except Exception as e:
        logger.debug(
            f"Puzzle {puzzle_id}: semantic intent failed ({e}), "
            f"falling back to deterministic"
        )
        try:
            result = resolve_intent(description, enable_semantic=False)
        except Exception as e2:
            logger.warning(
                f"Puzzle {puzzle_id}: intent resolution failed: {e2}"
            )
            return None

    if not result.matched:
        logger.debug(f"Puzzle {puzzle_id}: no intent match for description")
        return None

    if result.confidence < threshold:
        logger.debug(
            f"Puzzle {puzzle_id}: intent '{result.objective_id}' "
            f"below threshold ({result.confidence:.2f} < {threshold})"
        )
        return None

    slug = result.objective.slug if result.objective else None
    if not slug:
        logger.warning(
            f"Puzzle {puzzle_id}: intent matched '{result.objective_id}' "
            f"but objective has no slug"
        )
        return None

    logger.info(
        f"Puzzle {puzzle_id}: intent '{slug}' "
        f"(confidence={result.confidence:.2f}, tier={result.match_tier.value})"
    )
    return slug
