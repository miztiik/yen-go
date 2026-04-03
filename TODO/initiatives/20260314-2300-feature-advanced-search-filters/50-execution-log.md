# Execution Log — Advanced Search Filters

> Last Updated: 2026-03-20

## Parallel Lane Plan

| lane_id | task_ids | scope_files | dependencies | status |
|---------|----------|-------------|--------------|--------|
| L1 | T1, T2, T6 | `config/depth-presets.json`, `config/schemas/depth-presets.schema.json`, `frontend/src/lib/routing/canonicalUrl.ts`, `frontend/src/services/entryDecoder.ts` | None (Phase 1 — parallel) | ✅ merged |
| L2 | T4, T10 | `config/puzzle-quality.json`, `backend/puzzle_manager/core/quality.py`, `backend/puzzle_manager/tests/unit/test_quality_complexity.py`, `backend/puzzle_manager/tests/unit/test_correctness.py` | None (Phase 1 — parallel, backend scope) | ✅ merged |
| L3 | T3 | `frontend/src/services/puzzleQueryService.ts`, `frontend/src/services/__tests__/puzzleQueryService.test.ts` | L1 (T1 config needed) | ✅ merged |
| L4 | T5 | `frontend/src/hooks/usePuzzleFilters.ts` | L1, L3 | ✅ merged |
| L5 | T7 | 3 page files + 2 test files | L4 | ✅ merged |
| L6 | T8, T10 | test files | L5, L2 | ✅ merged |
| L7 | T11, T12 | docs + AGENTS.md | L5, L6 | ✅ merged |

## Lane L1 Execution — Phase 1 Foundation (T1, T2, T6)

### T1: Create depth preset config

| row_id | field | value |
|--------|-------|-------|
| EX-1 | files_created | `config/depth-presets.json`, `config/schemas/depth-presets.schema.json` |
| EX-2 | action | Created 3-preset config (quick 1-2, medium 3-5, deep 6+) with JSON schema |
| EX-3 | schema | Draft-07, validates id pattern, minDepth integer, maxDepth integer-or-null |
| EX-4 | status | ✅ completed |

### T2: Add `dp` param to canonical URL contract

| row_id | field | value |
|--------|-------|-------|
| EX-5 | file | `frontend/src/lib/routing/canonicalUrl.ts` |
| EX-6 | action | Added `dp?: string` to `CanonicalFilters`, `'dp'` to `CANONICAL_PARAM_ORDER` (alphabetical: after 'ct', before 'id'), parse/serialize/canonicalize dp handling |
| EX-7 | lines_changed | ~15 added across 5 modification sites |
| EX-8 | tests_added | 7 new tests: parse dp, parse dp+filters, ignore empty dp, serialize dp, canonical ordering, omit undefined, canonicalize preservation + reorder |
| EX-9 | tests_file | `frontend/tests/unit/canonical-url.test.ts` |
| EX-10 | regression | 43 existing tests pass unchanged |
| EX-11 | status | ✅ completed |

### T6: Add `ac` field to `DecodedEntry`

| row_id | field | value |
|--------|-------|-------|
| EX-12 | file | `frontend/src/services/entryDecoder.ts` |
| EX-13 | action | Added `readonly ac: number` to `DecodedEntry` interface, wired `ac: row.ac` in `decodePuzzleRow()` |
| EX-14 | lines_changed | 3 added (1 interface field, 1 assignment, 1 JSDoc) |
| EX-15 | tests_added | 2 new tests: decode ac=0, decode non-zero ac |
| EX-16 | tests_file | `frontend/tests/unit/entry-decoder.test.ts` |
| EX-17 | regression | 7 existing tests pass unchanged |
| EX-18 | existing_fixture | SAMPLE_ROW already had `ac: 0` — no test fixture change needed |
| EX-19 | status | ✅ completed |

### Lane L1 Validation Summary

| row_id | validation | command | result | status |
|--------|-----------|---------|--------|--------|
| EX-20 | L1 targeted tests | `npx vitest run tests/unit/canonical-url.test.ts tests/unit/entry-decoder.test.ts --no-coverage` | 60/60 pass (was 50) | ✅ |
| EX-21 | Full frontend suite | `npx vitest run --no-coverage` | 1307/1307 pass, 86 test files (was 1297) | ✅ |
| EX-22 | No new npm dependencies | package.json unchanged | ✅ | ✅ |

