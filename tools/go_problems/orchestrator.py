"""
Download orchestrator for GoProblems puzzles.

Coordinates fetching, validation, and saving puzzles with progress tracking,
checkpointing, and resume support. Supports three fetch modes:

1. ID Range (--start-id N --end-id M): Primary mode. Iterate range, skip 404s.
2. Specific IDs (--ids 100,200,300): Fetch exact list.
3. Paginated Listing (--list): Discover IDs via list endpoint, then fetch detail.
"""

from __future__ import annotations

import math
import signal
import time
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import ValidationError

from tools.core.logging import format_duration
from tools.core.rate_limit import RateLimiter

from .batching import count_total_files
from .checkpoint import (
    GoProblemsCheckpoint,
    load_checkpoint,
    save_checkpoint,
)
from .client import GoProblemsClient, GoProblemsClientError
from .config import (
    DEFAULT_BATCH_SIZE,
    DEFAULT_MAX_SOLUTION_DEPTH,
    DEFAULT_PUZZLE_DELAY,
    get_output_dir,
    get_sgf_dir,
)
from .converter import _extract_root_comment
from .index import load_puzzle_ids, rebuild_index, sort_index
from .logging_config import get_logger
from .models import GoProblemsDetail, GoProblemsListResponse
from .storage import save_puzzle
from .validator import validate_puzzle, validate_puzzle_early


@dataclass
class DownloadConfig:
    """Configuration for download operation."""

    max_puzzles: int = 10000
    resume: bool = False
    dry_run: bool = False
    output_dir: Path = field(default_factory=lambda: get_output_dir())

    # Fetch mode: ID range
    start_id: int | None = None
    end_id: int | None = None

    # Fetch mode: specific IDs
    puzzle_ids: list[int] | None = None

    # Fetch mode: paginated listing
    use_listing: bool = False

    # Rate limiting
    puzzle_delay: float = DEFAULT_PUZZLE_DELAY

    # Batching
    batch_size: int = DEFAULT_BATCH_SIZE

    # Validation
    max_solution_depth: int = DEFAULT_MAX_SOLUTION_DEPTH

    # Filtering
    canon_only: bool = True

    # Collection matching
    match_collections: bool = True

    # Intent resolution
    resolve_intent: bool = True
    intent_confidence_threshold: float = 0.8


@dataclass
class DownloadStats:
    """Statistics from download operation."""

    downloaded: int = 0
    skipped: int = 0
    errors: int = 0
    not_found: int = 0
    start_time: float = 0.0

    def elapsed_seconds(self) -> float:
        """Get elapsed time in seconds."""
        if self.start_time == 0:
            return 0.0
        return time.time() - self.start_time


class GracefulExit(Exception):
    """Raised on SIGINT to trigger graceful shutdown."""

    pass


