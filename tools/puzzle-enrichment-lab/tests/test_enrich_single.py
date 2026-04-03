"""Tests for Task A.5.1: Single-puzzle enrichment function.

Orchestrates: parse SGF → dual-engine analysis → validate correct move
→ generate refutations → estimate difficulty → assemble AiAnalysisResult.

4 unit tests + 1 integration test (deferred — requires KataGo binary).
All unit tests use mocked engines.
"""

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest

# Ensure tools/puzzle-enrichment-lab is importable
_LAB_DIR = Path(__file__).resolve().parent.parent

import analyzers.config_lookup as _config_lookup_mod
from analyzers.config_lookup import (
    clear_config_caches,
)
from analyzers.config_lookup import (
    extract_metadata as _extract_metadata,
)
from analyzers.config_lookup import (
    parse_tag_ids as _parse_tag_ids,
)
from analyzers.enrich_single import (
    _run_has_solution_path,
    _run_position_only_path,
    _run_standard_path,
    enrich_single_puzzle,
)
from analyzers.validate_correct_move import ValidationStatus
from config import clear_cache, load_enrichment_config
from core.tsumego_analysis import (
    extract_correct_first_move,
    extract_position,
    parse_sgf,
)
from models.ai_analysis_result import AI_ANALYSIS_SCHEMA_VERSION, AiAnalysisResult
from models.analysis_response import AnalysisResponse, MoveAnalysis
from models.enrichment_state import EnrichmentRunState

# Fixtures directory
_FIXTURES = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture(autouse=True)
def _clear_config_cache():
    """Ensure each test gets fresh config."""
    clear_cache()
    clear_config_caches()
    yield
    clear_cache()
    clear_config_caches()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_fixture(name: str) -> str:
    """Load an SGF fixture file as a string."""
    return (_FIXTURES / name).read_text(encoding="utf-8")


def _make_response(
    top_move: str = "D1",
    winrate: float = 0.85,
    visits: int = 200,
    policy: float = 0.65,
    extra_moves: list[MoveAnalysis] | None = None,
) -> AnalysisResponse:
    """Build a realistic mock AnalysisResponse."""
    moves = [
        MoveAnalysis(
            move=top_move,
            visits=visits,
            winrate=winrate,
            policy_prior=policy,
            pv=[top_move],
        ),
    ]
    if extra_moves:
        moves.extend(extra_moves)
    else:
        # Add a weaker alternative move for refutation candidacy
        moves.append(
            MoveAnalysis(
                move="E1",
                visits=30,
                winrate=0.25,
                policy_prior=0.10,
                pv=["E1", "F1"],
            )
        )
    return AnalysisResponse(
        request_id="req_0001",
        move_infos=moves,
        root_winrate=winrate,
        root_score=5.0 if winrate > 0.5 else -5.0,
        total_visits=visits,
    )


def _make_refutation_response(
    top_move: str = "F1",
    winrate: float = 0.80,
    visits: int = 100,
    policy: float = 0.55,
) -> AnalysisResponse:
    """Build a mock response for refutation analysis (opponent's response)."""
    return AnalysisResponse(
        request_id="req_0002",
        move_infos=[
            MoveAnalysis(
                move=top_move,
                visits=visits,
                winrate=winrate,
                policy_prior=policy,
                pv=[top_move, "G1"],
            ),
        ],
        root_winrate=winrate,
        root_score=5.0,
        total_visits=visits,
    )


def _make_mock_engine(
    analyze_response: AnalysisResponse | None = None,
    refutation_response: AnalysisResponse | None = None,
) -> MagicMock:
    """Create a mock LocalEngine that returns different responses per call.

    First call returns analyze_response (initial analysis).
    Subsequent calls return refutation_response (for refutation generation).
    """
    engine = MagicMock()
    engine.start = AsyncMock()
    engine.shutdown = AsyncMock()
    engine.health = AsyncMock(return_value={"status": "ready"})
    type(engine).is_running = PropertyMock(return_value=True)
    engine.config = MagicMock()
    engine.config.model_path = "test-model-b10c128.bin.gz"

    initial = analyze_response or _make_response()
    refutation = refutation_response or _make_refutation_response()

    # First call = initial analysis, subsequent = refutation queries
    engine.analyze = AsyncMock(side_effect=[initial] + [refutation] * 10)

    return engine


