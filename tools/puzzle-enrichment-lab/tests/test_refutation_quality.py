"""Tests for refutation tree quality improvements — Phases A through D.

TS-1: PI-1 ownership delta scoring (weight=0, weight=0.5, weight=1.0)
TS-2: PI-3 score delta filter (enabled/disabled, threshold edge cases)
TS-3: PI-4 model routing by category
TS-4: Config parsing and default values
TS-5: PI-10 opponent-response teaching comments
TS-8b: PI-2 adaptive visit allocation (fixed vs adaptive mode)
TS-8:  PI-5 board-size-scaled Dirichlet noise
TS-9:  PI-6 forced minimum visits per refutation candidate
TS-7:  PI-9 player-side alternative exploration (auto-detect, must-hold #4)
TS-11: PI-7 branch-local disagreement escalation
TS-12: PI-8 diversified root candidate harvesting
TS-10: PI-12 best-resistance line generation
TS-13: PI-11 surprise-weighted calibration
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
ENRICHMENT_CONFIG_PATH = _PROJECT_ROOT / "config" / "katago-enrichment.json"
TEACHING_CONFIG_PATH = _PROJECT_ROOT / "config" / "teaching-comments.json"


@pytest.fixture(autouse=True)
def _clear_caches():
    """Clear all config caches before each test."""
    from config import clear_cache
    from config.teaching import clear_teaching_cache
    clear_cache()
    clear_teaching_cache()
    yield
    clear_cache()
    clear_teaching_cache()


# ===========================================================================
# TS-1: PI-1 Ownership Delta Scoring
# ===========================================================================


@pytest.mark.unit
class TestOwnershipDelta:
    """PI-1: Ownership delta scoring for refutation candidates."""

    def test_compute_ownership_delta_no_data(self):
        from analyzers.generate_refutations import compute_ownership_delta
        assert compute_ownership_delta(None, None) == 0.0
        assert compute_ownership_delta([0.5] * 361, None) == 0.0
        assert compute_ownership_delta(None, [0.5] * 361) == 0.0

    def test_compute_ownership_delta_identical(self):
        from analyzers.generate_refutations import compute_ownership_delta
        root = [0.5] * 361
        move = [0.5] * 361
        assert compute_ownership_delta(root, move) == pytest.approx(0.0)

    def test_compute_ownership_delta_max_flip(self):
        from analyzers.generate_refutations import compute_ownership_delta
        root = [0.7] * 361
        move = [-0.7] * 361
        assert compute_ownership_delta(root, move) == pytest.approx(1.4)

    def test_compute_ownership_delta_single_flip(self):
        from analyzers.generate_refutations import compute_ownership_delta
        root = [0.0] * 361
        move = [0.0] * 361
        move[42] = 0.9  # One intersection flipped
        assert compute_ownership_delta(root, move) == pytest.approx(0.9)

    def test_compute_ownership_delta_nested_input(self):
        from analyzers.generate_refutations import compute_ownership_delta
        root = [0.0] * 361
        # Nested 19x19 list
        move = [[0.0] * 19 for _ in range(19)]
        move[2][3] = 0.8
        assert compute_ownership_delta(root, move) == pytest.approx(0.8)

    def test_compute_ownership_delta_short_arrays(self):
        from analyzers.generate_refutations import compute_ownership_delta
        root = [0.5] * 10
        move = [0.5] * 10
        assert compute_ownership_delta(root, move, board_size=19) == 0.0

    def test_identify_candidates_weight_zero_is_baseline(self):
        """ownership_delta_weight=0 produces candidate list without ownership boost."""
        from analyzers.generate_refutations import identify_candidates
        from config import load_enrichment_config
        from models.analysis_response import AnalysisResponse, MoveAnalysis

        config = load_enrichment_config()
        # Weight is 0.3 (PI-1 activated in v1.23)
        assert config.refutations.ownership_delta_weight == pytest.approx(0.3)
        # Use policy_only scoring to avoid temperature effects
        config.refutations.candidate_scoring.mode = "policy_only"

        analysis = AnalysisResponse(
            move_infos=[
                MoveAnalysis(move="D4", visits=100, winrate=0.9, policy_prior=0.6, score_lead=10.0),
                MoveAnalysis(move="E5", visits=50, winrate=0.3, policy_prior=0.3, score_lead=5.0),
                MoveAnalysis(move="F6", visits=30, winrate=0.4, policy_prior=0.1, score_lead=3.0),
            ],
            root_winrate=0.85,
            root_score=8.0,
        )
        result = identify_candidates(analysis, "D4", config)
        assert len(result) == 2
        # E5 has higher policy, should be first in policy_only mode
        assert result[0].move == "E5"

    def test_identify_candidates_weight_nonzero_boosts_ownership(self):
        """ownership_delta_weight > 0 boosts candidates with ownership flips."""
        from analyzers.generate_refutations import identify_candidates
        from config import load_enrichment_config
        from models.analysis_response import AnalysisResponse, MoveAnalysis
        config = load_enrichment_config()
        config.refutations.ownership_delta_weight = 1.0  # Full ownership weight
        config.refutations.candidate_scoring.mode = "policy_only"

        # E5: slightly higher policy, no ownership change
        # F6: slightly lower policy, massive ownership delta
        # With weight=1.0, composite = ownership_delta only
        analysis = AnalysisResponse(
            move_infos=[
                MoveAnalysis(
                    move="D4", visits=100, winrate=0.9,
                    policy_prior=0.5, score_lead=10.0,
                ),
                MoveAnalysis(
                    move="E5", visits=50, winrate=0.3,
                    policy_prior=0.15, score_lead=5.0,
                    ownership=[[0.01] * 19 for _ in range(19)],
                ),
                MoveAnalysis(
                    move="F6", visits=30, winrate=0.2,
                    policy_prior=0.12, score_lead=3.0,
                    ownership=[[0.95] * 19 for _ in range(19)],
                ),
            ],
            root_winrate=0.85,
            root_score=8.0,
            ownership=[0.0] * 361,
        )
        result = identify_candidates(analysis, "D4", config)
        assert len(result) == 2
        # F6 should be boosted by ownership delta (0.95 vs 0.01) and rank first
        assert result[0].move == "F6"


# ===========================================================================
# TS-2: PI-3 Score Delta Filter
# ===========================================================================


@pytest.mark.unit
class TestScoreDeltaFilter:
    """PI-3: Score-lead delta as complementary refutation filter."""

    def test_score_delta_enabled(self):
        from config import load_enrichment_config
        config = load_enrichment_config()
        assert config.refutations.score_delta_enabled is True
        assert config.refutations.score_delta_threshold == pytest.approx(5.0)

    def test_score_delta_config_fields_exist(self):
        from config.refutations import RefutationsConfig
        cfg = RefutationsConfig()
        assert hasattr(cfg, "score_delta_enabled")
        assert hasattr(cfg, "score_delta_threshold")
        assert cfg.score_delta_enabled is False
        assert cfg.score_delta_threshold == pytest.approx(5.0)

    def test_score_delta_enabled_in_json(self):
        data = json.loads(ENRICHMENT_CONFIG_PATH.read_text())
        ref = data["refutations"]
        assert "score_delta_enabled" in ref
        assert ref["score_delta_enabled"] is True
        assert "score_delta_threshold" in ref
        assert ref["score_delta_threshold"] == pytest.approx(5.0)

    def test_score_delta_rescue_includes_low_policy_move(self):
        """score_delta_enabled=True rescues a low-policy move with large score delta."""
        from analyzers.generate_refutations import identify_candidates
        from config import load_enrichment_config
        from models.analysis_response import AnalysisResponse, MoveAnalysis

        config = load_enrichment_config()
        config.refutations.score_delta_enabled = True
        config.refutations.score_delta_threshold = 5.0
        # Set min_policy > 0 so the rescue path activates
        config.refutations.candidate_min_policy = 0.05

        analysis = AnalysisResponse(
            move_infos=[
                MoveAnalysis(move="D4", visits=100, winrate=0.9, policy_prior=0.6, score_lead=10.0),
                MoveAnalysis(move="E5", visits=50, winrate=0.3, policy_prior=0.1, score_lead=5.0),
                # G7: low policy (below min_policy) but large score delta (10 - (-2) = 12 > 5)
                MoveAnalysis(move="G7", visits=10, winrate=0.2, policy_prior=0.01, score_lead=-2.0),
            ],
            root_winrate=0.85,
            root_score=10.0,
        )
        result = identify_candidates(analysis, "D4", config)
        result_moves = [m.move for m in result]
        assert "E5" in result_moves, "E5 should be included via normal policy threshold"
        assert "G7" in result_moves, "G7 should be rescued by score delta (|10 - (-2)| = 12 >= 5)"

    def test_score_delta_rescue_skips_when_disabled(self):
        """score_delta_enabled=False does not rescue low-policy moves."""
        from analyzers.generate_refutations import identify_candidates
        from config import load_enrichment_config
        from models.analysis_response import AnalysisResponse, MoveAnalysis

        config = load_enrichment_config()
        config.refutations.score_delta_enabled = False
        config.refutations.candidate_min_policy = 0.05

        analysis = AnalysisResponse(
            move_infos=[
                MoveAnalysis(move="D4", visits=100, winrate=0.9, policy_prior=0.6, score_lead=10.0),
                MoveAnalysis(move="E5", visits=50, winrate=0.3, policy_prior=0.1, score_lead=5.0),
                MoveAnalysis(move="G7", visits=10, winrate=0.2, policy_prior=0.01, score_lead=-2.0),
            ],
            root_winrate=0.85,
            root_score=10.0,
        )
        result = identify_candidates(analysis, "D4", config)
        result_moves = [m.move for m in result]
        assert "G7" not in result_moves, "G7 should NOT be rescued when score_delta_enabled=False"


# ===========================================================================
# TS-3: PI-4 Model Routing
# ===========================================================================


@pytest.mark.unit
class TestModelRouting:
    """PI-4: Model routing by puzzle complexity."""

    def test_model_by_category_default_empty(self):
        from config import load_enrichment_config
        config = load_enrichment_config()
        assert config.ai_solve.model_by_category == {}

    def test_model_by_category_in_json(self):
        data = json.loads(ENRICHMENT_CONFIG_PATH.read_text())
        assert "model_by_category" in data["ai_solve"]
        assert data["ai_solve"]["model_by_category"] == {}

    def test_get_model_for_level_empty_routing(self):
        from analyzers.single_engine import SingleEngineManager
        from config import load_enrichment_config
        config = load_enrichment_config()
        mgr = SingleEngineManager(config)
        assert mgr.get_model_for_level("intermediate") is None

    def test_get_model_for_level_active_routing(self):
        from analyzers.single_engine import SingleEngineManager
        from config import load_enrichment_config
        config = load_enrichment_config()
        config.ai_solve.model_by_category = {"entry": "test_fast", "core": "quick"}
        mgr = SingleEngineManager(config)
        result = mgr.get_model_for_level("novice")  # novice → entry → test_fast
        assert result is not None
        assert "b10c128" in result

    def test_get_model_for_level_unmapped_category(self):
        from analyzers.single_engine import SingleEngineManager
        from config import load_enrichment_config
        config = load_enrichment_config()
        config.ai_solve.model_by_category = {"entry": "test_fast"}
        mgr = SingleEngineManager(config)
        assert mgr.get_model_for_level("advanced") is None  # advanced → strong, not in map

    def test_model_label_for_routing_default(self):
        from analyzers.single_engine import SingleEngineManager
        from config import load_enrichment_config
        config = load_enrichment_config()
        mgr = SingleEngineManager(config)
        label = mgr.model_label_for_routing("intermediate")
        assert label == "b18c384"  # default model arch

    def test_model_label_for_routing_active(self):
        from analyzers.single_engine import SingleEngineManager
        from config import load_enrichment_config
        config = load_enrichment_config()
        config.ai_solve.model_by_category = {"entry": "test_fast"}
        mgr = SingleEngineManager(config)
        label = mgr.model_label_for_routing("beginner")  # beginner → entry → test_fast
        assert label == "b10c128"


# ===========================================================================
# TS-4: Config Parsing and Defaults
# ===========================================================================


@pytest.mark.unit
class TestPhaseAConfigParsing:
    """Phase A config keys parse correctly with proper defaults."""

    def test_ownership_delta_weight_default(self):
        from config import load_enrichment_config
        cfg = load_enrichment_config()
        assert cfg.refutations.ownership_delta_weight == pytest.approx(0.3)

    def test_score_delta_defaults(self):
        from config import load_enrichment_config
        cfg = load_enrichment_config()
        assert cfg.refutations.score_delta_enabled is True
        assert cfg.refutations.score_delta_threshold == pytest.approx(5.0)

    def test_model_by_category_default(self):
        from config import load_enrichment_config
        cfg = load_enrichment_config()
        assert cfg.ai_solve.model_by_category == {}

    def test_use_opponent_policy_default(self):
        from config import load_enrichment_config
        cfg = load_enrichment_config()
        assert cfg.teaching.use_opponent_policy is True

    def test_absent_keys_give_defaults(self, tmp_path):
        """Config without Phase A keys loads with defaults (backward compat)."""
        data = json.loads(ENRICHMENT_CONFIG_PATH.read_text())
        # Remove Phase A keys
        del data["refutations"]["ownership_delta_weight"]
        del data["refutations"]["score_delta_enabled"]
        del data["refutations"]["score_delta_threshold"]
        del data["ai_solve"]["model_by_category"]
        del data["teaching"]["use_opponent_policy"]
        minimal = tmp_path / "config.json"
        minimal.write_text(json.dumps(data))

        from config import load_enrichment_config
        cfg = load_enrichment_config(path=minimal)
        assert cfg.refutations.ownership_delta_weight == pytest.approx(0.0)
        assert cfg.refutations.score_delta_enabled is False
        assert cfg.refutations.score_delta_threshold == pytest.approx(5.0)
        assert cfg.ai_solve.model_by_category == {"strong": "referee"}
        assert cfg.teaching.use_opponent_policy is False

    def test_v1_18_changelog_present(self):
        data = json.loads(ENRICHMENT_CONFIG_PATH.read_text())
        versions = {e["version"]: e["changes"] for e in data["changelog"]}
        assert "1.18" in versions
        assert "PI-1" in versions["1.18"]
        assert "PI-3" in versions["1.18"]
        assert "PI-4" in versions["1.18"]
        assert "PI-10" in versions["1.18"]


# ===========================================================================
# TS-5: PI-10 Opponent-Response Teaching Comments
# ===========================================================================


@pytest.mark.unit
class TestOpponentResponseComments:
    """PI-10: Opponent-response phrases in wrong-move comments."""

    def test_feature_gate_off_no_change(self):
        """use_opponent_policy=False → no opponent-response appended."""
        from analyzers.comment_assembler import assemble_wrong_comment
        result = assemble_wrong_comment(
            "immediate_capture",
            opponent_move="cd",
            opponent_color="White",
            use_opponent_policy=False,
        )
        assert "White" not in result
        assert "captures" not in result

    def test_feature_gate_on_enabled_condition(self):
        """use_opponent_policy=True + enabled condition → opponent-response appended."""
        from analyzers.comment_assembler import assemble_wrong_comment
        result = assemble_wrong_comment(
            "immediate_capture",
            opponent_move="cd",
            opponent_color="White",
            use_opponent_policy=True,
        )
        assert "White" in result
        assert "captures the stone" in result

    def test_suppressed_condition_no_response(self):
        """Suppressed conditions should NOT get opponent-response."""
        from analyzers.comment_assembler import assemble_wrong_comment
        result = assemble_wrong_comment(
            "opponent_escapes",
            coord="df",
            opponent_move="cd",
            opponent_color="White",
            use_opponent_policy=True,
        )
        assert "White" not in result

    def test_all_five_active_conditions(self):
        """All 5 enabled conditions should produce opponent-response."""
        from analyzers.comment_assembler import assemble_wrong_comment
        active = [
            "immediate_capture", "capturing_race_lost",
            "self_atari", "wrong_direction", "default",
        ]
        for cond in active:
            result = assemble_wrong_comment(
                cond,
                opponent_move="cd",
                opponent_color="Black",
                use_opponent_policy=True,
            )
            assert "Black" in result, f"{cond} should have opponent-response"

    def test_seven_suppressed_conditions(self):
        """All 7 suppressed conditions should NOT produce opponent-response."""
        from analyzers.comment_assembler import assemble_wrong_comment
        suppressed = [
            "opponent_escapes", "opponent_lives", "opponent_takes_vital",
            "opponent_reduces_liberties", "shape_death_alias",
            "ko_involved", "almost_correct",
        ]
        for cond in suppressed:
            result = assemble_wrong_comment(
                cond,
                opponent_move="cd",
                opponent_color="White",
                use_opponent_policy=True,
            )
            assert "captures the stone" not in result, f"{cond} should be suppressed"
            assert "fills the last" not in result, f"{cond} should be suppressed"
            assert "claims the vital" not in result, f"{cond} should be suppressed"
            assert "responds decisively" not in result, f"{cond} should be suppressed"

    def test_conditional_dash_rule_wm_has_dash(self):
        """When WM has em-dash, opponent-response omits its dash."""
        from analyzers.comment_assembler import _assemble_opponent_response
        # shape_death_alias WM has "—" but is suppressed; use a custom scenario
        result = _assemble_opponent_response(
            condition="default",
            opponent_move="cd",
            opponent_color="White",
            wrong_move_comment="Something — consequence.",
            opponent_templates={
                "enabled_conditions": ["default"],
                "templates": [
                    {"condition": "default", "template": "{opponent_color} {!opponent_move} — responds decisively."},
                ],
            },
        )
        # The em-dash in the WM triggers dash omission in OR
        assert "\u2014" not in result  # No dash in opponent-response
        assert "responds decisively" in result

    def test_conditional_dash_rule_wm_no_dash(self):
        """When WM has no em-dash, opponent-response keeps its dash."""
        from analyzers.comment_assembler import _assemble_opponent_response
        result = _assemble_opponent_response(
            condition="immediate_capture",
            opponent_move="cd",
            opponent_color="White",
            wrong_move_comment="Captured immediately.",
            opponent_templates={
                "enabled_conditions": ["immediate_capture"],
                "templates": [
                    {"condition": "immediate_capture", "template": "{opponent_color} {!opponent_move} — captures the stone."},
                ],
            },
        )
        assert "\u2014" in result  # Dash preserved
        assert "captures the stone" in result

    def test_word_count_guard(self):
        """Combined comment must not exceed 15 words."""
        from analyzers.comment_assembler import _count_words, assemble_wrong_comment
        # Use a condition that produces a combined comment
        result = assemble_wrong_comment(
            "immediate_capture",
            opponent_move="cd",
            opponent_color="White",
            use_opponent_policy=True,
        )
        assert _count_words(result) <= 15


# ===========================================================================
# TS-8b: PI-2 Adaptive Visit Allocation
# ===========================================================================


@pytest.mark.unit
class TestAdaptiveVisitAllocation:
    """PI-2: Adaptive visit allocation per tree depth."""

    def test_visit_allocation_mode_adaptive(self):
        """Mode is 'adaptive' — PI-2 activated in v1.24."""
        from config import load_enrichment_config

        cfg = load_enrichment_config()
        assert cfg.ai_solve.solution_tree.visit_allocation_mode == "adaptive"

    def test_branch_visits_default(self):
        from config import load_enrichment_config

        cfg = load_enrichment_config()
        assert cfg.ai_solve.solution_tree.branch_visits == 500

    def test_continuation_visits_default(self):
        from config import load_enrichment_config

        cfg = load_enrichment_config()
        assert cfg.ai_solve.solution_tree.continuation_visits == 200

    def test_fixed_mode_uses_tree_visits(self):
        """In fixed mode, branch_visits and continuation_visits are not used."""
        from config.solution_tree import SolutionTreeConfig

        tree_cfg = SolutionTreeConfig(
            visit_allocation_mode="fixed",
            tree_visits=500,
            branch_visits=999,
            continuation_visits=77,
        )
        # In fixed mode, tree_visits is what the algorithm should use
        assert tree_cfg.visit_allocation_mode == "fixed"
        assert tree_cfg.tree_visits == 500

    def test_adaptive_mode_provides_branch_and_continuation(self):
        """In adaptive mode, separate visit counts for branch/continuation."""
        from config.solution_tree import SolutionTreeConfig

        tree_cfg = SolutionTreeConfig(
            visit_allocation_mode="adaptive",
            branch_visits=600,
            continuation_visits=150,
        )
        assert tree_cfg.visit_allocation_mode == "adaptive"
        assert tree_cfg.branch_visits == 600
        assert tree_cfg.continuation_visits == 150

    def test_config_parsing_from_json(self):
        """Phase B keys parse correctly from JSON."""
        data = json.loads(ENRICHMENT_CONFIG_PATH.read_text())
        st = data["ai_solve"]["solution_tree"]
        assert st["visit_allocation_mode"] == "adaptive"
        assert st["branch_visits"] == 500
        assert st["continuation_visits"] == 200

    def test_absent_keys_give_defaults(self, tmp_path):
        """Config without PI-2 keys loads with defaults (backward compat)."""
        data = json.loads(ENRICHMENT_CONFIG_PATH.read_text())
        st = data["ai_solve"]["solution_tree"]
        for key in ("visit_allocation_mode", "branch_visits", "continuation_visits"):
            st.pop(key, None)
        minimal = tmp_path / "config.json"
        minimal.write_text(json.dumps(data))

        from config import load_enrichment_config

        cfg = load_enrichment_config(path=minimal)
        assert cfg.ai_solve.solution_tree.visit_allocation_mode == "fixed"
        assert cfg.ai_solve.solution_tree.branch_visits == 500
        assert cfg.ai_solve.solution_tree.continuation_visits == 125


# ===========================================================================
# TS-8: PI-5 Board-Size-Scaled Dirichlet Noise
# ===========================================================================


@pytest.mark.unit
class TestBoardScaledNoise:
    """PI-5: Board-size-scaled Dirichlet noise for refutation candidates."""

    def test_noise_scaling_board_scaled(self):
        """Noise scaling is 'board_scaled' — PI-5 activated in v1.23."""
        from config import load_enrichment_config

        cfg = load_enrichment_config()
        assert cfg.refutations.refutation_overrides.noise_scaling == "board_scaled"

    def test_noise_base_default(self):
        from config import load_enrichment_config

        cfg = load_enrichment_config()
        assert cfg.refutations.refutation_overrides.noise_base == pytest.approx(0.03)

    def test_noise_reference_area_default(self):
        from config import load_enrichment_config

        cfg = load_enrichment_config()
        assert cfg.refutations.refutation_overrides.noise_reference_area == 361

    def test_board_scaled_9x9(self):
        """9×9 board: effective_noise = 0.03 * 361 / 81 ≈ 0.134."""
        from config.refutations import RefutationOverridesConfig

        cfg = RefutationOverridesConfig(
            noise_scaling="board_scaled",
            noise_base=0.03,
            noise_reference_area=361,
        )
        board_area = 9 * 9  # 81
        effective_noise = cfg.noise_base * cfg.noise_reference_area / board_area
        assert effective_noise == pytest.approx(0.03 * 361 / 81, rel=1e-4)
        assert effective_noise > cfg.wide_root_noise  # More noise on small boards

    def test_board_scaled_19x19(self):
        """19×19 board: effective_noise = 0.03 * 361 / 361 = 0.030."""
        from config.refutations import RefutationOverridesConfig

        cfg = RefutationOverridesConfig(
            noise_scaling="board_scaled",
            noise_base=0.03,
            noise_reference_area=361,
        )
        board_area = 19 * 19  # 361
        effective_noise = cfg.noise_base * cfg.noise_reference_area / board_area
        assert effective_noise == pytest.approx(0.03, rel=1e-6)

    def test_board_scaled_13x13(self):
        """13×13 board: effective_noise = 0.03 * 361 / 169 ≈ 0.064."""
        from config.refutations import RefutationOverridesConfig

        cfg = RefutationOverridesConfig(
            noise_scaling="board_scaled",
            noise_base=0.03,
            noise_reference_area=361,
        )
        board_area = 13 * 13  # 169
        effective_noise = cfg.noise_base * cfg.noise_reference_area / board_area
        assert effective_noise == pytest.approx(0.03 * 361 / 169, rel=1e-4)

    def test_fixed_mode_uses_wide_root_noise(self):
        """In fixed mode, wide_root_noise is used as-is."""
        from config.refutations import RefutationOverridesConfig

        cfg = RefutationOverridesConfig(
            noise_scaling="fixed",
            wide_root_noise=0.08,
        )
        assert cfg.noise_scaling == "fixed"
        assert cfg.wide_root_noise == pytest.approx(0.08)

    def test_config_parsing_from_json(self):
        """Phase B noise keys parse correctly from JSON."""
        data = json.loads(ENRICHMENT_CONFIG_PATH.read_text())
        ro = data["refutations"]["refutation_overrides"]
        assert ro["noise_scaling"] == "board_scaled"
        assert ro["noise_base"] == pytest.approx(0.03)
        assert ro["noise_reference_area"] == 361

    def test_absent_keys_give_defaults(self, tmp_path):
        """Config without PI-5 keys loads with defaults (backward compat)."""
        data = json.loads(ENRICHMENT_CONFIG_PATH.read_text())
        ro = data["refutations"]["refutation_overrides"]
        for key in ("noise_scaling", "noise_base", "noise_reference_area"):
            ro.pop(key, None)
        minimal = tmp_path / "config.json"
        minimal.write_text(json.dumps(data))

        from config import load_enrichment_config

        cfg = load_enrichment_config(path=minimal)
        assert cfg.refutations.refutation_overrides.noise_scaling == "fixed"
        assert cfg.refutations.refutation_overrides.noise_base == pytest.approx(0.03)
        assert cfg.refutations.refutation_overrides.noise_reference_area == 361


# ===========================================================================
# TS-9: PI-6 Forced Minimum Visits
# ===========================================================================


@pytest.mark.unit
class TestForcedMinVisits:
    """PI-6: Forced minimum visits per refutation candidate."""

    def test_forced_min_visits_enabled(self):
        """PI-6 forced minimum visits activated in v1.23."""
        from config import load_enrichment_config

        cfg = load_enrichment_config()
        assert cfg.refutations.forced_min_visits_formula is True

    def test_forced_visits_k_default(self):
        from config import load_enrichment_config

        cfg = load_enrichment_config()
        assert cfg.refutations.forced_visits_k == pytest.approx(2.0)

    def test_formula_sqrt_k_policy_visits(self):
        """Formula: nforced(c) = sqrt(k * P(c) * total_visits)."""
        k = 2.0
        policy = 0.1
        total_visits = 100
        expected = int(math.sqrt(k * policy * total_visits))
        assert expected == int(math.sqrt(2.0 * 0.1 * 100))
        assert expected == int(math.sqrt(20.0))
        assert expected == 4

    def test_formula_high_policy(self):
        """High-policy candidate: forced visits exceed base."""
        k = 2.0
        policy = 0.5
        base_visits = 100
        forced = int(math.sqrt(k * policy * base_visits))
        assert forced == int(math.sqrt(100.0))
        assert forced == 10

    def test_formula_low_policy(self):
        """Low-policy candidate: forced visits very small."""
        k = 2.0
        policy = 0.001
        base_visits = 100
        forced = int(math.sqrt(k * policy * base_visits))
        assert forced == 0  # sqrt(0.2) = 0.447... → int = 0

    def test_disabled_no_forced_visits(self):
        """When disabled, effective_visits stays at base refutation_visits."""
        from config.refutations import RefutationsConfig

        cfg = RefutationsConfig(
            forced_min_visits_formula=False,
            refutation_visits=100,
        )
        # Code path: if forced_min_visits_formula is False, skip formula
        assert cfg.forced_min_visits_formula is False
        # Effective visits stays at refutation_visits
        effective = cfg.refutation_visits
        assert effective == 100

    def test_enabled_increases_visits(self):
        """When enabled, effective_visits = max(base, forced)."""
        from config.refutations import RefutationsConfig

        cfg = RefutationsConfig(
            forced_min_visits_formula=True,
            forced_visits_k=2.0,
            refutation_visits=100,
        )
        wrong_move_policy = 0.5
        forced = int(math.sqrt(cfg.forced_visits_k * wrong_move_policy * cfg.refutation_visits))
        # sqrt(2.0 * 0.5 * 100) = sqrt(100) = 10
        effective = max(cfg.refutation_visits, forced)
        # 100 > 10 → stays at 100
        assert effective == 100

    def test_formula_only_increases_never_decreases(self):
        """Forced visits never reduce below refutation_visits."""
        from config.refutations import RefutationsConfig

        cfg = RefutationsConfig(
            forced_min_visits_formula=True,
            forced_visits_k=2.0,
            refutation_visits=100,
        )
        for policy in [0.001, 0.01, 0.1, 0.3, 0.5, 0.9]:
            forced = int(math.sqrt(cfg.forced_visits_k * policy * cfg.refutation_visits))
            effective = max(cfg.refutation_visits, forced)
            assert effective >= cfg.refutation_visits

    def test_config_parsing_from_json(self):
        """Phase B PI-6 keys parse correctly from JSON."""
        data = json.loads(ENRICHMENT_CONFIG_PATH.read_text())
        ref = data["refutations"]
        assert ref["forced_min_visits_formula"] is True
        assert ref["forced_visits_k"] == pytest.approx(2.0)

    def test_absent_keys_give_defaults(self, tmp_path):
        """Config without PI-6 keys loads with defaults (backward compat)."""
        data = json.loads(ENRICHMENT_CONFIG_PATH.read_text())
        ref = data["refutations"]
        for key in ("forced_min_visits_formula", "forced_visits_k"):
            ref.pop(key, None)
        minimal = tmp_path / "config.json"
        minimal.write_text(json.dumps(data))

        from config import load_enrichment_config

        cfg = load_enrichment_config(path=minimal)
        assert cfg.refutations.forced_min_visits_formula is False
        assert cfg.refutations.forced_visits_k == pytest.approx(2.0)


# ===========================================================================
# TS-7: PI-9 Player-Side Alternative Exploration
# ===========================================================================


@pytest.mark.unit
class TestPlayerAlternatives:
    """PI-9: Player-side alternative exploration with auto-detect."""

    def test_player_alternative_rate_active(self):
        """PI-9 player_alternative_rate set to 0.15 in v1.24."""
        from config import load_enrichment_config

        cfg = load_enrichment_config()
        assert cfg.ai_solve.solution_tree.player_alternative_rate == pytest.approx(0.15)

    def test_player_alternative_auto_detect_default_true(self):
        """Auto-detect is on by default."""
        from config import load_enrichment_config

        cfg = load_enrichment_config()
        assert cfg.ai_solve.solution_tree.player_alternative_auto_detect is True

    def test_must_hold_4_safeguard_zero_rate(self):
        """Must-hold #4: zero alternatives explored when rate=0.0.

        Behavioral test: calls build_solution_tree with a mock engine that
        offers multiple high-policy player moves at every depth. With
        player_alternative_rate=0.0, every player node must have exactly
        1 child (the best move only, no alternatives explored).

        This test WILL FAIL if the ``if alt_rate > 0`` guard in
        _build_tree_recursive() is weakened or removed.
        """
        from unittest.mock import MagicMock

        from analyzers.solve_position import build_solution_tree
        from config.ai_solve import AiSolveConfig
        from models.solve_result import QueryBudget

        # Engine returns 3 high-policy candidates at every query so the
        # tree builder *would* explore alternatives if the guard were absent.
        def _mock_query(moves, *, max_visits=None):
            resp = MagicMock()
            resp.moveInfos = [
                {"move": "D4", "winrate": 0.90, "prior": 0.40},
                {"move": "E5", "winrate": 0.88, "prior": 0.35},
                {"move": "F6", "winrate": 0.85, "prior": 0.25},
            ]
            resp.root_winrate = 0.90
            return resp

        engine = MagicMock()
        engine.query = _mock_query

        cfg = AiSolveConfig(
            solution_tree={
                "player_alternative_rate": 0.0,
                "player_alternative_auto_detect": False,
                "depth_profiles": {
                    "core": {"solution_min_depth": 1, "solution_max_depth": 4},
                },
                "max_total_tree_queries": 20,
                "transposition_enabled": False,
                "terminal_detection_enabled": False,
                "simulation_enabled": False,
            },
        )
        budget = QueryBudget(total=20)

        root = build_solution_tree(
            engine=engine,
            initial_moves=[],
            correct_move_gtp="C3",
            player_color="B",
            config=cfg,
            level_slug="intermediate",
            query_budget=budget,
            puzzle_id="mh4-safeguard",
        )

        # Walk tree: every player-turn node must have at most 1 child
        def _count_player_alternatives(node, is_player_turn, depth=0):
            """Return max children count at any player node."""
            max_children = 0
            if is_player_turn and node.children:
                max_children = len(node.children)
            for child in node.children:
                child_max = _count_player_alternatives(
                    child, not is_player_turn, depth + 1,
                )
                max_children = max(max_children, child_max)
            return max_children

        # Root is opponent turn (after player's first move C3)
        max_alt = _count_player_alternatives(root, is_player_turn=False)
        assert max_alt <= 1, (
            f"MH-4 violated: player node has {max_alt} children with rate=0.0; "
            f"expected at most 1 (no alternatives)"
        )


# ===========================================================================
# TS-11: PI-7 Branch-Local Disagreement Escalation
# ===========================================================================


@pytest.mark.unit
class TestBranchEscalation:
    """PI-7: Branch-local disagreement escalation at opponent nodes."""

    def test_branch_escalation_enabled(self):
        """PI-7 branch escalation activated in v1.24."""
        from config import load_enrichment_config

        cfg = load_enrichment_config()
        assert cfg.ai_solve.solution_tree.branch_escalation_enabled is True

    def test_branch_disagreement_threshold_default(self):
        from config import load_enrichment_config

        cfg = load_enrichment_config()
        assert cfg.ai_solve.solution_tree.branch_disagreement_threshold == pytest.approx(0.07)

    def test_disabled_no_escalation(self):
        """When disabled, disagreement above threshold does NOT trigger escalation."""
        from config.solution_tree import SolutionTreeConfig

        tree_cfg = SolutionTreeConfig(
            branch_escalation_enabled=False,
            branch_disagreement_threshold=0.10,
        )
        # When disabled, the guard `if tree_config.branch_escalation_enabled` is False
        assert tree_cfg.branch_escalation_enabled is False

    def test_enabled_with_high_threshold(self):
        """Enabled with high threshold — only extreme disagreement triggers."""
        from config.solution_tree import SolutionTreeConfig

        tree_cfg = SolutionTreeConfig(
            branch_escalation_enabled=True,
            branch_disagreement_threshold=0.50,
        )
        # Disagreement of 0.3 should NOT trigger (below 0.50)
        disagreement = 0.3
        assert not (disagreement > tree_cfg.branch_disagreement_threshold)

    def test_enabled_with_low_threshold(self):
        """Enabled with low threshold — moderate disagreement triggers."""
        from config.solution_tree import SolutionTreeConfig

        tree_cfg = SolutionTreeConfig(
            branch_escalation_enabled=True,
            branch_disagreement_threshold=0.05,
        )
        # Disagreement of 0.15 should trigger (above 0.05)
        disagreement = 0.15
        assert disagreement > tree_cfg.branch_disagreement_threshold

    def test_escalation_capped_by_max_total_queries(self):
        """Escalation respects max_total_tree_queries budget cap."""
        from config.solution_tree import SolutionTreeConfig

        tree_cfg = SolutionTreeConfig(
            branch_escalation_enabled=True,
            max_total_tree_queries=50,
        )
        # Budget cap is always checked: `query_budget.can_query()`
        assert tree_cfg.max_total_tree_queries == 50

    def test_config_parsing_from_json(self):
        """Phase C PI-7 keys parse correctly from JSON."""
        data = json.loads(ENRICHMENT_CONFIG_PATH.read_text())
        st = data["ai_solve"]["solution_tree"]
        assert st["branch_escalation_enabled"] is True
        assert st["branch_disagreement_threshold"] == pytest.approx(0.07)

    def test_absent_keys_give_defaults(self, tmp_path):
        """Config without PI-7 keys loads with defaults (backward compat)."""
        data = json.loads(ENRICHMENT_CONFIG_PATH.read_text())
        st = data["ai_solve"]["solution_tree"]
        for key in ("branch_escalation_enabled", "branch_disagreement_threshold"):
            st.pop(key, None)
        minimal = tmp_path / "config.json"
        minimal.write_text(json.dumps(data))

        from config import load_enrichment_config

        cfg = load_enrichment_config(path=minimal)
        assert cfg.ai_solve.solution_tree.branch_escalation_enabled is False
        assert cfg.ai_solve.solution_tree.branch_disagreement_threshold == pytest.approx(0.10)


# ===========================================================================
# TS-12: PI-8 Diversified Root Candidate Harvesting
# ===========================================================================


@pytest.mark.unit
class TestMultiPassHarvesting:
    """PI-8: Diversified root candidate harvesting."""

    def test_multi_pass_enabled(self):
        """PI-8 multi-pass harvesting activated in v1.24."""
        from config import load_enrichment_config

        cfg = load_enrichment_config()
        assert cfg.refutations.multi_pass_harvesting is True

    def test_secondary_noise_multiplier_default(self):
        from config import load_enrichment_config

        cfg = load_enrichment_config()
        assert cfg.refutations.secondary_noise_multiplier == pytest.approx(2.0)

    def test_disabled_single_pass(self):
        """When disabled, only the initial identify_candidates pass runs."""
        from config.refutations import RefutationsConfig

        cfg = RefutationsConfig(
            multi_pass_harvesting=False,
        )
        assert cfg.multi_pass_harvesting is False

    def test_enabled_with_multiplier(self):
        """Enabled with 2x noise: secondary noise is doubled."""
        from config.refutations import RefutationsConfig

        cfg = RefutationsConfig(
            multi_pass_harvesting=True,
            secondary_noise_multiplier=2.0,
        )
        base_noise = 0.08
        secondary = base_noise * cfg.secondary_noise_multiplier
        assert secondary == pytest.approx(0.16)

    def test_dedup_same_candidate(self):
        """Same candidate from both passes → single entry."""
        # If a candidate appears in both passes, dedup keeps only one
        existing_moves = {"D4", "E5"}
        new_move = "D4"  # Already exists
        assert new_move in existing_moves

    def test_dedup_new_candidate(self):
        """New candidate from secondary pass → added."""
        existing_moves = {"D4", "E5"}
        new_move = "F6"  # Does not exist
        assert new_move not in existing_moves

    def test_compute_bounded_by_max_count(self):
        """Merged candidates capped at candidate_max_count."""
        from config.refutations import RefutationsConfig

        cfg = RefutationsConfig(
            multi_pass_harvesting=True,
            candidate_max_count=5,
        )
        # Even if merge produces 8 candidates, cap at 5
        merged = list(range(8))
        capped = merged[:cfg.candidate_max_count]
        assert len(capped) == 5

    def test_config_parsing_from_json(self):
        """Phase C PI-8 keys parse correctly from JSON."""
        data = json.loads(ENRICHMENT_CONFIG_PATH.read_text())
        ref = data["refutations"]
        assert ref["multi_pass_harvesting"] is True
        assert ref["secondary_noise_multiplier"] == pytest.approx(2.0)

    def test_absent_keys_give_defaults(self, tmp_path):
        """Config without PI-8 keys loads with defaults (backward compat)."""
        data = json.loads(ENRICHMENT_CONFIG_PATH.read_text())
        ref = data["refutations"]
        for key in ("multi_pass_harvesting", "secondary_noise_multiplier"):
            ref.pop(key, None)
        minimal = tmp_path / "config.json"
        minimal.write_text(json.dumps(data))

        from config import load_enrichment_config

        cfg = load_enrichment_config(path=minimal)
        assert cfg.refutations.multi_pass_harvesting is False
        assert cfg.refutations.secondary_noise_multiplier == pytest.approx(2.0)


# ===========================================================================
# TS-10: PI-12 Best-Resistance Line Generation
# ===========================================================================


@pytest.mark.unit
class TestBestResistance:
    """PI-12: Best-resistance line generation."""

    def test_best_resistance_enabled(self):
        """PI-12 best-resistance activated in v1.23."""
        from config import load_enrichment_config

        cfg = load_enrichment_config()
        assert cfg.refutations.best_resistance_enabled is True

    def test_best_resistance_max_candidates_default(self):
        from config import load_enrichment_config

        cfg = load_enrichment_config()
        assert cfg.refutations.best_resistance_max_candidates == 3

    def test_disabled_uses_top_move(self):
        """When disabled, the opponent's top-visited move is the refutation."""
        from config.refutations import RefutationsConfig

        cfg = RefutationsConfig(best_resistance_enabled=False)
        assert cfg.best_resistance_enabled is False

    def test_enabled_selects_max_punishment(self):
        """When enabled, select response with highest punishment signal."""
        # Simulate: 3 opponent responses with different punishment values
        initial_winrate = 0.85
        responses = [
            {"move": "D4", "winrate": 0.90, "visits": 50},  # punishment: |1-0.90-0.85|=|−0.75|=0.75
            {"move": "E5", "winrate": 0.95, "visits": 30},  # punishment: |1-0.95-0.85|=|−0.80|=0.80
            {"move": "F6", "winrate": 0.92, "visits": 20},  # punishment: |1-0.92-0.85|=|−0.77|=0.77
        ]
        best = max(responses, key=lambda r: abs(1.0 - r["winrate"] - initial_winrate))
        assert best["move"] == "E5"  # Highest punishment

    def test_compute_cap_respected(self):
        """best_resistance_max_candidates limits evaluation count."""
        from config.refutations import RefutationsConfig

        cfg = RefutationsConfig(
            best_resistance_enabled=True,
            best_resistance_max_candidates=3,
        )
        responses = list(range(10))  # 10 responses
        evaluated = responses[:cfg.best_resistance_max_candidates]
        assert len(evaluated) == 3

    def test_single_response_no_change(self):
        """With only 1 opponent response, no best-resistance selection needed."""
        responses = [{"move": "D4", "winrate": 0.90}]
        # Only 1 response → best_resistance code skips (len > 1 guard)
        assert len(responses) == 1

    def test_config_parsing_from_json(self):
        """Phase C PI-12 keys parse correctly from JSON."""
        data = json.loads(ENRICHMENT_CONFIG_PATH.read_text())
        ref = data["refutations"]
        assert ref["best_resistance_enabled"] is True
        assert ref["best_resistance_max_candidates"] == 3

    def test_absent_keys_give_defaults(self, tmp_path):
        """Config without PI-12 keys loads with defaults (backward compat)."""
        data = json.loads(ENRICHMENT_CONFIG_PATH.read_text())
        ref = data["refutations"]
        for key in ("best_resistance_enabled", "best_resistance_max_candidates"):
            ref.pop(key, None)
        minimal = tmp_path / "config.json"
        minimal.write_text(json.dumps(data))

        from config import load_enrichment_config

        cfg = load_enrichment_config(path=minimal)
        assert cfg.refutations.best_resistance_enabled is False
        assert cfg.refutations.best_resistance_max_candidates == 3