### Lane L1 Ripple Effects

| impact_id | expected | observed | result | status |
|-----------|----------|----------|--------|--------|
| RPL-1 | dp param silently ignored by old URLs (no dp → filters.dp undefined) | parseCanonicalFilters('') returns {} — dp absent | match | ✅ verified |
| RPL-2 | Existing URL parsing unaffected by dp addition | All 43 existing canonical-url tests pass | match | ✅ verified |
| RPL-3 | DecodedEntry.ac additive — no existing consumers affected | All 7 existing entry-decoder tests pass, no compilation errors | match | ✅ verified |
| RPL-4 | CANONICAL_PARAM_ORDER remains alphabetical | c, ct, dp, id, l, match, offset, q, t — correct | match | ✅ verified |

## Lane L2 Execution — Backend AC→Quality Integration (T4, T10)

### T4a: Add `min_ac` to quality config

| row_id | field | value |
|--------|-------|-------|
| EX-23 | file | `config/puzzle-quality.json` |
| EX-24 | action | Added `"min_ac": 1` to level 4 requirements, `"min_ac": 2` to level 5 requirements |
| EX-25 | detail | Levels 1-3 unchanged (no min_ac) — backward compatible. Updated `last_updated` to 2026-03-19 |
| EX-26 | status | ✅ completed |

### T4b: Add `min_ac` check to `compute_puzzle_quality_level()`

| row_id | field | value |
|--------|-------|-------|
| EX-27 | file | `backend/puzzle_manager/core/quality.py` |
| EX-28 | action | Added `ac = parse_ac_level(game.yengo_props.quality)` in function body, added `min_ac = reqs.get("min_ac")` / `if min_ac is not None and ac < min_ac: continue` in threshold loop |
| EX-29 | pattern | Follows existing `min_comment_level` check pattern exactly |
| EX-30 | status | ✅ completed |

### T4c: Fix `compute_quality_metrics()` to preserve existing ac

| row_id | field | value |
|--------|-------|-------|
| EX-31 | file | `backend/puzzle_manager/core/quality.py` |
| EX-32 | action | Replaced hardcoded `ac:0` with `ac:{ac}` where `ac = parse_ac_level(game.yengo_props.quality)` |
| EX-33 | detail | Preserves enrichment-set ac value instead of always resetting to 0 |
| EX-34 | status | ✅ completed |

### T10: Backend tests for min_ac quality scoring

| row_id | field | value |
|--------|-------|-------|
| EX-35 | file | `backend/puzzle_manager/tests/unit/test_quality_complexity.py` |
| EX-36 | tests_added | 9 new tests in `TestMinAcQualityScoring` class |
| EX-37 | test_level_4_requires_min_ac_1 | ac=0 game with refutations+comments → level 3 (not 4) |
| EX-38 | test_level_4_with_ac_1 | ac=1 game → level 4 ✅ |
| EX-39 | test_level_5_requires_min_ac_2 | ac=1 game → level 4 (not 5) |
| EX-40 | test_level_5_with_ac_2 | ac=2 game → level 5 ✅ |
| EX-41 | test_level_5_with_ac_3 | ac=3 game → level 5 (exceeds min) ✅ |
| EX-42 | test_levels_1_to_3_no_regression | Levels 1-3 scores identical with/without ac (AC-7 regression test) |
| EX-43 | test_compute_quality_metrics_preserves_ac | ac=1 → output contains "ac:1" |
| EX-44 | test_compute_quality_metrics_ac_0_when_no_yq | No YQ → "ac:0" |
| EX-45 | test_parse_ac_level_integration | parse_ac_level edge cases (various YQ formats, None) |
| EX-46 | status | ✅ completed |

### Fixture updates (regression fix)

| row_id | field | value |
|--------|-------|-------|
| EX-47 | file | `backend/puzzle_manager/tests/unit/test_quality_complexity.py` |
| EX-48 | action | Updated all mock fixtures to set `yengo_props.quality` (required for new ac read). Updated level 4/5 test assertions to provide valid ac values. |
| EX-49 | file | `backend/puzzle_manager/tests/unit/test_correctness.py` |
| EX-50 | action | Updated `test_quality_metrics_reflect_refutations` assertion from `q:5` to `q:3` — game has no YQ/ac, so can't reach levels 4/5 with min_ac. |
| EX-51 | status | ✅ completed |

