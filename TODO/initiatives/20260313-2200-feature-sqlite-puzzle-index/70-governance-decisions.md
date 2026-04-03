# Governance Decisions — SQLite Puzzle Index

**Last Updated**: 2026-03-13
**Initiative**: `20260313-2200-feature-sqlite-puzzle-index`

---

## Gate 1: Charter Review

**Decision**: `approve_with_conditions`
**Status Code**: `GOV-CHARTER-CONDITIONAL`
**Date**: 2026-03-13

### Member Reviews

| review_id | member | domain | vote | supporting_comment |
|-----------|--------|--------|------|--------------------|
| GV-1 | Cho Chikun (9p) | Go domain | approve | Sorted AB/AW canonical hashing is mathematically sound. 5-15% dedup rate realistic. |
| GV-2 | Lee Sedol (9p) | Strategic | approve | Clean break is decisive. FTS5 enables discovery paths shards never could. |
| GV-3 | Shin Jinseo (9p) | Technical | approve | sql.js battle-tested. 1.2 MB is acceptable PWA cost. |
| GV-4 | Ke Jie (9p) | UX/Strategy | approve | 14× size reduction improves mobile. N-dimension search maps to study workflows. |
| GV-5 | Staff Engineer A | Architecture | approve (after RC) | Sound design. Caught daily generator scope gap. Resolved via RC-1. |
| GV-6 | Staff Engineer B | Pipeline | approve (after RC) | Pipeline clean. Daily generator migration ~50 lines. Resolved via RC-1/RC-2. |

### Required Changes (Resolved)

| RC-id | Change | Status |
|-------|--------|--------|
| RC-1 | Add daily challenge generator migration to In-Scope | ✅ Applied to 00-charter.md |
| RC-2 | Acknowledge daily test files in test scope | ✅ Applied to 00-charter.md |
| RC-3 | Update status.json phase tracking | ✅ Applied |

### Handover

| Field | Value |
|-------|-------|
| from_agent | Governance-Panel |
| to_agent | Feature-Planner |
| message | Charter approved. Proceed to options. Daily generator scope gap closed. |
| blocking_items | None (all RCs resolved) |

---

## Gate 2: Options Election

**Decision**: `approve`
**Status Code**: `GOV-OPTIONS-APPROVED`
**Date**: 2026-03-13
**Selected Option**: OPT-1 (Schema-First / Frontend-Led)

### Member Reviews

| review_id | member | domain | vote | supporting_comment |
|-----------|--------|--------|------|--------------------|
| GV-1 | Cho Chikun (9p) | Go domain | approve | OPT-1 allows early validation of sorted AB/AW hashing at small scale. |
| GV-2 | Lee Sedol (9p) | Strategic | approve | OPT-1 is the boldest clean move — visible result immediately. |
| GV-3 | Shin Jinseo (9p) | Technical | approve | Isolates highest-uncertainty integration (sql.js, FTS5) into earliest phase. |
| GV-4 | Ke Jie (9p) | UX/Strategy | approve | Matches user's mental model: frontend first, sample data, then pipeline. |
| GV-5 | Staff Engineer A | Architecture | approve | Best testability profile. Sample DB becomes permanent test fixture. |
| GV-6 | Staff Engineer B | Pipeline | approve | Sample seed is ~50 lines. Pipeline integration follows proven schema. |

### Selection Rationale
Unanimous 6/6. Fastest feedback loop, schema issues caught early, matches user's explicit sequencing preference.

### Must-Hold Constraints
1. Sample DB uses identical production schema — no simplified version.
2. Frontend validates AC3 (<300ms init) and AC4 (FTS5) before backend phase begins.
3. Shard deletion is a distinct isolated task.
4. Daily generator migration included in backend phase per RC-1.

### Handover

| Field | Value |
|-------|-------|
| from_agent | Governance-Panel |
| to_agent | Feature-Planner |
| message | OPT-1 unanimously elected. Proceed to plan + tasks + analysis. |
| blocking_items | None |

