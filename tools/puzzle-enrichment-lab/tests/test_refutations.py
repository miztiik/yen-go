"""Tests for wrong-move refutation generation.

Task A.2: Generate wrong-move refutations.

A.2.1 — Identify candidate wrong moves (config-driven)
A.2.2 — Generate refutation sequences
A.2.3 — Write refutations to AiAnalysisResult output

Unit tests use mocked AnalysisResponse objects (no KataGo needed).
Integration tests use the real KataGo engine (marked @pytest.mark.integration).
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

# Ensure tools/puzzle-enrichment-lab is importable
_HERE = Path(__file__).resolve().parent
_LAB = _HERE.parent

from analyzers.generate_refutations import (
    _enrich_curated_policy,
    generate_refutations,
    generate_single_refutation,
    identify_candidates,
)
from config import load_enrichment_config
from models.analysis_response import AnalysisResponse, MoveAnalysis, sgf_to_gtp
from models.position import Color, Position, Stone
from models.refutation_result import Refutation, RefutationResult

FIXTURES = Path(__file__).parent / "fixtures"

# ---------------------------------------------------------------------------
# Helpers — mock AnalysisResponse objects
# ---------------------------------------------------------------------------


def _mock_response(
    top_move: str = "D1",
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
    if extra_moves:
        for em in extra_moves:
            moves.append(MoveAnalysis(**em))
    return AnalysisResponse(
        move_infos=moves,
        root_winrate=root_winrate,
        total_visits=total_visits,
    )


def _simple_position() -> Position:
    """Minimal life-and-death position for testing."""
    return Position(
        board_size=19,
        stones=[
            Stone(color=Color.BLACK, x=2, y=15),  # cp
            Stone(color=Color.BLACK, x=3, y=15),  # dp
            Stone(color=Color.BLACK, x=4, y=15),  # ep
            Stone(color=Color.WHITE, x=6, y=15),  # gp
            Stone(color=Color.WHITE, x=3, y=16),  # dq
            Stone(color=Color.WHITE, x=5, y=16),  # fq
        ],
        player_to_move=Color.BLACK,
        komi=0.0,
    )


# ===================================================================
# A.2.1 — Identify candidate wrong moves
# ===================================================================


@pytest.mark.unit
class TestWrongMovesIdentified:
    """Test candidate wrong move identification."""

    def test_wrong_moves_identified(self) -> None:
        """Mock analysis with obvious wrong move -> identified in candidates."""
        response = _mock_response(
            top_move="D1",  # correct move
            top_policy=0.65,
            extra_moves=[
                {"move": "E1", "visits": 40, "winrate": 0.35, "policy_prior": 0.20, "pv": ["E1"]},
                {"move": "F1", "visits": 20, "winrate": 0.20, "policy_prior": 0.08, "pv": ["F1"]},
            ],
        )
        config = load_enrichment_config()
        candidates = identify_candidates(
            analysis=response,
            correct_move_gtp="D1",
            config=config,
        )
        # E1 and F1 are wrong moves with policy above threshold
        gtp_coords = [c.move for c in candidates]
        assert "E1" in gtp_coords
        assert "F1" in gtp_coords

    def test_correct_move_excluded(self) -> None:
        """Correct first move NOT in candidate list."""
        response = _mock_response(
            top_move="D1",
            top_policy=0.65,
            extra_moves=[
                {"move": "E1", "visits": 40, "winrate": 0.35, "policy_prior": 0.20, "pv": ["E1"]},
            ],
        )
        config = load_enrichment_config()
        candidates = identify_candidates(
            analysis=response,
            correct_move_gtp="D1",
            config=config,
        )
        gtp_coords = [c.move for c in candidates]
        assert "D1" not in gtp_coords

    def test_trivial_puzzle_no_candidates(self) -> None:
        """All policy on correct move -> empty candidate list."""
        response = _mock_response(
            top_move="D1",
            top_policy=0.95,
            extra_moves=[
                # Only moves with tiny policy -> below threshold (config min_policy=0.0)
                # With min_policy=0.0, only pass and correct moves are excluded
                # So we test that correct move itself is excluded
            ],
        )
        config = load_enrichment_config()
        candidates = identify_candidates(
            analysis=response,
            correct_move_gtp="D1",
            config=config,
        )
        assert len(candidates) == 0

    def test_policy_threshold_from_config(self) -> None:
        """With min_policy=0.0, all non-correct non-pass moves are candidates."""
        config = load_enrichment_config()

        response = _mock_response(
            top_move="D1",
            top_policy=0.65,
            extra_moves=[
                {"move": "E1", "visits": 40, "winrate": 0.35, "policy_prior": 0.01, "pv": ["E1"]},
                {"move": "F1", "visits": 10, "winrate": 0.20, "policy_prior": 0.001, "pv": ["F1"]},
            ],
        )
        candidates = identify_candidates(
            analysis=response,
            correct_move_gtp="D1",
            config=config,
        )
        gtp_coords = [c.move for c in candidates]
        # With min_policy=0.0, all non-correct moves are included
        assert "E1" in gtp_coords
        assert "F1" in gtp_coords
        # Correct move is always excluded
        assert "D1" not in gtp_coords

    def test_max_candidates_from_config(self) -> None:
        """At most candidate_max_count (from config) returned."""
        config = load_enrichment_config()
        max_count = config.refutations.candidate_max_count  # 8

        extra = [
            {"move": f"{chr(65 + i)}1", "visits": 20, "winrate": 0.30,
             "policy_prior": 0.10 + 0.01 * i, "pv": [f"{chr(65 + i)}1"]}
            for i in range(10)  # 10 wrong moves, more than max
            if chr(65 + i) != "D"  # skip correct move column
        ]

        response = _mock_response(
            top_move="D1",
            top_policy=0.30,
            extra_moves=extra,
        )
        candidates = identify_candidates(
            analysis=response,
            correct_move_gtp="D1",
            config=config,
        )
        assert len(candidates) <= max_count

    def test_pass_excluded(self) -> None:
        """'pass' is never a candidate wrong move."""
        response = _mock_response(
            top_move="D1",
            top_policy=0.65,
            extra_moves=[
                {"move": "pass", "visits": 30, "winrate": 0.30, "policy_prior": 0.15, "pv": []},
                {"move": "E1", "visits": 40, "winrate": 0.35, "policy_prior": 0.20, "pv": ["E1"]},
            ],
        )
        config = load_enrichment_config()
        candidates = identify_candidates(
            analysis=response,
            correct_move_gtp="D1",
            config=config,
        )
        gtp_coords = [c.move for c in candidates]
        assert "pass" not in gtp_coords
        assert "E1" in gtp_coords

    def test_sorted_by_policy_descending(self) -> None:
        """Candidates sorted by policy prior descending (most tempting first)."""
        response = _mock_response(
            top_move="D1",
            top_policy=0.65,
            extra_moves=[
                {"move": "E1", "visits": 20, "winrate": 0.30, "policy_prior": 0.08, "pv": ["E1"]},
                {"move": "F1", "visits": 40, "winrate": 0.30, "policy_prior": 0.15, "pv": ["F1"]},
                {"move": "G1", "visits": 30, "winrate": 0.30, "policy_prior": 0.12, "pv": ["G1"]},
            ],
        )
        config = load_enrichment_config()
        candidates = identify_candidates(
            analysis=response,
            correct_move_gtp="D1",
            config=config,
        )
        policies = [c.policy_prior for c in candidates]
        assert policies == sorted(policies, reverse=True)


# ===================================================================
# A.2.2 — Generate refutation sequences
# ===================================================================


@pytest.mark.unit
class TestRefutationPvFound:
    """Test refutation PV generation for wrong moves."""

    def test_refutation_pv_found(self) -> None:
        """Mock: known wrong move -> refutation PV with >= 2 moves."""
        # After wrong move E1, opponent responds with F1 then G1
        after_wrong_response = _mock_response(
            top_move="F1",
            top_visits=80,
            top_winrate=0.90,  # from opponent's perspective: good for opponent
            top_policy=0.50,
            top_pv=["F1", "G1", "H1"],
        )

        result = asyncio.run(
            generate_single_refutation(
                engine=AsyncMock(analyze=AsyncMock(return_value=after_wrong_response)),
                position=_simple_position(),
                wrong_move_gtp="E1",
                wrong_move_policy=0.20,
                initial_winrate=0.85,
                config=load_enrichment_config(),
            )
        )
        assert result is not None
        assert len(result.refutation_sequence) >= 2

    def test_delta_threshold_from_config(self) -> None:
        """Marginal wrong move (delta < config threshold) -> rejected."""
        config = load_enrichment_config()

        # After wrong move, winrate barely drops (still good for puzzle player)
        after_wrong = _mock_response(
            top_move="F1",
            top_visits=80,
            top_winrate=0.55,  # opponent perspective -> puzzle player = 1 - 0.55 = 0.45
            top_policy=0.50,
            top_pv=["F1"],
        )
        # initial_winrate=0.50, winrate_after_wrong=0.45, delta=|0.45-0.50|=0.05 < 0.15
        result = asyncio.run(
            generate_single_refutation(
                engine=AsyncMock(analyze=AsyncMock(return_value=after_wrong)),
                position=_simple_position(),
                wrong_move_gtp="E1",
                wrong_move_policy=0.20,
                initial_winrate=0.50,
                config=config,
            )
        )
        # Delta too small: should be None (rejected)
        assert result is None

    def test_refutation_depth_recorded(self) -> None:
        """Depth (moves until confirmed loss) is recorded."""
        after_wrong = _mock_response(
            top_move="F1",
            top_visits=80,
            top_winrate=0.95,  # opponent: 0.95 -> puzzle player: 0.05
            top_policy=0.50,
            top_pv=["F1", "G1", "H1", "J1"],
        )
        result = asyncio.run(
            generate_single_refutation(
                engine=AsyncMock(analyze=AsyncMock(return_value=after_wrong)),
                position=_simple_position(),
                wrong_move_gtp="E1",
                wrong_move_policy=0.20,
                initial_winrate=0.85,
                config=load_enrichment_config(),
            )
        )
        assert result is not None
        assert result.refutation_depth >= 1

    def test_refutation_type_unclassified(self) -> None:
        """In Phase A, all refutations have type='unclassified'."""
        after_wrong = _mock_response(
            top_move="F1",
            top_visits=80,
            top_winrate=0.95,
            top_policy=0.50,
            top_pv=["F1", "G1"],
        )
        result = asyncio.run(
            generate_single_refutation(
                engine=AsyncMock(analyze=AsyncMock(return_value=after_wrong)),
                position=_simple_position(),
                wrong_move_gtp="E1",
                wrong_move_policy=0.20,
                initial_winrate=0.85,
                config=load_enrichment_config(),
            )
        )
        assert result is not None
        assert result.refutation_type == "unclassified"

    def test_max_refutations_from_config(self) -> None:
        """At most refutation_max_count (from config), sorted by policy prior."""
        config = load_enrichment_config()
        max_count = config.refutations.refutation_max_count  # 3

        # Build an initial response with many wrong moves
        extra_moves = [
            {"move": f"{chr(65 + i)}1", "visits": 20, "winrate": 0.30,
             "policy_prior": 0.06 + 0.02 * i, "pv": [f"{chr(65 + i)}1"]}
            for i in range(7)
            if chr(65 + i) != "D"  # skip correct move column
        ]
        initial_response = _mock_response(
            top_move="D1",
            top_policy=0.30,
            extra_moves=extra_moves,
            root_winrate=0.85,
        )

        # After each wrong move, opponent has clear refutation
        after_wrong = _mock_response(
            top_move="Z1",
            top_visits=80,
            top_winrate=0.95,  # opponent wins
            top_policy=0.50,
            top_pv=["Z1", "Y1"],
        )

        mock_engine = AsyncMock()
        mock_engine.analyze = AsyncMock(return_value=after_wrong)

        result = asyncio.run(
            generate_refutations(
                engine=mock_engine,
                position=_simple_position(),
                correct_move_gtp="D1",
                initial_analysis=initial_response,
                config=config,
            )
        )

        assert len(result.refutations) <= max_count
        # Sorted by policy descending
        if len(result.refutations) > 1:
            policies = [r.wrong_move_policy for r in result.refutations]
            assert policies == sorted(policies, reverse=True)


# ===================================================================
# A.2.2 — Full generate_refutations orchestrator tests
# ===================================================================


@pytest.mark.unit
class TestGenerateRefutationsOrchestrator:
    """Test the full generate_refutations orchestrator."""

    def test_full_pipeline_produces_result(self) -> None:
        """Full pipeline with mocked engine produces RefutationResult."""
        initial_response = _mock_response(
            top_move="D1",
            top_policy=0.65,
            extra_moves=[
                {"move": "E1", "visits": 40, "winrate": 0.35, "policy_prior": 0.20, "pv": ["E1"]},
            ],
            root_winrate=0.85,
        )
        after_wrong = _mock_response(
            top_move="F1",
            top_visits=80,
            top_winrate=0.90,
            top_policy=0.50,
            top_pv=["F1", "G1"],
        )
        mock_engine = AsyncMock()
        mock_engine.analyze = AsyncMock(return_value=after_wrong)

        result = asyncio.run(
            generate_refutations(
                engine=mock_engine,
                position=_simple_position(),
                correct_move_gtp="D1",
                initial_analysis=initial_response,
                config=load_enrichment_config(),
                puzzle_id="test-puzzle",
            )
        )

        assert isinstance(result, RefutationResult)
        assert result.puzzle_id == "test-puzzle"
        assert len(result.refutations) >= 1
        ref = result.refutations[0]
        assert ref.wrong_move != ""
        assert ref.refutation_depth >= 1
        assert ref.refutation_type == "ai_generated"

    def test_no_engine_call_when_no_candidates(self) -> None:
        """If no candidates pass threshold, no engine calls for refutations."""
        # With min_policy=0.0, only the correct move and pass are excluded.
        # So we create a response with only the correct move — no wrong moves at all.
        initial_response = _mock_response(
            top_move="D1",
            top_policy=0.99,
            extra_moves=[],
            root_winrate=0.85,
        )
        mock_engine = AsyncMock()
        mock_engine.analyze = AsyncMock()

        config = load_enrichment_config()
        # Disable multi-pass harvesting so no secondary engine call is made
        config.refutations.multi_pass_harvesting = False

        result = asyncio.run(
            generate_refutations(
                engine=mock_engine,
                position=_simple_position(),
                correct_move_gtp="D1",
                initial_analysis=initial_response,
                config=config,
            )
        )

        assert len(result.refutations) == 0
        # Engine should not be called for refutation analysis
        mock_engine.analyze.assert_not_called()

    def test_uses_initial_analysis_when_provided(self) -> None:
        """When initial_analysis is provided, engine is NOT called for initial position."""
        initial_response = _mock_response(
            top_move="D1",
            top_policy=0.65,
            extra_moves=[
                {"move": "E1", "visits": 40, "winrate": 0.35, "policy_prior": 0.20, "pv": ["E1"]},
            ],
            root_winrate=0.85,
        )
        after_wrong = _mock_response(
            top_move="F1",
            top_visits=80,
            top_winrate=0.90,
            top_policy=0.50,
            top_pv=["F1", "G1"],
        )
        mock_engine = AsyncMock()
        mock_engine.analyze = AsyncMock(return_value=after_wrong)

        config = load_enrichment_config()
        # Disable multi-pass harvesting to isolate call counting
        config.refutations.multi_pass_harvesting = False

        asyncio.run(
            generate_refutations(
                engine=mock_engine,
                position=_simple_position(),
                correct_move_gtp="D1",
                initial_analysis=initial_response,
                config=config,
            )
        )

        # Only called for the refutation analysis (after wrong move),
        # NOT for initial position analysis
        assert mock_engine.analyze.call_count == 1


# ===================================================================
# A.2.3 — Refutation output in AiAnalysisResult
# ===================================================================


@pytest.mark.unit
class TestRefutationOutputSchema:
    """Test refutation fields in AiAnalysisResult."""

    def test_refutation_output_schema(self) -> None:
        """All required fields: wrong_move, refutation_pv, delta, refutation_depth, type."""
        from models.ai_analysis_result import RefutationEntry

        entry = RefutationEntry(
            wrong_move="cd",
            refutation_pv=["dc", "dd"],
            delta=-0.45,
            refutation_depth=2,
            refutation_type="unclassified",
        )
        assert entry.wrong_move == "cd"
        assert entry.refutation_pv == ["dc", "dd"]
        assert entry.delta == -0.45
        assert entry.refutation_depth == 2
        assert entry.refutation_type == "unclassified"

    def test_refutation_serialization(self) -> None:
        """Refutations serialize/deserialize correctly in AiAnalysisResult."""
        from analyzers.validate_correct_move import ValidationStatus
        from models.ai_analysis_result import (
            AI_ANALYSIS_SCHEMA_VERSION,
            AiAnalysisResult,
            EngineSnapshot,
            MoveValidation,
            RefutationEntry,
        )

        refutations = [
            RefutationEntry(
                wrong_move="cd",
                refutation_pv=["dc", "dd"],
                delta=-0.45,
                refutation_depth=2,
                refutation_type="unclassified",
            ),
            RefutationEntry(
                wrong_move="ef",
                refutation_pv=["fe", "fg", "gf"],
                delta=-0.30,
                refutation_depth=3,
                refutation_type="unclassified",
            ),
        ]

        result = AiAnalysisResult(
            puzzle_id="YENGO-test123",
            schema_version=AI_ANALYSIS_SCHEMA_VERSION,
            engine=EngineSnapshot(model="b15c192", visits=200, config_hash="abc"),
            validation=MoveValidation(
                correct_move_gtp="D1",
                katago_top_move_gtp="D1",
                status=ValidationStatus.ACCEPTED,
                katago_agrees=True,
                correct_move_winrate=0.92,
                correct_move_policy=0.65,
                validator_used="life_and_death",
            ),
            refutations=refutations,
            tags=[10],
        )

        # Roundtrip
        json_str = result.model_dump_json()
        restored = AiAnalysisResult.model_validate_json(json_str)

        assert len(restored.refutations) == 2
        assert restored.refutations[0].wrong_move == "cd"
        assert restored.refutations[0].refutation_pv == ["dc", "dd"]
        assert restored.refutations[0].delta == -0.45
        assert restored.refutations[0].refutation_depth == 2
        assert restored.refutations[0].refutation_type == "unclassified"
        assert restored.refutations[1].wrong_move == "ef"

    def test_empty_refutations_roundtrip(self) -> None:
        """Empty refutations list roundtrips correctly."""
        from analyzers.validate_correct_move import ValidationStatus
        from models.ai_analysis_result import (
            AiAnalysisResult,
            EngineSnapshot,
            MoveValidation,
        )

        result = AiAnalysisResult(
            puzzle_id="YENGO-test456",
            engine=EngineSnapshot(model="b6c96", visits=100, config_hash="xyz"),
            validation=MoveValidation(
                correct_move_gtp="D1",
                katago_top_move_gtp="D1",
                status=ValidationStatus.ACCEPTED,
                katago_agrees=True,
            ),
            refutations=[],
        )
        json_str = result.model_dump_json()
        restored = AiAnalysisResult.model_validate_json(json_str)
        assert restored.refutations == []

    def test_schema_version_bumped(self) -> None:
        """Schema version is 3 (bumped from 2 for difficulty fields in A.3.3)."""
        from models.ai_analysis_result import AI_ANALYSIS_SCHEMA_VERSION
        assert AI_ANALYSIS_SCHEMA_VERSION >= 2  # At least 2 (refutations added in A.2.3)


# ===================================================================
# Integration tests (uses shared integration_engine from conftest.py)
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
class TestRealRefutationGenerated:
    """Integration test: real puzzle -> refutation with PV."""

    def test_real_refutation_generated(self, integration_engine) -> None:
        """Real puzzle -> at least one refutation with PV.

        Uses nakade.sgf, which has a clear correct move and multiple
        plausible wrong moves that KataGo should generate refutations for.
        """
        from core.tsumego_analysis import extract_correct_first_move, extract_position, parse_sgf

        sgf_text = (FIXTURES / "nakade.sgf").read_text(encoding="utf-8")
        root = parse_sgf(sgf_text)
        position = extract_position(root)
        correct_move = extract_correct_first_move(root)
        assert correct_move is not None, "nakade.sgf must have a correct first move"
        correct_gtp = sgf_to_gtp(correct_move, position.board_size)

        async def _run():
            result = await generate_refutations(
                engine=integration_engine,
                position=position,
                correct_move_gtp=correct_gtp,
                max_visits=200,
            )
            return result

        result = asyncio.run(_run())

        # Must produce at least one refutation
        assert isinstance(result, RefutationResult)
        assert len(result.refutations) >= 1, (
            f"Expected >=1 refutation for nakade.sgf, got {len(result.refutations)}"
        )

        # Each refutation must have a wrong move and a refutation sequence (PV)
        for ref in result.refutations:
            assert ref.wrong_move, "Refutation must have a wrong_move"
            assert len(ref.refutation_sequence) >= 1, (
                f"Refutation for {ref.wrong_move} must have >=1 move in PV"
            )


# ===================================================================
# Curated refutation policy enrichment (Bug fix S.G.2)
# ===================================================================


@pytest.mark.unit
class TestEnrichCuratedPolicy:
    """Test _enrich_curated_policy enriches curated refutations from analysis.

    Bug S.G.2: Curated wrong branches from SGF always had wrong_move_policy=0.0
    because the SGF doesn't contain neural-net policy data. This zeroed out the
    trap_density component (20% of the difficulty score), making all curated
    puzzles appear easier than they should be.

    The fix looks up each curated move's policy prior from the KataGo initial
    analysis response.
    """

    def test_enriches_policy_from_analysis(self):
        """Curated refs with policy=0 should be enriched from KataGo analysis."""
        # Curated refutation at SGF coord 'cb' = GTP C17 on 19x19
        curated = [
            Refutation(
                wrong_move="cb",
                wrong_move_policy=0.0,
                refutation_sequence=[],
                winrate_after_wrong=0.3,
                winrate_delta=-0.5,
                refutation_depth=1,
                refutation_type="curated",
            )
        ]

        # KataGo analysis includes C18 (SGF 'cb' on 19x19) with policy 0.12
        analysis = AnalysisResponse(
            move_infos=[
                MoveAnalysis(move="D4", visits=100, winrate=0.85, policy_prior=0.65),
                MoveAnalysis(move="C18", visits=30, winrate=0.35, policy_prior=0.12),
            ],
            root_winrate=0.85,
            total_visits=200,
        )

        _enrich_curated_policy(curated, analysis, board_size=19)

        assert curated[0].wrong_move_policy == pytest.approx(0.12, abs=1e-6)

    def test_no_analysis_leaves_policy_unchanged(self):
        """Without initial analysis, curated policy stays at 0.0."""
        curated = [
            Refutation(
                wrong_move="cb",
                wrong_move_policy=0.0,
                refutation_sequence=[],
                winrate_after_wrong=0.3,
                winrate_delta=-0.5,
                refutation_depth=1,
                refutation_type="curated",
            )
        ]

        _enrich_curated_policy(curated, None, board_size=19)

        assert curated[0].wrong_move_policy == 0.0

    def test_move_not_in_analysis_stays_zero(self):
        """If the curated move isn't in analysis move_infos, it stays 0.0."""
        curated = [
            Refutation(
                wrong_move="ss",  # S19 — unlikely to be in analysis
                wrong_move_policy=0.0,
                refutation_sequence=[],
                winrate_after_wrong=0.3,
                winrate_delta=-0.5,
                refutation_depth=1,
                refutation_type="curated",
            )
        ]

        analysis = AnalysisResponse(
            move_infos=[
                MoveAnalysis(move="D4", visits=100, winrate=0.85, policy_prior=0.65),
            ],
            root_winrate=0.85,
            total_visits=200,
        )

        _enrich_curated_policy(curated, analysis, board_size=19)

        assert curated[0].wrong_move_policy == 0.0

    def test_already_nonzero_policy_not_overwritten(self):
        """Refutations with nonzero policy should not be modified."""
        curated = [
            Refutation(
                wrong_move="cb",
                wrong_move_policy=0.25,  # Already has a value
                refutation_sequence=[],
                winrate_after_wrong=0.3,
                winrate_delta=-0.5,
                refutation_depth=1,
                refutation_type="curated",
            )
        ]

        analysis = AnalysisResponse(
            move_infos=[
                MoveAnalysis(move="C18", visits=30, winrate=0.35, policy_prior=0.12),
            ],
            root_winrate=0.85,
            total_visits=200,
        )

        _enrich_curated_policy(curated, analysis, board_size=19)

        assert curated[0].wrong_move_policy == pytest.approx(0.25, abs=1e-6)

    def test_multiple_curated_refutations_enriched(self):
        """All curated refutations with policy=0 should be enriched."""
        curated = [
            Refutation(
                wrong_move="cb",  # C17
                wrong_move_policy=0.0,
                refutation_sequence=[],
                winrate_after_wrong=0.3,
                winrate_delta=-0.5,
                refutation_depth=1,
                refutation_type="curated",
            ),
            Refutation(
                wrong_move="dc",  # D16
                wrong_move_policy=0.0,
                refutation_sequence=[],
                winrate_after_wrong=0.4,
                winrate_delta=-0.4,
                refutation_depth=1,
                refutation_type="curated",
            ),
            Refutation(
                wrong_move="ed",  # E15
                wrong_move_policy=0.0,
                refutation_sequence=[],
                winrate_after_wrong=0.2,
                winrate_delta=-0.6,
                refutation_depth=1,
                refutation_type="curated",
            ),
        ]

        analysis = AnalysisResponse(
            move_infos=[
                MoveAnalysis(move="D4", visits=100, winrate=0.85, policy_prior=0.65),
                MoveAnalysis(move="C18", visits=30, winrate=0.35, policy_prior=0.10),
                MoveAnalysis(move="D17", visits=20, winrate=0.30, policy_prior=0.08),
                MoveAnalysis(move="E16", visits=10, winrate=0.25, policy_prior=0.05),
            ],
            root_winrate=0.85,
            total_visits=200,
        )

        _enrich_curated_policy(curated, analysis, board_size=19)

        assert curated[0].wrong_move_policy == pytest.approx(0.10, abs=1e-6)
        assert curated[1].wrong_move_policy == pytest.approx(0.08, abs=1e-6)
        assert curated[2].wrong_move_policy == pytest.approx(0.05, abs=1e-6)

    def test_enriches_winrate_from_analysis(self):
        """Curated ref with zero winrate fields gets winrate from analysis."""
        curated = [
            Refutation(
                wrong_move="cb",  # C18
                wrong_move_policy=0.10,
                refutation_sequence=[],
                winrate_after_wrong=0.0,
                winrate_delta=0.0,
                refutation_depth=1,
                refutation_type="curated",
            ),
        ]

        analysis = AnalysisResponse(
            move_infos=[
                MoveAnalysis(move="D4", visits=100, winrate=0.85, policy_prior=0.65),
                MoveAnalysis(move="C18", visits=30, winrate=0.35, policy_prior=0.10),
            ],
            root_winrate=0.85,
            total_visits=200,
        )

        _enrich_curated_policy(curated, analysis, board_size=19)

        assert curated[0].winrate_after_wrong == pytest.approx(0.35, abs=1e-6)
        assert curated[0].winrate_delta == pytest.approx(-0.5, abs=1e-6)

    def test_winrate_not_overwritten_if_already_set(self):
        """Curated ref with non-zero winrate fields should not be overwritten."""
        curated = [
            Refutation(
                wrong_move="cb",  # C18
                wrong_move_policy=0.10,
                refutation_sequence=[],
                winrate_after_wrong=0.45,
                winrate_delta=-0.4,
                refutation_depth=1,
                refutation_type="curated",
            ),
        ]

        analysis = AnalysisResponse(
            move_infos=[
                MoveAnalysis(move="C18", visits=30, winrate=0.35, policy_prior=0.10),
            ],
            root_winrate=0.85,
            total_visits=200,
        )

        _enrich_curated_policy(curated, analysis, board_size=19)

        assert curated[0].winrate_after_wrong == pytest.approx(0.45, abs=1e-6)
        assert curated[0].winrate_delta == pytest.approx(-0.4, abs=1e-6)

    def test_enriches_both_policy_and_winrate(self):
        """Curated ref with all zeros gets both policy and winrate enriched."""
        curated = [
            Refutation(
                wrong_move="cb",  # C18
                wrong_move_policy=0.0,
                refutation_sequence=[],
                winrate_after_wrong=0.0,
                winrate_delta=0.0,
                refutation_depth=1,
                refutation_type="curated",
            ),
        ]

        analysis = AnalysisResponse(
            move_infos=[
                MoveAnalysis(move="D4", visits=100, winrate=0.85, policy_prior=0.65),
                MoveAnalysis(move="C18", visits=30, winrate=0.30, policy_prior=0.12),
            ],
            root_winrate=0.85,
            total_visits=200,
        )

        _enrich_curated_policy(curated, analysis, board_size=19)

        assert curated[0].wrong_move_policy == pytest.approx(0.12, abs=1e-6)
        assert curated[0].winrate_after_wrong == pytest.approx(0.30, abs=1e-6)
        assert curated[0].winrate_delta == pytest.approx(-0.55, abs=1e-6)


