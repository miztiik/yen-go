"""
Reconcile inventory from disk (SGF files).

Provides functionality to rebuild inventory counts directly from the file system,
bypassing publish logs. This ensures inventory matches exactly what is on disk,
fixing desynchronization issues where logs might be missing or incomplete.

Implements user-requested 'reconcile' feature.

Performance: Uses parse_root_properties_only() for ~10-50x faster metadata
extraction vs full parse_sgf(), and ThreadPoolExecutor for parallel I/O.
"""

from __future__ import annotations

import logging
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from backend.puzzle_manager.core.fs_utils import extract_level_from_path
from backend.puzzle_manager.core.sgf_parser import parse_root_properties_only
from backend.puzzle_manager.inventory.models import (
    CollectionStats,
    PuzzleCollectionInventory,
)
from backend.puzzle_manager.paths import get_output_dir, rel_path

logger = logging.getLogger("puzzle_manager.inventory.reconcile")


@dataclass
class _FileResult:
    """Result from processing a single SGF file."""

    level: str | None
    tags: list[str]
    collections: list[str]
    quality: int
    has_hints: bool


def _process_single_sgf(sgf_path: Path, output_dir: Path) -> _FileResult | None:
    """Extract metadata from a single SGF file using the tokenizer-based parser.

    Returns None if the file cannot be processed.
    """
    try:
        # Level from path (fast)
        level = extract_level_from_path(
            str(sgf_path.relative_to(output_dir)).replace("\\", "/")
        )

        content = sgf_path.read_text(encoding="utf-8")
        props = parse_root_properties_only(content)

        # Tags (YT)
        tags: list[str] = []
        if "YT" in props and props["YT"]:
            tags = [t.strip() for t in props["YT"].split(",") if t.strip()]

        # Collections (YL)
        collections: list[str] = []
        if "YL" in props and props["YL"]:
            collections = [c.strip() for c in props["YL"].split(",") if c.strip()]

        # Quality (YQ) — parse "q:N" from "q:2;rc:0;hc:0"
        q_val = 1  # Default
        if "YQ" in props and props["YQ"]:
            for part in props["YQ"].split(";"):
                if part.startswith("q:"):
                    try:
                        q_val = int(part[2:])
                    except ValueError:
                        pass
                    break

        # Hints (YH) — existence check
        has_hints = bool(props.get("YH"))

        return _FileResult(
            level=level,
            tags=tags,
            collections=collections,
            quality=q_val,
            has_hints=has_hints,
        )
    except Exception as e:
        logger.debug("Failed to extract metadata from %s: %s", sgf_path.name, e, exc_info=True)
        return None


def reconcile_inventory(
    output_dir: Path | None = None,
    run_id: str | None = None,
) -> PuzzleCollectionInventory:
    """Rebuild inventory by scanning SGF files on disk.

    Scans all .sgf files in the output directory and reconstructs inventory counts.
    Level is extracted from path; tags and quality are extracted from SGF root
    properties using the tokenizer-based parser (no regex).

    Args:
        output_dir: Output directory containing sgf/. Uses default if None.
        run_id: Run ID for the reconciled inventory. Auto-generated if None.

    Returns:
        Reconciled PuzzleCollectionInventory
    """
    if output_dir is None:
        output_dir = get_output_dir()

    if run_id is None:
        run_id = f"reconcile-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}"

    sgf_dir = output_dir / "sgf"
    if not sgf_dir.exists():
        logger.warning(f"SGF directory not found: {sgf_dir}")
        return PuzzleCollectionInventory(
            schema_version="2.0",
            collection=CollectionStats(),
            last_updated=datetime.now(UTC),
            last_run_id=run_id,
        )

    logger.info(f"Scanning SGF files in {rel_path(sgf_dir)}...")

    total_puzzles = 0

    level_counts: Counter[str] = Counter()
    tag_counts: Counter[str] = Counter()
    quality_counts: Counter[str] = Counter()

    # Walk the directory
    files = list(sgf_dir.rglob("*.sgf"))
    total_files = len(files)

    logger.info(f"Found {total_files} SGF files. Analyzing metadata (8 workers)...")

    # Process files in parallel using ThreadPoolExecutor
    failed_count = 0
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {
            executor.submit(_process_single_sgf, sgf_path, output_dir): sgf_path
            for sgf_path in files
        }

        for i, future in enumerate(as_completed(futures)):
            if i > 0 and i % 5000 == 0:
                logger.info(f"Processed {i}/{total_files} files...")

            result = future.result()
            if result is None:
                sgf_path = futures[future]
                logger.warning(f"Failed to process {rel_path(sgf_path)}")
                failed_count += 1
                continue

            total_puzzles += 1

            if result.level:
                level_counts[result.level] += 1

            tag_counts.update(result.tags)
            quality_counts[str(result.quality)] += 1

    if failed_count:
        logger.warning(f"Failed to process {failed_count}/{total_files} files")

    # Create new CollectionStats (v2.0 — no avg_quality_score or hint_coverage_pct)
    new_collection = CollectionStats(
        total_puzzles=total_puzzles,
        by_puzzle_level=dict(level_counts),
        by_tag=dict(tag_counts),
        by_puzzle_quality=dict(quality_counts),
    )

    # Build inventory (v2.0 — no stages/metrics/audit)
    new_inventory = PuzzleCollectionInventory(
        schema_version="2.0",
        collection=new_collection,
        last_updated=datetime.now(UTC),
        last_run_id=run_id,
    )

    logger.info(f"Reconciliation complete. Total: {total_puzzles}")
    return new_inventory