### Lane L2 Validation Summary

| row_id | validation | command | result | status |
|--------|-----------|---------|--------|--------|
| EX-52 | L2 targeted tests | `pytest backend/puzzle_manager/tests/unit/test_quality_complexity.py` | 56/56 pass (was 47, +9 new) | ✅ |
| EX-53 | Backend unit suite | `pytest backend/ -m unit` | 1603/1603 pass, 0 failures | ✅ |
| EX-54 | No new Python dependencies | pyproject.toml unchanged | ✅ | ✅ |

### Lane L2 Ripple Effects

| impact_id | expected | observed | result | status |
|-----------|----------|----------|--------|--------|
| RPL-5 | Levels 1-3 scores unchanged (no min_ac requirement) | test_levels_1_to_3_no_regression passes — levels 1/2/3 produce expected scores | match | ✅ verified |
| RPL-6 | Level 4 now requires ac >= 1 (enriched) | test_level_4_requires_min_ac_1: ac=0 → level 3 | match | ✅ verified |
| RPL-7 | Level 5 now requires ac >= 2 (ai_solved) | test_level_5_requires_min_ac_2: ac=1 → level 4 | match | ✅ verified |
| RPL-8 | compute_quality_metrics preserves existing ac | test_compute_quality_metrics_preserves_ac: ac=1 retained | match | ✅ verified |
| RPL-9 | test_correctness assertion updated (was q:5, now q:3 — correct for ac=0) | 1603 unit tests pass | match | ✅ verified |

## Lane L3 Execution — Query Service Depth Presets (T3)

### T3: Add depth preset distribution query to puzzleQueryService

| row_id | field | value |
|--------|-------|-------|
| EX-55 | file | `frontend/src/services/puzzleQueryService.ts` |
| EX-56 | action_1 | Extended `FilterCounts` interface with `depthPresets: Record<string, number>` |
| EX-57 | action_2 | Added `getDepthPresetCounts(filters)` — SQL CASE expression buckets `cx_depth` into quick(1-2)/medium(3-5)/deep(6+), uses `COUNT(DISTINCT p.content_hash)`, respects active filters via shared `buildWhereClause`/`buildParams` |
| EX-58 | action_3 | Wired `depthPresets: getDepthPresetCounts(filters)` into both fast-path and filtered-path of `getFilterCounts()` |
| EX-59 | lines_changed | ~20 added (new function + 2 integration lines + 1 interface field) |
| EX-60 | test_file | `frontend/src/services/__tests__/puzzleQueryService.test.ts` |
| EX-61 | tests_added | 5 new tests: CASE expression structure, active filter respect, empty result, no-filters depthPresets, with-filters depthPresets |
| EX-62 | tests_updated | 4 existing getFilterCounts tests updated — added 6th mock return for depthPresets (additive) |
| EX-63 | status | ✅ completed |

### Lane L3 Validation Summary

| row_id | validation | command | result | status |
|--------|-----------|---------|--------|--------|
| EX-64 | L3 targeted tests | `npx vitest run src/services/__tests__/puzzleQueryService.test.ts --no-coverage` | 33/33 pass (was 28, +5 new) | ✅ |
| EX-65 | Full frontend suite | `npx vitest run --no-coverage` | 1312/1312 pass, 86 test files (was 1307) | ✅ |
| EX-66 | TypeScript strict | No TS errors in modified files | ✅ | ✅ |

### Lane L3 Ripple Effects

| impact_id | expected | observed | result | status |
|-----------|----------|----------|--------|--------|
| RPL-10 | FilterCounts.depthPresets additive — no existing consumers construct FilterCounts | All 86 test files pass, consumers only read the result | match | ✅ verified |
| RPL-11 | getDepthPresetCounts uses parameterized queries (no SQL injection) | CASE buckets are hardcoded strings, filters use ? placeholders | match | ✅ verified |
| RPL-12 | Existing getFilterCounts behavior unchanged (levels/tags/quality/contentTypes/collections all intact) | 4 existing getFilterCounts tests pass with added depthPresets assertion | match | ✅ verified |

