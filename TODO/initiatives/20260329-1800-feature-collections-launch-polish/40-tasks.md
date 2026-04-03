# Tasks: Collections Launch Polish (v2 — OPT-2)

_Last Updated: 2026-03-29_

## Task Dependency Graph

```
Phase 1 (Backend Utility):
  T1 (matcher consolidation) → T2 (embedder core) → T3 (OGS wrapper) [P] T3b (other wrappers)
  
Phase 2 (Config & Data):
  T4 (description improvements) [depends: T1]
  
Phase 3 (Frontend UX):
  T5 (sections merge + sort) [P] T6 (selective random) [P] T7 (in-section search)
  T8 (hover treatment all pages) [P] T9 (show-more reposition)
  
Phase 4 (Validation & Docs):
  T10 (embedder validation) [depends: T3]
  T11 (frontend tests) [depends: T5-T9]
  T12 (documentation updates) [P with T10-T11]
```

`[P]` = parallelizable with adjacent tasks

---

## Phase 1: Backend Utility (Embedder)

### T1: Consolidate phrase matchers into `tools/core/collection_matcher.py`

| Field | Value |
|-------|-------|
| **Status** | not-started |
| **Files** | `tools/core/collection_matcher.py` (create), `tools/ogs/collections.py` (update imports), `tools/go_problems/collections.py` (update imports), `tools/tsumego_hero/collections_matcher.py` (update imports) |
| **Goal** | G2 |
| **Description** | Extract enhanced phrase matcher from `tools/ogs/collections.py` into shared module. Features: NFKC normalize + tokenize, stop-word removal, CJK-aware splitting, longest-match-wins, optional local overrides. Rewire 3 existing tools to import from shared module. |
| **Tests** | Unit tests: exact match, phrase match, stop-word filtering, CJK input, longest-match-wins tie resolution, local override priority, no-match case. Regression tests for existing tool behavior. |
| **Acceptance** | All 3 existing tools pass with shared matcher. No behavior change in existing collection resolution. |

### T2: Build embedder core in `tools/core/collection_embedder.py`

| Field | Value |
|-------|-------|
| **Status** | not-started |
| **Depends** | T1 |
| **Files** | `tools/core/collection_embedder.py` (create) |
| **Goal** | G1 |
| **Description** | Strategy interface (`EmbedStrategy` protocol), registry, core `embed_collections()` function. Implements Strategy A (phrase match). Minimal-edit SGF: parse via `tools.core.sgf_parser`, use `SGFBuilder.from_tree()` round-trip mode which preserves ALL existing properties, add/update only `YL[]`. **SGF formatting note**: `publish_sgf()` round-trip may introduce minor whitespace differences in output. This is acceptable for `external-sources/` files because these files are (a) not git-tracked, (b) will be whitelist-rebuilt by the pipeline at ingest anyway, (c) only the `YL[]` value matters semantically. **Write safety**: Uses `atomic_write_text()` from `tools/core/atomic_write.py` for each file write — temp file + rename pattern prevents partial writes on crash. **Backup**: Before overwriting any SGF, the embedder creates a `.yl-backup` copy of the original file in the same directory. A `--restore-backups` flag reverses all modifications, providing full rollback. Idempotent: skip if YL already present with same slug. Checkpoint per directory. JSONL logging with embed events. |
| **Tests** | Unit tests: SGF with no YL → YL added, SGF with same-slug YL → skipped, SGF with different-slug YL → warned+skipped. Strategy A: directory name → slug resolution. Checkpoint resume: skips already-processed dirs. Dry-run mode: no file writes. Backup/restore: `.yl-backup` files created on write, `--restore-backups` reverses all modifications. Atomic write: interrupted mid-batch → no partial files. |
| **CLI Flags** | `--source-dir`, `--strategy`, `--dry-run`, `--resume`, `--verbose`, `--no-log-file` |
| **Acceptance** | Embedder processes a test directory; YL values match collections.json slugs; JSONL log produced; checkpoint written. |

### T3: OGS thin wrapper + Strategy B (manifest lookup)