def download_puzzles(config: DownloadConfig) -> DownloadStats:
    """Download puzzles from GoProblems.

    Supports three fetch modes:
    1. ID range (start_id to end_id) -- iterates through IDs, skips 404s
    2. Specific IDs -- fetches exact list
    3. Paginated listing -- discovers IDs via list endpoint

    Args:
        config: Download configuration

    Returns:
        Download statistics
    """
    stats = DownloadStats()
    stats.start_time = time.time()
    checkpoint: GoProblemsCheckpoint | None = None
    logger = get_logger()

    # Set up signal handler for graceful exit
    def signal_handler(signum: int, frame: object) -> None:
        logger.warning("\nReceived interrupt signal. Saving checkpoint...")
        raise GracefulExit()

    original_handler = signal.signal(signal.SIGINT, signal_handler)

    try:
        # Ensure output directory exists
        config.output_dir.mkdir(parents=True, exist_ok=True)
        sgf_dir = get_sgf_dir(config.output_dir)
        sgf_dir.mkdir(parents=True, exist_ok=True)

        session_downloaded = 0

        # Load checkpoint if resuming
        if config.resume:
            checkpoint = load_checkpoint(config.output_dir)
            if checkpoint:
                stats.downloaded = checkpoint.puzzles_downloaded
                stats.skipped = checkpoint.puzzles_skipped
                stats.errors = checkpoint.puzzles_errors
                stats.not_found = checkpoint.puzzles_not_found
                logger.info(
                    f"Resuming from checkpoint: {stats.downloaded} downloaded, "
                    f"last_id {checkpoint.last_processed_id}, "
                    f"batch {checkpoint.current_batch}"
                )

        # Create new checkpoint if needed
        if checkpoint is None:
            checkpoint = GoProblemsCheckpoint()

        # Load index for O(1) skip detection
        known_ids = load_puzzle_ids(config.output_dir)

        # Rebuild index if stale
        file_count = count_total_files(sgf_dir) if sgf_dir.exists() else 0
        if file_count > 0 and len(known_ids) < file_count:
            logger.info(
                f"Index has {len(known_ids)} entries but {file_count} files "
                f"exist, rebuilding..."
            )
            rebuild_index(config.output_dir, sgf_dir)
            known_ids = load_puzzle_ids(config.output_dir)

        if len(known_ids) > 0:
            logger.info(f"Found {len(known_ids)} indexed puzzles")

        # Initialize rate limiter
        puzzle_limiter = RateLimiter(
            min_delay=config.puzzle_delay,
            jitter_factor=0.2,
        )

        # Initialize HTTP client
        with GoProblemsClient() as client:
            # Determine puzzle IDs to fetch
            puzzle_ids_to_fetch = _resolve_puzzle_ids(
                config, checkpoint, client, logger
            )

            logger.info(
                f"Will process up to {len(puzzle_ids_to_fetch)} puzzle IDs "
                f"(max {config.max_puzzles} new downloads)"
            )

            # Process each puzzle ID
            for puzzle_id in puzzle_ids_to_fetch:
                if session_downloaded >= config.max_puzzles:
                    logger.info(
                        f"Reached max puzzles limit ({config.max_puzzles})"
                    )
                    break

                # Skip if already downloaded
                if puzzle_id in known_ids:
                    continue

                # Rate limit between requests
                wait_time = puzzle_limiter.wait_if_needed()
                if wait_time > 0:
                    logger.debug(f"Rate limit wait: {wait_time:.1f}s")

                try:
                    result = _process_puzzle(
                        client=client,
                        puzzle_id=puzzle_id,
                        config=config,
                        checkpoint=checkpoint,
                        known_ids=known_ids,
                    )

                    # Unpack tuple result from successful download
                    result_key: str
                    file_path: Path | None = None
                    if isinstance(result, tuple):
                        result_key, file_path = result
                    else:
                        result_key = result

                    if result_key == "downloaded":
                        stats.downloaded += 1
                        session_downloaded += 1
                        known_ids.add(puzzle_id)
                        checkpoint.record_success(puzzle_id, config.batch_size)

                        logger.puzzle_save(
                            puzzle_id=puzzle_id,
                            path=file_path.name if file_path else str(puzzle_id),
                            downloaded=stats.downloaded,
                            skipped=stats.skipped,
                            errors=stats.errors,
                        )

                        elapsed_sec = stats.elapsed_seconds()
                        elapsed = format_duration(elapsed_sec)
                        rate = (
                            session_downloaded / (elapsed_sec / 60)
                            if elapsed_sec > 0
                            else 0
                        )
                        logger.info(
                            f"  [{session_downloaded}/{config.max_puzzles}] "
                            f"saved | {len(known_ids)} on disk | "
                            f"{elapsed} elapsed | "
                            f"~{rate:.1f} puzzles/min"
                        )

                    elif result_key == "not_found":
                        stats.not_found += 1
                        checkpoint.record_not_found(puzzle_id)

                    elif result_key == "skipped":
                        stats.skipped += 1
                        checkpoint.record_skip(puzzle_id, "validation")

                    elif result_key == "dry_run":
                        stats.downloaded += 1
                        session_downloaded += 1

                except GoProblemsClientError as e:
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

                # Save checkpoint periodically
                save_checkpoint(checkpoint, config.output_dir)

    except GracefulExit:
        if checkpoint:
            checkpoint.puzzles_downloaded = stats.downloaded
            checkpoint.puzzles_skipped = stats.skipped
            checkpoint.puzzles_errors = stats.errors
            checkpoint.puzzles_not_found = stats.not_found
            save_checkpoint(checkpoint, config.output_dir)
            logger.info("Checkpoint saved. Run with --resume to continue.")

    finally:
        signal.signal(signal.SIGINT, original_handler)

    # Sort index for readability and clean git diffs
    if stats.downloaded > 0:
        sort_index(config.output_dir)

    return stats


