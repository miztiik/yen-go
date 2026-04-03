# OBS-2 Handoff: `lib/quality` Overlapping Exports — DRY Cleanup

**Origin**: Initiative `20260324-1800-feature-frontend-cleanup-post-recovery`, Governance Review OBS-2
**Correction Level**: Level 2 (Medium Single — 1-2 files, ~100 lines, explicit behavior change)
**Date**: 2026-03-24

---

## Problem Statement

The frontend has **3 files** that export overlapping quality-related types, constants, and functions. This is a DRY violation — the same data (slugs, names, stars, descriptions, ID maps) is defined in 3 places with slightly different shapes.

---

## The 3 Files

### File 1: `frontend/src/lib/quality/config.ts` (CANONICAL — build-time Vite JSON import)

- **Source of truth**: Imports `config/puzzle-quality.json` via Vite at build time
- **Exports**: `QualitySlug`, `QualityName`, `QualityMeta` (with `selectionWeight`, `requirements`, `displayColor`), `QualityRequirements`, `QUALITIES[]`, `QUALITY_SLUGS[]`, `QUALITY_COUNT`, `QUALITY_ID_MAP`, `QUALITY_SLUG_MAP`, `QUALITY_DISPLAY`, `isValidQuality()`, `getQualityId()`, `getQualitySlug()`
- **Imported by**: `services/configService.ts` (1 consumer)

### File 2: `frontend/src/lib/quality/generated-types.ts` (DEAD — zero imports)

- **Source**: Hardcoded literals (claims to be auto-generated but values are copy-pasted from JSON)
- **Exports**: `QualitySlug`, `QualityName`, `QualityMeta` (narrower — missing `selectionWeight`, `requirements`, `displayColor`), `QUALITIES[]`, `QUALITY_SLUGS[]`, `QUALITY_COUNT`, `QUALITY_ID_MAP`, `QUALITY_SLUG_MAP`, `isValidQuality()`, `getQualityId()`, `getQualitySlug()`
- **Imported by**: **0 consumers** (zero imports in `frontend/src/` and `frontend/tests/`)

### File 3: `frontend/src/models/quality.ts` (OLDER MODEL — has unique content)

- **Source**: Hardcoded literals + SGF parsing functions
- **Exports**: `PuzzleQualityLevel` (numeric 1-5), `PuzzleQualityName`, `PuzzleQualityInfo`, `PUZZLE_QUALITY_INFO` (Record\<1-5, info\>), `QualityMetrics`, `ComplexityMetrics`, `parseQualityMetrics()`, `parseComplexityMetrics()`, `getPuzzleQualityInfo()`, `isValidPuzzleQualityLevel()`, `DEFAULT_QUALITY_METRICS`, `DEFAULT_COMPLEXITY_METRICS`, plus 6 `@deprecated` aliases
- **Imported by**: `QualityFilter.tsx`, `QualityBadge.tsx`, `QualityBreakdown.tsx`, `ComplexityIndicator.tsx` (4 consumers)

---

## Overlap Analysis

| Symbol | `config.ts` | `generated-types.ts` | `models/quality.ts` |
|--------|-------------|---------------------|---------------------|
| Quality slug union type | `QualitySlug` | `QualitySlug` | `PuzzleQualityName` |
| Quality name union type | `QualityName` | `QualityName` | — |
| Metadata interface | `QualityMeta` (rich) | `QualityMeta` (narrow) | `PuzzleQualityInfo` |
| Metadata constant array | `QUALITIES[]` | `QUALITIES[]` | `PUZZLE_QUALITY_INFO{}` |
| Slug list | `QUALITY_SLUGS[]` | `QUALITY_SLUGS[]` | — |
| Count | `QUALITY_COUNT` | `QUALITY_COUNT` | — |
| ID→slug map | `QUALITY_ID_MAP` | `QUALITY_ID_MAP` | — |
| Slug→ID map | `QUALITY_SLUG_MAP` | `QUALITY_SLUG_MAP` | — |
| Type guard | `isValidQuality()` | `isValidQuality()` | `isValidPuzzleQualityLevel()` |
| ID from slug | `getQualityId()` | `getQualityId()` | — |
| Slug from ID | `getQualitySlug()` | `getQualitySlug()` | `getPuzzleQualityInfo()` |
| Numeric level type | — | — | `PuzzleQualityLevel` (1\|2\|3\|4\|5) |
| SGF metrics parsing | — | — | `parseQualityMetrics()`, `parseComplexityMetrics()` |
| Display colors | `QUALITY_DISPLAY` | — | `color` field in `PUZZLE_QUALITY_INFO` |
| Selection weight | `selectionWeight` in `QualityMeta` | — | — |
| Requirements | `requirements` in `QualityMeta` | — | — |

