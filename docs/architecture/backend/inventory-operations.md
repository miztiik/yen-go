# Inventory Operations Architecture

> **See also**:
>
> - [Architecture: Integrity](./integrity.md) — Validation, audit, trace observability
> - [Architecture: System Overview](../system-overview.md) — Directory layout and database architecture
> - [How-To: Rollback](../../how-to/backend/rollback.md) — Rollback operations
> - [How-To: CLI Reference](../../how-to/backend/cli-reference.md) — CLI commands

**Last Updated**: 2026-03-10

Design for inventory management operations at scale (300k–500k puzzles). Covers publish, rebuild, reconcile, rollback, and trace search — all optimized for throughput without sacrificing correctness.

---

## Overview

The inventory tracks the complete state of the puzzle collection: counts by level, tag, and collection, quality distribution, audit history, and rollback lineage. Five operations mutate or verify it:

| Operation        | Trigger                        | Complexity                       | SGF Reads                 |
| ---------------- | ------------------------------ | -------------------------------- | ------------------------- |
| **Publish**      | Every pipeline run             | O(batch_size)                    | 0                         |
| **Rebuild**      | `--rebuild` flag               | O(total_entries)                 | 0                         |
| **Reconcile**    | `--reconcile` flag or periodic | O(disk_files)                    | Minimal (root props only) |
| **Rollback**     | `rollback --run-id`            | O(affected_entities × pages)     | 0                         |
| **Trace Search** | `trace search` CLI             | O(1) with indexes, O(n) fallback | 0                         |

---

## Publish → Inventory (Incremental Update)

After each batch is published, the inventory is updated incrementally:

1. `InventoryManager.increment()` adds counts from the new `InventoryUpdate`
2. `runs_since_last_reconcile` counter is incremented
3. If the counter exceeds `reconcile_interval`, a full reconcile is triggered and the counter resets

This is O(batch_size) — no disk scans, no SGF parsing. The publish log entry (which has **mandatory** `level`, `tags`, `collections`, `quality`, and `trace_id` fields) provides all metadata.

### Error Isolation Design

The inventory update is wrapped in a `try/except` in the publish stage. This is a
deliberate architectural choice, not defensive programming:

**Problem**: The publish stage writes SGF files and builds the database BEFORE updating
the inventory. If the inventory update throws an unhandled exception (e.g., filelock
timeout, config file unreadable, Pydantic validation error), the stage executor catches
it and reports the entire stage as "failed" — even though all puzzle files were
successfully written to disk. The audit entry is also lost since it's written after
the inventory update.

**Result**: Puzzle files exist on disk, database is current, but inventory shows zero.
This is the exact scenario that occurred on 2026-03-06 and motivated this design.

**Solution**: Inventory and audit writes are non-fatal. Failures are logged at ERROR
level with a recovery instruction (`inventory --reconcile`). The stage result reports
the actual number of files published, not a blanket failure.

**Why not update inventory first?** The publish stage's primary contract is: "given
analyzed SGF files, produce published output". Inventory is a secondary concern — a
statistical summary that can always be reconstructed from the ground truth (SGF files
on disk). Making inventory failure non-fatal aligns with this priority:

| Component   | Can be rebuilt?                | Recovery method          | Priority    |
| ----------- | ------------------------------ | ------------------------ | ----------- |
| SGF files   | ❌ No (source data may change) | Re-run pipeline          | **Primary** |
| Search DB   | ✅ Yes (from SGF + config)     | Re-run publish           | **Primary** |
| Publish log | ✅ Yes (from SGF metadata)     | Re-run publish           | Secondary   |
| Inventory   | ✅ Yes (from SGF files)        | `inventory --reconcile`  | Secondary   |
| Audit log   | ⚠️ Partial (some events lost)  | Cannot fully reconstruct | Tertiary    |

### Drift Bug History

Previously, a subtle drift bug caused inventory counts to diverge from disk reality over repeated runs. The publish stage accumulated rounding errors in level/tag counts when batches overlapped with existing entries. The fix was twofold:

1. Made publish log fields mandatory (no more guessing from SGF)
2. Added periodic reconciliation as a safety net

---

## Periodic Reconciliation

A configurable safety net that automatically triggers a full reconcile after N publish runs.

**Configuration** (`PipelineConfig`):

```python
reconcile_interval: int = 20  # reconcile every 20 runs (0 = disabled)
```

**Behavior**:

- After each publish, `runs_since_last_reconcile` increments
- When `runs_since_last_reconcile >= reconcile_interval`, reconcile fires
- Reconcile resets the counter to 0
- Setting `reconcile_interval = 0` disables automatic reconciliation

This ensures inventory accuracy even if incremental updates drift over many runs.

---

## Rebuild (Publish-Log Based)

Rebuilds the inventory from publish log metadata only. **Zero SGF reads.**

- Scans all JSONL publish log files
- Extracts `level`, `tags`, `collections`, `quality` from each `PublishLogEntry`
- Detects ghost entries (entries in log but missing from disk) via upfront `rglob` → `set[str]`
- O(total_log_entries) time, I/O-bound on JSONL scan

Use when: inventory state is corrupted or needs full reset from source of truth (publish logs).

---

## Reconcile (Ground-Truth Disk Scan)

Reconciles inventory against actual SGF files on disk. The authoritative source of truth.

**Optimizations**:

