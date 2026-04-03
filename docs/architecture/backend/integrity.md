# Integrity Architecture

> **See also**:
>
> - [How-To: Rollback](../../how-to/backend/rollback.md) — Rollback operations
> - [How-To: Monitor](../../how-to/backend/monitor.md) — Observability
> - [Architecture: Pipeline](./pipeline.md) — Pipeline stages

**Last Updated**: 2026-02-20

Design for puzzle collection integrity: validation, audit trails, trace observability, and rollback.

---

## Overview

YenGo ensures puzzle collection integrity through:

1. **Validation** — Schema and content verification
2. **Trace Observability** — Per-file trace_id through entire pipeline (Spec 110)
3. **Publish Logs** — Audit trail for all changes
4. **Inventory** — Complete collection state
5. **Rollback** — Selective undo by run_id

---

## Trace Observability

### Design Goals

1. **Debug Failed Processing** — Quickly identify why a specific file failed
2. **Audit Provenance** — Trace any published puzzle back to its source
3. **Monitor Progress** — Track batch processing status in real-time

### Trace Map Architecture

Per-run `trace_id` mapping replaces the heavy trace registry. Trace IDs flow via an ephemeral flat JSON file:

```
┌─────────────────────────────────────────────────────────────────────────┐
│ INGEST STAGE                                                            │
│   source_file: sanderland-problems-...-102                              │
│   trace_id:    a1b2c3d4e5f67890     (NEW - generated here)              │
│   run_id:      20260202-abc12345                                        │
│   original_filename: 102.sgf        (extracted from source_link)        │
│   → Collects mapping: {source_file → trace_id}                          │
│   → Writes .trace-map-{run_id}.json at end of stage                     │
│   → Writes .original-filenames-{run_id}.json                            │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ ANALYZE STAGE                                                           │
│   → Loads trace map once at start                                       │
│   → trace_id = trace_map.get(source_file) for each puzzle (O(1) lookup) │
│   → trace_id used in log context for debugging                          │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ PUBLISH STAGE                                                           │
│   → Loads trace map and original filenames map once at start            │
│   → trace_id = trace_map.get(source_file) for each puzzle               │
│   puzzle_id:   fe50f720e43be8cc     (NEW - content hash, GN=YENGO-...)  │
│   → Publish-log: includes trace_id, source_file, original_filename      │
│   → Deletes .trace-map-{run_id}.json after completion (cleanup)         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Trace Map File

**Location**: `.pm-runtime/staging/.trace-map-{run_id}.json` (ephemeral, gitignored)

```json
{
  "sanderland-problems-2c-103": "a1b2c3d4e5f67890",
  "sanderland-problems-2c-104": "b2c3d4e5f6789012"
}
```

### Publish Log Entry with Trace Data

After publish, the **publish log** is the permanent trace record:

```json
{
  "run_id": "20260202-abc12345",
  "puzzle_id": "YENGO-fe50f720e43be8cc",
  "source_id": "sanderland",
  "path": "sgf/0015/fe50f720e43be8cc.sgf",
  "trace_id": "a1b2c3d4e5f67890",
  "source_file": "sanderland-problems-2c-103",
  "original_filename": "103.sgf",
  "level": "intermediate",
  "tags": ["life-and-death"],
  "collections": ["sanderland-collection"],
  "quality": 2
}
```

### Key Properties

| Identifier          | Stage Available | Notes                                |
| ------------------- | --------------- | ------------------------------------ |
| `source_file`       | All stages      | Pipeline-internal puzzle ID          |
| `trace_id`          | All stages      | 16-char hex UUID for log correlation |
| `original_filename` | Published       | Original filename from source        |
| `puzzle_id`         | Publish only    | Content hash (final, in GN property) |

---

## Validation

### Puzzle Validation (v2.0)

Puzzle validation is config-driven from `config/puzzle-validation.json` (schema version 2.0, fail-fast loading — missing config raises `FileNotFoundError`). Two implementations share the same rules:

| Validator               | Location                                          | Used By                                           |
| ----------------------- | ------------------------------------------------- | ------------------------------------------------- |
| `tools.core.validation` | `tools/core/validation.py`                        | Download tools (t-dragon, tsumego_hero, 101weiqi) |
| `PuzzleValidator`       | `backend/puzzle_manager/core/puzzle_validator.py` | Pipeline adapters (OGS, GoProblems, Sanderland)   |

**Validation checks (in order):**

1. Board width within `[min_board_dimension, max_board_dimension]` (default: 5-19)
2. Board height within `[min_board_dimension, max_board_dimension]`
3. Stone count >= `min_stones` (default: 2 — Go-valid minimum for attacker + defender)
4. Solution depth >= `min_solution_depth` (default: 1 — solution must exist)
5. Solution depth <= `max_solution_depth` (default: 30)

### Pipeline Validation

Each stage validates its inputs and outputs:

| Stage   | Validation                                           |
| ------- | ---------------------------------------------------- |
| INGEST  | SGF syntax, board size, stone bounds, solution depth |
| ANALYZE | Level validity, tag existence                        |
| PUBLISH | Schema compliance, no duplicates                     |

### Schema Validation

SGF properties are validated against `config/schemas/sgf-properties.schema.json`:

```bash
python -m backend.puzzle_manager validate
```

Checks:

- Required properties present (GN, YV, YM, YG, YQ, YX)
- Property formats match patterns
- Level slugs exist in config
- Tags exist in config

---

## Publish Logs

### Purpose

Every publish operation creates an audit trail enabling:

- Selective rollback by run_id
- Change history
- Compliance auditing

### Format

JSONL files in `yengo-puzzle-collections/.puzzle-inventory-state/publish-log/`:

```
.puzzle-inventory-state/publish-log/
├── 2026-01-30.jsonl
├── 2026-01-31.jsonl
└── ...
```

> **Note**: Spec 107 moved operational files to `.puzzle-inventory-state/` directory
> to clearly separate content (sgf/, views/) from operational metadata.

### Entry Structure

```json
{
  "run_id": "20260130-abc12345",
  "puzzle_id": "a1b2c3d4e5f67890",
  "source_id": "sanderland",
  "path": "sgf/0001/a1b2c3d4e5f67890.sgf",
  "quality": 2,
  "tags": ["ladder", "snapback"],
  "trace_id": "fedcba0987654321",
  "level": "intermediate",
  "collections": ["cho-chikun-life-death-elementary"]
}
```

**Notes**:

- `puzzle_id` is the 16-char content hash (same as filename). The SGF file's `GN` property uses the `YENGO-{puzzle_id}` format (e.g., `GN[YENGO-a1b2c3d4e5f67890]`).
- `level` and `collections` added in Spec 138 to enable targeted rollback of view indexes.
- `level`, `collections`, and `trace_id` are omitted from JSONL when empty/None for backward compatibility.

### Operations

| Operation | Description               |
| --------- | ------------------------- |
| `add`     | New puzzle added          |
| `update`  | Existing puzzle modified  |
| `delete`  | Puzzle removed (rollback) |

---

## Inventory

### Purpose

The inventory provides:

- Complete puzzle count
- Distribution by level/tag
- Quick state verification

### Location

`yengo-puzzle-collections/.puzzle-inventory-state/inventory.json`

> **Note**: Spec 107 moved operational files to `.puzzle-inventory-state/` directory
> to clearly separate content (sgf/, views/) from operational metadata.

### Structure

```json
{
  "generated_at": "2026-01-30T10:15:30Z",
  "total_puzzles": 5432,
  "by_level": {
    "novice": 234,
    "beginner": 567,
    "intermediate": 890
  },
  "by_tag": {
    "ladder": 234,
    "ko": 123,
    "snapback": 89
  },
  "runs": ["20260130-abc12345", "20260129-def67890"]
}
```

### Querying Inventory

```bash
python -m backend.puzzle_manager inventory

