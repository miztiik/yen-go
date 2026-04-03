"""Tests for ko-aware validation.

Task A.1.5: Ko-aware validation with KataGo PV analysis.

Ko validation reads the YK property (none, direct, approach) and uses
KataGo PV captures/recaptures to detect and validate ko sequences.
Unit tests use mocked responses; integration tests use real KataGo.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve().parent
_LAB = _HERE.parent

from analyzers.ko_validation import (
    KoType,
    detect_ko_in_pv,
    validate_ko,
)
from analyzers.validate_correct_move import ValidationStatus
from config import load_enrichment_config
from models.analysis_response import AnalysisResponse, MoveAnalysis

FIXTURES = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_response(
    top_move: str = "A1",
    top_visits: int = 100,
    top_winrate: float = 0.85,
    top_policy: float = 0.55,
    top_pv: list[str] | None = None,
    extra_moves: list[dict] | None = None,
    root_winrate: float = 0.80,
    root_score: float = 0.0,
) -> AnalysisResponse:
    """Create a mock AnalysisResponse for unit tests."""
    moves = [
        MoveAnalysis(
            move=top_move,
            visits=top_visits,
            winrate=top_winrate,
            policy_prior=top_policy,
            pv=top_pv or [top_move],
        )
    ]
    for em in (extra_moves or []):
        moves.append(MoveAnalysis(**em))
    return AnalysisResponse(
        request_id="mock",
        move_infos=moves,
        root_winrate=root_winrate,
        root_score=root_score,
        total_visits=200,
    )


# ===================================================================
# Unit Tests
# ===================================================================


@pytest.mark.unit
class TestKoDirectValidation:
    """YK=direct → validate correct ko capture move."""

    def test_ko_direct(self) -> None:
        """Direct ko: correct move is top move with ko recapture in PV → accepted."""
        config = load_enrichment_config()
        # PV shows: A1 captures, B1 recaptures, A1 captures again (ko fight)
        response = _mock_response(
            top_move="A1",
            top_winrate=0.88,
            top_policy=0.60,
            top_pv=["A1", "B1", "A1", "B1"],  # Ko captures/recaptures
        )
        result = validate_ko(
            response=response,
            correct_move_gtp="A1",
            ko_type=KoType.DIRECT,
            config=config,
        )
        assert result.status == ValidationStatus.ACCEPTED
        assert result.ko_detected
        assert result.katago_agrees


@pytest.mark.unit
class TestKoApproachValidation:
    """YK=approach → validate approach move sequence."""

    def test_ko_approach(self) -> None:
        """Approach ko: first move is an approach (not the ko capture itself)."""
        config = load_enrichment_config()
        # Approach move sets up the ko, not a direct capture
        response = _mock_response(
            top_move="C5",
            top_winrate=0.75,
            top_policy=0.40,
            top_pv=["C5", "D5", "C4", "D4"],  # Sequence leading to ko
        )
        result = validate_ko(
            response=response,
            correct_move_gtp="C5",
            ko_type=KoType.APPROACH,
            config=config,
        )
        assert result.status in (ValidationStatus.ACCEPTED, ValidationStatus.FLAGGED)
        assert result.katago_agrees


@pytest.mark.unit
class TestKoMultistepValidation:
    """Multi-step ko → full ko sequence checked."""

    def test_ko_multistep(self) -> None:
        """Multi-step ko: PV shows repeated captures at same point."""
        config = load_enrichment_config()
        # PV with repeated captures at the same point indicates multi-step ko
        response = _mock_response(
            top_move="A1",
            top_winrate=0.82,
            top_policy=0.50,
            top_pv=["A1", "B1", "C1", "A1", "B1"],  # Multi-step sequence
        )
        result = validate_ko(
            response=response,
            correct_move_gtp="A1",
            ko_type=KoType.DIRECT,
            config=config,
        )
        assert result.status in (ValidationStatus.ACCEPTED, ValidationStatus.FLAGGED)


@pytest.mark.unit
class TestKoDoubleValidation:
    """Double ko position → correctly identified and handled."""

    def test_ko_double(self) -> None:
        """Double ko: two different ko captures in the PV."""
        config = load_enrichment_config()
        # PV shows captures at two different ko points
        response = _mock_response(
            top_move="A1",
            top_winrate=0.80,
            top_policy=0.45,
            top_pv=["A1", "B1", "H1", "I1", "A1"],  # Two ko points
        )
        result = validate_ko(
            response=response,
            correct_move_gtp="A1",
            ko_type=KoType.DIRECT,
            config=config,
        )
        # Double ko is a valid ko situation
        assert result.status in (ValidationStatus.ACCEPTED, ValidationStatus.FLAGGED)


@pytest.mark.unit
class TestKo10000YearValidation:
    """Ten-thousand-year ko → recognized as special case."""

    def test_ko_10000year(self) -> None:
        """10000-year ko: long PV with ko captures, both sides can't afford to lose."""
        config = load_enrichment_config()
        # Long PV with ko recaptures — suggests neither side can concede
        response = _mock_response(
            top_move="A1",
            top_winrate=0.52,  # Near 0.5 — neither side wins decisively
            top_policy=0.45,
            top_pv=["A1", "B1", "A1", "B1", "A1", "B1"],  # Continuous ko
        )
        result = validate_ko(
            response=response,
            correct_move_gtp="A1",
            ko_type=KoType.DIRECT,
            config=config,
        )
        # 10000-year ko is accepted or flagged, never rejected if move is top
        assert result.status in (ValidationStatus.ACCEPTED, ValidationStatus.FLAGGED)
        assert "long_ko_fight" in result.flags or result.ko_detected


