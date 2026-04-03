# Backend Performance at Scale — Implementation Plan

**Last Updated**: 2026-02-19
**Status**: PLANNED — 0% Complete
**Scale Target**: 300,000-500,000 puzzles
**Migration Strategy**: Clean-slate (no backward compatibility — all legacy code deleted)
**Publish Log Fields**: All mandatory (level, tags, quality, trace_id, collections)
**Reconcile Strategy**: Periodic (every N runs, configurable) + explicit CLI
**Companion Plans**: [plan-compact-schema-filtering.md](./plan-compact-schema-filtering.md)

---

## 1. Executive Summary

Eliminate O(n) performance bottlenecks in rebuild, reconcile, rollback, and trace search operations. At 300-500k puzzles, the current pipeline spends **5-15 minutes on rebuild** (full SGF parsing that ignores existing metadata), **90-180 seconds on every publish** (unnecessary full-disk reconcile), and **8-25 seconds on trace searches** (no indexing). The publish log already stores all metadata (level, tags, quality, collections, trace_id) — the code simply doesn't use it.

This is a **clean-slate migration**: existing published collections are empty (0 puzzles in inventory), so there is no legacy data to support. All backward-compatibility code (~200+ lines across 10 files) is deleted. Publish log fields become mandatory. No fallback paths.

### Expert Review

Two expert personas independently validated this plan:

**Principal Systems Architect (Performance)** — Identified the root cause as "re-deriving data from primary sources instead of maintaining materialized indexes." The publish log is the source of truth; all derived state (inventory, indexes, traces) should be materialized views rebuildable from it. Ranked removing reconcile-on-every-publish as the single largest architectural improvement.

**Principal Staff Software Engineer** — Identified `_extract_tags_from_sgf()` calling full `parse_sgf()` while ignoring `entry.tags` as "THE BIGGEST BUG/WASTE in the codebase." Proposed practical optimizations: `parse_root_properties_only()` (no regex, no fragility), `ThreadPoolExecutor` for I/O-bound reconcile, batch ghost-checks via upfront file set.

### Impact at 300-500k Scale

| Operation | Before | After | Speedup |
|-----------|--------|-------|---------|
| Rebuild | 5-15 min | 15-25s | ~20-40x |
| Publish (per run) | 90-180s overhead | <1s overhead | ~100x |
| Reconcile (explicit) | 90-180s | 20-40s | ~4-5x |
| Trace search | 8-25s | <200ms | ~50-100x |
| Rollback (indexes) | 45-180s | 20-60s | ~2-3x |
| Legacy code | ~200 lines | 0 lines | Deleted |

---

## 2. Decisions Registry

| # | Decision | Choice | Rationale |
|---|----------|--------|-----------|
| D1 | Legacy support | **None** — clean-slate | Collection is empty; no data to migrate |
| D2 | Publish log fields | **All mandatory** (level, tags, quality, trace_id) | Eliminates all fallback/scan paths |
| D3 | Reconcile timing | **Periodic (every N runs) + explicit CLI** | Drift bug fixed at root; full scan only as safety net |
| D4 | SGF parsing for metadata | **`parse_root_properties_only()`** (no regex) | Robust parser-based extraction; stops at first move node |
| D5 | Regex for SGF properties | **Removed** | User concern: regex fragility; parser approach is more robust |
| D6 | Rebuild SGF reads | **Eliminated entirely** | Publish log has all metadata; no need to read files |
| D7 | Ghost-check strategy | **Batch upfront** | One `rglob` → `set[str]`, then O(1) lookups |
| D8 | Reconcile parallelism | **`ThreadPoolExecutor` (8 threads)** | I/O-bound; GIL released during file reads |
| D9 | Trace indexing | **Write-time JSON files** + string pre-filter | Layered: quick win first, then structural |
| D10 | Rollback state saves | **Batched** (1 save, not 29) | `remove_puzzles_batch()` method |
| D11 | Rollback distributions | **Delta decrements** | Use removed entries' `l`/`t` values |
| D12 | Page-targeted rollback | **Deferred** | Both personas agree: infrequent operation, batch saves capture most win |
| D13 | SQLite | **Not used** | Violates file-based constraint |
| D14 | New dependencies | **None** | `ThreadPoolExecutor` is stdlib; no new packages |
| D15 | Reconcile interval default | **20 runs** | Configurable in pipeline config |

---

## 3. Architecture: Materialized Views from Publish Log

The publish log is the **source of truth** — it's append-only, immutable per entry, and contains all puzzle metadata. Every other data store is a materialized view rebuildable from it:

```
Source of Truth:   JSONL publish log entries (append-only)
                              │
                              ▼
Materialized Views (incrementally maintained, fully rebuildable):
  ├── inventory.json              (total/level/tag/quality counts)
  ├── .pagination-state.json      (page counts, distribution maps)
  ├── views/by-level/             (paginated puzzle entries)
  ├── views/by-tag/               (paginated puzzle entries)
  ├── views/by-collection/        (paginated puzzle entries)
  ├── trace-registry/             (JSONL per run + index files)
  │   ├── .index-puzzle-id.json   (puzzle_id → [run_ids])
  │   └── .index-trace-id.json   (trace_id → run_id)
  └── master indexes              (level/tag/collection index.json)
```

