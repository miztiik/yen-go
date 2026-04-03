"""
Tests for PropertyPolicyRegistry and property policy system.

Covers:
- Policy loading and registry initialization
- Policy lookup for all property types
- Blocked/preserved/enrichable property sets
- is_enrichment_needed logic for each policy type
- Validators for ENRICH_IF_PARTIAL (YQ, YX)
- is_property_allowed for blocked vs. allowed
- Default value retrieval for enrich_if_absent (SZ)
"""

import pytest

from backend.puzzle_manager.core.enrichment import EnrichmentResult
from backend.puzzle_manager.core.property_policy import (
    PropertyPolicy,
    PropertyPolicyRegistry,
    get_policy_registry,
    validate_complexity_metrics,
    validate_quality_metrics,
)


@pytest.fixture
def registry() -> PropertyPolicyRegistry:
    """Get the real policy registry from config."""
    return get_policy_registry()


class TestPolicyLoading:
    """Test that config/sgf-property-policies.json loads correctly."""

    def test_registry_loads_without_error(self, registry):
        """Registry should load from config file."""
        assert registry is not None

    def test_registry_has_blocked_properties(self, registry):
        """Registry should contain blocked properties."""
        blocked = registry.blocked_properties()
        assert "DT" in blocked
        assert "CA" in blocked
        assert "RE" in blocked
        assert "AP" in blocked
        assert "KM" in blocked
        assert "VW" in blocked
        assert "ST" in blocked

    def test_an_is_not_blocked(self, registry):
        """AN (Annotations) should be preserved, not blocked."""
        assert registry.get_policy("AN") == PropertyPolicy.PRESERVE
        assert "AN" not in registry.blocked_properties()

    def test_registry_has_preserved_properties(self, registry):
        """Registry should contain preserved properties."""
        preserved = registry.preserved_properties()
        assert "PL" in preserved
        assert "GC" in preserved
        assert "PB" in preserved
        assert "PW" in preserved
        assert "AN" in preserved

    def test_registry_has_enrichable_properties(self, registry):
        """Registry should contain enrichable properties."""
        enrichable = registry.enrichable_properties()
        assert "YG" in enrichable
        assert "YT" in enrichable
        assert "YH" in enrichable
        assert "YC" in enrichable
        assert "YK" in enrichable
        assert "YO" in enrichable
        assert "YR" in enrichable
        assert "YL" in enrichable
        assert "YQ" in enrichable
        assert "YX" in enrichable
        assert "SZ" in enrichable


class TestPolicyLookup:
    """Test get_policy for each property category."""

    def test_blocked_policy(self, registry):
        assert registry.get_policy("DT") == PropertyPolicy.BLOCKED

    def test_preserve_policy(self, registry):
        assert registry.get_policy("PL") == PropertyPolicy.PRESERVE

    def test_hardcode_policy(self, registry):
        assert registry.get_policy("FF") == PropertyPolicy.HARDCODE
        assert registry.get_hardcode_value("FF") == "4"
        assert registry.get_policy("GM") == PropertyPolicy.HARDCODE
        assert registry.get_hardcode_value("GM") == "1"

    def test_override_policy(self, registry):
        assert registry.get_policy("YV") == PropertyPolicy.OVERRIDE
        assert registry.get_policy("GN") == PropertyPolicy.OVERRIDE

    def test_enrich_if_absent_policy(self, registry):
        assert registry.get_policy("YT") == PropertyPolicy.ENRICH_IF_ABSENT
        assert registry.get_policy("YG") == PropertyPolicy.ENRICH_IF_ABSENT
        assert registry.get_policy("YH") == PropertyPolicy.ENRICH_IF_ABSENT
        assert registry.get_policy("SZ") == PropertyPolicy.ENRICH_IF_ABSENT

    def test_enrich_if_partial_policy(self, registry):
        assert registry.get_policy("YQ") == PropertyPolicy.ENRICH_IF_PARTIAL
        assert registry.get_policy("YX") == PropertyPolicy.ENRICH_IF_PARTIAL

    def test_remove_policy(self, registry):
        assert registry.get_policy("SO") == PropertyPolicy.REMOVE

    def test_configurable_policy(self, registry):
        assert registry.get_policy("C") == PropertyPolicy.CONFIGURABLE
        assert registry.get_configurable_flag("C") == "preserve_root_comment"
        assert registry.get_configurable_default("C") is True

    def test_unknown_property_returns_none(self, registry):
        assert registry.get_policy("UNKNOWN_PROP") is None