---

## Gate 3: Plan Review

**Decision**: `approve_with_conditions`
**Status Code**: `GOV-PLAN-CONDITIONAL`
**Date**: 2026-03-13

### Member Reviews

| review_id | member | domain | vote | supporting_comment |
|-----------|--------|--------|------|--------------------|
| GV-1 | Cho Chikun (9p) | Go domain | approve | Sorted AB/AW canonical hashing sound. SGF files remain as individual files. Schema preserves puzzle_id identity. |
| GV-2 | Lee Sedol (9p) | Strategic | approve | Clean-break approach; FTS5 enables discovery paths shards prevented. 7-step phased sequence gives room to adapt. |
| GV-3 | Shin Jinseo (9p) | Technical | approve | sql.js battle-tested WASM. FTS5 risk identified. Web Worker init standard. <300ms achievable. `attrs TEXT` JSON column good. |
| GV-4 | Ke Jie (9p) | UX/Strategy | approve | 94% size reduction improves mobile. N-dimension queries enable real study workflows. 13-doc overhaul ensures developer onboarding. |
| GV-5 | Staff Engineer A | Architecture | concern → RC-1,RC-2,RC-4 | Architecture sound. SOLID compliance. Three concerns: AC8 gap (RE-6), T4 tools/ architecture violation, stale status.json. |
| GV-6 | Staff Engineer B | Pipeline | concern → RC-3 | Pipeline design clean. T36 needs first-run guardrail when DB-2 doesn't exist. RE-7 low severity. |

### Required Changes (All Applied)

| RC-id | Change | Status |
|-------|--------|--------|
| RC-1 | Scope RE-6 into T10: service worker must cache `.db`/`.wasm` files | ✅ Applied to 40-tasks.md T10 |
| RC-2 | Relocate seed script from `tools/` to `backend/puzzle_manager/scripts/` | ✅ Applied to 40-tasks.md T4 + 20-analysis.md §5 |
| RC-3 | Add first-run guardrail to T36: no DB-2 → skip dedup with INFO log | ✅ Applied to 40-tasks.md T36 |
| RC-4 | Update status.json to reflect actual phase state | ✅ Applied |

### Support Summary

Plan comprehensive and well-structured. 10/10 cross-artifact consistency checks pass. All 9 charter goals map to tasks. All 10 acceptance criteria verifiable. 56-task 7-step phased execution proportional to 41-file change surface. SOLID/DRY/KISS/YAGNI compliance verified. All 6 panel members support approval — 4 conditions resolved via localized text updates.

### Handover

| Field | Value |
|-------|-------|
| from_agent | Governance-Panel |
| to_agent | Plan-Executor |
| message | Plan approved with 4 conditions — all applied. Proceed with Step 1 (T1-T7) execution. |
| required_next_actions | Begin Step 1 execution; submit per-step PRs. |
| artifacts_to_update | 40-tasks.md (mark completed), status.json (track execution) |
| blocking_items | None (all RCs resolved) |

---

## Gate 4: Implementation Review

**Decision**: `change_requested` → `approve` (after RC-1 through RC-4 resolved)
**Status Code**: `GOV-REVIEW-APPROVED`
**Date**: 2026-03-14

### Initial Review (change_requested)

Panel identified 4 required changes:
- RC-1: Rename `useShardFilters` → `usePuzzleFilters` (naming vestige) → ✅ Resolved
- RC-2: Update `docs/architecture/backend/pipeline.md` → ✅ Already clean (only `config_snapshot` — different concept)
- RC-3: Clean stale test comments → ✅ Already resolved by L13b cleanup
- RC-4: Re-verify AC6/AC9 grep with corrected scope → ✅ Verified: 0 query-shard hits

### Member Reviews (Post-Remediation)

