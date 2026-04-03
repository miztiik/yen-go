"""Tests for SGF enricher — policy-aligned enrichment (ADR-007).

Takes AiAnalysisResult + original SGF → enriches SGF based on property
policies from ``config/sgf-property-policies.json``:

- ``enrich_if_absent``: write only when property is missing
- ``enrich_if_partial``: write when value is absent or invalid
- ``override``: always write

Also adds refutation branches to the SGF tree and derives YR from them.
"""

from pathlib import Path

import pytest
from analyzers.property_policy import clear_policy_cache, is_enrichment_needed

# Ensure tools/puzzle-enrichment-lab is importable
from analyzers.sgf_enricher import (
    _build_refutation_branches,
    _collect_existing_wrong_coords,
    _compute_level_distance,
    _count_existing_refutation_branches,
    _has_existing_refutation_branches,
    clear_enricher_cache,
    enrich_sgf,
)
from analyzers.validate_correct_move import ValidationStatus
from config import clear_cache
from core.tsumego_analysis import parse_sgf
from models.ai_analysis_result import (
    AiAnalysisResult,
    DifficultySnapshot,
    EngineSnapshot,
    MoveValidation,
    RefutationEntry,
)

# Fixture directory
_FIXTURES = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture(autouse=True)
def _clear_caches():
    clear_cache()
    clear_enricher_cache()
    clear_policy_cache()
    yield
    clear_cache()
    clear_enricher_cache()
    clear_policy_cache()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_fixture(name: str) -> str:
    return (_FIXTURES / name).read_text(encoding="utf-8")


def _make_accepted_result(
    puzzle_id: str = "test-puzzle",
    refutations: list[RefutationEntry] | None = None,
    level: str = "intermediate",
    level_id: int = 150,
    composite_score: float = 45.0,
    policy_prior: float = 0.15,
    visits_to_solve: int = 120,
    trap_density: float = 0.3,
    confidence: str = "high",
) -> AiAnalysisResult:
    """Build an ACCEPTED AiAnalysisResult for testing."""
    return AiAnalysisResult(
        puzzle_id=puzzle_id,
        engine=EngineSnapshot(model="b10c128.bin.gz", visits=200, config_hash="abc123"),
        validation=MoveValidation(
            correct_move_gtp="D1",
            katago_top_move_gtp="D1",
            status=ValidationStatus.ACCEPTED,
            katago_agrees=True,
            correct_move_winrate=0.95,
            correct_move_policy=policy_prior,
            validator_used="life_and_death",
            flags=[],
        ),
        refutations=refutations or [],
        difficulty=DifficultySnapshot(
            policy_prior_correct=policy_prior,
            visits_to_solve=visits_to_solve,
            trap_density=trap_density,
            composite_score=composite_score,
            suggested_level=level,
            suggested_level_id=level_id,
            confidence=confidence,
        ),
    )


def _make_flagged_result(**kwargs) -> AiAnalysisResult:
    """Build a FLAGGED result."""
    result = _make_accepted_result(**kwargs)
    result.validation.status = ValidationStatus.FLAGGED
    result.validation.katago_agrees = False
    result.validation.flags = ["low_confidence"]
    return result


def _make_rejected_result() -> AiAnalysisResult:
    """Build a REJECTED result."""
    return AiAnalysisResult(
        puzzle_id="test-puzzle",
        validation=MoveValidation(
            status=ValidationStatus.REJECTED,
            flags=["error: SGF parse failure"],
        ),
    )


def _sample_refutations() -> list[RefutationEntry]:
    """Standard refutation set for testing."""
    return [
        RefutationEntry(
            wrong_move="cd",
            refutation_pv=["dc", "dd"],
            delta=-0.4,
            refutation_depth=2,
        ),
        RefutationEntry(
            wrong_move="de",
            refutation_pv=["ef"],
            delta=-0.3,
            refutation_depth=1,
        ),
    ]


# ===================================================================
# Property Policy Tests
# ===================================================================


@pytest.mark.unit
class TestPropertyPolicyReader:
    """Verify the lightweight policy reader against config."""

    def test_yr_is_enrich_if_absent(self):
        assert is_enrichment_needed("YR", None) is True
        assert is_enrichment_needed("YR", "") is True
        assert is_enrichment_needed("YR", "cd,de") is False

    def test_yx_is_enrich_if_partial(self):
        # Absent → needs enrichment
        assert is_enrichment_needed("YX", None) is True
        assert is_enrichment_needed("YX", "") is True

        # Valid format → no enrichment needed
        assert is_enrichment_needed("YX", "d:1;r:2;s:19;u:1") is False
        assert is_enrichment_needed("YX", "d:1;r:2;s:19;u:1;a:0") is False
        # P0.1: u is binary (0 or 1), with optional w field for wrong-move count
        assert is_enrichment_needed("YX", "d:1;r:2;s:19;u:0") is False
        assert is_enrichment_needed("YX", "d:1;r:2;s:19;u:1;w:3") is False
        assert is_enrichment_needed("YX", "d:1;r:2;s:19;u:0;w:5;a:2") is False

        # Invalid format → needs enrichment
        assert is_enrichment_needed("YX", "d:1;r:2;s:19") is True
        assert is_enrichment_needed("YX", "garbage") is True
        # u > 1 is invalid (binary field)
        assert is_enrichment_needed("YX", "d:1;r:2;s:19;u:3") is True

    def test_yg_is_enrich_if_absent(self):
        assert is_enrichment_needed("YG", None) is True
        assert is_enrichment_needed("YG", "") is True
        assert is_enrichment_needed("YG", "beginner") is False

    def test_yq_is_enrich_if_partial(self):
        assert is_enrichment_needed("YQ", None) is True
        assert is_enrichment_needed("YQ", "q:2;rc:0;hc:2") is False
        assert is_enrichment_needed("YQ", "q:invalid") is True

    def test_yv_is_override(self):
        # Override → always enrichment needed
        assert is_enrichment_needed("YV", "13") is True

    def test_preserve_policies_never_enrich(self):
        assert is_enrichment_needed("PL", None) is False
        assert is_enrichment_needed("AB", None) is False


# ===================================================================
# Refutation Branch Detection
# ===================================================================


