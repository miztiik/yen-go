"""
Download orchestrator for TsumegoDragon puzzles.

Coordinates fetching, filtering, and saving puzzles with progress tracking.
"""

from __future__ import annotations

import signal
import time
from dataclasses import dataclass, field
from pathlib import Path

from tools.core.paths import rel_path
from tools.core.validation import DEFAULT_CONFIG, PuzzleValidationConfig, validate_sgf_puzzle

from .batching import DEFAULT_BATCH_SIZE, count_total_files
from .checkpoint import (
    TDragonCheckpoint,
    load_checkpoint,
    save_checkpoint,
)
from .client import DEFAULT_REQUEST_DELAY, TsumegoDragonClient
from .collections import resolve_collection_slug
from .config import CATEGORY_TO_INTENT
from .index import load_puzzle_ids, rebuild_index, sort_index
from .logging_config import get_logger
from .mappers import category_to_yt_tags, level_to_yg_slug, should_skip_category
from .models import DEFAULT_CATEGORIES, TDCategory
from .storage import save_puzzle


@dataclass
class DownloadConfig:
    """Configuration for download operation."""

    categories: list[str] | None = None  # None = use DEFAULT_CATEGORIES
    levels: list[int] = field(default_factory=lambda: [0, 1, 2])
    sample_per_category: int = 10
    max_puzzles: int = 100
    resume: bool = False
    dry_run: bool = False
    output_dir: Path = field(default_factory=lambda: Path("external-sources/tsumegodragon"))
    request_delay: float = DEFAULT_REQUEST_DELAY  # 15 seconds default
    # Exhaustive mode: download ALL puzzles without category/level filtering
    exhaustive: bool = False
    # Batching: organize files into batch-001, batch-002, etc.
    use_batching: bool = True
    batch_size: int = DEFAULT_BATCH_SIZE  # 500 files per batch
    # Start from a specific cursor (for retrying failed batches)
    start_cursor: int | None = None
    # Collection matching
    match_collections: bool = True
    # Intent resolution
    resolve_intent: bool = True
    # Validation: minimum stones override (None = use config default)
    min_stones: int | None = None

    @property
    def validation_config(self) -> PuzzleValidationConfig | None:
        """Build validation config with CLI overrides (if any)."""
        if self.min_stones is not None:
            return DEFAULT_CONFIG.merge({"min_stones": self.min_stones})
        return None


@dataclass
class DownloadStats:
    """Statistics from download operation."""

    downloaded: int = 0
    skipped: int = 0
    errors: int = 0
    categories_processed: int = 0
    collections_assigned: int = 0
    intents_resolved: int = 0
    start_time: float = 0.0

    def elapsed_seconds(self) -> float:
        if self.start_time == 0:
            return 0.0
        return time.time() - self.start_time

    def avg_seconds_per_puzzle(self) -> float:
        if self.downloaded == 0:
            return 0.0
        return self.elapsed_seconds() / self.downloaded

    def puzzles_per_minute(self) -> float:
        """Get download rate in puzzles per minute."""
        elapsed = self.elapsed_seconds()
        if elapsed == 0 or self.downloaded == 0:
            return 0.0
        return (self.downloaded / elapsed) * 60


class GracefulExit(Exception):
    """Raised on SIGINT to trigger graceful shutdown."""
    pass


