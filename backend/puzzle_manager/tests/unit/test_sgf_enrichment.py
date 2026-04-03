"""
Tests for SGF enrichment functionality (spec-053, spec-103).

Verifies enrichment behavior through the _enrich_sgf() method which uses
SGFBuilder.from_game() internally. Tests cover:
- SO property removal
- Tag sorting and deduplication
- GN standardization
- Root comment handling (preserve by default, remove when configured)
- Empty line removal
- YenGo property injection (YV, YG, YT, YQ, YX, YH, YC, YK, YO, YR)

Note: As of spec-103 Phase 12, the deprecated regex-based methods have been
removed. All tests now use the SGFBuilder-based _enrich_sgf() method.
"""

import pytest

from backend.puzzle_manager.core.enrichment import EnrichmentResult
from backend.puzzle_manager.core.sgf_parser import parse_sgf
from backend.puzzle_manager.stages.analyze import AnalyzeStage


@pytest.fixture
def analyze_stage():
    """Create AnalyzeStage instance for testing."""
    return AnalyzeStage()


class TestSORemoval:
    """Verify SO property is removed from enriched output."""

    def test_so_property_removed(self, analyze_stage):
        """SO property should be removed from SGF."""
        sgf = "(;GM[1]FF[4]SO[https://example.com/puzzle]SZ[9]AB[dd])"
        game = parse_sgf(sgf)
        enrichment = EnrichmentResult()

        result = analyze_stage._enrich_sgf(
            game=game,
            level=2,
            level_slug="beginner",
            tags=[],
            quality="q:2;rc:0",
            complexity="d:2;r:5;s:10;u:1",
            enrichment=enrichment,
            puzzle_id="",
        )

        assert "SO[" not in result
        assert "https://example.com" not in result

    def test_so_property_with_special_chars(self, analyze_stage):
        """SO with special characters should be fully removed."""
        sgf = "(;GM[1]FF[4]SO[https://example.com/puzzle?id=123&foo=bar]SZ[9])"
        game = parse_sgf(sgf)
        enrichment = EnrichmentResult()

        result = analyze_stage._enrich_sgf(
            game=game,
            level=2,
            level_slug="beginner",
            tags=[],
            quality="q:2;rc:0",
            complexity="d:2;r:5;s:10;u:1",
            enrichment=enrichment,
            puzzle_id="",
        )

        assert "SO[" not in result

    def test_no_so_property_still_valid(self, analyze_stage):
        """SGF without SO should be enriched normally."""
        sgf = "(;GM[1]FF[4]SZ[9]AB[dd])"
        game = parse_sgf(sgf)
        enrichment = EnrichmentResult()

        result = analyze_stage._enrich_sgf(
            game=game,
            level=2,
            level_slug="beginner",
            tags=[],
            quality="q:2;rc:0",
            complexity="d:2;r:5;s:10;u:1",
            enrichment=enrichment,
            puzzle_id="",
        )

        # Should still have required YenGo properties
        assert "YV[" in result
        assert "YG[beginner]" in result