**Write contract**: Every write (publish, rollback) updates materialized views incrementally.  
**Rebuild contract**: Any materialized view can be deterministically reconstructed from publish log + SGF files on disk.  
**Reconcile contract**: Ground-truth verification — scans actual disk, bypasses publish logs. Used as periodic safety net and explicit repair command.

---

## 4. Phases

### Phase 1 — Mandatory Publish Log Fields + Rebuild Fix

**Branch**: `perf/phase1-mandatory-fields-rebuild`  
**Estimated effort**: Medium  
**Files modified**: ~6  
**Lines removed**: ~80  

#### Steps

**1.1** Make publish log fields mandatory  
**File**: `backend/puzzle_manager/models/publish_log.py`  
- Change `quality: int | None = None` → `quality: int` (L51)
- Change `trace_id: str | None = None` → `trace_id: str` (L53)
- Change `level: str | None = None` → `level: str` (L54)
- Remove conditional `if` guards in `to_jsonl()` (L62-L74) — always write all fields
- Change `.get()` calls in `from_jsonl()` to `data["key"]` (L77-L97) — no defaults

**1.2** Delete `_extract_tags_from_sgf()` and SGF-based rebuild  
**File**: `backend/puzzle_manager/inventory/rebuild.py`  
- Delete `_extract_tags_from_sgf()` function entirely (L37-L55, ~19 lines)
- Remove `from backend.puzzle_manager.core.sgf_parser import parse_sgf` (L29)
- Replace `tags = _extract_tags_from_sgf(sgf_path)` (L132) with `tags = list(entry.tags)`
- Replace `level = extract_level_from_path(entry.path)` (L125) with `level = entry.level`
- Remove `from backend.puzzle_manager.core.fs_utils import extract_level_from_path` import
- Remove quality `None` fallback block (L137-L142) — use `entry.quality` directly

**1.3** Batch ghost-check in rebuild  
**File**: `backend/puzzle_manager/inventory/rebuild.py`  
- Before the main loop, build `existing_files: set[str]` from one `rglob("*.sgf")` walk
- Replace per-entry `sgf_path.exists()` (L106) with `entry.path in existing_files`

**1.4** Fix duplicate-skipping drift bug  
**File**: `backend/puzzle_manager/stages/publish.py`  
- In `_update_inventory()` (L480-L507), replace `reconcile_inventory()` call with incremental `manager.increment()` using `puzzles_by_level`, `puzzles_by_tag`, and quality data already in memory
- The drift root cause: skipped duplicates (L215) don't need re-counting — they were counted when originally published. The increment should only add newly-written files.
- Remove `from backend.puzzle_manager.inventory.reconcile import reconcile_inventory` import if no longer needed in this file

**1.5** Delete test for removed function  
**File**: `backend/puzzle_manager/tests/integration/test_inventory_rebuild.py`  
- Delete `TestExtractTagsFromSgf` class entirely (L103-L131, ~29 lines)
- Remove import of `_extract_tags_from_sgf`
- Update `TestRebuildProducesAccurateCounts` to verify rebuild uses `entry.tags`/`entry.level` from publish log

**1.6** Update publish inventory tests  
**File**: `backend/puzzle_manager/tests/integration/test_inventory_publish.py`  
- Update tests to verify incremental inventory update (no reconcile call)
- Add test: publishing duplicates does not double-count in inventory

**1.7** Update integration tests  
**File**: `backend/puzzle_manager/tests/integration/test_inventory_integration.py`  
- Update `TestRollbackRebuildConsistency` to work with publish-log-based rebuild

#### Success Criteria — Phase 1

| # | Criterion | Verification |
|---|-----------|-------------|
| S1.1 | `PublishLogEntry.level`, `.tags`, `.quality`, `.trace_id` are non-Optional | Type checker + `from_jsonl()` raises `KeyError` on missing fields |
| S1.2 | `_extract_tags_from_sgf()` deleted, `parse_sgf` not imported in rebuild.py | `grep -r "_extract_tags_from_sgf" backend/` returns 0 matches |
| S1.3 | Rebuild reads zero SGF files | Add assertion: no `Path.read_text()` calls during rebuild (mock or log) |
| S1.4 | `reconcile_inventory` not called during publish | `grep "reconcile_inventory" backend/puzzle_manager/stages/publish.py` returns 0 |
| S1.5 | Ghost-check uses set lookup, not per-file `exists()` | Code review: one `rglob` call, set membership check in loop |
| S1.6 | All tests pass: `pytest -m "not (cli or slow)"` | Exit code 0 |
| S1.7 | Duplicate publish does not double-count | New test: publish same batch twice, inventory total unchanged |

#### Post-Implementation Review — Phase 1

**Principal Staff Software Engineer** verifies:
- [ ] No fallback paths remain for `None` quality/level/trace_id in publish log model
- [ ] Rebuild function body has zero file I/O (only publish log JSONL reads + set check)
- [ ] Incremental inventory update correctly handles: first publish, subsequent publishes, skipped duplicates
- [ ] Test coverage: rebuild with mandatory fields, publish without reconcile, duplicate handling

**Principal Systems Architect** verifies:
- [ ] Publish log is treated as source of truth for rebuild (no SGF reads)
- [ ] Inventory update is O(batch_size) not O(total_puzzles)
- [ ] No hidden O(n) operations remain in the publish path
- [ ] Clean separation: reconcile is explicit/periodic only, never called by publish

