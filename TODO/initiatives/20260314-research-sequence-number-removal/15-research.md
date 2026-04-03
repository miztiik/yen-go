# Research: `sequence_number` Column in `puzzle_collections` — Keep or Remove?

**Last Updated**: 2026-03-14
**Initiative**: `20260314-research-sequence-number-removal`

---

## 1. Research Question and Boundaries

**Question**: Is `sequence_number` in `puzzle_collections` (DB-1) a meaningful column with real consumers, or an arbitrary artifact that complicates incremental DB updates and can be safely removed?

**Boundaries**:
- Scope: `sequence_number` column in `puzzle_collections` table only
- Out of scope: Other DB-1 schema changes, DB-2 schema, collection `ordering` config field semantics

---

## 2. Internal Code Evidence

### 2.1 How `sequence_number` Is Computed (Backend — Write Path)

All three backend paths that build DB-1 use **identical** logic:

| R-1 | File | Lines | Logic |
|-----|------|-------|-------|
| R-1a | [publish.py](../../backend/puzzle_manager/stages/publish.py#L550-L559) | 550–559 | `enumerate(sorted(hashes), start=1)` per collection |
| R-1b | [rollback.py](../../backend/puzzle_manager/rollback.py#L248-L257) | 248–257 | Same: `enumerate(sorted(hashes), start=1)` |
| R-1c | [reconcile.py](../../backend/puzzle_manager/inventory/reconcile.py#L261-L270) | 261–270 | Same: `enumerate(sorted(hashes), start=1)` |

**The sort key is `sorted(content_hash)` — i.e., lexicographic sort of 16-char hex strings.** This is **entirely arbitrary** and does NOT reflect any curated/meaningful ordering. It ignores the `ordering` field in `config/collections.json` (which supports `manual`, `source`, `difficulty`).

| R-2 | File | Lines | Role |
|-----|------|-------|------|
| R-2a | [db_builder.py](../../backend/puzzle_manager/core/db_builder.py#L41) | 41 | Schema: `sequence_number INTEGER` (nullable) |
| R-2b | [db_builder.py](../../backend/puzzle_manager/core/db_builder.py#L115-L129) | 115–129 | Insert: looks up `sequence_map.get((hash, col_id))` |

### 2.2 Frontend Consumers (Read Path)

| R-3 | File | Line | Usage |
|-----|------|------|-------|
| R-3a | [puzzleQueryService.ts](../../frontend/src/services/puzzleQueryService.ts#L111-L114) | 111–114 | `SELECT ... pc.sequence_number ... ORDER BY pc.sequence_number` |
| R-3b | [puzzleQueryService.ts](../../frontend/src/services/puzzleQueryService.ts#L16) | 16 | `PuzzleRow.sequence_number?: number \| null` |
| R-3c | [collectionService.ts](../../frontend/src/services/collectionService.ts#L76) | 76 | `CollectionViewEntry.sequence_number: number` |
| R-3d | [collectionService.ts](../../frontend/src/services/collectionService.ts#L212) | 212 | `row.sequence_number ?? 0` in `loadCollectionViewIndex()` |
| R-3e | [puzzleLoaders.ts](../../frontend/src/services/puzzleLoaders.ts#L68) | 68 | `EnrichedEntry.sequenceNumber?: number` |
| R-3f | [puzzleLoaders.ts](../../frontend/src/services/puzzleLoaders.ts#L88) | 88 | `row.sequence_number ?? undefined` |
| R-3g | [entryDecoder.ts](../../frontend/src/services/entryDecoder.ts#L53) | 53 | `readonly sequenceNumber?: number \| undefined` |
| R-3h | [indexes.ts (types)](../../frontend/src/types/indexes.ts#L34) | 34 | `CollectionEntry.sequence_number: number` |

**Critical finding**: No component, page, or hook accesses `.sequenceNumber` on any entry object. The value flows through types but is **never read by UI rendering code**. The grep `\.sequenceNumber` across `frontend/src/components/**` and `frontend/src/pages/**` returned **zero matches**.

The `PageNavigator` component mentions "sequence number" in a comment but uses **offset-based pagination** — it never reads `sequenceNumber` from data.

### 2.3 Frontend Test Consumers

| R-4 | File | Line | Usage |
|-----|------|------|-------|
| R-4a | [puzzleQueryService.test.ts](../../frontend/src/services/__tests__/puzzleQueryService.test.ts#L60-L66) | 60–66 | Test: `getPuzzlesByCollection orders by sequence_number` |
| R-4b | [puzzleLoaders.test.ts](../../frontend/src/services/__tests__/puzzleLoaders.test.ts#L65) | 65 | Mock data: `sequence_number: null` |

### 2.4 Backend Test Consumers

| R-5 | File | Line | Usage |
|-----|------|------|-------|
| R-5a | [test_db_builder.py](../../backend/puzzle_manager/tests/unit/test_db_builder.py#L137) | 137 | `SELECT collection_id, sequence_number` |
| R-5b | [test_db_builder.py](../../backend/puzzle_manager/tests/unit/test_db_builder.py#L154) | 154 | `SELECT sequence_number` |
| R-5c | [test_db_builder.py](../../backend/puzzle_manager/tests/unit/test_db_builder.py#L252-L272) | 252–272 | GAP-9 test: `TestSequenceNumberPopulated` |

### 2.5 Backend Non-Test Consumers (Read Path)

**The daily challenge generator does NOT use `sequence_number`.** It uses its own deterministic ordering via `_helpers.py` (`puzzle_hash` and numeric ID sorting).

### 2.6 Documentation References

| R-6 | File | Description |
|-----|------|-------------|
| R-6a | [view-index-schema.md](../../docs/reference/view-index-schema.md#L66) | Schema doc: `1-indexed position within collection` |
| R-6b | [collections.md](../../docs/concepts/collections.md#L261-L272) | Concept doc: `optional sequence_number` with example queries |
| R-6c | [pipeline.md](../../docs/architecture/backend/pipeline.md#L337) | Architecture doc: `(with sequence_number)` |
| R-6d | `CLAUDE.md`, `copilot-instructions.md` | Schema table: `puzzle_collections ... (with sequence_number)` |
| R-6e | `CHANGELOG.md` line 68 | `Rollback now updates collection indexes (with sequence_number renumbering)` |

### 2.7 Legacy Tool

| R-7 | File | Line | Usage |
|-----|------|------|-------|
| R-7a | [update_collection_views.py](../../tools/update_collection_views.py#L77) | 77 | `entry["sequence_number"] = i` — pre-SQLite JSON view writer (may be deprecated) |

---

## 3. External References

| R-8 | Reference | Relevance |
|-----|-----------|-----------|
| R-8a | SQLite `ORDER BY` on TEXT columns | Hex strings sort lexicographically; `ORDER BY content_hash` produces identical ordering to current `sequence_number` since `seq = enumerate(sorted(content_hash))` |
| R-8b | SQLite `ROWID` ordering | Without explicit ORDER BY, SQLite returns rows in insertion order (not guaranteed). An explicit `ORDER BY content_hash` is needed as a replacement. |
| R-8c | Incremental DB update patterns | Precomputed sequence numbers require full renumbering when a puzzle is added/removed from a collection. This is the classic "dense rank maintenance" problem that makes incremental updates O(n) per affected collection. |
| R-8d | Go tsumego collections (domain) | Some collections (e.g., Cho Chikun Life & Death Elementary) have a meaningful author-curated puzzle order. The current implementation **ignores this**, sorting by content_hash instead. |

---

## 4. Candidate Adaptations for Yen-Go

### Option A: Remove `sequence_number` entirely

- Drop the column from schema
- Replace `ORDER BY pc.sequence_number` with `ORDER BY p.content_hash` in `getPuzzlesByCollection()`
- Remove `sequence_map` computation from publish/rollback/reconcile (~20 lines each)
- Remove from all type definitions and test assertions
- **Result**: Identical runtime behavior (same sort order: hex lex = current sequence order)

### Option B: Keep column but make it query-time computed

- Remove column from schema
- Use `ORDER BY p.content_hash` in SQL
- Same outcome as A but framed differently

### Option C: Make `sequence_number` meaningful

- Read `ordering` from `config/collections.json`
- For `ordering: "manual"`: use source file ordering or external manifest
- For `ordering: "difficulty"`: sort by `level_id` then `content_hash`
- For `ordering: "source"`: sort by original source filename/ID
- **This is a feature enhancement**, not a removal. Would require adapter changes.

### Option D: Keep as-is (status quo)

- Continue maintaining identical `sequence_map` code in 3 locations
- Incremental DB updates remain complex due to renumbering
- No runtime benefit

---

## 5. Risks, License/Compliance Notes, and Rejection Reasons

| R-9 | Risk | Severity | Mitigation |
|-----|------|----------|------------|
| R-9a | Removing column changes DB schema (requires frontend DB re-fetch) | Low | Schema version bump; frontend already handles DB updates via `db-version.json` |
| R-9b | Some external tool reads `sequence_number` | Very Low | Only `tools/update_collection_views.py` uses it; this tool writes JSON views (pre-SQLite era) |
| R-9c | Future "curated ordering" feature loses the column | Low | Column can be re-added later; current data is meaningless (just `sorted(hash)`) |
| R-9d | `ORDER BY content_hash` marginally slower than integer column | Negligible | content_hash is TEXT(16), already indexed; for ~100 puzzles per collection, difference unmeasurable |

**Rejection reasons for keeping**: The column currently stores `enumerate(sorted(content_hash))` — a value that can be trivially recomputed by `ORDER BY content_hash`. It adds schema complexity, triples the sequence_map code across publish/rollback/reconcile, and is the primary barrier to incremental DB-1 updates.

---

## 6. Planner Recommendations

1. **Remove `sequence_number` column (Option A)** — The column stores a value functionally equivalent to `ORDER BY content_hash`. No UI component reads `sequenceNumber`. The daily generator ignores it. Removing it eliminates ~60 lines of triplicated `sequence_map` construction code and removes the primary barrier to incremental INSERT/UPDATE on DB-1.

2. **Replace with `ORDER BY p.content_hash`** — In `getPuzzlesByCollection()`, change `ORDER BY pc.sequence_number` to `ORDER BY p.content_hash`. This produces an identical sort order since `sequence_number = enumerate(sorted(content_hash))`.

3. **Defer "meaningful ordering" to a future initiative (Option C)** — If curated collection ordering is desired (collections have `ordering: "manual"|"source"|"difficulty"`), that's a separate feature that requires adapter-level changes. The current `sequence_number` doesn't implement it.

4. **Update ~8 doc files and ~6 frontend type/service files** — This is a Level 3 change (multiple files, schema change) but with zero behavioral impact since no consumer reads the value for display or logic.

---

## 7. Confidence and Risk Update

| Metric | Value |
|--------|-------|
| `post_research_confidence_score` | 95 |
| `post_research_risk_level` | low |

**Confidence justification**: Exhaustive grep across entire codebase. Every reference found and categorized. No component reads `.sequenceNumber`. The computation is trivially provable as `enumerate(sorted(hash))` = `ORDER BY content_hash`.

**Remaining uncertainty**: The `tools/update_collection_views.py` script uses `sequence_number` in JSON views — need to confirm whether this tool is still active or superseded by SQLite.

---

## Open Questions

| q_id | question | options | recommended | user_response | status |
|------|----------|---------|-------------|---------------|--------|
| Q1 | Is `tools/update_collection_views.py` still in active use, or was it superseded by the SQLite pipeline? | A: Still active / B: Superseded / Other | B: Superseded | | ❌ pending |
| Q2 | Should we reserve the column name for a future "curated ordering" feature, or clean-remove it? | A: Reserve (keep column, NULL it) / B: Clean remove / Other | B: Clean remove | | ❌ pending |

---

## Handoff

| Field | Value |
|-------|-------|
| `research_completed` | true |
| `initiative_path` | `TODO/initiatives/20260314-research-sequence-number-removal/` |
| `artifact` | `15-research.md` |
| `top_recommendations` | 1. Remove column 2. Replace with ORDER BY content_hash 3. Defer curated ordering 4. Update ~14 files |
| `open_questions` | Q1 (tool active?), Q2 (reserve column?) |
| `post_research_confidence_score` | 95 |
| `post_research_risk_level` | low |
