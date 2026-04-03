# Puzzle Manager Tests

## Quick Start

```bash
# Quick feedback (~30s) - for local development
pytest -m "not (cli or slow or adapter)"

# Unit tests only (~20s) - fastest isolated tests
pytest -m unit

# Standard (~90s) - before commit
pytest -m "not slow"

# Full suite (~3min) - CI/pre-PR
pytest

# Parallel execution (requires pytest-xdist)
pytest -n auto                           # Use all CPU cores
pytest -n auto -m "not (cli or slow)"    # Parallel quick tests

# Run with coverage
pytest --cov=backend/puzzle_manager
```

## Test Markers (Categories)

| Marker        | Tests | Time | When to Skip                 |
| ------------- | ----- | ---- | ---------------------------- |
| `unit`        | ~365  | ~20s | Never - always run           |
| `cli`         | 36    | ~40s | Local dev (subprocess heavy) |
| `slow`        | 11    | ~30s | Quick iterations             |
| `adapter`     | 161   | ~10s | Not touching adapters        |
| `inventory`   | 155   | ~15s | Not touching inventory       |
| `pagination`  | 68    | ~8s  | Not touching pagination      |
| `posix`       | 17    | ~2s  | Platform-specific CI         |
| `e2e`         | 10    | ~15s | Quick feedback               |
| `integration` | 186   | ~60s | Unit test focus              |

### Common Commands

```bash
# Skip slowest tests (CLI subprocess tests)
pytest -m "not cli"

# Only unit tests (fastest)
pytest -m unit

# Only adapter tests (when working on adapters)
pytest -m adapter

# Only inventory tests
pytest -m inventory

# Skip all optional categories (fastest)
pytest -m "not (cli or slow or adapter or e2e)"

# Run benchmarks only
pytest -m slow

# Parallel execution (install: pip install pytest-xdist)
pytest -n 4                 # Use 4 workers
pytest -n auto              # Auto-detect cores
pytest -n auto -m unit      # Parallel unit tests
```

## Test Organization

```
tests/
├── conftest.py              # Shared fixtures (tmp_path patterns)
├── fixtures/                # Test SGF files
├── adapters/                # Adapter-specific tests (@pytest.mark.adapter)
│   ├── test_ogs.py
│   ├── test_sanderland.py
│   └── ...
├── unit/                    # Fast isolated tests (@pytest.mark.unit auto-applied)
│   ├── conftest.py          # Auto-applies unit marker
│   ├── test_classifier.py
│   ├── test_sgf_parser.py
│   ├── test_sgf_builder.py
│   ├── test_primitives.py
│   ├── test_paths.py        # Directory getters
│   ├── test_posix_path.py   # to_posix_path() utility
│   └── ...
├── integration/             # Multi-component tests (@pytest.mark.integration)
│   ├── test_cli.py          # CLI subprocess tests (@pytest.mark.cli)
│   ├── test_pipeline.py     # Pipeline coordination
│   ├── test_inventory_*.py  # Inventory workflows
│   ├── test_*_posix.py      # POSIX path tests (@pytest.mark.posix)
│   └── ...
├── core/                    # Core module tests
├── models/                  # Model tests
└── stages/                  # Stage-specific tests
```

## Key Principles

### 1. Test Isolation with `tmp_path`

Tests MUST NOT write to production directories. Always use `tmp_path`:

```python
def test_ingest_stage(tmp_path):
    staging = tmp_path / "staging"
    staging.mkdir()

    # Test writes to staging, auto-cleaned after test
    stage = IngestStage(staging_dir=staging)
    stage.run(...)
```

### 2. Dry-Run is Tested at Stage Level

The `--dry-run` flag is implemented with guards in each stage:

| Stage                | Guards | What's Protected                       |
| -------------------- | ------ | -------------------------------------- |
| `ingest.py`          | 3      | Puzzle files, failed files, error logs |
| `analyze.py`         | 4      | Analyzed files, skipped files, copies  |
| `publish.py`         | 3      | Output puzzles, level/tag indexes      |
| `daily/generator.py` | 1      | Daily challenge JSON                   |

**Do NOT test dry-run via subprocess** - test it via stage unit tests.

### 3. CLI Tests Use `--help` Only

CLI tests verify argument parsing, NOT command execution:

```python
# ✅ CORRECT - tests argument parsing
def test_run_help(self):
    result = subprocess.run(
        [sys.executable, "-m", "backend.puzzle_manager", "run", "--help"],
        ...
    )
    assert result.returncode == 0

# ❌ WRONG - tests execution (slow, flaky, network-dependent)
def test_run_dry_mode(self):
    result = subprocess.run(
        [sys.executable, "-m", "backend.puzzle_manager", "run", "--dry-run"],
        ...
    )
```

### 4. No YENGO_TEST_MODE

The `YENGO_TEST_MODE` environment variable was removed (it was dead code - production never checked it). Test isolation is achieved via:

1. `tmp_path` for file operations
2. Optional constructor parameters for path injection
3. `--dry-run` guards at the stage level

## What NOT to Test Here

| Concern                     | Why Not                 | Alternative          |
| --------------------------- | ----------------------- | -------------------- |
| Full pipeline end-to-end    | Network-dependent, slow | Unit test each stage |
| External source fetching    | Flaky, API changes      | Mock HTTP responses  |
| Production directory writes | Risk of data corruption | Use `tmp_path`       |

## Fixtures

Common fixtures in `conftest.py`:

```python
@pytest.fixture
def sample_sgf():
    """Minimal valid SGF for testing."""
    return "(;GM[1]FF[4]SZ[9]AB[dd]AW[ff])"

@pytest.fixture
def staging_dirs(tmp_path):
    """Create standard staging directory structure."""
    dirs = {
        "ingest": tmp_path / "ingest",
        "analyze": tmp_path / "analyze",
        "output": tmp_path / "output",
    }
    for d in dirs.values():
        d.mkdir()
    return dirs
```

## Historical Note

Spec 044 attempted to add a `RuntimePaths` dependency injection pattern for test isolation. This was over-engineered and reverted in Spec 046. The simpler solution:

1. Add `--dry-run` guards to write operations
2. Use `tmp_path` in tests
3. Accept optional path parameters in constructors

See [DI Test Isolation (archived)](../../../docs/archive/di-test-isolation.md) for the full rationale.
