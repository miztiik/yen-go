# Governance Decisions — Browse Filter & Navigation Fix

**Initiative:** `20260312-1600-feature-browse-filter-navigation-fix`  
**Last Updated:** 2026-03-12

---

## Gate 1: Charter Preflight

**Date:** 2026-03-12  
**Decision:** `approve_with_conditions`  
**Status Code:** `GOV-CHARTER-CONDITIONAL`

### Panel Member Reviews

| review_id | member | domain | vote | supporting_comment | evidence |
|-----------|--------|--------|------|--------------------|----------|
| GV-1 | Cho Chikun (9p) | Classical tsumego authority | approve | Back-button bug (I-1) violates clean user flow through curated puzzles. Scope focused on broken paths; speculative enhancements correctly deferred. | E-1 confirmed: `handleBackToHome` → `{type:'home'}` at app.tsx L244 |
| GV-2 | Lee Sedol (9p) | Intuitive fighter | approve | "Counts or removed" framing (Goal 6) gives healthy ambiguity for options. Q7 agent-resolved as "include counts" may pre-constrain — carry both paths into options. | Goal 6 vs Q7 slight inconsistency noted; non-blocking |
| GV-3 | Shin Jinseo (9p) | AI-era professional | approve | Technical evidence systematically gathered and verified. useCanonicalUrl only handles numeric context-route params; options must address browse-page string params. | useCanonicalUrl.ts CanonicalFilters: numeric arrays only |
| GV-4 | Ke Jie (9p) | Strategic thinker | approve | DDK journey friction analysis compelling. Deferring I-7 (new CollectionsPage filters) is wise. | Research §5/§6 persona friction maps |
| GV-5 | Principal Staff Engineer A | Systems architect | concern | Charter well-structured. Two issues: (1) status.json phase tracking inconsistency, (2) constraint mentioning useCanonicalUrl misleading for browse pages. | status.json `charter: "in_progress"` during review; canonicalUrl.ts L20 |
| GV-6 | Principal Staff Engineer B | Data pipeline engineer | approve | Frontend-only, no pipeline impact. URL param collision analysis sound. Test coverage adequate. | routes.ts parseRoute: distinct browse vs context matching |

### Required Changes (from RC)

| RC-id | Required Change | Status |
|-------|----------------|--------|
| RC-1 | Update status.json charter phase to reflect actual state | ✅ Applied — set to `"approved"` |
| RC-2 | Add "Design Decisions for Options Phase" section to charter noting browse-page URL-sync is open question | ✅ Applied — section added to 00-charter.md |

### Handover

| Field | Value |
|-------|-------|
| from_agent | Governance-Panel |
| to_agent | Feature-Planner |
| message | Charter approved with two minor conditions (both applied). Proceed to options: evaluate browse-page URL-sync approaches and CTF counts vs removal. |
| required_next_actions | 1. Draft 25-options.md with ≥2 approaches. 2. Return for options governance. |
| blocking_items | None |

---

## Gate 2: Options Election

**Date:** 2026-03-12  
**Decision:** `approve`  
**Status Code:** `GOV-OPTIONS-APPROVED`  
**Selected Option:** A — `useBrowseParams` Hook

### Panel Member Reviews

| review_id | member | domain | vote | key_point |
|-----------|--------|--------|------|-----------|
| GV-1 | Cho Chikun (9p) | Classical tsumego authority | approve | Deterministic URL-state binding matches single-correct-answer pedagogy |
| GV-2 | Lee Sedol (9p) | Intuitive fighter | approve | DRY flexibility without over-engineering; CTF removal convergence sound |
| GV-3 | Shin Jinseo (9p) | AI-era professional | approve | String vs numeric param separation is fundamentally correct |
| GV-4 | Ke Jie (9p) | Strategic thinker | approve | Practical SDK/DDK journey improvement without context-page regression risk |
| GV-5 | Principal Staff Eng A | Systems architect | approve | Best isolation/testability/rollback; RC-1 popstate guard required |
| GV-6 | Principal Staff Eng B | Data pipeline engineer | approve | Performance neutral; observability improved; CTF removal verified safe |

### Required Changes

| RC-id | Required Change | Status |
|-------|----------------|--------|
| RC-1 | `useBrowseParams` popstate listener MUST guard against path changes — only re-read params when pathname unchanged. Unit test required. | ⏳ Pending — to be incorporated in plan |

### Selection Rationale

Unanimous approval (6/6). Best isolation/DRY balance. 3 immediate consumers justify abstraction. Zero routing infrastructure changes. Low regression risk. Single-branch rollback. Established hook pattern (14 existing hooks).

