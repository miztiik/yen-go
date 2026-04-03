# Plan: Rebuild-Centric Pipeline Architecture (Schema v12)

> **Status**: Phase 1-2 Complete, Phase 3A+3B Complete, Phase 5-6 Pending  
> **Last Updated**: 2026-02-20  
> **Scope**: Full architectural rewrite — no backward compatibility required  
> **Schema bump**: v10 → v12  
> **Phase 1-2**: Complete (YM property + trace elimination). 1720 passed. Staff reviewed.  
> **Phase 3A**: Complete (inventory model simplification). -3,188 lines. 1614 passed. Staff reviewed.  
> **Phase 3B**: Complete (PipelineLock + rollback rewrite). -2,428 lines. 1582 passed. Staff reviewed — P0 data corruption bugs caught and fixed.

## TL;DR

Replace the current incremental state management (trace sidecars, surgical rollback, dual inventory paths) with a rebuild-from-SGF architecture. Add `YM` property (JSON format) to SGF for pipeline metadata. Rollback simplifies from ~925 lines to ~150 (delete files → full rebuild). Eliminates ~1,800 lines of production code and ~1,700 lines of test code that maintain derived state. All published files can be thrown away and fully regenerated from SGFs + config.

**Core principle**: SGF files are the single source of truth. Everything else (views, inventory, pagination state) is derived and can be rebuilt.

## Architecture: What is Authoritative vs Derived

| State | Authoritative? | Can Be Rebuilt From | Current Maintenance Cost |
|-------|---------------|---------------------|--------------------------|
| `sgf/**/*.sgf` | **YES** — source of truth | N/A — original data | N/A |
| `publish-log/*.jsonl` | **YES** — provenance history | N/A — not derivable | Low (append-only, date-partitioned) |
| `views/by-*/**/*.json` | No — derived | SGF files + config JSONs | ~400L (remove/rebuild paths) |
| `inventory.json` | No — derived | SGF files or view indexes | ~500L (increment/decrement) |
| `.pagination-state.json` | No — derived | Page files or SGF files | ~200L in pagination_writer |
| `.batch-state.json` (×N) | No — derived | Filesystem directory scan | Already has recover fallback |
| `.trace-map-*.json` | No — sidecar | Eliminated (embedded in YM) | 189L (trace_map.py) |
| `.original-filenames-*.json` | No — sidecar | Eliminated (embedded in YM) | Same 189L file |
| `audit.jsonl` | No — duplicates git | Git commit history | ~80L (audit writer) |

## YM Property Design (JSON in SGF)

**Format**: `YM[{"t":"a1b2c3d4e5f67890","f":"Prob0001.json"}]`

| Field | Type | Description | Required |
|-------|------|-------------|----------|
| `t` | string | trace_id — 16-char hex UUID for cross-stage log correlation | Yes |
| `f` | string | original_filename — raw source filename from adapter source_link | No (may be empty) |

