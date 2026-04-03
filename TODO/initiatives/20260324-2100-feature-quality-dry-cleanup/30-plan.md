# 30 — Plan

**Initiative**: 20260324-2100-feature-quality-dry-cleanup  
**Selected Option**: OPT-1 (Full Merge into `config.ts` + Delete `models/quality.ts`)  
**Correction Level**: Level 2  
**Last Updated**: 2026-03-24

---

## Architecture & Design

### Current State (3 files)

```
frontend/src/lib/quality/config.ts          ← Canonical (Vite JSON import, 105 lines)
frontend/src/lib/quality/generated-types.ts  ← DEAD (0 imports, 120 lines)  
frontend/src/models/quality.ts               ← Overlapping (4 consumers, 203 lines)
```

### Target State (1 file)

```
frontend/src/lib/quality/config.ts           ← Single source (~175 lines)
```

### Migration Strategy

**Phase A: Extend `config.ts`** — Add unique content from `models/quality.ts`:

1. **Types**: `PuzzleQualityLevel = 1|2|3|4|5`, `PuzzleQualityInfo`, `QualityMetrics`, `ComplexityMetrics`
2. **Constants**: `PUZZLE_QUALITY_INFO` (derived from `QUALITIES` array, not hardcoded), `DEFAULT_QUALITY_METRICS`, `DEFAULT_COMPLEXITY_METRICS`
3. **Functions**: `parseQualityMetrics()`, `parseComplexityMetrics()`, `getPuzzleQualityInfo()`, `isValidPuzzleQualityLevel()`

Key design decisions:
- `PUZZLE_QUALITY_INFO` will be derived from `QUALITIES` array: `Object.fromEntries(QUALITIES.map(q => [q.id, { name: q.slug, displayLabel: q.name, stars: q.stars, description: q.description, color: q.displayColor }]))` — eliminating hardcoded duplication.
- `PuzzleQualityLevel` as a numeric union type stays separate from `QualitySlug` (string union) — both needed.
- Parser functions are pure transforms, placed after the existing functions section in `config.ts`.

**Phase B: Delete dead files**

1. Delete `frontend/src/lib/quality/generated-types.ts`
2. Delete `frontend/src/models/quality.ts`

**Phase C: Update consumers** — Change import paths in 4 files:

| File | Current Import | New Import |
|------|---------------|------------|
| `components/QualityFilter.tsx` | `from '../models/quality'` | `from '@/lib/quality/config'` |
| `components/QualityBadge.tsx` | `from '../models/quality'` | `from '@/lib/quality/config'` |
| `components/QualityBreakdown.tsx` | `from '../models/quality'` | `from '@/lib/quality/config'` |
| `components/ComplexityIndicator.tsx` | `from '../models/quality'` | `from '@/lib/quality/config'` |

**Phase D: Test verification**

1. Add parser test coverage to existing `quality-generated-types.test.ts`
2. Run `npx vitest run --no-coverage` — full pass required

### What Is NOT Changed

- `config/puzzle-quality.json` — untouched
- `services/configService.ts` — already imports from `@/lib/quality/config`
- Backend quality code — no changes
- Quality scale (1-5) — preserved
- `QUALITIES` array and `QUALITY_*` maps — already in `config.ts`

---

## Data Model Impact

None. No schema changes, no config changes. Only import path changes and file consolidation.

---

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Missed consumer — another file imports from `models/quality.ts` | Very low (grep verified 4 consumers) | Build failure (caught by TS strict) | Grep verification + TypeScript strict compilation |
| `PUZZLE_QUALITY_INFO` derivation mismatch | Low | Wrong display labels/colors | Unit test comparing derived values to known expected values |
| `config.ts` grows beyond target size | Very low | Reduced readability | Monitor: target is ~175 lines, hard cap at 200 |
| Import alias mismatch (`@/` vs relative) | Low | Build failure | Use `@/lib/quality/config` consistently |

---

## Must-Hold Constraints (from Governance)

1. `config.ts` must not exceed ~200 lines post-merge
2. `PuzzleQualityLevel = 1|2|3|4|5` numeric union preserved exactly
3. SGF parser function signatures preserved (no breaking changes)
4. Vite JSON import pattern in `config.ts` remains intact
5. All 6 deprecated aliases deleted, not re-exported

---

## Documentation Plan

| doc_id | Action | File | Why | Cross-reference |
|--------|--------|------|-----|-----------------|
| DOC-1 | No doc changes needed | — | This is an internal code cleanup. No user-facing docs, no architecture docs, no config changes. The module-level JSDoc in `config.ts` is the documentation. | — |

**Rationale**: The existing JSDoc header in `config.ts` already documents its purpose. No `docs/` files reference the internal quality type organization. No new concepts or patterns are introduced.

---

> **See also**:
> - [00-charter.md](00-charter.md) — Acceptance criteria
> - [25-options.md](25-options.md) — Option comparison
> - [OBS-2 Handoff Brief](../../../TODO/obs2-quality-dry-cleanup-brief.md) — Full overlap analysis