class TestSZEnrichIfAbsent:
    """Test SZ (board size) enrich_if_absent with default value 19."""

    def test_sz_policy_is_enrich_if_absent(self, registry):
        assert registry.get_policy("SZ") == PropertyPolicy.ENRICH_IF_ABSENT

    def test_sz_default_value_is_19(self, registry):
        assert registry.get_enrich_default("SZ") == "19"

    def test_sz_enrichment_needed_when_absent(self, registry):
        """SZ absent -> enrichment needed."""
        assert registry.is_enrichment_needed("SZ", None) is True
        assert registry.is_enrichment_needed("SZ", "") is True

    def test_sz_enrichment_not_needed_when_present(self, registry):
        """SZ present -> no enrichment (preserve source value)."""
        assert registry.is_enrichment_needed("SZ", "9") is False
        assert registry.is_enrichment_needed("SZ", "19") is False
        assert registry.is_enrichment_needed("SZ", 9) is False

    def test_sz_default_19_used_by_parser(self):
        """Parser defaults board_size to 19 when SZ is absent."""
        from backend.puzzle_manager.core.sgf_parser import parse_sgf
        game = parse_sgf("(;GM[1]FF[4]AB[dd])")
        assert game.board_size == 19

    def test_sz_preserved_when_present(self):
        """Parser uses source SZ when present."""
        from backend.puzzle_manager.core.sgf_parser import parse_sgf
        game = parse_sgf("(;GM[1]FF[4]SZ[9]AB[dd])")
        assert game.board_size == 9


class TestIsEnrichmentNeeded:
    """Test is_enrichment_needed for different policy types and value states."""

    def test_override_always_needs_enrichment(self, registry):
        """OVERRIDE policy -> always True, regardless of existing value."""
        assert registry.is_enrichment_needed("YV", 13) is True
        assert registry.is_enrichment_needed("YV", None) is True

    def test_enrich_if_absent_with_none(self, registry):
        """ENRICH_IF_ABSENT with None -> needs enrichment."""
        assert registry.is_enrichment_needed("YT", None) is True

    def test_enrich_if_absent_with_empty_list(self, registry):
        """ENRICH_IF_ABSENT with empty list -> needs enrichment."""
        assert registry.is_enrichment_needed("YT", []) is True
        assert registry.is_enrichment_needed("YL", []) is True

    def test_enrich_if_absent_with_empty_string(self, registry):
        """ENRICH_IF_ABSENT with empty string -> needs enrichment."""
        assert registry.is_enrichment_needed("YC", "") is True

    def test_enrich_if_absent_with_value(self, registry):
        """ENRICH_IF_ABSENT with existing value -> no enrichment needed."""
        assert registry.is_enrichment_needed("YT", ["ko", "ladder"]) is False
        assert registry.is_enrichment_needed("YC", "TL") is False
        assert registry.is_enrichment_needed("YK", "direct") is False
        assert registry.is_enrichment_needed("YO", "strict") is False
        assert registry.is_enrichment_needed("YR", "cd,de") is False
        assert registry.is_enrichment_needed("YH", ["Focus on corner"]) is False

    def test_enrich_if_partial_with_valid_yq(self, registry):
        """Valid YQ -> no enrichment needed."""
        assert registry.is_enrichment_needed("YQ", "q:3;rc:2;hc:1;ac:0") is False

    def test_enrich_if_partial_with_invalid_yq(self, registry):
        """Invalid/partial YQ -> needs enrichment."""
        assert registry.is_enrichment_needed("YQ", "q:3") is True
        assert registry.is_enrichment_needed("YQ", "garbage") is True

    def test_enrich_if_partial_with_missing_yq(self, registry):
        """Missing YQ -> needs enrichment."""
        assert registry.is_enrichment_needed("YQ", None) is True
        assert registry.is_enrichment_needed("YQ", "") is True

    def test_enrich_if_partial_with_valid_yx(self, registry):
        """Valid YX -> no enrichment needed."""
        assert registry.is_enrichment_needed("YX", "d:5;r:13;s:24;u:1") is False

    def test_enrich_if_partial_with_invalid_yx(self, registry):
        """Invalid/partial YX -> needs enrichment."""
        assert registry.is_enrichment_needed("YX", "d:5") is True

    def test_preserve_never_needs_enrichment(self, registry):
        """PRESERVE policy -> never needs enrichment."""
        assert registry.is_enrichment_needed("PL", None) is False
        assert registry.is_enrichment_needed("PL", "B") is False

    def test_blocked_never_needs_enrichment(self, registry):
        """BLOCKED policy -> never needs enrichment."""
        assert registry.is_enrichment_needed("DT", None) is False

    def test_unknown_property_never_needs_enrichment(self, registry):
        """Unknown property -> never needs enrichment."""
        assert registry.is_enrichment_needed("UNKNOWN", "value") is False


