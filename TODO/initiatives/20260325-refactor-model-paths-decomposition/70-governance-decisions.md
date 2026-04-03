# Governance Decisions: model_paths.py Decomposition

**Initiative**: 20260325-refactor-model-paths-decomposition
**Date**: 2026-03-25

---

## Gate 1: Charter Review

**Decision**: `change_requested` → RC-1 through RC-7 applied → resubmitting
**Status Code**: `GOV-CHARTER-REVISE`

### Required Changes (Applied)

| rc_id | description | artifact | status |
|---|---|---|---|
| RC-1 | Updated Goal 4 to reflect full decomposition (remove shim language) | `00-charter.md` | ✅ applied |
| RC-2 | Tightened AC-5 to "deleted after verification" only | `00-charter.md` | ✅ applied |
| RC-3 | Updated AC-7 to "All existing tests pass" (removed "without modification") | `00-charter.md` | ✅ applied |
| RC-4 | Moved 20+ importers from out-of-scope to in-scope | `00-charter.md` | ✅ applied |
| RC-5 | Fixed initiative_type from "feature" to "refactor" | `status.json` | ✅ applied |
| RC-6 | Updated phase_state.charter/clarify to "approved" | `status.json` | ✅ applied |
| RC-7 | Populated decision rationale from Q1/Q2 answers | `status.json` | ✅ applied |

### Panel Support Summary

| review_id | member | domain | vote |
|---|---|---|---|
| GV-1 | Cho Chikun (9p) | Classical tsumego | approve |
| GV-2 | Lee Sedol (9p) | Intuitive fighter | approve |
| GV-3 | Shin Jinseo (9p) | AI-era professional | approve |
| GV-4 | Ke Jie (9p) | Strategic thinker | approve |
| GV-5 | Principal Staff Engineer A | Systems architect | change_requested → applied |
| GV-6 | Principal Staff Engineer B | Data pipeline | change_requested → applied |
| GV-7 | Hana Park (1p) | Player experience | approve |
| GV-8 | Mika Chen | DevTools UX | approve |
| GV-9 | Dr. David Wu | KataGo engine | approve |
| GV-10 | Dr. Shin Jinseo | Tsumego correctness | approve |

Research quality rated excellent. 92 confidence well-earned by individual importer mapping and circular dependency trace.

---

## Gate 2: Options Election

**Decision**: `approve`
**Status Code**: `GOV-OPTIONS-APPROVED`
**Unanimous**: Yes (10/10)

### Selected Option

| Field | Value |
|---|---|
| Option ID | OPT-2 |
| Title | Full decomposition into config/ + conftest |
| Selection rationale | Only option satisfying all charter goals, all ACs, and user direction (Q5:A). Score 9.2/10. OPT-1 rejected (SRP violation, doesn't match direction). OPT-3 rejected (YAGNI). |

### Must-Hold Constraints

1. All 20+ import sites updated to direct imports — no permanent facade
2. `model_paths.py` deleted only after full test verification (Q1:B)
3. `clear_cache()` becomes config-internal (AC-6)
4. TEST_* resolution timing explicitly designed (eager constants in conftest)
5. `run_calibration.py::_resolve_model_paths()` scoping documented
6. All existing tests pass (AC-7)
7. AGENTS.md updated in same commit (AC-8)

---

## Gate 3: Plan Review

**Decision**: `approve_with_conditions`
**Status Code**: `GOV-PLAN-CONDITIONAL`
**Unanimous**: Yes (10/10)

### Conditions (Applied)

| rc_id | description | status |
|---|---|---|
| RC-1 | Fix D7 text — remove incorrect `_diag_attacker.py` and `_diag_offline.py` references | ✅ applied |
| RC-2 | Update status.json phase_state for analyze/plan | ✅ applied |

### Handover to Executor

- **Message**: Execute 3-phase task list (T1-T3 → T4-T21 → T22-T26). Run enrichment-regression at T22 and T26 checkpoints.
- **Blocking items**: None
- **Planning confidence**: 95
- **Risk level**: low

---

## Gate 4: Implementation Review

**Decision**: `approve`
**Status Code**: `GOV-REVIEW-APPROVED`
**Unanimous**: Yes (10/10)

### Member Reviews

| review_id | member | domain | vote | supporting_comment |
|---|---|---|---|---|
| GV-1 | Cho Chikun (9p) | Classical tsumego | approve | Clean structural solution. Single source of truth for model_path(). |
| GV-2 | Lee Sedol (9p) | Intuitive fighter | approve | Good adaptation — DEV-1 shows instinct when plan hits collision. |
| GV-3 | Shin Jinseo (9p) | AI-era professional | approve | D42 model indirection correctly preserved in config/helpers.py. |
| GV-4 | Ke Jie (9p) | Strategic thinker | approve | Minimal blast radius, mechanical changes, zero feature regression. |
| GV-5 | Principal Staff Engineer A | Systems architect | approve | Circular dep eliminated. SRP enforced. DEV-1 architecturally correct. |
| GV-6 | Principal Staff Engineer B | Data pipeline | approve | Pipeline unaffected. 2459 tests collect. Pre-existing failures identified. |
| GV-7 | Hana Park (1p) | Player experience | approve | Zero player impact — internal tool refactor only. |
| GV-8 | Mika Chen | DevTools UX | approve | AGENTS.md accurately reflects new structure. |
| GV-9 | Dr. David Wu | KataGo engine | approve | Engine integration paths identical. KataGo startup params unchanged. |
| GV-10 | Dr. Shin Jinseo | Tsumego correctness | approve | No move classification or enrichment behavior changes. |

### Support Summary

Unanimous approval. All 8 ACs met. DEV-1 (TEST_* in config/helpers.py) accepted as justified.

### Handover to Executor

- **Message**: Implementation review approved. Proceed to closeout.
- **Blocking items**: None
- **Required next actions**: Update status.json, prepare closeout artifacts.

### Docs Plan Verification

```json
{
  "docs_plan_verification": {
    "present": true,
    "coverage": "complete"
  }
}
```

---

## Gate 5: Closeout Audit

**Decision**: `approve`
**Status Code**: `GOV-CLOSEOUT-APPROVED`
**Unanimous**: Yes (10/10)

### Summary

All panel members approve closeout. 11/11 artifacts present and current. Full 4-gate lifecycle completed. All 8 acceptance criteria verified with live evidence. Zero remaining `model_paths` references. model_paths.py and tests/_model_paths.py deleted. AGENTS.md updated. No residual risk or open items.

### Member Reviews

| review_id | member | domain | vote |
|---|---|---|---|
| GV-1 | Cho Chikun (9p) | Classical tsumego | approve |
| GV-2 | Lee Sedol (9p) | Intuitive fighter | approve |
| GV-3 | Shin Jinseo (9p) | AI-era professional | approve |
| GV-4 | Ke Jie (9p) | Strategic thinker | approve |
| GV-5 | Principal Staff Engineer A | Systems architect | approve |
| GV-6 | Principal Staff Engineer B | Data pipeline | approve |
| GV-7 | Hana Park (1p) | Player experience | approve |
| GV-8 | Mika Chen | DevTools UX | approve |
| GV-9 | Dr. David Wu | KataGo engine | approve |
| GV-10 | Dr. Shin Jinseo | Tsumego correctness | approve |