## Lane L4 Execution — Hook Integration (T5)

### T5: Integrate depth presets into usePuzzleFilters hook

| row_id | field | value |
|--------|-------|-------|
| EX-67 | file | `frontend/src/hooks/usePuzzleFilters.ts` |
| EX-68 | import | Added `import depthPresetsConfig from '../../../config/depth-presets.json'` |
| EX-69 | interface_PuzzleFilterOptions | Added `readonly depthPresetOptions: readonly FilterOption[]` |
| EX-70 | interface_UsePuzzleFiltersResult | Added `depthPreset: string \| null` and `setDepthPreset: (id: string \| null) => void` |
| EX-71 | buildDepthPresetOptions | New exported function — maps config presets to FilterOption[] with counts from distribution; preserves config order |
| EX-72 | depthPresetToRange | New exported utility — translates preset slug to `{ minDepth, maxDepth }` for QueryFilters. Used by Archetype B pages. |
| EX-73 | FilterDistributions | Added `depth_preset` field; wired from `counts.depthPresets` |
| EX-74 | buildFilterOptions | Wired `depthPresetOptions` from `depth_preset` distribution |
| EX-75 | depthPreset_accessor | Reads `filters.dp` from canonical URL |
| EX-76 | setDepthPreset_accessor | Writes `dp` to canonical URL via `setFilters({ dp: ... })` |
| EX-77 | empty_defaults | Added `EMPTY_DEPTH_PRESET_OPTIONS` constant and field in `EMPTY_FILTER_OPTIONS` |
| EX-78 | lines_changed | ~45 added across 8 modification sites |
| EX-79 | status | ✅ completed |

### Lane L4 Validation Summary

| row_id | validation | command | result | status |
|--------|-----------|---------|--------|--------|
| EX-80 | TypeScript strict | Zero TS errors in modified file | ✅ | ✅ |
| EX-81 | Full frontend suite | `npx vitest run --no-coverage` | 1312/1312 pass, 86 test files | ✅ |
| EX-82 | No new npm dependencies | package.json unchanged | ✅ | ✅ |

### Lane L4 Ripple Effects

| impact_id | expected | observed | result | status |
|-----------|----------|----------|--------|--------|
| RPL-13 | PuzzleFilterOptions.depthPresetOptions additive — existing destructuring unaffected | 86 test files pass, consumers destructure only what they need | match | ✅ verified |
| RPL-14 | UsePuzzleFiltersResult.depthPreset/setDepthPreset additive — no consumer uses them yet | No consumer breakage; new accessors available for T7 pages | match | ✅ verified |
| RPL-15 | buildDepthPresetOptions and depthPresetToRange exported for Archetype B (T7) pages | TypeScript exports verified; no import errors | match | ✅ verified |
| RPL-16 | EMPTY_FILTER_OPTIONS matches PuzzleFilterOptions shape | TypeScript strict mode passes — shape is correct | match | ✅ verified |

## Lane L5 Execution — Page Integration (T7)

### T7: Add depth preset FilterBar to browse pages

**Task mapping note:** T7 referenced filenames that don't exist. Actual mapping:
- "TrainingPage" / "TrainingSelectionPage" → `TrainingBrowsePage.tsx` (single file, Archetype B)
- "TechniqueFocusPage" → `TechniqueBrowsePage.tsx` (Archetype B)
- "RandomPage" → `RandomPage.tsx` (Archetype B)

All 3 pages use Archetype B pattern (useCanonicalUrl + direct getFilterCounts). None use usePuzzleFilters hook.

### T7a: TrainingBrowsePage depth preset integration