---

## What Unique Value Each File Has

- **`config.ts`**: Only file that reads from JSON at build time (Vite import). Has `selectionWeight`, `requirements`, `displayColor`. This is the canonical source.
- **`generated-types.ts`**: **Nothing unique.** 0 imports. Pure duplicate of `config.ts` with narrower types. Candidate for **deletion**.
- **`models/quality.ts`**: Has `PuzzleQualityLevel` numeric type (1\|2\|3\|4\|5), `QualityMetrics` + `ComplexityMetrics` interfaces, `parseQualityMetrics()` + `parseComplexityMetrics()` SGF parsers, `DEFAULT_QUALITY_METRICS`, `DEFAULT_COMPLEXITY_METRICS`. These are **unique and actively used**.

---

## Recommended Approach

1. **Delete `generated-types.ts`** — 0 imports, pure duplicate. Also delete its test file `tests/unit/quality-generated-types.test.ts` if it exists.

2. **Merge unique `models/quality.ts` content into `lib/quality/config.ts`** — Move:
   - `PuzzleQualityLevel` type (numeric 1\|2\|3\|4\|5)
   - `QualityMetrics` and `ComplexityMetrics` interfaces
   - `parseQualityMetrics()` and `parseComplexityMetrics()` functions
   - `DEFAULT_QUALITY_METRICS` and `DEFAULT_COMPLEXITY_METRICS` constants
   - `getPuzzleQualityInfo()` (can be derived from `QUALITIES`)
   - `isValidPuzzleQualityLevel()` (equivalent to `isValidQuality()` but for numeric IDs)

3. **Rewrite `models/quality.ts` as a thin re-export** or **delete it** and update all 4 consumers (`QualityFilter.tsx`, `QualityBadge.tsx`, `QualityBreakdown.tsx`, `ComplexityIndicator.tsx`) to import from `@/lib/quality/config`.

4. **Remove all 6 `@deprecated` aliases** from `models/quality.ts` (`QualityTier`, `QualityTierName`, `QualityTierInfo`, `QUALITY_TIER_INFO`, `getTierInfo`, `isValidTier`).

---

## Constraints

- `config/puzzle-quality.json` is the single source of truth — never hardcode quality values
- `lib/quality/config.ts` uses Vite JSON import (build-time) — this pattern must stay
- Quality scale: 1=worst (unverified) → 5=best (premium)
- Keep `PuzzleQualityLevel = 1|2|3|4|5` numeric type — it's used in function signatures
- Keep SGF metric parsers (`parseQualityMetrics`, `parseComplexityMetrics`) — they're used by puzzle loading pipeline
- Test gate: `cd frontend && npx vitest run --no-coverage` must pass after changes
- Build gate: `npm run build` (pre-existing error in `useNavigationContext.ts` is unrelated)

---

## Acceptance Criteria

- [ ] `generated-types.ts` deleted (+ its test file)
- [ ] Single source location for all quality types/constants/functions
- [ ] 0 remaining `@deprecated` quality aliases
- [ ] All 4 component consumers updated to import from canonical location
- [ ] `npm test` passes (no new regressions)
- [ ] No duplicate type definitions across files
