# Tasks — Adaptive Learning Engine

> Last Updated: 2026-03-18
> Selected Option: **OPT-1 — Lazy Join**

## Task Dependency Graph

```
T1 (route) ──┐
T2 (analytics)┼──→ T5 (ProgressPage) ──→ T8 (smart practice page)
T3 (retry)  ──┤                          T9 (integration tests)
T4 (achieve) ─┘                          T10 (docs + AGENTS.md)
T6 (UserProfile onClick) ──→ T7 (app.tsx wiring)
[P] = parallelizable
```

## Checklist

### Phase 1: Foundation Services [P — all parallel]

- [x] **T1** — Add `progress` and `smart-practice` route types
  - File: `frontend/src/lib/routing/routes.ts`
  - Add `| { readonly type: 'progress' }` and `| { readonly type: 'smart-practice'; readonly techniques?: string[] }` to Route union
  - Add parse cases: `/progress` → `{ type: 'progress' }`, `/smart-practice` → `{ type: 'smart-practice' }`
  - Add serialize cases
  - Test: unit test for parseRoute/serializeRoute roundtrip
  - **Decommission**: Delete union members + parse/serialize cases

- [x] **T2** — Create `progressAnalytics.ts` service [P with T1, T3, T4]
  - File: `frontend/src/services/progressAnalytics.ts`
  - Implements: `computeProgressSummary()`, `getWeakestTechniques(n)`
  - Reads from: `progressTracker` (localStorage), `puzzleQueryService` (SQLite WASM)
  - SQL: batch `SELECT puzzle_id, tag_id FROM puzzle_tags WHERE puzzle_id IN (?)` (chunked ≤500)
  - Builds `TechniqueStats[]` with accuracy, avgTime, 30-day trend, lowData flag
  - Builds `DifficultyStats[]` from existing `UserStatistics.byDifficulty`
  - Builds `activityDays` map from `PuzzleCompletion.completedAt` timestamps
  - Pure functions, no side effects, zero modifications to existing services
  - Tests: Vitest unit tests mocking `query()` and `loadProgress()`
  - **Decommission**: Delete file

- [x] **T3** — Create `retryQueue.ts` service [P with T1, T2, T4]
  - File: `frontend/src/services/retryQueue.ts`
  - localStorage key: `yen-go-retry-queue`
  - Implements: `addToRetryQueue()`, `getRetryQueue(context?)`, `removeFromRetryQueue()`, `clearRetryQueue(context?)`
  - `RetryEntry`: `{ puzzleId, context, failedAt, retryCount }`
  - Context = technique slug or collection slug (per-module retry)
  - No modifications to existing services — caller invokes explicitly
  - Tests: Vitest unit tests with mock localStorage
  - **Decommission**: Delete file + `localStorage.removeItem('yen-go-retry-queue')`

- [x] **T4** — Create `achievementEngine.ts` service [P with T1, T2, T3]
  - File: `frontend/src/services/achievementEngine.ts`
  - Reads: `ACHIEVEMENT_DEFINITIONS` from `models/achievement.ts`, progress from `progressTracker`
  - localStorage key: `yen-go-achievement-progress`
  - Implements: `evaluateAchievements()` → returns newly unlocked achievements
  - 22 threshold checks against `totalSolved`, `streakData`, `rushHighScores`, `perfectSolves`
  - Tests: Vitest unit tests
  - **Decommission**: Delete file + `localStorage.removeItem('yen-go-achievement-progress')`

### Phase 2: UI Components [P — all parallel, depends on Phase 1]