| row_id | field | value |
|--------|-------|-------|
| EX-83 | file | `frontend/src/pages/TrainingBrowsePage.tsx` |
| EX-84 | import | Added `buildDepthPresetOptions`, `depthPresetToRange` from `@/hooks/usePuzzleFilters` |
| EX-85 | dp_read | Read `depthPreset = filters.dp ?? null` from `useCanonicalUrl()` |
| EX-86 | depth_options | `useMemo` computing `depthPresetOptions` via `getFilterCounts()` with cross-filter narrowing (tag + depth range) → `buildDepthPresetOptions()` |
| EX-87 | handler | `handleDepthPresetChange` — toggles `dp` param via `setFilters()` |
| EX-88 | render | `<FilterBar label="Filter by depth" ... testId="training-depth-filter" />` after tag chip, conditional on `depthPresetOptions.length > 0` |
| EX-89 | cross_filter | Updated `filteredLevels` memo to include `depthPresetToRange(depthPreset)` in `getFilterCounts()` call — levels with 0 matching puzzles hidden when depth preset active |
| EX-90 | lines_changed | ~25 added |
| EX-91 | status | ✅ completed |

### T7b: TechniqueBrowsePage depth preset integration

| row_id | field | value |
|--------|-------|-------|
| EX-92 | file | `frontend/src/pages/TechniqueBrowsePage.tsx` |
| EX-93 | import | Added `buildDepthPresetOptions`, `depthPresetToRange` from `../hooks/usePuzzleFilters`, `getFilterCounts` from `../services/puzzleQueryService` |
| EX-94 | dp_read | Read `depthPreset = filters.dp ?? null` from `useCanonicalUrl()` |
| EX-95 | depth_options | `useMemo` computing `depthPresetOptions` via `getFilterCounts()` with cross-filter narrowing (levelIds + depth range) → `buildDepthPresetOptions()` |
| EX-96 | handler | `handleDepthPresetChange` — toggles `dp` param via `setFilters()` |
| EX-97 | render | `<FilterBar label="Filter by depth" ... testId="depth-filter" />` in new Row 3 after level filter row, conditional on `depthPresetOptions.length > 0` |
| EX-98 | lines_changed | ~25 added |
| EX-99 | status | ✅ completed |

### T7c: RandomPage depth preset integration

| row_id | field | value |
|--------|-------|-------|
| EX-100 | file | `frontend/src/pages/RandomPage.tsx` |
| EX-101 | import | Added `buildDepthPresetOptions`, `depthPresetToRange` from `@/hooks/usePuzzleFilters`, `getFilterCounts` from `@/services/puzzleQueryService` |
| EX-102 | dp_read | Read `depthPreset = filters.dp ?? null` from `useCanonicalUrl()` |
| EX-103 | depth_options | `useMemo` computing `depthPresetOptions` via `getFilterCounts()` with cross-filter narrowing (levelId + tagId + depth range) → `buildDepthPresetOptions()` |
| EX-104 | handler | `handleDepthPresetChange` — toggles `dp` param via `setFilters()` |
| EX-105 | render | `<FilterBar label="Filter by depth" ... testId="random-depth-filter" />` after tag chip, conditional on `depthPresetOptions.length > 0` |
| EX-106 | lines_changed | ~25 added |
| EX-107 | status | ✅ completed |

### T7d: Test mock updates

| row_id | field | value |
|--------|-------|-------|
| EX-108 | file | `frontend/tests/unit/TrainingPage.test.tsx` |
| EX-109 | action | Added `depthPresets: {}` to `getFilterCounts` mock return (existing mock lacked new field) |
| EX-110 | file | `frontend/tests/unit/RandomPage.test.tsx` |
| EX-111 | action | Added `vi.mock('@/services/puzzleQueryService')` with `getFilterCounts` returning `{ levels: {}, tags: {}, collections: {}, depthPresets: {} }` (new import needed mock) |
| EX-112 | status | ✅ completed |

### T7e: CollectionViewPage verification (AC-2)

| row_id | field | value |
|--------|-------|-------|
| EX-113 | check | Verified `CollectionViewPage.tsx` does NOT import `buildDepthPresetOptions`, `depthPresetToRange`, or render depth FilterBar |
| EX-114 | status | ✅ AC-2 verified (negative test) |

### Lane L5 Validation Summary

| row_id | validation | command | result | status |
|--------|-----------|---------|--------|--------|
| EX-115 | TypeScript strict | Zero TS errors in all 3 modified page files | ✅ | ✅ |
| EX-116 | Full frontend suite | `npx vitest run --no-coverage` | 1312/1312 pass, 86 test files | ✅ |
| EX-117 | No new npm dependencies | package.json unchanged | ✅ | ✅ |

### Lane L5 Ripple Effects

