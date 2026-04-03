# Tasks — OPT-1: Hook-Integrated Depth Presets + AC-Quality Integration

> Initiative: `20260314-2300-feature-advanced-search-filters`
> Selected Option: OPT-1
> Last Updated: 2026-03-14

## Task Dependency Graph

```
T1 (config) ──┐
              ├──→ T3 (query service) ──→ T5 (hook) ──→ T7 (pages) ──→ T9 (depth badge)
T2 (URL)    ──┘                                                           │
                                                                          ↓
T4 (backend) ─────────────────────────────────────────────────────→ T10 (backend tests)
                                                                          │
T6 (entryDecoder) ────────────────────────────────────────────────→ T11 (docs)
                                                                          │
T8 (page tests) ──────────────────────────────────────────────────→ T12 (AGENTS.md)
```

## Tasks

### Phase 1: Foundation (parallelizable)

| id | task | files | depends | parallel | AC |
|----|------|-------|---------|----------|----|
| T1 | **Create depth preset config.** Create `config/depth-presets.json` with 3 presets (quick/medium/deep) and boundary definitions. Create JSON schema file in `config/schemas/`. | `config/depth-presets.json`, `config/schemas/depth-presets.schema.json` | — | [P] with T2, T4, T6 | AC-3 |
| T2 | **Add `dp` param to canonical URL contract.** Add `dp` (string) to `CanonicalFilters` type. Update `parseCanonicalFilters()` to read `dp` from URL. Update `serializeCanonicalFilters()` to write `dp`. Add to `CANONICAL_PARAM_ORDER`. | `frontend/src/lib/routing/canonicalUrl.ts` | — | [P] with T1, T4, T6 | AC-4 |
| T4 | **Backend: Add `min_ac` to quality scoring.** (a) Add `min_ac` requirement field to quality levels 4 and 5 in `puzzle-quality.json`. (b) Update `compute_puzzle_quality_level()`: read existing ac via `parse_ac_level(game.yengo_props.quality)` (function already exists at L319); add `min_ac` check in the threshold loop (same pattern as `min_comment_level`). (c) Fix `compute_quality_metrics()` L289: replace hardcoded `ac:0` with `parse_ac_level(game.yengo_props.quality) or 0` to preserve enrichment-set ac values. | `config/puzzle-quality.json`, `backend/puzzle_manager/core/quality.py` | — | [P] with T1, T2, T6 | AC-6, AC-7 |
| T6 | **Add `ac` field to `DecodedEntry`.** Decode `PuzzleRow.ac` into `DecodedEntry` as `readonly ac: number`. | `frontend/src/services/entryDecoder.ts` | — | [P] with T1, T2, T4 | AC-8 |

### Phase 2: Query & Distribution

| id | task | files | depends | parallel | AC |
|----|------|-------|---------|----------|----|
| T3 | **Add depth preset distribution query to `puzzleQueryService`.** Add `getDepthPresetCounts(filters)` using SQL CASE expression for bucket counting. Extend `FilterCounts` interface with `depthPresets` field. Wire into `getFilterCounts()` for cross-filter integration. | `frontend/src/services/puzzleQueryService.ts` | T1 | — | AC-9 |

### Phase 3: Hook Integration

| id | task | files | depends | parallel | AC |
|----|------|-------|---------|----------|----|
| T5 | **Integrate depth presets into `usePuzzleFilters` hook.** Import depth preset config. Add `depthPresetOptions` to `PuzzleFilterOptions`. Create `buildDepthPresetOptions()` builder (follows `buildQualityOptions` pattern). Translate `dp` URL param to `minDepth`/`maxDepth` in `QueryFilters`. Add `depthPreset` / `setDepthPreset` convenience accessors. Wire depth preset counts from `getFilterCounts()`. | `frontend/src/hooks/usePuzzleFilters.ts` | T1, T2, T3 | — | AC-3, AC-9 |

### Phase 4: Page Integration (parallelizable)

