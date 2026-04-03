# Tasks — SQLite Puzzle Index (OPT-1: Schema-First / Frontend-Led)

**Last Updated**: 2026-03-13
**Initiative**: `20260313-2200-feature-sqlite-puzzle-index`
**Selected Option**: OPT-1

---

## Legend

- `[P]` = parallelizable with prior task at same indent level
- `depends: T<N>` = must complete after listed task(s)
- File paths are relative to repo root unless otherwise noted

---

## Step 1: Schema + Sample DB Seed

| ID | Task | Files | Depends | Acceptance Criteria |
|----|------|-------|---------|---------------------|
| T1 | Create `db_models.py` — dataclasses for `PuzzleEntry`, `CollectionMeta`, `DbVersionInfo` | `core/db_models.py` (new) | — | Typed models match research §5 schema; unit tests pass |
| T2 | Create `db_builder.py` — build DB-1 from PuzzleEntry list + collections | `core/db_builder.py` (new) | T1 | Produces valid .db with all 5 tables + 6 indexes; FTS5 table populated |
| T3 | Create `content_db.py` — build DB-2 with SGF content + canonical position hash | `core/content_db.py` (new) | T1 | Position hash is deterministic (sorted AB/AW → SHA256[:16]); dedup query works |
| T4 | [P] Create `seed_sample_db.py` script — extract ~50 puzzles from real SGF corpus, build sample DB-1 | `backend/puzzle_manager/scripts/seed_sample_db.py` (new) | T2 | Produces `yengo-search-sample.db` for frontend development |
| T5 | Write unit tests for `db_models.py` | `tests/unit/test_db_models.py` (new) | T1 | All field validations pass |
| T6 | [P] Write unit tests for `db_builder.py` | `tests/unit/test_db_builder.py` (new) | T2 | Schema verified, row counts verified, FTS5 populated |
| T7 | [P] Write unit tests for `content_db.py` | `tests/unit/test_content_db.py` (new) | T3 | Position hash determinism, SGF round-trip, dedup detection |

## Step 2: Frontend sql.js Integration

| ID | Task | Files | Depends | Acceptance Criteria |
|----|------|-------|---------|---------------------|
| T8 | Add `sql.js` dependency to `package.json` | `frontend/package.json` | T4 | `npm install` succeeds; WASM file present in node_modules |
| T9 | Configure Vite to serve sql.js WASM file | `frontend/vite.config.ts` | T8 | Dev server serves .wasm correctly; build includes .wasm in dist |
| T10 | Create `sqliteService.ts` — fetch DB, load WASM, expose `query()`; update `sw.ts` to cache `.db` and `.wasm` files with stale-while-revalidate strategy (AC8) | `frontend/src/services/sqliteService.ts` (new), `frontend/src/sw.ts` (modify) | T8 | Init completes, queries return results, error on corrupt DB; service worker caches `.db`/`.wasm` files |
| T11 | Create `puzzleQueryService.ts` — typed query functions | `frontend/src/services/puzzleQueryService.ts` (new) | T10 | All query methods from plan §4 work against sample DB |
| T12 | Create `db-version.json` in collections dir | `yengo-puzzle-collections/db-version.json` (new) | T4 | Contains db_version, puzzle_count, timestamp, schema_version |
| T13 | Write unit tests for `sqliteService.ts` | `frontend/src/services/__tests__/sqliteService.test.ts` (new) | T10 | Mock sql.js: init, query, error paths tested |
| T14 | [P] Write unit tests for `puzzleQueryService.ts` (with real sample DB) | `frontend/src/services/__tests__/puzzleQueryService.test.ts` (new) | T11, T4 | All query methods return expected results |

## Step 3: Frontend Page Updates

