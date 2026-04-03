# Plan — Playing Modes DRY Compliance (OPT-1: Full PSP Unification)

**Initiative**: `20260329-1500-feature-playing-modes-dry-compliance`
**Selected Option**: OPT-1 (Full PuzzleSetPlayer Unification)
**Last Updated**: 2026-03-29

---

## Architecture Design

### Current State
```
Rush:   PuzzleRushPage → RushPuzzleRenderer → InlineSolver → GobanContainer (max-w-[600px])
Random: RandomChallengePage → App.renderRandomPuzzle → RushPuzzleRenderer → InlineSolver → GobanContainer
Daily:  DailyChallengePage → PuzzleSetPlayer → SolverView → GobanContainer ✅
```

### Target State
```
Rush:   PuzzleRushPage → PuzzleSetPlayer → SolverView(minimal) → GobanContainer ✅
Random: RandomChallengePage → PuzzleSetPlayer → SolverView(minimal) → GobanContainer ✅
Daily:  DailyChallengePage → PuzzleSetPlayer → SolverView → GobanContainer ✅ (unchanged)
```

### Key Design Decisions

#### 1. SolverView `minimal` Variant
- **Add one prop**: `minimal?: boolean` (default `false`)
- When `minimal=true`: hide sidebar column entirely — render only `solver-board-col`
- The `solver-layout` CSS handles responsive sizing automatically
- No sidebar = board fills available space (100% on mobile, flex-1 on desktop)
- PuzzleSetPlayer passes `minimal` through to SolverView — no other SolverView changes

#### 2. StreamingPuzzleSetLoader Interface
```typescript
export interface StreamingPuzzleSetLoader extends PuzzleSetLoader {
  /** Whether more puzzles can be loaded after current set. */
  hasMore(): boolean;
  /** Load the next batch of puzzles. Returns updated PuzzleSetInfo. */
  loadMore(): Promise<LoadResult<PuzzleEntry[]>>;
}
```
- `PuzzleSetInfo.totalPuzzles` changes to `totalPuzzles: number` with a new `isStreaming: boolean` field
- **Streaming initial totalPuzzles** (RC-7): Streaming loaders set `totalPuzzles` to the first batch size on `loadSet()`. The value is updated dynamically on each `loadMore()` call (incremented by batch size). This keeps `totalPuzzles` always reflecting the currently-loaded puzzle count.
- When streaming: header shows "Score: N" instead of "N / Total" progress bar
- `PuzzleSetPlayer` checks `if (loader is StreamingPuzzleSetLoader)` via simple duck-typing: `'hasMore' in loader`

#### 3. Rush Transition Timing (RC-1, RC-4, RC-5, RC-6)
- **Current PSP `failOnWrong` delay**: 400ms hardcoded in `handleFail` (`setTimeout(() => {...}, 400)`)
- **Solution**: Add `failOnWrongDelayMs?: number` prop to PuzzleSetPlayer (default 400)
- Rush passes `failOnWrongDelayMs={100}` for near-instant transitions
- **Auto-advance override** (RC-6): Add `autoAdvanceEnabled?: boolean` prop to PuzzleSetPlayer (overrides global `appSettings.autoAdvance` at prop level). Rush passes `autoAdvanceEnabled={false}`. This is a prop-level override — **global appSettings is never mutated**.
- For correct answers, `onPuzzleComplete` callback triggers `useRushSession.actions.recordCorrect()` which immediately loads next via StreamingLoader prefetch
- **Rush puzzle transition strategy** (RC-5): Use SGF **prefetch** pattern — `RushPuzzleLoader.loadMore()` pre-fetches next puzzle while current is being solved. When puzzle completes, next SGF is already loaded → no visible skeleton flash between puzzles. The `isLoadingSgf` state in PSP only triggers on first load, not on pre-fetched transitions.
- **Evidence needed**: Playwright test measuring puzzle-to-puzzle transition time (<300ms); Playwright test asserting no skeleton element visible between Rush puzzles

#### 4. RushOverlay Positioning (RC-3)
- RushOverlay is currently a flex-row HUD bar above the board
- With SolverView responsive layout, the board is inside `solver-board-col` which fills available width
- RushOverlay renders ABOVE the PuzzleSetPlayer (in the page, not inside PSP) via `renderHeader` slot — unaffected by board sizing
- **No positioning change needed** — RushOverlay is already full-width and independent of board container

#### 5. Rush Puzzle Loading
- New `RushPuzzleLoader` implements `StreamingPuzzleSetLoader`
- Wraps `getNextPuzzle()` from App.tsx (which queries SQL for random puzzles by level/tag)
- `loadSet()`: returns initial batch (e.g., 5 puzzles pre-fetched)
- `hasMore()`: always `true` (infinite mode)
- `loadMore()`: fetches next puzzle on demand
- PuzzleSetPlayer calls `loadMore()` when approaching end of current batch

