"""Shared test infrastructure for puzzle-enrichment-lab.

Enforces D42 (model name indirection): all model paths resolved from
config/katago-enrichment.json labels. No hardcoded filenames.

Owns TEST_* constants (eagerly resolved from config at import time).
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

# Ensure lab root is importable
_LAB_DIR = Path(__file__).resolve().parent.parent
if str(_LAB_DIR) not in sys.path:
    sys.path.insert(0, str(_LAB_DIR))

from config.helpers import (  # noqa: E402
    KATAGO_PATH,
    TEST_MAX_VISITS,
    TEST_NUM_THREADS,
    TEST_STARTUP_TIMEOUT,
    TSUMEGO_CFG,
    model_path,
)

# ---------------------------------------------------------------------------
# Shared integration engine fixture (D42)
#
# Replaces 4 identical copies in test_correct_move, test_fixture_coverage,
# test_ko_validation, test_refutations.
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def integration_engine():
    """Module-scoped KataGo engine with test_smallest (b6) model.

    Starts engine once per test module, yields it, shuts down after.
    Skips if KataGo binary or model file is missing.
    """
    _model = model_path("test_smallest")
    if not KATAGO_PATH.exists() or not _model.exists():
        pytest.skip("KataGo binary or model not available")

    from engine.config import EngineConfig
    from engine.local_subprocess import LocalEngine

    config = EngineConfig(
        katago_path=str(KATAGO_PATH),
        model_path=str(_model),
        config_path=str(TSUMEGO_CFG),
        default_max_visits=TEST_MAX_VISITS,
        default_board_size=19,
        num_threads=TEST_NUM_THREADS,
    )
    engine = LocalEngine(config)

    async def _start():
        await engine.start()
        ready = await engine.wait_for_ready(timeout=TEST_STARTUP_TIMEOUT)
        if not ready:
            await engine.shutdown()
            pytest.skip("Engine did not become ready within timeout")
        return engine

    started = asyncio.run(_start())
    yield started
    asyncio.run(engine.shutdown())