| ID | Task | Files | Depends | Acceptance Criteria |
|----|------|-------|---------|---------------------|
| T15 | Update `puzzleLoaders.ts` — replace shard-based `PuzzleSetLoader` with SQL-backed loader | `frontend/src/services/puzzleLoaders.ts` | T11 | Loader returns same domain types; no shard imports |
| T16 | Update `entryDecoder.ts` — replace array-of-arrays decoder with SQL row mapping | `frontend/src/services/entryDecoder.ts` | T11 | Domain type construction matches existing contract |
| T17 | [P] Update `TrainingSelectionPage.tsx` — load levels from DB | `frontend/src/pages/TrainingSelectionPage.tsx` | T15 | Level grid renders with correct puzzle counts |
| T18 | [P] Update `app.tsx` — remove snapshot bootstrap, add SQLite init | `frontend/src/app.tsx` | T10 | App starts with DB init instead of snapshot fetch |
| T19 | Update `FilterBar.tsx` / `FilterDropdown.tsx` — filter counts from SQL | `frontend/src/components/puzzle/FilterBar.tsx`, `FilterDropdown.tsx` | T11 | Filter dropdowns show dynamic counts from DB |
| T20 | Update collection browse/search pages — FTS5 search | relevant page files | T11 | Collection search returns ranked results; partial match works |
| T21 | Delete `snapshotService.ts` | `frontend/src/services/snapshotService.ts` (delete) | T18 | No imports reference deleted file |
| T22 | Delete `shardPageLoader.ts` | `frontend/src/services/shardPageLoader.ts` (delete) | T15 | No imports reference deleted file |
| T23 | Delete or repurpose `queryPlanner.ts` | `frontend/src/services/queryPlanner.ts` (delete or major rewrite) | T11 | DIRECT/MERGE/FALLBACK strategies removed |
| T24 | Repurpose `lib/shards/shard-key.ts` → `lib/dimension-ordering.ts` (if needed) or delete | `frontend/src/lib/shards/shard-key.ts` | T15 | Only kept if dimension ordering logic reused for URL params |
| T25 | [P] Write/update Vitest tests for `puzzleLoaders.ts` | `frontend/src/services/__tests__/puzzleLoaders.test.ts` | T15 | Loader tests use SQL-backed implementation |
| T26 | [P] Write Playwright E2E: Training page loads puzzles from DB | `frontend/tests/e2e/training-sqlite.spec.ts` (new) | T17 | Page renders puzzle grid with real DB |
| T27 | [P] Write Playwright E2E: Collection search with FTS5 | `frontend/tests/e2e/collection-search.spec.ts` (new) | T20 | Search returns ranked results |

## Step 4: Backend Pipeline (DB-1 Publish)

| ID | Task | Files | Depends | Acceptance Criteria |
|----|------|-------|---------|---------------------|
| T28 | Update `stages/publish.py` — call `db_builder.build_search_db()` instead of `ShardWriter` | `backend/puzzle_manager/stages/publish.py` | T2 | Publish stage produces .db file in output dir |
| T29 | Update `stages/protocol.py` — replace shard-related protocols with DB output types | `backend/puzzle_manager/stages/protocol.py` | T1 | Protocol types reference `DbVersionInfo` not shard models |
| T30 | Update `daily/generator.py` — read puzzle data from DB-1 instead of shard files | `backend/puzzle_manager/daily/generator.py` | T2 | Daily challenge generation works with DB-1 as source |
| T31 | [P] Update `pipeline/cleanup.py` — remove shard directory cleanup, add .db cleanup | `backend/puzzle_manager/pipeline/cleanup.py` | T28 | Cleanup removes old .db files, not shard dirs |
| T32 | [P] Update `cli.py` — update any shard-related CLI flags | `backend/puzzle_manager/cli.py` | T28 | CLI commands reflect DB-based output |
| T33 | Write integration test: full pipeline → DB-1 output | `tests/integration/test_publish_db_wiring.py` (new) | T28 | Pipeline produces valid DB-1; replaces `test_publish_snapshot_wiring.py` |
| T34 | [P] Write integration test: daily generator reads from DB | `tests/integration/test_daily_from_db.py` (new) | T30 | Daily challenge JSON generated from DB source |

## Step 5: Backend Pipeline (DB-2 Content/Dedup)

| ID | Task | Files | Depends | Acceptance Criteria |
|----|------|-------|---------|---------------------|
| T35 | Integrate `content_db.py` into publish stage — generate DB-2 alongside DB-1 | `backend/puzzle_manager/stages/publish.py` | T3, T28 | Publish produces both .db files |
| T36 | Add dedup check to ingest stage — query DB-2 for duplicate position; when DB-2 does not exist (first pipeline run), skip dedup gracefully with INFO log | `backend/puzzle_manager/stages/ingest.py` | T3 | Duplicate puzzle skipped with log message; no DB-2 → skip dedup with INFO log |
| T37 | Write integration test: dedup detection across pipeline runs | `tests/integration/test_dedup_detection.py` (new) | T36 | Second import of same puzzle is rejected |

## Step 6: Shard Decommission

