# SQLite Index Architecture

**Last Updated**: 2026-04-13

This document defines the canonical terminology and architecture for the SQLite-based puzzle index system.

## Overview

All puzzle metadata is served as a single SQLite database (`yengo-search.db`) loaded into the browser via sql.js WASM. The frontend resolves all filters via SQL queries against this in-memory database. A second database (`yengo-content.db`) is backend-only and stores SGF content with canonical position hashes for deduplication.

## Core Terms

| Term | Definition | Example |
| --- | --- | --- |
| **Search DB** | The frontend-facing SQLite database containing puzzle metadata, tags, collections, and complexity. Ships to the browser. | `yengo-search.db` |
| **Content DB** | Backend-only SQLite database storing SGF content and canonical position hashes for deduplication. | `yengo-content.db` |
| **db-version.json** | Version pointer file with puzzle count, timestamp, and schema version. Used by both frontend and backend. | `{"db_version": "20260313-a26defbf", "puzzle_count": 50}` |
| **content_hash** | 16-character hex SHA256 hash of puzzle content. Serves as puzzle identity (matches GN property and filename). | `765f38a5196edb79` |
| **batch** | Directory bucket for SGF files (e.g., "0001"). Combined with content_hash for path reconstruction. | `0001` |
| **level_id** | Numeric ID for difficulty level (110–230). Maps to level slugs via `config/puzzle-levels.json`. | `120` (beginner) |
| **tag_id** | Numeric ID for technique tags. Maps to tag slugs via `config/tags.json`. | `36` (ladder) |
| **collection_id** | Numeric ID for collections. Maps to collection slugs via `config/collections.json`. | `6` (cho-elementary) |
| **FTS5** | SQLite Full-Text Search extension used for collection name/slug search. | `collections_fts` table |

## Duplicate Detection Semantics (Ingest)

> **Canonical reference**: See [Duplicate Detection & Hashing](dedup-hashing.md) for the full three-hash system, algorithms, worked examples, decision matrix, and collision event logging.

Duplicate detection runs during ingest against `yengo-content.db` using a
two-phase check:

1. **Position hash gate** — `canonical_position_hash()` computes
   `SHA256("SZ{n}:B[sorted_ab]:W[sorted_aw]:PL[player]")[:16]` from board setup
   only (stones + size + player to move). No solution tree, comments, or metadata.

2. **Solution fingerprint comparison** — when a position collision is found from
   the same source, `compute_solution_fingerprint()` compares the moves-only
   serialization of the solution tree (comment/whitespace insensitive, branch-order
   insensitive). Same fingerprint → reject as true duplicate. Different fingerprint
   → allow as variant.

### Decision Summary

| Position | Source | Fingerprint | Result |
|---|---|---|---|
| NO MATCH | — | — | Allow |
| MATCH | Different | — | Allow (cross-source bypass) |
| MATCH | Same | MATCH | Reject (true duplicate) |
| MATCH | Same | DIFFER | Allow (variant preserved) |

### Content Hash (Publish Identity)

A separate `content_hash` — `SHA256(full_sgf_text)[:16]` — is computed at publish
and used for filenames (`{hash}.sgf`) and the `GN[YENGO-{hash}]` property. This is
not involved in dedup; it is purely for published puzzle identity.

## Database Schema (yengo-search.db)

### `puzzles` Table

| Column | Type | Description |
|--------|------|-------------|
| `content_hash` | TEXT PRIMARY KEY | 16-char hex (matches GN, filename) |
| `batch` | TEXT NOT NULL | Batch directory (e.g., "0001") |
| `level_id` | INTEGER NOT NULL | Numeric level ID (110-230) |
| `quality` | INTEGER NOT NULL DEFAULT 0 | Quality level (0-5) |
| `content_type` | INTEGER NOT NULL DEFAULT 1 | 1=curated, 2=practice, 3=training |
| `cx_depth` | INTEGER | Solution depth |
| `cx_refutations` | INTEGER | Total reading nodes |
| `cx_solution_len` | INTEGER | Solution length |
| `cx_unique_resp` | INTEGER | Unique first-move count |
| `ac` | INTEGER NOT NULL DEFAULT 0 | Analysis completeness (0=untouched, 1=enriched, 2=ai_solved, 3=verified) |

