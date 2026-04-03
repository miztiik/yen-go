# Research Brief: Daily Puzzle DB Migration

**Initiative**: `20260315-1500-feature-daily-db-migration`
**Last Updated**: 2026-03-15
**Researcher**: Feature-Researcher agent

---

## 1. Research Question & Boundaries

Migrate daily challenge storage from per-day JSON files (`views/daily/{YYYY}/{MM}/{YYYY-MM-DD}-001.json`) into the existing `yengo-search.db` (DB-1) as new tables, remove all JSON-based daily code, and enable incremental inserts without full DB rebuild.

**In scope**: Schema integration, publish pipeline hooks, frontend consumer inventory, incremental insert mechanism, error handling, tests, CI, config model, naming conflicts.

**Out of scope**: Frontend UI redesign, timed/tag challenge redesign, solver changes.

---

## 2. Findings by Research Question

### R1: Schema Integration — `build_search_db()` mechanism

| ID | Finding | Source |
|----|---------|--------|
| R1-1 | `build_search_db()` creates a **fresh DB every time** — connects to `output_path`, calls `_create_schema(conn)` which runs `conn.executescript(_SCHEMA_SQL)`. No `IF NOT EXISTS` guard. | `backend/puzzle_manager/core/db_builder.py` L74, L164-200 |
| R1-2 | The `_SCHEMA_SQL` string uses bare `CREATE TABLE` (not `CREATE TABLE IF NOT EXISTS`). Running it on an existing DB with tables would fail with "table already exists". | `db_builder.py` L18-72 |
| R1-3 | The publish stage builds to a **temp file** (`*.db.tmp`) then does `os.replace()` atomic swap. The live DB is completely replaced each run. | `stages/publish.py` L554-567 |
| R1-4 | `build_search_db` is called from `PublishStage._build_final_dbs()` which merges existing DB-2 (content DB) entries with new entries, then rebuilds DB-1 from scratch. | `stages/publish.py` L500-580 |
| R1-5 | Adding a `daily_schedule` table to `_SCHEMA_SQL` would cause it to be **created and wiped on every publish run**, since the whole DB is rebuilt from temp. | Implication of R1-1 + R1-3 |

**Conclusion (R1)**: Simply appending daily tables to `_SCHEMA_SQL` will NOT preserve daily data across publish runs. The entire DB-1 is rebuilt from scratch on each `publish` stage execution.

---

### R2: Publish Stage Integration — Pipeline hook points

| ID | Finding | Source |
|----|---------|--------|
| R2-1 | The `daily` command is a **standalone CLI command**, completely separate from the 3-stage pipeline (`ingest → analyze → publish`). It is invoked via `python -m backend.puzzle_manager daily`. | `cli.py` L353-400, L1101-1160 |
| R2-2 | The pipeline coordinator registers only 3 stages: `{"ingest": IngestStage(), "analyze": AnalyzeStage(), "publish": PublishStage()}`. Daily is not a stage. | `pipeline/coordinator.py` L168-172 |
| R2-3 | `cmd_daily()` instantiates `DailyGenerator(output_dir=get_output_dir())` directly, bypassing the coordinator/executor entirely. | `cli.py` L1101-1135 |
| R2-4 | The publish stage docstring explicitly says: _"Note: Daily challenges are generated separately via: `python -m backend.puzzle_manager daily`"_. | `stages/publish.py` L7-8 |
| R2-5 | `StageContext.daily_output_dir` exists as property (`views_dir / "daily"`), but is never referenced by the publish stage itself. | `stages/protocol.py` L121-123 |

**Hook point options**:
- **Option A**: Add daily generation as a sub-step within `PublishStage.run()` after DB rebuild (simplest, but couples daily to publish).
- **Option B**: Register a new `"daily"` stage in the coordinator, executed after publish. Would require `StageRunner` protocol conformance.
- **Option C** (current): Keep `daily` as a separate CLI command but have it write to DB-1 incrementally (requires DB-1 to support incremental updates).

---

### R3: Frontend Daily Consumers — EXHAUSTIVE inventory