---

### Phase 2 — Reconcile Speedup

**Branch**: `perf/phase2-reconcile-speedup`  
**Estimated effort**: Medium  
**Files modified**: ~3  
**Lines changed**: ~80  

#### Steps

**2.1** Add `parse_root_properties_only()` to sgf_parser.py  
**File**: `backend/puzzle_manager/core/sgf_parser.py`  
- New function (~30 lines): reuses existing tokenizer, stops after root node (before first `;B[]`/`;W[]` move)
- Returns `dict[str, str]` of property key-value pairs (e.g., `{"YT": "ko,ladder", "YQ": "q:2;rc:0;hc:0"}`)
- No regex, no tree construction — robust and fast (~10-50x faster than full `parse_sgf()`)

**2.2** Replace regex extraction in reconcile.py  
**File**: `backend/puzzle_manager/inventory/reconcile.py`  
- Remove the four precompiled regex patterns (`YT_PATTERN`, `YQ_PATTERN`, `YL_PATTERN`, `YH_PATTERN` at L33-L40)
- Remove `Q_VAL_PATTERN` (L40)
- Replace regex-based extraction in the main loop (L96-L140) with call to `parse_root_properties_only(content)`
- Parse `YQ` quality value from the property string (simple `split(";")/split(":")` — no regex)
- Parse `YT` tags from comma-separated string
- Parse `YL` collections from comma-separated string
- Check `YH` presence for hint coverage

**2.3** Parallelize file reads with `ThreadPoolExecutor`  
**File**: `backend/puzzle_manager/inventory/reconcile.py`  
- Import `concurrent.futures.ThreadPoolExecutor`
- Extract per-file processing into a `_process_single_sgf(sgf_path, output_dir)` function
- Use `ThreadPoolExecutor(max_workers=8)` to process files concurrently
- Aggregate results from futures into counters in the main thread
- Maintain progress logging (every 1,000 files)

**2.4** Add tests for `parse_root_properties_only()`  
**File**: `backend/puzzle_manager/tests/unit/test_sgf_parser.py` (or new test file)  
- Test: extracts YT, YQ, YL, YH, YG, YV from root node
- Test: stops before move nodes (does not parse solution tree)
- Test: handles SGF with no custom properties (returns empty dict)
- Test: handles malformed root node gracefully

#### Success Criteria — Phase 2

| # | Criterion | Verification |
|---|-----------|-------------|
| S2.1 | `parse_root_properties_only()` exists and returns dict | Unit tests pass |
| S2.2 | No regex patterns (`YT_PATTERN` etc.) in reconcile.py | `grep "PATTERN" backend/puzzle_manager/inventory/reconcile.py` returns 0 |
| S2.3 | Reconcile uses `parse_root_properties_only()` | Code review: call site in main loop |
| S2.4 | ThreadPoolExecutor with 8 workers used | Code review: `ThreadPoolExecutor(max_workers=8)` |
| S2.5 | All tests pass: `pytest -m "not (cli or slow)"` | Exit code 0 |
| S2.6 | Reconcile at 52k files (external-sources) completes in <30s | Manual timing: `time python -m backend.puzzle_manager inventory --reconcile` |

#### Post-Implementation Review — Phase 2

**Principal Staff Software Engineer** verifies:
- [ ] `parse_root_properties_only()` correctly stops at first move node
- [ ] No regex patterns remain in reconcile.py
- [ ] Thread safety: per-file processing function has no shared mutable state
- [ ] Progress logging still works with threaded execution
- [ ] Error handling: individual file failures don't crash the entire reconcile

**Principal Systems Architect** verifies:
- [ ] `parse_root_properties_only()` is O(root_node_size), not O(file_size)
- [ ] ThreadPoolExecutor parallelism is I/O-bound (GIL released during file reads)
- [ ] Reconcile still serves as ground-truth disk verification (independent of publish log)
- [ ] No correctness regression: reconcile output matches pre-optimization output for same input

---

### Phase 3 — Periodic Reconciliation Safety Net

**Branch**: `perf/phase3-periodic-reconcile`  
**Estimated effort**: Low  
**Files modified**: ~4  
**Lines added**: ~40  

#### Steps

**3.1** Add `runs_since_last_reconcile` to AuditMetrics  
**File**: `backend/puzzle_manager/inventory/models.py`  
- Add field: `runs_since_last_reconcile: int = 0` to `AuditMetrics` (after L94)
- This field increments on every publish and resets to 0 on reconcile

**3.2** Add `reconcile_interval` to pipeline config  
**File**: `backend/puzzle_manager/models/config.py`  
- Add field: `reconcile_interval: int = 20` (range 1-1000) — how many publish runs between automatic reconciles
- Document in field description: "Number of publish runs between automatic periodic reconciliation. Set to 0 to disable."

**3.3** Implement periodic reconcile trigger in publish  
**File**: `backend/puzzle_manager/stages/publish.py`  
- In `_update_inventory()`, after incremental update:
  - Increment `runs_since_last_reconcile` in audit metrics
  - If `runs_since_last_reconcile >= reconcile_interval` and `reconcile_interval > 0`:
    - Log: `"Periodic reconciliation triggered (every {interval} runs)"`
    - Call `reconcile_inventory()`
    - Reset `runs_since_last_reconcile = 0`
  - Save inventory