### `puzzle_tags` Table

| Column | Type | Description |
|--------|------|-------------|
| `content_hash` | TEXT NOT NULL | FK → puzzles.content_hash |
| `tag_id` | INTEGER NOT NULL | Numeric tag ID |

### `puzzle_collections` Table

| Column | Type | Description |
|--------|------|-------------|
| `content_hash` | TEXT NOT NULL | FK → puzzles.content_hash |
| `collection_id` | INTEGER NOT NULL | Numeric collection ID |
| `sequence_number` | INTEGER | Position within collection |

### `collections` Table

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PRIMARY KEY | Numeric collection ID |
| `slug` | TEXT NOT NULL | Collection slug |
| `name` | TEXT NOT NULL | Display name |
| `category` | TEXT | Collection category |
| `puzzle_count` | INTEGER | Number of puzzles |
| `attrs` | TEXT DEFAULT '{}' | JSON blob for extensible metadata |

#### Edition Sub-Collections

> **See also**: [Collection Editions](collection-editions.md) for the full concept doc (problem statement, detection logic, known limitations).

When multiple sources contribute to the same collection, synthetic edition rows are added:

- **Parent row**: `attrs` contains `{"is_parent": true, "edition_ids": [123456, 789012]}`
- **Edition rows**: `attrs` contains `{"parent_id": 10, "label": "Edition 1 (42 puzzles)", "type": "author"}`
- **Edition IDs**: Deterministic hash `SHA256(slug:source) % 10M + 100K`, range 100K–10.1M (config IDs are 1–200)
- **Puzzle mapping**: Puzzles are remapped from parent to edition via `puzzle_collections`

Frontend queries add `json_extract(attrs, '$.parent_id') IS NULL` to hide editions from browse/search.

#### Content DB `collection_slug` Column

`yengo-content.db` has a `collection_slug TEXT` column + index, populated from the `YL[]` SGF property. Used at publish for SQL-based cross-source collision detection:

```sql
SELECT collection_slug, source, GROUP_CONCAT(content_hash)
FROM sgf_files
WHERE collection_slug IS NOT NULL
GROUP BY collection_slug, source
```

### `collections_fts` Table

FTS5 virtual table for full-text search on collection names and slugs.

### `daily_schedule` Table

| Column | Type | Description |
|--------|------|-------------|
| `date` | TEXT PRIMARY KEY | ISO date (YYYY-MM-DD) |
| `version` | TEXT NOT NULL | Daily format version (e.g., "2.2") |
| `generated_at` | TEXT NOT NULL | ISO timestamp of generation |
| `technique_of_day` | TEXT | Tag slug for the day's technique focus |
| `attrs` | TEXT | JSON blob for extensible metadata |

### `daily_puzzles` Table

| Column | Type | Description |
|--------|------|-------------|
| `date` | TEXT NOT NULL | ISO date (FK → daily_schedule.date) |
| `content_hash` | TEXT NOT NULL | FK → puzzles.content_hash |
| `section` | TEXT NOT NULL | Challenge section: "standard", "timed", or "by_tag" |
| `position` | INTEGER NOT NULL | Order within section (0-indexed) |

Composite primary key: `(date, content_hash, section)`.

## Frontend Bootstrap Sequence

```text
1. Fetch yengo-search.db (~500 KB)
2. Initialize sql.js WASM
3. Load DB into memory
4. All queries via SQL (no shard fetching, no manifest resolution)
```

## Depth Preset Filter Pattern

Depth presets (`quick`, `medium`, `deep`) provide a user-friendly abstraction over the numeric `cx_depth` column. Presets are defined in `config/depth-presets.json` with `minDepth` / `maxDepth` boundaries.

