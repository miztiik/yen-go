# Level System Stability

*Last Updated: 2026-02-10*

## Status: Frozen

The 9-level difficulty system is **permanently frozen** as of schema v10 (Spec 126). The level slugs below are stable identifiers that will not change. Any modifications to the level set would require a **major schema version bump** and a full data migration.

## The 9 Permanent Level Slugs

| ID | Slug | Name | Rank Range |
|----|------|------|------------|
| 1 | `novice` | Novice | 30k–26k |
| 2 | `beginner` | Beginner | 25k–21k |
| 3 | `elementary` | Elementary | 20k–16k |
| 4 | `intermediate` | Intermediate | 15k–11k |
| 5 | `upper-intermediate` | Upper Intermediate | 10k–6k |
| 6 | `advanced` | Advanced | 5k–1k |
| 7 | `low-dan` | Low Dan | 1d–3d |
| 8 | `high-dan` | High Dan | 4d–6d |
| 9 | `expert` | Expert | 7d–9d |

## Source of Truth

`config/puzzle-levels.json` is the single source of truth for level definitions. The `"frozen": true` flag in that file signals that the level set is finalized.

## What "Frozen" Means

- **Level slugs** are permanent identifiers used in SGF paths (`sgf/{level}/batch-{NNNN}/`), YG properties, view indexes, and frontend routing.
- **Display names** (`name`, `shortName`) may be updated for localization without a schema bump.
- **Rank ranges** may be refined if Go ranking conventions change, but slug identifiers remain stable.
- **No levels may be added, removed, or reordered** without a major schema version bump (e.g., v10 → v11).

## Why Frozen

1. **Path stability**: SGF files are stored at `sgf/{level}/batch-{NNNN}/`. Changing level slugs would require migrating all published files.
2. **View index integrity**: `views/by-level/{level}.json` indexes use level slugs as filenames.
3. **Frontend routing**: Routes like `/collections/level-{slug}` depend on stable slugs.
4. **User progress**: Player progress in `localStorage` references level slugs. Changing them would invalidate progress data.
5. **External references**: GitHub Pages URLs contain level slugs. Changing them would break external links.

## Changing the Level System

If a future spec requires modifying levels:

1. Create a new spec with explicit migration plan
2. Bump SGF schema to next major version
3. Write a migration script (like `migrate_sharding.py`)
4. Update all view indexes
5. Provide frontend migration for localStorage data
6. Document the change in CHANGELOG.md

> **See also**:
> - [config/puzzle-levels.json](../../config/puzzle-levels.json) — Source of truth
> - [Architecture: Pipeline](../architecture/backend/pipeline.md) — How levels flow through the pipeline
> - [Concepts: Tags](./tags.md) — Tag taxonomy (also stable, but not frozen)
