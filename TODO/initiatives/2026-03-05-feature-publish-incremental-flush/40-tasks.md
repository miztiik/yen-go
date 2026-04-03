# Tasks — Publish Stage Incremental Flush & Logging

> Last Updated: 2026-03-05  
> Selected Option: **A — Inline Periodic Flush in Publish Loop**

## Task Graph

All tasks target exactly 2 files. Tasks are dependency-ordered. `[P]` marks tasks that can be executed in parallel with previously completed tasks.

---

### T1: Fix per-file logging level in publish.py

**File**: `backend/puzzle_manager/stages/publish.py`  
**Depends on**: none

Changes:

1. Add `from backend.puzzle_manager.pm_logging import DETAIL` import
2. Change `trace_logger.info("Published puzzle", ...)` (L311-320) to `logger.log(DETAIL, "Published puzzle", ...)` — per-file messages go to stage log file only, not console
3. Change `logger.info(f"Skipping already-published SGF ...")` (L214) to `logger.log(DETAIL, f"Skipping duplicate SGF ...")` — matches test_duplicate_skip_is_detail_level expectation
4. Note: The per-file `trace_logger.info(...)` currently uses the trace-aware logger. After this change, use `trace_logger.log(DETAIL, ...)` to preserve trace context (trace_id in log records) while lowering the level.

**Verification**: `test_per_file_log_is_detail_level` and `test_duplicate_skip_is_detail_level` should pass.

---

### T2: Add streaming progress logging to publish loop [P]

**File**: `backend/puzzle_manager/stages/publish.py`  
**Depends on**: none (parallel with T1)

Changes:

1. After the `except` block in the per-file loop, add streaming progress (matching ingest/analyze):
   ```python
   # Streaming progress (after try/except, inside the for loop)
   total = processed + failed + skipped
   logger.debug(
       "Progress: %d processed, %d failed, %d skipped (%d/%d)",
       processed, failed, skipped, total, batch_size,
   )
   if total > 0 and total % 100 == 0:
       logger.info(
           "[publish] %d/%d — %d ok, %d failed, %d skipped",
           total, batch_size, processed, failed, skipped,
       )
   ```
2. The `total > 0` guard prevents logging at iteration 0.

**Verification**: Manual review — no existing test for this specific pattern.

---

### T3: Refactor in-memory accumulators to pending buffers

**File**: `backend/puzzle_manager/stages/publish.py`  
**Depends on**: none (parallel with T1, T2)

Changes:

1. Rename/add pending buffers alongside the existing full accumulators:
   - `pending_entries: list[ShardEntry] = []` — entries awaiting snapshot flush
   - `pending_log_entries: list[PublishLogEntry] = []` — log entries awaiting flush
   - Keep `new_entries` as the full accumulator for the final inventory/stats (already exists)
2. In the per-file success path, append to both `new_entries` and `pending_entries` (for snapshot) and both `publish_log_entries` and `pending_log_entries` (for log)

Wait — simpler approach: just use `pending_entries` and `pending_log_entries` as the accumulators, and track `all_new_entries` separately (or rebuild from snapshots). Actually, the simplest approach:

- Keep `new_entries` for full-run tracking (inventory stats at end)
- Use `pending_log_entries` instead of `publish_log_entries` — flush and clear at boundaries
- For snapshot: at each flush, load existing + merge all `new_entries` so far

Revised approach:

1. `publish_log_entries` becomes the pending buffer — flush at boundaries and clear
2. `new_entries` remains the full-run list (needed for inventory stats)
3. Snapshot build at each 100-file boundary uses all `new_entries` accumulated so far

**Verification**: Existing tests still pass.

---

### T4: Add periodic flush block at 100-file boundary

**File**: `backend/puzzle_manager/stages/publish.py`  
**Depends on**: T2, T3

This is the core change. Inside the `for sgf_path in sgf_files` loop, after the streaming progress block from T2:

