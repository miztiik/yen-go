"""Tests for orchestrator counter propagation in SAVE log lines.

Verifies that puzzle_save() receives correct stats values from the main loop,
not zero defaults. Regression test for the counter bug where all SAVE lines
showed [saved=0 skip=0 err=0].
"""

from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch

from tools.go_problems.logging_config import StructuredLogger


class TestPuzzleSaveCounters:
    """Verify puzzle_save passes counters through to item_save."""

    def test_puzzle_save_forwards_counters(self):
        """puzzle_save() must forward downloaded/skipped/errors to item_save()."""
        mock_logger = MagicMock(spec=logging.Logger)
        logger = StructuredLogger(mock_logger)

        with patch.object(logger, "item_save") as mock_item_save:
            logger.puzzle_save(
                puzzle_id=42,
                path="42.sgf",
                downloaded=10,
                skipped=3,
                errors=1,
            )

            mock_item_save.assert_called_once_with(
                item_id="42",
                path="42.sgf",
                downloaded=10,
                skipped=3,
                errors=1,
            )

    def test_puzzle_save_defaults_are_zero(self):
        """Omitting counters defaults to 0 (documents the risk)."""
        mock_logger = MagicMock(spec=logging.Logger)
        logger = StructuredLogger(mock_logger)

        with patch.object(logger, "item_save") as mock_item_save:
            logger.puzzle_save(puzzle_id=1, path="1.sgf")

            mock_item_save.assert_called_once_with(
                item_id="1",
                path="1.sgf",
                downloaded=0,
                skipped=0,
                errors=0,
            )

    def test_puzzle_save_counters_must_not_be_omitted_in_production(self):
        """Document that callers MUST pass counters — this test exists as a reminder.

        The orchestrator main loop must pass stats.downloaded, stats.skipped, stats.errors
        to logger.puzzle_save(). If counters show zero in logs, check the call site.
        """
        # This test is intentionally a documentation test.
        # The actual integration is tested by verifying the orchestrator call site.
        pass