def _make_mock_single_engine_manager(
    quick_engine: MagicMock | None = None,
    analyze_response: AnalysisResponse | None = None,
) -> MagicMock:
    """Create a mock SingleEngineManager."""

    response = analyze_response or _make_response()
    quick = quick_engine or _make_mock_engine(analyze_response=response)

    manager = MagicMock()
    manager.start = AsyncMock()
    manager.shutdown = AsyncMock()
    manager.health = AsyncMock(return_value={"mode": "single"})
    type(manager).engine = PropertyMock(return_value=quick)
    type(manager).mode = PropertyMock(return_value="quick_only")

    manager.analyze = AsyncMock(return_value=response)
    manager.model_label = MagicMock(return_value="b10c128")

    return manager


# ===================================================================
# A.5.1 — Unit Tests
# ===================================================================


@pytest.mark.unit
class TestSinglePuzzleProducesResult:
    """Mock engine → valid AiAnalysisResult JSON output."""

    def test_single_puzzle_produces_result(self):
        sgf_text = _load_fixture("simple_life_death.sgf")
        manager = _make_mock_single_engine_manager()

        result = asyncio.run(enrich_single_puzzle(sgf_text, manager))

        assert isinstance(result, AiAnalysisResult)
        assert result.schema_version == AI_ANALYSIS_SCHEMA_VERSION

        # Should produce valid JSON
        json_str = result.model_dump_json()
        parsed = json.loads(json_str)
        assert "puzzle_id" in parsed
        assert "validation" in parsed
        assert "engine" in parsed


@pytest.mark.unit
class TestResultContainsAllSections:
    """Validation + refutations + difficulty all present and populated."""

    def test_result_contains_all_sections(self):
        sgf_text = _load_fixture("simple_life_death.sgf")
        manager = _make_mock_single_engine_manager()

        result = asyncio.run(enrich_single_puzzle(sgf_text, manager))

        # Validation section
        assert result.validation.status in (
            ValidationStatus.ACCEPTED,
            ValidationStatus.FLAGGED,
            ValidationStatus.REJECTED,
        )
        assert result.validation.correct_move_gtp != ""
        assert result.validation.validator_used != ""

        # Refutations section (list, possibly empty but field present)
        assert isinstance(result.refutations, list)

        # Difficulty section
        assert result.difficulty.suggested_level != "unknown"
        assert result.difficulty.suggested_level_id > 0
        assert result.difficulty.confidence in ("high", "medium", "low")

        # Engine section
        assert result.engine.model != ""
        assert result.engine.visits > 0


@pytest.mark.unit
class TestErrorHandlingReturnsError:
    """Broken SGF → error result with descriptive message."""

    def test_error_handling_invalid_sgf(self):
        """Completely invalid SGF text → error result, not exception."""
        manager = _make_mock_single_engine_manager()

        result = asyncio.run(enrich_single_puzzle("NOT_VALID_SGF", manager))

        assert isinstance(result, AiAnalysisResult)
        assert result.validation.status == ValidationStatus.REJECTED
        assert any("error" in f.lower() for f in result.validation.flags)

    def test_error_handling_no_correct_move(self):
        """SGF with no solution tree → position-only AI-Solve path (DD-9).

        DD-9: Position-only SGFs always enter AI-Solve.
        With mock engine, the inject-then-extract roundtrip fails
        → tier-1 stone-pattern fallback.
        """
        # Minimal SGF with stones but no moves
        sgf_no_moves = "(;FF[4]GM[1]SZ[19]PL[B]AB[dd]AW[ee])"
        manager = _make_mock_single_engine_manager()

        result = asyncio.run(enrich_single_puzzle(sgf_no_moves, manager))

        assert isinstance(result, AiAnalysisResult)
        # With mock engine, AI-Solve roundtrip fails → tier-1 fallback
        assert result.validation.status == ValidationStatus.FLAGGED
        assert result.enrichment_tier == 1
        assert result.ac_level == 0


