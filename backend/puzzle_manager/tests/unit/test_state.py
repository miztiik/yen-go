"""Unit tests for state manager module."""

import logging
import re
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

from backend.puzzle_manager.state.manager import StateManager
from backend.puzzle_manager.tests.fixtures.run_id import RUN_ID_PATTERN


class TestStateManager:
    """Tests for StateManager class."""

    def test_state_manager_creates(self, tmp_path: Path) -> None:
        """StateManager should be creatable."""
        manager = StateManager(state_dir=tmp_path)
        assert manager is not None

    def test_state_manager_has_state_dir(self, tmp_path: Path) -> None:
        """StateManager should have state_dir property."""
        manager = StateManager(state_dir=tmp_path)
        assert manager.state_dir == tmp_path


class TestStateManagerOperations:
    """Tests for state manager operations."""

    def test_create_run_returns_state(self, tmp_path: Path) -> None:
        """create_run should return run state."""
        manager = StateManager(state_dir=tmp_path)
        state = manager.create_run()

        assert state is not None
        assert state.run_id is not None

    def test_load_current_returns_none_initially(self, tmp_path: Path) -> None:
        """load_current should return None if no state exists."""
        manager = StateManager(state_dir=tmp_path)
        manager.init()

        state = manager.load_current()
        assert state is None

    def test_save_and_load_current(self, tmp_path: Path) -> None:
        """State should be saveable and loadable."""
        manager = StateManager(state_dir=tmp_path)

        # Create and save state
        state = manager.create_run()
        manager.save_current(state)

        # Load should return same state
        loaded = manager.load_current()
        assert loaded is not None
        assert loaded.run_id == state.run_id


class TestRunIdFormat:
    """Tests for run_id format (spec-041)."""

    def test_run_id_format_is_date_prefixed(self, tmp_path: Path) -> None:
        """run_id should be in YYYYMMDD-xxxxxxxx format."""
        manager = StateManager(state_dir=tmp_path)
        state = manager.create_run()

        # Format: YYYYMMDD-xxxxxxxx (8 digits, hyphen, 8 hex chars)
        assert re.match(r"^[0-9]{8}-[a-f0-9]{8}$", state.run_id), \
            f"run_id '{state.run_id}' does not match expected format YYYYMMDD-xxxxxxxx"

    def test_run_id_matches_validation_pattern(self, tmp_path: Path) -> None:
        """run_id should match the validation pattern."""
        manager = StateManager(state_dir=tmp_path)
        state = manager.create_run()

        assert re.match(RUN_ID_PATTERN, state.run_id), \
            f"run_id '{state.run_id}' does not match pattern {RUN_ID_PATTERN}"

    def test_run_id_date_prefix_is_utc(self, tmp_path: Path) -> None:
        """run_id date prefix should use UTC timezone."""
        manager = StateManager(state_dir=tmp_path)
        state = manager.create_run()

        # Extract date from run_id
        date_str = state.run_id[:8]  # YYYYMMDD
        run_date = datetime.strptime(date_str, "%Y%m%d").date()

        # Get current UTC date
        utc_today = datetime.now(UTC).date()

        # Should match UTC date (allow 1 day tolerance for test execution near midnight)
        date_diff = abs((run_date - utc_today).days)
        assert date_diff <= 1, \
            f"run_id date {run_date} differs from UTC today {utc_today} by {date_diff} days"

    def test_run_id_is_unique(self, tmp_path: Path) -> None:
        """Multiple run_ids should be unique."""
        manager = StateManager(state_dir=tmp_path)

        run_ids = [manager.create_run().run_id for _ in range(100)]

        assert len(run_ids) == len(set(run_ids)), "run_ids should be unique"


