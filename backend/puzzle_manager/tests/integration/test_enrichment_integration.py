"""
Integration tests for the enrichment module.

Tests with real SGF files and full pipeline integration.
"""


from backend.puzzle_manager.core.enrichment import (
    EnrichmentConfig,
    enrich_puzzle,
)
from backend.puzzle_manager.core.enrichment.hints import HintGenerator
from backend.puzzle_manager.core.sgf_parser import parse_sgf

# Sample SGF data for testing
SIMPLE_CORNER_PUZZLE = """
(;GM[1]FF[4]SZ[19]
AB[aa][ba][ab]
AW[ca][cb][bc]
PL[B]
C[Black to play - capture the white stones]
(;B[bb]C[Correct!])
(;B[ac]C[Wrong move]))
"""

LADDER_PUZZLE = """
(;GM[1]FF[4]SZ[19]
AB[cc][cd][dc][dd][ec]
AW[cb][db][bc][bd]
PL[B]
C[Ladder problem]
YT[ladder]
(;B[eb]C[Correct - starts the ladder]))
"""

KO_PUZZLE = """
(;GM[1]FF[4]SZ[19]
AB[aa][ba][ab][ca]
AW[bb][bc][ac][cb]
PL[B]
C[Ko problem]
YT[ko]
(;B[cc]C[Correct - starts the ko]))
"""

CENTER_PUZZLE = """
(;GM[1]FF[4]SZ[19]
AB[jj][ji][kj][jk]
AW[ii][ij][ik][ki]
PL[B]
C[Center life-and-death]
(;B[ih]C[Correct]))
"""


class TestEnrichPuzzleIntegration:
    """Integration tests for enrich_puzzle with real SGF data."""

    def test_simple_corner_puzzle(self):
        """Test enrichment of a simple corner puzzle without tags.

        With confidence gating, no-tag puzzles with captures (MEDIUM
        confidence) only get coordinate hints (YH3). No technique or
        reasoning hints are emitted to avoid guessing.
        """
        game = parse_sgf(SIMPLE_CORNER_PUZZLE)
        config = EnrichmentConfig(verbose=False)
        result = enrich_puzzle(game, config)

        # Should detect top-left region
        assert result.region == "TL"

        # No tags + captures = MEDIUM confidence → only coordinate hint.
        # The atari path may also fire if opponent is in atari and move captures.
        assert len(result.hints) >= 1
        # At least one hint should contain coordinate token (YH3)
        assert any("{!" in h for h in result.hints)

    def test_ladder_puzzle_with_tags(self):
        """Test enrichment of a ladder puzzle with technique tags."""
        game = parse_sgf(LADDER_PUZZLE)
        config = EnrichmentConfig(verbose=False)
        result = enrich_puzzle(game, config)

        # YH1 = technique hint mentioning ladder, YH2 = reasoning
        # YH3 = coordinate (always generated when solution exists)
        assert len(result.hints) >= 2
        assert "ladder" in result.hints[0].lower()

    def test_ko_puzzle_detection(self):
        """Test ko context detection from tags."""
        game = parse_sgf(KO_PUZZLE)
        config = EnrichmentConfig(verbose=False)
        result = enrich_puzzle(game, config)

        # Should detect ko context
        assert result.ko_context == "direct"

    def test_center_puzzle_region(self):
        """Test center region detection."""
        game = parse_sgf(CENTER_PUZZLE)
        config = EnrichmentConfig(verbose=False)
        result = enrich_puzzle(game, config)

        # Should detect center region
        assert result.region == "C"

    def test_enrichment_disabled(self):
        """Test that enrichment can be disabled."""
        game = parse_sgf(SIMPLE_CORNER_PUZZLE)
        config = EnrichmentConfig(
            enable_hints=False,
            enable_region=False,
            enable_ko=False,
            enable_move_order=False,
            enable_refutation=False,
        )
        result = enrich_puzzle(game, config)

        # All should be empty/None when disabled
        assert result.hints == []
        assert result.region is None
        assert result.ko_context is None