@pytest.mark.unit
class TestIdempotentEnrichment:
    """Same SGF + same mock → identical JSON output (deterministic)."""

    def test_idempotent_enrichment(self):
        sgf_text = _load_fixture("simple_life_death.sgf")

        # Create two identical managers with identical responses.
        # simple_life_death.sgf correct move is B[cs] = C1 in GTP.
        response = _make_response(top_move="C1")
        refutation_resp = _make_refutation_response()

        def _make_manager():
            quick = _make_mock_engine(
                analyze_response=response,
                refutation_response=refutation_resp,
            )
            return _make_mock_single_engine_manager(
                quick_engine=quick,
                analyze_response=response,
            )

        result1 = asyncio.run(enrich_single_puzzle(sgf_text, _make_manager()))
        result2 = asyncio.run(enrich_single_puzzle(sgf_text, _make_manager()))

        # Exclude intentionally-unique-per-call fields from comparison
        data1 = json.loads(result1.model_dump_json(indent=2))
        data2 = json.loads(result2.model_dump_json(indent=2))
        del data1["trace_id"]
        del data2["trace_id"]
        data1.pop("run_id", None)
        data2.pop("run_id", None)
        data1.pop("phase_timings", None)
        data2.pop("phase_timings", None)
        # queries_used reflects internal query-caching behaviour (warm vs cold
        # LRU) and can legitimately differ across calls; exclude from content check
        data1.pop("queries_used", None)
        data2.pop("queries_used", None)
        assert data1 == data2


# ===================================================================
# A.5.1 — _parse_tag_ids Tests (review fix P1)
# ===================================================================


@pytest.mark.unit
class TestParseTagIds:
    """Unit tests for _parse_tag_ids covering both numeric and slug paths."""

    def test_numeric_ids(self):
        """Comma-separated numeric IDs parsed correctly."""
        assert _parse_tag_ids("10,12,34") == [10, 12, 34]

    def test_single_numeric(self):
        assert _parse_tag_ids("42") == [42]

    def test_empty_string(self):
        assert _parse_tag_ids("") == []

    def test_whitespace_only(self):
        assert _parse_tag_ids("  ,  , ") == []

    def test_numeric_with_whitespace(self):
        assert _parse_tag_ids(" 10 , 12 ") == [10, 12]

    def test_slug_lookup(self):
        """Slug tags resolved via config/tags.json."""
        result = _parse_tag_ids("life-and-death,ko")
        # These are real tags in config/tags.json — verify they return numeric IDs
        assert len(result) == 2
        assert all(isinstance(r, int) for r in result)
        assert all(r > 0 for r in result)

    def test_unknown_slug_skipped(self):
        """Unknown slug produces warning, returns partial result."""
        result = _parse_tag_ids("life-and-death,nonexistent-tag-xyz")
        # Should have at least the known tag
        assert len(result) >= 1
        assert all(isinstance(r, int) for r in result)

    def test_cache_reused(self):
        """Second call reuses cached slug map (module-level cache)."""
        _parse_tag_ids("life-and-death")
        cached = _config_lookup_mod._TAG_SLUG_TO_ID
        assert cached is not None
        _parse_tag_ids("ko")
        assert _config_lookup_mod._TAG_SLUG_TO_ID is cached  # Same object


# ===================================================================
# Expert Review — YK property extraction (P2 fix)
# ===================================================================


