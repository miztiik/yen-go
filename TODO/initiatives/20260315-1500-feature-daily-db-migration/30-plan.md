# Plan — Daily Puzzle DB Migration (OPT-3)

**Initiative**: `20260315-1500-feature-daily-db-migration`
**Selected Option**: OPT-3 — Separate Daily Insert Module
**Last Updated**: 2026-03-15

## Architecture

### New Module: `daily/db_writer.py`

Pure persistence module. Takes DB path + data → writes rows. No generator imports.

```
daily/
├── __init__.py         # Updated exports
├── _helpers.py         # Unchanged
├── by_tag.py           # Unchanged (algorithm)
├── db_writer.py        # NEW — inject_daily_schedule(), prune_daily_window()
├── generator.py        # Modified — _write_challenge() replaced, _write_to_json() removed
├── standard.py         # Unchanged (algorithm)
└── timed.py            # Unchanged (algorithm)
```

### DB Schema Additions (in `_SCHEMA_SQL`)

```sql
CREATE TABLE daily_schedule (
    date             TEXT PRIMARY KEY,
    version          TEXT NOT NULL DEFAULT '3.0',
    generated_at     TEXT NOT NULL,
    technique_of_day TEXT DEFAULT '',
    attrs            TEXT DEFAULT '{}'
);

CREATE TABLE daily_puzzles (
    date         TEXT NOT NULL REFERENCES daily_schedule(date),
    content_hash TEXT NOT NULL REFERENCES puzzles(content_hash),
    section      TEXT NOT NULL,
    position     INTEGER NOT NULL,
    PRIMARY KEY (date, content_hash, section)
);

CREATE INDEX idx_daily_puzzles_date ON daily_puzzles(date);
CREATE INDEX idx_daily_puzzles_hash ON daily_puzzles(content_hash);
```

### Data Flow

```
                     ┌──────────────────┐
                     │  Puzzle Pool     │
                     │  (puzzles table) │
                     └────────┬─────────┘
                              │
              ┌───────────────┼───────────────┐
              │               │               │
         standard.py     timed.py        by_tag.py
              │               │               │
              └───────────────┼───────────────┘
                              │
                     DailyChallenge (Pydantic)
                              │
                     ┌────────┴────────┐
                     │   db_writer.py  │
                     │ inject_daily_   │
                     │ schedule()      │
                     └────────┬────────┘
                              │
              ┌───────────────┼───────────────┐
              │                               │
    Publish post-step               CLI `daily` command
    (after build_search_db)         (INSERT OR REPLACE)
```

### Write Path Details

**Path A — Publish Stage**:
1. `build_search_db()` creates DB-1 with empty `daily_schedule` + `daily_puzzles` tables
2. `inject_daily_schedule(db_path, challenges)` populates daily rows
3. DB-1 is finalized (VACUUM, ANALYZE)

**Path B — CLI Daily Command**:
1. Opens existing DB-1 at `yengo-puzzle-collections/yengo-search.db`
2. `inject_daily_schedule(db_path, challenges)` uses `INSERT OR REPLACE`
3. `prune_daily_window(db_path, rolling_window_days)` removes expired dates

**Path C — Rollback/Reconcile Post-Step**:
1. DB-1 rebuilt → empty daily tables
2. `inject_daily_schedule()` called as mandatory post-step

### Error Handling — LOUD FAILURE

| Site | Current | New |
|---|---|---|
| Per-date generation loop | `logger.warning` + continue | `logger.error(exc_info=True)` + collect failures + include in result |
| Puzzle pool loading (no DB) | Returns empty list | Raises `DailyGenerationError("yengo-search.db not found")` |
| Puzzle pool loading (DB error) | Returns empty list | Raises `DailyGenerationError` with original exception |
| `db_writer` DB errors | N/A (new) | Raises `DailyGenerationError` with context |

### Frontend Migration

Replace JSON fetch layer with SQL queries through existing `sqliteService`:

**New**: `frontend/src/services/dailyQueryService.ts`

```typescript
// Query daily schedule from in-memory yengo-search.db
export function getDailySchedule(date: string): DailyScheduleRow | null {
  const rows = query<DailyScheduleRow>(
    'SELECT * FROM daily_schedule WHERE date = ?', [date]
  );
  return rows[0] ?? null;
}

export function getDailyPuzzles(date: string, section?: string): DailyPuzzleRow[] {
  if (section) {
    return query<DailyPuzzleRow>(
      `SELECT dp.*, p.batch, p.level_id FROM daily_puzzles dp
       JOIN puzzles p ON dp.content_hash = p.content_hash
       WHERE dp.date = ? AND dp.section = ? ORDER BY dp.position`, [date, section]
    );
  }
  return query<DailyPuzzleRow>(
    `SELECT dp.*, p.batch, p.level_id FROM daily_puzzles dp
     JOIN puzzles p ON dp.content_hash = p.content_hash
     WHERE dp.date = ? ORDER BY dp.section, dp.position`, [date]
  );
}
```

**Delete**: `daily-loader.ts`, `dailyPath.ts`, `dailyChallengeService.ts` JSON fetch logic

**Update**: `dailyChallengeService.ts` → import from `dailyQueryService` instead of `daily-loader`

### Config Changes

```python
class DailyConfig(BaseModel):
    # ... existing fields unchanged ...
    rolling_window_days: int = Field(90, ge=7, le=365, description="Rolling window size in days")
```

Remove `OutputConfig.daily_path` (obsolete).

---

## Risks & Mitigations

| ID | Risk | Severity | Mitigation |
|---|---|---|---|
| RK1 | Publish/rollback runs without daily post-hook → empty daily tables | High | Enforce: add daily injection call in both `PublishStage.run()` and `RollbackManager`. Add integration test that verifies daily tables are populated after publish. |
| RK2 | `section` column typos | Low | Define `SECTION_STANDARD = "standard"` etc. as constants in `db_writer.py`. |
| RK3 | FK constraint violations if puzzle removed from DB-1 | Low | Daily regeneration always runs against current puzzle pool. Pruning deletes old rows first. |
| RK4 | Large test migration (~106 tests) | Medium | Phase: write new DB tests first, delete old JSON tests after verification. |

---

## Documentation Plan

| doc_action | file | why |
|---|---|---|
| Update | `docs/architecture/backend/puzzle-manager.md` | Add daily/db_writer.py to module tree, update daily data flow section |
| Update | `docs/how-to/backend/cli-reference.md` | Update `daily` command docs (output is now DB rows, not JSON) |
| Update | `docs/concepts/sqlite-index-architecture.md` | Add daily_schedule + daily_puzzles table documentation |
| Update | `backend/puzzle_manager/AGENTS.md` | Add db_writer.py to daily module map |
| Update | `frontend/src/AGENTS.md` | Update daily service layer description |
| Update | `.github/copilot-instructions.md` | Update DB-1 schema table, daily challenge format section |
| Update | `CLAUDE.md` | Update DB-1 schema table |
| Update | `docs/reference/github-actions.md` | Update daily generation workflow description |
| Delete | `views/daily/` references in all docs | Remove JSON path documentation |
