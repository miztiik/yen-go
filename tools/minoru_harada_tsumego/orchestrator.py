"""Orchestrator for Harada tsumego archive discovery and download pipeline.

Two-phase pipeline:
  Phase A: Discover — crawl index → year pages → build catalog
  Phase B: Download — fetch problem/answer pages → download images

Uses tools/core checkpoint pattern for resume support.
"""

from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from tools.core.atomic_write import atomic_write_json
from tools.core.checkpoint import ToolCheckpoint, load_checkpoint, save_checkpoint
from tools.core.logging import EventType, StructuredLogger
from tools.minoru_harada_tsumego.config import CollectionConfig
from tools.minoru_harada_tsumego.crawler import WaybackCrawler
from tools.minoru_harada_tsumego.models import Catalog, ImageError, PuzzleEntry, PuzzleImage
from tools.minoru_harada_tsumego.parsers import (
    parse_answer_page,
    parse_index_page,
    parse_problem_page,
    parse_year_page,
)


@dataclass
class DiscoverCheckpoint(ToolCheckpoint):
    """Checkpoint for the discovery phase."""

    last_year_completed: int = 0
    total_years_done: int = 0
    total_puzzles_found: int = 0


@dataclass
class DownloadCheckpoint(ToolCheckpoint):
    """Checkpoint for the download phase.

    Uses set-based tracking: completed_puzzles stores all puzzle numbers that
    have been fully processed. This allows non-sequential processing — puzzle #50
    can fail while #51-100 succeed, and the next run retries only #50.
    """

    completed_puzzles: list[int] = field(default_factory=list)
    pages_cached: int = 0
    images_downloaded: int = 0
    images_failed: int = 0
    images_skipped: int = 0


def _migrate_checkpoint(raw: dict) -> dict:
    """Migrate old sequential checkpoint to set-based format.

    Old format: {"last_problem_completed": 138, ...}
    New format: {"completed_puzzles": [1, 2, ..., 138], ...}
    """
    if "last_problem_completed" in raw and "completed_puzzles" not in raw:
        last = raw.pop("last_problem_completed")
        raw["completed_puzzles"] = list(range(1, last + 1))
    return raw


def _save_catalog(catalog: Catalog, config: CollectionConfig) -> None:
    """Atomically save catalog to disk."""
    catalog.update_stats()
    atomic_write_json(config.catalog_path(), catalog.to_dict())


def _load_catalog(config: CollectionConfig) -> Catalog:
    """Load catalog from disk, or create empty."""
    path = config.catalog_path()
    if path.exists():
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return Catalog.from_dict(data)
    return Catalog(
        collection_name=config.collection_name,
        collection_slug=config.collection_slug,
    )


# --- Phase A: Discover ---


