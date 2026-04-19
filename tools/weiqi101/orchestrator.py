"""
Main download orchestrator for 101weiqi puzzles.

Coordinates fetching, extraction, validation, enrichment, and saving
across different source modes (daily, puzzle-by-id).
"""

from __future__ import annotations

import logging
import signal
import time
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

from tools.core.chinese_translator import translate_chinese_text
from tools.core.paths import rel_path
from tools.core.rate_limit import RateLimiter

from . import _local_collections_mapping, _local_intent_mapping
from .checkpoint import (
    WeiQiCheckpoint,
    load_checkpoint,
    save_checkpoint,
)
from .client import WeiQiClient
from .complexity import compute_complexity
from .config import (
    CONSECUTIVE_EXTRACTION_FAILURE_LIMIT,
    CONSECUTIVE_FAILURE_LIMIT,
    COOLDOWN_DURATION,
    COOLDOWN_INTERVAL,
    DAILY_PUZZLE_COUNT,
    DEFAULT_BATCH_SIZE,
    DEFAULT_PUZZLE_DELAY,
    DELAY_JITTER_FACTOR,
    get_sgf_dir,
)
from .extractor import extract_qqdata, is_login_page, is_rate_limited_page
from .index import load_puzzle_ids, sort_index
from .models import PuzzleData
from .storage import save_puzzle
from .validator import validate_puzzle

logger = logging.getLogger("101weiqi.orchestrator")


@dataclass
class DownloadConfig:
    """Configuration for a download run."""

    # Source mode
    source_mode: str = "daily"  # "daily" or "puzzle"

    # Daily mode options
    start_date: date | None = None
    end_date: date | None = None

    # Puzzle mode options
    start_id: int | None = None
    end_id: int | None = None
    puzzle_ids: list[int] | None = None

    # General options
    output_dir: Path = Path(".")
    batch_size: int = DEFAULT_BATCH_SIZE
    puzzle_delay: float = DEFAULT_PUZZLE_DELAY
    resume: bool = False
    dry_run: bool = False
    max_puzzles: int = 10000

    # Authentication
    cookies: dict[str, str] | None = None

    # Enrichment options
    match_collections: bool = True
    resolve_intent: bool = True

    # Chapter-aware book download: puzzle_id → (chapter_number_str, position_in_chapter)
    # Populated when --book-id discovers chapters. Used by _process_html to emit
    # slug:CHAPTER/POSITION collection entries instead of bare slugs.
    chapter_sequences: dict[int, tuple[str, int]] | None = None
    book_collection_slug: str | None = None


@dataclass
class DownloadStats:
    """Statistics from a download run."""

    downloaded: int = 0
    skipped: int = 0
    errors: int = 0
    not_found: int = 0
    start_time: float = field(default_factory=time.time)

    @property
    def total_processed(self) -> int:
        return self.downloaded + self.skipped + self.errors + self.not_found


def download_puzzles(config: DownloadConfig) -> DownloadStats:
    """Main entry point for downloading puzzles.

    Routes to the appropriate source mode handler.

    Args:
        config: Download configuration.

    Returns:
        Download statistics.
    """
    if config.source_mode == "daily":
        return _download_daily(config)
    elif config.source_mode == "puzzle":
        return _download_by_id(config)
    else:
        logger.error(f"Unknown source mode: {config.source_mode}")
        return DownloadStats()


def _download_daily(config: DownloadConfig) -> DownloadStats:
    """Download daily puzzles for a date range.

    Iterates through each date and puzzle number (1-8),
    fetching and saving each puzzle.
    """
    stats = DownloadStats()
    stop_requested = False

    def _handle_sigint(sig: int, frame: object) -> None:
        nonlocal stop_requested
        stop_requested = True
        logger.warning("Interrupt received, finishing current puzzle...")

    prev_handler = signal.signal(signal.SIGINT, _handle_sigint)

    try:
        return _run_daily_download(config, stats, lambda: stop_requested)
    finally:
        signal.signal(signal.SIGINT, prev_handler)