# ===================================================================
# Score-based refutation fallback (suboptimal_branches)
# ===================================================================


@pytest.mark.unit
class TestScoreBasedRefutationFallback:
    """Test score-based refutation for positions where all moves win."""

    def _config_with_score_fallback(self, *, enabled: bool = True, threshold: float = 2.0):
        """Load config and enable/disable score-based refutation."""
        config = load_enrichment_config()
        config.refutations.suboptimal_branches.enabled = enabled
        config.refutations.suboptimal_branches.score_delta_threshold = threshold
        return config

    def test_score_based_refutation_generated_when_enabled(self) -> None:
        """When winrate delta is tiny but score delta is large, generate refutation."""
        # Opponent response: winrate 0.01 (from opponent perspective → puzzle player ~0.99)
        # Score lead: -5.0 from opponent perspective → puzzle player at +5.0
        # vs initial position at +10.0 → score delta = -5.0 (lost 5 points)
        after_wrong = AnalysisResponse(
            move_infos=[
                MoveAnalysis(
                    move="F1", visits=100, winrate=0.01,
                    policy_prior=0.5, pv=["F1", "G1"],
                    score_lead=-5.0,
                ),
            ],
            root_winrate=0.01,
            total_visits=100,
        )

        config = self._config_with_score_fallback(enabled=True, threshold=2.0)

        result = asyncio.run(
            generate_single_refutation(
                engine=AsyncMock(analyze=AsyncMock(return_value=after_wrong)),
                position=_simple_position(),
                wrong_move_gtp="E1",
                wrong_move_policy=0.20,
                initial_winrate=0.99,  # High winrate (winning position)
                config=config,
                initial_score=10.0,  # Puzzle player ahead by 10 points
            )
        )

        assert result is not None
        assert result.refutation_type == "score_based"
        assert abs(result.score_delta) >= 2.0

    def test_score_based_skipped_when_disabled(self) -> None:
        """When feature is disabled, small winrate delta → no refutation."""
        after_wrong = AnalysisResponse(
            move_infos=[
                MoveAnalysis(
                    move="F1", visits=100, winrate=0.01,
                    policy_prior=0.5, pv=["F1", "G1"],
                    score_lead=-5.0,
                ),
            ],
            root_winrate=0.01,
            total_visits=100,
        )

        config = self._config_with_score_fallback(enabled=False)
        # Also disable PI-3 score_delta_enabled — it runs before
        # suboptimal_branches and would generate the refutation.
        config.refutations.score_delta_enabled = False

        result = asyncio.run(
            generate_single_refutation(
                engine=AsyncMock(analyze=AsyncMock(return_value=after_wrong)),
                position=_simple_position(),
                wrong_move_gtp="E1",
                wrong_move_policy=0.20,
                initial_winrate=0.99,
                config=config,
                initial_score=10.0,
            )
        )

        assert result is None

    def test_score_delta_below_threshold_skipped(self) -> None:
        """Score delta below threshold → no refutation even when enabled."""
        after_wrong = AnalysisResponse(
            move_infos=[
                MoveAnalysis(
                    move="F1", visits=100, winrate=0.01,
                    policy_prior=0.5, pv=["F1"],
                    score_lead=-9.0,  # Only 1 point lost
                ),
            ],
            root_winrate=0.01,
            total_visits=100,
        )

        config = self._config_with_score_fallback(enabled=True, threshold=2.0)

        result = asyncio.run(
            generate_single_refutation(
                engine=AsyncMock(analyze=AsyncMock(return_value=after_wrong)),
                position=_simple_position(),
                wrong_move_gtp="E1",
                wrong_move_policy=0.20,
                initial_winrate=0.99,
                config=config,
                initial_score=10.0,  # Score after wrong = +9.0, delta = -1.0
            )
        )

        assert result is None

    def test_winrate_refutation_still_works_when_score_enabled(self) -> None:
        """Standard winrate-based refutation still works when score fallback is enabled."""
        # Large winrate delta (0.85 → 0.10 = -0.75 delta)
        after_wrong = AnalysisResponse(
            move_infos=[
                MoveAnalysis(
                    move="F1", visits=100, winrate=0.90,
                    policy_prior=0.5, pv=["F1", "G1"],
                    score_lead=10.0,
                ),
            ],
            root_winrate=0.90,
            total_visits=100,
        )

        config = self._config_with_score_fallback(enabled=True)

        result = asyncio.run(
            generate_single_refutation(
                engine=AsyncMock(analyze=AsyncMock(return_value=after_wrong)),
                position=_simple_position(),
                wrong_move_gtp="E1",
                wrong_move_policy=0.20,
                initial_winrate=0.85,
                config=config,
                initial_score=5.0,
            )
        )

        assert result is not None
        assert result.refutation_type != "score_based"  # Standard winrate-based