class TestHintGeneratorIntegration:
    """Integration tests for hint generator with real game data."""

    def test_yh1_with_liberty_analysis(self):
        """Test YH1 backward compat: returns technique hint for tagged puzzle."""
        game = parse_sgf(LADDER_PUZZLE)
        config = EnrichmentConfig(include_liberty_analysis=True)
        generator = HintGenerator(config)

        hint = generator.generate_yh1(game, region_code="TL")

        assert hint is not None
        assert len(hint) > 0
        # Ladder puzzle → technique hint mentions ladder
        assert "ladder" in hint.lower()

    def test_yh2_multiple_tags(self):
        """Test YH2 with multiple technique tags."""
        config = EnrichmentConfig(include_technique_reasoning=True)
        generator = HintGenerator(config)

        # First matching tag should be used
        hint = generator.generate_yh2(["unknown", "ladder", "net"])
        assert hint is not None
        assert "ladder" in hint.lower()

    def test_yh3_with_solution(self):
        """Test YH3 generation: always generates coordinate when solution exists."""
        config = EnrichmentConfig(include_consequence=True)
        generator = HintGenerator(config)

        # Depth-1 puzzle → coordinate generated (no outcome text)
        game_shallow = parse_sgf(SIMPLE_CORNER_PUZZLE)
        hint_shallow = generator.generate_yh3(game_shallow)
        assert hint_shallow is not None
        assert "{!" in hint_shallow  # Contains coordinate token

        # Deeper puzzle with multi-move solution → also generates
        deeper_sgf = """(;GM[1]FF[4]SZ[19]
        AB[aa][ba][ab]AW[ca][cb][bc]
        PL[B]YT[ladder]
        (;B[bb]C[Correct];W[da];B[db]C[Correct]))"""
        game_deep = parse_sgf(deeper_sgf)
        hint_deep = generator.generate_yh3(game_deep)
        assert hint_deep is not None
        assert "{!" in hint_deep


class TestEnrichmentPerformance:
    """Performance tests for enrichment module.

    Per spec 042: 5-second generous buffer per puzzle.
    """

    def test_enrichment_completes_within_timeout(self):
        """Test that enrichment completes within 5 seconds."""
        import time

        game = parse_sgf(SIMPLE_CORNER_PUZZLE)
        config = EnrichmentConfig()

        start = time.perf_counter()
        result = enrich_puzzle(game, config)
        elapsed = time.perf_counter() - start

        assert result is not None
        assert elapsed < 5.0, f"Enrichment took {elapsed:.2f}s, expected <5s"


class TestEnrichmentEdgeCases:
    """Edge case tests for enrichment."""

    def test_empty_game(self):
        """Test enrichment of empty game."""
        empty_sgf = "(;GM[1]FF[4]SZ[19]PL[B])"
        game = parse_sgf(empty_sgf)
        config = EnrichmentConfig()
        result = enrich_puzzle(game, config)

        # Should handle gracefully
        assert result is not None
        # Region is None when no stones (condition check skips it)
        assert result.region is None

    def test_game_without_solution(self):
        """Test enrichment of game without solution tree."""
        no_solution_sgf = "(;GM[1]FF[4]SZ[19]AB[aa][ba]AW[bb][cb]PL[B])"
        game = parse_sgf(no_solution_sgf)
        config = EnrichmentConfig()
        result = enrich_puzzle(game, config)

        # Should handle gracefully
        assert result is not None
        # No solution = no YH3 (hints may have 0-2 items)
        assert len(result.hints) <= 2

    def test_very_small_board(self):
        """Test enrichment on 9x9 board."""
        small_board_sgf = "(;GM[1]FF[4]SZ[9]AB[cc][dc]AW[cd][dd]PL[B])"
        game = parse_sgf(small_board_sgf)
        config = EnrichmentConfig()
        result = enrich_puzzle(game, config)

        assert result is not None
        assert result.region is not None