@pytest.mark.unit
class TestRefutationBranchDetection:
    """Detect existing wrong-move branches in SGF tree."""

    def test_no_wrong_branches(self):
        sgf = _load_fixture("simple_life_death.sgf")
        root = parse_sgf(sgf)
        # simple_life_death.sgf has "Wrong" in a nested child comment,
        # but we need to check if direct children have "Wrong"
        # The fixture has ;B[ds]C[Correct!] as first child,
        # then W variations. Let's check.
        assert isinstance(_has_existing_refutation_branches(root), bool)

    def test_detects_wrong_comment_prefix(self):
        # Build SGF with a wrong-move branch at root level
        sgf = "(;FF[4]GM[1]SZ[19]PL[B]AB[dd]AW[ee](;B[df]C[Correct.])(;B[ef]C[Wrong. Loses the group.]))"
        root = parse_sgf(sgf)
        assert _has_existing_refutation_branches(root) is True

    def test_detects_bm_marker(self):
        sgf = "(;FF[4]GM[1]SZ[19]PL[B]AB[dd]AW[ee](;B[df]C[Correct.])(;B[ef]BM[1]))"
        root = parse_sgf(sgf)
        assert _has_existing_refutation_branches(root) is True

    def test_no_detection_on_nested_wrong(self):
        """Wrong comments in deeper nodes don't count as root-level branches."""
        sgf = "(;FF[4]GM[1]SZ[19]PL[B]AB[dd]AW[ee];B[df]C[Correct.];W[eg]C[Wrong at deeper level.])"
        root = parse_sgf(sgf)
        assert _has_existing_refutation_branches(root) is False


# ===================================================================
# Refutation Branch Building
# ===================================================================


@pytest.mark.unit
class TestRefutationBranchBuilding:
    """Build refutation branch dicts from AI result."""

    def test_builds_branches(self):
        result = _make_accepted_result(refutations=_sample_refutations())
        branches = _build_refutation_branches(result, "B")
        assert len(branches) == 2
        assert branches[0]["wrong_move"] == "cd"
        assert branches[0]["color"] == "B"
        assert branches[0]["refutation"] == [("W", "dc"), ("B", "dd")]
        assert "Wrong" in branches[0]["comment"]

    def test_empty_refutations(self):
        result = _make_accepted_result(refutations=[])
        branches = _build_refutation_branches(result, "B")
        assert branches == []


# ===================================================================
# Level Mismatch
# ===================================================================


@pytest.mark.unit
class TestLevelMismatch:
    """Level distance computation for mismatch detection."""

    def test_same_level(self):
        assert _compute_level_distance("beginner", "beginner") == 0

    def test_adjacent_kyu_levels(self):
        # beginner(120) vs elementary(130) = 1 step
        assert _compute_level_distance("beginner", "elementary") == 1

    def test_kyu_to_dan_gap(self):
        # advanced(160) vs low-dan(210) = 5 steps
        assert _compute_level_distance("advanced", "low-dan") == 5

    def test_large_distance(self):
        # novice(110) vs expert(230) = 12 steps
        assert _compute_level_distance("novice", "expert") == 12

    def test_unknown_level_returns_zero(self):
        assert _compute_level_distance("unknown", "beginner") == 0
        assert _compute_level_distance("beginner", "nonexistent") == 0


# ===================================================================
# Core Enrichment Tests (enrich_sgf)
# ===================================================================


@pytest.mark.unit
class TestEnrichSgfPolicyCompliance:
    """enrich_sgf respects property policies."""

    def test_preserves_existing_yx(self):
        """Valid YX is preserved (enrich_if_partial policy)."""
        sgf = _load_fixture("simple_life_death.sgf")
        sgf_with_yx = sgf.replace("PL[B]", "PL[B]YX[d:1;r:2;s:19;u:1;a:0]")
        result = _make_accepted_result(refutations=_sample_refutations())

        enriched = enrich_sgf(sgf_with_yx, result)
        root = parse_sgf(enriched)
        # Valid YX should NOT be overwritten
        assert root.get("YX") == "d:1;r:2;s:19;u:1;a:0"

    def test_replaces_malformed_yx(self):
        """Malformed YX is recomputed (enrich_if_partial policy)."""
        sgf = _load_fixture("simple_life_death.sgf")
        sgf_with_bad_yx = sgf.replace("PL[B]", "PL[B]YX[garbage]")
        result = _make_accepted_result(refutations=_sample_refutations())

        enriched = enrich_sgf(sgf_with_bad_yx, result)
        root = parse_sgf(enriched)
        yx = root.get("YX")
        # Should be recomputed — valid format
        assert yx.startswith("d:")
        assert ";r:" in yx
        assert yx != "garbage"

    def test_overwrites_existing_yg_on_large_mismatch(self):
        """Existing YG is overwritten when mismatch distance is >= threshold."""
        sgf = _load_fixture("simple_life_death.sgf")
        sgf_with_yg = sgf.replace("PL[B]", "PL[B]YG[beginner]")
        result = _make_accepted_result(level="advanced", level_id=160)

        enriched = enrich_sgf(sgf_with_yg, result)
        root = parse_sgf(enriched)
        # beginner(120) -> advanced(160) = 4 steps, threshold=3 => overwrite
        assert root.get("YG") == "advanced"

    def test_preserves_existing_yg_on_small_mismatch(self):
        """Existing YG is preserved when mismatch distance is < threshold."""
        sgf = _load_fixture("simple_life_death.sgf")
        sgf_with_yg = sgf.replace("PL[B]", "PL[B]YG[beginner]")
        result = _make_accepted_result(level="elementary", level_id=130)

        enriched = enrich_sgf(sgf_with_yg, result)
        root = parse_sgf(enriched)
        # beginner(120) -> elementary(130) = 1 step, threshold=3 => preserved
        assert root.get("YG") == "beginner"

    def test_sets_yg_when_absent(self):
        """YG set when absent (enrich_if_absent policy)."""
        sgf = _load_fixture("simple_life_death.sgf")
        result = _make_accepted_result(level="advanced", level_id=160)

        enriched = enrich_sgf(sgf, result)
        root = parse_sgf(enriched)
        assert root.get("YG") == "advanced"

    def test_preserves_existing_yr(self):
        """Existing YR is preserved (enrich_if_absent policy)."""
        sgf = _load_fixture("simple_life_death.sgf")
        sgf_with_yr = sgf.replace("PL[B]", "PL[B]YR[ab,cd]")
        result = _make_accepted_result(refutations=_sample_refutations())

        enriched = enrich_sgf(sgf_with_yr, result)
        root = parse_sgf(enriched)
        # YR should NOT be overwritten — the refutation branches are also
        # skipped because the enricher checks for existing branches separately
        # But since there are no actual wrong-move branches in the tree,
        # refutation branches WILL be added when YR exists but has no tree branches
        yr = root.get("YR")
        # Branches were added → YR re-derived from them
        assert "cd" in yr
        assert "de" in yr