**Design decisions:**
- JSON over pipe-delimited: self-describing, extensible (add future fields without positional parsing), standard `json.loads()` parsing
- **Kept in published files**: enables post-hoc debugging without needing pipeline state. Reverses the v8 "provenance in pipeline state, not SGF" decision — trace_id in published SGF is more useful than trace_id in ephemeral sidecar files
- `f` field YAGNI note: currently empty in all 301 publish log entries (adapters don't always set `source_link`). Kept because: low cost (~20 bytes/file), useful when `source_link` IS set, and removing later is harder than carrying forward

**SGF escaping requirement**: The JSON value must be SGF-safe. The `SGFBuilder.build()` method must escape `]` and `\` characters in the YM value per SGF FF[4] spec. Since trace_id is hex-only and original_filename rarely contains `]`, this is defensive but mandatory. The `sgfmill` library handles escaping for standard properties — verify the same escaping applies to custom properties or apply explicitly.

**Defensive parsing**: `parse_pipeline_meta(ym_value)` must handle:
- Missing YM property → return `("", "")`
- Malformed JSON → log warning, return `("", "")`
- Missing `t` or `f` keys → default to `""`
- Old SGFs without YM (pre-v12) → gracefully ignored

## Rollback: Delete + Rebuild

**Current** (925 lines): LockManager + TransactionManager (backup SGFs before delete) + AuditLogWriter + surgical index updates + inventory decrement.

**New** (~200 lines): Date-filtered publish log lookup → identify affected entities (levels/tags/collections) from entries → delete SGF files → `rebuild_affected()` for touched entities only → update inventory from master index counts.

### What's removed and why

| Component | Lines | Why removable |
|-----------|-------|---------------|
| `LockManager` | ~70 | Single-user offline tool. No concurrent agents. Document this assumption explicitly |
| `TransactionManager` | ~100 | File backup before delete is redundant — git IS the backup. Users can `git checkout -- sgf/` to recover |
| `AuditLogWriter` | ~80 | Duplicates git commit history. Publish log itself is the audit trail |
| Surgical index removal | ~420 | Rebuild replaces surgical delta. Idempotent, always correct, no drift |
| Inventory decrement | ~150 | Inventory derived from rebuild, not incrementally maintained |

### Concurrency assumption (explicit)

The rollback-specific `LockManager` is removed. A new **`PipelineLock`** ensures only one pipeline/rollback process runs at a time, replacing both the old `LockManager` and the TOCTOU-vulnerable `ConfigLock`.

### Pipeline Execution Lock (new)

**Current state**: `ConfigLock` in [config/lock.py](backend/puzzle_manager/config/lock.py) protects config edits during runs. It also incidentally prevents concurrent runs (since the second run's `acquire()` fails). But it has a **TOCTOU race** (exists-check then write is not atomic) and **no crash recovery** (stale lock persists forever, requires manual `config-lock release --force`).

**New design**: Replace `ConfigLock` with a unified `PipelineLock` that protects both config AND pipeline execution:

| Aspect | Current `ConfigLock` | New `PipelineLock` |
|--------|---------------------|-------------------|
| **Lock file** | `.pm-runtime/config.lock` | `.pm-runtime/pipeline.lock` |
| **Atomicity** | TOCTOU race (exists-check → write) | Atomic create via `os.open(O_CREAT \| O_EXCL)` — kernel-level atomicity |
| **Crash recovery** | None — manual `--force` required | **PID-alive check**: if lock file exists, check if PID is still running (`os.kill(pid, 0)` on Unix, `psutil` or `ctypes.windll` on Windows). If PID dead → auto-recover (delete stale lock, re-acquire) |
| **Timeout** | `RollbackConfig.lock_timeout_hours` exists but is **never read** (dead config) | Lock file stores `acquired_at`. If lock age > `lock_timeout_hours` → treat as stale, auto-recover |
| **Scope** | Config edits only | Pipeline run + rollback + config edits — single serialization point |
| **Release** | `finally` block in coordinator.py | Same — `finally` block. Also `atexit` handler as safety net |

**Lock lifecycle**:
```
acquire() → O_CREAT|O_EXCL write {run_id, pid, hostname, acquired_at}
  ↓ if file exists:
    read lock file → check PID alive → if dead: delete + retry
    check lock age → if > timeout: delete + retry
    else: raise PipelineLockError("Pipeline already running: run_id=... pid=...")
