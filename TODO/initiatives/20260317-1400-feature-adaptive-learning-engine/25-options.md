# Options — Adaptive Learning Engine

> Last Updated: 2026-03-18

## Decision Context

The charter defines 6 goals (progress page, technique detection, smart practice, retry queue, achievements, modularity). The core architectural question is: **How do we compute technique-level accuracy from two separate data stores (localStorage completions + SQLite WASM puzzle tags) while keeping the feature modular and performant?**

Secondary decisions: smart practice puzzle selection, retry queue scope, and SVG visualization approach.

## Option Comparison

### OPT-1: Lazy Join (Query-on-Demand)

**Approach**: When the Progress page mounts, query SQLite for tags of all completed puzzle IDs. Compute technique accuracy in-memory. No pre-caching, no denormalization.

**Data Flow**:
```
ProgressPage mounts
  → Read completedPuzzles from localStorage (get all puzzle IDs)
  → Batch SQL: SELECT puzzle_id, tag_id FROM puzzle_tags WHERE puzzle_id IN (chunk of IDs)
  → Build Map<tagId, {correct, total, totalTimeMs}> in memory
  → Render technique bars, difficulty chart, etc.
```

| Criteria | Assessment |
|----------|-----------|
| **Complexity** | Low — single service function, no new storage |
| **Performance** | ~50-100ms for 5K puzzles (chunked IN-clauses of 500). Acceptable for page load. |
| **Modularity** | Excellent — `progressAnalytics.ts` is the only file. Delete it and the feature loses technique data, but nothing else breaks. |
| **Freshness** | Always current — computed from live data on every page visit |
| **Storage overhead** | Zero — no denormalized data |
| **Offline** | Works — SQLite DB is local, localStorage is local |
| **Risk** | sql.js runs synchronously on main thread. Large result sets (10K+ puzzle completions) could cause brief UI jank (~200ms). |
| **Mitigation** | Web Worker for sql.js (exists in plan but not implemented). Or: cap computation at most recent N puzzles. |

### OPT-2: Pre-Cached Tag Map (Boot-Time Index)

**Approach**: At app boot (or first Progress page visit), build a `Map<puzzleId, tagId[]>` from SQLite and persist it in memory (or sessionStorage). All subsequent technique computations use this cache.

**Data Flow**:
```
App boot / first Progress visit
  → SQL: SELECT puzzle_id, tag_id FROM puzzle_tags (full table scan ~40K rows for 750K puzzles)
  → Build Map<puzzleId, tagId[]> in memory (~2MB for 40K entries)
  → Cache in module-level variable
Progress page renders
  → Read completedPuzzles from localStorage
  → Cross-reference with cached tag map (pure in-memory, instant)
```

| Criteria | Assessment |
|----------|-----------|
| **Complexity** | Medium — cache management, invalidation on DB update |
| **Performance** | First load: ~200ms (full table scan). Subsequent: <1ms (pure memory lookup). |
| **Modularity** | Good — cache lives in `progressAnalytics.ts`. But module-level cache means the module stays warm in memory even when not on Progress page. |
| **Freshness** | Stale until cache refresh. Must invalidate on puzzle completion (requires hook into progress tracker). |
| **Storage overhead** | ~2MB in-memory for full tag map. sessionStorage alternative adds persistence overhead. |
| **Offline** | Works |
| **Risk** | Cache grows with puzzle count. At 750K puzzles × avg 2 tags = 1.5M entries = ~30MB. Too large. Must scope to completed puzzles only. |
| **Mitigation** | Only cache tags for completed puzzles, not the full table. This reduces to OPT-1 with caching semantics. |

### OPT-3: Denormalized Analytics Store (Write-Time Aggregation)

**Approach**: When a puzzle is completed, immediately update a `techniqueStats` record in localStorage. The Progress page reads pre-computed aggregates — no SQL joins needed at render time.

**Data Flow**:
```
Puzzle completed (in any mode)
  → Existing: recordPuzzleCompletion() updates completedPuzzles
  → NEW: progressAnalytics.recordTechniqueResult(puzzleId, success, timeMs)
    → SQL: SELECT tag_id FROM puzzle_tags WHERE puzzle_id = ? (single-row lookup)
    → Update localStorage techniqueStats: { [tagId]: { correct, total, totalTimeMs, last30Days: [...] } }
Progress page renders
  → Read techniqueStats from localStorage (instant, pre-computed)
  → Render directly
```

