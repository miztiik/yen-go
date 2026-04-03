"""Tests for specific config values, thresholds, defaults, and behavioral tests using config.

Consolidated from:
- test_enrichment_config.py (TestAllThresholdsPresent, TestLevelIdsMatchSourceOfTruth,
                             TestOwnershipThresholdsByRegion, TestWinrateRescueAutoAccept,
                             TestConfidenceReason, TestRankBandFlags, TestDifficultyEstimateUsesConfig)
- test_deep_enrich_config.py (TestDeepEnrichConfig, TestDeepEnrichVisitsWiring,
                              TestGetEffectiveMaxVisitsWithModeOverride)
- test_tsumego_config.py (TestTsumegoSettings, TestConfigMatchesExisting)
- test_ai_solve_config.py (TestAiSolveThresholdDefaults, TestDepthProfiles,
                           TestLevelCategoryMapping, TestRootAllocationCaps, TestAiSolveChangelogEntry)
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from config import (
    clear_cache,
    load_enrichment_config,
)
from config.analysis import DeepEnrichConfig
from config.helpers import get_effective_max_visits

# Ensure tools/puzzle-enrichment-lab is importable
_HERE = Path(__file__).resolve().parent
_LAB = _HERE.parent
# Project root (yen-go/)
_PROJECT_ROOT = _LAB.parent.parent

# Source of truth paths
ENRICHMENT_CONFIG_PATH = _PROJECT_ROOT / "config" / "katago-enrichment.json"
PUZZLE_LEVELS_PATH = _PROJECT_ROOT / "config" / "puzzle-levels.json"

# KataGo tsumego config path
_CFG_PATH = _LAB / "katago" / "tsumego_analysis.cfg"


def _parse_cfg(path: Path) -> dict[str, str]:
    """Parse a KataGo .cfg file into a key=value dict (ignoring comments)."""
    result: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" in stripped:
            key, _, value = stripped.partition("=")
            key = key.strip()
            value = value.strip()
            # Strip inline comments
            if "#" in value:
                value = value[: value.index("#")].strip()
            result[key] = value
    return result


@pytest.fixture(autouse=True)
def _clear_caches():
    """Clear config cache before each test to avoid stale state."""
    clear_cache()
    yield
    clear_cache()


# ---------------------------------------------------------------------------
# From test_enrichment_config.py
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestAllThresholdsPresent:
    """Verify all required threshold sections exist in config."""

    @pytest.fixture(autouse=True)
    def _load_config(self):
        from config import load_enrichment_config
        self.cfg = load_enrichment_config()

    def test_ownership_thresholds_present(self):
        ot = self.cfg.ownership_thresholds
        assert ot.alive == pytest.approx(0.7, abs=0.01)
        assert ot.dead == pytest.approx(-0.7, abs=0.01)
        assert ot.seki_low == pytest.approx(-0.3, abs=0.01)
        assert ot.seki_high == pytest.approx(0.3, abs=0.01)

    def test_difficulty_weights_present(self):
        w = self.cfg.difficulty.weights
        assert w.policy_rank > 0
        assert w.visits_to_solve > 0
        assert w.trap_density > 0
        assert w.structural > 0
        assert w.complexity > 0
        # Weights should sum to 100
        total = w.policy_rank + w.visits_to_solve + w.trap_density + w.structural + w.complexity
        assert total == pytest.approx(100.0)
        # G11/T17: PUCT-coupled signals (policy+visits) < 40%, structural >= 35%
        puct_weight = w.policy_rank + w.visits_to_solve
        assert puct_weight < 40.0, f"PUCT-coupled weight {puct_weight} >= 40%"
        assert w.structural >= 35.0, f"Structural weight {w.structural} < 35%"

    def test_refutation_escalation_present(self):
        esc = self.cfg.refutation_escalation
        assert esc.enabled is True
        assert esc.escalation_visits > self.cfg.refutations.refutation_visits
        assert esc.escalation_delta_threshold < self.cfg.refutations.delta_threshold
        # escalation_candidate_min_policy >= 0 (can be 0.0 for strong models)
        assert esc.escalation_candidate_min_policy >= 0.0
        assert esc.min_refutations_required >= 1
        assert 1 <= esc.max_escalation_attempts <= 5

    def test_sparse_position_config_present(self):
        sp = self.cfg.sparse_position
        assert 0.0 < sp.density_threshold < 0.5
        assert sp.min_board_size >= 9
        assert sp.action == "escalate_to_referee"

    def test_escalation_levels_present(self):
        levels = self.cfg.escalation.levels
        assert len(levels) >= 2
        # Visits should be monotonically increasing
        visits = [lv.visits for lv in levels]
        assert visits == sorted(visits)

    def test_refutation_thresholds_present(self):
        ref = self.cfg.refutations
        assert ref.candidate_min_policy >= 0  # 0.0 is valid for strong models
        assert ref.candidate_max_count > 0
        assert ref.refutation_max_count > 0
        assert ref.delta_threshold > 0

    def test_validation_thresholds_present(self):
        val = self.cfg.validation
        assert 0 < val.flagged_value_low < val.flagged_value_high < 1
        assert val.rejected_not_in_top_n >= 5
        assert 0 < val.winrate_rescue_auto_accept <= 1.0
        assert val.winrate_rescue_auto_accept >= val.flagged_value_high, (
            "winrate_rescue_auto_accept must be >= flagged_value_high"
        )

    def test_quality_gates_present(self):
        qg = self.cfg.quality_gates
        assert 0 < qg.acceptance_threshold <= 1.0
        assert 0 < qg.difficulty_match_threshold <= 1.0

    def test_analysis_defaults_present(self):
        ad = self.cfg.analysis_defaults
        assert ad.default_max_visits >= 1
        assert ad.puzzle_region_margin >= 0
        assert ad.visits_escalation_multiplier >= 1
        assert ad.visits_escalation_addend >= 0

    def test_paths_config_present(self):
        """Q10: Verify paths section exists and points to .lab-runtime/."""
        assert self.cfg.paths is not None
        assert self.cfg.paths.runtime_dir == ".lab-runtime"
        assert self.cfg.paths.logs_dir.startswith(".lab-runtime")
        assert self.cfg.paths.katago_logs_dir.startswith(".lab-runtime")
        assert self.cfg.paths.outputs_dir.startswith(".lab-runtime")
        assert self.cfg.paths.calibration_results_dir.startswith(".lab-runtime")

    def test_resolve_path_returns_absolute(self):
        """Q10: resolve_path returns absolute path under lab root."""
        from config import resolve_path
        logs = resolve_path(self.cfg, "logs_dir")
        assert logs.is_absolute()
        assert str(logs).endswith("logs")
        outputs = resolve_path(self.cfg, "outputs_dir")
        assert outputs.is_absolute()
        calibration = resolve_path(self.cfg, "calibration_results_dir")
        assert calibration.is_absolute()
        assert "calibration-results" in str(calibration)


@pytest.mark.unit
class TestLevelIdsMatchSourceOfTruth:
    """Verify level IDs in enrichment config match config/puzzle-levels.json."""

    @pytest.fixture(autouse=True)
    def _load_levels(self):
        data = json.loads(PUZZLE_LEVELS_PATH.read_text())
        self.levels = {lv["slug"]: lv["id"] for lv in data["levels"]}

    def test_all_9_levels_present(self):
        assert len(self.levels) == 9

    def test_level_ids_are_correct(self):
        """Level IDs must be 110, 120, 130, 140, 150, 160, 210, 220, 230."""
        expected = {
            "novice": 110,
            "beginner": 120,
            "elementary": 130,
            "intermediate": 140,
            "upper-intermediate": 150,
            "advanced": 160,
            "low-dan": 210,
            "high-dan": 220,
            "expert": 230,
        }
        for slug, expected_id in expected.items():
            assert self.levels[slug] == expected_id, (
                f"Level '{slug}' has ID {self.levels[slug]}, expected {expected_id}"
            )

    def test_config_level_slugs_match(self):
        """All level slugs in enrichment config difficulty thresholds
        must exist in puzzle-levels.json."""
        from config import load_enrichment_config
        cfg = load_enrichment_config()
        for entry in cfg.difficulty.score_to_level_thresholds:
            assert entry.level_slug in self.levels, (
                f"Level slug '{entry.level_slug}' in enrichment config "
                f"not found in puzzle-levels.json"
            )


@pytest.mark.unit
class TestOwnershipThresholdsByRegion:
    """Verify corner/edge use standard thresholds, center uses reduced."""

    @pytest.fixture(autouse=True)
    def _load_config(self):
        from config import load_enrichment_config
        self.cfg = load_enrichment_config()

    def test_standard_threshold(self):
        ot = self.cfg.ownership_thresholds
        assert ot.alive == pytest.approx(0.7)

    def test_center_reduced_threshold(self):
        ot = self.cfg.ownership_thresholds
        assert ot.center_alive < ot.alive, (
            "Center alive threshold should be lower than standard"
        )
        assert ot.center_alive == pytest.approx(0.5)

    def test_center_dead_threshold(self):
        ot = self.cfg.ownership_thresholds
        assert ot.center_dead > ot.dead, (
            "Center dead threshold should be less negative than standard"
        )


@pytest.mark.unit
class TestWinrateRescueAutoAccept:
    """Verify _status_from_classification uses WR + visits (rank removed)."""

    @pytest.fixture(autouse=True)
    def _load_config(self):
        from config import load_enrichment_config
        self.cfg = load_enrichment_config()

    def test_high_winrate_auto_accepted(self):
        """Winrate >= auto-accept threshold → ACCEPTED regardless of rank."""
        from analyzers.validate_correct_move import ValidationStatus, _status_from_classification
        status, flags = _status_from_classification(
            correct_winrate=0.95, config=self.cfg,
            correct_move_visits=100,
        )
        assert status == ValidationStatus.ACCEPTED

    def test_good_winrate_sufficient_visits_accepted(self):
        """WR >= flagged_high with enough visits → ACCEPTED."""
        from analyzers.validate_correct_move import ValidationStatus, _status_from_classification
        status, flags = _status_from_classification(
            correct_winrate=0.75, config=self.cfg,
            correct_move_visits=100,
        )
        assert status == ValidationStatus.ACCEPTED

    def test_good_winrate_insufficient_visits_flagged(self):
        """WR >= flagged_high but too few visits → FLAGGED as under-explored."""
        from analyzers.validate_correct_move import ValidationStatus, _status_from_classification
        status, flags = _status_from_classification(
            correct_winrate=0.75, config=self.cfg,
            correct_move_visits=10,
        )
        assert status == ValidationStatus.FLAGGED
        assert "reason:under_explored" in flags

    def test_uncertain_winrate_flagged(self):
        """WR between flagged_low and flagged_high → FLAGGED."""
        from analyzers.validate_correct_move import ValidationStatus, _status_from_classification
        status, flags = _status_from_classification(
            correct_winrate=0.5, config=self.cfg,
            correct_move_visits=500,
        )
        assert status == ValidationStatus.FLAGGED
        assert "reason:uncertain_winrate" in flags

    def test_rejected_low_winrate(self):
        """Low winrate → REJECTED."""
        from analyzers.validate_correct_move import ValidationStatus, _status_from_classification
        status, flags = _status_from_classification(
            correct_winrate=0.2, config=self.cfg,
            correct_move_visits=500,
        )
        assert status == ValidationStatus.REJECTED

    def test_rank_not_required_for_acceptance(self):
        """High WR + sufficient visits → ACCEPTED (rank params removed)."""
        from analyzers.validate_correct_move import ValidationStatus, _status_from_classification
        status, flags = _status_from_classification(
            correct_winrate=0.90, config=self.cfg,
            correct_move_visits=200,
        )
        assert status == ValidationStatus.ACCEPTED

    def test_source_trust_softens_rejected(self):
        """D4: Tier >= 4 softens REJECTED → FLAGGED with source_trust_rescue flag."""
        from analyzers.validate_correct_move import ValidationStatus, _status_from_classification
        # Low winrate without trust → REJECTED
        status, flags = _status_from_classification(
            correct_winrate=0.2, config=self.cfg,
            correct_move_visits=500, source_tier=0,
        )
        assert status == ValidationStatus.REJECTED

        # Same low winrate with tier 4 → FLAGGED
        status, flags = _status_from_classification(
            correct_winrate=0.2, config=self.cfg,
            correct_move_visits=500, source_tier=4,
        )
        assert status == ValidationStatus.FLAGGED
        assert "source_trust_rescue" in flags


@pytest.mark.unit
class TestConfidenceReason:
    """D1: Verify confidence_reason is populated in difficulty estimation."""

    def test_katago_disagrees_reason(self):
        from analyzers.estimate_difficulty import estimate_difficulty
        from models.refutation_result import RefutationResult
        from models.validation import CorrectMoveResult, ValidationStatus

        validation = CorrectMoveResult(
            status=ValidationStatus.FLAGGED,
            correct_move_gtp="D4", katago_agrees=False,
            katago_top_move="C3", correct_move_policy=0.3,
            correct_move_winrate=0.5, visits_used=500,
        )
        result = estimate_difficulty(validation, RefutationResult(), ["dd"], "test")
        assert result.confidence_reason == "katago_disagrees"

    def test_ko_capped_reason(self):
        from analyzers.estimate_difficulty import estimate_difficulty
        from models.refutation_result import RefutationResult
        from models.validation import ConfidenceLevel, CorrectMoveResult, ValidationStatus

        validation = CorrectMoveResult(
            status=ValidationStatus.ACCEPTED,
            correct_move_gtp="D4", katago_agrees=True,
            katago_top_move="D4", correct_move_policy=0.3,
            correct_move_winrate=0.8, visits_used=2000,
        )
        result = estimate_difficulty(
            validation, RefutationResult(), ["dd", "ee", "ff"], "test",
            tags=[12],  # ko tag
        )
        assert result.confidence == ConfidenceLevel.MEDIUM
        assert result.confidence_reason == "ko_capped"


@pytest.mark.unit
class TestRankBandFlags:
    """D2: Verify rank-band analytics flags in diagnostic flags."""

    def test_rank_band_top3(self):
        from analyzers.validate_correct_move import _build_diagnostic_flags
        from config import load_enrichment_config
        cfg = load_enrichment_config()
        flags = _build_diagnostic_flags(True, True, 0.5, 2, cfg, 0.9)
        assert "rank_band:top3" in flags

    def test_rank_band_top10(self):
        from analyzers.validate_correct_move import _build_diagnostic_flags
        from config import load_enrichment_config
        cfg = load_enrichment_config()
        flags = _build_diagnostic_flags(False, True, 0.5, 7, cfg, 0.9)
        assert "rank_band:top10" in flags

    def test_rank_band_outside(self):
        from analyzers.validate_correct_move import _build_diagnostic_flags
        from config import load_enrichment_config
        cfg = load_enrichment_config()
        flags = _build_diagnostic_flags(False, False, 0.5, 25, cfg, 0.9)
        assert "rank_band:outside_top20" in flags

    def test_rank_band_unranked(self):
        from analyzers.validate_correct_move import _build_diagnostic_flags
        from config import load_enrichment_config
        cfg = load_enrichment_config()
        flags = _build_diagnostic_flags(False, False, 0.0, 0, cfg, 0.0)
        assert "rank_band:unranked" in flags


@pytest.mark.unit
class TestDifficultyEstimateUsesConfig:
    """Verify estimate_difficulty outputs correct level IDs from config."""

    def test_novice_level_id(self):
        from analyzers.estimate_difficulty import estimate_difficulty
        from analyzers.validate_correct_move import CorrectMoveResult, ValidationStatus
        from models.refutation_result import RefutationResult

        # Easy puzzle: very high policy, minimal visits → novice
        validation = CorrectMoveResult(
            status=ValidationStatus.ACCEPTED,
            correct_move_gtp="D4",
            katago_agrees=True,
            katago_top_move="D4",
            correct_move_policy=0.95,
            correct_move_winrate=0.99,
            visits_used=1,
            confidence="high",
        )
        refutation = RefutationResult(refutations=[], total_candidates_evaluated=0)
        result = estimate_difficulty(validation, refutation, solution_moves=["cd"])
        assert result.estimated_level == "novice"
        assert result.estimated_level_id == 110  # NOT 100

    def test_expert_level_id(self):
        from analyzers.estimate_difficulty import estimate_difficulty
        from analyzers.validate_correct_move import CorrectMoveResult, ValidationStatus
        from models.refutation_result import Refutation, RefutationResult

        # Hard puzzle: very low policy, KataGo disagrees, deep solution,
        # high trap density (tempting wrong moves with large winrate drops)
        validation = CorrectMoveResult(
            status=ValidationStatus.ACCEPTED,
            correct_move_gtp="D4",
            katago_agrees=False,
            katago_top_move="E5",
            correct_move_policy=0.001,
            correct_move_winrate=0.55,
            visits_used=10000,
            confidence="low",
        )
        refutations = [
            Refutation(wrong_move="ce", wrong_move_policy=0.3,
                       refutation_sequence=["de", "df"], winrate_after_wrong=0.1,
                       winrate_delta=-0.9),
            Refutation(wrong_move="cf", wrong_move_policy=0.2,
                       refutation_sequence=["dg", "dh"], winrate_after_wrong=0.15,
                       winrate_delta=-0.8),
            Refutation(wrong_move="cg", wrong_move_policy=0.15,
                       refutation_sequence=["di", "dj"], winrate_after_wrong=0.12,
                       winrate_delta=-0.7),
        ]
        refutation_result = RefutationResult(
            refutations=refutations, total_candidates_evaluated=5
        )
        result = estimate_difficulty(
            validation, refutation_result,
            solution_moves=["cd", "dc", "dd", "cc", "cb", "db", "da", "ea",
                           "eb", "ec", "ed", "ee", "ef", "eg", "eh"],
            branch_count=5,
            local_candidate_count=15,
        )
        # G4 review: With 5-dimension structural weights (KM-04 added proof_depth),
        # this puzzle lands on the low-dan/high-dan/expert boundary. All are
        # acceptable for a puzzle with policy=0.001, 15-move solution, 5 branches,
        # 3 refutations.
        assert result.estimated_level in ("expert", "high-dan", "low-dan"), (
            f"Expected expert, high-dan, or low-dan, got {result.estimated_level}"
        )
        assert result.estimated_level_id >= 210  # low-dan (210), high-dan (220) or expert (230)


# ---------------------------------------------------------------------------
# From test_deep_enrich_config.py
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDeepEnrichConfig:
    """Deep enrich config values from katago-enrichment.json."""

    def test_config_loads_deep_enrich(self) -> None:
        """Config has a deep_enrich section."""
        config = load_enrichment_config()
        assert hasattr(config, "deep_enrich")
        assert isinstance(config.deep_enrich, DeepEnrichConfig)

    def test_deep_enrich_enabled_by_default(self) -> None:
        """Deep enrich is enabled by default in config."""
        config = load_enrichment_config()
        assert config.deep_enrich.enabled is True

    def test_deep_enrich_visits(self) -> None:
        """Deep enrich visits = 2000 (P1.1: performance-optimized)."""
        config = load_enrichment_config()
        assert config.deep_enrich.visits == 2000

    def test_deep_enrich_model(self) -> None:
        """Deep enrich uses b18c384 (P1.1: 3x faster, b28 for referee only)."""
        config = load_enrichment_config()
        assert "b18" in config.deep_enrich.model

    def test_deep_enrich_symmetries(self) -> None:
        """rootNumSymmetriesToSample = 4 (T25: standard analysis)."""
        config = load_enrichment_config()
        assert config.deep_enrich.root_num_symmetries_to_sample == 4

    def test_referee_symmetries(self) -> None:
        """referee_symmetries = 8 (T25: referee/T3 tier)."""
        config = load_enrichment_config()
        assert config.deep_enrich.referee_symmetries == 8

    def test_no_max_time_limit(self) -> None:
        """maxTime = 0 means no time limit per query."""
        config = load_enrichment_config()
        assert config.deep_enrich.max_time == 0

    def test_config_version_bumped(self) -> None:
        """Config version >= 1.12 (Plan 010)."""
        config = load_enrichment_config()
        major, minor = config.version.split(".")
        version_num = int(major) * 10 + int(minor)
        assert version_num >= 18

    def test_escalation_fields_present(self) -> None:
        """Escalation fields from deep_enrich section."""
        config = load_enrichment_config()
        assert config.deep_enrich.escalate_to_referee is True
        assert config.deep_enrich.escalation_winrate_low == 0.3
        assert config.deep_enrich.escalation_winrate_high == 0.7
        assert config.deep_enrich.tiebreaker_tolerance == 0.05


@pytest.mark.unit
class TestDeepEnrichVisitsWiring:
    """Deep enrich visits used by get_effective_max_visits()."""

    def test_deep_enrich_enabled_uses_deep_enrich_visits(self) -> None:
        """When deep_enrich.enabled, effective visits = deep_enrich.visits."""
        config = load_enrichment_config()
        assert config.deep_enrich.enabled is True
        effective = get_effective_max_visits(config)
        assert effective == config.deep_enrich.visits

    def test_deep_enrich_disabled_uses_defaults(self) -> None:
        """When deep_enrich.enabled=False, effective visits = analysis_defaults."""
        config = load_enrichment_config()
        config.deep_enrich.enabled = False
        effective = get_effective_max_visits(config)
        assert effective == config.analysis_defaults.default_max_visits


@pytest.mark.unit
class TestGetEffectiveMaxVisitsWithModeOverride:
    """get_effective_max_visits respects mode_override parameter."""

    def test_deep_enrich_returns_deep_enrich_visits(self) -> None:
        """Default (no override): deep_enrich.enabled → deep_enrich visits."""
        config = load_enrichment_config()
        assert config.deep_enrich.enabled is True
        assert get_effective_max_visits(config) == config.deep_enrich.visits

    def test_quick_only_override_returns_default_visits(self) -> None:
        """mode_override='quick_only' returns analysis_defaults.default_max_visits."""
        config = load_enrichment_config()
        result = get_effective_max_visits(config, mode_override="quick_only")
        assert result == config.analysis_defaults.default_max_visits

    def test_no_deep_enrich_returns_defaults(self) -> None:
        """deep_enrich disabled, no override → analysis defaults."""
        config = load_enrichment_config()
        config.deep_enrich.enabled = False
        result = get_effective_max_visits(config)
        assert result == config.analysis_defaults.default_max_visits


# ---------------------------------------------------------------------------
# From test_tsumego_config.py
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestTsumegoSettings:
    """Critical tsumego-specific settings are present and correct."""

    def test_root_num_symmetries_to_sample(self):
        """Default symmetries = 2 for fast iteration; lab mode overrides per-query (A8)."""
        settings = _parse_cfg(_CFG_PATH)
        assert settings.get("rootNumSymmetriesToSample") == "2", (
            f"Expected rootNumSymmetriesToSample=2 (fast default, A8), "
            f"got {settings.get('rootNumSymmetriesToSample', 'MISSING')}"
        )

    def test_static_score_utility_factor(self):
        """staticScoreUtilityFactor = 0.1 for controlled seki detection sensitivity."""
        settings = _parse_cfg(_CFG_PATH)
        assert settings.get("staticScoreUtilityFactor") == "0.1", (
            f"Expected staticScoreUtilityFactor=0.1, got {settings.get('staticScoreUtilityFactor', 'MISSING')}"
        )

    def test_removed_keys_absent(self):
        """Unused keys (v2 audit) must not be present — they generate KataGo warnings."""
        settings = _parse_cfg(_CFG_PATH)
        removed_keys = ["allowSelfAtari", "analysisWideRootNoise", "cpuctExplorationAtRoot", "scoreUtilityFactor"]
        for key in removed_keys:
            assert key not in settings, f"Removed key '{key}' should not be in .cfg (generates KataGo warning)"

    def test_dynamic_score_utility_factor(self):
        """Small dynamic score utility helps distinguish seki vs death."""
        settings = _parse_cfg(_CFG_PATH)
        val = settings.get("dynamicScoreUtilityFactor", "MISSING")
        assert val == "0.1", (
            f"Expected dynamicScoreUtilityFactor=0.1, got {val}"
        )


@pytest.mark.unit
class TestConfigMatchesExisting:
    """Verify the existing config has all required settings for tsumego enrichment."""

    def test_wide_root_noise_low(self):
        """wideRootNoise should be moderate for focused tsumego search with enough exploration."""
        settings = _parse_cfg(_CFG_PATH)
        val = float(settings.get("wideRootNoise", "1.0"))
        assert val <= 0.05, f"wideRootNoise too high: {val}"

    def test_conservative_pass_enabled(self):
        """conservativePass prevents premature passing in tsumego."""
        settings = _parse_cfg(_CFG_PATH)
        assert settings.get("conservativePass") == "true"

    def test_prevent_cleanup_phase(self):
        """preventCleanupPhase keeps focus on life/death, not scoring cleanup."""
        settings = _parse_cfg(_CFG_PATH)
        assert settings.get("preventCleanupPhase") == "true"

    def test_analysis_pv_len_sufficient(self):
        """PV length should be at least 10 for solution tree depth."""
        settings = _parse_cfg(_CFG_PATH)
        val = int(settings.get("analysisPVLen", "0"))
        assert val >= 10, f"analysisPVLen too short: {val}"

    def test_ignore_pre_root_history(self):
        """Preserve ko history — some puzzles involve ko sequences."""
        settings = _parse_cfg(_CFG_PATH)
        assert settings.get("ignorePreRootHistory") == "false"


# ---------------------------------------------------------------------------
# From test_ai_solve_config.py
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestAiSolveThresholdDefaults:
    """All threshold values match plan defaults (DD-1 through DD-12)."""

    @pytest.fixture(autouse=True)
    def _load(self):
        from config import load_enrichment_config
        self.cfg = load_enrichment_config()
        self.ai = self.cfg.ai_solve

    def test_t_good_default(self):
        assert self.ai.thresholds.t_good == pytest.approx(0.03)

    def test_t_bad_default(self):
        assert self.ai.thresholds.t_bad == pytest.approx(0.12)

    def test_t_hotspot_default(self):
        assert self.ai.thresholds.t_hotspot == pytest.approx(0.30)

    def test_t_disagreement_default(self):
        assert self.ai.thresholds.t_disagreement == pytest.approx(0.07)

    def test_thresholds_ordering(self):
        """t_good < t_bad < t_hotspot (enforced by validator)."""
        assert self.ai.thresholds.t_good < self.ai.thresholds.t_bad
        assert self.ai.thresholds.t_bad < self.ai.thresholds.t_hotspot

    def test_confidence_metrics_defaults(self):
        assert self.ai.confidence_metrics.pre_winrate_floor == pytest.approx(0.30)
        assert self.ai.confidence_metrics.post_winrate_ceiling == pytest.approx(0.95)

    def test_solution_tree_epsilons(self):
        assert self.ai.solution_tree.wr_epsilon == pytest.approx(0.02)
        assert self.ai.solution_tree.own_epsilon == pytest.approx(0.05)

    def test_solution_tree_branching(self):
        assert self.ai.solution_tree.branch_min_policy == pytest.approx(0.05)
        assert self.ai.solution_tree.max_branch_width == 3
        assert self.ai.solution_tree.max_total_tree_queries == 65

    def test_confirmation_min_policy(self):
        assert self.ai.solution_tree.confirmation_min_policy == pytest.approx(0.03)

    def test_tree_visits(self):
        assert self.ai.solution_tree.tree_visits == 500

    def test_seki_detection_defaults(self):
        seki = self.ai.seki_detection
        assert seki.winrate_band_low == pytest.approx(0.45)
        assert seki.winrate_band_high == pytest.approx(0.55)
        assert seki.seki_consecutive_depth == 3
        assert seki.score_lead_seki_max == pytest.approx(5.0)

    def test_goal_inference_defaults(self):
        gi = self.ai.goal_inference
        assert gi.score_delta_kill == pytest.approx(15.0)
        assert gi.score_delta_ko == pytest.approx(7.0)
        assert gi.ownership_threshold == pytest.approx(0.7)
        assert gi.ownership_variance_gate == pytest.approx(0.3)

    def test_edge_case_boosts_defaults(self):
        ec = self.ai.edge_case_boosts
        assert ec.corner_visit_boost == pytest.approx(1.5)
        assert ec.ladder_visit_boost == pytest.approx(2.0)
        assert ec.ladder_pv_threshold == 8

    def test_alternatives_defaults(self):
        alt = self.ai.alternatives
        assert alt.co_correct_min_gap == pytest.approx(0.02)
        assert alt.co_correct_score_gap == pytest.approx(2.0)
        assert alt.disagreement_threshold == pytest.approx(0.10)
        assert alt.losing_threshold == pytest.approx(0.30)

    def test_calibration_defaults(self):
        cal = self.ai.calibration
        assert cal.min_samples_per_class == 30
        assert cal.target_macro_f1 == pytest.approx(0.85)
        assert cal.visit_counts == [500, 1000, 2000]

    def test_observability_defaults(self):
        obs = self.ai.observability
        assert obs.disagreement_sink_path == ".lab-runtime/logs/disagreements"
        assert obs.collection_warning_threshold == pytest.approx(0.20)


@pytest.mark.unit
class TestDepthProfiles:
    """Level slug resolves deterministically to entry/core/strong depth profile."""

    @pytest.fixture(autouse=True)
    def _load(self):
        from config import load_enrichment_config
        self.cfg = load_enrichment_config()
        self.profiles = self.cfg.ai_solve.solution_tree.depth_profiles

    def test_three_categories_present(self):
        assert set(self.profiles.keys()) == {"entry", "core", "strong"}

    def test_entry_profile(self):
        p = self.profiles["entry"]
        assert p.solution_min_depth == 3
        assert p.solution_max_depth == 10

    def test_core_profile(self):
        p = self.profiles["core"]
        assert p.solution_min_depth == 3
        assert p.solution_max_depth == 16

    def test_strong_profile(self):
        p = self.profiles["strong"]
        assert p.solution_min_depth == 4
        assert p.solution_max_depth == 24

    def test_min_le_max_for_all_profiles(self):
        for cat, prof in self.profiles.items():
            assert prof.solution_min_depth <= prof.solution_max_depth, (
                f"Profile '{cat}': min {prof.solution_min_depth} > max {prof.solution_max_depth}"
            )


@pytest.mark.unit
class TestLevelCategoryMapping:
    """Level slug → category mapping is deterministic and complete."""

    def test_all_9_levels_mapped(self):
        from config.helpers import LEVEL_CATEGORY_MAP
        expected_slugs = {
            "novice", "beginner", "elementary",
            "intermediate", "upper-intermediate",
            "advanced", "low-dan", "high-dan", "expert",
        }
        assert set(LEVEL_CATEGORY_MAP.keys()) == expected_slugs

    def test_entry_levels(self):
        from config.helpers import get_level_category
        assert get_level_category("novice") == "entry"
        assert get_level_category("beginner") == "entry"
        assert get_level_category("elementary") == "entry"

    def test_core_levels(self):
        from config.helpers import get_level_category
        assert get_level_category("intermediate") == "core"
        assert get_level_category("upper-intermediate") == "core"

    def test_strong_levels(self):
        from config.helpers import get_level_category
        assert get_level_category("advanced") == "strong"
        assert get_level_category("low-dan") == "strong"
        assert get_level_category("high-dan") == "strong"
        assert get_level_category("expert") == "strong"

    def test_unknown_level_raises(self):
        from config.helpers import get_level_category
        with pytest.raises(KeyError):
            get_level_category("grandmaster")


@pytest.mark.unit
class TestRootAllocationCaps:
    """max_correct_root_trees=2 and max_refutation_root_trees=3 are present and enforced."""

    @pytest.fixture(autouse=True)
    def _load(self):
        from config import load_enrichment_config
        self.cfg = load_enrichment_config()
        self.tree = self.cfg.ai_solve.solution_tree

    def test_max_correct_root_trees_default(self):
        assert self.tree.max_correct_root_trees == 2

    def test_max_refutation_root_trees_default(self):
        assert self.tree.max_refutation_root_trees == 3

    def test_max_correct_root_trees_integer_bounds(self):
        """Must be >= 1 and <= 5."""
        from config.solution_tree import SolutionTreeConfig
        with pytest.raises(Exception):
            SolutionTreeConfig(max_correct_root_trees=0)
        # Valid boundaries
        SolutionTreeConfig(max_correct_root_trees=1)
        SolutionTreeConfig(max_correct_root_trees=5)

    def test_max_refutation_root_trees_integer_bounds(self):
        """Must be >= 0 and <= 10."""
        from config.solution_tree import SolutionTreeConfig
        with pytest.raises(Exception):
            SolutionTreeConfig(max_refutation_root_trees=-1)
        # Valid boundaries
        SolutionTreeConfig(max_refutation_root_trees=0)
        SolutionTreeConfig(max_refutation_root_trees=10)


@pytest.mark.unit
class TestAiSolveChangelogEntry:
    """v1.14 changelog entry exists in katago-enrichment.json."""

    def test_v1_14_changelog_present(self):
        data = json.loads(ENRICHMENT_CONFIG_PATH.read_text())
        versions = {e["version"]: e["changes"] for e in data["changelog"]}
        assert "1.14" in versions
        entry = versions["1.14"]
        assert "AI-Solve" in entry
        assert "ai_solve" in entry
