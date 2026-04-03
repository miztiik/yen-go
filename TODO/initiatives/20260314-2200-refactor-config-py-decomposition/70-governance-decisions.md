# Governance Decisions — config.py Decomposition

> Initiative: `20260314-2200-refactor-config-py-decomposition`
> Last Updated: 2026-03-14

## Gate 1: Charter Review

| Field | Value |
|-------|-------|
| decision | `approve` |
| status_code | `GOV-CHARTER-APPROVED` |
| unanimous | true (7/7) |
| date | 2026-03-14 |

### Member Reviews

| review_id | member | domain | vote | supporting_comment |
|-----------|--------|--------|------|--------------------|
| GV-1 | Cho Chikun (9p) | Classical tsumego | approve | Pure structural refactor, zero puzzle correctness impact. Deterministic builds preserved. |
| GV-2 | Lee Sedol (9p) | Intuitive fighter | approve | Bold Q1=B choice (no facade) is justified. 120+ imports rewritten cleanly — risk managed by full test suite. |
| GV-3 | Shin Jinseo (9p) | AI-era professional | approve | AI-Solve domain (14 models) correctly isolated. KataGo query construction unchanged. |
| GV-4 | Ke Jie (9p) | Strategic thinker | approve | Follows v2 initiative recommendation. Timing is correct — v2 stabilization closed. |
| GV-5 | Staff Engineer A | Systems architect | approve | Clean dependency tree: sub-modules define → core composes → __init__ re-exports. AC-8 protects against circular imports. |
| GV-6 | Staff Engineer B | Data pipeline | approve | Pipeline performance unaffected. Cache pattern preserved. Batch processing path unchanged. |
| GV-7 | Hana Park (1p) | Player experience | approve | Zero player-facing impact. No frontend, no puzzle data, no UX changes. |

### Handover

| Field | Value |
|-------|-------|
| from_agent | Governance-Panel |
| to_agent | Feature-Planner |
| message | Charter approved. Proceed to options. Evaluate 2-3 granularity alternatives. Key constraint: Q1=B (no facade). Research identified 9 natural domain clusters. |
| required_next_actions | 1. Draft 25-options.md  2. Each option: module list + model assignment + line estimates  3. Submit for governance election |
| blocking_items | (none) |

---

## Gate 2: Options Election

| Field | Value |
|-------|-------|
| decision | `approve` |
| status_code | `GOV-OPTIONS-APPROVED` |
| unanimous | true (7/7) |
| date | 2026-03-14 |
| revision | Rev 2 (after GOV-OPTIONS-REVISE on Rev 1) |

### RC Resolution (Rev 1 → Rev 2)

| RC | Required Change | Status |
|----|----------------|--------|
| RC-1 | Revise line estimates from actual grep positions | ✅ Resolved |
| RC-2 | Split ai_solve into ai_solve.py + solution_tree.py | ✅ Resolved |
| RC-3 | Extract infrastructure models from analysis.py | ✅ Resolved |
| RC-4 | Eliminate OPT-2 (fails AC-6) | ✅ Resolved |
| RC-5 | Verify dependency direction — no circular imports | ✅ Resolved |

### Selected Option

| Field | Value |
|-------|-------|
| option_id | OPT-3 |
| title | Hybrid (10 files) |
| selection_rationale | Groups naturally-coupled difficulty+validation domain. ai_solve/solution_tree split separates classification from tree construction. analysis/infrastructure split isolates plumbing. All files ≤246 lines. Single cross-dependency: ai_solve → solution_tree. |
| must_hold_constraints | All files ≤250 lines. No circular imports. Zero runtime behavior change. |

### Member Reviews

| review_id | member | domain | vote | supporting_comment |
|-----------|--------|--------|------|--------------------|
| GV-1 | Cho Chikun (9p) | Classical tsumego | approve | Difficulty+validation grouping mirrors actual tsumego evaluation workflow. |
| GV-2 | Lee Sedol (9p) | Intuitive fighter | approve | Cognitive grouping > file count. Related concepts stay together. |
| GV-3 | Shin Jinseo (9p) | AI-era professional | approve | ai_solve/solution_tree split correctly separates classification from tree construction. |
| GV-4 | Ke Jie (9p) | Strategic thinker | approve | 10 vs 11 files matters less than intuitive grouping. OPT-3 preferred. |
| GV-5 | Staff Engineer A | Systems architect | approve | All 5 RCs verified. DAG dependency confirmed. __init__.py size is structural necessity. |
| GV-6 | Staff Engineer B | Data pipeline | approve | Zero runtime impact. Infrastructure split is correct (operational vs domain). |
| GV-7 | Hana Park (1p) | Player experience | approve | Zero player-facing impact. Difficulty+validation grouping aids calibration maintainers. |

### Handover