| Criteria | Assessment |
|----------|-----------|
| **Complexity** | High — write-time hook, schema migration for existing completions, backfill logic |
| **Performance** | Render: <1ms (pre-computed). Write: ~5ms per puzzle (single SQL + localStorage write). |
| **Modularity** | Poor — requires modifying `progressCalculations.ts` to call the analytics hook. This creates a dependency from existing code → new feature, violating C6 (decommissionable). |
| **Freshness** | Always current for new puzzles. Requires one-time backfill for historical completions. |
| **Storage overhead** | ~10KB for typical user (~50 technique tags × 200 bytes each) |
| **Offline** | Works |
| **Risk** | The write-time hook means the feature is NOT cleanly removable — deleting the analytics service would leave a dead function call in the progress tracker. Migration/backfill adds complexity. |
| **Mitigation** | Use event dispatch pattern (CustomEvent) instead of direct function call. But this adds indirection. |

## Evaluation Matrix

| Criterion (weight) | OPT-1: Lazy Join | OPT-2: Pre-Cache | OPT-3: Denormalized |
|--------------------|-----------------:|------------------:|--------------------:|
| Modularity/Removability (30%) | 10 | 7 | 3 |
| Implementation Simplicity (25%) | 9 | 6 | 4 |
| Runtime Performance (20%) | 7 | 9 | 10 |
| Storage Efficiency (10%) | 10 | 5 | 8 |
| Freshness (10%) | 10 | 6 | 9 |
| Risk (5%) | 8 | 6 | 5 |
| **Weighted Score** | **9.05** | **6.70** | **5.55** |

## Recommendation

**OPT-1: Lazy Join** is the clear winner.

**Rationale**:
1. **Best modularity** — the user's #1 constraint. One service file to delete. Zero hooks into existing code.
2. **Simplest to build** — no caching, no migrations, no write-time hooks.
3. **50-100ms is acceptable** — this isn't a real-time game loop, it's a stats page that loads once per visit.
4. **Always fresh** — no stale cache, no invalidation logic.
5. **Zero storage overhead** — no denormalized data in localStorage.

The only risk (main-thread SQL jank at 10K+ completions) is mitigated by:
- Chunking IN-clauses (500 per batch)
- Most users will have <5K completions (even heavy users of 750K corpus)
- Can add Web Worker later if needed (separate initiative)

## Secondary Decisions

### SD-1: Accuracy Weighting

| Approach | Description | Recommendation |
|----------|------------|----------------|
| Raw accuracy | `correct / total` per technique | **Yes** — simple, intuitive, matches what users expect |
| Volume-adjusted | Weight by sample size (low-N techniques get less emphasis) | Add a "Low data" badge for techniques with <10 puzzles. Don't weight. |

### SD-2: Smart Practice Puzzle Selection

| Approach | Description | Recommendation |
|----------|------------|----------------|
| Weakest-first | Sort techniques by accuracy, pick puzzles from worst | **Yes** — pick bottom 2-3 techniques, query SQLite for unsolved puzzles matching those tags |
| Balanced set | Mix weak + strong techniques | No — defeats the purpose of targeted practice |
| Difficulty-adaptive | Pick puzzles at the user's frontier difficulty | No — complexity without clear benefit |

### SD-3: SVG Visualization Components

| Component | Approach | Recommendation |
|-----------|---------|----------------|
| Technique bars | `<div>` with Tailwind width% | **Yes** — simplest, CSS-only, responsive |
| Difficulty chart | SVG `<rect>` bars | **Yes** — clean, scalable, ~50 lines of code |
| Activity heatmap | SVG `<rect>` grid (7 rows × 13 cols for 90 days) | **Yes** — GitHub-style, well-understood pattern |
| Trend arrows | Existing `TrendUpIcon` + CSS rotation | **Yes** — reuse existing icon |
| Achievement badges | Existing `TrophyIcon` / `StarIcon` + color variants | **Yes** — reuse with tier-based coloring |