| review_id | member | domain | vote | supporting_comment |
|-----------|--------|--------|------|--------------------|
| GV-1 | Cho Chikun (9p) | Go domain | approve | Naming precision restored. usePuzzleFilters accurately describes the hook. |
| GV-2 | Lee Sedol (9p) | Strategic | approve | AC6 now genuinely met. Evidence integrity restored. |
| GV-3 | Shin Jinseo (9p) | Technical | approve | Grep verification corrected. Batch/date sharding out of scope. |
| GV-4 | Ke Jie (9p) | UX/Strategy | approve | Documentation gap closed. |
| GV-5 | Staff Engineer A | Architecture | approve | Renamed hook + updated consumers. Evidence corrected. |
| GV-6 | Staff Engineer B | Pipeline | approve | Test files clean. Validation report updated. |

### Handover

| Field | Value |
|-------|-------|
| from_agent | Governance-Panel |
| to_agent | Plan-Executor |
| message | Implementation approved. All 4 RCs resolved. Proceed to closeout. |
| blocking_items | None |

---

## Gate 5: Post-Closeout Remediation — Incremental Publish Fix

**Decision**: `approve` (after 2 rounds)
**Status Code**: `GOV-REVIEW-APPROVED`
**Date**: 2026-03-14

### Defects Addressed

| defect | severity | fix |
|--------|----------|-----|
| D1: DB-1 not incremental (only current run entries) | P0 | Publish merges DB-2 entries + new entries before building DB-1 |
| D2: DB-2 orphaned rows after re-enrichment | P2 | Added `vacuum-db` CLI command with `vacuum_orphans()` |
| D3: Hash unification (position_hash vs content_hash) | Lv5 | Deferred to future initiative. SZ removal rejected unanimously. |
| D4: Silent duplicate skip (no failure record) | P3 | Dedup now records structured failure + writes to failed_dir |

### User Decisions

| decision | answer |
|----------|--------|
| Q1: Same position, different solution trees = duplicate? | Yes (panel recommendation accepted) |
| Q2: Keep SZ in position hash? | Yes (panel recommendation accepted) |
| Hash unification | Deferred — content_hash for file identity, position_hash for dedup |

### Round 1 — change_requested (6/6 unanimous)

Required changes:
- GRC-1: Add unit tests for `read_all_entries()` → ✅ 3 tests added
- GRC-2: Add unit tests for `delete_entries()` → ✅ 4 tests added
- GRC-3: Add unit tests for `vacuum_orphans()` → ✅ 3 tests added
- GRC-4: Extract shared `sgf_to_puzzle_entry()` utility (DRY) → ✅ Single source of truth in db_models.py
- GRC-5: Fix evidence table typo → ✅ Corrected
- GRC-6: Add integration test for `rebuild_search_db_from_disk()` → ✅ 3 tests added

### Round 2 — approve (6/6 unanimous)

| review_id | member | domain | vote | supporting_comment |
|-----------|--------|--------|------|--------------------|
| GV-1 | Cho Chikun (9p) | Go domain | approve | sgf_to_puzzle_entry centralizes puzzle identity resolution. No risk of inconsistent classification. |
| GV-2 | Lee Sedol (9p) | Strategic | approve | Incremental merge is clean. Edge cases handled gracefully. |
| GV-3 | Shin Jinseo (9p) | Technical | approve | Parameterized SQL, read-only connections, try/finally. No security concerns. |
| GV-4 | Ke Jie (9p) | UX/Strategy | approve | 13 new tests add meaningful, non-redundant coverage. |
| GV-5 | Staff Engineer A | Architecture | approve | DRY extraction clean. Documentation updated across 6 canonical locations. |
| GV-6 | Staff Engineer B | Pipeline | approve | Incremental merge verified. Rebuild integration test validates full loop. |

### Implementation Summary

| metric | value |
|--------|-------|
| Files changed | 15 (7 code + 1 test + 1 integration test + 6 docs) |
| New tests added | 13 (10 unit + 3 integration) |
| Backend tests | 1955 passed, 0 failed |
| Frontend tests | 1262 passed, 0 failed |
| DRY violations resolved | 3 → 1 (sgf_to_puzzle_entry extracted to db_models.py) |

