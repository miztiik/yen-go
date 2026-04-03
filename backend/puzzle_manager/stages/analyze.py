"""
Analyze stage: classify + tag + enrich.

Processes puzzles from staging/ingest/ and outputs to staging/analyzed/.
Per Spec 027: Deletes processed files from ingest/ when cleanup_policy is ON_SUCCESS.

Reads trace_id from the YM property embedded in each SGF (v12) for
end-to-end observability.
"""

import logging
import time
from pathlib import Path

from backend.puzzle_manager.config.loader import ConfigLoader
from backend.puzzle_manager.core.classifier import (
    classify_difficulty,
    get_level_name,
    level_from_name,
    resolve_level_from_collections,
)
from backend.puzzle_manager.core.collection_assigner import assign_collections
from backend.puzzle_manager.core.complexity import compute_complexity_metrics
from backend.puzzle_manager.core.content_classifier import classify_content_type
from backend.puzzle_manager.core.correctness import mark_sibling_refutations
from backend.puzzle_manager.core.enrichment import EnrichmentConfig, EnrichmentResult, enrich_puzzle
from backend.puzzle_manager.core.fs_utils import cleanup_processed_files
from backend.puzzle_manager.core.quality import compute_quality_metrics, parse_quality_level
from backend.puzzle_manager.core.schema import get_yengo_sgf_version
from backend.puzzle_manager.core.sgf_builder import SGFBuilder
from backend.puzzle_manager.core.sgf_parser import SGFGame, parse_sgf
from backend.puzzle_manager.core.tactical_analyzer import analyze_tactics, derive_auto_tags
from backend.puzzle_manager.core.tagger import detect_techniques
from backend.puzzle_manager.core.text_cleaner import clean_for_correctness
from backend.puzzle_manager.core.trace_utils import parse_pipeline_meta
from backend.puzzle_manager.exceptions import ClassificationError, SGFParseError, TaggingError
from backend.puzzle_manager.inventory.manager import load_quality_levels
from backend.puzzle_manager.models.config import CleanupPolicy
from backend.puzzle_manager.pm_logging import DETAIL, create_trace_logger, to_relative_path
from backend.puzzle_manager.stages.protocol import StageContext, StageResult

logger = logging.getLogger("analyze")


