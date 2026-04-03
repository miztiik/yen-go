# Backend Puzzle Manager - Claude Code Instructions

## Stack

- Python 3.12+ with type hints required on all functions
- Pydantic 2.5+ for data models
- httpx for HTTP, tenacity for retries
- ruff for linting, mypy (strict) for type checking
- pytest for testing

## 3-Stage Pipeline

```
ingest (fetch -> parse -> validate) -> analyze (classify -> tag -> enrich) -> publish (index -> daily -> output)
```

```bash
python -m backend.puzzle_manager run --source {name} --stage ingest
python -m backend.puzzle_manager run --source {name} --stage analyze
python -m backend.puzzle_manager run --source {name} --stage publish
python -m backend.puzzle_manager run --source {name}  # all stages
```

## Commands (run from backend/puzzle_manager/)

```bash
pytest -m unit                          # ~365 tests, ~20s (FASTEST)
pytest -m "not (cli or slow)"          # ~1000 tests, ~30s (local dev)
pytest -m "not slow"                   # ~1240 tests, ~90s (pre-commit)
pytest                                  # Full suite ~1250 tests, ~3min
pytest -m adapter                      # Adapter-specific ~160 tests, ~10s
ruff check .                           # Linting
```

## After Making Changes

1. `pytest -m unit` (fastest, ~20s)
2. `pytest -m "not (cli or slow)"` for broader validation (~30s)
3. `ruff check .` (linting)
4. Only run full `pytest` before PR

## Test Markers

| Marker | Scope | Notes |
|--------|-------|-------|
| `unit` | Fast isolated (~365 tests, ~20s) | Auto-applied in tests/unit/ |
| `adapter` | Adapter-specific (~160 tests, ~10s) | |
| `cli` | CLI subprocess (~36 tests, ~40s) | Slowest category |
| `slow` | Benchmarks/large data (~11 tests) | |
| `e2e` | Full pipeline end-to-end | |
| `inventory` | Inventory management | |
| `pagination` | Pagination/views | |
| `posix` | POSIX path compatibility | CI only |

## Test Conventions

- Unit tests: mock external dependencies
- Integration tests: use pytest `tmp_path` for file isolation
- CLI tests: verify `--help` only, use dry-run flags
- Batch sizes in tests: use `batch_size=2` (if it works for 2, it works for N)

## Module Layout

```
core/        - Shared utilities (sgf_builder, sgf_parser, http, schema)
adapters/    - Source-specific ingestors (_base.py defines base class)
stages/      - Pipeline stage implementations (ingest.py, analyze.py, publish.py)
models/      - Pydantic data models
daily/       - Daily challenge generation
inventory/   - Puzzle inventory management
state/       - Pipeline state tracking
```

## Adapter Development

When creating/modifying adapters:
- Inherit from `_base.py` base class
- Adapters do NOT set final GN property (publish stage handles it)
- Return valid SGF with FF, GM, SZ, stones, solution
- Generate unique `puzzle_id` (any format, will be rehashed at publish)
- Source adapter ID stored in `YS` property

## GN Property Flow

```
INGEST:  Adapter returns puzzle_id -> staging/ingest/{puzzle_id}.sgf
ANALYZE: Enriches with YG, YT, YQ, YX, YH -> staging/analyzed/{puzzle_id}.sgf
PUBLISH: SHA256(content)[:16] -> GN[YENGO-{hash}], filename={hash}.sgf
```

## Runtime Directories

```
.pm-runtime/staging/  - Pipeline working files
.pm-runtime/state/    - Run state (current_run.json)
.pm-runtime/logs/     - Pipeline logs
```

Override with `YENGO_RUNTIME_DIR` env var.

## Error Handling

- Never swallow exceptions
- Fail fast on config errors
- Continue on individual puzzle errors (log + record)
- Batch-level recovery supported

## Ruff/mypy Config (pyproject.toml)

- Ruff: line-length 100, target py312, rules E/W/F/I/B/C4/UP
- mypy: strict mode, disallow_untyped_defs, no_implicit_optional