**3.4** Reset counter on explicit reconcile  
**File**: `backend/puzzle_manager/inventory/reconcile.py`  
- After successful reconcile, set `audit.runs_since_last_reconcile = 0` in the returned inventory

**3.5** Add tests  
**Files**: `backend/puzzle_manager/tests/integration/test_inventory_cli.py`, `backend/puzzle_manager/tests/integration/test_inventory_publish.py`  
- Test: `runs_since_last_reconcile` increments on publish
- Test: periodic reconcile triggers at threshold
- Test: explicit `--reconcile` resets counter
- Test: `reconcile_interval=0` disables periodic reconcile

#### Success Criteria — Phase 3

| # | Criterion | Verification |
|---|-----------|-------------|
| S3.1 | `AuditMetrics.runs_since_last_reconcile` field exists | Model validates, serializes/deserializes correctly |
| S3.2 | `reconcile_interval` configurable with default 20 | Config model validates range |
| S3.3 | Counter increments on publish | Test: publish 3 times → counter = 3 |
| S3.4 | Counter triggers reconcile at threshold | Test: set interval=2, publish 2 times → reconcile called |
| S3.5 | Counter resets on explicit reconcile | Test: counter > 0, run `--reconcile`, counter = 0 |
| S3.6 | `reconcile_interval=0` disables periodic | Test: set to 0, publish 100 times → reconcile never called |
| S3.7 | All tests pass: `pytest -m "not (cli or slow)"` | Exit code 0 |

#### Post-Implementation Review — Phase 3

**Principal Staff Software Engineer** verifies:
- [ ] Counter is persisted in inventory.json (survives process restarts)
- [ ] Edge case: counter does not overflow or wrap
- [ ] `reconcile_interval=0` is respected (disabled, not infinite loop)
- [ ] Periodic reconcile uses the optimized reconcile from Phase 2

**Principal Systems Architect** verifies:
- [ ] Periodic reconcile is a safety net, not a correctness requirement
- [ ] Default interval (20) is reasonable for 300-500k scale
- [ ] No performance regression on normal publish path (counter increment is O(1))

---

### Phase 4 — Trace Search Optimization

**Branch**: `perf/phase4-trace-search`  
**Estimated effort**: Medium  
**Files modified**: ~2  
**Lines added**: ~70  

#### Steps

**4.1** Add string pre-filter before JSON deserialization  
**File**: `backend/puzzle_manager/trace_registry.py`  
- In `search_by_puzzle_id()`: construct `needle = f'"puzzle_id":"{puzzle_id}"'`, check `if needle in line:` before `json.loads(line)`
- In `find_by_trace_id()` (cross-run search): same pattern with `f'"trace_id":"{trace_id}"'`
- In `find_by_source_file_any_run()`: same pattern with source_file needle
- This eliminates ~99.99% of JSON parsing (only matching lines are deserialized)

**4.2** Build write-time JSON index for puzzle_id  
**File**: `backend/puzzle_manager/trace_registry.py`  
- New method `_update_puzzle_index(puzzle_id, run_id)` — maintains `.index-puzzle-id.json` mapping `{puzzle_id: [run_id1, run_id2, ...]}`
- Called from trace write path
- `search_by_puzzle_id()` reads index first → only scans matched run files

**4.3** Build write-time JSON index for trace_id  
**File**: `backend/puzzle_manager/trace_registry.py`  
- New method `_update_trace_index(trace_id, run_id)` — maintains `.index-trace-id.json` mapping `{trace_id: run_id}`
- Called from trace write path
- `find_by_trace_id()` (without run_id) reads index → O(1) lookup instead of scanning all files

**4.4** Add `rebuild_indexes()` recovery method  
**File**: `backend/puzzle_manager/trace_registry.py`  
- Single-pass over all JSONL files → rebuilds both index files
- Called manually or from CLI: `python -m backend.puzzle_manager trace rebuild-indexes`

**4.5** Add tests  
**File**: `backend/puzzle_manager/tests/unit/test_trace_registry.py` (or appropriate test file)  
- Test: string pre-filter returns same results as full scan
- Test: write-time index is updated on trace write
- Test: `search_by_puzzle_id` uses index for O(1) run-file targeting
- Test: `rebuild_indexes()` produces correct indexes from JSONL data
- Test: missing index falls back to full scan (graceful degradation)

#### Success Criteria — Phase 4

| # | Criterion | Verification |
|---|-----------|-------------|
| S4.1 | String pre-filter in `search_by_puzzle_id`, `find_by_trace_id` | Code review: `needle in line` check before `json.loads()` |
| S4.2 | `.index-puzzle-id.json` maintained on write | Test: write trace → index file updated |
| S4.3 | `.index-trace-id.json` maintained on write | Test: write trace → index file updated |
| S4.4 | `rebuild_indexes()` produces correct output | Test: corrupt indexes → rebuild → correct result |
| S4.5 | Trace search at 200k entries < 200ms | Manual timing or benchmark test |
| S4.6 | Missing index falls back to full scan | Test: delete index files → search still works |
| S4.7 | All tests pass: `pytest -m "not (cli or slow)"` | Exit code 0 |

#### Post-Implementation Review — Phase 4

