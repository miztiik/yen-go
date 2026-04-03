# Governance Decisions — Config Panel + Sidebar Redesign

**Initiative**: `20260314-feature-enrichment-lab-config-panel`
**Last Updated**: 2026-03-15

---

## Gate 1: Charter Review

**Decision**: `approve_with_conditions`
**Status code**: `GOV-CHARTER-CONDITIONAL`
**Date**: 2026-03-14

### Member Reviews

| review_id | member | domain | vote | supporting_comment | evidence |
|-----------|--------|--------|------|--------------------|----------|
| GV-1 | Cho Chikun (9p, Meijin) | Classical tsumego authority | approve | Difficulty weight sliders (C-34 to C-38) with sum=100 constraint and normalize button are pedagogically sound. Difficulty calibration is most critical for tsumego quality. G-8 correctly includes DifficultyStage for engine-free re-run. | G-7, G-8; C-34–C-38; C-3; F.4 |
| GV-2 | Lee Sedol (9p) | Intuitive fighter | approve | Refutation params (C-10–C-15) control creative wrong-move exploration. No backward compat correct for dev tool. Per-stage TechniqueStage re-run will surface non-obvious tesuji classifications. | G-8; C-10–C-15; Q1 |
| GV-3 | Shin Jinseo (9p) | AI-era professional | approve | AI-solve params (C-22–C-29) and visit tiers (C-1, C-2, C-3) are the core KataGo tuning surface. All 45 params correctly identified as runtime-safe. Visits dropdown range (200–5000) is right. | B.1, B.3; G-5; RK-5; F.4 |
| GV-4 | Ke Jie (9p) | Strategic thinker | approve | All-45 scope (Q3→A) strategically correct over MVP-21 for a dev tuning tool. NG-1 (defer engine re-run) is wise — engine-free delivers 80% of value. localStorage persistence practical necessity. | G-1, G-6; Q3→A; NG-1 |
| GV-5 | Principal Staff Engineer A | Systems architect | approve | Architecture clean: self-contained in tools/, Pydantic v2 model_copy for overrides, server-side validation (C-4). status.json needs update (RC-1). | AGENTS.md; D-1, D-3; C-4 |
| GV-6 | Principal Staff Engineer B | Data pipeline engineer | approve | Pipeline analysis thorough: 10 stages, context I/O, serialization feasibility (22/28 JSON-safe). All-45 vs MVP-21 sizing delta should be in planning. | Section A, C, F; D-2; RK-3, RK-5 |
| GV-7 | Hana Park (1p) | Player experience & design | approve | Three-zone sidebar follows Grafana pattern. Accordion avoids cognitive overload. Config diff display (changed from defaults) not mentioned — consider in planning. | G-1–G-7; 4.1, 4.3, 4.5; C-7 |

### Required Changes

| RC-ID | Description | Status |
|-------|-------------|--------|
| RC-1 | Update status.json phase states (charter=approved, clarify=approved) | ✅ Done |
| RC-2 | Address G-8 phase boundary + config-diff-from-defaults in planning | ✅ Done (OPT-1 makes G-8 explicit Phase B; config-diff is planning enhancement) |

### Handover

```yaml
from_agent: Governance-Panel
to_agent: Feature-Planner
decision: approve_with_conditions
status_code: GOV-CHARTER-CONDITIONAL
message: >
  Charter approved 7/7. Proceed to options. Fix status.json (RC-1, done).
  Incorporate G-8 phase boundary and config-diff enhancement in options/plan (RC-2).
blocking_items: []
```

---

## Gate 2: Options Review

**Decision**: `approve`
**Status code**: `GOV-OPTIONS-APPROVED`
**Date**: 2026-03-14

### Selected Option

| Field | Value |
|-------|-------|
| option_id | OPT-1 |
| title | Phased Delivery: Core Panel → Re-Run |
| selection_rationale | Delivers 90% of user value (G-1–G-7) in Phase A without serialization risk. Respects Q4. Isolates PipelineContext serialization (6 non-JSON-safe fields) in Phase B. Unanimous 7/7. |
| must_hold_constraints | 1. All 45 params (not MVP-21). 2. Stepper onClick hook per stage. 3. Config-diff visual treatment in Phase A. 4. `GET /api/config` returns `model_dump()`. |

### Member Reviews

| review_id | member | vote | key rationale |
|-----------|--------|------|---------------|
| GV-1 | Cho Chikun (9p) | approve | Difficulty weights in Phase A; DifficultyStage re-run correctly deferred to Phase B |
| GV-2 | Lee Sedol (9p) | approve | Refutation/AI-solve tuning NOW, not blocked by serialization |
| GV-3 | Shin Jinseo (9p) | approve | All engine params in Phase A; 6 non-serializable fields isolated in Phase B |
| GV-4 | Ke Jie (9p) | approve | YAGNI: build tuning value now, defer optional re-run |
| GV-5 | PSE-A | approve | Clean architecture: self-contained, Pydantic model_copy, clean phase boundary |
| GV-6 | PSE-B | approve | Pipeline analysis validates phasing; all 45 runtime-safe |
| GV-7 | Hana Park (1p) | approve | Sidebar redesign is highest UX impact; config-diff as plan enhancement |

