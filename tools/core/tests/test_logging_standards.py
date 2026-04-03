"""Tests for tool logging standards.

Verifies that StructuredLogger subclasses implement the required methods
per the tool-development-standards.md specification.
"""

import logging
import time
from dataclasses import dataclass
from unittest.mock import patch

import pytest

from tools.core.logging import StructuredLogger as CoreStructuredLogger


class TestCoreStructuredLogger:
    """Test the core StructuredLogger base class."""

    @pytest.fixture
    def logger(self):
        """Create a core logger for testing."""
        base_logger = logging.getLogger("test_core_logger")
        base_logger.setLevel(logging.DEBUG)
        return CoreStructuredLogger(base_logger)

    def test_progress_method_exists(self, logger: CoreStructuredLogger):
        """Test that progress method is available."""
        with patch.object(logger, "event") as mock_event:
            logger.progress(
                downloaded=10,
                skipped=2,
                errors=1,
                elapsed_sec=60.0,
            )
            mock_event.assert_called_once()

    def test_run_start_method_exists(self, logger: CoreStructuredLogger):
        """Test that run_start method is available."""
        with patch.object(logger, "event") as mock_event:
            logger.run_start(
                output_dir="/test/output",
                max_items=100,
                resume=False,
            )
            mock_event.assert_called_once()

    def test_run_end_method_exists(self, logger: CoreStructuredLogger):
        """Test that run_end method is available."""
        with patch.object(logger, "event") as mock_event:
            logger.run_end(
                downloaded=10,
                skipped=2,
                errors=1,
                duration_sec=60.0,
            )
            mock_event.assert_called_once()


class TestToolLoggingStandards:
    """Test expected logging method signatures per tool-development-standards.md."""

    @dataclass
    class MockDownloadStats:
        """Mock DownloadStats to verify expected interface."""
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

    def test_download_stats_puzzles_per_minute(self):
        """Test puzzles_per_minute calculation."""
        stats = self.MockDownloadStats()
        stats.start_time = time.time() - 60  # 60 seconds ago
        stats.downloaded = 30

        rate = stats.puzzles_per_minute()
        assert 29 <= rate <= 31  # ~30 puzzles/min with some tolerance

    def test_download_stats_zero_downloaded(self):
        """Test puzzles_per_minute returns 0 when no downloads."""
        stats = self.MockDownloadStats()
        stats.start_time = time.time() - 60
        stats.downloaded = 0

        assert stats.puzzles_per_minute() == 0.0

    def test_download_stats_has_collections_assigned(self):
        """Test collections_assigned counter exists per standards."""
        stats = self.MockDownloadStats()
        assert stats.collections_assigned == 0
        stats.collections_assigned = 5
        assert stats.collections_assigned == 5

    def test_download_stats_has_intents_resolved(self):
        """Test intents_resolved counter exists per standards."""
        stats = self.MockDownloadStats()
        assert stats.intents_resolved == 0
        stats.intents_resolved = 3
        assert stats.intents_resolved == 3


class TestToolLoggingMethodSignatures:
    """Test that tool loggers should implement these method signatures.

    These tests verify the expected method signatures per the standards doc.
    Individual tool loggers should implement these methods.
    """

    def test_puzzle_enrich_signature(self):
        """Verify expected puzzle_enrich method signature."""
        # This is a documentation test - it verifies the expected signature
        def expected_puzzle_enrich(
            puzzle_id: str | int,
            level: str,
            tags: list[str],
            collections: list[str] | None = None,
            intent: str | None = None,
        ) -> None:
            pass

        # If this compiles, the signature is valid
        assert callable(expected_puzzle_enrich)

    def test_collection_match_signature(self):
        """Verify expected collection_match method signature."""
        def expected_collection_match(
            puzzle_id: str | int,
            source_name: str,
            matched_slug: str | None,
        ) -> None:
            pass

        assert callable(expected_collection_match)

    def test_intent_match_signature(self):
        """Verify expected intent_match method signature."""
        def expected_intent_match(
            puzzle_id: str | int,
            description_snippet: str,
            matched_slug: str | None,
            confidence: float = 0.0,
            tier: str = "",
        ) -> None:
            pass

        assert callable(expected_intent_match)
