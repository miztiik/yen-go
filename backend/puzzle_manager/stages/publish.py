"""Publish stage: index + output.

Publishes analyzed puzzles to output directory with proper structure.
Validates SGF files before publishing per Spec 036.
Writes publish log entries for rollback capability.

Note: Daily challenges are injected as a mandatory post-step after
    build_search_db(). Ad-hoc generation also available via:
    python -m backend.puzzle_manager daily

IMPORTANT: This stage uses context.output_dir for all path operations.
Do NOT call get_output_dir() directly - it will fail during tests.
"""

import json
import logging
import time
from pathlib import Path

from backend.puzzle_manager.audit import write_audit_entry
from backend.puzzle_manager.core.batch_writer import BatchState, BatchWriter
from backend.puzzle_manager.core.classifier import get_level_name
from backend.puzzle_manager.core.content_db import build_content_db, read_all_entries
from backend.puzzle_manager.core.db_builder import build_search_db
from backend.puzzle_manager.core.db_models import (
    CollectionMeta,
    PuzzleEntry,
    sgf_to_puzzle_entry,
)
from backend.puzzle_manager.core.fs_utils import cleanup_processed_files
from backend.puzzle_manager.core.id_maps import IdMaps, parse_yx
from backend.puzzle_manager.core.naming import generate_content_hash
from backend.puzzle_manager.core.quality import (
    compute_puzzle_quality_level,
    parse_ac_level,
    parse_quality_level,
)
from backend.puzzle_manager.core.sgf_builder import SGFBuilder
from backend.puzzle_manager.core.sgf_parser import parse_sgf
from backend.puzzle_manager.core.sgf_validator import SGFValidator
from backend.puzzle_manager.core.trace_utils import parse_pipeline_meta
from backend.puzzle_manager.exceptions import SGFValidationError
from backend.puzzle_manager.inventory.manager import InventoryManager, load_quality_levels
from backend.puzzle_manager.inventory.models import InventoryUpdate
from backend.puzzle_manager.models.config import CleanupPolicy
from backend.puzzle_manager.models.publish_log import PublishLogEntry
from backend.puzzle_manager.paths import to_posix_path
from backend.puzzle_manager.pm_logging import DETAIL, create_trace_logger, to_relative_path
from backend.puzzle_manager.publish_log import PublishLogWriter
from backend.puzzle_manager.stages.protocol import StageContext, StageResult

logger = logging.getLogger("publish")


def _chapter_sort_key(chapter: str) -> tuple[int, int | str]:
    """Sort key for chapter strings with natural numeric ordering (RC-1).

    Returns a tuple where:
    - (0, 0) for empty string (position-only, sorts first)
    - (1, <int>) for numeric chapters (sorted by integer value)
    - (2, <str>) for named chapters (sorted lexicographically after numeric)
    """
    if not chapter:
        return (0, 0)
    if chapter.isdigit():
        return (1, int(chapter))
    return (2, chapter)


def _sequence_sort_key(seq: tuple[str, int]) -> tuple:
    """Sort key for (chapter, position) with natural chapter ordering."""
    chapter, position = seq
    return (*_chapter_sort_key(chapter), position)


def _strip_ym_filename(game) -> None:
    """Strip the `f` (original_filename) field from YM pipeline metadata."""
    try:
        meta = json.loads(game.yengo_props.pipeline_meta)
        if isinstance(meta, dict) and "f" in meta:
            del meta["f"]
            game.yengo_props.pipeline_meta = json.dumps(meta, separators=(",", ":"))
    except (json.JSONDecodeError, TypeError):
        pass  # Defensive: leave YM unchanged if malformed


