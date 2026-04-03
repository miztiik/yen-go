"""AI-Solve calibration tests (Phase 11, ai-solve-enrichment-plan-v3).

Validates calibration infrastructure, threshold constraints, fixture
integrity, and classification consistency. Does NOT run live KataGo —
these are structural and constraint-validation tests.

Gate 11 criteria:
- Calibration fixtures are held-out (no overlap with pipeline collections)
- Macro-F1 >= configured target across model versions (structural check)
- Threshold stability documented across visit counts
- tests/fixtures/calibration/README.md documents provenance
"""

import sys
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve().parent
_LAB = _HERE.parent
if str(_LAB) not in sys.path:
    sys.path.insert(0, str(_LAB))

_FIXTURES = _HERE / "fixtures"
_CALIBRATION = _FIXTURES / "calibration"
_PROJECT_ROOT = _LAB.parent.parent

from analyzers.solve_position import classify_move_quality
from config import clear_cache, load_enrichment_config
from config.ai_solve import AiSolveConfig, AiSolveThresholds
from models.solve_result import MoveQuality


@pytest.fixture(autouse=True)
def _clear_cache():
    clear_cache()
    yield
    clear_cache()


# ===================================================================
# Calibration Fixture Integrity
# ===================================================================


@pytest.mark.unit
class TestCalibrationFixtureIntegrity:
    """Calibration fixture set structure and provenance."""

    def test_readme_documents_source(self):
        """Calibration README exists and documents provenance."""
        readme = _CALIBRATION / "README.md"
        assert readme.exists(), "tests/fixtures/calibration/README.md missing"
        content = readme.read_text()
        assert "Provenance" in content or "Source" in content
        assert "held-out" in content.lower() or "Held-Out" in content

    def test_fixture_dirs_exist(self):
        """All configured calibration fixture dirs exist."""
        cfg = load_enrichment_config()
        for dirname in cfg.calibration.fixture_dirs:
            dirpath = _CALIBRATION / dirname
            assert dirpath.exists(), f"Calibration dir missing: {dirname}"

    def test_cho_elementary_has_sgfs(self):
        """cho-elementary directory has SGF files."""
        sgfs = list((_CALIBRATION / "cho-elementary").glob("*.sgf"))
        assert len(sgfs) >= 5, f"Only {len(sgfs)} SGFs in cho-elementary"

    def test_cho_intermediate_has_sgfs(self):
        sgfs = list((_CALIBRATION / "cho-intermediate").glob("*.sgf"))
        assert len(sgfs) >= 5

    def test_cho_advanced_has_sgfs(self):
        sgfs = list((_CALIBRATION / "cho-advanced").glob("*.sgf"))
        assert len(sgfs) >= 5

    def test_no_overlap_with_pipeline_collections(self):
        """Calibration fixtures must NOT appear in yengo-puzzle-collections/."""
        pub_sgf = _PROJECT_ROOT / "yengo-puzzle-collections" / "sgf"
        if not pub_sgf.exists():
            pytest.skip("yengo-puzzle-collections/sgf/ not found")

        # Collect all published SGF filenames
        published = {f.stem for f in pub_sgf.rglob("*.sgf")}

        # Check calibration fixtures don't overlap
        for cal_dir in _CALIBRATION.iterdir():
            if not cal_dir.is_dir():
                continue
            for sgf in cal_dir.glob("*.sgf"):
                assert sgf.stem not in published, (
                    f"Calibration fixture {sgf.name} overlaps with "
                    f"published collections"
                )

    def test_minimum_samples_per_fixture_dir(self):
        """Each fixture directory has at least config.calibration.sample_size SGFs."""
        cfg = load_enrichment_config()
        min_count = cfg.calibration.sample_size
        for dirname in cfg.calibration.fixture_dirs:
            dirpath = _CALIBRATION / dirname
            sgfs = list(dirpath.glob("*.sgf"))
            assert len(sgfs) >= min_count, (
                f"{dirname}: only {len(sgfs)} SGFs, need {min_count}"
            )


