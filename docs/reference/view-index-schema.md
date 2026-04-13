# SQLite Index Schema Reference

**Last Updated**: 2026-03-20

---

## Overview

All puzzle indexes are served as a SQLite database (`yengo-search.db`) loaded into the browser via sql.js WASM. The backend produces two databases:

| Database | Scope | Purpose |
|----------|-------|---------|
| `yengo-search.db` | Frontend (browser) | Search/metadata index, ~500 KB for 9K puzzles |
| `yengo-content.db` | Backend only | SGF content + canonical position hash for dedup |

Version tracking is via `db-version.json`:

```json
{
  "db_version": "20260313-a26defbf",
  "puzzle_count": 50,
  "generated_at": "2026-03-13T21:49:02.339747+00:00",
  "schema_version": 1
}
```

---

## yengo-search.db Schema (Ships to Browser)

### `puzzles` Table

Core puzzle metadata. One row per published puzzle.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `content_hash` | TEXT | PRIMARY KEY | 16-char hex (matches GN property and filename) |
| `batch` | TEXT | NOT NULL | Batch directory (e.g., "0001") |
| `level_id` | INTEGER | NOT NULL | Numeric level ID (110-230, from config/puzzle-levels.json) |
| `quality` | INTEGER | NOT NULL DEFAULT 0 | Quality level (0-5) |
| `content_type` | INTEGER | NOT NULL DEFAULT 1 | 1=curated, 2=practice, 3=training |
| `cx_depth` | INTEGER | | Solution depth |
| `cx_refutations` | INTEGER | | Total reading nodes |
| `cx_solution_len` | INTEGER | | Solution length |
| `cx_unique_resp` | INTEGER | | Unique first-move count |
| `ac` | INTEGER | NOT NULL DEFAULT 0 | Analysis completeness (0=untouched, 1=enriched, 2=ai_solved, 3=verified) |

### `puzzle_tags` Table

Many-to-many relationship between puzzles and tags.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `content_hash` | TEXT | NOT NULL, FK → puzzles | Puzzle identifier |
| `tag_id` | INTEGER | NOT NULL | Numeric tag ID (from config/tags.json) |

**Index**: `(content_hash, tag_id)` unique.

### `puzzle_collections` Table

Many-to-many relationship between puzzles and collections, with ordering.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `content_hash` | TEXT | NOT NULL, FK → puzzles | Puzzle identifier |
| `collection_id` | INTEGER | NOT NULL | Numeric collection ID (from config/collections.json) |
| `sequence_number` | INTEGER | | 1-indexed position within collection |

**Index**: `(content_hash, collection_id)` unique.

### `collections` Table

Collection catalog mirrored from `config/collections.json`.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY | Numeric collection ID |
| `slug` | TEXT | NOT NULL UNIQUE | Collection slug (kebab-case) |
| `name` | TEXT | NOT NULL | Human-readable display name |
| `category` | TEXT | | Collection type (author, technique, graded, etc.) |
| `puzzle_count` | INTEGER | | Number of puzzles in this collection |

### `collections_fts` Table

FTS5 virtual table for full-text search on collection names and slugs.

```sql
CREATE VIRTUAL TABLE collections_fts USING fts5(slug, name, content=collections);
```

---

## AC → Quality Relationship

The `ac` (analysis completeness) column influences quality scoring in the pipeline. Quality levels 4 ("high") and 5 ("premium") in `config/puzzle-quality.json` have a `min_ac` requirement:

| Quality Level | `min_ac` | Meaning |
|---------------|----------|----------|
| 0–3 | — | No `min_ac` gate; ac does not affect quality |
| 4 (high) | 1 | Requires at least `enriched` status |
| 5 (premium) | 2 | Requires at least `ai_solved` status |

AC values: 0 = untouched, 1 = enriched, 2 = ai_solved, 3 = verified.

This means a puzzle cannot reach high or premium quality without enrichment processing, regardless of other metrics.

---

## Common Query Patterns

### Filter by level

```sql
SELECT * FROM puzzles WHERE level_id = 120 ORDER BY content_hash LIMIT 50 OFFSET 0;
```

### Filter by tag

```sql
SELECT p.* FROM puzzles p
JOIN puzzle_tags pt ON p.content_hash = pt.content_hash
WHERE pt.tag_id = 36;
```

### Filter by level + tag (2D intersection)

```sql
SELECT p.* FROM puzzles p
JOIN puzzle_tags pt ON p.content_hash = pt.content_hash
WHERE p.level_id = 120 AND pt.tag_id = 36;
```

### Collection puzzles (ordered)

```sql
SELECT p.*, pc.sequence_number FROM puzzles p
JOIN puzzle_collections pc ON p.content_hash = pc.content_hash
WHERE pc.collection_id = 6
ORDER BY pc.sequence_number;
```

### Collection search (FTS)

```sql
SELECT c.* FROM collections_fts fts
JOIN collections c ON c.rowid = fts.rowid
WHERE collections_fts MATCH 'cho chikun';
```

### Count by level (for filter UI)

```sql
SELECT level_id, COUNT(*) as cnt FROM puzzles GROUP BY level_id;
```

---

## Path Reconstruction

`content_hash` + `batch` → `sgf/{batch}/{content_hash}.sgf`

Example: `content_hash = "765f38a5196edb79"`, `batch = "0001"` → `sgf/0001/765f38a5196edb79.sgf`

**ID Extraction**: `sgf/0001/abc123.sgf` → `abc123`

---

## Historical Evolution

| Version | Changes |
| ------- | ------- |
| v1.0–v3.0 (JSON) | Paginated JSON views with ViewEnvelope, PageDocument, MasterIndex |
| v4.0 (SQLite) | Replaced JSON views with SQLite database. All queries via SQL. |

---

> **See also**:
>
> - [Concepts: SQLite Index Architecture](../concepts/sqlite-index-architecture.md) — Terminology and architecture overview
> - [Concepts: Numeric ID Scheme](../concepts/numeric-id-scheme.md) — ID ranges for levels, tags, collections
> - [Concepts: Collections](../concepts/collections.md) — Collection taxonomy