def run_discover(
    config: CollectionConfig,
    logger: StructuredLogger,
    dry_run: bool = False,
) -> Catalog:
    """Discover all puzzles by crawling the index and year pages.

    1. Fetch index page → extract year links
    2. For each year, fetch year page → extract puzzle entries
    3. Save complete catalog
    """
    start_time = time.monotonic()
    catalog = _load_catalog(config)

    # Load checkpoint for resume
    checkpoint = load_checkpoint(config.working_dir(), DiscoverCheckpoint, ".discover-checkpoint.json")
    resume_year = checkpoint.last_year_completed if checkpoint else 0

    logger.run_start(
        str(config.working_dir()),
        max_items=config.estimated_total_problems,
        resume=resume_year > 0,
        dry_run=dry_run,
    )

    if resume_year:
        logger.checkpoint_load(checkpoint.total_puzzles_found, page=resume_year)

    with WaybackCrawler(config, logger) as crawler:
        # Step 1: Fetch and parse the index page
        if not catalog.years:
            index_url = config.wayback_url(config.index_url)
            logger.event(EventType.PAGE_START, "Fetching index page", url=index_url)

            index_html = crawler.fetch_page(index_url, "index")
            if not index_html:
                logger.event(EventType.ITEM_ERROR, "Failed to fetch index page")
                return catalog

            catalog.years = parse_index_page(index_html)
            logger.event(
                EventType.PAGE_END,
                f"Index: {len(catalog.years)} years found",
                count=len(catalog.years),
            )

            if dry_run:
                for y in catalog.years:
                    print(f"  {y.year}: {y.problem_range} -> {y.original_url}")
                _save_catalog(catalog, config)
                return catalog

        # Step 2: Crawl each year page
        for year_entry in catalog.years:
            year = year_entry.year

            # Skip already completed years
            if year <= resume_year:
                continue

            # Skip already crawled years
            if year_entry.status == "crawled":
                continue

            # Construct Wayback URL for year page
            # Use timestamp from index page link if available
            ts = year_entry.wayback_ts or config.index_wayback_timestamp
            year_url = config.wayback_url(year_entry.original_url, ts)

            logger.event(EventType.PAGE_START, f"Year {year}", url=year_url)
            year_html = crawler.fetch_page(year_url, f"year-{year}")

            if not year_html or "404 NOT FOUND" in year_html:
                year_entry.status = "error"
                year_entry.error_detail = "404 or fetch failed"
                logger.item_error(f"year-{year}", "failed to fetch year page")
                continue

            puzzles = parse_year_page(year_html, year)
            year_entry.problem_count = len(puzzles)
            year_entry.status = "crawled"

            # Merge puzzles (avoid duplicates from resume)
            existing_numbers = {p.problem_number for p in catalog.puzzles}
            new_puzzles = [p for p in puzzles if p.problem_number not in existing_numbers]
            catalog.puzzles.extend(new_puzzles)

            logger.event(
                EventType.PAGE_END,
                f"Year {year}: {len(new_puzzles)} new puzzles (total: {len(catalog.puzzles)})",
                year=year,
                new_count=len(new_puzzles),
                total=len(catalog.puzzles),
            )

            # Save checkpoint after each year
            cp = DiscoverCheckpoint(
                last_year_completed=year,
                total_years_done=sum(1 for y in catalog.years if y.status == "crawled"),
                total_puzzles_found=len(catalog.puzzles),
            )
            cp.update_timestamp()
            save_checkpoint(cp, config.working_dir(), ".discover-checkpoint.json")
            _save_catalog(catalog, config)

    # Sort puzzles by number
    catalog.puzzles.sort(key=lambda p: p.problem_number)
    _save_catalog(catalog, config)

    elapsed = time.monotonic() - start_time
    logger.run_end(
        downloaded=len(catalog.puzzles),
        skipped=0,
        errors=sum(1 for y in catalog.years if y.status == "error"),
        duration_sec=elapsed,
    )

    return catalog


# --- Phase B: Download Pages & Images ---


def run_download(
    config: CollectionConfig,
    logger: StructuredLogger,
    dry_run: bool = False,
    limit: int = 0,
    retry_only: bool = False,
    year: int | None = None,
) -> Catalog:
    """Download problem/answer pages and images for all cataloged puzzles.

    For each puzzle:
    1. Fetch problem page → extract images → download GIFs
    2. Fetch answer page → extract images + text → download GIFs
    3. Update catalog with image metadata

    Args:
        retry_only: If True, skip fully completed puzzles. Only process pending/failed.
        year: If set, only process puzzles from this year.
    """
    # Prevent concurrent downloads (race condition corrupts catalog + images)
    lock_path = config.working_dir() / ".download.lock"
    if lock_path.exists():
        try:
            pid = int(lock_path.read_text().strip())
            # Check if the PID is still running (Windows-compatible)
            os.kill(pid, 0)
            logger.event(EventType.ITEM_ERROR, "Download locked by another process", pid=pid)
            sys.exit(1)
        except (ValueError, OSError, ProcessLookupError):
            # Stale lock file — previous process died
            lock_path.unlink(missing_ok=True)
    lock_path.write_text(str(os.getpid()))
    try:
        return _run_download_locked(config, logger, dry_run, limit, lock_path, retry_only, year)
    finally:
        lock_path.unlink(missing_ok=True)


