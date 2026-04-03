# Playing Modes — Unified PuzzleSetPlayer Architecture

> **See also**:
>
> - [Architecture: Puzzle Solving](./puzzle-solving.md) — Core move validation logic
> - [Architecture: Puzzle Modes (legacy)](./puzzle-modes.md) — Historical mode descriptions
> - [Architecture: State Management](./state-management.md) — Progress tracking
> - [Architecture: UI Layout](./ui-layout.md) — Page layout patterns

**Last Updated**: 2026-03-29

---

## Overview

All puzzle-playing modes in Yen-Go share a single `PuzzleSetPlayer` component backed by `SolverView`. Each mode is a **thin wrapper page** that provides:

1. A `PuzzleSetLoader` (or `StreamingPuzzleSetLoader` for infinite modes)
2. `renderHeader()` — mode-specific header/HUD
3. `renderSummary()` — mode-specific completion/results screen
4. Configuration props (`failOnWrong`, `autoAdvanceEnabled`, `minimal`, etc.)

This eliminates duplicate board rendering, move validation, and puzzle lifecycle management.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────┐
│  Page (thin wrapper)                                │
│  ┌───────────────┐  ┌───────────────────────────┐   │
│  │ PuzzleLoader   │  │ renderHeader / renderSummary│  │
│  │ (implements    │  │ (mode-specific UI)          │  │
│  │  PSL or SPSL) │  │                             │  │
│  └───────┬───────┘  └──────────┬──────────────────┘  │
│          │                     │                     │
│  ┌───────▼─────────────────────▼───────────────────┐ │
│  │         PuzzleSetPlayer                         │ │
│  │  ┌──────────────────────────────────────────┐   │ │
│  │  │ SolverView (board + optional sidebar)    │   │ │
│  │  │ ┌──────────┐  ┌───────────────────────┐ │   │ │
│  │  │ │GobanBoard │  │Hints, SolutionTree,   │ │   │ │
│  │  │ │          │  │MoveExplorer (sidebar) │ │   │ │
│  │  │ └──────────┘  └───────────────────────┘ │   │ │
│  │  └──────────────────────────────────────────┘   │ │
│  └─────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────┘
```

---

## PuzzleSetLoader Interface

```typescript
// services/puzzleLoaders.ts
interface PuzzleSetLoader {
  load(): Promise<void>;
  getStatus(): LoaderStatus;
  getTotal(): number;
  getPuzzleSgf(index: number): Promise<LoaderResult<string>>;
  getEntry(index: number): PuzzleEntryMeta | null;
  getError(): string | null;
}
```

For infinite/streaming modes (Rush, Random):

```typescript
interface StreamingPuzzleSetLoader extends PuzzleSetLoader {
  hasMore(): boolean;
  loadMore(): Promise<number>;
}
```

PuzzleSetPlayer detects streaming loaders via `'hasMore' in loader` and calls `loadMore()` near the end of the loaded set.

---

## Mode Configuration Matrix

| Mode | Page | Loader | `failOnWrong` | `failOnWrongDelayMs` | `autoAdvanceEnabled` | `minimal` | Streaming |
|------|------|--------|---------------|---------------------|---------------------|-----------|-----------|
| Collection | CollectionViewPage | CollectionPuzzleLoader | false | 400 (default) | undefined (global) | false | No |
| Daily | DailyChallengePage | DailyPuzzleLoader | true | 400 (default) | undefined (global) | false | No |
| Training | TrainingViewPage | TrainingPuzzleLoader | false | 400 (default) | undefined (global) | false | No |
| Technique | TechniqueFocusPage | TechniquePuzzleLoader | false | 400 (default) | undefined (global) | false | No |
| Smart Practice | SmartPracticePage | SmartPracticeLoader | false | 400 (default) | undefined (global) | false | No |
| Quality | QualityViewPage | QualityPuzzleLoader | false | 400 (default) | undefined (global) | false | No |
| **Rush** | PuzzleRushPage | **RushPuzzleLoader** | **true** | **100** | **false** | **true** | **Yes** |
| **Random** | RandomChallengePage | **RandomPuzzleLoader** | false | 400 (default) | undefined (global) | false | **Yes** |

---

## SolverView `minimal` Mode

When `minimal={true}`:
- Only the `solver-board-col` renders (the goban board)
- The sidebar column (hints, solution tree, move explorer) is hidden
- Used by Rush mode for maximum board space under time pressure

---

## Rush Mode

**Page**: `PuzzleRushPage.tsx`
**Loader**: `RushPuzzleLoader` (streaming, prefetches next SGF)
**Session hook**: `useRushSession` — manages timer, lives, score, streak

### Page States

1. **Countdown** — 3-2-1 countdown before game starts
2. **Playing** — PuzzleSetPlayer with RushOverlay HUD
3. **Finished** — Results screen (score, best, stats)

### Key Props

```typescript
<PuzzleSetPlayer
  loader={rushLoader}
  mode="rush"
  failOnWrong={true}
  failOnWrongDelayMs={100}    // Fast wrong-move feedback
  autoAdvanceEnabled={false}  // Never auto-advance in rush
  minimal={true}              // Board only, no sidebar
  renderHeader={() => <RushOverlay ... />}
  onPuzzleComplete={handlePuzzleComplete}
/>
```

### Bridge to useRushSession

`onPuzzleComplete` calls `actions.recordCorrect()` or `actions.recordWrong()` based on the `wasCorrect` flag, keeping the timer/lives/score system intact.

### SGF Prefetching (RC-5)

`RushPuzzleLoader.prefetchSgf()` loads the next puzzle's SGF in the background while the current puzzle is being solved, preventing visible skeleton flash between puzzles.

---

## Random Challenge Mode

**Page**: `RandomChallengePage.tsx`
**Loader**: `RandomPuzzleLoader` (streaming, infinite)

### Behavior

- `hasMore()` always returns true — infinite puzzle supply
- `loadMore()` picks a random puzzle from SQLite, avoids repeats via `usedPuzzleIds` set
- Filters by level and optional tag slug

---

## Design Decisions

### Why PuzzleSetPlayer for Everything?

1. **DRY**: Board rendering, move validation, puzzle lifecycle, auto-advance, and progress tracking are identical across modes
2. **Proven**: DailyChallengePage was the first PSP consumer and validated the pattern
3. **Maintainable**: Bug fixes to solving logic fix all 8 modes simultaneously

### Why StreamingPuzzleSetLoader?

Finite loaders (Collection, Daily) know total count upfront. Rush and Random need infinite puzzle supply — `hasMore()` + `loadMore()` extends the interface without breaking existing loaders.

### Why `minimal` mode on SolverView?

Rush needs maximum board real estate under time pressure. Rather than duplicating board rendering (the old InlineSolver approach), SolverView conditionally hides its sidebar.

### Why `failOnWrongDelayMs` as a prop?

Rush uses 100ms (fast feedback), other modes use 400ms (default). This avoids global setting mutation (RC-6) and keeps each mode's UX isolated.
