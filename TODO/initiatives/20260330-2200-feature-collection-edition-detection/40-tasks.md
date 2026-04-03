# Tasks: Collection Edition Detection

**Last Updated**: 2026-03-30  
**Total Tasks**: 22

---

## Phase 1: Schema Change — Add `collection_slug` to Content DB

| T_ID | Task | Files | Depends | Parallel | Acceptance Criteria |
|------|------|-------|---------|----------|-------------------|
| T1 | Add `collection_slug TEXT` column and index to `yengo-content.db` schema | `backend/puzzle_manager/core/content_db.py` | — | | Add column to `_SCHEMA_SQL`. Add `_ensure_collection_slug_column()` migration helper (same pattern as existing `_ensure_batch_column()`). Add `CREATE INDEX IF NOT EXISTS idx_sgf_collection ON sgf_files(collection_slug)`. |
| T2 | Add `_extract_collection_slug(sgf_content)` helper to parse `YL[]` from raw SGF text | `backend/puzzle_manager/core/content_db.py` | T1 | | Regex: `r'YL\[([^\]:,]+)'` (stops at comma, colon, or `]`). Returns first collection slug or None. Handles: no YL, YL with chapter/position suffix (`YL[slug:3/12]`), YL with comma-separated slugs (`YL[a,b]` → `"a"`). |
| T3 | Populate `collection_slug` in `build_content_db()` during row construction | `backend/puzzle_manager/core/content_db.py` | T1, T2 | | In `build_content_db()`: call `_extract_collection_slug(sgf_content)` for each entry, include in INSERT row. UPDATE the `INSERT OR REPLACE` SQL to include the new column. |
| T4 | Write unit tests for schema change and slug extraction | `tests/unit/test_collection_slug.py` (NEW) | T1-T3 | | Tests: (1) `_extract_collection_slug("...YL[cho-elementary:0/42]...")` returns `"cho-elementary"`; (2) No YL → None; (3) Multi-slug `YL[a,b]` → `"a"`; (4) `_ensure_collection_slug_column()` is idempotent; (5) `build_content_db()` writes `collection_slug` column. |

## Phase 2: Dedup Bypass — Allow Cross-Source Duplicates

| T_ID | Task | Files | Depends | Parallel | Acceptance Criteria |
|------|------|-------|---------|----------|-------------------|
| T5 | Modify `_check_dedup()` to accept `source_id` kwarg; use `fetchall()`; allow cross-source matches | `backend/puzzle_manager/stages/ingest.py` (line ~265) | — | [P] with T1 | Keep `@staticmethod`. New signature: `@staticmethod def _check_dedup(conn, sgf_content, *, source_id: str) -> str | None`. Uses `fetchall()`. Rejects if ANY row matches current source. Allows if ALL rows are from different sources. Update single caller in `run()` method (line ~128): `self._check_dedup(dedup_conn, result.sgf_content, source_id=source.id)`. |
| T6 | Migrate 5 existing `_check_dedup` tests to new signature | `tests/integration/test_dedup_detection.py` | T5 | | All 5 tests add `source_id="test"` kwarg. Calling convention unchanged (`IngestStage._check_dedup(conn, sgf, source_id="test")`) because method stays `@staticmethod`. |
| T7 | Write new dedup bypass tests | `tests/unit/test_dedup_bypass.py` (NEW) | T5 | | 5 tests: (1) No match → allow; (2) Same source match → reject; (3) Different source match → allow; (4) 3 sources, one matches → reject; (5) 3 sources, none match → allow. |

## Phase 3: Source Plumbing — PuzzleEntry Gets `source` Field

| T_ID | Task | Files | Depends | Parallel | Acceptance Criteria |
|------|------|-------|---------|----------|-------------------|
| T8 | Add `source: str = ""` field to `PuzzleEntry` dataclass | `backend/puzzle_manager/core/db_models.py` (line ~23) | — | [P] | Field exists after `ac`. Default `""`. NOT added to `_insert_puzzles()` in `db_builder.py` (transient field). All existing tests pass. |
| T9 | Update `sgf_to_puzzle_entry()` to accept `source` kwarg | `backend/puzzle_manager/core/db_models.py` (line ~85) | T8 | | Keyword-only arg after `batch_hint`. Passed through to `PuzzleEntry(source=source)`. |
| T10 | Pass `row["source"]` when converting content DB rows in `publish.py._build_search_database()` and `rollback.py._rebuild_search_db()` | `backend/puzzle_manager/stages/publish.py` (line ~565), `backend/puzzle_manager/rollback.py` (line ~222) | T9 | | Both call sites pass `source=row.get("source", "")` to `sgf_to_puzzle_entry()`. |

## Phase 4: Edition Detection — Shared Utility