**Principal Staff Software Engineer** verifies:
- [ ] Index files are valid JSON, atomically written (temp + rename)
- [ ] Write-time index update is O(1) amortized (JSON read + append + write)
- [ ] Pre-filter needle construction handles edge cases (special chars in IDs — but IDs are hex, so N/A)
- [ ] Graceful degradation: all code paths work without index files

**Principal Systems Architect** verifies:
- [ ] Index file size at 500k entries: `.index-puzzle-id.json` ≈ 15-25MB (acceptable)
- [ ] No consistency risk: index is append-only during normal operation, reconstructible via `rebuild_indexes()`
- [ ] Index is NOT the source of truth — JSONL files are. Index is a cache.

---

### Phase 5 — Rollback Efficiency + Legacy Code Deletion

**Branch**: `perf/phase5-rollback-legacy-cleanup`  
**Estimated effort**: Medium-High  
**Files modified**: ~12  
**Lines removed**: ~200+  

#### Steps

##### 5A. Rollback Legacy Removal

**5.1** Delete rollback legacy fallback code  
**File**: `backend/puzzle_manager/rollback.py`  
- Delete level fallback via `extract_level_from_path()` (L756-L758)
- Delete tag scan fallback — scanning ALL tag indexes when entry lacks tags (~22 lines, L789-L810)
- Delete collection scan fallback — scanning ALL collection indexes (~20 lines, L832-L852)
- Simplify `entry.level or extract_level_from_path(entry.path)` (L882) → `entry.level`
- Delete dead `_remove_from_index()` method (55 lines, L923-L978, 0 callers)

**5.2** Delete PaginationWriter legacy entry handling  
**File**: `backend/puzzle_manager/core/pagination_writer.py`  
- `_extract_puzzle_id_from_entry()`: delete `"path"` and `"id"` branches (L45-L50)
- `_read_page()`: remove `data.get("puzzles", [])` fallback (L498) → just `data.get("entries", [])`
- `_scan_paginated_directory()`: same `"puzzles"` fallback removal (L400)
- `_get_entry_key()`: simplify to `entry.get("p", "")` (L632-L637)
- Clean up comments referencing "legacy" format

**5.3** Delete daily module legacy branches  
**Files**: `backend/puzzle_manager/daily/_helpers.py`, `backend/puzzle_manager/daily/by_tag.py`, `backend/puzzle_manager/daily/standard.py`, `backend/puzzle_manager/daily/timed.py`  
- `_helpers.py`: remove `puzzle.get("id", "")` fallback in `extract_puzzle_id()` (L193)
- `_helpers.py`: delete legacy `{id, path, level}` branch in `to_puzzle_ref()` (L215-L219)
- `by_tag.py`: delete legacy `"tags"` slug check in `_has_tag()` (L151-L154)
- `standard.py`: remove legacy slug branches from `_is_beginner`, `_is_intermediate`, `_is_advanced` (L120-L150, 3 functions)
- `timed.py`: remove legacy slug branches from `_is_easy`, `_is_medium`, `_is_hard` (L124-L159, 3 functions)

**5.4** Delete deprecated config methods  
**File**: `backend/puzzle_manager/config/loader.py`  
- Delete `get_enabled_sources()` (L218-L234)
- Delete `set_active_adapter()` on ConfigLoader (L401-L414)

**5.5** Delete trace model backward compat  
**File**: `backend/puzzle_manager/models/trace.py`  
- Remove `if "original_filename" not in data: data["original_filename"] = None` (L159)

##### 5B. Rollback Performance

**5.6** Add `remove_puzzles_batch()` to PaginationWriter  
**File**: `backend/puzzle_manager/core/pagination_writer.py`  
- New method: processes all affected levels, tags, collections in one pass
- Calls internal `_remove_from_level_no_save()` etc. (suppressed per-entity saves)
- Single `save_state()` at the end

**5.7** Delta distribution updates during rollback  
**File**: `backend/puzzle_manager/core/pagination_writer.py`  
- In `_rebuild_index_structure()` or a new method: when removing entries, decrement `tag_distribution`/`level_distribution` by the removed entries' `t`/`l` values instead of recomputing from all remaining entries
- The compact entries already contain `l` (level id) and `t` (tag ids) — use them directly

**5.8** Wire rollback to use batch method  
**File**: `backend/puzzle_manager/rollback.py`  
- In `_update_indexes()`, replace individual `remove_puzzles_from_level/tag/collection` calls with single `remove_puzzles_batch()` call

**5.9** Update tests for legacy removal  
**Files**: Various test files  
- Update tests that use legacy entry formats (`{id, path, level}`) to use compact format (`{p, l, t, c, x}`)
- Add test for `remove_puzzles_batch()` — single state save verified
- Add test for delta distribution: remove 10 entries, verify distributions match full recompute
- Remove tests for deleted functions/methods

#### Success Criteria — Phase 5

