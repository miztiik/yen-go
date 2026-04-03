"""Engine health check tests.

Task A.0.2: Verify the local KataGo engine starts, responds to queries,
and returns ownership + policy data. These are integration tests that
require katago.exe and a model file to be present.

Marked @pytest.mark.integration — skipped in unit-only runs.
Uses the smallest model (b6c96, 3.7MB) for fast startup.

A module-scoped fixture starts KataGo ONCE, runs one query, and shares
the response across all tests that inspect response fields.
"""

import asyncio
from pathlib import Path

import pytest

# Ensure tools/puzzle-enrichment-lab is importable
_HERE = Path(__file__).resolve().parent
_LAB = _HERE.parent
# ---------------------------------------------------------------------------
# Paths & constants (D42: resolve model via config label)
# ---------------------------------------------------------------------------
from config.helpers import (
    KATAGO_PATH,
    TEST_MAX_VISITS,
    TEST_NUM_THREADS,
    TEST_QUERY_TIMEOUT,
    TEST_STARTUP_TIMEOUT,
    TSUMEGO_CFG,
    model_path,
)
from engine.config import EngineConfig
from engine.local_subprocess import LocalEngine
from models.analysis_request import AnalysisRequest
from models.position import Color, Position, Stone

_CONFIG_PATH = _LAB / "config.json"
_KATAGO_PATH = KATAGO_PATH
_SMALLEST_MODEL = model_path("test_smallest")

# Timeouts from config/katago-enrichment.json (D42)
_STARTUP_TIMEOUT = TEST_STARTUP_TIMEOUT
_QUERY_TIMEOUT = TEST_QUERY_TIMEOUT

# Skip all tests in this module if KataGo binary or model is missing
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not _KATAGO_PATH.exists(),
        reason=f"KataGo binary not found at {_KATAGO_PATH}",
    ),
    pytest.mark.skipif(
        not _SMALLEST_MODEL.exists(),
        reason=f"Model file not found at {_SMALLEST_MODEL}",
    ),
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_simple_position() -> Position:
    """A simple corner position for health check queries."""
    return Position(
        board_size=9,
        stones=[
            Stone(color=Color.BLACK, x=1, y=0),
            Stone(color=Color.BLACK, x=1, y=1),
            Stone(color=Color.BLACK, x=0, y=1),
            Stone(color=Color.WHITE, x=2, y=0),
            Stone(color=Color.WHITE, x=2, y=1),
            Stone(color=Color.WHITE, x=1, y=2),
            Stone(color=Color.WHITE, x=0, y=2),
        ],
        player_to_move=Color.BLACK,
    )


def _make_engine_config() -> EngineConfig:
    """Create engine config pointing to the smallest model (fastest startup)."""
    return EngineConfig(
        katago_path=str(_KATAGO_PATH),
        model_path=str(_SMALLEST_MODEL),
        config_path=str(TSUMEGO_CFG),
        default_max_visits=TEST_MAX_VISITS,
        default_board_size=9,
        num_threads=TEST_NUM_THREADS,
    )

# ---------------------------------------------------------------------------
# Module-scoped fixture — start KataGo once, query once, share response
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def engine_response():
    """Start KataGo, wait for readiness, send one query, yield response.

    The engine is started once for the whole module and torn down after
    all tests complete. This avoids repeated 10–20 s startup cost.
    """
    config = _make_engine_config()
    engine = LocalEngine(config)
    position = _make_simple_position()

    async def _run():
        await engine.start()
        ready = await engine.wait_for_ready(timeout=_STARTUP_TIMEOUT)
        if not ready:
            await engine.shutdown()
            pytest.skip("Engine did not become ready within timeout")

        request = AnalysisRequest(
            position=position,
            max_visits=50,
            include_ownership=True,
            include_pv=True,
        )
        response = await asyncio.wait_for(
            engine.analyze(request), timeout=_QUERY_TIMEOUT
        )
        return response

    response = asyncio.run(_run())
    yield response
    asyncio.run(engine.shutdown())


# ===================================================================
# Tests
# ===================================================================

class TestEngineStarts:
    """Engine subprocess lifecycle (no analysis query needed)."""

    def test_engine_starts_and_stops(self):
        """KataGo process starts and stays alive after start()."""
        config = _make_engine_config()
        engine = LocalEngine(config)

        async def _run():
            await engine.start()
            assert engine._process is not None
            assert engine._process.poll() is None, "Process exited prematurely"
            await engine.shutdown()

        asyncio.run(_run())

    def test_engine_config_from_file(self):
        """Engine config loads from config.json and resolves paths."""
        if not _CONFIG_PATH.exists():
            pytest.skip(f"config.json not found at {_CONFIG_PATH}")
        config = EngineConfig.from_file(_CONFIG_PATH)
        assert config.katago_path
        assert config.model_path


class TestHealthCheckResponse:
    """Engine responds to analysis queries with valid data."""

    def test_move_infos_present(self, engine_response):
        """Response should contain at least one move suggestion."""
        assert len(engine_response.move_infos) > 0, "No move suggestions returned"

    def test_root_winrate_valid(self, engine_response):
        """Root winrate should be in [0, 1]."""
        assert 0.0 <= engine_response.root_winrate <= 1.0

    def test_top_move_has_visits(self, engine_response):
        """Top move should have at least 1 visit."""
        top = engine_response.top_move
        assert top is not None
        assert top.visits > 0


class TestOwnershipAndPolicyPresent:
    """Response includes ownership and policy data for tsumego analysis."""

    def test_top_move_policy_prior_positive(self, engine_response):
        """Top move should have a non-zero policy prior."""
        top = engine_response.top_move
        assert top is not None
        assert top.policy_prior > 0.0, "Top move should have positive policy prior"

    def test_policy_values_sum_reasonable(self, engine_response):
        """Policy priors across reported moves should sum to a meaningful value."""
        total_policy = sum(m.policy_prior for m in engine_response.move_infos)
        assert total_policy > 0.1, (
            f"Policy sum too low: {total_policy}. "
            f"Moves: {[(m.move, m.policy_prior) for m in engine_response.move_infos[:5]]}"
        )


# --- Migrated from test_sprint5_fixes.py ---


@pytest.mark.unit
class TestKatagoBatchConfig:
    """P2.7: nnMaxBatchSize should be >= numSearchThreads * numAnalysisThreads."""

    def test_cfg_batch_size_adequate(self):
        """tsumego_analysis.cfg has nnMaxBatchSize >= total threads."""
        cfg_path = _LAB / "katago" / "tsumego_analysis.cfg"
        if not cfg_path.exists():
            pytest.skip("tsumego_analysis.cfg not found")

        text = cfg_path.read_text(encoding="utf-8")
        values = {}
        for line in text.splitlines():
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip().split("#")[0].strip()  # remove inline comments
                try:
                    values[key] = int(val)
                except ValueError:
                    pass

        batch_size = values.get("nnMaxBatchSize", 0)
        search_threads = values.get("numSearchThreadsPerAnalysisThread", 0)
        analysis_threads = values.get("numAnalysisThreads", 0)
        total_threads = search_threads * analysis_threads

        assert batch_size >= total_threads, (
            f"nnMaxBatchSize ({batch_size}) < "
            f"numSearchThreads ({search_threads}) * numAnalysisThreads ({analysis_threads}) "
            f"= {total_threads}. KataGo will warn about GPU serialization."
        )