def download_puzzles(config: DownloadConfig) -> DownloadStats:
    """Download puzzles according to configuration.

    Args:
        config: Download configuration.

    Returns:
        Download statistics.
    """
    # Use exhaustive mode if requested
    if config.exhaustive:
        return download_all_puzzles(config)

    logger = get_logger()
    stats = DownloadStats()
    stats.start_time = time.time()
    checkpoint: TDragonCheckpoint | None = None

    # Set up signal handler for graceful exit
    def signal_handler(signum, frame):
        logger.warning("\nReceived interrupt signal. Saving checkpoint...")
        raise GracefulExit()

    original_handler = signal.signal(signal.SIGINT, signal_handler)

    try:
        # Ensure output directory exists
        config.output_dir.mkdir(parents=True, exist_ok=True)

        # Load index for O(1) dedup
        known_ids = load_puzzle_ids(config.output_dir)
        total_files = count_total_files(config.output_dir / "sgf")
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

        # Create new checkpoint if needed
        if checkpoint is None:
            checkpoint = TDragonCheckpoint()

        with TsumegoDragonClient(request_delay=config.request_delay) as client:
            # Fetch categories
            logger.info("Fetching categories...")
            all_categories = client.fetch_categories()

            # Build category map: slug -> category
            category_map = {cat.slug: cat for cat in all_categories}

            # Determine which categories to download
            if config.categories:
                target_slugs = config.categories
            else:
                target_slugs = DEFAULT_CATEGORIES

            # Filter to only categories that exist
            valid_slugs = [s for s in target_slugs if s in category_map]
            invalid_slugs = [s for s in target_slugs if s not in category_map]

            if invalid_slugs:
                logger.warning(f"Unknown categories (skipping): {invalid_slugs}")
                logger.info(f"Available categories: {list(category_map.keys())}")

            if not valid_slugs:
                logger.error("No valid categories to download")
                return stats

            # Skip already-completed categories if resuming
            if checkpoint.categories_completed:
                valid_slugs = [
                    s for s in valid_slugs
                    if s not in checkpoint.categories_completed
                ]
                logger.info(
                    f"Resuming: {len(checkpoint.categories_completed)} categories already complete"
                )

            # Dry run: just print plan
            if config.dry_run:
                _print_download_plan(
                    valid_slugs, category_map, config.levels,
                    config.sample_per_category, config.max_puzzles
                )
                return stats

            # Download puzzles from each category
            for category_slug in valid_slugs:
                if stats.downloaded >= config.max_puzzles:
                    logger.info(f"Reached max puzzles limit ({config.max_puzzles})")
                    break

                category = category_map[category_slug]
                checkpoint.current_category = category_slug

                logger.info(f"\n{'='*60}")
                logger.info(f"Category: {category.name} ({category_slug})")
                logger.info(f"Total puzzles: {category.tsumego_count}")
                logger.info(f"{'='*60}")

                category_downloaded = 0

                # Download for each level
                for level in config.levels:
                    if category_downloaded >= config.sample_per_category:
                        break
                    if stats.downloaded >= config.max_puzzles:
                        break

                    # Resume from cursor if in progress
                    cursor = 0
                    if (checkpoint.current_category == category_slug and
                        checkpoint.current_cursor > 0):
                        cursor = checkpoint.current_cursor
                        logger.info(f"Resuming from cursor {cursor}")

                    remaining = config.sample_per_category - category_downloaded
                    puzzles_to_fetch = min(remaining, config.max_puzzles - stats.downloaded)

                    # Fetch puzzles for this category and level
                    while puzzles_to_fetch > 0:
                        try:
                            response = client.fetch_puzzles(
                                category_id=category.id,
                                level=level,
                                cursor=cursor,
                                limit=min(puzzles_to_fetch, 10),  # Small batches
                            )
                        except Exception as e:
                            logger.error(f"Failed to fetch puzzles: {e}")
                            checkpoint.errors.append(str(e))
                            stats.errors += 1
                            break

                        if not response.results:
                            logger.debug(f"No more puzzles at level {level}")
                            break

                        for puzzle in response.results:
                            if category_downloaded >= config.sample_per_category:
                                break
                            if stats.downloaded >= config.max_puzzles:
                                break

                            # Check if already downloaded
                            if puzzle.id in known_ids:
                                logger.debug(f"Skipping existing: {puzzle.id}")
                                stats.skipped += 1
                                checkpoint.puzzles_skipped += 1
                                continue

                            # Validate SGF content
                            if not puzzle.sgf_text or len(puzzle.sgf_text) < 10:
                                logger.warning(f"Skipping puzzle {puzzle.id}: no SGF content")
                                stats.skipped += 1
                                checkpoint.puzzles_skipped += 1
                                continue

                            # Validate puzzle against core rules
                            validation = validate_sgf_puzzle(puzzle.sgf_text, config=config.validation_config)
                            if not validation.is_valid:
                                logger.warning(f"Skipping puzzle {puzzle.id}: {validation.rejection_reason}")
                                stats.skipped += 1
                                checkpoint.puzzles_skipped += 1
                                continue

                            # Resolve collection and intent
                            collection_slug = resolve_collection_slug(category_slug) if config.match_collections else None
                            collection_slugs = [collection_slug] if collection_slug else None
                            root_comment = CATEGORY_TO_INTENT.get(category_slug) if config.resolve_intent else None

                            # Log collection and intent resolution
                            logger.collection_match(
                                puzzle_id=puzzle.id,
                                source_name=category_slug,
                                matched_slug=collection_slug,
                            )
                            if config.resolve_intent:
                                logger.intent_match(
                                    puzzle_id=puzzle.id,
                                    description_snippet=category_slug,
                                    matched_slug=root_comment,
                                    confidence=1.0 if root_comment else 0.0,
                                    tier="static_mapping" if root_comment else "",
                                )

                            # Track enrichment stats
                            if collection_slugs:
                                stats.collections_assigned += 1
                            if root_comment:
                                stats.intents_resolved += 1

                            # Save puzzle (with YG/YT enrichment)
                            try:
                                save_puzzle(
                                    puzzle, category_slug, config.output_dir,
                                    batch_size=config.batch_size,
                                    checkpoint=checkpoint,
                                    collection_slugs=collection_slugs,
                                    root_comment=root_comment,
                                )
                                stats.downloaded += 1
                                category_downloaded += 1
                                checkpoint.puzzles_downloaded += 1
                                checkpoint.record_success(config.batch_size)
                                known_ids.add(puzzle.id)

                                logger.info(
                                    f"[{stats.downloaded}/{config.max_puzzles}] "
                                    f"Downloaded: {puzzle.id} (Level {level}, ELO {puzzle.elo})"
                                )

                                # Progress logging every 10 puzzles
                                if stats.downloaded % 10 == 0:
                                    logger.progress(
                                        downloaded=stats.downloaded,
                                        skipped=stats.skipped,
                                        errors=stats.errors,
                                        elapsed_sec=stats.elapsed_seconds(),
                                        rate=stats.puzzles_per_minute(),
                                        on_disk=len(known_ids),
                                        max_target=config.max_puzzles,
                                    )

                            except Exception as e:
                                logger.error(f"Failed to save puzzle {puzzle.id}: {e}")
                                checkpoint.errors.append(f"{puzzle.id}: {e}")
                                stats.errors += 1

                            # Save checkpoint after each puzzle
                            checkpoint.current_cursor = cursor + 1
                            save_checkpoint(checkpoint, config.output_dir)

                        # Move cursor forward
                        cursor += len(response.results)
                        puzzles_to_fetch -= len(response.results)

                        # Check if more results available
                        if response.remaining == 0:
                            break

                # Mark category complete
                checkpoint.categories_completed.append(category_slug)
                checkpoint.current_category = None
                checkpoint.current_cursor = 0
                save_checkpoint(checkpoint, config.output_dir)

                stats.categories_processed += 1
                logger.info(f"Completed category: {category_slug} ({category_downloaded} puzzles)")

        # Sort index for deterministic output
        sort_index(config.output_dir)

    except GracefulExit:
        # Save final checkpoint on interrupt
        if checkpoint:
            save_checkpoint(checkpoint, config.output_dir)
        logger.info("Download interrupted. Checkpoint saved.")

    finally:
        # Restore original signal handler
        signal.signal(signal.SIGINT, original_handler)

    return stats


