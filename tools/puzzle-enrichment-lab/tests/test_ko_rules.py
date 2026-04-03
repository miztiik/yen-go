"""Tests for ko-aware analysis rules routing (Phase S.4, ADR D31).

Verifies that:
- AnalysisRequest emits correct rules and analysisPVLen in KataGo JSON
- build_query_from_sgf resolves rules/PV from ko_type and config
- Default fallback works when no config is provided
- Ko calibration fixtures are properly tagged
"""

from __future__ import annotations

from pathlib import Path

import pytest

_HERE = Path(__file__).resolve().parent
_LAB = _HERE.parent

from analyzers.query_builder import build_query_from_sgf
from config import load_enrichment_config
from config.analysis import KoAnalysisConfig
from models.analysis_request import AnalysisRequest
from models.position import Color, Position, Stone

FIXTURES = Path(__file__).parent / "fixtures"
CALIBRATION_KO = FIXTURES / "calibration" / "ko"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _minimal_position() -> Position:
    """A minimal 9×9 position for testing AnalysisRequest serialisation."""
    return Position(
        board_size=9,
        stones=[Stone(color=Color.BLACK, x=2, y=2), Stone(color=Color.WHITE, x=3, y=3)],
        player_to_move=Color.BLACK,
        komi=0.0,
    )


