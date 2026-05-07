# Tasks: Wire SnapshotBuilder into Publish Stage

**Last Updated**: 2026-03-05

---

## Task List

All tasks target `backend/puzzle_manager/stages/publish.py` unless noted.

### T1 [P] — Add snapshot imports

- Add: `from backend.puzzle_manager.core.snapshot_builder import SnapshotBuilder`
- Add: `from backend.puzzle_manager.core.shard_models import ShardEntry`
- Add: `from backend.puzzle_manager.core.id_maps import IdMaps, parse_yx`
- File: `publish.py` (imports section, lines 1-40)

### T2 [P] — Initialize IdMaps at stage start

- In `run()`, initialize `id_maps = IdMaps.load()` before the SGF loop
- Place after existing initializations (validator, log_writer, etc.)
- File: `publish.py` (around line 130)

### T3 — Replace per-puzzle tracking with ShardEntry construction

**Depends on**: T1, T2

In the SGF processing loop:

- [ ] Remove `puzzles_by_level`, `puzzles_by_tag`, `puzzles_by_collection` dict accumulation
- [ ] Remove `level_entry`, `tag_entry`, `collection_entry` dict construction
- [ ] Remove `collection_sequence` counter
- [ ] Add `new_entries: list[ShardEntry] = []` before the loop
- [ ] Add slug-based counters: `level_slug_counts: dict[str, int] = {}`, `tag_slug_counts: dict[str, int] = {}`
- [ ] Per published puzzle, construct `ShardEntry`:

  ```python
  level_id = id_maps.level_slug_to_id(level_name)  # numeric ID
  tag_ids = sorted([id_maps.tag_slug_to_id(t) for t in game.yengo_props.tags if id_maps.tag_slug_to_id_safe(t) is not None])
  collection_ids = sorted([id_maps.collection_slug_to_id(c) for c in game.yengo_props.collections if id_maps.collection_slug_to_id_safe(c) is not None])
  complexity = parse_yx(game.yengo_props.complexity)

  entry = ShardEntry(
      p=f"{batch_num:04d}/{content_hash}",
      l=level_id,
      t=tag_ids,
      c=collection_ids,
      x=complexity,
      q=quality_level,
  )
  new_entries.append(entry)
  ```

- [ ] Also maintain slug counters for inventory:
  ```python
  level_slug_counts[level_name] = level_slug_counts.get(level_name, 0) + 1
  for tag in game.yengo_props.tags:
      tag_slug_counts[tag] = tag_slug_counts.get(tag, 0) + 1
  ```
- File: `publish.py` (lines 115-300 — the SGF loop and tracking)

### T4 — Replace \_update_indexes() with SnapshotBuilder workflow

**Depends on**: T3

Replace the `self._update_indexes(...)` call with:

- [ ] Instantiate `builder = SnapshotBuilder(collections_dir=output_root, id_maps=id_maps)`
- [ ] Load existing: `existing = builder.load_existing_entries()`
- [ ] Merge: dedup by `p` field (new overrides existing)
- [ ] Build snapshot (only if merged entries exist, skip on dry_run):
  ```python
  if merged_entries and not context.dry_run:
      builder.build_snapshot(merged_entries)
  elif merged_entries and context.dry_run:
      logger.info(f"[DRY-RUN] Would build snapshot with {len(merged_entries)} entries")
  ```
- File: `publish.py` (around line 344)

### T5 — Remove dead code

**Depends on**: T4

Delete these methods from `PublishStage`:

- [ ] `_update_indexes()`
- [ ] `_update_indexes_flat()`
- [ ] `_update_collection_indexes()`
- File: `publish.py` (lines ~415-560)

### T6 [P with T4] — Adapt \_update_inventory() call

- [ ] Change `_update_inventory()` call to pass slug-based counters instead of `puzzles_by_level`/`puzzles_by_tag` dicts
- [ ] Update signature: `level_slug_counts: dict[str, int]` replaces `puzzles_by_level: dict[str, list[dict]]`
- [ ] Update body: `level_increments = level_slug_counts` (already int-valued)
- [ ] Similarly for tags: `tag_increments = tag_slug_counts`
- File: `publish.py` (`_update_inventory()` method, lines ~556-620)

### T7 — Verify snapshot wiring tests pass

**Depends on**: T5, T6

- [ ] Run: `pytest backend/puzzle_manager/tests/integration/test_publish_snapshot_wiring.py -v`
- [ ] All 5 tests must pass:
  - `test_first_publish_creates_snapshot`
  - `test_old_views_not_produced`
  - `test_empty_batch_no_snapshot`
  - `test_incremental_publish`
  - `test_shard_pages_array_format`

### T8 — Full regression check

**Depends on**: T7

- [ ] Run: `pytest -m "not (cli or slow)" --tb=short`
- [ ] Zero failures

---

## Notes

- **IdMaps test dependency**: Integration tests rely on `config/` directory being accessible from the repo root. `IdMaps.load()` defaults to `get_global_config_dir()`. If isolated CI environments are used, pass `config_dir` explicitly.
- **Parallel markers**: T1+T2 are parallel. T6 can run parallel with T4. T7+T8 are post-implementation validation.
- **Inventory decoupling**: Slug-based counters are intentionally separate from ShardEntry construction to avoid coupling inventory to numeric IDs.

> **See also**:
>
> - [Plan](./30-plan.md) — Architecture decisions and design rationale
> - [Charter](./00-charter.md) — Acceptance criteria
> - [Governance](./70-governance-decisions.md) — Approval conditions
