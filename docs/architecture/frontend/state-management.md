# State Management

> **See also**:
>
> - [Architecture: Frontend Overview](./overview.md) — Technology stack
> - [Architecture: Puzzle Solving](./puzzle-solving.md) — Validation flow
> - [How-To: Frontend Development](../../how-to/frontend/) — Implementation guides

**Last Updated**: 2026-02-01

How user state is persisted without a backend.

---

## Design Principle

**Local-First** — All user data lives in `localStorage` only.

Benefits:

- Works offline
- No backend infrastructure
- Instant state access
- Privacy-friendly

Tradeoffs:

- Device-bound (no sync)
- Browser storage limits (~5MB)
- Data loss on clear

---

## Storage Namespace

All keys prefixed to avoid conflicts:

```typescript
const STORAGE_PREFIX = "yengo:";

function getKey(name: string): string {
  return `${STORAGE_PREFIX}${name}`;
}
```

---

## State Categories

### 1. User Progress

Tracks which puzzles are solved:

```typescript
interface ProgressState {
  version: 2;
  solved: Record<string, SolvedPuzzle>; // puzzleId → data
  stats: UserStats;
}

interface SolvedPuzzle {
  solvedAt: string; // ISO timestamp
  attempts: number; // Tries to solve
  hintsUsed: number; // 0-3
  timeMs: number; // Solve time
}

interface UserStats {
  totalSolved: number;
  streakDays: number;
  lastSolvedDate: string; // YYYY-MM-DD
}
```

Storage key: `yengo:progress`

### 2. Preferences

User settings:

```typescript
interface PreferencesState {
  version: 1;
  theme: "light" | "dark" | "system";
  boardStyle: "classic" | "minimal";
  soundEnabled: boolean;
  showCoordinates: boolean;
  autoAdvance: boolean; // Auto-load next puzzle
}
```

Storage key: `yengo:preferences`

### 3. Achievements

Unlocked achievements:

```typescript
interface AchievementsState {
  version: 1;
  unlocked: Record<string, UnlockedAchievement>;
}

interface UnlockedAchievement {
  unlockedAt: string;
  puzzleId?: string; // Which puzzle triggered it
}
```

Storage key: `yengo:achievements`

### 4. Rush Mode

Puzzle rush state:

```typescript
interface RushState {
  version: 1;
  bestScores: {
    threeMin: number;
    fiveMin: number;
    survival: number;
  };
  history: RushAttempt[]; // Last 10 attempts
}
```

Storage key: `yengo:rush`

---

## Schema Versioning

Every state object includes a `version` field:

```typescript
function loadState<T>(key: string, migrate: Migrator<T>): T {
  const raw = localStorage.getItem(getKey(key));
  if (!raw) return migrate.default();

  const data = JSON.parse(raw);
  return migrate.toLatest(data);
}
```

### Migration Example

```typescript
const progressMigrator: Migrator<ProgressState> = {
  default: () => ({ version: 2, solved: {}, stats: defaultStats }),

  toLatest: (data) => {
    // v1 → v2: added stats field
    if (data.version === 1) {
      data.version = 2;
      data.stats = computeStatsFromSolved(data.solved);
    }
    return data;
  },
};
```

---

## State Access Patterns

### Read State

```typescript
function getProgress(): ProgressState {
  return loadState("progress", progressMigrator);
}
```

### Update State

Immutable updates:

```typescript
function markPuzzleSolved(puzzleId: string, result: SolveResult): void {
  const progress = getProgress();

  const updated: ProgressState = {
    ...progress,
    solved: {
      ...progress.solved,
      [puzzleId]: {
        solvedAt: new Date().toISOString(),
        attempts: result.attempts,
        hintsUsed: result.hintsUsed,
        timeMs: result.timeMs,
      },
    },
    stats: updateStats(progress.stats, result),
  };

  saveState("progress", updated);
}
```

### Save State

```typescript
function saveState<T>(key: string, state: T): void {
  try {
    localStorage.setItem(getKey(key), JSON.stringify(state));
  } catch (e) {
    if (e.name === "QuotaExceededError") {
      handleStorageQuotaExceeded();
    }
    throw e;
  }
}
```

---

## Reactive State

Using Preact signals for UI reactivity:

```typescript
import { signal, computed } from '@preact/signals';

// Global progress signal
export const progressSignal = signal<ProgressState>(getProgress());

// Derived state
export const solvedCount = computed(() =>
  Object.keys(progressSignal.value.solved).length
);

// Update triggers UI refresh
function markSolved(puzzleId: string, result: SolveResult) {
  const updated = /* compute new state */;
  progressSignal.value = updated;
  saveState('progress', updated);
}
```

---

## Quota Management

localStorage has ~5MB limit:

```typescript
function handleStorageQuotaExceeded(): void {
  // Option 1: Prune old data
  pruneOldSolvedPuzzles();

  // Option 2: Warn user
  showWarning("Storage is full. Oldest progress may be lost.");
}

function pruneOldSolvedPuzzles(): void {
  const progress = getProgress();
  const sorted = Object.entries(progress.solved).sort((a, b) =>
    a[1].solvedAt.localeCompare(b[1].solvedAt),
  );

  // Keep only last 1000 puzzles
  const toKeep = sorted.slice(-1000);
  progress.solved = Object.fromEntries(toKeep);
  saveState("progress", progress);
}
```

---

## State Export/Import

For user data portability:

```typescript
function exportUserData(): string {
  const data = {
    progress: getProgress(),
    preferences: getPreferences(),
    achievements: getAchievements(),
    rush: getRushState(),
    exportedAt: new Date().toISOString(),
  };
  return JSON.stringify(data, null, 2);
}

function importUserData(json: string): void {
  const data = JSON.parse(json);
  // Validate and migrate each section
  saveState("progress", progressMigrator.toLatest(data.progress));
  saveState("preferences", preferencesMigrator.toLatest(data.preferences));
  // etc.
}
```

---

## Testing State

In tests, mock localStorage:

```typescript
// tests/utils/mockStorage.ts
export function mockLocalStorage(): Storage {
  let store: Record<string, string> = {};
  return {
    getItem: (key) => store[key] || null,
    setItem: (key, value) => {
      store[key] = value;
    },
    removeItem: (key) => {
      delete store[key];
    },
    clear: () => {
      store = {};
    },
    get length() {
      return Object.keys(store).length;
    },
    key: (i) => Object.keys(store)[i] || null,
  };
}
```
