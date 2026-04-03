# Plan — SQLite Puzzle Index (OPT-1: Schema-First / Frontend-Led)

**Last Updated**: 2026-03-13
**Initiative**: `20260313-2200-feature-sqlite-puzzle-index`
**Selected Option**: OPT-1 — unanimously elected by governance panel

---

## 1. Architecture

### Data Flow (New)

```
Backend Publish Pipeline
  ├── stages/publish.py → core/db_builder.py → yengo-search.db (DB-1)
  ├── stages/publish.py → core/content_db.py → yengo-content.db (DB-2, backend only)
  └── daily/generator.py reads DB-1 instead of shard files

Frontend (Browser)
  ├── Fetch yengo-puzzle-collections/yengo-search.db (~500 KB)
  ├── sql.js WASM loads DB into memory
  ├── services/sqliteService.ts → initialize + cache
  ├── services/puzzleQueryService.ts → typed SQL queries
  └── Pages/Loaders call puzzleQueryService instead of shard fetch
```

### Data Flow (Removed)

```
❌ active-snapshot.json → manifest.json → shard meta.json → shard page-NNN.json
❌ ShardWriter → 237 directories → 676 files → 8.61 MB
❌ queryPlanner.ts (DIRECT/MERGE/FALLBACK strategies)
❌ shardPageLoader.ts (array-of-arrays decoding)
❌ .shard-state.json reverse index
```

### Component Map

| New Component | Location | Replaces |
|---------------|----------|----------|
| `db_builder.py` | `backend/puzzle_manager/core/` | `shard_writer.py` + `snapshot_builder.py` |
| `content_db.py` | `backend/puzzle_manager/core/` | Nothing (new capability) |
| `db_models.py` | `backend/puzzle_manager/core/` | `shard_models.py` |
| `sqliteService.ts` | `frontend/src/services/` | `snapshotService.ts` |
| `puzzleQueryService.ts` | `frontend/src/services/` | `queryPlanner.ts` + `shardPageLoader.ts` |
| `db-version.json` | `yengo-puzzle-collections/` | `active-snapshot.json` + `manifest.json` |

---

## 2. Data Model Impact

### DB-1: Search/Metadata (see research 15-research.md §5 for full schema)

| Table | Rows (9K) | Row Size | Total |
|-------|-----------|----------|-------|
| `puzzles` | 9,059 | ~90 bytes | ~800 KB |
| `puzzle_tags` | ~18K (avg 2 tags/puzzle) | ~20 bytes | ~360 KB |
| `puzzle_collections` | ~12K (avg 1.3 cols/puzzle) | ~24 bytes | ~288 KB |
| `collections` | ~100 (growing to 5K) | ~100 bytes | ~10 KB |
| `collections_fts` | ~100 | ~50 bytes | ~5 KB |
| Indexes (6) | — | — | ~200 KB |
| **Total DB-1** | — | — | **~500 KB** |

### DB-2: SGF Content/Dedup (backend only)

| Table | Rows (9K) | Row Size | Total |
|-------|-----------|----------|-------|
| `sgf_files` | 9,059 | ~400 bytes (338 avg SGF + metadata) | ~3.5 MB |
| Indexes (3) | — | — | ~100 KB |
| **Total DB-2** | — | — | **~3.6 MB** |

### Comparison: Before vs After

| Metric | Shards (Before) | SQLite (After) | Change |
|--------|-----------------|----------------|--------|
| Frontend index size | 8.61 MB | ~500 KB | **-94%** |
| Files for index | 676 | 1 | **-99.8%** |
| Directories for index | 237 | 0 | **-100%** |
| Query capabilities | Pre-computed 2D only | Arbitrary N-dimension SQL | **Unlimited** |
| Collection search | Client-side filter | FTS5 ranked | **New** |
| Complexity filters | Not available | SQL range queries | **New** |

---

## 3. Risks and Mitigations

| ID | Risk | Severity | Mitigation |
|----|------|----------|------------|
| RK-1 | sql.js WASM cold start exceeds 300ms on mobile | Medium | Web Worker initialization, split load/query, measure in Playwright |
| RK-2 | Schema needs adjustment after frontend integration | Low | OPT-1 catches this early via sample DB; schema change = re-run seed script |
| RK-3 | Daily generator migration breaks daily challenges | Medium | Dedicated test coverage per charter RC-1; Playwright E2E for daily page |
| RK-4 | 41 files affected — large change surface | Medium | Phased execution (7 steps); each step independently testable |
| RK-5 | FTS5 not available in all sql.js builds | Low | Verify sql.js includes FTS5 extension; fallback to LIKE queries |

---

## 4. Contracts & Interfaces

### Backend → Static Files

