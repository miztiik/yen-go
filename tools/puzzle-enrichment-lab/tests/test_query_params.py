"""Tests for query parameter correctness (T26).

Validates:
1. reportAnalysisWinratesAs=BLACK is always in payload
2. rootNumSymmetriesToSample is 4 for standard, 8 for referee
3. Refutation override settings are present
4. Visit tier values appear in request
"""

from pathlib import Path

import pytest

_LAB = Path(__file__).resolve().parent.parent

from config import clear_cache, load_enrichment_config
from models.analysis_request import AnalysisRequest
from models.position import Color, Position, Stone


@pytest.fixture(autouse=True)
def _clear_config_cache():
    clear_cache()
    yield
    clear_cache()


def _make_position() -> Position:
    """Create a minimal valid position for testing."""
    return Position(
        board_size=19,
        player_to_move=Color.BLACK,
        black_stones=[Stone(color=Color.BLACK, x=3, y=3), Stone(color=Color.BLACK, x=4, y=3)],
        white_stones=[Stone(color=Color.WHITE, x=5, y=3), Stone(color=Color.WHITE, x=5, y=4)],
    )


@pytest.mark.unit
class TestReportWinratesAsBlack:
    """reportAnalysisWinratesAs=BLACK must always be in payload."""

    def test_default_report_as_black(self) -> None:
        """Default AnalysisRequest reports winrates as BLACK."""
        req = AnalysisRequest(position=_make_position())
        assert req.report_analysis_winrates_as == "BLACK"

    def test_payload_excludes_report_winrates(self) -> None:
        """KataGo JSON payload must NOT include reportAnalysisWinratesAs.

        reportAnalysisWinratesAs is a cfg-level setting set in tsumego_analysis.cfg,
        not a per-query field.  Sending it as JSON causes KataGo to warn and ignore.
        """
        req = AnalysisRequest(position=_make_position())
        payload = req.to_katago_json()
        assert "reportAnalysisWinratesAs" not in payload

    def test_build_query_preserves_winrate_perspective(self) -> None:
        """build_query_from_sgf produces model with report_analysis_winrates_as=BLACK,
        but the field is NOT in the KataGo JSON payload (cfg-level setting)."""
        from analyzers.query_builder import build_query_from_sgf

        fixtures = Path(__file__).parent / "fixtures"
        sgf = (fixtures / "simple_life_death.sgf").read_text(encoding="utf-8")
        result = build_query_from_sgf(sgf)
        # Model field is present
        assert result.request.report_analysis_winrates_as == "BLACK"
        # But NOT serialized to JSON payload
        payload = result.request.to_katago_json()
        assert "reportAnalysisWinratesAs" not in payload


@pytest.mark.unit
class TestSymmetriesConfiguration:
    """rootNumSymmetriesToSample: 4 for standard, 8 for referee."""

    def test_standard_symmetries_is_4(self) -> None:
        """Config deep_enrich.root_num_symmetries_to_sample is 4."""
        config = load_enrichment_config()
        assert config.deep_enrich.root_num_symmetries_to_sample == 4

    def test_referee_symmetries_is_8(self) -> None:
        """Config deep_enrich.referee_symmetries is 8."""
        config = load_enrichment_config()
        assert config.deep_enrich.referee_symmetries == 8

    def test_query_builder_wires_standard_symmetries(self) -> None:
        """build_query_from_sgf passes standard symmetries into override_settings."""
        from analyzers.query_builder import build_query_from_sgf

        fixtures = Path(__file__).parent / "fixtures"
        sgf = (fixtures / "simple_life_death.sgf").read_text(encoding="utf-8")
        result = build_query_from_sgf(sgf)
        payload = result.request.to_katago_json()
        assert "overrideSettings" in payload
        assert payload["overrideSettings"]["rootNumSymmetriesToSample"] == 4

    def test_override_settings_in_request(self) -> None:
        """AnalysisRequest with override_settings includes them in payload."""
        req = AnalysisRequest(
            position=_make_position(),
            override_settings={"rootNumSymmetriesToSample": 8},
        )
        payload = req.to_katago_json()
        assert payload["overrideSettings"]["rootNumSymmetriesToSample"] == 8


@pytest.mark.unit
class TestRefutationOverrides:
    """Refutation override settings are present in config."""

    def test_refutation_overrides_present(self) -> None:
        """Config has refutation override settings."""
        config = load_enrichment_config()
        ro = config.refutations.refutation_overrides
        assert ro is not None
        assert ro.root_policy_temperature == 1.3
        assert ro.root_fpu_reduction_max == 0.0
        assert ro.wide_root_noise == 0.08

    def test_tenuki_rejection_present(self) -> None:
        """Config has tenuki rejection settings."""
        config = load_enrichment_config()
        tr = config.refutations.tenuki_rejection
        assert tr is not None
        assert tr.enabled is True
        assert tr.manhattan_threshold == 4.0


@pytest.mark.unit
class TestVisitTierInRequest:
    """Visit tier values appear in request max_visits."""

    def test_t1_visits_in_request(self) -> None:
        """T1 visits (500) can be set on AnalysisRequest."""
        config = load_enrichment_config()
        req = AnalysisRequest(
            position=_make_position(),
            max_visits=config.visit_tiers.T1.visits,
        )
        payload = req.to_katago_json()
        assert payload["maxVisits"] == 500

    def test_t2_visits_in_request(self) -> None:
        """T2 visits (2000) can be set on AnalysisRequest."""
        config = load_enrichment_config()
        req = AnalysisRequest(
            position=_make_position(),
            max_visits=config.visit_tiers.T2.visits,
        )
        payload = req.to_katago_json()
        assert payload["maxVisits"] == 2000

    def test_t3_visits_in_request(self) -> None:
        """T3 visits (5000) can be set on AnalysisRequest."""
        config = load_enrichment_config()
        req = AnalysisRequest(
            position=_make_position(),
            max_visits=config.visit_tiers.T3.visits,
        )
        payload = req.to_katago_json()
        assert payload["maxVisits"] == 5000