...pipeline/rollback runs...
release() → delete lock file
```

**Where used**:
- `coordinator.py` — wrap entire pipeline run (ingest/analyze/publish)
- `rollback.py` — wrap rollback operation
- `ConfigWriter` — check lock before config changes (read-only check, same as today)

**Implementation**: ~80 lines in `backend/puzzle_manager/pipeline/lock.py`. Replaces `config/lock.py` (~200L) and the dead `RollbackConfig.lock_timeout_hours`. Net code reduction.

## Inventory Simplification

The current `inventory.json` has accumulated fields over many specs with growing complexity. In a rebuild-centric architecture, several sections are redundant or drift-prone.

### Current inventory.json fields

| Section | Fields | Source of Truth | Verdict |
|---------|--------|----------------|---------|
| `collection.total_puzzles` | int | SGF files on disk | **KEEP** — core metric, derived from rebuild |
| `collection.by_puzzle_level` | dict[str,int] | SGF files (YG) | **KEEP** — derived from rebuild, used by CLI status |
| `collection.by_tag` | dict[str,int] | SGF files (YT) | **KEEP** — derived from rebuild |
| `collection.by_puzzle_quality` | dict[str,int] | SGF files (YQ) | **KEEP** — derived from rebuild |
| `collection.avg_quality_score` | float | Weighted average of quality | **REMOVE** — fragile on rollback (acknowledged drift). Compute on-read from `by_puzzle_quality` distribution: `sum(q*count)/total` |
| `collection.hint_coverage_pct` | float | Requires counting SGFs with YH | **REMOVE** — fragile on rollback. Compute on-read from `rebuild_all()` or on demand |
| `stages.ingest` | attempted/passed/failed | Pipeline run state | **REMOVE** — cumulative across ALL runs, never reset. After 100 runs: `attempted=50000` but `total_puzzles=300`. Misleading. Per-run metrics already in run state files (`.pm-runtime/state/runs/`) |
| `stages.analyze` | enriched/skipped | Pipeline run state | **REMOVE** — same problem as ingest |
| `stages.publish` | new/failed | Pipeline run state | **REMOVE** — same problem |
| `metrics.daily_publish_throughput` | int | Last run count | **REMOVE** — single-run snapshot, not a daily aggregate. Misleading name. Available from run state |
| `metrics.error_rate_ingest` | float | Derived from stages | **REMOVE** — derived from removed fields |
| `metrics.error_rate_publish` | float | Derived from stages | **REMOVE** — derived from removed fields |
| `audit.total_rollbacks` | int | Rollback history | **REMOVE** — can be counted from publish log deletions or git history |
| `audit.last_rollback_date` | datetime | Rollback history | **REMOVE** — same |
| `audit.runs_since_last_reconcile` | int | Reconcile tracking | **REMOVE** — no longer relevant with rebuild-centric architecture (every rollback IS a reconcile) |
| `schema_version` | str | Static | **KEEP** — useful for migration |
| `schema_ref` | str | Static path | **REMOVE** — never used for validation, dead field |
| `last_updated` | datetime | Metadata | **KEEP** |
| `last_run_id` | str | Metadata | **KEEP** |

### Simplified inventory.json (v2)

```json
{
  "schema_version": "2.0",
  "last_updated": "2026-02-20T12:00:00Z",
  "last_run_id": "20260220-81cf9f4d",
  "collection": {
    "total_puzzles": 623,
    "by_puzzle_level": {"novice": 5, "beginner": 287, "elementary": 8},
    "by_tag": {"life-and-death": 300, "tesuji": 150},
    "by_puzzle_quality": {"1": 0, "2": 500, "3": 100, "4": 23, "5": 0}
  }
}
```

**What's removed**: `stages`, `metrics`, `audit`, `avg_quality_score`, `hint_coverage_pct`, `schema_ref`.

**What's kept**: `collection` wrapper with `total_puzzles`, `by_puzzle_level`, `by_tag`, `by_puzzle_quality` (always correct — derived from rebuild). Metadata fields (`schema_version`, `last_updated`, `last_run_id`).

**Code eliminated**: ~200 lines from `inventory/models.py` (remove `StagesStats`, `IngestMetrics`, `AnalyzeMetrics`, `PublishMetrics`, `ComputedMetrics`, `AuditMetrics`), ~150 lines from `inventory/manager.py` (`update_stage_metrics()`, `increment_rollback_audit()`, weighted average math).

### Inventory check simplification

Current `check_integrity()` compares inventory counts vs disk files vs publish log entries. With rebuild-centric architecture:
- **No need to compare inventory vs disk** — inventory IS rebuilt from disk, so it's always correct
- **Orphan detection remains useful**: files on disk with no publish log entry, or publish log entries with no file
- Simplify `check.py` to orphan detection only (~50 lines vs current 223 lines)

## Rebuild Engine

Two functions with different use cases:

### `rebuild_affected()` — used by rollback (selective, fast)

```
Input: output_dir, deleted_puzzle_ids: set[str], affected_levels: set[str],
       affected_tags: set[str], affected_collections: set[str]

1. For each affected level slug:
   a. Load all page files for that level
   b. Filter out entries whose puzzle_id is in deleted_puzzle_ids
   c. Rewrite pages via PaginationWriter._rebuild_index_structure()
2. Repeat for affected tags and collections
3. For collections: re-assign "n" (sequence numbers) after filtering
4. Update master indexes: recompute counts for affected entities only
5. Recompute inventory from master index aggregate counts
```

**Complexity**: O(puzzles_in_affected_entities), NOT O(total_puzzles).
At 1M total, rolling back 100 puzzles touching 2 levels = scan ~20K entries ≈ 1-3s.

### `rebuild_all()` — used by CLI `reconcile` command (full, slow)

```
Input: output_dir (containing sgf/ directory)
Output: views/ directory + inventory.json + .pagination-state.json

1. Scan: rglob("*.sgf") → list of paths
2. Parse: ThreadPoolExecutor(max_workers=8) → parse_root_properties_only() per file
   Extract: puzzle_id (stem), level (from path + YG), tags (YT), collections (YL), complexity (YX), quality (YQ), hints (YH)
3. Build compact entries per file:
   {"p": "batch/hash", "l": level_id, "t": [tag_ids], "c": [col_ids], "x": [d,r,s,u]}
   Uses IdMaps for slug → numeric ID resolution
