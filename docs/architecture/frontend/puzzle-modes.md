# Puzzle Modes Architecture

> **⚠️ Partially superseded**: See [Playing Modes — Unified Architecture](./playing-modes.md) for the current PuzzleSetPlayer-based architecture. This document retains historical mode descriptions.

> **See also**:
>
> - [Architecture: Playing Modes](./playing-modes.md) — Current unified PuzzleSetPlayer architecture
> - [Architecture: Puzzle Solving](./puzzle-solving.md) — Core validation logic
> - [Architecture: State Management](./state-management.md) — Progress tracking
> - [Concepts: Levels](../../concepts/levels.md) — Difficulty system

**Last Updated**: 2026-03-29

How different puzzle-solving modes are implemented.

---

## Mode Overview

| Mode     | Description           | Time Limit | Progress Tracking |
| -------- | --------------------- | ---------- | ----------------- |
| Standard | Solve at your pace    | None       | Per-puzzle        |
| Daily    | Daily challenge       | None       | Streak-based      |
| Rush     | Solve many fast       | 3min/5min  | Best score        |
| Review   | Post-solve review     | None       | N/A               |

---

## Standard Mode

The default mode for learning.

### Behavior

- Select puzzle by level, tag, or collection
- Unlimited time
- Hints available (0-3)
- Can retry incorrect moves
- Progress saved per puzzle

### State Machine

```
LOADING → READY → SOLVING → COMPLETE
                    │
                    ├── User move correct → (continue/complete)
                    ├── User move incorrect → SOLVING (retry)
                    └── User requests hint → SOLVING (hint revealed)
```

### Implementation

```typescript
interface PracticeState {
  puzzle: Puzzle;
  currentNode: MoveNode;
  hintsRevealed: number;
  attempts: number;
  startTime: number;
}

function practiceModeReducer(
  state: PracticeState,
  action: PracticeAction,
): PracticeState {
  switch (action.type) {
    case "MOVE_PLAYED":
      return handleMove(state, action.move);
    case "HINT_REQUESTED":
      return revealHint(state);
    case "RETRY":
      return resetToStart(state);
  }
}
```

---

## Daily Challenge Mode

One curated puzzle per day.

### Behavior

- New puzzle at midnight UTC
- Same puzzle for all users (deterministic selection)
- Streak tracking (consecutive days)
- Calendar view of past completions

### Puzzle Selection

Daily challenges are pre-generated and stored in SQLite tables inside `yengo-search.db`:

- `daily_schedule` — One row per date (version, generated_at, technique_of_day, attrs)
- `daily_puzzles` — Many-to-many: date ↔ puzzles (section, position)

Sections: `standard`, `timed`, `by_tag`. The frontend queries these tables via sql.js WASM — no JSON files are used.

### State

```typescript
interface DailyState {
  currentDate: string; // YYYY-MM-DD
  puzzle: Puzzle | null;
  completed: boolean;
  streak: {
    current: number;
    best: number;
    lastDate: string; // Last completion date
  };
}

function calculateStreak(
  lastDate: string,
  currentDate: string,
  wasCompleted: boolean,
): number {
  if (!wasCompleted) return 0;

  const last = new Date(lastDate);
  const current = new Date(currentDate);
  const diffDays = daysBetween(last, current);

  if (diffDays === 1) return state.streak.current + 1;
  if (diffDays === 0) return state.streak.current;
  return 1; // Streak broken
}
```

### Calendar View

```typescript
interface CalendarDay {
  date: string;
  completed: boolean;
  puzzleId?: string;
}

function getCalendarMonth(year: number, month: number): CalendarDay[] {
  const days: CalendarDay[] = [];
  const daysInMonth = getDaysInMonth(year, month);

  for (let day = 1; day <= daysInMonth; day++) {
    const date = `${year}-${pad(month)}-${pad(day)}`;
    days.push({
      date,
      completed: isPuzzleSolvedOnDate(date),
      puzzleId: getDailyPuzzleId(date),
    });
  }
  return days;
}
```

---

## Rush Mode

Solve as many puzzles as possible under time pressure.

### Variants

- **3 Minute Rush**: 180 seconds
- **5 Minute Rush**: 300 seconds

### Behavior

- Random puzzles from lower difficulties
- One attempt per puzzle (no hints)
- Wrong answer = skip (no penalty)
- Score = puzzles solved
- Leaderboard (local best scores)

### State

```typescript
interface RushState {
  variant: "3min" | "5min";
  timeRemaining: number; // milliseconds
  score: number;
  currentPuzzle: Puzzle;
  puzzleQueue: Puzzle[]; // Pre-fetched
  isRunning: boolean;
}

function rushReducer(state: RushState, action: RushAction): RushState {
  switch (action.type) {
    case "START":
      return startRush(state);
    case "CORRECT_MOVE":
      return {
        ...state,
        score: state.score + 1,
        currentPuzzle: state.puzzleQueue.shift()!,
      };
    case "INCORRECT_MOVE":
      return {
        ...state,
        currentPuzzle: state.puzzleQueue.shift()!,
      };
    case "TICK":
      return handleTick(state, action.deltaMs);
    case "TIME_UP":
      return endRush(state);
  }
}
```

### Timer Implementation

```typescript
function useRushTimer(onTimeUp: () => void) {
  const [remaining, setRemaining] = useState(0);
  const intervalRef = useRef<number>();

  const start = (durationMs: number) => {
    setRemaining(durationMs);
    intervalRef.current = setInterval(() => {
      setRemaining((r) => {
        if (r <= 100) {
          clearInterval(intervalRef.current);
          onTimeUp();
          return 0;
        }
        return r - 100;
      });
    }, 100);
  };

  const stop = () => clearInterval(intervalRef.current);

  return { remaining, start, stop };
}
```

### Puzzle Queue

Pre-fetch puzzles to avoid delays:

```typescript
async function prefetchRushPuzzles(count: number): Promise<Puzzle[]> {
  // Select from easier levels for rush
  const levels = ["novice", "beginner", "elementary"];
  const puzzles: Puzzle[] = [];

  for (let i = 0; i < count; i++) {
    const level = levels[Math.floor(Math.random() * levels.length)];
    const puzzle = await fetchRandomPuzzle(level);
    puzzles.push(puzzle);
  }

  return puzzles;
}
```

---

## Mode Selection UI

Modes are presented on the home page via `HomePageGrid`. Each mode has a distinct page color identity (see [structure.md](./structure.md)).

---

## Cross-Mode Progress

Some achievements span modes:

```typescript
const CROSS_MODE_ACHIEVEMENTS = [
  {
    id: "well-rounded",
    name: "Well Rounded",
    description: "Complete puzzles in all modes",
    check: (state) =>
      state.standard.solvedCount > 0 &&
      state.daily.completedCount > 0 &&
      state.rush.bestScore > 0,
  },
];
```