### Handover

```yaml
from_agent: Governance-Panel
to_agent: Feature-Planner
decision: approve
status_code: GOV-OPTIONS-APPROVED
message: >
  OPT-1 selected 7/7. Phase A: G-1-G-7 + config-diff enhancement.
  Phase B: G-8 (deferred). Must-hold: all 45, stepper onClick hook,
  GET /api/config model_dump, config-diff visual.
blocking_items: []
```

---

## Gate 3: Plan Review

**Decision**: `approve_with_conditions`
**Status code**: `GOV-PLAN-APPROVED`
**Date**: 2026-03-14

### Member Reviews (Summary)

| review_id | member | vote | key rationale |
|-----------|--------|------|---------------|
| GV-1 | Cho Chikun (9p) | approve | Weight sliders (DD-7) with sum=100 + normalize are pedagogically essential |
| GV-2 | Lee Sedol (9p) | approve | Refutation params (12 in accordion group 2) control creative exploration |
| GV-3 | Shin Jinseo (9p) | approve | AI-solve params (C-22-C-29) are core KataGo tuning; dotted-path transport correct |
| GV-4 | Ke Jie (9p) | approve | Strategic scoping sound; localStorage version field is forward-thinking |
| GV-5 | PSE-A | approve | Pydantic `__init__` reconstruction (DD-2) triggers all validators; `.config-*` namespace avoids CSS conflicts |
| GV-6 | PSE-B | approve | All 45 params runtime-safe; 8 test cases cover critical override paths |
| GV-7 | Hana Park (1p) | approve | Three-zone sidebar solves biggest UX pain; config-diff addresses charter concern |

### Required Changes (Resolved)

| RC-ID | Description | Status |
|-------|-------------|--------|
| RC-1 | T21 must say "Delete pipeline-bar.js" not "gut" | ✅ Fixed |
| RC-2 | T5 must confirm visits wiring status | ✅ Fixed — verified: already wired (bridge.py L302-305) |

### Handover

```yaml
from_agent: Governance-Panel
to_agent: Plan-Executor
decision: approve_with_conditions
status_code: GOV-PLAN-APPROVED
message: >
  Plan approved 7/7. 2 minor RCs resolved. 26 tasks, 7 phases.
  Begin Phase 1: T1, T3, T5, T6, T15 (parallelizable).
blocking_items: []
```

---

## Gate 4: Implementation Review

**Decision**: `approve_with_conditions`
**Status code**: `GOV-REVIEW-CONDITIONAL`
**Date**: 2026-03-14

### Member Reviews (Summary)

| review_id | member | vote | key rationale |
|-----------|--------|------|---------------|
| GV-1 | Cho Chikun (9p) | concern | Weight gating gap (RC-1) — submitting non-100 weights produces incorrect difficulty scores |
| GV-2 | Lee Sedol (9p) | approve | Refutation param tuning fully exposed, config-diff display gives immediate feedback |
| GV-3 | Shin Jinseo (9p) | approve | All AI-solve params + visit tiers exposed, dotted-path transport efficient |
| GV-4 | Ke Jie (9p) | approve | All 45 params delivered (MH-1), localStorage persistence practical |
| GV-5 | PSE-A | concern | CRA-1 plan deviation: getConfigOverrides() doesn't filter weights when sum≠100 |
| GV-6 | PSE-B | approve | Solid test results (11 new + 1905 lab + 1969 backend), all ripple-effects verified |
| GV-7 | Hana Park (1p) | concern | UX silent failure on invalid weights; three-zone sidebar and config diff are excellent |

### Required Changes

| RC-ID | Description | Status |
|-------|-------------|--------|
| RC-1 | `getConfigOverrides()` must filter `difficulty.structural_weights.*` paths when weight sum ≠ 100 (per DD-7) | ✅ Fixed — weight gating added |

### Handover

```yaml
from_agent: Governance-Panel
to_agent: Plan-Executor
decision: approve_with_conditions
status_code: GOV-REVIEW-CONDITIONAL
message: >
  6/7 approve, 3 concerns on one finding (RC-1). Fixed: weight gating
  added to getConfigOverrides(). Proceed to closeout.
blocking_items: []
```

---

## Gate 5: Closeout Audit

**Decision**: `approve_with_conditions`
**Status code**: `GOV-CLOSEOUT-CONDITIONAL`
**Date**: 2026-03-14

### Closeout Checks

