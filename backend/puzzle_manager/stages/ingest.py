"""
Ingest stage: fetch + parse + validate.

Fetches puzzles from configured sources and stores in staging/ingest/.

Generates trace_id per file and embeds it in the SGF via YM property (v12)
for end-to-end observability across pipeline stages.
"""

import logging
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path

from backend.puzzle_manager.adapters._base import FetchResult
from backend.puzzle_manager.adapters._registry import create_adapter
from backend.puzzle_manager.config.loader import ConfigLoader
from backend.puzzle_manager.core.content_db import (
    FINGERPRINT_VERSION,
    canonical_position_hash,
    compute_solution_fingerprint,
    extract_position_data,
)
from backend.puzzle_manager.core.sgf_builder import SGFBuilder
from backend.puzzle_manager.core.sgf_parser import parse_sgf
from backend.puzzle_manager.core.trace_utils import generate_trace_id
from backend.puzzle_manager.exceptions import SGFParseError
from backend.puzzle_manager.pm_logging import DETAIL, create_trace_logger, to_relative_path
from backend.puzzle_manager.stages.protocol import StageContext, StageResult

logger = logging.getLogger("ingest")


@dataclass
class DedupResult:
    """Result of dedup check with collision detail for logging."""

    is_duplicate: bool
    existing_hash: str | None = None
    position_hash: str = ""
    event_type: str = ""
    solution_fingerprint: str = ""
    existing_fingerprint: str | None = None
    existing_source: str | None = None