### Must-Hold Constraints

1. `useBrowseParams` must NOT modify or depend on `useCanonicalUrl`/`Route`/`parseRoute`/`serializeRoute`
2. `popstate` listener must guard against path changes (RC-1)
3. `ContentTypeFilter` removed from all 3 browse pages; component file retained
4. Existing `/contexts/` URLs must remain functional
5. Hook file placed in `frontend/src/hooks/useBrowseParams.ts`
6. Dead code policy: removed CTF imports from browse pages

### Handover

| Field | Value |
|-------|-------|
| from_agent | Governance-Panel |
| to_agent | Feature-Planner |
| message | Option A approved unanimously. Proceed to analysis + plan + tasks. Plan MUST incorporate RC-1 popstate path guard. |
| required_next_actions | 1. Update status.json option_selection 2. Draft 20-analysis.md 3. Draft 30-plan.md 4. Draft 40-tasks.md 5. Return for plan governance |
| blocking_items | None |

---

## Gate 3: Plan Review (Round 1)

**Date:** 2026-03-12  
**Mode:** `plan`  
**Decision:** `change_requested`  
**Status Code:** `GOV-PLAN-REVISE`  
**Unanimous:** Yes (6/6)

### Critical Finding: Dual-Hook URL Write Conflict

Both `useCanonicalUrl` and the planned `useBrowseParams` replace the **entire** URL search string via `history.replaceState`. On TechniqueFocusPage and TrainingSelectionPage (where both hooks coexist), changing a level filter would erase the category param and vice versa — the exact bug the initiative aims to fix.

**Evidence:** `buildSearchString` (useCanonicalUrl.ts L116-140) creates a new `URLSearchParams` from only canonical keys, discarding all others. `writeToUrl` (L218-235) replaces full URL search string with this output.

### Required Changes

| RC-id | Required Change | Status |
|-------|----------------|--------|
| RC-2 | `useBrowseParams` must use read-merge-write URL pattern | ✅ applied to 30-plan.md + 40-tasks.md T3 |
| RC-3 | `useCanonicalUrl.writeToUrl` must preserve unmanaged params | ✅ applied: T4b added to 40-tasks.md |
| RC-4 | Update analysis F-4 to acknowledge conflict + resolution | ✅ applied to 20-analysis.md |
| RC-5 | T9 must include dual-hook integration test | ✅ applied to 40-tasks.md T9 |
| RC-6 | Plan file list: add `useCanonicalUrl.ts` as 7th file | ✅ applied to 30-plan.md |

### Panel Reviews

| review_id | member | domain | vote |
|-----------|--------|--------|------|
| GV-1 | Cho Chikun (9p) | Classical tsumego authority | change_requested |
| GV-2 | Lee Sedol (9p) | Intuitive fighter | change_requested |
| GV-3 | Shin Jinseo (9p) | AI-era professional | change_requested |
| GV-4 | Ke Jie (9p) | Strategic thinker | change_requested |
| GV-5 | Principal Staff Engineer A | Systems architect | change_requested |
| GV-6 | Principal Staff Engineer B | Data pipeline engineer | change_requested |

## Gate 3: Plan Review (Round 2 — Re-review)

**Date:** 2026-03-12  
**Mode:** `plan`  
**Decision:** `approve`  
**Status Code:** `GOV-PLAN-APPROVED`  
**Unanimous:** Yes (6/6)

### RC Verification

All 5 required changes from Round 1 verified as fully applied:

| RC-id | Verified | Evidence |
|-------|----------|----------|
| RC-2 | ✅ | T3 spec: read-merge-write pattern in `setParam()` and `clearParams()` |
| RC-3 | ✅ | T4b: `buildSearchString` starts from `window.location.search`, ~5-line change |
| RC-4 | ✅ | F-4 severity upgraded to Medium (corrected) with full conflict narrative |
| RC-5 | ✅ | T9: 4 dual-hook integration/RMW test scenarios |
| RC-6 | ✅ | 30-plan.md §6 added, rollback updated to 6 files, risk escalated to Medium |

### Panel Reviews