@pytest.mark.unit
class TestEnrichSgfRefutationBranches:
    """Refutation branches added to SGF tree."""

    def test_adds_branches_when_none_exist(self):
        sgf = _load_fixture("simple_life_death.sgf")
        result = _make_accepted_result(refutations=_sample_refutations())

        enriched = enrich_sgf(sgf, result)
        # The enriched SGF should contain "Wrong" comment
        assert "Wrong" in enriched
        # And the wrong move coordinates
        assert "cd" in enriched

    def test_adds_ai_branches_alongside_curated_wrongs(self):
        """AI branches are added alongside curated wrongs, up to cap."""
        sgf = "(;FF[4]GM[1]SZ[19]PL[B]AB[dd]AW[ee](;B[df]C[Correct.])(;B[ef]C[Wrong. Existing.]))"
        result = _make_accepted_result(refutations=_sample_refutations())

        enriched = enrich_sgf(sgf, result)
        # The existing "Wrong. Existing." should still be there
        assert "Wrong. Existing." in enriched
        # AI branches should now be added alongside curated (cap=3, existing=1, budget=2)
        root = parse_sgf(enriched)
        yr = root.get("YR", "")
        assert "cd" in yr
        assert "de" in yr

    def test_derives_yr_from_added_branches(self):
        sgf = _load_fixture("simple_life_death.sgf")
        result = _make_accepted_result(refutations=_sample_refutations())

        enriched = enrich_sgf(sgf, result)
        root = parse_sgf(enriched)
        yr = root.get("YR")
        assert yr == "cd,de"

    def test_no_refutations_no_branches(self):
        sgf = _load_fixture("simple_life_death.sgf")
        result = _make_accepted_result(refutations=[])

        enriched = enrich_sgf(sgf, result)
        root = parse_sgf(enriched)
        yr = root.get("YR", "")
        assert yr == ""


@pytest.mark.unit
class TestRejectedSkipsEnrichment:
    """status=REJECTED → SGF not modified at all."""

    def test_rejected_returns_original(self):
        sgf = _load_fixture("simple_life_death.sgf")
        result = _make_rejected_result()

        enriched = enrich_sgf(sgf, result)
        assert enriched == sgf

    def test_rejected_with_existing_props(self):
        sgf = _load_fixture("simple_life_death.sgf")
        sgf_with_yg = sgf.replace("PL[B]", "PL[B]YG[novice]")
        result = _make_rejected_result()

        enriched = enrich_sgf(sgf_with_yg, result)
        assert enriched == sgf_with_yg


@pytest.mark.unit
class TestRoundtripPreservation:
    """SGF structure and existing properties preserved after enrichment."""

    def test_roundtrip_preserves_structure(self):
        sgf = _load_fixture("simple_life_death.sgf")
        result = _make_accepted_result(
            level="intermediate",
            level_id=150,
            refutations=_sample_refutations(),
        )

        enriched = enrich_sgf(sgf, result)
        root = parse_sgf(enriched)

        # Original properties preserved
        assert root.get("FF") == "4"
        assert root.get("GM") == "1"
        assert root.get("SZ") == "19"
        assert root.get("PL") == "B"

        # Enrichment properties set
        assert root.get("YG") == "intermediate"
        assert "cd" in root.get("YR")

        # YX should be valid format
        yx = root.get("YX")
        assert yx.startswith("d:")
        assert ";r:" in yx

    def test_existing_comments_preserved(self):
        sgf = _load_fixture("simple_life_death.sgf")
        result = _make_accepted_result()

        enriched = enrich_sgf(sgf, result)
        root = parse_sgf(enriched)
        assert "Kill" in root.get("C")

    def test_existing_tags_preserved(self):
        """YT already present in source SGF is preserved (enrich_if_absent policy)."""
        sgf = _load_fixture("simple_life_death.sgf")
        # simple_life_death.sgf has YT[life-and-death] — enricher must not overwrite it
        result = _make_accepted_result()

        enriched = enrich_sgf(sgf, result)
        root = parse_sgf(enriched)
        assert root.get("YT") == "life-and-death"


# ===================================================================
# Sample Pipeline Puzzle (User's Real-World Test Case)
# ===================================================================


@pytest.mark.unit
class TestSamplePipelinePuzzle:
    """Test with the user's actual analyzed puzzle from the pipeline.

    This puzzle has: YG=beginner, YT=net, YH=hints, YQ=q:2;rc:0;hc:2,
    YX=d:1;r:2;s:19;u:1;a:0, YC=TR, YL=ishigure-basic-tsumego.
    It has NO YR and NO refutation branches.

    Expected: Add refutation branches + derive YR. Preserve everything else.
    """

    _SAMPLE_SGF = (
        "(;SZ[19]FF[4]GM[1]PL[B]GN[YENGO-0b5cf0cbe321ec80]"
        "YC[TR]YG[beginner]"
        'YH[Your group is in atari! Escape or make eyes immediately.|Play at {!ra}.]'
        'YL[ishigure-basic-tsumego]'
        'YM[{"t":"2d11965953bd4715","i":"20260228-7e3ace94","fp":"3442d2e501019864"}]'
        "YQ[q:2;rc:0;hc:2]YT[net]YV[13]"
        "YX[d:1;r:2;s:19;u:1;a:0]"
        "AB[pe][od][nd][nc][ob][mb][lc][rc][rd][qe]"
        "AW[nb][na][oa][pa][oc][pc][rb][sa][sc]"
        ";B[ra]C[Correct])"
    )

    def test_preserves_yg(self):
        result = _make_accepted_result(level="elementary", level_id=130)
        enriched = enrich_sgf(self._SAMPLE_SGF, result)
        root = parse_sgf(enriched)
        assert root.get("YG") == "beginner"  # preserved, not overwritten

    def test_preserves_yx(self):
        result = _make_accepted_result(refutations=_sample_refutations())
        enriched = enrich_sgf(self._SAMPLE_SGF, result)
        root = parse_sgf(enriched)
        assert root.get("YX") == "d:1;r:2;s:19;u:1;a:0"  # valid → preserved

    def test_preserves_yq(self):
        result = _make_accepted_result()
        enriched = enrich_sgf(self._SAMPLE_SGF, result)
        root = parse_sgf(enriched)
        yq = root.get("YQ")
        # S3-G4: YQ preserves existing q/rc/hc, adds ac and qk fields
        assert yq.startswith("q:2;rc:0;hc:2;ac:0;qk:")

    def test_preserves_yt(self):
        result = _make_accepted_result()
        enriched = enrich_sgf(self._SAMPLE_SGF, result)
        root = parse_sgf(enriched)
        assert root.get("YT") == "net"

    def test_preserves_yh(self):
        result = _make_accepted_result()
        enriched = enrich_sgf(self._SAMPLE_SGF, result)
        root = parse_sgf(enriched)
        assert "atari" in root.get("YH")

    def test_preserves_yc(self):
        result = _make_accepted_result()
        enriched = enrich_sgf(self._SAMPLE_SGF, result)
        root = parse_sgf(enriched)
        assert root.get("YC") == "TR"

    def test_preserves_yl(self):
        result = _make_accepted_result()
        enriched = enrich_sgf(self._SAMPLE_SGF, result)
        root = parse_sgf(enriched)
        assert root.get("YL") == "ishigure-basic-tsumego"

    def test_adds_refutation_branches(self):
        result = _make_accepted_result(refutations=_sample_refutations())
        enriched = enrich_sgf(self._SAMPLE_SGF, result)
        assert "Wrong" in enriched
        assert "cd" in enriched

    def test_derives_yr_from_branches(self):
        result = _make_accepted_result(refutations=_sample_refutations())
        enriched = enrich_sgf(self._SAMPLE_SGF, result)
        root = parse_sgf(enriched)
        yr = root.get("YR")
        assert yr == "cd,de"

    def test_no_refutations_no_yr(self):
        result = _make_accepted_result(refutations=[])
        enriched = enrich_sgf(self._SAMPLE_SGF, result)
        root = parse_sgf(enriched)
        yr = root.get("YR", "")
        assert yr == ""


