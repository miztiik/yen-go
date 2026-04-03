# Governance Decisions

**Initiative**: `20260324-1900-feature-timed-puzzle-json-to-sql`
**Last Updated**: 2026-03-24

---

## Gate 1: Charter Review

**Date**: 2026-03-24
**Decision**: `approve_with_conditions`
**Status Code**: `GOV-CHARTER-CONDITIONAL`
**Unanimous**: Yes (10/10 approve)

### Member Reviews

| review_id | member | domain | vote | supporting_comment | evidence |
|-----------|--------|--------|------|--------------------|----------|
| GV-1 | Cho Chikun (9p) | Classical tsumego authority | approve | Clean structural deletion. Single-path dependency tree with clear root. Removing broken import is good hygiene. | 0 external consumers verified for all 7 files |
| GV-2 | Lee Sedol (9p) | Intuitive fighter | approve | Chain is conclusively dead. All paths lead to same verdict: delete. Good instinct to include `dailyPath.ts`. | `dailyPath.ts` sole consumer is dead; confidence 90 justified |
| GV-3 | Shin Jinseo (9p) | AI-era professional | approve | Latent crash has zero benefit. Charter scope is tight. TS compiler + vitest provide strong verification. | AC-5 + AC-6 provide automated verification |
| GV-4 | Ke Jie (9p) | Strategic thinker | approve | Zero learning value. Deleting removes confusion for future developers. | Non-Goals protect active types; SQLite untouched |
| GV-5 | Principal Staff Engineer A | Systems architect | approve | Strong architectural awareness. Two minor gaps: stale CDN comments, E3 hedging language. | status.json decisions align; Q5-ANALYSIS proves SQLite-based |
| GV-6 | Principal Staff Engineer B | Data pipeline engineer | approve | Daily JSON architecture fully superseded by SQLite tables. VIEW_PATHS should be checked. | Charter references correct DB-1 architecture |
| GV-7 | Hana Park (1p) | Player experience | approve | Dead code only — no player-visible behavior changes. Latent crash removal prevents future regression. | 0 active call sites; daily challenge flow unaffected |
| GV-8 | Mika Chen | DevTools UX | approve | No developer tooling component. AGENTS.md is documentation maintenance. | Dispatch skipped per protocol |
| GV-9 | Dr. David Wu | KataGo engine | approve | No KataGo/enrichment component. | Dispatch skipped per protocol |
| GV-10 | Dr. Shin Jinseo | Tsumego correctness | approve | No puzzle correctness changes. Charter protects puzzle data flow. | Non-Goals confirm no SQLite/classification changes |

### Required Changes (Conditions)

| RC-id | Source | Requirement | Target | Severity | Resolution |
|-------|--------|-------------|--------|----------|------------|
| RC-1 | CON-1/GV-5 | Add stale CDN comment cleanup in `loader.ts:35,40` to scope | `00-charter.md` E5 | minor | ✅ addressed — E5 added |
| RC-2 | CON-2/GV-5 | Resolve E3 ambiguity: commit or defer `CollectionSummary.path` removal | `00-charter.md` E3 | minor | ✅ addressed — committed to removal (0 consumers verified) |
| RC-3 | CON-3/GV-6 | Verify `VIEW_PATHS` orphan status post-deletion | `00-charter.md` E1 | minor | ✅ addressed — NOT orphaned (`pagination.ts` → `usePaginatedPuzzles.ts` active) |

### Handover

- **from_agent**: Governance-Panel
- **to_agent**: Feature-Planner
- **decision**: approve_with_conditions
- **status_code**: GOV-CHARTER-CONDITIONAL
- **message**: Charter approved with 3 minor conditions. All 3 resolved in charter update.
- **blocking_items**: none
- **re_review_requested**: false

---

## Gate 2: Options Election

**Date**: 2026-03-24
**Decision**: `approve`
**Status Code**: `GOV-OPTIONS-APPROVED`
**Unanimous**: Yes (3/3 approve OPT-1)

