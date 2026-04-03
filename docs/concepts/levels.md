# Levels (9-Level Difficulty System)

> **See also**:
>
> - [Concepts: SGF Properties](./sgf-properties.md) — YG property format
> - [Concepts: Mastery](./mastery.md) — User progress tracking per level
> - [Reference: Levels Config](../../config/puzzle-levels.json) — Canonical definitions

**Last Updated**: 2026-02-10

**Single Source of Truth**: [`config/puzzle-levels.json`](../../config/puzzle-levels.json)

YenGo uses a 9-level difficulty system mapping to Go ranks.

---

## Level System

| Level | Slug                 | Display Name       | Rank Range | Description                   |
| ----- | -------------------- | ------------------ | ---------- | ----------------------------- |
| 1     | `novice`             | Novice             | 30k-26k    | First puzzles, basic captures |
| 2     | `beginner`           | Beginner           | 25k-21k    | Simple tactics                |
| 3     | `elementary`         | Elementary         | 20k-16k    | Common patterns               |
| 4     | `intermediate`       | Intermediate       | 15k-11k    | Multi-step sequences          |
| 5     | `upper-intermediate` | Upper Intermediate | 10k-6k     | Complex reading               |
| 6     | `advanced`           | Advanced           | 5k-1k      | Deep calculations             |
| 7     | `low-dan`            | Low Dan            | 1d-3d      | Professional patterns         |
| 8     | `high-dan`           | High Dan           | 4d-6d      | Master techniques             |
| 9     | `expert`             | Expert             | 7d-9d      | Professional level            |

---

## YG Property Format

The `YG` property stores level using slugs:

```sgf
YG[beginner]
YG[intermediate]
YG[low-dan]
```

### With Sublevel

For finer granularity:

```sgf
YG[intermediate:1]  # Lower intermediate
YG[intermediate:2]  # Mid intermediate
YG[intermediate:3]  # Upper intermediate
```

---

## Level Mapping Rules

### From Source Data

Adapters may provide level hints that the enricher validates:

```python
# Adapter provides level hint
puzzle.metadata["level_hint"] = "intermediate"

# Enricher validates against config
if level_hint in valid_slugs:
    puzzle.yg = level_hint
else:
    puzzle.yg = compute_level_from_complexity(puzzle)
```

### From Complexity Metrics

When no source level is available, the enricher computes level from:

1. **Solution depth** (YX.d) — longer = harder
2. **Reading count** (YX.r) — more variations = harder
3. **Stone count** (YX.s) — context for depth
4. **Uniqueness** (YX.u) — miai = slightly easier

### Rank-to-Level Mapping

```python
def rank_to_level(rank: str) -> str:
    """Map Go rank to YenGo level slug."""
    rank_num = parse_rank(rank)  # e.g., "15k" → 15, "3d" → -3

    if rank_num >= 26: return "novice"
    if rank_num >= 21: return "beginner"
    if rank_num >= 16: return "elementary"
    if rank_num >= 11: return "intermediate"
    if rank_num >= 6: return "upper-intermediate"
    if rank_num >= 1: return "advanced"
    if rank_num >= -3: return "low-dan"
    if rank_num >= -6: return "high-dan"
    return "expert"
```

---

## Configuration

### puzzle-levels.json

```json
{
  "version": "1.0",
  "levels": [
    {
      "id": 1,
      "slug": "novice",
      "name": "Novice",
      "rank_min": "30k",
      "rank_max": "26k"
    },
    {
      "id": 2,
      "slug": "beginner",
      "name": "Beginner",
      "rank_min": "25k",
      "rank_max": "21k"
    }
    // ... etc
  ]
}
```

### Key Fields

| Field      | Description           |
| ---------- | --------------------- |
| `id`       | Numeric level (1-9)   |
| `slug`     | URL-safe identifier   |
| `name`     | Display name          |
| `rank_min` | Lowest rank in range  |
| `rank_max` | Highest rank in range |

---

## Frontend Usage

### Filter by Level

```typescript
// Single level
const beginnerPuzzles = puzzles.filter((p) => p.level === "beginner");

// Range
const easyPuzzles = puzzles.filter((p) =>
  ["novice", "beginner", "elementary"].includes(p.level),
);
```

### Level Display

```typescript
const levelNames: Record<string, string> = {
  novice: "Novice (30k-26k)",
  beginner: "Beginner (25k-21k)",
  elementary: "Elementary (20k-16k)",
  intermediate: "Intermediate (15k-11k)",
  "upper-intermediate": "Upper Intermediate (10k-6k)",
  advanced: "Advanced (5k-1k)",
  "low-dan": "Low Dan (1d-3d)",
  "high-dan": "High Dan (4d-6d)",
  expert: "Expert (7d+)",
};
```

---

## Legacy Format

**Deprecated**: Numeric YG values

```sgf
# OLD (deprecated)
YG[4]

# NEW (v8)
YG[intermediate]
```

The pipeline automatically migrates old format during enrichment.

---

## Design Decisions

### Why Slugs Over Numbers?

1. **Readable**: `YG[beginner]` is self-documenting
2. **Stable**: Adding levels doesn't shift existing values
3. **Meaningful**: Ranks are subjective; slugs are consistent

### Why 9 Levels?

- Maps cleanly to 30k → 9d rank spectrum
- Enough granularity without overwhelming
- Matches traditional Go rank groupings

### Why Sublevels?

Optional `:1`, `:2`, `:3` suffixes allow finer granularity without changing the core system.

---

## System Stability (Frozen)

**Status: Frozen as of Schema v10 (Spec 126)**

The 9-level difficulty system is **permanently frozen**. The level slugs are stable identifiers that will not change. Any modifications to the level set would require a **major schema version bump** and a full data migration.

### What "Frozen" Means

- **Level slugs** are permanent identifiers used in SGF paths (`sgf/{level}/batch-{NNNN}/`), YG properties, view indexes, and frontend routing.
- **Display names** (`name`, `shortName`) may be updated for localization without a schema bump.
- **Rank ranges** may be refined if Go ranking conventions change, but slug identifiers remain stable.
- **No levels may be added, removed, or reordered** without a major schema version bump (e.g., v10 → v11).

### Why Frozen

1. **SGF metadata**: SGF files contain `YG[{slug}]` level property. Changing level slugs requires re-processing all published files.
2. **Database index integrity**: The SQLite search index (`yengo-search.db`) uses numeric level IDs (e.g., `120`). Adding/removing levels changes the query surface.
3. **Frontend routing**: Routes like `/contexts/training/{slug}` depend on stable slugs.
4. **User progress**: Player progress in `localStorage` references level slugs. Changing them would invalidate progress data.
5. **External references**: GitHub Pages URLs contain level slugs. Changing them would break external links.

### Changing the Level System

If a future spec requires modifying levels:

1. Create a new spec with explicit migration plan
2. Bump SGF schema to next major version
3. Write a migration script
4. Rebuild database indexes
5. Provide frontend migration for localStorage data
6. Document the change in CHANGELOG.md
