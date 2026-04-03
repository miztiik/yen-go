"""Tests for config infrastructure: loading, parsing, schema validation, round-trip, backward compat.

Consolidated from:
- test_enrichment_config.py (TestConfigLoadsFromFile, TestRefutationPvCap, TestExistingLabHardcodedIdsRemoved)
- test_deep_enrich_config.py (TestDeepEnrichModel)
- test_tsumego_config.py (TestConfigLoads)
- test_teaching_comments_config.py (TestTeachingCommentsConfigLoader)
- test_ai_solve_config.py (TestAiSolveConfigParsesFromJson, TestAiSolveMissingKeyBackwardCompat,
                           TestAiSolveModelRoundTrip, TestAiSolveValidators, TestKMConfigExtension)
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from config import (
    EnrichmentConfig,
    clear_cache,
    load_enrichment_config,
    load_puzzle_levels,
)
from config.analysis import DeepEnrichConfig
from config.teaching import (
    TeachingCommentEntry,
    TeachingCommentsConfig,
    load_teaching_comments_config,
)

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
class TestConfigLoadsFromFile:
    """Test that config/katago-enrichment.json loads and validates."""

    def test_config_file_exists(self):
        assert ENRICHMENT_CONFIG_PATH.exists(), (
            f"config/katago-enrichment.json not found at {ENRICHMENT_CONFIG_PATH}"
        )

    def test_config_loads_valid_json(self):
        data = json.loads(ENRICHMENT_CONFIG_PATH.read_text())
        assert isinstance(data, dict)
        assert "schema_version" in data

    def test_config_loads_via_loader(self):
        from config import load_enrichment_config
        cfg = load_enrichment_config()
        assert cfg is not None
        assert cfg.version == "1.28"


@pytest.mark.unit
class TestRefutationPvCap:
    """P0.4: Refutation PV cap must be config-driven, not hardcoded."""

    def test_config_has_max_pv_length(self):
        """RefutationsConfig has max_pv_length field."""
        from config.refutations import RefutationsConfig
        cfg = RefutationsConfig()
        assert hasattr(cfg, "max_pv_length")
        assert cfg.max_pv_length == 4  # default matches old hardcode

    def test_config_max_pv_length_customizable(self):
        """max_pv_length can be set to 8 for dan puzzles."""
        from config.refutations import RefutationsConfig
        cfg = RefutationsConfig(max_pv_length=8)
        assert cfg.max_pv_length == 8

    def test_config_max_pv_length_validated(self):
        """max_pv_length must be 1-20."""
        from config.refutations import RefutationsConfig
        with pytest.raises(Exception):
            RefutationsConfig(max_pv_length=0)
        with pytest.raises(Exception):
            RefutationsConfig(max_pv_length=25)

    def test_loaded_config_has_max_pv_length(self):
        """katago-enrichment.json includes max_pv_length."""
        from config import load_enrichment_config
        cfg = load_enrichment_config()
        assert cfg.refutations.max_pv_length >= 1


@pytest.mark.unit
class TestExistingLabHardcodedIdsRemoved:
    """Verify no hardcoded level IDs remain in estimate_difficulty.py."""

    def test_no_stale_hardcoded_ids(self):
        """estimate_difficulty.py must NOT contain hardcoded stale level IDs
        (100, 110, 120, ... 180 pattern from the old code)."""
        src = (_LAB / "analyzers" / "estimate_difficulty.py").read_text()
        # The old code had "id": 100, "id": 110, etc.
        # After fix, it should load from config, not have a LEVELS list
        assert '"id": 100' not in src, "Stale hardcoded level ID 100 found"
        assert '"id": 170' not in src, "Stale hardcoded level ID 170 found"
        assert '"id": 180' not in src, "Stale hardcoded level ID 180 found"

    def test_loads_levels_from_config(self):
        """Level loading uses config-driven levels from puzzle-levels.json."""
        levels = load_puzzle_levels()
        assert len(levels) == 9
        assert levels["novice"] == 110
        assert levels["expert"] == 230


# ---------------------------------------------------------------------------
# From test_deep_enrich_config.py
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDeepEnrichModel:
    """DeepEnrichConfig pydantic model validation."""

    def test_default_values(self) -> None:
        """DeepEnrichConfig has sensible defaults (with explicit model)."""
        dec = DeepEnrichConfig(model="b18c384")
        assert dec.enabled is True
        assert dec.model == "b18c384"
        assert dec.visits == 2000
        assert dec.root_num_symmetries_to_sample == 4
        assert dec.referee_symmetries == 8
        assert dec.max_time == 0
        assert dec.escalate_to_referee is True
        assert dec.tiebreaker_tolerance == 0.05

    def test_visits_minimum(self) -> None:
        """visits must be >= 100."""
        with pytest.raises(Exception):
            DeepEnrichConfig(model="b18c384", visits=50)

    def test_symmetries_range(self) -> None:
        """symmetries must be 1-8."""
        DeepEnrichConfig(model="b18c384", root_num_symmetries_to_sample=1)
        DeepEnrichConfig(model="b18c384", root_num_symmetries_to_sample=8)
        with pytest.raises(Exception):
            DeepEnrichConfig(model="b18c384", root_num_symmetries_to_sample=0)
        with pytest.raises(Exception):
            DeepEnrichConfig(model="b18c384", root_num_symmetries_to_sample=9)

    def test_enrichment_config_includes_deep_enrich(self) -> None:
        """EnrichmentConfig has deep_enrich field."""
        ec = load_enrichment_config()
        assert isinstance(ec.deep_enrich, DeepEnrichConfig)


# ---------------------------------------------------------------------------
# From test_tsumego_config.py
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestConfigLoads:
    """Config file exists and is parseable."""

    def test_cfg_file_exists(self):
        assert _CFG_PATH.exists(), f"Missing: {_CFG_PATH}"

    def test_cfg_parses_without_error(self):

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
                    if "#" in value:
                        value = value[: value.index("#")].strip()
                    result[key] = value
            return result

        settings = _parse_cfg(_CFG_PATH)
        assert isinstance(settings, dict)
        assert len(settings) > 0, "Config should have at least one setting"


# ---------------------------------------------------------------------------
# From test_teaching_comments_config.py
# ---------------------------------------------------------------------------


class TestTeachingCommentsConfigLoader:
    """Tests for load_teaching_comments_config()."""

    def test_loads_real_config(self):
        cfg = load_teaching_comments_config()
        assert isinstance(cfg, TeachingCommentsConfig)

        # Validate the checked-in config file directly against the Pydantic schema.
        config_path = Path(__file__).resolve().parents[3] / "config" / "teaching-comments.json"
        raw_json = config_path.read_text(encoding="utf-8")
        validated = TeachingCommentsConfig.model_validate_json(raw_json)
        assert isinstance(validated, TeachingCommentsConfig)

    def test_all_28_tags_present(self):
        cfg = load_teaching_comments_config()
        assert len(cfg.correct_move_comments) == 28

    def test_each_tag_has_required_fields(self):
        cfg = load_teaching_comments_config()
        for slug, entry in cfg.correct_move_comments.items():
            assert entry.comment, f"{slug} missing comment"
            assert entry.hint_text, f"{slug} missing hint_text"
            assert entry.min_confidence in ("HIGH", "CERTAIN"), (
                f"{slug} has invalid min_confidence: {entry.min_confidence}"
            )

    def test_joseki_fuseki_use_certain(self):
        cfg = load_teaching_comments_config()
        assert cfg.correct_move_comments["joseki"].min_confidence == "CERTAIN"
        assert cfg.correct_move_comments["fuseki"].min_confidence == "CERTAIN"

    def test_dead_shapes_has_alias_comments(self):
        cfg = load_teaching_comments_config()
        entry = cfg.correct_move_comments["dead-shapes"]
        assert entry.alias_comments is not None
        assert "bent-four" in entry.alias_comments
        assert "bulky-five" in entry.alias_comments
        assert "rabbity-six" in entry.alias_comments
        assert "l-group" in entry.alias_comments
        assert "straight-three" in entry.alias_comments
        assert "flower-six" in entry.alias_comments
        assert "table shape" in entry.alias_comments
        assert "pyramid four" in entry.alias_comments
        assert "crossed five" in entry.alias_comments
        assert len(entry.alias_comments) == 9

    def test_tesuji_has_alias_comments(self):
        cfg = load_teaching_comments_config()
        entry = cfg.correct_move_comments["tesuji"]
        assert entry.alias_comments is not None
        assert "hane" in entry.alias_comments
        assert "crane's nest" in entry.alias_comments
        assert "wedge" in entry.alias_comments
        assert "tiger's mouth" in entry.alias_comments
        assert "kosumi" in entry.alias_comments
        assert "keima" in entry.alias_comments
        assert "warikomi" in entry.alias_comments
        assert "nose tesuji" in entry.alias_comments
        assert "descent" in entry.alias_comments
        assert "sagari" in entry.alias_comments
        assert "atekomi" in entry.alias_comments
        assert len(entry.alias_comments) == 11

    def test_wrong_move_templates_present(self):
        cfg = load_teaching_comments_config()
        wm = cfg.wrong_move_comments
        conditions = [t.condition for t in wm.templates]
        assert "immediate_capture" in conditions
        assert "ko_involved" in conditions
        assert "default" in conditions

    def test_delta_annotations_present(self):
        cfg = load_teaching_comments_config()
        da = cfg.wrong_move_comments.delta_annotations
        assert "significant_loss" in da
        assert "moderate_loss" in da
        assert da["significant_loss"].threshold == 0.5
        assert da["moderate_loss"].threshold == 0.2

    def test_comment_max_15_words(self):
        cfg = load_teaching_comments_config()
        for slug, entry in cfg.correct_move_comments.items():
            words = entry.comment.split()
            assert len(words) <= 15, (
                f"{slug} comment exceeds 15 words ({len(words)}): {entry.comment}"
            )

    def test_caching_returns_same_object(self):
        cfg1 = load_teaching_comments_config()
        cfg2 = load_teaching_comments_config()
        assert cfg1 is cfg2

    def test_custom_path(self, tmp_path):
        data = {
            "schema_version": "0.1",
            "correct_move_comments": {
                "test-tag": {
                    "comment": "Test comment for unit test.",
                    "hint_text": "Test Tag",
                    "min_confidence": "HIGH",
                }
            },
            "wrong_move_comments": {
                "templates": [
                    {"condition": "default", "comment": "Wrong."}
                ],
                "delta_annotations": {
                    "significant_loss": {"threshold": 0.5, "template": "Bad."},
                    "moderate_loss": {"threshold": 0.2, "template": "Not great."},
                },
            },
        }
        p = tmp_path / "test-teaching-comments.json"
        p.write_text(json.dumps(data), encoding="utf-8")
        cfg = load_teaching_comments_config(path=p)
        assert len(cfg.correct_move_comments) == 1
        assert cfg.correct_move_comments["test-tag"].hint_text == "Test Tag"

    def test_confidence_enum_validation(self):
        with pytest.raises(Exception):
            TeachingCommentEntry(
                comment="test", hint_text="test", min_confidence="LOW"
            )

    def test_almost_correct_threshold_from_config(self):
        """T14a/MH-5: almost_correct_threshold is read from config."""
        cfg = load_teaching_comments_config()
        assert hasattr(cfg.wrong_move_comments, "almost_correct_threshold")
        assert cfg.wrong_move_comments.almost_correct_threshold == 0.05


# ---------------------------------------------------------------------------
# From test_ai_solve_config.py
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestAiSolveConfigParsesFromJson:
    """Verify ai_solve section in katago-enrichment.json loads correctly."""

    def test_config_json_has_ai_solve_section(self):
        data = json.loads(ENRICHMENT_CONFIG_PATH.read_text())
        assert "ai_solve" in data, "ai_solve section missing from katago-enrichment.json"

    def test_config_version_is_1_28(self):
        data = json.loads(ENRICHMENT_CONFIG_PATH.read_text())
        assert data["schema_version"] == "1.28"

    def test_config_loads_with_ai_solve(self):
        from config import load_enrichment_config
        cfg = load_enrichment_config()
        assert cfg.ai_solve is not None
        assert cfg.version == "1.28"

    def test_ai_solve_has_no_enabled_flag(self):
        """enabled flag was removed — AI-Solve is always active."""
        from config import load_enrichment_config
        cfg = load_enrichment_config()
        assert not hasattr(cfg.ai_solve, "enabled")


@pytest.mark.unit
class TestAiSolveMissingKeyBackwardCompat:
    """Missing ai_solve key → None (backward compatibility)."""

    def test_missing_ai_solve_key_uses_default(self, tmp_path):
        """Config without ai_solve key should load with default AiSolveConfig()."""
        data = json.loads(ENRICHMENT_CONFIG_PATH.read_text())
        del data["ai_solve"]
        minimal = tmp_path / "config.json"
        minimal.write_text(json.dumps(data))

        from config import load_enrichment_config
        cfg = load_enrichment_config(path=minimal)
        assert cfg.ai_solve is not None  # Phase 0: default AiSolveConfig()

    def test_ai_solve_none_does_not_affect_other_sections(self, tmp_path):
        """Removing ai_solve doesn't break existing config sections."""
        data = json.loads(ENRICHMENT_CONFIG_PATH.read_text())
        del data["ai_solve"]
        minimal = tmp_path / "config.json"
        minimal.write_text(json.dumps(data))

        from config import load_enrichment_config
        cfg = load_enrichment_config(path=minimal)
        assert cfg.ownership_thresholds.alive == pytest.approx(0.7)
        assert cfg.deep_enrich.enabled is True
        assert cfg.models.quick.label == "quick"