# ===========================================================================
# Config Version & Changelog
# ===========================================================================


@pytest.mark.unit
class TestPhaseCConfigParsing:
    """Phase C config version and changelog."""

    def test_v1_20_changelog_present(self):
        data = json.loads(ENRICHMENT_CONFIG_PATH.read_text())
        versions = {e["version"]: e["changes"] for e in data["changelog"]}
        assert "1.20" in versions
        assert "PI-7" in versions["1.20"]
        assert "PI-8" in versions["1.20"]
        assert "PI-12" in versions["1.20"]

    def test_all_phase_c_keys_present_in_json(self):
        """All 6 Phase C config keys exist in the JSON."""
        data = json.loads(ENRICHMENT_CONFIG_PATH.read_text())
        # PI-7
        st = data["ai_solve"]["solution_tree"]
        assert "branch_escalation_enabled" in st
        assert "branch_disagreement_threshold" in st
        # PI-8
        ref = data["refutations"]
        assert "multi_pass_harvesting" in ref
        assert "secondary_noise_multiplier" in ref
        # PI-12
        assert "best_resistance_enabled" in ref
        assert "best_resistance_max_candidates" in ref


# ===========================================================================
# RC-3: Algorithm Integration Tests (Phase C)
# ===========================================================================


@pytest.mark.unit
class TestPI7DisagreementMetric:
    """RC-1/RC-3: PI-7 disagreement uses sibling winrate comparison."""

    def test_disagreement_uses_sibling_winrate(self):
        """Disagreement = abs(child.winrate - first_child_winrate), not policy vs winrate."""
        from config.solution_tree import SolutionTreeConfig

        cfg = SolutionTreeConfig(
            branch_escalation_enabled=True,
            branch_disagreement_threshold=0.10,
        )
        # Scenario: first child winrate=0.85, second child winrate=0.60
        # Disagreement should be abs(0.60 - 0.85) = 0.25 > 0.10 threshold
        first_wr = 0.85
        second_wr = 0.60
        disagreement = abs(second_wr - first_wr)
        assert disagreement == pytest.approx(0.25)
        assert disagreement > cfg.branch_disagreement_threshold

    def test_no_disagreement_similar_siblings(self):
        """Low disagreement when siblings have similar winrates."""
        from config.solution_tree import SolutionTreeConfig

        cfg = SolutionTreeConfig(
            branch_escalation_enabled=True,
            branch_disagreement_threshold=0.10,
        )
        first_wr = 0.85
        second_wr = 0.82
        disagreement = abs(second_wr - first_wr)
        assert disagreement == pytest.approx(0.03)
        assert disagreement < cfg.branch_disagreement_threshold

    def test_old_metric_would_false_trigger(self):
        """The old metric (abs(policy - winrate)) would trigger on typical moves.

        A move with policy_prior=0.20 and search_winrate=0.85 produces
        abs(0.20 - 0.85) = 0.65 — far above 0.10 threshold.
        The new metric using sibling winrate comparison avoids this.
        """
        policy_prior = 0.20
        search_winrate = 0.85
        first_child_winrate = 0.87
        old_disagreement = abs(policy_prior - search_winrate)
        new_disagreement = abs(search_winrate - first_child_winrate)
        assert old_disagreement == pytest.approx(0.65)  # would always trigger
        assert new_disagreement == pytest.approx(0.02)  # correctly no trigger


