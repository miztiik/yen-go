"""
Pytest configuration and fixtures for backend/puzzle_manager tests.

## TEST COMMANDS FOR AI AGENTS

Quick validation (~30s):
    pytest -m "not (cli or slow or adapter)"

Unit tests only (~20s):
    pytest -m unit

Pre-commit (~90s):
    pytest -m "not slow"

Full suite (~3min):
    pytest

Adapter only (~10s):
    pytest -m adapter

Parallel execution:
    pytest -n auto                        # All cores
    pytest -n auto -m "not (cli or slow)" # Parallel quick tests

## TEST DIRECTORY STRUCTURE

tests/
├── unit/          # Fast isolated tests (auto-marked @pytest.mark.unit)
├── integration/   # Multi-component tests
├── adapters/      # Adapter-specific tests (marked @pytest.mark.adapter)
├── core/          # Core module tests
├── models/        # Model tests
└── stages/        # Stage-specific tests

## AVAILABLE MARKERS

- unit: Fast isolated tests with no I/O (auto-applied in tests/unit/)
- cli: CLI subprocess tests (slowest, ~40s)
- slow: Benchmarks, large data tests (~30s)
- adapter: Adapter-specific tests (~10s)
- inventory: Inventory management tests
- pagination: Pagination/views tests
- posix: POSIX path compatibility tests
- e2e: End-to-end pipeline tests
- integration: Multi-component tests

See pyproject.toml for marker definitions.
See docs/architecture/backend/testing.md for full documentation.
"""

import json
import tempfile
from functools import lru_cache
from pathlib import Path

import pytest

from backend.puzzle_manager.core.id_maps import IdMaps


@lru_cache(maxsize=1)
def get_test_id_maps() -> IdMaps:
    """Create IdMaps with real config + additional test slugs.

    Extends the production config with fake slugs used in tests.
    Test IDs use 900+ range to avoid collision with real IDs.
    """
    real = IdMaps.load()

    # Copy real maps
    level_s2i = dict(real._level_slug_to_id)
    level_i2s = dict(real._level_id_to_slug)
    tag_s2i = dict(real._tag_slug_to_id)
    tag_i2s = dict(real._tag_id_to_slug)
    col_s2i = dict(real._collection_slug_to_id)
    col_i2s = dict(real._collection_id_to_slug)

    # Add test level slugs
    test_levels = {
        "test": 900, "level": 901, "small": 902, "paginated": 903,
        "empty_test": 904, "rebuild_test": 905, "valid": 906,
    }
    for slug, id_ in test_levels.items():
        level_s2i[slug] = id_
        level_i2s[id_] = slug

    # Add test collection slugs (only if not already in real config)
    test_collections = {
        "test-col": 900, "test-collection": 901, "cho-elementary": 902,
        "essential-life-and-death": 903, "ko-problems": 904,
        "tesuji-training": 905, "ladder-problems": 906,
    }
    for slug, id_ in test_collections.items():
        if slug not in col_s2i:
            col_s2i[slug] = id_
            col_i2s[id_] = slug

    return IdMaps(level_s2i, level_i2s, tag_s2i, tag_i2s, col_s2i, col_i2s)


def make_compact_entry(
    batch: str = "0001",
    hash_id: str = "fc38f029205dde14",
    level_id: int = 130,
    tag_ids: list[int] | None = None,
    col_ids: list[int] | None = None,
    yx: list[int] | None = None,
    n: int | None = None,
    q: int | None = None,
) -> dict:
    """Create a compact entry in wire format {p, l, t, c, x[, q][, n]}.

    Centralised test helper for the v4.0 compact entry schema.
    Use this in all test fixtures that need view-index entry dicts.

    Args:
        batch: Batch directory number (e.g., "0001").
        hash_id: Puzzle content hash (16 hex chars).
        level_id: Numeric level ID (110-230, or 900+ for test slugs).
        tag_ids: Numeric tag IDs.
        col_ids: Numeric collection IDs.
        yx: Complexity metrics [depth, refutations, solution_length, unique_responses].
        n: Sequence number (collection entries only).

    Returns:
        Compact entry dict matching the wire format.
    """
    entry: dict = {
        "p": f"{batch}/{hash_id}",
        "l": level_id,
        "t": tag_ids if tag_ids is not None else [],
        "c": col_ids if col_ids is not None else [],
        "x": yx if yx is not None else [0, 0, 0, 0],
    }
    if q is not None:
        entry["q"] = q
    if n is not None:
        entry["n"] = n
    return entry