@pytest.mark.unit
class TestAiSolveModelRoundTrip:
    """Pydantic model round-trips all values (serialize → deserialize)."""

    def test_round_trip_via_model_dump(self):
        from config.ai_solve import AiSolveConfig
        original = AiSolveConfig()
        dumped = original.model_dump()
        restored = AiSolveConfig(**dumped)
        assert restored == original

    def test_round_trip_via_json(self):
        from config.ai_solve import AiSolveConfig
        original = AiSolveConfig()
        json_str = original.model_dump_json()
        restored = AiSolveConfig.model_validate_json(json_str)
        assert restored == original

    def test_full_config_round_trip(self):
        """Full EnrichmentConfig with ai_solve round-trips."""
        from config import load_enrichment_config
        cfg = load_enrichment_config()
        dumped = cfg.model_dump(by_alias=True)
        restored = EnrichmentConfig(**dumped)
        assert restored.ai_solve == cfg.ai_solve
        assert restored.version == cfg.version


@pytest.mark.unit
class TestAiSolveValidators:
    """Pydantic validators enforce constraints."""

    def test_t_good_ge_t_bad_rejected(self):
        from config.ai_solve import AiSolveThresholds
        with pytest.raises(ValueError, match="t_good.*must be < t_bad"):
            AiSolveThresholds(t_good=0.20, t_bad=0.15, t_hotspot=0.30)

    def test_t_bad_ge_t_hotspot_rejected(self):
        from config.ai_solve import AiSolveThresholds
        with pytest.raises(ValueError, match="t_bad.*must be < t_hotspot"):
            AiSolveThresholds(t_good=0.05, t_bad=0.35, t_hotspot=0.30)

    def test_depth_profile_min_gt_max_rejected(self):
        from config.solution_tree import DepthProfile
        with pytest.raises(ValueError, match="solution_min_depth.*solution_max_depth"):
            DepthProfile(solution_min_depth=20, solution_max_depth=10)

    def test_depth_profile_valid(self):
        from config.solution_tree import DepthProfile
        p = DepthProfile(solution_min_depth=3, solution_max_depth=16)
        assert p.solution_min_depth == 3
        assert p.solution_max_depth == 16

    def test_depth_profile_equal_min_max_valid(self):
        from config.solution_tree import DepthProfile
        p = DepthProfile(solution_min_depth=5, solution_max_depth=5)
        assert p.solution_min_depth == p.solution_max_depth