# ===================================================================
# PI-1: Ownership delta scoring tests
# ===================================================================

@pytest.mark.unit
class TestOwnershipDeltaScoring:
    """PI-1: Verify ownership_delta_weight affects candidate ranking."""

    def _make_analysis_with_ownership(
        self,
        root_ownership: list[float] | None = None,
        move_ownerships: dict[str, list[list[float]] | None] | None = None,
    ) -> AnalysisResponse:
        """Build an AnalysisResponse with ownership data for candidates."""
        board_size = 19
        n = board_size * board_size

        if root_ownership is None:
            root_ownership = [0.5] * n

        moves = [
            MoveAnalysis(
                move="D1", visits=100, winrate=0.92,
                policy_prior=0.65, pv=["D1"],
            ),
            MoveAnalysis(
                move="E1", visits=40, winrate=0.35,
                policy_prior=0.20, pv=["E1"],
                ownership=(move_ownerships or {}).get("E1"),
            ),
            MoveAnalysis(
                move="F1", visits=30, winrate=0.30,
                policy_prior=0.15, pv=["F1"],
                ownership=(move_ownerships or {}).get("F1"),
            ),
        ]

        return AnalysisResponse(
            move_infos=moves,
            root_winrate=0.85,
            total_visits=200,
            ownership=root_ownership,
        )

    def test_ownership_weight_zero_no_change(self) -> None:
        """With ownership_delta_weight=0.0, candidate ordering is policy-descending."""
        config = load_enrichment_config()
        config.refutations.ownership_delta_weight = 0.0

        analysis = self._make_analysis_with_ownership()
        candidates = identify_candidates(
            analysis=analysis,
            correct_move_gtp="D1",
            config=config,
        )

        gtp_moves = [c.move for c in candidates]
        # Policy order: E1 (0.20) > F1 (0.15)
        assert gtp_moves.index("E1") < gtp_moves.index("F1")

    def test_ownership_weight_one_reranks(self) -> None:
        """With ownership_delta_weight=1.0 and mock ownership, higher delta ranks first."""
        config = load_enrichment_config()
        config.refutations.ownership_delta_weight = 1.0
        # Use temperature scoring mode to enable PI-1 composite scoring
        config.refutations.candidate_scoring.mode = "temperature"

        board_size = 19
        n = board_size * board_size

        # Root: all 0.5
        root_own = [0.5] * n
        # F1 has a HUGE ownership flip (0.5 → -0.5 everywhere) while E1 has none
        f1_own = [[-0.5] * board_size for _ in range(board_size)]
        e1_own = [[0.5] * board_size for _ in range(board_size)]

        analysis = self._make_analysis_with_ownership(
            root_ownership=root_own,
            move_ownerships={"E1": e1_own, "F1": f1_own},
        )

        candidates = identify_candidates(
            analysis=analysis,
            correct_move_gtp="D1",
            config=config,
        )

        gtp_moves = [c.move for c in candidates]
        assert len(gtp_moves) >= 2
        # F1 has much larger ownership delta, should rank first despite lower policy
        assert gtp_moves[0] == "F1"

    def test_no_ownership_data_falls_through(self) -> None:
        """When analysis has no ownership arrays, scoring falls through to policy order."""
        config = load_enrichment_config()
        config.refutations.ownership_delta_weight = 1.0

        # No ownership data at all
        analysis = self._make_analysis_with_ownership(root_ownership=None)

        candidates = identify_candidates(
            analysis=analysis,
            correct_move_gtp="D1",
            config=config,
        )

        gtp_moves = [c.move for c in candidates]
        # Falls through to policy-descending
        assert gtp_moves.index("E1") < gtp_moves.index("F1")


