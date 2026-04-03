# Plan: Rush/Progress Component Tests

**Last Updated:** 2026-03-24
**Selected Option:** OPT-1 (co-located `__tests__` dirs)

## Architecture

No architecture changes. Tests are additive `.test.tsx` files using existing vitest + jsdom + @testing-library/preact infrastructure.

## Dependencies Confirmed

- `@testing-library/preact@^3.2.4` — in devDependencies ✅
- `vitest@^1.1.0` — in devDependencies ✅
- `jsdom@^23.0.1` — in devDependencies ✅
- `@preact/preset-vite` — JSX transform ✅
- vitest `globals: true` — `describe`/`it`/`expect` available globally ✅
- vitest `setupFiles: ['./tests/setup.ts']` — `cleanup()`, `localStorage` mock, `matchMedia` mock ✅

## Mock Strategy

All component tests must mock heavy dependencies to stay fast and isolated:

### Score.test.tsx — Minimal mocks
- **No mocks needed**: `Score` is a pure presentational component. Props in → DOM out.
- CSS import: handled by vitest (auto-stubbed in jsdom).
- `FireIcon`: real component (lightweight SVG, no side effects).

### Results.test.tsx — Mock rush lib functions
- `vi.mock('../../lib/rush')` — mock `calculateRank` and `formatDetailedTime` to return predictable values.
- `FireIcon`: render real (lightweight SVG).

### PuzzleRushPage.test.tsx — Heavy mocking required
- `vi.mock('../hooks/useRushSession')` — return controllable state object.
- `vi.mock('../services/progress')` — stub `recordRushScore`.
- `vi.mock('../components/Rush')` — stub `RushOverlay` to avoid deep rendering.
- `vi.mock('../components/Layout')` — stub `PageLayout` as passthrough.
- `vi.mock('../components/shared/Button')` — stub as `<button>`.
- `vi.mock('../components/shared/ErrorState')` — stub.
- `vi.mock('../components/shared/icons')` — stub icon components.
- `vi.mock('../lib/accuracy-color')` — stub `getAccuracyColorClass` → `''`.

---

## File 1: `frontend/src/components/Rush/__tests__/Score.test.tsx`

### Props interface
```ts
interface ScoreProps {
  state: ScoringState;   // { totalScore, currentStreak, longestStreak, isPerfect, puzzleCount, puzzleScores }
  lastScore?: PuzzleScore | null;  // { basePoints, timeBonus, streakBonus, skipPenalty, total }
  showBreakdown?: boolean;
  className?: string;
}
```

### Test cases (6 tests)

| ID | Test | Assertion |
|----|------|-----------|
| S1 | renders total score value | `screen.getByText('250')` for state.totalScore=250 |
| S2 | renders Score label | `screen.getByText('Score')` |
| S3 | renders streak value | `screen.getByText(/5/)` for currentStreak=5 |
| S4 | shows FireIcon when streak ≥ 3 | streak=3 → `container.querySelector('svg')` inside streak span |
| S5 | hides FireIcon when streak < 3 | streak=2 → no SVG in streak element |
| S6 | shows perfect badge when isPerfect && puzzleCount > 0 | `screen.getByText('✨')` |
| S7 | hides perfect badge when isPerfect but puzzleCount = 0 | `queryByText('✨')` → null |
| S8 | renders breakdown when showBreakdown + lastScore | `screen.getByText('+100')` for basePoints, `screen.getByText('+25 time')` for timeBonus |

### CompactScore sub-component (2 tests)

| ID | Test | Assertion |
|----|------|-----------|
| CS1 | renders compact score value | `screen.getByText('150')` |
| CS2 | shows streak multiplier with fire at ≥3 | `screen.getByText(/x3/)` + SVG present |

**Total: ~10 tests**

---

## File 2: `frontend/src/components/Rush/__tests__/Results.test.tsx`

