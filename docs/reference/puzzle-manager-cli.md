# Puzzle Manager CLI Reference

> **Spec Reference**: 035-puzzle-manager-refactor  
> **Entry Point**: `python -m backend.puzzle_manager [command]`  
> **Last Updated**: 2026-01-31

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

| Stage | Input | Output | What It Does |
|-------|-------|--------|--------------|
| **ingest** | External source | `.pm-runtime/staging/ingest/` | Fetches puzzles from source, validates SGF |
| **analyze** | `staging/ingest/` | `.pm-runtime/staging/analyzed/` | Classifies difficulty, adds tags, enriches hints |
| **publish** | `staging/analyzed/` | `yengo-puzzle-collections/` | Writes to collection, updates indexes |

### Stage Flow

```bash
# Run all 3 stages for a source
python -m backend.puzzle_manager run --source ogs

# Or run stages separately:
python -m backend.puzzle_manager run --source ogs --stage ingest    # Step 1
python -m backend.puzzle_manager run --source ogs --stage analyze   # Step 2
python -m backend.puzzle_manager run --source ogs --stage publish   # Step 3

# Or combine stages:
python -m backend.puzzle_manager run --source ogs --stage analyze --stage publish
```

### Runtime Directory

All staging and state files are in `.pm-runtime/` at project root:

```
.pm-runtime/
├── staging/
│   ├── ingest/      # Raw SGF files after ingest
│   ├── analyzed/    # Enriched SGF files after analyze
│   └── failed/      # Files that failed processing
├── state/
│   ├── runs/        # Run state JSON files
│   └── failures/    # Failure tracking
└── logs/            # Log files
```

---

## Installation

```bash
# From repository root
pip install -e "./backend/puzzle_manager[dev]"

# Verify
python -m backend.puzzle_manager --version
```

---

## Global Options

```bash
python -m backend.puzzle_manager [OPTIONS] COMMAND [ARGS]
```

| Option | Description |
|--------|-------------|
| `--version` | Show version and exit |
| `-v, --verbose` | Increase verbosity (use -vv for debug) |
| `--config PATH` | Path to config directory |
| `-h, --help` | Show help |

---

## Commands

### run

Run the 3-stage pipeline (INGEST → ANALYZE → PUBLISH).

> **Note**: The `--source` flag is **REQUIRED** for the ingest stage. It specifies which adapter to use for fetching puzzles.

```bash
# Run full pipeline using active_adapter (default from sources.json)
python -m backend.puzzle_manager run

# Run full pipeline for a specific source
python -m backend.puzzle_manager run --source sanderland

# Run specific source with batch limit
python -m backend.puzzle_manager run --source sanderland --batch-size 5

# Run specific stage(s)
python -m backend.puzzle_manager run --source sanderland --stage ingest
python -m backend.puzzle_manager run --source sanderland --stage analyze
python -m backend.puzzle_manager run --source sanderland --stage publish
python -m backend.puzzle_manager run --source sanderland --stage analyze --stage publish

# Resume interrupted run (restores source_id from saved state)
python -m backend.puzzle_manager run --resume

# Preview mode (no file changes)
python -m backend.puzzle_manager run --source sanderland --dry-run

# Custom batch size
python -m backend.puzzle_manager run --source sanderland --batch-size 50

# Verbose output
python -m backend.puzzle_manager run --source sanderland -vv

# Skip cleanup after run
python -m backend.puzzle_manager run --source sanderland --skip-cleanup
```

| Option | Description |
|--------|-------------|
| `--source SOURCE_ID` | **REQUIRED**: Source adapter to run. Examples: sanderland, goproblems, blacktoplay, ogs. Must be specified for ingest stage. |
| `--stage STAGE` | Run specific stage(s) only. Can be repeated. |
| `--batch-size N` | Override batch size (default: 100) |
| `--resume` | Resume from last checkpoint if pipeline was interrupted |
| `--dry-run` | Preview changes without writing files |
| `--skip-cleanup` | Skip cleanup after run |

**Source-Specific Options** (for adapters that support them):

| Option | Adapters | Description |
|--------|----------|-------------|
| `--puzzle-id ID` | ogs | Import single puzzle by ID |
| `--type TYPE` | ogs | Filter by puzzle type (life_and_death, tesuji, fuseki, joseki, endgame, best_move) |
| `--collection ID` | ogs | Filter by collection ID |
| `--fetch-only` | ogs | Two-phase mode: fetch raw JSON to `.pm-runtime/raw/` only |
| `--transform-only` | ogs | Two-phase mode: transform raw JSON to SGF only |
| `--strict-translation` | ogs | Skip puzzles that can't be cleanly translated |