### Preset → SQL Translation

The frontend translates a preset selection into a SQL range filter:

| Preset | Depth Range | SQL Clause |
|--------|-------------|------------|
| `quick` | 1–2 | `cx_depth >= 1 AND cx_depth <= 2` |
| `medium` | 3–5 | `cx_depth >= 3 AND cx_depth <= 5` |
| `deep` | 6+ | `cx_depth >= 6` (no upper bound) |

### Distribution Counts

Filter pill counts are computed via a SQL CASE expression that buckets `cx_depth` into preset IDs:

```sql
SELECT
  CASE
    WHEN p.cx_depth <= 2 THEN 'quick'
    WHEN p.cx_depth <= 5 THEN 'medium'
    ELSE 'deep'
  END AS preset,
  COUNT(DISTINCT p.content_hash) AS cnt
FROM puzzles p {join} {where}
GROUP BY preset
```

This integrates with cross-filter narrowing — depth preset counts update when level, tag, or quality filters are active.

### Config-Driven Boundaries

Preset definitions are config-driven (`config/depth-presets.json`), not hardcoded. The last preset uses `maxDepth: null` to represent an unbounded upper range.

## Path Reconstruction

`content_hash` + `batch` → `sgf/{batch}/{content_hash}.sgf`

Example: `content_hash = "765f38a5196edb79"`, `batch = "0001"` → `sgf/0001/765f38a5196edb79.sgf`

## Incremental Publish

Each pipeline run reads `yengo-content.db` for existing entries, merges with new entries, and rebuilds `yengo-search.db`. The `db-version.json` file is updated atomically with version, puzzle count, and timestamp. Rollback and reconcile operations also rebuild `yengo-search.db` from remaining `yengo-content.db` entries. Use `vacuum-db` CLI command for maintenance.

### Atomic File Writes

All DB and version file writes use a temp-file + `os.replace()` pattern to prevent partial/corrupt files:

1. Write to `yengo-search.db.tmp` (or `db-version.json.tmp`)
2. Atomically replace: `os.replace(tmp_path, final_path)`

This applies to publish, rollback, and reconcile operations.

### Deterministic Versioning

The `db_version` string in `db-version.json` uses the format `YYYYMMDD-{hex8}`. The hex suffix is derived from `SHA256(sorted content_hashes)[:8]`, ensuring deterministic builds: identical puzzle sets produce identical version strings. Rollback and reconcile operations use `datetime.now()` for the hex part since they operate outside the pipeline's deterministic context.

### Update Checking (Frontend)

The frontend stores the current `db_version` in `localStorage` on init. A `checkForUpdates()` API fetches `db-version.json` and compares against the stored version, returning whether a newer database is available. This is non-blocking and never throws.

## Relationship to Legacy Terms

| Legacy Term | New Term | Notes |
| --- | --- | --- |
| Snapshot | DB version (`db-version.json`) | Single version pointer instead of snapshot directories |
| Shard (query shard) | SQL query | Replaced by SQL WHERE/JOIN clauses |
| Manifest | yengo-search.db schema | Table structure replaces manifest.json |
| Shard meta | SQL COUNT/aggregation | Counts computed via SQL, not pre-computed meta files |
| Active snapshot pointer | `db-version.json` | Version tracking via JSON, not directory pointers |
| Query planner (frontend) | `puzzleQueryService` | SQL queries via sql.js |
| Flat sharding (SGF) | Batch directories | Unchanged — SGF files still in `sgf/{NNNN}/` |

> **See also**:
>
> - [Architecture: System Overview](../architecture/system-overview.md) — High-level architecture
> - [Architecture: Database Deployment Topology](../architecture/database-deployment-topology.md) — Deployment ADR
> - [Concepts: Numeric ID Scheme](./numeric-id-scheme.md) — ID ranges for levels, tags, collections
