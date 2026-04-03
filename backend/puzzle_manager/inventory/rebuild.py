"""
Rebuild inventory from publish logs.

Provides functionality to reconstruct inventory counts from publish log entries.
Used when inventory file is corrupted or missing.

Performance plan: Rebuild uses ONLY publish log metadata (level, tags, quality).
No SGF file reads are performed. Ghost entries are checked via a single
upfront rglob() to build a set of existing file paths.

Implements T044-T046 from Spec 052.
"""

from __future__ import annotations

import logging
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from backend.puzzle_manager.inventory.manager import InventoryManager
from backend.puzzle_manager.inventory.models import (
    AnalyzeMetrics,
    AuditMetrics,
    CollectionStats,
    IngestMetrics,
    PublishMetrics,
    PuzzleCollectionInventory,
    StagesStats,
)
from backend.puzzle_manager.paths import get_output_dir, rel_path
from backend.puzzle_manager.publish_log import PublishLogReader

logger = logging.getLogger("puzzle_manager.inventory.rebuild")


def rebuild_inventory(
    output_dir: Path | None = None,
    run_id: str | None = None,
) -> PuzzleCollectionInventory:
    """Rebuild inventory by scanning all publish logs.

    Uses ONLY publish log metadata (level, tags, quality).
    No SGF files are read — all metadata comes from mandatory publish log fields.

    Ghost entries (publish log entries without corresponding SGF files) are
    detected via a single upfront rglob() and skipped.

    Args:
        output_dir: Output directory containing publish-log/. Uses default if None.
        run_id: Run ID for the rebuilt inventory. Auto-generated if None.

    Returns:
        Rebuilt PuzzleCollectionInventory
    """
    if output_dir is None:
        output_dir = get_output_dir()

    if run_id is None:
        run_id = f"rebuild-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}"

    # Publish log is under .puzzle-inventory-state/
    ops_dir = output_dir / ".puzzle-inventory-state"
    publish_log_dir = ops_dir / "publish-log"

    log_reader = PublishLogReader(log_dir=publish_log_dir)

    total_puzzles = 0
    level_counts: Counter[str] = Counter()
    tag_counts: Counter[str] = Counter()
    quality_counts: Counter[str] = Counter()
    puzzles_processed = 0
    ghost_entries_skipped = 0
    seen_paths: set[str] = set()  # Track processed paths to deduplicate

    logger.info(f"Starting inventory rebuild from {rel_path(publish_log_dir)}")

    # Phase 1.3: Batch ghost-check — one rglob walk, then O(1) lookups
    sgf_dir = output_dir / "sgf"
    existing_files: set[str] = set()
    if sgf_dir.exists():
        for sgf_path in sgf_dir.rglob("*.sgf"):
            # Store relative path from output_dir in POSIX format for matching
            rel = str(sgf_path.relative_to(output_dir)).replace("\\", "/")
            existing_files.add(rel)
    logger.info(f"Built file index: {len(existing_files)} SGF files on disk")

    # Iterate through all entries in publish log
    for entry in log_reader.read_all():
        puzzles_processed += 1

        # Ghost-check via set lookup (O(1)) instead of per-file exists()
        entry_path = entry.path.replace("\\", "/")
        if entry_path not in existing_files:
            ghost_entries_skipped += 1
            logger.debug(f"Skipping ghost entry (file missing): {entry.path}")
            continue

        # Skip duplicates (same path published multiple times)
        if entry_path in seen_paths:
            logger.debug(f"Skipping duplicate entry: {entry.path}")
            continue
        seen_paths.add(entry_path)

        total_puzzles += 1

        # Use level from publish log (mandatory field)
        level = entry.level
        if level:
            level_counts[level] += 1
        else:
            logger.warning(f"Empty level for {entry.puzzle_id}")

        # Use tags from publish log (mandatory field)
        for tag in entry.tags:
            tag_counts[tag] += 1

        # Use quality from publish log (mandatory field)
        quality_counts[str(entry.quality)] += 1

        # Progress logging
        if puzzles_processed % 1000 == 0:
            logger.info(f"Processed {puzzles_processed} entries...")

    logger.info(
        f"Rebuild complete: {total_puzzles} puzzles, "
        f"{len(level_counts)} levels, {len(tag_counts)} tags, "
        f"quality distribution: {dict(quality_counts)}, "
        f"ghost entries skipped: {ghost_entries_skipped}"
    )

    # Build quality breakdown dict with all keys initialized
    by_puzzle_quality = {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0}
    for q, count in quality_counts.items():
        if q in by_puzzle_quality:
            by_puzzle_quality[q] = count

    # Build inventory
    inventory = PuzzleCollectionInventory(
        schema_version="1.1",  # Updated for quality support (Spec 102)
        last_updated=datetime.now(UTC),
        last_run_id=run_id,
        collection=CollectionStats(
            total_puzzles=total_puzzles,
            by_puzzle_level=dict(level_counts),
            by_tag=dict(tag_counts),
            by_puzzle_quality=by_puzzle_quality,  # Spec 102, T031
        ),
        stages=StagesStats(
            ingest=IngestMetrics(),
            analyze=AnalyzeMetrics(),
            publish=PublishMetrics(new=total_puzzles),
        ),
        audit=AuditMetrics(
            total_rollbacks=0,
            last_rollback_date=None,
        ),
    )

    return inventory


def rebuild_and_save(
    output_dir: Path | None = None,
    inventory_path: Path | None = None,
    run_id: str | None = None,
) -> PuzzleCollectionInventory:
    """Rebuild inventory and save to file.

    Args:
        output_dir: Output directory containing publish-log/
        inventory_path: Path to save inventory. Uses default if None.
        run_id: Run ID for the rebuilt inventory

    Returns:
        Rebuilt and saved PuzzleCollectionInventory
    """
    inventory = rebuild_inventory(output_dir=output_dir, run_id=run_id)

    # Use InventoryManager to save (gets atomic write for free)
    manager = InventoryManager(inventory_path=inventory_path)
    manager.save(inventory)

    logger.info(f"Rebuilt inventory saved to {manager.inventory_path}")

    return inventory