def _run_daily_download(
    config: DownloadConfig,
    stats: DownloadStats,
    should_stop: object,
) -> DownloadStats:
    """Inner daily download loop with checkpoint support."""
    if not config.start_date or not config.end_date:
        logger.error("Daily mode requires --start-date and --end-date")
        return stats

    output_dir = config.output_dir
    sgf_dir = get_sgf_dir(output_dir)
    sgf_dir.mkdir(parents=True, exist_ok=True)

    # Load checkpoint for resume
    checkpoint: WeiQiCheckpoint | None = None
    if config.resume:
        checkpoint = load_checkpoint(output_dir)
        if checkpoint and checkpoint.source_mode == "daily":
            logger.info(
                f"Resuming from date={checkpoint.last_date}, "
                f"puzzle={checkpoint.last_puzzle_num}, "
                f"downloaded={checkpoint.puzzles_downloaded}"
            )

    if checkpoint is None:
        checkpoint = WeiQiCheckpoint(source_mode="daily")

    # Load known IDs for dedup
    known_ids = load_puzzle_ids(output_dir)
    logger.info(f"Loaded {len(known_ids)} known puzzle IDs from index")

    rate_limiter = RateLimiter(
        min_delay=config.puzzle_delay,
        jitter_factor=DELAY_JITTER_FACTOR,
    )

    with WeiQiClient(cookies=config.cookies) as client:
        current_date = config.start_date

        # Skip to resume point if applicable
        if config.resume and checkpoint.last_date:
            resume_date = date.fromisoformat(checkpoint.last_date)
            if resume_date > current_date:
                current_date = resume_date
                logger.info(f"Skipping to resume date: {current_date}")

        while current_date <= config.end_date:
            if should_stop():
                logger.info("Stop requested, saving checkpoint")
                save_checkpoint(checkpoint, output_dir)
                break

            if stats.downloaded >= config.max_puzzles:
                logger.info(f"Reached max puzzles limit ({config.max_puzzles})")
                break

            start_num = 1
            # Skip to resume puzzle number on the resume date
            if (
                config.resume
                and checkpoint.last_date == current_date.isoformat()
                and checkpoint.last_puzzle_num > 0
            ):
                start_num = checkpoint.last_puzzle_num + 1

            consecutive_failures = 0

            total_for_date = DAILY_PUZZLE_COUNT - start_num + 1

            for puzzle_num in range(start_num, DAILY_PUZZLE_COUNT + 1):
                if should_stop() or stats.downloaded >= config.max_puzzles:
                    break

                idx = puzzle_num - start_num + 1
                logger.info(
                    f"[{current_date}] puzzle {idx}/{total_for_date} "
                    f"(p{puzzle_num}) [saved={stats.downloaded} skip={stats.skipped} err={stats.errors}]"
                )

                # Rate limiting (processing-aware)
                wait_time = rate_limiter.wait_if_needed()
                if wait_time > 0:
                    logger.info(f"WAIT {wait_time:.1f}s (rate_limit)")

                result = _process_daily_puzzle(
                    client=client,
                    current_date=current_date,
                    puzzle_num=puzzle_num,
                    output_dir=output_dir,
                    config=config,
                    checkpoint=checkpoint,
                    known_ids=known_ids,
                    stats=stats,
                )

                if result == "rate_limited":
                    logger.error(
                        "CAPTCHA rate-limit detected. Aborting. "
                        "Solve the CAPTCHA in a browser, then re-run with --resume."
                    )
                    save_checkpoint(checkpoint, output_dir)
                    return stats

                if result == "error":
                    consecutive_failures += 1
                    if consecutive_failures >= CONSECUTIVE_FAILURE_LIMIT:
                        logger.warning(
                            f"Stopping date {current_date}: "
                            f"{consecutive_failures} consecutive failures"
                        )
                        break
                else:
                    consecutive_failures = 0

                # Update checkpoint
                checkpoint.last_date = current_date.isoformat()
                checkpoint.last_puzzle_num = puzzle_num

                # Save checkpoint every 10 puzzles
                if stats.total_processed % 10 == 0:
                    save_checkpoint(checkpoint, output_dir)

            current_date += timedelta(days=1)

    # Final checkpoint + sort index
    save_checkpoint(checkpoint, output_dir)
    sort_index(output_dir)

    return stats