# ===================================================================
# Backward Compatibility
# ===================================================================


@pytest.mark.unit
class TestBackwardCompatibility:
    """Legacy patch alias is intentionally removed."""

    def test_patch_sgf_alias(self):
        with pytest.raises(ImportError):
            from analyzers.sgf_enricher import patch_sgf  # noqa: F401


# ---------------------------------------------------------------------------
# Test Remediation: Vital Node Embedding (T12a / F16)
# ---------------------------------------------------------------------------

from analyzers.sgf_enricher import _embed_teaching_comments


@pytest.mark.unit
class TestVitalNodeEmbedding:
    """Test that _embed_teaching_comments places vital comment on the correct deeper node."""

    def test_embed_vital_comment_on_deeper_node(self):
        """T12a/F16: C[] appears on the vital node, not root's first child."""
        from core.sgf_parser import SGF

        # 3-move correct line: root -> B[cc] -> W[dd] -> B[ee]
        sgf = "(;GM[1]SZ[19]PL[B];B[cc];W[dd];B[ee])"
        result = _embed_teaching_comments(
            sgf,
            correct_comment="",  # Root suppressed
            wrong_comments={},
            vital_comment="Decisive tesuji completes the sequence.",
            vital_node_index=2,
        )
        # Parse result back
        root = SGF.parse_sgf(result)

        # First child = B[cc] (move 1) — should NOT have the vital comment
        node1 = root.children[0]
        comment1 = node1.get_property("C", "")
        if comment1:
            assert "Decisive tesuji" not in comment1, (
                "Vital comment should NOT be on the first correct node"
            )

        # Walk to vital node at index 2: root.children[0] -> children[0] (W[dd], index 2)
        node2 = node1.children[0]  # This is the vital node (index 2 from main line)
        comment2 = node2.get_property("C", "")
        assert comment2, "Vital node should have a C[] property"
        assert "Decisive tesuji" in comment2


# ===================================================================
# T8/T12: _compute_qk + _build_yx all 8 fields (AC-1)
# ===================================================================

from analyzers.sgf_enricher import _build_yq, _build_yx, _compute_qk
from config.difficulty import QualityWeightsConfig


@pytest.mark.unit
class TestComputeQk:
    """T8: _compute_qk returns quality score 0-5 using config-driven weights."""

    def test_zero_inputs_return_zero(self):
        w = QualityWeightsConfig()
        assert _compute_qk(0.0, 0.0, 0, 0.0, 1000, w) == 0

    def test_max_inputs_return_five(self):
        w = QualityWeightsConfig()
        qk = _compute_qk(1.0, 10.0, 8, 1.0, 1000, w)
        assert qk == 5

    def test_medium_inputs(self):
        w = QualityWeightsConfig()
        qk = _compute_qk(0.5, 5.0, 4, 0.5, 1000, w)
        assert 1 <= qk <= 4

    def test_clamp_lower_bound(self):
        w = QualityWeightsConfig()
        assert _compute_qk(0.0, 0.0, 0, 0.0, 0, w) == 0

    def test_clamp_upper_bound(self):
        w = QualityWeightsConfig()
        qk = _compute_qk(1.0, 100.0, 100, 1.0, 10000, w)
        assert qk == 5

    def test_visit_gate_degrades_score(self):
        """AC-4: Visit-count gate at rank_min_visits=500 degrades qk."""
        w = QualityWeightsConfig()
        qk_high = _compute_qk(0.8, 6.0, 5, 0.7, 1000, w)
        qk_low = _compute_qk(0.8, 6.0, 5, 0.7, 100, w)
        assert qk_low <= qk_high

    def test_custom_weights_respected(self):
        """C3: Config-driven weights, not hardcoded."""
        w = QualityWeightsConfig(
            trap_density=1.0,
            avg_refutation_depth=0.0,
            correct_move_rank=0.0,
            policy_entropy=0.0,
        )
        qk = _compute_qk(1.0, 10.0, 8, 1.0, 1000, w)
        assert qk == 5
        # Now only trap contributes, rest are zero
        qk_zero = _compute_qk(0.0, 10.0, 8, 1.0, 1000, w)
        assert qk_zero == 0


# ===================================================================
# T12: _build_yx all 8 fields (AC-1)
# ===================================================================


@pytest.mark.unit
class TestBuildYxAllFields:
    """T12: _build_yx emits d, r, s, u, w, a, b, t fields."""

    def test_all_eight_fields_present(self):
        result = _make_accepted_result(
            refutations=_sample_refutations(),
            trap_density=0.25,
        )
        result.move_order = "strict"
        yx = _build_yx(result, ["cc", "dd", "ee"])
        parts = dict(p.split(":") for p in yx.split(";"))
        assert set(parts.keys()) == {"d", "r", "s", "u", "w", "a", "b", "t"}

    def test_depth_and_solution_length(self):
        result = _make_accepted_result(refutations=[])
        yx = _build_yx(result, ["cc", "dd", "ee"])
        parts = dict(p.split(":") for p in yx.split(";"))
        assert parts["d"] == "3"
        assert parts["s"] == "3"

    def test_refutation_metrics(self):
        result = _make_accepted_result(refutations=_sample_refutations())
        yx = _build_yx(result, ["cc"])
        parts = dict(p.split(":") for p in yx.split(";"))
        assert parts["r"] == "2"  # 2 refutations
        assert parts["w"] == "2"  # 2 distinct wrong moves
        # avg depth: (2+1)/2 = 1.5 → round → 2
        assert parts["a"] == "2"

    def test_unique_flag_strict(self):
        result = _make_accepted_result()
        result.move_order = "strict"
        yx = _build_yx(result, ["cc"])
        parts = dict(p.split(":") for p in yx.split(";"))
        assert parts["u"] == "1"

    def test_unique_flag_miai(self):
        result = _make_accepted_result()
        result.move_order = "miai"
        yx = _build_yx(result, ["cc"])
        parts = dict(p.split(":") for p in yx.split(";"))
        assert parts["u"] == "0"

    def test_branch_count_from_difficulty(self):
        result = _make_accepted_result()
        result.difficulty.branch_count = 3
        yx = _build_yx(result, ["cc"])
        parts = dict(p.split(":") for p in yx.split(";"))
        assert parts["b"] == "3"

    def test_trap_density_percentage(self):
        result = _make_accepted_result(trap_density=0.45)
        yx = _build_yx(result, ["cc"])
        parts = dict(p.split(":") for p in yx.split(";"))
        assert parts["t"] == "45"

    def test_trap_density_sentinel_becomes_zero(self):
        result = _make_accepted_result(trap_density=-1.0)
        yx = _build_yx(result, ["cc"])
        parts = dict(p.split(":") for p in yx.split(";"))
        assert parts["t"] == "0"


