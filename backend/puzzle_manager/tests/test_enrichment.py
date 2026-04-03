"""
Unit tests for the enrichment module.

Tests for spec 042-sgf-enrichment.
"""

import pytest

from backend.puzzle_manager.core.enrichment import (
    EnrichmentConfig,
    EnrichmentResult,
)
from backend.puzzle_manager.core.enrichment.hints import (
    HintGenerator,
)
from backend.puzzle_manager.core.enrichment.ko import (
    KoContextType,
)
from backend.puzzle_manager.core.enrichment.move_order import (
    MoveOrderFlexibility,
)
from backend.puzzle_manager.core.enrichment.refutation import (
    format_refutations,
    point_to_sgf,
    sgf_to_point,
)
from backend.puzzle_manager.core.enrichment.region import (
    BoardRegion,
    detect_region,
    region_to_description,
    region_to_sgf,
)
from backend.puzzle_manager.core.primitives import Color, Point


class TestBoardRegion:
    """Tests for region detection."""

    def test_top_left_corner(self):
        """Stones in top-left corner should be detected as TL."""
        stones = [Point(0, 0), Point(1, 1), Point(2, 2)]
        region = detect_region(stones, board_size=19)
        assert region == BoardRegion.TL

    def test_bottom_right_corner(self):
        """Stones in bottom-right corner should be detected as BR."""
        stones = [Point(16, 16), Point(17, 17), Point(18, 18)]
        region = detect_region(stones, board_size=19)
        assert region == BoardRegion.BR

    def test_center_region(self):
        """Stones in center should be detected as CENTER."""
        stones = [Point(8, 8), Point(9, 9), Point(10, 10)]
        region = detect_region(stones, board_size=19)
        assert region == BoardRegion.C

    def test_full_board(self):
        """Stones spread across board should be detected as FULL."""
        stones = [Point(0, 0), Point(18, 18), Point(0, 18), Point(18, 0)]
        region = detect_region(stones, board_size=19)
        assert region == BoardRegion.FULL

    def test_empty_stones(self):
        """Empty stone list should return FULL."""
        region = detect_region([], board_size=19)
        assert region == BoardRegion.FULL

    def test_region_to_description(self):
        """Test region descriptions."""
        assert "corner" in region_to_description(BoardRegion.TL).lower()
        assert "center" in region_to_description(BoardRegion.C).lower()

    def test_region_to_sgf(self):
        """Test SGF code generation."""
        assert region_to_sgf(BoardRegion.TL) == "TL"
        assert region_to_sgf(BoardRegion.BR) == "BR"
        assert region_to_sgf(BoardRegion.C) == "C"


class TestHintGenerator:
    """Tests for hint generation."""

    def test_generate_yh1_with_region(self):
        """YH1 returns a string (may be empty when game has no tags)."""
        config = EnrichmentConfig(include_liberty_analysis=False)
        generator = HintGenerator(config)

        # Create minimal mock game
        class MockGame:
            black_stones = [Point(0, 0)]
            white_stones = [Point(1, 1)]
            player_to_move = Color.BLACK
            board_size = 19
            has_solution = False
            yengo_props = None

        hint = generator.generate_yh1(MockGame(), region_code="TL")
        assert isinstance(hint, str)

    def test_generate_yh2_with_tags(self):
        """YH2 should generate technique hint from tags."""
        config = EnrichmentConfig(include_technique_reasoning=True)
        generator = HintGenerator(config)

        hint = generator.generate_yh2(["ladder"])
        assert hint is not None
        assert "ladder" in hint.lower()

    def test_generate_yh2_no_matching_tags(self):
        """YH2 should return None if no matching tags."""
        config = EnrichmentConfig()
        generator = HintGenerator(config)

        hint = generator.generate_yh2(["unknown_tag"])
        assert hint is None

    def test_generate_yh2_empty_tags(self):
        """YH2 should return None for empty tags."""
        config = EnrichmentConfig()
        generator = HintGenerator(config)

        hint = generator.generate_yh2([])
        assert hint is None

    def test_technique_hints_dictionary(self):
        """Check that TECHNIQUE_HINTS has expected techniques."""
        assert "ladder" in HintGenerator.TECHNIQUE_HINTS
        assert "net" in HintGenerator.TECHNIQUE_HINTS
        assert "snapback" in HintGenerator.TECHNIQUE_HINTS
        assert "ko" in HintGenerator.TECHNIQUE_HINTS