```python
if total > 0 and total % 100 == 0 and not context.dry_run:
    # Periodic flush: snapshot + publish log + batch state
    if pending_log_entries:
        log_writer.write_batch(pending_log_entries)
        logger.info(f"Flushed {len(pending_log_entries)} publish log entries")
        pending_log_entries.clear()

    if new_entries:
        builder = SnapshotBuilder(collections_dir=output_root, id_maps=id_maps)
        existing = builder.load_existing_entries()
        existing_by_p = {e.p: e for e in existing}
        for e in new_entries:
            existing_by_p[e.p] = e
        merged_entries = list(existing_by_p.values())
        builder.build_snapshot(merged_entries)
        logger.info(
            f"Incremental snapshot: {len(new_entries)} new + {len(existing)} existing "
            f"= {len(merged_entries)} total"
        )

    if "global" in batch_states:
        batch_states["global"].save(sgf_root)
```

**Verification**: New test `test_incremental_snapshot_every_100` (see T7).

---

### T5: Replace post-loop all-at-once snapshot/log with remainder flush

**File**: `backend/puzzle_manager/stages/publish.py`  
**Depends on**: T4

Changes:

1. Remove the post-loop snapshot block (L342-356) — replaced by periodic flush
2. Remove the post-loop publish log block (L358-362) — replaced by periodic flush
3. Add a **remainder flush** after the loop for any entries since the last 100-boundary:

   ```python
   # Flush remaining entries (less than 100 since last boundary)
   if not context.dry_run:
       if pending_log_entries:
           log_writer.write_batch(pending_log_entries)
           logger.info(f"Flushed {len(pending_log_entries)} remaining publish log entries")

       if new_entries:
           builder = SnapshotBuilder(collections_dir=output_root, id_maps=id_maps)
           existing = builder.load_existing_entries()
           existing_by_p = {e.p: e for e in existing}
           for e in new_entries:
               existing_by_p[e.p] = e
           merged_entries = list(existing_by_p.values())
           builder.build_snapshot(merged_entries)
           logger.info(
               f"Final snapshot: {len(new_entries)} new + {len(existing)} existing "
               f"= {len(merged_entries)} total"
           )

       if "global" in batch_states:
           batch_states["global"].save(sgf_root)
   ```

4. Note: The periodic flush (T4) and remainder flush share the same logic. Consider extracting a `_flush_incremental()` helper to avoid duplication (DRY).

**Verification**: Existing tests still pass (publish log entries still written, snapshot still built).

---

### T6: Extract \_flush_incremental helper to DRY periodic + remainder flush [P]

**File**: `backend/puzzle_manager/stages/publish.py`  
**Depends on**: T4, T5

Extract shared flush logic into a local helper or private method:

```python
def _flush_incremental(
    new_entries, pending_log_entries, batch_states,
    output_root, sgf_root, id_maps, log_writer, context, label
):
    """Flush pending publish log, build incremental snapshot, save batch state."""
    if pending_log_entries:
        log_writer.write_batch(pending_log_entries)
        logger.info(f"Flushed {len(pending_log_entries)} publish log entries ({label})")
        pending_log_entries.clear()

    if new_entries:
        builder = SnapshotBuilder(collections_dir=output_root, id_maps=id_maps)
        existing = builder.load_existing_entries()
        existing_by_p = {e.p: e for e in existing}
        for e in new_entries:
            existing_by_p[e.p] = e
        merged = list(existing_by_p.values())
        builder.build_snapshot(merged)
        logger.info(
            f"Snapshot ({label}): {len(new_entries)} new + {len(existing)} existing "
            f"= {len(merged)} total"
        )

    if "global" in batch_states:
        batch_states["global"].save(sgf_root)
```

Both periodic flush (T4) and remainder flush (T5) call this helper.

**Verification**: Code review — no behavioral change.

---

### T7: Update test_publish_robustness.py — existing test fixes

**File**: `backend/puzzle_manager/tests/integration/test_publish_robustness.py`  
**Depends on**: T1, T5

Changes:

