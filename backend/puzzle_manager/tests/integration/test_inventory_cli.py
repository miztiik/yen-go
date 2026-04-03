"""Tests for inventory CLI command.

Tests for T010-T011:
- T010: Test inventory CLI command displays summary
- T011: Test --json flag outputs raw JSON

Skip with: pytest -m "not inventory"
"""

import json

import pytest

# Mark all tests in this module as inventory tests
pytestmark = pytest.mark.inventory

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from backend.puzzle_manager.inventory.models import (
    CollectionStats,
    PuzzleCollectionInventory,
)

# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def sample_inventory() -> PuzzleCollectionInventory:
    """Create a sample inventory for testing."""
    return PuzzleCollectionInventory(
        schema_version="2.0",
        last_updated=datetime(2026, 1, 31, 10, 30, 0, tzinfo=UTC),
        last_run_id="2026-01-31_abc123def456",
        collection=CollectionStats(
            total_puzzles=12500,
            by_puzzle_level={
                "novice": 500,
                "beginner": 1200,
                "elementary": 2000,
                "intermediate": 2500,
                "upper-intermediate": 2000,
                "advanced": 1500,
                "low-dan": 1200,
                "high-dan": 1000,
                "expert": 600,
            },
            by_tag={
                "life-and-death": 3400,
                "tesuji": 2800,
                "ko": 1200,
                "ladder": 800,
                "capturing-race": 600,
                "connection": 500,
                "cutting": 400,
                "liberty": 300,
                "throw-in": 200,
                "snapback": 100,
            },
            by_puzzle_quality={
                "1": 200,
                "2": 500,
                "3": 3000,
                "4": 5000,
                "5": 3800,
            },
        ),
    )


# =============================================================================
# Test CLI Human-Readable Output (T010)
# =============================================================================

class TestInventoryCLIDisplay:
    """Tests for human-readable inventory display."""

    def test_displays_total_puzzles(self, sample_inventory, capsys):
        """CLI shows total puzzle count."""
        from backend.puzzle_manager.inventory.cli import format_inventory_summary

        output = format_inventory_summary(sample_inventory)

        assert "Total Puzzles: 12,500" in output

    def test_displays_header(self, sample_inventory):
        """CLI shows header."""
        from backend.puzzle_manager.inventory.cli import format_inventory_summary

        output = format_inventory_summary(sample_inventory)

        assert "Puzzle Collection Inventory" in output
        assert "===========================" in output

    def test_displays_by_level_section(self, sample_inventory):
        """CLI shows By Level section with all levels."""
        from backend.puzzle_manager.inventory.cli import format_inventory_summary

        output = format_inventory_summary(sample_inventory)

        assert "By Level:" in output
        assert "novice:" in output
        assert "500" in output
        assert "4.0%" in output
        assert "expert:" in output
        assert "600" in output

    def test_displays_by_tag_section(self, sample_inventory):
        """CLI shows By Tag section (top 10)."""
        from backend.puzzle_manager.inventory.cli import format_inventory_summary

        output = format_inventory_summary(sample_inventory)

        assert "By Tag" in output
        assert "life-and-death:" in output
        assert "3,400" in output
        assert "27.2%" in output
        assert "tesuji:" in output

    def test_displays_quality_breakdown(self, sample_inventory):
        """T010: CLI shows By Quality section with counts and percentages."""
        from backend.puzzle_manager.inventory.cli import format_inventory_summary

        output = format_inventory_summary(sample_inventory)

        assert "By Quality:" in output
        # Verify all quality levels are shown (ordered 5→1)
        assert "Premium (5):" in output
        assert "High (4):" in output
        assert "Standard (3):" in output
        assert "Basic (2):" in output
        assert "Unverified (1):" in output
        # Verify counts
        assert "3,800" in output  # Premium
        assert "5,000" in output  # High
        assert "3,000" in output  # Standard
        assert "500" in output    # Basic
        assert "200" in output    # Unverified

    def test_quality_breakdown_ordered_premium_first(self, sample_inventory):
        """T010: Quality breakdown is ordered 5→1 (Premium first)."""
        from backend.puzzle_manager.inventory.cli import format_inventory_summary

        output = format_inventory_summary(sample_inventory)

        # Premium should appear before Unverified in the output
        premium_pos = output.find("Premium (5):")
        unverified_pos = output.find("Unverified (1):")
        assert premium_pos < unverified_pos, "Premium should appear before Unverified"

    def test_displays_last_updated(self, sample_inventory):
        """CLI shows last updated timestamp."""
        from backend.puzzle_manager.inventory.cli import format_inventory_summary

        output = format_inventory_summary(sample_inventory)

        assert "Last Updated:" in output
        assert "2026-01-31" in output

    def test_displays_last_run_id(self, sample_inventory):
        """CLI shows last run ID."""
        from backend.puzzle_manager.inventory.cli import format_inventory_summary

        output = format_inventory_summary(sample_inventory)

        assert "Last Run ID:" in output
        assert "2026-01-31_abc123def456" in output


