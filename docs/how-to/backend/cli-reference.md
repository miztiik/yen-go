# CLI Reference

> **See also**:
>
> - [CLI Quick Reference](../../reference/cli-quick-ref.md) — One-page cheat sheet
> - [Run Pipeline](./run-pipeline.md) — Pipeline operations guide
> - [Architecture: Pipeline](../../architecture/backend/pipeline.md) — Pipeline design

**Last Updated**: 2026-03-15  
**Entry Point**: `python -m backend.puzzle_manager [command]`

Complete reference for the puzzle manager command-line interface.

---

## Pipeline Overview

The puzzle manager runs a **3-stage pipeline**:

```
INGEST → ANALYZE → PUBLISH
   ↓         ↓         ↓
 Fetch    Enrich    Write to
 puzzles  & tag     collection
```

| Stage       | Input               | Output                          | What It Does                                     |
| ----------- | ------------------- | ------------------------------- | ------------------------------------------------ |
| **ingest**  | External source     | `.pm-runtime/staging/ingest/`   | Fetches puzzles from source, validates SGF       |
| **analyze** | `staging/ingest/`   | `.pm-runtime/staging/analyzed/` | Classifies difficulty, adds tags, enriches hints |
| **publish** | `staging/analyzed/` | `yengo-puzzle-collections/`     | Writes to collection, updates indexes            |

---

## Global Options

```bash
python -m backend.puzzle_manager [OPTIONS] COMMAND [ARGS]
```

| Option          | Description                            |
| --------------- | -------------------------------------- |
| `--version`     | Show version and exit                  |
| `-v, --verbose` | Increase verbosity (use -vv for debug) |
| `--config PATH` | Path to config directory               |
| `-h, --help`    | Show help                              |

---

## Commands

### run

Run the 3-stage pipeline (INGEST → ANALYZE → PUBLISH).

```bash
# Run full pipeline (--source is REQUIRED)
python -m backend.puzzle_manager run --source sanderland

# Run specific stage(s)
python -m backend.puzzle_manager run --source sanderland --stage ingest
python -m backend.puzzle_manager run --stage analyze
python -m backend.puzzle_manager run --stage publish
python -m backend.puzzle_manager run --stage analyze --stage publish

# Resume interrupted run
python -m backend.puzzle_manager run --resume

# Preview mode (no file changes)
python -m backend.puzzle_manager run --source sanderland --dry-run

# Custom batch size
python -m backend.puzzle_manager run --source sanderland --batch-size 50

# Process all pending files (overrides batch size)
python -m backend.puzzle_manager run --source sanderland --drain

# Custom flush interval for crash recovery checkpoints
python -m backend.puzzle_manager run --source sanderland --flush-interval 200
```

| Option               | Description                                                                                   |
| -------------------- | --------------------------------------------------------------------------------------------- |
| `--source SOURCE_ID` | **REQUIRED**: Source adapter to run (use IDs from `python -m backend.puzzle_manager sources`) |
| `--stage STAGE`      | Run specific stage(s) only. Can be repeated.                                                  |
| `--batch-size N`     | Override batch size (default: 2000 for `run`, 100 for `ingest`)                               |
| `--drain`            | Process all pending files (overrides `--batch-size`)                                          |
| `--flush-interval N` | Flush batch state every N processed files (default: 500, 0 to disable)                        |
| `--resume`           | Resume from last checkpoint if pipeline was interrupted                                       |
| `--dry-run`          | Preview changes without writing files                                                         |
| `--skip-cleanup`     | Skip cleanup after run                                                                        |
| `--no-enrichment`    | Disable all enrichment (hints, region, ko, etc.)                                              |
| `--no-hints`         | Disable hint generation (YH)                                                                  |
| `--no-region`        | Disable region detection (YC)                                                                 |
| `--no-ko`            | Disable ko detection (YK)                                                                     |
| `--source-override`  | Allow `--source` to override `active_adapter`                                                 |

**Source-Specific Options** (for adapters that support them):

_Legacy source-specific fetch flags were removed from the core CLI. Source-specific fetch behavior is handled by dedicated source tooling under `tools/`._

---

### status

Show pipeline status and history.