| Field | Value |
|-------|-------|
| **Status** | not-started |
| **Depends** | T2 |
| **Files** | `tools/ogs/__main__.py` (add `embed-collections` subcommand), `tools/core/collection_embedder.py` (add Strategy B) |
| **Goal** | G3 |
| **Description** | OGS-specific strategy: read `20260211-203516-collections-sorted.jsonl`, build reverse index (puzzle_id → collection + position), match collection names via `CollectionMatcher`, embed `YL[slug:0/position]`. Position from `puzzles` array index. Chapter 0. |
| **Tests** | Unit tests: JSONL parsing, reverse index building, position encoding. Integration test against sample OGS SGF files. Coverage validation: ≥80% of OGS directories resolve to known slugs. |
| **Acceptance** | OGS `sgf-by-collection/` SGFs get correct YL tags. Coverage ≥80%. JSONL logs show match/skip/error counts. |

### T3b: Other source wrappers (kisvadim, gotools) [P with T3]

| Field | Value |
|-------|-------|
| **Status** | not-started |
| **Depends** | T2 |
| **Files** | Source-specific wrappers (may add to existing tool directories or create new ones) |
| **Goal** | G3 |
| **Description** | **IN scope** (this initiative): (a) kisvadim-goproblems: Strategy A (phrase match on folder names like "Cho Chikun Encyclopedia Life And Death - Elementary"). (b) gotools: Strategy C (filename pattern `gotools_lv{N}_{ch}_p{id}.sgf`). **DEFERRED** (follow-up): eidogo (~200 puzzles), tasuki (~200), 101weiqi (~500), syougo (~130) — low puzzle counts, Strategy A applicable when needed. |
| **Tests** | Per-source: sample directory → correct YL values. Regex tests for gotools filename pattern. |
| **Acceptance** | Each source produces correct YL values for ≥80% of identifiable collections. |

---

## Phase 2: Config & Data

### T4: Improve weak collection descriptions

| Field | Value |
|-------|-------|
| **Status** | not-started |
| **Depends** | T1 (needs matcher to identify weak slugs) |
| **Files** | `config/collections.json` |
| **Goal** | G10 |
| **Description** | Identify collections with vague descriptions (e.g., "taruc-practice", single-word descriptions). Write meaningful descriptions for browse card display. Data change only — no schema update. |
| **Tests** | Validate all descriptions are ≥20 characters and describe the collection's content/difficulty. |
| **Acceptance** | No collection has a single-word or generic description. |

---

## Phase 3: Frontend UX

### T5: Merge 4 browse sections → 3; apply section sorting

| Field | Value |
|-------|-------|
| **Status** | not-started |
| **Files** | `frontend/src/pages/CollectionsBrowsePage.tsx`, `frontend/src/pages/CollectionsPage.tsx` (if exists as separate), `frontend/src/services/collectionService.ts` |
| **Goal** | G4, G5, G6 |
| **Description** | (a) Update `SECTIONS` constant: Learning Paths (graded), Practice (technique+reference), Books (author). (b) Learning Paths: sort by `level_hint` mapped to `puzzle-levels.json` numeric order. (c) Books: sort by tier rank (editorial>premier>curated) → quality → puzzle_count desc → name alpha. (d) Filter: hide collections with <15 puzzles from browse sections (not from search). (e) **Section visibility threshold**: if a section has <2 visible collections after <15 filter, hide the section entirely to avoid a single-card section. |
| **Tests** | Component tests: 3 sections rendered, correct types in each, sort order verified, <15 filter applied, search still shows filtered-out collections. |
| **Acceptance** | Browse page shows 3 sections. Learning Paths in difficulty order. Books sorted by quality. <15 hidden from browse. |

### T6: Selective randomization (toggleable)

| Field | Value |
|-------|-------|
| **Status** | not-started |
| **Files** | `frontend/src/constants/collectionConfig.ts` (create), `frontend/src/services/puzzleLoaders/CollectionPuzzleLoader.ts`, `frontend/src/services/collectionService.ts` |
| **Goal** | G7 |
| **Description** | (a) Create `SHUFFLE_POLICY` constant: `{ graded: false, author: false, technique: true, reference: true, system: false }`. (b) **Type resolution mechanism**: `CollectionViewPage` already knows the collection slug. Add a `collectionType` parameter to `CollectionPuzzleLoader` constructor, resolved by `CollectionViewPage` from the loaded catalog (`catalog.collections.find(c => c.slug === slug)?.type`). (c) In `CollectionPuzzleLoader.loadSet()`, after loading puzzles by `sequence_number`, check `SHUFFLE_POLICY[this.collectionType]`. (d) If true: Fisher-Yates shuffle on loaded array. If false: keep sequence order. (e) Toggleable: setting to false disables randomization globally for future. |
| **Tests** | Unit test: technique collection → shuffled array, author collection → sequential. Config toggle test. |
| **Acceptance** | Technique/training collections present random order per session. Books/author maintain author's sequence. |

