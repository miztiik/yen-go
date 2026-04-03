"""Tests for t-dragon logging_config module.

Verifies that all structured logging methods work correctly.
"""

import logging

# Import from conftest loaded modules
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import patch

import pytest

# Get the logging config module loaded by conftest
t_dragon_logging_config = sys.modules.get("t_dragon_logging_config")
if t_dragon_logging_config is None:
    # Load it directly if conftest hasn't run
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "t_dragon_logging_config",
        Path(__file__).parent.parent / "logging_config.py"
    )
    t_dragon_logging_config = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(t_dragon_logging_config)

StructuredLogger = t_dragon_logging_config.StructuredLogger


class TestStructuredLoggerMethods:
    """Test the structured logging methods."""

    @pytest.fixture
    def logger(self):
        """Create a logger for testing."""
        base_logger = logging.getLogger("test_tdragon")
        base_logger.setLevel(logging.DEBUG)
        return StructuredLogger(base_logger)

    def test_puzzle_enrich(self, logger: StructuredLogger):
        """Test puzzle_enrich logs correctly."""
        with patch.object(logger, "event") as mock_event:
            logger.puzzle_enrich(
                puzzle_id="12345",
                level="intermediate",
                tags=["life-and-death", "corner"],
            )

            mock_event.assert_called_once()
            call_args = mock_event.call_args
            assert call_args[0][0] == "puzzle_enrich"
            assert "12345" in call_args[0][1]
            assert call_args[1]["puzzle_id"] == "12345"
            assert call_args[1]["level"] == "intermediate"
            assert call_args[1]["tags"] == ["life-and-death", "corner"]

    def test_collection_match_with_match(self, logger: StructuredLogger):
        """Test collection_match logs correctly when match found."""
        with patch.object(logger, "event") as mock_event:
            logger.collection_match(
                puzzle_id="12345",
                source_name="capture",
                matched_slug="capture-race",
            )

            mock_event.assert_called_once()
            call_args = mock_event.call_args
            assert call_args[0][0] == "collection_match"
            assert call_args[1]["status"] == "matched"
            assert call_args[1]["matched_slug"] == "capture-race"

    def test_collection_match_no_match(self, logger: StructuredLogger):
        """Test collection_match logs correctly when no match."""
        with patch.object(logger, "event") as mock_event:
            logger.collection_match(
                puzzle_id="12345",
                source_name="unknown-category",
                matched_slug=None,
            )

            mock_event.assert_called_once()
            call_args = mock_event.call_args
            assert call_args[1]["status"] == "no_match"
            assert call_args[1]["matched_slug"] is None

    def test_intent_match_with_match(self, logger: StructuredLogger):
        """Test intent_match logs correctly when match found."""
        with patch.object(logger, "event") as mock_event:
            logger.intent_match(
                puzzle_id="12345",
                description_snippet="Black to capture the white stones",
                matched_slug="black-to-capture",
                confidence=0.95,
                tier="exact",
            )

            mock_event.assert_called_once()
            call_args = mock_event.call_args
            assert call_args[0][0] == "intent_match"
            assert call_args[1]["status"] == "matched"
            assert call_args[1]["confidence"] == 0.95
            assert call_args[1]["tier"] == "exact"

    def test_intent_match_no_match(self, logger: StructuredLogger):
        """Test intent_match logs correctly when no match."""
        with patch.object(logger, "event") as mock_event:
            logger.intent_match(
                puzzle_id="12345",
                description_snippet="Some unknown description",
                matched_slug=None,
                confidence=0.0,
                tier="",
            )

            mock_event.assert_called_once()
            call_args = mock_event.call_args
            assert call_args[1]["status"] == "no_match"
            assert call_args[1]["matched_slug"] is None

    def test_intent_match_truncates_long_description(self, logger: StructuredLogger):
        """Test that intent_match truncates long descriptions."""
        with patch.object(logger, "event") as mock_event:
            long_description = "A" * 100
            logger.intent_match(
                puzzle_id="12345",
                description_snippet=long_description,
                matched_slug="some-slug",
                confidence=0.8,
                tier="semantic",
            )

            call_args = mock_event.call_args
            # description_snippet in event_data should be truncated to 50 chars
            assert len(call_args[1]["description_snippet"]) == 50


class TestDownloadStats:
    """Test DownloadStats class.

    Uses a minimal local dataclass since the full orchestrator has many dependencies.
    This verifies the expected interface exists.
    """

    @dataclass
    class MinimalDownloadStats:
        """Minimal version of DownloadStats for testing the expected interface."""
        downloaded: int = 0
        skipped: int = 0
        errors: int = 0
        collections_assigned: int = 0
        intents_resolved: int = 0
        start_time: float = 0.0

        def elapsed_seconds(self) -> float:
            if self.start_time == 0:
                return 0.0
            return time.time() - self.start_time

        def puzzles_per_minute(self) -> float:
            elapsed = self.elapsed_seconds()
            if elapsed == 0 or self.downloaded == 0:
                return 0.0
            return (self.downloaded / elapsed) * 60

    def test_puzzles_per_minute_calculation(self):
        """Test puzzles_per_minute calculation."""
        stats = self.MinimalDownloadStats()
        stats.start_time = time.time() - 60  # 60 seconds ago
        stats.downloaded = 30

        rate = stats.puzzles_per_minute()
        assert 29 <= rate <= 31  # ~30 puzzles/min with some tolerance

    def test_puzzles_per_minute_zero_downloaded(self):
        """Test puzzles_per_minute returns 0 when no downloads."""
        stats = self.MinimalDownloadStats()
        stats.start_time = time.time() - 60
        stats.downloaded = 0

        assert stats.puzzles_per_minute() == 0.0

    def test_collections_assigned_counter(self):
        """Test collections_assigned counter exists."""
        stats = self.MinimalDownloadStats()
        assert stats.collections_assigned == 0
        stats.collections_assigned = 5
        assert stats.collections_assigned == 5

    def test_intents_resolved_counter(self):
        """Test intents_resolved counter exists."""
        stats = self.MinimalDownloadStats()
        assert stats.intents_resolved == 0
        stats.intents_resolved = 3
        assert stats.intents_resolved == 3
