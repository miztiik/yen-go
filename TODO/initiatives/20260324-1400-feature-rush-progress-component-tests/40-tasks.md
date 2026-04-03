# Tasks

**Last Updated:** 2026-03-24

## Dependency Order

T1 and T2 are independent (parallel-safe). T3 depends on mock patterns established in T1/T2.
T4 depends on all prior tasks.

---

## Task List

| ID | Task | File(s) | Tests | Deps | Parallel |
|----|------|---------|-------|------|----------|
| T1 | Create Score component tests | `frontend/src/components/Rush/__tests__/Score.test.tsx` | ~10 | — | [P] |
| T2 | Create Results component tests | `frontend/src/components/Rush/__tests__/Results.test.tsx` | ~10 | — | [P] |
| T3 | Create PuzzleRushPage tests | `frontend/src/pages/__tests__/PuzzleRushPage.test.tsx` | ~8 | T1, T2 (pattern) | — |
| T4 | Regression verification | (no files) | — | T1, T2, T3 | — |

---

## T1: Score.test.tsx [P]

**File:** `frontend/src/components/Rush/__tests__/Score.test.tsx`

**Mocks needed:**
- None required (pure presentational component)
- CSS import auto-stubbed by vitest

**Test cases:**

```
describe('Score', () => {
  S1: renders total score value from state.totalScore
  S2: renders "Score" label text
  S3: renders current streak value from state.currentStreak
  S4: shows FireIcon (SVG) when currentStreak >= 3
  S5: does NOT show FireIcon when currentStreak < 3
  S6: shows perfect badge (✨) when isPerfect=true AND puzzleCount > 0
  S7: hides perfect badge when isPerfect=true but puzzleCount = 0
  S8: renders breakdown items when showBreakdown=true and lastScore provided
      - basePoints: "+100"
      - timeBonus: "+25 time"
      - streakBonus: "+10 streak"
      - skipPenalty: "-10 skip"
})

describe('CompactScore', () => {
  CS1: renders compact score value
  CS2: shows streak multiplier "x3" with FireIcon when streak >= 3
})
```

**Fixture data:**
```ts
const baseScoringState: ScoringState = {
  totalScore: 250,
  currentStreak: 5,
  longestStreak: 7,
  isPerfect: false,
  puzzleCount: 3,
  puzzleScores: [],
};

const baseLastScore: PuzzleScore = {
  basePoints: 100,
  timeBonus: 25,
  streakBonus: 10,
  skipPenalty: 0,
  total: 135,
};
```

---

## T2: Results.test.tsx [P]

**File:** `frontend/src/components/Rush/__tests__/Results.test.tsx`

**Mocks needed:**
```ts
vi.mock('../../../lib/rush', () => ({
  calculateRank: vi.fn(() => ({ rank: 'A', title: 'Expert', nextRank: 'S', nextRankScore: 1000 })),
  formatDetailedTime: vi.fn(() => '2:30'),
}));
```

**Test cases:**

```
describe('Results', () => {
  R1: renders "Time's Up!" title when timedOut=true
  R2: renders "Rush Complete!" title when timedOut=false
  R3: renders the score value
  R4: renders rank letter from calculateRank mock ('A')
  R5: renders rank title ('Expert')
  R6: computes and renders accuracy (correctCount/completedCount * 100)
  R7: renders longest streak with FireIcon at >= 3
  R8: renders "Play Again" button; click fires onPlayAgain
  R9: renders skipped count stat when skippedCount > 0
  R10: hides skipped stat when skippedCount = 0
  R11: renders perfect badge when isPerfect=true
})
```

**Fixture data:**
```ts
const baseQueueState: QueueState = {
  items: [],
  currentIndex: 0,
  completedCount: 10,
  correctCount: 8,
  skippedCount: 2,
};

const baseProps: ResultsProps = {
  score: 500,
  totalTimeMs: 150000,
  queueState: baseQueueState,
  longestStreak: 5,
  isPerfect: false,
  timedOut: true,
  onPlayAgain: vi.fn(),
  onHome: vi.fn(),
};
```

---

## T3: PuzzleRushPage.test.tsx

**File:** `frontend/src/pages/__tests__/PuzzleRushPage.test.tsx`

**Mocks needed:**
```ts
// Hook mock (controls page behavior)
vi.mock('../../hooks/useRushSession', () => ({
  useRushSession: vi.fn(),
}));

// Service mocks
vi.mock('../../services/progress', () => ({
  recordRushScore: vi.fn(),
}));

// Component stubs (prevent deep rendering)
vi.mock('../../components/Rush', () => ({
  RushOverlay: () => <div data-testid="rush-overlay" />,
}));

vi.mock('../../components/Layout', () => ({
  PageLayout: ({ children, mode }: any) => <div data-testid="page-layout" data-mode={mode}>{children}</div>,
}));

vi.mock('../../components/shared/Button', () => ({
  Button: ({ children, onClick, ...props }: any) => <button onClick={onClick} {...props}>{children}</button>,
}));

vi.mock('../../components/shared/ErrorState', () => ({
  ErrorState: ({ message }: any) => <div>{message}</div>,
}));

vi.mock('../../components/shared/icons', () => ({
  HeartIcon: () => <span>♥</span>,
  FireIcon: () => <span>🔥</span>,
}));

vi.mock('../../lib/accuracy-color', () => ({
  getAccuracyColorClass: () => '',
}));
```

**useRushSession mock factory:**
```ts
function mockRushSession(overrides = {}) {
  return {
    state: { score: 0, lives: 3, maxLives: 3, puzzlesSolved: 0, puzzlesFailed: 0,
             currentStreak: 0, timeRemaining: 180, ...overrides },
    actions: { start: vi.fn(), pause: vi.fn(), resume: vi.fn(), recordCorrect: vi.fn(),
               recordWrong: vi.fn(), skip: vi.fn(), reset: vi.fn() },
    isGameOver: false,
    isPaused: false,
    timeDisplay: '3:00',
    ...overrides,
  };
}
```

**Test cases:**

```
describe('PuzzleRushPage', () => {
  P1: renders PageLayout with mode="rush"
      → getByTestId('page-layout').dataset.mode === 'rush'

  P2: starts in countdown state showing "Get ready!"
      → getByText('Get ready!')

  P3: renders countdown value element
      → getByTestId('countdown-value')

  P4: accepts custom testId prop
      → testId="custom-rush" → getByTestId('custom-rush')

  P5: finished state renders "Game Over!" heading
      → Mock useRushSession with isGameOver=true, use fake timers to advance past countdown
      → getByText('Game Over!')

  P6: finished state renders final score display
      → getByTestId('final-score')

  P7: finished state Play Again button calls onNewRush
      → getByTestId('play-again-button') → click → expect(onNewRush).toHaveBeenCalled()

  P8: finished state Go Home button calls onNavigateHome
      → getByTestId('home-button') → click → expect(onNavigateHome).toHaveBeenCalled()
})
```

---

## T4: Regression Verification

**Command:**
```bash
cd frontend && npx vitest run --no-coverage
```

**Acceptance:**
- All 3 new test files appear in output
- All existing tests still pass
- ≥15 new test cases pass (target: ~28)
- Zero production file changes (verify with `git diff --name-only`)

---

## Summary

| File | Tests | Mocks |
|------|-------|-------|
| Score.test.tsx | ~10 | None (pure component) |
| Results.test.tsx | ~10 | `calculateRank`, `formatDetailedTime` |
| PuzzleRushPage.test.tsx | ~8 | `useRushSession`, `recordRushScore`, 5 component stubs |
| **Total** | **~28** | |