#### 6. Random Puzzle Loading
- New `RandomPuzzleLoader` implements `StreamingPuzzleSetLoader`
- Similar to RushPuzzleLoader but without timer/lives integration
- Single puzzle at a time (no batch pre-fetch needed)

#### 7. PuzzleRushPage Refactor
- Becomes thin wrapper around PuzzleSetPlayer (like DailyChallengePage)
- `renderHeader` → returns `<RushOverlay>` (timer, lives, score, skip, quit)
- `renderNavigation` → returns `null` (no dot nav in Rush)
- `renderSummary` → returns Rush results screen (score, accuracy, stats)
- `failOnWrong={true}`, `failOnWrongDelayMs={100}`
- `onPuzzleComplete` bridges to `useRushSession.actions.recordCorrect/recordWrong`
- Countdown screen stays in page (before mounting PSP)
- `mode="rush"` for CSS accent cascade

#### 8. RandomChallengePage Refactor
- Becomes thin wrapper around PuzzleSetPlayer (like DailyChallengePage)
- `renderHeader` → returns Random header (level, accuracy, puzzle count)
- `renderNavigation` → returns `null`
- `renderSummary` → returns Random results screen (correct/wrong, action buttons)
- `mode="random"` for CSS accent cascade

---

## Data Model Impact

### Changes to `PuzzleSetLoader` Interface (types.ts)
- Add optional `getEntry(index: number)` if not already present
- No breaking changes to existing loaders

### New Interface: `StreamingPuzzleSetLoader`
- Extends `PuzzleSetLoader` with `hasMore()` and `loadMore()`
- Existing 3 loaders unchanged (they don't implement streaming)

### Changes to `PuzzleSetInfo`
- Add `isStreaming?: boolean` (optional, default false)
- `totalPuzzles` remains `number` — streaming modes set it to current loaded count

### Changes to `PuzzleSetPlayerProps`
- Add `failOnWrongDelayMs?: number` (optional, default 400)
- Add `autoAdvanceEnabled?: boolean` (optional — when provided, overrides global `appSettings.autoAdvance` at prop level without mutating global state)
- Add `minimal?: boolean` (optional, default false — passed to SolverView)

### Changes to `SolverViewProps`
- Add `minimal?: boolean` (optional, default false)

---

## Risks and Mitigations

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Rush feels sluggish with PSP | Medium | High | `failOnWrongDelayMs={100}` + disabled auto-advance; Playwright timing test |
| StreamingLoader race conditions | Low | Medium | Single puzzle pre-fetch; cancel on unmount |
| SolverView minimal breaks existing CSS | Low | Low | Board-only already works (solver-board-col is independent) |
| 22 test files need updating | High | Medium | Tests target behavior, not implementation; testid preservation where possible |
| Dead code deletion breaks imports | Low | Low | Verified: none of the 5 files are imported anywhere |

---

## Documentation Plan

| doc_id | file | action | why_updated |
|--------|------|--------|-------------|
| DOC-1 | `frontend/src/AGENTS.md` | Update | Structural code change — add SolverView minimal variant, StreamingLoader, updated Rush/Random architecture |
| DOC-2 | `docs/architecture/frontend/playing-modes.md` | Create | Document the unified PuzzleSetPlayer architecture across all 8 modes |
| DOC-3 | This plan file (`30-plan.md`) | Complete | Part of initiative artifacts |

---

## Playwright Evidence Strategy

### E2E Tests — Canvas Click Play (AC-3, AC-4)
1. **Rush play test**: Navigate to Rush → select duration → countdown → board renders → click correct move on canvas → score increases → verify next puzzle loads
2. **Random play test**: Navigate to Random → select level → board renders → click correct move on canvas → result screen → click "Another" → new puzzle loads

### Visual Evidence — Board Sizing (AC-1, AC-2, AC-8)
3. **Rush board sizing**: Screenshot at 1440px viewport → board occupies responsive width (≥600px), not hardcoded 600px
4. **Random board sizing**: Screenshot at 1440px viewport → board occupies responsive width
5. **Rush mobile sizing**: Screenshot at 375px viewport → board fills width properly

### Timing Evidence (RC-1)
6. **Rush transition timing**: Measure time from wrong-move to next-puzzle-visible; assert <300ms

---

## Rollout / Rollback

### Rollout
1. Phase 1: Dead code cleanup (delete 5 files, InlineSolver, RushPuzzleRenderer)
2. Phase 2: SolverView `minimal` prop + StreamingLoader interface
3. Phase 3: Random → PSP migration + tests
4. Phase 4: Rush → PSP migration + tests
5. Phase 5: App.tsx cleanup (remove renderPuzzle/renderRandomPuzzle indirection)
6. Phase 6: Playwright e2e tests

### Rollback
- Each phase is independently revertible via git
- Phase 1 (dead code) is independent of phases 2-6
- Phase 3 (Random) and Phase 4 (Rush) are independent of each other
