# Frontend Testing

> **See also**:
>
> - [Architecture: Frontend Overview](./overview.md) — Technology stack
> - [How-To: Playwright Visual Testing](../../how-to/frontend/playwright-visual-testing.md) — How to write and run visual tests
> - [How-To: Run Pipeline](../../how-to/backend/run-pipeline.md) — Backend pipeline execution
> - [Reference: CLI Quick Reference](../../reference/cli-quick-ref.md) — CLI commands

**Last Updated**: 2026-02-20

## Test Stack

| Type          | Framework            | Config                               | Location                 |
| ------------- | -------------------- | ------------------------------------ | ------------------------ |
| Unit          | Vitest 1.6.1 (jsdom) | `vitest.config.ts`                   | `frontend/tests/unit/`   |
| Visual        | Playwright ^1.48     | `playwright.config.ts`               | `frontend/tests/visual/` |
| E2E           | Playwright ^1.48     | `playwright.e2e.config.ts`           | `frontend/tests/e2e/`    |
| Investigation | Playwright ^1.48     | `playwright.investigation.config.ts` | ad-hoc                   |

## Running Tests

```bash
cd frontend

# Unit tests
npm test                    # Watch mode
npm test -- --run           # Single run
npm test -- --coverage      # With coverage

# Visual tests
npm run test:visual         # Run Playwright
npm run test:visual:update  # Update snapshots
```

## Unit Testing (Vitest)

### Structure

```
frontend/tests/
├── unit/               # Vitest unit tests (~1000+ tests)
│   ├── ErrorState.test.tsx
│   ├── ProgressBar.test.tsx
│   ├── slug-formatter.test.ts
│   ├── goban-init.test.ts
│   ├── useGoban.test.ts
│   ├── mastery-badge.test.ts
│   └── ...
├── visual/             # Playwright visual regression
│   ├── specs/          # Visual test specs
│   └── baselines/      # Reference screenshots
├── e2e/                # End-to-end tests
└── setup.ts            # Vitest global setup
```

### Example

```typescript
// tests/lib/puzzle.test.ts
import { describe, it, expect } from "vitest";
import { validateMove } from "../../src/lib/puzzle";

describe("validateMove", () => {
  it("should accept correct first move", () => {
    const puzzle = loadTestPuzzle("simple-capture");
    const result = validateMove(puzzle, "cc");
    expect(result.correct).toBe(true);
  });
});
```

## Visual Testing (Playwright)

### Purpose

Catch visual regressions in UI components, especially the Go board renderer.

### Structure

```
frontend/tests/visual/
├── board.visual.ts
├── achievements.visual.ts
├── baselines/          # Reference screenshots
└── test-results/       # Diff output
```

### Example

```typescript
// tests/visual/board.visual.ts
import { test, expect } from "@playwright/test";

test("board renders 9x9 correctly", async ({ page }) => {
  await page.goto("/test/board-9x9");
  await expect(page.locator(".go-board")).toHaveScreenshot("board-9x9.png");
});
```

### Updating Baselines

```bash
npm run test:visual:update
```

## Coverage Targets

| Area                | Target |
| ------------------- | ------ |
| Core logic (`lib/`) | 90%    |
| Components          | 70%    |
| Services            | 80%    |

## E2E Testing Conventions (Playwright)

### Valid Routes

E2E tests must use the actual app routes. The app uses **path-based routing** (no hash `/#/` routes).

