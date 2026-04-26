# Monitor Pipeline & Collection

> **See also**:
>
> - [Architecture: Integrity](../../architecture/backend/integrity.md) — Observability design
> - [Run Pipeline](./run-pipeline.md) — Operating the pipeline
> - [Rollback](./rollback.md) — Undoing bad imports

**Last Updated**: 2026-02-02

This guide explains how to monitor and analyze the YenGo puzzle collection using the inventory system.

---

## Overview

The puzzle collection inventory (`puzzle-collection-inventory.json`) provides a single source of truth for collection statistics. It's automatically updated during publish and rollback operations.

---

## Trace Observability (Spec 110)

Every puzzle processed through the pipeline gets a **trace_id** — a unique 16-character hex identifier that follows the puzzle from ingest to publish.

### What is a Trace ID?

- **Format**: 16-character lowercase hex (e.g., `a1b2c3d4e5f67890`)
- **Generation**: Created at ingest stage for each source file
- **Persistence**: Embedded in SGF via `YM` property and recorded in publish log entries
- **Purpose**: End-to-end debugging, audit trails, cross-run correlation

### Trace Status Flow

```
CREATED → INGESTED → ANALYZED → PUBLISHED
            │
            └─► FAILED (with reason)
```

### Trace CLI Commands

```bash
# Search by trace_id
python -m backend.puzzle_manager trace search --trace-id a1b2c3d4e5f67890

# Search by puzzle_id (cross-run correlation)
python -m backend.puzzle_manager trace search --puzzle-id YENGO-abc123def456

# List all traces in a run
python -m backend.puzzle_manager trace search --run-id 20260202-abc12345

# Get summary for a run
python -m backend.puzzle_manager trace summary --run-id 20260202-abc12345

# Output formats
python -m backend.puzzle_manager trace search --trace-id xxx --format json
python -m backend.puzzle_manager trace search --run-id xxx --format jsonl

# Limit results
python -m backend.puzzle_manager trace search --run-id xxx --limit 10
```

### Grep Logs by Trace ID

All log entries include the trace_id for correlation:

```bash
# Find all log entries for a specific trace
grep '"trace_id":"a1b2c3d4e5f67890"' .pm-runtime/logs/pipeline.jsonl | jq .

# Find all failed traces
grep '"status":"failed"' .pm-runtime/logs/pipeline.jsonl | jq .trace_id

# Cross-reference trace with error details
grep 'a1b2c3d4e5f67890' .pm-runtime/logs/*.jsonl
```

### Debug Failed Processing

When a puzzle fails, use trace_id to investigate:

```bash
# 1. Find the failing trace
python -m backend.puzzle_manager trace search --run-id 20260202-abc12345 --format json | \
  jq '.[] | select(.status == "failed")'

# 2. Get full trace details
python -m backend.puzzle_manager trace search --trace-id <trace_id>

# 3. Check logs for that trace
grep '<trace_id>' .pm-runtime/logs/pipeline.jsonl
```

### Audit Published Puzzle Provenance

For any published puzzle, trace back to its source:

```bash
# 1. Get trace_id from publish log
python -m backend.puzzle_manager publish-log search --puzzle-id YENGO-abc123 --format json | \
  jq '.[0].trace_id'

# 2. Find full trace history
python -m backend.puzzle_manager trace search --trace-id <trace_id>

# 3. View all processing events
grep '<trace_id>' .pm-runtime/logs/*.jsonl | jq .
```

---

## Inventory Commands

### View Inventory

```bash
# Human-readable summary
python -m backend.puzzle_manager inventory

# JSON output
python -m backend.puzzle_manager inventory --json

# Rebuild from publish logs
python -m backend.puzzle_manager inventory --rebuild
```

### Sample Output