| Field | Value |
|-------|-------|
| from_agent | Governance-Panel |
| to_agent | Feature-Planner |
| message | OPT-3 elected unanimously. Proceed to plan + tasks. 120+ import rewrites, 10 new files, 30+ test updates. Plan must include phased execution, import rewrite approach, rollback strategy. |
| required_next_actions | 1. Draft 30-plan.md  2. Draft 40-tasks.md  3. Draft 20-analysis.md  4. Submit for plan governance review |
| blocking_items | (none) |

---

## Gate 3: Plan Review

| Field | Value |
|-------|-------|
| decision | `approve_with_conditions` |
| status_code | `GOV-PLAN-CONDITIONAL` |
| unanimous | false (4 approve, 3 concern → converted to RC rows) |
| date | 2026-03-14 |

### Required Corrections (resolved)

| RC | Required Change | Status |
|----|----------------|--------|
| RC-1 | Add task for `analyzers/stages/solve_paths.py` (missed from task list) | ✅ T27B added |
| RC-2 | Correct detector count 26 → 29 in T28 | ✅ Corrected |
| RC-3 | Correct test file count ~30 → ~38 in T35 | ✅ Corrected |
| RC-4 | Update import site count to 161 (from 120+) | ✅ Noted, not critical |

### Member Reviews

| review_id | member | domain | vote | supporting_comment |
|-----------|--------|--------|------|--------------------|
| GV-1 | Cho Chikun (9p) | Classical tsumego | approve | Clean mechanical refactor. 7-phase approach mirrors disciplined methodology. |
| GV-2 | Lee Sedol (9p) | Intuitive fighter | concern→approve | solve_paths.py miss proves the risk is real; T38/T39 safety net would catch it, but proactive fix is better. |
| GV-3 | Shin Jinseo (9p) | AI-era professional | concern→approve | solve_paths.py is an AI-Solve pipeline hot path — runtime import, not just type-checking. |
| GV-4 | Ke Jie (9p) | Strategic thinker | approve | 7-phase execution sound. Symbol mapping table eliminates judgment calls. |
| GV-5 | Staff Engineer A | Systems architect | concern→approve | Three count errata fixable without plan restructuring. Architecture is sound. |
| GV-6 | Staff Engineer B | Data pipeline | approve | Pipeline execution unaffected. Cache distribution correct. |
| GV-7 | Hana Park (1p) | Player experience | approve | Zero player-facing impact. AC-5 gates behavioral regression. |

### Handover

| Field | Value |
|-------|-------|
| from_agent | Governance-Panel |
| to_agent | Plan-Executor |
| message | Plan approved with conditions. 4 errata corrections required (all resolved). Begin execution. Key: solve_paths.py added as T27B. Architecture, phasing, and safety nets endorsed unanimously. |
| required_next_actions | 1. Apply RC corrections (done) 2. Set status to execute 3. Begin Phase 1 |
| blocking_items | (none — all RCs resolved) |

---

## Gate 4: Implementation Review

| Field | Value |
|-------|-------|
| decision | `approve` |
| status_code | `GOV-REVIEW-APPROVED` |
| unanimous | true (7/7) |
| date | 2026-03-14 |

### Member Reviews

| review_id | member | domain | vote | supporting_comment |
|-----------|--------|--------|------|--------------------|
| GV-1 | Cho Chikun (9p) | Classical tsumego | approve | Pure structural refactor with zero puzzle-logic changes. DEV-1 fix (config_lookup shadow) is clean. |
| GV-2 | Lee Sedol (9p) | Intuitive fighter | approve | Bold monolith deletion with 27+ file rewrites. Safety nets caught DEV-1 immediately. |
| GV-3 | Shin Jinseo (9p) | AI-era professional | approve | AI-Solve pipeline integrity verified. ai_solve → solution_tree dependency is clean. |
| GV-4 | Ke Jie (9p) | Strategic thinker | approve | 9-module domain mapping mirrors actual pipeline stages. CRB-2 worth monitoring. |
| GV-5 | Staff Engineer A | Systems architect | approve | Clean dependency DAG. DEV-1 fix robust. CRA-1 is pre-existing pattern. |
| GV-6 | Staff Engineer B | Data pipeline | approve | Cache pattern distributed correctly. 1894 tests / 0 failures definitive. |
| GV-7 | Hana Park (1p) | Player experience | approve | Zero player-facing impact. JSON configs untouched. |

### Required Changes (resolved)

| RC | Required Change | Status |
|----|----------------|--------|
| RC-1 | Stale docstring in generate_refutations.py "via config.py" → "via config package" | ✅ Resolved |

### Handover

| Field | Value |
|-------|-------|
| from_agent | Governance-Panel |
| to_agent | Plan-Executor |
| message | Implementation approved unanimously. All 8 ACs met. 1894 tests pass. RC-1 resolved. Proceed to closeout. |
| required_next_actions | 1. RC-1 fixed  2. Set governance_review to approved  3. Proceed to closeout |
| blocking_items | (none) |

---

## Gate 5: Closeout Audit

