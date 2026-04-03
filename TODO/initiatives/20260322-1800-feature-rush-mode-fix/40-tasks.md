# Tasks — Rush Mode Fix (OPT-1: Refactor-First, Two-Phase)

**Initiative**: `20260322-1800-feature-rush-mode-fix`
**Selected Option**: OPT-1
**Last Updated**: 2026-03-22

---

## Phase A: Pure Refactor (Zero Behavior Change)

All existing tests must pass after each task. No logic changes.

| task_id | title | files | depends_on | AC | parallel |
|---------|-------|-------|------------|-----|---------|
| T1 | Extract `RushPuzzle` type to `types/goban.ts` | `frontend/src/types/goban.ts`, `frontend/src/app.tsx` | — | AC-9 | [P] with T2 |
| T2 | Create `services/puzzleRushService.ts` — extract `getNextPuzzle`, `loadLevelIndex`, `loadRushTagEntries`, `getBestScore` removal | `frontend/src/services/puzzleRushService.ts` (new), `frontend/src/app.tsx` | — | AC-9 | [P] with T1 |
| T3 | Create `components/shared/InlineSolver/InlineSolver.tsx` — extract `InlinePuzzleSolver` (keep wrongAttempts>=3 for now) | `frontend/src/components/shared/InlineSolver/InlineSolver.tsx` (new), `frontend/src/components/shared/InlineSolver/index.ts` (new) | — | AC-9 | [P] with T1, T2 |
| T4 | Move `RushPuzzleRenderer` to `components/Rush/RushPuzzleRenderer.tsx` | `frontend/src/components/Rush/RushPuzzleRenderer.tsx` (new), `frontend/src/components/Rush/index.ts` (update) | T3 | AC-9 | |
| T5 | Update `app.tsx` — replace inline definitions with imports from T1-T4 modules. Wire `getRushHighScore()` from progress system instead of dead `getBestScore()`. | `frontend/src/app.tsx` | T1, T2, T3, T4 | AC-9, AC-4 | |
| T6 | Phase A verification — run vitest + verify zero behavior change | — | T5 | AC-11 | |

---

## Phase B: Bug Fixes + Theme Alignment

| task_id | title | files | depends_on | AC | parallel |
|---------|-------|-------|------------|-----|---------|
| T7 | Add `maxAttempts` prop to `InlineSolver` (default=3). Rush passes 1, Random uses default. | `frontend/src/components/shared/InlineSolver/InlineSolver.tsx` | T6 | AC-6, AC-7 | [P] with T8, T9 |
| T8 | Create `FireIcon` SVG component (replace 🔥 emoji) | `frontend/src/components/shared/icons/FireIcon.tsx` (new), `frontend/src/components/shared/icons/index.ts` | T6 | AC-2 | [P] with T7, T9 |
| T9 | Create `PauseIcon` SVG component (replace ⏸ emoji) | `frontend/src/components/shared/icons/PauseIcon.tsx` (new), `frontend/src/components/shared/icons/index.ts` | T6 | AC-2 | [P] with T7, T8 |
| T10 | Replace emojis in `PuzzleRushPage.tsx` with `FireIcon` SVG | `frontend/src/pages/PuzzleRushPage.tsx` | T8 | AC-2 | |
| T11 | Replace emojis in `RushOverlay.tsx` with `FireIcon` + `PauseIcon` SVGs | `frontend/src/components/Rush/RushOverlay.tsx` | T8, T9 | AC-2 | |
| T12 | Wrap `PuzzleRushPage` in `PageLayout` (variant="single-column", mode="rush") | `frontend/src/pages/PuzzleRushPage.tsx` | T6 | AC-1 | [P] with T7, T8, T9 |
| T13 | Fix `RushOverlay` paused/game-over overlay positioning — move to page-level container | `frontend/src/pages/PuzzleRushPage.tsx`, `frontend/src/components/Rush/RushOverlay.tsx` | T12 | AC-3 | |
| T14 | Wire `masterLoaded` to SQLite puzzle count data in `RushBrowsePage` | `frontend/src/pages/RushBrowsePage.tsx` | T6 | AC-5 | [P] with T7-T13 |
| T15 | Add audio feedback to `InlineSolver` (correct/wrong sounds via audioService) | `frontend/src/components/shared/InlineSolver/InlineSolver.tsx` | T7 | AC-8 | |
| T16 | Update `renderPuzzle`/`renderRandomPuzzle` in `app.tsx` to pass `maxAttempts` prop | `frontend/src/app.tsx` | T7 | AC-6, AC-7 | |
| T17 | Fix E2E test paths from `/puzzle-rush` to `/modes/rush` | `frontend/tests/e2e/rush-start.spec.ts`, `rush-correct.spec.ts`, `rush-wrong.spec.ts`, `rush-game-over.spec.ts` | T6 | AC-10 | [P] with T7-T16 |
| T18 | Write unit tests: InlineSolver maxAttempts=1 (Rush) and maxAttempts=3 (Random) | `frontend/src/components/shared/InlineSolver/InlineSolver.test.tsx` (new) | T7 | AC-6, AC-7 | |
| T19 | Remove dead setup screen from `PuzzleRushPage` (unreachable when duration is provided) | `frontend/src/pages/PuzzleRushPage.tsx` | T12 | AC-9 | |

---

## Phase C: Documentation + Cleanup

| task_id | title | files | depends_on | AC | parallel |
|---------|-------|-------|------------|-----|---------|
| T20 | Update `frontend/src/AGENTS.md` — add InlineSolver, puzzleRushService, RushPuzzleRenderer entries | `frontend/src/AGENTS.md` | T16 | AC-11 | [P] with T21 |
| T21 | Full regression — run vitest + verify all ACs | — | T7-T19 | AC-11 | |

---

## Task Dependency Graph

```
Phase A:
  T1 ──┐
  T2 ──┤──> T5 ──> T6 (verification gate)
  T3 ──┤
       └──> T4 ──┘

Phase B (after T6):
  T7 ──┬──> T15 (audio)
       └──> T16 (wire maxAttempts) ──> T18 (tests)
  T8 ──┬──> T10 (replace emoji in page)
       └──> T11 (replace emoji in overlay)
  T9 ──────> T11
  T12 ─────> T13 (overlay fix)
  T14 (filters — independent)
  T17 (E2E paths — independent)
  T19 (dead code — after T12)

Phase C:
  T20, T21 (after all Phase B tasks)
```

---

## AC-to-Task Traceability

| AC | Tasks |
|----|-------|
| AC-1 (PageLayout wrapping) | T12 |
| AC-2 (Emoji → SVG) | T8, T9, T10, T11 |
| AC-3 (Overlay covers full page) | T13 |
| AC-4 (Best score displays) | T5 |
| AC-5 (Filters functional) | T14 |
| AC-6 (Rush 1-attempt) | T7, T16, T18 |
| AC-7 (Random 3-retry) | T7, T16, T18 |
| AC-8 (Audio feedback) | T15 |
| AC-9 (app.tsx cleaned) | T1, T2, T3, T4, T5, T19 |
| AC-10 (E2E paths) | T17 |
| AC-11 (All tests pass) | T6, T21 |
