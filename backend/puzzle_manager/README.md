# Puzzle Manager

Yen-Go puzzle manager - A 3-stage pipeline for processing Go (Baduk/Weiqi) tsumego puzzles.

> **Full Documentation**:
>
> - [How-To: Run Pipeline](../../docs/how-to/backend/run-pipeline.md) — Step-by-step guide
> - [How-To: Create Adapter](../../docs/how-to/backend/create-adapter.md) — Add new sources
> - [Architecture: Pipeline](../../docs/architecture/backend/pipeline.md) — Design decisions

## Quick Start

```bash
# Run full pipeline (--source is REQUIRED)
python -m backend.puzzle_manager run --source sanderland

# Run specific stage
python -m backend.puzzle_manager run --source sanderland --stage ingest

# Resume interrupted run
python -m backend.puzzle_manager run --resume

# Check status
python -m backend.puzzle_manager status

# Rollback a pipeline run
python -m backend.puzzle_manager rollback --run-id abc123def456 --dry-run
```

## Runtime Directories (Spec 048)

Runtime artifacts (logs, state, staging) are stored **outside** the source code directory:

| Directory              | Purpose                                  |
| ---------------------- | ---------------------------------------- |
| `.pm-runtime/logs/`    | Pipeline log files                       |
| `.pm-runtime/state/`   | Run state and checkpoints                |
| `.pm-runtime/staging/` | Temporary puzzle files during processing |

**Location**: `.pm-runtime/` at project root (where `.git` lives)

**Override**: Set `YENGO_RUNTIME_DIR` environment variable to use a custom location:

```bash
# Use custom runtime directory (CI/containers)
export YENGO_RUNTIME_DIR=/tmp/pm-runtime
python -m backend.puzzle_manager run --source sanderland

# View current runtime directory
python -m backend.puzzle_manager status
```

**Note**: The `.pm-runtime/` directory is gitignored and should never be committed.

## Observability (Spec 043, Spec 110)

The pipeline provides structured logging with run and trace correlation:

- **run_id**: Every log entry includes `run_id` for tracing (format: `YYYYMMDD-xxxxxxxx`)
- **source_id**: Puzzle operations log the source adapter name
- **trace_id**: Per-file unique identifier (16-char hex) for end-to-end debugging (Spec 110)
- **Stage status**: Unrequested stages show `SKIPPED` (not `PENDING`)
- **Structured summary**: Pipeline completion logs total puzzles, duration, and per-stage stats

### Trace ID (Spec 110)

Every puzzle processed through the pipeline gets a **trace_id** that follows it from ingest to publish:

```bash
# Search by trace_id
python -m backend.puzzle_manager trace search --trace-id a1b2c3d4e5f67890

# Search by puzzle_id (cross-run correlation)
python -m backend.puzzle_manager trace search --puzzle-id YENGO-abc123def456

# Get run summary
python -m backend.puzzle_manager trace summary --run-id 20260202-abc12345
```

Example log correlation:

```json
{
  "run_id": "20260129-abc12345",
  "trace_id": "a1b2c3d4e5f67890",
  "source_id": "sanderland",
  "puzzle_id": "gp-12345",
  "message": "Puzzle processed"
}
```

## Installation

```bash
# From repository root
pip install -e "./backend/puzzle_manager[dev]"

# Or just dependencies
pip install pydantic>=2.5.0 httpx>=0.26.0 tenacity>=8.2.0
```

## Testing

```bash
# Run from repository root
pytest backend/puzzle_manager/tests/

# With coverage
pytest --cov=backend/puzzle_manager --cov-report=html
```

## Adapter Selection (Spec 051)

The pipeline uses an `active_adapter` setting to determine which source to process.

### View Current Adapter

```bash
python -m backend.puzzle_manager sources
# Output shows: Active Adapter: ogs
```

### Change Active Adapter

```bash
# Set active adapter
python -m backend.puzzle_manager enable-adapter sanderland

# Clear active adapter (requires --source for all commands)
python -m backend.puzzle_manager disable-adapter
```

### Override Active Adapter

When `--source` differs from `active_adapter`, use `--source-override`:

```bash
# If active_adapter is "ogs" but you want sanderland:
python -m backend.puzzle_manager run --source sanderland --source-override
# Logs warning and proceeds
```

| Command                            | Effect                                            |
| ---------------------------------- | ------------------------------------------------- |
| `run` (no flags)                   | Uses `active_adapter` from sources.json           |
| `run --source X`                   | Uses X if it matches `active_adapter`, else error |
| `run --source X --source-override` | Uses X with warning                               |
| `enable-adapter X`                 | Sets `active_adapter` to X                        |
| `disable-adapter`                  | Clears `active_adapter`                           |