| review_id | member | domain | vote | supporting_comment |
|-----------|--------|--------|------|--------------------|
| GV-1 | Cho Chikun (9p) | Classical tsumego authority | approve | RMW ensures both difficulty and category preserved on back/forward navigation |
| GV-2 | Lee Sedol (9p) | Intuitive fighter | approve | Hooks keep clear territory; T4b is surgically precise (~5 lines) |
| GV-3 | Shin Jinseo (9p) | AI-era professional | approve | Single-threaded JS eliminates race conditions between hooks |
| GV-4 | Ke Jie (9p) | Strategic thinker | approve | Phase 3 correctly gated on both T3 and T4b |
| GV-5 | Principal Staff Engineer A | Systems architect | approve | No architecture debt; rollback correctly accounts for 6 files |
| GV-6 | Principal Staff Engineer B | Data pipeline engineer | approve | Frontend-only, zero pipeline impact; RMW is idempotent |

### Handover

| Field | Value |
|-------|-------|
| from_agent | Governance-Panel |
| to_agent | Plan-Executor |
| decision | approve |
| status_code | GOV-PLAN-APPROVED |
| message | Plan approved unanimously on Round 2 re-review. All 5 RCs verified. Execute 12 active tasks (T1, T3, T4, T4b, T5-T12) in 6 phases. T4b must complete before Phase 3 page refactors. T9 dual-hook integration tests mandatory before merge. |
| required_next_actions | 1. Update status.json. 2. Execute Phases 1-6. 3. Return for Gate 4 review. |
| blocking_items | None |

---

> **See also**:
> - [00-charter.md](./00-charter.md) — Feature scope
> - [25-options.md](./25-options.md) — Options and selection rationale

---

## Gate 4: Implementation Review

**Date:** 2026-03-13  
**Mode:** `review`  
**Decision:** `approve`  
**Status Code:** `GOV-REVIEW-APPROVED`  
**Unanimous:** Yes (6/6)

### Evidence Summary

| gate_check | status | evidence |
|------------|--------|----------|
| All 12 tasks completed | ✅ | EX-10 through EX-21, all ✅ in 50-execution-log.md |
| 0 deviations from plan | ✅ | No scope expansion, no task modifications |
| TypeScript compilation | ✅ | 0 errors across all 7 modified/created source files |
| Test suite | ✅ | 82 files, 1373 tests, 0 failures (VAL-1/VAL-2) |
| New tests | ✅ | 12 hook tests + 7 route tests (56 total new assertions) |
| Dead code cleanup | ✅ | No stale ContentTypeFilter imports, no [DEBUG] statements (VAL-15/VAL-17) |
| Documentation | ✅ | docs/concepts/browse-url-params.md created, frontend/CLAUDE.md updated |
| Backward compatibility | ✅ | Existing /contexts/ URLs work (AC-11 regression test) |
| Ripple-effects | ✅ | VAL-18 through VAL-22 all verified, 0 mismatches |

### Panel Member Reviews

| review_id | member | domain | vote | supporting_comment | evidence |
|-----------|--------|--------|------|--------------------|----------|
| GV-1 | Cho Chikun (9p) | Classical tsumego authority | approve | Back-button deterministically returns to browse context. Filter state persists. Default category fix removes surprising hidden-puzzle behavior. | AC-1 onBack → collections-browse; AC-7 default cat:'all'; VAL-4/VAL-6 |
| GV-2 | Lee Sedol (9p) | Intuitive fighter | approve | Read-merge-write is elegant for dual-hook coexistence. clearParams preserving unmanaged keys is defensively correct. | RC-2/RC-3 verified; RC-5 dual-hook tests |
| GV-3 | Shin Jinseo (9p) | AI-era professional | approve | Pathname guard (RC-1) prevents cross-page leakage. defaultsRef prevents stale closures. No race conditions. | useBrowseParams.ts pathname guard + dual-hook test |
| GV-4 | Ke Jie (9p) | Strategic thinker | approve | DDK/SDK browsing journey improved. ContentTypeFilter removal eliminates misleading UI. All 12 ACs verified. | AC-2 through AC-11 via validation report |
| GV-5 | Principal Staff Engineer A | Systems architect | approve | useBrowseParams fully isolated from routing/canonical systems. RMW prevents dual-write clobbering. No architecture debt. | 0 imports from routes.ts; RMW with canonical key ordering |
| GV-6 | Principal Staff Engineer B | Data pipeline engineer | approve | Frontend-only, zero pipeline impact. Test coverage adequate. Documentation follows update-first policy. | 1373 tests, 0 failures; browse-url-params.md |

### RC Verification from Previous Gates

All required changes from Gates 1-3 verified in implementation:

