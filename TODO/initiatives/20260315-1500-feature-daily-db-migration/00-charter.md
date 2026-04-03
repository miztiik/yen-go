# Charter — Daily Puzzle DB Migration

**Initiative**: `20260315-1500-feature-daily-db-migration`
**Type**: Feature (architectural migration)
**Last Updated**: 2026-03-15

## Problem Statement

The daily puzzle generation system currently writes per-day JSON files to `views/daily/{YYYY}/{MM}/{YYYY-MM-DD}-001.json`. This design predates the SQLite-based architecture (`yengo-search.db`) that now serves all puzzle metadata to the frontend via sql.js WASM. The JSON-file approach:

1. **Never worked locally** — the `views/daily/` directory was never generated; no daily puzzles have been served. **This means zero user regression risk from the migration — there is nothing to break.**
2. **Is architecturally inconsistent** — every other puzzle index (levels, tags, collections, search) uses the SQLite DB, but dailies use a separate JSON file tree.
3. **Creates unnecessary file proliferation** — each day produces a JSON file; over time this is 365+ files/year in the collections directory.
4. **Has silent failure** — the generator swallows per-date exceptions, making debugging impossible.

## Goals

| ID | Goal |
|---|---|
| G1 | Store daily puzzle schedules inside `yengo-search.db` using two new tables: `daily_schedule` (one row per date, with `attrs` JSON for metadata/technique) and `daily_puzzles` (one row per puzzle-per-date, FK to `puzzles.content_hash`) |
| G2 | Remove all JSON-based daily file generation and associated frontend code |
| G3 | Integrate daily generation into the publish stage with appropriate CLI flags |
| G4 | Support configurable rolling window (default 90 days), pruning only dates older than the window; current day and future dates are never pruned |
| G5 | Implement LOUD FAILURE — daily generation errors must propagate, not be silently swallowed |
| G6 | Frontend loads daily data from same sql.js DB — no additional network fetch |
| G7 | Two write paths: **(a) Publish path** — daily tables are created in `_SCHEMA_SQL` and populated after each DB-1 rebuild (regeneration, <1s). **(b) CLI path** — `daily` command uses `INSERT OR REPLACE` on existing DB-1 for incremental inserts without full rebuild. Both are valid and complementary. |
| G8 | Update all affected documentation |
| G9 | Update CI workflow (`.github/workflows/daily-generation.yml`) to commit DB changes instead of JSON files |

## Non-Goals

| ID | Non-Goal |
|---|---|
| NG1 | User accounts or cloud sync for daily progress |
| NG2 | Backward compatibility with JSON daily files |
| NG3 | Full DB rebuild/reconcile for daily data changes — daily rows are derived projections, regenerable from puzzle pool in <1s |
| NG4 | Daily generation in the browser (remains backend-only, pre-computed) |
| NG5 | Changing the puzzle selection algorithm (standard/timed/by_tag logic unchanged) |

## Constraints

- C1: Must follow Zero Runtime Backend holy law (static files only)
- C2: Must be deterministic (same date + same pool = same output)
- C3: Must integrate with existing `build_search_db()` flow or operate alongside it
- C4: Frontend code must use existing `sqliteService.ts` query infrastructure
- C5: No new WASM files or external dependencies
- C6: Rolling window pruning must not remove dates for which localStorage has in-progress daily sessions — guarantee: current day and future dates are never pruned

## Acceptance Criteria

- AC1: `python -m backend.puzzle_manager daily --date 2026-03-15` generates daily rows in `yengo-search.db`
- AC2: Frontend can query daily puzzles via `SELECT ... FROM daily_schedule WHERE date = ?`
- AC3: No `views/daily/` directory or JSON files are produced
- AC4: All legacy daily JSON code (generator paths, frontend loaders, tests) is deleted
- AC5: Pipeline publish stage includes daily generation as a mandatory post-step (always-on; standalone CLI `daily` command exists for ad-hoc generation)
- AC6: LOUD FAILURE at three specific sites: (a) per-date generation loop — errors logged at ERROR with `exc_info=True` and included in result; (b) puzzle pool loading — missing DB or DB errors raise `DailyGenerationError` instead of returning empty list; (c) overall generation — failure count surfaced in result
- AC7: Rolling window is configurable via `DailyConfig.rolling_window_days`
- AC8: Documentation updated: architecture, CLI reference, concepts
- AC9: All existing daily-related tests pass or are replaced with DB-based equivalents
- AC10: Frontend daily page renders puzzle board from SQL-sourced data (E2E verification that the rendering pipeline works end-to-end, not just the query)
