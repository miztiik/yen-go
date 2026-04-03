# Execution Log — SQLite Puzzle Index

**Initiative**: `20260313-2200-feature-sqlite-puzzle-index`
**Started**: 2026-03-13

---

## Parallel Lane Plan

| lane_id | task_ids | scope_files | dependencies | status |
|---------|----------|-------------|--------------|--------|
| L1 | T1, T5 | core/db_models.py, tests/unit/test_db_models.py | None | not_started |
| L2 | T2, T6 | core/db_builder.py, tests/unit/test_db_builder.py | L1 | not_started |
| L3 | T3, T7 | core/content_db.py, tests/unit/test_content_db.py | L1 | not_started |
| L4 | T4, T12 | scripts/seed_sample_db.py, db-version.json | L2 | not_started |
| L5 | T8, T9, T10, T13 | package.json, vite.config.ts, sqliteService.ts, sw.ts, tests | L4 | not_started |
| L6 | T11, T14 | puzzleQueryService.ts, tests | L5 | not_started |
| L7 | T28, T29, T33 | stages/publish.py, stages/protocol.py, test_publish_db_wiring.py | L2 | not_started |
| L8 | T30, T31, T32, T34 | daily/generator.py, pipeline/cleanup.py, cli.py, test_daily_from_db.py | L7 | not_started |
| L9 | T15, T16, T25 | puzzleLoaders.ts, entryDecoder.ts, tests | L6 | not_started |
| L10 | T17, T18, T19, T20 | TrainingSelectionPage, app.tsx, FilterBar, collection pages | L9 | not_started |
| L11 | T35, T36, T37 | stages/publish.py (DB-2), stages/ingest.py, test_dedup | L7, L3 | not_started |
| L12 | T21-T24, T43 | Delete shard frontend files | L10 | not_started |
| L13 | T38-T42, T44, T45, T46 | Delete shard backend files, snapshot data, .gitignore | L11, L12 | not_started |
| L14 | T47-T56 | All documentation files | L13 | not_started |
| L15 | T26, T27 | Playwright E2E tests | L10 | not_started |

---

## Execution Progress

### Batch 1: Backend Schema + Builders (T1-T7)

| EX-1 | L1 | T1, T5 | db_models.py + tests | ✅ merged | 6/6 tests pass |
| EX-2 | L2 | T2, T6 | db_builder.py + tests | ✅ merged | 11/11 tests pass |
| EX-3 | L3 | T3, T7 | content_db.py + tests | ✅ merged | 12/12 tests pass |
| EX-4 | L4 | T4, T12 | seed_sample_db.py + db-version.json | ✅ merged | 50 puzzles seeded |

### Batch 2: Frontend sql.js + Backend Pipeline

| EX-5 | L5 | T8, T9, T10, T13 | sql.js dep + vite config + sqliteService + sw.ts | ✅ merged | 8/8 vitest pass |
| EX-6 | L6 | T11, T14 | puzzleQueryService.ts + tests | ✅ merged | 20/20 vitest pass |
| EX-7 | L7 | T28, T29, T33 | publish.py + protocol.py + integration test | ✅ merged | 2094 backend pass |
| EX-8 | L8 | T30, T31, T32, T34 | generator.py + cleanup.py + cli.py + daily test | ✅ merged | 2107 backend pass |
| EX-9 | L11 | T35, T36, T37 | DB-2 in publish + dedup in ingest + test | ✅ merged | 2098 backend pass |

### Batch 3: Frontend Pages

| EX-10 | L9 | T15, T16, T25 | puzzleLoaders.ts + entryDecoder.ts + tests | ✅ merged | 9/9 vitest pass |
| EX-11 | L10 | T17, T18, T19, T20 | TrainingSelectionPage + app.tsx + FilterBar + collections | ✅ merged | 14/14 vitest pass |

### Batch 4: Shard Decommission