**Example: OGS Adapter Usage**:
```bash
# Import single puzzle
python -m backend.puzzle_manager run --source ogs --puzzle-id 12345

# Batch import life-and-death puzzles
python -m backend.puzzle_manager run --source ogs --type life_and_death

# Two-phase import for large batches (supports resume)
python -m backend.puzzle_manager run --source ogs --fetch-only
python -m backend.puzzle_manager run --source ogs --transform-only

# Import from specific collection
python -m backend.puzzle_manager run --source ogs --collection 456

# Combined filters
python -m backend.puzzle_manager run --source ogs --type tesuji --collection 789
```

**Pipeline Stages**:
| Stage | Sub-stages | Description |
|-------|------------|-------------|
| `ingest` | fetch → parse → validate | Download, parse SGF, verify structure |
| `analyze` | classify → tag → enrich | Assign difficulty, detect techniques, add hints |
| `publish` | index → daily → output | Build indexes, generate daily challenges, write output |

**Common Workflows**:

```bash
# Workflow 1: Full pipeline (recommended)
python -m backend.puzzle_manager run --source ogs

# Workflow 2: Stage-by-stage execution
# Step 1: Ingest puzzles to staging
python -m backend.puzzle_manager run --source ogs --stage ingest
# Check staging: ls .pm-runtime/staging/ingest/

# Step 2: Analyze and enrich
python -m backend.puzzle_manager run --source ogs --stage analyze
# Check staging: ls .pm-runtime/staging/analyzed/

# Step 3: Publish to collection
python -m backend.puzzle_manager run --source ogs --stage publish
# Check output: ls yengo-puzzle-collections/sgf/

# Workflow 3: Continue from interrupted run
python -m backend.puzzle_manager run --resume

# Workflow 4: Re-analyze without re-ingesting
python -m backend.puzzle_manager run --source ogs --stage analyze --stage publish
```

---

### status

Show pipeline status and history.

```bash
# Show current status
python -m backend.puzzle_manager status

# JSON output for scripting
python -m backend.puzzle_manager status --json
```

| Option | Description |
|--------|-------------|
| `--json` | Output as JSON |

**Output includes**:
- Current run ID and status
- Stage completion status
- Processed/failed/skipped counts
- Last run timestamp

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

| Option | Description |
|--------|-------------|
| `--file PATH` | Validate specific SGF file |
| `--config-only` | Only validate configuration files |

---

### sources

Manage puzzle sources.

```bash
# List configured sources (shows active_adapter)
python -m backend.puzzle_manager sources

# Check source availability
python -m backend.puzzle_manager sources --check

# JSON output
python -m backend.puzzle_manager sources --json
```

The `sources` command shows the `active_adapter` setting and all configured sources:

```bash
$ python -m backend.puzzle_manager sources
Active Adapter: ogs

Configured Sources:
  ogs          Online-Go.com Puzzles
  sanderland   Sanderland Collection
  goproblems   GoProblems.com
  ...
```

**active_adapter Configuration**:

The `active_adapter` in `backend/puzzle_manager/config/sources.json` sets the default source for `run` and `ingest` commands when `--source` is not specified:

```json
{
  "active_adapter": "ogs",
  "sources": [...]
}
```

To change the default, use CLI commands (preferred) or edit `sources.json` directly:

```bash
# Set active adapter via CLI
python -m backend.puzzle_manager enable-adapter sanderland

# Disable active adapter (requires --source for all commands)
python -m backend.puzzle_manager disable-adapter

# Then run without --source flag:
python -m backend.puzzle_manager run  # Uses active_adapter
```

| Option | Description |
|--------|-------------|
| `--check` | Test source connectivity |
| `--json` | Output as JSON |

---

### enable-adapter

Set the active adapter in `sources.json`.

```bash
# Set active adapter to sanderland
python -m backend.puzzle_manager enable-adapter sanderland

# Set active adapter to ogs
python -m backend.puzzle_manager enable-adapter ogs
```

After setting, commands without `--source` will use this adapter:

```bash
python -m backend.puzzle_manager run  # Uses sanderland
```

---

### disable-adapter

Clear the active adapter from `sources.json`.

```bash
python -m backend.puzzle_manager disable-adapter
```

After disabling, you MUST specify `--source` for all pipeline commands:

```bash
python -m backend.puzzle_manager run --source sanderland
```

---

### Source Override Behavior

When `--source` is specified and differs from `active_adapter`, the pipeline requires explicit confirmation:

```bash
# If active_adapter is "ogs" but you want to run "sanderland":
python -m backend.puzzle_manager run --source sanderland
# ERROR: source 'sanderland' differs from active_adapter 'ogs'

# Use --source-override to explicitly confirm:
python -m backend.puzzle_manager run --source sanderland --source-override
# WARNING: Source overridden to 'sanderland' (active_adapter is 'ogs')
```