class TestIsPropertyAllowed:
    """Test is_property_allowed for blocked vs. allowed properties."""

    def test_blocked_properties_not_allowed(self, registry):
        assert registry.is_property_allowed("DT") is False
        assert registry.is_property_allowed("CA") is False
        assert registry.is_property_allowed("RE") is False
        assert registry.is_property_allowed("KM") is False

    def test_preserved_properties_allowed(self, registry):
        assert registry.is_property_allowed("PL") is True
        assert registry.is_property_allowed("GC") is True
        assert registry.is_property_allowed("AN") is True

    def test_remove_properties_allowed(self, registry):
        """REMOVE properties are allowed through parse (deleted later)."""
        assert registry.is_property_allowed("SO") is True

    def test_unknown_properties_allowed_by_default(self, registry):
        """Properties not in registry are allowed (safe default)."""
        assert registry.is_property_allowed("SOME_NEW_PROP") is True

    def test_enrichable_properties_allowed(self, registry):
        assert registry.is_property_allowed("YT") is True
        assert registry.is_property_allowed("YQ") is True


class TestValidators:
    """Test validation functions for ENRICH_IF_PARTIAL properties."""

    def test_valid_quality_metrics(self):
        assert validate_quality_metrics("q:3;rc:2;hc:1;ac:0") is True
        assert validate_quality_metrics("q:1;rc:0;hc:0;ac:0") is True
        assert validate_quality_metrics("q:5;rc:99;hc:1;ac:1") is True
        assert validate_quality_metrics("q:5;rc:3;hc:2;ac:2") is True  # hc:2 (teaching text)
        assert validate_quality_metrics("q:4;rc:5;hc:1;ac:3") is True  # ac:3 (verified)

    def test_invalid_quality_metrics(self):
        assert validate_quality_metrics(None) is False
        assert validate_quality_metrics("") is False
        assert validate_quality_metrics("q:3") is False
        assert validate_quality_metrics("q:6;rc:0;hc:0;ac:0") is False  # q > 5
        assert validate_quality_metrics("garbage") is False
        assert validate_quality_metrics("q:3;rc:2;hc:1") is False  # missing ac
        assert validate_quality_metrics("q:3;rc:2;hc:1;ac:4") is False  # ac > 3

    def test_valid_complexity_metrics(self):
        assert validate_complexity_metrics("d:5;r:13;s:24;u:1") is True
        assert validate_complexity_metrics("d:0;r:1;s:1;u:0") is True
        assert validate_complexity_metrics("d:99;r:999;s:88;u:1") is True
        # With optional w field (wrong-move count, added by enrichment lab)
        assert validate_complexity_metrics("d:5;r:13;s:24;u:1;w:3") is True
        assert validate_complexity_metrics("d:5;r:13;s:24;u:0;w:5") is True
        # With both w and a fields
        assert validate_complexity_metrics("d:5;r:13;s:24;u:1;w:3;a:2") is True
        # With a but no w (backward compat)
        assert validate_complexity_metrics("d:5;r:13;s:24;u:1;a:2") is True

    def test_invalid_complexity_metrics(self):
        assert validate_complexity_metrics(None) is False
        assert validate_complexity_metrics("") is False
        assert validate_complexity_metrics("d:5") is False
        assert validate_complexity_metrics("d:5;r:13") is False
        assert validate_complexity_metrics("garbage") is False
        # u > 1 is invalid (binary field)
        assert validate_complexity_metrics("d:5;r:13;s:24;u:3") is False