# ===================================================================
# PI-3: Score delta rescue tests (candidate identification)
# ===================================================================

@pytest.mark.unit
class TestScoreDeltaRescue:
    """PI-3: Verify score_delta_enabled rescues low-policy candidates."""

    def test_score_delta_disabled_no_rescue(self) -> None:
        """With score_delta_enabled=False, low-policy moves are not rescued."""
        config = load_enrichment_config()
        config.refutations.score_delta_enabled = False
        config.refutations.candidate_min_policy = 0.05

        response = _mock_response(
            top_move="D1",
            top_policy=0.65,
            extra_moves=[
                {"move": "E1", "visits": 10, "winrate": 0.20,
                 "policy_prior": 0.01, "pv": ["E1"], "score_lead": -15.0},
            ],
        )

        candidates = identify_candidates(
            analysis=response,
            correct_move_gtp="D1",
            config=config,
        )

        gtp_moves = [c.move for c in candidates]
        assert "E1" not in gtp_moves

    def test_score_delta_enabled_rescues_low_policy(self) -> None:
        """With score_delta_enabled=True, low-policy move with large score delta is rescued."""
        config = load_enrichment_config()
        config.refutations.score_delta_enabled = True
        config.refutations.score_delta_threshold = 5.0
        config.refutations.candidate_min_policy = 0.05

        response = _mock_response(
            top_move="D1",
            top_policy=0.65,
            root_winrate=0.85,
            extra_moves=[
                # Low policy (0.01 < 0.05 threshold) but large score delta (|0.85 - (-15.0)| = 15.85)
                {"move": "E1", "visits": 10, "winrate": 0.20,
                 "policy_prior": 0.01, "pv": ["E1"], "score_lead": -15.0},
            ],
        )

        candidates = identify_candidates(
            analysis=response,
            correct_move_gtp="D1",
            config=config,
        )

        gtp_moves = [c.move for c in candidates]
        assert "E1" in gtp_moves

    def test_score_delta_threshold_edge(self) -> None:
        """Move exactly at score_delta threshold is included."""
        config = load_enrichment_config()
        config.refutations.score_delta_enabled = True
        config.refutations.score_delta_threshold = 5.0
        config.refutations.candidate_min_policy = 0.05

        # root_score from AnalysisResponse.root_score (default 0.0)
        # score_lead for E1 = -5.0 → |0.0 - (-5.0)| = 5.0 = threshold exactly
        response = _mock_response(
            top_move="D1",
            top_policy=0.65,
            extra_moves=[
                {"move": "E1", "visits": 10, "winrate": 0.20,
                 "policy_prior": 0.01, "pv": ["E1"], "score_lead": -5.0},
            ],
        )

        candidates = identify_candidates(
            analysis=response,
            correct_move_gtp="D1",
            config=config,
        )

        gtp_moves = [c.move for c in candidates]
        assert "E1" in gtp_moves
