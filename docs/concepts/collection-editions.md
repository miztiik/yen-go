# Collection Editions

**Last Updated**: 2026-04-13

---

## Problem Statement

Two problems occur when multiple sources contribute puzzles to the same collection:

### Problem 1: Same-Source Variant Loss at Ingest (Resolved)

Ingest dedup now uses a two-phase check: position hash gate followed by solution
fingerprint comparison. Same-source puzzles with the same board position but
**different solution trees** are allowed through as variants. Only true duplicates
(same position + same source + same fingerprint) are rejected.

> **See also**: [Duplicate Detection & Hashing](dedup-hashing.md) — full algorithm, decision matrix, and collision event logging.

### Problem 2: Interleaved Ordering at Publish

When both sources' puzzles land in the same collection via `YL[]` aliases, they're merged into one flat list. The sort tiebreaker (`content_hash`) scrambles the pedagogical order that each source carefully maintained.

## How Detection Works

### `collection_slug` Column

The `sgf_files` table in `yengo-content.db` has a `collection_slug TEXT` column, populated from the `YL[]` SGF property during `build_content_db()`. The regex `YL\[([^\]:,]+)` extracts the first slug, stopping at commas, colons, or closing brackets.

### SQL-Based Collision Detection

At publish time, `create_editions()` queries:

```sql
SELECT collection_slug, source, GROUP_CONCAT(content_hash)
FROM sgf_files
WHERE collection_slug IS NOT NULL AND source IS NOT NULL
GROUP BY collection_slug, source
```

Collections with 2+ distinct sources get edition sub-collections.

### Cross-Source Dedup Bypass

`_check_dedup()` in `ingest.py` uses source-aware, fingerprint-aware dedup. Same-source true duplicates (same position + same fingerprint) are rejected. Same-source variants (different fingerprint) and cross-source duplicates are allowed through.

> **See also**: [Duplicate Detection & Hashing](dedup-hashing.md) — complete decision matrix.

## Edition Sub-Collections in `yengo-search.db`

Edition sub-collections are synthetic rows in the `collections` table with JSON attrs:

```json
{
  "parent_id": 10,
  "label": "Edition 1 (42 puzzles)",
  "type": "author"
}
```

The parent collection gets:

```json
{
  "is_parent": true,
  "edition_ids": [123456, 789012]
}
```

### Edition ID Allocation

Edition IDs are deterministic: `SHA256(slug:source) % 10M + 100K`. Range 100K–10.1M, well outside config IDs (1–200).

### Puzzle Remapping

When editions are created, puzzles are remapped from the parent collection ID to their edition's ID. Each edition has independent sequence numbers 1–N, preserving each source's pedagogical order.

## Frontend EditionPicker

When a user navigates to a parent collection, `CollectionViewPage` detects `is_parent=true` with edition sub-collections. Instead of showing puzzles, it renders an `EditionPicker` component with cards for each edition.

Edition sub-collections are hidden from browse/search queries via `json_extract(attrs, '$.parent_id') IS NULL` filters on all collection-returning queries.

## Known Limitations

- **Progress orphaning**: When a collection splits into editions, progress data keyed to the parent's ID is not migrated. Users start fresh on each edition.
- **Generic labels**: Edition labels are functional (`"Edition 1 (42 puzzles)"`) but don't indicate the source origin, as raw source IDs (e.g., "kisvadim") are meaningless to Go players.
- **Single-slug detection**: `collection_slug` stores only the first slug for multi-collection puzzles (`YL[a,b]`). Collision detection triggers on any shared slug, not all.
- **Legacy entries**: Pre-existing entries without `collection_slug` (NULL) are excluded from collision detection.

> **See also**:
>
> - [SQLite Index Architecture](sqlite-index-architecture.md) — Edition rows in collections table
> - [How-To: CLI Reference](../how-to/backend/cli-reference.md) — Pipeline commands
> - [Architecture: Pipeline](../architecture/backend/pipeline.md) — 3-stage pipeline