class TestParserBlockedProperties:
    """Test that blocked properties are actually dropped at parse time."""

    def test_blocked_dt_dropped(self):
        """DT (Date) should be dropped at parse time."""
        from backend.puzzle_manager.core.sgf_parser import parse_sgf
        sgf = "(;GM[1]FF[4]SZ[9]DT[2026-01-01]AB[dd])"
        game = parse_sgf(sgf)
        assert "DT" not in game.metadata

    def test_blocked_re_dropped(self):
        """RE (Result) should be dropped at parse time."""
        from backend.puzzle_manager.core.sgf_parser import parse_sgf
        sgf = "(;GM[1]FF[4]SZ[9]RE[B+R]AB[dd])"
        game = parse_sgf(sgf)
        assert "RE" not in game.metadata

    def test_blocked_ap_dropped(self):
        """AP (Application) should be dropped at parse time."""
        from backend.puzzle_manager.core.sgf_parser import parse_sgf
        sgf = "(;GM[1]FF[4]SZ[9]AP[SomeApp]AB[dd])"
        game = parse_sgf(sgf)
        assert "AP" not in game.metadata

    def test_preserved_an_kept(self):
        """AN (Annotations) should be preserved."""
        from backend.puzzle_manager.core.sgf_parser import parse_sgf
        sgf = "(;GM[1]FF[4]SZ[9]AN[Annotator Name]AB[dd])"
        game = parse_sgf(sgf)
        assert game.metadata.get("AN") == "Annotator Name"

    def test_preserved_gc_kept(self):
        """GC (Game Comment) should be preserved."""
        from backend.puzzle_manager.core.sgf_parser import parse_sgf
        sgf = "(;GM[1]FF[4]SZ[9]GC[Some game comment]AB[dd])"
        game = parse_sgf(sgf)
        assert game.metadata.get("GC") == "Some game comment"

    def test_so_still_parsed_for_removal(self):
        """SO should still be parsed (it's REMOVE policy, not BLOCKED)."""
        from backend.puzzle_manager.core.sgf_parser import parse_sgf
        sgf = "(;GM[1]FF[4]SZ[9]SO[https://example.com]AB[dd])"
        game = parse_sgf(sgf)
        assert "SO" in game.metadata


