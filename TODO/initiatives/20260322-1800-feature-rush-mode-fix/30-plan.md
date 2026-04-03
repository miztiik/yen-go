# Plan — Rush Mode Fix (OPT-1: Refactor-First, Two-Phase)

**Initiative**: `20260322-1800-feature-rush-mode-fix`
**Selected Option**: OPT-1 — Refactor-First (Two-Phase)
**Last Updated**: 2026-03-22

---

## Architecture Overview

### Current State
```
app.tsx (~700 lines)
├── RushPuzzle type (L34)
├── getBestScore() (L40-46) — reads dead localStorage key
├── loadRushTagEntries() (L53-60)
├── loadLevelIndex() (L62-76)
├── RushPuzzleRenderer component (L92-145)
├── InlinePuzzleSolver component (L156-186) — hardcoded wrongAttempts >= 3
├── getNextPuzzle() (L360-450)
├── renderPuzzle callback (L491-500)
├── renderRandomPuzzle callback (L506-513)
└── route dispatching for Rush + Random
```

### Target State (After Phase A + B)
```
components/shared/InlineSolver/
├── InlineSolver.tsx          — extracted from app.tsx, adds maxAttempts prop
└── InlineSolver.test.tsx     — unit tests for maxAttempts behavior (Phase B)

components/Rush/
├── RushPuzzleRenderer.tsx    — extracted from app.tsx
├── RushOverlay.tsx           — existing (fix overlay positioning in Phase B)
└── index.ts                  — barrel export

services/
├── puzzleRushService.ts      — extracted: getNextPuzzle, loadLevelIndex, loadRushTagEntries
└── puzzleRushService.test.ts — unit tests (Phase B)

types/goban.ts                — RushPuzzle type added (alongside existing RushDuration)

pages/
├── PuzzleRushPage.tsx        — wrap in PageLayout, replace emojis (Phase B)
└── RushBrowsePage.tsx        — wire masterLoaded to SQLite data (Phase B)

app.tsx                       — ~470 lines removed; imports from new modules
```

---

## Phase A: Pure Refactor (Zero Behavior Change)

### Design Decisions

| DA | Decision | Rationale |
|----|----------|-----------|
| DA-1 | Extract `InlinePuzzleSolver` → `components/shared/InlineSolver/InlineSolver.tsx` | Shared by Rush and Random modes. Must be importable, not app.tsx-internal. |
| DA-2 | Extract `RushPuzzleRenderer` → `components/Rush/RushPuzzleRenderer.tsx` | Co-located with `RushOverlay` in existing Rush component directory. |
| DA-3 | Move `RushPuzzle` type → `types/goban.ts` | `RushDuration` and `RushSessionState` already live there. Cohesive type file. |
| DA-4 | Extract `getNextPuzzle`, `loadLevelIndex`, `loadRushTagEntries` → `services/puzzleRushService.ts` | Follows pattern: `dailyChallengeService.ts`, `collectionService.ts`. |
| DA-5 | Remove dead `getBestScore()` from app.tsx | Reads `yen-go-rush-best-score` that nothing writes. Replace usage with `getRushHighScore()` from progress system. |
| DA-6 | Keep `renderPuzzle` / `renderRandomPuzzle` callbacks in app.tsx | These are route-level wiring — they belong in the route dispatcher. They now import from extracted modules. |

### Safety Guarantee
- **Zero behavior change**: All existing tests must pass unchanged after Phase A
- `InlinePuzzleSolver` keeps its hardcoded `wrongAttempts >= 3` in Phase A (changed in Phase B)
- App.tsx imports from new locations; no logic changes

---

## Phase B: Bug Fixes + Theme Alignment

### Design Decisions

