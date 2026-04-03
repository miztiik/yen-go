# Plan: Wire SnapshotBuilder into Publish Stage

**Last Updated**: 2026-03-05  
**Correction Level**: 3 (Multiple Files — publish.py + dead code removal)

---

## Architecture

No new components. Wire existing `SnapshotBuilder` (which delegates to `ShardWriter`) into the publish stage's post-SGF-output index phase, replacing legacy flat JSON view writing.

### Data Flow Change

**Before** (legacy — broken):

```
SGF props → {path, tags} dicts → flat JSON files per level/tag/collection
                                  views/by-level/{level}.json
                                  views/by-tag/{tag}.json
                                  views/by-collection/{slug}.json
```

**After** (snapshot-centric — correct):

```
SGF props → ShardEntry(p, l, t, c, x, q, ct) via IdMaps
         → SnapshotBuilder.load_existing_entries() + merge
         → SnapshotBuilder.build_snapshot()
         → snapshots/{id}/manifest.json
         → snapshots/{id}/views/shards/{key}/meta.json + page-NNN.json
         → active-snapshot.json
```

### Pattern Reference

Follow `rollback.py` exactly:

```python
builder = SnapshotBuilder(collections_dir=output_root)
existing = builder.load_existing_entries()
# merge existing + new, dedup by p
merged = _merge_entries(existing, new_entries)
if merged:
    builder.build_snapshot(merged)
```

## Design Decisions

### D1: Inventory Strategy — Slug-Based Counters

`InventoryUpdate` requires `level_increments: dict[str, int]` and `tag_increments: dict[str, int]` using **slug keys** (e.g., `"elementary"`, `"ladder"`). The ShardEntry model uses numeric IDs.

**Decision**: Keep separate slug-based counters in the SGF processing loop. This adds ~5 lines of code but cleanly decouples inventory tracking from the shard data model. No changes to `_update_inventory()` or `InventoryUpdate` model needed.

```python
# In the SGF loop, alongside ShardEntry construction:
level_slug_counts[level_name] = level_slug_counts.get(level_name, 0) + 1
for tag in game.yengo_props.tags:
    tag_slug_counts[tag] = tag_slug_counts.get(tag, 0) + 1
```

### D2: IdMaps Initialization

`IdMaps.load()` defaults to `get_global_config_dir()` → `config/` directory. In production and tests (run from repo root), this works. No `config_dir` override needed.

### D3: Merge Strategy

Dedup existing + new entries by `p` field (compact path). New entries override existing (same content_hash = same puzzle).

```python
def _merge_entries(existing: list[ShardEntry], new: list[ShardEntry]) -> list[ShardEntry]:
    by_path = {e.p: e for e in existing}
    for entry in new:
        by_path[entry.p] = entry
    return list(by_path.values())
```

### D4: Dry-Run Handling

Skip `build_snapshot()` call on dry-run (matches existing dry-run behavior for file writes).

### D5: Empty Batch Handling

If no puzzles were processed AND no existing snapshot entries exist, skip snapshot build entirely (matches `test_empty_batch_no_snapshot` expectation).

## Risks & Mitigations

| Risk                                  | Probability | Impact           | Mitigation                                                |
| ------------------------------------- | ----------- | ---------------- | --------------------------------------------------------- |
| IdMaps.load() fails in isolated CI    | Low         | Tests fail       | IdMaps.load() accepts config_dir param; document in tasks |
| Full rebuild slow at scale (>5K)      | Low         | Slower publishes | Accepted — correctness > speed; monitor at scale          |
| Existing tests have setup assumptions | Medium      | Test failures    | Review test fixtures after wiring                         |

## What Changes

### File: `backend/puzzle_manager/stages/publish.py`

1. **Add imports**: `SnapshotBuilder`, `ShardEntry`, `IdMaps`, `parse_yx`
2. **Add IdMaps initialization** at stage start
3. **Replace per-puzzle dict tracking** with ShardEntry construction:
   - Remove `puzzles_by_level`, `puzzles_by_tag`, `puzzles_by_collection` dicts
   - Remove `level_entry`, `tag_entry`, `collection_entry` dict construction
   - Add `new_entries: list[ShardEntry]` collection
   - Add slug-based counters for inventory: `level_slug_counts`, `tag_slug_counts`
4. **Replace `_update_indexes()` call** with SnapshotBuilder workflow
5. **Remove dead methods**: `_update_indexes()`, `_update_indexes_flat()`, `_update_collection_indexes()`
6. **Adapt `_update_inventory()` call** to use slug-based counters

### Files NOT Changed

- `core/snapshot_builder.py` — already correct
- `core/shard_writer.py` — already correct
- `core/shard_models.py` — already correct
- `core/id_maps.py` — already correct
- `stages/protocol.py` — snapshot-aware properties already exist
- `rollback.py` — already uses SnapshotBuilder
- Frontend — already snapshot-only

> **See also**:
>
> - [Charter](./00-charter.md) — Goals, non-goals, acceptance criteria
> - [Tasks](./40-tasks.md) — Dependency-ordered execution checklist
> - [Analysis](./20-analysis.md) — Consistency and coverage assessment