@pytest.fixture
def test_id_maps() -> IdMaps:
    """Fixture providing IdMaps with test slugs."""
    return get_test_id_maps()


# =============================================================================
# Test Isolation via tmp_path
# =============================================================================
# Tests use pytest's built-in tmp_path fixture which creates isolated directories.
# Components receive paths as OPTIONAL constructor parameters with defaults,
# so tests can pass explicit paths via tmp_path for isolation.
#
# Example:
#     def test_something(tmp_path):
#         coordinator = PipelineCoordinator(
#             staging_dir=tmp_path / "staging",
#             state_dir=tmp_path / "state",
#             output_dir=tmp_path / "output",
#         )
# =============================================================================

@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_sgf():
    """Return a sample valid SGF string."""
    return "(;GM[1]FF[4]SZ[19]AB[dd][de][ed]AW[ee][ef][fe];B[ff])"


@pytest.fixture
def minimal_sgf():
    """Return minimal valid SGF."""
    return "(;SZ[19])"


@pytest.fixture
def puzzle_sgf_with_solution():
    """Return SGF with solution moves."""
    return """(;GM[1]FF[4]SZ[9]
        AB[cc][cd][dc]
        AW[dd][de][ed][ee]
        PL[B]
        ;B[ce]
        (;W[df];B[cf];W[cg];B[bg])
        (;W[cf];B[df])
    )"""


@pytest.fixture
def puzzle_sgf_with_yengo():
    """Return SGF with YenGo properties."""
    return "(;SZ[19]YG[5]YT[life-and-death,ladder]AB[dd]AW[ee];B[ff])"


@pytest.fixture
def temp_config_dir(temp_dir):
    """Create a temporary config directory with minimal config."""
    config_dir = temp_dir / "config"
    config_dir.mkdir()

    # Pipeline config (batch size=2 per dev guidelines: "if it works for 2, it works for N")
    pipeline = {
        "batch": {"size": 2, "max_files_per_dir": 10},
        "retention": {"days": 7},
        "daily": {"puzzles_per_day": 3, "days_ahead": 3},
        "output": {"sgf_root": "sgf", "views_root": "views"},
    }
    (config_dir / "pipeline.json").write_text(json.dumps(pipeline))

    # Sources config
    sources = {"sources": []}
    (config_dir / "sources.json").write_text(json.dumps(sources))

    # Note: tags.json is NOT created here - it's loaded from global config/tags.json
    # which is the single source of truth per architecture

    # Levels config - copy from global config (single source of truth)
    # Per constitution: "Use real config files — Don't mock levels.json, tags.json"
    import shutil
    global_levels = Path(__file__).parent.parent.parent.parent / "config" / "puzzle-levels.json"
    if global_levels.exists():
        shutil.copy(global_levels, config_dir / "puzzle-levels.json")
    else:
        # Fallback for CI environments where global config may not be at expected path
        levels = {}  # Empty placeholder - tests should use real config
        (config_dir / "puzzle-levels.json").write_text(json.dumps(levels))

    return config_dir


@pytest.fixture
def temp_state_dir(temp_dir):
    """Create a temporary state directory."""
    state_dir = temp_dir / "state"
    state_dir.mkdir()
    return state_dir


@pytest.fixture
def temp_staging_dir(temp_dir):
    """Create a temporary staging directory."""
    staging_dir = temp_dir / "staging"
    staging_dir.mkdir()
    (staging_dir / "ingest").mkdir()
    (staging_dir / "analyzed").mkdir()
    (staging_dir / "failed").mkdir()
    return staging_dir