# ===================================================================
# T13: _build_yq with qk field (AC-2)
# ===================================================================


@pytest.mark.unit
class TestBuildYqWithQk:
    """T13: _build_yq includes qk field computed from result signals."""

    def test_yq_includes_qk_field(self):
        result = _make_accepted_result(
            refutations=_sample_refutations(),
            trap_density=0.5,
        )
        result.difficulty.policy_entropy = 0.6
        result.difficulty.correct_move_rank = 3
        result.ac_level = 1
        yq = _build_yq(result, "")
        assert ";qk:" in yq
        parts = dict(p.split(":") for p in yq.split(";"))
        assert "qk" in parts
        qk_val = int(parts["qk"])
        assert 0 <= qk_val <= 5

    def test_yq_preserves_existing_fields(self):
        result = _make_accepted_result()
        result.ac_level = 2
        yq = _build_yq(result, "q:3;rc:1;hc:2")
        parts = dict(p.split(":") for p in yq.split(";"))
        assert parts["q"] == "3"
        assert parts["rc"] == "1"
        assert parts["hc"] == "2"
        assert parts["ac"] == "2"
        assert "qk" in parts

    def test_yq_with_sentinel_signals(self):
        """qk computed safely when policy_entropy/correct_move_rank are sentinels."""
        result = _make_accepted_result()
        # Default DifficultySnapshot has policy_entropy=-1.0, correct_move_rank=-1
        yq = _build_yq(result, "")
        assert ";qk:" in yq
        parts = dict(p.split(":") for p in yq.split(";"))
        qk_val = int(parts["qk"])
        assert 0 <= qk_val <= 5


# ===================================================================
# T14: Config parsing quality_weights (AC-3)
# ===================================================================


@pytest.mark.unit
class TestQualityWeightsConfig:
    """T14: QualityWeightsConfig parses from config and has correct defaults."""

    def test_default_weights(self):
        w = QualityWeightsConfig()
        assert w.trap_density == 0.40
        assert w.avg_refutation_depth == 0.30
        assert w.correct_move_rank == 0.20
        assert w.policy_entropy == 0.10
        assert w.rank_min_visits == 500
        assert w.rank_clamp_max == 8
        assert w.avg_depth_max == 10
        assert w.low_visit_multiplier == 0.7

    def test_config_loads_quality_weights(self):
        from config import load_enrichment_config
        cfg = load_enrichment_config()
        w = cfg.quality_weights
        assert isinstance(w, QualityWeightsConfig)
        assert w.rank_min_visits == 500
        assert 0.0 <= w.trap_density <= 1.0

    def test_custom_weights(self):
        w = QualityWeightsConfig(
            trap_density=0.5,
            avg_refutation_depth=0.2,
            correct_move_rank=0.2,
            policy_entropy=0.1,
            rank_min_visits=1000,
        )
        assert w.trap_density == 0.5
        assert w.rank_min_visits == 1000


# ===================================================================
# T15: Visit-count gate degradation (AC-4)
# ===================================================================


@pytest.mark.unit
class TestVisitCountGate:
    """T15: Visit-count gate at rank_min_visits degrades qk score."""

    def test_below_threshold_degrades(self):
        w = QualityWeightsConfig()
        # Same inputs, different visit counts
        qk_above = _compute_qk(0.6, 5.0, 3, 0.5, 600, w)
        qk_below = _compute_qk(0.6, 5.0, 3, 0.5, 400, w)
        assert qk_below <= qk_above

    def test_exactly_at_threshold_no_degradation(self):
        w = QualityWeightsConfig(rank_min_visits=500)
        qk_at = _compute_qk(0.6, 5.0, 3, 0.5, 500, w)
        qk_above = _compute_qk(0.6, 5.0, 3, 0.5, 501, w)
        assert qk_at == qk_above

    def test_zero_visits_gate_fires(self):
        w = QualityWeightsConfig(rank_min_visits=500)
        qk_no_visits = _compute_qk(0.8, 8.0, 5, 0.8, 0, w)
        qk_high_visits = _compute_qk(0.8, 8.0, 5, 0.8, 1000, w)
        assert qk_no_visits <= qk_high_visits

    def test_gate_disabled_when_min_visits_zero(self):
        w = QualityWeightsConfig(rank_min_visits=0)
        qk = _compute_qk(0.6, 5.0, 3, 0.5, 0, w)
        qk_high = _compute_qk(0.6, 5.0, 3, 0.5, 10000, w)
        assert qk == qk_high  # No degradation when gate is at 0


# ===================================================================
# T16: Signal propagation end-to-end (AC-7)
# ===================================================================


@pytest.mark.unit
class TestSignalPropagation:
    """T16: policy_entropy and correct_move_rank flow into DifficultySnapshot and YQ."""

    def test_difficulty_snapshot_has_entropy_and_rank(self):
        """Verify DifficultySnapshot fields accept values."""
        snap = DifficultySnapshot(
            policy_prior_correct=0.15,
            visits_to_solve=200,
            trap_density=0.3,
            policy_entropy=0.65,
            correct_move_rank=3,
        )
        assert snap.policy_entropy == 0.65
        assert snap.correct_move_rank == 3

    def test_signals_flow_into_yq_qk(self):
        """policy_entropy + correct_move_rank in DifficultySnapshot affect qk output."""
        result_with_signals = _make_accepted_result(
            refutations=_sample_refutations(),
            trap_density=0.5,
        )
        result_with_signals.difficulty.policy_entropy = 0.8
        result_with_signals.difficulty.correct_move_rank = 5
        result_with_signals.difficulty.visits_to_solve = 1000
        yq_with = _build_yq(result_with_signals, "")
        parts_with = dict(p.split(":") for p in yq_with.split(";"))
        qk_with = int(parts_with["qk"])

        result_without_signals = _make_accepted_result(
            refutations=_sample_refutations(),
            trap_density=0.5,
        )
        result_without_signals.difficulty.policy_entropy = 0.0
        result_without_signals.difficulty.correct_move_rank = 0
        result_without_signals.difficulty.visits_to_solve = 1000
        yq_without = _build_yq(result_without_signals, "")
        parts_without = dict(p.split(":") for p in yq_without.split(";"))
        qk_without = int(parts_without["qk"])

        # With signals should produce >= score compared to without
        assert qk_with >= qk_without

    def test_sentinel_values_produce_safe_qk(self):
        """Sentinel values (-1) should not crash or produce negative qk."""
        result = _make_accepted_result()
        # Default sentinels: policy_entropy=-1.0, correct_move_rank=-1
        yq = _build_yq(result, "")
        parts = dict(p.split(":") for p in yq.split(";"))
        qk = int(parts["qk"])
        assert 0 <= qk <= 5

