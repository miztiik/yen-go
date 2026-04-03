"""Tests for HumanSL feature gate (Phase 3, T59).

Validates:
- is_humansl_available() returns False when disabled, missing path, or model absent
- is_humansl_available() returns True when enabled + model exists
- build_humansl_query() returns None when not available
- build_humansl_query() returns payload with humanSLProfile when available
- human_sl_profile field in AnalysisRequest wires into to_katago_json()
"""

from pathlib import Path

import pytest

_HERE = Path(__file__).resolve().parent
_LAB = _HERE.parent


@pytest.fixture(autouse=True)
def _clear_config_cache():
    from config import clear_cache
    clear_cache()
    yield
    clear_cache()


def _make_config(*, enabled=False, model_path="", profile_name="humanSLProfile", strength=None):
    """Load base EnrichmentConfig from JSON, then override HumanSL settings."""
    from config import load_enrichment_config
    from config.analysis import HumanSLConfig
    cfg = load_enrichment_config()
    cfg.humansl = HumanSLConfig(
        enabled=enabled,
        model_path=model_path,
        profile_name=profile_name,
        humanSLCalibrateStrength=strength,
    )
    return cfg


def _make_request():
    """Build a minimal AnalysisRequest for testing."""
    from models.analysis_request import AnalysisRequest
    from models.position import Position
    pos = Position(
        board_size=9,
        black_stones=["C3", "D4"],
        white_stones=["E5"],
    )
    return AnalysisRequest(position=pos)


# --- is_humansl_available tests ---

class TestIsHumanSLAvailable:
    def test_returns_false_when_disabled(self):
        from analyzers.humansl_calibration import is_humansl_available
        cfg = _make_config(enabled=False, model_path="/some/path")
        assert is_humansl_available(cfg) is False

    def test_returns_false_when_model_path_empty(self):
        from analyzers.humansl_calibration import is_humansl_available
        cfg = _make_config(enabled=True, model_path="")
        assert is_humansl_available(cfg) is False

    def test_returns_false_when_model_file_missing(self):
        from analyzers.humansl_calibration import is_humansl_available
        cfg = _make_config(enabled=True, model_path="/nonexistent/model.bin")
        assert is_humansl_available(cfg) is False

    def test_returns_true_when_enabled_and_model_exists(self, tmp_path):
        from analyzers.humansl_calibration import is_humansl_available
        model_file = tmp_path / "model.bin"
        model_file.write_bytes(b"dummy")
        cfg = _make_config(enabled=True, model_path=str(model_file))
        assert is_humansl_available(cfg) is True


# --- build_humansl_query tests ---

class TestBuildHumanSLQuery:
    def test_returns_none_when_not_available(self):
        from analyzers.humansl_calibration import build_humansl_query
        cfg = _make_config(enabled=False)
        req = _make_request()
        assert build_humansl_query(req, cfg) is None

    def test_returns_payload_with_profile_when_available(self, tmp_path):
        from analyzers.humansl_calibration import build_humansl_query
        model_file = tmp_path / "model.bin"
        model_file.write_bytes(b"dummy")
        cfg = _make_config(
            enabled=True,
            model_path=str(model_file),
            profile_name="preaz_18k",
        )
        req = _make_request()
        result = build_humansl_query(req, cfg)
        assert result is not None
        assert result["humanSLProfile"] == "preaz_18k"
        # Should have standard KataGo fields
        assert "id" in result
        assert "initialStones" in result

    def test_includes_calibrate_strength_when_set(self, tmp_path):
        from analyzers.humansl_calibration import build_humansl_query
        model_file = tmp_path / "model.bin"
        model_file.write_bytes(b"dummy")
        cfg = _make_config(
            enabled=True,
            model_path=str(model_file),
            strength=1200.0,
        )
        req = _make_request()
        result = build_humansl_query(req, cfg)
        assert result is not None
        assert result["overrideSettings"]["humanSLCalibrateStrength"] == 1200.0

    def test_no_calibrate_strength_when_none(self, tmp_path):
        from analyzers.humansl_calibration import build_humansl_query
        model_file = tmp_path / "model.bin"
        model_file.write_bytes(b"dummy")
        cfg = _make_config(
            enabled=True,
            model_path=str(model_file),
            strength=None,
        )
        req = _make_request()
        result = build_humansl_query(req, cfg)
        assert result is not None
        assert "overrideSettings" not in result or "humanSLCalibrateStrength" not in result.get("overrideSettings", {})


# --- AnalysisRequest.human_sl_profile tests ---

class TestAnalysisRequestHumanSLField:
    def test_default_is_none(self):
        req = _make_request()
        assert req.human_sl_profile is None

    def test_not_in_payload_when_none(self):
        req = _make_request()
        payload = req.to_katago_json()
        assert "humanSLProfile" not in payload

    def test_in_payload_when_set(self):
        from models.analysis_request import AnalysisRequest
        from models.position import Position
        pos = Position(
            board_size=9,
            black_stones=["C3"],
            white_stones=["E5"],
        )
        req = AnalysisRequest(position=pos, human_sl_profile="preaz_18k")
        payload = req.to_katago_json()
        assert payload["humanSLProfile"] == "preaz_18k"