| ID | File | Role | Depends On |
|----|------|------|------------|
| R3-1 | `frontend/src/lib/puzzle/daily-loader.ts` | Core data fetcher: fetches JSON from CDN, parses `DailyIndex`, builds `InternalPuzzle[]` | `getDailyPath()`, `safeFetchJson`, `DailyIndex` type |
| R3-2 | `frontend/src/services/dailyChallengeService.ts` | Service layer: wraps `daily-loader`, provides `getTodaysChallenge()`, countdown, status | `daily-loader.ts`, `DailyIndex` types |
| R3-3 | `frontend/src/utils/dailyPath.ts` | Path utilities: `getDailyPath()`, `getDailyUrl()`, `parseDailyPath()`, `isDailyPath()` | Pure utility — constructs `views/daily/...` paths |
| R3-4 | `frontend/src/services/puzzleLoaders.ts` (`DailyPuzzleLoader`) | Class-based loader: fetches daily JSON, extracts standard puzzles | `APP_CONSTANTS.paths.dailyBase`, `DailyPuzzleEntry` |
| R3-5 | `frontend/src/pages/DailyChallengePage.tsx` | Page component: puzzle solving view for daily challenges | `DailyPuzzleLoader`, `dailyChallengeService`, `DailySummary` |
| R3-6 | `frontend/src/pages/DailyBrowsePage.tsx` | Browse page: hero card for today's challenge, mode selection | `dailyChallengeService.getTodaysChallenge()` |
| R3-7 | `frontend/src/pages/HomePageGrid.tsx` | Home page: displays today's challenge card | `dailyChallengeService.getTodaysChallenge()` |
| R3-8 | `frontend/src/app.tsx` | Router: imports `DailyChallengePage`, `DailyBrowsePage`, `DailyChallengeMode` | Page components |
| R3-9 | `frontend/src/components/DailyChallenge/DailySummary.tsx` | Completion summary component | `DailyPerformanceData` model |
| R3-10 | `frontend/src/models/dailyChallenge.ts` | Type definitions: `DailyChallengeMode`, `DailyPerformanceData` | Pure types |
| R3-11 | `frontend/src/models/level.ts` | Level grouping: `DailyChallengeGroup`, `PUZZLE_LEVEL_TO_DAILY_GROUP` | Pure types/constants |
| R3-12 | `frontend/src/models/progress.ts` | Progress types: `DifficultyStats`, streak tracking | `DailyChallengeGroup` |
| R3-13 | `frontend/src/services/progress/progressCalculations.ts` | Progress logic: `getDailyProgress()`, `updateDailyProgress()`, `recordDailyPuzzleCompletion()` | `storageOperations` |
| R3-14 | `frontend/src/services/progress/storageOperations.ts` | Storage: `loadDailyProgress()`, `saveDailyProgress()` | `localStorage`, `DailyProgress` type |
| R3-15 | `frontend/src/services/progress/index.ts` | Re-exports daily progress functions | All progress modules |
| R3-16 | `frontend/src/types/indexes.ts` | Type defs: `DailyIndex`, `DailyPuzzleEntry`, `DailyStandard`, `DailyTimed`, etc. | Pure types |
| R3-17 | `frontend/src/config/constants.ts` | `APP_CONSTANTS.paths.dailyBase` — CDN path for daily JSON | Config |