def _compute_semantic_id(puzzle: PuzzleEntry, img: PuzzleImage) -> str:
    """Generate a human-readable identifier for a puzzle image asset.

    Format: {year}_{NNN}_{level}_{type}[_v{variant}]
    Example: 1996_001_elementary_problem, 1996_001_intermediate_answer_wrong_v1

    Level comes before type so that all elementary images sort
    together and all intermediate images sort together, making
    visual inspection easier.
    """
    parts = [str(puzzle.year), f"{puzzle.problem_number:03d}"]
    if img.level:
        parts.append(img.level)
    parts.append(img.image_type)
    if img.variant > 0:
        parts.append(f"v{img.variant}")
    return "_".join(parts)


def _run_download_locked(
    config: CollectionConfig,
    logger: StructuredLogger,
    dry_run: bool,
    limit: int,
    lock_path: Path,
    retry_only: bool = False,
    year: int | None = None,
) -> Catalog:
    start_time = time.monotonic()
    catalog = _load_catalog(config)

    if not catalog.puzzles:
        logger.event(EventType.ITEM_ERROR, "No puzzles in catalog. Run 'discover' first.")
        return catalog

    # Load checkpoint — with migration from old sequential format
    checkpoint_path = config.working_dir() / ".download-checkpoint.json"
    checkpoint: DownloadCheckpoint | None = None
    if checkpoint_path.exists():
        with open(checkpoint_path, encoding="utf-8") as f:
            raw = json.load(f)
        raw = _migrate_checkpoint(raw)
        checkpoint = DownloadCheckpoint(**{
            k: v for k, v in raw.items() if k in DownloadCheckpoint.__dataclass_fields__
        })

    completed_set: set[int] = set(checkpoint.completed_puzzles) if checkpoint else set()

    logger.run_start(
        str(config.working_dir()),
        max_items=len(catalog.puzzles),
        resume=bool(completed_set),
        dry_run=dry_run,
    )

    if completed_set:
        logger.checkpoint_load(
            len(completed_set),
            page=max(completed_set) if completed_set else 0,
        )

    downloaded = checkpoint.images_downloaded if checkpoint else 0
    skipped = checkpoint.images_skipped if checkpoint else 0
    errors = checkpoint.images_failed if checkpoint else 0
    pages_cached = checkpoint.pages_cached if checkpoint else 0
    processed = 0

    with WaybackCrawler(config, logger) as crawler:
        for puzzle in catalog.puzzles:
            num = puzzle.problem_number

            # Year filter
            if year and puzzle.year != year:
                continue

            # Set-based skip: already completed in checkpoint
            if num in completed_set:
                continue

            # Retry-only: skip puzzles that are already fully complete
            if retry_only and puzzle.is_complete:
                continue

            # Limit for testing
            if limit and processed >= limit:
                break

            processed += 1

            if dry_run:
                summary = puzzle.asset_summary
                print(f"  No.{num:4d} ({puzzle.full_date}) [{puzzle.status}]"
                      f"  imgs: {summary['images_downloaded']}/{summary['images_total']}"
                      f"  pending: {summary['images_pending']}")
                continue

            # --- Fetch problem page ---
            if puzzle.problem_page_url and not puzzle.problem_page_cached:
                ts = puzzle.problem_wayback_ts or config.index_wayback_timestamp
                prob_url = config.wayback_url(puzzle.problem_page_url, ts)
                prob_html = crawler.fetch_page(prob_url, f"problem-{num}")

                if prob_html and "404 NOT FOUND" not in prob_html:
                    puzzle.problem_page_cached = True
                    pages_cached += 1

                    # Parse for images
                    prob_images = parse_problem_page(prob_html, num)
                    for img in prob_images:
                        if not any(existing.url == img.url for existing in puzzle.images):
                            puzzle.images.append(img)

            # --- Fetch answer page ---
            if puzzle.answer_page_url and not puzzle.answer_page_cached:
                ts = puzzle.answer_wayback_ts or config.index_wayback_timestamp
                ans_url = config.wayback_url(puzzle.answer_page_url, ts)
                ans_html = crawler.fetch_page(ans_url, f"answer-{num}")

                if ans_html and "404 NOT FOUND" not in ans_html:
                    puzzle.answer_page_cached = True
                    pages_cached += 1

                    # Parse for images and text
                    ans_images, ans_texts = parse_answer_page(ans_html, num)
                    for img in ans_images:
                        if not any(existing.url == img.url for existing in puzzle.images):
                            puzzle.images.append(img)

                    # Store extracted text
                    if "elementary_answer" in ans_texts:
                        puzzle.elementary_answer_text = ans_texts["elementary_answer"]
                    if "intermediate_answer" in ans_texts:
                        puzzle.intermediate_answer_text = ans_texts["intermediate_answer"]

            # --- Assign semantic IDs to all images ---
            for img in puzzle.images:
                if not img.semantic_id:
                    img.semantic_id = _compute_semantic_id(puzzle, img)

            # --- Download images ---
            puzzle_has_transient = False
            now_ts = datetime.now(UTC).isoformat()
            for img in puzzle.images:
                if img.downloaded:
                    skipped += 1
                    continue
                # Skip images with permanent errors (404, html_not_image)
                if img.has_permanent_error:
                    skipped += 1
                    continue
                # In retry mode, reset transient errors so they get re-attempted
                if retry_only and img.has_error and not img.has_permanent_error:
                    img.error = ""

                # Construct image wayback URL
                page_ts = puzzle.problem_wayback_ts or puzzle.answer_wayback_ts or config.index_wayback_timestamp
                img_wayback_url = (
                    f"{config.wayback_base}/{page_ts}im_/{img.url}"
                )

                # Use semantic ID as filename on disk (keeps original extension)
                orig_ext = Path(img.url).suffix or ".gif"
                semantic_filename = f"{img.semantic_id}{orig_ext}"

                success, local_path, file_size = crawler.download_image(
                    img_wayback_url,
                    puzzle.year,
                    semantic_filename,
                    f"No.{num} {img.level} {img.image_type}",
                )

                # Fallback: if 404, try without pinned timestamp (Wayback auto-redirect)
                fallback_url = ""
                if not success and local_path == "404":
                    fallback_url = f"{config.wayback_base}/im_/{img.url}"
                    success, local_path, file_size = crawler.download_image(
                        fallback_url,
                        puzzle.year,
                        semantic_filename,
                        f"No.{num} {img.level} {img.image_type} (fallback)",
                    )

                if success:
                    img.downloaded = True
                    img.local_path = local_path
                    img.file_size = file_size
                    img.wayback_url = img_wayback_url
                    img.error = ""
                    downloaded += 1
                elif local_path == "404":
                    img.error = ImageError(
                        status="404",
                        url=img_wayback_url,
                        fallback_url=fallback_url,
                        http_code=404,
                        reason="Not found on Wayback Machine (pinned + fallback)",
                        timestamp=now_ts,
                    ).to_dict()
                    errors += 1
                elif local_path == "":
                    img.error = ImageError(
                        status="transient",
                        url=img_wayback_url,
                        reason="Request failed after retries (timeout/HTTP error)",
                        timestamp=now_ts,
                    ).to_dict()
                    errors += 1
                    puzzle_has_transient = True
                else:
                    img.error = ImageError(
                        status="html_not_image",
                        url=img_wayback_url,
                        fallback_url=fallback_url,
                        reason="Wayback served HTML instead of image",
                        timestamp=now_ts,
                    ).to_dict()
                    errors += 1

            # Update puzzle status
            if puzzle.is_complete:
                puzzle.status = "images_downloaded"
            elif puzzle.problem_page_cached:
                puzzle.status = "page_cached"
            elif puzzle.images:
                puzzle.status = "discovered"
            else:
                puzzle.status = "error"

            # Mark as completed in checkpoint only if fully done (no transient errors)
            if puzzle.is_complete and not puzzle_has_transient:
                completed_set.add(num)

            # Save checkpoint after each puzzle
            cp = DownloadCheckpoint(
                completed_puzzles=sorted(completed_set),
                pages_cached=pages_cached,
                images_downloaded=downloaded,
                images_failed=errors,
                images_skipped=skipped,
            )
            cp.update_timestamp()
            save_checkpoint(cp, config.working_dir(), ".download-checkpoint.json")
            _save_catalog(catalog, config)

            # Progress logging every 10 puzzles
            if processed % 10 == 0:
                elapsed = time.monotonic() - start_time
                rate = downloaded / (elapsed / 60) if elapsed > 60 else 0
                logger.progress(
                    downloaded=downloaded,
                    skipped=skipped,
                    errors=errors,
                    page=num,
                    elapsed_sec=elapsed,
                    rate=rate,
                )

            # Fail-fast on too many transient (non-404) errors in this run
            transient_errors = sum(
                1 for p in catalog.puzzles for i in p.images
                if i.has_error and not i.has_permanent_error
            )
            if transient_errors > 20:
                logger.event(
                    EventType.ITEM_ERROR,
                    "Too many transient errors, stopping",
                    transient_count=transient_errors,
                )
                break

    _save_catalog(catalog, config)

    elapsed = time.monotonic() - start_time
    logger.run_end(
        downloaded=downloaded,
        skipped=skipped,
        errors=errors,
        duration_sec=elapsed,
    )

    return catalog