- Uses `parse_root_properties_only()` — a fast parser that extracts only root-node SGF properties without parsing the full game tree. Reuses the `SGFParser` tokenizer.
- Parallelized with `ThreadPoolExecutor(max_workers=8)` for file I/O
- Each file result is a lightweight `_FileResult` dataclass

Use when: publish logs may be incomplete, or as periodic safety net.

---

## Cleanup ↔ Inventory Interaction

The `clean --target puzzles-collection` command deletes SGF files, databases, and
publish logs, then conditionally resets inventory to zero.

### Safety Defaults

`cleanup_target("puzzles-collection")` defaults to **dry-run** unless the caller
passes `dry_run=False` explicitly. The CLI layer (`_parse_dry_run_flag`) also defaults
`puzzles-collection` to dry-run. This two-layer safety net prevents accidental
deletion when calling the function directly from scripts or tests.

### Guard: Remaining File Check

After deleting files, the cleanup checks if any SGF files survived (e.g., due to
Windows file locking). An audit entry is written **first**, then inventory is reset
**only if** no files remain:

```python
remaining = count_puzzles_in_dir(output_dir / "sgf")

# 1. Write audit entry FIRST (journal before destructive mutation)
write_cleanup_audit_entry(...)

# 2. Reset inventory only after audit succeeds AND no files remain
if remaining == 0:
    _reset_inventory()  # All zeros, run_id: "clean-{timestamp}"
else:
    logger.warning("Skipping inventory reset: files still exist")
```

This ordering ensures:
- If audit write fails (e.g., disk full), the exception propagates and inventory is
  preserved — no silent state corruption.
- If files remain on disk (e.g., file locking), inventory retains its counts — no
  desync where inventory says 0 but SGF files exist.

### Historical Note: Test Isolation Bug (2026-03-10)

A test in `test_inventory_protection.py` previously patched `get_output_dir` but not
`_reset_inventory()`. Since `_reset_inventory` creates `InventoryManager()` with no
args (resolving to the real inventory path), every pytest run silently zeroed the
production `inventory.json`. This was fixed by mocking `_reset_inventory` in the test.

### Recovery from Desync

If desync does occur (e.g., inventory reset + files still exist, or publish wrote
files but inventory update failed), the recovery path is:

```bash
python -m backend.puzzle_manager inventory --reconcile
```

This scans all SGF files on disk, extracts metadata from root properties, and
rebuilds inventory from ground truth. It is O(disk_files) with 8-thread parallelism.

---

## Rollback

Rolls back a specific pipeline run, removing its published puzzles from disk and rebuilding the database.

### Database-Based Rebuild

Rollback deletes rolled-back entries from `yengo-content.db`, then rebuilds `yengo-search.db` from remaining content DB entries. The `vacuum-db` CLI command can be used to clean orphaned entries and rebuild the search index.

The rebuild is O(total_entries) but runs infrequently and is simple/correct:

1. Delete rolled-back entries from `yengo-content.db`
2. Rebuild `yengo-search.db` from remaining content DB entries
3. Update `db-version.json` atomically

If all puzzles are deleted, `db-version.json` is updated to reflect zero puzzles.

### Inventory Reconciliation

After database rebuild, inventory is fully reconciled from disk (SGF files remain the source of truth for inventory counts).

### Targeted Deletion

Rollback uses publish log entry metadata (`entry.puzzle_id`, `entry.path`) to delete only the affected SGF files. Empty batch directories are automatically cleaned up.

---

## Trace Map

Per-file observability is achieved via an ephemeral trace map file (`.trace-map-{run_id}.json`) in the staging directory. This replaces the previous trace registry JSONL system.

### Design

- **Written once**: At the end of ingest stage
- **Read once**: At the start of analyze and publish stages
- **Deleted**: After publish completes
- **Location**: `.pm-runtime/staging/.trace-map-{run_id}.json` (gitignored)

### Lookup Performance

Trace map is a flat `{source_file: trace_id}` dict loaded into memory. Lookup is O(1) dict access — no JSONL scanning. For a run with 1000 puzzles, the entire trace map is ~50KB JSON.

### Permanent Record

After publish, trace data is persisted in the **publish log**, which includes:

- `trace_id`: 16-char hex UUID for log correlation
- `source_file`: Pipeline-internal puzzle ID
- `original_filename`: Original filename from source adapter

---

## Scale Characteristics

| Metric                        | 100k puzzles | 300k puzzles | 500k puzzles |
| ----------------------------- | ------------ | ------------ | ------------ |
| Publish (per batch of 100)    | <1s          | <1s          | <1s          |
| Rebuild (from logs)           | ~5s          | ~15s         | ~25s         |
| Reconcile (threaded)          | ~10s         | ~30s         | ~50s         |
| Rollback (batch, 100 puzzles) | <2s          | <2s          | <2s          |
| Trace lookup (dict access)    | <1ms         | <1ms         | <1ms         |

All operations scale linearly. At 1M puzzles, the architecture remains the same — publish logs and indexes are the primary data structures, not in-memory collections.

---

## Clean-Slate Decision

As of this implementation, **all legacy format support has been removed**:

- Publish log entries have **mandatory** `quality`, `trace_id`, `level` fields
- View indexes use **compact entries only** (`{p, l, t, c, x}`)
- No backward-compatible fallbacks for `{id, path, level}` entry format
- No slug-based level categorization in daily modules (numeric IDs only)
- No deprecated config methods (`get_enabled_sources`, `ConfigLoader.set_active_adapter`)
- No trace model backward compatibility for missing `original_filename`

This eliminates ~200 lines of defensive code paths and simplifies every read operation.
