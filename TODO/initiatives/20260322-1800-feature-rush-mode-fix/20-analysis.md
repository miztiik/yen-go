# Analysis — Rush Mode Fix

**Initiative**: `20260322-1800-feature-rush-mode-fix`
**Last Updated**: 2026-03-22

---

## Planning Metrics

| Metric | Value |
|--------|-------|
| `planning_confidence_score` | 80 (pre-research) → 90 (post-research) |
| `risk_level` | medium |
| `research_invoked` | true |

---

## 1. Cross-Artifact Consistency

| finding_id | check | result | notes |
|------------|-------|--------|-------|
| F1 | Charter goals → tasks coverage | ✅ pass | All 8 goals map to tasks. See AC traceability in 40-tasks.md. |
| F2 | Every AC has ≥1 task | ✅ pass | AC-1 through AC-11 each trace to specific tasks. |
| F3 | Tasks → plan alignment | ✅ pass | Phase A tasks T1-T6 match plan DA-1 through DA-6. Phase B tasks T7-T19 match DB-1 through DB-8. |
| F4 | Clarification decisions → plan | ✅ pass | Q1:A→T5 (remove getBestScore), Q2:A→T7 (maxAttempts=1), Q3:A→T15 (audio), Q4:A→T14 (filters), Q5:B→T1-T6 (extract), Q6:A→T7 (shared prop), Q7:A→T17 (fix paths) |
| F5 | Options selected → plan derived | ✅ pass | Plan explicitly states "Selected Option: OPT-1". Two-phase structure matches. |
| F6 | Governance must-hold constraints → tasks | ✅ pass | Constraint 1 (Phase A zero change) → T6. Constraint 2 (maxAttempts) → T7. Constraint 3 (Random 3-retry) → T18. Constraint 4 (no new deps) → verified. Constraint 5 (emojis) → T8-T11. |
| F7 | Risk mitigations → tasks | ✅ pass | R-1 → T18 (unit test). R-2 → T12 + T21 (visual verify). R-4 → T13 + T21. |
| F8 | Dead code removal included | ✅ pass | T5 removes getBestScore(), T19 removes dead setup screen. |

---

## 2. Coverage Map

| area | covered? | tasks |
|------|----------|-------|
| Best-score bug (GP-1) | ✅ | T5 |
| Hidden filters (GP-7) | ✅ | T14 |
| 3-retry threshold (GP-3) | ✅ | T7, T16, T18 |
| PageLayout missing (CSS-1) | ✅ | T12 |
| Emoji violations (CSS-2/3) | ✅ | T8, T9, T10, T11 |
| Overlay positioning (CSS-4) | ✅ | T13 |
| Board sizing (CSS-5) | ⚠️ partial | T12 (PageLayout handles sizing). Board-specific `max-w-[500px]` may need adjustment — executor should verify. |
| app.tsx SRP violation (AQ-1) | ✅ | T1-T5 |
| Duplicate RushPuzzle type (AQ-2) | ✅ | T1 (consolidate to types/goban.ts) |
| InlineSolver not reusable (AQ-3) | ✅ | T3 |
| No Rush service (AQ-4) | ✅ | T2 |
| E2E path mismatch (AQ-5) | ✅ | T17 |
| Audio feedback missing | ✅ | T15 |
| Dead setup screen (GP-2) | ✅ | T19 |
| Async state race (GP-4) | ⚠️ not addressed | Low severity. `isGameOver` async check after lives decrement is a potential minor race. Not in scope per charter. |
| Skip button at lives=1 (GP-5) | ⚠️ not addressed | Low severity. Possibly intentional UX decision. Not in scope. |
| Pool exhaustion feedback (GP-6) | ⚠️ not addressed | Low severity. Silent reset is acceptable for MVP. Not in scope. |
| Countdown race (GP-8) | ⚠️ not addressed | Low severity. Edge case with React batching. Not in scope. |

---

## 3. Unmapped Tasks

None. All tasks in 40-tasks.md trace to at least one AC and one charter goal.

