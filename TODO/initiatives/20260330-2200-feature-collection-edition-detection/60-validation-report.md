# Validation Report

**Initiative**: `20260330-2200-feature-collection-edition-detection`
**Date**: 2026-03-30

---

## Test Results

| VAL-1 | Test Suite | Command | Result |
|-------|-----------|---------|--------|
| VAL-1 | Backend unit tests | `pytest backend/ -m unit` | **1594 passed**, 0 failed |
| VAL-2 | Backend integration tests | `pytest backend/puzzle_manager/tests/ -m "not (cli or slow)"` | **2388 passed**, 0 failed |
| VAL-3 | New collection_slug tests (T4) | `pytest test_collection_slug.py` | **9 passed** |
| VAL-4 | New dedup bypass tests (T7) | `pytest test_dedup_bypass.py` | **5 passed** |
| VAL-5 | Migrated dedup tests (T6) | `pytest test_dedup_detection.py` | **4 passed** |
| VAL-6 | Edition detection tests (T14) | `pytest test_edition_detection.py` | **6 passed** |
| VAL-7 | Frontend edition queries (T18) | `vitest run edition-queries.test.ts` | **4 passed** |
| VAL-8 | Frontend query service (existing) | `vitest run puzzleQueryService.test.ts` | **33 passed** (1 updated for new getAllCollections filter) |
| VAL-9 | Ruff lint (new file) | `ruff check edition_detection.py` | **All checks passed** |

## Ripple Effects Validation

| impact_id | expected_effect | observed_effect | result | follow_up_task | status |
|-----------|----------------|-----------------|--------|---------------|--------|
| RE1 | Rollback calls create_editions() | Code wired in rollback.py, db_path.unlink() removed | ✅ verified | — | ✅ verified |
| RE2 | Frontend progress orphaning documented | Noted in collection-editions.md limitations | ✅ verified | — | ✅ verified |
| RE3 | Daily challenges unaffected | Daily uses level/tag, not collection | ✅ verified | — | ✅ verified |
| RE4 | Collection embedder unchanged | YL[] semantics unchanged | ✅ verified | — | ✅ verified |
| RE5 | Enrichment lab unaffected | Operates on individual SGFs | ✅ verified | — | ✅ verified |
| RE6 | Existing puzzleQueryService test updated | `getAllCollections` test updated to expect parent_id filter | ✅ verified | — | ✅ verified |

## Pre-existing Failures (Not Related)

- `frontend/tests/unit/hints.test.tsx`: 4 failures in hint reveal tests — pre-existing, unrelated to edition changes

## Files Modified

| File | Change Type | Lines Changed |
|------|------------|---------------|
| `backend/puzzle_manager/core/content_db.py` | Modified | +25 (schema, extraction, migration) |
| `backend/puzzle_manager/core/db_models.py` | Modified | +3 (source field, kwarg) |
| `backend/puzzle_manager/core/edition_detection.py` | **New** | 130 lines |
| `backend/puzzle_manager/stages/ingest.py` | Modified | +12 (cross-source dedup) |
| `backend/puzzle_manager/stages/publish.py` | Modified | +4 (source kwarg, edition wiring) |
| `backend/puzzle_manager/rollback.py` | Modified | +4/-1 (source kwarg, edition wiring, unlink fix) |
| `frontend/src/services/puzzleQueryService.ts` | Modified | +15 (edition query, parent_id filters) |
| `frontend/src/components/Collections/EditionPicker.tsx` | **New** | 63 lines |
| `frontend/src/components/Collections/index.ts` | Modified | +3 (export) |
| `frontend/src/pages/CollectionViewPage.tsx` | Modified | +30 (edition detection) |
| `backend/puzzle_manager/tests/unit/test_collection_slug.py` | **New** | 93 lines |
| `backend/puzzle_manager/tests/unit/test_dedup_bypass.py` | **New** | 116 lines |
| `backend/puzzle_manager/tests/integration/test_edition_detection.py` | **New** | 125 lines |
| `backend/puzzle_manager/tests/integration/test_dedup_detection.py` | Modified | +4 (source_id kwarg) |
| `frontend/tests/unit/edition-queries.test.ts` | **New** | 57 lines |
| `frontend/tests/unit/puzzleQueryService.test.ts` | Modified | +3 (updated assertion) |
| `docs/concepts/collection-editions.md` | **New** | 75 lines |
| `docs/concepts/sqlite-index-architecture.md` | Modified | +20 (edition section) |
| `backend/puzzle_manager/AGENTS.md` | Modified | +4 |
| `frontend/src/AGENTS.md` | Modified | +3 |