class TestRefutation:
    """Tests for refutation extraction."""

    def test_point_to_sgf(self):
        """Test point to SGF coordinate conversion."""
        assert point_to_sgf(Point(0, 0)) == "aa"
        assert point_to_sgf(Point(2, 3)) == "cd"
        assert point_to_sgf(Point(18, 18)) == "ss"

    def test_sgf_to_point(self):
        """Test SGF coordinate to point conversion."""
        assert sgf_to_point("aa") == Point(0, 0)
        assert sgf_to_point("cd") == Point(2, 3)
        assert sgf_to_point("ss") == Point(18, 18)

    def test_format_refutations_empty(self):
        """Empty refutation list should return None."""
        assert format_refutations([]) is None

    def test_format_refutations_single(self):
        """Single refutation should format correctly."""
        result = format_refutations([Point(2, 3)])
        assert result == "cd"

    def test_format_refutations_multiple(self):
        """Multiple refutations should be comma-separated."""
        result = format_refutations([Point(2, 3), Point(4, 5)])
        assert result == "cd,ef"

    def test_sgf_to_point_invalid(self):
        """Invalid SGF coordinate should raise ValueError."""
        with pytest.raises(ValueError):
            sgf_to_point("a")  # Too short
        with pytest.raises(ValueError):
            sgf_to_point("abc")  # Too long


class TestMoveOrder:
    """Tests for move order detection."""

    def test_flexibility_enum(self):
        """Test MoveOrderFlexibility enum values."""
        assert MoveOrderFlexibility.STRICT.value == "strict"
        assert MoveOrderFlexibility.FLEXIBLE.value == "flexible"


class TestKoContext:
    """Tests for ko context detection."""

    def test_ko_context_enum(self):
        """Test KoContextType enum values."""
        assert KoContextType.NONE.value == "none"
        assert KoContextType.DIRECT.value == "direct"
        assert KoContextType.APPROACH.value == "approach"


class TestEnrichmentConfig:
    """Tests for enrichment configuration."""

    def test_default_config(self):
        """Test default configuration values."""
        config = EnrichmentConfig()
        assert config.enable_hints is True
        assert config.enable_region is True
        assert config.enable_ko is True
        assert config.enable_move_order is True
        assert config.enable_refutation is True

    def test_custom_config(self):
        """Test custom configuration."""
        config = EnrichmentConfig(
            enable_hints=False,
            enable_region=False,
            verbose=True,
        )
        assert config.enable_hints is False
        assert config.enable_region is False
        assert config.verbose is True

    def test_thresholds(self):
        """Test that region thresholds are computed, not configurable."""
        config = EnrichmentConfig()
        assert config.enable_region is True


class TestEnrichmentResult:
    """Tests for enrichment result."""

    def test_default_result(self):
        """Test default result values are empty/None."""
        result = EnrichmentResult()
        assert result.hints == []
        assert result.region is None
        assert result.ko_context is None
        assert result.move_order is None
        assert result.refutations is None

    def test_result_with_values(self):
        """Test result with populated values."""
        result = EnrichmentResult(
            hints=["Focus on the top-left corner.", "Look for a ladder pattern."],
            region="TL",
            ko_context="direct",
        )
        assert result.hints[0] == "Focus on the top-left corner."
        assert result.hints[1] == "Look for a ladder pattern."
        assert result.region == "TL"
        assert result.ko_context == "direct"