| # | Criterion | Verification |
|---|-----------|-------------|
| S5.1 | Zero legacy fallback code in rollback.py | `grep -n "extract_level_from_path\|Legacy\|fallback\|scan all" rollback.py` returns 0 matches for fallback paths |
| S5.2 | `_remove_from_index()` deleted | `grep "_remove_from_index" rollback.py` returns 0 |
| S5.3 | No `"path"`, `"id"`, `"puzzles"` key lookups in pagination_writer.py | `grep '"path"\|"id"\|"puzzles"' pagination_writer.py` returns 0 |
| S5.4 | No legacy slug branches in daily modules | `grep "puzzle.get.*level\|puzzle.get.*id\|puzzle.get.*tags" daily/*.py` returns 0 for legacy patterns |
| S5.5 | Deprecated config methods deleted | `grep "DEPRECATED\|get_enabled_sources\|set_active_adapter" loader.py` returns 0 |
| S5.6 | `remove_puzzles_batch()` exists and is used by rollback | Code review: rollback calls batch method |
| S5.7 | Rollback produces 1 state save, not 29 | Test: mock `save_state()`, verify call count = 1 |
| S5.8 | All tests pass: `pytest -m "not (cli or slow)"` | Exit code 0 |

#### Post-Implementation Review — Phase 5

**Principal Staff Software Engineer** verifies:
- [ ] All ~200 lines of legacy code confirmed deleted (diff review)
- [ ] No orphaned imports after deletions
- [ ] `remove_puzzles_batch()` correctly handles: empty input, single entity, many entities
- [ ] Delta distribution produces identical results to full recompute (test with known data)
- [ ] Test coverage: no reduction in meaningful test coverage (only legacy-format tests removed)

**Principal Systems Architect** verifies:
- [ ] Rollback is O(affected_entities × pages_per_entity) with 1 state save — not O(affected_entities × pages × state_saves)
- [ ] Delta distribution eliminates the secondary O(n) loop during rollback rebuild
- [ ] No hidden backward-compat assumptions remain in the codebase
- [ ] Daily module functions are clean: one code path per function (compact format only)

---

### Phase 6 — Documentation & Benchmark Tests

**Branch**: `perf/phase6-docs-benchmarks`  
**Estimated effort**: Low-Medium  
**Files modified/created**: ~5  

#### Steps

**6.1** Create architecture document  
**File**: `docs/architecture/backend/inventory-operations.md`  
Content:
- **Publish → Inventory**: Incremental update, O(batch_size). Drift bug history and fix.
- **Periodic Reconciliation**: Safety net (configurable interval). When it triggers. How to adjust.
- **Rebuild**: Uses publish log metadata only. Zero SGF reads. O(total_entries) for JSONL scan.
- **Reconcile**: Ground-truth disk scan. Uses `parse_root_properties_only()`. Parallelized with ThreadPoolExecutor. When to use.
- **Rollback**: Batch state saves. Delta distribution updates. O(affected_entities × pages). Targeted removal via publish log entry metadata (level, tags, collections always present).
- **Trace Registry**: Write-time JSON indexes. String pre-filter. Rebuild-indexes recovery.
- **Scale Characteristics**: Performance table at 100k, 300k, 500k puzzles.
- **Cross-references**: Links to [integrity.md](../docs/architecture/backend/integrity.md), [view-index-pagination.md](../docs/architecture/backend/view-index-pagination.md), [rollback.md](../docs/how-to/backend/rollback.md)
- **Clean-slate decision**: No backward compatibility. Mandatory publish log fields. Date of migration.

**6.2** Update CLI reference  
**File**: `docs/how-to/backend/cli-reference.md`  
- Update `--reconcile` vs `--rebuild` comparison table: reconcile is no longer auto-run, only explicit + periodic
- Document periodic reconcile behavior and `reconcile_interval` config

**6.3** Update integrity doc  
**File**: `docs/architecture/backend/integrity.md`  
- Add section on periodic reconciliation
- Update rollback section to reflect batch state saves and delta distributions

**6.4** Add benchmark tests  
**File**: `backend/puzzle_manager/tests/integration/test_performance_benchmarks.py` (new)  
- Marked `@pytest.mark.slow`
- Benchmark: rebuild with 1k, 5k, 10k publish log entries (no SGF reads)
- Benchmark: reconcile with 1k, 5k, 10k SGF files (threaded)
- Benchmark: trace search with 1k, 5k entries across 10, 50 runs
- Benchmark: rollback batch removal from 5k entries across 5 levels, 10 tags
- Each benchmark asserts completion within time threshold (generous for CI)

**6.5** Run full test suite  
- `pytest` — full suite, all tests pass
- `ruff check .` — no lint warnings
- Manual timing comparison on external-sources data (52k+ files)

#### Success Criteria — Phase 6

| # | Criterion | Verification |
|---|-----------|-------------|
| S6.1 | `docs/architecture/backend/inventory-operations.md` exists | File present with all sections |
| S6.2 | CLI reference updated | `--reconcile` docs reflect new behavior |
| S6.3 | Integrity doc updated | Periodic reconciliation section present |
| S6.4 | Benchmark tests exist and pass | `pytest -m slow` passes |
| S6.5 | Full test suite passes | `pytest` exit code 0 |
| S6.6 | No lint warnings | `ruff check .` exit code 0 |

#### Post-Implementation Review — Phase 6

**Principal Staff Software Engineer** verifies:
- [ ] Documentation accurately reflects implemented behavior (not aspirational)
- [ ] Benchmark thresholds are realistic for CI (not just fast local machines)
- [ ] Cross-references in docs are valid links
- [ ] No stale documentation references to removed features (reconcile-on-publish, legacy formats)