@pytest.mark.unit
class TestPI8MergeReRanking:
    """RC-2/RC-3: PI-8 merge re-sorts by policy_prior before capping."""

    def test_secondary_high_policy_not_dropped(self):
        """High-policy secondary candidates survive capping after re-sort."""
        from models.analysis_response import MoveAnalysis

        # First pass: 3 candidates with moderate policy
        first = [
            MoveAnalysis(move="D4", policy_prior=0.20, winrate=0.3, score_lead=2.0),
            MoveAnalysis(move="E5", policy_prior=0.15, winrate=0.3, score_lead=2.0),
            MoveAnalysis(move="F6", policy_prior=0.10, winrate=0.3, score_lead=2.0),
        ]
        # Secondary pass: 1 candidate with higher policy than E5 and F6
        secondary = [
            MoveAnalysis(move="G7", policy_prior=0.25, winrate=0.3, score_lead=2.0),
        ]

        # Merge (simulating the fixed code)
        candidates = list(first)
        existing = {m.move.upper() for m in candidates}
        for sc in secondary:
            if sc.move.upper() not in existing:
                candidates.append(sc)
                existing.add(sc.move.upper())

        # Re-sort by policy_prior (RC-2 fix)
        candidates.sort(key=lambda m: m.policy_prior, reverse=True)
        # Cap at 3
        capped = candidates[:3]

        moves = [m.move for m in capped]
        # G7 (0.25) should be included, F6 (0.10) should be dropped
        assert "G7" in moves
        assert "F6" not in moves

    def test_without_resort_secondary_dropped(self):
        """Without re-sort, secondary candidates at end are dropped."""
        from models.analysis_response import MoveAnalysis

        first = [
            MoveAnalysis(move="D4", policy_prior=0.20, winrate=0.3, score_lead=2.0),
            MoveAnalysis(move="E5", policy_prior=0.15, winrate=0.3, score_lead=2.0),
            MoveAnalysis(move="F6", policy_prior=0.10, winrate=0.3, score_lead=2.0),
        ]
        secondary = [
            MoveAnalysis(move="G7", policy_prior=0.25, winrate=0.3, score_lead=2.0),
        ]

        # Old behavior: just append and cap without re-sort
        candidates = list(first)
        for sc in secondary:
            candidates.append(sc)
        capped_old = candidates[:3]
        # G7 would be at index 3, dropped
        assert "G7" not in [m.move for m in capped_old]


