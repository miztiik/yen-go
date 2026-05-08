# Duplicate Detection & Hashing

**Last Updated**: 2026-04-13

---

This document is the canonical reference for the three-hash system used to detect duplicates, identify puzzle variants, and assign published filenames.

## Hash Inventory

The pipeline uses three independent hashes — each with exactly one job:

| Hash | Computed From | Purpose | Length | Stored In |
| ------ | -------------- | --------- | -------- | ----------- |
| `position_hash` | Board setup: `SZ + sorted(AB) + sorted(AW) + PL` | Ingest dedup gate (position identity) | 16 hex | `yengo-content.db` column |
| `solution_fingerprint` | Moves-only solution tree serialization | Same-source variant detection | 16 hex | `yengo-content.db` column |
| `content_hash` | Full SGF text verbatim | Publish identity / filename / GN property | 16 hex | `yengo-content.db` PK, `yengo-search.db` PK |

**Isolation rule**: Each hash has exactly one job. They never substitute for each other.

## Position Hash

Determines whether two puzzles share the same board setup.

### Algorithm

```python
canonical_position_hash(board_size, black_stones, white_stones, first_player) -> str
```

```text
SHA256("SZ{board_size}:B[{sorted_ab}]:W[{sorted_aw}]:PL[{first_player}]")[:16]
```

### Inputs

| Input | Source | Default |
| ------- | -------- | --------- |
| `SZ[]` | Board size | `19` |
| `AB[]` | Black setup stones (sorted lexicographically) | — |
| `AW[]` | White setup stones (sorted lexicographically) | — |
| `PL[]` | Player to move | `B` |

### Not Included

- Solution tree moves (`B[]`, `W[]` after root)

- Comments (`C[]`)

- YenGo custom properties (`Y*`)

- Annotations, markup

### Properties

- **Deterministic**: Same stones always produce the same hash

- **Order-independent**: `AB[pd][qd]` and `AB[qd][pd]` produce the same hash

- **Player-sensitive**: `PL[B]` and `PL[W]` produce different hashes

### Location

`backend/puzzle_manager/core/content_db.py` → `canonical_position_hash()`

## Solution Fingerprint

Determines whether two puzzles with the same position have the same solution tree, ignoring comments, whitespace, and metadata noise.

### Algorithm

```python
compute_solution_fingerprint(solution_tree: SolutionNode) -> str
```

```text
SHA256(canonical_tree_serialization.encode('utf-8'))[:16]
```

### Serialization Rules (Version 1)

1. **Node token**: `{color}{move_sgf}{'!' if correct else '?'}` — e.g., `Bds!`, `Wcs?`

1. **Tree walk**: Depth-first, children sorted lexicographically by token before recursing

1. **Branching**: Multiple children → parenthesized groups, sorted. Single child → no parens

1. **Root skip**: Root `SolutionNode` has no move — serialization starts from its children

### What's Included

- Move color (`B` or `W`)

- Move SGF coordinate (e.g., `ds`, `cs`)

- Correctness flag (`!` for correct, `?` for wrong)

### What's Excluded

- Comments (`C[]`)

- YenGo properties (`Y*`)

- Annotations, markup

- Whitespace, formatting

### Worked Examples

**Linear puzzle** (all correct):

```text
SGF:    ;B[ds];W[cs];B[ar];W[ap];B[es];W[ao];B[dr]
Tokens: Bds!Wcs!Bar!Wap!Bes!Wao!Bdr!
Hash:   SHA256("Bds!Wcs!Bar!Wap!Bes!Wao!Bdr!")[:16]
```

**Branched puzzle** (root has correct `B[ds]` and wrong `B[ab]`):

```text
Sort:   "Bab?" < "Bds!" (lexicographic)
Result: (Bab?)(Bds!Wcs!Bar!)
Hash:   SHA256("(Bab?)(Bds!Wcs!Bar!)")[:16]
```

### Properties

- **Deterministic**: Same moves + correctness always produce the same hash

- **Comment-insensitive**: Different `C[]` values → same fingerprint

- **Branch-order-insensitive**: Children sorted before hashing

- **Correctness-sensitive**: Same move marked correct vs wrong → different fingerprint

### Fingerprint Versioning

| `fingerprint_version` | Algorithm |
| --- | --- |
| 1 | Moves + correctness, siblings sorted lexicographically |
| 2+ (future) | Could add ko-state, pass moves, nested depth, etc. |

**Version mismatch rule**: When comparing two rows with different `fingerprint_version`, treat as **non-match** (conservative — allows both through). A version bump never causes false-positive rejections.

### Location

`backend/puzzle_manager/core/content_db.py` → `compute_solution_fingerprint()`

## Content Hash

Determines the published identity of a puzzle — its filename and `GN` property.

### Algorithm

```python
generate_content_hash(sgf_content: str) -> str
```

```text
SHA256(full_sgf_content.encode('utf-8'))[:16]
```

Uses the **entire SGF text verbatim** — any change (including whitespace or comment edits) produces a different hash.

### Location

`backend/puzzle_manager/core/naming.py` → `generate_content_hash()`

### Usage

- Publish stage generates `GN[YENGO-{content_hash}]`

- Filename: `{content_hash}.sgf`

- Primary key in both `yengo-content.db` and `yengo-search.db`

## Decision Matrix

The dedup check runs during ingest. Only puzzles with a position-hash collision reach the fingerprint comparison.

| Position Hash | Source | Fingerprint | FP Version | Result | Event Type |
| --- | --- | --- | --- | --- | --- |
| NO MATCH | — | — | — | **Allow** | `no_collision` |
| MATCH | Different | — | — | **Allow** | `cross_source_allowed` |
| MATCH | Same | MATCH | Same | **Reject** | `true_duplicate` |
| MATCH | Same | DIFFER | Same | **Allow** | `variant_allowed` |
| MATCH | Same | ANY | Different | **Allow** | `variant_allowed` |

## Collision Event Logging

Every position collision is logged as a structured event with `action: dedup_collision` and an `event_type` field:

| Event Type | Meaning | Outcome |
| --- | --- | --- |
| `no_collision` | Unique position (not logged) | Allowed |
| `true_duplicate` | Same position + same source + same fingerprint | Rejected |
| `variant_allowed` | Same position + same source + different fingerprint | Allowed |
| `cross_source_allowed` | Same position + different source | Allowed |

### Filtering Pipeline Logs

```bash
# Find all collision events
grep "dedup_collision" .pm-runtime/logs/pipeline.log

# Filter by event type
grep "event_type.*variant_allowed" .pm-runtime/logs/pipeline.log
grep "event_type.*true_duplicate" .pm-runtime/logs/pipeline.log
```

## `yengo-content.db` Schema (Dedup-Related Columns)

```sql
CREATE TABLE sgf_files (
    content_hash          TEXT PRIMARY KEY,
    sgf_content           TEXT NOT NULL,
    position_hash         TEXT,
    solution_fingerprint  TEXT,
    fingerprint_version   INTEGER NOT NULL DEFAULT 1,
    ...
);

CREATE INDEX idx_sgf_position ON sgf_files(position_hash);
CREATE INDEX idx_sgf_pos_sol  ON sgf_files(position_hash, solution_fingerprint);
```

> **See also**:
>
> - [SQLite Index Architecture](sqlite-index-architecture.md) — Full database schemas and terminology
>
> - [Collection Editions](collection-editions.md) — Cross-source collision handling and edition splitting
>
> - [Architecture: Pipeline](../architecture/backend/pipeline.md) — 3-stage pipeline flow
