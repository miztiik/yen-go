# Governance Decisions — Daily DB Migration

**Initiative**: `20260315-1500-feature-daily-db-migration`
**Last Updated**: 2026-03-15

## Gate 1: Charter Review

| Field | Value |
|---|---|
| `gate` | charter-review |
| `decision` | approve_with_conditions |
| `status_code` | GOV-CHARTER-CONDITIONAL |
| `from_agent` | Governance-Panel |
| `to_agent` | Feature-Planner |

### Member Reviews

| review_id | member | domain | vote | supporting_comment | evidence |
|---|---|---|---|---|---|
| GV-1 | Cho Chikun (9p) | Classical tsumego | approve | Selection logic correctly isolated from storage. Normalized schema maintains referential integrity. | AC1, NG5, Q5 |
| GV-2 | Lee Sedol (9p) | Intuitive fighter | approve | Hard cutover is correct — no live users, no regression. `attrs` JSON column leaves room for future challenge types. | Problem #1, Q3/Q7 |
| GV-3 | Shin Jinseo (9p) | AI-era professional | approve | No AI/ML impact. Daily tables add ~2KB to DB-1. Deterministic builds well-suited to SQLite. | RK-2, C2, E-1 |
| GV-4 | Ke Jie (9p) | Strategic thinker | concern | Transition gap not documented. → RC-1 | Problem #1 |
| GV-5 | PSE-A | Systems architect | concern | status.json stale (RC-2), G7 ambiguous (RC-3), table count unclear (RC-4) | status.json, G7, Q6 |
| GV-6 | PSE-B | Data pipeline | concern | CI workflow not scoped (RC-5), AC6 error scope unspecified (RC-6) | R7, R5 |
| GV-7 | Hana Park (1p) | Player experience | concern | No E2E rendering AC (RC-7), rolling window vs active session (RC-8) | AC2, G4, localStorage |

### Required Changes

| rc_id | description | status |
|---|---|---|
| RC-1 | Note in charter: daily never worked locally → zero transition risk | ✅ resolved |
| RC-2 | Update status.json decisions to reflect Q3/Q4/Q7 | ✅ resolved |
| RC-3 | Clarify G7: distinguish CLI incremental vs publish regenerate paths | ✅ resolved |
| RC-4 | Resolve table count: 2 tables with metadata as attrs on daily_schedule | ✅ resolved |
| RC-5 | Add CI workflow migration to charter scope | ✅ resolved |
| RC-6 | Refine AC6: specify all 3 error propagation sites | ✅ resolved |
| RC-7 | Add AC10: E2E frontend rendering verification | ✅ resolved |
| RC-8 | Add pruning safety constraint for active sessions | ✅ resolved |

### Rebuild/Reconcile Simplification (User Question)

**Panel unanimous**: Yes, removing rebuild/reconcile for daily data simplifies the architecture. Daily rows are **derived projections** — deterministically regenerable from the puzzle pool in <1s. Treating them as disposable-and-regenerable eliminates backup/restore complexity in rollback, reconcile, and publish log.

### Handover

```json
{
  "from_agent": "Governance-Panel",
  "to_agent": "Feature-Planner",
  "message": "Charter approved with 8 conditions, all resolved. Proceed to options.",
  "required_next_actions": ["Draft 25-options.md"],
  "artifacts_to_update": ["status.json", "00-charter.md"],
  "blocking_items": []
}
```

---

## Gate 2: Options Review

| Field | Value |
|---|---|
| `gate` | options-review |
| `decision` | approve_with_conditions |
| `status_code` | GOV-OPTIONS-CONDITIONAL |
| `from_agent` | Governance-Panel |
| `to_agent` | Feature-Planner |

### Selected Option

| Field | Value |
|---|---|
| `option_id` | OPT-3 |
| `title` | Separate Daily Insert Module |
| `selection_rationale` | Unanimous panel preference. Clean separation of generation (generator.py) from persistence (db_writer.py). Independently testable. Follows core/db_builder.py pattern. Best evolutionary fit. |

### Must-Hold Constraints

| ID | Constraint |
|---|---|
| MH-1 | `db_writer.py` must be a pure module — functions take `(db_path, data)` and return results. No generator imports. |
| MH-2 | Schema: `daily_schedule` + `daily_puzzles` tables. |
| MH-3 | Two write paths both call `db_writer`: publish post-step + CLI command. |
| MH-4 | LOUD FAILURE — `db_writer` raises `DailyGenerationError` on DB errors. |
| MH-5 | `prune_daily_window()` must be a separate, independently testable function. |
| MH-6 | Rolling window default 90 days, configurable via `DailyConfig.rolling_window_days`. |

### Member Votes (Options Gate)

| review_id | member | vote |
|---|---|---|
| GV-1 | Cho Chikun (9p) | approve |
| GV-2 | Lee Sedol (9p) | approve |
| GV-3 | Shin Jinseo (9p) | approve |
| GV-4 | Ke Jie (9p) | approve |
| GV-5 | PSE-A | concern (heading inconsistency → RC-1, resolved) |
| GV-6 | PSE-B | approve |
| GV-7 | Hana Park (1p) | approve |

### Required Changes