---

## 4. Ripple-Effects Table

| impact_id | direction | area | risk | mitigation | owner_task | status |
|-----------|-----------|------|------|------------|------------|--------|
| RE-1 | downstream | `RandomChallengePage` — uses `InlinePuzzleSolver` via `renderRandomPuzzle` callback | High | T7 adds `maxAttempts` prop with default=3 (backward-compatible). T16 wires it. T18 tests it explicitly. | T7, T16, T18 | ✅ addressed |
| RE-2 | downstream | `TrainingViewPage` — may use `renderPuzzle` callback (check) | Low | Phase A is zero-behavior-change. Training uses separate `SolverView`, not `InlinePuzzleSolver`. Verified in research R-5. | T6 | ✅ addressed |
| RE-3 | lateral | `app.tsx` route dispatcher — must import from new module locations | Medium | T5 updates all imports. T6 verifies all tests pass. | T5, T6 | ✅ addressed |
| RE-4 | upstream | `services/progress/progressCalculations.ts` — `getRushHighScore()` already exists | None | No changes needed to progress system. Just switch from dead `getBestScore()` to existing `getRushHighScore()`. | T5 | ✅ addressed |
| RE-5 | lateral | `frontend/src/components/shared/icons/index.ts` — barrel export must include new icons | Low | T8+T9 add FireIcon/PauseIcon to barrel. Standard pattern. | T8, T9 | ✅ addressed |
| RE-6 | downstream | Visual regression tests — `rush.visual.spec.ts` and `rush-modal.visual.spec.ts` may need baseline updates | Medium | After PageLayout wrapping and emoji replacement, visual baselines will change. Executor must update reference screenshots. | T21 | ✅ addressed |
| RE-7 | lateral | `types/goban.ts` — adding `RushPuzzle` type alongside `RushDuration` | Low | No naming conflicts. Type extends `CollectionPuzzleEntry` which already exists in `models/collection.ts`. | T1 | ✅ addressed |
| RE-8 | lateral | `AGENTS.md` — architecture map must reflect new module structure | Low | T20 explicitly updates AGENTS.md. Must be in same commit as structural change per project rules. | T20 | ✅ addressed |

---

## 5. Severity Assessment

| severity | count | findings |
|----------|-------|----------|
| Critical | 0 | All critical bugs (GP-1, GP-7) have tasks assigned |
| High | 0 | All high-severity issues (GP-3, CSS-1, AQ-1) have tasks assigned |
| Medium | 1 | CSS-5 (board sizing) partially addressed — executor should verify after PageLayout wrapping |
| Low | 4 | GP-4, GP-5, GP-6, GP-8 — acknowledged as out of scope per charter non-goals |
| Info | 0 | — |

**Overall assessment**: The plan and tasks comprehensively address all critical and high-severity issues. 4 low-severity issues are intentionally deferred. 1 medium issue (board sizing) needs executor attention during T12.

---

## 6. Test Strategy

### Phase A Gate (T6)
- Run full vitest suite — all existing tests must pass unchanged
- This proves the extraction introduced no behavior changes

### Phase B Tests (T18)
- **New unit tests**: `InlineSolver.test.tsx`
  - Test 1: `maxAttempts=1` → first wrong triggers `onComplete(false)`
  - Test 2: `maxAttempts=3` (default) → requires 3 wrong to trigger `onComplete(false)`
  - Test 3: correct solution → `onComplete(true)` regardless of maxAttempts
  - Test 4: audio callback fires on correct/wrong

### Phase B E2E (T17)
- Fix paths in 4-6 rush E2E test files
- Verify they navigate to `/modes/rush` correctly

### Final Regression (T21)
- Full vitest run
- Visual regression comparison for Rush pages

> **See also**:
> - [Charter: 00-charter.md](./00-charter.md) — Acceptance criteria
> - [Plan: 30-plan.md](./30-plan.md) — Architecture decisions
> - [Tasks: 40-tasks.md](./40-tasks.md) — Dependency-ordered task list
