# Observability Concepts

> **See also**:
>
> - [Architecture: Integrity](../architecture/backend/integrity.md) — Design decisions
> - [How-To: Monitor](../how-to/backend/monitor.md) — Usage guide
> - [Reference: CLI](../reference/cli-quick-ref.md) — Command reference

**Last Updated**: 2026-02-23

Core concepts for pipeline observability: identifiers, logging, and debugging.

---

## Identifiers

The pipeline uses several identifiers to track puzzles through processing:

### run_id

- **Format**: `YYYYMMDD-xxxxxxxx` (date + 8 random hex chars)
- **Scope**: Identifies a single pipeline execution
- **Generation**: Created when pipeline starts
- **Usage**: Group all operations from one run

### trace_id (Spec 110)

- **Format**: 16-character lowercase hex (e.g., `a1b2c3d4e5f67890`)
- **Scope**: Identifies a single file through all stages
- **Generation**: Created at ingest stage entry
- **Usage**: End-to-end debugging and audit trails

### puzzle_id

- **Format**: 16-character lowercase hex (e.g., `765f38a5196edb79`)
- **Scope**: Identifies a published puzzle permanently
- **Generation**: Created at publish stage from content hash
- **Usage**: Filename, publish log entries
- **Note**: SGF `GN` property uses `YENGO-{puzzle_id}` prefix (e.g., `GN[YENGO-765f38a5196edb79]`)

### source_file

- **Format**: Adapter-specific (e.g., `sanderland-problems-2c-103`)
- **Scope**: Identifies file within a source adapter
- **Generation**: Set by adapter during ingest
- **Usage**: Filename in staging directories

---

## ID Relationships

```
INGEST:   source_file → trace_id created
ANALYZE:  trace_id → looked up by source_file
PUBLISH:  trace_id → puzzle_id created, trace_id linked
```

| Identifier  | Ingest | Analyze | Publish | Published |
| ----------- | ------ | ------- | ------- | --------- |
| source_file | ✓      | ✓       | ✓       | —         |
| trace_id    | ✓      | ✓       | ✓       | —         |
| puzzle_id   | —      | —       | ✓       | ✓         |

**Key insight**: `trace_id` is the ONLY identifier that exists across ALL stages.

---

## Trace Status Flow

```
CREATED → INGESTED → ANALYZED → PUBLISHED
    │         │          │
    └─────────┴──────────┴──► FAILED (with reason)
```

| Status      | Stage   | Meaning                           |
| ----------- | ------- | --------------------------------- |
| `created`   | Ingest  | Trace entry created at file entry |
| `ingested`  | Ingest  | SGF parsed and validated          |
| `analyzed`  | Analyze | Level/tags/hints assigned         |
| `published` | Publish | Written to collection             |
| `failed`    | Any     | Processing error (reason stored)  |

---

## Trace Persistence

Trace IDs are persisted in two locations:

1. **SGF files** — `YM` property embeds `trace_id` directly in the puzzle file (e.g., `YM[{"t":"a1b2c3d4e5f67890"}]`)
2. **Publish log** — Each `PublishLogEntry` includes `trace_id` for cross-run querying

### Querying

```bash
# By puzzle_id
python -m backend.puzzle_manager publish-log search --puzzle-id fe50f720e43be8cc

# By run_id (all in run)
python -m backend.puzzle_manager publish-log search --run-id 20260202-abc12345

# By source
python -m backend.puzzle_manager publish-log search --source sanderland
```

> **Historical note**: The trace-registry JSONL system (Spec 110) was removed in favor
> of embedding trace_id in the `YM` SGF property and publish log. This eliminated a
> separate stateful directory and its associated index maintenance.

---

## Logging Integration

Every log entry includes identifiers for correlation:

```json
{
  "timestamp": "2026-02-02T10:15:30.123456Z",
  "level": "INFO",
  "run_id": "20260202-abc12345",
  "trace_id": "a1b2c3d4e5f67890",
  "source_id": "sanderland",
  "message": "Puzzle analyzed",
  "level_assigned": "intermediate"
}
```

### Publish Stage Log Levels

| Log Message                            | Level | When                               |
| -------------------------------------- | ----- | ---------------------------------- |
| `"Publish stage starting"`             | INFO  | Stage start                        |
| `"Progress: N/M (...)"`                | INFO  | Every 100 files                    |
| `"Publish complete: processed=N, ..."` | INFO  | Stage end                          |
| `"Building snapshot: ..."`             | INFO  | Snapshot rebuild                   |
| `"Recovered K orphaned puzzles ..."`   | INFO  | Orphan recovery (after crash)      |
| `"Published puzzle"`                   | DEBUG | Per-file detail (use `-vv` to see) |
| `"Skipping duplicate SGF content ..."` | DEBUG | Per-duplicate detail               |
| `"Flushed batch state at N processed"` | DEBUG | Sub-batch checkpoint               |

**Reducing noise**: Per-file logs are at DEBUG level by default. A 2000-file publish run produces
~25 INFO lines (start + progress every 100 + summary) instead of ~4000+. Use `-vv` for per-file detail.

### Grep Patterns

```bash
# All logs for a trace
grep '"trace_id":"a1b2c3d4e5f67890"' .pm-runtime/logs/pipeline.jsonl

# All failures in a run
grep '"run_id":"20260202-abc12345"' .pm-runtime/logs/pipeline.jsonl | \
  grep '"level":"ERROR"'

# Cross-reference trace with stage
grep 'a1b2c3d4e5f67890' .pm-runtime/logs/*.jsonl | grep analyze
```

---

## Storage Locations

| Data          | Location                               | Retention |
| ------------- | -------------------------------------- | --------- |
| Pipeline logs | `.pm-runtime/logs/`                    | 30 days   |
| Publish logs  | `.puzzle-inventory-state/publish-log/` | Permanent |
| Run state     | `.pm-runtime/state/`                   | 90 days   |

**Note**: `.puzzle-inventory-state/` survives cleanup operations.

---

## Debugging Workflows

### Debug a Failed File

```bash
# 1. Check publish log for a run
python -m backend.puzzle_manager publish-log search --run-id 20260202-abc12345

# 2. Check logs for a specific trace_id
grep '<trace_id>' .pm-runtime/logs/pipeline.jsonl | jq .
```

### Audit a Published Puzzle

```bash
# 1. Find trace from publish log
python -m backend.puzzle_manager publish-log search \
  --puzzle-id YENGO-abc123

# 2. Check logs for that trace_id
grep '<trace_id>' .pm-runtime/logs/pipeline.jsonl | jq .
```

### Compare Across Runs

```bash
# Find all publish log entries for a puzzle
python -m backend.puzzle_manager publish-log search --puzzle-id YENGO-abc123
# Shows processing history across all runs
```

---

## Important Notes

1. **trace_id IS in SGF files** — Embedded in the `YM` property (e.g., `YM[{"t":"a1b2c3d4e5f67890"}]`)
2. **puzzle_id IS in SGF files** — As the `GN` property
3. **Publish log is the permanent trace record** — Each entry includes `trace_id` for correlation
4. **Cross-run correlation uses puzzle_id** — To find same puzzle processed in different runs