def rebuild_search_db_from_disk(output_dir: Path | None = None) -> int:
    """Rebuild yengo-search.db by scanning published SGF files on disk.

    Scans all .sgf files, re-parses metadata, and rebuilds yengo-search.db.
    Also rebuilds yengo-content.db to ensure consistency.

    Args:
        output_dir: Output directory containing sgf/. Uses default if None.

    Returns:
        Number of puzzles indexed.
    """
    import json
    import os

    from backend.puzzle_manager.core.content_db import build_content_db
    from backend.puzzle_manager.core.db_builder import build_search_db
    from backend.puzzle_manager.core.db_models import (
        CollectionMeta,
        PuzzleEntry,
        sgf_to_puzzle_entry,
    )
    from backend.puzzle_manager.core.id_maps import IdMaps

    if output_dir is None:
        output_dir = get_output_dir()

    sgf_dir = output_dir / "sgf"
    if not sgf_dir.exists():
        logger.warning("SGF directory not found: %s", sgf_dir)
        return 0

    files = list(sgf_dir.rglob("*.sgf"))
    logger.info("Rebuilding search DB from %d SGF files on disk...", len(files))

    id_maps = IdMaps.load()
    entries: list[PuzzleEntry] = []
    sgf_content_map: dict[str, str] = {}

    for sgf_path in files:
        try:
            content = sgf_path.read_text(encoding="utf-8")
            content_hash = sgf_path.stem
            batch = sgf_path.parent.name

            entry = sgf_to_puzzle_entry(content, content_hash, id_maps, output_dir, batch_hint=batch)
            if entry is not None:
                entries.append(entry)
            sgf_content_map[content_hash] = content
        except Exception as e:
            logger.debug("Failed to process %s: %s", sgf_path.name, e)

    # Load collections from config
    from backend.puzzle_manager.paths import get_global_config_dir
    config_path = get_global_config_dir() / "collections.json"
    collections: list[CollectionMeta] = []
    if config_path.exists():
        data = json.loads(config_path.read_text(encoding="utf-8"))
        for col in data.get("collections", []):
            collections.append(CollectionMeta(
                collection_id=col["id"],
                slug=col["slug"],
                name=col["name"],
                category=col.get("type"),
            ))

    # Rebuild yengo-search.db via atomic swap (Issue 2)
    db_path = output_dir / "yengo-search.db"
    version_path = output_dir / "db-version.json"
    tmp_db_path = db_path.with_suffix('.db.tmp')
    if tmp_db_path.exists():
        tmp_db_path.unlink()

    # Build deterministic sequence_map
    from collections import defaultdict as _defaultdict
    _col_entries: dict[int, list[str]] = _defaultdict(list)
    for e in entries:
        for col_id in e.collection_ids:
            _col_entries[col_id].append(e.content_hash)
    _sequence_map: dict[tuple[str, int], int] = {}
    for col_id, hashes in _col_entries.items():
        for seq, ch in enumerate(sorted(hashes), start=1):
            _sequence_map[(ch, col_id)] = seq

    # Reconcile generated_at uses datetime.now(UTC) — accepted
    # deviation from pure determinism for non-pipeline operations (RC-4).
    version_info = build_search_db(
        entries=entries,
        collections=collections,
        output_path=tmp_db_path,
        sequence_map=_sequence_map,
    )

    # Atomic swap
    os.replace(str(tmp_db_path), str(db_path))

    # Atomic write for version file (RC-2)
    tmp_version_path = version_path.with_suffix('.json.tmp')
    tmp_version_path.write_text(
        json.dumps(version_info.to_dict(), indent=2),
        encoding="utf-8",
    )
    os.replace(str(tmp_version_path), str(version_path))

    # Rebuild yengo-content.db
    content_db_path = output_dir / "yengo-content.db"
    if content_db_path.exists():
        content_db_path.unlink()
    if sgf_content_map:
        build_content_db(sgf_content_map, content_db_path)

    logger.info(
        "Search DB rebuilt from disk: %d puzzles, version=%s",
        len(entries), version_info.db_version,
    )

    # Regenerate daily schedules for the last 90 days (backward from today)
    from datetime import timedelta

    from backend.puzzle_manager.core.datetime_utils import utc_now
    from backend.puzzle_manager.daily.db_writer import inject_daily_schedule, prune_daily_window
    from backend.puzzle_manager.daily.generator import DailyGenerator
    try:
        today = utc_now()
        start_date = today - timedelta(days=89)
        generator = DailyGenerator(db_path=db_path)
        result = generator.generate(start_date=start_date, end_date=today, force=True)
        if result.challenges:
            inject_daily_schedule(db_path, result.challenges)
            prune_daily_window(db_path, generator.config.rolling_window_days)
            logger.info("Reconcile daily: regenerated %d schedule(s)", len(result.challenges))
    except Exception as daily_err:
        logger.warning("Reconcile daily regeneration failed (non-fatal): %s", daily_err)

    return len(entries)
