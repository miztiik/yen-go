# Charter — Rush Mode Fix

**Initiative**: `20260322-1800-feature-rush-mode-fix`
**Type**: Feature (bug fix + targeted refactor)
**Last Updated**: 2026-03-22

---

## Goals

1. **Fix rendering/CSS**: Align Rush play page with the app's design system (PageLayout, CSS variables, no emojis)
2. **Fix gameplay bugs**: Best-score storage mismatch (GP-1), disabled filters (GP-7), wrong retry threshold (GP-3)
3. **Fix overlay positioning**: Game-over/paused overlays cover entire page, not just HUD bar (CSS-4)
4. **Extract Rush code from app.tsx**: Move ~470 lines of Rush-specific code to dedicated modules (SRP)
5. **Make InlinePuzzleSolver reusable with configurable attempts**: Support Rush (1 attempt) and Random (3 attempts) via props
6. **Wire browse page filters to SQLite**: Enable level + technique filtering on Rush browse page
7. **Add audio feedback**: Integrate existing `audioService` for correct/wrong sounds
8. **Fix E2E test paths**: Update tests from `/puzzle-rush` to `/modes/rush`

## Non-Goals

- Full Rush mode rewrite or new features
- Hints/transforms in Rush mode (speed mode — hints defeat purpose)
- Per-puzzle progress tracking for Rush (aggregate score only)
- New visual design / UI redesign beyond theme alignment
- Backend changes

## Constraints

- Must NOT duplicate code — reuse `InlinePuzzleSolver`, `PageLayout`, `audioService`, `puzzleQueryService`
- Must NOT break `RandomChallengePage` which shares `InlinePuzzleSolver`
- Must follow project rules: no emojis in production UI, SVG icons only
- Level 3 correction: 2-3 files UI + logic, phased execution
- Backward compatibility NOT required for `yen-go-rush-best-score` localStorage key (dead code)

## Acceptance Criteria

| AC | Criterion | Verification |
|----|-----------|-------------|
| AC-1 | `PuzzleRushPage` wrapped in `PageLayout` with `mode="rush"` | Visual inspection + DOM `data-mode="rush"` |
| AC-2 | All emojis replaced with SVG icons from `components/shared/icons/` | grep for emoji characters returns 0 results |
| AC-3 | Game-over/paused overlays cover full page, not just HUD bar | Visual test: overlay obscures board + controls |
| AC-4 | Best score displays correctly on browse page | Play rush → finish → return to browse → see score |
| AC-5 | Level + technique filters visible and functional on browse page | Change filters → see filtered puzzle counts |
| AC-6 | First wrong move in Rush = lose 1 life + advance | Play rush → wrong move → life decremented, new puzzle |
| AC-7 | Random mode still gives 3 retries | Play random → wrong move → "try again (2 left)" |
| AC-8 | Correct/wrong audio plays during Rush | Correct → ding. Wrong → buzzer. |
| AC-9 | `app.tsx` no longer contains Rush types/components/loaders | grep for `RushPuzzle`, `InlinePuzzleSolver`, `RushPuzzleRenderer` in app.tsx returns 0 |
| AC-10 | E2E rush tests navigate to correct route `/modes/rush` | E2E tests pass |
| AC-11 | All existing vitest + E2E tests pass | CI green |

## Risk Summary

| Risk | Severity | Mitigation |
|------|----------|------------|
| Breaking `RandomChallengePage` during InlinePuzzleSolver refactor | High | AC-7: explicit test for Random 3-retry behavior |
| Board sizing regression after PageLayout wrapping | Medium | Visual regression test comparison |
| Filter data loading slows Rush browse page | Low | SQLite queries are fast (~2ms); same pattern as TechniqueBrowsePage |

> **See also**:
> - [Research: 15-research.md](../20260322-research-rush-timed-puzzle-audit/15-research.md) — Full audit findings