### Selected Option

| Field | Value |
|-------|-------|
| option_id | OPT-1 |
| title | Single-Commit Deletion |
| selection_rationale | All 7 files have 0 active consumers. Edits are mechanical. Phasing adds overhead with no risk reduction. Single commit = single revert = cleanest rollback. Aligns with dead code policy. |
| must_hold_constraints | 1. `tsc --noEmit` passes. 2. `vitest run` passes with 0 new failures. 3. Selective `git add` only. 4. AGENTS.md updated in same commit. |

### Member Reviews

| review_id | member | domain | vote | supporting_comment | evidence |
|-----------|--------|--------|------|--------------------|----------|
| GV-11 | Architect | Structure/Dependencies | OPT-1 | 0-consumer files need no phasing. Single atomic commit preserves bisectability. | Charter confirms exhaustive grep verification |
| GV-12 | Frontend Lead | TypeScript/Vitest | OPT-1 | Trivial edits won't cause TS cascading failures. Phasing buys nothing when intermediate state is worse. | Edits are removal-only; no new code |
| GV-13 | Release Engineer | Git/Rollback | OPT-1 | One commit = `git revert HEAD`. For ~1,670 lines of pure deletion, single-commit is standard. | Rollback complexity lower with OPT-1 |

### Handover

- **from_agent**: Governance-Panel
- **to_agent**: Feature-Planner
- **decision**: approve
- **status_code**: GOV-OPTIONS-APPROVED
- **message**: OPT-1 approved. Delete D1-D7, edit E1-E5, update AGENTS.md in single commit. Verify with `tsc --noEmit` + `vitest run`.
- **blocking_items**: none

---

## Gate 3: Plan Review

**Date**: 2026-03-24
**Decision**: `approve_with_conditions`
**Status Code**: `GOV-PLAN-CONDITIONAL`

### Member Reviews

