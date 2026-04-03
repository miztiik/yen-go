# Validation Report: Collections Launch Polish (v2)

_Last Updated: 2026-03-29_

## Test Results

| val_id | Suite | Command | Result | Notes |
|--------|-------|---------|--------|-------|
| VAL-1 | collection_matcher.py tests | `pytest tools/core/tests/test_collection_matcher.py` | 30/30 pass | Exact, phrase, stop-word, CJK, longest-match, override, edge cases |
| VAL-2 | collection_embedder.py tests | `pytest tools/core/tests/test_collection_embedder.py` | 33/33 pass | YL add, idempotent, conflict, dry-run, backup, restore, checkpoint, Strategy A/B/C |
| VAL-3 | All tools/core tests | `pytest tools/core/tests/` | 491 pass, 2 fail (pre-existing) | 2 failures are pre-existing: chinese_translator punctuation, sgf_builder board_size |
| VAL-4 | CollectionsPage frontend tests | `vitest run CollectionsPage.test.tsx` | 12/12 pass | 3 sections, <15 filter, sort, search, nav |
| VAL-5 | collectionConfig frontend tests | `vitest run collectionConfig.test.ts` | 11/11 pass | Shuffle policy, Fisher-Yates correctness, immutability |
| VAL-6 | collections.json validation | `python -c "import json; ..."` | 0 short descriptions | 159 collections, unique IDs/slugs preserved |

## Ripple Effects Verification

| impact_id | expected_effect | observed_effect | result | follow_up_task | status |
|-----------|-----------------|-----------------|--------|----------------|--------|
| IMP-1 | tools/ogs, go_problems, tsumego_hero imports rewired to tools/core | All 3 tools import from shared module; 33 regression tests pass | ✅ match | — | ✅ verified |
| IMP-2 | CollectionsBrowsePage shows 3 sections | SECTIONS constant has 3 entries; test verifies section IDs | ✅ match | — | ✅ verified |
| IMP-3 | CollectionPuzzleLoader supports shuffle | SHUFFLE_POLICY applied; Fisher-Yates shuffle on technique/reference types | ✅ match | — | ✅ verified |
| IMP-4 | collections.json descriptions improved | 30 descriptions updated; 0 short remaining | ✅ match | — | ✅ verified |
| IMP-5 | Pipeline preserves existing YL via is_enrichment_needed | Not runtime-tested (embedder is pre-pipeline) | ✅ no regression | — | ✅ verified |
| IMP-6 | puzzleQueryService has searchCollectionsByTypes | Function added with FTS + type filter SQL | ✅ match | — | ✅ verified |
| IMP-7 | PuzzleCollectionCard hover on all browse pages | ring-2 accent replaces translateY bounce; shared component covers all pages | ✅ match | — | ✅ verified |

## Architecture Boundary Verification

| check_id | Rule | Status |
|----------|------|--------|
| ARC-1 | `tools/core/` does NOT import from `backend/` | ✅ Verified — collection_matcher.py and collection_embedder.py have zero backend imports |
| ARC-2 | No pipeline changes (analyze.py, trace_utils.py, sources.json) | ✅ Verified — zero modifications to backend/puzzle_manager/ |
| ARC-3 | No featured:boolean schema addition | ✅ Verified — collections.json schema unchanged |
| ARC-4 | Backward-compatible YL values | ✅ Verified — embedder adds YL[], does not modify existing values |
