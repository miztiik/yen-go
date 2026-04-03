"""
State manager for pipeline execution tracking.

Provides persistence for run state with JSON files.
"""

import json
import logging
import secrets
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from backend.puzzle_manager.core.atomic_write import atomic_write_text
from backend.puzzle_manager.exceptions import StateLoadError, StateSaveError
from backend.puzzle_manager.models.enums import RunStatus
from backend.puzzle_manager.paths import ensure_runtime_dirs, rel_path
from backend.puzzle_manager.state.models import Failure, RunState

logger = logging.getLogger("puzzle_manager.state")

# Date boundaries for anomaly detection
_MIN_VALID_DATE = datetime(2024, 1, 1, tzinfo=UTC)
_MAX_FUTURE_DAYS = 1


class StateManager:
    """Manager for pipeline run state persistence.

    Implements StateManagerProtocol from contracts/state-manager.md.
    """

    def __init__(self, state_dir: Path) -> None:
        """Initialize state manager.

        Args:
            state_dir: State directory (REQUIRED)
        """
        self._state_dir = state_dir
        self._initialized = False

    @property
    def state_dir(self) -> Path:
        """Get state directory."""
        return self._state_dir

    @property
    def current_path(self) -> Path:
        """Path to current run state file."""
        return self.state_dir / "current_run.json"

    @property
    def runs_dir(self) -> Path:
        """Path to archived runs directory."""
        return self.state_dir / "runs"

    @property
    def failures_dir(self) -> Path:
        """Path to failures directory."""
        return self.state_dir / "failures"

    def init(self) -> None:
        """Initialize runtime directories.

        Creates pm_staging/, pm_state/, and logs/ directories.
        Safe to call multiple times.
        """
        if self._initialized:
            return

        ensure_runtime_dirs()
        self._initialized = True
        logger.debug("State manager initialized runtime directories")

    def create_run(self, config_snapshot: dict[str, Any] | None = None) -> RunState:
        """Create a new run state.

        Args:
            config_snapshot: Configuration to snapshot.

        Returns:
            New RunState with unique ID in format YYYYMMDD-xxxxxxxx.
        """
        self.init()

        now = datetime.now(UTC)

        # Check for date anomalies (system clock issues)
        self._check_date_anomaly(now)

        # Generate run_id: YYYYMMDD-xxxxxxxx (date prefix + 8 hex chars)
        run_id = f"{now:%Y%m%d}-{secrets.token_hex(4)}"
        state = RunState(
            run_id=run_id,
            config_snapshot=config_snapshot,
        )

        logger.info(f"Created new run: {run_id}")
        return state

    def _check_date_anomaly(self, now: datetime) -> None:
        """Log warning if system date appears anomalous.

        Args:
            now: Current timestamp to check.
        """
        from datetime import timedelta

        # Check for date too far in the past
        if now < _MIN_VALID_DATE:
            logger.warning(
                f"System date {now.date()} is before minimum valid date "
                f"({_MIN_VALID_DATE.date()}). Check system clock."
            )
            return

        # Check for date too far in the future
        max_valid = datetime.now(UTC) + timedelta(days=_MAX_FUTURE_DAYS)
        if now > max_valid:
            logger.warning(
                f"System date {now.date()} appears to be in the future "
                f"(> {_MAX_FUTURE_DAYS} day ahead). Check system clock."
            )

    def load_current(self) -> RunState | None:
        """Load current run state.

        Returns:
            RunState if exists, None otherwise.

        Raises:
            StateLoadError: If state file is corrupted.
        """
        self.init()

        if not self.current_path.exists():
            return None

        try:
            data = json.loads(self.current_path.read_text(encoding="utf-8"))
            return RunState.model_validate(data)
        except json.JSONDecodeError as e:
            raise StateLoadError(
                f"Invalid JSON in state file: {e}",
                context={"path": str(self.current_path)},
            ) from e
        except Exception as e:
            raise StateLoadError(
                f"Failed to load state: {e}",
                context={"path": str(self.current_path)},
            ) from e

    def save_current(self, state: RunState) -> None:
        """Save current run state.

        Args:
            state: RunState to persist.

        Raises:
            StateSaveError: If save fails.
        """
        self.init()

        try:
            self.state_dir.mkdir(parents=True, exist_ok=True)
            atomic_write_text(
                self.current_path,
                state.model_dump_json(indent=2),
            )
            logger.debug(f"Saved state for run {state.run_id}")
        except Exception as e:
            raise StateSaveError(
                f"Failed to save state: {e}",
                context={"path": str(self.current_path), "run_id": state.run_id},
            ) from e

    def archive(self, state: RunState) -> None:
        """Archive completed run and clear current.

        Args:
            state: Completed RunState to archive.
        """
        self.init()
        self.runs_dir.mkdir(parents=True, exist_ok=True)

        # Create archive filename with datetime prefix for sorting (YYYYMMDD-HHMMSS)
        datetime_prefix = state.started_at.strftime("%Y%m%d-%H%M%S")
        archive_path = self.runs_dir / f"{datetime_prefix}_{state.run_id}.json"

        try:
            archive_path.write_text(
                state.model_dump_json(indent=2),
                encoding="utf-8",
            )
            logger.info(f"Archived run {state.run_id} to {archive_path.name}")

            # Save failures if any
            if state.failures:
                self._save_failures(state)

            # Clear current run
            self.current_path.unlink(missing_ok=True)
        except Exception as e:
            raise StateSaveError(
                f"Failed to archive state: {e}",
                context={"path": str(archive_path), "run_id": state.run_id},
            ) from e

    def _save_failures(self, state: RunState) -> None:
        """Save failure records to separate file."""
        self.failures_dir.mkdir(parents=True, exist_ok=True)
        failures_path = self.failures_dir / f"{state.run_id}.json"

        failures_data = [f.model_dump(mode="json") for f in state.failures]
        failures_path.write_text(
            json.dumps(failures_data, indent=2, default=str),
            encoding="utf-8",
        )

    def get_history(self, limit: int = 10) -> list[RunState]:
        """Get recent run history.

        Args:
            limit: Maximum runs to return.

        Returns:
            List of RunState, most recent first.
        """
        self.init()

        if not self.runs_dir.exists():
            return []

        files = sorted(self.runs_dir.glob("*.json"), reverse=True)
        results = []

        for path in files[:limit]:
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                results.append(RunState.model_validate(data))
            except Exception as e:
                logger.warning(f"Failed to load history file {rel_path(path)}: {e}")
                continue

        return results

    def cleanup(self, max_age_days: int) -> int:
        """Remove archived runs older than max_age_days.

        Args:
            max_age_days: Maximum age in days.

        Returns:
            Number of files deleted.
        """
        self.init()

        if max_age_days < 1:
            raise ValueError("max_age_days must be at least 1")

        deleted = 0
        cutoff = datetime.now(UTC).timestamp() - (max_age_days * 86400)

        for path in self.runs_dir.glob("*.json"):
            if path.stat().st_mtime < cutoff:
                path.unlink()
                deleted += 1
                logger.debug(f"Deleted old state file: {path.name}")

        # Also clean up failure files
        for path in self.failures_dir.glob("*.json"):
            if path.stat().st_mtime < cutoff:
                path.unlink()
                deleted += 1

        if deleted > 0:
            logger.info(f"Cleaned up {deleted} old state files")

        return deleted

    def record_failure(
        self,
        state: RunState,
        item_id: str,
        stage: str,
        error: Exception,
        source_path: str | None = None,
    ) -> Failure:
        """Record a failure and add to state.

        Args:
            state: Current run state.
            item_id: Failed item identifier.
            stage: Stage where failure occurred.
            error: The exception that occurred.
            source_path: Original source path.

        Returns:
            Created Failure record.
        """
        failure = Failure(
            item_id=item_id,
            stage=stage,
            error_type=type(error).__name__,
            error_message=str(error),
            source_path=source_path,
        )

        state.add_failure(failure)
        self.save_current(state)

        return failure

    def start_run(self, config_snapshot: dict[str, Any] | None = None) -> str:
        """Start a new run and persist it.

        Args:
            config_snapshot: Configuration to snapshot.

        Returns:
            Run ID of the new run.
        """
        state = self.create_run(config_snapshot)
        state.status = RunStatus.RUNNING
        self.save_current(state)
        return state.run_id

    def update_resolved_paths(self, paths: list[str]) -> None:
        """Update config_snapshot with resolved SGF paths.

        Spec 105: Replace template placeholders with actual paths written.

        Args:
            paths: List of resolved SGF paths (e.g., ["sgf/intermediate/batch-0001"])
        """
        state = self.load_current()
        if not state:
            logger.warning("No current run to update resolved paths")
            return

        if state.config_snapshot and "output" in state.config_snapshot:
            # Replace sgf_path template with resolved paths list
            state.config_snapshot["output"]["sgf_paths_resolved"] = paths
            # Remove the template placeholder since we now have resolved paths
            state.config_snapshot["output"].pop("sgf_path", None)
            self.save_current(state)
            logger.debug(f"Updated config_snapshot with {len(paths)} resolved paths")

    def complete_run(self, processed: int = 0, failed: int = 0, requested_stages: list[str] | None = None) -> None:
        """Complete the current run and archive it.

        Args:
            processed: Number of items processed.
            failed: Number of items that failed.
            requested_stages: List of stages that were requested to run.
                             Stages not in this list will be marked as SKIPPED.
        """
        state = self.load_current()
        if not state:
            logger.warning("No current run to complete")
            return

        # Mark unrequested stages as skipped (spec-043: fix stage status bug)
        if requested_stages is not None:
            self._mark_skipped_stages(state, requested_stages)

        state.status = RunStatus.COMPLETED if failed == 0 else RunStatus.FAILED
        state.completed_at = datetime.now(UTC)

        self.archive(state)

    def _mark_skipped_stages(self, state: RunState, requested_stages: list[str]) -> None:
        """Mark stages not in requested list as SKIPPED.

        This fixes the bug where unrequested stages show 'pending' status
        after run completion. When only specific stages are run (e.g., --stages ingest),
        the other stages should be marked as 'skipped' not 'pending'.

        Args:
            state: Current run state to modify.
            requested_stages: List of stage names that were requested to run.
        """
        for stage in state.stages:
            if stage.name not in requested_stages and stage.status == RunStatus.PENDING:
                stage.status = RunStatus.SKIPPED
                logger.debug(f"Marked stage '{stage.name}' as skipped (not in requested stages)")

    def load_state(self) -> "PipelineState":
        """Load full pipeline state.

        Returns:
            PipelineState with current run, last run, and history.
        """
        self.init()

        history = self.get_history()
        current = self.load_current()
        last_run = history[0] if history else None

        return PipelineState(
            current_run=current,
            last_run=last_run,
            history=history,
        )

    def get_current_run(self) -> RunState | None:
        """Get current run state, creating if needed.

        Returns:
            Current RunState or None.
        """
        return self.load_current()

    def start_stage(self, stage_name: str) -> None:
        """Mark a stage as started in current run state.

        Args:
            stage_name: Name of the stage being started.
        """
        state = self.load_current()
        if state:
            stage = state.get_stage(stage_name)
            if stage:
                stage.start()
                self.save_current(state)
                logger.debug(f"Started stage: {stage_name}")

    def complete_stage(
        self,
        stage_name: str,
        processed: int,
        failed: int,
        error: str | None = None,
        skipped: int = 0,
    ) -> None:
        """Mark a stage as complete in current run state.

        Args:
            stage_name: Name of the completed stage.
            processed: Number of items processed.
            failed: Number of items that failed.
            error: Error message if stage failed.
            skipped: Number of items skipped (e.g., duplicates).
        """
        state = self.load_current()
        if state:
            stage = state.get_stage(stage_name)
            if stage:
                stage.processed_count = processed
                stage.failed_count = failed
                stage.skipped_count = skipped
                if error:
                    stage.fail()
                else:
                    stage.complete()
                self.save_current(state)
                logger.debug(f"Completed stage: {stage_name} (processed={processed}, failed={failed}, skipped={skipped})")


class PipelineState:
    """Combined pipeline state for status display."""

    def __init__(
        self,
        current_run: RunState | None = None,
        last_run: RunState | None = None,
        history: list[RunState] | None = None,
    ):
        self.current_run = current_run
        self.last_run = last_run
        self.history = history or []
