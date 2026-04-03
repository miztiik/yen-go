# Options — Daily Puzzle DB Migration

**Initiative**: `20260315-1500-feature-daily-db-migration`
**Last Updated**: 2026-03-15

## Context

From research (R4): `build_search_db()` creates DB-1 from scratch each publish. Daily tables will be in the schema but data is regenerated. The daily generator (selection algorithm) is unchanged — only the output target changes (DB tables vs JSON files). User directives: evolutionary architecture, integrate with publish, LOUD FAILURE, no rebuild/reconcile, docs mandatory.

---

## Option OPT-1: Embedded Post-Hook

**Summary**: Add daily tables to `_SCHEMA_SQL`. After `build_search_db()` completes in the publish stage, call `inject_daily_schedule(db_path, config)` as a post-hook. The standalone `daily` CLI command calls the same function via `INSERT OR REPLACE` on the existing DB-1.

### Schema

```sql
CREATE TABLE daily_schedule (
    date        TEXT PRIMARY KEY,   -- 'YYYY-MM-DD'
    version     TEXT NOT NULL DEFAULT '3.0',
    generated_at TEXT NOT NULL,
    technique_of_day TEXT DEFAULT '',
    attrs       TEXT DEFAULT '{}'   -- JSON: timed scoring, distribution, etc.
);

CREATE TABLE daily_puzzles (
    date         TEXT NOT NULL REFERENCES daily_schedule(date),
    content_hash TEXT NOT NULL REFERENCES puzzles(content_hash),
    section      TEXT NOT NULL,     -- 'standard', 'timed_blitz', 'timed_sprint', 'timed_endurance', 'by_tag'
    position     INTEGER NOT NULL,  -- ordering within section
    PRIMARY KEY (date, content_hash, section)
);

CREATE INDEX idx_daily_puzzles_date ON daily_puzzles(date);
CREATE INDEX idx_daily_puzzles_hash ON daily_puzzles(content_hash);
```

### Write Paths

| Path | Trigger | Mechanism | When |
|---|---|---|---|
| Publish | `python -m backend.puzzle_manager run --source X --stage publish` | DB-1 rebuilt from scratch → `inject_daily_schedule()` called as post-step | Every publish |
| CLI | `python -m backend.puzzle_manager daily --date 2026-03-15` | `INSERT OR REPLACE` on existing DB-1 | Ad-hoc / CI cron |
| Rollback | `python -m backend.puzzle_manager rollback --run-id X` | DB-1 rebuilt → `inject_daily_schedule()` called as post-step | On rollback |

### Frontend Query

```sql
-- Get today's standard puzzles
SELECT dp.content_hash, dp.position, p.batch, p.level_id
FROM daily_puzzles dp
JOIN puzzles p ON dp.content_hash = p.content_hash
WHERE dp.date = ? AND dp.section = 'standard'
ORDER BY dp.position;

-- Get daily metadata
SELECT * FROM daily_schedule WHERE date = ?;
```

### Benefits

| ID | Benefit |
|---|---|
| B1 | Single DB download — frontend already fetches `yengo-search.db` at bootstrap |
| B2 | SQL queries are consistent with how every other puzzle index is queried |
| B3 | `inject_daily_schedule()` is a pure function: takes db_path + config → inserts rows. Reusable from any context. |
| B4 | No schema surgery — tables are in `_SCHEMA_SQL`, created every rebuild |
| B5 | Rolling window pruning is a simple `DELETE FROM daily_schedule WHERE date < ?` |
| B6 | DB size increase is negligible (~2KB for 90-day window) |

### Drawbacks

| ID | Drawback |
|---|---|
| D1 | Daily data is lost on every publish rebuilds — must be regenerated (~90 deterministic inserts, <1s) |
| D2 | `daily_puzzles` has no FK enforcement at write time (SQLite FK pragmas off by default in build) |
| D3 | `section` column is a free-text string — risk of typos (mitigated by constants) |

### Risks

| ID | Risk | Severity | Mitigation |
|---|---|---|---|
| RK1 | Publish runs without daily post-hook → empty daily tables | High | Make `inject_daily_schedule()` call mandatory in publish, rollback, and reconcile flows |
| RK2 | Frontend queries daily tables before they exist (race on first load) | Low | Tables exist in schema (just empty). Frontend handles empty result gracefully. |
| RK3 | `INSERT OR REPLACE` on read-optimized DB-1 may be slightly slower | Low | <100 rows, <1s. Irrelevant. |

### Complexity: **Low** (estimated ~400 LOC backend, ~200 LOC frontend)

---

## Option OPT-2: Daily as 4th Pipeline Stage

**Summary**: Register `DailyStage` in the pipeline coordinator as a 4th stage (`ingest → analyze → publish → daily`). It runs after publish, reads the rebuilt DB-1 puzzle pool, generates daily schedule rows, and writes them to DB-1. Full `StageRunner` protocol compliance (state tracking, error handling, resume).

### Schema

Same as OPT-1 (identical tables).