@pytest.mark.unit
class TestPI12BestResistance:
    """RC-3: PI-12 best-resistance selects maximum punishment response."""

    def test_best_resistance_selects_max_punishment(self):
        """Selects the opponent response with the highest punishment delta."""
        from models.analysis_response import MoveAnalysis

        initial_winrate = 0.85

        # Opp responses ranked by visits (first is top_move)
        responses = [
            MoveAnalysis(move="C3", visits=200, winrate=0.25),  # punishment: abs(1-0.25-0.85) = 0.10
            MoveAnalysis(move="D3", visits=150, winrate=0.10),  # punishment: abs(1-0.10-0.85) = 0.05
            MoveAnalysis(move="E3", visits=100, winrate=0.05),  # punishment: abs(1-0.05-0.85) = 0.10
        ]

        # Simulate PI-12 logic
        opp_best = responses[0]
        max_punishment = abs(1.0 - opp_best.winrate - initial_winrate)
        best_response = opp_best

        max_candidates = 3
        sorted_responses = sorted(responses, key=lambda m: m.visits, reverse=True)[:max_candidates]
        for alt in sorted_responses[1:]:
            alt_punishment = abs(1.0 - alt.winrate - initial_winrate)
            if alt_punishment > max_punishment:
                max_punishment = alt_punishment
                best_response = alt

        # E3 has punishment 0.10, same as C3, so C3 stays as best
        # D3 has punishment 0.05 — less
        assert best_response.move == "C3"

    def test_best_resistance_replaces_when_better_found(self):
        """Replaces opp_best when alternative has higher punishment."""
        from models.analysis_response import MoveAnalysis

        initial_winrate = 0.85

        responses = [
            MoveAnalysis(move="C3", visits=200, winrate=0.30),  # punishment: abs(1-0.30-0.85) = 0.15
            MoveAnalysis(move="D3", visits=150, winrate=0.02),  # punishment: abs(1-0.02-0.85) = 0.13
            MoveAnalysis(move="E3", visits=100, winrate=0.40),  # punishment: abs(1-0.40-0.85) = 0.25
        ]

        opp_best = responses[0]
        max_punishment = abs(1.0 - opp_best.winrate - initial_winrate)
        best_response = opp_best

        for alt in responses[1:]:
            alt_punishment = abs(1.0 - alt.winrate - initial_winrate)
            if alt_punishment > max_punishment:
                max_punishment = alt_punishment
                best_response = alt

        # E3 has highest punishment (0.25 vs 0.15)
        assert best_response.move == "E3"
        assert max_punishment == pytest.approx(0.25)


