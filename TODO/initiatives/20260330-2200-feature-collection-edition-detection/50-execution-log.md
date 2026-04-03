# Execution Log

**Initiative**: `20260330-2200-feature-collection-edition-detection`
**Started**: 2026-03-30

---

## Intake Validation

| ID | Check | Result |
|----|-------|--------|
| EX-1 | Plan approval evidence | ✅ GOV-PLAN-APPROVED, 95+ score |
| EX-2 | Task graph valid | ✅ 22 tasks, 6 phases, dependency graph verified |
| EX-3 | Analysis findings resolved | ✅ No CRITICAL findings, 4 Medium/Low accepted |
| EX-4 | Backward compat decision | ✅ Not required (additive changes) |
| EX-5 | Governance handover | ✅ 5 RCs resolved, 7 approve |
| EX-6 | Docs plan present | ✅ T19-T22 mapped to 4 doc files |

## Parallel Lane Plan

| lane_id | task_ids | scope_files | dependencies | status |
|---------|----------|-------------|--------------|--------|
| L1 | T1-T4 | content_db.py, test_collection_slug.py | None | ✅ merged |
| L2 | T5-T7 | ingest.py, test_dedup_detection.py, test_dedup_bypass.py | None | ✅ merged |
| L3 | T8-T10 | db_models.py, publish.py, rollback.py | None | ✅ merged |
| L4 | T11-T14 | edition_detection.py, publish.py, rollback.py, test_edition_detection.py | L1, L3 | ✅ merged |
| L5 | T15-T18 | puzzleQueryService.ts, EditionPicker.tsx, CollectionViewPage.tsx, CollectionsBrowsePage.tsx | None | ✅ merged |
| L6 | T19-T22 | docs/, AGENTS.md files | L4, L5 | ✅ merged |

## Execution Progress

### Phase 1-3 (L1, L2, L3 — parallel)
- **T1**: Added `collection_slug TEXT` column to `_SCHEMA_SQL`, `_ensure_collection_slug_column()` migration
- **T2**: Added `_extract_collection_slug()` with regex `YL\[([^\]:,]+)`
- **T3**: Populated `collection_slug` in `build_content_db()` INSERT
- **T4**: 9 unit tests (slug extraction, migration idempotency, build_content_db writes slug)
- **T5**: `_check_dedup()` accepts `source_id` kwarg, uses `fetchall()`, cross-source bypass
- **T6**: 4 existing dedup tests migrated to new `source_id` kwarg
- **T7**: 5 new bypass tests (no match, same source, different source, 3-source scenarios)
- **T8**: `source: str = ""` field added to `PuzzleEntry` dataclass
- **T9**: `sgf_to_puzzle_entry()` accepts keyword `source` arg
- **T10**: `publish.py` and `rollback.py` pass `source=row.get("source", "")`

### Phase 4 (L4 — depends on L1+L3)
- **T11**: Created `create_editions()` in `edition_detection.py` (130 lines)
- **T12**: Wired into `publish.py._build_search_database()` after entry merge
- **T13**: Wired into `rollback.py._rebuild_search_db()`; deleted `db_path.unlink()` (pre-emptive delete bug fix)
- **T14**: 6 integration tests (2-source, 1-source, parent flag, sequences, deterministic ID, missing DB)

### Phase 5 (L5 — independent)
- **T15**: `getEditionCollections(parentId)` query in puzzleQueryService.ts
- **T16**: `EditionPicker` component in Collections/; CollectionViewPage detects parents
- **T17**: Added `parent_id IS NULL` filter to `searchCollections()`, `searchCollectionsByTypes()`, `getAllCollections()`
- **T18**: 4 frontend tests (edition query, filters); updated 1 existing test

### Phase 6 (L6 — docs)
- **T19**: Created `docs/concepts/collection-editions.md`
- **T20**: Updated `docs/concepts/sqlite-index-architecture.md` with edition section
- **T21**: Updated `backend/puzzle_manager/AGENTS.md`
- **T22**: Updated `frontend/src/AGENTS.md`