| Field | Value |
|-------|-------|
| decision | `approve` |
| status_code | `GOV-CLOSEOUT-APPROVED` |
| unanimous | true (7/7) |
| date | 2026-03-14 |

### Member Reviews

| review_id | member | domain | vote | supporting_comment |
|-----------|--------|--------|------|--------------------|
| GV-1 | Cho Chikun (9p) | Classical tsumego | approve | Zero puzzle-logic changes. Deterministic outcome. |
| GV-2 | Lee Sedol (9p) | Intuitive fighter | approve | Bold Q1=B decision executed cleanly. DEV-1 caught and fixed. |
| GV-3 | Shin Jinseo (9p) | AI-era professional | approve | AI-Solve pipeline integrity verified across all phases. |
| GV-4 | Ke Jie (9p) | Strategic thinker | approve | Textbook lifecycle execution with productive revision cycles. |
| GV-5 | Staff Engineer A | Systems architect | approve | Clean architecture, robust DEV-1 fix, status.json minor housekeeping. |
| GV-6 | Staff Engineer B | Data pipeline | approve | Pipeline unchanged. Cache distribution correct. 1894 tests definitive. |
| GV-7 | Hana Park (1p) | Player experience | approve | Zero player-facing impact. Internal tooling only. |

### Handover

| Field | Value |
|-------|-------|
| from_agent | Governance-Panel |
| to_agent | Plan-Executor |
| message | Closeout approved. Initiative complete. All 8 ACs met, 4 governance gates passed, 1894 tests green. |

---

## Gate 6: Implementation Re-Review (Post RC Fixes)

| Field | Value |
|-------|-------|
| decision | `pending` |
| status_code | `pending` |
| date | 2026-03-14 |

### RC Resolution Summary

| RC | Required Change | Source | File(s) | Status |
|----|----------------|-------|---------|--------|
| RC-1 | Fix `from config import DepthProfile` → `from config.solution_tree import DepthProfile` | CRA-1, GV-3, GV-5 | `analyzers/solve_position.py` L913 | ✅ Fixed |
| RC-2 | Expose `clear_teaching_cache()` in teaching.py; call from `clear_cache()` | CRB-1, GV-5 | `config/teaching.py`, `config/__init__.py` | ✅ Fixed |
| RC-3 | Remove dead import `from config.teaching import _cached_teaching_comments` | CRA-2 | `config/__init__.py` | ✅ Fixed (subsumed by RC-2) |

### Post-Fix Validation

| val_id | Command | Exit Code | Result | Status |
|--------|---------|-----------|--------|--------|
| VAL-10 | `pytest tests/ -x --ignore=golden5,calibration,ai_solve_calibration` | 0 | 1894 passed, 36 skipped | ✅ |

### Code Review Results

| reviewer | verdict | critical | major | minor |
|----------|---------|----------|-------|-------|
| CR-ALPHA-R2 | pass | 0 | 0 | 0 |
| CR-BETA-R2 | pass | 0 | 0 | 0 |

### Member Reviews

| review_id | member | domain | vote | supporting_comment |
|-----------|--------|--------|------|--------------------|
| GV-1 | Cho Chikun (9p) | Classical tsumego | approve | RC fixes are mechanical corrections, zero puzzle correctness impact. 1894 tests pass. |
| GV-2 | Lee Sedol (9p) | Intuitive fighter | approve | RC-2 encapsulation fix is the most meaningful — proper API boundary. Bold Q1=B validated across 6 gates with zero regressions. |
| GV-3 | Shin Jinseo (9p) | AI-era professional | approve | RC-1 addresses AI-Solve pipeline path. DepthProfile import now references domain owner. |
| GV-4 | Ke Jie (9p) | Strategic thinker | approve | 6 governance gates, 3 post-review RCs, zero behavioral changes. Proportionate fixes. |
| GV-5 | Staff Engineer A | Systems architect | approve | RC-2 respects ISP — clear_cache() delegates to teaching module API. AR-3 remains documented minor deviation. |
| GV-6 | Staff Engineer B | Data pipeline | approve | Pipeline unchanged. Cache clearing functionally identical. 1894 tests definitive. |
| GV-7 | Hana Park (1p) | Player experience | approve | Zero player-facing impact. Config JSON untouched. Teaching comments system maintained. |

### Decision

| Field | Value |
|-------|-------|
| decision | `approve` |
| status_code | `GOV-REVIEW-APPROVED` |
| unanimous | true (7/7) |
| date | 2026-03-14 |

### Handover

| Field | Value |
|-------|-------|
| from_agent | Governance-Panel |
| to_agent | Plan-Executor |
| message | Gate 6 re-review approved unanimously. All 3 RC fixes verified in source and by code reviewers (pass/0/0/0). 1894 tests pass. Initiative complete. |
| required_next_actions | 1. Set governance_review → approved 2. Set closeout → approved 3. Archive initiative |
| blocking_items | (none) |
| required_next_actions | 1. Finalize status.json  2. Archive initiative |
| blocking_items | (none) |