def _process_daily_puzzle(
    client: WeiQiClient,
    current_date: date,
    puzzle_num: int,
    output_dir: Path,
    config: DownloadConfig,
    checkpoint: WeiQiCheckpoint,
    known_ids: set[int],
    stats: DownloadStats,
) -> str:
    """Process a single daily puzzle.

    Returns:
        "ok", "skipped", or "error"
    """
    date_str = current_date.isoformat()
    ref = f"daily/{date_str}/p{puzzle_num}"

    if config.dry_run:
        logger.info(f"[DRY RUN] Would fetch {ref}")
        stats.skipped += 1
        return "skipped"

    # Fetch HTML
    html = client.fetch_daily_puzzle(
        year=current_date.year,
        month=current_date.month,
        day=current_date.day,
        num=puzzle_num,
    )

    if html is None:
        stats.not_found += 1
        return "error"

    return _process_html(
        html=html,
        ref=ref,
        output_dir=output_dir,
        config=config,
        checkpoint=checkpoint,
        known_ids=known_ids,
        stats=stats,
    )


def _download_by_id(config: DownloadConfig) -> DownloadStats:
    """Download puzzles by numeric ID range or specific IDs."""
    stats = DownloadStats()
    stop_requested = False

    def _handle_sigint(sig: int, frame: object) -> None:
        nonlocal stop_requested
        stop_requested = True
        logger.warning("Interrupt received, finishing current puzzle...")

    prev_handler = signal.signal(signal.SIGINT, _handle_sigint)

    try:
        return _run_id_download(config, stats, lambda: stop_requested)
    finally:
        signal.signal(signal.SIGINT, prev_handler)