class PublishStage:
    """PUBLISH: index + output.

    1. Read puzzles from staging/analyzed/
    2. Organize into batch directories
    3. Copy to output directory
    4. Build search database (SQLite)
    5. Return aggregate result
    """

    @property
    def name(self) -> str:
        return "publish"

    def validate_prerequisites(self, context: StageContext) -> list[str]:
        """Check prerequisites for publish stage."""
        errors = []

        analyzed_dir = context.get_analyzed_dir()
        if not analyzed_dir.exists():
            errors.append(f"Analyzed directory does not exist: {analyzed_dir}")
        elif not list(analyzed_dir.glob("*.sgf")):
            errors.append("No puzzles in staging/analyzed/ - run analyze first")

        return errors

    def run(self, context: StageContext) -> StageResult:
        """Execute the publish stage.

        Periodic operations (publish log flush, batch state save) happen
        at every 100-file boundary, matching the ingest/analyze streaming progress
        cadence. The BatchConfig.flush_interval setting is NOT used by publish.
        """
        start_time = time.time()
        processed = 0
        failed = 0
        skipped = 0
        errors: list[str] = []
        processed_files: list[Path] = []  # Track for cleanup
        resolved_paths: set[str] = set()  # Spec 105: Track unique SGF directory paths

        analyzed_dir = context.get_analyzed_dir()
        failed_dir = context.get_failed_dir("publish")
        failed_dir.mkdir(parents=True, exist_ok=True)

        # Use context paths - NOT get_output_dir() which fails during tests
        output_root = context.output_dir
        sgf_root = context.sgf_output_dir

        batch_size = context.batch_size or context.config.batch.size
        max_files_per_dir = context.config.batch.max_files_per_dir
        sgf_files = sorted(analyzed_dir.glob("*.sgf"))

        # Log stage start with source context
        source_id = context.source_id or "unknown"
        logger.info(
            "Publish stage starting",
            extra={
                "source_id": source_id,
                "file_count": len(sgf_files),
                "batch_size": batch_size,
            }
        )

        # Initialize IdMaps for numeric ID conversion
        id_maps = IdMaps.load()

        # Track new PuzzleEntry objects for database building
        new_entries: list[PuzzleEntry] = []
        # Track SGF content for content database (DB-2)
        sgf_content_map: dict[str, str] = {}
        # Source-provided collection sequences from YL :CHAPTER/POSITION (v14)
        source_collection_sequences: dict[tuple[str, int], tuple[str, int]] = {}
        # Slug-based counters for inventory (InventoryUpdate expects slug keys)
        level_slug_counts: dict[str, int] = {}
        tag_slug_counts: dict[str, int] = {}
        # Track puzzles by quality level for inventory (Spec 102)
        puzzles_by_quality: dict[str, int] = {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0}

        # Initialize BatchWriter for batch directory resolution
        batch_writer = BatchWriter(sgf_root, max_files_per_dir=max_files_per_dir)

        # O(1) fast path: Track BatchState per level for high-throughput publishing (Spec 126)
        # Key format: "{level}" -> BatchState
        batch_states: dict[str, BatchState] = {}

        # Initialize validator (T081-T085)
        validator = SGFValidator()
        skip_validation = context.skip_validation if hasattr(context, 'skip_validation') else False

        # Initialize publish log writer (T008)
        # Use context.publish_log_dir to avoid calling get_publish_log_dir() during tests
        log_writer = PublishLogWriter(log_dir=context.publish_log_dir)
        pending_log_entries: list[PublishLogEntry] = []

        # Get run_id from state for YI property (T009)
        run_id = context.state.run_id if hasattr(context.state, 'run_id') else None

        for sgf_path in sgf_files:
            if processed + failed >= batch_size:
                break

            try:
                content = sgf_path.read_text(encoding="utf-8")
                game = parse_sgf(content)

                # Extract trace_id from YM property (replaces trace registry lookup)
                trace_id, _, _, _ = parse_pipeline_meta(game.yengo_props.pipeline_meta)

                # Strip `f` (original_filename) from YM before publishing
                _strip_ym_filename(game)

                # Create trace-aware logger for this file
                trace_logger = create_trace_logger(
                    run_id=context.run_id,
                    source_id=source_id,
                    trace_id=trace_id or None,
                    stage="publish",
                ) if trace_id else logger

                # Inject run_id into game object BEFORE validation (YI is required)
                if run_id and game.yengo_props.run_id is None:
                    game.yengo_props.run_id = run_id

                # Validate SGF before publishing (T085)
                if not skip_validation:
                    result = validator.validate(game)
                    if not result.is_valid:
                        error_msg = "; ".join(result.errors)
                        raise SGFValidationError(f"SGF validation failed: {error_msg}")
                    for warning in result.warnings:
                        trace_logger.warning(f"Validation warning for {sgf_path.stem}: {warning}")

                # Get level
                level = game.yengo_props.level or 1
                level_name = get_level_name(level)

                # O(1) fast path: Load global BatchState once (Spec 126)
                if "global" not in batch_states:
                    batch_states["global"] = BatchState.load_or_recover(
                        sgf_root, max_files_per_dir
                    )
                state = batch_states["global"]

                # Get batch directory using O(1) in-memory state (no filesystem scan)
                batch_dir, batch_num = batch_writer.get_batch_dir_fast(
                    state.current_batch, state.files_in_current_batch
                )

                # Flat path with 4-digit batch
                resolved_path = f"sgf/{batch_num:04d}"
                resolved_paths.add(resolved_path)

                # Generate content-based hash filename (per Spec 028)
                content_hash = generate_content_hash(content)
                output_path = batch_dir / f"{content_hash}.sgf"

                if output_path.exists():
                    logger.log(DETAIL, f"Skipping already-published SGF {content_hash} (from {to_relative_path(sgf_path)}). File already exists at {to_relative_path(output_path)}.")
                    skipped += 1
                    processed_files.append(sgf_path)  # Also cleanup skipped (already published)
                    continue

                # Update GN property to match filename hash (ensures GN == filename)
                game.metadata["GN"] = f"YENGO-{content_hash}"

                # Inject YI[run_id] property into game object (T009)
                if run_id:
                    game.yengo_props.run_id = run_id

                # Re-serialize via builder for consistent Y* property ordering
                content = SGFBuilder.from_game(game).build()

                if not context.dry_run:
                    output_path.write_text(content, encoding="utf-8")
                else:
                    logger.info(f"[DRY-RUN] Would write: {to_relative_path(output_path)}")

                # Track for indexing - use POSIX paths for cross-platform URL compatibility
                rel_path = to_posix_path(output_path, relative_to=output_root)

                # Extract quality level from YQ or compute it (Spec 102)
                quality_level = parse_quality_level(game.yengo_props.quality)
                if quality_level is None:
                    # Fallback: compute from puzzle data
                    quality_level = compute_puzzle_quality_level(game)
                    trace_logger.debug(
                        f"Quality computed for {content_hash}: {quality_level} (no YQ property)"
                    )

                # Track quality for inventory (Spec 102)
                puzzles_by_quality[str(quality_level)] += 1

                # Build PuzzleEntry with numeric IDs for database
                level_id = id_maps.level_slug_to_id(level_name)
                tag_ids = sorted(
                    id_maps.tag_slug_to_id(t)
                    for t in (game.yengo_props.tags or [])
                    if id_maps.tag_slug_to_id_safe(t) is not None
                )
                collection_ids = sorted(
                    id_maps.collection_slug_to_id(c)
                    for c in (game.yengo_props.collections or [])
                    if id_maps.collection_slug_to_id_safe(c) is not None
                )

                # Capture source-provided collection sequences (v14: YL slug:CHAPTER/POSITION)
                for slug, (chapter, position) in (game.yengo_props.collection_sequences or {}).items():
                    col_id = id_maps.collection_slug_to_id_safe(slug)
                    if col_id is not None:
                        source_collection_sequences[(content_hash, col_id)] = (chapter, position)
                complexity = parse_yx(game.yengo_props.complexity)

                # Read content_type from YM pipeline metadata (RC-3: wire ct to DB-1)
                from backend.puzzle_manager.core.content_classifier import get_content_type_id
                from backend.puzzle_manager.core.trace_utils import parse_pipeline_meta_extended
                pipeline_meta = parse_pipeline_meta_extended(game.yengo_props.pipeline_meta)
                content_type = pipeline_meta.content_type if pipeline_meta.content_type is not None else get_content_type_id("practice")

                # Extract analysis completeness from YQ (0=untouched if absent)
                ac_level = parse_ac_level(game.yengo_props.quality)

                entry = PuzzleEntry(
                    content_hash=content_hash,
                    batch=f"{batch_num:04d}",
                    level_id=level_id,
                    tag_ids=tag_ids,
                    collection_ids=collection_ids,
                    cx_depth=complexity[0],
                    cx_refutations=complexity[1],
                    cx_solution_len=complexity[2],
                    cx_unique_resp=complexity[3],
                    quality=quality_level or 0,
                    content_type=content_type,
                    ac=ac_level,
                )
                new_entries.append(entry)

                # Track SGF content for DB-2 (content database)
                sgf_content_map[content_hash] = content

                # Slug-based counters for inventory
                level_slug_counts[level_name] = level_slug_counts.get(level_name, 0) + 1
                for tag in (game.yengo_props.tags or []):
                    tag_slug_counts[tag] = tag_slug_counts.get(tag, 0) + 1

                # Create publish log entry (T008, Spec 110: include trace_id)
                # Use YS property from SGF (set at ingest) for accurate source tracking.
                # Fall back to context.source_id for backward compatibility with pre-YS files.
                current_source_id = game.yengo_props.source or context.source_id or "unknown"

                # Spec 107: Include tags in publish log for rollback tag decrement
                puzzle_tags = tuple(game.yengo_props.tags) if game.yengo_props.tags else ()

                log_entry = PublishLogEntry(
                    run_id=run_id or "unknown",
                    puzzle_id=content_hash,
                    source_id=current_source_id,
                    path=rel_path,
                    quality=quality_level,  # Spec 102: Track quality in publish log
                    trace_id=trace_id or "",  # Spec 110: Include trace_id for provenance
                    level=level_name,  # Spec 138: Level slug for rollback index updates
                    tags=puzzle_tags,  # Spec 107: Tags for rollback support
                    collections=tuple(game.yengo_props.collections) if game.yengo_props.collections else (),  # Spec 138
                )
                pending_log_entries.append(log_entry)

                processed += 1
                processed_files.append(sgf_path)

                # O(1) fast path: Update batch state after successful write
                state.record_file_saved(max_files_per_dir)

                trace_logger.log(
                    DETAIL,
                    "Published puzzle",
                    extra={
                        "action": "publish",
                        "puzzle_id": content_hash,
                        "source_file": sgf_path.stem,
                        "output_path": rel_path,  # Already POSIX format from to_posix_path()
                        "puzzle_level": level_name,
                    },
                )

            except Exception as e:
                trace_logger.warning(f"Error publishing {sgf_path.name}: {e}")
                errors.append(f"{sgf_path.name}: {e}")
                failed += 1

            # Streaming progress (matches ingest/analyze dual-level pattern)
            total = processed + failed + skipped
            logger.debug(
                "Progress: %d processed, %d failed, %d skipped (%d/%d)",
                processed, failed, skipped, total, batch_size,
            )
            # Console progress: every 100 puzzles
            if total > 0 and total % 100 == 0:
                logger.info(
                    "[publish] %d/%d — %d ok, %d failed, %d skipped",
                    total, batch_size, processed, failed, skipped,
                )
                # Periodic flush: publish log + batch state (no snapshot)
                # Each flush is a crash-recovery commit point.
                if not context.dry_run:
                    self._flush_periodic(
                        pending_log_entries=pending_log_entries,
                        batch_states=batch_states,
                        sgf_root=sgf_root,
                        log_writer=log_writer,
                        label=f"periodic@{total}",
                    )

        # Remainder flush: log entries since last 100-file boundary
        if not context.dry_run:
            self._flush_periodic(
                pending_log_entries=pending_log_entries,
                batch_states=batch_states,
                sgf_root=sgf_root,
                log_writer=log_writer,
                label="final",
            )

        # Build search database ONCE after all files are processed
        if new_entries and not context.dry_run:
            self._build_search_database(
                new_entries=new_entries,
                output_root=output_root,
                source_collection_sequences=source_collection_sequences,
            )

            # Build content database (DB-2) for dedup support
            if sgf_content_map:
                build_content_db(
                    sgf_files=sgf_content_map,
                    output_path=context.content_db_path,
                    source=context.source_id,
                    batch=f"{batch_num:04d}",
                )
        elif new_entries and context.dry_run:
            logger.info(
                f"[DRY-RUN] Would build search DB with {len(new_entries)} new entries"
            )
            if sgf_content_map:
                logger.info(
                    f"[DRY-RUN] Would build content DB with {len(sgf_content_map)} SGFs"
                )
            if pending_log_entries:
                logger.info(f"[DRY-RUN] Would write {len(pending_log_entries)} entries to publish log")

        # Update inventory statistics (Spec 052, T023-T028, Spec 102)
        # Wrapped in try/except: inventory/audit failures must not crash the stage
        # after files have already been written to disk. Use `inventory --reconcile`
        # to recover from inventory desync.
        if processed > 0 and not context.dry_run:
            try:
                self._update_inventory(
                    level_slug_counts=level_slug_counts,
                    tag_slug_counts=tag_slug_counts,
                    puzzles_by_quality=puzzles_by_quality,
                    run_id=run_id or "unknown",
                    processed_count=processed,
                    output_dir=output_root,
                )
            except Exception as e:
                logger.error(
                    "Failed to update inventory after publishing %d files: %s. "
                    "Run 'inventory --reconcile' to fix.",
                    processed, e,
                    exc_info=True,
                )

            try:
                # Write audit entry for publish operation
                audit_file = output_root / ".puzzle-inventory-state" / "audit.jsonl"
                write_audit_entry(
                    audit_file=audit_file,
                    operation="publish",
                    target="puzzles-collection",
                    details={
                        "files_published": processed,
                        "files_failed": failed,
                        "files_skipped": skipped,
                        "source": source_id,
                        "run_id": run_id or "unknown",
                    },
                )
            except Exception as e:
                logger.error(
                    "Failed to write audit entry: %s", e, exc_info=True,
                )

        # Cleanup processed files from analyzed/ per Spec 027
        cleanup_policy = context.config.staging.cleanup_policy
        if cleanup_policy == CleanupPolicy.ON_SUCCESS and processed_files:
            deleted = cleanup_processed_files(processed_files, logger)
            logger.info(f"Cleanup: deleted {deleted} processed files from analyzed/")

        duration = time.time() - start_time

        logger.info(
            f"Publish complete: processed={processed}, failed={failed}, "
            f"skipped={skipped}, duration={duration:.2f}s",
            extra={
                "quality_breakdown": puzzles_by_quality,  # Spec 102, T017
            }
        )

        remaining = len(sgf_files) - (processed + failed + skipped)

        return StageResult.partial_result(
            processed=processed,
            failed=failed,
            errors=errors,
            duration=duration,
            skipped=skipped,
            remaining=remaining,
            resolved_paths=sorted(resolved_paths),  # Spec 105: Include resolved paths
        )

    def _flush_periodic(
        self,
        *,
        pending_log_entries: list[PublishLogEntry],
        batch_states: dict[str, BatchState],
        sgf_root: Path,
        log_writer: PublishLogWriter,
        label: str,
    ) -> None:
        """Flush publish log and batch state periodically.

        Called at every 100-file boundary and after the loop ends (remainder).
        Each call is a crash-recovery commit point for log + batch state.
        Database is built separately at end via _build_search_database().
        """
        # 1. Publish log: flush pending entries and clear the buffer
        if pending_log_entries:
            log_writer.write_batch(list(pending_log_entries))
            logger.info(
                "Publish log flush (%s): wrote %d entries",
                label, len(pending_log_entries),
            )
            pending_log_entries.clear()

        # 2. Batch state: save global state
        if "global" in batch_states:
            batch_states["global"].save(sgf_root)
            logger.debug("Saved global batch state (%s)", label)

    def _build_search_database(
        self,
        *,
        new_entries: list[PuzzleEntry],
        output_root: Path,
        source_collection_sequences: dict[tuple[str, int], tuple[str, int]] | None = None,
    ) -> None:
        """Build SQLite search database from DB-2 entries + new entries.

        Reads all existing entries from yengo-content.db, re-parses SGF
        to extract metadata, merges with current run's new_entries (dedup
        by content_hash), then rebuilds yengo-search.db from the full set.
        """
        collections = self._load_collections_meta()
        id_maps = IdMaps.load()

        db_path = output_root / "yengo-search.db"
        version_path = output_root / "db-version.json"
        content_db_path = output_root / "yengo-content.db"

        # Build set of new content_hashes for fast dedup
        new_hashes = {e.content_hash for e in new_entries}

        # Read existing entries from DB-2 and convert to PuzzleEntry
        existing_entries: list[PuzzleEntry] = []
        db2_rows = read_all_entries(content_db_path)
        for row in db2_rows:
            ch = row["content_hash"]
            if ch in new_hashes:
                continue  # Current run's entry takes precedence
            sgf_content = row["sgf_content"]
            if not sgf_content:
                continue
            try:
                entry = sgf_to_puzzle_entry(
                    sgf_content, ch, id_maps, output_root,
                    batch_hint=row.get("batch"),
                    source=row.get("source", ""),
                )
                if entry is not None:
                    existing_entries.append(entry)
            except Exception as e:
                logger.debug("Failed to convert DB-2 entry %s: %s", ch, e)

        all_entries = existing_entries + new_entries
        all_entries.sort(key=lambda e: e.content_hash)
        logger.info(
            "Merging %d existing + %d new = %d total entries for search DB",
            len(existing_entries), len(new_entries), len(all_entries),
        )

        # Edition detection: split multi-source collections into editions
        from backend.puzzle_manager.core.edition_detection import create_editions
        edition_cols = create_editions(all_entries, collections, content_db_path)
        collections.extend(edition_cols)

        # Build to temp file then atomic swap (Issue 2: prevent corrupt intermediate state)
        import os
        tmp_db_path = db_path.with_suffix('.db.tmp')
        if tmp_db_path.exists():
            tmp_db_path.unlink()

        # Build sequence_map: use source-provided sequences (v14) when available,
        # fall back to deterministic alphabetical ordering by content_hash
        sequence_map: dict[tuple[str, int], int] = {}
        chapter_map: dict[tuple[str, int], str] = {}
        src_seqs = source_collection_sequences or {}
        from collections import defaultdict
        col_entries: dict[int, list[str]] = defaultdict(list)
        for e in all_entries:
            for col_id in e.collection_ids:
                col_entries[col_id].append(e.content_hash)
        for col_id, hashes in col_entries.items():
            # Check if this collection has ANY source-provided sequences
            source_keys = {
                ch for ch in hashes
                if (ch, col_id) in src_seqs
            }
            if source_keys:
                # Use source-provided ordering with natural chapter sort (RC-1)
                # and content_hash tiebreaker for determinism (RC-5)
                sentinel = ("\uffff", 999999)
                sorted_hashes = sorted(
                    hashes,
                    key=lambda ch: (
                        _sequence_sort_key(src_seqs.get((ch, col_id), sentinel)),
                        ch,
                    ),
                )
            else:
                sorted_hashes = sorted(hashes)
            for seq, ch in enumerate(sorted_hashes, start=1):
                sequence_map[(ch, col_id)] = seq

            # Build chapter_map from source sequences
            for ch in hashes:
                if (ch, col_id) in src_seqs:
                    chapter_str, _ = src_seqs[(ch, col_id)]
                    chapter_map[(ch, col_id)] = chapter_str

        # Build per-collection chapter lists and inject into collection attrs
        col_chapters: dict[int, list[str]] = defaultdict(list)
        for (ch, col_id), chapter_str in chapter_map.items():
            if chapter_str and chapter_str != "0":
                col_chapters[col_id].append(chapter_str)
        for col in collections:
            distinct = sorted(set(col_chapters.get(col.collection_id, [])),
                              key=_chapter_sort_key)
            if distinct:
                col.attrs = {**col.attrs, "chapters": distinct}

        version_info = build_search_db(
            entries=all_entries,
            collections=collections,
            output_path=tmp_db_path,
            sequence_map=sequence_map,
            chapter_map=chapter_map,
        )

        # Atomic swap: replace live DB with completed temp file
        os.replace(str(tmp_db_path), str(db_path))

        # Atomic write for version file (RC-2)
        tmp_version_path = version_path.with_suffix('.json.tmp')
        tmp_version_path.write_text(
            json.dumps(version_info.to_dict(), indent=2),
            encoding="utf-8",
        )
        os.replace(str(tmp_version_path), str(version_path))
        logger.info(
            "Search DB built: %d puzzles, version=%s",
            version_info.puzzle_count, version_info.db_version,
        )

    @staticmethod
    def _load_collections_meta() -> list[CollectionMeta]:
        """Load collection metadata from config/collections.json."""
        from backend.puzzle_manager.paths import get_global_config_dir

        config_path = get_global_config_dir() / "collections.json"
        data = json.loads(config_path.read_text(encoding="utf-8"))
        result: list[CollectionMeta] = []
        for col in data.get("collections", []):
            result.append(CollectionMeta(
                collection_id=col["id"],
                slug=col["slug"],
                name=col["name"],
                category=col.get("type"),
            ))
        return result

    def _format_quality_summary(self, puzzles_by_quality: dict[str, int]) -> str:
        """Format quality breakdown as human-readable summary string.

        Spec 102, T018: Format quality summary (e.g., "3xStandard, 2xHigh").

        Args:
            puzzles_by_quality: Counts by quality level (1-5).

        Returns:
            Formatted summary string, ordered by quality level (5→1).
        """
        # Load quality names from config (DRY: single source of truth)
        quality_names = load_quality_levels()

        parts = []
        for level in ["5", "4", "3", "2", "1"]:  # Order: best to worst
            count = puzzles_by_quality.get(level, 0)
            if count > 0:
                name = quality_names.get(level, f"Level {level}")
                parts.append(f"{count}x{name}")

        return ", ".join(parts) if parts else "none"

    # NOTE: _get_next_batch_number removed - now using BatchWriter.get_next_batch_number()

    def _update_inventory(
        self,
        level_slug_counts: dict[str, int],
        tag_slug_counts: dict[str, int],
        puzzles_by_quality: dict[str, int],
        run_id: str,
        processed_count: int,
        output_dir: Path,
    ) -> None:
        """Update puzzle collection inventory after successful publish.

        Spec 052, T023-T028: Integrate inventory updates with publish stage.
        Spec 102: Track puzzle quality breakdown.

        Args:
            level_slug_counts: Puzzle counts by level slug.
            tag_slug_counts: Puzzle counts by tag slug.
            puzzles_by_quality: Puzzle counts by quality level (1-5).
            run_id: Pipeline run ID.
            processed_count: Number of puzzles published.
            output_dir: Output directory root.
        """
        # Spec 102: Include quality breakdown in inventory update
        update = InventoryUpdate(
            puzzles_added=processed_count,
            level_increments=level_slug_counts,
            tag_increments=tag_slug_counts,
            quality_increments=puzzles_by_quality,
        )

        # Spec 107: Inventory file in ops_dir (.puzzle-inventory-state/inventory.json)
        ops_dir = output_dir / ".puzzle-inventory-state"

        # Ensure ops directory exists before writing to it
        ops_dir.mkdir(parents=True, exist_ok=True)

        inventory_path = ops_dir / "inventory.json"

        manager = InventoryManager(inventory_path=inventory_path)

        # Apply increment (creates file if missing)
        # Note: increment() already updates stages.publish.new; no separate
        # update_stage_metrics call needed here to avoid double-counting.
        manager.increment(update, run_id=run_id)

        logger.info(
            f"Updated inventory: +{processed_count} puzzles",
            extra={
                "levels": level_slug_counts,
                "tags_count": len(tag_slug_counts),
                "quality": puzzles_by_quality,  # Spec 102
            },
        )