### T7: DB-scoped in-section search

| Field | Value |
|-------|-------|
| **Status** | not-started |
| **Files** | `frontend/src/pages/CollectionsBrowsePage.tsx`, `frontend/src/services/puzzleQueryService.ts` |
| **Goal** | G8 |
| **Description** | (a) Add `searchCollectionsByType(query, types[])` to `puzzleQueryService.ts` using `collections_fts` + type filter. (b) Add small search input in each section header. (c) Debounced input filters collections within that section via DB query. (d) Global search bar remains — collapses sections into flat results (existing behavior). |
| **Tests** | Query test: search "cho" within Books section → only author-type collections. UI test: section search box renders, debounces, filters correctly. |
| **Acceptance** | Each section has a search box. Typing filters within that section only. Global search still works. |

### T8: Hover color treatment — all browse pages

| Field | Value |
|-------|-------|
| **Status** | not-started |
| **Files** | `frontend/src/components/shared/PuzzleCollectionCard.tsx`, technique browse page (if exists), training browse page (if exists) |
| **Goal** | G9 (partial) |
| **Description** | (a) Replace or augment current `hover:-translate-y-1 hover:shadow-xl` with color treatment using CSS custom properties. (b) Apply consistently across all browse pages (collections, technique, training). (c) Must work in both light and dark themes. UX expert consulted for final color choices. |
| **Tests** | Visual regression test or manual verification in both themes. |
| **Acceptance** | All browse page cards have consistent hover color treatment in both themes. |

### T9: "Show more" button → top of section

| Field | Value |
|-------|-------|
| **Status** | not-started |
| **Files** | `frontend/src/pages/CollectionsBrowsePage.tsx` |
| **Goal** | G9 (partial) |
| **Description** | Move "Show all N collections" button from below the card grid to the section header row, inline with title and search box. Layout: `[Title (count)] [search] [Show all →]`. Apply to all browse pages with expandable sections. |
| **Tests** | UI test: button renders in header row, expand/collapse still works, layout correct on mobile. |
| **Acceptance** | Button at top of section. No visual jarring on initial load. |

---

## Phase 4: Validation & Docs

### T10: Embedder validation run

| Field | Value |
|-------|-------|
| **Status** | not-started |
| **Depends** | T3, T3b |
| **Description** | **Must execute BEFORE any actual (non-dry-run) embedder writes.** Dependency: T10 dry-run validation → actual embed runs (T3/T3b non-dry-run). Steps: (a) Run embedder with `--dry-run` against all priority sources (OGS, kisvadim, gotools). (b) Review dry-run JSONL output: verify ≥80% YL coverage per source, 0 false positives (wrong slug assignments), logs parseable and complete. (c) Spot-check 5 sample matches per source against `config/collections.json` aliases manually. (d) Document unmatched folders for follow-up alias updates. (e) Only after dry-run passes can actual writes proceed. (f) Actual writes create `.yl-backup` files — rollback available via `--restore-backups` if post-write issues found. |
| **Acceptance** | Dry-run results show ≥80% coverage. No false positives. Unmatched folder list reviewed. |

### T11: Frontend integration tests

| Field | Value |
|-------|-------|
| **Status** | not-started |
| **Depends** | T5, T6, T7, T8, T9 |
| **Description** | (a) Component tests for 3-section layout, sort orders, <15 filter. (b) Shuffle policy test. (c) In-section search query test. (d) Hover treatment visual check. (e) Show-more button position test. |
| **Acceptance** | All frontend tests pass. No regressions in existing collection flow. |

### T12: Documentation updates [P with T10, T11]

| Field | Value |
|-------|-------|
| **Status** | not-started |
| **Files** | See Documentation Plan in `30-plan.md` |
| **Goal** | All |
| **Description** | (a) Update `docs/concepts/collections.md`: chapter 0 convention, embedder utility, multi-strategy approach. (b) Update `tools/core/AGENTS.md`: new modules. (c) Update `frontend/src/AGENTS.md`: section config, shuffle policy, in-section search. (d) Update `CLAUDE.md`: tool descriptions. (e) Update `tools/core/README.md`. (f) Update `docs/how-to/backend/tool-development-standards.md`: minimal-edit SGF exception. |
| **Acceptance** | All AGENTS.md updated in same commit as structural code changes. Docs reflect v2 architecture. |
