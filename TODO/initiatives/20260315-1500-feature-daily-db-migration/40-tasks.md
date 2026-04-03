# Tasks — Daily Puzzle DB Migration (OPT-3)

**Initiative**: `20260315-1500-feature-daily-db-migration`
**Selected Option**: OPT-3 — Separate Daily Insert Module
**Last Updated**: 2026-03-15

## Dependency Order

```
T1 (schema) ──┐
              ├── T3 (db_writer) ── T4 (generator refactor) ── T5 (publish hook)
T2 (config) ──┘                                                     │
                                                              T6 (CLI refactor)
                                                                     │
                              T7 (error handling) ─── T8 (backend tests)
                                                                     │
T9 (frontend query) ── T10 (frontend service) ── T11 (frontend tests)
                                                                     │
                    T12 (legacy delete) ── T13 (CI workflow) ── T14 (docs)
```

## Task Checklist

### Phase 1: Backend Schema & Core Module

- [ ] **T1** — Add daily tables to `_SCHEMA_SQL` in `core/db_builder.py`
  - Add `daily_schedule` and `daily_puzzles` CREATE TABLE statements
  - Add indexes: `idx_daily_puzzles_date`, `idx_daily_puzzles_hash`
  - Scope: `backend/puzzle_manager/core/db_builder.py`
  - Verify: `build_search_db()` creates DB with the 2 new tables

- [ ] **T2** — Add `rolling_window_days` to `DailyConfig`, remove `OutputConfig.daily_path`
  - Add `rolling_window_days: int = Field(90, ge=7, le=365)`
  - Remove `daily_path` from `OutputConfig` (obsolete)
  - Scope: `backend/puzzle_manager/models/config.py`
  - Verify: `DailyConfig()` has `rolling_window_days=90`

- [P] T1 and T2 are **parallel** — no dependency between them.

- [ ] **T3** — Create `daily/db_writer.py` module
  - `inject_daily_schedule(db_path: Path, challenges: list[DailyChallenge]) -> int` — writes daily_schedule + daily_puzzles rows via INSERT OR REPLACE. Returns row count. Raises `DailyGenerationError` on DB errors.
  - `prune_daily_window(db_path: Path, rolling_window_days: int) -> int` — deletes daily_schedule + daily_puzzles rows WHERE date < (today - rolling_window_days) AND date < today. Current date and future dates are NEVER pruned (C6 constraint). Returns deleted count.
  - Define section constants: `SECTION_STANDARD`, `SECTION_TIMED_BLITZ`, `SECTION_TIMED_SPRINT`, `SECTION_TIMED_ENDURANCE`, `SECTION_BY_TAG`
  - Scope: `backend/puzzle_manager/daily/db_writer.py` (NEW)
  - Must-hold: MH-1 (pure module, no generator imports), MH-4 (LOUD FAILURE), MH-5 (prune separate function)
  - Depends on: T1 (schema exists)

- [ ] **T4** — Refactor `DailyGenerator` to use `db_writer`
  - Replace `_write_challenge(challenge, path)` with call to `inject_daily_schedule(db_path, [challenge])`
  - Remove `_get_output_path()` method (no more JSON paths)
  - Remove `generate_daily_master_index()` method (no more JSON index)
  - Remove `_build_daily_index_entry()` method
  - Update `generate()` and `_generate_for_date()` to write to DB
  - Scope: `backend/puzzle_manager/daily/generator.py`
  - Depends on: T3

- [ ] **T5** — Add daily injection as publish stage post-step + rollback/reconcile post-steps
  - After `build_search_db()` completes in `PublishStage.run()`, call `inject_daily_schedule()`
  - After `RollbackManager._rebuild_search_db()`, call `inject_daily_schedule()` (WARNING-level on failure — do not abort rollback)
  - After `rebuild_search_db_from_disk()` in inventory/reconcile, call `inject_daily_schedule()` (WARNING-level on failure)
  - Generate rolling window of daily schedules from the newly-built puzzle pool
  - Scope: `backend/puzzle_manager/stages/publish.py`, `backend/puzzle_manager/rollback.py`, `backend/puzzle_manager/inventory/reconcile.py`
  - Must-hold: MH-3 (publish post-step calls db_writer)
  - Depends on: T3, T4

### Phase 2: CLI & Error Handling

- [ ] **T6** — Refactor `cmd_daily()` CLI command
  - Constructor: `DailyGenerator(db_path=...)` instead of `DailyGenerator(output_dir=...)`
  - Remove master index regeneration logic
  - Add `--rolling-window` CLI flag (overrides config default)
  - Call `prune_daily_window()` after generation
  - Scope: `backend/puzzle_manager/cli.py`
  - Depends on: T4

- [ ] **T7** — Implement LOUD FAILURE error handling
  - `generator.py` L100: `except Exception` → `logger.error(exc_info=True)` + collect in failures list
  - `generator.py` _load_puzzle_pool: missing DB → raise `DailyGenerationError` (not return `[]`)
  - `generator.py` _load_puzzle_pool_from_db: DB error → raise `DailyGenerationError` (not return `[]`)
  - `db_writer.py`: all sqlite3 errors → raise `DailyGenerationError`
  - Return generation result with success/failure counts
  - Scope: `backend/puzzle_manager/daily/generator.py`, `backend/puzzle_manager/daily/db_writer.py`
  - Depends on: T4

- [P] T6 and T7 are **parallel** — independent refactors.