def _resolve_puzzle_ids(
    config: DownloadConfig,
    checkpoint: GoProblemsCheckpoint,
    client: GoProblemsClient,
    logger: object,
) -> list[int]:
    """Determine which puzzle IDs to fetch based on config mode.

    Args:
        config: Download configuration
        checkpoint: Current checkpoint (for resume)
        client: GoProblems HTTP client
        logger: Logger instance

    Returns:
        List of puzzle IDs to process
    """
    # Mode 1: Specific IDs
    if config.puzzle_ids:
        ids = sorted(config.puzzle_ids)
        if config.resume and checkpoint.last_processed_id > 0:
            ids = [i for i in ids if i > checkpoint.last_processed_id]
        return ids

    # Mode 2: Paginated listing
    if config.use_listing:
        return _fetch_ids_from_listing(client, config, checkpoint, logger)

    # Mode 3: ID range (default)
    if config.start_id is not None and config.end_id is not None:
        start = config.start_id
        if config.resume and checkpoint.last_processed_id >= start:
            start = checkpoint.last_processed_id + 1
        return list(range(start, config.end_id + 1))

    # No mode specified -- this shouldn't happen (CLI validates)
    return []


def _fetch_ids_from_listing(
    client: GoProblemsClient,
    config: DownloadConfig,
    checkpoint: GoProblemsCheckpoint,
    logger: object,
) -> list[int]:
    """Discover puzzle IDs via the paginated list endpoint.

    Args:
        client: GoProblems HTTP client
        config: Download configuration
        checkpoint: Current checkpoint
        logger: Logger instance

    Returns:
        List of discovered puzzle IDs
    """
    all_ids: list[int] = []
    page = 1
    page_size = 50

    if config.resume and checkpoint.last_page > 0:
        page = checkpoint.last_page + 1

    while True:
        try:
            response = client.get_puzzles_page(page=page, page_size=page_size)
            page_data = GoProblemsListResponse.model_validate(response)

            for item in page_data.results:
                all_ids.append(item.id)

            total_pages = math.ceil(page_data.count / page_size) if page_data.count > 0 else 0

            if not page_data.next or page > total_pages:
                break

            page += 1

        except GoProblemsClientError as e:
            logger.warning(f"Failed to fetch list page {page}: {e}")  # type: ignore[attr-defined]
            break

    return sorted(all_ids)