```
Puzzle Collection Inventory
===========================
Total Puzzles: 15,000

By Level:
  beginner:         3,000 (20.0%)
  intermediate:     5,000 (33.3%)
  advanced:         4,000 (26.7%)
  low-dan:          2,000 (13.3%)
  high-dan:         1,000 (6.7%)

By Tag (top 10):
  life-and-death:   8,000 (53.3%)
  tesuji:           4,000 (26.7%)
  ko:               2,000 (13.3%)
  ladder:           1,000 (6.7%)

Quality Metrics:
  Average Quality Score: 4.2/5.0
  Hint Coverage: 85.0%

Last Updated: 2026-01-30T10:00:00Z
Last Run ID:  20260130-abc12345
```

---

## Log Correlation

Every log entry includes the `run_id` for tracing:

```json
{
  "timestamp": "2026-01-30T10:15:30.123456Z",
  "level": "INFO",
  "run_id": "20260130-abc12345",
  "source_id": "yengo-source",
  "message": "Processing puzzle",
  "puzzle_id": "puz-12345"
}
```

### Filter Logs by Run

```bash
grep '"run_id":"20260130-abc12345"' .pm-runtime/logs/*.jsonl
```

### Find Errors

```bash
grep '"level":"ERROR"' .pm-runtime/logs/pipeline.jsonl | jq .
```

---

## Publish Logs

Every published puzzle is recorded in publish-log files:

```bash
# List all publish logs
python -m backend.puzzle_manager publish-log list

# Search by run ID
python -m backend.puzzle_manager publish-log search --run-id 20260130-abc12345

# Search by puzzle ID
python -m backend.puzzle_manager publish-log search --puzzle-id gp-12345

# Search by source
python -m backend.puzzle_manager publish-log search --source yengo-source
```

Publish log entry format:

```json
{
  "run_id": "20260130-abc12345",
  "puzzle_id": "puz-12345",
  "source_id": "yengo-source",
  "path": "sgf/beginner/batch-0001/puz-12345.sgf",
  "tags": ["life-and-death"],
  "level": "beginner",
  "collections": ["cho-elementary"]
}
```

> **Note** (Spec 138): `level`, `tags`, and `collections` are included to enable
> targeted rollback of view indexes. These fields are omitted when empty/None.

---

## Inventory File

### Location

```
yengo-puzzle-collections/puzzle-collection-inventory.json
```

### Structure

```json
{
  "schema_version": "1.1",
  "last_updated": "2026-01-30T10:00:00Z",
  "last_run_id": "20260130-abc12345",
  "collection": {
    "total_puzzles": 15000,
    "by_puzzle_level": {
      "beginner": 3000,
      "intermediate": 5000,
      "advanced": 4000
    },
    "by_tag": {
      "life-and-death": 8000,
      "tesuji": 4000,
      "ko": 2000
    },
    "avg_quality_score": 4.2,
    "hint_coverage_pct": 85.0
  },
  "stages": {
    "ingest": { "attempted": 16000, "passed": 15500, "failed": 500 },
    "analyze": { "enriched": 15200, "skipped": 300 },
    "publish": { "new": 15000 }
  },
  "audit": {
    "total_rollbacks": 3,
    "last_rollback_date": "2026-01-25T14:30:00Z"
  }
}
```

### Update Rules

The inventory is updated automatically:

1. **On Publish**: Increments `total_puzzles`, `by_puzzle_level`, `by_tag`
2. **On Rollback**: Decrements counts and increments `audit.total_rollbacks`
3. **On Stage Completion**: Updates stage metrics

---

## Stage Status

Check pipeline status:

```bash
python -m backend.puzzle_manager status
python -m backend.puzzle_manager status --json
```

Stage statuses:
| Status | Meaning |
|--------|---------|
| `completed` | Stage finished successfully |
| `failed` | Stage encountered errors |
| `in_progress` | Stage currently running |
| `pending` | Stage not yet started |
| `skipped` | Stage not in requested stages |

---

## Pipeline State

State is persisted in `.pm-runtime/state/`:

```
.pm-runtime/state/
├── current_run.json       # Active run state
├── archived/              # Completed run states
│   └── 20260130-abc12345.json
└── publish-log/           # Publish records (JSONL)
    └── 20260130-abc12345.jsonl
```
