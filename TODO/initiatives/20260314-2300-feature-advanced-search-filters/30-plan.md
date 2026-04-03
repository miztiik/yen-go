# Plan — OPT-1: Hook-Integrated Depth Presets + AC-Quality Integration

> Initiative: `20260314-2300-feature-advanced-search-filters`
> Selected Option: OPT-1
> Last Updated: 2026-03-14

## Architecture

### Frontend: Depth Presets

The implementation threads through 4 existing layers, adding depth presets as a new filter dimension parallel to quality/content-type:

```
config/depth-presets.json  →  usePuzzleFilters (build options + counts)
                           →  CanonicalFilters (dp param)
                           →  FilterBar (render pills on pages)
                           →  puzzleQueryService (minDepth/maxDepth already wired)
```

**Key design decision:** Depth presets translate to `minDepth`/`maxDepth` in `QueryFilters` — no new SQL columns or query logic needed. The preset is a UI concept only; the query layer works with numeric ranges.

### Backend: AC → Quality Scoring

```
puzzle-quality.json (add min_ac per level)
    → quality.py: compute_puzzle_quality_level() reads ac, checks min_ac threshold
    → quality.py: compute_quality_metrics() passes ac through (already outputs ac:0)
```

**Pipeline sequencing:** The analyze stage processes enrichment (which sets `ac`) before quality scoring. `compute_puzzle_quality_level()` already receives the `SGFGame` — it can read existing `YQ` property to get the current `ac` value, or accept `ac` as an optional parameter.

## Data Model Impact

### New Config File: `config/depth-presets.json`

```json
{
  "version": "1.0.0",
  "presets": [
    { "id": "quick", "label": "Quick", "minDepth": 1, "maxDepth": 2 },
    { "id": "medium", "label": "Medium", "minDepth": 3, "maxDepth": 5 },
    { "id": "deep", "label": "Deep", "minDepth": 6, "maxDepth": null }
  ]
}
```

### Modified Config: `config/puzzle-quality.json`

Add `min_ac` to quality level requirements (optional field, backward-compatible):

```json
"4": {
  "name": "high",
  "requirements": {
    "refutation_count_min": 2,
    "min_comment_level": 1,
    "min_ac": 1
  }
},
"5": {
  "name": "premium",
  "requirements": {
    "refutation_count_min": 3,
    "min_comment_level": 1,
    "min_ac": 2
  }
}
```

### Modified Types

**`CanonicalFilters`** — add `dp?: string` (depth preset ID):
```typescript
export interface CanonicalFilters {
  // ... existing l, t, c, q, ct, match
  readonly dp?: string;  // depth preset slug: "quick" | "medium" | "deep"
}
```

**`FilterCounts`** — add `depthPresets: Record<string, number>`:
```typescript
export interface FilterCounts {
  // ... existing levels, tags, collections, quality, contentTypes
  depthPresets: Record<string, number>;  // preset_id → count
}
```

**`PuzzleFilterOptions`** — add `depthPresetOptions: readonly FilterOption[]`

**`DecodedEntry`** — add `ac: number`

## Contracts & Interfaces

### Depth Preset → QueryFilters Translation

`usePuzzleFilters` translates `dp` from URL to `minDepth`/`maxDepth` in `QueryFilters`:
```
dp="quick"  → { minDepth: 1, maxDepth: 2 }
dp="medium" → { minDepth: 3, maxDepth: 5 }
dp="deep"   → { minDepth: 6 }  // no maxDepth
dp=undefined → {} // no depth filter (default)
```

### Depth Count Query

`getFilterCounts()` gets a new depth preset dimension using SQL CASE:
```sql
SELECT
  CASE 
    WHEN p.cx_depth <= 2 THEN 'quick'
    WHEN p.cx_depth <= 5 THEN 'medium'
    ELSE 'deep'
  END as preset,
  COUNT(DISTINCT p.content_hash) as cnt
FROM puzzles p {join} {where}
GROUP BY preset
```

This integrates with existing cross-filter narrowing — depth preset counts update when level/tag/quality filters are active.

### Backend: `compute_puzzle_quality_level()` Change

Add `min_ac` check to the existing threshold loop:
```python
# Check min_ac (analysis completeness)
min_ac_req = reqs.get("min_ac")
if min_ac_req is not None and ac < min_ac_req:
    continue
```

The `ac` value is read from the game's existing `YQ` property via `parse_quality_metrics()`.

## Risks & Mitigations

| risk_id | risk | severity | mitigation |
|---------|------|----------|------------|
| R-1 | Bucket boundaries don't match data distribution | Low | Config-driven — tunable without code change. Count badges give immediate feedback. |
| R-2 | `usePuzzleFilters` hook grows too large | Low | ~40 lines added. Hook is ~400 lines already. Follows established pattern. |
| R-3 | AC quality bump changes scores for existing puzzles | Low | Only affects puzzles with ac≥1. Most puzzles are ac=0 (no change). Scores can only go UP (bump, never downgrade). |
| R-4 | `getFilterCounts()` performance impact from depth CASE query | Negligible | ~9K rows, in-memory SQL, integer comparison. Sub-millisecond. |

## Rollback Plan

1. **Frontend:** Remove `dp` from `CanonicalFilters`, remove depth preset code from `usePuzzleFilters`, remove `<FilterBar>` additions from 4 pages, remove depth badge. Unknown `dp` URL params gracefully ignored by existing parser.
2. **Backend:** Remove `min_ac` from `puzzle-quality.json` requirements. Quality scores revert to previous levels on next pipeline run.
3. **Config:** Delete `config/depth-presets.json`.

## Documentation Plan

| doc_action | file | why |
|------------|------|-----|
| files_to_create | `config/depth-presets.json` | New config file for depth bucket definitions |
| files_to_update | `config/puzzle-quality.json` | Add `min_ac` requirement field |
| files_to_update | `frontend/src/AGENTS.md` | New filter dimension, new config import, updated hook docs |
| files_to_update | `docs/concepts/sqlite-index-architecture.md` | Document depth preset filter pattern |
| files_to_update | `docs/reference/view-index-schema.md` | Note ac→quality relationship |

> **See also:**
> - [Architecture: SQLite Index](../../../docs/concepts/sqlite-index-architecture.md)
> - [Reference: View Index Schema](../../../docs/reference/view-index-schema.md)
> - [Charter](./00-charter.md)