| T_ID | Task | Files | Depends | Parallel | Acceptance Criteria |
|------|------|-------|---------|----------|-------------------|
| T11 | Create `create_editions()` function in shared utility | `backend/puzzle_manager/core/edition_detection.py` (NEW) | T3, T10 | | Function signature: `create_editions(all_entries, collections, content_db_path) -> list[CollectionMeta]`. Queries content DB for `SELECT collection_slug, source, GROUP_CONCAT(content_hash) FROM sgf_files WHERE collection_slug IS NOT NULL GROUP BY collection_slug, source`. Finds collections with 2+ sources. Creates edition `CollectionMeta` objects. Remaps puzzle `collection_ids`. Returns new editions. |
| T12 | Wire `create_editions()` into `publish.py._build_search_database()` | `backend/puzzle_manager/stages/publish.py` | T11 | | Call after building `all_entries`, before building `sequence_map`. Extend `collections` with returned editions. |
| T13 | Wire `create_editions()` into `rollback.py._rebuild_search_db()` + fix atomic swap | `backend/puzzle_manager/rollback.py` | T11 | [P] with T12 | (1) Pass `source=row.get("source", "")` to `sgf_to_puzzle_entry()` at line ~222; (2) Call `create_editions(entries, collections, content_db_path)` before `build_search_db()`; (3) Extend `collections` with returned editions; (4) **Delete `db_path.unlink()` at line ~246** — the existing `os.replace(tmp, final)` at lines ~260-273 already handles overwrite atomically. This 1-line deletion fixes the pre-existing bug where rollback failure destroys search DB permanently. |
| T14 | Write integration tests for edition detection (publish + rollback paths) | `tests/integration/test_edition_detection.py` (NEW) | T11-T13 | | 6 tests: (1) 2-source collection → 2 editions; (2) 1-source → no editions; (3) Parent has `is_parent=true`; (4) Each edition has independent sequence 1-N; (5) Rollback produces editions (not interleaved); (6) Rollback failure leaves DB-1 intact (mock crash). |

## Phase 5: Frontend — Edition Picker

| T_ID | Task | Files | Depends | Parallel | Acceptance Criteria |
|------|------|-------|---------|----------|-------------------|
| T15 | Add `getEditionCollections(parentId)` query | `frontend/src/services/puzzleQueryService.ts` | — | [P] | SQL: `SELECT * FROM collections WHERE json_extract(attrs, '$.parent_id') = ? ORDER BY puzzle_count DESC`. Returns `CollectionRow[]`. |
| T16 | Create `EditionPicker` component + modify `CollectionViewPage` to detect parents | `frontend/src/components/collections/EditionPicker.tsx` (NEW), `frontend/src/pages/CollectionViewPage.tsx` | T15 | | EditionPicker renders edition cards with label, puzzle count, onClick navigates to edition's collection page. CollectionViewPage checks `is_parent && edition_ids.length > 0` → shows EditionPicker. Empty parent → shows "No editions available". |
| T17 | Filter editions from ALL browse/search queries; exempt parents from MIN_PUZZLE_COUNT | `frontend/src/pages/CollectionsBrowsePage.tsx`, `frontend/src/services/puzzleQueryService.ts` | T15 | [P] with T16 | Audit ALL collection-returning queries and add `AND json_extract(c.attrs, '$.parent_id') IS NULL` filter. Checklist: (1) `searchCollections()` (line ~121); (2) `searchCollectionsByTypes()` (line ~138); (3) `getAllCollections()` (line ~157); (4) any other query returning collection rows used in browse grid or search. Parent collections exempt from `MIN_PUZZLE_COUNT` filter. Badge shows "N editions". |
| T18 | Write frontend tests | `frontend/tests/` | T16, T17 | | Vitest tests: (1) Parent shows EditionPicker; (2) Edition shows puzzle list; (3) Browse hides editions; (4) Search excludes editions; (5) Empty parent shows error state. |

## Phase 6: Documentation

| T_ID | Task | Files | Depends | Parallel | Acceptance Criteria |
|------|------|-------|---------|----------|-------------------|
| T19 | Create `docs/concepts/collection-editions.md` — edition model concept doc | `docs/concepts/collection-editions.md` (NEW) | T14 | [P] | Sections: (1) Problem statement (content loss + interleaving) with examples; (2) How detection works (`collection_slug` column + SQL GROUP BY); (3) Edition sub-collections in `yengo-search.db` (attrs JSON shape, parent/child); (4) Frontend EditionPicker behavior; (5) Known limitations (progress orphaning, generic labels); (6) See-also cross-references. |
| T20 | Update `docs/concepts/sqlite-index-architecture.md` — add edition sub-collections | `docs/concepts/sqlite-index-architecture.md` | T14 | [P] | Add: edition rows in `collections` table with attrs examples; `puzzle_collections` mapping to edition IDs; edition ID range (100K–10.1M) vs config IDs (1–200); `collection_slug` column in content DB. |
| T21 | Update `backend/puzzle_manager/AGENTS.md` — edition detection in publish + rollback | `backend/puzzle_manager/AGENTS.md` | T14 | [P] | Add: `edition_detection.py` module (`create_editions()` function); dedup bypass in ingest (`_check_dedup` new signature); `collection_slug` column in content DB schema; shared utility called by both publish and rollback. |
| T22 | Update `frontend/src/AGENTS.md` — EditionPicker and edition queries | `frontend/src/AGENTS.md` | T18 | [P] | Add: `EditionPicker` component (location, props, behavior); `getEditionCollections()` query; parent detection in `CollectionViewPage`; browse/search filtering (`parent_id IS NULL`). |

---

## Dependency Graph

```
T1 ──> T2 ──> T3 ──> T4
                 └──> T11 ──> T12 ──> T14 ──> T19, T20, T21
                       │
T5 ──> T6             T13 (parallel with T12)
  └──> T7
                       
T8 ──> T9 ──> T10 ──> T11

T15 ──> T16 ──> T18 ──> T22
   └──> T17
```

## Parallel Execution Groups

| Group | Tasks | Why independent |
|-------|-------|-----------------|
| A | T1, T5, T8, T15 | Schema change, dedup bypass, PuzzleEntry field, frontend query — all different files |
| B | T12, T13 | Publish wiring and rollback wiring are independent |
| C | T16, T17 | EditionPicker and browse filtering are independent |
| D | T19, T20, T21, T22 | All documentation tasks are independent |