# --- Status ---


def show_status(config: CollectionConfig) -> None:
    """Print catalog status summary with per-year breakdown."""
    catalog = _load_catalog(config)
    catalog.update_stats()

    total = catalog.total_puzzles_discovered
    complete = sum(1 for p in catalog.puzzles if p.is_complete)
    imgs_dl = catalog.total_images_downloaded
    imgs_total = catalog.total_images_discovered
    imgs_404 = sum(
        sum(1 for i in p.images if i.has_permanent_error) for p in catalog.puzzles
    )
    imgs_transient = sum(
        sum(1 for i in p.images if i.has_error and not i.has_permanent_error)
        for p in catalog.puzzles
    )
    imgs_pending = imgs_total - imgs_dl - imgs_404

    print(f"\n{'=' * 72}")
    print(f"  {catalog.collection_name} (v{catalog.version})")
    print(f"{'=' * 72}")
    print(f"  Total: {total} puzzles | {catalog.total_years_discovered} years"
          f" (1996-2020)")
    print(f"  Complete: {complete}/{total} puzzles ({round(100*complete/total) if total else 0}%)")
    print(f"  Images: {imgs_dl}/{imgs_total} downloaded"
          f" | {imgs_404} 404 | {imgs_transient} transient"
          f" | {imgs_pending} pending")
    print(f"  Pages cached: {catalog.total_pages_cached}")

    if catalog.puzzles:
        year_summary = catalog.per_year_summary()
        print(f"\n  {'Year':>6}  {'Total':>5}  {'Done':>4}  {'Pend':>4}"
              f"  {'Err':>3}  {'Imgs':>5}  {'DL':>5}  {'404':>4}  {'Progress':>8}")
        print(f"  {'-'*6}  {'-'*5}  {'-'*4}  {'-'*4}"
              f"  {'-'*3}  {'-'*5}  {'-'*5}  {'-'*4}  {'-'*8}")
        for yr, s in year_summary.items():
            print(f"  {yr:>6}  {s['total']:>5}  {s['complete']:>4}  {s['pending']:>4}"
                  f"  {s['errors']:>3}  {s['images_total']:>5}  {s['images_downloaded']:>5}"
                  f"  {s['images_404']:>4}  {s['pct']:>6}%")

        # Retry candidates
        retry_count = sum(
            1 for p in catalog.puzzles if not p.is_complete
        )
        if retry_count:
            print(f"\n  Retry candidates: {retry_count} puzzles with pending pages/images")

        # Status distribution
        statuses: dict[str, int] = {}
        for p in catalog.puzzles:
            statuses[p.status] = statuses.get(p.status, 0) + 1
        print("\n  Puzzle status distribution:")
        for status, count in sorted(statuses.items()):
            print(f"    {status:20s}: {count}")

    print()