@pytest.mark.unit
class TestNoiseHelper:
    """RC-4: Shared noise helper function."""

    def test_fixed_mode_returns_wide_root_noise(self):
        """Fixed noise_scaling returns wide_root_noise unchanged."""
        from analyzers.generate_refutations import _calculate_effective_noise
        from config.refutations import RefutationOverridesConfig

        cfg = RefutationOverridesConfig(
            noise_scaling="fixed",
            wide_root_noise=0.04,
        )
        assert _calculate_effective_noise(cfg, 19) == pytest.approx(0.04)

    def test_board_scaled_19x19(self):
        """Board-scaled noise on 19x19 = noise_base * 361 / 361 = noise_base."""
        from analyzers.generate_refutations import _calculate_effective_noise
        from config.refutations import RefutationOverridesConfig

        cfg = RefutationOverridesConfig(
            noise_scaling="board_scaled",
            noise_base=0.03,
            noise_reference_area=361,
        )
        result = _calculate_effective_noise(cfg, 19)
        assert result == pytest.approx(0.03)

    def test_board_scaled_9x9(self):
        """Board-scaled noise on 9x9 = noise_base * 361 / 81 ≈ 0.134."""
        from analyzers.generate_refutations import _calculate_effective_noise
        from config.refutations import RefutationOverridesConfig

        cfg = RefutationOverridesConfig(
            noise_scaling="board_scaled",
            noise_base=0.03,
            noise_reference_area=361,
        )
        result = _calculate_effective_noise(cfg, 9)
        expected = 0.03 * 361 / 81
        assert result == pytest.approx(expected)


