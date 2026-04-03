# Puzzle Manager Architecture

> **Spec Reference**: 035-puzzle-manager-refactor  
> **Location**: `backend/puzzle_manager/`  
> **Entry Point**: `python -m backend.puzzle_manager [command]`

The Puzzle Manager is a CLI tool that processes Go puzzles through a 3-stage pipeline.

## System Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLI Entry Point                          │
│              python -m backend.puzzle_manager [command]          │
│                      (argparse-based, no click)                  │
└─────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Pipeline Coordinator                         │
│  (Thin orchestrator - delegates to focused collaborators)        │
└─────────────────────────────────────────────────────────────────┘
          │
          ├──▶ StageExecutor (runs stages)
          ├──▶ StateManager (load/save state)
          ├──▶ CleanupCoordinator (retention cleanup)
          └──▶ PrerequisiteChecker (validates inputs)
                                  │
          ┌───────────────────────┼───────────────────────┐
          ▼                       ▼                       ▼
    ┌──────────┐           ┌──────────┐           ┌──────────┐
    │  INGEST  │    ──▶    │ ANALYZE  │    ──▶    │ PUBLISH  │
    │          │           │          │           │          │
    │ • fetch  │           │ • classify│          │ • index  │
    │ • parse  │           │ • tag    │           │ • daily  │
    │ • validate│          │ • enrich │           │ • output │
    └──────────┘           └──────────┘           └──────────┘
          │                       │                       │
          ▼                       ▼                       ▼
    .pm-runtime/           .pm-runtime/             yengo-puzzle-
    staging/ingest/        staging/analyzed/        collections/
```

## Directory Structure

```
backend/puzzle_manager/
├── __init__.py          # Package version
├── __main__.py          # Entry point for python -m
├── cli.py               # CLI with argparse (no click)
├── exceptions.py        # Single exception hierarchy
├── logging.py           # Structured JSON logging
├── paths.py             # Path utilities (uses .git marker)
├── py.typed             # PEP 561 marker
├── pyproject.toml       # Package config
│
├── core/                # Core utilities (SOLID - shared abstractions)
│   ├── primitives.py    # Point, Color, Move
│   ├── coordinates.py   # SGF/GTP coordinate conversion
│   ├── board.py         # Board representation, captures, ko
│   ├── sgf_parser.py    # Parse SGF files
│   ├── sgf_builder.py   # Build SGF files
│   ├── sgf_publisher.py # Serialize SGF to string
│   ├── schema.py        # SGF schema version
│   ├── classifier.py    # Difficulty classification (9-level)
│   ├── tagger.py        # Technique detection (loads from global config)
│   ├── text_cleaner.py  # Comment text cleaning (HTML, URLs, boilerplate)
│   ├── correctness.py   # Move correctness inference (markers, comments)
│   └── http.py          # HTTP client with retry/backoff (tenacity)
│
├── models/              # Pydantic data models
│   ├── enums.py         # SkillLevel, RunStatus, Stage
│   ├── puzzle.py        # Puzzle dataclass
│   ├── config.py        # Config models
│   └── daily.py         # Daily challenge models
│
├── config/              # Local configuration
│   ├── loader.py        # Config loader (loads tags from global config/)
│   ├── pipeline.json    # Pipeline settings
│   ├── sources.json     # Source definitions
│   └── levels.json      # 9-level difficulty definitions
│
├── state/               # State management
│   ├── models.py        # RunState, StageState
│   └── manager.py       # Single StateManager class
│
├── inventory/           # Collection inventory (Spec 052)
│   ├── models.py        # Pydantic models for inventory
│   ├── manager.py       # InventoryManager (CRUD + metrics)
│   ├── rebuild.py       # Rebuild from publish logs
│   └── cli.py           # inventory command handler
│
├── adapters/            # Source adapters (plugin-based)
│   ├── base.py          # BaseAdapter protocol, FetchResult
│   ├── registry.py      # @register_adapter decorator
│   ├── local.py         # Local directory adapter
│   ├── url.py           # URL-based adapter
│   └── ...              # Other adapters
│
├── stages/              # Pipeline stages
│   ├── protocol.py      # StageRunner protocol
│   ├── ingest.py        # INGEST stage
│   ├── analyze.py       # ANALYZE stage
│   └── publish.py       # PUBLISH stage
│
├── pipeline/            # Pipeline coordination
│   ├── coordinator.py   # PipelineCoordinator (thin)
│   ├── executor.py      # StageExecutor
│   ├── prerequisites.py # PrerequisiteChecker
│   └── cleanup.py       # CleanupCoordinator
│
├── daily/               # Daily challenge generation
│   ├── _helpers.py      # Shared helpers: seeding, tag/level lookups, config-driven rotation
│   ├── db_writer.py     # inject_daily_schedule(), prune_daily_window() — write daily rows to DB-1
│   ├── generator.py     # Main DailyGenerator (writes via db_writer)
│   ├── standard.py      # Standard daily (30 puzzles, config-driven levels)
│   ├── timed.py         # Timed challenge sets
│   └── by_tag.py        # Tag-focused challenges (rotation loaded from config/tags.json)
│
└── tests/               # Test suite (pytest)
    ├── conftest.py      # Fixtures
    ├── test_*.py        # Unit tests
    ├── unit/            # Unit tests
    └── integration/     # Integration tests
