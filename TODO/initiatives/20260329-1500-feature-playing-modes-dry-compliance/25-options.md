# Options — Playing Modes DRY Compliance Refactor

**Initiative**: `20260329-1500-feature-playing-modes-dry-compliance`
**Last Updated**: 2026-03-29
**Planning Confidence Score**: 88 (post-research)
**Risk Level**: medium

---

## Option Comparison

| OPT | Title | Approach | DRY Score | Risk | Complexity | Test Impact |
|-----|-------|----------|-----------|------|------------|-------------|
| OPT-1 | Full PuzzleSetPlayer Unification | Both Rush + Random migrate to PuzzleSetPlayer | 10/10 | Medium-High | High | ~22 test files rewritten |
| OPT-2 | Hybrid (PSP for Random, SolverView for Rush) | Random → PSP, Rush → SolverView directly (bypass PSP sequencer) | 8/10 | Medium | Medium | ~15 test files updated |
| OPT-3 | Shared Sub-Components Only | Keep separate pages, replace InlineSolver with SolverView minimal, extract shared results | 6/10 | Low | Low | ~8 test files updated |

---

## OPT-1: Full PuzzleSetPlayer Unification

### Approach
Both Rush and Random migrate to `PuzzleSetPlayer`:
- Rush: PuzzleSetPlayer with a `RushStreamLoader`, `renderHeader` → RushOverlay, `renderSummary` → Rush results, `failOnWrong=true`
- Random: PuzzleSetPlayer with a `RandomStreamLoader`, `renderHeader` → Random header, `renderSummary` → Random results
- SolverView gains `minimal` boolean prop (hides sidebar, hints, transforms)
- New `StreamingPuzzleSetLoader` interface extends `PuzzleSetLoader` with `hasMore(): boolean` and `loadNext(): Promise<LoadResult<PuzzleEntry>>`
- PuzzleSetPlayer gains `streaming` mode: no fixed `totalPuzzles`, shows "?" count, advances dynamically

### Benefits
- Maximum DRY: single rendering + sequencing pipeline for ALL 8 modes
- All modes automatically get future SolverView improvements (transforms, viewport cropping, keyboard shortcuts)
- Single test surface for puzzle sequencing
- Aligns with chess.com/Lichess pattern (shared board, mode-specific chrome)
- Eliminates InlineSolver, RushPuzzleRenderer, and App.tsx render-prop indirection entirely

### Drawbacks
- Rush timer/lives/scoring logic in `useRushSession` must integrate with PuzzleSetPlayer's completion flow — needs `onPuzzleComplete` to bridge to `actions.recordCorrect()/recordWrong()`
- PuzzleSetPlayer currently assumes finite puzzle sets (`totalPuzzles` displayed in header/nav) — streaming mode adds complexity
- Risk of Rush "feeling different" if PSP's auto-advance, skeleton loading, or transition timing doesn't match current behavior
- Higher test rewrite burden: 19 Rush + 3 Random test files need updating

### Risks
| Risk | Probability | Mitigation |
|------|------------|------------|
| Rush UX regression (timing feels off) | Medium | Preserve identical skeleton loading; A/B visual comparison via Playwright screenshots |
| PuzzleSetPlayer becomes too complex with streaming | Low-Medium | Streaming is additive — existing finite behavior unchanged; guarded by `loader.hasMore()` |
| Hard to debug if PSP sequencing breaks Rush | Low | useRushSession is decoupled from rendering; can unit-test independently |

### Architecture Compliance
- ✅ DRY: single pipeline
- ✅ SRP: PuzzleSetPlayer handles sequencing, SolverView handles rendering, pages handle mode chrome
- ✅ OGS alignment: all modes use `.solver-layout` responsive CSS
- ✅ Open/Closed: new modes extend via render-props + loader interface

### Rollback Plan
Revert to pre-refactor commit. Old InlineSolver/RushPuzzleRenderer preserved in git history.

---

## OPT-2: Hybrid (PSP for Random, SolverView direct for Rush)

### Approach
- **Random → PuzzleSetPlayer**: Similar to Daily Timed — thin wrapper with `RandomStreamLoader`, custom header via `renderHeader`
- **Rush → SolverView directly**: PuzzleRushPage keeps its own sequencer (`useRushSession`) but replaces InlineSolver with SolverView `minimal` variant for board rendering. No PuzzleSetPlayer wrapper.
- SolverView gains `minimal` boolean prop
- New `StreamingPuzzleSetLoader` for Random (simpler — only Random needs it)
- Rush page simplified: removes board container `max-w-[600px]`, lets SolverView handle responsive layout
- InlineSolver + RushPuzzleRenderer deleted