def _run_id_download(
    config: DownloadConfig,
    stats: DownloadStats,
    should_stop: object,
) -> DownloadStats:
    """Inner ID-based download loop."""
    output_dir = config.output_dir
    sgf_dir = get_sgf_dir(output_dir)
    sgf_dir.mkdir(parents=True, exist_ok=True)

    # Build puzzle ID list
    if config.puzzle_ids:
        ids = config.puzzle_ids
    elif config.start_id is not None and config.end_id is not None:
        ids = list(range(config.start_id, config.end_id + 1))
    else:
        logger.error("Puzzle mode requires --ids or --start-id/--end-id")
        return stats

    # Load checkpoint for resume
    checkpoint: WeiQiCheckpoint | None = None
    if config.resume:
        checkpoint = load_checkpoint(output_dir)
        if checkpoint and checkpoint.source_mode == "puzzle":
            logger.info(
                f"Resuming from puzzle_id={checkpoint.last_puzzle_id}, "
                f"downloaded={checkpoint.puzzles_downloaded}"
            )

    if checkpoint is None:
        checkpoint = WeiQiCheckpoint(source_mode="puzzle")

    # Load known IDs for dedup
    known_ids = load_puzzle_ids(output_dir)
    logger.info(f"Loaded {len(known_ids)} known puzzle IDs from index")

    rate_limiter = RateLimiter(
        min_delay=config.puzzle_delay,
        jitter_factor=DELAY_JITTER_FACTOR,
    )

    consecutive_failures = 0
    consecutive_extraction_failures = 0
    total_ids = len(ids)
    downloads_since_cooldown = 0

    with WeiQiClient(cookies=config.cookies) as client:
        for idx, puzzle_id in enumerate(ids, 1):
            if should_stop():
                logger.info("Stop requested, saving checkpoint")
                save_checkpoint(checkpoint, output_dir)
                break

            if stats.downloaded >= config.max_puzzles:
                logger.info(f"Reached max puzzles limit ({config.max_puzzles})")
                break

            # Skip if already downloaded
            if puzzle_id in known_ids:
                stats.skipped += 1
                checkpoint.record_skip("duplicate")
                logger.info(
                    f"SKIP puzzle/{puzzle_id} ({idx}/{total_ids}) already downloaded "
                    f"[saved={stats.downloaded} skip={stats.skipped} err={stats.errors}]"
                )
                continue

            # Skip if before resume point
            if config.resume and checkpoint.last_puzzle_id > 0 and puzzle_id <= checkpoint.last_puzzle_id:
                continue

            # Batch cooldown: pause periodically to avoid triggering CAPTCHA
            if downloads_since_cooldown >= COOLDOWN_INTERVAL:
                logger.info(
                    f"Batch cooldown: pausing {COOLDOWN_DURATION:.0f}s after "
                    f"{downloads_since_cooldown} downloads to avoid rate limiting"
                )
                time.sleep(COOLDOWN_DURATION)
                downloads_since_cooldown = 0

            logger.info(
                f"GET puzzle/{puzzle_id} ({idx}/{total_ids}) "
                f"[saved={stats.downloaded} skip={stats.skipped} err={stats.errors}]"
            )

            # Rate limiting
            wait_time = rate_limiter.wait_if_needed()
            if wait_time > 0:
                logger.info(f"WAIT {wait_time:.1f}s (rate_limit)")

            ref = f"puzzle/{puzzle_id}"

            if config.dry_run:
                logger.info(f"[DRY RUN] Would fetch {ref}")
                stats.skipped += 1
                continue

            # Fetch HTML
            html = client.fetch_puzzle_by_id(puzzle_id)

            if html is None:
                stats.not_found += 1
                # Only apply consecutive failure stopping for range probing
                # (start_id/end_id). When iterating explicit IDs (book mode),
                # a few locked/unavailable pages should not abort the whole run.
                if config.puzzle_ids is None:
                    consecutive_failures += 1
                    if consecutive_failures >= CONSECUTIVE_FAILURE_LIMIT:
                        logger.warning(
                            f"Stopping: {consecutive_failures} consecutive failures at ID {puzzle_id}"
                        )
                        break
                else:
                    logger.warning(f"Skipping puzzle/{puzzle_id}: page unavailable (no qqdata)")
                continue

            result = _process_html(
                html=html,
                ref=ref,
                output_dir=output_dir,
                config=config,
                checkpoint=checkpoint,
                known_ids=known_ids,
                stats=stats,
            )

            if result == "rate_limited":
                logger.error(
                    f"CAPTCHA rate-limit detected at puzzle/{puzzle_id} after "
                    f"{stats.downloaded} downloads. Aborting to avoid wasting requests. "
                    f"Wait a few minutes, solve the CAPTCHA in a browser, "
                    f"then re-run with --resume and fresh --cookies."
                )
                save_checkpoint(checkpoint, output_dir)
                break

            if result == "error":
                consecutive_extraction_failures += 1
                # Apply consecutive failure stopping for range probing
                if config.puzzle_ids is None:
                    consecutive_failures += 1
                    if consecutive_failures >= CONSECUTIVE_FAILURE_LIMIT:
                        logger.warning(
                            f"Stopping: {consecutive_failures} consecutive failures at ID {puzzle_id}"
                        )
                        break
                # Also stop book mode after many consecutive extraction failures
                # (likely a session/rate-limit issue, not individual puzzle issues)
                elif consecutive_extraction_failures >= CONSECUTIVE_EXTRACTION_FAILURE_LIMIT:
                    logger.error(
                        f"Stopping: {consecutive_extraction_failures} consecutive extraction "
                        f"failures in book mode at puzzle/{puzzle_id}. "
                        f"Likely rate-limited — re-run with --resume and fresh --cookies."
                    )
                    save_checkpoint(checkpoint, output_dir)
                    break
            else:
                consecutive_failures = 0
                consecutive_extraction_failures = 0
                if result == "ok":
                    downloads_since_cooldown += 1

            # Update checkpoint
            checkpoint.last_puzzle_id = puzzle_id

            # Save checkpoint every 10 puzzles
            if stats.total_processed % 10 == 0:
                save_checkpoint(checkpoint, output_dir)

    # Final checkpoint + sort index
    save_checkpoint(checkpoint, output_dir)
    sort_index(output_dir)

    return stats