| ID | Task | Files | Depends | Acceptance Criteria |
|----|------|-------|---------|---------------------|
| T38 | Delete `core/shard_writer.py` | `backend/puzzle_manager/core/shard_writer.py` (delete) | T28 | No imports reference deleted file |
| T39 | [P] Delete `core/shard_models.py` | `backend/puzzle_manager/core/shard_models.py` (delete) | T29 | No imports reference deleted file |
| T40 | [P] Delete `core/snapshot_builder.py` | `backend/puzzle_manager/core/snapshot_builder.py` (delete) | T28 | No imports reference deleted file |
| T41 | Repurpose or delete `core/shard_key.py` → `core/dimension_key.py` | `backend/puzzle_manager/core/shard_key.py` | T28 | Only kept if dimension logic reused; otherwise deleted |
| T42 | Delete shard-related test files (6 files) | `tests/unit/test_shard_writer.py`, `test_shard_models.py`, `test_shard_labels.py`, `test_shard_writer_n_assignment.py`; `tests/integration/test_snapshot_builder.py`, `test_publish_snapshot_wiring.py` | T33, T38-T40 | No orphan test files; all remaining tests pass |
| T43 | Delete frontend shard infrastructure | `frontend/src/lib/shards/` directory (if empty) | T21-T24 | No shard-related code in frontend |
| T44 | Delete snapshot data from `yengo-puzzle-collections/` | `snapshots/` dir, `active-snapshot.json` | T28 | Replaced by `.db` files + `db-version.json` |
| T45 | Add `*.db` to `.gitignore` (or only DB-2, and track DB-1 if desired) | `.gitignore` | T44 | DB files handled correctly by git |
| T46 | Run full grepp verification: zero "shard" / "snapshot" in production code | — | T38-T44 | `grep -r "shard\|snapshot" --include="*.py" --include="*.ts" --include="*.tsx"` returns only docs/tests/config |

## Step 7: Documentation + Holy Laws

| ID | Task | Files | Depends | Acceptance Criteria |
|----|------|-------|---------|---------------------|
| T47 | Rewrite `CLAUDE.md` — replace Snapshot-Centric section → SQLite architecture | `CLAUDE.md` | T46 | No shard references; SQLite DB-1/DB-2 documented |
| T48 | [P] Rewrite `frontend/CLAUDE.md` — data loading section | `frontend/CLAUDE.md` | T46 | sql.js bootstrap sequence documented |
| T49 | [P] Rewrite `.github/copilot-instructions.md` — Snapshot-Centric section | `.github/copilot-instructions.md` | T46 | Updated for AI agents |
| T50 | [P] Rename + rewrite `docs/concepts/snapshot-shard-terminology.md` → `sqlite-index-architecture.md` | `docs/concepts/` | T46 | New canonical concept doc |
| T51 | [P] Update `docs/reference/view-index-schema.md` with SQLite schema | `docs/reference/view-index-schema.md` | T46 | Tables + columns documented |
| T52 | [P] Update `docs/architecture/system-overview.md` — data flow diagram | `docs/architecture/system-overview.md` | T46 | Reflects DB-based flow |
| T53 | [P] Update `docs/architecture/snapshot-deployment-topology.md` | `docs/architecture/` | T46 | Renamed to DB deployment |
| T54 | [P] Update `docs/how-to/backend/rollback.md` | `docs/how-to/backend/rollback.md` | T46 | DB rollback procedure |
| T55 | [P] Update remaining docs (D9-D13 from plan) | various | T46 | All cross-references updated |
| T56 | Update `backend/CLAUDE.md` | `backend/CLAUDE.md` | T46 | Backend guidance reflects DB pipeline |

---

## Task Summary

| Step | Task Count | Parallel Tasks |
|------|-----------|----------------|
| Step 1: Schema + Seed | T1-T7 (7) | T4∥T5∥T6∥T7 |
| Step 2: Frontend sql.js | T8-T14 (7) | T13∥T14 |
| Step 3: Frontend Pages | T15-T27 (13) | T17∥T18, T21-T24∥, T25∥T26∥T27 |
| Step 4: Backend DB-1 | T28-T34 (7) | T31∥T32, T33∥T34 |
| Step 5: Backend DB-2 | T35-T37 (3) | — |
| Step 6: Decommission | T38-T46 (9) | T38∥T39∥T40, T47-T55∥ |
| Step 7: Docs | T47-T56 (10) | All [P] |
| **Total** | **56 tasks** | |

---

## Critical Path

```
T1 → T2 → T4 → T8 → T10 → T11 → T15 → T28 → T38 → T46 → T47
                                    ↓
                                   T30 (daily generator — catches RC-1 risk)
```

---

> **See also**:
> - [Plan](./30-plan.md) — Architecture, risks, contracts
> - [Charter](./00-charter.md) — Acceptance criteria
> - [Research](../20260313-research-sqlite-puzzle-index/15-research.md) — Full SQL schema