| rc_id | description | status |
|---|---|---|
| RC-1 | Remove "(Recommended)" label from OPT-1 heading | ✅ resolved |

---

## Gate 3: Plan Review

| Field | Value |
|---|---|
| `gate` | plan-review |
| `decision` | approve_with_conditions |
| `status_code` | GOV-PLAN-CONDITIONAL |
| `from_agent` | Governance-Panel |
| `to_agent` | Plan-Executor |

### Member Votes (Plan Gate)

| review_id | member | vote | key_comment |
|---|---|---|---|
| GV-1 | Cho Chikun (9p) | approve | Puzzle integrity preserved; algorithms untouched |
| GV-2 | Lee Sedol (9p) | approve | Operational flexibility strong; attrs JSON is good hedge |
| GV-3 | Shin Jinseo (9p) | approve | Deterministic builds preserved; additive schema |
| GV-4 | Ke Jie (9p) | concern | Rollback/reconcile gap → RC-2 (resolved) |
| GV-5 | PSE-A | concern | status.json stale → RC-1, T5/T11 scope → RC-2/RC-3 (all resolved) |
| GV-6 | PSE-B | approve | Pipeline integration clean; schema additive-only |
| GV-7 | Hana Park (1p) | concern | AC10 E2E → RC-3, prune safety → RC-4 (all resolved) |

### Required Changes

| rc_id | description | status |
|---|---|---|
| RC-1 | Update status.json phase fields | ✅ resolved |
| RC-2 | Extend T5: rollback + reconcile post-steps | ✅ resolved |
| RC-3 | Add explicit E2E rendering test to T11 | ✅ resolved |
| RC-4 | Specify prune date guard in T3 (C6 constraint) | ✅ resolved |

### Handover

```json
{
  "from_agent": "Governance-Panel",
  "to_agent": "Plan-Executor",
  "message": "Plan approved. All 4 conditions resolved. Proceed with Phase 1 execution.",
  "required_next_actions": ["Execute T1∥T2 (parallel)", "Then T3", "Then T15∥T4 (parallel)", "Then T5"],
  "artifacts_to_update": [],
  "blocking_items": []
}
```

---

## Gate 4: Implementation Review (Round 1)

| Field | Value |
|---|---|
| `gate` | implementation-review |
| `decision` | change_requested |
| `status_code` | GOV-REVIEW-REVISE |
| `from_agent` | Governance-Panel |
| `to_agent` | Plan-Executor |

### Required Changes (all resolved)

| rc_id | description | status |
|---|---|---|
| RC-1 | Fix broken `constants.test.ts` asserting deleted `dailyBase` | ✅ resolved |
| RC-2 | Delete dead `DailyIndexEntry`/`DailyMasterIndex` models | ✅ resolved |
| RC-3 | Delete `get_daily_output_dir()`/`daily_output_dir` dead code | ✅ resolved |
| RC-4 | Cache `date.today()` once in `prune_daily_window()` | ✅ resolved |
| RC-5 | Remove `views/daily/` references from stale docs | ✅ resolved |

### Verification Evidence
- `constants.test.ts`: 10 tests pass (dailyBase assertion removed)
- `test_paths.py`: 17 tests pass (daily dir test removed)
- `test_daily_db_writer.py`: 10 tests pass (prune date fix)
- Zero `DailyIndexEntry`/`DailyMasterIndex` references in non-cache backend files
- Zero `views/daily/` references in docs

---

## Gate 4: Implementation Review (Round 2 — Approved)

| Field | Value |
|---|---|
| `gate` | implementation-review |
| `decision` | approve |
| `status_code` | GOV-REVIEW-APPROVED |
| `unanimous` | true |
| `from_agent` | Governance-Panel |
| `to_agent` | Plan-Executor |

### Member Votes (Round 2)

| review_id | member | vote |
|---|---|---|
| GV-1 | Cho Chikun (9p) | approve |
| GV-2 | Lee Sedol (9p) | approve |
| GV-3 | Shin Jinseo (9p) | approve |
| GV-4 | Ke Jie (9p) | approve |
| GV-5 | PSE-A | approve |
| GV-6 | PSE-B | approve |
| GV-7 | Hana Park (1p) | approve |

All 10 ACs met. 88 tests pass. All 5 RCs from Round 1 resolved and verified.

---

## Gate 5: Closeout Audit (Approved)

| Field | Value |
|---|---|
| `gate` | closeout |
| `decision` | approve_with_conditions |
| `status_code` | GOV-CLOSEOUT-CONDITIONAL |
| `from_agent` | Governance-Panel |
| `to_agent` | Plan-Executor |

### Condition
RC-1: Clean up 4 stale `views/daily/` references (indexes.ts comments, E2E test mock comment, skip-marked test class) — all resolved in closeout.

### Member Votes

| review_id | member | vote |
|---|---|---|
| GV-1 | Cho Chikun (9p) | approve |
| GV-2 | Lee Sedol (9p) | approve |
| GV-3 | Shin Jinseo (9p) | approve |
| GV-4 | Ke Jie (9p) | approve |
| GV-5 | PSE-A | concern (mapped to RC-1, resolved) |
| GV-6 | PSE-B | approve |
| GV-7 | Hana Park (1p) | approve |