| Route                     | Page                     | Notes                                                    |
| ------------------------- | ------------------------ | -------------------------------------------------------- |
| `/`                       | Home                     | Mode tiles (Daily, Rush, Collections, etc.)              |
| `/collections`            | Collections catalog      | Search, category sections                                |
| `/collections/:id`        | Collection detail        | `id` = `curated-{slug}`, `level-{slug}`, or `tag-{slug}` |
| `/collections/:id/:index` | Puzzle solver            | `index` is 1-based                                       |
| `/daily`                  | Daily challenge browse   | Mode toggle (Standard/Timed)                             |
| `/daily/:date`            | Daily for specific date  | YYYY-MM-DD format                                        |
| `/puzzle-rush`            | Puzzle Rush              | Shows `RushBrowsePage` first, then `PuzzleRushPage`      |
| `/technique/:tag`         | Technique browse         | Browse page, not per-tag solver                          |
| `/training`               | Training level selection | Level cards                                              |
| `/training/:level`        | Training at level        | e.g., `/training/beginner`                               |
| `/random`                 | Random puzzle            | No level parameter                                       |

### Collection ID Prefixes

The `CollectionPuzzleLoader` requires prefixed IDs to route correctly:

| Prefix      | Example                       | Resolves to                                                        |
| ----------- | ----------------------------- | ------------------------------------------------------------------ |
| `curated-`  | `curated-beginner-essentials` | SQL query: `getPuzzlesByCollection(id)` (numeric collection ID)    |
| `level-`    | `level-beginner`              | SQL query: `getPuzzlesByLevel(id)` (numeric level ID, e.g., `120`) |
| `tag-`      | `tag-snapback`                | SQL query: `getPuzzlesByTag(id)` (numeric tag ID, e.g., `30`)      |
| (bare slug) | `beginner`                    | Tries level query first, then `curated-` fallback                  |

**For E2E tests**, always use the full prefixed form: `/collections/curated-beginner-essentials/1`

### Key Test IDs

| Test ID                   | Component            | Notes                               |
| ------------------------- | -------------------- | ----------------------------------- |
| `goban-board`             | SolverView board div | Board container where goban renders |
| `puzzle-counter`          | SolverView sidebar   | Shows "X / Y" puzzle count          |
| `action-bar`              | SolverView sidebar   | Undo/Reset/Next buttons             |
| `solution-tree-container` | SolverView sidebar   | Solution tree (review mode)         |
| `rush-overlay`            | RushOverlay          | Timer, lives, score during Rush     |
| `rush-duration-3/5/10`    | RushBrowsePage       | Duration selection cards            |
| `start-daily`             | DailyBrowsePage      | Start challenge button              |
| `daily-hero-card`         | DailyBrowsePage      | Hero card with date                 |
| `collections-search`      | CollectionsPage      | Search input                        |

### Puzzle Rush Flow

The Puzzle Rush has a two-page flow:

1. **`/puzzle-rush`** → `RushBrowsePage` (when `rushDuration === null`)
   - Duration cards: `rush-duration-3`, `rush-duration-5`, `rush-duration-10`
   - Clicking a card triggers `onStartRush(duration)`
2. **`/puzzle-rush`** → `PuzzleRushPage` (when `rushDuration` is set)
   - Goes directly to countdown (no setup screen — `durationMinutes` is provided)
   - Countdown → Playing → Finished states

### E2E Test Gotchas

- **Home page tiles** use `role="button"`, NOT `role="link"`
- **Daily mode toggle** — "Standard" text appears in both the toggle button AND the "Start Standard Challenge" button. Use `.first()` to avoid strict mode violations
- **Reset/Undo buttons** are `disabled` when no moves have been made — check `isEnabled()` before clicking
- **`goban-board`** will NOT appear if the collection fails to load — verify the collection exists and use `curated-` prefix
- **Vitest exclude**: Playwright test files in `tests/audit/` must be excluded from Vitest via `vitest.config.ts`

## Test Principles

1. **Test behavior, not implementation**
2. **Test first for core logic** (puzzle validation, SGF parsing)
3. **Visual tests for UI regressions**
4. **No mocking of config files** — use real `config/*.json`

## Visual Regression Strategy (Spec 132)

### Baseline Workflow

1. Capture baselines at milestone boundaries (6 pages × 3 viewports × 2 themes = 36 screenshots)
2. Store in `frontend/tests/visual/baselines/{milestone}/`
3. Compare before/after any visual change

