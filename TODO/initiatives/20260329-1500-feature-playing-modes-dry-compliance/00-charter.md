# Charter — Playing Modes DRY/SRP/SOLID Compliance Refactor

**Initiative**: `20260329-1500-feature-playing-modes-dry-compliance`
**Last Updated**: 2026-03-29
**Correction Level**: Level 3 (Multiple Files — UI + Logic)

---

## Goals

1. **Migrate Puzzle Rush** to use `PuzzleSetPlayer` with `SolverView` for board rendering, eliminating the custom `InlineSolver` layout that causes board narrowing on large screens
2. **Migrate Random Challenge** to use `PuzzleSetPlayer` with a streaming puzzle loader, eliminating the custom sequencer
3. **Add SolverView `minimal` variant** that hides sidebar/hints for speed-focused modes (Rush, Random)
4. **Build `StreamingLoader`** adapter for PuzzleSetPlayer to support infinite/unbounded puzzle modes
5. **Delete dead/unused files**: `RushPage.tsx` (superseded by PuzzleRushPage), `RushMode.tsx` (uses old Board component), `PuzzleSolvePage.tsx` (pre-SolverView dead code), `ReviewPage.tsx` (not routed), `TrainingPage.tsx` (unused duplicate of TrainingViewPage — note: TrainingPage itself uses PuzzleSetPlayer, it's just unreferenced)
6. **Remove `InlineSolver` component** (functionality absorbed by SolverView minimal variant)
7. **Remove `RushPuzzleRenderer`** (functionality absorbed by PuzzleSetPlayer's SGF loading)
8. **Write Playwright e2e tests** with actual board play (canvas clicking) + visual screenshot evidence proving board sizing is correct

## Non-Goals

- Modifying the 6 compliant modes (Collection, Technique, Training, Daily Standard, Daily Timed, Smart Practice)
- Changing Rush game mechanics (timer, lives, scoring, streak)
- Changing Random challenge mechanics (level selection, accuracy tracking)
- Backend changes
- SGF rendering changes (GobanContainer stays as-is)
- Route path changes (keep `/modes/rush` and `/modes/random`)

## Constraints

1. All existing Rush/Random e2e tests must pass after refactor (updated to new component structure)
2. All existing unit tests must pass or be updated
3. Board must render at same or larger size as collection viewer on all screen sizes
4. Rush HUD (timer, lives, score, streak, skip, quit) must remain functionally identical
5. Random header (level display, accuracy, puzzle count) must remain functionally identical
6. `useRushSession` hook is preserved (game mechanics are separate from rendering)
7. No new dependencies — use existing Playwright, Preact, Tailwind

## Acceptance Criteria

| AC | Description | Verification |
|----|-------------|-------------|
| AC-1 | Rush board uses SolverView (responsive `.solver-layout` CSS), not hardcoded 600px | Playwright screenshot at 1440px viewport shows board ≥600px |
| AC-2 | Random board uses SolverView (responsive `.solver-layout` CSS) | Playwright screenshot at 1440px viewport |
| AC-3 | Rush mode plays correctly: countdown → play → correct/wrong → game over | Playwright canvas-click play test |
| AC-4 | Random mode plays correctly: load → solve → result → another | Playwright canvas-click play test |
| AC-5 | All dead code files deleted | File system check |
| AC-6 | InlineSolver component deleted | File system check |
| AC-7 | RushPuzzleRenderer component deleted | File system check |
| AC-8 | No board narrowing on ≥1024px screens | Playwright visual evidence |
| AC-9 | All existing Vitest unit + integration tests pass | CI |
| AC-10 | All Playwright e2e tests pass | CI |

## Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| Rush UX regression (timer/lives feel different) | High | Preserve `useRushSession` hook; only change rendering, not mechanics |
| Test suite breakage (19 Rush + 1 Random unit + 2 Random visual test files) | Medium | Update tests in same commit; preserve testid contracts where possible |
| Rush puzzle-transition skeleton UX (loading state between puzzles) | Medium | Preserve or improve the board skeleton shown during puzzle loading |
| Random correct/wrong feedback timing | Low | Verify feedback overlay timing matches current behavior |
| SolverView `minimal` variant adds unwanted complexity | Low | Single boolean prop, no structural change to SolverView |
| StreamingLoader abstraction over-engineering | Low | Minimal interface (extend PuzzleSetLoader with `hasMore()`) |