# --- Clean ---


def clean_downloads(
    config: CollectionConfig,
    *,
    year: int | None = None,
    keep_catalog: bool = True,
) -> None:
    """Clean downloaded images and reset download state.

    Args:
        config: Collection configuration.
        year: If specified, only clean images for this year.
        keep_catalog: If True (default), keep the catalog but reset download
            status. If False, also delete the catalog and checkpoints.
    """
    catalog = _load_catalog(config)
    image_dir = config.image_dir()
    files_deleted = 0

    if year:
        # Clean only a single year's images
        year_dir = image_dir / str(year)
        if year_dir.exists():
            for f in year_dir.iterdir():
                if f.is_file():
                    f.unlink()
                    files_deleted += 1
            # Only rmdir if empty
            if not any(year_dir.iterdir()):
                year_dir.rmdir()

        # Reset image state for this year's puzzles in catalog
        for puzzle in catalog.puzzles:
            if puzzle.year != year:
                continue
            for img in puzzle.images:
                img.downloaded = False
                img.local_path = ""
                img.file_size = 0
                img.error = ""
            puzzle.status = "discovered" if puzzle.images else puzzle.status

        # Remove these puzzles from checkpoint
        cp_path = config.working_dir() / ".download-checkpoint.json"
        if cp_path.exists():
            cp = load_checkpoint(DownloadCheckpoint, config.working_dir(), ".download-checkpoint.json")
            year_nums = {p.number for p in catalog.puzzles if p.year == year}
            cp.completed_puzzles = sorted(set(cp.completed_puzzles) - year_nums)
            cp.update_timestamp()
            save_checkpoint(cp, config.working_dir(), ".download-checkpoint.json")

        _save_catalog(catalog, config)
        print(f"Cleaned {files_deleted} files for year {year}")

    else:
        # Clean all images
        if image_dir.exists():
            for year_dir in sorted(image_dir.iterdir()):
                if year_dir.is_dir():
                    for f in year_dir.iterdir():
                        if f.is_file():
                            f.unlink()
                            files_deleted += 1
                    year_dir.rmdir()

        if keep_catalog:
            # Reset all image download state but keep puzzle entries
            for puzzle in catalog.puzzles:
                for img in puzzle.images:
                    img.downloaded = False
                    img.local_path = ""
                    img.file_size = 0
                    img.error = ""
                puzzle.status = "discovered" if puzzle.images else puzzle.status
            _save_catalog(catalog, config)

            # Reset checkpoint
            cp_path = config.working_dir() / ".download-checkpoint.json"
            if cp_path.exists():
                cp_path.unlink()
            print(f"Cleaned {files_deleted} files. Catalog kept ({len(catalog.puzzles)} puzzles).")
        else:
            # Full wipe: catalog + checkpoints
            catalog_path = config.working_dir() / "catalog.json"
            if catalog_path.exists():
                catalog_path.unlink()
            for cp_name in [".discover-checkpoint.json", ".download-checkpoint.json"]:
                cp_file = config.working_dir() / cp_name
                if cp_file.exists():
                    cp_file.unlink()
            print(f"Cleaned {files_deleted} files. Catalog and checkpoints deleted.")
