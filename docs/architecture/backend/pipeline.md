# Pipeline Architecture

> **See also**:
>
> - [How-To: Run Pipeline](../../how-to/backend/run-pipeline.md) — Operations guide
> - [How-To: CLI Reference](../../how-to/backend/cli-reference.md) — All commands
> - [Architecture: Adapters](./adapters.md) — Source adapters

**Last Updated**: 2026-03-09

Design and data flow for the Puzzle Manager pipeline (v4.0).

---

## Overview

The pipeline transforms external puzzle sources into static browser-ready files:

```text
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   External  │────▶│   Puzzle    │────▶│   GitHub    │────▶│   Browser   │
│   Sources   │     │   Manager   │     │   Pages     │     │  (Frontend) │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
     SGF            Python pipeline      Static CDN        Preact + Canvas
```

---

## 3-Stage Pipeline

| Stage       | Input               | Output                      | Purpose                  |
| ----------- | ------------------- | --------------------------- | ------------------------ |
| **INGEST**  | Sources             | `staging/ingest/`           | Fetch + Parse + Validate |
| **ANALYZE** | `staging/ingest/`   | `staging/analyzed/`         | Classify + Tag + Enrich  |
| **PUBLISH** | `staging/analyzed/` | `yengo-puzzle-collections/` | Index + Daily + Output   |

```text
INGEST ────────▶ ANALYZE ────────▶ PUBLISH
   │                │                  │
   ▼                ▼                  ▼
staging/ingest/   staging/analyzed/   yengo-puzzle-collections/
```

---

## Stage 1: INGEST

**Purpose**: Fetch puzzles from sources, parse SGF, validate structure.

### Ingest Operations

1. **Fetch** — Download or read SGF files via adapters
2. **Parse** — Tokenize SGF, build game tree, extract properties
3. **Validate** — Check board size, stones, solution exists

### Validation Checks

- Valid board size (9, 13, 19)
- Stones within bounds
- Player to move specified
- Solution exists (at least one move)

### Ingest Data Flow

```text
external-sources/           adapters/
├── source-a/              ──▶ AdapterA
├── source-b/              ──▶ AdapterB
└── source-c/              ──▶ AdapterC
                               │
                               ▼
                          staging/ingest/
                          └── {source_id}/
                              └── *.json (validated puzzles)
```

---

## Stage 2: ANALYZE

**Purpose**: Classify difficulty, detect techniques, generate hints.

### Analyze Operations

1. **Classify** — Assign difficulty level (9-level system)
2. **Tag** — Detect techniques (ladder, ko, snapback, etc.)
3. **Enrich** — Generate hints (`YH`), quality metrics (`YQ`, `YX`)

### 9-Level System

| Level | Name               | Rank Range |
| ----- | ------------------ | ---------- |
| 1     | Novice             | 30k-26k    |
| 2     | Beginner           | 25k-21k    |
| 3     | Elementary         | 20k-16k    |
| 4     | Intermediate       | 15k-11k    |
| 5     | Upper Intermediate | 10k-6k     |
| 6     | Advanced           | 5k-1k      |
| 7     | Low Dan            | 1d-3d      |
| 8     | High Dan           | 4d-6d      |
| 9     | Expert             | 7d-9d      |

### Hint Generation

Hints are pedagogically designed by professional Go players.

**Format**: `YH[hint1|hint2|hint3]` (pipe-delimited, max 3)

| Hint # | Content                            | Goal             |
| ------ | ---------------------------------- | ---------------- |
| 1      | Technique identification           | Name the CONCEPT |
| 2      | Reasoning + wrong approach warning | Explain WHY      |
| 3      | Coordinate + technique outcome     | Show WHERE       |

### Analyze Data Flow

```text
staging/ingest/              staging/analyzed/
└── {source_id}/     ──▶  └── {level}/
    └── *.json                └── *.json (with tags, hints, quality)
```

---

## Stage 3: PUBLISH

**Purpose**: Build search databases, generate daily challenges, write final output.

### Operation Ordering & Error Isolation

The publish stage performs operations in a strict order where **file writes are isolated
from metadata updates**. This is a deliberate design choice:

```text
1. SGF files written to disk (per-file loop)
2. Publish log entries flushed (write-ahead)
3. Search databases built from existing + new entries
4. ─── Error boundary ───
5. Inventory updated (try/except — non-fatal)
6. Audit log entry written (try/except — non-fatal)
7. Staging cleanup
```