class TestDateAnomalyWarning:
    """Tests for date anomaly warning (spec-041 FR-004)."""

    def test_warning_logged_for_date_before_2024(self, tmp_path: Path, caplog) -> None:
        """Warning should be logged if system date is before 2024-01-01."""
        manager = StateManager(state_dir=tmp_path)

        # Mock datetime.now to return a date before 2024
        past_date = datetime(2023, 6, 15, tzinfo=UTC)

        with patch('backend.puzzle_manager.state.manager.datetime') as mock_dt:
            mock_dt.now.return_value = past_date
            mock_dt.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

            with caplog.at_level(logging.WARNING, logger="puzzle_manager.state"):
                manager.create_run()

        # Check warning was logged
        assert any("before minimum valid date" in record.message
                   for record in caplog.records), \
            "Expected warning about date before minimum valid date"

    def test_no_warning_for_normal_date(self, tmp_path: Path, caplog) -> None:
        """No warning should be logged for normal dates."""
        manager = StateManager(state_dir=tmp_path)

        with caplog.at_level(logging.WARNING, logger="puzzle_manager.state"):
            manager.create_run()

        # Check no warning about date anomaly
        assert not any("Check system clock" in record.message
                       for record in caplog.records), \
            "Unexpected warning about system clock"


class TestSkippedStages:
    """Tests for marking unrequested stages as SKIPPED (spec-043)."""

    def test_skipped_stages_marked_correctly(self, tmp_path: Path) -> None:
        """Unrequested stages should be marked as SKIPPED after run completion."""
        manager = StateManager(state_dir=tmp_path)

        # Start a run
        manager.start_run()

        # Simulate only running ingest stage
        manager.start_stage("ingest")
        manager.complete_stage("ingest", processed=10, failed=0)

        # Complete run with only ingest requested
        manager.complete_run(processed=10, failed=0, requested_stages=["ingest"])

        # Load archived state
        history = manager.get_history(limit=1)
        assert len(history) == 1
        state = history[0]

        # Verify stage statuses
        stages = {s.name: s.status.value for s in state.stages}
        assert stages["ingest"] == "completed", "Ingest should be completed"
        assert stages["analyze"] == "skipped", "Analyze should be skipped"
        assert stages["publish"] == "skipped", "Publish should be skipped"

    def test_all_stages_completed_when_all_requested(self, tmp_path: Path) -> None:
        """All stages should be completed when all are requested."""
        manager = StateManager(state_dir=tmp_path)

        # Start a run
        manager.start_run()

        # Run all stages
        for stage in ["ingest", "analyze", "publish"]:
            manager.start_stage(stage)
            manager.complete_stage(stage, processed=5, failed=0)

        # Complete run with all stages requested
        manager.complete_run(processed=15, failed=0, requested_stages=["ingest", "analyze", "publish"])

        # Load archived state
        history = manager.get_history(limit=1)
        state = history[0]

        # All stages should be completed
        for stage in state.stages:
            assert stage.status.value == "completed", f"Stage {stage.name} should be completed"


class TestConfigSnapshot:
    """Tests for config_snapshot population (spec-043)."""

    def test_config_snapshot_populated_on_start(self, tmp_path: Path) -> None:
        """Config snapshot should be populated when run starts."""
        manager = StateManager(state_dir=tmp_path)

        config = {
            "source_id": "sanderland",
            "batch_size": 2,
            "dry_run": False,
        }

        manager.start_run(config_snapshot=config)

        # Load current state
        state = manager.load_current()
        assert state is not None
        assert state.config_snapshot is not None
        assert state.config_snapshot["source_id"] == "sanderland"
        assert state.config_snapshot["batch_size"] == 2
        assert state.config_snapshot["dry_run"] is False

    def test_config_snapshot_preserved_in_archive(self, tmp_path: Path) -> None:
        """Config snapshot should be preserved when run is archived."""
        manager = StateManager(state_dir=tmp_path)

        config = {
            "source_id": "goproblems",
            "batch_size": 2,
            "dry_run": True,
        }

        manager.start_run(config_snapshot=config)
        manager.complete_run(processed=0, failed=0, requested_stages=["ingest"])

        # Load archived state
        history = manager.get_history(limit=1)
        state = history[0]

        assert state.config_snapshot is not None
        assert state.config_snapshot["source_id"] == "goproblems"
        assert state.config_snapshot["batch_size"] == 2
        assert state.config_snapshot["dry_run"] is True