- [x] **T5** — Create `ProgressPage.tsx` and section components
  - Files:
    - `frontend/src/pages/ProgressPage.tsx` — main scrollable page
    - `frontend/src/components/Progress/ProgressOverview.tsx` — rank badge + 4-stat row
    - `frontend/src/components/Progress/TechniqueRadar.tsx` — horizontal bars + trend arrows + insight
    - `frontend/src/components/Progress/DifficultyChart.tsx` — SVG bar chart
    - `frontend/src/components/Progress/ActivityHeatmap.tsx` — SVG 90-day grid
    - `frontend/src/components/Progress/AchievementsGrid.tsx` — badge tiles
    - `frontend/src/components/Progress/SmartPracticeCTA.tsx` — weakest + start button
    - `frontend/src/components/Progress/AchievementToast.tsx` — toast notification
    - `frontend/src/components/Progress/index.ts` — barrel export
  - Uses: `PageLayout variant="single-column"`, `PageHeader` with back arrow
  - Calls: `computeProgressSummary()` on mount
  - All values from `TechniqueStats[]`, `DifficultyStats[]`, `activityDays`, achievements
  - SVG icons only (C4/C10): reuse `TrendUpIcon`, `TrophyIcon`, `StarIcon`, `StreakIcon`
  - Technique bars: CSS `width: ${accuracy}%` with Tailwind utility classes
  - Difficulty chart: SVG `<rect>` elements
  - Heatmap: SVG `<rect>` grid, 7 rows × 13 cols
  - Achievement badges: tier-based coloring (bronze/silver/gold/platinum via CSS variables)
  - "Low data" label for <10 puzzles in technique bar
  - Smart insight: "Your {weakest} dropped {trend}% — try {n} puzzles"
  - Tests: Vitest component tests with mocked analytics service. Must include edge cases: empty state (0 puzzles solved), single puzzle solved, all techniques at 100%, only 1 technique with data.
  - **Decommission**: Delete `pages/ProgressPage.tsx` + `components/Progress/` directory

- [x] **T6** — Wire UserProfile onClick [P with T5]
  - File: `frontend/src/components/Layout/UserProfile.tsx`
  - Add optional `onClick` prop to `UserProfileProps`
  - Wire `<button onClick={onClick}>` (currently has no onClick)
  - **Decommission**: Remove `onClick` prop

### Phase 3: App Integration [depends on T1, T5, T6]

- [x] **T7** — Wire routes in `app.tsx`
  - File: `frontend/src/app.tsx`
  - Add `handleNavigateProgress` callback: `navigateTo({ type: 'progress' })`
  - Pass `onClickProfile={handleNavigateProgress}` to `AppHeader` → `UserProfile`
  - Add route case for `progress` → `<ProgressPage onBack={handleBackToHome} />`
  - Add route case for `smart-practice` → `<SmartPracticePage onBack={handleNavigateProgress} />`
  - **Decommission**: Remove ~15 lines

- [x] **T8** — Create `SmartPracticePage.tsx` [depends on T2, T5]
  - File: `frontend/src/pages/SmartPracticePage.tsx`
  - Calls: `getWeakestTechniques(3)` to determine focus techniques
  - Queries SQLite for unsolved puzzles matching weak technique tags
  - Builds puzzle set (10-20 puzzles)
  - Renders `PuzzleSetPlayer` (existing component, reused as-is)
  - On completion: shows summary with technique accuracy delta
  - On failure: calls `retryQueue.addToRetryQueue(puzzleId, techniqueSlug)`
  - **Decommission**: Delete file

### Phase 4: Quality & Documentation [depends on T7]

- [x] **T9** — Integration tests + regression check
  - Route roundtrip test: `/progress` ↔ `{ type: 'progress' }`
  - Profile button click → navigation test
  - Progress page renders with mocked data
  - Smart practice session flow
  - Retry queue persistence
  - Achievement evaluation and toast
  - Run full frontend test suite: `npm test -- --run --no-coverage`
  - Verify: no existing test failures

- [x] **T10** — Documentation updates
  - Update `frontend/src/AGENTS.md`: add Progress page, services, component hierarchy
  - Create `docs/how-to/frontend/progress-page.md`: user-facing feature guide
  - Update any page inventory docs if they exist
  - **Decommission note**: mention removability procedure in AGENTS.md

## Summary

| Metric | Value |
|--------|-------|
| New files | ~12 (1 service × 3 + 2 pages + 8 components + 1 barrel) |
| Modified files | 3 (routes.ts, app.tsx, UserProfile.tsx) |
| New npm dependencies | 0 |
| Estimated tests | ~25-30 new tests |
| Parallel phases | Phase 1 (4 tasks), Phase 2 (2 tasks) |
| Sequential phases | Phase 3 (2 tasks), Phase 4 (2 tasks) |
