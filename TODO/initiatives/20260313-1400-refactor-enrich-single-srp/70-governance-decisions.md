# Governance Decisions

**Initiative ID:** 20260313-1400-refactor-enrich-single-srp  
**Last Updated:** 2026-03-13

---

## Charter Review — Round 1

**Decision:** `change_requested`  
**Status Code:** `GOV-CHARTER-REVISE`

### Required Changes

| rc_id | requirement | status |
|-------|-------------|--------|
| RC-1 | Add "Prior Art" section referencing `2026-03-07-refactor-enrich-single-decomposition` | ✅ addressed |
| RC-2 | Clarify success criterion #2 vs Q9:B consistency | ✅ addressed |
| RC-3 | Update `status.json` decisions (stale "pending" values) | ✅ addressed |
| RC-4 | Add `planning_confidence_score` and `risk_level` to `status.json` | ✅ addressed |
| RC-5 | Remove false `filelock` claim from `15-research.md` | ✅ addressed |
| RC-6 | Fix line count (~1,735 → ~1,726) in `00-charter.md` | ✅ addressed |

### Panel Support Table

| review_id | member | domain | vote | supporting_comment |
|-----------|--------|--------|------|--------------------|
| GV-1 | Cho Chikun (9p) | Classical tsumego | concern | Prior initiative not referenced — need scope delta context |
| GV-2 | Lee Sedol (9p) | Intuitive fighter | approve | Scope and research quality sufficient |
| GV-3 | Shin Jinseo (9p) | AI-era professional | approve | KataGo boundary correctly handled |
| GV-4 | Ke Jie (9p) | Strategic thinker | concern | Success criterion #2 vs Q9:B tension |
| GV-5 | Principal Staff Engineer A | Systems architect | change_requested | status.json stale, prior art missing, false evidence |
| GV-6 | Principal Staff Engineer B | Data pipeline | change_requested | Line count, confidence fields, prior context needed |

---

## Charter Review — Round 2 (Re-submission)

**Decision:** `approve`  
**Status Code:** `GOV-CHARTER-APPROVED`  
**Unanimous:** Yes (6/6 approve)

All 6 required changes from Round 1 verified against source artifacts. Charter, research, and clarifications form a complete, internally consistent artifact set. Scope is explicit, research is evidence-based, and the tools→backend import prohibition is correctly navigated via Protocol ABCs.

### Handover
- **From:** Governance-Panel → Feature-Planner
- **Message:** Proceed to options drafting. Draft 2-3 decomposition strategy options.
- **Blocking items:** None

---

## Options Review

**Decision:** `approve_with_conditions`  
**Status Code:** `GOV-OPTIONS-CONDITIONAL`  
**Selected Option:** OPT-1 (Stage Runner Pattern)  
**Unanimous:** No (5 approve, 1 concern — Ke Jie: runner complexity if merger deferred)

### Selection Rationale
OPT-1 is the only option fully aligned with binding decisions Q7:A (auto-wrap) and Q8:A (declarative error policy). Best SRP, DRY (zero boilerplate), and backend merger readiness. Pattern proven in backend's `StageExecutor`.

### Required Changes for Plan
| rc_id | requirement |
|-------|-------------|
| RC-1 | Plan must include "Runner Sunset Criteria" subsection |
| RC-2 | Plan must document PipelineContext field ownership table |

### Must-Hold Constraints
1. PipelineContext fields: typed annotations only — no `dict[str, Any]` catch-all
2. Field ownership table in plan
3. Runner sunset criteria documented
4. All changes confined to `tools/puzzle-enrichment-lab/`
5. Existing tests pass unchanged

---

## Plan Review

**Decision:** `approve_with_conditions`  
**Status Code:** `GOV-PLAN-CONDITIONAL`  
**Unanimous:** No (3 approve, 3 concern — all concerns mapped to RCs)

---

## Implementation Review

**Decision:** `approve_with_conditions`  
**Status Code:** `GOV-REVIEW-CONDITIONAL`  
**Date:** 2026-03-13  
**Unanimous:** No (4 approve, 2 concern — all concerns mapped to RCs)

### Required Changes (Resolved)