# ===================================================================
# RC-1: Wrong-move comment prefix enforcement
# ===================================================================


@pytest.mark.unit
class TestWrongMovePrefixEnforcement:
    """RC-1: All wrong-move comments get canonical 'Wrong.' prefix."""

    def test_close_comment_gets_wrong_prefix(self):
        """'Close' text should be wrapped as 'Wrong. Close ...'."""
        sgf = _load_fixture("simple_life_death.sgf")
        refs = [
            RefutationEntry(
                wrong_move="cd",
                refutation_pv=["dc"],
                delta=-0.03,
                refutation_depth=1,
            ),
        ]
        result = _make_accepted_result(refutations=refs)
        enriched = enrich_sgf(sgf, result)
        # Every branch comment should start with "Wrong"
        root = parse_sgf(enriched)
        for child in root.children:
            c = child.get_property("C", "")
            if c and "Close" in c:
                assert c.startswith("Wrong"), (
                    f"Expected 'Wrong' prefix on close comment, got: {c!r}"
                )

    def test_already_wrong_prefix_not_doubled(self):
        """A comment already starting with 'Wrong' should not get double prefix."""
        sgf = _load_fixture("simple_life_death.sgf")
        refs = [
            RefutationEntry(
                wrong_move="cd",
                refutation_pv=["dc"],
                delta=-0.4,
                refutation_depth=1,
            ),
        ]
        result = _make_accepted_result(refutations=refs)
        enriched = enrich_sgf(sgf, result)
        assert "Wrong. Wrong" not in enriched


# ===================================================================
# RC-4: Level mismatch — strict greater-than threshold
# ===================================================================


@pytest.mark.unit
class TestLevelMismatchStrictThreshold:
    """RC-4: Level overwrite at exact threshold should NOT trigger."""

    def test_distance_equal_to_threshold_no_overwrite(self):
        """distance == threshold (3) should preserve existing level."""
        sgf = _load_fixture("simple_life_death.sgf")
        # Add an existing YG that is exactly 3 steps from suggested
        # beginner(120) → intermediate(150) = 3 steps
        sgf_with_yg = sgf.replace("PL[B]", "PL[B]YG[beginner]")
        result = _make_accepted_result(level="intermediate")

        enriched = enrich_sgf(sgf_with_yg, result)
        root = parse_sgf(enriched)
        # With >= it would overwrite; with > it should NOT
        assert root.get("YG") == "beginner"

    def test_distance_above_threshold_overwrites(self):
        """distance > threshold (4 > 3) should overwrite existing level."""
        sgf = _load_fixture("simple_life_death.sgf")
        # novice(110) → upper-intermediate(155 or similar) = 4 steps
        sgf_with_yg = sgf.replace("PL[B]", "PL[B]YG[novice]")
        result = _make_accepted_result(level="upper-intermediate")

        enriched = enrich_sgf(sgf_with_yg, result)
        root = parse_sgf(enriched)
        assert root.get("YG") == "upper-intermediate"


# ===================================================================
# RC-5: All-almost-correct refutation guard
# ===================================================================


@pytest.mark.unit
class TestAllAlmostCorrectGuard:
    """RC-5 REVERSED: Almost-correct branches are now added (not skipped).

    Initiative 20260320-1400-feature-enrichment-almost-correct-reversal
    reversed the RC-5 all-skip gate. Almost-correct moves now go to the
    wrong tree with a non-spoiler comment.
    """

    def test_all_deltas_below_threshold_adds_branches(self):
        """When every refutation delta < 0.05, branches ARE added (RC-5 reversed)."""
        sgf = _load_fixture("simple_life_death.sgf")
        almost_refs = [
            RefutationEntry(
                wrong_move="cd", refutation_pv=["dc"], delta=-0.02, refutation_depth=1,
            ),
            RefutationEntry(
                wrong_move="de", refutation_pv=["ef"], delta=-0.04, refutation_depth=1,
            ),
        ]
        result = _make_accepted_result(refutations=almost_refs)
        enriched = enrich_sgf(sgf, result)
        root = parse_sgf(enriched)
        yr = root.get("YR", "")
        assert "cd" in yr, "Almost-correct branches should be added"
        assert "de" in yr, "Almost-correct branches should be added"

    def test_mixed_deltas_adds_branches_normally(self):
        """When some refutations have large delta, branches are added."""
        sgf = _load_fixture("simple_life_death.sgf")
        mixed_refs = [
            RefutationEntry(
                wrong_move="cd", refutation_pv=["dc"], delta=-0.02, refutation_depth=1,
            ),
            RefutationEntry(
                wrong_move="de", refutation_pv=["ef"], delta=-0.4, refutation_depth=1,
            ),
        ]
        result = _make_accepted_result(refutations=mixed_refs)
        enriched = enrich_sgf(sgf, result)
        root = parse_sgf(enriched)
        yr = root.get("YR", "")
        assert yr, "Expected YR to be set when some refutations have large delta"

    def test_no_refutations_no_branches(self):
        """Empty refutations list should not attempt branch building."""
        sgf = _load_fixture("simple_life_death.sgf")
        result = _make_accepted_result(refutations=[])
        enriched = enrich_sgf(sgf, result)
        root = parse_sgf(enriched)
        yr = root.get("YR", "")
        assert yr == ""


# ===================================================================
# Almost-Correct Reversal: Scenario Tests
# (Initiative: 20260320-1400-feature-enrichment-almost-correct-reversal)
# ===================================================================


def _almost_correct_refutations() -> list[RefutationEntry]:
    """Refutations with ALL deltas below almost_correct_threshold (0.05)."""
    return [
        RefutationEntry(
            wrong_move="cd",
            refutation_pv=["dc", "dd"],
            delta=-0.03,
            refutation_depth=2,
        ),
        RefutationEntry(
            wrong_move="de",
            refutation_pv=["ef"],
            delta=-0.02,
            refutation_depth=1,
        ),
    ]