**Why this order matters**: Steps 1–3 are the pipeline's **primary job** — getting puzzle
files onto disk in the correct structure. Steps 5–6 are **bookkeeping** that track
aggregate statistics. If bookkeeping fails (e.g., filelock timeout, config read error,
disk full), the puzzle files are already safely published and the search database is live.

**The error boundary at step 4** ensures that inventory/audit failures do NOT crash the
publish stage. Instead, errors are logged with a recovery instruction:

```text
ERROR: Failed to update inventory after publishing 2000 files: <error>.
       Run 'inventory --reconcile' to fix.
```

This design reflects a key principle: **data integrity (SGF files + search database) takes
precedence over operational metadata (inventory counts)**. Inventory can always be
rebuilt from disk via `inventory --reconcile`; lost SGF files cannot be recovered.

### Crash Consistency

The publish stage uses **write-ahead logging** for crash safety:

1. Each SGF file is written to disk
2. Immediately after, a publish log entry is flushed to the JSONL log
3. After all files are processed, the search databases are rebuilt from existing + new entries
4. Inventory and audit logs are updated last

If the process crashes mid-loop, the write-ahead publish log ensures every written SGF
has a corresponding log entry. On the next run, **orphan recovery** detects any published
files that weren't included in the database (O(1) detection via state check, O(K) recovery
via publish log diff). The JSONL reader skips corrupted/truncated lines automatically.

**Sub-batch flushing**: BatchState is saved to disk every `flush_interval` files (default: 500)
to reduce data loss window on crash. Configurable via `BatchConfig.flush_interval` or
`--flush-interval N` CLI flag.

### Publish Operations

1. **Orphan Recovery** — Recover entries from crashed previous run (automatic, O(1) detect)
2. **SGF Output** — Write enriched SGF files to batch directories (write-ahead logged)
3. **Database Build** — Incrementally build SQLite databases: merge existing content DB entries with new entries to rebuild `yengo-search.db`, and append new SGF content to `yengo-content.db` via `db_builder` and `content_db`
4. **Daily** — Create daily challenge sets
5. **Inventory** — Update puzzle collection statistics (single-lock read-modify-write)

### Output Structure

```text
yengo-puzzle-collections/
├── .puzzle-inventory-state/          # Operational files (Spec 107)
│   ├── audit.jsonl                   # Cleanup/rollback audit log
│   ├── inventory.json                # Puzzle counts by level/tag
│   ├── publish-log/                  # Run-level publish tracking
│   │   └── {YYYY-MM-DD}.jsonl
│   └── rollback-backup/              # Transaction backups
├── sgf/
│   ├── .batch-state.json             # Global batch counter (single file)
│   ├── {NNNN}/                       # Flat batch dirs (no level nesting)
│   │   └── {content_hash}.sgf
│   └── ...
├── yengo-search.db                   # Search/metadata index (~500 KB)
├── yengo-content.db                  # SGF content + canonical position hash
├── db-version.json                   # Version pointer (puzzle count, timestamp)
└── views/
    └── daily/{YYYY}/{MM}/            # Daily challenges
```

> **Design Decision: Flat SGF Batching**
>
> SGF files are stored in flat `sgf/{NNNN}/` directories without level nesting.
> The level is encoded in each SGF file (`YG` property) and in database entries
> (`level_id` field), NOT in the directory path. This ensures:
>
> - Frontend path reconstruction: `content_hash` + `batch` → `sgf/{batch}/{content_hash}.sgf`
> - No path reconstruction ambiguity in database entries
> - Simpler rollback (single global batch counter, not per-level)
> - Uniform batching across all difficulty levels
> **Note**: Spec 107 separates content (sgf/, views/) from operational metadata
> (.puzzle-inventory-state/) for cleaner CI/CD exclusion patterns.

### Publish Data Flow

```text
staging/analyzed/             yengo-puzzle-collections/
└── {level}/             ──▶  ├── sgf/
    └── *.json                │   └── {NNNN}/
                              │       └── *.sgf
                              ├── yengo-search.db
                              ├── yengo-content.db
                              ├── db-version.json
                              └── .puzzle-inventory-state/
                                  ├── inventory.json
                                  └── publish-log/ (audit trail)
```

---

## Runtime Directory

Default location: `.pm-runtime/` (override with `YENGO_RUNTIME_DIR`)

```text
.pm-runtime/
├── staging/
│   ├── ingest/
│   └── analyzed/
├── state/
│   ├── current_run.json
│   ├── archived/
│   └── publish-log/
└── logs/
    └── pipeline.jsonl
```

---

## State Management

### Run State