class AnalyzeStage:
    """ANALYZE: classify + tag + enrich.

    1. Read puzzles from staging/ingest/
    2. For each puzzle:
       a. Classify difficulty level
       b. Detect technique tags
       c. Enrich with hints
       d. Add YenGo properties (YG, YT, YH)
       e. Write to staging/analyzed/
    3. Return aggregate result
    """

    @property
    def name(self) -> str:
        return "analyze"

    def validate_prerequisites(self, context: StageContext) -> list[str]:
        """Check prerequisites for analyze stage."""
        errors = []

        ingest_dir = context.get_ingest_dir()
        if not ingest_dir.exists():
            errors.append(f"Ingest directory does not exist: {ingest_dir}")
        elif not list(ingest_dir.glob("*.sgf")):
            errors.append("No puzzles in staging/ingest/ - run ingest first")

        return errors

    def run(self, context: StageContext) -> StageResult:
        """Execute the analyze stage."""
        start_time = time.time()
        processed = 0
        failed = 0
        skipped = 0
        errors: list[str] = []
        processed_files: list[Path] = []  # Track for cleanup
        # Track quality assignments for batch summary (Spec 102)
        quality_counts: dict[str, int] = {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0}

        ingest_dir = context.get_ingest_dir()
        analyzed_dir = context.get_analyzed_dir()
        failed_dir = context.get_failed_dir("analyze")

        analyzed_dir.mkdir(parents=True, exist_ok=True)
        failed_dir.mkdir(parents=True, exist_ok=True)

        batch_size = context.batch_size or context.config.batch.size
        sgf_files = list(ingest_dir.glob("*.sgf"))

        # Log stage start with source context
        source_id = context.source_id or "unknown"

        # Spec 128: Load collection alias map once for the entire batch
        alias_map: dict[str, str] = {}
        level_hint_map: dict[str, str] = {}
        try:
            loader = ConfigLoader()
            alias_map = loader.get_collection_aliases()
            level_hint_map = loader.get_collection_level_hints()
        except Exception as e:
            logger.warning(f"Could not load collection aliases: {e}")

        logger.info(
            "Analyze stage starting",
            extra={
                "source_id": source_id,
                "file_count": len(sgf_files),
                "batch_size": batch_size,
            }
        )

        total_files = len(sgf_files)

        for sgf_path in sgf_files:
            if processed + failed >= batch_size:
                break

            try:
                outcome, quality_level = self._analyze_puzzle(
                    sgf_path, analyzed_dir, failed_dir, context,
                    alias_map=alias_map,
                    level_hint_map=level_hint_map,
                )

                if outcome == "processed":
                    processed += 1
                    processed_files.append(sgf_path)
                    # Track quality for batch summary (Spec 102)
                    if quality_level is not None:
                        quality_counts[str(quality_level)] += 1
                elif outcome == "failed":
                    failed += 1
                else:
                    skipped += 1
                    processed_files.append(sgf_path)  # Also cleanup skipped (already processed)
                    # Track quality for skipped too if available (Spec 102)
                    if quality_level is not None:
                        quality_counts[str(quality_level)] += 1

            except Exception as e:
                logger.warning(f"Error analyzing {sgf_path.name}: {e}")
                errors.append(f"{sgf_path.name}: {e}")
                failed += 1
                self._move_to_failed(sgf_path, failed_dir, str(e), context)

            # Streaming progress
            current = processed + failed + skipped
            # Detailed per-puzzle progress → log file only
            logger.debug(
                "Progress: %d/%d analyzed (%d processed, %d failed, %d skipped)",
                current, total_files, processed, failed, skipped,
                extra={
                    "action": "progress",
                    "source_id": source_id,
                    "processed": processed,
                    "failed": failed,
                    "skipped": skipped,
                    "current": current,
                    "total_files": total_files,
                },
            )
            # Console progress: every 100 puzzles
            if current % 100 == 0:
                logger.info(
                    "[analyze] %d/%d — %d ok, %d failed, %d skipped",
                    current, total_files, processed, failed, skipped,
                )

        # Cleanup processed files from ingest/ per Spec 027
        cleanup_policy = context.config.staging.cleanup_policy
        if cleanup_policy == CleanupPolicy.ON_SUCCESS and processed_files:
            deleted = cleanup_processed_files(processed_files, logger)
            logger.info(f"Cleanup: deleted {deleted} processed files from ingest/")

        duration = time.time() - start_time

        logger.info(
            f"Analyze complete: processed={processed}, failed={failed}, "
            f"skipped={skipped}, duration={duration:.2f}s",
            extra={
                "quality_breakdown": quality_counts,
            }
        )

        return StageResult.partial_result(
            processed=processed,
            failed=failed,
            errors=errors,
            duration=duration,
            skipped=skipped,
        )

    def _format_quality_summary(self, quality_counts: dict[str, int]) -> str:
        """Format quality breakdown as human-readable summary string.

        Spec 102, T021: Format quality summary (e.g., "3xStandard, 2xHigh").

        Args:
            quality_counts: Counts by quality level (1-5).

        Returns:
            Formatted summary string, ordered by quality level (5→1).
        """
        # Load quality names from config (DRY: single source of truth)
        quality_names = load_quality_levels()

        parts = []
        for level in ["5", "4", "3", "2", "1"]:  # Order: best to worst
            count = quality_counts.get(level, 0)
            if count > 0:
                name = quality_names.get(level, f"Level {level}")
                parts.append(f"{count}x{name}")

        return ", ".join(parts) if parts else "none"

    def _analyze_puzzle(
        self,
        sgf_path: Path,
        analyzed_dir: Path,
        failed_dir: Path,
        context: StageContext,
        *,
        alias_map: dict[str, str] | None = None,
        level_hint_map: dict[str, str] | None = None,
    ) -> tuple[str, int | None]:
        """Analyze a single puzzle.

        Reads trace_id from the YM property embedded in the SGF (v12).

        Args:
            sgf_path: Path to SGF file in ingest directory
            analyzed_dir: Output directory for analyzed files
            failed_dir: Directory for failed files
            context: Stage context
            alias_map: Optional collection alias map

        Returns:
            Tuple of (outcome, quality_level) where:
            - outcome is "processed", "failed", or "skipped"
            - quality_level is 1-5 or None if not computed
        """
        puzzle_id = sgf_path.stem  # source_file from ingest
        content = sgf_path.read_text(encoding="utf-8")

        # Extract trace_id from YM property embedded in SGF (v12)
        # Parse SGF first, then read pipeline_meta
        trace_id: str | None = None
        source_id = context.source_id or "unknown"
        trace_logger = logger  # Fallback before try block (P0-3 fix)

        try:
            # Parse SGF
            game = parse_sgf(content)

            # Fix unmarked sibling refutations before any quality/complexity computation
            if game.solution_tree:
                sibling_marked = mark_sibling_refutations(game.solution_tree)
                if sibling_marked > 0:
                    logger.debug(
                        "Marked %d unmarked sibling refutations for %s",
                        sibling_marked, puzzle_id,
                    )

            # Read trace_id from YM property (v13)
            if game.yengo_props.pipeline_meta:
                trace_id_val, _, _, _ = parse_pipeline_meta(game.yengo_props.pipeline_meta)
                trace_id = trace_id_val or None  # Normalize empty string to None

            # Create trace-aware logger for this file
            trace_logger = create_trace_logger(
                run_id=context.run_id,
                source_id=source_id,
                trace_id=trace_id,
                stage="analyze",
            ) if trace_id else logger

            # Skip if already has ALL required YenGo properties at current schema version
            # Required: YV (version), YG (level), YQ (quality), YX (complexity)
            props = game.yengo_props
            current_version = get_yengo_sgf_version()
            is_fully_enriched = (
                props.version == current_version
                and props.level is not None
                and props.quality is not None
                and props.complexity is not None
            )
            if is_fully_enriched:
                logger.log(DETAIL, f"Skipping already analyzed (v{current_version}): {puzzle_id}")
                # Still copy to analyzed directory
                output_path = analyzed_dir / f"{puzzle_id}.sgf"
                if not context.dry_run:
                    output_path.write_text(content, encoding="utf-8")
                else:
                    logger.info(f"[DRY-RUN] Would write: {to_relative_path(output_path)}")
                # Return existing quality level for tracking (Spec 102)
                existing_quality = parse_quality_level(props.quality)
                return ("skipped", existing_quality)

            # Policy-driven enrichment — use registry to decide
            # which properties need computation vs. preservation
            from backend.puzzle_manager.core.property_policy import get_policy_registry
            policy_registry = get_policy_registry()

            # Classify difficulty — enrich only if source YG is absent/invalid
            source_level_slug = game.yengo_props.level_slug
            source_level = game.yengo_props.level
            if not policy_registry.is_enrichment_needed("YG", source_level_slug or source_level):
                # Source provided a valid YG — preserve it
                if source_level_slug and level_from_name(source_level_slug) is not None:
                    level = level_from_name(source_level_slug)
                    level_slug = source_level_slug
                    trace_logger.debug(f"Preserving source-provided YG: {level_slug}")
                elif source_level is not None and 1 <= source_level <= 9:
                    level = source_level
                    level_slug = get_level_name(level)
                    trace_logger.debug(f"Preserving source-provided YG (numeric): {level_slug}")
                else:
                    # Unexpected: policy says don't enrich but value is invalid
                    level = classify_difficulty(game)
                    level_slug = get_level_name(level)
            else:
                # No valid source YG — compute from heuristics
                try:
                    level = classify_difficulty(game)
                    level_slug = get_level_name(level)
                except ClassificationError:
                    # Fallback: elementary (level 3) — practically unreachable
                    level = 3
                    level_slug = "elementary"
                    trace_logger.warning(
                        f"Classification failed for {puzzle_id}, "
                        f"falling back to {level_slug}"
                    )

            # Detect techniques — enrich only if source YT is absent
            if policy_registry.is_enrichment_needed("YT", game.yengo_props.tags):
                tags = detect_techniques(game)
            else:
                tags = list(game.yengo_props.tags)
                trace_logger.debug(f"Preserving source-provided YT for {puzzle_id}")

            # Tactical analysis — detect patterns for auto-tagging,
            # position validation, and difficulty signals
            tactical_analysis = analyze_tactics(game)
            if tactical_analysis.validation_notes:
                trace_logger.debug(
                    "Tactical validation notes for %s: %s",
                    puzzle_id,
                    tactical_analysis.validation_notes,
                )

            # Merge auto-tags from tactical analysis (ENRICH_IF_ABSENT)
            auto_tags = derive_auto_tags(tactical_analysis)
            if auto_tags:
                existing_tag_set = set(tags)
                for tag in auto_tags:
                    if tag not in existing_tag_set:
                        tags.append(tag)
                tags = sorted(set(tags))
                trace_logger.debug(
                    "Auto-tags merged for %s: %s", puzzle_id, auto_tags
                )

            # Assign collections — enrich only if source YL is absent
            if policy_registry.is_enrichment_needed("YL", game.yengo_props.collections):
                collections: list[str] = []
                if alias_map:
                    collections = assign_collections(
                        source_link="",  # source_link not persisted to SGF
                        puzzle_id=puzzle_id,
                        existing_collections=[],
                        alias_map=alias_map,
                    )
            else:
                collections = list(game.yengo_props.collections)
                trace_logger.debug(f"Preserving source-provided YL for {puzzle_id}")

            # Collection-based level override (v5.0):
            # If any assigned collection has a level_hint, override the
            # heuristic/source-provided level. Lowest level wins on conflict.
            if collections and level_hint_map:
                collection_level = resolve_level_from_collections(
                    collections,
                    level_hint_map,
                    puzzle_id=puzzle_id,
                    heuristic_level=level,
                )
                if collection_level is not None:
                    level, level_slug = collection_level

            # Compute quality metrics — enrich if absent or partial
            if policy_registry.is_enrichment_needed("YQ", game.yengo_props.quality):
                quality = compute_quality_metrics(game)
            else:
                quality = game.yengo_props.quality
                logger.debug(f"Preserving existing YQ for {puzzle_id}: {quality}")

            # Compute complexity metrics — enrich if absent or partial
            if policy_registry.is_enrichment_needed("YX", game.yengo_props.complexity):
                complexity = compute_complexity_metrics(game)
            else:
                complexity = game.yengo_props.complexity
                logger.debug(f"Preserving existing YX for {puzzle_id}: {complexity}")

            # Extract quality level for tracking (Spec 102)
            quality_level = parse_quality_level(quality)
            if quality_level is None:
                quality_level = 1  # Default to Unverified
                logger.debug(
                    f"Quality defaulted to 1 for {puzzle_id}: "
                    "could not parse quality from YQ string"
                )

            # Enrich puzzle with hints, region, ko, move order, refutations
            # Use context's enrichment config if provided, otherwise use defaults
            enrichment_config = context.enrichment_config
            if enrichment_config is None:
                enrichment_config = EnrichmentConfig(
                    enable_hints=True,
                    enable_region=True,
                    enable_ko=True,
                    enable_move_order=True,
                    enable_refutation=True,
                    include_liberty_analysis=True,
                    include_technique_reasoning=True,
                    include_consequence=True,
                    verbose=False,
                )
            enrichment = enrich_puzzle(game, enrichment_config)

            # Classify content type (curated/practice/training)
            # Uses ENRICH_IF_ABSENT policy — preserves existing ct if set
            from backend.puzzle_manager.core.trace_utils import parse_pipeline_meta_extended
            existing_meta = parse_pipeline_meta_extended(game.yengo_props.pipeline_meta)
            if existing_meta.content_type is not None:
                content_type = existing_meta.content_type
                trace_logger.debug(f"Preserving existing content type: {content_type}")
            else:
                content_type = classify_content_type(game)

            # Build enriched SGF (pass puzzle_id for GN standardization)
            enriched_sgf = self._enrich_sgf(
                game, level, level_slug, tags, quality, complexity,
                enrichment, puzzle_id, collections=collections,
                enrichment_config=enrichment_config,
                content_type=content_type,
            )

            # Save to analyzed directory
            output_path = analyzed_dir / f"{puzzle_id}.sgf"
            if not context.dry_run:
                output_path.write_text(enriched_sgf, encoding="utf-8")
            else:
                trace_logger.info(f"[DRY-RUN] Would write: {to_relative_path(output_path)}")

            # Structured logging of enrichment results (Spec 102/110: use trace_logger)
            # Per-file logging at INFO level — stage log files get per-puzzle detail
            trace_logger.log(
                DETAIL,
                "Analyzed puzzle",
                extra={
                    "action": "analyze",
                    "puzzle_id": puzzle_id,
                    "source_file": sgf_path.name,
                    "output_file": output_path.name,
                    "level": level_slug,
                    "quality_level": quality_level,
                    "tags": tags,
                    "collections": collections,
                    "hints_count": len(enrichment.hints) if enrichment else 0,
                    "region": enrichment.region if enrichment else None,
                    "ko": enrichment.ko_context if enrichment else None,
                    "move_order": enrichment.move_order if enrichment else None,
                },
            )

            return ("processed", quality_level)

        except SGFParseError as e:
            trace_logger.log(DETAIL, f"Parse error for {puzzle_id}: {e}")
            self._move_to_failed(sgf_path, failed_dir, str(e), context, trace_id=trace_id)
            return ("failed", None)

        except TaggingError as e:
            trace_logger.log(DETAIL, f"Tagging error for {puzzle_id}: {e}")
            self._move_to_failed(sgf_path, failed_dir, str(e), context, trace_id=trace_id)
            return ("failed", None)

    def _enrich_sgf(
        self,
        game: SGFGame,
        level: int,
        level_slug: str,
        tags: list[str],
        quality: str,
        complexity: str,
        enrichment: EnrichmentResult | None = None,
        puzzle_id: str = "",
        *,
        collections: list[str] | None = None,
        enrichment_config: "EnrichmentConfig | None" = None,
        content_type: int | None = None,
    ) -> str:
        """Create enriched SGF with YenGo properties using SGFBuilder.

        Uses SGFBuilder.from_game() to create a builder from the parsed game,
        then modifies it and builds the output SGF. This is cleaner than
        regex-based manipulation and ensures consistent output.

        Per spec-053 (SGF Enrichment Refactor):
        - Removes SO property (provenance stored in pipeline state)
        - Conditionally preserves root-level C[] comment (controlled by
          enrichment_config.preserve_root_comment, default: True)
        - Standardizes GN property to YENGO-{hash} format
        - Output is clean without empty lines (SGFBuilder guarantees this)
        """
        # Create builder from parsed game (copies solution tree, stones, metadata)
        builder = SGFBuilder.from_game(game)

        # Remove SO property from metadata (provenance stored in pipeline state)
        if "SO" in builder.metadata:
            del builder.metadata["SO"]

        # Preserve root comment if configured (default: True)
        # Clean HTML tags/entities from root comment but preserve case for display
        preserve = True
        if enrichment_config is not None:
            preserve = enrichment_config.preserve_root_comment
        if preserve and game.root_comment:
            cleaned_comment = clean_for_correctness(game.root_comment)
            if cleaned_comment:
                builder.set_metadata("C", cleaned_comment)

        # Note: GN property is NOT set here.
        # The publish stage sets GN to match the final content hash filename.
        # This ensures GN == filename for all puzzles regardless of adapter.

        # Set YenGo properties — use policy registry for enrichment decisions
        from backend.puzzle_manager.core.property_policy import get_policy_registry
        policy_registry = get_policy_registry()

        # YV: Always overwritten (OVERRIDE policy)
        builder.set_version(get_yengo_sgf_version())

        # YG, YT, YQ, YX: Already resolved by _analyze_puzzle() via policy
        builder.set_level(level)
        builder.set_level_slug(level_slug)
        builder.yengo_props.tags = []  # Clear existing tags before adding
        builder.add_tags(sorted(set(tags)))  # Dedupe and sort alphabetically
        builder.set_quality(quality)
        builder.set_complexity(complexity)

        # Spec 128: Set collection memberships (YL property)
        if collections:
            builder.set_collections(sorted(set(collections)))

        # Enrichment properties — apply only if source doesn't already have them
        if enrichment:
            # YH: Hints — enrich only if source hints are absent
            if policy_registry.is_enrichment_needed("YH", game.yengo_props.hint_texts):
                if enrichment.hints:
                    builder.add_hints(enrichment.hints)
            # else: source hints preserved via from_game() copy

            # YC: Corner/region — enrich only if source is absent
            if policy_registry.is_enrichment_needed("YC", game.yengo_props.corner):
                if enrichment.region:
                    builder.set_corner(enrichment.region)

            # YK: Ko context — enrich only if source is absent
            if policy_registry.is_enrichment_needed("YK", game.yengo_props.ko_context):
                if enrichment.ko_context and enrichment.ko_context != "none":
                    builder.set_ko_context(enrichment.ko_context)

            # YO: Move order — enrich only if source is absent
            if policy_registry.is_enrichment_needed("YO", game.yengo_props.move_order):
                if enrichment.move_order:
                    builder.set_move_order(enrichment.move_order)

            # YR: Refutations — enrich only if source is absent
            if policy_registry.is_enrichment_needed("YR", game.yengo_props.refutation_count):
                if enrichment.refutations:
                    builder.set_refutation_count(enrichment.refutations)

        # Rebuild YM with content_type if provided
        if content_type is not None:
            from backend.puzzle_manager.core.trace_utils import (
                build_pipeline_meta,
                parse_pipeline_meta_extended,
            )
            existing = parse_pipeline_meta_extended(game.yengo_props.pipeline_meta)
            builder.yengo_props.pipeline_meta = build_pipeline_meta(
                trace_id=existing.trace_id,
                original_filename=existing.original_filename,
                run_id=existing.run_id,
                content_type=content_type,
                trivial_capture=existing.trivial_capture,
            )

        # Build the SGF output
        sgf_output = builder.build()

        return sgf_output

    def _move_to_failed(
        self,
        sgf_path: Path,
        failed_dir: Path,
        reason: str,
        context: StageContext,
        *,
        trace_id: str | None = None,
    ) -> None:
        """Move failed puzzle to failed directory.

        Spec 110: Include trace_id in error file for debugging.
        """
        import shutil

        dest = failed_dir / sgf_path.name
        error_path = failed_dir / f"{sgf_path.stem}.error"

        # Include trace_id in error content for debugging
        error_content = reason
        if trace_id:
            error_content = f"trace_id: {trace_id}\n{reason}"

        if not context.dry_run:
            shutil.copy(str(sgf_path), str(dest))
            error_path.write_text(error_content, encoding="utf-8")
        else:
            logger.info(f"[DRY-RUN] Would copy: {sgf_path.name} -> {to_relative_path(dest)}")
            logger.info(f"[DRY-RUN] Would write: {to_relative_path(error_path)}")