@pytest.mark.unit
class TestDetectKoInPV:
    """AI enhancement: detect ko from KataGo PV."""

    def test_yk_ai_enhancement(self) -> None:
        """KataGo PV with repeated captures/recaptures → ko detected."""
        # Simulate a PV with the pattern: capture → recapture → capture
        pv = ["A1", "B1", "A1", "B1", "A1"]
        result = detect_ko_in_pv(pv)
        assert result.ko_detected
        assert result.ko_type_hint is not None

    def test_yk_none_no_ko_in_pv(self) -> None:
        """No ko in PV → no ko enrichment."""
        # Normal PV without repetition
        pv = ["D4", "E5", "F6", "G7"]
        result = detect_ko_in_pv(pv)
        assert not result.ko_detected

    def test_ownership_oscillation_detects_ko(self) -> None:
        """Detection of ko through repeated move at same coordinate in PV."""
        # A move appearing 3+ times in PV strongly suggests ko
        pv = ["C3", "D3", "C3", "D3", "C3"]
        result = detect_ko_in_pv(pv)
        assert result.ko_detected


# ===================================================================
# Integration Tests (uses shared integration_engine from conftest.py)
# ===================================================================

from config.helpers import KATAGO_PATH, model_path


@pytest.mark.integration
@pytest.mark.skipif(
    not KATAGO_PATH.exists(),
    reason="KataGo binary not found",
)
@pytest.mark.skipif(
    not model_path("test_smallest").exists(),
    reason="Model file not found",
)
class TestIntegrationKo:
    """Integration tests with real KataGo engine for ko puzzles."""

    def test_direct_ko_fixture(self, integration_engine) -> None:
        """Fixture SGF with direct ko → validated correctly."""
        from analyzers.query_builder import build_query_from_sgf
        from core.tsumego_analysis import extract_correct_first_move, parse_sgf
        from models.analysis_response import sgf_to_gtp

        sgf = (FIXTURES / "ko_direct.sgf").read_text(encoding="utf-8")
        root = parse_sgf(sgf)
        correct_sgf = extract_correct_first_move(root)
        assert correct_sgf is not None

        query_result = build_query_from_sgf(sgf, max_visits=1000)
        request = query_result.request
        correct_gtp = sgf_to_gtp(correct_sgf, query_result.original_board_size)

        async def _run():
            response = await asyncio.wait_for(
                integration_engine.analyze(request), timeout=60.0
            )
            return validate_ko(
                response=response,
                correct_move_gtp=correct_gtp,
                ko_type=KoType.DIRECT,
            )

        result = asyncio.run(_run())
        # Direct ko puzzle should be accepted or flagged, not rejected
        assert result.status in (ValidationStatus.ACCEPTED, ValidationStatus.FLAGGED)

    def test_approach_ko_fixture(self, integration_engine) -> None:
        """Fixture SGF with approach ko → validated correctly."""
        from analyzers.query_builder import build_query_from_sgf
        from core.tsumego_analysis import extract_correct_first_move, parse_sgf
        from models.analysis_response import sgf_to_gtp

        sgf = (FIXTURES / "ko_approach.sgf").read_text(encoding="utf-8")
        root = parse_sgf(sgf)
        correct_sgf = extract_correct_first_move(root)
        assert correct_sgf is not None

        query_result = build_query_from_sgf(sgf, max_visits=1000)
        request = query_result.request
        correct_gtp = sgf_to_gtp(correct_sgf, query_result.original_board_size)

        async def _run():
            response = await asyncio.wait_for(
                integration_engine.analyze(request), timeout=60.0
            )
            return validate_ko(
                response=response,
                correct_move_gtp=correct_gtp,
                ko_type=KoType.APPROACH,
            )

        result = asyncio.run(_run())
        # Approach ko puzzle should be accepted or flagged
        assert result.status in (ValidationStatus.ACCEPTED, ValidationStatus.FLAGGED)