### Theme-Aware Screenshots

Visual tests must capture both light and dark mode to verify:

- No bright artifacts in dark mode
- Board surface adapts (Kaya → Night Play)

## Grouped Test Commands (Faster Feedback)

**Default behavior:** `npm test` runs ALL ~900+ vitest tests (~30-40 seconds)

| Command                    | Tests | Time | When to Use            |
| -------------------------- | ----- | ---- | ---------------------- |
| `npm run test:unit`        | ~650  | ~15s | Unit tests only        |
| `npm run test:integration` | ~265  | ~10s | Integration tests only |
| `npm run test:regression`  | ~28   | ~4s  | Regression tests only  |

### Full Command Reference

```bash
npm test                    # Run all vitest tests once
npm run test:watch          # Watch mode for development
npm run test:coverage       # Run with coverage report
npm run test:unit           # Unit tests only (~15s)
npm run test:integration    # Integration tests only (~10s)
npm run test:regression     # Regression tests only (~4s)
npm run test:visual         # Playwright visual tests
npm run test:visual:update  # Update visual baselines
npm run test:visual:ui      # Playwright interactive UI
npm run test:e2e            # End-to-end tests
npm run test:e2e:ui         # E2E interactive debugging UI
npm run test:all            # Full suite (vitest + visual + e2e)
```

### Fine-Grained Groups by Domain

**Group 1: Core SGF & Rules** (~207 tests, ~5s)

```bash
npm test -- --run tests/unit/sgf-*.test.ts tests/unit/rules/*.test.ts tests/unit/rulesEngine.test.ts
```

**Group 2: Tree Visualization** (~60 tests, ~4s)

```bash
npm test -- --run tests/unit/tree/*.test.ts
```

**Group 3: Services** (~174 tests, ~4s)

```bash
npm test -- --run tests/unit/achievement*.test.ts tests/unit/collectionService.test.ts tests/unit/streakManager.test.ts
```

**Group 4: UI Components** (~215 tests, ~7s)

```bash
npm test -- --run tests/unit/solution-tree-component.test.tsx tests/unit/quick-controls.test.tsx tests/unit/qualityBadge.test.tsx tests/unit/qualityBreakdown.test.tsx tests/unit/qualityFallback.test.tsx tests/unit/qualityFilter.test.tsx tests/unit/problem-nav.test.tsx tests/unit/levelList.test.tsx tests/unit/hints.test.tsx tests/unit/DailyChallengeModal.test.tsx tests/unit/variant-toggle.test.tsx tests/unit/keyboard-shortcuts-legend.test.tsx
```

**Group 5: Integration** (~265 tests, ~10s)

```bash
npm run test:integration
```

**Group 6: Regression** (~28 tests, ~4s)

```bash
npm run test:regression
```

## Timeout Configuration

Vitest is configured with safeguards to prevent hanging tests:

| Setting       | Value | Purpose                                       |
| ------------- | ----- | --------------------------------------------- |
| `testTimeout` | 10s   | Max time per individual test                  |
| `hookTimeout` | 10s   | Max time per setup/teardown hook              |
| `bail`        | 5     | Stop after 5 failures (catches runaway tests) |

> If tests hang for more than 60 seconds, something is wrong. The `bail: 5` setting will stop execution after 5 failures to prevent infinite waits.

## Test File Naming Conventions

| Test Type   | File Pattern       | Location                | Example                |
| ----------- | ------------------ | ----------------------- | ---------------------- |
| Unit        | `*.test.ts`        | `tests/unit/`           | `rulesEngine.test.ts`  |
| Integration | `*.test.tsx`       | `tests/integration/`    | `PuzzleView.test.tsx`  |
| Regression  | `*.test.ts(x)`     | `tests/regression/`     | `bug-fix-123.test.ts`  |
| Visual      | `*.visual.spec.ts` | `tests/visual/specs/`   | `Board.visual.spec.ts` |
| E2E         | `*.spec.ts`        | `tests/e2e/`            | `puzzle-flow.spec.ts`  |

