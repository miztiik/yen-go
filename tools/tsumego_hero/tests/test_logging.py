"""Tests for tsumego_hero logging_config module.

Verifies that all structured logging methods work correctly.
"""

import logging
from unittest.mock import patch

import pytest

from tools.tsumego_hero.logging_config import StructuredLogger


class TestStructuredLoggerMethods:
    """Test the structured logging methods."""

    @pytest.fixture
    def logger(self):
        """Create a logger for testing."""
        base_logger = logging.getLogger("test_tsumego_hero")
        base_logger.setLevel(logging.DEBUG)
        return StructuredLogger(base_logger)

    def test_puzzle_enrich(self, logger: StructuredLogger):
        """Test puzzle_enrich logs correctly."""
        with patch.object(logger, "event") as mock_event:
            logger.puzzle_enrich(
                puzzle_id=12345,
                level="intermediate",
                tags=["life-and-death", "corner"],
                collections=["cho-chikun-elementary"],
                intent="black-to-kill",
            )

            mock_event.assert_called_once()
            call_args = mock_event.call_args
            assert call_args[0][0] == "puzzle_enrich"
            assert "12345" in call_args[0][1]
            assert call_args[1]["puzzle_id"] == 12345
            assert call_args[1]["level"] == "intermediate"
            assert call_args[1]["tags"] == ["life-and-death", "corner"]
            assert call_args[1]["collections"] == ["cho-chikun-elementary"]
            assert call_args[1]["intent"] == "black-to-kill"

    def test_puzzle_enrich_with_none_values(self, logger: StructuredLogger):
        """Test puzzle_enrich handles None values."""
        with patch.object(logger, "event") as mock_event:
            logger.puzzle_enrich(
                puzzle_id=12345,
                level="beginner",
                tags=["tesuji"],
                collections=None,
                intent=None,
            )

            call_args = mock_event.call_args
            assert call_args[1]["collections"] == []
            assert call_args[1]["intent"] == ""

    def test_collection_match_with_match(self, logger: StructuredLogger):
        """Test collection_match logs correctly when match found."""
        with patch.object(logger, "event") as mock_event:
            logger.collection_match(
                puzzle_id=12345,
                source_name="Cho Chikun Vol 1",
                matched_slug="cho-chikun-elementary",
            )

            mock_event.assert_called_once()
            call_args = mock_event.call_args
            assert call_args[0][0] == "collection_match"
            assert call_args[1]["status"] == "matched"
            assert call_args[1]["matched_slug"] == "cho-chikun-elementary"

    def test_collection_match_no_match(self, logger: StructuredLogger):
        """Test collection_match logs correctly when no match."""
        with patch.object(logger, "event") as mock_event:
            logger.collection_match(
                puzzle_id=12345,
                source_name="Unknown Collection",
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
                puzzle_id=12345,
                description_snippet="Black to kill the white group",
                matched_slug="black-to-kill",
                confidence=0.92,
                tier="keyword",
            )

            mock_event.assert_called_once()
            call_args = mock_event.call_args
            assert call_args[0][0] == "intent_match"
            assert call_args[1]["status"] == "matched"
            assert call_args[1]["confidence"] == 0.92
            assert call_args[1]["tier"] == "keyword"

    def test_intent_match_no_match(self, logger: StructuredLogger):
        """Test intent_match logs correctly when no match."""
        with patch.object(logger, "event") as mock_event:
            logger.intent_match(
                puzzle_id=12345,
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
                puzzle_id=12345,
                description_snippet=long_description,
                matched_slug="some-slug",
                confidence=0.8,
                tier="semantic",
            )

            call_args = mock_event.call_args
            # description_snippet in event_data should be truncated to 50 chars
            assert len(call_args[1]["description_snippet"]) == 50


class TestDownloadStats:
    """Test DownloadStats class."""

    def test_puzzles_per_minute_calculation(self):
        """Test puzzles_per_minute calculation."""
        import time

        from tools.tsumego_hero.orchestrator import DownloadStats

        stats = DownloadStats()
        stats.start_time = time.time() - 60  # 60 seconds ago
        stats.downloaded = 30

        rate = stats.puzzles_per_minute()
        assert 29 <= rate <= 31  # ~30 puzzles/min with some tolerance

    def test_puzzles_per_minute_zero_downloaded(self):
        """Test puzzles_per_minute returns 0 when no downloads."""
        import time

        from tools.tsumego_hero.orchestrator import DownloadStats

        stats = DownloadStats()
        stats.start_time = time.time() - 60
        stats.downloaded = 0

        assert stats.puzzles_per_minute() == 0.0

    def test_collections_assigned_counter(self):
        """Test collections_assigned counter exists."""
        from tools.tsumego_hero.orchestrator import DownloadStats

        stats = DownloadStats()
        assert stats.collections_assigned == 0
        stats.collections_assigned = 5
        assert stats.collections_assigned == 5

    def test_intents_resolved_counter(self):
        """Test intents_resolved counter exists."""
        from tools.tsumego_hero.orchestrator import DownloadStats

        stats = DownloadStats()
        assert stats.intents_resolved == 0
        stats.intents_resolved = 3
        assert stats.intents_resolved == 3
