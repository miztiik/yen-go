# Tasks — Playing Modes DRY Compliance (OPT-1)

**Initiative**: `20260329-1500-feature-playing-modes-dry-compliance`
**Last Updated**: 2026-03-29

---

## Phase 0: Pre-Flight

| ID | Task | Files | Dependencies | Parallel |
|----|------|-------|--------------|----------|
| T01 | Commit existing frontend changes to preserve clean git history | `frontend/` | None | — |

## Phase 1: Dead Code Cleanup

| ID | Task | Files | Dependencies | Parallel |
|----|------|-------|--------------|----------|
| T02 | Delete `RushPage.tsx` (legacy Rush with inline styles) | `frontend/src/pages/RushPage.tsx`, `frontend/src/pages/RushPage.css` | T01 | [P] |
| T03 | Delete `RushMode.tsx` (old Board component version) | `frontend/src/components/Rush/RushMode.tsx` | T01 | [P] |
| T04 | Delete `PuzzleSolvePage.tsx` (pre-SolverView dead code) | `frontend/src/pages/PuzzleSolvePage.tsx` | T01 | [P] |
| T05 | Delete `ReviewPage.tsx` (not routed) | `frontend/src/pages/ReviewPage.tsx` | T01 | [P] |
| T06 | Delete `TrainingPage.tsx` (unreferenced duplicate of TrainingViewPage) | `frontend/src/pages/TrainingPage.tsx` | T01 | [P] |
| T07 | Verify no broken imports after deletion; run `npm run build` | — | T02-T06 | — |

## Phase 2: Infrastructure — SolverView Minimal + StreamingLoader

| ID | Task | Files | Dependencies | Parallel |
|----|------|-------|--------------|----------|
| T08 | Add `minimal?: boolean` prop to `SolverViewProps` — when true, render only `solver-board-col` (hide sidebar) | `frontend/src/components/Solver/SolverView.tsx` | T07 | [P] |
| T09 | Add `StreamingPuzzleSetLoader` interface extending `PuzzleSetLoader` with `hasMore()` + `loadMore()` | `frontend/src/services/puzzleLoaders/types.ts` | T07 | [P] |
| T10 | Add `failOnWrongDelayMs?: number` and `autoAdvanceEnabled?: boolean` props to `PuzzleSetPlayerProps` — use `failOnWrongDelayMs` in `handleFail` setTimeout; use `autoAdvanceEnabled` to override global `appSettings.autoAdvance` at prop level (RC-6: never mutate global settings) | `frontend/src/components/PuzzleSetPlayer/index.tsx` | T07 | [P] |
| T11 | Add `minimal?: boolean` prop to `PuzzleSetPlayerProps` — pass through to SolverView | `frontend/src/components/PuzzleSetPlayer/index.tsx` | T08 | — |
| T12 | Add streaming support to PuzzleSetPlayer: detect StreamingLoader, show "?" for total, call `loadMore()` near end. Streaming loaders set `totalPuzzles` to first batch size on `loadSet()`, updated on each `loadMore()` (RC-7). | `frontend/src/components/PuzzleSetPlayer/index.tsx` | T09 | — |
| T13 | Write unit tests for SolverView minimal variant (board renders, sidebar hidden) | `frontend/tests/unit/SolverView-minimal.test.tsx` | T08 | — |
| T14 | Write unit tests for `failOnWrongDelayMs` prop | `frontend/tests/unit/PuzzleSetPlayer-failDelay.test.tsx` | T10 | — |
| T15 | Export `StreamingPuzzleSetLoader` from `puzzleLoaders/index.ts` barrel | `frontend/src/services/puzzleLoaders/index.ts` | T09 | [P] |

## Phase 3: Random Challenge Migration

| ID | Task | Files | Dependencies | Parallel |
|----|------|-------|--------------|----------|
| T16 | Create `RandomPuzzleLoader` implementing `StreamingPuzzleSetLoader` — wraps `getRandomPuzzle()` query | `frontend/src/services/puzzleLoaders/RandomPuzzleLoader.ts` | T09, T15 | — |
| T17 | Refactor `RandomChallengePage` to thin wrapper around `PuzzleSetPlayer` — use `renderHeader` for header, `renderSummary` for results, `mode="random"` | `frontend/src/pages/RandomChallengePage.tsx` | T11, T12, T16 | — |
| T18 | Remove `renderRandomPuzzle` callback from `App.tsx` — Random now uses PSP internally | `frontend/src/app.tsx` | T17 | — |
| T19 | Update `RandomPage.test.tsx` unit tests for new PSP-based structure | `frontend/tests/unit/RandomPage.test.tsx` | T17 | — |
| T20 | Update Random visual tests | `frontend/tests/visual/specs/random.visual.spec.ts`, `random-page.visual.spec.ts` | T17 | [P] |
| T21 | Verify Random mode manually / run existing tests | — | T17-T20 | — |

## Phase 4: Rush Mode Migration