# =============================================================================
# Test CLI JSON Output (T011)
# =============================================================================

class TestInventoryCLIJsonOutput:
    """Tests for --json flag output."""

    def test_json_flag_outputs_valid_json(self, sample_inventory):
        """--json flag outputs valid JSON."""
        from backend.puzzle_manager.inventory.cli import format_inventory_json

        output = format_inventory_json(sample_inventory)

        # Should be valid JSON
        data = json.loads(output)
        assert isinstance(data, dict)

    def test_json_contains_all_top_level_fields(self, sample_inventory):
        """JSON output contains all top-level fields."""
        from backend.puzzle_manager.inventory.cli import format_inventory_json

        output = format_inventory_json(sample_inventory)
        data = json.loads(output)

        assert "schema_version" in data
        assert "last_updated" in data
        assert "last_run_id" in data
        assert "collection" in data

    def test_json_contains_collection_stats(self, sample_inventory):
        """JSON output contains collection statistics."""
        from backend.puzzle_manager.inventory.cli import format_inventory_json

        output = format_inventory_json(sample_inventory)
        data = json.loads(output)

        assert data["collection"]["total_puzzles"] == 12500
        assert data["collection"]["by_puzzle_level"]["novice"] == 500
        assert data["collection"]["by_tag"]["life-and-death"] == 3400

    def test_json_contains_by_puzzle_quality(self, sample_inventory):
        """T011: JSON output contains by_puzzle_quality field."""
        from backend.puzzle_manager.inventory.cli import format_inventory_json

        output = format_inventory_json(sample_inventory)
        data = json.loads(output)

        assert "by_puzzle_quality" in data["collection"]
        quality = data["collection"]["by_puzzle_quality"]
        assert quality["1"] == 200
        assert quality["2"] == 500
        assert quality["3"] == 3000
        assert quality["4"] == 5000
        assert quality["5"] == 3800

    def test_json_is_pretty_printed(self, sample_inventory):
        """JSON output is pretty-printed with indentation."""
        from backend.puzzle_manager.inventory.cli import format_inventory_json

        output = format_inventory_json(sample_inventory)

        # Pretty-printed JSON has newlines and indentation
        assert "\n" in output
        assert "  " in output  # Indentation


# =============================================================================
# Test CLI Command Integration
# =============================================================================

