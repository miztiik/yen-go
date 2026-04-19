"""
Download orchestrator for Tsumego Hero puzzles.

Coordinates fetching, filtering, and saving puzzles with progress tracking,
checkpointing, and resume support.
"""

from __future__ import annotations

import signal
import time
from dataclasses import dataclass, field
from pathlib import Path

from tools.core.paths import rel_path
from tools.core.sgf_builder import SGFBuildError
from tools.core.validation import DEFAULT_CONFIG, PuzzleValidationConfig, validate_sgf_puzzle

from .batching import THERO_BATCH_SIZE, count_total_files, get_sgf_dir
from .checkpoint import (
    THeroCheckpoint,
    load_checkpoint,
    save_checkpoint,
)
from .client import PuzzleData, TsumegoHeroClient, TsumegoHeroClientError
from .collections_matcher import resolve_collection_slug
from .index import load_puzzle_ids, rebuild_index, sort_index
from .logging_config import StructuredLogger, get_logger
from .storage import save_puzzle

# Default output directory
DEFAULT_OUTPUT_DIR = Path("external-sources/t-hero")

# Checkpoint save interval (every N puzzles)
CHECKPOINT_INTERVAL = 10

# Tool display name
TOOL_NAME = "Tsumego Hero Downloader"


@dataclass
class DownloadConfig:
    """Configuration for download operation."""

    # Target collections (None = all enabled)
    collections: list[str] | None = None

    # Limits
    max_puzzles: int = 1000
    max_per_collection: int | None = None

    # Modes
    resume: bool = False
    dry_run: bool = False

    # Output
    output_dir: Path = field(default_factory=lambda: DEFAULT_OUTPUT_DIR)
    batch_size: int = THERO_BATCH_SIZE

    # Rate limiting
    request_delay: float = 2.5
    jitter_factor: float = 0.4

    # Collection matching
    match_collections: bool = True

    # Intent resolution
    resolve_intent: bool = True
    intent_confidence_threshold: float = 0.8
    # Validation: minimum stones override (None = use config default)
    min_stones: int | None = None
    # Validation: minimum board dimension override (None = use config default)
    min_board_size: int | None = None
    # Validation: maximum solution depth override (None = use config default, 0 = no cap)
    max_solution_depth: int | None = None
    # Validation: minimum solution depth override (None = use config default, 0 = allow no-solution)
    min_solution_depth: int | None = None

    # Gap fill: after collections, auto-find and download out-of-collection puzzles
    fill_gaps: bool = False
    fill_gaps_max_id: int = 17500

    @property
    def validation_config(self) -> PuzzleValidationConfig | None:
        """Build validation config with CLI overrides (if any)."""
        overrides: dict = {}
        if self.min_stones is not None:
            overrides["min_stones"] = self.min_stones
        if self.min_board_size is not None:
            overrides["min_board_size"] = self.min_board_size
        if self.min_solution_depth is not None:
            overrides["min_solution_depth"] = self.min_solution_depth
        if self.max_solution_depth is not None:
            # 0 means no cap
            overrides["max_solution_depth"] = None if self.max_solution_depth == 0 else self.max_solution_depth
        if overrides:
            return DEFAULT_CONFIG.merge(overrides)
        return None


@dataclass
class DownloadStats:
    """Statistics from download operation."""

    downloaded: int = 0
    skipped: int = 0
    errors: int = 0
    collections_processed: int = 0
    collections_assigned: int = 0
    intents_resolved: int = 0
    start_time: float = 0.0

    def elapsed_seconds(self) -> float:
        """Get elapsed time in seconds."""
        if self.start_time == 0:
            return 0.0
        return time.time() - self.start_time

    def puzzles_per_minute(self) -> float:
        """Get download rate in puzzles per minute."""
        elapsed = self.elapsed_seconds()
        if elapsed == 0 or self.downloaded == 0:
            return 0.0
        return (self.downloaded / elapsed) * 60


class GracefulExit(Exception):
    """Raised on SIGINT to trigger graceful shutdown."""
    pass