def _load(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


# ===================================================================
# AnalysisRequest serialisation tests
# ===================================================================


@pytest.mark.unit
class TestAnalysisRequestKoFields:
    """AnalysisRequest.to_katago_json() respects rules and analysis_pv_len."""

    def test_default_rules_is_chinese(self) -> None:
        """Default rules should be 'chinese' (superko)."""
        req = AnalysisRequest(position=_minimal_position())
        payload = req.to_katago_json()
        assert payload["rules"] == "chinese"

    def test_tromp_taylor_rules_emitted(self) -> None:
        """When rules='tromp-taylor', the KataGo JSON uses tromp-taylor."""
        req = AnalysisRequest(position=_minimal_position(), rules="tromp-taylor")
        payload = req.to_katago_json()
        assert payload["rules"] == "tromp-taylor"

    def test_analysis_pv_len_omitted_when_none(self) -> None:
        """analysisPVLen should NOT appear in payload when not set."""
        req = AnalysisRequest(position=_minimal_position(), analysis_pv_len=None)
        payload = req.to_katago_json()
        assert "analysisPVLen" not in payload

    def test_analysis_pv_len_emitted_when_set(self) -> None:
        """analysisPVLen=30 should appear in the KataGo JSON payload."""
        req = AnalysisRequest(position=_minimal_position(), analysis_pv_len=30)
        payload = req.to_katago_json()
        assert payload["analysisPVLen"] == 30

    def test_analysis_pv_len_boundary_1(self) -> None:
        """analysisPVLen=1 is the minimum valid value."""
        req = AnalysisRequest(position=_minimal_position(), analysis_pv_len=1)
        payload = req.to_katago_json()
        assert payload["analysisPVLen"] == 1

    def test_both_fields_together(self) -> None:
        """rules + analysisPVLen both appear when set for ko puzzles."""
        req = AnalysisRequest(
            position=_minimal_position(),
            rules="tromp-taylor",
            analysis_pv_len=30,
        )
        payload = req.to_katago_json()
        assert payload["rules"] == "tromp-taylor"
        assert payload["analysisPVLen"] == 30


# ===================================================================
# query_builder ko routing tests
# ===================================================================


@pytest.mark.unit
class TestQueryBuilderKoRouting:
    """build_query_from_sgf resolves rules/PV from ko_type."""

    def test_no_ko_uses_chinese(self) -> None:
        """ko_type='none' (default) → rules='chinese', no analysisPVLen."""
        sgf = _load("ko_direct.sgf")
        result = build_query_from_sgf(sgf, ko_type="none")
        payload = result.request.to_katago_json()
        assert payload["rules"] == "chinese"
        assert "analysisPVLen" not in payload

    def test_direct_ko_uses_tromp_taylor(self) -> None:
        """ko_type='direct' → rules='tromp-taylor', analysisPVLen=30."""
        sgf = _load("ko_direct.sgf")
        result = build_query_from_sgf(sgf, ko_type="direct")
        payload = result.request.to_katago_json()
        assert payload["rules"] == "tromp-taylor"
        assert payload["analysisPVLen"] == 30

    def test_approach_ko_uses_tromp_taylor(self) -> None:
        """ko_type='approach' → rules='tromp-taylor', analysisPVLen=30."""
        sgf = _load("ko_approach.sgf")
        result = build_query_from_sgf(sgf, ko_type="approach")
        payload = result.request.to_katago_json()
        assert payload["rules"] == "tromp-taylor"
        assert payload["analysisPVLen"] == 30

    def test_unknown_ko_type_falls_back_to_none(self) -> None:
        """Unknown ko_type string → treated as 'none' (chinese, no PV override)."""
        sgf = _load("ko_direct.sgf")
        result = build_query_from_sgf(sgf, ko_type="unknown_garbage")
        payload = result.request.to_katago_json()
        assert payload["rules"] == "chinese"
        assert "analysisPVLen" not in payload


# ===================================================================
# query_builder with config override tests
# ===================================================================


@pytest.mark.unit
class TestQueryBuilderKoWithConfig:
    """build_query_from_sgf uses config.ko_analysis when provided."""

    def test_config_driven_rules(self) -> None:
        """Config ko_analysis overrides default rules mapping."""
        config = load_enrichment_config()
        sgf = _load("ko_direct.sgf")
        result = build_query_from_sgf(sgf, ko_type="direct", config=config)
        payload = result.request.to_katago_json()
        # Config maps direct → tromp-taylor
        assert payload["rules"] == "tromp-taylor"

    def test_config_driven_pv_len(self) -> None:
        """Config ko_analysis overrides PV length for ko puzzles."""
        config = load_enrichment_config()
        sgf = _load("ko_direct.sgf")
        result = build_query_from_sgf(sgf, ko_type="direct", config=config)
        payload = result.request.to_katago_json()
        assert payload["analysisPVLen"] == 30

    def test_config_none_ko_no_pv_override(self) -> None:
        """Config with ko_type='none' → pv_len=15, which is ≤15, so no override."""
        config = load_enrichment_config()
        sgf = _load("ko_direct.sgf")
        result = build_query_from_sgf(sgf, ko_type="none", config=config)
        payload = result.request.to_katago_json()
        assert payload["rules"] == "chinese"
        # pv_len=15 is ≤15, so query_builder skips the override
        assert "analysisPVLen" not in payload


# ===================================================================
# KoAnalysisConfig Pydantic model tests
# ===================================================================


@pytest.mark.unit
class TestKoAnalysisConfigModel:
    """KoAnalysisConfig Pydantic model validation."""

    def test_default_rules_mapping(self) -> None:
        """Default rules_by_ko_type has 3 entries."""
        cfg = KoAnalysisConfig()
        assert cfg.rules_by_ko_type["none"] == "chinese"
        assert cfg.rules_by_ko_type["direct"] == "tromp-taylor"
        assert cfg.rules_by_ko_type["approach"] == "tromp-taylor"

    def test_default_pv_len_mapping(self) -> None:
        """Default pv_len_by_ko_type has expected values."""
        cfg = KoAnalysisConfig()
        assert cfg.pv_len_by_ko_type["none"] == 15
        assert cfg.pv_len_by_ko_type["direct"] == 30
        assert cfg.pv_len_by_ko_type["approach"] == 30

    def test_config_json_has_ko_analysis(self) -> None:
        """katago-enrichment.json has the ko_analysis section."""
        config = load_enrichment_config()
        assert hasattr(config, "ko_analysis")
        assert config.ko_analysis.rules_by_ko_type["direct"] == "tromp-taylor"
        assert config.ko_analysis.pv_len_by_ko_type["direct"] == 30


# ===================================================================
# Ko calibration fixture integrity tests
# ===================================================================


@pytest.mark.unit
class TestKoCalibrationFixtures:
    """Calibration/ko fixtures exist and have correct YK properties."""

    def test_calibration_ko_dir_exists(self) -> None:
        """tests/fixtures/calibration/ko/ directory exists."""
        assert CALIBRATION_KO.is_dir(), f"Missing calibration/ko directory at {CALIBRATION_KO}"

    def test_minimum_fixture_count(self) -> None:
        """At least 3 ko calibration fixtures exist."""
        sgf_files = list(CALIBRATION_KO.glob("*.sgf"))
        assert len(sgf_files) >= 3, f"Expected ≥3 ko fixtures, found {len(sgf_files)}"

    def test_all_fixtures_have_yk_property(self) -> None:
        """Every ko calibration fixture has a YK[] property."""
        for sgf_path in sorted(CALIBRATION_KO.glob("*.sgf")):
            content = sgf_path.read_text(encoding="utf-8")
            assert "YK[" in content, f"{sgf_path.name} missing YK property"

    def test_both_ko_types_represented(self) -> None:
        """Both 'direct' and 'approach' ko types present in calibration set."""
        ko_types_found: set[str] = set()
        for sgf_path in sorted(CALIBRATION_KO.glob("*.sgf")):
            content = sgf_path.read_text(encoding="utf-8")
            if "YK[direct]" in content:
                ko_types_found.add("direct")
            if "YK[approach]" in content:
                ko_types_found.add("approach")
        assert "direct" in ko_types_found, "No YK[direct] fixtures found"
        assert "approach" in ko_types_found, "No YK[approach] fixtures found"

    def test_fixtures_have_yg_level(self) -> None:
        """Every ko calibration fixture has a YG[] level property."""
        for sgf_path in sorted(CALIBRATION_KO.glob("*.sgf")):
            content = sgf_path.read_text(encoding="utf-8")
            assert "YG[" in content, f"{sgf_path.name} missing YG property"

    def test_fixtures_have_pc_source(self) -> None:
        """Every ko calibration fixture has a PC[] source URL."""
        for sgf_path in sorted(CALIBRATION_KO.glob("*.sgf")):
            content = sgf_path.read_text(encoding="utf-8")
            assert "PC[" in content, f"{sgf_path.name} missing PC source URL"