| Scenario | Behavior |
|----------|----------|
| No `--source` | Uses `active_adapter` from sources.json |
| `--source` matches `active_adapter` | Proceeds normally |
| `--source` differs, no `--source-override` | Error, exit(1) |
| `--source` differs, with `--source-override` | Warning, proceeds |

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
```

| Option | Description |
|--------|-------------|
| `--json` | Output as JSON instead of human-readable |
| `--rebuild` | Rebuild inventory from publish logs |

**Sample Output**:
```
Puzzle Collection Inventory
===========================
Total Puzzles: 15,000

By Level:
  beginner:       3,000 (20.0%)
  intermediate:   5,000 (33.3%)
  ...

By Tag (top 10):
  life-and-death: 8,000 (53.3%)
  ...

By Quality:
  Premium (5):    1,500 (10.0%)
  High (4):       3,000 (20.0%)
  Standard (3):   6,000 (40.0%)
  Basic (2):      3,500 (23.3%)
  Unverified (1): 1,000 (6.7%)

Stage Metrics:
  Ingest:  15,500 passed / 16,000 attempted (96.9%)
  Analyze: 15,200 enriched / 300 skipped
  Publish: 15,000 new

Audit:
  Total Rollbacks: 3
  Last Rollback:   2026-01-25T14:30:00Z
```

See [How-To: Monitor Pipeline](../how-to/backend/monitor.md) for detailed usage.

---

### clean

Clean old files (logs, state, staging).

```bash
# Preview what would be deleted
python -m backend.puzzle_manager clean --dry-run

# Clean with default retention (45 days)
python -m backend.puzzle_manager clean

# Custom retention period
python -m backend.puzzle_manager clean --retention-days 30
```

| Option | Description |
|--------|-------------|
| `--retention-days N` | Days to retain (default: 45) |
| `--dry-run` | Preview what would be deleted |

**What gets cleaned**:
- `.pm-runtime/staging/ingest/` - Raw SGF files older than retention
- `.pm-runtime/staging/analyzed/` - Analyzed SGF files older than retention
- `.pm-runtime/logs/` - Log files older than retention
- `.pm-runtime/state/` - Old state files (keeps current)

---

### daily

Generate daily puzzle challenges.

```bash
# Generate for today
python -m backend.puzzle_manager daily

# Generate for specific date
python -m backend.puzzle_manager daily --date 2026-01-28

# Generate range of dates
python -m backend.puzzle_manager daily --start 2026-01-01 --end 2026-01-31

# Dry run
python -m backend.puzzle_manager daily --dry-run
```

| Option | Description |
|--------|-------------|
| `--date YYYY-MM-DD` | Generate for specific date |
| `--start YYYY-MM-DD` | Start date for range |
| `--end YYYY-MM-DD` | End date for range |
| `--dry-run` | Preview without writing |

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `YENGO_ROOT` | Override project root detection | Auto-detect via `.git` |
| `YENGO_LOG_LEVEL` | Log level (DEBUG, INFO, WARNING, ERROR) | `INFO` |

---

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error |
| 2 | Configuration error |
| 3 | Invalid arguments |

---

## Examples

### Full Pipeline Run

```bash
# Standard run
python -m backend.puzzle_manager run

# With verbose output
python -m backend.puzzle_manager run -vv

# Dry run to preview
python -m backend.puzzle_manager run --dry-run
```

### Staged Execution

```bash
# Ingest new puzzles only
python -m backend.puzzle_manager run --stage ingest

# Re-analyze after tag updates
python -m backend.puzzle_manager run --stage analyze

# Publish without re-processing
python -m backend.puzzle_manager run --stage publish
```

### Maintenance

```bash
# Check what needs cleaning
python -m backend.puzzle_manager clean --dry-run

# Clean old files
python -m backend.puzzle_manager clean --retention-days 30

# Generate daily challenges for next week
python -m backend.puzzle_manager daily --start 2026-01-28 --end 2026-02-04
```

### Scripting

```bash
# Get status as JSON
status=$(python -m backend.puzzle_manager status --json)
echo "$status" | jq '.current_run.status'

# List sources as JSON
python -m backend.puzzle_manager sources --json | jq '.[] | select(.enabled)'
```

---

## See Also

- [Architecture](../architecture/backend/puzzle-manager.md) - Puzzle manager architecture
- [Configuration](configuration.md) - Configuration reference
- [Adapter Development](../architecture/backend/adapter-design-standards.md) - Creating adapters
- [Troubleshooting](../how-to/backend/troubleshoot.md) - Common issues and solutions