### Write Paths

| Path | Trigger | Mechanism |
|---|---|---|
| Pipeline | `python -m backend.puzzle_manager run --source X` | All 4 stages run in order; daily stage runs after publish |
| Stage-only | `python -m backend.puzzle_manager run --stage daily` | Only daily stage runs |
| Rollback | DB-1 rebuilt → daily stage re-invoked | Via coordinator |

### Benefits

| ID | Benefit |
|---|---|
| B1 | Full lifecycle: state tracking, error recovery, resume support, consistent logging |
| B2 | `--stage daily` works like `--stage ingest` — consistent CLI UX |
| B3 | StageRunner protocol gives automatic error propagation (LOUD FAILURE built-in) |
| B4 | Pipeline coordinator handles ordering/dependencies |

### Drawbacks

| ID | Drawback |
|---|---|
| D1 | **Overengineered** — daily gen takes <1s, doesn't need resume/checkpoint/batch support |
| D2 | Must implement full `StageRunner` protocol (7+ methods) for a single INSERT operation |
| D3 | Creates coupling: daily is now a mandatory pipeline stage, not an optional post-step |
| D4 | Stage ordering requires daily to always run after publish — coordinator must enforce this |
| D5 | Requires `--source` flag even for daily-only runs (pipeline protocol requirement) |

### Risks

| ID | Risk | Severity | Mitigation |
|---|---|---|---|
| RK1 | StageRunner protocol churn affects daily stage | Medium | Protocol is stable, but adds maintenance surface |
| RK2 | Users must run `--stage daily` explicitly if not doing full pipeline | Low | Default `run` includes all stages |
| RK3 | Daily depends on publish completing first, but stage isolation makes this implicit | Medium | Add explicit stage dependency check |

### Complexity: **Medium** (estimated ~600 LOC backend, ~200 LOC frontend, StageRunner scaffolding)

---

## Option OPT-3: Separate Daily Insert Module (Middle Ground)

**Summary**: Create a `daily/db_writer.py` module with `inject_daily_schedule()` and `prune_daily_window()`. This module is called from both: (a) `PublishStage.run()` as a post-step, (b) `cmd_daily()` CLI command. The daily generator's `_write_challenge()` method is replaced to call `db_writer` instead of writing JSON. NOT a pipeline stage — just a reusable module.

### Schema

Same as OPT-1 (identical tables).

### Difference from OPT-1

| Aspect | OPT-1 | OPT-3 |
|---|---|---|
| Module organization | `inject_daily_schedule()` lives in `generator.py` | Separate `daily/db_writer.py` module — clean separation of concerns |
| Generator coupling | Generator produces Pydantic models → same function converts to DB rows | Generator produces Pydantic models → `db_writer` converts to DB rows |
| Testing | Test the combined generate+insert flow | Test `db_writer` in isolation from generation logic |
| Error handling | LOUD FAILURE in generator | LOUD FAILURE in `db_writer` + generator |

### Benefits

| ID | Benefit |
|---|---|
| B1 | Clean module boundary: generation logic (algorithm) vs persistence (DB writes) separated |
| B2 | `db_writer` is independently testable with mock data |
| B3 | Consistent with existing codebase pattern (e.g., `core/db_builder.py` is separate from stage logic) |
| B4 | No StageRunner overhead — remains a simple function call |

### Drawbacks

| ID | Drawback |
|---|---|
| D1 | One more file to maintain (but it's small and focused) |
| D2 | Slightly more indirection than OPT-1 |

### Risks

Same as OPT-1 (RK1-RK3).

### Complexity: **Low** (estimated ~450 LOC backend, ~200 LOC frontend)

---

## Comparison Matrix

| Criterion | OPT-1: Post-Hook | OPT-2: 4th Stage | OPT-3: Separate Module |
|---|---|---|---|
| Architecture fit | Good — lightweight | Overengineered | **Best** — clean separation |
| LOUD FAILURE | Manual implementation | Built-in via StageRunner | Manual but isolated |
| Complexity | Low (~600 LOC) | Medium (~800 LOC) | Low (~650 LOC) |
| Testability | Medium | Medium | **Best** — isolated db_writer |
| CLI UX | `daily` stays separate command | `--stage daily` | `daily` stays separate command |
| Maintenance burden | Low | Medium (StageRunner protocol) | Low |
| Evolutionary fit | Good | Rigid (full stage protocol) | **Best** — incremental evolution |
| Publish integration | Post-hook call | Stage dependency | Post-hook call |
| YAGNI compliance | Good | **Violates** — over-abstracted | Good |

### Recommendation

**OPT-3** (Separate Daily Insert Module) — it combines OPT-1's simplicity with clean module separation. The `db_writer.py` module is independently testable, follows existing codebase patterns (`core/db_builder.py`), and avoids StageRunner over-engineering. It's the most evolutionarily sound option — if daily ever needs to become a full stage, the `db_writer` module already exists and can be wrapped in a `StageRunner`.