def _process_html(
    html: str,
    ref: str,
    output_dir: Path,
    config: DownloadConfig,
    checkpoint: WeiQiCheckpoint,
    known_ids: set[int],
    stats: DownloadStats,
) -> str:
    """Process a downloaded HTML page into SGF.

    Common logic shared between daily and ID-based modes.

    Returns:
        "ok", "skipped", or "error"
    """
    # Detect CAPTCHA / rate-limit page before attempting extraction
    if is_rate_limited_page(html):
        logger.error(
            f"Rate-limited (CAPTCHA page) while fetching {ref}. "
            "The session has been throttled by 101weiqi."
        )
        stats.errors += 1
        checkpoint.record_error(ref, "rate_limited_captcha")
        return "rate_limited"

    # Detect login/authentication redirect
    if is_login_page(html):
        logger.error(
            f"Login page detected while fetching {ref}. "
            "Session expired or this puzzle requires authentication. "
            "Re-run with fresh --cookies."
        )
        stats.errors += 1
        checkpoint.record_error(ref, "login_redirect")
        return "rate_limited"  # Treat as rate_limited to trigger abort

    # Extract qqdata JSON
    qqdata = extract_qqdata(html)
    if qqdata is None:
        logger.warning(f"Failed to extract qqdata from {ref}")
        stats.errors += 1
        checkpoint.record_error(ref, "extraction_failed")
        return "error"

    # Parse to model
    try:
        puzzle = PuzzleData.from_qqdata(qqdata)
    except Exception as e:
        logger.warning(f"Failed to parse puzzle {ref}: {e}")
        stats.errors += 1
        checkpoint.record_error(ref, f"parse_error: {e}")
        return "error"

    # Dedup check
    if puzzle.puzzle_id in known_ids:
        logger.info(f"SKIP {ref} (ID {puzzle.puzzle_id}) duplicate [saved={stats.downloaded} skip={stats.skipped} err={stats.errors}]")
        stats.skipped += 1
        checkpoint.record_skip("duplicate")
        return "skipped"

    # Validate
    error = validate_puzzle(puzzle)
    if error:
        logger.warning(f"Validation failed for {ref}: {error}")
        stats.errors += 1
        checkpoint.record_error(ref, f"validation: {error}")
        return "error"

    # Enrichment: complexity metrics (YX)
    cx = compute_complexity(puzzle.solution_nodes)
    yx_string = cx.to_yx_string() if cx.total_nodes > 0 else None

    # Enrichment: root comment / intent (C[])
    root_comment: str | None = None
    if config.resolve_intent:
        root_comment = _local_intent_mapping.resolve_intent(
            puzzle.type_name, puzzle.player_to_move
        )

    # Enrichment: collection membership (YL[] — books only)
    collection_entries: list[str] | None = None

    # Book membership from bookinfos
    collection_entries = _local_collections_mapping.enrich_collections_from_bookinfos(
        collection_entries, puzzle.bookinfos,
    )

    # Chapter-aware enrichment: append slug:CHAPTER/POSITION when available
    if config.chapter_sequences and puzzle.puzzle_id in config.chapter_sequences:
        chapter_str, position = config.chapter_sequences[puzzle.puzzle_id]
        book_slug = config.book_collection_slug
        if book_slug:
            entry = f"{book_slug}:{chapter_str}/{position}"
            if collection_entries is None:
                collection_entries = [entry]
            elif book_slug not in [e.split(":")[0] for e in collection_entries]:
                collection_entries.append(entry)

    # Save SGF
    try:
        file_path, batch_num = save_puzzle(
            puzzle=puzzle,
            output_dir=output_dir,
            batch_size=config.batch_size,
            checkpoint=checkpoint,
            root_comment=root_comment,
            collection_entries=collection_entries,
            yx_string=yx_string,
        )
        known_ids.add(puzzle.puzzle_id)
        stats.downloaded += 1
        checkpoint.record_success(config.batch_size)

        logger.info(
            f"SAVE {ref} -> {rel_path(file_path)} "
            f"(ID={puzzle.puzzle_id}, level={puzzle.level_name}, "
            f"type={translate_chinese_text(puzzle.type_name)}) "
            f"[saved={stats.downloaded} skip={stats.skipped} err={stats.errors}]"
        )
        return "ok"

    except Exception as e:
        logger.error(f"Failed to save {ref}: {e}")
        stats.errors += 1
        checkpoint.record_error(ref, f"save_error: {e}")
        return "error"