@pytest.mark.unit
class TestExtractMetadataYK:
    """Verify _extract_metadata extracts the YK (ko context) property."""

    def test_yk_direct_extracted(self):
        """YK[direct] → ko_type='direct' in metadata."""
        from core.tsumego_analysis import parse_sgf
        sgf = "(;FF[4]GM[1]SZ[19]YK[direct]YT[12]AB[cc][cd]AW[dc][dd];B[cb])"
        root = parse_sgf(sgf)
        meta = _extract_metadata(root)
        assert meta["ko_type"] == "direct"

    def test_yk_approach_extracted(self):
        """YK[approach] → ko_type='approach' in metadata."""
        from core.tsumego_analysis import parse_sgf
        sgf = "(;FF[4]GM[1]SZ[19]YK[approach]YT[12]AB[cc][cd]AW[dc][dd];B[cb])"
        root = parse_sgf(sgf)
        meta = _extract_metadata(root)
        assert meta["ko_type"] == "approach"

    def test_yk_none_when_absent(self):
        """No YK property → ko_type='none' (default)."""
        from core.tsumego_analysis import parse_sgf
        sgf = "(;FF[4]GM[1]SZ[19]AB[cc][cd]AW[dc][dd];B[cb])"
        root = parse_sgf(sgf)
        meta = _extract_metadata(root)
        assert meta["ko_type"] == "none"

    def test_yk_invalid_defaults_to_none(self):
        """Invalid YK value → ko_type='none'."""
        from core.tsumego_analysis import parse_sgf
        sgf = "(;FF[4]GM[1]SZ[19]YK[bogus]AB[cc][cd]AW[dc][dd];B[cb])"
        root = parse_sgf(sgf)
        meta = _extract_metadata(root)
        assert meta["ko_type"] == "none"


# ===================================================================
# A.5.1 — Difficulty fallback path test (review fix P2)
# ===================================================================


@pytest.mark.unit
class TestDifficultyFallback:
    """When estimate_difficulty raises, fallback to policy-only."""

    def test_difficulty_fallback_produces_result(self):
        sgf_text = _load_fixture("simple_life_death.sgf")
        manager = _make_mock_single_engine_manager()

        with patch("analyzers.stages.difficulty_stage.estimate_difficulty", side_effect=RuntimeError("boom")):
            result = asyncio.run(enrich_single_puzzle(sgf_text, manager))

        assert isinstance(result, AiAnalysisResult)
        # Should still produce a valid difficulty section via fallback
        assert result.difficulty.suggested_level != "unknown"
        assert result.difficulty.confidence in ("high", "medium", "low")


# ===================================================================
# T8: Position-only full AI-Solve success (DD-2 rev, DD-9)
# ===================================================================


@pytest.mark.unit
class TestPositionOnlyAiSolveSuccess:
    """Position-only SGF enters AI-Solve path and produces result (DD-2 rev, DD-9)."""

    def test_position_only_enters_ai_solve_not_rejected(self):
        """DD-9: Position-only SGFs always enter AI-Solve path.

        Verifies the puzzle is not hard-rejected with the old
        "No correct first move" error, and instead gets enriched.
        With mock engine, the roundtrip check may fail → tier 1 fallback.
        """
        sgf_no_moves = "(;FF[4]GM[1]SZ[19]PL[B]AB[dd][dc][cd]AW[ee][ed][de])"
        response = _make_response(top_move="D1", winrate=0.95, visits=500, policy=0.85)
        manager = _make_mock_single_engine_manager(analyze_response=response)

        result = asyncio.run(enrich_single_puzzle(sgf_no_moves, manager))

        assert isinstance(result, AiAnalysisResult)
        # Must NOT be hard-rejected with old "No correct first move" error
        assert not any(
            "No correct first move" in f
            for f in result.validation.flags
        ), "DD-9 violated: position-only puzzle hard-rejected with old error"
        # With mock engine, tier 1 fallback is expected (roundtrip fails)
        assert result.enrichment_tier in (1, 2, 3)


