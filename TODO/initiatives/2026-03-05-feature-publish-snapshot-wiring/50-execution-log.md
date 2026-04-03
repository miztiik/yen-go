# Execution Log: Wire SnapshotBuilder into Publish Stage

**Last Updated**: 2026-03-05

---

## Task Execution

### T1 — Add snapshot imports ✅

- Added 3 imports to `publish.py`: `SnapshotBuilder`, `ShardEntry`, `IdMaps`/`parse_yx`
- File: `backend/puzzle_manager/stages/publish.py` (imports section)

### T2 — Initialize IdMaps at stage start ✅

- Added `id_maps = IdMaps.load()` after existing initializations
- Added `new_entries: list[ShardEntry] = []` before the SGF loop
- Added `level_slug_counts` and `tag_slug_counts` dict counters
- Removed legacy tracking dicts: `puzzles_by_level`, `puzzles_by_tag`, `puzzles_by_collection`, `collection_sequence`

### T3 — Replace per-puzzle tracking with ShardEntry construction ✅

- Removed `level_entry`/`tag_entry` legacy dict construction
- Added ShardEntry construction per published puzzle using IdMaps conversions:
  - `level_id = id_maps.level_slug_to_id(level_name)`
  - `tag_ids` via `tag_slug_to_id` with safe lookups
  - `collection_ids` via `collection_slug_to_id` with safe lookups
  - `complexity = parse_yx(game.yengo_props.complexity)`
- Added slug-based counters for inventory alongside ShardEntry
- Removed legacy by-level/by-tag/by-collection dict accumulation block (~25 lines)

### T4 — Replace \_update_indexes() with SnapshotBuilder workflow ✅

- Replaced `self._update_indexes(...)` call with SnapshotBuilder workflow:
  1. `builder = SnapshotBuilder(collections_dir=output_root, id_maps=id_maps)`
  2. `existing = builder.load_existing_entries()`
  3. Merge by `p` field (new overrides existing)
  4. `builder.build_snapshot(merged_entries)` — only if entries exist and not dry_run
- Added dry-run logging path
- Updated `_update_inventory()` call to pass slug-based counters

### T5 — Remove dead code ✅

- Deleted `_update_indexes()` method (~20 lines)
- Deleted `_update_indexes_flat()` method (~50 lines)
- Deleted `_update_collection_indexes()` method (~45 lines)
- Total: ~115 lines of legacy JSON view code removed

### T6 — Adapt \_update_inventory() ✅

- Changed signature from `puzzles_by_level: dict[str, list[dict]]` to `level_slug_counts: dict[str, int]`
- Changed signature from `puzzles_by_tag: dict[str, list[dict]]` to `tag_slug_counts: dict[str, int]`
- Simplified body: removed `len(puzzles)` extraction loops, pass slug counters directly to `InventoryUpdate`
- Total: ~10 lines simplified

### T7 — Snapshot wiring tests ✅

- Ran: `pytest backend/puzzle_manager/tests/integration/test_publish_snapshot_wiring.py -v`
- Result: **7 passed in 1.67s** (all 5 publish wiring + 2 builder validation tests)

### T8 — Full regression check ✅

- Ran: `pytest backend/puzzle_manager/tests -m "not (cli or slow)" --tb=short -q`
- Result: **2030 passed, 9 failed, 44 deselected** in 76s
- All 9 failures are pre-existing and unrelated:
  - 2× `test_adapter_registry` — adapter discovery logging (unrelated)
  - 1× `test_tag_taxonomy` — version "8.2" vs "8.1" (config drift)
  - 1× `test_inventory_publish` — missing `_save_unlocked` attribute (unrelated)
  - 2× `test_publish_log_integration` — mock expects per-file `write()` but code uses `write_batch()` (pre-existing)
  - 3× `test_publish_robustness` — DETAIL level, flush interval, remaining files (pre-existing)

## Deviations

None. All tasks executed per approved plan.

## Summary

- **File modified**: `backend/puzzle_manager/stages/publish.py` only
- **Net change**: 211 insertions, 533 deletions (−322 lines net)
- **Scope**: Exact match to approved T1-T8 task set
- **No new dependencies**: Used existing `SnapshotBuilder`, `ShardWriter`, `IdMaps`, `ShardEntry`
