# Backend Testing Architecture

> **Last Updated**: 2026-02-02

This document describes the testing strategy for `backend/puzzle_manager/`.

## Test Suite Overview

| Category              | Tests  | Time  | Markers                        |
| --------------------- | ------ | ----- | ------------------------------ |
| **Total**             | ~1,250 | ~3min | -                              |
| **Unit (isolated)**   | ~365   | ~20s  | `unit`                         |
| **Quick (local dev)** | ~1,000 | ~30s  | `not (cli or slow or adapter)` |
| **Adapters**          | ~160   | ~10s  | `adapter`                      |
| **CLI (slowest)**     | ~36    | ~40s  | `cli`                          |
| **Benchmarks**        | ~11    | ~30s  | `slow`                         |

## Test Markers

Markers are defined in [pyproject.toml](../../../backend/puzzle_manager/pyproject.toml).

| Marker        | Purpose                                           | Skip Command           |
| ------------- | ------------------------------------------------- | ---------------------- |
| `unit`        | Fast isolated tests (auto-applied in tests/unit/) | -                      |
| `cli`         | CLI subprocess tests (slowest)                    | `-m "not cli"`         |
| `slow`        | Benchmarks, large data tests                      | `-m "not slow"`        |
| `adapter`     | Adapter-specific tests                            | `-m "not adapter"`     |
| `inventory`   | Inventory management                              | `-m "not inventory"`   |
| `pagination`  | Pagination/views                                  | `-m "not pagination"`  |
| `posix`       | POSIX path compatibility                          | `-m "not posix"`       |
| `e2e`         | End-to-end pipeline                               | `-m "not e2e"`         |
| `integration` | Multi-component tests                             | `-m "not integration"` |

## Recommended Test Commands

### For AI Coding Agents

```bash
# UNIT TESTS ONLY (fastest feedback)
cd backend/puzzle_manager && pytest -m unit -q --tb=short

# QUICK VALIDATION (use after making changes)
cd backend/puzzle_manager && pytest -m "not (cli or slow)" -q --tb=short

# PARALLEL EXECUTION (requires pytest-xdist)
cd backend/puzzle_manager && pytest -n auto -m "not (cli or slow)"

# ADAPTER WORK ONLY
cd backend/puzzle_manager && pytest -m adapter -q

# FULL SUITE (before PR only)
cd backend/puzzle_manager && pytest
```

### Developer Workflow

| Scenario       | Command                                    | Tests  | Time  |
| -------------- | ------------------------------------------ | ------ | ----- |
| Unit only      | `pytest -m unit`                           | ~365   | ~20s  |
| Quick feedback | `pytest -m "not (cli or slow or adapter)"` | ~1,000 | ~30s  |
| Pre-commit     | `pytest -m "not slow"`                     | ~1,240 | ~90s  |
| Full CI        | `pytest`                                   | ~1,250 | ~3min |
| Parallel CI    | `pytest -n auto`                           | ~1,250 | ~60s  |
| Adapter focus  | `pytest -m adapter`                        | ~160   | ~10s  |
| Single file    | `pytest tests/unit/test_sgf_parser.py`     | varies | <5s   |

## Test Organization

```
tests/
├── conftest.py         # Shared fixtures (tmp_path patterns)
├── fixtures/           # Test SGF files
├── adapters/           # Adapter tests (marked: adapter)
│   ├── test_ogs.py
│   ├── test_sanderland.py
│   └── test_ogs_e2e.py (also marked: e2e)
├── unit/               # Fast isolated tests (auto-marked: unit)
│   ├── conftest.py     # Auto-applies unit marker
│   ├── test_sgf_parser.py
│   ├── test_sgf_builder.py
│   ├── test_classifier.py
│   ├── test_primitives.py
│   ├── test_paths.py   # Directory getters
│   └── test_posix_path.py  # to_posix_path() utility
├── integration/        # Multi-component tests
│   ├── test_cli.py     # (marked: cli, integration)
│   ├── test_pipeline.py
│   ├── test_inventory_*.py  # Inventory workflows
│   ├── test_*_posix.py # (marked: posix)
│   └── test_*_benchmark.py  # (marked: slow)
├── core/               # Core module tests
├── models/             # Model tests
└── stages/             # Stage tests
```

## Parallel Execution

Install `pytest-xdist` for parallel test execution:

```bash
pip install pytest-xdist
```

Commands:

```bash
pytest -n auto              # Use all CPU cores
pytest -n 4                 # Use 4 workers
pytest -n auto -m unit      # Parallel unit tests only
```

**Note**: CLI tests (`-m cli`) don't parallelize well due to subprocess overhead.

## Adding New Tests

### Where to Put New Tests

| Test Type           | Location             | Auto-marker                            |
| ------------------- | -------------------- | -------------------------------------- |
| Pure function tests | `tests/unit/`        | `@pytest.mark.unit` (auto)             |
| Adapter-specific    | `tests/adapters/`    | Add `pytestmark = pytest.mark.adapter` |
| Multi-component     | `tests/integration/` | None (add manually if needed)          |
| CLI subprocess      | `tests/integration/` | Add `pytestmark = pytest.mark.cli`     |
| Benchmarks          | `tests/integration/` | Add `pytestmark = pytest.mark.slow`    |

### Marking New Test Files

Add `pytestmark` at module level for automatic marker application:

```python
"""My test module."""
import pytest

# Mark all tests in this module
pytestmark = pytest.mark.adapter  # or: [pytest.mark.cli, pytest.mark.slow]

# ... rest of tests
```

### When to Apply Markers

| If your test...            | Apply marker  |
| -------------------------- | ------------- |
| Uses `subprocess.run()`    | `cli`         |
| Takes >5 seconds           | `slow`        |
| Tests adapter code         | `adapter`     |
| Tests inventory code       | `inventory`   |
| Tests pagination code      | `pagination`  |
| Tests POSIX path handling  | `posix`       |
| Runs full pipeline         | `e2e`         |
| Touches filesystem heavily | `integration` |

## CI Configuration

Recommended GitHub Actions workflow:

```yaml
jobs:
  quick:
    name: Quick Tests
    runs-on: ubuntu-latest
    steps:
      - run: pytest -m "not (cli or slow)" --tb=short

  full:
    name: Full Suite
    runs-on: ubuntu-latest
    needs: quick # Only if quick passes
    steps:
      - run: pytest --tb=short
```

## See Also

- [tests/README.md](../../../backend/puzzle_manager/tests/README.md) — Test directory documentation
- [pyproject.toml](../../../backend/puzzle_manager/pyproject.toml) — Marker definitions
- [.github/copilot-instructions.md](../../../.github/copilot-instructions.md) — AI agent guidelines
