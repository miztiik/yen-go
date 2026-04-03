# Options — Advanced Search Filters

> Initiative: `20260314-2300-feature-advanced-search-filters`
> Last Updated: 2026-03-14

## Option Comparison

### OPT-1: Hook-Integrated Depth Presets (Recommended)

**Approach:** Add depth preset options directly into the existing `usePuzzleFilters` hook and `QueryFilters` interface. Depth presets map to `minDepth`/`maxDepth` values (already wired in `buildWhereClause`). Bucket definitions live in a new `depth-presets.json` config file. A new `depthPreset` field in `CanonicalFilters` stores the selected bucket in the URL (e.g., `?dp=quick`). The hook exposes `depthPresetOptions` alongside existing `levelOptions`/`tagOptionGroups`. Pages render depth pills via the existing `FilterBar` component.

**Frontend changes:**
- `puzzleQueryService.ts`: No SQL changes needed — `minDepth`/`maxDepth` already work
- `usePuzzleFilters.ts`: Add `depthPresetOptions` to `PuzzleFilterOptions`, build from bucket config + distribution query
- `canonicalUrl.ts`: Add `dp` param for depth preset
- `entryDecoder.ts`: Add `ac` field to `DecodedEntry`
- Pages (4): Add `<FilterBar>` for depth presets alongside existing filter strips

**Backend changes:**
- `puzzle-quality.json`: Add `min_ac` requirement field per quality level
- `quality.py`: Read ac from YQ string, check `min_ac` threshold in scoring loop

**Benefits:**
- Minimal new code — reuses existing `FilterBar`, `buildWhereClause`, `usePuzzleFilters` patterns
- Bucket definitions are config-driven (changeable without code deploys)
- Distribution query uses existing `getFilterCounts` pattern (one SQL query per load)
- URL contract stays deterministic and additive

**Drawbacks:**
- `usePuzzleFilters` hook grows by ~40 lines (depth preset builder + distribution)
- Need a new distribution query `getDepthPresetCounts()` — but it's a simple `GROUP BY` CASE expression

**Risks:**
- Low: bucket boundaries may need tuning after seeing real data distribution

**Rollback:** Remove depth preset config + revert 4 page changes. URL `dp` param ignored gracefully.

---

### OPT-2: Standalone Depth Filter Component

**Approach:** Create a new `DepthPresetFilter` component (similar to `ContentTypeFilter`) that manages its own state and emits depth range changes. Each page using it passes a callback handler. The component fetches its own distribution counts independently. Depth presets stored in a dedicated hook `useDepthPreset` separate from `usePuzzleFilters`.

**Frontend changes:**
- New component: `DepthPresetFilter.tsx` (~100 lines)
- New hook: `useDepthPreset.ts` (~60 lines)
- `puzzleQueryService.ts`: Add `getDepthPresetCounts()` distribution query
- `canonicalUrl.ts`: Add `dp` param
- `entryDecoder.ts`: Add `ac` field
- Pages (4): Import and wire `DepthPresetFilter` + `useDepthPreset`

**Backend changes:** Same as OPT-1 (quality.py + puzzle-quality.json)

**Benefits:**
- `usePuzzleFilters` stays unchanged — no risk of regression in existing filter logic
- Self-contained component — easy to remove or move between pages
- Follows `ContentTypeFilter` precedent

**Drawbacks:**
- More new files (+2 component + hook) — violates "minimal change principle"
- Parallel state management (depth filter state lives separately from other filters)
- Distribution counts fetched independently = extra SQL query per page load
- Doesn't integrate with `getFilterCounts()` cross-filter narrowing (depth preset counts won't update when level/tag filters change)
- More wiring per page (each page needs both `usePuzzleFilters` + `useDepthPreset`)

**Risks:**
- Medium: state synchronization between `useDepthPreset` and `usePuzzleFilters` creates coupling complexity
- Count badges won't reflect cross-filter interactions (depth pill shows global count, not level-filtered count)

**Rollback:** Delete component + hook + revert page imports.

---

### OPT-3: Query-Layer Only (No Hook Integration)

**Approach:** Add depth presets as URL-only parameters. Each page reads `dp` from URL directly, maps to `minDepth`/`maxDepth`, passes to existing SQL query. No hook changes, no distribution counts, no count badges. Pages individually translate the URL param to query filters.

**Frontend changes:**
- `canonicalUrl.ts`: Add `dp` param
- `entryDecoder.ts`: Add `ac` field
- Pages (4): Read `dp` from URL, map to depth range, pass to query

**Backend changes:** Same as OPT-1

**Benefits:**
- Smallest change set — minimal files touched
- No hook changes = zero regression risk in filter system

**Drawbacks:**
- No count badges (AC-9 not met)
- Duplicate depth-to-range mapping logic across 4 pages
- Depth presets not integrated with cross-filter narrowing
- Each page re-implements the same logic — DRY violation

**Risks:**
- Low technical risk, but fails AC-9 acceptance criterion

**Rollback:** Remove URL param handling from pages.

---

## Evaluation Matrix

| Criterion | OPT-1 (Hook-Integrated) | OPT-2 (Standalone Component) | OPT-3 (Query-Layer Only) |
|-----------|------------------------|------------------------------|--------------------------|
| Files changed | ~8 | ~10 (+2 new) | ~6 |
| New files | 1 (config) | 3 (component + hook + config) | 1 (config) |
| Meets all AC | ✅ (AC-1 through AC-11) | ✅ | ❌ (fails AC-9) |
| Cross-filter integration | ✅ (counts update with filters) | ❌ (independent counts) | ❌ (no counts) |
| DRY compliance | ✅ (centralized in hook) | ⚠️ (parallel state) | ❌ (duplicated logic) |
| Regression risk | Low (additive to hook) | Low (isolated) | Lowest |
| Follows existing patterns | ✅ (`usePuzzleFilters` pattern) | ⚠️ (`ContentTypeFilter` pattern) | ❌ (ad-hoc) |
| Rollback ease | Simple | Simple | Simplest |
| YAGNI compliance | ✅ | ⚠️ (new abstractions) | ✅ |
| Config-driven | ✅ | ✅ | ❌ (hardcoded in pages) |

## Recommendation

**OPT-1 (Hook-Integrated Depth Presets)** — minimal new files, reuses all existing patterns, meets all acceptance criteria, integrates depth counts with cross-filter narrowing. The `usePuzzleFilters` hook is designed to be the single composable for all filter state, and adding depth presets follows the same pattern as existing level/tag/quality options.