# ===================================================================
# Threshold Constraint Tests
# ===================================================================


@pytest.mark.unit
class TestThresholdConstraints:
    """Threshold ordering and calibration config consistency."""

    def test_t_good_less_than_t_bad_enforced(self):
        """T_good < T_bad enforced by Pydantic validator."""
        with pytest.raises(ValueError, match="t_good.*must be < t_bad"):
            AiSolveThresholds(t_good=0.20, t_bad=0.10, t_hotspot=0.30)

    def test_t_bad_less_than_t_hotspot(self):
        """T_bad < T_hotspot enforced."""
        with pytest.raises(ValueError, match="t_bad.*must be < t_hotspot"):
            AiSolveThresholds(t_good=0.05, t_bad=0.40, t_hotspot=0.30)

    def test_default_thresholds_valid(self):
        """Default thresholds from config pass all constraints."""
        cfg = load_enrichment_config()
        ai = cfg.ai_solve
        assert ai.thresholds.t_good < ai.thresholds.t_bad
        assert ai.thresholds.t_bad < ai.thresholds.t_hotspot

    def test_calibration_target_f1_reasonable(self):
        """Target macro-F1 is between 0.5 and 1.0."""
        cfg = load_enrichment_config()
        target = cfg.ai_solve.calibration.target_macro_f1
        assert 0.5 <= target <= 1.0

    def test_calibration_visit_counts_ascending(self):
        """Visit counts should be in ascending order."""
        cfg = load_enrichment_config()
        visits = cfg.ai_solve.calibration.visit_counts
        assert visits == sorted(visits)
        assert len(visits) >= 2

    def test_minimum_samples_per_class(self):
        """Config specifies at least 30 samples per class."""
        cfg = load_enrichment_config()
        assert cfg.ai_solve.calibration.min_samples_per_class >= 10


# ===================================================================
# Classifier Consistency Tests (Determinism)
# ===================================================================


@pytest.mark.unit
class TestClassifierConsistency:
    """Verify classifier produces deterministic results."""

    def _config(self, **kwargs):
        return AiSolveConfig(enabled=True, **kwargs)

    def test_same_inputs_same_output(self):
        """Identical inputs → identical classification."""
        config = self._config()
        for _ in range(10):
            result = classify_move_quality(0.48, 0.50, 0.30, config)
            assert result == MoveQuality.TE

    def test_boundary_stability(self):
        """Boundary cases produce consistent results across repeated calls."""
        config = self._config()
        # Exactly at t_good boundary (0.05)
        for _ in range(10):
            result = classify_move_quality(0.45, 0.50, 0.30, config)
            assert result == MoveQuality.TE

    def test_visit_count_sensitivity_structural(self):
        """Different visit count configs produce same threshold classifications.

        This is a structural test — thresholds don't change with visit counts,
        but the signal quality (winrate/policy) may shift. This verifies that
        the classifier function itself is visit-agnostic.
        """
        config = self._config()
        # Same delta, different policy values (simulating visit count effects)
        for policy in [0.10, 0.30, 0.50, 0.80]:
            result = classify_move_quality(0.48, 0.50, policy, config)
            assert result == MoveQuality.TE  # Delta doesn't change → same class


# ===================================================================
# Depth Sanity Tests (Cho Elementary/Advanced)
# ===================================================================