```python
# db_builder.py output contract
def build_search_db(entries: list[PuzzleEntry], collections: list[CollectionMeta],
                     output_path: Path) -> DbVersionInfo:
    """Generate yengo-search.db with full schema from research §5."""
    ...

# content_db.py output contract
def build_content_db(sgf_files: dict[str, str], output_path: Path) -> None:
    """Generate yengo-content.db with full SGF + position hash."""
    ...

# db-version.json contract
{
    "db_version": "20260313-abc123",
    "puzzle_count": 9059,
    "generated_at": "2026-03-13T22:00:00Z",
    "schema_version": 1
}
```

### Frontend Service Contract

```typescript
// sqliteService.ts
interface SqliteService {
  init(): Promise<void>;           // Load WASM + fetch DB
  query<T>(sql: string, params?: any[]): T[];
  isReady(): boolean;
}

// puzzleQueryService.ts
interface PuzzleQueryService {
  getPuzzlesByLevel(levelId: number): PuzzleRow[];
  getPuzzlesByTag(tagId: number): PuzzleRow[];
  getPuzzlesByCollection(colId: number): PuzzleRow[];
  searchCollections(query: string): CollectionRow[];
  getFilterCounts(filters: QueryFilters): FilterCounts;
  getPuzzlesFiltered(filters: QueryFilters, limit?: number, offset?: number): PuzzleRow[];
}
```

---

## 5. Test Plan

### Backend Tests

| Test Area | Strategy | Framework |
|-----------|----------|-----------|
| `db_builder.py` | Unit: verify schema, row counts, index existence | pytest |
| `content_db.py` | Unit: verify position hash correctness, SGF content round-trip | pytest |
| `canonical_position_hash()` | Unit: sorted AB/AW produces deterministic hash | pytest |
| `daily/generator.py` | Integration: generates daily challenge from DB-1 | pytest |
| Publish stage | Integration: full pipeline produces valid .db files | pytest |

### Frontend Tests

| Test Area | Strategy | Framework |
|-----------|----------|-----------|
| `sqliteService.ts` | Unit: init, query execution, error handling | Vitest + mock sql.js |
| `puzzleQueryService.ts` | Unit: SQL correctness for each query pattern | Vitest + real sample DB |
| Loader updates | Unit: PuzzleSetLoader implementations return correct data | Vitest |
| FTS5 search | Unit: partial match, ranking, empty results | Vitest |
| Collection page | E2E: filter, search, browse works | Playwright |
| Training page | E2E: level selection loads puzzles | Playwright |
| Daily page | E2E: daily challenge loads and plays | Playwright |
| Performance | Benchmark: init + first query < 300ms | Playwright |

### Deletion Verification

| Check | Method |
|-------|--------|
| Zero "shard" in production code | `grep -r "shard" backend/puzzle_manager/ frontend/src/ --include="*.py" --include="*.ts" --include="*.tsx"` |
| Zero "snapshot" in production code (except db-version) | Same grep |
| All tests pass | `pytest -m "not (cli or slow)"` + `vitest run` |

---

## 6. Documentation Plan

| ID | File | Action | Why |
|----|------|--------|-----|
| D1 | `CLAUDE.md` | Rewrite Snapshot-Centric section → SQLite architecture | Root project guidance |
| D2 | `frontend/CLAUDE.md` | Rewrite data loading section | Frontend developer guidance |
| D3 | `.github/copilot-instructions.md` | Replace Snapshot-Centric section | AI agent guidance |
| D4 | `docs/concepts/snapshot-shard-terminology.md` | Rename → `sqlite-index-architecture.md` | Canonical concept doc |
| D5 | `docs/reference/view-index-schema.md` | Rewrite with SQLite schema | Schema reference |
| D6 | `docs/architecture/snapshot-deployment-topology.md` | Rewrite → database deployment | Architecture ADR |
| D7 | `docs/architecture/system-overview.md` | Update data flow diagram | System overview |
| D8 | `docs/how-to/backend/rollback.md` | Update rollback procedure | Operational guide |
| D9 | `docs/how-to/frontend/filtering-ux-implementation-roadmap.md` | Update filter examples | Frontend guide |
| D10 | `docs/architecture/backend/inventory-operations.md` | Update publish references | Backend ops |
| D11 | `docs/concepts/collections.md` | Update query patterns | Concept doc |
| D12 | `docs/reference/github-actions.md` | Update CI artifact paths | CI reference |
| D13 | `docs/architecture/README.md` | Update cross-references | Index page |

---

> **See also**:
> - [Charter](./00-charter.md) — Goals, acceptance criteria
> - [Options](./25-options.md) — Why OPT-1 was selected
> - [Research](../20260313-research-sqlite-puzzle-index/15-research.md) — Full SQL schema, size math
