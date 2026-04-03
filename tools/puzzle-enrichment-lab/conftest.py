"""Pytest configuration for puzzle-enrichment-lab."""

import os
import sys
from pathlib import Path

import pytest

# Ensure puzzle-enrichment-lab root is importable
_LAB_DIR = Path(__file__).resolve().parent
if str(_LAB_DIR) not in sys.path:
    sys.path.insert(0, str(_LAB_DIR))


def pytest_configure(config: pytest.Config) -> None:
    """Register custom markers and initialise structured logging."""
    config.addinivalue_line(
        "markers",
        "integration: integration tests requiring KataGo binary and model files",
    )
    config.addinivalue_line(
        "markers",
        "unit: fast isolated unit tests with no external dependencies",
    )
    config.addinivalue_line(
        "markers",
        "slow: long-running tests (performance, scale, model comparison)",
    )
    config.addinivalue_line(
        "markers",
        "golden5: canonical 5-puzzle integration tests (1 L&D, 1 ko, 1 tesuji, 1 small-board, 1 miai)",
    )
    config.addinivalue_line(
        "markers",
        "calibration: calibration tests against reference collections (never run during fixes)",
    )

    # --- Structured logging for test runs ---
    # Uses console_format="human" for readable pytest output.
    # LOG_LEVEL=DEBUG or -v flag enables verbose tracebacks.
    from log_config import bootstrap
    verbose = config.getoption("verbose", 0) > 0 or os.environ.get("LOG_LEVEL", "").upper() == "DEBUG"
    bootstrap(
        verbose=verbose,
        console_format="human",
        log_dir=_LAB_DIR / ".lab-runtime" / "logs" / "tests",
    )