Each pipeline run generates a unique `run_id` (format: `YYYYMMDD-xxxxxxxx`).

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
    "source_id": "<source_id>",
    "batch_size": 100,
    "stages": ["ingest", "analyze", "publish"]
  }
}
```

### Resume Support

Pipeline supports resume from checkpoints:

1. State saved after each batch
2. On `--resume`, restore from `config_snapshot`
3. Skip completed batches
4. Maintain original `run_id`

---

## Browser Integration

### Fetch Flow

```text
Browser                       GitHub Pages
   │                              │
   ├──────── GET /db-version.json ───────────────────────────▶
   │◀──────────────────────────────────────────────────────────
   │
   ├──────── GET /yengo-search.db (~500 KB) ─────────────────▶
   │◀──────────────────────────────────────────────────────────
   │
   ├── Initialize sql.js WASM
   ├── Load DB into memory
   ├── All queries via SQL
   │
   ├──────── GET /sgf/0001/YENGO-xxx.sgf ────────────────────▶
   │◀──────────────────────────────────────────────────────────
   │
   ├── Parse SGF (~5KB parser)
   ├── Validate moves
   └── Store progress in localStorage
```

### File Formats

**SGF** (puzzle storage):

```sgf
(;FF[4]GM[1]SZ[9]
YV[15]YG[intermediate]YT[snapback,throw_in]
YQ[q:4;rc:2;hc:1;ac:0]YX[d:5;r:13;s:24;u:1]
YM[{"t":"0000000000000000","i":"run-001"}]
AB[aa][ba][ca]AW[ab][bb]
PL[B]
;B[cb];W[da];B[db];W[ea])
```

**SQLite Database** (search index, yengo-search.db schema):

| Table | Purpose |
|-------|---------|
| `puzzles` | Core metadata: content_hash, batch, level_id, quality, content_type, complexity |
| `puzzle_tags` | Many-to-many: puzzle ↔ tags (all numeric IDs) |
| `puzzle_collections` | Many-to-many: puzzle ↔ collections (with sequence_number) |
| `collections` | Collection catalog: slug, name, category, puzzle_count |
| `collections_fts` | FTS5 full-text search on collection names/slugs |

**Path Reconstruction**: `content_hash` + `batch` → `sgf/{batch}/{content_hash}.sgf`

See [SQLite Index Architecture](../../concepts/sqlite-index-architecture.md) for full DB schema details.

**localStorage** (progress):

```json
{
  "version": 1,
  "solved": ["YENGO-abc123"],
  "streak": 5,
  "lastPlayed": "2026-01-27"
}
```

---

## Design Principles

1. **SGF is source of truth** — All puzzle data stored as SGF with YenGo extensions
2. **SQLite for indexes** — Fast browser lookups via sql.js WASM
3. **localStorage for progress** — No server-side storage
4. **Flat batching** — Max 2000 files per directory (`BatchConfig.max_files_per_dir`)
5. **Config-driven** — Batch sizes and limits in `pipeline.json`, not hardcoded
6. **Deterministic** — Same inputs → identical outputs
7. **Resumable** — Checkpoints after each batch

---

## Batching & Batch Configuration

The publish stage distributes SGF files across numbered batch directories to avoid
filesystem performance degradation from large directories.

| Setting                   | Location        | Default | Purpose                      |
| ------------------------- | --------------- | ------- | ---------------------------- |
| `batch.size`              | `pipeline.json` | 2000    | Max puzzles per pipeline run |
| `batch.max_files_per_dir` | `pipeline.json` | 2000    | Max SGF files per batch dir  |
| `pagination.page_size`    | `pipeline.json` | 500     | Entries per view index page  |

**Source of truth**: `backend/puzzle_manager/config/pipeline.json`

**Data flow**: `pipeline.json` → `BatchConfig` (Pydantic) → `publish.py` → `BatchWriter`

`BatchWriter` does NOT define its own default for `max_files_per_dir` — it is a
required parameter that must come from config. This prevents silent default
shadowing.

### Batch Directory Format

```text
sgf/
├── .batch-state.json    # Global: {current_batch, files_in_current_batch}
├── 0001/                # 4-digit zero-padded, up to 9999 batches
│   ├── abc123.sgf
│   └── def456.sgf
├── 0002/
│   └── ...
```

### Compact Entry Path Reconstruction

- Backend `build_batch_ref()`: `sgf/0001/hash.sgf` → `"0001/hash"` (stored in view indexes)
- Frontend `expandPath()`: `"0001/hash"` → `sgf/0001/hash.sgf` (URL for fetch)

---