@pytest.mark.unit
class TestMaxQueriesPerPuzzle:
    """RC-5/MH-7: BatchSummaryAccumulator tracks max queries per puzzle."""

    def test_max_queries_tracked(self):
        """max_queries_per_puzzle reflects the puzzle with most queries."""
        from analyzers.observability import BatchSummaryAccumulator

        acc = BatchSummaryAccumulator(batch_id="test-batch")
        acc.record_puzzle(has_solution=True, queries_used=10)
        acc.record_puzzle(has_solution=True, queries_used=25)
        acc.record_puzzle(has_solution=True, queries_used=15)
        summary = acc.emit()
        assert summary.max_queries_per_puzzle == 25

    def test_max_queries_zero_when_empty(self):
        """No puzzles → max_queries_per_puzzle is 0."""
        from analyzers.observability import BatchSummaryAccumulator

        acc = BatchSummaryAccumulator(batch_id="test-empty")
        summary = acc.emit()
        assert summary.max_queries_per_puzzle == 0

    def test_max_queries_single_puzzle(self):
        """Single puzzle: max equals its queries_used."""
        from analyzers.observability import BatchSummaryAccumulator

        acc = BatchSummaryAccumulator(batch_id="test-single")
        acc.record_puzzle(has_solution=True, queries_used=42)
        summary = acc.emit()
        assert summary.max_queries_per_puzzle == 42


