# Run the Puzzle Pipeline

> **See also**:
>
> - [Architecture: Pipeline Design](../../architecture/backend/pipeline.md) — Why this flow
> - [Concepts: Batching and Checkpoints](../../concepts/batching-and-checkpoints.md) — Per-file checkpoint design, failure resilience, multi-run workflows
> - [CLI Reference](./cli-reference.md) — Complete command reference
> - [Troubleshooting](./troubleshoot.md) — Common errors & fixes

**Last Updated**: 2026-02-24

Guide for operating and monitoring the puzzle manager pipeline.

---

## Overview

The puzzle manager pipeline processes Go tsumego puzzles through three stages:

```
INGEST → ANALYZE → PUBLISH
```

Each pipeline run generates a unique `run_id` (format: `YYYYMMDD-xxxxxxxx`) that correlates all logs and state.

---

## Quick Start

```bash
# Run full pipeline for a source (--source is REQUIRED)
python -m backend.puzzle_manager run --source yengo-source

# Run specific stage only
python -m backend.puzzle_manager run --source yengo-source --stage ingest

# Run with custom batch size
python -m backend.puzzle_manager run --source yengo-source --batch-size 50

# Process all pending files (overrides batch size)
python -m backend.puzzle_manager run --source yengo-source --drain

# Dry run (preview without writing files)
python -m backend.puzzle_manager run --source yengo-source --dry-run
```

> **Important**: The `--source` flag is **required**. This ensures consistent log correlation and publish-log entries.

---

## Batch Size Strategy

The `--batch-size` flag controls how many files each stage processes per run:

| Command               | Default batch size | Notes                   |
| --------------------- | ------------------ | ----------------------- |
| `run`                 | 2000               | From `BatchConfig.size` |
| `ingest` (standalone) | 100                | Separate default        |

Use `--drain` to process **all** pending files regardless of batch size. This is useful after accumulating many files across multiple ingest runs.

When the batch size is smaller than the total pending files, the pipeline processes **one batch and exits**. A per-file checkpoint is saved so the next run with `--resume` continues from exactly where it stopped. The CLI output shows how many remain:

```
[OK] Pipeline completed successfully for 'yengo-source'
  Processed: 50 (analyze: 50, publish: 50)
  Remaining: 150 in staging
  Duration: 12.34s
```

> **Checkpoint detail**: The adapter saves a checkpoint after every single file (not per-batch). On crash or interruption, at most one file of progress is lost. See [Batching and Checkpoints](../../concepts/batching-and-checkpoints.md) for full details.

### Large Dataset Workflow

When importing a source with more files than the batch size (e.g., 10,000 files with default batch of 2000), you have three options:

**Option A — Multiple runs with resume:**

```bash
# Each run processes one batch, saves checkpoint, exits
python -m backend.puzzle_manager run --source yengo-source --stage ingest           # files 1–2000
python -m backend.puzzle_manager run --source yengo-source --stage ingest --resume  # files 2001–4000
python -m backend.puzzle_manager run --source yengo-source --stage ingest --resume  # files 4001–6000
# ... repeat until "Remaining: 0", then analyze + publish
python -m backend.puzzle_manager run --stage analyze --drain
python -m backend.puzzle_manager run --stage publish --drain
```

**Option B — Drain everything at once:**

```bash
python -m backend.puzzle_manager run --source yengo-source --drain
```

**Option C — Script a loop:**

```bash
while python -m backend.puzzle_manager run --source yengo-source --stage ingest --resume; do
  echo "Batch complete, continuing..."
done
```

### Choosing `--drain` vs `--batch-size`

| Scenario                    | Recommendation                                         |
| --------------------------- | ------------------------------------------------------ |
| Testing / development       | `--batch-size 5` — quick feedback                      |
| Normal daily import         | Default (2000) — balanced throughput                   |
| Large initial import        | `--drain` if time allows, or default + `--resume` loop |
| CI/CD with time constraints | `--batch-size 50` — predictable duration               |

---

## Crash Recovery

The publish stage is designed for **crash safety**:

- **Write-ahead logging**: Each SGF file gets a publish log entry immediately after being written to disk. If the process crashes, the log entry survives.
- **Sub-batch flushing**: `BatchState` is saved to disk every `flush_interval` files (default: 500). Override with `--flush-interval N`.
- **Orphan recovery**: On the next publish run after a crash, orphaned entries (logged but not in snapshot) are automatically recovered — no user action needed.
- **Atomic state writes**: Pipeline state files use temp-file-then-rename for crash safety.
- **Self-healing JSONL**: Corrupted/truncated publish log lines are safely skipped during reads.

---

## Pipeline Stages