class IngestStage:
    """INGEST: fetch + parse + validate.

    1. Load enabled sources from config
    2. For each source:
       a. Get adapter from registry
       b. Configure adapter
       c. Fetch puzzles (yielding FetchResult)
       d. Parse SGF content
       e. Validate structure (has solution)
       f. Write to staging/ingest/
    3. Return aggregate result
    """

    @property
    def name(self) -> str:
        return "ingest"

    def validate_prerequisites(self, context: StageContext) -> list[str]:
        """Check prerequisites for ingest stage."""
        errors = []

        # Check for configured sources
        loader = ConfigLoader()
        sources = [s for s in loader.load_sources() if getattr(s, 'enabled', True)]
        if not sources:
            errors.append("No sources configured or enabled")

        return errors

    def run(self, context: StageContext) -> StageResult:
        """Execute the ingest stage."""
        start_time = time.time()
        processed = 0
        failed = 0
        skipped = 0
        errors: list[str] = []

        # Track rejection reasons (Spec 108 T052/T053)
        rejection_reasons: dict[str, int] = {}

        # Get enabled sources
        loader = ConfigLoader()
        sources = [s for s in loader.load_sources() if getattr(s, 'enabled', True)]

        # Filter to specific source if requested
        if context.source_id:
            sources = [s for s in sources if s.id == context.source_id]
            if not sources:
                return StageResult.failure_result(f"Source not found or disabled: {context.source_id}")

        if not sources:
            return StageResult.failure_result("No sources configured")

        ingest_dir = context.get_ingest_dir()
        failed_dir = context.get_failed_dir("ingest")
        ingest_dir.mkdir(parents=True, exist_ok=True)
        failed_dir.mkdir(parents=True, exist_ok=True)

        batch_size = context.batch_size or context.config.batch.size

        # Open content DB for dedup detection (RC-3: graceful skip when missing)
        content_db_path = context.content_db_path
        dedup_conn: sqlite3.Connection | None = None
        if content_db_path.exists():
            dedup_conn = sqlite3.connect(f"file:{content_db_path}?mode=ro", uri=True)
            logger.info("Content database loaded for dedup: %s", to_relative_path(content_db_path))
        else:
            logger.info("Content database not found at %s, skipping dedup check", to_relative_path(content_db_path))

        # Log stage start with source context
        source_id = context.source_id or "all"
        logger.info(
            "Ingest stage starting",
            extra={
                "source_id": source_id,
                "batch_size": batch_size,
            }
        )

        for source in sources:
            logger.info(f"Processing source: {source.id}")

            try:
                # Create and configure adapter
                # Spec 109: Merge resume flag into adapter config
                adapter_config = source.config.model_dump()
                if context.resume:
                    adapter_config["resume"] = True
                adapter = create_adapter(source.adapter, adapter_config)

                # Fetch puzzles
                for result in adapter.fetch(batch_size=batch_size):
                    if result.is_success:
                        # Dedup check against content DB (yengo-content.db)
                        if dedup_conn is not None and result.sgf_content:
                            # Compute solution fingerprint for the incoming puzzle
                            sol_fp = ""
                            try:
                                game = parse_sgf(result.sgf_content)
                                sol_fp = compute_solution_fingerprint(game.solution_tree)
                            except Exception:
                                logger.debug("Could not compute solution fingerprint for %s", result.puzzle_id)

                            dedup_result = self._check_dedup(
                                dedup_conn,
                                result.sgf_content,
                                source_id=source.id,
                                solution_fingerprint=sol_fp,
                            )

                            # Log all position collisions (not no_collision — too noisy)
                            if dedup_result.event_type != "no_collision":
                                logger.info(
                                    "Dedup %s: puzzle=%s position_hash=%s existing=%s",
                                    dedup_result.event_type, result.puzzle_id,
                                    dedup_result.position_hash, dedup_result.existing_hash,
                                    extra={
                                        "action": "dedup_collision",
                                        "event_type": dedup_result.event_type,
                                        "puzzle_id": result.puzzle_id,
                                        "position_hash": dedup_result.position_hash,
                                        "solution_fingerprint": dedup_result.solution_fingerprint,
                                        "existing_hash": dedup_result.existing_hash,
                                        "existing_fingerprint": dedup_result.existing_fingerprint,
                                        "existing_source": dedup_result.existing_source,
                                        "source_id": source.id,
                                    },
                                )
                                rejection_reasons[dedup_result.event_type] = (
                                    rejection_reasons.get(dedup_result.event_type, 0) + 1
                                )

                            if dedup_result.is_duplicate:
                                failed += 1
                                dup_error = (
                                    f"duplicate_of:{dedup_result.existing_hash} "
                                    f"position_hash:{dedup_result.position_hash}"
                                )
                                errors.append(
                                    f"{result.puzzle_id}: {dup_error}"
                                )
                                # Write duplicate SGF to failed directory for audit trail
                                if result.sgf_content:
                                    dup_failed_path = failed_dir / f"dup_{result.puzzle_id}.sgf"
                                    dup_failed_path.write_text(
                                        result.sgf_content, encoding="utf-8"
                                    )
                                total = processed + failed + skipped
                                if total >= batch_size:
                                    break
                                continue

                        # Validate and save
                        outcome = self._process_puzzle(
                            result, ingest_dir, failed_dir, context,
                            source_id=source.id,
                        )
                        if outcome == "processed":
                            processed += 1
                        elif outcome == "failed":
                            failed += 1
                        else:
                            skipped += 1

                    elif result.is_skipped:
                        skipped += 1
                        reason = result.error or "unknown"
                        # Track rejection by reason (Spec 108 T052/T053)
                        rejection_reasons[reason] = rejection_reasons.get(reason, 0) + 1
                        logger.log(
                            DETAIL,
                            "Skipped puzzle",
                            extra={
                                "action": "skip",
                                "puzzle_id": result.puzzle_id,
                                "source_id": source.id,
                                "reason": reason,
                            },
                        )

                    else:  # failed
                        failed += 1
                        errors.append(f"{source.id}: {result.error}")
                        logger.warning(
                            "Failed puzzle",
                            extra={
                                "action": "fail",
                                "puzzle_id": result.puzzle_id,
                                "source_id": source.id,
                                "reason": result.error or "unknown",
                            },
                        )

                    # Streaming progress
                    total = processed + failed + skipped
                    # Detailed per-puzzle progress → log file only
                    logger.debug(
                        "Progress: %d processed, %d failed, %d skipped (%d/%d)",
                        processed, failed, skipped, total, batch_size,
                        extra={
                            "action": "progress",
                            "source_id": source.id,
                            "processed": processed,
                            "failed": failed,
                            "skipped": skipped,
                            "total": total,
                            "batch_size": batch_size,
                        },
                    )
                    # Console progress: every 100 puzzles
                    if total % 100 == 0:
                        logger.info(
                            "[ingest] %d/%d — %d ok, %d failed, %d skipped",
                            total, batch_size, processed, failed, skipped,
                        )

                    # Check batch limit (count ALL attempts, including skipped)
                    if total >= batch_size:
                        break

            except Exception as e:
                logger.error(f"Source error {source.id}: {e}")
                errors.append(f"Source {source.id}: {e}")

            # Check batch limit across sources
            if processed + failed + skipped >= batch_size:
                break

        # Close dedup DB connection
        if dedup_conn is not None:
            dedup_conn.close()

        duration = time.time() - start_time

        # Build log extras with rejection breakdown (Spec 108 T052/T053)
        log_extras = {
            "source_id": source_id,
            "processed": processed,
            "failed": failed,
            "skipped": skipped,
            "duration": round(duration, 2),
        }
        if rejection_reasons:
            log_extras["rejection_reasons"] = rejection_reasons

        logger.info("Ingest complete", extra=log_extras)

        return StageResult.partial_result(
            processed=processed,
            failed=failed,
            errors=errors,
            duration=duration,
            skipped=skipped,
        )

    @staticmethod
    def _check_dedup(
        conn: sqlite3.Connection,
        sgf_content: str,
        *,
        source_id: str,
        solution_fingerprint: str,
        fingerprint_version: int = FINGERPRINT_VERSION,
    ) -> DedupResult:
        """Check if a puzzle's position already exists in the content DB.

        Uses a two-phase check:
        1. Position hash collision gate (board setup identity)
        2. Solution fingerprint comparison when same-source collision found

        Returns a DedupResult with event_type for structured logging.
        """
        pos = extract_position_data(sgf_content)
        p_hash = canonical_position_hash(
            pos["board_size"],  # type: ignore[arg-type]
            pos["black_stones"],  # type: ignore[arg-type]
            pos["white_stones"],  # type: ignore[arg-type]
            pos["first_player"],  # type: ignore[arg-type]
        )

        rows = conn.execute(
            "SELECT content_hash, source, solution_fingerprint, fingerprint_version "
            "FROM sgf_files WHERE position_hash = ?",
            (p_hash,),
        ).fetchall()

        if not rows:
            return DedupResult(
                is_duplicate=False,
                position_hash=p_hash,
                event_type="no_collision",
                solution_fingerprint=solution_fingerprint,
            )

        for existing_hash, existing_source, existing_fp, existing_fv in rows:
            if existing_source != source_id:
                continue  # Cross-source → skip (allow)
            # Same source + same position → check fingerprint
            if existing_fv != fingerprint_version:
                continue  # Version mismatch → treat as non-match (allow)
            if existing_fp == solution_fingerprint:
                return DedupResult(
                    is_duplicate=True,
                    existing_hash=existing_hash,
                    position_hash=p_hash,
                    event_type="true_duplicate",
                    solution_fingerprint=solution_fingerprint,
                    existing_fingerprint=existing_fp,
                    existing_source=existing_source,
                )

        # Position collision(s) found but no true duplicate
        has_cross_source = any(s != source_id for _, s, _, _ in rows)
        has_same_source = any(s == source_id for _, s, _, _ in rows)

        if has_same_source:
            # Same source but different fingerprint → variant
            event_type = "variant_allowed"
        elif has_cross_source:
            event_type = "cross_source_allowed"
        else:
            event_type = "variant_allowed"

        return DedupResult(
            is_duplicate=False,
            position_hash=p_hash,
            event_type=event_type,
            solution_fingerprint=solution_fingerprint,
            existing_hash=rows[0][0],
            existing_fingerprint=rows[0][2],
            existing_source=rows[0][1],
        )

    def _process_puzzle(
        self,
        result: FetchResult,
        ingest_dir: Path,
        failed_dir: Path,
        context: StageContext,
        *,
        source_id: str,
    ) -> str:
        """Process a single fetched puzzle.

        Generates trace_id per file and embeds it in the SGF via YM property
        for cross-stage correlation.

        Args:
            result: FetchResult from adapter
            ingest_dir: Directory for successful ingests
            failed_dir: Directory for failed puzzles
            context: Stage context
            source_id: Source adapter ID

        Returns:
            "processed", "failed", or "skipped"
        """
        if not result.sgf_content or not result.puzzle_id:
            logger.log(
                DETAIL,
                "Skipped puzzle",
                extra={
                    "action": "skip",
                    "puzzle_id": result.puzzle_id or "unknown",
                    "source_id": source_id,
                    "reason": "missing sgf_content or puzzle_id",
                },
            )
            return "skipped"

        # Generate trace_id at file entry point
        trace_id = generate_trace_id()
        source_file = result.puzzle_id  # adapter's identifier for the source file

        # Extract original filename from source_link for traceability
        # e.g., "C:\...\45.sgf" -> "45.sgf", or URL -> last segment
        original_filename: str = ""
        if result.source_link:
            original_filename = Path(result.source_link).name

        # Create trace-aware logger for this file
        trace_logger = create_trace_logger(
            run_id=context.run_id,
            source_id=source_id,
            trace_id=trace_id,
        )

        try:
            # Parse and validate SGF
            game = parse_sgf(result.sgf_content)

            # Validate has solution
            if not game.has_solution:
                trace_logger.log(
                    DETAIL,
                    "Failed puzzle",
                    extra={
                        "action": "fail",
                        "puzzle_id": result.puzzle_id,
                        "reason": "No solution found in SGF",
                    },
                )
                self._save_failed(result, failed_dir, "No solution found", context, trace_id=trace_id)

                return "failed"

            # v13: Source adapter ID tracked via context, not embedded in YM
            game.yengo_props.source = source_id
            builder = SGFBuilder.from_game(game)
            # Embed trace_id, original_filename into YM (v13)
            builder.set_pipeline_meta(trace_id, original_filename)
            enriched_content = builder.build()

            # Save to ingest directory
            output_path = ingest_dir / f"{result.puzzle_id}.sgf"
            if not context.dry_run:
                output_path.write_text(enriched_content, encoding="utf-8")
            else:
                trace_logger.info(f"[DRY-RUN] Would write: {to_relative_path(output_path)}")

            trace_logger.log(
                DETAIL,
                "Ingested puzzle",
                extra={
                    "action": "ingest",
                    "puzzle_id": result.puzzle_id,
                    "source_file": source_file,
                    "output_file": output_path.name,
                    "original_filename": original_filename,
                },
            )

            return "processed"

        except SGFParseError as e:
            trace_logger.log(DETAIL, f"Parse error for {result.puzzle_id}: {e}")
            self._save_failed(result, failed_dir, str(e), context, trace_id=trace_id)

            return "failed"

        except Exception as e:
            trace_logger.warning(f"Error processing {result.puzzle_id}: {e}")
            self._save_failed(result, failed_dir, str(e), context, trace_id=trace_id)

            return "failed"

    def _save_failed(
        self,
        result: FetchResult,
        failed_dir: Path,
        reason: str,
        context: StageContext,
        *,
        trace_id: str | None = None,
    ) -> None:
        """Save failed puzzle for debugging.

        Args:
            result: FetchResult from adapter
            failed_dir: Directory for failed puzzles
            reason: Failure reason
            context: Stage context
            trace_id: Optional trace_id for logging (Spec 110)
        """
        if result.sgf_content and result.puzzle_id:
            failed_path = failed_dir / f"{result.puzzle_id}.sgf"
            error_path = failed_dir / f"{result.puzzle_id}.error"

            if not context.dry_run:
                failed_path.write_text(result.sgf_content, encoding="utf-8")
                # Include trace_id in error file for debugging
                error_content = reason
                if trace_id:
                    error_content = f"trace_id: {trace_id}\n{reason}"
                error_path.write_text(error_content, encoding="utf-8")
            else:
                logger.info(f"[DRY-RUN] Would write: {to_relative_path(failed_path)}")
                logger.info(f"[DRY-RUN] Would write: {to_relative_path(error_path)}")