```bash
# Show current status
python -m backend.puzzle_manager status

# JSON output for scripting
python -m backend.puzzle_manager status --json
```

| Option   | Description    |
| -------- | -------------- |
| `--json` | Output as JSON |

---

### sources

Manage puzzle sources.

```bash
# List configured sources
python -m backend.puzzle_manager sources

# Check source availability
python -m backend.puzzle_manager sources --check

# JSON output
python -m backend.puzzle_manager sources --json
```

| Option    | Description              |
| --------- | ------------------------ |
| `--check` | Test source connectivity |
| `--json`  | Output as JSON           |

---

### inventory

View or manage the puzzle collection inventory.

```bash
# Show inventory summary
python -m backend.puzzle_manager inventory

# Output as JSON
python -m backend.puzzle_manager inventory --json

# Rebuild from publish logs
python -m backend.puzzle_manager inventory --rebuild

# Reconcile from disk (most accurate — scans actual SGF files)
python -m backend.puzzle_manager inventory --reconcile

# Check inventory integrity (Spec 107)
python -m backend.puzzle_manager inventory --check

# Check and auto-fix discrepancies
python -m backend.puzzle_manager inventory --check --fix
```

| Option        | Description                                                       |
| ------------- | ----------------------------------------------------------------- |
| `--json`      | Output as JSON                                                    |
| `--rebuild`   | Rebuild inventory from publish logs                               |
| `--reconcile` | Reconcile inventory by scanning SGF files on disk (most accurate) |
| `--check`     | Verify inventory matches actual files (FR-018)                    |
| `--fix`       | Auto-fix by rebuilding if --check finds issues (FR-024)           |

**`--reconcile` vs `--rebuild`:**

|                  | `--reconcile`                                  | `--rebuild`                                        |
| ---------------- | ---------------------------------------------- | -------------------------------------------------- |
| **Data source**  | SGF files on disk                              | Publish log entries                                |
| **SGF parsing**  | Root properties only (fast)                    | None — metadata from logs                          |
| **Parallelism**  | ThreadPoolExecutor (8 workers)                 | Sequential JSONL scan                              |
| **When to use**  | Inventory counts don't match actual files      | Publish logs are intact but inventory is corrupted |
| **Preserves**    | stages, metrics, audit from existing inventory | Nothing (fresh inventory)                          |
| **Handles**      | Files added/removed outside pipeline           | Ghost entries (log entry without file)             |
| **Auto-trigger** | Every `reconcile_interval` runs (default: 20)  | Never (explicit only)                              |

**Periodic Reconciliation:**

Reconcile runs automatically every N publish runs as a safety net against drift.
Configure via `PipelineConfig.reconcile_interval` (default: 20, set to 0 to disable).
The counter (`runs_since_last_reconcile`) is tracked in `AuditMetrics` and resets after each reconcile.

**Integrity Check Details** (FR-018 to FR-024):

The `--check` flag compares inventory against actual files:

- Verifies `total_puzzles` equals SGF file count
- Verifies each level count matches files in that level directory
- Detects orphan entries (publish log entry without file)
- Detects orphan files (file without publish log entry)
- Returns exit code 0 if all checks pass, non-zero if any fail

Example output:

```
✓ Total puzzles: inventory=4, actual=4
✓ Level 'beginner': inventory=1, actual=1
✗ Level 'advanced': inventory=2, actual=3 (MISMATCH)
✗ Orphan entry: puzzle-abc123 (in publish log, file missing)
Integrity check FAILED: 2 issues found
```

---

### clean

Clean old files (logs, state, staging).

```bash
# Preview what would be deleted
python -m backend.puzzle_manager clean --target staging --dry-run

# Clean staging directory
python -m backend.puzzle_manager clean --target staging

# Clean state files
python -m backend.puzzle_manager clean --target state

# Clean everything
python -m backend.puzzle_manager clean --target all
```

| Option               | Description                                      |
| -------------------- | ------------------------------------------------ |
| `--target TARGET`    | What to clean: `staging`, `state`, `logs`, `all` |
| `--retention-days N` | Days to retain (default: 45)                     |
| `--dry-run`          | Preview what would be deleted                    |