4. Group entries by level → write pages via PaginationWriter._rebuild_index_structure()
5. Group entries by tag → write pages
6. Group entries by collection → write pages + assign "n" (sequence numbers)
   Sequence rule: sorted by puzzle_id (content hash) within each collection — deterministic
7. Generate master indexes: PaginationWriter.generate_master_indexes()
8. Compute inventory counts as by-product of step 4-6 grouping
9. Write inventory.json
```

**Complexity**: O(total_puzzles). At 1M ≈ ~5 min. Only for manual recovery, never used by rollback.

### Atomicity

Writing 24+ view files isn't atomic. If rebuild crashes midway, views are inconsistent.

**Mitigation**: Write all output to a `views.tmp/` directory, then atomic rename `views/` → `views.old/`, `views.tmp/` → `views/`, delete `views.old/`. This provides crash-consistent view generation. If the process crashes before the rename, the old views remain intact.

### Empty entity handling

After rollback, some levels/tags/collections may have 0 puzzles. Rebuild must:
- Skip entities with 0 entries (no pages generated)
- Exclude 0-count entities from master indexes
- This is inherently correct with the rebuild approach (only non-empty groups produce output)

### Collection sequence numbers (`n` field)

The `n` field provides ordering within a collection. During publish, `n` is assigned incrementally. During rebuild:
- **Deterministic rule**: Sort entries within each collection by puzzle_id (content hash), assign `n = 1, 2, 3, ...`
- This produces stable, reproducible ordering that doesn't depend on publish order
- Trade-off: original publisher-assigned sequence may differ. Acceptable since no backward compatibility needed

## Performance Characteristics

**Target scale: 1,000,000 puzzles.**

### Full rebuild timing (all puzzles)

| Scale | SGF Parse (8 threads) | Entry Building | View Writing | Total Rebuild |
|-------|----------------------|----------------|--------------|---------------|
| 300 puzzles | <0.1s | <0.05s | <0.1s | **<0.3s** |
| 10K puzzles | ~2s | ~0.5s | ~1s | **~3-5s** |
| 100K puzzles | ~15s | ~5s | ~10s | **~30s** |
| 1M puzzles | ~150s | ~50s | ~100s | **~5 min** |

Full rebuild at 1M is unacceptable for rollback (~5 min). **Selective rebuild is mandatory.**

### Selective rebuild (mandatory for rollback)

Rollback does NOT rebuild everything. It rebuilds only the **affected entities**:

1. Read publish log entries for the rolled-back run → extract unique `level`, `tags`, `collections` values
2. Delete only those SGFs
3. For each affected level/tag/collection: scan ONLY the page files for that entity, filter out removed puzzle_ids, rewrite pages
4. Update master indexes (update counts for affected entities only)
5. Recompute inventory from master index counts (O(num_entities), not O(num_puzzles))

**Selective rebuild timing at 1M total puzzles:**

| Rollback scope | Entities affected | Puzzles to re-scan | Time |
|----------------|-------------------|-------------------|------|
| 100 puzzles, 2 levels | 2 level dirs + ~5 tag dirs + ~2 collection dirs | ~20K (puzzles in those entities) | **~1-3s** |
| 1K puzzles, 5 levels | ~5 levels + ~10 tags + ~5 collections | ~100K | **~10-15s** |
| 10K puzzles, all 9 levels | All entities (degrades to full rebuild) | 1M | **~5 min** |

The key insight: rollback typically affects 1-3 levels and a handful of tags. Selective rebuild keeps it under 15 seconds even at 1M total.

**Implementation**: `rebuild_affected(output_dir, affected_levels, affected_tags, affected_collections)` — takes the sets of affected entity slugs from the deleted publish log entries. For each affected entity, reload its page files, filter, rewrite. Unaffected entities are untouched.

### Publish remains incremental

Normal pipeline flow (ingest → analyze → publish) still appends to views incrementally. Rebuild is only triggered by rollback — the rare correction case.

### Publish log query performance

`PublishLogReader` currently does O(n) linear scans across all JSONL files. At 1M puzzles with 90-day retention:
- ~11K entries/day → ~1M entries across 90 JSONL files
- Linear scan per rollback query: ~1-2s (acceptable but noisy)

**Mandatory optimization**: Publish log files are already date-partitioned (`YYYY-MM-DD.jsonl`). Rollback by `run_id` extracts the date prefix (`20260220-...`) → scan only that day's file, not all 90 files. This reduces scan from O(total_entries) to O(entries_per_day) ≈ 11K entries ≈ <100ms. This date-based filtering **must** be implemented in Phase 3-4.

## `.pm-runtime` Directory Optimization

### Current files (what changes with v12)

| Path | Size/Count | After v12 | Reason |
|------|-----------|-----------|--------|
| `logs/*.log` | 4 files/day | **KEEP** | Per-stage logs, needed for debugging |
| `raw/{source}/` | Varies | **KEEP** | Raw download cache (adapter-specific) |
| `staging/ingest/*.sgf` | N files | **KEEP** | SGFs between stages |
| `staging/analyzed/*.sgf` | N files | **KEEP** | Enriched SGFs for publish |
| `staging/failed/{analyze,ingest,publish}/` | Usually empty | **KEEP** | Failed files for debugging |
| `staging/.trace-map-{run}.json` | 1 per run | **ELIMINATE** | Replaced by YM in SGF |
| `staging/.original-filenames-{run}.json` | 1 per run | **ELIMINATE** | Replaced by YM in SGF |
| `state/runs/*.json` | Grows unbounded | **ADD RETENTION** | 4+ files already. Add cleanup for runs older than 90 days (match publish log retention) |
| `state/failures/` | Usually empty | **KEEP** | Failure state tracking |
| `config.lock` | 0-1 file | **REPLACE** | Becomes `pipeline.lock` with atomic create + crash recovery |

### Run state file retention (new)

Run state files in `.pm-runtime/state/runs/` accumulate over time with no cleanup. At 1M puzzles with daily pipeline runs, this means hundreds of JSON files, each ~2-5KB. Add `cleanup_old_run_states(retention_days=90)` to the existing `cleanup_old_files()` function in `pipeline/cleanup.py`. Low priority but prevents unbounded growth.

## Phase Structure: Tests and Documentation

Each implementation phase includes its own tests and documentation. Here's the explicit breakdown:

### Phase 1-2 (Commit 1): YM + Trace Elimination

| Category | What |
|----------|------|
| **Production** | Add YM to parser/builder, set in ingest, read in analyze/publish, delete trace_map.py |
| **Tests deleted** | 5 trace sidecar test files (~1,034L) |
| **Tests created** | 2 new YM test files (pipeline_meta round-trip, defensive parsing) |
| **Tests modified** | 1 file (performance benchmarks — remove trace_map usage) |
| **Docs** | None (deferred to Phase 5-6 to avoid double-editing) |

### Phase 3-4 (Commit 2): Rebuild Engine + Rollback + Lock + Inventory

| Category | What |
|----------|------|
| **Production** | Rebuild engine, rollback rewrite, PipelineLock, inventory simplification, pagination cleanup |
| **Tests deleted** | 4 files (~1,410L): batch_removal, pagination_rollback, inventory_rollback, (parts of inventory_manager) |
| **Tests rewritten** | 3 files (~1,600L): rollback unit, rollback integration, rollback benchmark |
| **Tests created** | 2 new files: rebuild_all unit, rebuild integration E2E |
| **Tests modified** | 4 files: rollback_posix, inventory_manager, compact_entries, inventory_integration |
| **Docs** | None (deferred to Phase 5-6) |

### Phase 5-6 (Commit 3): Documentation + Test Cleanup

| Category | What |
|----------|------|
| **Production** | None |
| **Tests** | Final cleanup — remove any remaining stale assertions, update conftest helpers |
| **Docs rewritten** | 3 files: integrity architecture, observability concepts, rollback how-to |
| **Docs modified** | 9 files: sgf-properties, monitor, cli-reference, cli-quick-ref, cleanup, troubleshoot, CLAUDE.md, backend/CLAUDE.md, copilot-instructions.md |
| **Total doc files** | 12 |

## Implementation Phases

### Phase 1-2: YM Property + Trace Elimination (Commit 1) ✅ COMPLETE

> **Completed**: 2026-02-20  
> **Test results**: 1720 passed, 0 failed, 13 skipped  
> **Staff review**: All P0/P1 issues identified and fixed. Key fixes: `to_game()` property loss (P0-1), `UnboundLocalError` in analyze/publish exception handlers (P0-3/P1-3), `unescape_sgf_value()` added for SGF→JSON safety, schema `current_version` updated.  
> **Additional deliverables**: `unescape_sgf_value()` utility function, 6 unescape unit tests, SGF-escaped JSON parse test.

> Smallest blast radius. Independently testable. After this phase, pipeline works identically but without sidecar files.

**Phase atomicity requirement**: After this commit, the old rollback code (not yet rewritten) must still work. This is safe because `read_trace_map()` already returns an empty dict when the sidecar file doesn't exist, producing `trace_id=""` in publish log entries — the same behavior as today. No import breakage occurs because `trace_map.py` is deleted but rollback.py doesn't import from it (only publish.py and analyze.py do, and both are updated in this phase).

**Production code changes:**

| File | Action | Detail |
|------|--------|--------|
| `core/sgf_parser.py` | Modify (~5L) | Add `pipeline_meta: str \| None = None` to `YenGoProperties`. Parse `YM` in `from_sgf_props()` |
| `core/sgf_builder.py` | Modify (~15L) | Add `set_pipeline_meta(trace_id, original_filename)` method. Emit `YM[{...}]` in `build()`. Ensure SGF escaping of `]` chars |
| `core/trace_utils.py` | Modify (~20L) | Add `parse_pipeline_meta(ym_value: str) -> tuple[str, str]` with defensive JSON parsing |
| `core/schema.py` | Modify (~1L) | `YENGO_SGF_VERSION` → 12 |
| `config/schemas/sgf-properties.schema.json` | Modify (~15L) | Add `YM` definition, version → 12, changelog |
| `stages/ingest.py` | Modify (~30L) | Set YM in SGF instead of accumulating trace_mapping/original_filenames dicts. Remove batch writes |
| `stages/analyze.py` | Modify (~15L) | Read trace_id from `game.yengo_props.pipeline_meta` instead of trace map sidecar |
| `stages/publish.py` | Modify (~30L) | Read trace_id + original_filename from YM instead of sidecars. Remove sidecar loads and deletes |
| `core/trace_map.py` | **DELETE** (189L) | Entire sidecar mechanism replaced |

**Test changes:**

| File | Action | Detail |
|------|--------|--------|
| `tests/unit/test_trace_map.py` | **DELETE** (194L) | Tests deleted module |
| `tests/stages/test_ingest_trace.py` | **DELETE** (227L) | Tests sidecar writing |
| `tests/stages/test_analyze_trace.py` | **DELETE** (193L) | Tests sidecar reading |
| `tests/stages/test_publish_trace.py` | **DELETE** (259L) | Tests sidecar read/cleanup |
| `tests/integration/test_trace_e2e.py` | **DELETE** (161L) | E2E sidecar flow |
| New: `tests/unit/test_pipeline_meta.py` | Create | YM round-trip: set in ingest → read in analyze → survive to publish |
| New: `tests/unit/test_parse_pipeline_meta.py` | Create | Defensive parsing: missing, malformed, empty, valid |
| `tests/integration/test_performance_benchmarks.py` | Modify | Remove trace_map usage |

**Phase gate**: All existing tests pass. Pipeline produces identical output (except SGFs now contain YM property and YV[12]).

### Phase 3-4: Rebuild Engine + Rollback Simplification (Commit 2)

> Core architectural change. Depends on Phase 1-2 being complete.

**Production code changes:**

| File | Action | Detail |
|------|--------|--------|
| `inventory/reconcile.py` | Modify/Extend | Add `rebuild_affected(output_dir, affected_levels, affected_tags, affected_collections) -> RebuildResult` for selective rebuild. Also add `rebuild_all(output_dir)` for full reconciliation (CLI command). Both use `ThreadPoolExecutor(max_workers=8)` and `IdMaps`. Selective rebuild: reload affected entity page files → filter out removed IDs → rewrite pages → update master indexes. Full rebuild: scan all SGFs (for CLI `reconcile` command only, not rollback) |
| `inventory/rebuild.py` | **DELETE** or merge (187L) | Redundant — `rebuild_all()` replaces both `rebuild_inventory()` (from publish logs) and `reconcile_inventory()` (from SGFs). Single path eliminates dual-rebuild confusion |
| `rollback.py` | **REWRITE** (~838L → ~200L) | New `RollbackManager`: date-filtered publish log lookup → delete SGF files → `rebuild_affected()` for only touched levels/tags/collections → update inventory from master index counts. No LockManager, TransactionManager, AuditLogWriter. Acquires `PipelineLock` before operating |
| `pipeline/lock.py` | **CREATE** (~80L) | New `PipelineLock` with atomic `O_CREAT\|O_EXCL`, PID-alive stale detection, timeout-based auto-recovery. Replaces `config/lock.py` |
| `config/lock.py` | **DELETE** (~200L) | Replaced by `pipeline/lock.py`. TOCTOU race and no crash recovery eliminated |
| `inventory/models.py` | Modify (~200L removed) | Remove `StagesStats`, `IngestMetrics`, `AnalyzeMetrics`, `PublishMetrics`, `ComputedMetrics`, `AuditMetrics`. Keep `CollectionStats` wrapper with `total_puzzles`, `by_puzzle_level`, `by_tag`, `by_puzzle_quality`. Remove `avg_quality_score`, `hint_coverage_pct`. New schema v2.0 |
| `inventory/check.py` | **REWRITE** (223L → ~50L) | Simplify to orphan detection only (files without publish log entries, entries without files). Remove inventory-vs-disk count comparisons (rebuild makes them always correct) |
| `models/rollback.py` | **DELETE** (231L) | 6 of 8 models are rollback-only. `PublishLogEntry`/`PublishLogFile` already canonical in `models/publish_log.py`. Define minimal `RollbackResult` in rollback.py |
| `inventory/manager.py` | Modify (~150L removed) | Remove `decrement()` (~120L) and `increment_rollback_audit()` (~28L). Keep `increment()`, `update_stage_metrics()`, `load_or_create()`, `save()` |
| `core/pagination_writer.py` | Modify (~420L removed) | Remove: `remove_puzzles_batch`, `_remove_from_level_no_save`, `_remove_from_tag_no_save`, `_remove_from_collection_no_save`, `_rebuild_pages_delta_distribution`, `rebuild_level`, `rebuild_tag`, `remove_puzzles_from_level`, `remove_puzzles_from_tag`, `remove_puzzles_from_collection`, `_load_all_*_puzzles`. Keep: `_rebuild_index_structure`, `generate_master_indexes`, `append_*` methods |
| `cli.py` | Modify (~30L) | Update rollback command handler for simplified `RollbackResult`. Remove imports from `models/rollback.py` |
| `paths.py` | Modify (minor) | Simplify or remove `get_rollback_backup_dir()` if backup dir eliminated |

**Test changes:**

| File | Action | Detail |
|------|--------|--------|
| `tests/unit/test_rollback.py` (641L) | **REWRITE** | Test new simplified rollback (delete + rebuild) |
| `tests/integration/test_rollback_integration.py` (641L) | **REWRITE** | Full rollback integration tests |
| `tests/integration/test_rollback_benchmark.py` (317L) | **REWRITE** | Rollback performance benchmarks |
| `tests/integration/test_rollback_posix.py` (204L) | Modify | Adapt path handling tests |
| `tests/integration/test_inventory_rollback.py` (446L) | **DELETE** or rewrite | Decrement tests no longer relevant |
| `tests/unit/test_batch_removal.py` (246L) | **DELETE** | Tests `remove_puzzles_batch` (deleted functionality) |
| `tests/unit/test_pagination_rollback.py` (272L) | **DELETE** | Tests rebuild_level/rebuild_tag (deleted) |
| `tests/unit/test_inventory_manager.py` (468L) | Modify | Remove rollback audit tests, keep increment/other tests |
| `tests/unit/test_compact_entries.py` (296L) | Modify | Update distribution recompute tests for rebuild path |
| `tests/integration/test_inventory_integration.py` (429L) | Modify | Update to test rebuild-only path |
| New: `tests/unit/test_rebuild_all.py` | Create | Unit tests for `rebuild_all()` — empty, single, multi-level/tag/collection, sequence numbers |
| New: `tests/integration/test_rebuild_integration.py` | Create | E2E: publish → rollback → verify views rebuilt correctly |

**Phase gate**: Rollback works via delete + rebuild. All views/inventory can be fully reconstructed from SGFs.

### Phase 5-6: Documentation + Test Cleanup (Commit 3)

> Non-functional. Documentation reflects new architecture.

**Documentation updates:**

| File | Action | Sections |
|------|--------|----------|
| `docs/concepts/sgf-properties.md` | Modify | Add YM property, bump version table, add JSON format docs |
| `docs/architecture/backend/integrity.md` | **Heavy rewrite** | Replace "Trace Map Architecture" and "Rollback Design" with rebuild-centric description |
| `docs/concepts/observability.md` | **Heavy rewrite** | Rewrite trace_id lifecycle (now in SGF, not sidecar), remove trace map references |
| `docs/how-to/backend/rollback.md` | **Rewrite** | "What Rollback Does" → delete + rebuild. Remove surgical index update docs |
| `docs/how-to/backend/monitor.md` | Modify | Update trace_id section, publish log format, remove sidecar references |
| `docs/how-to/backend/cli-reference.md` | Modify | Update rollback command docs, remove reconcile/rebuild distinction |
| `docs/reference/cli-quick-ref.md` | Modify | Update rollback and publish log sections |
| `docs/how-to/backend/cleanup.md` | Modify | Update rollback capability references |
| `docs/how-to/backend/troubleshoot.md` | Modify | Update "Rollback Issues" section |
| `CLAUDE.md` | Modify | Add YM to property table, bump schema version references, update trace_id note |
| `backend/CLAUDE.md` | Modify | Add YM to property docs, update trace_id note |
| `.github/copilot-instructions.md` | Modify | Add YM to SGF Custom Properties table, bump version |

## Impact Summary

| Metric | Before | After |
|--------|--------|-------|
| Production code (rollback/trace/inventory) | ~4,400L | ~2,600L (**-1,800L**) |
| Test code (affected files) | ~3,900L | ~2,200L (**-1,700L**) |
| Sidecar files per run | 2 (trace-map + original-filenames) | 0 |
| Rollback complexity | 4 classes, 925L | 1 class, ~150L |
| Inventory maintenance paths | 3 (increment, decrement, rebuild) | 1 (rebuild only) |
| Views rebuild paths | 2 (append + surgical remove) | 1 (append + selective rebuild on rollback) |
| Files deleted entirely | 8 (2 prod + 6 test) | — |
| Files heavily modified | 8 | — |
| Files lightly modified | 5 | — |
| Documentation files | 12 | — |
| **Total blast radius** | **~33 files** | — |

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| SGF escaping breaks YM JSON | Low | High — corrupt SGF | Test with edge-case filenames containing `]` `\` chars |
| Rebuild too slow at scale | Low (selective) | Medium | Selective rebuild per affected entity — O(affected) not O(total). Full rebuild only via CLI `reconcile` command |
| Crash during rebuild leaves inconsistent views | Low | Medium | Atomic temp-dir + rename pattern |
| Concurrent operations without lock | Low | Low | New `PipelineLock` with atomic create + PID-alive stale detection + timeout auto-recovery |
| Lost collection sequence numbers | None (by design) | Low | Deterministic rule: sort by puzzle_id within collection |

## Decisions Log

| Decision | Choice | Alternative Considered | Rationale |
|----------|--------|----------------------|-----------|
| YM format | JSON object | Pipe-delimited (like YH) | Extensible, self-describing field names, standard parsing |
| Property name | YM (Yengo Metadata) | SO (overload standard SGF) | SO is standard FF[4] property — external viewers show raw content |
| Schema version | v12 (skip v11) | v11 | Marks architectural change, not incremental addition |
| Keep YM in published files | Yes | Strip at publish | Enables post-hoc debugging. trace_id in SGF > trace_id in ephemeral sidecar |
| Rebuild on rollback | Selective (affected entities only) | Full rebuild of all views | Full rebuild is O(1M) = ~5 min. Selective is O(affected) = ~1-15s. Full rebuild only available via CLI `reconcile` for manual recovery |
| Remove LockManager | Yes — replaced by PipelineLock | Keep rollback-specific lock | PipelineLock covers pipeline + rollback + config. Single serialization point |
| Remove TransactionManager | Yes | Keep for safety | Git is the backup. `git checkout -- sgf/` recovers any deletion |
| Inventory schema | v2.0 — keep `collection.*` prefix, remove stages/metrics/audit | Keep v1.1 | Stages/metrics are cumulative noise (never reset). Quality averages drift. Rebuild makes counts always correct |
| Pipeline concurrency | PipelineLock with atomic create + crash recovery | Keep ConfigLock | ConfigLock has TOCTOU race, no crash recovery, no PID-alive check |
| Inventory maintenance | Rebuild only | Keep incremental + rebuild | Eliminates drift. One path = one source of truth |
| Collection `n` rule | Sort by puzzle_id | Sort by original_filename | puzzle_id (content hash) is always present; original_filename may be empty |

## Verification

### Automated
- `pytest -m unit` — all unit tests pass
- `pytest -m "not (cli or slow)"` — full regression
- `ruff check .` — no lint warnings

### Manual integration test
1. `clean --target puzzles-collection --dry-run false`
2. `run --source sanderland` (full pipeline: ingest → analyze → publish)
3. Verify published SGFs contain `YM[{"t":"...","f":"..."}]` and `YV[12]`
4. Verify NO sidecar files in `.pm-runtime/staging/` (no `.trace-map-*`, no `.original-filenames-*`)
5. Verify views and inventory match expected counts
6. `rollback --run-id {run-id}` — verify files deleted, views rebuilt, inventory updated
7. Re-run `run --source sanderland` — verify clean re-publish works