| RC-id | Gate | Verified | Evidence |
|-------|------|----------|----------|
| RC-1 (Gate 2) | Options | ✅ | Popstate pathname guard in useBrowseParams.ts + unit tests |
| RC-2 (Gate 3) | Plan R1 | ✅ | useBrowseParams read-merge-write in setParam/clearParams |
| RC-3 (Gate 3) | Plan R1 | ✅ | useCanonicalUrl.buildSearchString starts from window.location.search |
| RC-4 (Gate 3) | Plan R1 | ✅ | Analysis F-4 updated with conflict narrative |
| RC-5 (Gate 3) | Plan R1 | ✅ | Dual-hook integration tests in useBrowseParams.test.ts |
| RC-6 (Gate 3) | Plan R1 | ✅ | useCanonicalUrl.ts in plan file list + rollback scope |

### Handover

| Field | Value |
|-------|-------|
| from_agent | Governance-Panel |
| to_agent | Plan-Executor |
| decision | approve |
| status_code | GOV-REVIEW-APPROVED |
| message | Implementation review approved unanimously. All 12 tasks completed, all 12 ACs verified, 1373 tests pass, 0 regressions. Proceed to closeout audit. |
| required_next_actions | 1. Update status.json 2. Return for closeout governance audit |
| blocking_items | None |

---

## Gate 5: Closeout Audit

**Date:** 2026-03-13  
**Mode:** `closeout`  
**Decision:** `approve`  
**Status Code:** `GOV-CLOSEOUT-APPROVED`  
**Unanimous:** Yes (6/6)

### Closeout Checks

| check | status | evidence |
|-------|--------|----------|
| All phases approved | ✅ | status.json phase_state all `approved` |
| 50-execution-log.md complete | ✅ | EX-1 through EX-21, all ✅, 0 deviations |
| 60-validation-report.md complete | ✅ | VAL-1 through VAL-33, all ✅ |
| 70-governance-decisions.md complete | ✅ | Gates 1–4 recorded with member reviews and RCs |
| Lifecycle RCs all verified | ✅ | 8 issued across Gates 1-3, all 8 verified in implementation |
| Documentation rationale quality | ✅ | WHY rationale documented for RMW, pathname guard, shorthands, CTF removal |
| Cross-references present | ✅ | browse-url-params.md has See also section |
| No residual risks | ✅ | All risks addressed; pre-existing TS errors out of scope |

### Panel Member Reviews

| review_id | member | domain | vote | supporting_comment |
|-----------|--------|--------|------|--------------------|
| GV-1 | Cho Chikun (9p) | Classical tsumego authority | approve | Clean closure — puzzle navigation determinism fully restored |
| GV-2 | Lee Sedol (9p) | Intuitive fighter | approve | RMW resolution well-documented with full rationale chain |
| GV-3 | Shin Jinseo (9p) | AI-era professional | approve | Technical evidence chain complete; 19 new tests provide strong regression coverage |
| GV-4 | Ke Jie (9p) | Strategic thinker | approve | DDK/SDK journey improvement delivered as chartered; non-goals deferred |
| GV-5 | Principal Staff Engineer A | Systems architect | approve | 5 gates, 8 RCs verified, 0 deviations. Documentation follows update-first policy |
| GV-6 | Principal Staff Engineer B | Data pipeline engineer | approve | Zero pipeline impact. 1373 tests, 0 regressions. Ripple-effects all green |

### Lifecycle Reconciliation

| gate | mode | decision | status_code | unanimous | RCs_issued | RCs_verified |
|------|------|----------|-------------|-----------|------------|-------------|
| 1 | charter | approve_with_conditions | GOV-CHARTER-CONDITIONAL | No (1 concern) | 2 | 2 ✅ |
| 2 | options | approve | GOV-OPTIONS-APPROVED | Yes (6/6) | 1 | 1 ✅ |
| 3 R1 | plan | change_requested | GOV-PLAN-REVISE | Yes (6/6) | 5 | 5 ✅ |
| 3 R2 | plan | approve | GOV-PLAN-APPROVED | Yes (6/6) | 0 | — |
| 4 | review | approve | GOV-REVIEW-APPROVED | Yes (6/6) | 0 | — |
| 5 | closeout | approve | GOV-CLOSEOUT-APPROVED | Yes (6/6) | 0 | — |

**Total RCs: 8 issued, 8 verified ✅**

### Handover

| Field | Value |
|-------|-------|
| from_agent | Governance-Panel |
| to_agent | Plan-Executor (final) |
| decision | approve |
| status_code | GOV-CLOSEOUT-APPROVED |
| message | Initiative formally closed. All 5 lifecycle gates passed. |
| required_next_actions | Update status.json closeout to approved |
| blocking_items | None |