**Migration impact**: R3-1 through R3-4 are the direct JSON fetch layer and would need to be rewritten to use SQL queries against the in-memory `yengo-search.db`. R3-5 through R3-8 use the service layer and would require minimal changes (swap service implementation). R3-9 through R3-17 are types/models/progress that remain unchanged (they don't fetch JSON).

---

### R4: Incremental Insert Feasibility

| ID | Finding | Source |
|----|---------|--------|
| R4-1 | `build_search_db()` creates a fresh DB each time (no append mode). | `db_builder.py` L164-230 |
| R4-2 | `build_content_db()` (DB-2) uses `CREATE TABLE IF NOT EXISTS` and `INSERT OR REPLACE`, supporting incremental append across runs. | `content_db.py` L16-35, L148 |
| R4-3 | Publish stage merges DB-2 entries with new entries before rebuilding DB-1. Daily rows would be lost in this merge-rebuild cycle. | `stages/publish.py` L500-580 |
| R4-4 | DB-1 is designed as a **read-only distribution artifact** — after building, it runs `VACUUM`, `ANALYZE`, switches to `journal_mode=DELETE`. | `db_builder.py` L222-225 |

**Three approaches evaluated**:

| ID | Approach | Pros | Cons | Fits Codebase? |
|----|----------|------|------|----------------|
| R4-A | Exclude daily tables from drop/recreate | Requires splitting `_SCHEMA_SQL`, conditional schema creation | Complex schema management, fragile | **No** — too invasive |
| R4-B | Re-generate daily rows **after** each DB rebuild | Simple — daily gen appends to rebuilt DB-1 | Daily gen must always run after publish; deterministic if date-seeded | **Yes** — matches existing pattern |
| R4-C | Store daily schedule in a separate `daily.db` | Full isolation from rebuild | Frontend must load 2 DBs; increases complexity | **No** — violates "single DB" architecture |

**Recommendation**: Approach **R4-B** — have `build_search_db()` include daily tables in `_SCHEMA_SQL` (they get created each rebuild). After the publish stage rebuilds DB-1, the daily generator populates the daily tables. The daily CLI command does the same (connects to existing DB-1, inserts daily rows). Both paths use `INSERT OR REPLACE` for idempotency.

**Key insight**: Daily data is *derived from* the puzzle pool in DB-1. It can always be regenerated from DB-1 data. The daily generator already reads from `yengo-search.db` (see `_load_puzzle_pool()` at generator.py L207-215). So re-generating daily rows after each rebuild is logically sound and consistent with how the daily generator already works.

---

### R5: Error Handling — Silent failures in daily code

| ID | Location | Pattern | Severity |
|----|----------|---------|----------|
| R5-1 | `generator.py` L100-101 | `except Exception as e: logger.warning(f"Failed to generate for {current.date()}: {e}")` — catches ALL exceptions in the per-date loop, only warns | **High** — silently skips days |
| R5-2 | `generator.py` L214 | `logger.warning("yengo-search.db not found")` then returns `[]` — no DB = empty pool, no error raised | **Medium** — silently produces nothing |
| R5-3 | `generator.py` L273-274 | `except sqlite3.Error as e: logger.warning(...)` then returns `[]` | **Medium** — DB errors swallowed |
| R5-4 | `generator.py` L324 | `except Exception as e:` in `_build_daily_index_entry` loop | **Low** — single entry skip OK |
| R5-5 | `standard.py` L53, L57 | `except (ValueError, TypeError)` and `except (OSError, json.JSONDecodeError)` — parsing errors | **Low** — defensive parsing |

**Pipeline error pattern (reference)**: The `StageExecutor` at `pipeline/executor.py` L105-115 catches exceptions, logs with `logger.error(... exc_info=True)`, updates state manager with error, and returns `StageResult.failure_result()`. This is the "LOUD FAILURE" pattern — errors are:
1. Logged at ERROR level with stack trace
2. Recorded in state
3. Returned as failure result
4. Bubbled up to coordinator

**Recommendation**: Daily generation should follow the same `StageResult`-compatible pattern when integrated into the pipeline. At minimum, R5-1 should be changed from `logger.warning` to `logger.error` with `exc_info=True`, and the result should include the failure count.

---

### R6: Existing Tests — Complete inventory

**Backend daily tests** (7 files):

| ID | File | Test Classes/Functions | Approx Tests |
|----|------|----------------------|--------------|
| R6-1 | `tests/unit/test_daily_generator.py` | `TestDailyGeneratorDateHandling`, `TestDailyConfigValidation`, `TestCompactFormatDailyGeneration` | ~15 |
| R6-2 | `tests/unit/test_daily_quality_weighting.py` | `TestStandardDailyQualityIntegration` + others | ~15 |
| R6-3 | `tests/integration/test_daily.py` | `TestDailyGenerator`, `TestDailyChallenge` | ~5 |
| R6-4 | `tests/integration/test_daily_from_db.py` | `TestDailyFromDb` | ~5 |
| R6-5 | `tests/integration/test_daily_master_index.py` | `TestDailyMasterIndexGeneration` | ~5 |
| R6-6 | `tests/integration/test_daily_output.py` | `TestDailyOutputFormat`, `TestDailyOutputPath`, `TestDailyJsonSchema`, `TestDailyOutputContent`, `TestDailyOutputIdempotency` | ~15 |
| R6-7 | `tests/integration/test_daily_posix.py` | `TestDailyPosixPaths` | ~3 |
| R6-8 | `tests/unit/test_paths.py` | `test_daily_dir_under_views` | 1 |
| R6-9 | `tests/unit/test_posix_path.py` | `test_daily_puzzle_ref_scenario` | 1 |

**Backend total**: ~65 tests across 9 files

**Frontend daily tests** (6 files):

| ID | File | Description | Approx Tests |
|----|------|-------------|--------------|
| R6-10 | `tests/unit/daily-loader.test.ts` | Core loader tests: formatDateKey, loadDailyIndex, extractPuzzlePaths, cache, etc. | ~25 |
| R6-11 | `tests/unit/routes.test.ts` | Route parsing for `/modes/daily`, `/modes/daily/{date}` | ~5 |
| R6-12 | `tests/unit/progressWiring.test.ts` | `recordDailyPuzzleCompletion`, streak tracking | ~3 |
| R6-13 | `tests/unit/navigationState.test.ts` | Daily challenge offline fallback | ~2 |
| R6-14 | `tests/unit/constants.test.ts` | `dailyBase` path validation | 1 |
| R6-15 | `tests/e2e/daily-load.spec.ts` | E2E: daily challenge loading | ~3 |
| R6-16 | `tests/visual/specs/daily.visual.spec.ts` | Visual regression: DailyChallengePage | ~2 |

**Frontend total**: ~41 tests across 7 files

**Grand total**: ~106 daily-related tests across 16 files.

---

### R7: GitHub Actions Workflow

| ID | Finding | Source |
|----|---------|--------|
| R7-1 | `.github/workflows/daily-generation.yml` runs on cron `0 0 * * *` (daily at midnight UTC) and `workflow_dispatch` with optional date input. | L6-14 |
| R7-2 | The workflow runs `python -m backend.puzzle_manager daily --date "$DATE"` then commits JSON to `yengo-puzzle-collections/` and pushes. | L60-65 |
| R7-3 | A separate `deploy` job builds the frontend and deploys to GitHub Pages. Depends on `generate` job. | L80-120 |
| R7-4 | The workflow deploys to branch `001-core-platform` (conditional: `if: github.ref == 'refs/heads/001-core-platform'`). | L85 |

**Migration impact**: The workflow would need to:
1. Run `python -m backend.puzzle_manager daily --date "$DATE"` which now writes to DB-1 instead of JSON.
2. Commit `yengo-search.db` + `db-version.json` instead of `views/daily/` JSON files.
3. The `git add` target changes from `yengo-puzzle-collections/` (which catches JSON) to specifically `yengo-puzzle-collections/yengo-search.db yengo-puzzle-collections/db-version.json`.

---

### R8: Config Model — `DailyConfig`

| ID | Finding | Source |
|----|---------|--------|
| R8-1 | `DailyConfig` lives at `backend/puzzle_manager/models/config.py` L54-84. | Direct read |
| R8-2 | Current fields: `standard_puzzle_count` (30), `timed_set_count` (3), `timed_puzzles_per_set` (50), `tag_puzzle_count` (50), `min_quality` (2), `excluded_content_types` ([3]), `level_weights` (dict with validation). | L57-84 |
| R8-3 | `DailyConfig` has a `puzzles_per_day` property alias for `standard_puzzle_count`. | L79-81 |
| R8-4 | `DailyConfig` is embedded in `PipelineConfig` at L157 as `daily: DailyConfig = Field(default_factory=DailyConfig)`. | L157 |
| R8-5 | `OutputConfig` at L92-97 has `daily_path: str = Field("views/daily")`. This becomes obsolete when daily moves to DB. | L97 |
| R8-6 | No `rolling_window_days` field exists. Adding it is straightforward — add to `DailyConfig` as `rolling_window_days: int = Field(90, ge=7, le=365)`. | Proposed |
| R8-7 | Config is loaded via `ConfigLoader` from `pipeline.json` if it exists, otherwise uses defaults. `DailyConfig` defaults are all in the model class itself. | `config/loader.py` |

**No `pipeline.json` override file was found** — all config uses `DailyConfig` defaults.

---

### R9: Naming Conflict Check — `daily_schedule` / `daily_challenges`

| ID | Finding | Source |
|----|---------|--------|
| R9-1 | No existing table named `daily_schedule`, `daily_challenges`, or `daily_challenge` in `_SCHEMA_SQL`. | `db_builder.py` L18-72 |
| R9-2 | `DAILY_CHALLENGE_GROUPS` constant exists in `frontend/src/models/level.ts` but is a TypeScript constant, not a DB table. | `models/level.ts` L62 |
| R9-3 | `DailyChallenge` is a Pydantic model in `backend/puzzle_manager/models/daily.py` — used for JSON serialization. Not a DB entity. | grep results |
| R9-4 | No SQLite code anywhere references `daily_schedule` or `daily_challenges` as table names. | Full workspace search |

**Conclusion**: The names `daily_schedule` and `daily_puzzles` are safe to use. No naming conflicts exist.

---

## 3. External References

| ID | Reference | Relevance |
|----|-----------|-----------|
| E-1 | sql.js documentation: DDL support in WASM SQLite | sql.js supports full SQLite DDL including `INSERT OR REPLACE`, `CREATE TABLE IF NOT EXISTS`. All standard SQL operations available. |
| E-2 | SQLite `INSERT OR REPLACE` semantics | Idempotent upsert pattern — matches R4-B approach. Already used in `content_db.py`. |
| E-3 | SQLite WAL journal mode for concurrent reads | DB-1 is distributed as `journal_mode=DELETE` (read-only artifact). Daily inserts would need to temporarily use WAL, then switch back. Already done in `build_search_db()`. |
| E-4 | GitHub Actions: committing binary DB files | Binary DB files generate larger diffs than JSON. Consider `git lfs` for `yengo-search.db` if it grows beyond ~5MB. Currently ~500KB. |

---

## 4. Candidate Adaptations for Yen-Go

### Approach A: Daily tables in DB-1, regenerated on each publish

**Mechanism**: Add `daily_schedule` and `daily_puzzles` to `_SCHEMA_SQL`. After `build_search_db()` completes, the daily generator opens the newly built DB-1 and inserts rows. The daily CLI command also opens DB-1 directly for incremental inserts.

**Pros**: Simple, consistent with existing rebuild pattern, no schema surgery needed.
**Cons**: All daily data is regenerated on publish. For a rolling 90-day window this is fast (~90 inserts).

### Approach B: Separate daily insert after DB-1 build (post-hook)

**Mechanism**: `build_search_db()` returns the DB path. A new `inject_daily_rows(db_path, rows)` function opens the DB and inserts daily rows. Called both from publish stage and CLI.

**Pros**: Clean separation, daily function is reusable.
**Cons**: Minimal difference from Approach A in practice.

### Approach C: Daily as 4th pipeline stage

**Mechanism**: Register `DailyStage` in coordinator. Runs after publish. Reads DB-1 puzzle pool, generates daily, writes to DB-1.

**Pros**: Full lifecycle management (state tracking, error handling, resume support).
**Cons**: Overkill for a simple insert operation. Daily gen takes <1s.

---

## 5. Risks, License/Compliance, Rejection Reasons

| ID | Risk | Severity | Mitigation |
|----|------|----------|------------|
| RK-1 | DB-1 binary diff in git — larger commits than JSON | Low | DB is ~500KB. Daily adds ~2KB. Git handles this fine. Monitor if >5MB. |
| RK-2 | Frontend must load entire DB before showing daily challenge (no lazy JSON fetch) | Low | DB is already loaded on app bootstrap (step 1 of bootstrap sequence). Daily queries add negligible overhead. |
| RK-3 | Atomic swap in publish destroys daily rows unless re-generated | High | R4-B approach handles this: re-generate daily rows after each rebuild. |
| RK-4 | CI workflow commits binary DB instead of human-readable JSON | Medium | JSON files were not human-reviewed anyway. `db-version.json` provides audit trail. |
| RK-5 | Rolling window pruning could accidentally delete future pre-generated days | Low | Prune only dates < `today - rolling_window_days`. |
| RK-6 | ~106 existing tests need migration or deletion | Medium | Phase the migration: keep JSON tests working until DB tests are proven. |

**No license/compliance issues** — all changes are internal, no new external dependencies.

---

## 6. Planner Recommendations

1. **Use R4-B (re-generate daily rows after rebuild)**: Add `daily_schedule` and `daily_puzzles` tables to `_SCHEMA_SQL`. After `build_search_db()` in the publish stage, call a new `inject_daily_schedule()` function that generates daily rows from the puzzle pool and inserts them into the just-built DB-1. The standalone `daily` CLI command does the same via `INSERT OR REPLACE` on the existing DB-1 file.

2. **Keep daily as a separate CLI command (don't add a 4th pipeline stage)**: The daily generator is lightweight (<1s). Adding it as a full pipeline stage would be overengineering. Instead, call `inject_daily_schedule()` as a post-step within `PublishStage.run()` and as the primary action of `cmd_daily()`.

3. **Phase the frontend migration**: The frontend already loads `yengo-search.db` on bootstrap. Replace `daily-loader.ts` fetch logic with SQL queries against the in-memory DB. The `DailyPuzzleLoader` class and `dailyChallengeService` become thin wrappers around SQL queries. Files R3-5 through R3-8 (pages, app.tsx) need minimal changes — only the data source changes, not the component interface.

4. **Change daily error handling to "LOUD FAILURE"**: Replace `logger.warning` with `logger.error(exc_info=True)` in generator.py L100-101. Return failure counts in the daily generation result. Follow the `StageExecutor` pattern for error propagation.

---

## 7. Confidence & Risk Update

| Metric | Value |
|--------|-------|
| `post_research_confidence_score` | 85 |
| `post_research_risk_level` | medium |

**Open questions**:

| q_id | question | options | recommended | user_response | status |
|------|----------|---------|-------------|---------------|--------|
| Q1 | Should the publish stage automatically re-generate daily rows for the rolling window, or should daily remain a manual CLI step? | A: Auto-generate in publish / B: Manual CLI only / C: Both (publish generates, CLI for ad-hoc) | C | | ❌ pending |
| Q2 | What rolling window size should be the default? | A: 30 days / B: 60 days / C: 90 days / D: Other | C (90 days) | | ❌ pending |
| Q3 | Should the `views/daily/` JSON files be deleted from the repo as part of this migration, or kept as fallback? | A: Delete immediately / B: Keep for 1 release cycle / C: Keep indefinitely | A | | ❌ pending |
| Q4 | For the frontend, should daily queries go through the existing `sqliteService` or a new dedicated daily query module? | A: Extend sqliteService / B: New dailyQueryService / C: Other | A | | ❌ pending |

---

## Handoff

```json
{
  "research_completed": true,
  "initiative_path": "TODO/initiatives/20260315-1500-feature-daily-db-migration/",
  "artifact": "15-research.md",
  "top_recommendations": [
    "Use R4-B: re-generate daily rows after each DB-1 rebuild + INSERT OR REPLACE for CLI",
    "Keep daily as separate CLI command, don't add 4th pipeline stage",
    "Phase frontend migration: replace daily-loader.ts fetch with SQL queries",
    "Change daily error handling to LOUD FAILURE pattern (logger.error + exc_info)"
  ],
  "open_questions": ["Q1: auto-generate vs manual CLI", "Q2: rolling window size", "Q3: delete JSON files?", "Q4: frontend query module placement"],
  "post_research_confidence_score": 85,
  "post_research_risk_level": "medium"
}
```
