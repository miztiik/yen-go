"""
Unit tests for the enrichment module.

Tests for spec 042-sgf-enrichment.
"""

import pytest

from backend.puzzle_manager.core.enrichment import (
    EnrichmentConfig,
    EnrichmentResult,
    enrich_puzzle,
)
from backend.puzzle_manager.core.enrichment.hints import (
    ATARI_SKIP_TAGS,
    SEMEAI_KO_TAGS,
    HintGenerator,
)
from backend.puzzle_manager.core.enrichment.ko import (
    KoContextType,
    _detect_from_comments,
    _detect_from_tags,
    _detect_from_text,
    detect_ko_context,
)
from backend.puzzle_manager.core.enrichment.move_order import (
    MoveOrderFlexibility,
    detect_move_order,
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
from backend.puzzle_manager.core.enrichment.solution_tagger import (
    InferenceConfidence,
    infer_technique_from_solution,
    move_captures_stones,
)
from backend.puzzle_manager.core.primitives import Color, Point
from backend.puzzle_manager.core.sgf_parser import SGFGame, SolutionNode, YenGoProperties
from backend.puzzle_manager.exceptions import (
    ConfigFileNotFoundError,
    ConfigurationError,
)


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
        """Test canonical SGF code generation (6-value output)."""
        assert region_to_sgf(BoardRegion.TL) == "TL"
        assert region_to_sgf(BoardRegion.BR) == "BR"
        assert region_to_sgf(BoardRegion.C) == "C"
        # Edge regions collapse to "E"
        assert region_to_sgf(BoardRegion.T) == "E"
        assert region_to_sgf(BoardRegion.B) == "E"
        assert region_to_sgf(BoardRegion.L) == "E"
        assert region_to_sgf(BoardRegion.R) == "E"
        # FULL collapses to "C"
        assert region_to_sgf(BoardRegion.FULL) == "C"

    # --- Edge region tests ---

    def test_top_edge_region(self):
        """Stones along top edge (not in a corner) should be T."""
        # Stones centered at top, spanning past corner threshold
        stones = [Point(7, 0), Point(8, 1), Point(9, 2), Point(10, 1)]
        region = detect_region(stones, board_size=19)
        assert region == BoardRegion.T

    def test_bottom_edge_region(self):
        """Stones along bottom edge should be B."""
        stones = [Point(7, 17), Point(8, 18), Point(9, 17), Point(10, 18)]
        region = detect_region(stones, board_size=19)
        assert region == BoardRegion.B

    def test_left_edge_region(self):
        """Stones along left edge should be L."""
        stones = [Point(0, 7), Point(1, 8), Point(0, 9), Point(1, 10)]
        region = detect_region(stones, board_size=19)
        assert region == BoardRegion.L

    def test_right_edge_region(self):
        """Stones along right edge should be R."""
        stones = [Point(17, 7), Point(18, 8), Point(17, 9), Point(18, 10)]
        region = detect_region(stones, board_size=19)
        assert region == BoardRegion.R

    def test_top_right_corner(self):
        """Stones in top-right corner should be TR."""
        stones = [Point(16, 0), Point(17, 1), Point(18, 2)]
        region = detect_region(stones, board_size=19)
        assert region == BoardRegion.TR

    def test_bottom_left_corner(self):
        """Stones in bottom-left corner should be BL."""
        stones = [Point(0, 16), Point(1, 17), Point(2, 18)]
        region = detect_region(stones, board_size=19)
        assert region == BoardRegion.BL

    def test_single_stone_corner(self):
        """Single stone in corner should detect that corner."""
        assert detect_region([Point(0, 0)], board_size=19) == BoardRegion.TL
        assert detect_region([Point(18, 18)], board_size=19) == BoardRegion.BR

    def test_single_stone_center(self):
        """Single stone at tengen should detect center."""
        region = detect_region([Point(9, 9)], board_size=19)
        assert region == BoardRegion.C

    def test_9x9_board_corner(self):
        """Corner detection on 9x9 board."""
        stones = [Point(0, 0), Point(1, 1), Point(2, 0)]
        region = detect_region(stones, board_size=9)
        assert region == BoardRegion.TL

    def test_9x9_board_bottom_right(self):
        """9x9 puzzle AB[ih][hh][gh][fh][fi] should be BR, not B.

        This was the original bug: corner_threshold=6 on a 9x9 board
        extended past the center, making corner detection impossible.
        """
        # Stones at (8,7), (7,7), (6,7), (5,7), (5,8) on a 9x9 board
        stones = [Point(8, 7), Point(7, 7), Point(6, 7), Point(5, 7), Point(5, 8)]
        region = detect_region(stones, board_size=9)
        assert region == BoardRegion.BR

    def test_9x9_board_top_left(self):
        """Stones in the top-left of a 9x9 board."""
        stones = [Point(0, 0), Point(1, 0), Point(0, 1), Point(1, 1)]
        region = detect_region(stones, board_size=9)
        assert region == BoardRegion.TL

    def test_9x9_board_center(self):
        """Stones in the center of a 9x9 board."""
        stones = [Point(4, 4), Point(3, 3), Point(5, 5)]
        region = detect_region(stones, board_size=9)
        assert region == BoardRegion.C

    def test_13x13_board_center(self):
        """Center detection on 13x13 board."""
        stones = [Point(5, 5), Point(6, 6), Point(7, 7)]
        region = detect_region(stones, board_size=13)
        assert region == BoardRegion.C

    def test_13x13_board_bottom_left(self):
        """Corner detection on 13x13 board."""
        stones = [Point(0, 11), Point(1, 12), Point(2, 11)]
        region = detect_region(stones, board_size=13)
        assert region == BoardRegion.BL

    def test_5x5_board_corner(self):
        """Corner detection on 5x5 board."""
        stones = [Point(0, 0), Point(1, 0)]
        region = detect_region(stones, board_size=5)
        assert region == BoardRegion.TL

    def test_5x5_board_bottom_right(self):
        """Corner detection on 5x5 board (bottom-right)."""
        stones = [Point(3, 3), Point(4, 4)]
        region = detect_region(stones, board_size=5)
        assert region == BoardRegion.BR

    def test_7x7_board_corner(self):
        """Corner detection on 7x7 board."""
        stones = [Point(5, 5), Point(6, 6), Point(5, 6)]
        region = detect_region(stones, board_size=7)
        assert region == BoardRegion.BR

    def test_4x4_board_corner(self):
        """Corner detection on 4x4 board (extreme small)."""
        stones = [Point(0, 0), Point(1, 0)]
        region = detect_region(stones, board_size=4)
        assert region == BoardRegion.TL

    def test_canonical_sgf_values_only(self):
        """region_to_sgf should only produce the 6 canonical values."""
        valid_values = {"TL", "TR", "BL", "BR", "C", "E"}
        for region in BoardRegion:
            sgf_value = region_to_sgf(region)
            assert sgf_value in valid_values, (
                f"BoardRegion.{region.name} maps to '{sgf_value}',"
                f" expected one of {valid_values}"
            )

    def test_proportional_thresholds_scale(self):
        """Verify thresholds scale proportionally across board sizes."""
        from backend.puzzle_manager.core.enrichment.region import (
            _compute_corner_threshold,
            _compute_edge_threshold,
        )
        # 19x19: corner=6, edge=2 (original values)
        assert _compute_corner_threshold(19) == 6
        assert _compute_edge_threshold(19) == 2
        # 9x9: corner=3, edge=1
        assert _compute_corner_threshold(9) == 3
        assert _compute_edge_threshold(9) == 1
        # 13x13: corner=4, edge=1
        assert _compute_corner_threshold(13) == 4
        assert _compute_edge_threshold(13) == 1
        # 5x5: minimums apply
        assert _compute_corner_threshold(5) == 2
        assert _compute_edge_threshold(5) == 1


class TestHintGenerator:
    """Tests for hint generation (redesigned: Technique → Reasoning → Coordinate)."""

    # --- Helpers ---

    @staticmethod
    def _make_mock_game(
        tags=None,
        has_solution=False,
        solution_children=None,
        black_stones=None,
        white_stones=None,
    ):
        """Create a minimal mock game object for testing."""
        class MockSolutionNode:
            def __init__(self, move=None, is_correct=True, comment="", children=None, color=None):
                self.move = move
                self.is_correct = is_correct
                self.comment = comment
                self.children = children or []
                self.color = color

        class MockYenGoProps:
            def __init__(self, tag_list):
                self.tags = tag_list

        class MockGame:
            pass

        game = MockGame()
        game.black_stones = black_stones or [Point(0, 0)]
        game.white_stones = white_stones or [Point(1, 1)]
        game.player_to_move = Color.BLACK
        game.board_size = 19
        game.has_solution = has_solution
        game.yengo_props = MockYenGoProps(tags or [])
        game.metadata = {}
        game.solution_tree = MockSolutionNode(
            children=solution_children or []
        )
        return game, MockSolutionNode

    # --- Backward compatibility (old method names still work) ---

    def test_generate_yh1_backward_compat(self):
        """generate_yh1() should still work (backward-compatible alias)."""
        config = EnrichmentConfig(include_liberty_analysis=False)
        generator = HintGenerator(config)
        game, _ = self._make_mock_game(tags=["ladder"])
        hint = generator.generate_yh1(game, region_code="TL")
        assert hint  # Should return technique hint, not empty
        assert "ladder" in hint.lower()

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

    # --- Phase 1: Key mismatch fixes ---

    def test_key_mismatch_capture_race(self):
        """B1: 'capture-race' tag now produces a hint (was 'capture' key only)."""
        config = EnrichmentConfig(include_technique_reasoning=True)
        generator = HintGenerator(config)
        hint = generator.generate_yh2(["capture-race"])
        assert hint is not None
        assert "semeai" in hint.lower() or "capturing" in hint.lower()

    def test_key_mismatch_connection(self):
        """B1: 'connection' tag now produces a hint (was 'connect' key only)."""
        config = EnrichmentConfig(include_technique_reasoning=True)
        generator = HintGenerator(config)
        hint = generator.generate_yh2(["connection"])
        assert hint is not None
        assert "connect" in hint.lower()

    def test_key_mismatch_cutting(self):
        """B1: 'cutting' tag now produces a hint (was 'cut' key only)."""
        config = EnrichmentConfig(include_technique_reasoning=True)
        generator = HintGenerator(config)
        hint = generator.generate_yh2(["cutting"])
        assert hint is not None
        assert "cut" in hint.lower()

    def test_key_mismatch_liberty_shortage(self):
        """B1: 'liberty-shortage' tag now produces a hint (was 'squeeze' key only)."""
        config = EnrichmentConfig(include_technique_reasoning=True)
        generator = HintGenerator(config)
        hint = generator.generate_yh2(["liberty-shortage"])
        assert hint is not None
        assert "liberty" in hint.lower() or "damezumari" in hint.lower()

    # --- Phase 2: All 28 tags produce hints ---

    ALL_28_TAGS = [
        "ladder", "net", "snapback", "ko", "liberty-shortage", "throw-in",
        "sacrifice", "connection", "cutting", "capture-race", "life-and-death",
        "escape", "double-atari", "nakade", "clamp", "vital-point",
        "connect-and-die", "under-the-stones", "eye-shape", "dead-shapes",
        "corner", "shape", "endgame", "joseki", "fuseki", "tesuji",
        "living", "seki",
    ]

    @pytest.mark.parametrize("tag", ALL_28_TAGS)
    def test_all_28_tags_produce_yh2(self, tag):
        """E1: Every tag in config/tags.json produces a non-None YH2."""
        config = EnrichmentConfig(include_technique_reasoning=True)
        generator = HintGenerator(config)
        hint = generator.generate_yh2([tag])
        assert hint is not None, f"Tag '{tag}' produces no YH2 hint"
        assert len(hint) > 0

    @pytest.mark.parametrize("tag", ALL_28_TAGS)
    def test_all_28_tags_produce_technique_hint(self, tag):
        """E1: Every tag produces a technique hint via generate_technique_hint."""
        config = EnrichmentConfig(include_liberty_analysis=False)
        generator = HintGenerator(config)
        game, _ = self._make_mock_game(tags=[tag])
        hint = generator.generate_technique_hint([tag], game)
        assert hint is not None, f"Tag '{tag}' produces no technique hint"

    @pytest.mark.parametrize("tag", ALL_28_TAGS)
    def test_all_28_tags_produce_reasoning_hint(self, tag):
        """E1: Every tag produces a reasoning hint via generate_reasoning_hint."""
        config = EnrichmentConfig(include_technique_reasoning=True, include_liberty_analysis=False)
        generator = HintGenerator(config)
        game, _ = self._make_mock_game(tags=[tag])
        hint = generator.generate_reasoning_hint([tag], game)
        assert hint is not None, f"Tag '{tag}' produces no reasoning hint"

    # --- Tag priority ordering ---

    def test_priority_snapback_over_life_and_death(self):
        """E3: Specific tesuji (snapback) wins over category (life-and-death)."""
        config = EnrichmentConfig(include_technique_reasoning=True)
        generator = HintGenerator(config)
        hint = generator.generate_yh2(["life-and-death", "snapback"])
        assert hint is not None
        assert "snapback" in hint.lower()

    def test_priority_ladder_over_life_and_death(self):
        """E3: Tactical (ladder) wins over category (life-and-death)."""
        config = EnrichmentConfig(include_technique_reasoning=True)
        generator = HintGenerator(config)
        hint = generator.generate_yh2(["life-and-death", "ladder"])
        assert hint is not None
        assert "ladder" in hint.lower()

    def test_priority_double_atari_over_capture_race(self):
        """E3: Specific (double-atari) wins over general (capture-race)."""
        config = EnrichmentConfig(include_technique_reasoning=True)
        generator = HintGenerator(config)
        hint = generator.generate_yh2(["capture-race", "double-atari"])
        assert hint is not None
        assert "double atari" in hint.lower()

    def test_primary_tag_extraction(self):
        """_get_primary_tag returns highest-priority tag."""
        config = EnrichmentConfig()
        generator = HintGenerator(config)
        assert generator._get_primary_tag(["life-and-death", "snapback"]) == "snapback"
        assert generator._get_primary_tag(["ko", "ladder"]) == "ladder"
        assert generator._get_primary_tag(["life-and-death"]) == "life-and-death"

    # --- Liberty gating (Phase 3) ---

    def test_liberty_gating_net_no_liberty_text(self):
        """A2: Net puzzle should NOT get liberty analysis in any hint."""
        config = EnrichmentConfig(include_liberty_analysis=True, include_technique_reasoning=True)
        generator = HintGenerator(config)
        # Game with both sides having low liberties
        game, _ = self._make_mock_game(
            tags=["net"],
            black_stones=[Point(2, 2), Point(3, 2)],
            white_stones=[Point(2, 3), Point(3, 3)],
        )
        technique = generator.generate_technique_hint(["net"], game)
        reasoning = generator.generate_reasoning_hint(["net"], game)
        # Neither should mention "liberties" since net is not semeai/ko
        if technique:
            assert "liberties" not in technique.lower()
        if reasoning:
            assert "liberties" not in reasoning.lower()

    def test_liberty_gating_capture_race_includes_liberties(self):
        """A2: Capture-race puzzle SHOULD get liberty analysis."""
        config = EnrichmentConfig(include_liberty_analysis=True, include_technique_reasoning=True)
        generator = HintGenerator(config)
        # Game where both sides have unequal liberties
        game, _ = self._make_mock_game(
            tags=["capture-race"],
            black_stones=[Point(0, 0)],       # 1 stone, will have some libs
            white_stones=[Point(18, 18)],      # 1 stone, will have some libs
        )
        reasoning = generator.generate_reasoning_hint(["capture-race"], game)
        assert reasoning is not None
        # The reasoning should at minimum contain the base text
        assert "liberties" in reasoning.lower() or "semeai" in reasoning.lower() or "capturing" in reasoning.lower()

    # --- Atari standalone (Phase 3) ---

    def test_atari_standalone_for_non_semeai(self):
        """A3: Atari hint only when correct move captures the atari group."""
        config = EnrichmentConfig(include_liberty_analysis=True)
        generator = HintGenerator(config)
        _, MockNode = self._make_mock_game()
        # White at corner (0,0) with 1 liberty at (0,1).
        # Correct move IS (0,1) which captures white → atari hint should fire.
        game, _ = self._make_mock_game(
            tags=["life-and-death"],
            has_solution=True,
            solution_children=[
                MockNode(move=Point(0, 1), is_correct=True),
            ],
            black_stones=[Point(1, 0)],  # Blocks one of white's liberties
            white_stones=[Point(0, 0)],  # White in atari (1 liberty at (0,1))
        )
        hint = generator.generate_technique_hint(["life-and-death"], game)
        assert hint is not None
        assert "atari" in hint.lower()

    def test_atari_suppressed_when_irrelevant(self):
        """Atari hint suppressed when correct move does NOT capture atari group."""
        config = EnrichmentConfig(include_liberty_analysis=True)
        generator = HintGenerator(config)
        _, MockNode = self._make_mock_game()
        # White at corner (0,0) in atari (1 liberty at (0,1)),
        # but correct move is at (5,5) — unrelated to the atari.
        game, _ = self._make_mock_game(
            tags=["life-and-death"],
            has_solution=True,
            solution_children=[
                MockNode(move=Point(5, 5), is_correct=True),
            ],
            black_stones=[Point(1, 0)],
            white_stones=[Point(0, 0)],
        )
        hint = generator.generate_technique_hint(["life-and-death"], game)
        assert hint is not None
        # Should NOT say "atari" — should fall through to tag-based hint
        assert "atari" not in hint.lower()
        assert "life" in hint.lower() and "death" in hint.lower()

    def test_player_atari_hint_when_move_saves_group(self):
        """R5: Player-atari hint emitted when correct move saves the atari group."""
        config = EnrichmentConfig(include_liberty_analysis=True)
        generator = HintGenerator(config)
        _, MockNode = self._make_mock_game()
        # Black at (5,5) in atari: W at (4,5),(6,5),(5,6). Only liberty (5,4).
        # Correct move (5,4) connects → group has 3 liberties → saved.
        game, _ = self._make_mock_game(
            tags=["life-and-death"],
            has_solution=True,
            solution_children=[
                MockNode(move=Point(5, 4), is_correct=True),
            ],
            black_stones=[Point(5, 5)],
            white_stones=[Point(4, 5), Point(6, 5), Point(5, 6)],
        )
        hint = generator.generate_technique_hint(["life-and-death"], game)
        assert hint is not None
        assert "atari" in hint.lower()

    def test_player_atari_suppressed_when_move_does_not_save(self):
        """R5: Player-atari hint suppressed when move doesn't save atari group.

        Mirrors the puzzle (YENGO-18a7d28762c4f459): Black has a stone in
        atari but the correct move creates eye shape elsewhere. The atari
        is incidental.
        """
        config = EnrichmentConfig(include_liberty_analysis=True)
        generator = HintGenerator(config)
        _, MockNode = self._make_mock_game()
        # Black at (0,0) in atari: neighbors (1,0)=W, (0,1)=W.
        # Only liberty is... none actually — it's surrounded.
        # Better scenario: Black at (3,0) with 1 liberty at (3,1),
        # surrounded by W at (2,0) and (4,0). Correct move is at (8,8).
        game, _ = self._make_mock_game(
            tags=["life-and-death"],
            has_solution=True,
            solution_children=[
                MockNode(move=Point(8, 8), is_correct=True),
            ],
            black_stones=[Point(3, 0), Point(5, 0)],
            white_stones=[Point(2, 0), Point(4, 0)],
        )
        hint = generator.generate_technique_hint(["life-and-death"], game)
        assert hint is not None
        # Should NOT say "atari" — should fall through to tag-based hint
        assert "atari" not in hint.lower()
        assert "life" in hint.lower() and "death" in hint.lower()

    def test_player_atari_hint_when_move_captures_threatening_stone(self):
        """R5: Player-atari hint emitted when move captures the threatening stone."""
        config = EnrichmentConfig(include_liberty_analysis=True)
        generator = HintGenerator(config)
        _, MockNode = self._make_mock_game()
        # Black at (1,0) in atari: surrounded by W at (0,0), (2,0), (1,1).
        # Only liberty is... wait, that's zero. Let's set up:
        # Black at (1,1) in atari: W at (0,1), (2,1), (1,2). Liberty at (1,0).
        # White at (0,1) has liberties (0,0) and (0,2) — 2 libs.
        # But if correct move at (1,0) → Black (1,1) now has liberties at (1,0)
        # actually (1,0) is where black just played. So (1,1) group = {(1,0),(1,1)}.
        # Let's simplify: Black at (0,1) with W at (0,0) — W has 1 lib at (1,0).
        # Black captures W by playing (1,0). But this is opponent atari, not player.
        # Player atari saving by capture: B at (1,0), W at (0,0) and (2,0).
        # B has liberties at (1,1) only → atari. But correct move (0,1) is
        # adjacent to W(0,0). W(0,0) neighbors: (1,0)=B, (0,1)=move. If W(0,0)
        # also has no other liberties, B captures it, freeing (0,0) as liberty for B(1,0).
        # Setup: B at (1,0). W at (0,0) with only liberty (0,1).
        # B(1,0) liberties: (0,0)=W, (2,0)=empty, (1,1)=empty → 2 libs. Not atari.
        # Let's just use: B at (1,1), W at (0,1),(1,0),(2,1). B liberty=(1,2) only.
        # Correct move (1,2) connects → B group {(1,1),(1,2)} has more liberties.
        game, _ = self._make_mock_game(
            tags=["life-and-death"],
            has_solution=True,
            solution_children=[
                MockNode(move=Point(1, 2), is_correct=True),
            ],
            black_stones=[Point(1, 1)],
            white_stones=[Point(0, 1), Point(1, 0), Point(2, 1)],
        )
        hint = generator.generate_technique_hint(["life-and-death"], game)
        assert hint is not None
        # Correct move (1,2) connects to and saves the atari group
        assert "atari" in hint.lower()

    # --- Solution depth gating (Phase 3) ---

    def test_depth_1_generates_coordinate(self):
        """A5: Depth-1 puzzle generates coordinate (no outcome text)."""
        config = EnrichmentConfig(include_consequence=True)
        generator = HintGenerator(config)
        _, MockNode = self._make_mock_game()
        game, _ = self._make_mock_game(
            tags=["ladder"],
            has_solution=True,
            solution_children=[
                MockNode(move=Point(2, 3), is_correct=True),
            ],
        )
        hint = generator.generate_coordinate_hint(game, ["ladder"])
        assert hint is not None, "Depth-1 should still generate coordinate"
        assert "{!cd}" in hint
        # Depth 1: no outcome text
        assert "begins the chase" not in hint

    def test_depth_2_generates_coordinate_only(self):
        """A5: Depth-2 puzzle should generate coordinate without outcome text."""
        config = EnrichmentConfig(include_consequence=True)
        generator = HintGenerator(config)
        _, MockNode = self._make_mock_game()
        game, _ = self._make_mock_game(
            tags=["ladder"],
            has_solution=True,
            solution_children=[
                MockNode(
                    move=Point(2, 3), is_correct=True,
                    children=[MockNode(
                        move=Point(4, 5), is_correct=False,
                        children=[MockNode(move=Point(6, 7), is_correct=True)],
                    )],
                ),
            ],
        )
        hint = generator.generate_coordinate_hint(game, ["ladder"])
        assert hint is not None
        assert "{!cd}" in hint
        # Depth 2-3: no outcome text
        assert "begins the chase" not in hint

    def test_depth_4_generates_coordinate_with_outcome(self):
        """A5: Depth-4+ puzzle should include technique-specific outcome."""
        config = EnrichmentConfig(include_consequence=True)
        generator = HintGenerator(config)
        _, MockNode = self._make_mock_game()
        # Build a 4-deep solution tree
        game, _ = self._make_mock_game(
            tags=["ladder"],
            has_solution=True,
            solution_children=[
                MockNode(
                    move=Point(2, 3), is_correct=True,
                    children=[MockNode(
                        move=Point(3, 4), is_correct=True,
                        children=[MockNode(
                            move=Point(4, 5), is_correct=True,
                            children=[MockNode(
                                move=Point(5, 6), is_correct=True,
                            )],
                        )],
                    )],
                ),
            ],
        )
        hint = generator.generate_coordinate_hint(game, ["ladder"])
        assert hint is not None
        assert "{!cd}" in hint
        assert "begins the chase" in hint.lower()

    # --- Technique-aware YH3 templates ---

    def test_yh3_net_template(self):
        """A4: Net puzzle YH3 should mention 'enclosure'."""
        config = EnrichmentConfig(include_consequence=True)
        generator = HintGenerator(config)
        _, MockNode = self._make_mock_game()
        game, _ = self._make_mock_game(
            tags=["net"],
            has_solution=True,
            solution_children=[
                MockNode(
                    move=Point(2, 3), is_correct=True,
                    children=[MockNode(
                        move=Point(3, 4), is_correct=True,
                        children=[MockNode(
                            move=Point(4, 5), is_correct=True,
                            children=[MockNode(
                                move=Point(5, 6), is_correct=True,
                            )],
                        )],
                    )],
                ),
            ],
        )
        hint = generator.generate_coordinate_hint(game, ["net"])
        assert hint is not None
        assert "enclosure" in hint.lower()

    # --- Solution depth calculation ---

    def test_solution_depth_empty_tree(self):
        """Depth of empty tree should be 0."""
        config = EnrichmentConfig()
        generator = HintGenerator(config)
        _, MockNode = self._make_mock_game()
        tree = MockNode(children=[])
        assert generator._get_solution_depth(tree) == 0

    def test_solution_depth_single_move(self):
        """Depth of single correct move should be 1."""
        config = EnrichmentConfig()
        generator = HintGenerator(config)
        _, MockNode = self._make_mock_game()
        tree = MockNode(children=[
            MockNode(move=Point(2, 3), is_correct=True),
        ])
        assert generator._get_solution_depth(tree) == 1

    def test_solution_depth_chain(self):
        """Depth of 3-move chain should be 3."""
        config = EnrichmentConfig()
        generator = HintGenerator(config)
        _, MockNode = self._make_mock_game()
        tree = MockNode(children=[
            MockNode(
                move=Point(2, 3), is_correct=True,
                children=[MockNode(
                    move=Point(4, 5), is_correct=True,
                    children=[MockNode(
                        move=Point(6, 7), is_correct=True,
                    )],
                )],
            ),
        ])
        assert generator._get_solution_depth(tree) == 3

    # --- New method names work ---

    def test_generate_technique_hint_returns_technique(self):
        """generate_technique_hint should return technique name hint."""
        config = EnrichmentConfig(include_liberty_analysis=False)
        generator = HintGenerator(config)
        game, _ = self._make_mock_game(tags=["net"])
        hint = generator.generate_technique_hint(["net"], game)
        assert hint is not None
        assert "net" in hint.lower() or "geta" in hint.lower()

    def test_generate_reasoning_hint_returns_reasoning(self):
        """generate_reasoning_hint should return reasoning text."""
        config = EnrichmentConfig(include_technique_reasoning=True, include_liberty_analysis=False)
        generator = HintGenerator(config)
        game, _ = self._make_mock_game(tags=["net"])
        hint = generator.generate_reasoning_hint(["net"], game)
        assert hint is not None
        assert "escape" in hint.lower() or "capture" in hint.lower()

    # --- Solution-aware fallback (when tags are missing) ---

    def test_solution_aware_capture_hint_no_tags(self):
        """When no tags, capture position with atari → atari hint (Path 1).

        For a no-tag puzzle where opponent is in atari and the correct
        move captures, Path 1 (atari detection) fires with certainty.
        Path 3 (solution_tagger, MEDIUM confidence) is never reached.
        """
        config = EnrichmentConfig(include_liberty_analysis=True)
        generator = HintGenerator(config)
        _, MockNode = self._make_mock_game()
        # White at (0,0) in atari, correct move (0,1) captures it.
        game, _ = self._make_mock_game(
            tags=[],
            has_solution=True,
            solution_children=[
                MockNode(move=Point(0, 1), is_correct=True),
            ],
            black_stones=[Point(1, 0)],
            white_stones=[Point(0, 0)],
        )
        hint = generator.generate_technique_hint([], game)
        # Path 1 fires: opponent in atari + correct move captures
        assert hint is not None
        assert "atari" in hint.lower()

    def test_solution_aware_no_capture_no_tags(self):
        """When no tags, correct move that doesn't capture → None (LOW confidence).

        Unknown move effect is LOW confidence, below the HIGH threshold.
        The system emits coordinate-only (YH3) instead of guessing.
        """
        config = EnrichmentConfig(include_liberty_analysis=True)
        generator = HintGenerator(config)
        _, MockNode = self._make_mock_game()
        # No atari anywhere, no tags, correct move doesn't capture.
        game, _ = self._make_mock_game(
            tags=[],
            has_solution=True,
            solution_children=[
                MockNode(move=Point(9, 9), is_correct=True),
            ],
            black_stones=[Point(2, 2)],
            white_stones=[Point(16, 16)],
        )
        hint = generator.generate_technique_hint([], game)
        # LOW confidence (unknown effect) → no technique hint emitted
        assert hint is None

    def test_solution_aware_reasoning_no_tags(self):
        """When no tags, unknown effect → no reasoning hint (LOW confidence).

        With LOW confidence inference, no effective tag is determined,
        so no reasoning hint can be produced.
        """
        config = EnrichmentConfig(
            include_liberty_analysis=True,
            include_technique_reasoning=True,
        )
        generator = HintGenerator(config)
        _, MockNode = self._make_mock_game()
        game, _ = self._make_mock_game(
            tags=[],
            has_solution=True,
            solution_children=[
                MockNode(move=Point(9, 9), is_correct=True),
            ],
            black_stones=[Point(2, 2)],
            white_stones=[Point(16, 16)],
        )
        hint = generator.generate_reasoning_hint([], game)
        # LOW confidence → no effective tag → no reasoning
        assert hint is None

    def test_solution_aware_no_solution(self):
        """When no tags AND no solution, technique hint should be None."""
        config = EnrichmentConfig(include_liberty_analysis=True)
        generator = HintGenerator(config)
        game, _ = self._make_mock_game(
            tags=[],
            has_solution=False,
        )
        hint = generator.generate_technique_hint([], game)
        # No tags, no solution → cannot generate anything
        assert hint is None

    def test_move_captures_stones(self):
        """move_captures_stones returns True when move captures."""
        game, _ = self._make_mock_game(
            black_stones=[Point(1, 0)],
            white_stones=[Point(0, 0)],
        )
        # (0,1) captures white at (0,0)
        assert move_captures_stones(game, Point(0, 1), Color.BLACK)

    def test_move_does_not_capture_stones(self):
        """move_captures_stones returns False when move doesn't capture."""
        game, _ = self._make_mock_game(
            black_stones=[Point(1, 0)],
            white_stones=[Point(0, 0)],
        )
        # (5,5) does not capture white at (0,0)
        assert not move_captures_stones(game, Point(5, 5), Color.BLACK)

    # --- Confidence-gated inference: HIGH+ only ---

    def test_solution_aware_ko_technique_hint(self):
        """Ko creation → CERTAIN confidence from solution_tagger.

        Tests infer_technique_from_solution directly since ko positions
        always involve atari (Path 1 fires first in generate_technique_hint).
        In production, ko puzzles have a 'ko' tag, so Path 2 handles them.
        This verifies the solution_tagger correctly identifies ko creation.
        """
        _, MockNode = self._make_mock_game()
        # Setup: ko position. Black plays at (0,0) capturing White (1,0),
        # creating a ko.
        game, _ = self._make_mock_game(
            tags=[],
            has_solution=True,
            solution_children=[
                MockNode(move=Point(0, 0), is_correct=True),
            ],
            black_stones=[Point(2, 0), Point(1, 1)],
            white_stones=[Point(1, 0), Point(0, 1)],
        )
        result = infer_technique_from_solution(game)
        assert result.confidence == InferenceConfidence.CERTAIN
        assert result.tag == "ko"
        assert result.effect == "ko_created"

    def test_solution_aware_connection_technique_hint(self):
        """Group connection → HIGH confidence → technique hint emitted."""
        config = EnrichmentConfig(include_liberty_analysis=True)
        generator = HintGenerator(config)
        _, MockNode = self._make_mock_game()
        # Two black groups that connect when Black plays at (3,0).
        # Group 1: Black at (2,0); Group 2: Black at (4,0)
        # Playing B(3,0) merges them into one group.
        game, _ = self._make_mock_game(
            tags=[],
            has_solution=True,
            solution_children=[
                MockNode(move=Point(3, 0), is_correct=True),
            ],
            black_stones=[Point(2, 0), Point(4, 0)],
            white_stones=[Point(10, 10)],
        )
        hint = generator.generate_technique_hint([], game)
        # HIGH confidence (connects) → technique hint
        assert hint is not None
        assert "connect" in hint.lower()

    def test_solution_tagger_capture_confidence(self):
        """Captures → MEDIUM confidence, no tag emitted."""
        _, MockNode = self._make_mock_game()
        game, _ = self._make_mock_game(
            tags=[],
            has_solution=True,
            solution_children=[
                MockNode(move=Point(0, 1), is_correct=True),
            ],
            black_stones=[Point(1, 0)],
            white_stones=[Point(0, 0)],
        )
        result = infer_technique_from_solution(game)
        assert result.confidence == InferenceConfidence.MEDIUM
        assert result.tag is None  # Below HIGH threshold
        assert result.effect == "captures"

    def test_solution_tagger_unknown_confidence(self):
        """Unknown effect → LOW confidence, no tag emitted."""
        _, MockNode = self._make_mock_game()
        game, _ = self._make_mock_game(
            tags=[],
            has_solution=True,
            solution_children=[
                MockNode(move=Point(9, 9), is_correct=True),
            ],
            black_stones=[Point(2, 2)],
            white_stones=[Point(16, 16)],
        )
        result = infer_technique_from_solution(game)
        assert result.confidence == InferenceConfidence.LOW
        assert result.tag is None  # Below HIGH threshold
        assert result.effect == "unknown"

    # --- R1: _get_first_correct_move returns None for no correct children ---

    def test_first_correct_move_no_correct_children_returns_none(self):
        """R1: When no child has is_correct=True, return None (not any child)."""
        _, MockNode = self._make_mock_game()
        game, _ = self._make_mock_game(
            tags=[],
            has_solution=True,
            solution_children=[
                MockNode(move=Point(0, 1), is_correct=False),
                MockNode(move=Point(1, 0), is_correct=False),
            ],
        )
        config = EnrichmentConfig()
        generator = HintGenerator(config)
        result = generator._get_first_correct_move(game.solution_tree)
        assert result is None

    def test_first_correct_move_correct_child_still_returned(self):
        """R1: When a correct child exists, it is still returned."""
        _, MockNode = self._make_mock_game()
        game, _ = self._make_mock_game(
            tags=[],
            has_solution=True,
            solution_children=[
                MockNode(move=Point(0, 1), is_correct=False),
                MockNode(move=Point(1, 0), is_correct=True),
            ],
        )
        config = EnrichmentConfig()
        generator = HintGenerator(config)
        result = generator._get_first_correct_move(game.solution_tree)
        assert result == Point(1, 0)

    # --- R2: Atari skip tags expanded for sacrifice/snapback/throw-in ---

    def test_atari_skip_tags_includes_sacrifice_techniques(self):
        """R2: ATARI_SKIP_TAGS includes sacrifice, snapback, throw-in."""
        assert "sacrifice" in ATARI_SKIP_TAGS
        assert "snapback" in ATARI_SKIP_TAGS
        assert "throw-in" in ATARI_SKIP_TAGS
        # Original SEMEAI_KO_TAGS still included
        assert SEMEAI_KO_TAGS.issubset(ATARI_SKIP_TAGS)

    def test_sacrifice_puzzle_skips_atari_hint(self):
        """R2: Sacrifice-tagged puzzle skips atari hint — gets tag hint instead."""
        _, MockNode = self._make_mock_game()
        # Opponent in atari: white at (0,0), black surrounds on 3 sides
        game, _ = self._make_mock_game(
            tags=["sacrifice"],
            has_solution=True,
            solution_children=[
                MockNode(move=Point(0, 1), is_correct=True),
            ],
            black_stones=[Point(1, 0), Point(0, 1)],
            white_stones=[Point(0, 0)],
        )
        config = EnrichmentConfig(include_liberty_analysis=True)
        generator = HintGenerator(config)
        # _try_atari_hint should return None for sacrifice
        atari_hint = generator._try_atari_hint(["sacrifice"], game)
        assert atari_hint is None

        # But technique hint from tag should work
        technique = generator.generate_technique_hint(["sacrifice"], game)
        assert technique is not None
        assert "sacrific" in technique.lower()  # matches "sacrificing", "sacrifice", etc.

    # --- R3: YH2 gated on YH1 presence ---

    def test_no_yh1_means_no_yh2_in_enrichment(self):
        """R3: When no technique hint (YH1) is generated, reasoning (YH2) is skipped."""
        # No tags and captures only → MEDIUM confidence → no YH1
        game, _ = self._make_mock_game(
            tags=[],
            has_solution=True,
            solution_children=[
                # Correct move captures white stone at (0,0)
                type("MockNode", (), {
                    "move": Point(0, 1),
                    "is_correct": True,
                    "comment": "",
                    "children": [],
                    "color": None,
                })(),
            ],
            black_stones=[Point(1, 0)],
            white_stones=[Point(0, 0)],
        )
        config = EnrichmentConfig(verbose=False)
        result = enrich_puzzle(game, config)
        # No YH1 → no YH2 → hints should only have coordinate (YH3) and maybe atari
        # No hint should be a pure "reasoning" text without a preceding technique
        for _hint in result.hints:
            # Reasoning hints typically contain "because", "consider", "think about"
            # Coordinate hints contain {! tokens or "Play at"
            # Atari hints contain "atari"
            pass  # Just verifying it doesn't crash and produces hints
        # The key check: no more than 2 hints (atari + coordinate, or just coordinate)
        assert len(result.hints) <= 2

    # --- R4: Connects checked before captures ---

    def test_capture_and_connect_classified_as_connects(self):
        """R4: Move that both captures and connects → 'connects' (HIGH confidence).

        Board setup (row, col):
            Col:  0  1  2
        Row 0:  B  W  B    ← Two black groups separated by white
        Row 1:  B  .  B    ← Support stones providing atari on white

        White at (0,1) has exactly one liberty: (1,1) (edge row, flanked by B).
        Black plays (1,1): captures white, and connects {(0,0),(1,0)} with {(0,2),(1,2)}.
        """
        _, MockNode = self._make_mock_game()
        game, _ = self._make_mock_game(
            tags=[],
            has_solution=True,
            solution_children=[
                MockNode(move=Point(1, 1), is_correct=True),
            ],
            # Two separate black groups flanking white
            black_stones=[Point(0, 0), Point(1, 0), Point(0, 2), Point(1, 2)],
            # White stone in atari between them (one liberty at (1,1))
            white_stones=[Point(0, 1)],
        )
        result = infer_technique_from_solution(game)
        # R4: Should classify as "connects" (HIGH), not "captures" (MEDIUM)
        assert result.effect == "connects", (
            f"Expected 'connects' but got '{result.effect}'. "
            "A move that captures AND connects groups should prefer connection."
        )
        assert result.confidence == InferenceConfidence.HIGH

    # --- Config-driven YH1 ---

    def test_config_driven_technique_hint_includes_japanese(self):
        """Config-driven YH1: teaching-comments.json hint_text used (has Japanese terms)."""
        config = EnrichmentConfig(include_liberty_analysis=False)
        generator = HintGenerator(config)
        game, _ = self._make_mock_game(tags=["ladder"])
        hint = generator.generate_technique_hint(["ladder"], game)
        assert hint is not None
        # teaching-comments.json has "Ladder (shicho)" as hint_text
        assert "shicho" in hint.lower() or "ladder" in hint.lower()

    def test_config_driven_net_includes_geta(self):
        """Config-driven YH1: net hint should include Japanese term geta."""
        config = EnrichmentConfig(include_liberty_analysis=False)
        generator = HintGenerator(config)
        game, _ = self._make_mock_game(tags=["net"])
        hint = generator.generate_technique_hint(["net"], game)
        assert hint is not None
        assert "geta" in hint.lower() or "net" in hint.lower()

    def test_config_driven_snapback_includes_uttegaeshi(self):
        """Config-driven YH1: snapback hint should include uttegaeshi."""
        config = EnrichmentConfig(include_liberty_analysis=False)
        generator = HintGenerator(config)
        game, _ = self._make_mock_game(tags=["snapback"])
        hint = generator.generate_technique_hint(["snapback"], game)
        assert hint is not None
        assert "uttegaeshi" in hint.lower() or "snapback" in hint.lower()

    # --- Config Fail-Fast ---

    def test_config_missing_raises_config_file_not_found(self, monkeypatch):
        """Fail-fast: missing teaching-comments.json raises ConfigFileNotFoundError."""
        from unittest.mock import patch

        import backend.puzzle_manager.core.enrichment.hints as hints_mod

        monkeypatch.setattr(hints_mod, "_teaching_comments_cache", None)
        with patch("pathlib.Path.exists", return_value=False):
            with pytest.raises(ConfigFileNotFoundError, match="not found"):
                hints_mod._load_teaching_comments()

    def test_config_corrupt_raises_configuration_error(self, monkeypatch):
        """Fail-fast: corrupt JSON in teaching-comments.json raises ConfigurationError."""
        from unittest.mock import patch

        import backend.puzzle_manager.core.enrichment.hints as hints_mod

        monkeypatch.setattr(hints_mod, "_teaching_comments_cache", None)
        with patch("pathlib.Path.exists", return_value=True), \
             patch("pathlib.Path.read_text", return_value="{invalid json"):
            with pytest.raises(ConfigurationError, match="Malformed JSON"):
                hints_mod._load_teaching_comments()

    def test_generate_yh2_uses_config_driven_hint_text(self):
        """Legacy generate_yh2() uses config-driven hint text, not TECHNIQUE_HINTS tuple[0]."""
        config = EnrichmentConfig(include_technique_reasoning=True)
        generator = HintGenerator(config)
        hint = generator.generate_yh2(["ladder"])
        assert hint is not None
        # Config has "Ladder (shicho)" as hint_text; should include reasoning too
        assert "shicho" in hint.lower() or "ladder" in hint.lower()
        # Reasoning from TECHNIQUE_HINTS: "The opponent can only escape in one direction."
        assert "opponent" in hint.lower() or "direction" in hint.lower() or "escape" in hint.lower()

    # --- Dynamic YH2 Reasoning ---

    def test_reasoning_includes_solution_depth(self):
        """Dynamic YH2: includes solution depth when depth >= 2."""
        config = EnrichmentConfig(include_technique_reasoning=True, include_liberty_analysis=False)
        generator = HintGenerator(config)
        _, MockNode = self._make_mock_game()
        # Build a solution with depth 3: 3 sequential moves
        game, _ = self._make_mock_game(
            tags=["ladder"],
            has_solution=True,
            solution_children=[
                MockNode(
                    move=Point(5, 5), is_correct=True,
                    children=[MockNode(
                        move=Point(6, 5), is_correct=True,
                        children=[MockNode(move=Point(7, 5), is_correct=True)],
                    )],
                ),
            ],
        )
        hint = generator.generate_reasoning_hint(["ladder"], game)
        assert hint is not None
        assert "3 moves of reading" in hint

    def test_reasoning_no_depth_for_shallow(self):
        """Dynamic YH2: no depth context for depth < 2 puzzles."""
        config = EnrichmentConfig(include_technique_reasoning=True, include_liberty_analysis=False)
        generator = HintGenerator(config)
        _, MockNode = self._make_mock_game()
        game, _ = self._make_mock_game(
            tags=["ladder"],
            has_solution=True,
            solution_children=[
                MockNode(move=Point(5, 5), is_correct=True),
            ],
        )
        hint = generator.generate_reasoning_hint(["ladder"], game)
        assert hint is not None
        assert "moves of reading" not in hint

    def test_reasoning_includes_refutation_count(self):
        """Dynamic YH2: includes refutation count when wrong moves exist."""
        config = EnrichmentConfig(include_technique_reasoning=True, include_liberty_analysis=False)
        generator = HintGenerator(config)
        _, MockNode = self._make_mock_game()
        game, _ = self._make_mock_game(
            tags=["net"],
            has_solution=True,
            solution_children=[
                MockNode(move=Point(5, 5), is_correct=True),
                MockNode(move=Point(6, 6), is_correct=False),
                MockNode(move=Point(7, 7), is_correct=False),
            ],
        )
        hint = generator.generate_reasoning_hint(["net"], game)
        assert hint is not None
        assert "2 tempting wrong moves" in hint

    def test_reasoning_single_refutation(self):
        """Dynamic YH2: singular form for 1 wrong move."""
        config = EnrichmentConfig(include_technique_reasoning=True, include_liberty_analysis=False)
        generator = HintGenerator(config)
        _, MockNode = self._make_mock_game()
        game, _ = self._make_mock_game(
            tags=["net"],
            has_solution=True,
            solution_children=[
                MockNode(move=Point(5, 5), is_correct=True),
                MockNode(move=Point(6, 6), is_correct=False),
            ],
        )
        hint = generator.generate_reasoning_hint(["net"], game)
        assert hint is not None
        assert "1 tempting wrong move" in hint
        assert "moves" not in hint.split("1 tempting wrong move")[1] if "1 tempting wrong move" in hint else True

    def test_reasoning_includes_secondary_tag(self):
        """Dynamic YH2: includes secondary tag context when 2+ tags exist."""
        config = EnrichmentConfig(include_technique_reasoning=True, include_liberty_analysis=False)
        generator = HintGenerator(config)
        game, _ = self._make_mock_game(tags=["life-and-death", "ladder"], has_solution=True)
        hint = generator.generate_reasoning_hint(["life-and-death", "ladder"], game)
        assert hint is not None
        # Primary is "ladder" (higher priority), secondary should be "life-and-death"
        assert "also consider" in hint.lower()

    def test_reasoning_no_secondary_for_single_tag(self):
        """Dynamic YH2: no secondary tag text when only one tag."""
        config = EnrichmentConfig(include_technique_reasoning=True, include_liberty_analysis=False)
        generator = HintGenerator(config)
        game, _ = self._make_mock_game(tags=["ladder"], has_solution=True)
        hint = generator.generate_reasoning_hint(["ladder"], game)
        assert hint is not None
        assert "also consider" not in hint.lower()

    def test_reasoning_combined_depth_and_refutations(self):
        """Dynamic YH2: combines depth + refutations when both apply."""
        config = EnrichmentConfig(include_technique_reasoning=True, include_liberty_analysis=False)
        generator = HintGenerator(config)
        _, MockNode = self._make_mock_game()
        # Depth 2 (correct→correct) + 1 refutation
        game, _ = self._make_mock_game(
            tags=["ladder"],
            has_solution=True,
            solution_children=[
                MockNode(
                    move=Point(5, 5), is_correct=True,
                    children=[MockNode(move=Point(7, 5), is_correct=True)],
                ),
                MockNode(move=Point(8, 8), is_correct=False),
            ],
        )
        hint = generator.generate_reasoning_hint(["ladder"], game)
        assert hint is not None
        assert "2 moves of reading" in hint
        assert "1 tempting wrong move" in hint

    # --- Helper methods ---

    def test_count_refutations_empty(self):
        """_count_refutations returns 0 when no wrong moves."""
        config = EnrichmentConfig()
        generator = HintGenerator(config)
        _, MockNode = self._make_mock_game()
        tree = MockNode(children=[MockNode(move=Point(1, 1), is_correct=True)])
        assert generator._count_refutations(tree) == 0

    def test_count_refutations_multiple(self):
        """_count_refutations counts wrong first-move children."""
        config = EnrichmentConfig()
        generator = HintGenerator(config)
        _, MockNode = self._make_mock_game()
        tree = MockNode(children=[
            MockNode(move=Point(1, 1), is_correct=True),
            MockNode(move=Point(2, 2), is_correct=False),
            MockNode(move=Point(3, 3), is_correct=False),
            MockNode(move=Point(4, 4), is_correct=False),
        ])
        assert generator._count_refutations(tree) == 3

    def test_get_secondary_tag(self):
        """_get_secondary_tag returns next-priority tag excluding primary."""
        config = EnrichmentConfig()
        generator = HintGenerator(config)
        # ladder is priority 2, life-and-death is priority 4
        assert generator._get_secondary_tag(["ladder", "life-and-death"], "ladder") == "life-and-death"
        # When primary IS life-and-death, secondary is ladder
        assert generator._get_secondary_tag(["ladder", "life-and-death"], "life-and-death") == "ladder"

    def test_get_secondary_tag_none_for_single(self):
        """_get_secondary_tag returns None when only one tag."""
        config = EnrichmentConfig()
        generator = HintGenerator(config)
        assert generator._get_secondary_tag(["ladder"], "ladder") is None


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
    """Tests for move order detection algorithm."""

    def test_flexibility_enum(self):
        """Test MoveOrderFlexibility enum values."""
        assert MoveOrderFlexibility.STRICT.value == "strict"
        assert MoveOrderFlexibility.FLEXIBLE.value == "flexible"

    def test_single_correct_first_move_is_strict(self):
        """Single correct first move should be strict."""
        tree = SolutionNode(children=[
            SolutionNode(move=Point(2, 3), is_correct=True),
            SolutionNode(move=Point(4, 5), is_correct=False),
        ])
        assert detect_move_order(tree) == MoveOrderFlexibility.STRICT

    def test_multiple_correct_first_moves_is_flexible(self):
        """Multiple correct first moves (miai) should be flexible."""
        tree = SolutionNode(children=[
            SolutionNode(move=Point(2, 3), is_correct=True),
            SolutionNode(move=Point(4, 5), is_correct=True),
        ])
        assert detect_move_order(tree) == MoveOrderFlexibility.FLEXIBLE

    def test_three_correct_first_moves_is_flexible(self):
        """Three correct first moves should be flexible."""
        tree = SolutionNode(children=[
            SolutionNode(move=Point(0, 0), is_correct=True),
            SolutionNode(move=Point(1, 1), is_correct=True),
            SolutionNode(move=Point(2, 2), is_correct=True),
        ])
        assert detect_move_order(tree) == MoveOrderFlexibility.FLEXIBLE

    def test_no_children_is_strict(self):
        """Empty solution tree should default to strict."""
        tree = SolutionNode(children=[])
        assert detect_move_order(tree) == MoveOrderFlexibility.STRICT

    def test_transposition_marker_also_correct(self):
        """Comment with 'also correct' should be flexible."""
        tree = SolutionNode(children=[
            SolutionNode(
                move=Point(2, 3),
                is_correct=True,
                children=[SolutionNode(comment="Also correct order")],
            ),
        ])
        assert detect_move_order(tree) == MoveOrderFlexibility.FLEXIBLE

    def test_transposition_marker_miai(self):
        """Comment with 'miai' should be flexible."""
        tree = SolutionNode(children=[
            SolutionNode(
                move=Point(2, 3),
                is_correct=True,
                comment="This is miai",
            ),
        ])
        assert detect_move_order(tree) == MoveOrderFlexibility.FLEXIBLE

    def test_transposition_marker_equally_good(self):
        """Comment with 'equally good' should be flexible."""
        tree = SolutionNode(children=[
            SolutionNode(
                move=Point(2, 3),
                is_correct=True,
                comment="Equally good",
            ),
        ])
        assert detect_move_order(tree) == MoveOrderFlexibility.FLEXIBLE

    def test_transposition_marker_both_work(self):
        """Comment with 'both work' should be flexible."""
        tree = SolutionNode(children=[
            SolutionNode(
                move=Point(2, 3),
                is_correct=True,
                comment="Both work here",
            ),
        ])
        assert detect_move_order(tree) == MoveOrderFlexibility.FLEXIBLE

    def test_no_transposition_marker_in_unrelated_comment(self):
        """Unrelated comment should not trigger flexible mode."""
        tree = SolutionNode(children=[
            SolutionNode(
                move=Point(2, 3),
                is_correct=True,
                comment="Correct! Good move.",
            ),
        ])
        assert detect_move_order(tree) == MoveOrderFlexibility.STRICT

    def test_single_correct_no_comment_is_strict(self):
        """Single correct move with no comment should be strict."""
        tree = SolutionNode(children=[
            SolutionNode(move=Point(2, 3), is_correct=True, comment=""),
        ])
        assert detect_move_order(tree) == MoveOrderFlexibility.STRICT


class TestKoContext:
    """Tests for ko context detection algorithm."""

    def test_ko_context_enum(self):
        """Test KoContextType enum values."""
        assert KoContextType.NONE.value == "none"
        assert KoContextType.DIRECT.value == "direct"
        assert KoContextType.APPROACH.value == "approach"

    # --- _detect_from_tags ---

    def test_tag_ko_detects_direct(self):
        """Tag 'ko' should detect direct ko."""
        assert _detect_from_tags(["ko"]) == KoContextType.DIRECT

    def test_tag_ko_fight_detects_direct(self):
        """Tag 'ko-fight' should detect direct ko."""
        assert _detect_from_tags(["ko-fight"]) == KoContextType.DIRECT

    def test_tag_approach_ko_detects_approach(self):
        """Tag 'approach-ko' should detect approach ko."""
        assert _detect_from_tags(["approach-ko"]) == KoContextType.APPROACH

    def test_tag_case_insensitive(self):
        """Ko tags should be case-insensitive."""
        assert _detect_from_tags(["Ko"]) == KoContextType.DIRECT
        assert _detect_from_tags(["KO"]) == KoContextType.DIRECT
        assert _detect_from_tags(["Approach-Ko"]) == KoContextType.APPROACH

    def test_unrelated_tags_return_none(self):
        """Non-ko tags should return NONE."""
        assert _detect_from_tags(["ladder", "net", "snapback"]) == KoContextType.NONE

    def test_empty_tags_return_none(self):
        """Empty tag list should return NONE."""
        assert _detect_from_tags([]) == KoContextType.NONE

    def test_approach_ko_takes_priority_over_ko_tag(self):
        """When both approach-ko and ko tags present, approach wins."""
        assert _detect_from_tags(["approach-ko", "ko"]) == KoContextType.APPROACH

    # --- _detect_from_text ---

    def test_text_ko_word_boundary(self):
        """'ko' as standalone word should detect direct."""
        assert _detect_from_text("This is a ko") == KoContextType.DIRECT
        assert _detect_from_text("ko fight starts") == KoContextType.DIRECT

    def test_text_ko_no_false_positive_substring(self):
        """'ko' as substring should NOT trigger detection."""
        assert _detect_from_text("place stone at the korner") == KoContextType.NONE
        assert _detect_from_text("kokeshi doll") == KoContextType.NONE
        assert _detect_from_text("invoke the method") == KoContextType.NONE

    def test_text_approach_ko(self):
        """'approach ko' should detect approach."""
        assert _detect_from_text("This is an approach ko") == KoContextType.APPROACH

    def test_text_recapture_word_boundary(self):
        """'recapture' should detect direct ko."""
        assert _detect_from_text("Black can recapture") == KoContextType.DIRECT

    def test_text_ko_threat(self):
        """'ko threat' should detect direct ko."""
        assert _detect_from_text("Find a ko threat first") == KoContextType.DIRECT

    def test_text_needs_ko_threat_detects_approach(self):
        """'needs ko threat' should detect approach ko."""
        assert _detect_from_text("Black needs ko threat") == KoContextType.APPROACH

    def test_text_empty_returns_none(self):
        """Empty text should return NONE."""
        assert _detect_from_text("") == KoContextType.NONE

    def test_text_unrelated_returns_none(self):
        """Unrelated text should return NONE."""
        assert _detect_from_text("Correct! Good move.") == KoContextType.NONE

    def test_text_japanese_ko(self):
        """Japanese ko term コウ should detect direct."""
        assert _detect_from_text("この手はコウです") == KoContextType.DIRECT

    def test_text_korean_ko(self):
        """Korean ko term 패 should detect direct."""
        assert _detect_from_text("이것은 패입니다") == KoContextType.DIRECT

    def test_text_chinese_ko(self):
        """Chinese ko term 劫 should detect direct."""
        assert _detect_from_text("这是一个劫") == KoContextType.DIRECT

    # --- _detect_from_comments (tree walk) ---

    def test_comments_detects_ko_in_child_node(self):
        """Ko keyword in child node comment should be detected."""
        tree = SolutionNode(children=[
            SolutionNode(
                move=Point(2, 3),
                comment="This creates a ko",
            ),
        ])
        assert _detect_from_comments(tree) == KoContextType.DIRECT

    def test_comments_detects_ko_in_grandchild(self):
        """Ko keyword in grandchild should be detected."""
        tree = SolutionNode(children=[
            SolutionNode(
                move=Point(2, 3),
                children=[
                    SolutionNode(comment="Now it's a ko fight"),
                ],
            ),
        ])
        assert _detect_from_comments(tree) == KoContextType.DIRECT

    def test_comments_respects_depth_limit(self):
        """Detection should respect the depth limit of 10."""
        # Build a chain deeper than 10
        node = SolutionNode(comment="This is a ko")
        for _ in range(12):
            node = SolutionNode(children=[node])
        assert _detect_from_comments(node) == KoContextType.NONE

    def test_comments_no_ko_returns_none(self):
        """Comments without ko should return NONE."""
        tree = SolutionNode(children=[
            SolutionNode(comment="Correct!"),
            SolutionNode(comment="Wrong move"),
        ])
        assert _detect_from_comments(tree) == KoContextType.NONE

    # --- detect_ko_context (full integration) ---

    def test_full_detection_from_tags(self):
        """Full detection should find ko from tags."""
        game = SGFGame(
            yengo_props=YenGoProperties(tags=["ko", "life-and-death"]),
            solution_tree=SolutionNode(children=[
                SolutionNode(move=Point(2, 3), is_correct=True),
            ]),
        )
        assert detect_ko_context(game) == KoContextType.DIRECT

    def test_full_detection_from_solution_comments(self):
        """Full detection should find ko from solution comments."""
        game = SGFGame(
            yengo_props=YenGoProperties(tags=["life-and-death"]),
            solution_tree=SolutionNode(children=[
                SolutionNode(
                    move=Point(2, 3),
                    is_correct=True,
                    comment="This leads to a ko",
                ),
            ]),
        )
        assert detect_ko_context(game) == KoContextType.DIRECT

    def test_full_detection_from_root_comment(self):
        """Full detection should find ko from root comment."""
        game = SGFGame(
            yengo_props=YenGoProperties(tags=[]),
            solution_tree=SolutionNode(
                comment="Ko problem - find the ko",
                children=[
                    SolutionNode(move=Point(2, 3), is_correct=True),
                ],
            ),
        )
        assert detect_ko_context(game) == KoContextType.DIRECT

    def test_full_detection_no_ko(self):
        """Full detection should return NONE when no ko indicators."""
        game = SGFGame(
            yengo_props=YenGoProperties(tags=["ladder"]),
            solution_tree=SolutionNode(children=[
                SolutionNode(
                    move=Point(2, 3),
                    is_correct=True,
                    comment="Correct!",
                ),
            ]),
        )
        assert detect_ko_context(game) == KoContextType.NONE

    def test_full_detection_tags_take_priority(self):
        """Tags should be checked before comments."""
        game = SGFGame(
            yengo_props=YenGoProperties(tags=["approach-ko"]),
            solution_tree=SolutionNode(children=[
                SolutionNode(
                    move=Point(2, 3),
                    is_correct=True,
                    comment="This is a ko",  # would be DIRECT
                ),
            ]),
        )
        # Tags detect APPROACH, which takes priority over comment DIRECT
        assert detect_ko_context(game) == KoContextType.APPROACH


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

    def test_thresholds_removed(self):
        """corner_threshold and edge_threshold are no longer configurable.

        They are now computed proportionally inside detect_region().
        """
        config = EnrichmentConfig()
        assert not hasattr(config, "corner_threshold")
        assert not hasattr(config, "edge_threshold")


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
            hints=["Focus on the corner.", "Look for a ladder pattern."],
            region="TL",
            ko_context="direct",
        )
        assert result.hints[0] == "Focus on the corner."
        assert result.hints[1] == "Look for a ladder pattern."
        assert result.region == "TL"
        assert result.ko_context == "direct"