def _resolve_puzzle_intent(
    puzzle_id: int,
    description: str,
    threshold: float,
    logger: object,
) -> str | None:
    """Resolve puzzle description/comment to an objective slug via puzzle_intent.

    Strategy:
    1. Try with semantic matching enabled (enable_semantic=True)
    2. If that fails (ImportError, model error, etc.), fall back to deterministic
    3. Apply confidence threshold

    Args:
        puzzle_id: GoProblems puzzle ID (for logging)
        description: Text to resolve (typically root C[] content)
        threshold: Minimum confidence to accept
        logger: Logger instance

    Returns:
        Objective slug string (e.g. "life-and-death-black-kill") or None
    """
    try:
        from tools.puzzle_intent import resolve_intent
    except ImportError as e:
        logger.warning(  # type: ignore[attr-defined]
            f"Puzzle {puzzle_id}: puzzle_intent not available: {e}"
        )
        return None

    # Try semantic matching first, fall back to deterministic
    try:
        result = resolve_intent(description, enable_semantic=True)
    except Exception as e:
        logger.debug(  # type: ignore[attr-defined]
            f"Puzzle {puzzle_id}: semantic intent failed ({e}), "
            f"falling back to deterministic"
        )
        try:
            result = resolve_intent(description, enable_semantic=False)
        except Exception as e2:
            logger.warning(  # type: ignore[attr-defined]
                f"Puzzle {puzzle_id}: intent resolution failed: {e2}"
            )
            return None

    if not result.matched:
        logger.debug(  # type: ignore[attr-defined]
            f"Puzzle {puzzle_id}: no intent match for '{description}'"
        )
        return None

    if result.confidence < threshold:
        logger.debug(  # type: ignore[attr-defined]
            f"Puzzle {puzzle_id}: intent '{result.objective_id}' "
            f"below threshold ({result.confidence:.2f} < {threshold})"
        )
        return None

    slug = result.objective.slug if result.objective else None
    if not slug:
        logger.warning(  # type: ignore[attr-defined]
            f"Puzzle {puzzle_id}: intent matched '{result.objective_id}' "
            f"but objective has no slug"
        )
        return None

    logger.info(  # type: ignore[attr-defined]
        f"Puzzle {puzzle_id}: intent '{slug}' "
        f"(confidence={result.confidence:.2f}, tier={result.match_tier.value})"
    )
    return slug


def _process_puzzle(
    client: GoProblemsClient,
    puzzle_id: int,
    config: DownloadConfig,
    checkpoint: GoProblemsCheckpoint,
    known_ids: set[int],
) -> str | tuple[str, Path]:
    """Fetch, validate, and save a single puzzle.

    Args:
        client: GoProblems HTTP client
        puzzle_id: Puzzle ID to process
        config: Download configuration
        checkpoint: Current checkpoint
        known_ids: Set of already-downloaded IDs

    Returns:
        Result string ("not_found", "skipped", "dry_run") or tuple ("downloaded", file_path)
    """
    logger = get_logger()
    url = f"{client.base_url}/problems/{puzzle_id}"

    logger.puzzle_fetch(puzzle_id, url)

    # Fetch puzzle data
    raw_data = client.get_puzzle(puzzle_id)

    if raw_data is None:
        logger.puzzle_not_found(puzzle_id)
        return "not_found"

    # Early validation (before Pydantic)
    rejection = validate_puzzle_early(
        raw_data, puzzle_id, canon_only=config.canon_only
    )
    if rejection:
        logger.puzzle_skip(puzzle_id, rejection)
        return "skipped"

    # Parse with Pydantic
    puzzle = GoProblemsDetail.model_validate(raw_data)

    # Full validation (SGF content) — pass CLI max_solution_depth
    validation = validate_puzzle(
        puzzle.sgf, puzzle_id,
        max_solution_depth=config.max_solution_depth,
    )
    if not validation.is_valid:
        logger.puzzle_skip(
            puzzle_id, validation.rejection_reason or "Invalid"
        )
        return "skipped"

    # Dry run
    if config.dry_run:
        logger.info(f"[DRY RUN] Would save puzzle {puzzle_id}")
        return "dry_run"

    # Resolve puzzle intent from root C[] comment (before enrichment strips it)
    root_comment: str | None = None
    if config.resolve_intent:
        raw_comment = _extract_root_comment(puzzle.sgf)
        if raw_comment:
            root_comment = _resolve_puzzle_intent(
                puzzle_id=puzzle_id,
                description=raw_comment,
                threshold=config.intent_confidence_threshold,
                logger=logger,
            )

    # Save puzzle
    file_path, batch_num = save_puzzle(
        puzzle,
        config.output_dir,
        config.batch_size,
        checkpoint=checkpoint,
        match_collections=config.match_collections,
        root_comment=root_comment,
    )

    return ("downloaded", file_path)