# Output:
# Total puzzles: 5,432
# By level:
#   novice: 234
#   beginner: 567
#   ...
```

### Periodic Reconciliation

A safety net that automatically reconciles inventory after a configurable number of publish runs.

- **Config**: `PipelineConfig.reconcile_interval` (default: 20, 0 = disabled)
- **Tracking**: `AuditMetrics.runs_since_last_reconcile` increments after each publish
- **Trigger**: When counter reaches `reconcile_interval`, reconcile runs automatically
- **Reset**: Counter resets to 0 after each reconcile

This guards against drift from incremental updates over many runs. The reconcile uses `parse_root_properties_only()` (fast root-only SGF parser) with `ThreadPoolExecutor(max_workers=8)` for parallel I/O.

> **See also**: [Inventory Operations](./inventory-operations.md) — Full architecture details

---

## Rollback Design

### Atomic Rollback

Rollback is **atomic** — either all puzzles from a run are removed, or none.

### Process

1. **Identify run** — `python -m backend.puzzle_manager publish-log list`
2. **Preview** — `python -m backend.puzzle_manager rollback --run-id 20260130-abc12345 --dry-run`
3. **Execute** — `python -m backend.puzzle_manager rollback --run-id 20260130-abc12345`

### Rollback Steps

```
1. Read publish-log entries for run_id
2. Collect affected levels, tags, collections from entry metadata
3. Batch-remove all puzzle IDs from affected indexes (single save_state())
4. Delta-decrement distribution counters (no full recompute)
5. Regenerate master indexes
6. Update inventory counts (decrement)
7. Log to audit trail
```

> **Note**: Publish log entries have mandatory `level`, `tags`, and `collections`
> fields. No fallback scanning or SGF parsing is needed for rollback.

### Safety Features

- **Dry-run default** — Preview before executing
- **Confirmation prompt** — Explicit confirmation required
- **Audit trail** — Rollback operations logged
- **Transactional** — Partial rollback leaves consistent state

---

## Cleanup

### Staging Cleanup

```bash
# Preview
python -m backend.puzzle_manager clean --target staging --dry-run

