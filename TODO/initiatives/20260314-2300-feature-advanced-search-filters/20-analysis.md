# Analysis — Advanced Search Filters

> Initiative: `20260314-2300-feature-advanced-search-filters`
> Last Updated: 2026-03-14

## Planning Confidence

| metric | value |
|--------|-------|
| planning_confidence_score | 88 |
| risk_level | low |
| research_invoked | yes (Lee Sedol + Cho Chikun personas) |
| post_research_confidence | 82 → 88 (after all clarifications resolved) |

## Consistency Findings

| finding_id | severity | area | finding | resolution |
|------------|----------|------|---------|------------|
| F1 | info | charter ↔ tasks | All 11 acceptance criteria (AC-1 through AC-11) map to at least one task | ✅ covered |
| F2 | info | options ↔ plan | OPT-1 claims ~8 files changed; task list identifies ~14 files (includes test files + docs). Plan is more accurate. | ✅ non-blocking |
| F3 | info | research ↔ plan | Research REC-1 (depth presets, browse only) fully reflected in AC-1/AC-2 and T7 page list | ✅ aligned |
| F4 | info | research ↔ plan | Research REC-2 (fold AC into quality) fully reflected in T4 backend task | ✅ aligned |
| F5 | low | plan ↔ codebase | `compute_puzzle_quality_level(game)` currently takes only `SGFGame`. T4 reads ac via `parse_ac_level(game.yengo_props.quality)` — function already exists in quality.py L319. `compute_quality_metrics()` hardcoded `ac:0` — T4 fixes to preserve existing ac. | ✅ addressed in T4 (RC-2 resolved) |
| F6 | info | URL contract | `CanonicalFilters` currently has only numeric-array params (l,t,c,q,ct) + match string. Adding `dp` as a string slug is a new param type. `CANONICAL_PARAM_ORDER` needs `dp` inserted alphabetically. | ✅ addressed in T2 |
| F7 | info | config | `depth-presets.json` is a new config file. `config/README.md` should be updated to list it. | ⚠️ minor — include in T11 docs task |

## Coverage Map

| acceptance_criterion | task_ids | test_task |
|---------------------|----------|-----------|
| AC-1 (depth pills on 4 pages) | T7 | T8 |
| AC-2 (NOT on CollectionViewPage) | T7 | T8 |
| AC-3 (preset filters by cx_depth) | T1, T5 | T8 |
| AC-4 (URL persistence) | T2 | T8 |
| AC-5 (depth badge) | T9 | T8 |
| AC-6 (backend ac→quality) | T4 | T10 |
| AC-7 (quality no regression) | T4 | T10 |
| AC-8 (ac in DecodedEntry) | T6 | T8 |
| AC-9 (count badges) | T3, T5 | T8 |
| AC-10 (unit tests) | T8, T10 | — |
| AC-11 (AGENTS.md) | T12 | — |

## Unmapped Tasks

None — all tasks trace to at least one AC.

## Ripple-Effects Table

| impact_id | direction | area | risk | mitigation | owner_task | status |
|-----------|-----------|------|------|------------|------------|--------|
| RE-1 | downstream | `usePuzzleFilters` consumers | Low — all 4 pages call hook, adding `depthPresetOptions` is additive | Pages that don't render depth pills simply ignore the new field | T5, T7 | ✅ addressed |
| RE-2 | downstream | `CanonicalFilters` URL contract | Low — old URLs without `dp` work as "no depth filter" | Parser returns `undefined` for missing `dp` — existing behavior | T2 | ✅ addressed |
| RE-3 | lateral | `getFilterCounts()` return type | Low — `FilterCounts` grows by one field (`depthPresets`) | All callers destructure only what they need | T3 | ✅ addressed |
| RE-4 | upstream | `puzzle-quality.json` schema | Low — `min_ac` is optional field. Levels without it score identically to before | Backward compat guaranteed by `reqs.get("min_ac")` defaulting to None | T4 | ✅ addressed |
| RE-5 | downstream | Pipeline quality scores | Medium — existing puzzles with ac≥1 may get higher quality scores on next pipeline run | Scores can only go UP. Published puzzles keep existing scores until re-run. | T4 | ✅ addressed |
| RE-6 | lateral | `DecodedEntry` consumers | None — `ac` field is additive. No existing code reads it. | TypeScript compilation catches any issues | T6 | ✅ addressed |
| RE-7 | lateral | `CollectionViewPage` | None — explicitly excluded. Must verify it does NOT render depth pills. | Negative test in T8. | T7, T8 | ✅ addressed |
| RE-8 | lateral | `config/README.md` | Low — new config file not documented in README | Include in T11 | T11 | ⚠️ needs action |

## Must-Hold Constraints Verification

| constraint | task_id | verification |
|-----------|---------|-------------|
| No depth filter on CollectionViewPage | T7, T8 | Negative test: CollectionViewPage does not import/render depth pills |
| Bucket boundaries config-driven | T1, T5 | Presets loaded from `config/depth-presets.json`, not hardcoded |
| Default = All (no preset selected) | T5 | `dp=undefined` maps to no `minDepth`/`maxDepth` in QueryFilters |
| Zero-count pills dimmed/disabled | T7, T8 | FilterBar renders pills with count=0 as disabled |
| `min_ac` backward-compatible | T4, T10 | Levels without `min_ac` requirement skip the check (None → pass) |