def download_all_puzzles(config: DownloadConfig) -> DownloadStats:
    """Download ALL puzzles without category/level filtering.

    This is the exhaustive mode that ensures we get every puzzle in the database,
    including those without category assignments or level classifications.

    Args:
        config: Download configuration.

    Returns:
        Download statistics.
    """
    logger = get_logger()
    stats = DownloadStats()
    stats.start_time = time.time()
    checkpoint: TDragonCheckpoint | None = None

    def signal_handler(signum, frame):
        logger.warning("\nReceived interrupt signal. Saving checkpoint...")
        raise GracefulExit()

    original_handler = signal.signal(signal.SIGINT, signal_handler)

    try:
        config.output_dir.mkdir(parents=True, exist_ok=True)

        # Load index for O(1) dedup
        known_ids = load_puzzle_ids(config.output_dir)
        total_files = count_total_files(config.output_dir / "sgf")
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
                logger.checkpoint_load(
                    cursor=checkpoint.current_cursor,
                    downloaded=checkpoint.puzzles_downloaded,
                )

        if checkpoint is None:
            checkpoint = TDragonCheckpoint()

        with TsumegoDragonClient(request_delay=config.request_delay) as client:
            # Build category ID -> slug map for organizing files
            logger.info("Fetching categories for organization...")
            all_categories = client.fetch_categories()
            category_id_to_slug = {cat.id: cat.slug for cat in all_categories}

            # Get initial count
            logger.info("Fetching total puzzle count...")
            initial_response = client.fetch_puzzles(limit=1, cursor=0)
            total_puzzles = initial_response.remaining + 1

            logger.info(f"\n{'='*60}")
            logger.info(f"EXHAUSTIVE MODE: Downloading ALL {total_puzzles} puzzles")
            logger.info(f"Max limit: {config.max_puzzles}")
            logger.info(f"Batching: {'enabled' if config.use_batching else 'disabled'} (max {config.batch_size} per dir)")
            logger.info(f"Request delay: {config.request_delay}s")
            logger.info(f"{'='*60}\n")

            if config.dry_run:
                estimated_time = min(total_puzzles, config.max_puzzles) * config.request_delay / 3600
                print(f"\nDRY RUN - Would download up to {min(total_puzzles, config.max_puzzles)} puzzles")
                print(f"Estimated time: ~{estimated_time:.1f} hours ({config.request_delay}s delay)")
                return stats

            # Resume from checkpoint cursor if available, or use start_cursor if specified
            if config.start_cursor is not None:
                cursor = config.start_cursor
                logger.info(f"Starting from specified cursor {cursor}")
            elif checkpoint.current_cursor > 0:
                cursor = checkpoint.current_cursor
                logger.info(f"Resuming from checkpoint cursor {cursor}")
            else:
                cursor = 0

            api_batch_size = 100  # Max allowed by API

            while stats.downloaded < config.max_puzzles:
                # Log API request
                api_url = f"https://tsumegodragon.com/api/1.1/obj/tsumego?limit={api_batch_size}&cursor={cursor}"
                logger.api_request(url=api_url, description=f"cursor={cursor} limit={api_batch_size}")

                try:
                    response = client.fetch_puzzles(
                        category_id=None,  # No filter
                        level=None,  # No filter
                        cursor=cursor,
                        limit=api_batch_size,
                    )
                    logger.api_response(count=len(response.results), remaining=response.remaining)
                except Exception as e:
                    logger.api_error(url=api_url, error=str(e))
                    checkpoint.errors.append(f"cursor={cursor}: {e}")
                    stats.errors += 1
                    # Try to continue with next batch
                    cursor += api_batch_size
                    continue

                if not response.results:
                    logger.info("No more puzzles to fetch")
                    break

                for puzzle in response.results:
                    if stats.downloaded >= config.max_puzzles:
                        break

                    # Determine category slug for file organization
                    cat_id = getattr(puzzle, 'category', None)
                    category_slug = category_id_to_slug.get(cat_id, 'uncategorized') if cat_id else 'uncategorized'
                    level = getattr(puzzle, 'level_sort_number', None)
                    elo = getattr(puzzle, 'elo', 0) or 0

                    # Log puzzle fetched
                    logger.puzzle_fetch(puzzle_id=puzzle.id, url=f"https://tsumegodragon.com/api/1.1/obj/tsumego/{puzzle.id}", category=category_slug)

                    # Skip non-tsumego categories (e.g., endgame-yose, opening-basics)
                    if should_skip_category(category_slug):
                        logger.puzzle_skip(puzzle_id=puzzle.id, reason=f"non-tsumego category: {category_slug}")
                        stats.skipped += 1
                        checkpoint.puzzles_skipped += 1
                        continue

                    # Check if already downloaded
                    if puzzle.id in known_ids:
                        logger.puzzle_skip(puzzle_id=puzzle.id, reason="already exists")
                        stats.skipped += 1
                        checkpoint.puzzles_skipped += 1
                        continue

                    # Validate SGF content
                    if not puzzle.sgf_text or len(puzzle.sgf_text) < 10:
                        logger.puzzle_skip(puzzle_id=puzzle.id, reason="no SGF content")
                        stats.skipped += 1
                        checkpoint.puzzles_skipped += 1
                        continue

                    # Validate puzzle against core rules
                    validation = validate_sgf_puzzle(puzzle.sgf_text, config=config.validation_config)
                    if not validation.is_valid:
                        logger.puzzle_skip(puzzle_id=puzzle.id, reason=validation.rejection_reason)
                        stats.skipped += 1
                        checkpoint.puzzles_skipped += 1
                        continue

                    # Get enrichment info for logging
                    yg_slug = level_to_yg_slug(getattr(puzzle, 'level', None))
                    yt_tags = category_to_yt_tags(category_slug) or []
                    logger.puzzle_enrich(puzzle_id=puzzle.id, level=yg_slug, tags=yt_tags)

                    # Resolve collection and intent
                    collection_slug = resolve_collection_slug(category_slug) if config.match_collections else None
                    collection_slugs = [collection_slug] if collection_slug else None
                    root_comment = CATEGORY_TO_INTENT.get(category_slug) if config.resolve_intent else None

                    # Log collection and intent resolution
                    logger.collection_match(
                        puzzle_id=puzzle.id,
                        source_name=category_slug,
                        matched_slug=collection_slug,
                    )
                    if config.resolve_intent:
                        logger.intent_match(
                            puzzle_id=puzzle.id,
                            description_snippet=category_slug,
                            matched_slug=root_comment,
                            confidence=1.0 if root_comment else 0.0,
                            tier="static_mapping" if root_comment else "",
                        )

                    # Track enrichment stats
                    if collection_slugs:
                        stats.collections_assigned += 1
                    if root_comment:
                        stats.intents_resolved += 1

                    # Save puzzle (with YG/YT enrichment)
                    try:
                        sgf_path = save_puzzle(
                            puzzle, category_slug, config.output_dir,
                            batch_size=config.batch_size,
                            checkpoint=checkpoint,
                            collection_slugs=collection_slugs,
                            root_comment=root_comment,
                        )
                        stats.downloaded += 1
                        checkpoint.puzzles_downloaded += 1
                        checkpoint.record_success(config.batch_size)
                        known_ids.add(puzzle.id)

                        logger.puzzle_save(
                            puzzle_id=puzzle.id,
                            path=rel_path(sgf_path),
                            category=category_slug,
                            puzzle_level=level,
                            elo=elo,
                            index=stats.downloaded,
                            max_puzzles=config.max_puzzles,
                        )

                        # Progress logging every 10 puzzles
                        if stats.downloaded % 10 == 0:
                            logger.progress(
                                downloaded=stats.downloaded,
                                skipped=stats.skipped,
                                errors=stats.errors,
                                elapsed_sec=stats.elapsed_seconds(),
                                rate=stats.puzzles_per_minute(),
                                on_disk=len(known_ids),
                                max_target=config.max_puzzles,
                            )
                    except Exception as e:
                        logger.puzzle_error(puzzle_id=puzzle.id, error=str(e))
                        checkpoint.errors.append(f"{puzzle.id}: {e}")
                        stats.errors += 1

                    # Update checkpoint
                    checkpoint.current_cursor = cursor
                    save_checkpoint(checkpoint, config.output_dir)
                    logger.checkpoint_save(cursor=cursor, downloaded=stats.downloaded)

                cursor += len(response.results)

                if response.remaining == 0:
                    logger.info("Reached end of database")
                    break

            # Sort index for deterministic output
            sort_index(config.output_dir)

            logger.info("\nExhaustive download complete!")

    except GracefulExit:
        if checkpoint:
            save_checkpoint(checkpoint, config.output_dir)
        logger.info("Download interrupted. Checkpoint saved.")

    finally:
        signal.signal(signal.SIGINT, original_handler)

    return stats


def _print_download_plan(
    slugs: list[str],
    category_map: dict[str, TDCategory],
    levels: list[int],
    sample_per_category: int,
    max_puzzles: int,
) -> None:
    """Print download plan without executing."""
    print("\n" + "="*60)
    print("DRY RUN - Download Plan")
    print("="*60)
    print(f"\nCategories to download: {len(slugs)}")
    print(f"Levels: {levels}")
    print(f"Sample per category: {sample_per_category}")
    print(f"Max total puzzles: {max_puzzles}")
    print("\nCategories:")

    total_available = 0
    for slug in slugs:
        cat = category_map[slug]
        level_counts = [
            getattr(cat, f"level_{lvl}_count", 0) for lvl in levels
        ]
        available = sum(level_counts)
        total_available += available
        print(f"  - {cat.name} ({slug}): {available} puzzles available at levels {levels}")

    estimated = min(total_available, len(slugs) * sample_per_category, max_puzzles)
    print(f"\nEstimated downloads: ~{estimated} puzzles")
    print(f"Estimated time: ~{estimated * 30 / 60:.1f} minutes (30s delay per request)")
    print("\n" + "="*60)
