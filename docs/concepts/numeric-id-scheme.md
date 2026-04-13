# Numeric ID Scheme

**Last Updated**: 2026-02-20

## Overview

All view indexes use **numeric IDs** instead of string slugs for level, tag, and collection references. This reduces wire payload by ~52% and enables faster client-side filtering via integer comparison. The scheme is defined in config files and used consistently across backend (view directory names, compact entries) and frontend (decode layer, URL construction).

## ID Ranges

### Level IDs (Sparse, Go-Rank-Aligned)

Kyu ranks use the 100-series; Dan ranks use the 200-series. Gaps of 10 allow future insertion without renumbering.

| ID  | Slug                 | Name               | Rank Range | Future Insertion Slots      |
| --- | -------------------- | ------------------ | ---------- | --------------------------- |
| 110 | `novice`             | Novice             | 30k-26k    | 100 = pre-novice            |
| 120 | `beginner`           | Beginner           | 25k-21k    | 121, 125 = sub-split        |
| 130 | `elementary`         | Elementary         | 20k-16k    |                             |
| 140 | `intermediate`       | Intermediate       | 15k-11k    | 141, 145, 148 = 3-way split |
| 150 | `upper-intermediate` | Upper Intermediate | 10k-6k     |                             |
| 160 | `advanced`           | Advanced           | 5k-1k      | 170 = approaching-dan       |
| 210 | `low-dan`            | Low Dan            | 1d-3d      |                             |
| 220 | `high-dan`           | High Dan           | 4d-6d      |                             |
| 230 | `expert`             | Expert             | 7d-9d      | 240 = professional          |

**Source of truth**: `config/puzzle-levels.json`

### Tag IDs (Sparse by Category)

Tags are grouped into pedagogical categories with dedicated ID bands. Each band has spare even-numbered slots for future additions.

| Range     | Category   | Tags                                                                                                                                                                                               |
| --------- | ---------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **10-28** | Objectives | 10 = life-and-death, 12 = ko, 14 = living, 16 = seki                                                                                                                                               |
| **30-52** | Tesuji     | 30 = snapback, 32 = double-atari, 34 = ladder, 36 = net, 38 = throw-in, 40 = clamp, 42 = nakade, 44 = connect-and-die, 46 = under-the-stones, 48 = liberty-shortage, 50 = vital-point, 52 = tesuji |
| **60-82** | Techniques | 60 = capture-race, 62 = eye-shape, 64 = dead-shapes, 66 = escape, 68 = connection, 70 = cutting, 72 = sacrifice, 74 = corner, 76 = shape, 78 = endgame, 80 = joseki, 82 = fuseki                   |
| **84-98** | Future     | Reserved for new categories                                                                                                                                                                        |

**Source of truth**: `config/tags.json`

### Collection IDs (Sequential)

Collections use sequential integer IDs (1, 2, 3, ...). IDs are append-only and never reassigned.

**Source of truth**: `config/collections.json`

## SQLite Path Reconstruction

Numeric IDs are stored in the `yengo-search.db` SQLite database tables:

| Table | ID Column | Example |
|-------|-----------|----------|
| `puzzles` | `level_id` | 120 (beginner) |
| `puzzle_tags` | `tag_id` | 36 (net) |
| `puzzle_collections` | `collection_id` | 1 (first collection) |

SGF file path reconstruction: `content_hash` + `batch` → `sgf/{batch}/{content_hash}.sgf`

Example: content_hash `fc38f029205dde14`, batch `0001` → `sgf/0001/fc38f029205dde14.sgf`

## Compact Entry Format

All view pages use compact entries with numeric IDs:

```json
{
  "p": "0001/fc38f029205dde14",
  "l": 130,
  "t": [12, 34, 36],
  "c": [1],
  "x": [3, 2, 19, 1]
}
```

| Key | Type     | Description                                                         |
| --- | -------- | ------------------------------------------------------------------- |
| `p` | string   | Path ref: `batch/hash` → `sgf/0001/hash.sgf`                        |
| `l` | number   | Level ID (110-230)                                                  |
| `t` | number[] | Tag IDs                                                             |
| `c` | number[] | Collection IDs                                                      |
| `x` | number[] | Complexity: [depth, refutations, solution_length, unique_responses] |
| `n` | number?  | Sequence number (collection entries only, 1-indexed)                |

## Frontend Decode Layer

- **`services/entryDecoder.ts`**: Converts SQLite PuzzleRow to domain types. Provides `expandPath()`, `decodePuzzleRow()`.
- **`services/configService.ts`**: Resolves numeric IDs to slugs/names. Provides `levelIdToSlug()`, `tagIdToSlug()`, etc.
- **`services/puzzleQueryService.ts`**: Typed SQL query functions against the SQLite database.

Downstream code works with decoded domain types only — numeric IDs never leak past the decode boundary.

## Backend ID Resolution

- **`backend/puzzle_manager/core/id_maps.py`**: The `IdMaps` class loads ID mappings from config files at pipeline startup. Used by the publish stage to write numeric IDs into `yengo-search.db` entries and by enrichment to assign numeric IDs during classification. Methods: `level_slug_to_id()`, `tag_slug_to_id()`, `collection_slug_to_id()` and reverse lookups.
- **Database keys**: `yengo-search.db` uses numeric IDs in all tables (`level_id`, `tag_id`, `collection_id`). `yengo-content.db` uses `content_hash` as primary key with a `batch` column for path reconstruction.

## Database Query Layer

The `puzzleQueryService.ts` frontend service uses numeric IDs for SQL queries against the in-memory SQLite database. ID resolution to human-readable slugs happens in the decode layer (`entryDecoder.ts`, `configService.ts`).

## Design Rationale

1. **Wire efficiency**: Numeric IDs are 2-3 bytes vs 8-20 byte slugs, yielding ~52% payload reduction.
2. **Filter performance**: Integer comparison (`entry.l === 120`) is faster than string comparison.
3. **Stability**: Numeric IDs are immutable. Slug renames (display-only) don't break published data.
4. **Sparse ranges**: Gaps between IDs allow insertion without renumbering existing entries.
5. **Category grouping**: Tag ID bands (10s = objectives, 30s = tesuji, 60s = techniques) enable O(1) category detection.

---

> **See also**:
>
> - [Reference: SQLite Index Schema](../reference/view-index-schema.md) — Full schema specification
> - [Concepts: SQLite Index Architecture](./sqlite-index-architecture.md) — Canonical terminology
> - [Architecture: System Overview](../architecture/system-overview.md) — Directory layout
> - [config/puzzle-levels.json](../../config/puzzle-levels.json) — Level ID definitions
> - [config/tags.json](../../config/tags.json) — Tag ID definitions
> - [config/collections.json](../../config/collections.json) — Collection ID definitions