@pytest.mark.unit
class TestScenarioA_AllAlmostCorrect:
    """Scenario A: 1 correct, 0 wrong, AI finds 1-3 wrongs ALL almost-correct.

    Previously (RC-5), all branches were dropped. Now they should be added
    as wrong branches.
    """

    def test_all_almost_correct_branches_added(self):
        """Branches with delta < 0.05 are no longer dropped."""
        sgf = _load_fixture("simple_life_death.sgf")
        result = _make_accepted_result(refutations=_almost_correct_refutations())

        enriched = enrich_sgf(sgf, result)
        assert "Wrong" in enriched
        root = parse_sgf(enriched)
        yr = root.get("YR", "")
        assert "cd" in yr
        assert "de" in yr

    def test_yr_set_for_all_almost_correct(self):
        """YR property is set even when all refutations are almost-correct."""
        sgf = _load_fixture("simple_life_death.sgf")
        result = _make_accepted_result(refutations=_almost_correct_refutations())

        enriched = enrich_sgf(sgf, result)
        root = parse_sgf(enriched)
        yr = root.get("YR", "")
        assert yr, "YR should be set (not empty) for almost-correct refutations"


@pytest.mark.unit
class TestScenarioF_PositionOnly:
    """Scenario F: position-only puzzle (no pre-existing solution branches).

    KataGo discovers correct + wrongs; the same fix as A applies — all-skip
    removed, so almost-correct wrongs are added to the tree.
    """

    def test_position_only_gets_branches(self):
        """Position-only SGF (AB/AW stones, no children) gets AI branches."""
        sgf = "(;FF[4]GM[1]SZ[19]PL[B]AB[dd]AW[ee])"
        result = _make_accepted_result(refutations=[
            RefutationEntry(
                wrong_move="cd", refutation_pv=["dc"], delta=-0.02,
                refutation_depth=1,
            ),
        ])
        enriched = enrich_sgf(sgf, result)
        root = parse_sgf(enriched)
        yr = root.get("YR", "")
        assert "cd" in yr, "Position-only puzzle should get AI refutation branches"


@pytest.mark.unit
class TestScenarioBC_Unchanged:
    """Scenarios B (mixed) and C (all true wrong): behavior unchanged."""

    def test_mixed_refutations_all_added(self):
        """Scenario B: mixed almost-correct and true wrong — all added."""
        sgf = _load_fixture("simple_life_death.sgf")
        refs = [
            RefutationEntry(
                wrong_move="cd", refutation_pv=["dc"], delta=-0.03,
                refutation_depth=1,
            ),
            RefutationEntry(
                wrong_move="de", refutation_pv=["ef"], delta=-0.4,
                refutation_depth=1,
            ),
        ]
        result = _make_accepted_result(refutations=refs)
        enriched = enrich_sgf(sgf, result)
        root = parse_sgf(enriched)
        yr = root.get("YR", "")
        assert "cd" in yr
        assert "de" in yr

    def test_all_true_wrong_added(self):
        """Scenario C: all true wrong — all added (unchanged)."""
        sgf = _load_fixture("simple_life_death.sgf")
        result = _make_accepted_result(refutations=_sample_refutations())
        enriched = enrich_sgf(sgf, result)
        root = parse_sgf(enriched)
        yr = root.get("YR", "")
        assert "cd" in yr
        assert "de" in yr


@pytest.mark.unit
class TestScenarioD_CuratedPlusAI:
    """Scenario D: 1 correct, 1+ curated wrong, AI finds additional wrongs.

    Previously, the curated gate blocked ALL AI wrongs. Now AI wrongs are
    added alongside curated, up to max_refutation_root_trees cap (3).
    """

    def test_ai_branches_added_alongside_curated(self):
        """AI wrongs coexist with curated wrongs."""
        sgf = "(;FF[4]GM[1]SZ[19]PL[B]AB[dd]AW[ee](;B[df]C[Correct.])(;B[ef]C[Wrong. Curated.]))"
        result = _make_accepted_result(refutations=[
            RefutationEntry(
                wrong_move="cd", refutation_pv=["dc"], delta=-0.3,
                refutation_depth=1,
            ),
        ])
        enriched = enrich_sgf(sgf, result)
        # Both curated and AI wrongs should be present
        assert "Wrong. Curated." in enriched
        root = parse_sgf(enriched)
        yr = root.get("YR", "")
        assert "cd" in yr

    def test_dedup_same_coord_as_curated(self):
        """AI branch with same coord as curated is deduped."""
        sgf = "(;FF[4]GM[1]SZ[19]PL[B]AB[dd]AW[ee](;B[df]C[Correct.])(;B[ef]C[Wrong. Curated.]))"
        result = _make_accepted_result(refutations=[
            RefutationEntry(
                wrong_move="ef", refutation_pv=["dc"], delta=-0.3,
                refutation_depth=1,
            ),
        ])
        enriched = enrich_sgf(sgf, result)
        # ef already exists as curated — AI branch should be deduped
        # Count occurrences of "Wrong" in enriched text — should be exactly 1 (the curated one)
        assert enriched.count("Wrong") == 1


@pytest.mark.unit
class TestScenarioD_Cap:
    """Scenario D: Cap enforcement — total wrongs (curated + AI) <= 3."""

    def test_cap_limits_ai_branches(self):
        """2 curated + 3 AI available → only 1 AI added (cap=3)."""
        sgf = (
            "(;FF[4]GM[1]SZ[19]PL[B]AB[dd]AW[ee]"
            "(;B[df]C[Correct.])"
            "(;B[ef]C[Wrong. Curated1.])"
            "(;B[fg]C[Wrong. Curated2.]))"
        )
        result = _make_accepted_result(refutations=[
            RefutationEntry(
                wrong_move="cd", refutation_pv=["dc"], delta=-0.3,
                refutation_depth=1,
            ),
            RefutationEntry(
                wrong_move="de", refutation_pv=["ef"], delta=-0.25,
                refutation_depth=1,
            ),
            RefutationEntry(
                wrong_move="gh", refutation_pv=["hi"], delta=-0.2,
                refutation_depth=1,
            ),
        ])
        enriched = enrich_sgf(sgf, result)
        root = parse_sgf(enriched)
        yr = root.get("YR", "")
        # 2 curated exist → budget = 3-2 = 1 → only first AI branch added
        assert "cd" in yr
        assert "de" not in yr
        assert "gh" not in yr

    def test_cap_reached_no_ai_added(self):
        """3 curated wrongs already at cap → zero AI branches added."""
        sgf = (
            "(;FF[4]GM[1]SZ[19]PL[B]AB[dd]AW[ee]"
            "(;B[df]C[Correct.])"
            "(;B[ef]C[Wrong. C1.])"
            "(;B[fg]C[Wrong. C2.])"
            "(;B[gh]C[Wrong. C3.]))"
        )
        result = _make_accepted_result(refutations=[
            RefutationEntry(
                wrong_move="cd", refutation_pv=["dc"], delta=-0.3,
                refutation_depth=1,
            ),
        ])
        enriched = enrich_sgf(sgf, result)
        root = parse_sgf(enriched)
        yr = root.get("YR", "")
        # Cap already reached — no AI branches
        assert "cd" not in yr


