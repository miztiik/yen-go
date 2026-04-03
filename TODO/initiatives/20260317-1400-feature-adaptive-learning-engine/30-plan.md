# Plan — Adaptive Learning Engine

> Last Updated: 2026-03-18
> Selected Option: **OPT-1 — Lazy Join (Query-on-Demand)**

## Architecture

### Component Hierarchy

```
AppHeader
  └─ UserProfile (onClick → navigateTo('/progress'))

ProgressPage (new: pages/ProgressPage.tsx)
  ├─ ProgressOverview (rank badge, 4-stat row)
  ├─ TechniqueRadar (horizontal accuracy bars + trend arrows + smart insight)
  ├─ DifficultyChart (SVG bar chart by skill level)
  ├─ ActivityHeatmap (SVG 90-day grid)
  ├─ AchievementsGrid (badge tiles with lock/unlock state)
  └─ SmartPracticeCTA (weakest technique summary + start button)

SmartPracticePage (new: pages/SmartPracticePage.tsx)
  └─ PuzzleSetPlayer (existing, reused as-is)

AchievementToast (new: components/Progress/AchievementToast.tsx)
```

### Data Flow (OPT-1: Lazy Join)

```
ProgressPage mounts
  → progressAnalytics.computeTechniqueStats(completedPuzzles)
    → Extract puzzle IDs from localStorage completedPuzzles
    → Chunk IDs into batches of 500
    → For each batch: SQL query against puzzle_tags table
      SELECT pt.tag_id, COUNT(*) as total,
             SUM(CASE WHEN ? THEN 1 ELSE 0 END) as correct
      FROM puzzle_tags pt
      WHERE pt.content_hash IN (?,?,?...)
      GROUP BY pt.tag_id
    → NOTE: correct/total must come from localStorage PuzzleCompletion records
           (SQL only provides tag mapping, not solve outcomes)
    → Actual flow:
      1. Read all PuzzleCompletion records from localStorage
      2. SQL: SELECT content_hash, tag_id FROM puzzle_tags WHERE content_hash IN (chunk)
      3. Build Map<tagId, PuzzleCompletion[]> — group completions by tag
      4. Compute per-tag: { correct, total, avgTimeMs, last30Days }
  → Return TechniqueStats[]
  → Render UI sections
```

### SQL Query Shape

```sql
-- Batch lookup: get tags for a set of completed puzzle IDs
SELECT pt.content_hash, pt.tag_id
FROM puzzle_tags pt
WHERE pt.content_hash IN (?, ?, ?, ...)
-- Chunked: max 500 params per batch
```

The `puzzle_id` here is `content_hash` (the 16-char hex that matches `GN` and filenames).

### Service Interfaces

```typescript
// services/progressAnalytics.ts
interface TechniqueStats {
  tagId: number;
  tagSlug: string;
  tagName: string;
  correct: number;
  total: number;
  accuracy: number;        // correct / total * 100
  avgTimeMs: number;
  trend30d: number;        // accuracy delta vs 30 days ago (-100 to +100)
  lowData: boolean;        // total < 10
}

interface DifficultyStats {
  levelId: number;
  levelName: string;
  correct: number;
  total: number;
  accuracy: number;
}

interface ProgressSummary {
  totalSolved: number;
  overallAccuracy: number;
  currentStreak: number;
  longestStreak: number;
  avgTimeMs: number;
  rankSlug: string;
  rankName: string;
  rankProgress: number;    // 0-100% progress to next rank
  techniques: TechniqueStats[];
  difficulties: DifficultyStats[];
  activityDays: Map<string, number>;  // YYYY-MM-DD → puzzle count
}

export function computeProgressSummary(): ProgressSummary;
export function getWeakestTechniques(n: number): TechniqueStats[];
```

```typescript
// services/retryQueue.ts
interface RetryEntry {
  puzzleId: string;
  context: string;         // technique slug or collection slug
  failedAt: string;        // ISO 8601
  retryCount: number;
}

export function addToRetryQueue(puzzleId: string, context: string): void;
export function getRetryQueue(context?: string): RetryEntry[];
export function removeFromRetryQueue(puzzleId: string): void;
export function clearRetryQueue(context?: string): void;
```

```typescript
// services/achievementEngine.ts
export function evaluateAchievements(): AchievementNotification[];
export function checkAndNotify(): void;  // Called after puzzle completion
```

### Integration Points (Minimal)

| File | Change | Reversibility |
|------|--------|---------------|
| `lib/routing/routes.ts` | Add `'progress'` and `'smart-practice'` to Route union + parseRoute/serializeRoute | Delete 2 union members + 2 parse cases + 2 serialize cases |
| `app.tsx` | Add `handleNavigateProgress` callback, pass to AppHeader. Add route cases for `progress` and `smart-practice`. | Delete ~15 lines |
| `components/Layout/UserProfile.tsx` | Add `onClick` prop, wire to navigate | Remove onClick prop |

### Decommission Procedure

To remove this feature entirely:

1. **Delete directories/files**:
   - `frontend/src/pages/ProgressPage.tsx`
   - `frontend/src/pages/SmartPracticePage.tsx`
   - `frontend/src/components/Progress/` (entire directory)
   - `frontend/src/services/progressAnalytics.ts`
   - `frontend/src/services/retryQueue.ts`
   - `frontend/src/services/achievementEngine.ts`

2. **Revert integration points**:
   - `routes.ts`: Remove `'progress'` and `'smart-practice'` route types + parse/serialize cases
   - `app.tsx`: Remove route handlers and cases
   - `UserProfile.tsx`: Remove `onClick` prop

3. **Optional cleanup**:
   - `localStorage.removeItem('yen-go-retry-queue')`
   - `localStorage.removeItem('yen-go-achievement-progress')`

No other files affected. No shared utilities depend on this feature.

## Risks & Mitigations

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|-----------|
| Main-thread SQL jank at 10K+ completions | Low | Medium | Chunk IN-clauses to 500. Most users <5K. Web Worker future option. |
| localStorage quota at high puzzle counts | Very Low | Low | Existing `storage.ts` quota management. ~200 bytes/puzzle = 5K puzzles ≈ 1MB. |
| SVG heatmap rendering on old mobile devices | Low | Low | Keep <100 SVG elements. 90-day grid = 90 rects max. |
| Achievement evaluation performance | Very Low | Low | 22 simple threshold checks. O(1) per achievement. |

## Documentation Plan

| doc_action | file | why_updated |
|------------|------|-------------|
| create | `docs/how-to/frontend/progress-page.md` | User-facing guide for the My Progress feature |
| update | `frontend/src/AGENTS.md` | Add Progress page and services to architecture map |
| update | `docs/architecture/frontend/page-architecture.md` | Add ProgressPage and SmartPracticePage to page inventory (create if not exists, update if exists) |