1. **`test_batch_state_flushed_at_interval`** (L227): Update to expect flush at 100-file boundaries (or test with <100 files where flush happens at end). Currently expects flush every 2 files with `flush_interval=2`. Update to verify flush at end-of-loop (since <100 files).
2. **`test_publish_log_entries_written_per_file`** (L93): This test name is misleading — entries are now flushed every 100 (or at end for <100 files). The test creates 3 files, so all entries flush at end. Test should still pass as-is — verify.
3. **`test_crash_mid_loop_preserves_logged_entries`** (L125): With 3 files, crash on 3rd, the 2 successful entries are flushed at end of loop. But if crash prevents reaching end-of-loop code... This test patches `SGFBuilder.from_game` to raise (caught by the `except` block in the loop), so the loop continues and the post-loop flush executes normally. Test should still pass.

**Verification**: `pytest backend/puzzle_manager/tests/integration/test_publish_robustness.py`

---

### T8: Add new tests for incremental flush behavior [P]

**File**: `backend/puzzle_manager/tests/integration/test_publish_robustness.py`  
**Depends on**: T4, T5

New test methods:

0. **Extend `_create_valid_sgf` helper**: The current helper generates only 12 unique board positions (`4 rows × 3 col-groups`). Since the publish stage normalizes content via `SGFBuilder.from_game(game).build()`, board position governs the content hash. 250+ files require 250+ unique hashes. Fix: add a unique comment (e.g., `C[unique:{idx}]`) or expand the position grid to ensure distinct normalized content per file.

1. **`test_incremental_snapshot_every_100_files`**: Create 250 files. After publish, verify that `SnapshotBuilder.build_snapshot()` was called at least 3 times (at 100, 200, and end). Use `unittest.mock.patch` to count calls.

2. **`test_publish_log_flushed_every_100_files`**: Create 250 files. Verify `log_writer.write_batch()` called at least 3 times with appropriate entry counts.

3. **`test_batch_state_saved_every_100_files`**: Create 250 files. Verify `BatchState.save()` called at least 3 times.

4. **`test_crash_at_150_preserves_first_100_snapshot`**: Create 200 files. Patch to crash at file 150. Verify snapshot exists with entries from first 100 files (the 100-boundary flush executed). Verify publish log has entries from first 100 files.

**Verification**: All new tests pass.

---

### T9: Remove dead `flush_interval` wiring expectations

**File**: `backend/puzzle_manager/tests/integration/test_publish_robustness.py`  
**Depends on**: T7

Changes:

1. Update or remove `test_batch_state_flushed_at_interval` — the `flush_interval` parameter is no longer the mechanism for periodic saves in publish. Replace with a test that verifies batch state is saved at 100-file boundaries.
2. Add a code comment in `publish.py` documenting that `flush_interval` config is not used by publish stage (periodic operations use the 100-file cadence matching ingest/analyze).

**Verification**: No test references `flush_interval` as the save trigger for publish.

---

### T10: Run full test suite validation

**File**: both files  
**Depends on**: T1-T9

Run: `pytest -m "not (cli or slow)"` and verify all tests pass.

**Verification**: Zero failures.

---

## Dependency Graph

```
T1 (fix log levels) ─────────────────┐
T2 (streaming progress) ─────────────├── T4 (periodic flush) → T5 (remainder flush) → T6 (DRY helper)
T3 (pending buffers) ────────────────┘                                    │
                                                                          ├── T7 (fix existing tests)
                                                                          ├── T8 (new tests) [P with T7]
                                                                          └── T9 (remove dead flush_interval)
                                                                                      │
                                                                                      └── T10 (full validation)
```

## Parallel Execution Markers

- **Parallel batch 1**: T1, T2, T3 (all independent changes in publish.py)
- **Parallel batch 2**: T7, T8 (both test file changes, independent of each other)
- **Sequential**: T4 depends on T2+T3; T5 depends on T4; T6 depends on T4+T5; T9 follows T7; T10 is final