## Inventory Module (Spec 052)

The inventory module tracks collection statistics and pipeline observability metrics.

### View Inventory

```bash
# Human-readable summary
python -m backend.puzzle_manager inventory

# Raw JSON output
python -m backend.puzzle_manager inventory --json

# Rebuild from publish logs
python -m backend.puzzle_manager inventory --rebuild
```

### Inventory File

Location: `yengo-puzzle-collections/puzzle-collection-inventory.json`

| Section      | Contents                                     |
| ------------ | -------------------------------------------- |
| `collection` | Total puzzles, counts by level and tag       |
| `stages`     | Per-stage metrics (ingest, analyze, publish) |
| `metrics`    | Computed error rates, throughput             |
| `audit`      | Rollback tracking                            |

### Key Features

- **Atomic updates**: Uses tempfile + os.replace for data integrity
- **File locking**: Advisory locks prevent concurrent corruption
- **Auto-update**: Publish increments, rollback decrements
- **Protected**: Excluded from all cleanup operations
- **Rebuildable**: Can reconstruct from publish logs

See [docs/how-to/backend/monitor.md](../../docs/how-to/backend/monitor.md) for full documentation.

## Rollback Commands (Spec 036)

The puzzle manager supports atomic rollback operations for undoing pipeline runs.

### Rollback by Run ID

```bash
# Preview what would be rolled back (dry run)
python -m backend.puzzle_manager rollback --run-id abc123def456 --dry-run

# Execute rollback with confirmation prompt
python -m backend.puzzle_manager rollback --run-id abc123def456 --reason "Bad source data"

# Skip confirmation (use with caution)
python -m backend.puzzle_manager rollback --run-id abc123def456 --yes
```

### Rollback by Puzzle ID

```bash
# Rollback specific puzzles
python -m backend.puzzle_manager rollback --puzzle-id gp-12345 --puzzle-id gp-67890 --dry-run
```

### Publish Log Commands

```bash
# List all publish log files
python -m backend.puzzle_manager publish-log list

# Search by run ID
python -m backend.puzzle_manager publish-log search --run-id abc123def456

# Search by puzzle ID
python -m backend.puzzle_manager publish-log search --puzzle-id gp-12345

# Output as JSON
python -m backend.puzzle_manager publish-log search --run-id abc123 --format json
```

### Cleanup Commands

```bash
# Clean old publish logs (default 90 days retention)
python -m backend.puzzle_manager clean --target publish-logs

# Custom retention period
python -m backend.puzzle_manager clean --target publish-logs --retention-days 30 --dry-run
```

### Safety Features

- **Dry run**: Always preview with `--dry-run` before executing
- **Confirmation**: Prompts for confirmation when >100 puzzles affected
- **Batch limit**: Maximum 10,000 puzzles per rollback
- **Transaction backup**: All deletions are backed up for recovery
- **Audit logging**: All operations logged to `audit.jsonl`
- **Lock protection**: Only one rollback operation at a time

## Documentation

> **📚 All detailed documentation is in the global `docs/` directory.**
>
> This follows the Kubernetes/open-source pattern: package README contains quick-start only,
> authoritative documentation lives in a single location.

| Topic                   | Location                                                                                                             |
| ----------------------- | -------------------------------------------------------------------------------------------------------------------- |
| **Architecture**        | [docs/architecture/backend/puzzle-manager.md](../../docs/architecture/backend/puzzle-manager.md)                     |
| **CLI Reference**       | [docs/reference/puzzle-manager-cli.md](../../docs/reference/puzzle-manager-cli.md)                                   |
| **Configuration**       | [docs/reference/configuration.md](../../docs/reference/configuration.md)                                             |
| **Adapter Development** | [docs/architecture/backend/adapter-design-standards.md](../../docs/architecture/backend/adapter-design-standards.md) |
| **Technique Tags**      | [docs/reference/technique-tags.md](../../docs/reference/technique-tags.md)                                           |

## Key Design Decisions (Spec 035)

- **CLI**: Uses `argparse` (stdlib) instead of `click` - zero external CLI dependencies
- **Location**: `backend/puzzle_manager/` (not `puzzle_manager/`)
- **Entry Point**: `python -m backend.puzzle_manager [command]`
- **Configuration**: Local config in `config/`, tags loaded from global `config/tags.json` (Single Source of Truth)
- **Path Detection**: Uses `.git` marker to find project root

## License

MIT
