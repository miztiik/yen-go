"""
Download orchestrator for BlackToPlay (BTP) puzzles.

Coordinates fetching, conversion, and saving puzzles with progress tracking,
checkpointing, and resume support. Iterates over puzzle types (Classic, AI,
Endgame), fetches puzzle lists, and downloads each puzzle individually.
"""

from __future__ import annotations

import random
import signal
import time
from dataclasses import dataclass, field
from pathlib import Path

from tools.core.validation import (
    DEFAULT_CONFIG as DEFAULT_VALIDATION_CONFIG,
)
from tools.core.validation import (
    PuzzleValidationConfig,
    validate_sgf_puzzle,
)

from .btp_checkpoint import (
    BTPCheckpoint,
    clear_checkpoint,
    load_checkpoint,
    save_checkpoint,
)
from .client import BTPClient, BTPClientError
from .config import (
    ALL_PUZZLE_TYPES,
    DEFAULT_BATCH_SIZE,
    DEFAULT_PUZZLE_DELAY,
    DELAY_JITTER_FACTOR,
    PUZZLE_TYPE_NAMES,
    get_output_dir,
    get_sgf_dir,
)
from .index import sort_index
from .logging_config import get_logger
from .sgf_converter import convert_puzzle_to_sgf
from .storage import load_known_ids, save_puzzle


@dataclass
class DownloadConfig:
    """Configuration for BTP download operation."""

    max_puzzles: int = 10000
    resume: bool = False
    dry_run: bool = False
    output_dir: Path = field(default_factory=lambda: get_output_dir())
    puzzle_types: list[int] = field(default_factory=lambda: list(ALL_PUZZLE_TYPES))
    puzzle_delay: float = DEFAULT_PUZZLE_DELAY
    batch_size: int = DEFAULT_BATCH_SIZE
    use_cache: bool = True  # Use cached puzzle list as fallback
    match_collections: bool = True  # Enable YL[] collection matching
    resolve_intent: bool = True  # Enable C[] intent resolution
    min_stones: int | None = None  # Override min_stones validation (None = use config default)

    @property
    def validation_config(self) -> PuzzleValidationConfig:
        """Build validation config, applying CLI overrides."""
        if self.min_stones is not None:
            return DEFAULT_VALIDATION_CONFIG.merge({"min_stones": self.min_stones})
        return DEFAULT_VALIDATION_CONFIG


@dataclass
class DownloadStats:
    """Statistics from download operation."""

    downloaded: int = 0
    skipped: int = 0
    errors: int = 0
    start_time: float = 0.0

    def elapsed_seconds(self) -> float:
        if self.start_time == 0:
            return 0.0
        return time.time() - self.start_time

    def avg_seconds_per_puzzle(self) -> float:
        if self.downloaded == 0:
            return 0.0
        return self.elapsed_seconds() / self.downloaded


class GracefulExit(Exception):
    """Raised on SIGINT to trigger graceful shutdown."""

    pass


def download_puzzles(config: DownloadConfig) -> DownloadStats:
    """Download puzzles from BlackToPlay.com.

    Iterates over requested puzzle types, fetches puzzle lists, and
    downloads each puzzle. Supports checkpointing for resume.

    Args:
        config: Download configuration.

    Returns:
        Download statistics.
    """
    stats = DownloadStats()
    stats.start_time = time.time()
    checkpoint: BTPCheckpoint | None = None
    logger = get_logger()

    # Set up signal handler for graceful exit
    def signal_handler(signum, frame):
        logger.warning("\nReceived interrupt signal. Saving checkpoint...")
        raise GracefulExit()

    original_handler = signal.signal(signal.SIGINT, signal_handler)

    try:
        # Ensure output directories exist
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
                logger.info(
                    "Resuming from checkpoint: %d downloaded, type %d index %d, batch %d",
                    stats.downloaded,
                    checkpoint.current_type,
                    checkpoint.current_type_index,
                    checkpoint.current_batch,
                )

        if checkpoint is None:
            checkpoint = BTPCheckpoint()

        # Load known IDs for skip detection
        known_ids = load_known_ids(config.output_dir)
        if known_ids:
            logger.info("Found %d indexed puzzles", len(known_ids))

        type_name_str = ", ".join(
            PUZZLE_TYPE_NAMES.get(t, str(t)) for t in config.puzzle_types
        )
        logger.run_start(
            max_puzzles=config.max_puzzles,
            resume=config.resume,
            output_dir=str(config.output_dir),
            puzzle_types=type_name_str,
        )

        with BTPClient() as client:
            for puzzle_type in config.puzzle_types:
                if session_downloaded >= config.max_puzzles:
                    logger.info("Reached max puzzles limit (%d)", config.max_puzzles)
                    break

                # Skip already-completed types on resume
                if config.resume and puzzle_type in checkpoint.completed_types:
                    logger.info(
                        "Skipping completed type: %s",
                        PUZZLE_TYPE_NAMES.get(puzzle_type, str(puzzle_type)),
                    )
                    continue

                type_downloaded, type_skipped, type_errors = _process_type(
                    client=client,
                    puzzle_type=puzzle_type,
                    config=config,
                    checkpoint=checkpoint,
                    known_ids=known_ids,
                    session_limit=config.max_puzzles - session_downloaded,
                )

                session_downloaded += type_downloaded
                stats.downloaded += type_downloaded
                stats.skipped += type_skipped
                stats.errors += type_errors

                # Mark type as completed
                checkpoint.completed_types.append(puzzle_type)
                checkpoint.current_type_index = 0
                checkpoint.puzzles_downloaded = stats.downloaded
                checkpoint.puzzles_skipped = stats.skipped
                checkpoint.puzzles_errors = stats.errors
                save_checkpoint(checkpoint, config.output_dir)

    except GracefulExit:
        logger.info("Graceful shutdown — saving checkpoint")
        if checkpoint:
            checkpoint.puzzles_downloaded = stats.downloaded
            checkpoint.puzzles_skipped = stats.skipped
            checkpoint.puzzles_errors = stats.errors
            save_checkpoint(checkpoint, config.output_dir)

    except Exception:
        logger.exception("Unexpected error during download")
        if checkpoint:
            checkpoint.puzzles_downloaded = stats.downloaded
            checkpoint.puzzles_skipped = stats.skipped
            checkpoint.puzzles_errors = stats.errors
            save_checkpoint(checkpoint, config.output_dir)
        raise

    finally:
        signal.signal(signal.SIGINT, original_handler)

    # Sort index for readability and clean diffs
    if not config.dry_run:
        sorted_count = sort_index(config.output_dir)
        if sorted_count > 0:
            logger.info("Sorted index: %d entries", sorted_count)

    # Clear checkpoint on successful completion
    if not config.dry_run:
        all_types_done = all(
            t in (checkpoint.completed_types if checkpoint else [])
            for t in config.puzzle_types
        )
        if all_types_done:
            clear_checkpoint(config.output_dir)
            logger.info("All types complete — checkpoint cleared")

    logger.run_end(
        downloaded=stats.downloaded,
        skipped=stats.skipped,
        errors=stats.errors,
        duration_sec=stats.elapsed_seconds(),
    )

    return stats