class TestTagSortingDeduplication:
    """Verify tag sorting and deduplication."""

    def test_tags_sorted_alphabetically(self, analyze_stage):
        """Tags should be sorted alphabetically in output."""
        sgf = "(;GM[1]FF[4]SZ[9])"
        game = parse_sgf(sgf)
        enrichment = EnrichmentResult()

        result = analyze_stage._enrich_sgf(
            game=game,
            level=5,
            level_slug="intermediate",
            tags=["ko", "ladder", "life-and-death", "atari"],  # Unsorted
            quality="q:3;rc:0",
            complexity="d:3;r:10;s:15;u:1",
            enrichment=enrichment,
            puzzle_id="",
        )

        # Extract YT value from result
        import re
        yt_match = re.search(r'YT\[([^\]]+)\]', result)
        assert yt_match is not None
        tags_str = yt_match.group(1)
        tags = tags_str.split(",")

        # Verify sorted
        assert tags == sorted(tags)
        assert tags == ["atari", "ko", "ladder", "life-and-death"]

    def test_duplicate_tags_removed(self, analyze_stage):
        """Duplicate tags should be deduplicated."""
        sgf = "(;GM[1]FF[4]SZ[9])"
        game = parse_sgf(sgf)
        enrichment = EnrichmentResult()

        result = analyze_stage._enrich_sgf(
            game=game,
            level=2,
            level_slug="beginner",
            tags=["ko", "ladder", "ko", "life-and-death", "ladder"],  # Duplicates
            quality="q:2;rc:0",
            complexity="d:2;r:5;s:10;u:1",
            enrichment=enrichment,
            puzzle_id="",
        )

        import re
        yt_match = re.search(r'YT\[([^\]]+)\]', result)
        assert yt_match is not None
        tags_str = yt_match.group(1)
        tags = tags_str.split(",")

        # No duplicates
        assert len(tags) == len(set(tags))
        assert tags == ["ko", "ladder", "life-and-death"]

    def test_empty_tags_no_yt_property(self, analyze_stage):
        """Empty tag list should not produce YT property."""
        sgf = "(;GM[1]FF[4]SZ[9])"
        game = parse_sgf(sgf)
        enrichment = EnrichmentResult()

        result = analyze_stage._enrich_sgf(
            game=game,
            level=1,
            level_slug="novice",
            tags=[],  # Empty
            quality="q:1;rc:0",
            complexity="d:1;r:3;s:5;u:1",
            enrichment=enrichment,
            puzzle_id="",
        )

        assert "YT[" not in result


class TestGNHandlingInEnrichment:
    """Verify GN property behavior in enrichment stage.

    Note: GN standardization to YENGO-{hash} format happens in PUBLISH stage,
    not in analyze/enrichment. The _enrich_sgf method preserves existing GN
    if present, or doesn't add one if missing. Publish stage's
    _update_gn_to_match_hash() sets the final GN based on content hash.
    """

    def test_existing_gn_preserved_in_enrichment(self, analyze_stage):
        """Existing GN is preserved through enrichment (publish sets final GN)."""
        sgf = "(;GM[1]FF[4]SZ[9]GN[Some Puzzle Name])"
        game = parse_sgf(sgf)
        enrichment = EnrichmentResult()

        result = analyze_stage._enrich_sgf(
            game=game,
            level=2,
            level_slug="beginner",
            tags=[],
            quality="q:2;rc:0",
            complexity="d:2;r:5;s:8;u:1",
            enrichment=enrichment,
            puzzle_id="",  # Not used in analyze stage
        )

        # GN is preserved as-is; publish stage will update it
        assert "GN[Some Puzzle Name]" in result

    def test_sgf_without_gn_remains_without_gn(self, analyze_stage):
        """SGF without GN stays without GN (publish adds it)."""
        sgf = "(;GM[1]FF[4]SZ[9]AB[dd])"
        game = parse_sgf(sgf)
        enrichment = EnrichmentResult()

        result = analyze_stage._enrich_sgf(
            game=game,
            level=2,
            level_slug="beginner",
            tags=[],
            quality="q:2;rc:0",
            complexity="d:2;r:5;s:8;u:1",
            enrichment=enrichment,
            puzzle_id="",
        )

        # GN not added by enrichment; publish stage will add it
        # Check that YenGo properties were added
        assert "YG[beginner]" in result
        assert "YQ[q:2;rc:0]" in result

    def test_puzzle_id_param_unused_in_enrichment(self, analyze_stage):
        """puzzle_id parameter is not used for GN in enrichment."""
        sgf = "(;GM[1]FF[4]SZ[9])"
        game = parse_sgf(sgf)
        enrichment = EnrichmentResult()
        puzzle_id = "YENGO-abcdef1234567890"  # Passed but not used

        result = analyze_stage._enrich_sgf(
            game=game,
            level=2,
            level_slug="beginner",
            tags=[],
            quality="q:2;rc:0",
            complexity="d:2;r:5;s:8;u:1",
            enrichment=enrichment,
            puzzle_id=puzzle_id,
        )

        # GN is NOT set in enrichment (publish handles it)
        # puzzle_id param exists for backward compat but not used for GN
        assert "YV[" in result  # Version is set
        assert "YG[beginner]" in result  # Level is set


