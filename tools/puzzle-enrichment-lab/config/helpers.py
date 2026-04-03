"""Helper functions for config access.

Groups: path constants, model path resolution (D42),
level category mapping, and effective max visits calculator.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from config import EnrichmentConfig

# ---------------------------------------------------------------------------
# Path constants (eagerly computed — pure path constants, no I/O)
# ---------------------------------------------------------------------------

LAB_DIR = Path(__file__).resolve().parent.parent
KATAGO_PATH = LAB_DIR / "katago" / "katago.exe"
TSUMEGO_CFG = LAB_DIR / "katago" / "tsumego_analysis.cfg"
MODELS_DIR = LAB_DIR / "models-data"

# ---------------------------------------------------------------------------
# Lazy config loading (D42) — deferred until first access via @lru_cache
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def _get_cfg():
    """Load and cache enrichment config lazily on first call."""
    from config import load_enrichment_config

    return load_enrichment_config()


def model_path(label: str) -> Path:
    """Resolve a config model label to a full filesystem path.

    Labels: test_smallest, test_fast, quick, referee, deep_enrich, benchmark.
    Raises ValueError for unknown labels.
    """
    cfg = _get_cfg()
    if cfg.models is None:
        raise RuntimeError(
            "models section missing from config/katago-enrichment.json (D42)"
        )
    entry = getattr(cfg.models, label, None)
    if entry is None:
        raise ValueError(
            f"Unknown model label '{label}'. "
            f"Valid: test_smallest, test_fast, quick, referee, deep_enrich, benchmark"
        )
    return MODELS_DIR / entry.filename

# ---------------------------------------------------------------------------
# Config-driven test defaults (eagerly resolved at import time)
# ---------------------------------------------------------------------------
_td = _get_cfg().test_defaults
TEST_STARTUP_TIMEOUT: float = _td.startup_timeout if _td else 180.0
TEST_QUERY_TIMEOUT: float = _td.query_timeout if _td else 30.0
TEST_MAX_VISITS: int = _td.default_max_visits if _td else 50
TEST_NUM_THREADS: int = _td.num_threads if _td else 1
del _td

# Level-category mapping for depth profiles (DD-1)
LEVEL_CATEGORY_MAP: dict[str, str] = {
    "novice": "entry",
    "beginner": "entry",
    "elementary": "entry",
    "intermediate": "core",
    "upper-intermediate": "core",
    "advanced": "strong",
    "low-dan": "strong",
    "high-dan": "strong",
    "expert": "strong",
}


def get_level_category(level_slug: str) -> str:
    """Map a level slug to its depth-profile category.

    Args:
        level_slug: Level slug from puzzle-levels.json.

    Returns:
        Category string: 'entry', 'core', or 'strong'.

    Raises:
        KeyError: If level_slug is not a recognized level.
    """
    return LEVEL_CATEGORY_MAP[level_slug]


def get_effective_max_visits(
    config: EnrichmentConfig,
    mode_override: str | None = None,
) -> int:
    """Return the max visits to use for analysis, respecting lab mode.

    Decision tree (B3, architectural review 2026-03-02):
        mode_override="quick_only" → config.analysis_defaults.default_max_visits
        deep_enrich.enabled=True   → config.deep_enrich.visits            (2000)
        deep_enrich.enabled=False  → config.analysis_defaults.default_max_visits (200)

    All query builder and analysis call sites MUST use this function
    instead of reading ``analysis_defaults.default_max_visits`` directly.
    Reading the defaults field directly bypasses lab mode and silently
    downgrades analysis to 200 visits.

    Args:
        config: Loaded EnrichmentConfig.
        mode_override: Explicit mode from caller. When "quick_only",
            returns quick_visits regardless of deep_enrich (A2 fix).

    Returns:
        Effective max visits integer.
    """
    if mode_override == "quick_only":
        return config.analysis_defaults.default_max_visits
    if config.deep_enrich.enabled:
        return config.deep_enrich.visits
    return config.analysis_defaults.default_max_visits