| rc_id | requirement | status |
|-------|-------------|--------|
| RC-1 | Fix line count in execution/validation artifacts (actual 254, not 224) | ✅ fixed |
| RC-2 | Replace `Any` with proper TYPE_CHECKING annotations on PipelineContext | ✅ fixed — 12 fields now properly typed |

### Evidence
- 993 passed, 35 skipped, 0 failures
- enrich_single.py: 254 lines (1,642 before)
- 12 new stage modules properly extracting all pipeline logic
- PipelineContext fields now fully typed (no `Any` for field annotations)

### Panel Support Table

| review_id | member | domain | vote | supporting_comment | evidence |
|-----------|--------|--------|------|--------------------|----------|
| GV-1 | Cho Chikun (9p) | Classical tsumego | concern | `metadata: dict` violates Must-Hold #1 typing constraint. TypedDict resolves. | Field Ownership Table; source line 282 |
| GV-2 | Lee Sedol (9p) | Intuitive fighter | approve | 3-path dispatch stays in orchestrator correctly. 8 stage extractions genuinely independent. Solve paths cleanest extraction at 445 lines. | Research §2.2 R-6 |
| GV-3 | Shin Jinseo (9p) | AI-era professional | approve | KataGo boundary cleanly handled. engine_manager as immutable PipelineContext field. ErrorPolicy split (FAIL_FAST/DEGRADE) appropriate per stage. | Field Ownership Table + T7-T9 |
| GV-4 | Ke Jie (9p) | Strategic thinker | concern | Runner Sunset Criteria pragmatically sound. But `metadata: dict` creates maintenance risk. TypedDict is minimal viable fix. | Plan §Sunset; source lines 298-302 |
| GV-5 | PSE-A | Systems architect | concern | 3 documentation gaps: metadata type, calibration script, naming convention. All conditions-level, not blockers. | Grep: scripts/run_calibration.py:41; Plan §1c vs §2b |
| GV-6 | PSE-B | Data pipeline | approve | StageRunner auto-wrapping fixes 2 timing anomalies. Timings runner-managed not PipelineContext field. metadata typing concern valid but addressable as RC. | Research §3.2 timing anomalies |

### Required Changes (All Addressed)

| rc_id | requirement | status |
|-------|-------------|--------|
| RC-1 | `metadata` field must use `SgfMetadata` TypedDict in PipelineContext (not bare `dict`) — update Field Ownership Table and T2 scope | ✅ addressed |
| RC-2 | Add `scripts/run_calibration.py` as R15 in ripple effects table | ✅ addressed |
| RC-3 | T6 must specify naming convention (drop underscore prefix for solve path functions); T14 must include function name updates in test files | ✅ addressed |

### Support Summary

Plan is architecturally sound and internally consistent across 8 artifacts. All 9 charter goals mapped to task IDs. Confidence 85 (above 80 floor). Stage Runner is correct choice for Q7:A and Q8:A. 4-phase execution with 19 tasks is thorough. Field ownership (25 rows) and Runner Sunset Criteria address prior Options governance conditions. Three RCs addressed in artifact updates without plan direction change.

### Handover

- **From:** Governance-Panel
- **To:** Plan-Executor
- **Message:** Plan approved with conditions. All 3 RCs addressed in artifacts. Proceed to executor handoff. Update status.json phases to reflect completion.
- **Required next actions:** Update status.json → handoff to Plan-Executor
- **Blocking items:** None (all RCs resolved)

---

## Closeout Audit

**Decision:** `approve_with_conditions`  
**Status Code:** `GOV-CLOSEOUT-CONDITIONAL`  
**Date:** 2026-03-13  
**Unanimous:** Yes (6/6 approve)

### Required Changes (Resolved)

| rc_id | requirement | status |
|-------|-------------|--------|
| RC-1 | Update README.md "~150 lines" to "~250 lines" (2 occurrences) | ✅ fixed |
| RC-2 | Update status.json to mark all phases approved including closeout | ✅ fixed |

### Panel Assessment
Initiative achieved its primary objective: decomposing a 1,642-line God function into 12 focused modules (254-line orchestrator + 1,697 lines across stages + 148-line result builders). All 4 governance gates passed. Test evidence comprehensive (993 passed, 0 failures). Documentation quality strong. Residual tech debt: backward-compat re-exports (DEV-2), curated_wrongs bare generic — both minor and tracked.