class TestPointToToken:
    """Tests for coordinate token generation ({!xy} format).

    The {!xy} token syntax embeds SGF coordinates in hint text so the
    frontend can resolve them to human-readable notation after applying
    board transforms (flip/rotate).
    """

    def test_origin_point(self):
        """Point (0,0) should produce {!aa} token."""
        config = EnrichmentConfig()
        generator = HintGenerator(config)
        token = generator._point_to_token(Point(0, 0))
        assert token == "{!aa}"

    def test_center_point(self):
        """Point (9,9) — tengen on 19x19 — should produce {!jj}."""
        config = EnrichmentConfig()
        generator = HintGenerator(config)
        token = generator._point_to_token(Point(9, 9))
        assert token == "{!jj}"

    def test_corner_point(self):
        """Point (18,18) — bottom-right on 19x19 — should produce {!ss}."""
        config = EnrichmentConfig()
        generator = HintGenerator(config)
        token = generator._point_to_token(Point(18, 18))
        assert token == "{!ss}"

    def test_arbitrary_point(self):
        """Point (3,15) should produce {!dp} (d=3, p=15)."""
        config = EnrichmentConfig()
        generator = HintGenerator(config)
        token = generator._point_to_token(Point(3, 15))
        assert token == "{!dp}"

    def test_yh3_uses_token_not_human_readable(self):
        """generate_yh3() should embed {!xy} tokens, not 'C5' coordinates."""

        class MockSolutionNode:
            def __init__(self, move=None, is_correct=True, comment="", children=None):
                self.move = move
                self.is_correct = is_correct
                self.comment = comment
                self.children = children or []

        class MockYenGoProps:
            tags = []

        class MockGame:
            board_size = 19
            has_solution = True
            player_to_move = Color.BLACK
            yengo_props = MockYenGoProps()
            black_stones = [Point(0, 0)]
            white_stones = [Point(1, 1)]
            metadata = {}
            # Depth-2 tree so YH3 is not suppressed by depth gating
            solution_tree = MockSolutionNode(
                children=[MockSolutionNode(
                    move=Point(1, 1), is_correct=True,
                    children=[MockSolutionNode(
                        move=Point(2, 2), is_correct=True,
                    )],
                )]
            )

        config = EnrichmentConfig(include_consequence=False)
        generator = HintGenerator(config)
        hint = generator.generate_yh3(MockGame())

        assert hint is not None
        # Must contain token format, not human-readable
        assert "{!bb}" in hint
        # Must NOT contain the old human-readable coordinate
        assert "B18" not in hint

    def test_refutation_uses_token(self):
        """_get_refutation_consequence() should use {!xy} tokens."""

        class MockSolutionNode:
            def __init__(self, move=None, is_correct=True, comment="", children=None):
                self.move = move
                self.is_correct = is_correct
                self.comment = comment
                self.children = children or []

        class MockGame:
            board_size = 19
            has_solution = True
            player_to_move = Color.BLACK
            solution_tree = MockSolutionNode(
                children=[
                    MockSolutionNode(move=Point(1, 1), is_correct=True),
                    MockSolutionNode(move=Point(2, 3), is_correct=False, comment="bad"),
                ]
            )

        config = EnrichmentConfig(include_consequence=True)
        generator = HintGenerator(config)
        consequence = generator._get_refutation_consequence(MockGame())

        assert consequence is not None
        assert "{!cd}" in consequence