| check_id | check | result |
|----------|-------|--------|
| CC-1 | All charter goals (G-1–G-7) met | ✅ |
| CC-2 | All governance RCs resolved (Gates 1–4) | ✅ |
| CC-3 | Tests passing (11 + 1905 + 1969) | ✅ |
| CC-4 | Documentation updated | ✅ (after RC-1 fix) |
| CC-5 | No blocking items remain | ✅ |

### Required Changes (Resolved)

| RC-ID | Description | Status |
|-------|-------------|--------|
| RC-1 | Update `docs/architecture/tools/enrichment-lab-gui.md` — replace pipeline-bar.js, add D9/D10/D11 design decisions | ✅ Fixed |
| RC-2 | Update `status.json` phase states | ✅ Fixed |

### Handover

```yaml
from_agent: Governance-Panel
to_agent: Plan-Executor
decision: approve_with_conditions
status_code: GOV-CLOSEOUT-CONDITIONAL
message: >
  Closeout approved. RC-1 (docs update) and RC-2 (status.json) resolved.
  Initiative closed.
blocking_items: []
```

---

## Gate 6: Post-Fix Implementation Re-Review

**Decision**: `approve`
**Status code**: `GOV-REVIEW-APPROVED`
**Date**: 2026-03-15

### Code Review Summary

| Reviewer | Verdict | AC Met | Architecture | Security | Critical | Major | Minor |
|----------|---------|--------|-------------|----------|----------|-------|-------|
| CR-ALPHA | pass_with_findings → all FIXED | 7/7 | — | — | 0 | 1 (FIXED) | 5 (FIXED) |
| CR-BETA | pass_with_findings → all FIXED | — | compliant (5/5) | clean (3/3) | 0 | 1 (FIXED) | 0 |
| **Combined** | **pass** (post-fix) | **7/7** | **compliant** | **clean** | **0** | **0 open** | **0 open** |

### Findings Fixed

| Finding | Severity | Fix Applied |
|---------|----------|-------------|
| CRA-1/CRB-1 | Major | Moved `apply_config_overrides()` before `StreamingResponse` with `try/except ValidationError → HTTPException(422)` |
| CRA-2 | Minor | Added `Number()` coercion in weight sum calculation in `getConfigOverrides()` |
| CRA-3 | Minor | Changed `.sidebar` from `overflow-y: auto` to `overflow: hidden` |
| CRA-4 | Minor | Added modified badges and reset buttons to Ko analysis group params |
| CRA-6 | Minor | Updated stale "pipeline bar" reference to "stage stepper" in app.js JSDoc |

### Member Reviews

| review_id | member | domain | vote | supporting_comment | evidence |
|-----------|--------|--------|------|--------------------|----------|
| GV-1 | Cho Chikun (9p, Meijin) | Classical tsumego authority | approve | Weight sliders with sum=100 + normalize correctly implemented. Gate 4 weight gating concern fully resolved. | config-panel.js weight params + getConfigOverrides gating |
| GV-2 | Lee Sedol (9p) | Intuitive fighter | approve | All 12 refutation params exposed. Config-diff badges give immediate tuning feedback. | config-panel.js refutation params; VAL-11 |
| GV-3 | Shin Jinseo (9p) | AI-era professional | approve | AI-solve params fully exposed. CRA-1 fix ensures reliable 422 for invalid KataGo params. | bridge.py pre-SSE validation; bridge_config_utils.py |
| GV-4 | Ke Jie (9p) | Strategic thinker | approve | All-45 params + localStorage persistence validated. Zero deviations from plan. | 50-execution-log.md 26/26 tasks |
| GV-5 | PSE-A | Systems architect | approve | CRA-1/CRB-1 fix properly implemented. No log handler leak. 11 unit tests cover override paths. | bridge.py L357-367; test_bridge_config.py |
| GV-6 | PSE-B | Data pipeline engineer | approve | Test results strong: 11 + 1905 + 1969 all passing. 10/10 ripple effects verified. | VAL-1-3 + RE-1-10 |
| GV-7 | Hana Park (1p) | Player experience & design | approve | Three-zone sidebar, Ko badges (CRA-4), overflow fix (CRA-3) all improve UX consistency. | styles.css overflow fix; config-panel.js Ko badges |

### Handover

```yaml
from_agent: Governance-Panel
to_agent: Plan-Executor
decision: approve
status_code: GOV-REVIEW-APPROVED
message: >
  Re-review approved 7/7 unanimous. All code review findings fixed.
  All charter goals met. Tests passing. No open issues.
blocking_items: []
re_review_requested: false
```

---

> **See also**:
> - [00-charter.md](./00-charter.md) — Reviewed charter
> - [10-clarifications.md](./10-clarifications.md) — User decisions
> - [15-research.md](./15-research.md) — Technical research
> - [15-research-ux.md](./15-research-ux.md) — UX research
> - [50-execution-log.md](./50-execution-log.md) — Execution details
> - [60-validation-report.md](./60-validation-report.md) — Test results
