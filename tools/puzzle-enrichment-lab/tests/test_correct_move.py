"""Tests for correct move validation — tag-aware dispatch.

Task A.1.3: Validate correct move against KataGo with tag-aware dispatch.

Unit tests use mocked AnalysisResponse objects (no KataGo needed).
Integration tests use the real KataGo engine (marked @pytest.mark.integration).
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

# Ensure tools/puzzle-enrichment-lab is importable
_HERE = Path(__file__).resolve().parent
_LAB = _HERE.parent
from analyzers.validate_correct_move import (
    ValidationStatus,
    _dispatch_by_tags,
    _validate_capture_race,
    _validate_connection,
    _validate_life_and_death,
    _validate_seki,
    _validate_tactical,
    validate_correct_move,
)
from config import load_enrichment_config
from models.analysis_response import AnalysisResponse, MoveAnalysis

FIXTURES = Path(__file__).parent / "fixtures"

# ---------------------------------------------------------------------------
# Helpers — build mock AnalysisResponse objects
# ---------------------------------------------------------------------------


def _mock_response(
    top_move: str = "A1",
    top_visits: int = 100,
    top_winrate: float = 0.92,
    top_policy: float = 0.65,
    top_pv: list[str] | None = None,
    extra_moves: list[dict] | None = None,
    root_winrate: float = 0.85,
    total_visits: int = 200,
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
        root_score=0.0,
        total_visits=total_visits,
    )


def _mock_response_with_ownership(
    top_move: str = "A1",
    top_winrate: float = 0.92,
    correct_move: str = "A1",
    correct_winrate: float = 0.92,
) -> AnalysisResponse:
    """Mock response where top move is given and correct move may differ."""
    moves = [
        MoveAnalysis(
            move=top_move,
            visits=100,
            winrate=top_winrate,
            policy_prior=0.6,
            pv=[top_move],
        ),
    ]
    if correct_move != top_move:
        moves.append(
            MoveAnalysis(
                move=correct_move,
                visits=30,
                winrate=correct_winrate,
                policy_prior=0.15,
                pv=[correct_move],
            )
        )
    return AnalysisResponse(
        request_id="mock",
        move_infos=moves,
        root_winrate=0.80,
        root_score=0.0,
        total_visits=200,
    )


# ===================================================================
# Unit Tests — tag-aware dispatch logic
# ===================================================================


@pytest.mark.unit
class TestLifeAndDeathOwnership:
    """Life-and-death puzzles use ownership-based validation."""

    def test_life_and_death_ownership_validation(self) -> None:
        """Life-and-death puzzle → correct move is top move → accepted."""
        config = load_enrichment_config()
        response = _mock_response(
            top_move="D1",
            top_winrate=0.95,
            top_policy=0.7,
        )
        result = _validate_life_and_death(
            response=response,
            correct_move_gtp="D1",
            config=config,
            corner="TL",
        )
        assert result.status == ValidationStatus.ACCEPTED
        assert result.katago_agrees

    def test_life_and_death_flagged(self) -> None:
        """Correct move not top but winrate in uncertain range → flagged."""
        config = load_enrichment_config()
        response = _mock_response(
            top_move="E1",
            top_winrate=0.60,
            top_policy=0.4,
            extra_moves=[{
                "move": "D1",
                "visits": 50,
                "winrate": 0.55,
                "policy_prior": 0.3,
                "pv": ["D1"],
            }],
        )
        result = _validate_life_and_death(
            response=response,
            correct_move_gtp="D1",
            config=config,
            corner="TL",
        )
        assert result.status == ValidationStatus.FLAGGED

    def test_life_and_death_rejected(self) -> None:
        """Correct move not in top N → rejected."""
        config = load_enrichment_config()
        # 6 moves that all rank above the correct move
        extra = [
            {"move": f"E{i}", "visits": 50 - i * 5, "winrate": 0.7, "policy_prior": 0.1, "pv": [f"E{i}"]}
            for i in range(1, 6)
        ]
        response = _mock_response(
            top_move="A2",
            top_visits=100,
            top_winrate=0.92,
            extra_moves=extra,
        )
        # D1 isn't even in the move list
        result = _validate_life_and_death(
            response=response,
            correct_move_gtp="D1",
            config=config,
            corner="TL",
        )
        assert result.status == ValidationStatus.REJECTED


@pytest.mark.unit
class TestTacticalPvValidation:
    """Tactical puzzles (ladder, net, snapback) validate via PV patterns."""

    def test_tactical_pv_validation(self) -> None:
        """Ladder puzzle → correct move is top with forcing PV → accepted."""
        config = load_enrichment_config()
        response = _mock_response(
            top_move="C6",
            top_winrate=0.92,
            top_policy=0.55,
            top_pv=["C6", "C7", "D7", "D8"],  # Forcing ladder sequence
        )
        result = _validate_tactical(
            response=response,
            correct_move_gtp="C6",
            config=config,
            tag_slug="ladder",
        )
        assert result.status == ValidationStatus.ACCEPTED
        assert result.katago_agrees


@pytest.mark.unit
class TestCaptureRaceValidation:
    """Capture-race (semeai) puzzles — liberty-related validation."""

    def test_semeai_liberty_validation(self) -> None:
        """Capture-race → correct move top → accepted."""
        config = load_enrichment_config()
        response = _mock_response(
            top_move="B5",
            top_winrate=0.88,
            top_policy=0.50,
            top_pv=["B5", "F5", "F4"],  # Liberty reduction sequence
        )
        result = _validate_capture_race(
            response=response,
            correct_move_gtp="B5",
            config=config,
        )
        assert result.status == ValidationStatus.ACCEPTED
        assert result.katago_agrees


@pytest.mark.unit
class TestConnectionValidation:
    """Connection/cutting puzzles — group connectivity validation."""

    def test_connection_validation(self) -> None:
        """Connection puzzle → correct move is top → accepted."""
        config = load_enrichment_config()
        response = _mock_response(
            top_move="F4",
            top_winrate=0.80,
            top_policy=0.45,
            top_pv=["F4", "F3", "E3"],
        )
        result = _validate_connection(
            response=response,
            correct_move_gtp="F4",
            config=config,
        )
        assert result.status == ValidationStatus.ACCEPTED


@pytest.mark.unit
class TestSekiValidation:
    """Seki puzzles — combined 3-signal validation."""

    def test_seki_combined_signals(self) -> None:
        """Seki puzzle: winrate near 0.5 + low score → accepted.

        Seki validated with 3 signals:
        - ownership near 0 (neither owns)
        - neither player profits (score near 0)
        - both groups survive (winrate near 0.5)
        """
        config = load_enrichment_config()
        response = _mock_response(
            top_move="B2",
            top_winrate=0.52,  # Near 0.5 — neither side wins big
            top_policy=0.40,
            top_pv=["B2"],
        )
        # Override root score to near 0 (seki = no territory gain)
        response.root_score = 0.5
        result = _validate_seki(
            response=response,
            correct_move_gtp="B2",
            config=config,
        )
        assert result.status == ValidationStatus.ACCEPTED

    def test_seki_with_eyes(self) -> None:
        """Seki with one-sided eyes → ownership may be 0.4, still valid seki."""
        config = load_enrichment_config()
        response = _mock_response(
            top_move="B2",
            top_winrate=0.55,  # Slight advantage but still seki range
            top_policy=0.35,
            top_pv=["B2"],
        )
        response.root_score = 1.5  # Small score — asymmetric seki
        result = _validate_seki(
            response=response,
            correct_move_gtp="B2",
            config=config,
        )
        # Seki with slight advantage is still accepted if within thresholds
        assert result.status in (ValidationStatus.ACCEPTED, ValidationStatus.FLAGGED)

    def test_seki_hanezeki(self) -> None:
        """Flower/hane seki correctly identified."""
        config = load_enrichment_config()
        response = _mock_response(
            top_move="C3",
            top_winrate=0.50,  # Perfect balance
            top_policy=0.30,
            top_pv=["C3"],
        )
        response.root_score = 0.0
        result = _validate_seki(
            response=response,
            correct_move_gtp="C3",
            config=config,
        )
        assert result.status == ValidationStatus.ACCEPTED


@pytest.mark.unit
class TestMiaiValidation:
    """Miai puzzles (YO=miai) — both correct moves should pass."""

    def test_miai_puzzle_both_moves_validated(self) -> None:
        """YO=miai puzzle → both correct moves are valid."""
        load_enrichment_config()
        # Two moves with similar high winrate and good visits
        response = _mock_response(
            top_move="B2",
            top_visits=80,
            top_winrate=0.90,
            top_policy=0.35,
            extra_moves=[{
                "move": "D1",
                "visits": 70,
                "winrate": 0.88,
                "policy_prior": 0.30,
                "pv": ["D1"],
            }],
        )
        # Validate first miai move (top move)
        result1 = validate_correct_move(
            response=response,
            correct_move_gtp="B2",
            tags=[10],  # life-and-death
            corner="TL",
            move_order="miai",
            all_correct_moves_gtp=["B2", "D1"],
        )
        assert result1.status == ValidationStatus.ACCEPTED

        # Validate second miai move (not top, but high in list)
        result2 = validate_correct_move(
            response=response,
            correct_move_gtp="D1",
            tags=[10],
            corner="TL",
            move_order="miai",
            all_correct_moves_gtp=["B2", "D1"],
        )
        assert result2.status == ValidationStatus.ACCEPTED


@pytest.mark.unit
class TestOwnershipThresholdByRegion:
    """Center puzzles use reduced ownership threshold."""

    def test_ownership_threshold_by_region(self) -> None:
        """Center puzzle (YC=C) uses center_alive threshold (0.5) from config."""
        config = load_enrichment_config()
        # Center threshold is 0.5 (reduced from normal 0.7)
        assert config.ownership_thresholds.center_alive == 0.5

        response = _mock_response(
            top_move="J10",
            top_winrate=0.75,
            top_policy=0.50,
        )
        result = _validate_life_and_death(
            response=response,
            correct_move_gtp="J10",
            config=config,
            corner="C",  # Center
        )
        assert result.status == ValidationStatus.ACCEPTED


@pytest.mark.unit
class TestFallbackValidation:
    """Unknown tags fall back to ownership-based validation."""

    def test_fallback_to_ownership(self) -> None:
        """Unknown tag → falls back to ownership-based (life-and-death) validation."""
        load_enrichment_config()
        response = _mock_response(
            top_move="A1",
            top_winrate=0.90,
            top_policy=0.60,
        )
        result = validate_correct_move(
            response=response,
            correct_move_gtp="A1",
            tags=[999],  # Unknown tag
            corner="TL",
        )
        assert result.status == ValidationStatus.ACCEPTED


@pytest.mark.unit
class TestStatusValues:
    """Validate status field values: accepted, flagged, rejected."""

    def test_status_accepted(self) -> None:
        """KataGo agrees → status=accepted."""
        load_enrichment_config()
        response = _mock_response(top_move="D1", top_winrate=0.95)
        result = validate_correct_move(
            response=response,
            correct_move_gtp="D1",
            tags=[10],
            corner="TL",
        )
        assert result.status == ValidationStatus.ACCEPTED

    def test_status_flagged(self) -> None:
        """KataGo uncertain (value 0.3-0.7) → status=flagged."""
        load_enrichment_config()
        response = _mock_response(
            top_move="E1",
            top_winrate=0.55,
            extra_moves=[{
                "move": "D1",
                "visits": 40,
                "winrate": 0.50,
                "policy_prior": 0.20,
                "pv": ["D1"],
            }],
        )
        result = validate_correct_move(
            response=response,
            correct_move_gtp="D1",
            tags=[10],
            corner="TL",
        )
        assert result.status == ValidationStatus.FLAGGED

    def test_status_rejected(self) -> None:
        """Correct move not in top N and low winrate → status=rejected."""
        load_enrichment_config()
        extras = [
            {"move": f"E{i}", "visits": 50 - i * 5, "winrate": 0.8, "policy_prior": 0.1, "pv": [f"E{i}"]}
            for i in range(1, 6)
        ]
        response = _mock_response(
            top_move="A2",
            top_visits=100,
            top_winrate=0.95,
            extra_moves=extras,
        )
        result = validate_correct_move(
            response=response,
            correct_move_gtp="Z9",  # Not even in the list — winrate=0
            tags=[10],
            corner="TL",
        )
        assert result.status == ValidationStatus.REJECTED


@pytest.mark.unit
class TestWinrateRescue:
    """Winrate rescue: not in top-N by visits but high winrate → auto-accept or flagged."""

    @staticmethod
    def _make_filler_moves(count: int = 22) -> list[dict]:
        """Generate ``count`` filler moves that all rank above the correct move.

        With ``rejected_not_in_top_n=20`` we need >20 fillers so the
        correct move (added separately) falls outside top-N.
        Starts at row 10 to avoid collisions with common test moves
        (A1, A2, B2, K10, C13, B13).
        """
        cols = "DEFGHJLMNOPQRST"  # 15 columns, avoids A/B/C/K
        return [
            {
                "move": f"{cols[i % len(cols)]}{10 + i // len(cols)}",
                "visits": 80 - i,
                "winrate": 0.8,
                "policy_prior": 0.04,
                "pv": [f"{cols[i % len(cols)]}{10 + i // len(cols)}"],
            }
            for i in range(count)
        ]

    def test_high_winrate_not_in_top_n_auto_accepted(self) -> None:
        """Move outside top-N with winrate >= auto_accept (0.85) → ACCEPTED.

        Rank is no longer a gating signal — winrate + visits determines
        acceptance. High WR is accepted regardless of rank or visits.
        """
        extras = self._make_filler_moves(22)
        # Correct move has high winrate but very few visits (rank >20)
        extras.append({
            "move": "K10", "visits": 2, "winrate": 0.99,
            "policy_prior": 0.001, "pv": ["K10"],
        })
        response = _mock_response(
            top_move="A2",
            top_visits=100,
            top_winrate=0.95,
            extra_moves=extras,
        )
        result = validate_correct_move(
            response=response,
            correct_move_gtp="K10",
            tags=[10],  # life-and-death
            corner="TL",
        )
        assert result.status == ValidationStatus.ACCEPTED

    def test_low_winrate_not_in_top_n_rejected(self) -> None:
        """Move outside top-N with winrate < flagged_low → REJECTED."""
        extras = self._make_filler_moves(22)
        # Correct move has low winrate AND not in top-N
        extras.append({
            "move": "K10", "visits": 1, "winrate": 0.2,
            "policy_prior": 0.001, "pv": ["K10"],
        })
        response = _mock_response(
            top_move="A2",
            top_visits=100,
            top_winrate=0.95,
            extra_moves=extras,
        )
        result = validate_correct_move(
            response=response,
            correct_move_gtp="K10",
            tags=[10],
            corner="TL",
        )
        assert result.status == ValidationStatus.REJECTED

    def test_zero_visit_move_still_rejected(self) -> None:
        """Move with 0 visits (not in moveInfos) → rejected (winrate=0)."""
        extras = self._make_filler_moves(22)
        response = _mock_response(
            top_move="A2",
            top_visits=100,
            top_winrate=0.95,
            extra_moves=extras,
        )
        result = validate_correct_move(
            response=response,
            correct_move_gtp="Z9",  # Not in moveInfos at all
            tags=[10],
            corner="TL",
        )
        assert result.status == ValidationStatus.REJECTED

    def test_winrate_rescue_tactical(self) -> None:
        """High winrate works for tactical validator too → ACCEPTED."""
        extras = self._make_filler_moves(22)
        extras.append({
            "move": "C13", "visits": 3, "winrate": 0.99,
            "policy_prior": 0.0001, "pv": ["C13", "D14", "E15"],
        })
        response = _mock_response(
            top_move="B13",
            top_visits=100,
            top_winrate=0.95,
            extra_moves=extras,
        )
        result = validate_correct_move(
            response=response,
            correct_move_gtp="C13",
            tags=[42],  # nakade → tactical
            corner="TL",
        )
        assert result.status == ValidationStatus.ACCEPTED

    def test_seki_winrate_rescue(self) -> None:
        """Seki puzzle: no seki signals but high winrate → auto-accept.

        Occurs when a local seki exists but board-level territory
        imbalances mask the seki signals (root_winrate not ~0.5,
        root_score not near 0, move not in top-N).
        """
        # Correct move not in top-20 but has high winrate
        extras = self._make_filler_moves(22)
        extras.append({
            "move": "B2", "visits": 2, "winrate": 0.92,
            "policy_prior": 0.0002, "pv": ["B2"],
        })
        response = AnalysisResponse(
            request_id="mock",
            move_infos=[
                MoveAnalysis(move="A1", visits=100, winrate=0.90, policy_prior=0.65, pv=["A1"]),
                *[MoveAnalysis(**em) for em in extras],
            ],
            root_winrate=0.90,    # NOT near 0.5 → fails seki signal 1
            root_score=15.0,      # NOT near 0 → fails seki signal 2
            total_visits=200,
        )
        result = validate_correct_move(
            response=response,
            correct_move_gtp="B2",
            tags=[10, 16],  # life-and-death + seki
            corner="TL",
        )
        assert result.status == ValidationStatus.ACCEPTED
        assert "seki_winrate_rescue_auto_accepted" in result.flags

    @pytest.mark.parametrize("wr, expected_status, expected_flag", [
        (0.85, ValidationStatus.ACCEPTED, None),
        (0.849, ValidationStatus.FLAGGED, "reason:under_explored"),
        (0.7, ValidationStatus.FLAGGED, "reason:under_explored"),
        (0.699, ValidationStatus.FLAGGED, "reason:uncertain_winrate"),
        (0.29, ValidationStatus.REJECTED, "reason:low_winrate"),
    ])
    def test_winrate_rescue_boundary(
        self, wr: float, expected_status: ValidationStatus, expected_flag: str | None,
    ) -> None:
        """Boundary test: accepted, flagged (under-explored/uncertain), rejected."""
        extras = self._make_filler_moves(22)
        extras.append({
            "move": "K10", "visits": 2, "winrate": wr,
            "policy_prior": 0.001, "pv": ["K10"],
        })
        response = _mock_response(
            top_move="A2",
            top_visits=100,
            top_winrate=0.95,
            extra_moves=extras,
        )
        result = validate_correct_move(
            response=response,
            correct_move_gtp="K10",
            tags=[10],
            corner="TL",
        )
        assert result.status == expected_status
        if expected_flag:
            assert expected_flag in result.flags


@pytest.mark.unit
class TestDispatchRouting:
    """Verify tag-aware dispatch routes to correct validator."""

    def test_dispatch_life_and_death(self) -> None:
        """Tags containing 10 (life-and-death) routes to L&D validator."""
        validator_name = _dispatch_by_tags([10, 62])
        assert validator_name == "life_and_death"

    def test_dispatch_ko(self) -> None:
        """Tag 12 (ko) routes to ko validator."""
        validator_name = _dispatch_by_tags([12])
        assert validator_name == "ko"

    def test_dispatch_seki(self) -> None:
        """Tag 16 (seki) routes to seki validator."""
        validator_name = _dispatch_by_tags([16])
        assert validator_name == "seki"

    def test_dispatch_ladder(self) -> None:
        """Tag 34 (ladder) routes to tactical validator."""
        validator_name = _dispatch_by_tags([34])
        assert validator_name == "tactical"

    def test_dispatch_capture_race(self) -> None:
        """Tag 60 (capture-race) routes to capture_race validator."""
        validator_name = _dispatch_by_tags([60])
        assert validator_name == "capture_race"

    def test_dispatch_connection(self) -> None:
        """Tag 68 (connection) routes to connection validator."""
        validator_name = _dispatch_by_tags([68])
        assert validator_name == "connection"

    def test_dispatch_cutting(self) -> None:
        """Tag 70 (cutting) routes to connection validator."""
        validator_name = _dispatch_by_tags([70])
        assert validator_name == "connection"

    def test_dispatch_fallback(self) -> None:
        """Unknown tag routes to ownership fallback."""
        validator_name = _dispatch_by_tags([999])
        assert validator_name == "life_and_death"

    def test_dispatch_priority(self) -> None:
        """Ko tag takes priority over life-and-death when both present."""
        validator_name = _dispatch_by_tags([10, 12])
        assert validator_name == "ko"


@pytest.mark.unit
class TestKoTypePassthrough:
    """Verify ko_type parameter propagates to ko validator."""

    def test_ko_type_direct_uses_validator(self) -> None:
        """ko_type='direct' is used when tag 12 dispatches to ko."""
        response = _mock_response(top_move="D1", top_winrate=0.95)
        result = validate_correct_move(
            response=response,
            correct_move_gtp="D1",
            tags=[12],
            ko_type="direct",
        )
        assert result.status == ValidationStatus.ACCEPTED
        assert result.validator_used == "ko"

    def test_ko_type_approach_uses_validator(self) -> None:
        """ko_type='approach' passes through to validate_ko."""
        response = _mock_response(top_move="D1", top_winrate=0.95)
        result = validate_correct_move(
            response=response,
            correct_move_gtp="D1",
            tags=[12],
            ko_type="approach",
        )
        assert result.status == ValidationStatus.ACCEPTED
        assert result.validator_used == "ko"

    def test_ko_type_none_defaults_to_direct(self) -> None:
        """ko_type='none' with ko tag still works (falls back to direct)."""
        response = _mock_response(top_move="D1", top_winrate=0.95)
        result = validate_correct_move(
            response=response,
            correct_move_gtp="D1",
            tags=[12],
            ko_type="none",
        )
        assert result.status == ValidationStatus.ACCEPTED

    def test_ko_type_invalid_defaults_to_direct(self) -> None:
        """Invalid ko_type string falls back to DIRECT gracefully."""
        response = _mock_response(top_move="D1", top_winrate=0.95)
        result = validate_correct_move(
            response=response,
            correct_move_gtp="D1",
            tags=[12],
            ko_type="bogus_value",
        )
        assert result.status == ValidationStatus.ACCEPTED

    def test_non_ko_tag_ignores_ko_type(self) -> None:
        """ko_type is ignored when dispatch doesn't route to ko validator."""
        response = _mock_response(top_move="D1", top_winrate=0.95)
        result = validate_correct_move(
            response=response,
            correct_move_gtp="D1",
            tags=[10],  # life-and-death, not ko
            ko_type="direct",
        )
        assert result.validator_used == "life_and_death"


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
class TestIntegrationValidation:
    """Integration tests with real KataGo engine."""

    def test_known_correct_puzzle_validated(self, integration_engine) -> None:
        """Fixture SGF with known-correct solution → status=accepted."""
        from analyzers.query_builder import build_query_from_sgf
        from core.tsumego_analysis import extract_correct_first_move, parse_sgf
        from models.analysis_response import sgf_to_gtp

        # nakade.sgf: 9x9, reliable with b6 model (simpler than simple_life_death)
        sgf = (FIXTURES / "nakade.sgf").read_text(encoding="utf-8")
        root = parse_sgf(sgf)
        correct_sgf = extract_correct_first_move(root)
        assert correct_sgf is not None

        query = build_query_from_sgf(sgf, max_visits=1000)
        correct_gtp = sgf_to_gtp(correct_sgf, query.original_board_size)

        async def _run():
            response = await asyncio.wait_for(
                integration_engine.analyze(query.request), timeout=60.0
            )
            return validate_correct_move(
                response=response,
                correct_move_gtp=correct_gtp,
                tags=[42],  # nakade
                corner="TL",
            )

        result = asyncio.run(_run())
        # A well-known simple life-and-death puzzle should be accepted or flagged
        # (never rejected — the move IS correct even with small model)
        assert result.status in (ValidationStatus.ACCEPTED, ValidationStatus.FLAGGED)

    def test_known_broken_puzzle_rejected(self, integration_engine) -> None:
        """Fixture SGF with wrong solution → status=rejected."""
        from analyzers.query_builder import build_query_from_sgf
        from core.tsumego_analysis import extract_correct_first_move, parse_sgf
        from models.analysis_response import sgf_to_gtp

        sgf = (FIXTURES / "broken_puzzle.sgf").read_text(encoding="utf-8")
        root = parse_sgf(sgf)
        correct_sgf = extract_correct_first_move(root)
        assert correct_sgf is not None

        query = build_query_from_sgf(sgf, max_visits=100)
        correct_gtp = sgf_to_gtp(correct_sgf, query.original_board_size)

        async def _run():
            response = await asyncio.wait_for(
                integration_engine.analyze(query.request), timeout=30.0
            )
            return validate_correct_move(
                response=response,
                correct_move_gtp=correct_gtp,
                tags=[10],
                corner="TL",
            )

        result = asyncio.run(_run())
        # The broken puzzle's "correct" move is nonsensical — should be rejected or flagged
        assert result.status in (ValidationStatus.REJECTED, ValidationStatus.FLAGGED)