| impact_id | expected | observed | result | status |
|-----------|----------|----------|--------|--------|
| RPL-17 | Depth FilterBar only visible when DB has depth data (depthPresetOptions.length > 0) | Conditional rendering guards on all 3 pages | match | ✅ verified |
| RPL-18 | Cross-filter narrowing: selecting depth preset narrows level/tag counts | depthPresetToRange included in getFilterCounts calls | match | ✅ verified |
| RPL-19 | CollectionViewPage NOT modified (AC-2) | No depth imports or FilterBar in CollectionViewPage.tsx | match | ✅ verified |
| RPL-20 | Existing TrainingPage tests pass (14 tests) | All 14 pass with updated mock | match | ✅ verified |
| RPL-21 | Existing RandomPage tests pass (14 tests) | All 14 pass with added mock | match | ✅ verified |
| RPL-22 | Defensive `?? {}` on depthPresets access prevents runtime errors in unmocked test contexts | All pages use `counts.depthPresets ?? {}` | match | ✅ verified |

---

## Lane L6 Execution — Frontend Tests (T8)

### T8: Depth preset unit tests

| row_id | field | value |
|--------|-------|-------|
| EX-118 | file_created | `frontend/tests/unit/depth-presets.test.ts` |
| EX-119 | test_count | 17 tests across 4 describe blocks |
| EX-120 | block_1 | `buildDepthPresetOptions` — 6 tests: config order, labels, counts, missing counts default to 0, empty dist, zero-count pills present |
| EX-121 | block_2 | `depthPresetToRange` — 7 tests: quick→{1,2}, medium→{3,5}, deep→{6} no maxDepth, null→{}, undefined→{}, unknown→{}, empty-string→{} |
| EX-122 | block_3 | `depth-presets.json config` — 3 tests: 3 presets, contiguous ranges, last preset unbounded |
| EX-123 | block_4 | `AC-2: CollectionViewPage exclusion` — 1 static analysis test: reads page source, asserts no depth preset imports |
| EX-124 | status | ✅ completed |

### T10 (backend tests) — already done in L2

| row_id | field | value |
|--------|-------|-------|
| EX-125 | note | T10 backend quality tests completed and merged in L2. No additional T10 work needed in L6. |

### Lane L6 Validation Summary

| row_id | validation | command | result | status |
|--------|-----------|---------|--------|--------|
| EX-126 | T8 tests only | `npx vitest run tests/unit/depth-presets.test.ts --no-coverage` | 17/17 pass | ✅ |
| EX-127 | Full frontend suite | `npx vitest run --no-coverage` | 1329/1329 pass, 87 test files | ✅ |
| EX-128 | No regressions | Suite grew from 1312→1329 (+17 new tests), all green | ✅ | ✅ |

### Lane L6 Ripple Effects

| impact_id | expected | observed | result | status |
|-----------|----------|----------|--------|--------|
| RPL-23 | New test file imports `buildDepthPresetOptions` and `depthPresetToRange` from usePuzzleFilters | Both exports exist and import successfully | match | ✅ verified |
| RPL-24 | Config JSON import in test matches runtime config | Test reads from same `config/depth-presets.json` used in production code | match | ✅ verified |
| RPL-25 | AC-2 negative test prevents accidental depth preset addition to CollectionViewPage | Static source analysis test blocks regressions | match | ✅ verified |
| RPL-26 | No existing test files broken by new test | 87/87 test files pass (was 86 in L5) | match | ✅ verified |

---

## Lane L7 Execution — Documentation (T11, T12)

### T11: Documentation updates

| row_id | field | value |
|--------|-------|-------|
| EX-129 | file_updated | `docs/concepts/sqlite-index-architecture.md` |
| EX-130 | changes | Added "Depth Preset Filter Pattern" section: preset→SQL translation table, CASE distribution query, config-driven boundaries. Updated Last Updated. |
| EX-131 | file_updated | `docs/reference/view-index-schema.md` |
| EX-132 | changes | Added "AC → Quality Relationship" section: min_ac requirements table for quality levels 4-5, ac value definitions. Updated Last Updated. |
| EX-133 | status | ✅ completed |

### T12: AGENTS.md update