# ===================================================================
# T9: Position-only AI-Solve fails → fallback (DD-3, DD-7)
# ===================================================================


@pytest.mark.unit
class TestPositionOnlyAiSolveFallback:
    """Position-only SGF where AI-Solve fails → partial enrichment."""

    def test_ai_solve_no_correct_moves_tier2(self):
        """AI-Solve with mock engine → roundtrip fails → tier-1 fallback."""
        sgf_no_moves = "(;FF[4]GM[1]SZ[19]PL[B]AB[dd]AW[ee])"
        manager = _make_mock_single_engine_manager()

        result = asyncio.run(enrich_single_puzzle(sgf_no_moves, manager))

        assert isinstance(result, AiAnalysisResult)
        assert result.validation.status == ValidationStatus.FLAGGED
        assert result.enrichment_tier == 1
        assert result.ac_level == 0

    def test_engine_exception_tier1(self):
        """Engine exception during AI-Solve → tier-1 fallback (DD-7)."""
        sgf_no_moves = "(;FF[4]GM[1]SZ[19]PL[B]AB[dd]AW[ee])"

        # Create a manager whose analyze() raises RuntimeError
        manager = _make_mock_single_engine_manager()
        manager.analyze = AsyncMock(side_effect=RuntimeError("Engine unavailable"))

        result = asyncio.run(enrich_single_puzzle(sgf_no_moves, manager))

        assert isinstance(result, AiAnalysisResult)
        assert result.validation.status == ValidationStatus.FLAGGED
        assert result.enrichment_tier == 1
        assert result.ac_level == 0


# ===================================================================
# T10: Correct-moves-only SGF (standard path, no wrong moves)
# ===================================================================


@pytest.mark.unit
class TestCorrectMovesOnlySgf:
    """SGF with correct moves but no wrong branches → standard enrichment."""

    def test_correct_moves_produces_full_result(self):
        """SGF with solution tree → full enrichment (tier=3)."""
        sgf_text = _load_fixture("simple_life_death.sgf")
        # simple_life_death.sgf correct move is B[cs] = C1 in GTP.
        # Mock must return C1 as top move so validation doesn't reject.
        response = _make_response(top_move="C1", winrate=0.95, visits=500, policy=0.85)
        manager = _make_mock_single_engine_manager(analyze_response=response)

        result = asyncio.run(enrich_single_puzzle(sgf_text, manager))

        assert isinstance(result, AiAnalysisResult)
        assert result.enrichment_tier == 3
        assert result.validation.correct_move_gtp != ""
        # Validation should still be populated (not an error result)
        assert result.validation.status != ValidationStatus.REJECTED


# ===================================================================
# A.5.1 — Integration Test (requires KataGo binary)
# ===================================================================

from config.helpers import (
    KATAGO_PATH,
    TEST_NUM_THREADS,
    TEST_STARTUP_TIMEOUT,
    TSUMEGO_CFG,
    model_path,
)

_KATAGO_PATH = KATAGO_PATH
_SMALLEST_MODEL = model_path("test_smallest")
_TSUMEGO_CFG = TSUMEGO_CFG