> ⚠️ Never mix Playwright test files into `tests/unit/`, `tests/integration/`, or `tests/regression/` — Vitest will attempt to run them and fail.

## AI Agent Guidelines

| Scenario                     | Command                              | Time |
| ---------------------------- | ------------------------------------ | ---- |
| After making changes (quick) | `npm run test:unit`                  | ~15s |
| Domain-specific work         | Use relevant group above             | ~5s+ |
| Before PR submission         | `npm test`                           | ~30s |
| Full suite with visual/E2E   | `npm run test:all`                   | ~60s |

## Cache Isolation Best Practices

**CRITICAL**: The frontend uses multiple independent caches that must ALL be cleared between tests.

| Cache                     | Module                 | Purpose                             |
| ------------------------- | ---------------------- | ----------------------------------- |
| `collectionService` cache | `collectionService.ts` | Caches fetched collection manifests |
| `puzzleLoader` cache      | `puzzleLoader.ts`      | Caches loaded puzzle data           |
| `puzzleValidation` cache  | `puzzleLoader.ts`      | Caches SGF validation results       |

### The `clearAllCaches()` Pattern

Always use `clearAllCaches()` from `collectionService.ts` in `beforeEach` to ensure complete test isolation:

```typescript
import { clearAllCaches } from '../../src/services/collectionService';

beforeEach(() => {
  clearAllCaches(); // Clears ALL caches (collection + puzzleLoader + validation)
  localStorageMock.clear();
  vi.clearAllMocks();
});
```

**Why?** Tests that fetch collections populate the `puzzleLoader` cache. Subsequent tests that don't clear this cache receive stale/cached data, causing intermittent failures.

**Do NOT use** `clearCache()` alone — it only clears the collection service cache, leaving `puzzleLoader` and `puzzleValidation` caches populated.

### Diagnosing Cache-Related Failures

| Symptom                                  | Likely Cause                      | Fix                                    |
| ---------------------------------------- | --------------------------------- | -------------------------------------- |
| Test passes alone, fails in suite        | Cache pollution from prior test   | Add `clearAllCaches()` to `beforeEach` |
| Random intermittent test failures        | Incomplete cache clearing         | Replace `clearCache()` with `clearAllCaches()` |
| Stale data in assertions                 | `puzzleLoader` cache not cleared  | Use `clearAllCaches()` |

## Common Issues

### 1. "Cannot find module" errors

Verify you're running the correct framework:

```bash
# For tests in unit/, integration/, regression/
npm test

# For tests in visual/, e2e/
npm run test:visual   # or npm run test:e2e
```

### 2. Canvas errors in JSDOM

`HTMLCanvasElement.prototype.getContext` errors are expected in Vitest — JSDOM doesn't fully implement Canvas. Tests still pass as long as they don't depend on actual canvas rendering.

### 3. Flaky async component tests

Use `waitFor` helpers rather than arbitrary timeouts:

```typescript
await waitFor(() => {
  expect(screen.getByText('Expected')).toBeInTheDocument();
});
```

## CI/CD Integration

```yaml
# Vitest (unit/integration)
- run: npm test

# Playwright (visual/e2e)
- run: npx playwright install --with-deps
- run: npm run test:visual
```
- Mode accent colors render correctly in both themes
- Stone rendering consistent across themes

### Playwright Configs

| Config                               | Purpose                 | When       |
| ------------------------------------ | ----------------------- | ---------- |
| `playwright.config.ts`               | Visual regression tests | Pre-commit |
| `playwright.e2e.config.ts`           | Functional E2E tests    | Pre-merge  |
| `playwright.investigation.config.ts` | Ad-hoc debugging        | Manual     |