class TestInventoryCLICommand:
    """Tests for the inventory command handler."""

    def test_command_returns_0_on_success(self, sample_inventory, tmp_path):
        """Command returns 0 on successful execution."""
        from backend.puzzle_manager.inventory.cli import cmd_inventory

        # Create a mock args object - explicitly set check/fix to False
        args = MagicMock()
        args.json = False
        args.rebuild = False
        args.reconcile = False
        args.check = False  # Spec 107: Explicitly disable check
        args.fix = False    # Spec 107: Explicitly disable fix
        args.verbose = 0

        with patch("backend.puzzle_manager.inventory.cli.InventoryManager") as mock_manager:
            mock_manager.return_value.exists.return_value = True
            mock_manager.return_value.load.return_value = sample_inventory
            result = cmd_inventory(args)

        assert result == 0

    def test_command_with_json_flag(self, sample_inventory, tmp_path):
        """Command outputs JSON when --json flag is set."""
        from backend.puzzle_manager.inventory.cli import cmd_inventory

        args = MagicMock()
        args.json = True
        args.rebuild = False
        args.reconcile = False
        args.check = False  # Spec 107: Explicitly disable check
        args.fix = False    # Spec 107: Explicitly disable fix
        args.verbose = 0

        with patch("backend.puzzle_manager.inventory.cli.InventoryManager") as mock_manager:
            mock_manager.return_value.exists.return_value = True
            mock_manager.return_value.load.return_value = sample_inventory
            with patch("builtins.print") as mock_print:
                result = cmd_inventory(args)

        assert result == 0
        # Check that JSON was printed
        printed = mock_print.call_args[0][0]
        data = json.loads(printed)
        assert data["collection"]["total_puzzles"] == 12500

    def test_command_handles_missing_inventory(self, tmp_path):
        """Command shows message when inventory doesn't exist."""
        from backend.puzzle_manager.inventory.cli import cmd_inventory

        args = MagicMock()
        args.json = False
        args.rebuild = False
        args.reconcile = False
        args.check = False  # Spec 107: Explicitly disable check
        args.fix = False    # Spec 107: Explicitly disable fix
        args.verbose = 0

        with patch("backend.puzzle_manager.inventory.cli.InventoryManager") as mock_manager:
            mock_manager.return_value.exists.return_value = False
            mock_manager.return_value.inventory_path = "/fake/path"
            with patch("builtins.print") as mock_print:
                result = cmd_inventory(args)

        assert result == 0
        # Check that info message was printed
        assert any("No inventory file found" in str(call) for call in mock_print.call_args_list)


# =============================================================================
# Test Edge Cases
# =============================================================================

class TestInventoryCLIEdgeCases:
    """Tests for edge cases in CLI output."""

    def test_handles_empty_inventory(self):
        """CLI handles empty inventory gracefully."""
        from backend.puzzle_manager.inventory.cli import format_inventory_summary
        from backend.puzzle_manager.inventory.models import PuzzleCollectionInventory

        empty = PuzzleCollectionInventory(
            last_updated=datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC),
            last_run_id="init",
        )
        output = format_inventory_summary(empty)

        assert "Total Puzzles: 0" in output
        assert "By Level:" in output

    def test_handles_zero_values_in_percentages(self):
        """CLI handles zero values without division errors."""
        from backend.puzzle_manager.inventory.cli import format_inventory_summary
        from backend.puzzle_manager.inventory.models import (
            CollectionStats,
            PuzzleCollectionInventory,
        )

        inventory = PuzzleCollectionInventory(
            last_updated=datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC),
            last_run_id="init",
            collection=CollectionStats(
                total_puzzles=0,
                by_puzzle_level={"novice": 0},
                by_tag={},
            )
        )
        output = format_inventory_summary(inventory)

        # Should not crash and should show 0
        assert "Total Puzzles: 0" in output

    def test_formats_large_numbers_with_commas(self):
        """CLI formats large numbers with thousand separators."""
        from backend.puzzle_manager.inventory.cli import format_inventory_summary
        from backend.puzzle_manager.inventory.models import (
            CollectionStats,
            PuzzleCollectionInventory,
        )

        inventory = PuzzleCollectionInventory(
            last_updated=datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC),
            last_run_id="init",
            collection=CollectionStats(
                total_puzzles=1234567,
                by_puzzle_level={},
                by_tag={},
            )
        )
        output = format_inventory_summary(inventory)

        assert "1,234,567" in output