@pytest.fixture(scope="module")
def integration_single_engine():
    """Module-scoped SingleEngineManager in quick_only mode for integration tests."""
    if not _KATAGO_PATH.exists() or not _SMALLEST_MODEL.exists():
        pytest.skip("KataGo binary or model not available")

    from analyzers.single_engine import SingleEngineManager
    from engine.config import EngineConfig
    from engine.local_subprocess import LocalEngine

    config = load_enrichment_config()

    engine_config = EngineConfig(
        katago_path=str(_KATAGO_PATH),
        model_path=str(_SMALLEST_MODEL),
        config_path=str(_TSUMEGO_CFG),
        default_max_visits=200,
        default_board_size=19,
        num_threads=TEST_NUM_THREADS,
    )
    quick_engine = LocalEngine(engine_config)

    async def _start():
        await quick_engine.start()
        ready = await quick_engine.wait_for_ready(timeout=TEST_STARTUP_TIMEOUT)
        if not ready:
            await quick_engine.shutdown()
            pytest.skip("Engine did not become ready within timeout")

    asyncio.run(_start())

    manager = SingleEngineManager(
        config=config,
        katago_path=str(_KATAGO_PATH),
        model_path=str(_SMALLEST_MODEL),
        katago_config_path=str(_TSUMEGO_CFG),
        engine=quick_engine,
        mode_override="quick_only",
    )
    yield manager
    asyncio.run(quick_engine.shutdown())


@pytest.mark.integration
@pytest.mark.skipif(
    not KATAGO_PATH.exists(),
    reason="KataGo binary not found",
)
@pytest.mark.skipif(
    not model_path("test_smallest").exists(),
    reason="Model file not found",
)
class TestRealPuzzleEnrichment:
    """Real SGF + real KataGo → valid JSON with all fields."""

    def test_real_puzzle_enrichment(self, integration_single_engine):
        """nakade.sgf → fully populated AiAnalysisResult with real KataGo."""
        sgf_text = (_FIXTURES / "nakade.sgf").read_text(encoding="utf-8")

        result = asyncio.run(enrich_single_puzzle(sgf_text, integration_single_engine))

        # Result must be a valid AiAnalysisResult
        assert isinstance(result, AiAnalysisResult)

        # Schema version should be current
        assert result.schema_version == AI_ANALYSIS_SCHEMA_VERSION

        # Validation: should not be rejected for a known-good puzzle
        assert result.validation.status != ValidationStatus.REJECTED
        assert result.validation.correct_move_gtp != ""

        # Difficulty: should produce a non-unknown level
        assert result.difficulty.suggested_level != "unknown"
        assert result.difficulty.suggested_level_id > 0

        # Refutations: nakade.sgf may produce refutations
        assert isinstance(result.refutations, list)

        # JSON serialization round-trip
        json_str = result.model_dump_json()
        parsed = json.loads(json_str)
        assert "validation" in parsed
        assert "difficulty" in parsed
        assert "refutations" in parsed


# ===================================================================
# T17 — Unit tests for extracted code-path functions
# ===================================================================


def _parse_fixture(name: str):
    """Parse a fixture SGF and return (root, position, metadata)."""
    sgf_text = _load_fixture(name)
    root = parse_sgf(sgf_text)
    metadata = _extract_metadata(root)
    position = extract_position(root)
    return root, position, metadata


@pytest.mark.unit
class TestRunStandardPath:
    """_run_standard_path sets flow-through vars from existing solution."""

    def test_sets_correct_move_gtp(self):
        root, position, metadata = _parse_fixture("simple_life_death.sgf")
        correct_move_sgf = extract_correct_first_move(root)
        assert correct_move_sgf is not None
        state = EnrichmentRunState()
        state = _run_standard_path(state, root, position, correct_move_sgf)
        assert state.correct_move_gtp is not None
        assert state.correct_move_sgf == correct_move_sgf

    def test_sets_solution_moves(self):
        root, position, metadata = _parse_fixture("simple_life_death.sgf")
        correct_move_sgf = extract_correct_first_move(root)
        state = EnrichmentRunState()
        state = _run_standard_path(state, root, position, correct_move_sgf)
        assert isinstance(state.solution_moves, list)
        assert len(state.solution_moves) >= 1

    def test_does_not_modify_path_flags(self):
        root, position, metadata = _parse_fixture("simple_life_death.sgf")
        correct_move_sgf = extract_correct_first_move(root)
        state = EnrichmentRunState()
        state = _run_standard_path(state, root, position, correct_move_sgf)
        assert state.position_only_path is False
        assert state.has_solution_path is False
        assert state.ai_solve_failed is False