| EX-12 | L12 | T23, T24, T43 | Delete queryPlanner + shard-key + count-tier + shards dir | ✅ merged | tsc clean |
| EX-13 | L12b | T21, T22 | Migrate consumers + delete snapshotService + shardPageLoader | ✅ merged | 79 vitest files pass |
| EX-14 | L13a | T38-T42, T44, T45 | Delete 14 backend shard files + .gitignore update | ✅ merged | 1947 backend pass |
| EX-15 | L13b | T46 | Clean remaining shard/snapshot references | ✅ merged | 1942 backend pass |

### Batch 5: Documentation

| EX-16 | L14 | T47-T56 | CLAUDE.md + copilot-instructions + frontend/CLAUDE.md + docs/* | ✅ merged | grep clean |

### Final Validation

| VAL-1 | Backend regression | `pytest -m "not (cli or slow)"` | 1942 passed, 0 failed | ✅ |
| VAL-2 | Frontend regression | `vitest run` | 78 files, 1262 tests, 0 failed | ✅ |
| VAL-3 | AC6 grep | Zero "shard" in production code | 0 hits | ✅ |
| VAL-4 | AC9 grep | Zero query-snapshot in production code | 0 hits (only config_snapshot) | ✅ |

---

## Post-Closeout Remediation Batch 2 — 13-Gap Structural Fix

**Date**: 2026-03-14
**Trigger**: User-identified 13 gaps post-closeout
**Governance**: Gate 6 — approved with conditions (6/6 unanimous)

### Gap Execution Summary

| EX-id | Gap | Severity | Files Changed | Description | Status |
|-------|-----|----------|---------------|-------------|--------|
| EX-17 | GAP-1 | HIGH | puzzleQueryService.ts, puzzleQueryService.test.ts | AND semantics: GROUP BY + HAVING COUNT(DISTINCT) for multi-tag filter | ✅ |
| EX-18 | GAP-10 | HIGH | puzzleQueryService.ts, puzzleQueryService.test.ts | FTS5 metacharacter sanitization: strip `["\-*()^~]` before MATCH | ✅ |
| EX-19 | GAP-3 | HIGH | sqliteService.ts, sqliteService.test.ts | Init retry: clear initPromise on rejection | ✅ |
| EX-20 | GAP-2 | HIGH | shardPageLoader.ts (DEL), entryDecoder.ts, entry-decoder.test.ts | Shard decommission: deleted shardPageLoader.ts, removed dead code from entryDecoder.ts | ✅ |
| EX-21 | GAP-12 | LOW | useShardFilters.ts (DEL) | Dead code: deleted useShardFilters.ts (zero importers) | ✅ |
| EX-22 | GAP-4 | MEDIUM | cleanup.py | DB-2 cleanup: added yengo-content.db deletion to clear_index_state | ✅ |
| EX-23 | GAP-5 | MEDIUM | content_db.py, publish.py | Deterministic builds: ORDER BY content_hash, sorted() glob, sorted all_entries | ✅ |
| EX-24 | GAP-8 | MEDIUM | db_builder.py, test_db_builder.py | puzzle_count: UPDATE collections in same transaction (RC-4 compliant) | ✅ |
| EX-25 | GAP-9 | MEDIUM | publish.py, rollback.py, reconcile.py, db_builder.py | sequence_number: build deterministic sequence_map, pass to all rebuild paths | ✅ |
| EX-26 | GAP-11 | MEDIUM | content_db.py, db_models.py, publish.py, rollback.py, reconcile.py, test_content_db.py | Batch column in DB-2: schema migration, backfill, batch_hint in all paths (RC-3, RC-5) | ✅ |
| EX-27 | GAP-6 | LOW | numeric-id-scheme.md, stages.md, rush-mode.md, view-index-pagination.md | Stale docs: replaced shard/snapshot references with SQLite terminology | ✅ |
| EX-28 | GAP-13 | LOW | enrichment.md | Content-type classification: documented current default + planned signals | ✅ |
| EX-29 | GAP-7 | MEDIUM | — | DEFERRED per governance RC-1: content_type classification to separate initiative | ⏸️ |

### Batch 3 — Structural Fixes (Gate 7)

| EX-id | Issue | Severity | Files Changed | Description | Status |
|-------|-------|----------|---------------|-------------|--------|
| EX-30 | Issue 4 | HIGH | db_models.py, db_builder.py, test_db_models.py | Deterministic versioning: SHA256 of sorted content_hashes → hex suffix. Removed secrets.token_hex. | ✅ |
| EX-31 | Issue 2 | HIGH | publish.py, rollback.py, reconcile.py | Atomic file writes: temp-file + os.replace() for yengo-search.db and db-version.json in all 3 paths | ✅ |
| EX-32 | Issue 6 | MEDIUM | db_models.py, publish.py, test_db_models.py | content_type propagation: read ct from YM via parse_pipeline_meta_extended in sgf_to_puzzle_entry and publish inline | ✅ |
| EX-33 | Issue 1 | MEDIUM | sqliteService.ts, sqliteService.test.ts | Cache invalidation: checkForUpdates() API, localStorage version storage on init, UpdateCheckResult interface | ✅ |
| EX-34 | RC-4 | LOW | rollback.py, reconcile.py | Timestamp deviation comment: rollback/reconcile use datetime.now() by design | ✅ |
| EX-35 | RC-5 | LOW | sqlite-index-architecture.md, enrichment.md | Docs updated: atomic writes, deterministic versioning, update checking, content_type classification status | ✅ |

### New Tests Added

| test_id | File | Test | Gap |
|---------|------|------|-----|
| NT-1 | test_content_db.py | TestBatchColumn::test_batch_stored_and_retrieved | GAP-11 |
| NT-2 | test_content_db.py | TestBatchColumn::test_batch_defaults_to_none | GAP-11 |
| NT-3 | test_content_db.py | TestBatchColumn::test_backfill_from_filesystem | GAP-11 |
| NT-4 | test_content_db.py | TestBatchColumn::test_backfill_skips_missing_files | GAP-11 |
| NT-5 | test_content_db.py | TestBatchColumn::test_schema_migration_adds_batch_column | GAP-11 |
| NT-6 | test_db_builder.py | TestPuzzleCountComputed::test_puzzle_count_nonzero | GAP-8 |
| NT-7 | test_db_builder.py | TestPuzzleCountComputed::test_puzzle_count_zero_when_no_members | GAP-8 |
| NT-8 | test_db_builder.py | TestSequenceNumberPopulated::test_multiple_entries_ordered | GAP-9 |
| NT-9 | puzzleQueryService.test.ts | AND semantics — multi-tag GROUP BY + HAVING | GAP-1 |
| NT-10 | puzzleQueryService.test.ts | AND semantics — single tag | GAP-1 |
| NT-11 | puzzleQueryService.test.ts | AND semantics — no tags | GAP-1 |
| NT-12 | puzzleQueryService.test.ts | FTS5 metacharacter stripping | GAP-10 |
| NT-13 | puzzleQueryService.test.ts | FTS5 special chars stripping | GAP-10 |
| NT-14 | puzzleQueryService.test.ts | FTS5 all-special input → empty | GAP-10 |
| NT-15 | sqliteService.test.ts | init retry after failure | GAP-3 |

### Validation Results

| VAL-id | Check | Command | Result | Status |
|--------|-------|---------|--------|--------|
| VAL-5 | Backend regression | `pytest backend/ -m "not (cli or slow)"` | 1963 passed, 0 failed | ✅ |
| VAL-6 | Frontend service tests | `vitest run` (2 service test files) | 35 passed, 0 failed | ✅ |
| VAL-7 | Dead code grep | Zero shardPageLoader/useShardFilters refs | 0 hits | ✅ |
| VAL-8 | TypeScript strict | `tsc --noEmit` on changed files | 0 new errors | ✅ |