| id | task | files | depends | parallel | AC |
|----|------|-------|---------|----------|----|
| T7 | **Add depth preset `FilterBar` to 4 pages.** Two page archetypes: **Archetype A (hook-based):** `TrainingPage` — already uses `usePuzzleFilters`; simply destructure `depthPresetOptions` from hook and render `<FilterBar>`. ~5 lines. **Archetype B (direct-wiring, ~30 lines each):** `TrainingSelectionPage`, `TechniqueFocusPage`, `RandomPage` — these use `useCanonicalUrl` + direct `getFilterCounts()` calls. For each: (1) import depth preset config, (2) read `dp` from canonical URL params, (3) include `minDepth`/`maxDepth` from preset in existing `getFilterCounts()` call (cross-filter narrowing works because these pages already pass active filters), (4) build depth preset options from returned counts using `buildDepthPresetOptions()` (export from hook or extract to shared util), (5) render `<FilterBar>` for depth pills. Verify NOT added to CollectionViewPage. Zero-count pills rendered but dimmed/disabled. Note: this is the largest task (~2 hours) due to per-page wiring. | `frontend/src/pages/TrainingSelectionPage.tsx`, `frontend/src/pages/TechniqueFocusPage.tsx`, `frontend/src/pages/TrainingPage.tsx`, `frontend/src/pages/RandomPage.tsx` | T5 | [P] across pages | AC-1, AC-2 |
| T9 | **~~REMOVED~~ — Depth badge dropped from scope.** Showing "X moves" on puzzle cards spoils the reading depth surprise. Knowing the move count changes how you approach the puzzle. Count badges on filter PILLS are fine (browse-level hint), but per-puzzle depth display is not. | — | — | — | ~~AC-5~~ |

### Phase 5: Tests (parallelizable)

| id | task | files | depends | parallel | AC |
|----|------|-------|---------|----------|----|
| T8 | **Frontend tests: depth presets + canonical URL.** Unit tests for: `buildDepthPresetOptions()`, depth preset distribution query (CASE expression), `dp` URL parse/serialize, `DecodedEntry.ac` decoding, zero-count pill disabled state. **AC-2 negative test:** verify CollectionViewPage does NOT import or render depth preset `FilterBar`. Cross-filter count verification: depth preset counts narrow correctly when level/tag filters are active. | `frontend/src/services/__tests__/puzzleQueryService.test.ts`, `frontend/src/hooks/__tests__/usePuzzleFilters.test.ts` (or colocated), `frontend/tests/unit/entry-decoder.test.ts`, `frontend/tests/unit/canonical-url.test.ts` | T3, T5, T6 | [P] with T10 | AC-10 |
| T10 | **Backend tests: `min_ac` quality scoring.** Test that quality scoring with `min_ac` correctly bumps/caps quality levels. **Explicit no-min_ac regression test:** quality levels 1-3 (which lack `min_ac`) must produce identical scores with and without the feature (assert old scores == new scores for same input). Test `compute_quality_metrics()` preserves existing ac from YQ (no longer hardcodes `ac:0`). Test `parse_ac_level()` integration in quality scoring. | `backend/puzzle_manager/tests/unit/test_quality.py` (or `tests/core/test_quality.py`) | T4 | [P] with T8 | AC-10 |

### Phase 6: Documentation

| id | task | files | depends | parallel | AC |
|----|------|-------|---------|----------|----|
| T11 | **Update docs.** Update `docs/concepts/sqlite-index-architecture.md` with depth preset filter pattern. Update `docs/reference/view-index-schema.md` noting ac→quality relationship. | `docs/concepts/sqlite-index-architecture.md`, `docs/reference/view-index-schema.md` | T7, T10 | [P] with T12 | — |
| T12 | **Update AGENTS.md.** Update `frontend/src/AGENTS.md` with new depth preset config import, updated hook docs, new `ac` field in DecodedEntry. | `frontend/src/AGENTS.md` | T7, T10 | [P] with T11 | AC-11 |

## Summary

| Metric | Value |
|--------|-------|
| Total tasks | 12 |
| Files modified | ~14 |
| New files | 2 (depth-presets.json, depth-presets.schema.json) |
| Parallel phases | 3 (Phase 1: 4 tasks, Phase 4: 2 tasks, Phase 5: 2 tasks, Phase 6: 2 tasks) |
| Backend tasks | 2 (T4, T10) |
| Frontend tasks | 8 (T2, T3, T5, T6, T7, T8, T9, T12) |
| Config tasks | 1 (T1) |
| Doc tasks | 1 (T11) |
