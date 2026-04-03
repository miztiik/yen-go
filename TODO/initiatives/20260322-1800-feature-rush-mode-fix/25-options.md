# Options — Rush Mode Fix

**Initiative**: `20260322-1800-feature-rush-mode-fix`
**Last Updated**: 2026-03-22

---

## Options Comparison

| Criterion | OPT-1: Refactor-First | OPT-2: Fix-In-Place | OPT-3: Interleaved |
|-----------|----------------------|---------------------|---------------------|
| **Approach** | Phase A: Extract Rush code from app.tsx (pure refactor, zero behavior change). Phase B: Fix all bugs in the new clean modules. | Fix all bugs directly in current file locations (app.tsx, PuzzleRushPage, etc). No structural extraction. | For each bug/issue, extract the relevant code to its module AND fix it in the same commit. |
| **Files touched** | Phase A: 4-5 files (app.tsx, new modules). Phase B: 6-8 files (pages, components, tests). | 6-8 files (same as current) | 6-8 files per iteration |
| **Risk of regression** | **Low** — Phase A is pure move (rename-refactor), no logic change. Phase B changes behavior on clean foundation. | **Medium** — fixing logic inside deeply-nested app.tsx callbacks is error-prone. Hard to verify isolated changes. | **Medium-High** — mixing structural + behavioral changes in same commits makes rollback ambiguous. |
| **DRY compliance** | **Excellent** — clean module boundaries enable proper sharing. `InlinePuzzleSolver` becomes a shared import. | **Poor** — `InlinePuzzleSolver` stays in app.tsx, cannot be properly imported by other modules. `maxAttempts` prop still gets wired through app.tsx closures. | **Good** — modules get extracted as needed, but partial extraction may leave orphaned code. |
| **Rollback safety** | **Best** — Phase A can be rolled back independently (pure refactor). Phase B can be rolled back independently (behavior changes). | **Worst** — all changes in one commit/branch, all-or-nothing rollback. | **Medium** — each interleaved commit has mixed concerns. |
| **Complexity** | 2 phases, clean separation. ~10 tasks. | Single phase. ~8 tasks. | Single phase but more verification per task. ~12 tasks. |
| **Test strategy** | Phase A: existing tests must pass unchanged (refactor safety). Phase B: new tests for behavior changes. | New tests interleaved with fixes. Hard to prove no regressions from structural debt. | Tests per iteration but harder to attribute failures. |
| **Time estimate** | — | — | — |
| **Recommendation** | **★ Recommended** | | |

---

## OPT-1: Refactor-First (Two-Phase)

### Summary
**Phase A — Pure Refactor (no behavior change):**
1. Extract `InlinePuzzleSolver` → `components/shared/InlineSolver/InlineSolver.tsx`
2. Extract `RushPuzzleRenderer` → `components/Rush/RushPuzzleRenderer.tsx`
3. Extract `RushPuzzle` type → `types/goban.ts` (where `RushDuration` already lives)
4. Extract `getNextPuzzle`, `loadLevelIndex`, `loadRushTagEntries` → `services/puzzleRushService.ts`
5. Remove dead `getBestScore()` from app.tsx (it reads a key nothing writes)
6. Update app.tsx to import from new locations
7. All existing tests must pass — zero behavior change

**Phase B — Bug Fixes + Theme Alignment:**
1. Add `maxAttempts` prop to `InlinePuzzleSolver` (default=3, Rush passes 1)
2. Wire `getRushHighScore()` in app.tsx (replace dead `getBestScore`)
3. Wrap `PuzzleRushPage` in `PageLayout`
4. Fix `RushOverlay` positioning (overlays cover full page)
5. Replace emojis with SVG icons
6. Wire `masterLoaded` to actual data in `RushBrowsePage`
7. Add audio feedback via `audioService`
8. Fix E2E test paths
9. Add unit tests for `maxAttempts` behavior

### Benefits
- Clean separation of refactor vs behavior change
- Each phase independently verifiable and rollback-safe
- Shared `InlineSolver` immediately reusable by Random mode
- `app.tsx` becomes dramatically cleaner (~470 lines removed)
- Easy to code review in two small PRs

### Drawbacks
- Two phases mean two review cycles
- Slightly more total work (but less risky work)

### Architecture/Policy Compliance
- Follows SRP (app.tsx loses Rush-specific code)
- Follows project file structure (components/shared/, services/)
- DRY: one solver component, configurable via props
- No new dependencies

---

## OPT-2: Fix-In-Place

### Summary
Fix all bugs directly in current files without extracting code from app.tsx. Add `maxAttempts` prop to `InlinePuzzleSolver` in-place within app.tsx.

### Benefits
- Fewer files changed
- Single review cycle
- Fastest to start

### Drawbacks
- `InlinePuzzleSolver` stays trapped in app.tsx — cannot be properly imported elsewhere
- `maxAttempts` prop wired through app.tsx closures, not clean module boundary
- Leaves ~470 lines of Rush code in app.tsx (SRP violation persists)
- Harder to verify individual fixes in a monolithic file
- Next person who touches Rush has same structural problem

### Architecture/Policy Compliance
- ❌ Violates SRP — app.tsx remains bloated
- ⚠️ DRY technically satisfied but code organization is poor
- No new dependencies

---

## OPT-3: Interleaved

### Summary
For each issue, extract the relevant code AND fix the bug in the same commit. E.g., extract `InlinePuzzleSolver` to shared module AND add `maxAttempts` prop simultaneously.

### Benefits
- Each commit is a complete "feature unit"
- No separate refactor phase

### Drawbacks
- Mixed concerns per commit — if a bug fix introduces regression, rolling back also reverts the extraction
- Harder to code review (structural + behavioral in same diff)
- More complex git bisect if issues arise
- Higher risk of merge conflicts between tasks

### Architecture/Policy Compliance
- Follows SRP (code eventually extracted)
- DRY satisfied
- ⚠️ Rollback granularity is poor

---

## Planner Recommendation

**OPT-1 (Refactor-First)** is recommended because:

1. **User explicitly requested DRY** — clean extraction enables proper module sharing
2. **Phase A is zero-risk** — pure refactor with existing tests as safety net
3. **Phase B is cleaner** — fixing bugs in properly-organized modules is straightforward
4. **Rollback granularity** — each phase can be independently reverted
5. **Alignment with project principles** — SRP, KISS, and the "dead code policy" rule

The governance handover specifically suggested considering "whether the app.tsx extraction should be a separate first phase (pure refactor, no behavior change) followed by bug fixes, or interleaved." OPT-1 follows the recommended first-phase-refactor approach.