---

### rollback

Rollback published puzzles.

```bash
# Preview rollback
python -m backend.puzzle_manager rollback --run-id 20260130-abc12345 --dry-run

# Execute rollback
python -m backend.puzzle_manager rollback --run-id 20260130-abc12345

# Rollback specific puzzles
python -m backend.puzzle_manager rollback --puzzle-ids puz-001,puz-002
```

| Option             | Description                                    |
| ------------------ | ---------------------------------------------- |
| `--run-id ID`      | Rollback all puzzles from this run             |
| `--puzzle-ids IDS` | Comma-separated list of puzzle IDs to rollback |
| `--dry-run`        | Preview without executing                      |
| `--yes`            | Skip confirmation prompt                       |
| `--verify`         | Verify file counts after rollback              |

---

### publish-log

Query publish logs.

```bash
# List all publish logs
python -m backend.puzzle_manager publish-log list

# Search by run ID
python -m backend.puzzle_manager publish-log search --run-id 20260130-abc12345

# Search by puzzle ID
python -m backend.puzzle_manager publish-log search --puzzle-id gp-12345

# Search by source
python -m backend.puzzle_manager publish-log search --source sanderland
```

---

### daily

Generate daily puzzle challenges. Output is written as rows in the `daily_schedule` and `daily_puzzles` tables inside `yengo-search.db`.

```bash
# Generate for today
python -m backend.puzzle_manager daily

# Generate for specific date
python -m backend.puzzle_manager daily --date 2026-01-28

# Generate range of dates
python -m backend.puzzle_manager daily --start 2026-01-01 --end 2026-01-31

# Custom rolling window (prune dates older than N days)
python -m backend.puzzle_manager daily --rolling-window 90

# Dry run
python -m backend.puzzle_manager daily --dry-run
```

| Option                  | Description                                          |
| ----------------------- | ---------------------------------------------------- |
| `--date YYYY-MM-DD`     | Generate for specific date                           |
| `--start YYYY-MM-DD`    | Start date for range                                 |
| `--end YYYY-MM-DD`      | End date for range                                   |
| `--rolling-window N`    | Rolling window in days (default: 90); prunes old dates |
| `--dry-run`             | Preview without writing                              |

---

### validate

Validate configuration and SGF files.

```bash
# Validate all configuration
python -m backend.puzzle_manager validate

# Validate specific SGF file
python -m backend.puzzle_manager validate --file puzzle.sgf

# Validate configuration only
python -m backend.puzzle_manager validate --config-only
```

---

## Environment Variables

| Variable            | Description                             | Default                          |
| ------------------- | --------------------------------------- | -------------------------------- |
| `YENGO_RUNTIME_DIR` | Override runtime directory              | `.pm-runtime/`                   |
| `YENGO_LOG_LEVEL`   | Log level (DEBUG, INFO, WARNING, ERROR) | `INFO`                           |
| `YENGO_CONFIG_DIR`  | Override config directory               | `backend/puzzle_manager/config/` |

---

## Exit Codes

| Code | Meaning             |
| ---- | ------------------- |
| 0    | Success             |
| 1    | General error       |
| 2    | Configuration error |
| 3    | Invalid arguments   |

---

## Source Selection Behavior

The `--source` flag is **required** for the ingest stage.

| Scenario                                 | Behavior               |
| ---------------------------------------- | ---------------------- |
| `--source` specified                     | Uses specified adapter |
| `--source` matches `active_adapter`      | Proceeds normally      |
| `--source` differs from `active_adapter` | Warning, proceeds      |
| No `--source` for ingest                 | Error, exit(1)         |

---

## Runtime Directories

| Directory                       | Purpose                          |
| ------------------------------- | -------------------------------- |
| `.pm-runtime/staging/ingest/`   | Raw SGF files after ingest       |
| `.pm-runtime/staging/analyzed/` | Enriched SGF files after analyze |
| `.pm-runtime/staging/failed/`   | Files that failed processing     |
| `.pm-runtime/state/`            | Pipeline state and checkpoints   |
| `.pm-runtime/logs/`             | Log files                        |
| `yengo-puzzle-collections/`     | Published SGF files              |