### Key Behaviors Fixed

- Publish source A (1000) then source B (100) → DB-1 has 1100 puzzles
- Rollback removes entries from both DB-1 and DB-2
- Reconcile rebuilds DB-1 from disk via `rebuild_search_db_from_disk()`

---

## Gate 7 — Structural Fixes Plan Approval (2026-03-14)

**Scope**: 4 structural gaps (Issue 1: cache invalidation, Issue 2: atomic writes, Issue 4: determinism, Issue 6: content_type)

**Decision**: `approve_with_conditions`
**Status Code**: `GOV-PLAN-CONDITIONAL`

### Required Conditions (All Resolved)

| rc_id | condition | resolution | status |
|-------|-----------|------------|--------|
| RC-1 | Update generate_db_version signature + all callers to accept content_hashes | db_models.py, db_builder.py updated; rollback/reconcile use None fallback | ✅ resolved |
| RC-2 | db-version.json write must also be atomic | temp-file + os.replace in publish.py, rollback.py, reconcile.py | ✅ resolved |
| RC-3 | Wire ct from YM in both sgf_to_puzzle_entry AND publish.py inline | Both paths read ct via parse_pipeline_meta_extended | ✅ resolved |
| RC-4 | Document rollback/reconcile timestamp deviation | Comments added to rollback.py and reconcile.py | ✅ resolved |
| RC-5 | Update sqlite-index-architecture.md + enrichment.md | Atomic writes, deterministic versioning, content_type status documented | ✅ resolved |

### Implementation Evidence

| metric | value |
|--------|-------|
| Files changed | 9 (6 code + 2 test + 2 docs) |
| New tests added | 7 (3 deterministic version + 3 content_type + 4 checkForUpdates − 3 existing test updates) |
| Backend tests | 1969 passed, 0 failed |
| Frontend service tests | 48 passed, 0 failed |
| Governance conditions | 5/5 resolved |

---

## Gate 7 — Implementation Review Approval (2026-03-14)

**Decision**: `approve`
**Status Code**: `GOV-REVIEW-APPROVED`
**Vote**: 6/6 unanimous

### Member Votes

| GV-id | member | vote | comment |
|-------|--------|------|---------|
| GV-1 | Cho Chikun (9p) | approve | SHA256 of sorted content_hash is mathematically deterministic |
| GV-2 | Lee Sedol (9p) | approve | checkForUpdates() is clean opt-in API with graceful degradation |
| GV-3 | Shin Jinseo (9p) | approve | Atomic os.replace() applied consistently across all 3 write paths |
| GV-4 | Ke Jie (9p) | approve | content_type propagation closes last data-flow gap with safe default |
| GV-5 | Principal Staff Engineer A | approve | All 5 RCs resolved with evidence. No new dependencies. |
| GV-6 | Principal Staff Engineer B | approve | +6 backend, +13 frontend tests. Zero regressions. |

---

## Gate 7 — Closeout Audit Approval (2026-03-14)

**Decision**: `approve`
**Status Code**: `GOV-CLOSEOUT-APPROVED`
**Vote**: 6/6 unanimous

All 7 governance gates passed. 56 tasks completed, 1969 backend + 48 frontend service tests passing. Zero open issues. Initiative formally closed.
- Duplicate detected → file FAILS (not skipped), written to failed_dir with structured error
- `vacuum-db` CLI cleans orphaned DB-2 entries

---

## Gate 6: Post-Closeout Remediation Batch 2 — 13-Gap Structural Fix

**Decision**: `approve_with_conditions` → `approve` (conditions met)
**Status Code**: `GOV-REVIEW-APPROVED`
**Date**: 2026-03-14

### Gaps Evaluated