```

## Key Design Decisions (Spec 035)

| Aspect              | Decision                           | Rationale                                             |
| ------------------- | ---------------------------------- | ----------------------------------------------------- |
| CLI Framework       | `argparse` (stdlib)                | Zero external CLI dependencies                        |
| Dependencies        | 3 only (pydantic, httpx, tenacity) | Minimal footprint                                     |
| Path Detection      | `.git` marker only                 | `pyproject.toml` exists in subpackages                |
| Configuration       | Local + Global split               | Tags are Single Source of Truth in `config/tags.json` |
| State Management    | Single `StateManager` class        | Avoids name collision from previous design            |
| Exception Hierarchy | Single `exceptions.py`             | No duplication                                        |
| Adapter Registry    | Plugin-based `@register_adapter`   | Open/Closed principle                                 |

## Configuration

### Single Source of Truth Pattern

| Config File          | Location                        | Scope                               |
| -------------------- | ------------------------------- | ----------------------------------- |
| `puzzle-levels.json` | **`config/`** (repository root) | **Global - Single Source of Truth** |
| **`tags.json`**      | **`config/`** (repository root) | **Global - Single Source of Truth** |

### Config-Driven Daily Tag Rotation

The daily tag challenge (`daily/by_tag.py`) is **fully driven by `config/tags.json`**. No tag slugs are hardcoded in the pipeline.

- **Rotation order**: all tags from `config/tags.json`, sorted by their numeric `id` field (stable, deterministic).
- **Related-tag fallback**: siblings are all other tags with the same `category` value in config.
- **Adding a tag**: add it to `config/tags.json` — it is immediately included in the daily rotation and fallback logic.

Internally, `daily/_helpers.py` provides two cached helpers:

| Helper                     | Returns           | Purpose                             |
| -------------------------- | ----------------- | ----------------------------------- |
| `build_tag_rotation()`     | `tuple[str, ...]` | Full ordered rotation from config   |
| `build_tag_category_map()` | `dict[str, str]`  | Slug → category mapping from config |

### Path Resolution

```python
# paths.py - uses .git marker only
_ROOT_MARKER = ".git"

def get_project_root() -> Path:
    """Find project root by .git directory."""
    # Searches upward from current file

def get_global_config_dir() -> Path:
    """Return global config/ directory."""
    return get_project_root() / "config"
```

## State Management

State tracked in `.pm-runtime/state/manager_state.json`:

- Current run ID and status
- Stage completion status
- Processed/failed/skipped counts
- Timestamps

Rules:

- Skip already-completed batches
- Write state after each batch
- Re-running processes only incomplete items
- Support `--resume` flag

## Error Handling

| Scenario      | Behavior                 |
| ------------- | ------------------------ |
| Config error  | Fail fast, abort         |
| Puzzle error  | Log, record, continue    |
| Batch failure | Checkpoint, resume later |

All errors logged with structured context: puzzle_id, stage, batch, source.

## 9-Level Difficulty System

Refer to config/puzzle-levels.json for definitions.

## See Also

- [CLI Reference](../../reference/puzzle-manager-cli.md)
- [Configuration Reference](../../reference/configuration.md)
- [Adapter Design Standards](adapter-design-standards.md)
- [Data Flow](data-flow.md)
