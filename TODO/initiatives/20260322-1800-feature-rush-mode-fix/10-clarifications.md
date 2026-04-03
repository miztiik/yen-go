# Clarifications — Rush Mode Fix

**Initiative**: `20260322-1800-feature-rush-mode-fix`
**Status**: Round 1 — resolved (planner defaults applied)

---

## Round 1

| q_id | question | options | recommended | user_response | status |
|------|----------|---------|-------------|---------------|--------|
| Q1 | **Backward compatibility**: Is backward compatibility required for Rush localStorage data, and should old code paths (e.g., `getBestScore()` reading `yen-go-rush-best-score`) be removed? | A: Remove old code, migrate to progress system only / B: Keep both paths for legacy compatibility / C: Other | A — the inline `getBestScore()` reads a key that nothing writes; it's dead code. Remove it and standardize on `getRushHighScore()` from progress system. | A (planner default) | ✅ resolved |
| Q2 | **Wrong-answer behavior**: Should Rush mode fail a puzzle on first wrong move (costs 1 life, advance to next) or keep the current 3-retry system? | A: 1 attempt (strict Rush — first wrong = lose life + advance) / B: 3 attempts (current) / C: Configurable per duration | A — strict Rush aligns with chess.com Puzzle Rush and other competitive timed puzzle UX. 3 retries makes Rush too easy and dilutes the time pressure. | A (planner default) | ✅ resolved |
| Q3 | **Audio feedback**: Should Rush mode play correct/wrong sounds like the standard solver, or should it be silent for speed? | A: Yes, same audio as standard solver / B: No, silent mode / C: User toggle | A — audio feedback is essential for game feel; the `audioService` is already imported in `app.tsx`. | A (planner default) | ✅ resolved |
| Q4 | **Filters**: The browse page has level + technique filters that are permanently hidden (`masterLoaded = false`). Should we wire them up to SQLite data, or remove them? | A: Wire up to SQLite (show real filter counts) / B: Remove filter UI (simplify Rush) / C: Show filters without counts | A — filters are already coded, they just need data from `puzzleQueryService`. Aligns with user request to make Rush "work". | A (planner default) | ✅ resolved |
| Q5 | **Scope boundary**: Should this initiative include the `app.tsx` refactoring (extract Rush code to dedicated modules), or focus only on CSS/rendering/gameplay bugs? | A: Bugs only (CSS + rendering + gameplay) / B: Bugs + extract Rush code from app.tsx / C: Full Rush rewrite | B — extracting Rush code from `app.tsx` is necessary to fix the InlinePuzzleSolver retry behavior cleanly and prevents future regression. It's also needed to properly share the solver between Rush and Random modes. | B (planner default) | ✅ resolved |
| Q6 | **InlinePuzzleSolver sharing**: `InlinePuzzleSolver` is also used by `RandomChallengePage`. Should the refactored solver support configurable attempt limits via props (Rush=1, Random=3)? | A: Yes, shared component with `maxAttempts` prop / B: No, create separate Rush-only solver / C: Other | A — DRY principle: one component, different configs. Matches user's explicit request to "not duplicate". | A (planner default) | ✅ resolved |
| Q7 | **E2E test paths**: Rush E2E tests navigate to `/puzzle-rush` but the actual route is `/modes/rush`. Should we fix test paths or add a redirect? | A: Fix test paths to `/modes/rush` / B: Add redirect from `/puzzle-rush` to `/modes/rush` / C: Both | A — fix the tests. No redirect needed for an internal test issue. | A (planner default) | ✅ resolved |