| row_id | field | value |
|--------|-------|-------|
| EX-134 | file_updated | `frontend/src/AGENTS.md` |
| EX-135 | changes_1 | Updated `hooks/usePuzzleFilters.ts` entry: mentions `buildDepthPresetOptions()`, `depthPresetToRange()` exports and `config/depth-presets.json` import |
| EX-136 | changes_2 | Updated `services/puzzleQueryService.ts` entry: added `getFilterCounts()` with depth preset distribution note |
| EX-137 | changes_3 | Updated `DecodedEntry` type: added `ac: number` field |
| EX-138 | changes_4 | Added 2 new gotchas: "Depth presets are UI-only" (cx_depth range translation) and "ac column gates quality scoring" (min_ac in quality levels 4+) |
| EX-139 | changes_5 | Updated Last Updated timestamp and trigger description |
| EX-140 | status | ✅ completed |

### Lane L7 Validation Summary

| row_id | validation | command | result | status |
|--------|-----------|---------|--------|--------|
| EX-141 | Full frontend suite | `npx vitest run --no-coverage` | 1329/1329 pass, 87 test files | ✅ |
| EX-142 | Doc files render valid Markdown | Manual structure check — all tables, code blocks, headers valid | ✅ | ✅ |
| EX-143 | No broken cross-references | See-also links in sqlite-index-architecture.md and view-index-schema.md intact | ✅ | ✅ |

### Lane L7 Ripple Effects

| impact_id | expected | observed | result | status |
|-----------|----------|----------|--------|--------|
| RPL-27 | AGENTS.md reflects new depth preset exports from usePuzzleFilters | Hook entry documents buildDepthPresetOptions, depthPresetToRange, config import | match | ✅ verified |
| RPL-28 | DecodedEntry type in AGENTS.md includes ac field | ac: number added to DecodedEntry field list | match | ✅ verified |
| RPL-29 | sqlite-index-architecture.md documents depth CASE query pattern | New section with SQL example matches actual puzzleQueryService implementation | match | ✅ verified |
| RPL-30 | view-index-schema.md notes ac→quality gating | New section documents min_ac requirements for levels 4-5 | match | ✅ verified |
| RPL-31 | No existing doc cross-references broken | All See-also blocks remain valid | match | ✅ verified |

---

## Post-Closeout Addendum — Additional Co-located Tests (2026-03-21)

> Note: The initiative was already closed (status.json: closeout approved). This section records an **additional** test file created in a follow-up session based on a stale conversation summary that indicated L6 was still in progress.

### Additional T8 coverage: `frontend/src/hooks/__tests__/usePuzzleFilters.test.ts`

| row_id | field | value |
|--------|-------|-------|
| EX-150 | relationship | Complementary to `frontend/tests/unit/depth-presets.test.ts` (L6, 17 tests). Co-located style with source. |
| EX-151 | file_created | `frontend/src/hooks/__tests__/usePuzzleFilters.test.ts` |
| EX-152 | test_count | 22 tests across 4 describe blocks |
| EX-153 | block_1 | `buildDepthPresetOptions` (8 tests) — config order, labels, count injection, zero defaults, empty dist, partial dist, array check, zero-count contract |
| EX-154 | block_2 | `depthPresetToRange` (8 tests) — quick/medium/deep ranges, null/undefined/empty/unknown → {}, deep has no maxDepth key |
| EX-155 | block_3 | `AC-2 negative` (3 tests) — CollectionViewPage lacks buildDepthPresetOptions, depthPresetToRange, depth-filter testId |
| EX-156 | block_4 | `Cross-filter narrowing contract` (3 tests) — range spread into QueryFilters, null spread leaves no keys, depth-only range has no level/tag keys |
| EX-157 | validation_isolated | `npx vitest run src/hooks/__tests__/usePuzzleFilters.test.ts --no-coverage` → 22/22 pass ✅ |
| EX-158 | validation_combined | Both T8 files together: `npx vitest run src/hooks/__tests__/usePuzzleFilters.test.ts tests/unit/depth-presets.test.ts --no-coverage` → 39/39 pass ✅ |
| EX-159 | full_suite | `npx vitest run --no-coverage` → **1351/1351 pass, 88 test files** ✅ (was 1329/87 pre-addendum) |
| EX-160 | status | ✅ addendum completed and validated |
