# 40 — Tasks

**Initiative**: 20260324-2100-feature-quality-dry-cleanup  
**Selected Option**: OPT-1  
**Last Updated**: 2026-03-24

---

## Task Dependency Graph

```
T1 (extend config.ts)
 ├── T2 (derive PUZZLE_QUALITY_INFO) [P]  
 ├── T3 (add parsers + defaults)    [P]
 │
 ├──> T4 (delete generated-types.ts)  [P]
 ├──> T5 (update consumer: QualityFilter.tsx)    [P]
 ├──> T6 (update consumer: QualityBadge.tsx)     [P]
 ├──> T7 (update consumer: QualityBreakdown.tsx) [P]
 ├──> T8 (update consumer: ComplexityIndicator.tsx) [P]
 │
 ├──> T9 (delete models/quality.ts) — depends on T5-T8
 │
 ├──> T10 (add parser tests) [P with T5-T8]
 │
 └──> T11 (full test gate) — depends on T1-T10
```

---

## Task Checklist

| task_id | title | files | depends_on | parallel | AC |
|---------|-------|-------|-----------|----------|-----|
| T1 | Add unique types from `models/quality.ts` to `config.ts` | `frontend/src/lib/quality/config.ts` | — | — | AC-3 |
| T2 | [P] Derive `PUZZLE_QUALITY_INFO` from `QUALITIES` array | `frontend/src/lib/quality/config.ts` | T1 | T3 | AC-3, AC-7 |
| T3 | [P] Add `parseQualityMetrics`, `parseComplexityMetrics`, defaults to `config.ts` | `frontend/src/lib/quality/config.ts` | T1 | T2 | AC-3 |
| T4 | [P] Delete `generated-types.ts` | `frontend/src/lib/quality/generated-types.ts` (delete) | T1 | T5-T8 | AC-1 |
| T5 | [P] Update `QualityFilter.tsx` imports to `@/lib/quality/config` | `frontend/src/components/QualityFilter.tsx` | T1 | T4, T6-T8 | AC-5 |
| T6 | [P] Update `QualityBadge.tsx` imports to `@/lib/quality/config` | `frontend/src/components/QualityBadge.tsx` | T1 | T4, T5, T7-T8 | AC-5 |
| T7 | [P] Update `QualityBreakdown.tsx` imports to `@/lib/quality/config` | `frontend/src/components/QualityBreakdown.tsx` | T1 | T4-T6, T8 | AC-5 |
| T8 | [P] Update `ComplexityIndicator.tsx` imports to `@/lib/quality/config` | `frontend/src/components/ComplexityIndicator.tsx` | T1 | T4-T7 | AC-5 |
| T9 | Delete `models/quality.ts` (remove 6 deprecated aliases + all content) | `frontend/src/models/quality.ts` (delete) | T5, T6, T7, T8 | — | AC-4 |
| T10 | [P] Add parser + defaults tests to `quality-generated-types.test.ts` | `frontend/tests/unit/quality-generated-types.test.ts` | T1-T3 | T5-T8 | AC-6 |
| T11 | Run full test gate: `cd frontend && npx vitest run --no-coverage` | — | T1-T10 | — | AC-6 |

---

## Detailed Task Descriptions

### T1: Add unique types from `models/quality.ts` to `config.ts`

Add to `config.ts` (after existing types section):
- `PuzzleQualityLevel = 1 | 2 | 3 | 4 | 5` numeric union type
- `PuzzleQualityInfo` interface (`name`, `displayLabel`, `stars`, `description`, `color`)
- `QualityMetrics` interface (`level`, `refutationCount`, `commentLevel`)
- `ComplexityMetrics` interface (`solutionDepth`, `readingCount`, `stoneCount`, `uniqueness`)

**Do NOT add**: `QualityTier`, `QualityTierName`, `QualityTierInfo`, `QUALITY_TIER_INFO`, `getTierInfo`, `isValidTier` (deprecated aliases — AC-4).