class TestRootCommentHandling:
    """Verify root comment preservation and removal behavior.

    By default (preserve_root_comment=True), root C[] is preserved in enriched
    output. When preserve_root_comment=False, root C[] is removed. Move comments
    in variations are always preserved.
    """

    def test_root_comment_preserved_by_default(self, analyze_stage):
        """Root-level C[] should be preserved by default."""
        sgf = "(;GM[1]FF[4]C[This is a puzzle about life and death]SZ[9]AB[dd])"
        game = parse_sgf(sgf)
        enrichment = EnrichmentResult()

        result = analyze_stage._enrich_sgf(
            game=game,
            level=2,
            level_slug="beginner",
            tags=[],
            quality="q:2;rc:0",
            complexity="d:2;r:5;s:8;u:1",
            enrichment=enrichment,
            puzzle_id="",
        )

        assert "C[This is a puzzle about life and death]" in result
        # Other properties preserved
        assert "GM[1]" in result
        assert "AB[dd]" in result

    def test_root_comment_removed_when_configured(self, analyze_stage):
        """Root-level C[] should be removed when preserve_root_comment=False."""
        from backend.puzzle_manager.core.enrichment import EnrichmentConfig

        sgf = "(;GM[1]FF[4]C[This is a puzzle about life and death]SZ[9]AB[dd])"
        game = parse_sgf(sgf)
        enrichment = EnrichmentResult()

        result = analyze_stage._enrich_sgf(
            game=game,
            level=2,
            level_slug="beginner",
            tags=[],
            quality="q:2;rc:0",
            complexity="d:2;r:5;s:8;u:1",
            enrichment=enrichment,
            puzzle_id="",
            enrichment_config=EnrichmentConfig(preserve_root_comment=False),
        )

        assert "C[This is a puzzle" not in result
        # Other properties preserved
        assert "GM[1]" in result
        assert "AB[dd]" in result

    def test_no_root_comment_still_valid(self, analyze_stage):
        """SGF without root comment should be enriched normally."""
        sgf = "(;GM[1]FF[4]SZ[9]AB[dd])"
        game = parse_sgf(sgf)
        enrichment = EnrichmentResult()

        result = analyze_stage._enrich_sgf(
            game=game,
            level=2,
            level_slug="beginner",
            tags=[],
            quality="q:2;rc:0",
            complexity="d:2;r:5;s:8;u:1",
            enrichment=enrichment,
            puzzle_id="",
        )

        # Should still have required properties
        assert "YV[" in result
        assert "YG[beginner]" in result


class TestEmptyLineRemoval:
    """Verify empty line removal from SGF output.

    SGFBuilder.build() produces clean output without empty lines.
    """

    def test_no_empty_lines_in_output(self, analyze_stage):
        """Output should not contain empty lines."""
        # Input with empty lines
        sgf = """(;GM[1]FF[4]SZ[9]

AB[dd]

AW[ee])"""
        game = parse_sgf(sgf)
        enrichment = EnrichmentResult()

        result = analyze_stage._enrich_sgf(
            game=game,
            level=2,
            level_slug="beginner",
            tags=[],
            quality="q:2;rc:0",
            complexity="d:2;r:5;s:8;u:1",
            enrichment=enrichment,
            puzzle_id="",
        )

        # No double newlines in output
        assert "\n\n" not in result
        # Content preserved
        assert "AB[dd]" in result
        assert "AW[ee]" in result

    def test_single_line_output_format(self, analyze_stage):
        """Simple SGF should produce clean single-line output."""
        sgf = "(;GM[1]FF[4]SZ[9]AB[dd])"
        game = parse_sgf(sgf)
        enrichment = EnrichmentResult()

        result = analyze_stage._enrich_sgf(
            game=game,
            level=2,
            level_slug="beginner",
            tags=[],
            quality="q:2;rc:0",
            complexity="d:2;r:5;s:8;u:1",
            enrichment=enrichment,
            puzzle_id="",
        )

        # Should start and end properly
        assert result.startswith("(;")
        assert result.endswith(")")