def _resolve_puzzle_intent(
    puzzle_id: int,
    description: str,
    threshold: float,
    logger: StructuredLogger,
) -> str | None:
    """Resolve puzzle description to an objective slug via puzzle_intent.

    Strategy:
    1. Try with semantic matching enabled
    2. Fall back to deterministic if semantic fails
    3. Apply confidence threshold

    Args:
        puzzle_id: Puzzle ID (for logging).
        description: Puzzle description text.
        threshold: Minimum confidence to accept.
        logger: Structured logger instance.

    Returns:
        Objective slug string or None.
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
            logger.warning(f"Puzzle {puzzle_id}: intent resolution failed: {e2}")
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
        logger.intent_match(
            puzzle_id=puzzle_id,
            description_snippet=description,
            matched_slug=None,
            confidence=result.confidence,
            tier=result.match_tier,
        )
        return None

    logger.intent_match(
        puzzle_id=puzzle_id,
        description_snippet=description,
        matched_slug=slug,
        confidence=result.confidence,
        tier=result.match_tier,
    )
    return slug


def _enrich_puzzle(
    puzzle: PuzzleData,
    config: DownloadConfig,
    logger: StructuredLogger,
) -> tuple[list[str] | None, str | None]:
    """Resolve collection and intent for a puzzle.

    Args:
        puzzle: Puzzle data from client.
        config: Download configuration.
        logger: Structured logger.

    Returns:
        Tuple of (collection_slugs, root_comment).
    """
    # Collection resolution (YL)
    collection_slugs: list[str] | None = None
    collection_slug: str | None = None
    if config.match_collections and puzzle.collection_name:
        collection_slug = resolve_collection_slug(puzzle.collection_name)
        if collection_slug:
            collection_slugs = [collection_slug]

    # Log collection match
    logger.collection_match(
        puzzle_id=puzzle.url_id,
        source_name=puzzle.collection_name or "",
        matched_slug=collection_slug,
    )

    # Intent resolution (C[])
    root_comment: str | None = None
    if config.resolve_intent and puzzle.description:
        root_comment = _resolve_puzzle_intent(
            puzzle_id=puzzle.url_id,
            description=puzzle.description,
            threshold=config.intent_confidence_threshold,
            logger=logger,
        )

    return collection_slugs, root_comment


def download_puzzles(config: DownloadConfig) -> DownloadStats:
    """Download puzzles from Tsumego Hero.

    Args:
        config: Download configuration.

    Returns:
        Download statistics.
    """
    stats = DownloadStats()
    stats.start_time = time.time()
    checkpoint: THeroCheckpoint | None = None
    logger = get_logger()

    # Set up signal handler for graceful exit
    def signal_handler(signum, frame):
        logger.warning("Received interrupt signal. Saving checkpoint...")
        raise GracefulExit()

    original_handler = signal.signal(signal.SIGINT, signal_handler)

    try:
        # Ensure output directory exists
        config.output_dir.mkdir(parents=True, exist_ok=True)
        sgf_dir = get_sgf_dir(config.output_dir)
        sgf_dir.mkdir(parents=True, exist_ok=True)

        # Load index for O(1) dedup
        known_ids = load_puzzle_ids(config.output_dir)
        total_files = count_total_files(sgf_dir)
        if len(known_ids) < total_files:
            logger.info(f"Index stale ({len(known_ids)} < {total_files} files), rebuilding...")
            rebuild_index(config.output_dir)
            known_ids = load_puzzle_ids(config.output_dir)
        logger.info(f"Loaded index: {len(known_ids)} known puzzles")

        # Load checkpoint if resuming
        if config.resume:
            checkpoint = load_checkpoint(config.output_dir)
            if checkpoint:
                stats.downloaded = checkpoint.puzzles_downloaded
                stats.skipped = checkpoint.puzzles_skipped
                stats.errors = checkpoint.puzzles_errors
                logger.info(
                    f"Resuming from checkpoint: {stats.downloaded} downloaded, "
                    f"{len(checkpoint.collections_completed)} collections done"
                )

        # Create new checkpoint if needed
        if checkpoint is None:
            checkpoint = THeroCheckpoint()
            # Count existing files
            existing_count = count_total_files(sgf_dir)
            if existing_count > 0:
                logger.info(f"Found {existing_count} existing files")

        # Initialize HTTP client
        with TsumegoHeroClient(
            base_delay=config.request_delay,
            jitter_factor=config.jitter_factor,
        ) as client:

            # Fetch collection list
            logger.info("Fetching collections from /sets...")
            collections = client.fetch_collections()
            logger.info(f"Found {len(collections)} collections")

            # Filter to target collections if specified
            if config.collections:
                target_set_ids = config.collections
            else:
                target_set_ids = list(collections.keys())

            # Skip completed collections
            target_set_ids = [
                set_id for set_id in target_set_ids
                if set_id not in checkpoint.collections_completed
            ]

            if not target_set_ids:
                logger.info("All collections already completed")
                return stats

            logger.info(f"Processing {len(target_set_ids)} collections")

            # Dry run: just print plan
            if config.dry_run:
                _print_download_plan(collections, target_set_ids, config)
                return stats

            # Track session downloads for --max-puzzles limit
            session_downloaded = 0

            # Process each collection
            for set_id in target_set_ids:
                if session_downloaded >= config.max_puzzles:
                    logger.info(f"Reached max puzzles limit ({config.max_puzzles})")
                    break

                collection_info = collections.get(set_id, {})
                collection_name = collection_info.get("name", f"Collection {set_id}")

                logger.collection_start(
                    set_id=set_id,
                    name=collection_name,
                    count=collection_info.get("puzzle_count", 0),
                )
                checkpoint.start_collection(set_id, collection_name)

                try:
                    # Fetch puzzle IDs in this collection
                    puzzle_ids = client.fetch_collection_puzzles(int(set_id))
                    logger.info(f"Found {len(puzzle_ids)} puzzles in {collection_name}")

                    # Skip already-processed puzzles if resuming mid-collection
                    start_idx = checkpoint.puzzle_index_in_collection
                    if start_idx > 0:
                        logger.info(f"Resuming from puzzle index {start_idx}")

                    collection_downloaded = 0

                    for idx, puzzle_id in enumerate(puzzle_ids[start_idx:], start=start_idx):
                        if session_downloaded >= config.max_puzzles:
                            break

                        if config.max_per_collection and collection_downloaded >= config.max_per_collection:
                            logger.info(f"Reached per-collection limit ({config.max_per_collection})")
                            break

                        checkpoint.puzzle_index_in_collection = idx

                        # Check if already downloaded
                        if puzzle_id in known_ids:
                            stats.skipped += 1
                            checkpoint.record_skip("exists")
                            continue

                        # Log puzzle fetch with URL (at INFO per standards)
                        puzzle_url = f"https://tsumego.com/{puzzle_id}"
                        logger.puzzle_fetch(puzzle_id=puzzle_id, url=puzzle_url)

                        # --- Elapsed-aware rate limiting (start of cycle) ---
                        # t_start captures the beginning of the full fetch cycle
                        # (HTTP + validate + enrich + save).  apply_rate_limit()
                        # in the finally block subtracts this elapsed time so the
                        # total gap between request starts matches the target window.
                        t_start = time.monotonic()

                        # Fetch puzzle — rate limiting is owned by this loop,
                        # not by the client method itself.
                        try:
                            puzzle = client.fetch_puzzle(puzzle_id)

                            if puzzle is None:
                                stats.errors += 1
                                checkpoint.record_error(puzzle_id, "No SGF found")
                                logger.warning(f"No SGF found for puzzle {puzzle_id}")
                                continue

                            # Validate puzzle against core rules
                            validation = validate_sgf_puzzle(puzzle.sgf, config=config.validation_config)
                            if not validation.is_valid:
                                logger.puzzle_skip(puzzle_id=puzzle_id, reason=validation.rejection_reason)
                                stats.skipped += 1
                                continue

                            # Resolve enrichment: collection, intent
                            collection_slugs, root_comment = _enrich_puzzle(
                                puzzle, config, logger
                            )

                            # Track enrichment stats
                            if collection_slugs:
                                stats.collections_assigned += 1
                            if root_comment:
                                stats.intents_resolved += 1

                            # Save puzzle with whitelist rebuild
                            sgf_path = save_puzzle(
                                puzzle,
                                config.output_dir,
                                config.batch_size,
                                checkpoint,
                                collection_slugs=collection_slugs,
                                root_comment=root_comment,
                            )

                            # Update stats
                            stats.downloaded += 1
                            session_downloaded += 1
                            collection_downloaded += 1
                            checkpoint.record_success(config.batch_size)
                            known_ids.add(puzzle_id)

                            logger.puzzle_save(
                                puzzle_id=puzzle_id,
                                path=rel_path(sgf_path),
                                downloaded=stats.downloaded,
                                skipped=stats.skipped,
                                errors=stats.errors,
                            )

                            # Progress logging with elapsed time
                            if stats.downloaded % 10 == 0:
                                elapsed = stats.elapsed_seconds()
                                logger.progress(
                                    downloaded=stats.downloaded,
                                    skipped=stats.skipped,
                                    errors=stats.errors,
                                    rate=stats.puzzles_per_minute(),
                                    elapsed_sec=elapsed,
                                    on_disk=len(known_ids),
                                    max_target=config.max_puzzles,
                                )

                            # Periodic checkpoint save
                            if stats.downloaded % CHECKPOINT_INTERVAL == 0:
                                save_checkpoint(checkpoint, config.output_dir)

                        except TsumegoHeroClientError as e:
                            stats.errors += 1
                            checkpoint.record_error(puzzle_id, str(e))
                            logger.puzzle_error(puzzle_id=puzzle_id, error=str(e))

                        except SGFBuildError as e:
                            stats.errors += 1
                            checkpoint.record_error(puzzle_id, str(e))
                            logger.puzzle_error(puzzle_id=puzzle_id, error=str(e))

                        finally:
                            # Apply rate limit after every HTTP fetch cycle,
                            # regardless of outcome (success / skip / error).
                            # Subtracts time already spent so the inter-request
                            # gap stays within the configured window.
                            client.apply_rate_limit(elapsed=time.monotonic() - t_start)

                    # Mark collection complete
                    checkpoint.complete_collection(set_id)
                    stats.collections_processed += 1
                    logger.collection_end(
                        set_id=set_id,
                        name=collection_name,
                        downloaded=collection_downloaded,
                    )

                except TsumegoHeroClientError as e:
                    logger.error(f"Error processing collection {set_id}: {e}")

                # Save checkpoint after each collection
                save_checkpoint(checkpoint, config.output_dir)

        # Gap fill phase: find and download out-of-collection puzzles
        if config.fill_gaps:
            logger.info(
                f"Starting gap fill phase (scanning IDs 1-{config.fill_gaps_max_id})..."
            )
            gap_stats = fill_gaps_download(config)
            stats.downloaded += gap_stats.downloaded
            stats.skipped += gap_stats.skipped
            stats.errors += gap_stats.errors

        # Sort index for deterministic output
        sort_index(config.output_dir)

    except GracefulExit:
        logger.info("Graceful shutdown initiated")
        if checkpoint:
            save_checkpoint(checkpoint, config.output_dir)

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        if checkpoint:
            save_checkpoint(checkpoint, config.output_dir)
        raise

    finally:
        signal.signal(signal.SIGINT, original_handler)

        # Final checkpoint save
        if checkpoint:
            save_checkpoint(checkpoint, config.output_dir)

        # Log final stats
        logger.run_end(
            downloaded=stats.downloaded,
            skipped=stats.skipped,
            errors=stats.errors,
            duration_sec=stats.elapsed_seconds(),
        )

    return stats


def fill_gaps_download(config: DownloadConfig) -> DownloadStats:
    """Find and download puzzles that exist outside collections.

    Uses the gap finder to identify puzzle IDs in [1, config.fill_gaps_max_id]
    not yet in the local index, then fetches them via download_from_ids.
    Repeats until a full round produces zero new downloads (handles cases
    where a single gap-fill run is capped by max_puzzles).

    Args:
        config: Download configuration.  fill_gaps_max_id controls the
                ID scan range.  max_puzzles caps each individual round.

    Returns:
        Aggregated DownloadStats across all gap-fill rounds.
    """
    from .gap_finder import find_missing_ids, get_downloaded_ids_from_index

    logger = get_logger()
    total = DownloadStats()
    total.start_time = time.time()
    temp_ids_file = config.output_dir / "auto-gap-ids.txt"

    round_num = 0
    while True:
        round_num += 1

        downloaded_ids = get_downloaded_ids_from_index(config.output_dir)
        missing_ids = find_missing_ids(downloaded_ids, 1, config.fill_gaps_max_id)

        if not missing_ids:
            logger.info(f"Gap fill round {round_num}: no missing IDs in range, done")
            break

        logger.info(
            f"Gap fill round {round_num}: {len(missing_ids)} candidate IDs "
            f"(range 1-{config.fill_gaps_max_id})"
        )

        # Write candidate IDs to temp file
        with open(temp_ids_file, "w", encoding="utf-8") as f:
            for pid in missing_ids:
                f.write(f"{pid}\n")

        stats = download_from_ids(temp_ids_file, config)
        total.downloaded += stats.downloaded
        total.skipped += stats.skipped
        total.errors += stats.errors

        logger.info(
            f"Gap fill round {round_num} done: "
            f"+{stats.downloaded} downloaded, {stats.skipped} skipped/not-found"
        )

        if stats.downloaded == 0:
            logger.info("No new puzzles found in gap fill round, stopping")
            break

    # Clean up temp file
    if temp_ids_file.exists():
        temp_ids_file.unlink()

    return total


def download_from_ids(
    id_file: Path,
    config: DownloadConfig,
) -> DownloadStats:
    """Download puzzles from a list of specific IDs.

    Used for gap-filling after collection-based download.

    Args:
        id_file: Path to file containing puzzle IDs (one per line).
        config: Download configuration.

    Returns:
        Download statistics.
    """
    stats = DownloadStats()
    stats.start_time = time.time()
    logger = get_logger()

    # Read IDs from file
    if not id_file.exists():
        raise FileNotFoundError(f"ID file not found: {id_file}")

    puzzle_ids = []
    with open(id_file, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and line.isdigit():
                puzzle_ids.append(int(line))

    if not puzzle_ids:
        logger.info("No puzzle IDs found in file")
        return stats

    logger.info(f"Loaded {len(puzzle_ids)} puzzle IDs from {id_file}")

    # Set up signal handler for graceful exit
    def signal_handler(signum, frame):
        logger.warning("Received interrupt signal.")
        raise GracefulExit()

    original_handler = signal.signal(signal.SIGINT, signal_handler)

    # Create/load checkpoint for gap-fill mode
    checkpoint: THeroCheckpoint | None = None
    if config.resume:
        checkpoint = load_checkpoint(config.output_dir)
    if checkpoint is None:
        checkpoint = THeroCheckpoint()

    try:
        # Ensure output directory exists
        config.output_dir.mkdir(parents=True, exist_ok=True)
        sgf_dir = get_sgf_dir(config.output_dir)
        sgf_dir.mkdir(parents=True, exist_ok=True)

        # Load index for O(1) dedup (gap-fill mode)
        known_ids = load_puzzle_ids(config.output_dir)
        total_files = count_total_files(sgf_dir)
        if len(known_ids) < total_files:
            logger.info(f"Index stale ({len(known_ids)} < {total_files} files), rebuilding...")
            rebuild_index(config.output_dir)
            known_ids = load_puzzle_ids(config.output_dir)
        logger.info(f"Loaded index: {len(known_ids)} known puzzles")

        # Dry run: just show plan
        if config.dry_run:
            logger.info("=" * 60)
            logger.info("DRY RUN - Gap Fill Plan")
            logger.info("=" * 60)
            logger.info(f"Source file: {id_file}")
            logger.info(f"IDs to download: {len(puzzle_ids)}")
            logger.info(f"Max puzzles: {config.max_puzzles}")
            logger.info(f"ID range: {min(puzzle_ids)} - {max(puzzle_ids)}")
            logger.info("=" * 60)
            return stats

        # Initialize HTTP client
        with TsumegoHeroClient(
            base_delay=config.request_delay,
            jitter_factor=config.jitter_factor,
        ) as client:

            session_downloaded = 0

            for puzzle_id in puzzle_ids:
                if session_downloaded >= config.max_puzzles:
                    logger.info(f"Reached max puzzles limit ({config.max_puzzles})")
                    break

                # Check if already downloaded
                if puzzle_id in known_ids:
                    stats.skipped += 1
                    continue

                # Log puzzle fetch with URL (at INFO per standards)
                puzzle_url = f"https://tsumego.com/{puzzle_id}"
                logger.puzzle_fetch(puzzle_id=puzzle_id, url=puzzle_url)

                # --- Elapsed-aware rate limiting (start of cycle) ---
                t_start = time.monotonic()

                try:
                    puzzle = client.fetch_puzzle(puzzle_id)

                    if puzzle is None:
                        stats.errors += 1
                        logger.debug(f"No SGF found for puzzle {puzzle_id}")
                        continue

                    # Validate puzzle against core rules
                    validation = validate_sgf_puzzle(puzzle.sgf, config=config.validation_config)
                    if not validation.is_valid:
                        logger.puzzle_skip(puzzle_id=puzzle_id, reason=validation.rejection_reason)
                        stats.skipped += 1
                        continue

                    # Resolve enrichment: collection, intent
                    collection_slugs, root_comment = _enrich_puzzle(
                        puzzle, config, logger
                    )

                    # Track enrichment stats
                    if collection_slugs:
                        stats.collections_assigned += 1
                    if root_comment:
                        stats.intents_resolved += 1

                    # Save puzzle with whitelist rebuild
                    sgf_path = save_puzzle(
                        puzzle,
                        config.output_dir,
                        config.batch_size,
                        checkpoint,
                        collection_slugs=collection_slugs,
                        root_comment=root_comment,
                    )

                    # Update stats
                    stats.downloaded += 1
                    session_downloaded += 1
                    checkpoint.record_success(config.batch_size)
                    known_ids.add(puzzle_id)

                    logger.puzzle_save(
                        puzzle_id=puzzle_id,
                        path=rel_path(sgf_path),
                        downloaded=stats.downloaded,
                        skipped=stats.skipped,
                        errors=stats.errors,
                    )

                    # Progress logging with elapsed time
                    if stats.downloaded % 10 == 0:
                        elapsed = stats.elapsed_seconds()
                        logger.progress(
                            downloaded=stats.downloaded,
                            skipped=stats.skipped,
                            errors=stats.errors,
                            rate=stats.puzzles_per_minute(),
                            elapsed_sec=elapsed,
                            on_disk=len(known_ids),
                            max_target=config.max_puzzles,
                        )

                    # Periodic checkpoint save
                    if stats.downloaded % CHECKPOINT_INTERVAL == 0:
                        save_checkpoint(checkpoint, config.output_dir)

                except TsumegoHeroClientError as e:
                    stats.errors += 1
                    logger.warning(f"Error fetching puzzle {puzzle_id}: {e}")

                except SGFBuildError as e:
                    stats.errors += 1
                    logger.warning(f"SGF build error for puzzle {puzzle_id}: {e}")

                finally:
                    # Always apply rate limit after every HTTP fetch cycle.
                    client.apply_rate_limit(elapsed=time.monotonic() - t_start)

        # Sort index for deterministic output
        sort_index(config.output_dir)

    except GracefulExit:
        logger.info("Graceful shutdown initiated")

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise

    finally:
        signal.signal(signal.SIGINT, original_handler)

        if checkpoint:
            save_checkpoint(checkpoint, config.output_dir)

        logger.run_end(
            downloaded=stats.downloaded,
            skipped=stats.skipped,
            errors=stats.errors,
            duration_sec=stats.elapsed_seconds(),
        )

    return stats


def _print_download_plan(
    collections: dict,
    target_set_ids: list[str],
    config: DownloadConfig,
) -> None:
    """Print download plan for dry run."""
    logger = get_logger()

    logger.info("=" * 60)
    logger.info("DRY RUN - Download Plan")
    logger.info("=" * 60)
    logger.info(f"Output directory: {rel_path(config.output_dir)}")
    logger.info(f"Batch size: {config.batch_size} files")
    logger.info(f"Max puzzles: {config.max_puzzles}")
    logger.info(f"Collections to process: {len(target_set_ids)}")
    logger.info("")

    for set_id in target_set_ids[:10]:  # Show first 10
        info = collections.get(set_id, {})
        name = info.get("name", f"Collection {set_id}")
        count = info.get("puzzle_count", "?")
        logger.info(f"  - {name} ({count} puzzles)")

    if len(target_set_ids) > 10:
        logger.info(f"  ... and {len(target_set_ids) - 10} more collections")

    logger.info("")
    logger.info("Run without --dry-run to start downloading.")
    logger.info("=" * 60)
