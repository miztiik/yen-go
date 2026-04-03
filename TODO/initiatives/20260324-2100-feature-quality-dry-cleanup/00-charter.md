# 00 — Charter

**Initiative**: 20260324-2100-feature-quality-dry-cleanup  
**Type**: Feature (DRY cleanup / dead code removal)  
**Correction Level**: Level 2 (Medium Single — 1-2 files, ~100 lines, explicit behavior change)  
**Origin**: OBS-2 from initiative `20260324-1800-feature-frontend-cleanup-post-recovery`  
**Last Updated**: 2026-03-24

---

## Goals

1. **Eliminate `generated-types.ts`** — dead file with 0 source imports.
2. **Consolidate all quality types/constants/functions** into `lib/quality/config.ts` as the single canonical source.
3. **Remove 6 `@deprecated` aliases** from `models/quality.ts`.
4. **Migrate unique `models/quality.ts` content** (SGF parsers, numeric types, defaults) into `config.ts`.
5. **Update or replace `models/quality.ts`** so no duplicate definitions remain.
6. **Ensure test coverage** for migrated functions.

## Non-Goals

- Changing quality scale (1-5) or adding new quality levels.
- Modifying `config/puzzle-quality.json`.
- Refactoring consumers beyond import path changes.
- Touching backend quality code.
- Creating new barrel/index files.

## Constraints

- `config/puzzle-quality.json` remains the single source of truth — never hardcode.
- `lib/quality/config.ts` uses Vite JSON import (build-time) — this pattern must stay.
- `PuzzleQualityLevel = 1|2|3|4|5` numeric type must be preserved.
- SGF metric parsers must be preserved (used by puzzle loading pipeline).
- Test gate: `cd frontend && npx vitest run --no-coverage` must pass.
- Build gate: `npm run build` must not regress (pre-existing error in `useNavigationContext.ts` is unrelated).
- Dead code policy: "Delete, don't deprecate."

## Acceptance Criteria

| AC | Description |
|----|-------------|
| AC-1 | `generated-types.ts` deleted |
| AC-2 | `quality-generated-types.test.ts` references updated (already imports from `config.ts`) |
| AC-3 | Single source location for all quality types/constants/functions |
| AC-4 | 0 remaining `@deprecated` quality aliases |
| AC-5 | All 4 component consumers compile with correct imports |
| AC-6 | `npx vitest run --no-coverage` passes — no new regressions |
| AC-7 | No duplicate type definitions across files |

## Scope Boundary

| In Scope | Out of Scope |
|----------|--------------|
| `frontend/src/lib/quality/config.ts` | Backend quality code |
| `frontend/src/lib/quality/generated-types.ts` | `config/puzzle-quality.json` |
| `frontend/src/models/quality.ts` | Other `models/*.ts` files  |
| 4 component consumers (QualityFilter, QualityBadge, QualityBreakdown, ComplexityIndicator) | Non-quality components |
| `frontend/tests/unit/quality-generated-types.test.ts` | Backend tests |

---

> **See also**:
> - [OBS-2 Handoff Brief](../../../TODO/obs2-quality-dry-cleanup-brief.md) — Full overlap analysis