class TestEnrichmentPreservation:
    """Test that existing enrichment properties are preserved when present.

    Uses the full analyze stage _enrich_sgf to verify that source properties
    are not overwritten by computed enrichment when already present.
    """

    @pytest.fixture
    def analyze_stage(self):
        from backend.puzzle_manager.stages.analyze import AnalyzeStage
        return AnalyzeStage()

    def test_existing_yh_preserved(self, analyze_stage):
        """Source YH (hints) should be preserved, enrichment skipped."""
        from backend.puzzle_manager.core.sgf_parser import parse_sgf
        sgf = "(;GM[1]FF[4]SZ[9]YH[Existing hint 1|Existing hint 2])"
        game = parse_sgf(sgf)
        enrichment = EnrichmentResult(hints=["Computed hint 1", "Computed hint 2"])

        result = analyze_stage._enrich_sgf(
            game=game, level=2, level_slug="beginner",
            tags=[], quality="q:2;rc:0;hc:0",
            complexity="d:2;r:5;s:10;u:1",
            enrichment=enrichment, puzzle_id="",
        )

        assert "YH[Existing hint 1|Existing hint 2]" in result
        assert "Computed hint" not in result

    def test_existing_yc_preserved(self, analyze_stage):
        """Source YC (corner) should be preserved, enrichment skipped."""
        from backend.puzzle_manager.core.sgf_parser import parse_sgf
        sgf = "(;GM[1]FF[4]SZ[9]YC[BL])"
        game = parse_sgf(sgf)
        enrichment = EnrichmentResult(region="TL")

        result = analyze_stage._enrich_sgf(
            game=game, level=2, level_slug="beginner",
            tags=[], quality="q:2;rc:0;hc:0",
            complexity="d:2;r:5;s:10;u:1",
            enrichment=enrichment, puzzle_id="",
        )

        assert "YC[BL]" in result
        assert "YC[TL]" not in result

    def test_existing_yk_preserved(self, analyze_stage):
        """Source YK (ko context) should be preserved, enrichment skipped."""
        from backend.puzzle_manager.core.sgf_parser import parse_sgf
        sgf = "(;GM[1]FF[4]SZ[9]YK[direct])"
        game = parse_sgf(sgf)
        enrichment = EnrichmentResult(ko_context="approach")

        result = analyze_stage._enrich_sgf(
            game=game, level=2, level_slug="beginner",
            tags=[], quality="q:2;rc:0;hc:0",
            complexity="d:2;r:5;s:10;u:1",
            enrichment=enrichment, puzzle_id="",
        )

        assert "YK[direct]" in result
        assert "YK[approach]" not in result

    def test_existing_yo_preserved(self, analyze_stage):
        """Source YO (move order) should be preserved, enrichment skipped."""
        from backend.puzzle_manager.core.sgf_parser import parse_sgf
        sgf = "(;GM[1]FF[4]SZ[9]YO[flexible])"
        game = parse_sgf(sgf)
        enrichment = EnrichmentResult(move_order="strict")

        result = analyze_stage._enrich_sgf(
            game=game, level=2, level_slug="beginner",
            tags=[], quality="q:2;rc:0;hc:0",
            complexity="d:2;r:5;s:10;u:1",
            enrichment=enrichment, puzzle_id="",
        )

        assert "YO[flexible]" in result
        assert "YO[strict]" not in result

    def test_existing_yr_preserved(self, analyze_stage):
        """Source YR (refutations) should be preserved, enrichment skipped."""
        from backend.puzzle_manager.core.sgf_parser import parse_sgf
        sgf = "(;GM[1]FF[4]SZ[9]YR[cd,de])"
        game = parse_sgf(sgf)
        enrichment = EnrichmentResult(refutations="ab,bc")

        result = analyze_stage._enrich_sgf(
            game=game, level=2, level_slug="beginner",
            tags=[], quality="q:2;rc:0;hc:0",
            complexity="d:2;r:5;s:10;u:1",
            enrichment=enrichment, puzzle_id="",
        )

        assert "YR[cd,de]" in result
        assert "YR[ab,bc]" not in result

    def test_absent_yh_gets_enriched(self, analyze_stage):
        """Absent YH should be enriched with computed hints."""
        from backend.puzzle_manager.core.sgf_parser import parse_sgf
        sgf = "(;GM[1]FF[4]SZ[9])"
        game = parse_sgf(sgf)
        enrichment = EnrichmentResult(hints=["Computed hint"])

        result = analyze_stage._enrich_sgf(
            game=game, level=2, level_slug="beginner",
            tags=[], quality="q:2;rc:0;hc:0",
            complexity="d:2;r:5;s:10;u:1",
            enrichment=enrichment, puzzle_id="",
        )

        assert "YH[Computed hint]" in result

    def test_absent_yc_gets_enriched(self, analyze_stage):
        """Absent YC should be enriched with computed region."""
        from backend.puzzle_manager.core.sgf_parser import parse_sgf
        sgf = "(;GM[1]FF[4]SZ[9])"
        game = parse_sgf(sgf)
        enrichment = EnrichmentResult(region="TL")

        result = analyze_stage._enrich_sgf(
            game=game, level=2, level_slug="beginner",
            tags=[], quality="q:2;rc:0;hc:0",
            complexity="d:2;r:5;s:10;u:1",
            enrichment=enrichment, puzzle_id="",
        )

        assert "YC[TL]" in result