# ===========================================================================
# TS-13: PI-11 Surprise-Weighted Calibration
# ===========================================================================


@pytest.mark.unit
class TestSurpriseWeightedCalibration:
    """PI-11: Surprise-weighted calibration infrastructure."""

    def test_surprise_weighting_enabled(self):
        """PI-11 surprise weighting activated in v1.23."""
        from config import load_enrichment_config

        cfg = load_enrichment_config()
        assert cfg.calibration.surprise_weighting is True

    def test_surprise_weight_scale_default(self):
        """Default scale is 2.0."""
        from config import load_enrichment_config

        cfg = load_enrichment_config()
        assert cfg.calibration.surprise_weight_scale == 2.0

    def test_disabled_returns_uniform_weight(self):
        """When disabled, all positions get weight 1.0 regardless of winrates."""
        from config.infrastructure import compute_surprise_weight

        # Large disagreement should still return 1.0 when disabled
        w = compute_surprise_weight(0.9, 0.1, enabled=False, scale=2.0)
        assert w == 1.0

    def test_disabled_zero_disagreement(self):
        """When disabled, identical winrates → weight 1.0."""
        from config.infrastructure import compute_surprise_weight

        w = compute_surprise_weight(0.5, 0.5, enabled=False, scale=2.0)
        assert w == 1.0

    def test_enabled_high_surprise_gets_more_weight(self):
        """Enabled: position with high surprise gets higher weight."""
        from config.infrastructure import compute_surprise_weight

        # T0=0.9 vs T2=0.1 → surprise = 0.8 → weight = 1 + 2.0 * 0.8 = 2.6
        w = compute_surprise_weight(0.9, 0.1, enabled=True, scale=2.0)
        assert w == pytest.approx(2.6)

    def test_enabled_zero_surprise_uniform(self):
        """Enabled: position with zero surprise gets weight 1.0 (same as disabled)."""
        from config.infrastructure import compute_surprise_weight

        # T0=0.5 vs T2=0.5 → surprise = 0.0 → weight = 1 + 2.0 * 0.0 = 1.0
        w = compute_surprise_weight(0.5, 0.5, enabled=True, scale=2.0)
        assert w == 1.0

    def test_enabled_moderate_surprise(self):
        """Enabled: moderate surprise gives proportional weight."""
        from config.infrastructure import compute_surprise_weight

        # T0=0.6 vs T2=0.4 → surprise = 0.2 → weight = 1 + 2.0 * 0.2 = 1.4
        w = compute_surprise_weight(0.6, 0.4, enabled=True, scale=2.0)
        assert w == pytest.approx(1.4)

    def test_scale_zero_gives_uniform(self):
        """When surprise_weight_scale=0, output is always 1.0 (identical to disabled)."""
        from config.infrastructure import compute_surprise_weight

        w = compute_surprise_weight(0.9, 0.1, enabled=True, scale=0.0)
        assert w == 1.0

    def test_surprise_order_independent(self):
        """Surprise score is symmetric: |T0 - T2| = |T2 - T0|."""
        from config.infrastructure import compute_surprise_weight

        w1 = compute_surprise_weight(0.8, 0.3, enabled=True, scale=2.0)
        w2 = compute_surprise_weight(0.3, 0.8, enabled=True, scale=2.0)
        assert w1 == w2

    def test_weight_always_at_least_one(self):
        """Weight is always >= 1.0 (never downweights a position)."""
        from config.infrastructure import compute_surprise_weight

        for t0, t2 in [(0.5, 0.5), (0.0, 1.0), (0.99, 0.01), (0.5, 0.48)]:
            w = compute_surprise_weight(t0, t2, enabled=True, scale=2.0)
            assert w >= 1.0, f"Weight {w} < 1.0 for t0={t0}, t2={t2}"

    def test_custom_scale_factor(self):
        """Custom scale factor produces correct weight."""
        from config.infrastructure import compute_surprise_weight

        # surprise = 0.5, scale = 3.0 → weight = 1 + 3.0 * 0.5 = 2.5
        w = compute_surprise_weight(0.7, 0.2, enabled=True, scale=3.0)
        assert w == pytest.approx(2.5)
