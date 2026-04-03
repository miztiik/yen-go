# Governance Decisions

**Initiative:** `2026-03-07-feature-enrichment-lab-query-fix`
**Last Updated:** 2026-03-07

---

## Options Review — GOV-OPTIONS-APPROVED

**Date:** 2026-03-07
**Decision:** approve
**Status code:** GOV-OPTIONS-APPROVED
**Unanimous:** Yes (6/6)
**Selected option:** OPT-B — Extract shared `prepare_tsumego_query()` + simplify adapter

### Per-Member Support

| review_id | member           | domain              | vote    | comment                                                                                                                                |
| --------- | ---------------- | ------------------- | ------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| GV-1      | Cho Chikun (9p)  | Classical tsumego   | approve | Fix by construction: single function always sets region constraint. OPT-A leaves door open for future violations.                      |
| GV-2      | Lee Sedol (9p)   | Intuitive fighter   | approve | 3-path divergence is a creative trap. OPT-B makes constraint obvious: one function, all paths.                                         |
| GV-3      | Shin Jinseo (9p) | AI-era professional | approve | Missing allowed_moves makes KataGo produce full-board policy — meaningless for tsumego. OPT-B ensures all prep flows through one path. |
| GV-4      | Ke Jie (9p)      | Strategic thinker   | approve | Broken trees actively harm learning. OPT-B fixes by construction + golden fixture prevents regression.                                 |
| GV-5      | Staff Engineer A | Systems architect   | approve | Textbook DRY extraction. Must-hold: extracted function must be pure (no engine ref).                                                   |
| GV-6      | Staff Engineer B | Data pipeline       | approve | Single function = single logging point. Backward-compat waiver correct (broken output, no consumers).                                  |

### Must-Hold Constraints

1. Extracted function must be **pure** (position + config → query bundle; no engine reference, no side effects)
2. `SyncEngineAdapter` remains in `solve_position.py` (preserves dependency direction)
3. Extracted function returns data including `allowed_moves` — callers cannot bypass it
4. Existing 125+ tests must continue to pass (AC-8)
5. Golden fixture must test the exact failure mode: adapter path producing correct solutions within puzzle region

### Selection Rationale

Only option that achieves DRY+SRP+DIP compliance simultaneously; fixes BUG-1 by construction; auto-propagates ko-aware rules, symmetries, max_time to all query paths; ~40 lines of extraction follows KISS/YAGNI.

---

## Plan Review — GOV-PLAN-CONDITIONAL

**Date:** 2026-03-07
**Decision:** approve_with_conditions
**Status code:** GOV-PLAN-CONDITIONAL
**Unanimous:** Yes (6/6)

### Per-Member Support

| review_id | member           | domain              | vote    | comment                                                                                                 |
| --------- | ---------------- | ------------------- | ------- | ------------------------------------------------------------------------------------------------------- |
| GV-1      | Cho Chikun (9p)  | Classical tsumego   | approve | Plan guarantees deterministic puzzle region restriction. Golden fixture uses real corner L&D position.  |
| GV-2      | Lee Sedol (9p)   | Intuitive fighter   | approve | Refutation branch cleanup correctly removes winrate diagnostics. "Wrong." is sufficient for teaching.   |
| GV-3      | Shin Jinseo (9p) | AI-era professional | approve | TsumegoQueryBundle separates query prep from engine interaction. Ko/symmetries/max_time auto-propagate. |
| GV-4      | Ke Jie (9p)      | Strategic thinker   | approve | Encoding fix (latin-1 → utf-8) addresses double-encoding pattern. Preserves original C[] content.       |
| GV-5      | Staff Engineer A | Systems architect   | approve | All SOLID principles respected. Task ordering correct. Dependency graph clean.                          |
| GV-6      | Staff Engineer B | Data pipeline       | approve | Logging filter fix uses explicit prefix allowlist. run_id format change has confirmed-low impact.       |

### Conditions

| RC-id | Required Change                                                         | Severity |
| ----- | ----------------------------------------------------------------------- | -------- |
| RC-1  | Update status.json: set `analyze` to `approved` before execution begins | Low      |

### Handover

Plan approved by unanimous panel (6/6). Execute tasks T1-T11 in dependency order. All source code locations verified. Ensure RE-5 test assertions updated in T8.

---

## Implementation Review — GOV-REVIEW-APPROVED

**Date:** 2026-03-07
**Decision:** approve
**Status code:** GOV-REVIEW-APPROVED
**Unanimous:** Yes (6/6)

### Per-Member Support

| review_id | member           | domain              | vote    | comment                                                                                                                                                   |
| --------- | ---------------- | ------------------- | ------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| GV-1      | Cho Chikun (9p)  | Classical tsumego   | approve | Fix is deterministic and structurally correct. `prepare_tsumego_query()` enforces region restriction. Golden fixture tests prevent regression.            |
| GV-2      | Lee Sedol (9p)   | Intuitive fighter   | approve | Refutation branch cleanup correct. Retaining "Refutation line N/M." for multi-branch is a good pedagogical compromise. BUG-1 fix is the real victory.     |
| GV-3      | Shin Jinseo (9p) | AI-era professional | approve | KataGo policy is meaningless without `allowed_moves`. `TsumegoQueryBundle` makes constraint impossible to bypass. Pure function = no hidden engine state. |
| GV-4      | Ke Jie (9p)      | Strategic thinker   | approve | Broken solution trees harm students. Fix restores fundamental contract. Golden fixture encoded the real-world failure case.                               |
| GV-5      | Staff Engineer A | Systems architect   | approve | Textbook DRY extraction. SRP/DIP preserved. Status.json gates correct.                                                                                    |
| GV-6      | Staff Engineer B | Data pipeline       | approve | Logging fix correct: prefix tuple matches actual `__name__` values. `generate_run_id()` format change low-impact. 222 tests pass.                         |

### Observations (Non-Blocking)

| obs_id | finding                                                                                               | severity      |
| ------ | ----------------------------------------------------------------------------------------------------- | ------------- |
| OBS-1  | `_apply_patches()` at sgf_enricher.py L525-526 still uses `latin-1` — pre-existing, out of scope.     | Low           |
| OBS-2  | 2 pre-existing ruff warnings in solve_position.py (L1558, L1714) — not in changed code.               | Low           |
| OBS-3  | T7 retains "Refutation line N/M." for multi-branch — acceptable (structural content, not diagnostic). | Informational |

> **See also**:
>
> - [25-options.md](./25-options.md) — Full options analysis
> - [30-plan.md](./30-plan.md) — Technical plan
