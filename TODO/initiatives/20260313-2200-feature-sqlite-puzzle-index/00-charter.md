# Charter — SQLite Puzzle Index

**Last Updated**: 2026-03-13
**Initiative**: `20260313-2200-feature-sqlite-puzzle-index`
**Type**: Feature (architecture replacement)

---

## 1. Summary

Replace the shard-file index system with two SQLite databases: a search/metadata index shipped to the browser via sql.js WASM, and a backend-only SGF content database for duplicate detection. Complete removal of all shard infrastructure.

## 2. Goals

| ID | Goal |
|----|------|
| G1 | **DB-1 (Search Index)**: Single SQLite database (~500 KB at 9K puzzles) serves as the sole puzzle query engine in the browser, replacing 237 shard directories / 676 JSON files (8.61 MB). |
| G2 | **DB-2 (Content/Dedup)**: Backend-only SQLite database stores full SGF content with canonical position hash (sorted AB/AW) for cross-source duplicate identification. |
| G3 | **Arbitrary N-dimension search**: Frontend supports intersection of level × tag × collection × quality × complexity × content_type in a single SQL query. No pre-computed shard combinations. |
| G4 | **FTS5 collection search**: Fuzzy text search across ~5K collection names, slugs, and aliases. |
| G5 | **All-numeric IDs**: Level (110-230), tag (10-98), collection (1-N), quality (0-5), content_type (1-3) stored as INTEGER for minimal DB size. |
| G6 | **Extensible schema**: `attrs TEXT` JSON column on puzzle and collection tables for horizontal growth without schema migration. |
| G7 | **Complete shard removal**: Delete ShardWriter, shard_key, shard_models, queryPlanner, shardPageLoader, snapshot manifests, shard directories, and all related code. |
| G8 | **Documentation overhaul**: Update all docs (CLAUDE.md, frontend/CLAUDE.md, docs/, copilot-instructions.md) to remove shard/snapshot references and document the SQLite architecture. |
| G9 | clarify that sql.js is a query engine, not browser AI. |

## 3. Non-Goals

| ID | Non-Goal |
|----|----------|
| NG1 | Rotation-normalized duplicate detection (8 symmetries). Too complex, low ROI for V1. |
| NG2 | HTTP range request support (sql.js-httpvfs). Full download is correct for offline-first PWA. |
| NG3 | Backend dual output (shards + DB). Clean break, DB only. |
| NG4 | Backward compatibility with existing shard format. Republish is acceptable. |
| NG5 | Custom compression. GitHub Pages CDN handles gzip/brotli automatically. |
| NG6 | Migration tooling for shard → DB. One-time republish from SGF source files. |
| NG7 | Frontend WASM fallback for browsers without WebAssembly (>96% global support). |

## 4. Constraints

| ID | Constraint |
|----|-----------|
| C1 | Zero Runtime Backend. SQLite DB is a static file on GitHub Pages. |
| C2 | Determinism not required for AI analysis. |
| C3 | Local-First. User progress stays in localStorage, not in SQLite. |
| C4 | DB files are build artifacts → `.gitignore`. Not tracked in git. |
| C5 | `db-version.json` lives at `yengo-puzzle-collections/db-version.json`. |
| C6 | sql.js is the WASM library (MIT license, ~1.2 MB). |
| C7 | Python `sqlite3` stdlib module for backend DB generation (no new dependency). |
| C8 | SGF files continue to exist as individual `.sgf` files in `yengo-puzzle-collections/sgf/`. DB-1 references them by `batch/content_hash` path. |

## 5. Acceptance Criteria

| ID | Criterion | Verification |
|----|-----------|-------------|
| AC1 | DB-1 serves all current frontend browse/filter/search patterns via SQL queries | Vitest tests comparing SQL results to expected entries |
| AC2 | DB-1 file size ≤ 1 MB for 9K puzzles (currently 8.61 MB as shards) | Measure output of publish pipeline |
| AC3 | sql.js initialization + first query < 300ms on desktop | Performance test in Playwright |
| AC4 | FTS5 collection search returns results for partial name matches | Vitest test suite |
| AC5 | DB-2 canonical position hash detects same-position puzzles from different sources | pytest test with known duplicate SGFs |
| AC6 | All shard-related code deleted (grep for "shard" returns zero hits in production code) | grep verification |
| AC7 | All existing frontend pages function correctly (collections, training, technique, daily) | Playwright E2E smoke tests |
| AC8 | Service worker caches `.db` file with stale-while-revalidate strategy | Manual verification + Lighthouse audit |
| AC9 | `docs/` updated: zero references to "shard", "snapshot manifest", "active-snapshot.json" | grep verification |
| AC10 | Backend `pytest -m "not (cli or slow)"` passes with zero failures | CI gate |

## 6. Scope Boundary

### In Scope
- SQL schema design and implementation (DB-1 + DB-2)
- Backend `core/db_builder.py` and `core/content_db.py`
- Frontend `services/sqliteService.ts` and `services/puzzleQueryService.ts`
- Deletion of shard infrastructure (backend + frontend)
- Daily challenge generator migration (`daily/generator.py`) — migrate from shard reading to DB-1 querying
- Daily-related test updates (`test_daily_master_index.py`, `test_daily_quality_weighting.py`)
- Service worker update for `.db` caching
- Documentation overhaul
- `.gitignore` update

### Out of Scope
- Puzzle enrichment pipeline (tools/puzzle-enrichment-lab)
- SGF file format changes
- User progress storage (remains localStorage)
- Config file format changes (tags.json, puzzle-levels.json, collections.json remain as-is)

---

> **See also**:
> - [Research: SQLite Puzzle Index](../20260313-research-sqlite-puzzle-index/15-research.md) — Full research brief with schema design, governance opinions, size estimates
> - [Numeric ID Scheme](../../docs/concepts/numeric-id-scheme.md) — ID ranges for levels, tags, collections