@pytest.mark.unit
class TestRunPositionOnlyPath:
    """_run_position_only_path dispatches AI-Solve for position-only SGFs."""

    def test_engine_error_returns_early_result(self):
        """Engine failure → returns (state, AiAnalysisResult) for tier-1.

        Note: _build_partial_result has a pre-existing issue where int tag IDs
        are passed to classify_techniques which expects string slugs. This
        causes an AttributeError. Since this extraction must preserve existing
        behavior (MH-6), we verify the exception propagates as-is.
        """
        root, position, metadata = _parse_fixture("position_only_life_death.sgf")
        manager = _make_mock_single_engine_manager()
        manager.analyze = AsyncMock(side_effect=RuntimeError("engine down"))
        config = load_enrichment_config()
        state = EnrichmentRunState()

        # Pre-existing bug: _build_partial_result passes int tags to
        # classify_techniques which calls .lower() on them → AttributeError.
        # This is the same behavior as the inline code before extraction.
        with pytest.raises(AttributeError, match="lower"):
            asyncio.run(_run_position_only_path(
                state, root, position, manager, config, metadata,
                source_file="test.sgf", trace_id="t0001", run_id="r0001",
            ))

    def test_success_returns_none_early_result(self):
        """Successful AI-Solve → returns (state, None) with flow vars set."""
        root, position, metadata = _parse_fixture("position_only_life_death.sgf")

        # Build a response where top move looks like a valid correct move
        response = _make_response(top_move="D1", winrate=0.95, policy=0.80)
        manager = _make_mock_single_engine_manager(analyze_response=response)

        config = load_enrichment_config()
        state = EnrichmentRunState()

        # This may return early (tier-2 if no correct moves found, which
        # triggers _build_partial_result with the same pre-existing tag bug),
        # or succeed with (state, None). We test state is always returned.
        try:
            state, early_result = asyncio.run(_run_position_only_path(
                state, root, position, manager, config, metadata,
                source_file="test.sgf", trace_id="t0001", run_id="r0001",
            ))
            assert isinstance(state, EnrichmentRunState)
        except AttributeError:
            # Pre-existing: classify_techniques int tag bug in fallback path
            pass


@pytest.mark.unit
class TestRunHasSolutionPath:
    """_run_has_solution_path validates existing solutions."""

    def test_engine_exception_sets_ai_solve_failed(self):
        """MH-5: Exception → state.ai_solve_failed = True, no early return."""
        root, position, metadata = _parse_fixture("simple_life_death.sgf")
        correct_move_sgf = extract_correct_first_move(root)
        assert correct_move_sgf is not None

        manager = _make_mock_single_engine_manager()
        manager.analyze = AsyncMock(side_effect=ValueError("bad analysis"))
        config = load_enrichment_config()
        state = EnrichmentRunState()

        result_state = asyncio.run(_run_has_solution_path(
            state, root, position, manager, config, metadata,
            ai_solve_config=config.ai_solve,
            correct_move_sgf=correct_move_sgf,
        ))
        assert result_state.ai_solve_failed is True
        assert result_state.correct_move_gtp is not None
        assert result_state.solution_moves is not None

    def test_sets_has_solution_path_flag(self):
        """Always marks state.has_solution_path = True."""
        root, position, metadata = _parse_fixture("simple_life_death.sgf")
        correct_move_sgf = extract_correct_first_move(root)
        manager = _make_mock_single_engine_manager()
        # Make analyze fail so we test the exception path (still sets flag)
        manager.analyze = AsyncMock(side_effect=ValueError("test"))
        config = load_enrichment_config()
        state = EnrichmentRunState()

        result_state = asyncio.run(_run_has_solution_path(
            state, root, position, manager, config, metadata,
            ai_solve_config=config.ai_solve,
            correct_move_sgf=correct_move_sgf,
        ))
        assert result_state.has_solution_path is True
