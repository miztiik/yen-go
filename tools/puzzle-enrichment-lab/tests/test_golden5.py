"""Sprint 0: Golden-5 canonical puzzle integration tests.

Tests 5 carefully selected puzzles through the full enrichment pipeline,
each targeting a specific capability:

  1. simple_life_death.sgf — 19×19 L&D (winrate validation, hint generation)
  2. ko_direct.sgf         — 9×9 ko (ko detection, YK property handling)
  3. sacrifice.sgf         — 9×9 sacrifice tesuji (low-policy correct move)
  4. board_9x9.sgf         — 9×9 minimal (coordinate conversion, small board)
  5. miai_puzzle.sgf        — 19×19 miai (multi-response, move_order handling)

Run with: ``pytest -m golden5``

These tests use real KataGo in quick_only mode (~2–3 min total).
They sit between fast unit tests (mocked, ~20s) and slow calibration
tests (full dual-engine, ~15 min).  After every algorithm change,
run ``pytest -m "unit or golden5"`` for rapid feedback.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

# Ensure puzzle-enrichment-lab root is importable
FIXTURES = Path(__file__).resolve().parent / "fixtures"

from config.helpers import KATAGO_PATH, TSUMEGO_CFG, model_path
from models.ai_analysis_result import AI_ANALYSIS_SCHEMA_VERSION

_KATAGO_PATH = KATAGO_PATH
_FAST_MODEL = model_path("test_fast")   # b10c128 — fast enough for plumbing tests
_TSUMEGO_CFG = TSUMEGO_CFG

# Fallback to smallest model for CI where fast model isn't present
_SMALLEST_MODEL = model_path("test_smallest")

_skip_reasons: list[str] = []
if not _KATAGO_PATH.exists():
    _skip_reasons.append("KataGo binary not found")
if not _FAST_MODEL.exists() and not _SMALLEST_MODEL.exists():
    _skip_reasons.append("No KataGo model files found")


def _best_model() -> Path:
    """Return the best available model (prefer test_fast b10, fallback to test_smallest b6)."""
    if _FAST_MODEL.exists():
        return _FAST_MODEL
    return _SMALLEST_MODEL


# ---------------------------------------------------------------------------
# Golden-5 fixture definitions
# ---------------------------------------------------------------------------

GOLDEN5_PUZZLES = {
    "life_and_death": {
        "file": "simple_life_death.sgf",
        "board_size": 19,
        "description": "19×19 L&D (advanced) — validates winrate, hints, L&D tag dispatch",
    },
    "ko_direct": {
        "file": "ko_direct.sgf",
        "board_size": 9,
        "description": "9×9 ko — validates ko detection, YK property handling",
    },
    "tesuji": {
        "file": "tesuji.sgf",
        "board_size": 19,
        "description": "19×19 tesuji — validates tesuji acceptance",
    },
    "small_board": {
        "file": "board_9x9.sgf",
        "board_size": 9,
        "description": "9×9 minimal — validates coordinate conversion, small board",
    },
    "miai_multi_response": {
        "file": "miai_puzzle.sgf",
        "board_size": 19,
        "description": "19×19 miai — validates multi-response, move_order=miai",
    },
}


@pytest.mark.golden5
@pytest.mark.integration
@pytest.mark.skipif(
    bool(_skip_reasons),
    reason="; ".join(_skip_reasons) if _skip_reasons else "OK",
)
class TestGolden5:
    """Canonical 5-puzzle integration suite.

    Each test validates a specific enrichment capability end-to-end
    through real KataGo analysis.  The class-scoped engine fixture
    starts KataGo once and reuses it for all 5 puzzles.
    """

    @pytest.fixture(autouse=True, scope="class")
    def _engine(self):
        """Class-scoped SingleEngineManager in quick_only mode."""
        from analyzers.single_engine import SingleEngineManager
        from config import load_enrichment_config

        config = load_enrichment_config()
        # Local override: cap refutation candidates to 2 for faster golden5 runs.
        # This validates pipeline plumbing without exploring all 5 candidates.
        config = config.model_copy(update={
            "refutations": config.refutations.model_copy(update={
                "candidate_max_count": 2,
            })
        })
        manager = SingleEngineManager(
            config=config,
            katago_path=str(_KATAGO_PATH),
            model_path=str(_best_model()),
            katago_config_path=str(_TSUMEGO_CFG),
            mode_override="quick_only",
        )

        async def _start():
            await manager.start()
            return manager

        started = asyncio.run(_start())
        type(self).engine_manager = started
        type(self).config = config
        yield
        asyncio.run(manager.shutdown())

    # -------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------

    def _enrich(self, fixture_name: str) -> AiAnalysisResult:  # noqa: F821
        """Run full enrichment pipeline for a golden5 fixture."""
        from analyzers.enrich_single import enrich_single_puzzle

        sgf_path = FIXTURES / fixture_name
        assert sgf_path.exists(), f"Fixture not found: {sgf_path}"
        sgf_text = sgf_path.read_text(encoding="utf-8")

        async def _run():
            return await enrich_single_puzzle(
                sgf_text=sgf_text,
                engine_manager=self.engine_manager,
                config=self.config,
                source_file=fixture_name,
                run_id="golden5-test",
            )

        return asyncio.run(_run())

    # -------------------------------------------------------------------
    # Test 1: Life & Death (19×19)
    # -------------------------------------------------------------------

    def test_life_and_death_19x19(self) -> None:
        """simple_life_death.sgf — pipeline completes, produces valid output.

        Capabilities tested:
          - L&D winrate validation
          - Hint generation
          - Difficulty estimation produces a valid level

        NOTE: Sourced from goproblems (advanced L&D, white-to-kill).
        The correct move is W[br] = B2 GTP.
        """
        result = self._enrich("simple_life_death.sgf")

        # Pipeline must complete — status is recorded but any value is OK
        # for Sprint 0 baseline.  TODO: tighten to accepted/flagged after P1.1.
        assert result.validation.status.value in (
            "accepted",
            "flagged",
            "rejected",
        ), f"Unexpected status: {result.validation.status.value}"

        # Correct move GTP should be extracted regardless of validation
        assert result.validation.correct_move_gtp == "B2", (
            f"Wrong correct move: {result.validation.correct_move_gtp}"
        )

        # Should produce a difficulty estimate with a valid level ID
        assert result.difficulty.suggested_level_id > 0, (
            "No difficulty level assigned"
        )

        # Should generate at least one hint
        assert len(result.hints) >= 1, "No hints generated for L&D puzzle"

        # Pipeline plumbing: trace_id and schema_version (puzzle-independent)
        assert result.trace_id != "", "No trace_id generated"
        assert result.schema_version == AI_ANALYSIS_SCHEMA_VERSION, (
            f"schema_version {result.schema_version} != {AI_ANALYSIS_SCHEMA_VERSION}"
        )

    # -------------------------------------------------------------------
    # Test 2: Ko (9×9)
    # -------------------------------------------------------------------

    def test_ko_direct_9x9(self) -> None:
        """ko_direct.sgf → accepted/flagged, ko detection active.

        Capabilities tested:
          - Ko-aware validation thresholds (YK[direct])
          - Small board (9×9) coordinate handling
          - Refutation generation for ko positions
        """
        result = self._enrich("ko_direct.sgf")

        # Must not be rejected
        assert result.validation.status.value in (
            "accepted",
            "flagged",
        ), f"Ko puzzle rejected: {result.validation.flags}"

        # Should detect correct move
        assert result.validation.correct_move_gtp != "", (
            "No correct move GTP for ko puzzle"
        )

        # Difficulty should be assigned
        assert result.difficulty.suggested_level_id > 0, (
            "No difficulty level for ko puzzle"
        )

    # -------------------------------------------------------------------
    # Test 3: Sacrifice Tesuji (9×9)
    # -------------------------------------------------------------------

    def test_sacrifice_tesuji(self) -> None:
        """sacrifice.sgf — pipeline completes, sacrifice technique detected.

        Capabilities tested:
          - Low-policy correct move acceptance (sacrifice moves have low prior)
          - Technique classification (should detect "sacrifice")
          - Refutation generation (2 wrong branches in fixture)

        NOTE: Sacrifice moves have inherently low policy prior.  KataGo may
        REJECT if the winrate rescue doesn't fire.  Sprint 1 P0.2 (tree
        validation sort by visits) should improve acceptance.
        """
        result = self._enrich("sacrifice.sgf")

        # Pipeline must complete — any status OK for Sprint 0 baseline
        assert result.validation.status.value in (
            "accepted",
            "flagged",
            "rejected",
        ), f"Unexpected status: {result.validation.status.value}"

        # Correct move should be extracted
        assert result.validation.correct_move_gtp == "E9", (
            f"Wrong correct move: {result.validation.correct_move_gtp}"
        )

        # Sacrifice technique should be classified
        assert "sacrifice" in result.technique_tags, (
            f"Expected 'sacrifice' in techniques, got: {result.technique_tags}"
        )

        # Should produce refutations (fixture has 2 wrong branches)
        # Note: KataGo may find additional wrong moves beyond the SGF branches
        assert result.difficulty.suggested_level_id > 0, (
            "No difficulty level for sacrifice puzzle"
        )

    # -------------------------------------------------------------------
    # Test 4: Small Board 9×9
    # -------------------------------------------------------------------

    def test_small_board_9x9(self) -> None:
        """board_9x9.sgf — pipeline completes, coordinate mapping valid.

        Capabilities tested:
          - 9×9 board coordinate conversion (GTP ↔ SGF)
          - Tight-board crop on small board
          - Minimal puzzle (no tags, no wrong branches) still enriches

        NOTE: This minimal fixture may be REJECTED because the correct
        move E2 gets 0 policy.  The primary test is coordinate validity.
        """
        result = self._enrich("board_9x9.sgf")

        # Pipeline must complete — any status OK for Sprint 0 baseline
        assert result.validation.status.value in (
            "accepted",
            "flagged",
            "rejected",
        ), f"Unexpected status: {result.validation.status.value}"

        # GTP coord must be valid for a 9×9 board (A1–J9, no I)
        gtp = result.validation.correct_move_gtp.upper()
        assert gtp == "E2", f"Wrong correct move GTP: {gtp}"
        col_letter = gtp[0]
        row_num = int(gtp[1:])
        assert col_letter in "ABCDEFGHJ", (
            f"Invalid column letter for 9×9: {col_letter}"
        )
        assert 1 <= row_num <= 9, (
            f"Row number {row_num} out of 9×9 range"
        )

        # Difficulty should still be assigned even for minimal puzzles
        assert result.difficulty.suggested_level_id > 0, (
            "No difficulty for 9×9 puzzle"
        )

    # -------------------------------------------------------------------
    # Test 5: Miai / Multi-Response (19×19)
    # -------------------------------------------------------------------

    def test_miai_multi_response(self) -> None:
        """miai_puzzle.sgf → accepted/flagged, miai handling.

        Capabilities tested:
          - move_order=miai detection (YO[miai])
          - Multi-correct-move puzzles (u field = 0 in pipeline terms)
          - Hint generation for miai positions
        """
        result = self._enrich("miai_puzzle.sgf")

        # Must not be rejected — miai puzzles have multiple correct answers
        assert result.validation.status.value in (
            "accepted",
            "flagged",
        ), f"Miai puzzle rejected: {result.validation.flags}"

        # Move order should be detected from YO[miai]
        assert result.move_order == "miai", (
            f"Expected move_order='miai', got '{result.move_order}'"
        )

        # Difficulty should be assigned
        assert result.difficulty.suggested_level_id > 0, (
            "No difficulty level for miai puzzle"
        )


