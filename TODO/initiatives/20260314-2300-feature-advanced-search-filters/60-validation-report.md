# Validation Report — Advanced Search Filters

> Initiative: `20260314-2300-feature-advanced-search-filters`
> Validated: 2026-03-20

## Test Suite Results

| val_id | suite | command | result | exit_code | status |
|--------|-------|---------|--------|-----------|--------|
| VAL-1 | Backend (not cli/slow) | `pytest backend/ -m "not (cli or slow)" -q --no-header --tb=short` | 1989 passed, 44 deselected | 0 | ✅ |
| VAL-2 | Frontend (vitest) | `npx vitest run --no-coverage` | 1329 passed, 87 test files | 0 | ✅ |
| VAL-3 | TypeScript strict | VS Code diagnostics on all modified files | 0 errors | — | ✅ |
| VAL-4 | Ruff lint (quality.py) | `ruff check core/quality.py` | 19 pre-existing errors (none introduced) | — | ✅ |

**Note**: Backend ruff shows 2740 total errors across the entire codebase — all pre-existing. The files modified by this initiative did not introduce new lint violations.

## Acceptance Criteria Verification

| val_id | ac_id | criterion | evidence | status |
|--------|-------|-----------|----------|--------|
| VAL-5 | AC-1 | Depth preset pills visible on browse pages | `buildDepthPresetOptions` + `<FilterBar>` in `TrainingBrowsePage.tsx`, `TechniqueBrowsePage.tsx`, `RandomPage.tsx` | ✅ |
| VAL-6 | AC-2 | Depth preset pills NOT on CollectionViewPage | grep confirms zero depth imports in `CollectionViewPage.tsx`; AC-2 negative test in `depth-presets.test.ts` | ✅ |
| VAL-7 | AC-3 | Selecting preset filters to matching cx_depth range | `depthPresetToRange()` translates quick→{1,2}, medium→{3,5}, deep→{6,∞}; wired into `buildWhereClause` via `minDepth`/`maxDepth` | ✅ |
| VAL-8 | AC-4 | Depth preset persisted in URL | `dp` param in `CanonicalFilters` type, `parseCanonicalFilters()`, `serializeCanonicalFilters()`, `CANONICAL_PARAM_ORDER` | ✅ |
| VAL-9 | AC-5 | ~~Depth badge~~ REMOVED | Dropped per charter — spoils reading depth surprise | ✅ n/a |
| VAL-10 | AC-6 | Backend quality scoring uses `min_ac` | `quality.py` L233-235: `min_ac` check in threshold loop; `puzzle-quality.json`: levels 4→`min_ac:1`, 5→`min_ac:2` | ✅ |
| VAL-11 | AC-7 | Quality filter no regression | 1989 backend tests pass including existing quality tests; `p.quality >= ?` unchanged | ✅ |
| VAL-12 | AC-8 | `ac` field in DecodedEntry | `entryDecoder.ts` L53: `readonly ac: number`; L94: `ac: row.ac` | ✅ |
| VAL-13 | AC-9 | Count badges on depth preset pills | `buildDepthPresetOptions(dist)` maps distribution counts to FilterOption.count; SQL CASE query in `puzzleQueryService.ts` | ✅ |
| VAL-14 | AC-10 | All changes have unit tests | depth-presets.test.ts (17), canonical-url.test.ts (7 new dp), entry-decoder.test.ts (2 new ac), puzzleQueryService.test.ts (5 new), backend quality tests (L2) | ✅ |
| VAL-15 | AC-11 | AGENTS.md updated | `frontend/src/AGENTS.md`: updated hook entry, DecodedEntry type, puzzleQueryService entry, 2 new gotchas, timestamp | ✅ |

## Ripple Effects Validation

| val_id | expected_effect | observed_effect | result | follow_up_task | status |
|--------|----------------|-----------------|--------|----------------|--------|
| VAL-16 | Existing URL params unaffected (additive) | `dp` is new optional param; missing `dp` = no filter (default) | match | — | ✅ verified |
| VAL-17 | Quality scores for ac=0 puzzles unchanged | `min_ac` check uses `continue` (skip level); ac=0 puzzles scored normally at levels 1-3 | match | — | ✅ verified |
| VAL-18 | CollectionViewPage & TrainingViewPage excluded | Both are solve pages; depth presets only on browse pages | match | — | ✅ verified |
| VAL-19 | Cross-filter narrowing works | Depth preset counts in all 3 pages include active level/tag filters in getFilterCounts call | match | — | ✅ verified |
| VAL-20 | Zero-count pills present (not filtered) | `buildDepthPresetOptions` always returns all 3 presets; count=0 entries included | match | — | ✅ verified |
| VAL-21 | Config-driven boundaries (not hardcoded) | `config/depth-presets.json` imported at build time; test validates 3 presets with contiguous ranges | match | — | ✅ verified |
| VAL-22 | No new npm/pip dependencies | `package.json` and `pyproject.toml` unchanged | match | — | ✅ verified |

## Documentation Verification

| val_id | doc_file | update | status |
|--------|----------|--------|--------|
| VAL-23 | `docs/concepts/sqlite-index-architecture.md` | Added "Depth Preset Filter Pattern" section | ✅ |
| VAL-24 | `docs/reference/view-index-schema.md` | Added "AC → Quality Relationship" section | ✅ |
| VAL-25 | `frontend/src/AGENTS.md` | Updated hook entry, query service entry, DecodedEntry type, 2 gotchas | ✅ |

## Page Name Mapping Note

T7 referenced page names that don't exist in the codebase. Actual mapping applied during execution:

| Charter / Task Name | Actual File | Archetype | Status |
|---------------------|-------------|-----------|--------|
| "TrainingPage" / "TrainingSelectionPage" | `TrainingBrowsePage.tsx` | B (direct) | ✅ depth presets added |
| "TechniqueFocusPage" | `TechniqueBrowsePage.tsx` | B (direct) | ✅ depth presets added |
| "RandomPage" | `RandomPage.tsx` | B (direct) | ✅ depth presets added |
| "TrainingPage" (Archetype A) | `TrainingViewPage.tsx` | Solve page | Correctly excluded (same principle as AC-2) |

`TrainingViewPage.tsx` is a solve/play page (user solves puzzles at a specific level). It was correctly excluded — depth presets apply only to browse-level pages where users discover/filter puzzles. This aligns with the charter's non-goal: "No depth filter on Collection Solve page (preserves sequential study flow)."

## Summary

All 11 acceptance criteria pass. All test suites green. No regressions. Documentation updated. Ready for governance review.