**Principal Systems Architect** verifies:
- [ ] Architecture doc tells the "why" story: materialized views, source of truth, clean-slate decision
- [ ] Scale characteristics table has credible numbers backed by benchmark data
- [ ] Future scaling path is clear: what changes at 1M? (answer: mostly nothing — log-based architecture scales linearly)

---

## 5. Git Safety & Branch/Merge/Commit Process

All git operations follow the [Git Safety Prompt](../docs/reference/git-safety-prompt.md). This section provides the exact workflow for the coding agent.

### 5.1 Forbidden Commands (NEVER USE)

```bash
# These will PERMANENTLY DESTROY untracked files
❌ git stash              # Any variant
❌ git reset --hard       # Destroys uncommitted changes
❌ git clean -fd          # Deletes untracked files
❌ git checkout .         # Reverts all tracked changes
❌ git restore .          # Same as checkout .
❌ git add .              # Stages everything including others' files
❌ git add -A             # Same as git add .
```

### 5.2 Protected Directories

These directories contain runtime/crawled data NOT tracked by git. Destructive git operations will permanently delete them with NO recovery:

| Directory | Contents | Recovery Time |
|-----------|----------|---------------|
| `external-sources/*/sgf/` | Crawled puzzles (52k+ files) | Hours (re-crawl) |
| `external-sources/*/logs/` | Crawl history | Lost forever |
| `.pm-runtime/` | Pipeline state | Re-run pipeline |
| `tools/*/output/` | Tool outputs | Re-run tool |

### 5.3 Per-Phase Branch Workflow

Each phase follows this exact sequence:

```bash
# ─── STEP 1: Pre-flight safety check ───
# Check for untracked files outside your scope
git status --porcelain | grep "^??"
# If files exist in external-sources/, .pm-runtime/, tools/*/output/ → DO NOT TOUCH THEM

# ─── STEP 2: Create feature branch ───
git checkout -b perf/phase{N}-{description}
# Example: git checkout -b perf/phase1-mandatory-fields-rebuild

# ─── STEP 3: Make changes, run tests ───
# ... edit files ...
pytest -m "not (cli or slow)"    # Quick validation after each sub-step

# ─── STEP 4: Stage ONLY your files (explicit paths) ───
# NEVER use `git add .` or `git add -A`
git add backend/puzzle_manager/models/publish_log.py
git add backend/puzzle_manager/inventory/rebuild.py
git add backend/puzzle_manager/stages/publish.py
git add backend/puzzle_manager/tests/integration/test_inventory_rebuild.py
# ... etc, one file at a time or space-separated

# ─── STEP 5: Verify staged files are ONLY yours ───
git diff --cached --name-only
# If you see unexpected files: git reset HEAD <file>

# ─── STEP 6: Commit with descriptive message ───
git commit -m "perf(phase1): mandatory publish log fields, rebuild uses log metadata

- Make quality, level, trace_id mandatory in PublishLogEntry
- Delete _extract_tags_from_sgf() — rebuild uses entry.tags directly
- Batch ghost-check with upfront set[str]
- Fix duplicate-skipping drift bug in publish inventory update
- Remove reconcile-on-every-publish
- Delete TestExtractTagsFromSgf, update publish/rebuild tests
- ~80 lines removed"

# ─── STEP 7: Merge to main ───
git checkout main
git merge --no-ff perf/phase{N}-{description} -m "Merge perf/phase{N}-{description}"

# ─── STEP 8: Delete feature branch ───
git branch -d perf/phase{N}-{description}

# ─── STEP 9: Post-merge verification ───
pytest -m "not (cli or slow)"    # Verify tests pass on main
```

### 5.4 If You Need to Switch Branches with Uncommitted Work

**DO NOT use `git stash`.** Instead:

1. **Ask the user** how to proceed
2. Or commit your changes to a WIP branch first:
   ```bash
   git checkout -b wip/phase{N}-partial
   git add <your-files-only>
   git commit -m "wip: partial phase {N} progress"
   ```

### 5.5 Multi-Phase Commit Sequence

Phases MUST be committed in order (1 → 2 → 3 → 4 → 5 → 6). Each phase builds on the previous:

| Phase | Branch Name | Depends On |
|-------|-------------|------------|
| 1 | `perf/phase1-mandatory-fields-rebuild` | None |
| 2 | `perf/phase2-reconcile-speedup` | Phase 1 |
| 3 | `perf/phase3-periodic-reconcile` | Phase 1 |
| 4 | `perf/phase4-trace-search` | None (independent) |
| 5 | `perf/phase5-rollback-legacy-cleanup` | Phase 1 |
| 6 | `perf/phase6-docs-benchmarks` | All previous phases |

Phases 2, 3, 4, 5 can be done in any order after Phase 1. Phase 6 must be last.

### 5.6 Commit Message Convention

```
perf(phase{N}): short description

- Bullet 1: what changed
- Bullet 2: what was deleted
- Bullet 3: test impact
- ~{N} lines removed/added
```

---

## 6. Files Affected (Complete Inventory)

### Modified Files

