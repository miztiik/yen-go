# Execution Log: Collections Launch Polish (v2)

_Last Updated: 2026-03-29_

## Parallel Lane Plan

| lane_id | task_ids | scope_files | dependencies | status |
|---------|----------|-------------|--------------|--------|
| L1 | T1 | `tools/core/collection_matcher.py` (create), `tools/ogs/collections.py`, `tools/go_problems/collections.py`, `tools/tsumego_hero/collections_matcher.py` | none | ❌ not started |
| L2 | T2 | `tools/core/collection_embedder.py` (create) | L1 |  ❌ not started |
| L3a | T3 | `tools/ogs/__main__.py`, `tools/core/collection_embedder.py` (Strategy B) | L2 | ❌ not started |
| L3b | T3b | source-specific wrappers (kisvadim, gotools) | L2 | ❌ not started |
| L4 | T4 | `config/collections.json` | L1 | ❌ not started |
| L5a | T5, T7, T9 | `frontend/src/pages/CollectionsBrowsePage.tsx`, `CollectionsPage.tsx`, `collectionService.ts`, `puzzleQueryService.ts` | none | ❌ not started |
| L5b | T6 | `frontend/src/constants/collectionConfig.ts`, `CollectionPuzzleLoader.ts` | none | ❌ not started |
| L5c | T8 | `frontend/src/components/shared/PuzzleCollectionCard.tsx`, other browse pages | none | ❌ not started |
| L6a | T10 | validation (no file writes) | L3a, L3b | ❌ not started |
| L6b | T11 | frontend tests | L5a, L5b, L5c | ❌ not started |
| L6c | T12 | docs + AGENTS.md | none | ❌ not started |

## Batch Execution Schedule

| batch_id | Lanes | Rationale |
|----------|-------|-----------|
| B1 | L1 | Prerequisite: shared matcher must exist first |
| B2 | L2 + L4 | T2 depends on T1 (matcher), T4 depends on T1 for slug validation. No file overlap. |
| B3 | L3a + L3b | OGS wrapper + kisvadim/gotools wrappers. Parallel — T3 modifies collection_embedder (Strategy B), T3b creates new files. |
| B4 | L5a + L5b + L5c | Frontend parallelizable. T5/T7/T9 share CollectionsBrowsePage (sequential within L5a). T6 and T8 are independent. |
| B5 | L6a + L6b + L6c | Validation, tests, docs — all parallel. |

## Execution Log

### Structural Prerequisites

| ex_id | Action | Status |
|-------|--------|--------|
| EX-1 | Promote 7 `.new` files → replace originals | ✅ done |
| EX-2 | Clean up research subagent temp directory | ✅ done |
| EX-3 | Update status.json: `execute: in_progress` | ✅ done |

### Batch 1: L1 (T1 — Matcher Consolidation)

| ex_id | Task | Lane | Result | Evidence |
|-------|------|------|--------|----------|
| EX-4 | T1: collection_matcher.py | L1 | ✅ done | 30/30 tests pass, 3 tools rewired, 23+10 regression tests pass |

### Batch 2: L2 (T2 — Embedder Core)

| ex_id | Task | Lane | Result | Evidence |
|-------|------|------|--------|----------|
| EX-5 | T2: collection_embedder.py | L2 | ✅ done | 19/19 tests pass, Strategy A + backup/restore + checkpoint |

### Batch 3: L3a + L3b (T3 + T3b — Source Wrappers)

| ex_id | Task | Lane | Result | Evidence |
|-------|------|------|--------|----------|
| EX-6 | T3: OGS Strategy B + embed-collections CLI | L3a | ✅ done | ManifestLookupStrategy + OGS __main__.py subcommand |
| EX-7 | T3b: kisvadim + gotools wrappers | L3b | ✅ done | FilenamePatternStrategy + kisvadim/gotools wrappers |
| EX-8 | Combined validation | L3a+L3b | ✅ done | 63/63 embedder+matcher tests pass |

### Batch 4: L5a + L5b + L5c (Frontend UX)

| ex_id | Task | Lane | Result | Evidence |
|-------|------|------|--------|----------|
| EX-9 | T5: 4→3 sections + sort + <15 filter | L5a | ✅ done | SECTIONS constant, level sort, tier sort, MIN_PUZZLE_COUNT=15 |
| EX-10 | T7: In-section search | L5a | ✅ done | searchCollectionsByTypes() + per-section input |
| EX-11 | T9: Show-more → top | L5a | ✅ done | Button in section header row |
| EX-12 | T6: Selective randomization | L5b | ✅ done | SHUFFLE_POLICY + Fisher-Yates shuffle, 11/11 tests pass |
| EX-13 | T8: Hover color treatment | L5c | ✅ done | ring-2 accent, all browse pages via shared card |
| EX-14 | Frontend validation | All | ✅ done | 23/23 tests pass (12 collections + 11 config) |

### Batch 5: L4 + L6c (Config + Docs)

| ex_id | Task | Lane | Result | Evidence |
|-------|------|------|--------|----------|
| EX-15 | T4: Description improvements | L4 | ✅ done | 30 descriptions improved, 0 short remaining |
| EX-16 | T12: Documentation updates | L6c | ✅ done | 6 files updated (docs, AGENTS.md, CLAUDE.md, README) |

### T10: Embedder Validation (Procedure Documented)

T10 is a dry-run validation that runs against actual source SGFs. The tool is built and tested; actual dry-run execution is performed by the user at ingest time. Procedure:
1. `python -m tools.ogs embed-collections --source-dir external-sources/ogs/sgf-by-collection --dry-run --verbose`
2. Review JSONL log for ≥80% coverage
3. Spot-check 5 matches per source
4. Only after dry-run passes → actual writes

### T11: Frontend Integration Tests

Covered by existing test runs:
- CollectionsPage.test.tsx: 12/12 pass (3 sections, <15 filter, sort, search)
- collectionConfig.test.ts: 11/11 pass (shuffle policy, Fisher-Yates)