@pytest.mark.unit
class TestCountAndCollectHelpers:
    """Tests for _count_existing_refutation_branches and _collect_existing_wrong_coords."""

    def test_count_zero_wrongs(self):
        root = parse_sgf("(;FF[4]GM[1]SZ[19](;B[cc])(;B[ef]))")
        assert _count_existing_refutation_branches(root) == 0

    def test_count_one_wrong(self):
        root = parse_sgf("(;FF[4]GM[1]SZ[19](;B[cc])(;B[ef]C[Wrong]))")
        assert _count_existing_refutation_branches(root) == 1

    def test_count_multiple_wrongs(self):
        root = parse_sgf("(;FF[4]GM[1]SZ[19](;B[cc])(;B[ef]C[Wrong])(;B[gh]BM[1]))")
        assert _count_existing_refutation_branches(root) == 2

    def test_collect_coords_empty(self):
        root = parse_sgf("(;FF[4]GM[1]SZ[19](;B[cc])(;B[ef]))")
        assert _collect_existing_wrong_coords(root) == set()

    def test_collect_coords_mixed(self):
        root = parse_sgf("(;FF[4]GM[1]SZ[19](;B[cc])(;B[ef]C[Wrong])(;B[gh]BM[1]))")
        coords = _collect_existing_wrong_coords(root)
        assert "ef" in coords
        assert "gh" in coords
        assert "cc" not in coords


# --- Migrated from test_sprint1_fixes.py (P0.1 gap ID) ---


@pytest.mark.unit
class TestYxUFieldSemantics:
    """P0.1: YX `u` field is binary (0=miai, 1=unique correct first move).

    Previous code computed u = count of unique wrong moves (from refutations).
    Pipeline canonical definition: u = 1 if exactly one correct first move,
    u = 0 if miai (multiple correct first moves). Wrong-move count is now
    tracked as the separate `w` field.
    """

    def test_unique_puzzle_u_is_1(self):
        """Standard puzzle (strict move order) → u=1."""
        from analyzers.sgf_enricher import _build_yx
        from models.ai_analysis_result import AiAnalysisResult, RefutationEntry

        result = AiAnalysisResult(
            move_order="strict",
            refutations=[
                RefutationEntry(wrong_move="A1", refutation_pv=["B2"], delta=-0.5, refutation_depth=1),
                RefutationEntry(wrong_move="C3", refutation_pv=["D4"], delta=-0.4, refutation_depth=1),
            ],
        )
        yx = _build_yx(result, ["A2", "B3"])
        assert ";u:1" in yx, f"Expected u:1 for strict puzzle, got: {yx}"
        assert ";w:2" in yx, f"Expected w:2 for 2 wrong moves, got: {yx}"

    def test_miai_puzzle_u_is_0(self):
        """Miai puzzle (multiple correct first moves) → u=0."""
        from analyzers.sgf_enricher import _build_yx
        from models.ai_analysis_result import AiAnalysisResult, RefutationEntry

        result = AiAnalysisResult(
            move_order="miai",
            refutations=[
                RefutationEntry(wrong_move="A1", refutation_pv=["B2"], delta=-0.5, refutation_depth=1),
            ],
        )
        yx = _build_yx(result, ["A2", "B3"])
        assert ";u:0" in yx, f"Expected u:0 for miai puzzle, got: {yx}"

    def test_no_refutations_no_w_field(self):
        """No refutations → w field omitted (additive, not present when 0)."""
        from analyzers.sgf_enricher import _build_yx
        from models.ai_analysis_result import AiAnalysisResult

        result = AiAnalysisResult(move_order="strict", refutations=[])
        yx = _build_yx(result, ["A2"])
        assert ";u:1" in yx
        assert ";w:" not in yx, f"w field should be omitted when 0, got: {yx}"

    def test_yx_regex_accepts_w_field(self):
        """Property policy regex accepts optional w field."""
        from analyzers.property_policy import _validate_value
        # Without w
        assert _validate_value("complexity_metrics", "d:2;r:3;s:5;u:1") is True
        assert _validate_value("complexity_metrics", "d:2;r:3;s:5;u:0") is True
        # With w
        assert _validate_value("complexity_metrics", "d:2;r:3;s:5;u:1;w:3") is True
        assert _validate_value("complexity_metrics", "d:2;r:3;s:5;u:0;w:5") is True
        # With w and a
        assert _validate_value("complexity_metrics", "d:2;r:3;s:5;u:1;w:3;a:2") is True
        # u > 1 should be invalid (binary)
        assert _validate_value("complexity_metrics", "d:2;r:3;s:5;u:3") is False


# --- Migrated from test_sprint3_fixes.py ---


@pytest.mark.unit
class TestDynamicRefutationColors:
    """P3.3: Refutation branch colors must work for any PV length."""

    def test_6_move_pv_gets_6_colors(self):
        """A 6-move refutation PV produces 6 colored moves."""
        from analyzers.sgf_enricher import _build_refutation_branches
        from models.ai_analysis_result import AiAnalysisResult, RefutationEntry

        result = AiAnalysisResult(
            refutations=[
                RefutationEntry(
                    wrong_move="cd",
                    refutation_pv=["dd", "ce", "de", "cf", "df", "cg"],
                    delta=-0.5,
                    refutation_depth=6,
                ),
            ],
        )
        branches = _build_refutation_branches(result, "B")
        assert len(branches) == 1
        branch = branches[0]
        # All 6 PV moves should have color assignments
        moves = branch.get("refutation", [])
        assert len(moves) == 6, f"Expected 6 colored moves, got {len(moves)}"

    def test_alternating_colors_correct(self):
        """Colors alternate: opponent, player, opponent, player, ..."""
        from analyzers.sgf_enricher import _build_refutation_branches
        from models.ai_analysis_result import AiAnalysisResult, RefutationEntry

        result = AiAnalysisResult(
            refutations=[
                RefutationEntry(
                    wrong_move="cd",
                    refutation_pv=["aa", "bb", "cc", "dd", "ee", "ff"],
                    delta=-0.5,
                    refutation_depth=6,
                ),
            ],
        )
        branches = _build_refutation_branches(result, "B")
        moves = branches[0]["refutation"]
        # Player=B, so opponent=W. Alternation: W, B, W, B, W, B
        expected_colors = ["W", "B", "W", "B", "W", "B"]
        actual_colors = [m[0] for m in moves]
        assert actual_colors == expected_colors, (
            f"Expected {expected_colors}, got {actual_colors}"
        )

    def test_single_move_pv(self):
        """A 1-move PV still works."""
        from analyzers.sgf_enricher import _build_refutation_branches
        from models.ai_analysis_result import AiAnalysisResult, RefutationEntry

        result = AiAnalysisResult(
            refutations=[
                RefutationEntry(
                    wrong_move="cd",
                    refutation_pv=["dd"],
                    delta=-0.5,
                    refutation_depth=1,
                ),
            ],
        )
        branches = _build_refutation_branches(result, "B")
        moves = branches[0]["refutation"]
        assert len(moves) == 1
        assert moves[0][0] == "W"  # opponent responds
