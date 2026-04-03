"""Tests for SingleEngineManager behavior."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from analyzers.single_engine import SingleEngineManager
from config import load_enrichment_config
from models.analysis_response import AnalysisResponse


def _response(winrate: float, visits: int = 200) -> AnalysisResponse:
    return AnalysisResponse(
        request_id="req_0001",
        move_infos=[],
        root_winrate=winrate,
        root_score=0.0,
        total_visits=visits,
    )


@pytest.mark.unit
def test_no_escalation_when_clear() -> None:
    config = load_enrichment_config()
    engine = MagicMock()
    engine.analyze = AsyncMock(return_value=_response(0.9))

    manager = SingleEngineManager(config=config, engine=engine)
    req = MagicMock()
    req.max_visits = config.analysis_defaults.default_max_visits
    req.model_copy = MagicMock(return_value=req)

    result = asyncio.run(manager.analyze(req))

    assert result.root_winrate == 0.9
    assert engine.analyze.await_count == 1
    req.model_copy.assert_not_called()


@pytest.mark.unit
def test_escalates_when_uncertain() -> None:
    config = load_enrichment_config()
    first = _response(0.5, visits=config.analysis_defaults.default_max_visits)
    second = _response(0.6, visits=config.deep_enrich.visits)

    engine = MagicMock()
    engine.analyze = AsyncMock(side_effect=[first, second])

    manager = SingleEngineManager(config=config, engine=engine)

    req = MagicMock()
    req.max_visits = config.analysis_defaults.default_max_visits
    escalated_req = MagicMock()
    escalated_req.max_visits = config.deep_enrich.visits
    req.model_copy = MagicMock(return_value=escalated_req)

    result = asyncio.run(manager.analyze(req))

    assert result.total_visits == config.deep_enrich.visits
    assert engine.analyze.await_count == 2
    req.model_copy.assert_called_once()


@pytest.mark.unit
def test_quick_only_disables_escalation() -> None:
    config = load_enrichment_config()
    engine = MagicMock()
    engine.analyze = AsyncMock(return_value=_response(0.5))

    manager = SingleEngineManager(config=config, engine=engine, mode_override="quick_only")

    req = MagicMock()
    req.max_visits = config.analysis_defaults.default_max_visits
    req.model_copy = MagicMock()

    asyncio.run(manager.analyze(req))

    assert engine.analyze.await_count == 1
    req.model_copy.assert_not_called()


# --- PI-4: Model routing by puzzle complexity ---

@pytest.mark.unit
class TestModelRouting:
    """PI-4: Verify model routing via model_by_category config."""

    @staticmethod
    def _make_config_with_routing(model_by_category: dict[str, str]) -> EnrichmentConfig:  # noqa: F821
        """Build an EnrichmentConfig with custom model_by_category."""
        config = load_enrichment_config()
        if config.ai_solve is not None:
            config.ai_solve.model_by_category = model_by_category
        else:
            from config.ai_solve import AiSolveConfig
            config.ai_solve = AiSolveConfig(model_by_category=model_by_category)
        return config

    def test_model_by_category_routes_entry(self) -> None:
        """With model_by_category={"entry": "test_fast"}, novice maps to test_fast filename."""
        config = self._make_config_with_routing({"entry": "test_fast"})
        engine = MagicMock()
        manager = SingleEngineManager(config=config, engine=engine)
        result = manager.get_model_for_level("novice")
        # Should resolve to test_fast model's filename
        assert result is not None
        assert result == config.models.test_fast.filename

    def test_model_by_category_empty_returns_none(self) -> None:
        """With model_by_category={}, returns None (no routing)."""
        config = self._make_config_with_routing({})
        engine = MagicMock()
        manager = SingleEngineManager(config=config, engine=engine)
        result = manager.get_model_for_level("novice")
        assert result is None

    def test_model_by_category_unknown_level_returns_none(self) -> None:
        """Category mapping without the relevant category returns None."""
        # "intermediate" maps to "core" category — only map "entry" and "strong"
        config = self._make_config_with_routing({"entry": "test_fast", "strong": "referee"})
        engine = MagicMock()
        manager = SingleEngineManager(config=config, engine=engine)
        result = manager.get_model_for_level("intermediate")
        # "intermediate" -> category "core", which is not in the mapping
        assert result is None


# --- Migrated from test_sprint1_fixes.py (G2 gap ID) ---


@pytest.mark.unit
class TestCompareResultsCorrectMove:
    """G2: Correct-move escalation flows through single-engine manager path."""

    def test_compare_results_accepts_correct_move(self):
        """SingleEngineManager exposes callable _should_escalate for escalation checks."""
        from analyzers.single_engine import SingleEngineManager

        assert hasattr(SingleEngineManager, "_should_escalate")
        assert callable(SingleEngineManager._should_escalate)
