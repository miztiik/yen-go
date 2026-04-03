# Analysis — Daily Puzzle DB Migration (OPT-3)

**Initiative**: `20260315-1500-feature-daily-db-migration`
**Last Updated**: 2026-03-15

## Planning Context

| Metric | Value |
|---|---|
| `planning_confidence_score` | 85 |
| `risk_level` | medium |
| `research_invoked` | true |
| `selected_option` | OPT-3: Separate Daily Insert Module |

---

## Cross-Artifact Consistency

| finding_id | artifact_a | artifact_b | check | status |
|---|---|---|---|---|
| F1 | `00-charter.md` G1 | `30-plan.md` schema | Schema matches: 2 tables (`daily_schedule` + `daily_puzzles`) with `attrs` JSON | ✅ pass |
| F2 | `00-charter.md` G7 | `30-plan.md` write paths | Two write paths documented: publish post-step + CLI INSERT OR REPLACE | ✅ pass |
| F3 | `00-charter.md` AC6 | `40-tasks.md` T7 | T7 covers all 3 LOUD FAILURE sites (per-date loop, pool loading, db_writer) | ✅ pass |
| F4 | `00-charter.md` AC10 | `40-tasks.md` T11 | T11 includes explicit E2E rendering test step for AC10 | ✅ pass |
| F5 | `10-clarifications.md` Q6 | `25-options.md` schema | Q6 says `daily_metadata` table; schema uses `daily_schedule.attrs` instead (2 tables, not 3). Consistent with RC-4 resolution. | ✅ pass |
| F6 | `70-governance.md` MH-1 | `40-tasks.md` T3 | T3 explicitly states "no generator imports" constraint | ✅ pass |
| F7 | `70-governance.md` MH-5 | `40-tasks.md` T3 | T3 includes `prune_daily_window()` as separate function | ✅ pass |
| F8 | `70-governance.md` MH-6 | `40-tasks.md` T2 | T2 adds `rolling_window_days` with default 90 | ✅ pass |
| F9 | `00-charter.md` G9 | `40-tasks.md` T13 | T13 covers CI workflow update | ✅ pass |
| F10 | `00-charter.md` AC4 | `40-tasks.md` T12 | T12 has comprehensive delete list covering all legacy JSON code | ✅ pass |

### Gap Remediation

| finding_id | gap | remediation | task_ref |
|---|---|---|---|
| F4 | AC10 (E2E rendering) not explicitly in task T11 | Add explicit E2E test step: verify daily page renders from SQL data | T11 scope note |

---

## Coverage Map

| charter_item | type | task_ids | status |
|---|---|---|---|
| G1 (DB tables) | goal | T1, T3 | ✅ covered |
| G2 (remove JSON code) | goal | T12 | ✅ covered |
| G3 (publish integration) | goal | T5 | ✅ covered |
| G4 (rolling window) | goal | T2, T3 | ✅ covered |
| G5 (LOUD FAILURE) | goal | T7 | ✅ covered |
| G6 (frontend SQL) | goal | T9, T10 | ✅ covered |
| G7 (write paths) | goal | T4, T5, T6 | ✅ covered |
| G8 (docs) | goal | T14 | ✅ covered |
| G9 (CI workflow) | goal | T13 | ✅ covered |
| AC1 (CLI generates DB rows) | criteria | T4, T6 | ✅ covered |
| AC2 (frontend SQL query) | criteria | T9 | ✅ covered |
| AC3 (no JSON files) | criteria | T4, T12 | ✅ covered |
| AC4 (legacy deleted) | criteria | T12 | ✅ covered |
| AC5 (publish --daily flag) | criteria | T5 | ✅ covered |
| AC6 (LOUD FAILURE sites) | criteria | T7 | ✅ covered |
| AC7 (rolling_window_days) | criteria | T2 | ✅ covered |
| AC8 (docs updated) | criteria | T14 | ✅ covered |
| AC9 (tests pass) | criteria | T8, T11 | ✅ covered |
| AC10 (E2E rendering) | criteria | T11 | ✅ covered |

### Unmapped Tasks

| task_id | reason |
|---|---|
| T15 | Housekeeping (__init__.py exports) — supports T3/T4, no charter item needed |

---

## Ripple-Effects Analysis

| impact_id | direction | area | risk | mitigation | owner_task | status |
|---|---|---|---|---|---|---|
| RE-1 | upstream | `build_search_db()` schema changes | Low — additive only (new tables) | No existing tables modified | T1 | ✅ addressed |
| RE-2 | downstream | `PublishStage.run()` post-step addition | Medium — must not break existing publish flow | Add daily injection after successful DB build only | T5 | ✅ addressed |
| RE-3 | downstream | `RollbackManager` — DB-1 rebuild | Medium — daily tables empty after rollback | Add `inject_daily_schedule()` call as rollback post-step (WARNING-level) | T5 | ✅ addressed |
| RE-4 | downstream | `cmd_reconcile` — DB-1 rebuild | Medium — daily tables empty after reconcile | Add `inject_daily_schedule()` call as reconcile post-step (WARNING-level) | T5 | ✅ addressed |
| RE-5 | lateral | Frontend `sqliteService.ts` | Low — no changes to service, just new queries | New `dailyQueryService.ts` uses existing `query()` function | T9 | ✅ addressed |
| RE-6 | lateral | `DailyPuzzleLoader` in `puzzleLoaders.ts` | Medium — class must be deleted or refactored | Delete class, replace consumers with SQL queries | T12 | ✅ addressed |
| RE-7 | lateral | `APP_CONSTANTS.paths.dailyBase` | Low — constant referenced in loader code | Delete constant, remove references | T12 | ✅ addressed |
| RE-8 | lateral | Page components (`DailyChallengePage`, `DailyBrowsePage`, `HomePageGrid`) | Low — use service layer, not direct fetch | Service API shape unchanged; data source changes transparently | T10 | ✅ addressed |
| RE-9 | upstream | `daily/generator.py` constructor signature | Medium — changes from `output_dir` to `db_path` | Update all callers (CLI, tests, publish) | T4, T6, T8 | ✅ addressed |
| RE-10 | lateral | `models/daily.py` Pydantic models | Low — models unchanged, still used by generator | No changes needed | — | ✅ addressed |
| RE-11 | downstream | `db-version.json` regeneration | Low — daily inserts may change DB hash | `db-version.json` generated after daily injection, not before | T5 | ✅ addressed |
| RE-12 | lateral | Progress localStorage (`storageOperations.ts`) | None — stores date keys + completion data, doesn't reference JSON paths | No migration needed | — | ✅ addressed |

### Unresolved Ripple Effects

None — all ripple effects addressed.

---

## Severity-Based Findings Summary

| severity | count | finding_ids |
|---|---|---|
| High | 0 | — |
| Medium | 0 | — |
| Low | 0 | — |
| Info | 1 | T15 unmapped (housekeeping) |

---

## Confidence Assessment

Post-analysis confidence: **88/100**

- Schema design is clean and additive
- Two write paths are well-defined
- Frontend migration is straightforward (replace fetch with SQL query)
- Legacy cleanup scope is fully inventoried
- Rollback/reconcile post-steps resolved (T5 scope extended)
- AC10 E2E test step added to T11
- Pruning safety guard (C6) codified in T3