| gap_id | severity | title | decision |
|--------|----------|-------|----------|
| GAP-1 | HIGH | Multi-tag AND semantics (JOIN duplication) | Fix: GROUP BY + HAVING |
| GAP-2 | HIGH | Dead shard files (shardPageLoader.ts, entryDecoder dead code) | Fix: Delete + prune |
| GAP-3 | HIGH | Init retry (cached rejection) | Fix: Clear initPromise on catch |
| GAP-4 | MEDIUM | DB-2 not cleaned by clear_index_state | Fix: Add to cleanup |
| GAP-5 | MEDIUM | Non-deterministic build (no ORDER BY, unsorted glob) | Fix: ORDER BY + sorted() |
| GAP-6 | LOW | Stale docs (4 files reference shards/snapshots) | Fix: Update terminology |
| GAP-7 | MEDIUM | content_type always defaults to 2 | DEFERRED per RC-1 |
| GAP-8 | MEDIUM | puzzle_count always 0 | Fix: UPDATE in same tx |
| GAP-9 | MEDIUM | sequence_number always NULL | Fix: Build sequence_map |
| GAP-10 | HIGH | FTS5 injection (raw user input to MATCH) | Fix: Sanitize metacharacters |
| GAP-11 | MEDIUM | Batch resolution O(N×batches) | Fix: batch column in DB-2 |
| GAP-12 | LOW | useShardFilters.ts dead code | Fix: Delete |
| GAP-13 | LOW | content_type classification undocumented | Fix: Document in enrichment.md |

### Governance Conditions

| RC-id | Condition | Status |
|-------|-----------|--------|
| RC-1 | DEFER GAP-7 to separate initiative (classification logic is domain) | ✅ Applied |
| RC-2 | GAP-2: also remove decodeEntry, retain only live exports | ✅ Applied |
| RC-3 | GAP-11: add backfill_batch_column() + test_batch_column_round_trip | ✅ 5 tests added |
| RC-4 | GAP-8: UPDATE must be in same transaction as inserts | ✅ Applied |
| RC-5 | reconcile.py + rollback.py must pass batch_hint from DB-2 | ✅ Applied |

### Panel Reviews

| review_id | member | domain | vote | supporting_comment |
|-----------|--------|--------|------|--------------------|
| GV-1 | Cho Chikun (9p) | Go domain | approve | Sequence ordering ensures collection integrity. Deterministic builds critical for puzzle provenance. |
| GV-2 | Lee Sedol (9p) | Strategic | approve | FTS5 sanitization prevents injection. AND semantics critical for combo tag searches. |
| GV-3 | Shin Jinseo (9p) | Technical | approve | GROUP BY + HAVING is correct SQL pattern for set intersection. Batch column avoids O(N×B) at 500K scale. |
| GV-4 | Ke Jie (9p) | UX/Strategy | approve | puzzle_count fix means UI shows real counts. sequence_number enables collection ordering. |
| GV-5 | Staff Engineer A | Architecture | approve | Structural solutions. batch_hint pattern is DI-clean. Dead code removal comprehensive. |
| GV-6 | Staff Engineer B | Pipeline | approve | Deterministic ordering + batch column scale to 500K. backfill migration handles existing DBs. |

### Implementation Evidence

| metric | value |
|--------|-------|
| Gaps fixed | 12 of 13 (1 deferred) |
| Files changed | 16 (9 code + 4 docs + 2 tests + 1 deleted) |
| Files deleted | 2 (shardPageLoader.ts, useShardFilters.ts) |
| New tests (backend) | 8 (5 batch column + 2 puzzle_count + 1 sequence_number) |
| New tests (frontend) | 7 (3 AND semantics + 3 FTS5 + 1 init retry) |
| Backend tests total | 1963 passed, 0 failed |
| Frontend service tests | 35 passed, 0 failed |

### Gate 6 Review Decision

**Decision**: `approve_with_conditions` → `approve` (RC-1 resolved)
**Status Code**: `GOV-REVIEW-APPROVED`

**RC-1** (stale shard refs in numeric-id-scheme.md L95-96) → ✅ Resolved: replaced shard terminology with SQLite/DB terminology. grep `shard` returns 0 hits.