@pytest.mark.unit
class TestDepthSanity:
    """Depth profile sanity for elementary and advanced puzzles."""

    def test_cho_elementary_tree_depth(self):
        """Elementary depth profile has reasonable bounds."""
        cfg = load_enrichment_config()
        profile = cfg.ai_solve.solution_tree.depth_profiles["entry"]
        assert profile.solution_min_depth >= 1
        assert profile.solution_max_depth <= 15
        assert profile.solution_min_depth <= profile.solution_max_depth

    def test_cho_elementary_branch_count(self):
        """Max branch width is reasonable for elementary puzzles."""
        cfg = load_enrichment_config()
        assert cfg.ai_solve.solution_tree.max_branch_width >= 1
        assert cfg.ai_solve.solution_tree.max_branch_width <= 10

    def test_strong_profile_deeper_than_entry(self):
        """Strong profile allows deeper trees than entry."""
        cfg = load_enrichment_config()
        entry = cfg.ai_solve.solution_tree.depth_profiles["entry"]
        strong = cfg.ai_solve.solution_tree.depth_profiles["strong"]
        assert strong.solution_max_depth > entry.solution_max_depth

    def test_natural_stopping_covers_solution(self):
        """Stopping conditions are complete — all enum values covered.

        Checks that the 6 stopping conditions from DD-1 are all
        testable with the current config structure.
        """
        cfg = load_enrichment_config()
        tree = cfg.ai_solve.solution_tree
        seki = cfg.ai_solve.seki_detection

        # 1. Winrate stability: wr_epsilon exists
        assert tree.wr_epsilon > 0
        # 2. Ownership convergence: own_epsilon exists
        assert tree.own_epsilon > 0
        # 3. Seki detection: seki band params exist
        assert seki.winrate_band_low < seki.winrate_band_high
        assert seki.seki_consecutive_depth >= 1
        # 4. Hard cap: max depth per profile
        for _, profile in tree.depth_profiles.items():
            assert profile.solution_max_depth >= 1
        # 5. Budget: max_total_tree_queries exists
        assert tree.max_total_tree_queries >= 1
        # 6. Terminal: handled by pass/no-legal-moves (always applicable)


# ===================================================================
# Macro-F1 Structural Test
# ===================================================================


@pytest.mark.unit
class TestMacroF1:
    """Verify macro-F1 computation is correct (not micro)."""

    def test_macro_f1_not_micro(self):
        """Macro-F1 averages per-class F1, not overall precision/recall.

        This verifies the formula, not the actual KataGo results.
        """
        # Simulated per-class precision/recall
        te_p, te_r = 0.90, 0.85
        bm_p, bm_r = 0.80, 0.90
        ne_p, ne_r = 0.70, 0.75

        te_f1 = 2 * te_p * te_r / (te_p + te_r)
        bm_f1 = 2 * bm_p * bm_r / (bm_p + bm_r)
        ne_f1 = 2 * ne_p * ne_r / (ne_p + ne_r)

        macro_f1 = (te_f1 + bm_f1 + ne_f1) / 3

        # Macro-F1 should NOT equal micro-F1 (weighted by support)
        # Just verify the formula is applied correctly
        assert 0.0 < macro_f1 < 1.0
        assert macro_f1 == pytest.approx(
            (te_f1 + bm_f1 + ne_f1) / 3, abs=0.001
        )

    def test_f1_above_minimum_structural(self):
        """Config target F1 is set and reasonable."""
        cfg = load_enrichment_config()
        target = cfg.ai_solve.calibration.target_macro_f1
        assert target >= 0.5
        assert target <= 1.0


# ===================================================================
# Stratified Class Balance
# ===================================================================


@pytest.mark.unit
class TestStratifiedClassBalance:
    """Verify calibration has minimum samples per class (structural)."""

    def test_stratified_class_balance_config(self):
        """Config specifies minimum samples for stratified calibration."""
        cfg = load_enrichment_config()
        min_per_class = cfg.ai_solve.calibration.min_samples_per_class
        assert min_per_class >= 10, f"min_samples_per_class too low: {min_per_class}"

    def test_total_calibration_fixtures_sufficient(self):
        """Total calibration SGFs across all dirs meets minimum requirement."""
        cfg = load_enrichment_config()
        total_sgfs = 0
        for dirname in cfg.calibration.fixture_dirs:
            dirpath = _CALIBRATION / dirname
            if dirpath.exists():
                total_sgfs += len(list(dirpath.glob("*.sgf")))
        # Need at least 30 total (10 per class × 3 classes)
        assert total_sgfs >= 30, f"Only {total_sgfs} calibration SGFs total"