| Stage       | Input               | Output                          | What It Does                                     |
| ----------- | ------------------- | ------------------------------- | ------------------------------------------------ |
| **ingest**  | External source     | `.pm-runtime/staging/ingest/`   | Fetches puzzles from source, validates SGF       |
| **analyze** | `staging/ingest/`   | `.pm-runtime/staging/analyzed/` | Classifies difficulty, adds tags, enriches hints |
| **publish** | `staging/analyzed/` | `yengo-puzzle-collections/`     | Writes to collection, updates indexes            |

### Running Individual Stages

```bash
# Run stages separately
python -m backend.puzzle_manager run --source yengo-source --stage ingest    # Step 1
python -m backend.puzzle_manager run --stage analyze                 # Step 2
python -m backend.puzzle_manager run --stage publish                 # Step 3

# Or combine stages
python -m backend.puzzle_manager run --source yengo-source --stage analyze --stage publish
```

---

## Resuming Interrupted Runs

```bash
# Resume from last checkpoint
python -m backend.puzzle_manager run --resume
```

On resume, the pipeline:

1. Restores `source_id` from the saved `config_snapshot`
2. Continues from the last completed batch
3. Maintains the original `run_id` for correlation

---

## Monitoring

### Check Pipeline Status

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
grep '"run_id":"20260130-abc12345"' .pm-runtime/logs/*.jsonl
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
    "ingest": { "status": "completed", "processed": 100, "failed": 0 },
    "analyze": { "status": "completed", "processed": 95, "failed": 5 },
    "publish": { "status": "completed", "processed": 95, "failed": 0 }
  },
  "config_snapshot": {
    "source_id": "yengo-source",
    "batch_size": 100,
    "stages": ["ingest", "analyze", "publish"]
  }
}
```

---

## Best Practices

1. **Always specify source**: Use `--source` to ensure log correlation
2. **Use dry-run first**: Preview changes before writing
3. **Monitor logs**: Check logs for errors during long runs
4. **Archive state**: State files are auto-archived after completion
5. **Small batches for testing**: Use `--batch-size 5` for testing

---

## Environment Variables

| Variable            | Purpose                                     | Default                          |
| ------------------- | ------------------------------------------- | -------------------------------- |
| `YENGO_RUNTIME_DIR` | Runtime directory for staging, state, logs  | `.pm-runtime/`                   |
| `YENGO_LOG_LEVEL`   | Log verbosity (DEBUG, INFO, WARNING, ERROR) | `INFO`                           |
| `YENGO_CONFIG_DIR`  | Configuration directory                     | `backend/puzzle_manager/config/` |

### Custom Runtime Directory

Override the default runtime directory:

```bash
export YENGO_RUNTIME_DIR=/custom/path
python -m backend.puzzle_manager run --source yengo-source
```

This creates:

```
/custom/path/
├── staging/
├── state/
└── logs/
```

---

## CI/CD Configuration

### GitHub Actions Example

```yaml
jobs:
  import-puzzles:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: |
          cd backend/puzzle_manager
          pip install -e .

      - name: Run pipeline
        env:
          YENGO_RUNTIME_DIR: ${{ runner.temp }}/yengo
          OGS_API_KEY: ${{ secrets.OGS_API_KEY }}
        run: |
          python -m backend.puzzle_manager run --source yengo-source --batch-size 50

      - name: Upload results
        uses: actions/upload-artifact@v4
        with:
          name: pipeline-state
          path: ${{ runner.temp }}/yengo/state/
```

### Docker Example

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY backend/puzzle_manager /app/backend/puzzle_manager
COPY config /app/config

RUN pip install -e /app/backend/puzzle_manager

ENV YENGO_RUNTIME_DIR=/app/runtime
ENV YENGO_CONFIG_DIR=/app/config

CMD ["python", "-m", "backend.puzzle_manager", "run", "--source", "yengo-source"]
```

Run with:

```bash
docker run -v $(pwd)/output:/app/yengo-puzzle-collections \
           -e OGS_API_KEY=$OGS_API_KEY \
           yengo-pipeline
```

---

## Common Workflows

### Daily Import

```bash
# Check current active adapter
python -m backend.puzzle_manager sources

# Run full pipeline
python -m backend.puzzle_manager run --source yengo-source

# Check results
python -m backend.puzzle_manager status
```

### Testing New Source

```bash
# Dry run first
python -m backend.puzzle_manager run --source new-source --batch-size 5 --dry-run

# If looks good, run for real
python -m backend.puzzle_manager run --source new-source --batch-size 5
```

### Recovery After Failure

```bash
# Check what failed
python -m backend.puzzle_manager status

# Resume from checkpoint
python -m backend.puzzle_manager run --resume
```