| DB | Decision | Rationale |
|----|----------|-----------|
| DB-1 | Add `maxAttempts` prop to `InlineSolver` (default=3) | Rush passes `maxAttempts={1}`, Random uses default 3. DRY — one component, two configs. |
| DB-2 | Replace `getBestScore()` usage with `getRushHighScore()` | The progress system already has the correct function. Just wire it. |
| DB-3 | Wrap `PuzzleRushPage` in `<PageLayout variant="single-column" mode="rush">` | Matches `RushBrowsePage` pattern. Gets consistent padding, scroll, and CSS variable cascade. |
| DB-4 | Restructure `RushOverlay` so overlays are siblings of content, not inside HUD bar | Paused/game-over overlays need to cover the full page. Move overlay divs to be children of the page-level container, not the HUD bar. |
| DB-5 | Create `FireIcon` SVG and `PauseIcon` SVG | No existing fire/pause icons in the icon library. Follow `StreakIcon` pattern. Replace `🔥` and `⏸`. |
| DB-6 | Wire `masterLoaded` to actual puzzle count from SQLite | Follow `TechniqueBrowsePage` pattern — query `puzzleQueryService` for counts, set `masterLoaded = true` when data arrives. |
| DB-7 | Add `audioService.play('correct'/'wrong')` in `InlineSolver` callbacks | Already imported in app.tsx. Pass audio callback or integrate directly. |
| DB-8 | Fix E2E test paths from `/puzzle-rush` to `/modes/rush` | Simple string replacement in 4-6 test files. |

---

## Data Model Impact

No data model changes. No schema changes. No backend changes.

**localStorage impact**: The dead `yen-go-rush-best-score` key will no longer be read. Existing data in the progress system (`statistics.rushHighScores`) is the source of truth and already works correctly.

---

## Risks & Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| R-1: Breaking RandomChallengePage during refactor | High | AC-7 explicitly tests Random retains 3-retry. Phase A is zero-behavior-change. |
| R-2: Board sizing regression after PageLayout wrapping | Medium | Visual comparison before/after. PuzzleRushPage currently does `min-h-[calc(100vh-3.5rem)]` which PageLayout handles. |
| R-3: InlineSolver maxAttempts=1 may feel too harsh | Low | Q2:A resolved this — strict Rush is intentional. Matches chess.com Puzzle Rush UX. |
| R-4: RushOverlay restructuring changes DOM order | Medium | E2E tests verify overlay visibility. `data-testid` attributes preserved. |
| R-5: Filter data loading slows browse page | Low | SQLite queries are ~2ms. Same pattern used by TechniqueBrowsePage successfully. |

---

## Contracts & Interfaces

### InlineSolver Props (Phase B addition)
```typescript
interface InlineSolverProps {
  sgf: string;
  onComplete: (success: boolean) => void;
  maxAttempts?: number; // default: 3. Rush passes 1.
  onAudioFeedback?: (type: 'correct' | 'wrong') => void; // optional audio callback
}
```

### puzzleRushService.ts Exports
```typescript
export interface RushPuzzle extends CollectionPuzzleEntry {
  level: SkillLevel;
  tags: readonly string[];
}

export function getNextPuzzle(
  levelIndex: Map<string, { path: string; tags: readonly string[]; level: string }[]>,
  rushTagEntries: readonly { path: string; level: string }[],
  usedPuzzleIds: Set<string>,
  levelId?: number,
  tagId?: number,
): RushPuzzle | null;

export function loadLevelIndex(levelSlug: string): Promise<{ success: boolean; data?: { entries: ... } }>;
export function loadRushTagEntries(tagId: number): Promise<readonly { path: string; level: string }[]>;
```

---

## Documentation Plan

| doc_id | Action | File | Why |
|--------|--------|------|-----|
| DOC-1 | Update | `frontend/src/AGENTS.md` | Add InlineSolver, puzzleRushService, RushPuzzleRenderer module entries. Remove app.tsx Rush code references. |
| DOC-2 | Update | `frontend/CLAUDE.md` | Note Rush mode component architecture if mentioned. |
| DOC-3 | No change | `docs/` | No user-facing documentation impact — this is an internal bug fix. |

> **See also**:
> - [Charter: 00-charter.md](./00-charter.md) — Goals and acceptance criteria
> - [Options: 25-options.md](./25-options.md) — OPT-1 selection rationale
> - [Research: 15-research.md](../20260322-research-rush-timed-puzzle-audit/15-research.md) — Full audit