def _process_type(
    client: BTPClient,
    puzzle_type: int,
    config: DownloadConfig,
    checkpoint: BTPCheckpoint,
    known_ids: set[str],
    session_limit: int,
) -> tuple[int, int, int]:
    """Process all puzzles of a given type.

    Returns:
        (downloaded, skipped, errors) counts.
    """
    logger = get_logger()
    type_name = PUZZLE_TYPE_NAMES.get(puzzle_type, str(puzzle_type))

    # Fetch puzzle list
    puzzle_list = client.list_puzzles(puzzle_type, use_cache=config.use_cache)
    if not puzzle_list:
        logger.warning("No puzzles found for type %s", type_name)
        return 0, 0, 0

    logger.type_start(puzzle_type, type_name, len(puzzle_list))

    downloaded = 0
    skipped = 0
    errors = 0

    # Resume from checkpoint index
    start_idx = 0
    if config.resume and checkpoint.current_type == puzzle_type:
        start_idx = checkpoint.current_type_index

    for idx in range(start_idx, len(puzzle_list)):
        if downloaded >= session_limit:
            break

        item = puzzle_list[idx]
        puzzle_stem = f"btp-{item.puzzle_id}"

        # Skip if already downloaded
        if puzzle_stem in known_ids:
            logger.puzzle_skip(item.puzzle_id, "already_downloaded")
            skipped += 1
            continue

        # Fetch and convert
        try:
            puzzle = client.fetch_puzzle(item.puzzle_id, puzzle_type)

            if not puzzle.position_hash:
                logger.puzzle_skip(item.puzzle_id, "no_position_hash")
                skipped += 1
                continue

            sgf_content = convert_puzzle_to_sgf(
                puzzle,
                match_collections=config.match_collections,
                resolve_intent=config.resolve_intent,
            )

            # Validate SGF: board size, stone count, solution depth
            validation = validate_sgf_puzzle(sgf_content, config=config.validation_config)
            if not validation.is_valid:
                logger.puzzle_skip(item.puzzle_id, validation.rejection_reason or "validation_failed")
                skipped += 1
                continue

            save_puzzle(
                puzzle=puzzle,
                sgf_content=sgf_content,
                output_dir=config.output_dir,
                checkpoint=checkpoint,
                batch_size=config.batch_size,
                dry_run=config.dry_run,
            )

            known_ids.add(puzzle_stem)
            downloaded += 1

            # Save checkpoint after EVERY successful file save (per tool-development-standards.md)
            checkpoint.current_type = puzzle_type
            checkpoint.current_type_index = idx + 1
            checkpoint.puzzles_downloaded += 1
            save_checkpoint(checkpoint, config.output_dir)

            if downloaded % 50 == 0:
                logger.progress(
                    downloaded=downloaded,
                    skipped=skipped,
                    errors=errors,
                )

        except BTPClientError as e:
            logger.warning("Failed to fetch puzzle %s: %s", item.puzzle_id, e)
            errors += 1

        except Exception as e:
            logger.warning(
                "Error processing puzzle %s: %s", item.puzzle_id, e
            )
            errors += 1

        # Rate limit with jitter
        if config.puzzle_delay > 0:
            delay = config.puzzle_delay * (1 + random.uniform(-DELAY_JITTER_FACTOR, DELAY_JITTER_FACTOR))
            time.sleep(delay)

    logger.type_end(puzzle_type, type_name, downloaded, skipped, errors)
    return downloaded, skipped, errors