| review_id | member | domain | vote | supporting_comment | evidence |
|-----------|--------|--------|------|--------------------|----------|
| GV-14 | Architect | Structure/Dependencies | conditional approve | E1/T8 would break tsc — 6 of 8 "orphan" types are field types within active `DailyIndex`. Shrink to 2 orphan functions only. | `DailyIndex` imported by `dailyChallengeService.ts`, `DailyPuzzleLoader.ts`, `DailyChallengeModal.tsx` |
| GV-15 | Integrity Reviewer | File verification | conditional approve | D7 path incorrect (`app.tsx.new` doesn't exist); E2/T10 misses `views/by-collection/` at line 405 | `SolutionTreeView.tsx.new` is the only `.tsx.new` file |
| GV-16 | Safety Reviewer | Risk assessment | approve | D1-D6 verified safe. E3/T9 confirmed: `CollectionSummary.path` never read. Verification plan sufficient. | 0-consumer chains closed |

### Conditions

| PC-id | Source | Requirement | Status |
|-------|--------|-------------|--------|
| PC-1 | GV-14 | Shrink E1/T8 to only `isDailyIndexV2` and `isTimedV2` (2 functions). Keep all 6 interface types. | ✅ addressed |
| PC-2 | GV-15 | Fix D7: drop from scope (`app.tsx.new` doesn't exist) | ✅ addressed |
| PC-3 | GV-15 | Extend E2/T10: add `views/by-collection/` path string (~line 405) | ✅ addressed |

### Handover

- **from_agent**: Governance-Panel
- **to_agent**: Plan-Executor
- **decision**: approve_with_conditions (all conditions addressed)
- **status_code**: GOV-PLAN-CONDITIONAL
- **message**: Plan approved. All 3 conditions resolved. Execution order: Deletions (D1-D6) → Edits (E1-E5) → Verify (`tsc --noEmit` → `vitest run` → grep) → Commit. Do NOT commit if verification fails.
- **blocking_items**: none

---

## Gate 4: Implementation Review

**Date**: 2026-03-24
**Decision**: `approve`
**Status Code**: `GOV-REVIEW-APPROVED`
**Unanimous**: Yes (10/10 approve)

### Member Reviews

| review_id | member | domain | vote | supporting_comment | evidence |
|-----------|--------|--------|------|--------------------|----------|
| GV-17 | Cho Chikun (9p) | Classical tsumego | approve | Clean structural excision. Dependency tree verified. No puzzle logic touched. | 6/6 files absent; dailyChallengeService unaffected |
| GV-18 | Lee Sedol (9p) | Intuitive fighter | approve | Dead code chain definitively dead. Good instinct to keep structurally-required types. | DD-3 validated by tsc pass |
| GV-19 | Shin Jinseo (9p) | AI-era professional | approve | Verification gates provide strong automated proof. Zero human judgment required. | VAL-1, VAL-2, VAL-3 pass |
| GV-20 | Ke Jie (9p) | Strategic thinker | approve | ~1,170 lines removed reduces confusion. No learning value lost. | Non-Goals protect active SQLite paths |
| GV-21 | Staff Engineer A | Systems architect | approve | 0 deviations from plan. All ripple-effects verified. Minor: 4 stale JSDoc comments remain (CRA-1, Level 0). | 50-execution-log, 60-validation-report |
| GV-22 | Staff Engineer B | Pipeline engineer | approve | VIEW_PATHS preserved. CollectionPuzzleEntry.path preserved. | IMP-3, IMP-8 verified |
| GV-23 | Hana Park (1p) | Player experience | approve | No player-visible change. Latent crash removal improves stability. | AC-5, IMP-5, IMP-7 |
| GV-24 | Mika Chen | DevTools UX | approve | No tooling component. | Dispatch skipped |
| GV-25 | Dr. David Wu | KataGo | approve | No enrichment component. | Dispatch skipped |
| GV-26 | Dr. Shin Jinseo | Tsumego correctness | approve | No correctness changes. | Non-Goals explicit |

### Minor Follow-Up (Non-Blocking)

| FU-id | item | severity |
|-------|------|----------|
| FU-1 | Remove stale JSDoc refs to `views/by-level/`, `views/by-tag/` in `collectionService.ts` | Level 0 |

### Handover

- **from_agent**: Governance-Panel
- **to_agent**: Plan-Executor
- **decision**: approve
- **status_code**: GOV-REVIEW-APPROVED
- **message**: Implementation approved. All 7 ACs met, 0 deviations. Proceed to closeout.
- **blocking_items**: none

---

## Gate 5: Closeout Audit

**Date**: 2026-03-24
**Decision**: `approve`
**Status Code**: `GOV-CLOSEOUT-APPROVED`
**Unanimous**: Yes (10/10 approve)

### Closeout Checks

| CL-id | check | result |
|-------|-------|--------|
| CL-1 | Artifact path exists | ✅ |
| CL-2 | Closure artifacts current | ✅ |
| CL-3 | All gates recorded (4/4) | ✅ |
| CL-4 | Scope evidence verified | ✅ |
| CL-5 | Test evidence verified | ✅ |
| CL-6 | Docs evidence verified | ✅ |
| CL-7 | Governance trail complete | ✅ |
| CL-8 | Decisions in status.json | ✅ |
| CL-9 | Docs "why" quality | ✅ |
| CL-10 | Cross-references | ✅ |
| CL-11 | Update-first policy | ✅ |
| CL-12 | No unresolved blockers | ✅ |
| CL-13 | Ripple-effects closure (8/8) | ✅ |

### Handover

- **from_agent**: Governance-Panel
- **to_agent**: Plan-Executor
- **decision**: approve
- **status_code**: GOV-CLOSEOUT-APPROVED
- **message**: Initiative closed. All 5 lifecycle gates passed. FU-1 (stale JSDoc) is Level 0 non-blocking.
- **blocking_items**: none