class TestEnrichmentProperties:
    """Test enrichment-specific properties (YH, YC, YK, YO, YR)."""

    def test_enrichment_hints_compact_format(self, analyze_stage):
        """Hints use compact pipe-delimited format: YH[hint1|hint2|hint3]."""
        sgf = "(;GM[1]FF[4]SZ[9])"
        game = parse_sgf(sgf)
        enrichment = EnrichmentResult(
            hints=["Focus on corner", "Look for ladder", "Key move is D5"]
        )

        result = analyze_stage._enrich_sgf(
            game=game,
            level=5,
            level_slug="intermediate",
            tags=["ladder"],
            quality="q:3;rc:1",
            complexity="d:5;r:12;s:18;u:1",
            enrichment=enrichment,
            puzzle_id="",
        )

        # v8 compact format
        assert "YH[Focus on corner|Look for ladder|Key move is D5]" in result

    def test_enrichment_region_property(self, analyze_stage):
        """YC (region) property from enrichment."""
        sgf = "(;GM[1]FF[4]SZ[9])"
        game = parse_sgf(sgf)
        enrichment = EnrichmentResult(region="corner")

        result = analyze_stage._enrich_sgf(
            game=game,
            level=2,
            level_slug="beginner",
            tags=[],
            quality="q:2;rc:0",
            complexity="d:2;r:5;s:8;u:1",
            enrichment=enrichment,
            puzzle_id="",
        )

        assert "YC[corner]" in result

    def test_enrichment_ko_context_property(self, analyze_stage):
        """YK (ko context) property from enrichment."""
        sgf = "(;GM[1]FF[4]SZ[9])"
        game = parse_sgf(sgf)
        enrichment = EnrichmentResult(ko_context="simple")

        result = analyze_stage._enrich_sgf(
            game=game,
            level=2,
            level_slug="beginner",
            tags=[],
            quality="q:2;rc:0",
            complexity="d:2;r:5;s:8;u:1",
            enrichment=enrichment,
            puzzle_id="",
        )

        assert "YK[simple]" in result

    def test_enrichment_ko_none_not_written(self, analyze_stage):
        """YK with 'none' value is NOT written (default)."""
        sgf = "(;GM[1]FF[4]SZ[9])"
        game = parse_sgf(sgf)
        enrichment = EnrichmentResult(ko_context="none")

        result = analyze_stage._enrich_sgf(
            game=game,
            level=2,
            level_slug="beginner",
            tags=[],
            quality="q:2;rc:0",
            complexity="d:2;r:5;s:8;u:1",
            enrichment=enrichment,
            puzzle_id="",
        )

        assert "YK[" not in result  # 'none' is default, not written

    def test_enrichment_move_order_property(self, analyze_stage):
        """YO (move order) property from enrichment."""
        sgf = "(;GM[1]FF[4]SZ[9])"
        game = parse_sgf(sgf)
        enrichment = EnrichmentResult(move_order="strict")

        result = analyze_stage._enrich_sgf(
            game=game,
            level=2,
            level_slug="beginner",
            tags=[],
            quality="q:2;rc:0",
            complexity="d:2;r:5;s:8;u:1",
            enrichment=enrichment,
            puzzle_id="",
        )

        assert "YO[strict]" in result

    def test_enrichment_refutations_property(self, analyze_stage):
        """YR (refutations) property from enrichment."""
        sgf = "(;GM[1]FF[4]SZ[9])"
        game = parse_sgf(sgf)
        enrichment = EnrichmentResult(refutations="3")

        result = analyze_stage._enrich_sgf(
            game=game,
            level=2,
            level_slug="beginner",
            tags=[],
            quality="q:2;rc:0",
            complexity="d:2;r:5;s:8;u:1",
            enrichment=enrichment,
            puzzle_id="",
        )

        assert "YR[3]" in result