| ID | Task | Files | Dependencies | Parallel |
|----|------|-------|--------------|----------|
| T22 | Create `RushPuzzleLoader` implementing `StreamingPuzzleSetLoader` — wraps `getNextPuzzle()` with batch pre-fetch of next puzzle while current is being solved (RC-5: no skeleton flash between puzzles) | `frontend/src/services/puzzleLoaders/RushPuzzleLoader.ts` | T09, T15 | — |
| T23 | Refactor `PuzzleRushPage` to thin wrapper around `PuzzleSetPlayer` — `renderHeader` → RushOverlay, `renderNavigation` → null, `renderSummary` → Rush results, `failOnWrong=true`, `failOnWrongDelayMs=100`, `autoAdvanceEnabled=false` (RC-6), `minimal=true`. Rush transitions use prefetched SGF — no visible skeleton between puzzles (RC-5). | `frontend/src/pages/PuzzleRushPage.tsx` | T11, T12, T22 | — |
| T24 | Bridge `useRushSession` to PSP — `onPuzzleComplete` calls `actions.recordCorrect/recordWrong`, timer/lives/streak continue to work | `frontend/src/pages/PuzzleRushPage.tsx` | T23 | — |
| T25 | Preserve Rush countdown screen (before PSP mount) and finished screen (PSP `renderSummary`) | `frontend/src/pages/PuzzleRushPage.tsx` | T23 | — |
| T26 | Remove `renderPuzzle` prop injection from `App.tsx` — Rush now uses PSP internally | `frontend/src/app.tsx` | T23 | — |
| T27 | Delete `InlineSolver` component (no longer used by any mode) | `frontend/src/components/shared/InlineSolver/` | T23, T17 | — |
| T28 | Delete `RushPuzzleRenderer` component (no longer used) | `frontend/src/components/Rush/RushPuzzleRenderer.tsx` | T23, T17 | — |
| T29 | Update Rush unit tests (6 files): `rush.test.ts`, `rush-score.test.tsx`, `rush-results.test.tsx`, `PuzzleRushPage.test.ts`, `PuzzleRushPage-component.test.tsx`, `puzzleRushService.test.ts` | `frontend/tests/unit/rush*.test.*`, `frontend/tests/unit/PuzzleRushPage*.test.*` | T23-T25 | — |
| T30 | Update Rush integration tests (2 files): `rushMode.test.tsx`, `puzzleRush.test.tsx` | `frontend/tests/integration/rush*.test.tsx` | T23-T25 | — |
| T31 | Update Rush visual tests (6 files) | `frontend/tests/visual/**/*rush*` | T23-T25 | [P] |
| T32 | Verify Rush mode manually / run existing tests | — | T29-T31 | — |

## Phase 5: App.tsx Cleanup

| ID | Task | Files | Dependencies | Parallel |
|----|------|-------|--------------|----------|
| T33 | Remove `getNextPuzzle`, `getRandomPuzzle`, `renderPuzzle`, `renderRandomPuzzle` from App.tsx (moved into loaders) | `frontend/src/app.tsx` | T18, T26 | — |
| T34 | Remove `RushPuzzleRenderer` import and `RushPuzzle` type if no longer used in App.tsx | `frontend/src/app.tsx` | T33 | — |
| T35 | Full Vitest run — verify all unit + integration tests pass | — | T33-T34 | — |

## Phase 6: Playwright E2E Tests

| ID | Task | Files | Dependencies | Parallel |
|----|------|-------|--------------|----------|
| T36 | Write Playwright Rush play test: navigate → countdown → play → canvas click correct move → score increases → next puzzle loads | `frontend/tests/e2e/rush-play-compliance.spec.ts` | T32 | [P] |
| T37 | Write Playwright Random play test: navigate → select level → canvas click correct move → result → another puzzle | `frontend/tests/e2e/random-play-compliance.spec.ts` | T21 | [P] |
| T38 | Write Playwright Rush board sizing test: screenshot at 1440px → board ≥600px width (not hardcoded) | `frontend/tests/e2e/rush-board-sizing.spec.ts` | T32 | [P] |
| T39 | Write Playwright Random board sizing test: screenshot at 1440px → responsive width | `frontend/tests/e2e/random-board-sizing.spec.ts` | T21 | [P] |
| T40 | Write Playwright Rush transition timing test: measure wrong-move → next-puzzle time < 300ms | `frontend/tests/e2e/rush-transition-timing.spec.ts` | T32 | [P] |
| T41 | Update existing Rush e2e tests (5 files) to match new component structure / testids | `frontend/tests/e2e/rush-*.spec.ts` | T32 | — |
| T42 | Run full Playwright e2e suite | — | T36-T41 | — |

## Phase 7: Documentation

| ID | Task | Files | Dependencies | Parallel |
|----|------|-------|--------------|----------|
| T43 | Update `frontend/src/AGENTS.md` — document SolverView minimal, StreamingLoader, updated Rush/Random architecture | `frontend/src/AGENTS.md` | T32 | [P] |
| T44 | Create `docs/architecture/frontend/playing-modes.md` — unified PSP architecture for all 8 modes | `docs/architecture/frontend/playing-modes.md` | T32 | [P] |

---

## Summary

- **Total tasks**: 44
- **Phases**: 7 (+ Phase 0 pre-flight)
- **Files created**: ~6 (2 loaders, 2 unit tests, ~4 Playwright tests, 2 docs)
- **Files modified**: ~10 (SolverView, PSP, PuzzleRushPage, RandomChallengePage, App.tsx, types.ts, barrel exports, plus existing test files)
- **Files deleted**: ~10 (5 dead pages, InlineSolver dir, RushPuzzleRenderer, RushPage.css)
- **Parallel tasks**: T02-T06, T08-T10, T20, T31, T36-T40, T43-T44