@pytest.mark.unit
class TestKMConfigExtension:
    """T013-T015: KM-01 through KM-04 config parameter validation."""

    def test_km_config_parses_with_new_fields(self):
        """T013: All new KM fields parse from config/katago-enrichment.json."""
        from config import clear_cache, load_enrichment_config
        clear_cache()
        cfg = load_enrichment_config()
        assert cfg.ai_solve is not None
        tree = cfg.ai_solve.solution_tree
        # KM-01
        assert isinstance(tree.simulation_enabled, bool)
        assert isinstance(tree.simulation_verify_visits, int)
        assert tree.simulation_verify_visits > 0
        # KM-02
        assert isinstance(tree.transposition_enabled, bool)
        # G1/G2 terminal detection
        assert isinstance(tree.terminal_detection_enabled, bool)
        # KM-03
        assert isinstance(tree.forced_move_visits, int)
        assert isinstance(tree.forced_move_policy_threshold, float)
        assert 0.0 <= tree.forced_move_policy_threshold <= 1.0
        # KM-04 normalization ceiling
        norm = cfg.difficulty.normalization
        assert norm is not None
        assert hasattr(norm, 'max_resolved_depth_ceiling')
        assert norm.max_resolved_depth_ceiling > 0

    def test_km_config_missing_fields_use_defaults(self):
        """T014: Config without KM fields loads via Pydantic defaults."""
        import tempfile

        from config import clear_cache, load_enrichment_config

        # Load the real config and strip the KM-specific fields
        clear_cache()
        data = json.loads(ENRICHMENT_CONFIG_PATH.read_text(encoding="utf-8"))

        # Strip KM fields from solution_tree
        st = data.get("ai_solve", {}).get("solution_tree", {})
        for key in ["simulation_enabled", "simulation_verify_visits", "forced_move_visits",
                     "forced_move_policy_threshold", "transposition_enabled",
                     "terminal_detection_enabled"]:
            st.pop(key, None)

        # Strip proof_depth from structural_weights
        sw = data.get("difficulty", {}).get("structural_weights", {})
        sw.pop("proof_depth", None)
        # Set weights that sum to 90, so proof_depth default (10) brings total to 100
        sw["solution_depth"] = 35.0
        sw["branch_count"] = 25.0
        sw["local_candidates"] = 18.0
        sw["refutation_count"] = 12.0

        # Strip max_resolved_depth_ceiling from normalization
        norm = data.get("difficulty", {}).get("normalization", {})
        norm.pop("max_resolved_depth_ceiling", None)

        # Write temp config
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
            json.dump(data, f)
            tmp_path = Path(f.name)

        try:
            clear_cache()
            cfg = load_enrichment_config(tmp_path)
            tree = cfg.ai_solve.solution_tree
            # Defaults should be applied
            assert tree.simulation_enabled is True
            assert tree.simulation_verify_visits == 50
            assert tree.transposition_enabled is True
            assert tree.terminal_detection_enabled is True
            assert tree.forced_move_visits == 125
            assert tree.forced_move_policy_threshold == 0.85
        finally:
            tmp_path.unlink(missing_ok=True)
            clear_cache()

    def test_structural_weights_sum_with_proof_depth(self):
        """T015: Rebalanced 5-weight StructuralDifficultyWeights sum = 100."""
        from config.difficulty import StructuralDifficultyWeights
        # Default values should sum to 100
        w = StructuralDifficultyWeights()
        total = w.solution_depth + w.branch_count + w.local_candidates + w.refutation_count + w.proof_depth
        assert abs(total - 100.0) < 0.01

        # Invalid sum should raise
        with pytest.raises(ValueError, match="must sum to 100"):
            StructuralDifficultyWeights(
                solution_depth=40.0,
                branch_count=25.0,
                local_candidates=20.0,
                refutation_count=15.0,
                proof_depth=10.0,  # sum = 110
            )