class TestYenGoPropertyInjection:
    """Test core YenGo property injection (YV, YG, YT, YQ, YX)."""

    def test_minimal_sgf_basic_properties(self, analyze_stage):
        """Minimal SGF with only required properties."""
        sgf = "(;GM[1]FF[4]SZ[9])"
        game = parse_sgf(sgf)
        enrichment = EnrichmentResult()

        result = analyze_stage._enrich_sgf(
            game=game,
            level=2,
            level_slug="beginner",
            tags=[],
            quality="q:2;rc:0",
            complexity="d:2;r:5;s:10;u:1",
            enrichment=enrichment,
            puzzle_id="",
        )

        # Required YenGo properties
        assert "YV[" in result  # Version injected
        assert "YG[beginner]" in result
        assert "YQ[q:2;rc:0]" in result
        assert "YX[d:2;r:5;s:10;u:1]" in result
        assert "YT[" not in result  # No tags = no YT property

        # Structure preserved
        assert result.startswith("(;")

    def test_existing_yengo_properties_overwritten(self, analyze_stage):
        """Existing YG, YT are set to new values passed as arguments.

        Note: The _enrich_sgf method receives already-resolved values from
        _analyze_puzzle, which uses the policy registry to decide whether to
        preserve or compute. By the time values reach _enrich_sgf, the
        decision is already made.
        """
        sgf = "(;GM[1]FF[4]SZ[9]YG[novice]YT[old-tag,stale])"
        game = parse_sgf(sgf)
        enrichment = EnrichmentResult()

        result = analyze_stage._enrich_sgf(
            game=game,
            level=7,
            level_slug="advanced",
            tags=["new-tag"],
            quality="q:4;rc:2",
            complexity="d:7;r:18;s:25;u:0",
            enrichment=enrichment,
            puzzle_id="",
        )

        # New values applied (passed in as arguments)
        assert "YG[advanced]" in result
        assert "YT[new-tag]" in result
        # Only one occurrence of each property
        assert result.count("YG[") == 1
        assert result.count("YT[") == 1


class TestIntegration:
    """Integration tests for full enrichment functionality."""

    def test_full_enrichment_pipeline(self, analyze_stage):
        """Full enrichment should apply all transformations."""
        sgf = """(;GM[1]FF[4]SZ[9]
GN[Old Name]
SO[https://source.com]
C[Root comment to remove]
YG[beginner]
YT[ko,ladder]

AB[dd][ee]
AW[ff])"""

        game = parse_sgf(sgf)
        enrichment = EnrichmentResult(
            hints=["Focus on corner", "Look for ladder"],
            region="TL",
        )

        result = analyze_stage._enrich_sgf(
            game=game,
            level=5,
            level_slug="intermediate",
            tags=["ladder", "ko", "life-and-death"],
            quality="q:3;rc:2;hc:1",
            complexity="d:5;r:15;s:20;u:1",
            enrichment=enrichment,
            puzzle_id="1234567890abcdef",  # Not used for GN in analyze
        )

        # SO removed
        assert "SO[" not in result

        # Root comment preserved (default: preserve_root_comment=True)
        assert "C[Root comment to remove]" in result

        # GN is preserved (publish stage sets final GN)
        # Existing GN "Old Name" is preserved through enrichment
        assert "GN[Old Name]" in result

        # Tags sorted, deduplicated
        import re
        yt_match = re.search(r'YT\[([^\]]+)\]', result)
        assert yt_match is not None
        assert yt_match.group(1) == "ko,ladder,life-and-death"

        # New level applied
        assert "YG[intermediate]" in result
        assert result.count("YG[") == 1

        # Hints in compact format
        assert "YH[Focus on corner|Look for ladder]" in result

        # Region added
        assert "YC[TL]" in result

        # No empty lines
        assert "\n\n" not in result

        # Stones preserved
        assert "AB[dd]" in result or "AB[dd][ee]" in result
        assert "AW[ff]" in result

    def test_stones_and_variations_preserved(self, analyze_stage):
        """Initial stones and solution variations are preserved."""
        sgf = "(;GM[1]FF[4]SZ[9]AB[dd][ee]AW[ff];B[cc](;W[bb])(;W[aa]))"
        game = parse_sgf(sgf)
        enrichment = EnrichmentResult()

        result = analyze_stage._enrich_sgf(
            game=game,
            level=5,
            level_slug="intermediate",
            tags=[],
            quality="q:3;rc:1",
            complexity="d:4;r:10;s:15;u:1",
            enrichment=enrichment,
            puzzle_id="",
        )

        # Stones preserved (may be in different format)
        assert "AB[" in result
        assert "AW[" in result
        # Solution tree preserved
        assert ";B[cc]" in result or "B[cc]" in result