### Benefits
- Random migration is low risk (structurally identical to Daily Timed)
- Rush keeps its unique sequencer — timer/lives/scoring stays exactly where it is
- SolverView `minimal` gives Rush responsive board sizing without the PSP overhead
- Smaller blast radius than OPT-1 (Rush page structure stays, just rendering changes)
- Future option to migrate Rush to PSP later (after Random validates the streaming pattern)

### Drawbacks
- Two sequencing patterns remain: PSP for 7 modes, custom for Rush
- Rush still has its own puzzle loading (via `getNextPuzzle` from App.tsx) instead of PSP's loader
- Slightly less DRY than OPT-1 (sequencing duplicated for Rush)
- Rush page keeps countdown/results screens inline (not extracted to reusable components)

### Risks
| Risk | Probability | Mitigation |
|------|------------|------------|
| Random migration breaks something | Low | Daily Timed already validates PSP + failOnWrong pattern |
| Rush SolverView minimal doesn't size correctly | Low | SolverView + solver-layout CSS is battle-tested across 6 modes |
| Future modes still need custom pages | Low | If Rush pattern works, OPT-1 migration is incremental |

### Architecture Compliance
- ✅ DRY: 7/8 modes on PSP (up from 6). Rush uses SolverView (up from InlineSolver)
- ⚠️ SRP: Rush page still handles sequencing + rendering (improved but not ideal)
- ✅ OGS alignment: all modes use `.solver-layout` responsive CSS
- ✅ Open/Closed: Random extends via render-props + StreamingLoader

### Rollback Plan
Random and Rush can be rolled back independently. Random reverts to RandomChallengePage + InlineSolver. Rush reverts to PuzzleRushPage + InlineSolver.

---

## OPT-3: Shared Sub-Components Only

### Approach
- Keep PuzzleRushPage and RandomChallengePage as separate pages with their own sequencers
- Replace InlineSolver with SolverView `minimal` variant in both Rush and Random
- Extract shared `SessionResults` component from Rush/Random results screens
- Fix board sizing: remove `max-w-[600px]`, use SolverView's responsive layout
- Delete dead code files
- No StreamingLoader, no PuzzleSetPlayer changes

### Benefits
- Minimal risk — existing page structure preserved
- Smallest blast radius (only rendering + results extraction)
- Fastest to implement
- Board sizing fix is immediate (SolverView responsive CSS takes over)

### Drawbacks
- Sequencing logic remains duplicated in Rush + Random pages
- Future modes still need custom pages and custom sequencers
- App.tsx render-prop indirection (`renderPuzzle`, `renderRandomPuzzle`) remains
- Doesn't fully address DRY concern from code review (CRB-2)
- Still 3 sequencing patterns: PSP (6 modes), Rush custom, Random custom

### Risks
| Risk | Probability | Mitigation |
|------|------------|------------|
| SolverView minimal doesn't integrate cleanly with Rush's fast puzzle cycling | Low-Medium | Test puzzle transition timing |
| Shared SessionResults component is too rigid for both Rush/Random | Low | Use render-prop pattern for customization |

### Architecture Compliance
- ⚠️ DRY: sequencing still duplicated (partially addressed)
- ❌ SRP: Rush/Random pages handle sequencing + rendering + results
- ✅ OGS alignment: all modes use `.solver-layout` responsive CSS
- ⚠️ Open/Closed: new modes still need custom pages

### Rollback Plan
Straightforward per-file revert.

---

## Recommendation

**OPT-1 (Full PuzzleSetPlayer Unification)** is recommended.

**Rationale**: 
1. The user explicitly requested "Option B — refactor so that we are compliant" and "all 5 playing options are compliant". OPT-1 achieves this fully.
2. PuzzleSetPlayer already has the render-prop slots (`renderHeader`, `renderNavigation`, `renderSummary`, `failOnWrong`) that Rush needs.
3. DailyChallengePage is a proven reference — it migrated from a 674-line monolith to a thin wrapper around PSP. Rush (283 lines) and Random (180 lines) can follow the same pattern.
4. External precedent (chess.com, Lichess) validates the "shared board + mode overlay" pattern.
5. StreamingLoader is a small interface extension (~20 lines) that enables infinite modes.
6. The test rewrite burden is acceptable — tests target behavior (did the score increase? did the timer work?), which doesn't change.

**Risk mitigation**: Implement in phases — Random first (lower risk, validates StreamingLoader), then Rush. Playwright canvas-click tests provide end-to-end verification.
