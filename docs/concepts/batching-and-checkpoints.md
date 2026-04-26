# Batching and Checkpoints

> **See also**:
>
> - [How-To: Run Pipeline](../how-to/backend/run-pipeline.md) — Step-by-step pipeline operations
> - [Architecture: Pipeline Design](../architecture/backend/pipeline.md) — Crash consistency design
> - [Reference: CLI Quick Ref](../reference/cli-quick-ref.md) — Command cheat sheet

**Last Updated**: 2026-02-24

How the pipeline processes large datasets in batches with per-file checkpoint safety.

---

## Overview

The pipeline processes puzzles in **batches** — a configurable number of files per run. When the total file count exceeds the batch size, the pipeline processes one batch, saves a checkpoint, and exits. Subsequent runs with `--resume` continue from where the previous run stopped.

This design enables:

- **Controlled resource usage** — avoid processing 10,000 files in one long-running session
- **Incremental progress** — each batch is a self-contained, resumable unit
- **Crash resilience** — at most one file of progress is lost on failure

---

## Batch Size Configuration

| Source       | Mechanism                                | Default                                                   |
| ------------ | ---------------------------------------- | --------------------------------------------------------- |
| Config model | `BatchConfig.size` in `models/config.py` | **2000**                                                  |
| CLI flag     | `--batch-size N`                         | Overrides config                                          |
| Drain mode   | `--drain`                                | Sets batch size to **10,000,000** (effectively unlimited) |

Priority: `--drain` > `--batch-size N` > config default (2000)

### When to Use Each

| Scenario                             | Recommendation                                         |
| ------------------------------------ | ------------------------------------------------------ |
| Testing / development                | `--batch-size 5` — quick feedback                      |
| Normal daily import                  | Default (2000) — balanced throughput                   |
| Large initial import (10,000+ files) | `--drain` if time allows, or default + `--resume` loop |
| CI/CD with time constraints          | `--batch-size 50` — predictable duration               |

---

## Checkpoint Granularity: Per-File

The adapter checkpoint is updated **after every single file**, regardless of outcome (success, failure, or skip). The checkpoint is saved _before_ the result is yielded to the caller, per spec 111 FR-010.

### What the Checkpoint Tracks

```json
{
  "schema_version": 2,
  "adapter_id": "yengo-source",
  "timestamp": "2026-01-15T10:30:00Z",
  "state": {
    "current_folder": "1a-tsumego-beginner",
    "current_folder_index": 0,
    "files_completed": 50,
    "total_processed": 45,
    "total_skipped": 3,
    "total_failed": 2,
    "config_signature": "a1b2c3d4"
  }
}
```

| Field                                                | Meaning                                                                         |
| ---------------------------------------------------- | ------------------------------------------------------------------------------- |
| `current_folder`                                     | Name of the folder currently being processed                                    |
| `current_folder_index`                               | Index in the ordered folder list (for fast skip)                                |
| `files_completed`                                    | Count of files processed in the current folder (1-indexed)                      |
| `total_processed` / `total_skipped` / `total_failed` | Running totals across all folders                                               |
| `config_signature`                                   | MD5 hash of include/exclude folder config — detects config changes between runs |

### Checkpoint Storage

- **Location**: `.pm-runtime/state/{adapter_id}_checkpoint.json`
- **Write method**: Atomic (temp file + rename) via `atomic_write_json()` — safe against mid-write crashes
- **Cleared**: Automatically deleted when all files are processed

---

## Failure Resilience

### Crash Scenarios

| Crash Point                         | Data Lost         | Recovery                                                                   |
| ----------------------------------- | ----------------- | -------------------------------------------------------------------------- |
| Mid-file (reading SGF)              | Current file only | `--resume` picks up from next file                                         |
| After checkpoint save, before yield | Nothing           | `--resume` skips the already-checkpointed file                             |
| Process killed (SIGKILL)            | At most 1 file    | Atomic write ensures checkpoint is either old or new, never corrupt        |
| Disk full during checkpoint         | 0 files           | Atomic write fails cleanly; old checkpoint preserved                       |
| Power loss                          | At most 1 file    | Atomic file rename is filesystem-atomic on most OS/filesystem combinations |

### How Each Outcome Is Handled

Every code path in the adapter saves the checkpoint before yielding:

- **Success** → increment `total_processed`, save checkpoint, yield result
- **Parse error** → increment `total_failed`, save checkpoint, yield `FetchResult.failed`
- **Validation skip** → increment `total_skipped`, save checkpoint, yield `FetchResult.skipped`
- **UnicodeDecodeError** → increment `total_failed`, save checkpoint, yield `FetchResult.failed`
- **OSError** → increment `total_failed`, save checkpoint, yield `FetchResult.failed`
- **ValueError** → increment `total_failed`, save checkpoint, yield `FetchResult.failed`

Failed and skipped files do **not** count toward the batch limit — only successful fetches advance the batch counter.

---

## Two Levels of State Tracking

The pipeline has two independent but complementary state systems:

### 1. Adapter Checkpoint (file-level)

- **Scope**: Which file within which folder to process next
- **Granularity**: Per-file
- **Storage**: `.pm-runtime/state/{adapter_id}_checkpoint.json`
- **Used by**: Adapter `fetch()` during the ingest stage
- **Trigger**: `--resume` flag or `resume: true` in adapter config

### 2. Pipeline State (stage-level)

- **Scope**: Which pipeline stages (ingest/analyze/publish) have completed
- **Granularity**: Per-stage
- **Storage**: `.pm-runtime/state/current_run.json`
- **Used by**: Pipeline coordinator to skip completed stages
- **Trigger**: `--resume` flag

On resume, **both** systems activate: the coordinator skips completed stages, and the adapter skips completed files within the current stage.

---

## Config Change Detection

The checkpoint includes a `config_signature` — an MD5 hash of the adapter's `include_folders` and `exclude_folders` settings. If you change which folders are included between runs:

- The pipeline logs a **warning**: _"Config changed since checkpoint... Consider using resume=false for a fresh start."_
- Processing continues, but folder positions may not align correctly
- **Recommendation**: Clear the checkpoint (`clean --target state`) or run without `--resume` after changing folder config

---

## Multi-Run Workflow for Large Datasets

When importing a source with more files than the batch size (e.g., 10,000 files with default batch of 2000):

### Option A: Multiple Runs with Resume

```bash
# Run 1: processes files 1–2000, saves checkpoint
python -m backend.puzzle_manager run --source yengo-source --stage ingest

# Run 2: processes files 2001–4000
python -m backend.puzzle_manager run --source yengo-source --stage ingest --resume

# Run 3: processes files 4001–6000
python -m backend.puzzle_manager run --source yengo-source --stage ingest --resume

# ... repeat until "Remaining: 0"
# Then analyze and publish
python -m backend.puzzle_manager run --stage analyze --drain
python -m backend.puzzle_manager run --stage publish --drain
```

### Option B: Drain Everything at Once

```bash
# Process all files in one run (may take a long time)
python -m backend.puzzle_manager run --source yengo-source --drain
```

### Option C: Script It

```bash
# Loop until all files are processed
while python -m backend.puzzle_manager run --source yengo-source --stage ingest --resume; do
  echo "Batch complete, continuing..."
done
```

> **Note**: The pipeline exits with status 0 on success. When all files are processed, the checkpoint is cleared and subsequent `--resume` runs start fresh.