| File | Phase | Changes |
|------|-------|---------|
| `backend/puzzle_manager/models/publish_log.py` | 1 | Mandatory fields, remove conditionals |
| `backend/puzzle_manager/inventory/rebuild.py` | 1 | Delete SGF parsing, use publish log |
| `backend/puzzle_manager/stages/publish.py` | 1, 3 | Remove reconcile, add periodic trigger |
| `backend/puzzle_manager/core/sgf_parser.py` | 2 | Add `parse_root_properties_only()` |
| `backend/puzzle_manager/inventory/reconcile.py` | 2 | Replace regex with parser, add threading |
| `backend/puzzle_manager/inventory/models.py` | 3 | Add `runs_since_last_reconcile` |
| `backend/puzzle_manager/models/config.py` | 3 | Add `reconcile_interval` |
| `backend/puzzle_manager/trace_registry.py` | 4 | Pre-filter, write-time indexes |
| `backend/puzzle_manager/rollback.py` | 5 | Delete legacy, use batch method |
| `backend/puzzle_manager/core/pagination_writer.py` | 5 | Delete legacy, add batch method, delta distributions |
| `backend/puzzle_manager/daily/_helpers.py` | 5 | Delete legacy branches |
| `backend/puzzle_manager/daily/by_tag.py` | 5 | Delete legacy slug check |
| `backend/puzzle_manager/daily/standard.py` | 5 | Delete legacy slug branches |
| `backend/puzzle_manager/daily/timed.py` | 5 | Delete legacy slug branches |
| `backend/puzzle_manager/config/loader.py` | 5 | Delete deprecated methods |
| `backend/puzzle_manager/models/trace.py` | 5 | Delete backward compat |

### Modified Test Files

| File | Phase | Changes |
|------|-------|---------|
| `tests/integration/test_inventory_rebuild.py` | 1 | Delete `TestExtractTagsFromSgf`, update rebuild tests |
| `tests/integration/test_inventory_publish.py` | 1, 3 | Update for incremental update, add periodic test |
| `tests/integration/test_inventory_integration.py` | 1 | Update rollback-rebuild consistency |
| `tests/integration/test_inventory_cli.py` | 3 | Add periodic reconcile trigger test |
| `tests/unit/test_pagination_rollback.py` | 5 | Add batch method + delta distribution tests |
| Various daily tests | 5 | Remove legacy format test cases |

### New Files

| File | Phase | Purpose |
|------|-------|---------|
| `docs/architecture/backend/inventory-operations.md` | 6 | Architecture: rebuild, reconcile, rollback design |
| `tests/integration/test_performance_benchmarks.py` | 6 | Scale benchmarks (marked `@pytest.mark.slow`) |

### New Test Cases

| Test | Phase | Verifies |
|------|-------|----------|
| `test_rebuild_uses_entry_tags` | 1 | Rebuild reads tags from publish log, not SGF |
| `test_publish_duplicate_no_double_count` | 1 | Duplicate skipping doesn't inflate inventory |
| `test_publish_incremental_no_reconcile` | 1 | Publish does not call reconcile_inventory |
| `test_parse_root_properties_only` | 2 | Lightweight parser extracts root properties |
| `test_parse_root_stops_at_moves` | 2 | Parser does not traverse solution tree |
| `test_periodic_reconcile_triggers` | 3 | Counter reaches threshold → reconcile runs |
| `test_periodic_reconcile_disabled` | 3 | interval=0 → never triggers |
| `test_explicit_reconcile_resets_counter` | 3 | `--reconcile` resets runs_since counter |
| `test_trace_search_with_index` | 4 | Index-based lookup returns correct results |
| `test_trace_search_without_index` | 4 | Missing index falls back to full scan |
| `test_rebuild_indexes` | 4 | Recovery method produces correct indexes |
| `test_remove_puzzles_batch` | 5 | Single state save for batch removal |
| `test_delta_distribution_matches_full` | 5 | Delta decrement matches full recompute |
| `test_benchmark_rebuild_{1k,5k,10k}` | 6 | Rebuild performance at scale |
| `test_benchmark_reconcile_{1k,5k,10k}` | 6 | Reconcile performance at scale |

---

## 7. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Incremental inventory drifts after drift-bug fix | Low | Medium | Periodic reconcile safety net (Phase 3); explicit `--reconcile` always available |
| `parse_root_properties_only()` misses edge-case SGF | Low | Low | Comprehensive tests; reconcile is not on critical publish path |
| Trace index files grow large at 500k | Low | Low | ~25MB JSON file; loads in <500ms. Can shard if needed at 1M+ |
| Rollback delta distributions produce wrong counts | Low | Medium | Test: compare delta vs full recompute; reconcile corrects if needed |
| ThreadPoolExecutor contention on slow disks | Low | Low | Configurable `max_workers`; single-threaded fallback if needed |

---

## 8. Non-Goals (Explicitly Excluded)

| Item | Reason |
|------|--------|
| SQLite for indexing | Violates file-based constraint |
| Page-targeted rollback removal | Both personas agree: infrequent operation, batch saves capture most win |
| `multiprocessing` for reconcile | GIL doesn't block file I/O; threads suffice; multiprocessing adds IPC complexity |
| Memory-mapped files | No benefit for small sequential reads |
| Bloom filters | YAGNI at 300-500k scale |
| JSONL sharding by hash prefix | Sequential reads are fast; problem is scanning ALL files, not individual reads |
| Backward compatibility with legacy entries | Clean-slate migration; collection is empty |

---

*Last Updated: 2026-02-19*
