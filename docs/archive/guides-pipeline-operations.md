# Pipeline Operations Guide

> ⚠️ **ARCHIVED** — This document is preserved for historical context.
> Current canonical documentation: [docs/how-to/backend/run-pipeline.md](../how-to/backend/run-pipeline.md)
> Archived: 2026-03-24

> **Spec Reference**: 043-pipeline-observability  
> **Last Updated**: 2026-01-30

Guide for operating and monitoring the puzzle manager pipeline.

---

## Overview

The puzzle manager pipeline processes Go tsumego puzzles through three stages:

```
INGEST → ANALYZE → PUBLISH
```

Each pipeline run generates a unique `run_id` (format: `YYYYMMDD-xxxxxxxx`) that correlates all logs and state.

---

## Running the Pipeline

### Basic Usage

```bash
# Run full pipeline for a source (--source is REQUIRED)
python -m backend.puzzle_manager run --source yengo-source

# Run specific stage only
python -m backend.puzzle_manager run --source yengo-source --stage ingest

# Run with custom batch size
python -m backend.puzzle_manager run --source yengo-source --batch-size 50

# Dry run (preview without writing files)
python -m backend.puzzle_manager run --source yengo-source --dry-run
```

> **Important**: The `--source` flag is **required** (per spec 043). This ensures consistent log correlation and publish-log entries.

### Resuming Interrupted Runs

```bash
# Resume from last checkpoint
python -m backend.puzzle_manager run --resume
```

On resume, the pipeline:
1. Restores `source_id` from the saved `config_snapshot`
2. Continues from the last completed batch
3. Maintains the original `run_id` for correlation

---

## Observability Features

### Log Correlation

Every log entry includes the `run_id` for tracing:

```json
{
  "timestamp": "2026-01-30T10:15:30.123456Z",
  "level": "INFO",
  "run_id": "20260130-abc12345",
  "source_id": "yengo-source",
  "message": "Processing puzzle",
  "puzzle_id": "gp-12345"
}
```

Filter logs by run:
```bash
grep '"run_id":"20260130-abc12345"' pm_logs/*.jsonl
```

### Stage Status

Check pipeline status with:
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
| `skipped` | Stage not in requested stages (e.g., `--stage ingest` skips analyze/publish) |

### Publish Log

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
{"run_id":"20260130-abc12345","puzzle_id":"gp-12345","source_id":"yengo-source","path":"sgf/beginner/2026/01/batch-001/gp-12345.sgf"}
```

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

### State File Structure

```json
{
  "run_id": "20260130-abc12345",
  "status": "completed",
  "stages": {
    "ingest": {"status": "completed", "processed": 100, "failed": 0},
    "analyze": {"status": "skipped"},
    "publish": {"status": "skipped"}
  },
  "config_snapshot": {
    "source_id": "yengo-source",
    "batch_size": 100,
    "stages": ["ingest"]
  }
}
```

---

## Troubleshooting

### Pipeline Errors

```bash
# Check status for errors
python -m backend.puzzle_manager status

# View recent logs
tail -100 pm_logs/pipeline.jsonl | jq .

# Find failed puzzles
grep '"level":"ERROR"' pm_logs/pipeline.jsonl
```

### Rollback a Run

```bash
# Preview rollback
python -m backend.puzzle_manager rollback --run-id 20260130-abc12345 --dry-run

# Execute rollback
python -m backend.puzzle_manager rollback --run-id 20260130-abc12345 --reason "Bad data"
```

### Clear Staging

```bash
# Dry run
python -m backend.puzzle_manager clean --target staging --dry-run

# Execute
python -m backend.puzzle_manager clean --target staging
```

---

## Best Practices

1. **Always specify source**: Use `--source` to ensure log correlation
2. **Use dry-run first**: Preview changes before writing
3. **Monitor logs**: Check logs for errors during long runs
4. **Archive state**: State files are auto-archived after completion
5. **Small batches for testing**: Use `--batch-size 5` for testing

---

## Related Documentation

- [CLI Reference](../reference/puzzle-manager-cli.md)
- [Rollback Guide](./rollback.md)
- [Troubleshooting Guide](./troubleshoot.md)
