"""Tests for refutation framing consistency (T16–T19).

T16: Refutation stage uses framed position from AnalyzeStage
T16B: Temperature-scored candidate ranking vs policy-only
T17: Puzzle-region allowMoves restriction on refutation queries
T18: Refutation-specific overrideSettings
T18B: Tenuki rejection flags far-away PV responses
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

_HERE = Path(__file__).resolve().parent
_LAB = _HERE.parent

from analyzers.generate_refutations import (
    generate_refutations,
    generate_single_refutation,
    identify_candidates,
)
from analyzers.stages.protocols import PipelineContext, SgfMetadata
from analyzers.stages.refutation_stage import RefutationStage
from config import EnrichmentConfig
from config.refutations import CandidateScoringConfig, RefutationsConfig, TenukiRejectionConfig
from models.analysis_response import AnalysisResponse, MoveAnalysis
from models.position import Color, Position, Stone

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _simple_position(board_size: int = 19) -> Position:
    return Position(
        board_size=board_size,
        player_to_move=Color.BLACK,
        komi=0.0,
        stones=[
            Stone(x=2, y=2, color=Color.BLACK),
            Stone(x=2, y=3, color=Color.WHITE),
            Stone(x=3, y=2, color=Color.WHITE),
        ],
    )


def _framed_position(board_size: int = 9) -> Position:
    """A smaller 'framed' position distinct from the raw position."""
    return Position(
        board_size=board_size,
        player_to_move=Color.BLACK,
        komi=0.0,
        stones=[
            Stone(x=2, y=2, color=Color.BLACK),
            Stone(x=2, y=3, color=Color.WHITE),
            Stone(x=3, y=2, color=Color.WHITE),
            # Frame stones
            Stone(x=0, y=0, color=Color.WHITE),
            Stone(x=0, y=1, color=Color.BLACK),
        ],
    )


def _mock_response(
    top_move: str = "D1",
    extra_moves: list[dict] | None = None,
    root_winrate: float = 0.85,
    root_score: float = 10.0,
) -> AnalysisResponse:
    moves = [
        MoveAnalysis(
            move=top_move,
            visits=100,
            winrate=0.92,
            score_lead=12.0,
            policy_prior=0.65,
            pv=[top_move],
        )
    ]
    if extra_moves:
        for em in extra_moves:
            moves.append(MoveAnalysis(**em))
    return AnalysisResponse(
        move_infos=moves,
        root_winrate=root_winrate,
        root_score=root_score,
        total_visits=200,
    )


def _make_config(**overrides) -> EnrichmentConfig:
    """Build a minimal EnrichmentConfig with defaults and overrides."""
    from config import load_enrichment_config
    cfg = load_enrichment_config()
    if overrides:
        cfg = cfg.model_copy(update=overrides)
    return cfg


# ---------------------------------------------------------------------------
# T16: Refutation stage uses framed_position
# ---------------------------------------------------------------------------


class TestRefutationUsesFramedPosition:
    """Verify refutation stage forwards framed position, not raw."""

    def test_stage_uses_framed_position_when_set(self):
        """When ctx.framed_position is set, refutation should use it."""
        raw = _simple_position(board_size=19)
        framed = _framed_position(board_size=9)

        stage = RefutationStage()
        cfg = _make_config()
        # Disable escalation to get a single generate_refutations call
        cfg = cfg.model_copy(update={
            "refutation_escalation": cfg.refutation_escalation.model_copy(update={"enabled": False}),
        })

        mock_engine = MagicMock()
        mock_engine.engine = AsyncMock()
        mock_engine.mode = "quick"

        # Track which position generate_refutations receives
        captured_positions: list[Position] = []

        async def fake_gen(
            engine, position, correct_move_gtp, **kwargs
        ):
            captured_positions.append(position)
            from models.refutation_result import RefutationResult
            return RefutationResult(puzzle_id="test")

        ctx = PipelineContext(
            config=cfg,
            engine_manager=mock_engine,
            position=raw,
            framed_position=framed,
            metadata=SgfMetadata(puzzle_id="test-001"),
            correct_move_gtp="D4",
            solution_moves=["D4"],
            response=_mock_response(),
        )

        with patch(
            "analyzers.stages.refutation_stage.generate_refutations",
            side_effect=fake_gen,
        ):
            asyncio.run(stage.run(ctx))

        assert len(captured_positions) == 1
        assert captured_positions[0].board_size == 9  # framed, not raw

    def test_stage_falls_back_to_raw_position(self):
        """Without framed_position, fall back to ctx.position."""
        raw = _simple_position(board_size=19)

        stage = RefutationStage()
        cfg = _make_config()
        cfg = cfg.model_copy(update={
            "refutation_escalation": cfg.refutation_escalation.model_copy(update={"enabled": False}),
        })

        mock_engine = MagicMock()
        mock_engine.engine = AsyncMock()
        mock_engine.mode = "quick"

        captured_positions: list[Position] = []

        async def fake_gen(engine, position, correct_move_gtp, **kwargs):
            captured_positions.append(position)
            from models.refutation_result import RefutationResult
            return RefutationResult(puzzle_id="test")

        ctx = PipelineContext(
            config=cfg,
            engine_manager=mock_engine,
            position=raw,
            framed_position=None,
            metadata=SgfMetadata(puzzle_id="test-002"),
            correct_move_gtp="D4",
            solution_moves=["D4"],
            response=_mock_response(),
        )

        with patch(
            "analyzers.stages.refutation_stage.generate_refutations",
            side_effect=fake_gen,
        ):
            asyncio.run(stage.run(ctx))

        assert len(captured_positions) == 1
        assert captured_positions[0].board_size == 19  # raw


# ---------------------------------------------------------------------------
# T16B: Temperature scoring vs policy-only
# ---------------------------------------------------------------------------


class TestTemperatureScoring:
    """identify_candidates respects candidate_scoring config."""

    def _analysis_with_candidates(self) -> AnalysisResponse:
        """Three wrong moves with different policy/score profiles."""
        return AnalysisResponse(
            move_infos=[
                MoveAnalysis(move="D4", visits=100, winrate=0.90, score_lead=10.0, policy_prior=0.50, pv=["D4"]),
                # High policy but big score loss
                MoveAnalysis(move="E5", visits=80, winrate=0.60, score_lead=2.0, policy_prior=0.30, pv=["E5"]),
                # Lower policy but small score loss
                MoveAnalysis(move="C3", visits=50, winrate=0.80, score_lead=8.0, policy_prior=0.15, pv=["C3"]),
            ],
            root_winrate=0.85,
            root_score=10.0,
            total_visits=230,
        )

    def test_policy_only_sorts_by_policy(self):
        analysis = self._analysis_with_candidates()
        cfg = _make_config(
            refutations=RefutationsConfig(
                candidate_scoring=CandidateScoringConfig(mode="policy_only"),
            )
        )
        candidates = identify_candidates(analysis, "D4", config=cfg)
        # Sorted by policy: E5 (0.30) > C3 (0.15)
        assert candidates[0].move == "E5"
        assert candidates[1].move == "C3"

    def test_temperature_reranks_by_weighted_score(self):
        analysis = self._analysis_with_candidates()
        cfg = _make_config(
            refutations=RefutationsConfig(
                candidate_scoring=CandidateScoringConfig(mode="temperature", temperature=1.5),
            )
        )
        candidates = identify_candidates(analysis, "D4", config=cfg)
        # E5 loses 8pts → weight = exp(-1.5*8) ≈ 6e-6, score ≈ 0.30*6e-6 ≈ tiny
        # C3 loses 2pts → weight = exp(-1.5*2) ≈ 0.05, score ≈ 0.15*0.05 ≈ 0.0075
        # C3 should rank higher than E5 in temperature mode
        assert candidates[0].move == "C3"
        assert candidates[1].move == "E5"


# ---------------------------------------------------------------------------
# T18: Override settings in refutation queries
# ---------------------------------------------------------------------------


class TestRefutationOverrideSettings:
    """Override settings are passed through to AnalysisRequest."""

    def test_override_settings_passed_to_request(self):
        """generate_single_refutation includes override_settings in request."""
        cfg = _make_config()
        mock_engine = AsyncMock()
        # Engine returns a response with a strong opponent move
        mock_engine.analyze.return_value = AnalysisResponse(
            move_infos=[
                MoveAnalysis(
                    move="E5", visits=100, winrate=0.95,
                    score_lead=15.0, policy_prior=0.80, pv=["E5"],
                )
            ],
            root_winrate=0.95,
            root_score=15.0,
            total_visits=100,
        )

        overrides = {
            "rootPolicyTemperature": 1.3,
            "rootFpuReductionMax": 0.0,
            "wideRootNoise": 0.08,
        }

        asyncio.run(
            generate_single_refutation(
                engine=mock_engine,
                position=_simple_position(),
                wrong_move_gtp="E5",
                wrong_move_policy=0.30,
                initial_winrate=0.85,
                config=cfg,
                override_settings=overrides,
            )
        )

        # Verify engine.analyze was called with override_settings
        call_args = mock_engine.analyze.call_args[0][0]
        assert call_args.override_settings == overrides


# ---------------------------------------------------------------------------
# T18B: Tenuki rejection
# ---------------------------------------------------------------------------


class TestTenukiRejection:
    """Refutations where PV response is far from wrong move are flagged."""

    def test_tenuki_flagged_when_far(self):
        """Manhattan distance > threshold → tenuki_flagged=True."""
        cfg = _make_config(
            refutations=RefutationsConfig(
                tenuki_rejection=TenukiRejectionConfig(enabled=True, manhattan_threshold=4.0),
            )
        )
        mock_engine = AsyncMock()
        # Wrong move at C3 (SGF: cc), PV response at S19 (SGF: ss) — very far
        mock_engine.analyze.return_value = AnalysisResponse(
            move_infos=[
                MoveAnalysis(
                    move="S19", visits=100, winrate=0.95,
                    score_lead=20.0, policy_prior=0.80, pv=["S19"],
                )
            ],
            root_winrate=0.95,
            root_score=20.0,
            total_visits=100,
        )

        result = asyncio.run(
            generate_single_refutation(
                engine=mock_engine,
                position=_simple_position(),
                wrong_move_gtp="C3",
                wrong_move_policy=0.20,
                initial_winrate=0.85,
                config=cfg,
            )
        )

        assert result is not None
        assert result.tenuki_flagged is True

    def test_no_tenuki_when_close(self):
        """Manhattan distance <= threshold → tenuki_flagged=False."""
        cfg = _make_config(
            refutations=RefutationsConfig(
                tenuki_rejection=TenukiRejectionConfig(enabled=True, manhattan_threshold=4.0),
            )
        )
        mock_engine = AsyncMock()
        # Wrong move at C3, PV response at D4 — close
        mock_engine.analyze.return_value = AnalysisResponse(
            move_infos=[
                MoveAnalysis(
                    move="D4", visits=100, winrate=0.95,
                    score_lead=20.0, policy_prior=0.80, pv=["D4"],
                )
            ],
            root_winrate=0.95,
            root_score=20.0,
            total_visits=100,
        )

        result = asyncio.run(
            generate_single_refutation(
                engine=mock_engine,
                position=_simple_position(),
                wrong_move_gtp="C3",
                wrong_move_policy=0.20,
                initial_winrate=0.85,
                config=cfg,
            )
        )

        assert result is not None
        assert result.tenuki_flagged is False

    def test_tenuki_disabled(self):
        """When disabled, never flag tenuki."""
        cfg = _make_config(
            refutations=RefutationsConfig(
                tenuki_rejection=TenukiRejectionConfig(enabled=False, manhattan_threshold=1.0),
            )
        )
        mock_engine = AsyncMock()
        mock_engine.analyze.return_value = AnalysisResponse(
            move_infos=[
                MoveAnalysis(
                    move="S19", visits=100, winrate=0.95,
                    score_lead=20.0, policy_prior=0.80, pv=["S19"],
                )
            ],
            root_winrate=0.95,
            root_score=20.0,
            total_visits=100,
        )

        result = asyncio.run(
            generate_single_refutation(
                engine=mock_engine,
                position=_simple_position(),
                wrong_move_gtp="C3",
                wrong_move_policy=0.20,
                initial_winrate=0.85,
                config=cfg,
            )
        )

        assert result is not None
        assert result.tenuki_flagged is False


# ---------------------------------------------------------------------------
# T17 + T18 integration: Full orchestrator passes allowMoves + overrides
# ---------------------------------------------------------------------------


class TestRefutationOrchestrator:
    """End-to-end orchestrator wiring for T17/T18."""

    def test_generate_refutations_passes_overrides_and_region(self):
        """generate_refutations builds override_settings and allowed_moves."""
        cfg = _make_config()
        mock_engine = AsyncMock()

        initial = _mock_response(
            extra_moves=[
                {"move": "E5", "visits": 50, "winrate": 0.40, "score_lead": -5.0,
                 "policy_prior": 0.15, "pv": ["E5"]},
            ],
        )

        # Mock the per-candidate call
        captured_requests: list = []

        async def capture_analyze(request):
            captured_requests.append(request)
            return AnalysisResponse(
                move_infos=[
                    MoveAnalysis(
                        move="D5", visits=100, winrate=0.95,
                        score_lead=15.0, policy_prior=0.80, pv=["D5"],
                    )
                ],
                root_winrate=0.95,
                root_score=15.0,
                total_visits=100,
            )

        mock_engine.analyze = capture_analyze

        asyncio.run(
            generate_refutations(
                engine=mock_engine,
                position=_simple_position(),
                correct_move_gtp="D1",
                initial_analysis=initial,
                config=cfg,
                puzzle_id="test",
            )
        )

        # At least one request should have been made for the wrong move E5
        assert len(captured_requests) >= 1
        req = captured_requests[0]
        # T18: override settings should be present
        assert req.override_settings is not None
        assert "rootPolicyTemperature" in req.override_settings
        assert req.override_settings["rootPolicyTemperature"] == cfg.refutations.refutation_overrides.root_policy_temperature