### Props interface
```ts
interface ResultsProps {
  score: number;
  totalTimeMs: number;
  queueState: QueueState;  // { items, currentIndex, completedCount, correctCount, skippedCount }
  longestStreak: number;
  isPerfect: boolean;
  timedOut: boolean;
  onPlayAgain?: () => void;
  onHome?: () => void;
  className?: string;
}
```

### Test cases (8 tests)

| ID | Test | Assertion |
|----|------|-----------|
| R1 | renders "Time's Up!" when timedOut=true | `screen.getByText("Time's Up!")` |
| R2 | renders "Rush Complete!" when timedOut=false | `screen.getByText('Rush Complete!')` |
| R3 | renders final score value | `screen.getByText('500')` |
| R4 | renders rank letter from calculateRank | Mock returns `{rank:'A', title:'Expert'}` → `screen.getByText('A')` |
| R5 | renders accuracy percentage | correctCount=8, completedCount=10 → `screen.getByText('80%')` |
| R6 | renders longest streak with FireIcon at ≥3 | longestStreak=5 → SVG inside stat |
| R7 | renders Play Again button and fires callback | `screen.getByText('Play Again')` → click → expect `onPlayAgain` called |
| R8 | renders skipped count when skippedCount > 0 | skippedCount=3 → `screen.getByText('3')` in Skipped stat |
| R9 | hides skipped stat when skippedCount = 0 | `queryByText('Skipped')` → null |
| R10 | shows perfect badge when isPerfect | `screen.getByText(/Perfect Run/)` |

**Total: ~10 tests**

---

## File 3: `frontend/src/pages/__tests__/PuzzleRushPage.test.tsx`

### Props interface
```ts
interface PuzzleRushPageProps {
  durationMinutes?: number;
  selectedLevelId?: number | null;
  selectedTagId?: number | null;
  onNavigateHome: () => void;
  onNewRush: () => void;
  getNextPuzzle: () => Promise<RushPuzzle | null>;
  renderPuzzle?: (puzzle, onComplete) => JSX.Element;
  puzzle?: LoadedPuzzle;
  testId?: string;
}
```

### Test cases (7 tests)

| ID | Test | Assertion |
|----|------|-----------|
| P1 | renders with PageLayout mode="rush" | Mock PageLayout captures `mode` prop → assert `mode === 'rush'` |
| P2 | starts in countdown state with "Get ready!" | `screen.getByText('Get ready!')` |
| P3 | shows countdown number | `screen.getByTestId('countdown-value')` |
| P4 | renders custom testId | `testId="my-rush"` → `screen.getByTestId('my-rush')` |
| P5 | finished state shows "Game Over!" heading | Simulate `useRushSession` returning `isGameOver=true` → `screen.getByText('Game Over!')` |
| P6 | finished state shows final score | `screen.getByTestId('final-score')` |
| P7 | finished state shows Play Again button | `screen.getByTestId('play-again-button')` → click → `onNewRush` called |
| P8 | finished state shows Go Home button | `screen.getByTestId('home-button')` → click → `onNavigateHome` called |

**Total: ~8 tests**

---

## Grand Total: ~28 test cases across 3 files (exceeds ≥15 target)

## Documentation Plan

No documentation updates needed — test-only addition.

## Risks & Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| CSS imports fail in jsdom | Low | vitest auto-stubs CSS; `@preact/preset-vite` handles this. Confirmed by existing tests. |
| `useRushSession` hook is complex to mock | Medium | Mock the entire hook module; return a controlled state object per test. Pattern already used in existing tests. |
| Timer `setInterval` in PuzzleRushPage countdown | Medium | Use `vi.useFakeTimers()` + `vi.advanceTimersByTime()` for countdown tests. Call `vi.useRealTimers()` in cleanup (already in setup.ts). |
| `calculateRank` / `formatDetailedTime` internal logic | Low | Mock `../../lib/rush` module; return predictable `{rank, title, nextRank}`. |