### T2: Derive `PUZZLE_QUALITY_INFO` from `QUALITIES`

Add constant derived from existing `QUALITIES` array:
```ts
export const PUZZLE_QUALITY_INFO: Record<PuzzleQualityLevel, PuzzleQualityInfo> = 
  Object.fromEntries(
    QUALITIES.map(q => [q.id, { name: q.slug, displayLabel: q.name, stars: q.stars, description: q.description, color: q.displayColor }])
  ) as Record<PuzzleQualityLevel, PuzzleQualityInfo>;
```

This eliminates the hardcoded constant in `models/quality.ts`.

### T3: Add parsers and defaults

Add to `config.ts` (after functions section):
- `parseQualityMetrics(value: string): QualityMetrics` — exact same implementation
- `parseComplexityMetrics(value: string): ComplexityMetrics` — exact same implementation
- `getPuzzleQualityInfo(level: PuzzleQualityLevel): PuzzleQualityInfo`
- `isValidPuzzleQualityLevel(level: number): level is PuzzleQualityLevel`
- `DEFAULT_QUALITY_METRICS: QualityMetrics`
- `DEFAULT_COMPLEXITY_METRICS: ComplexityMetrics`

### T4: Delete `generated-types.ts`

Remove `frontend/src/lib/quality/generated-types.ts`. Verify no imports reference it (already confirmed: 0 source imports).

### T5-T8: Update consumer imports

For each of the 4 consumer files, change:
```ts
// Before
import { PuzzleQualityLevel, PUZZLE_QUALITY_INFO } from '../models/quality';
// After  
import { PuzzleQualityLevel, PUZZLE_QUALITY_INFO } from '@/lib/quality/config';
```

Exact imports per consumer:
- **T5** `QualityFilter.tsx`: `PuzzleQualityLevel`, `PUZZLE_QUALITY_INFO`
- **T6** `QualityBadge.tsx`: `PuzzleQualityLevel`, `PUZZLE_QUALITY_INFO`
- **T7** `QualityBreakdown.tsx`: `PuzzleQualityLevel`, `QualityMetrics`, `PUZZLE_QUALITY_INFO`
- **T8** `ComplexityIndicator.tsx`: `ComplexityMetrics`

### T9: Delete `models/quality.ts`

Remove `frontend/src/models/quality.ts` entirely. This removes:
- All 6 deprecated aliases (`QualityTier`, `QualityTierName`, `QualityTierInfo`, `QUALITY_TIER_INFO`, `getTierInfo`, `isValidTier`)
- All types/constants/functions now in `config.ts`

### T10: Add parser tests

Add test sections to `frontend/tests/unit/quality-generated-types.test.ts`:
- `parseQualityMetrics`: parses valid YQ string, handles missing fields, handles empty string
- `parseComplexityMetrics`: parses valid YX string, handles missing fields
- `PUZZLE_QUALITY_INFO`: verify derived constant has all 5 levels with correct display labels
- `DEFAULT_QUALITY_METRICS`: verify default values
- `DEFAULT_COMPLEXITY_METRICS`: verify default values
- `isValidPuzzleQualityLevel`: valid (1-5) and invalid (0, 6, 1.5)
- `getPuzzleQualityInfo`: valid level returns info, invalid falls back to level 1

### T11: Full test gate

```bash
cd frontend && npx vitest run --no-coverage
```
All tests must pass. No new failures.

---

## Execution Order Summary

1. **Batch 1** (sequential): T1 — extend `config.ts` with types
2. **Batch 2** (parallel): T2 + T3 — add derived constants + parsers
3. **Batch 3** (parallel): T4 + T5 + T6 + T7 + T8 + T10 — delete dead file + update consumers + add tests
4. **Batch 4** (sequential): T9 — delete `models/quality.ts` (after consumers updated)
5. **Batch 5** (sequential): T11 — run test gate