# Execute
python -m backend.puzzle_manager clean --target staging
```

### State Cleanup

```bash
# Reset pipeline state (keeps staging)
python -m backend.puzzle_manager clean --target state
```

### Full Reset

```bash
# Remove staging, state, and logs
python -m backend.puzzle_manager clean --target all
```

---

## Data Retention

| Data Type        | Location                                   | Retention    |
| ---------------- | ------------------------------------------ | ------------ |
| Published SGF    | `yengo-puzzle-collections/sgf/`            | Permanent    |
| View indexes     | `yengo-puzzle-collections/views/`          | Permanent    |
| Publish logs     | `.puzzle-inventory-state/publish-log/`     | Permanent    |
| Inventory        | `.puzzle-inventory-state/inventory.json`   | Permanent    |
| Audit log        | `.puzzle-inventory-state/audit.jsonl`      | Permanent    |
| Rollback backups | `.puzzle-inventory-state/rollback-backup/` | Until commit |
| Staging          | `.pm-runtime/staging/`                     | 45 days      |
| State            | `.pm-runtime/state/archived/`              | 90 days      |
| Logs             | `.pm-runtime/logs/`                        | 30 days      |

### Directory Organization (Spec 107)

```
yengo-puzzle-collections/
├── .puzzle-inventory-state/    # Operational files (hidden)
│   ├── audit.jsonl             # Rollback audit log
│   ├── inventory.json          # Collection statistics
│   ├── publish-log/            # Publish tracking
│   └── rollback-backup/        # Transaction backups
├── sgf/                        # Content (puzzles)
└── views/                      # Content (indexes)
```

---

## Consistency Guarantees

### Write-Ahead Logging

1. Entry written to publish-log BEFORE file written
2. On crash recovery, log is source of truth
3. Incomplete writes are detected and cleaned

### Idempotency

Running the same pipeline twice with same inputs:

- Produces identical outputs
- No duplicate puzzles
- No state corruption

### Verification

```bash
# Check inventory integrity (FR-018 to FR-024)
python -m backend.puzzle_manager inventory --check

# Auto-fix discrepancies by rebuilding
python -m backend.puzzle_manager inventory --check --fix
```

**Integrity Check** (Spec 107) verifies:

- `total_puzzles` equals actual SGF file count (FR-021)
- Level counts match files per level directory (FR-022)
- No orphan entries (publish log entry without file) (FR-019)
- No orphan files (file without publish log entry) (FR-020)
- Exit code 0 if pass, non-zero if fail (FR-023)
