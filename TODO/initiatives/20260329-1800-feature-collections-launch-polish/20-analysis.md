# Analysis: Collections Launch Polish (v2)

_Last Updated: 2026-03-29_

## Planning Metrics

| Metric | Value |
|--------|-------|
| `planning_confidence_score` | 95 |
| `risk_level` | medium |
| `research_invoked` | yes |
| `option_selected` | OPT-2 (Multi-Strategy Embedder) |

## Cross-Artifact Consistency

| finding_id | severity | area | description | resolution |
|------------|----------|------|-------------|------------|
| F1 | info | charter↔research | G1 (embedder utility) supported by source audit — 3 priority sources with 50K+ exploitable puzzles | ✅ aligned |
| F2 | info | charter↔options | G1-G3 directly map to OPT-2 multi-strategy architecture | ✅ aligned |
| F3 | info | plan↔tasks | Plan's 3 strategies map to T2 (core + Strategy A), T3 (Strategy B), T3b (Strategy C) | ✅ aligned |
| F4 | warning | plan↔codebase | `tools/core/collection_matcher.py` consolidation requires rewiring 3 existing tool imports. T1 must include backward-compat re-exports. | T1 includes import rewiring |
| F5 | info | charter↔plan | NG1 (no pipeline changes) verified — plan contains zero references to `analyze.py`, `trace_utils.py`, or `sources.json` | ✅ verified |
| F6 | info | charter↔plan | NG2 (no featured boolean) verified — plan does not add `featured` field | ✅ verified |
| F7 | warning | plan↔frontend | F6 (selective randomization) requires knowing collection `type` at puzzle-load time. `CollectionPuzzleLoader` currently receives only `collectionId` (string slug). Need to resolve type during load. | T6 must resolve collection type from catalog or DB |
| F8 | info | plan↔tool-dev-standards | Minimal-edit SGF exception documented in plan. Pipeline whitelist rebuild is enforcement point. | ✅ documented |

## Coverage Map

| goal_id | Goal | Task IDs | Covered? |
|---------|------|----------|----------|
| G1 | Embedder utility in tools/core/ | T2, T3, T3b | ✅ |
| G2 | Consolidate 4 matchers | T1 | ✅ |
| G3 | Thin CLI wrappers | T3, T3b | ✅ |
| G4 | 4→3 section merge | T5 | ✅ |
| G5 | Difficulty sort + tier sort | T5 | ✅ |
| G6 | <15 filter | T5 | ✅ |
| G7 | Selective randomization | T6 | ✅ |
| G8 | In-section search | T7 | ✅ |
| G9 | Show-more + hover | T8, T9 | ✅ |
| G10 | Description improvements | T4 | ✅ |

## Unmapped Tasks

None — all tasks trace to goals.

## Ripple Effects

| impact_id | direction | area | risk | mitigation | owner_task | status |
|-----------|-----------|------|------|------------|------------|--------|
| IMP-1 | downstream | tools/ogs, tools/go_problems, tools/tsumego_hero imports | Medium | Re-export from new location | T1 | ❌ needs action |
| IMP-2 | downstream | CollectionsBrowsePage SECTIONS constant | Low | Data-driven change | T5 | ❌ needs action |
| IMP-3 | lateral | CollectionPuzzleLoader shuffle | Low | Additive code path | T6 | ❌ needs action |
| IMP-4 | upstream | config/collections.json descriptions | Low | Data-only, no schema change | T4 | ❌ needs action |
| IMP-5 | downstream | Pipeline ingest of embedder-modified SGFs | Low | Pipeline preserves existing YL via `is_enrichment_needed()` | N/A | ✅ addressed |
| IMP-6 | lateral | puzzleQueryService.ts new search query | Medium | Add function using collections_fts + type | T7 | ❌ needs action |
| IMP-7 | downstream | Other browse pages hover treatment | Low | CSS-only change | T8 | ❌ needs action |

## Quality Strategy

| task_id | TDD Approach |
|---------|-------------|
| T1 | Red: test shared matcher produces same results as existing tool matchers → Green: implement shared module → Refactor: rewire imports |
| T2 | Red: test embed function adds YL to SGF without YL → Green: implement core embedder → Refactor: idempotency + checkpoint |
| T3 | Red: test JSONL parsing + reverse index building → Green: implement Strategy B → Refactor: coverage validation |
| T5 | Red: test 3 sections rendered with correct types and sort orders → Green: implement section merge + sort → Refactor: <15 filter |
| T6 | Red: test technique collection shuffled, author collection sequential → Green: implement shuffle policy → Refactor: config toggle |
| T7 | Red: test scoped search query returns only matching-type collections → Green: implement query + UI → Refactor: debounce |
