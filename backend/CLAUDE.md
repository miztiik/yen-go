# Backend (Puzzle Manager)

Python pipeline for importing, enriching, and publishing Go tsumego puzzles. See root `CLAUDE.md` for project-wide constraints and SGF schema.

## Stack

- **Language**: Python 3.11+ with type hints everywhere
- **SGF Parsing**: KaTrain pure-Python parser (`core/katrain_sgf_parser.py`)
- **Models**: `pydantic` (>=2.5)
- **HTTP**: `httpx` (>=0.26) with `tenacity` (>=8.2) for retry
- **CLI**: `click` (>=8.1)
- **Testing**: `pytest` with markers
- **Linting**: `ruff`

## Commands

```bash
# Tests
pytest                                       # Full suite (~1250 tests, ~3min)
pytest -m unit                               # Fast isolated tests (~365, ~20s)
pytest -m "not (cli or slow)"                # Quick validation after changes
pytest -m "not (cli or slow or adapter)"     # Local dev (~1000, ~30s)
pytest -m adapter                            # Adapter-specific (~160, ~10s)
pytest -n auto                               # Parallel execution (CI)

# Linting
ruff check .

# CLI (--source is REQUIRED)
python -m backend.puzzle_manager run --source sanderland                          # Full pipeline
python -m backend.puzzle_manager run --source sanderland --stage ingest           # Fetch only
python -m backend.puzzle_manager run --source sanderland --stage analyze          # Enrich only
python -m backend.puzzle_manager run --source sanderland --stage publish          # Publish only
python -m backend.puzzle_manager status                                    # Run status
python -m backend.puzzle_manager status --history                          # Run history
python -m backend.puzzle_manager sources                                   # List sources
python -m backend.puzzle_manager daily --date 2026-01-28                   # Daily challenge
python -m backend.puzzle_manager clean --target staging                    # Clean staging
python -m backend.puzzle_manager validate                                  # Validate config
python -m backend.puzzle_manager publish-log search --puzzle-id abc123def456  # Find by puzzle
python -m backend.puzzle_manager publish-log search --run-id abc123def456     # All in run
python -m backend.puzzle_manager publish-log search --source sanderland       # By source
python -m backend.puzzle_manager publish-log list                            # Available dates
```

## Key Directories

```
puzzle_manager/
  core/              # Core utilities (SgfBuilder, parser, publisher, HttpClient, classifier, tagger)
  pipeline/          # Pipeline coordinator, executor, prerequisites
  stages/            # ingest, analyze, publish stage implementations
  adapters/          # Source-specific adapters (sanderland, kisvadim, blacktoplay, etc.)
  models/            # Pydantic data models
  state/             # State management (run state, checkpoints)
  inventory/         # Collection inventory management
  daily/             # Daily challenge generation
  maintenance/       # Maintenance tasks
  tests/             # Test suite
    unit/            # Fast isolated tests (auto-marked @pytest.mark.unit)
    integration/     # Multi-component tests
    adapters/        # Adapter-specific tests
    core/            # Core module tests
    stages/          # Stage-specific tests
```

## Pipeline Architecture (3-Stage)

| Stage       | Sub-stages                 | Description                                                     |
| ----------- | -------------------------- | --------------------------------------------------------------- |
| **ingest**  | fetch -> parse -> validate | Download from source, parse SGF, verify structure               |
| **analyze** | classify -> tag -> enrich  | Assign difficulty (9 levels), detect techniques, generate hints |
| **publish** | index -> daily -> output   | Build view indexes, daily challenges, write enriched SGF output |

## GN Property Flow (Critical for Adapter Development)

```
INGEST:  Adapter returns puzzle_id (any format)
         -> File: staging/ingest/{puzzle_id}.sgf
         -> GN: can be anything (will be overwritten)

ANALYZE: Enriches SGF with YG, YT, YQ, YX, YH
         -> File: staging/analyzed/{puzzle_id}.sgf

PUBLISH: Generates content_hash = SHA256(content)[:16]
         -> Updates GN to: GN[YENGO-{content_hash}]
         -> File: {content_hash}.sgf
         -> GUARANTEED: GN == filename
```

Adapter checklist: Generate unique puzzle_id, return valid SGF (FF, GM, SZ, stones, solution). Do NOT set GN to YENGO format -- publish stage handles it.

## Core Utilities (Use These, Don't Reinvent)

| Utility             | Import                                         | Purpose                              |
| ------------------- | ---------------------------------------------- | ------------------------------------ |
| `SgfBuilder`        | `backend.puzzle_manager.core.sgf_builder`      | Build SGF from primitives            |
| `parse_sgf()`       | `backend.puzzle_manager.core.sgf_parser`       | Parse SGF string to SGFGame          |
| `publish_sgf()`     | `backend.puzzle_manager.core.sgf_publisher`    | Serialize SGFGame to string          |
| `HttpClient`        | `backend.puzzle_manager.core.http`             | HTTP with retry, rate-limit, backoff |
| `YENGO_SGF_VERSION` | `backend.puzzle_manager.core.schema`           | Current schema version               |
| `PuzzleValidator`   | `backend.puzzle_manager.core.puzzle_validator` | Centralized validation               |

## Runtime Directories

```
.pm-runtime/
  staging/     # Intermediate files during pipeline runs
  state/       # Run state, checkpoints (current_run.json)
  logs/        # Pipeline logs
```

Override with `YENGO_RUNTIME_DIR` env var.

## State Management

- State tracked in `.pm-runtime/state/current_run.json`
- Skip already-completed batches
- Write state after each batch
- Re-running processes only incomplete/failed items
- Support `--resume` flag for interrupted runs

## Error Handling

- **Config errors**: Fail fast
- **Puzzle errors**: Log, record, continue (batch-level recovery)
- Never swallow exceptions
- `trace_id` is stored in SGF via `YM` property (v12). Also appears in publish log entries and pipeline logs. Use `puzzle_id` (GN) for published identity.

## Test Strategy

- **Unit tests**: Mock external dependencies. Use `pytest.tmp_path` for file isolation.
- **Integration tests**: Multi-component, CLI subprocess.
- **Batch sizes in tests**: Use `batch_size=2` (if it works for 2, it works for N).
- After changes: `pytest -m "not (cli or slow)"` for quick validation.
- Before PR: full `pytest`.

## Config Files (Source of Truth)

| File                            | Purpose                          |
| ------------------------------- | -------------------------------- |
| `config/tags.json`              | Tag definitions (never hardcode) |
| `config/puzzle-levels.json`     | 9-level difficulty system        |
| `config/collections.json`       | Collection definitions           |
| `config/puzzle-quality.json`    | Quality metrics                  |
| `config/puzzle-validation.json` | Validation rules                 |
| `config/source-quality.json`    | Source quality ratings           |
| `config/schemas/`               | JSON schemas for all config      |