### Phase 3: Backend Tests

- [ ] **T8** — Write new DB-based daily tests, verify existing algorithm tests pass
  - New tests for `db_writer.py`: inject, prune, idempotency, error cases
  - New integration tests: publish → daily tables populated, CLI → daily tables populated
  - Update `test_daily_from_db.py` to verify DB rows instead of JSON files
  - Update `test_daily_output.py` to verify DB format instead of JSON format
  - Keep algorithm tests unchanged (standard.py, timed.py, by_tag.py logic tests)
  - Scope: `backend/puzzle_manager/tests/unit/`, `backend/puzzle_manager/tests/integration/`
  - Depends on: T7

### Phase 4: Frontend Migration

- [ ] **T9** — Create `dailyQueryService.ts`
  - `getDailySchedule(date: string)` → queries `daily_schedule` table
  - `getDailyPuzzles(date: string, section?: string)` → queries `daily_puzzles` JOIN `puzzles`
  - `isDailyAvailable(date: string)` → checks if date exists in `daily_schedule`
  - Uses existing `query()` from `sqliteService.ts`
  - Scope: `frontend/src/services/dailyQueryService.ts` (NEW)
  - Depends on: T1 (schema)

- [ ] **T10** — Update `dailyChallengeService.ts` to use SQL queries
  - Replace `loadDailyIndexRaw()` calls with `getDailySchedule()` / `getDailyPuzzles()`
  - Remove JSON fetch/parse logic
  - Keep: countdown calculation, status tracking, performance calculation (unchanged)
  - Update `NormalizedDailyChallenge` construction to use DB row data
  - Scope: `frontend/src/services/dailyChallengeService.ts`
  - Depends on: T9

- [ ] **T11** — Update frontend tests
  - New tests for `dailyQueryService.ts`: mock `sqliteService.query()`
  - Update `daily-loader.test.ts` → replace with `dailyQueryService.test.ts`
  - **Add E2E rendering test: verify daily page renders puzzle board from SQL-sourced data (AC10) — confirm query → service → component → board rendering pipeline**
  - Update page component tests if data shape changes
  - Keep: progress tests, countdown tests (pure logic, unchanged)
  - Scope: `frontend/tests/unit/`, `frontend/src/services/__tests__/`
  - Depends on: T10

### Phase 5: Legacy Cleanup & Deployment

- [ ] **T12** — Delete legacy daily JSON code
  - Delete: `frontend/src/lib/puzzle/daily-loader.ts`
  - Delete: `frontend/src/utils/dailyPath.ts`
  - Delete: `frontend/tests/unit/daily-loader.test.ts`
  - Delete: `frontend/tests/e2e/daily-load.spec.ts`
  - Delete: `frontend/tests/visual/specs/daily.visual.spec.ts`
  - Remove: `APP_CONSTANTS.paths.dailyBase` from `config/constants.ts`
  - Remove: JSON-related daily types from `frontend/src/types/indexes.ts` (DailyIndex JSON shape)
  - Remove: `generate_daily_master_index()` related tests from backend
  - Remove: `test_daily_posix.py` (JSON path tests)
  - Remove: `OutputConfig.daily_path` references in tests
  - Remove: `DailyPuzzleLoader` from `puzzleLoaders.ts`
  - Scope: Multiple files (see list above)
  - Depends on: T11 (new tests pass first)

- [ ] **T13** — Update CI workflow
  - `.github/workflows/daily-generation.yml`: `git add` targets `yengo-search.db` + `db-version.json` instead of `views/daily/`
  - Update workflow steps: remove JSON validation, update commit message
  - Scope: `.github/workflows/daily-generation.yml`
  - Depends on: T12

- [ ] **T14** — Documentation updates
  - Update `docs/architecture/backend/puzzle-manager.md` — module tree, daily data flow
  - Update `docs/how-to/backend/cli-reference.md` — daily command output
  - Update `docs/concepts/sqlite-index-architecture.md` — new tables
  - Update `backend/puzzle_manager/AGENTS.md` — add db_writer.py
  - Update `frontend/src/AGENTS.md` — daily service layer
  - Update `.github/copilot-instructions.md` — DB-1 schema, daily format
  - Update `CLAUDE.md` — DB-1 schema
  - Update `docs/reference/github-actions.md` — daily workflow
  - Remove all `views/daily/` JSON path references from docs
  - Scope: 8+ documentation files
  - Depends on: T12

- [P] T13 and T14 are **parallel** — independent of each other.

- [ ] **T15** — Update `daily/__init__.py` exports
  - Add `db_writer` exports: `inject_daily_schedule`, `prune_daily_window`
  - Remove any JSON-path-related exports
  - Scope: `backend/puzzle_manager/daily/__init__.py`
  - Depends on: T3

- [P] T15 is **parallel** with T4.

## Summary

| Phase | Tasks | Parallel markers | Est. files changed |
|---|---|---|---|
| 1: Schema & Core | T1, T2, T3, T4, T5 | T1∥T2, T15∥T4 | 5 |
| 2: CLI & Errors | T6, T7 | T6∥T7 | 3 |
| 3: Backend Tests | T8 | — | 6 |
| 4: Frontend | T9, T10, T11 | — | 5 |
| 5: Cleanup & Deploy | T12, T13, T14 | T13∥T14 | 15+ |
| **Total** | **15 tasks** | **4 parallel pairs** | **~35 files** |
