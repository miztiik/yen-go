# Execution Log — Publish Stage Cleanup

> Last Updated: 2026-03-06

## Intake Validation

- [x] Plan approval: GOV-PLAN-APPROVED (unanimous 6/6)
- [x] Task graph verified: T01+T02 parallel → T03 → T04 → T05 → T06+T07 → T08+T09
- [x] No unresolved CRITICAL analysis findings
- [x] Backward compatibility: explicitly not required (user confirmed)
- [x] Governance handover consumed: blocking_items = none

## Files Modified

| File                                           | Lines Changed | Tasks                        |
| ---------------------------------------------- | ------------- | ---------------------------- |
| `models/publish_log.py`                        | -10           | T01                          |
| `stages/publish.py`                            | +100/-106     | T02, T03, T04, T05, T06, T07 |
| `tests/integration/test_publish_robustness.py` | +15/-12       | T08                          |
| `tests/unit/test_publish_stage_cleanup.py`     | +106 (new)    | T09                          |

## Task Execution

### T01: Remove dead fields from PublishLogEntry ✅

5 replacements in `models/publish_log.py`:

1. Removed `source_file: str = ""` field
2. Removed `original_filename: str = ""` field
3. Removed `"source_file"` key from `to_jsonl()` dict
4. Removed `.get("source_file", "")` from `from_jsonl()`
5. Updated docstring to remove references

### T02: Replace trace registry with YM-based extraction ✅

10 replacements in `stages/publish.py`:

1. Removed module docstring reference to trace_id by source_file
2. Added `parse_pipeline_meta` import from `core.trace_utils`
3. Removed `TraceEntry, TraceStatus` imports
4. Removed `TraceRegistryReader, TraceRegistryWriter` imports
5. Removed trace registry initialization block
6. Moved trace*id extraction inside try: `trace_id, *, _, _ = parse_pipeline_meta(game.yengo_props.pipeline_meta)`
7. Removed `source_file` variable assignment
8. Removed PUBLISHED trace status update
9. Removed FAILED trace status update
10. Fixed `source_file` → `sgf_path.stem` in log extra

### T03: Strip `f` from YM at publish time ✅

3 changes in `stages/publish.py`:

1. Added `_strip_ym_filename(game)` module-level helper (JSON parse → del f → re-serialize)
2. Call after `parse_pipeline_meta()` and before `SGFBuilder.from_game(game).build()`
3. Fixed dangling `source_file` reference in validation warning → `sgf_path.stem`

### T04: Decouple snapshot from periodic flush ✅

- Renamed `_flush_incremental()` → `_flush_periodic()`
- Removed snapshot build code from periodic flush method
- `_flush_periodic()` now only: (1) write pending log entries, (2) save batch state
- Updated both call sites: periodic@100 and final

### T05: Add `_build_final_snapshot()` method ✅

- Added `_build_final_snapshot()` method: loads existing entries, merges new, builds snapshot once
- Called once after final `_flush_periodic()`, guarded by `if new_entries and not context.dry_run`

### T06: Wire audit entry at publish completion ✅

- Added `from backend.puzzle_manager.audit import write_audit_entry` import
- Wired `write_audit_entry()` call after `_update_inventory()` with: operation="publish", target="puzzles-collection", details={files_published, files_failed, files_skipped, source, run_id}

### T07: Remove unused imports ✅

- Removed `from typing import Optional` (no longer needed after trace registry removal)

### T08: Update existing tests ✅

**Grep verification:** No test files reference `source_file=` or `original_filename=` as kwargs to `PublishLogEntry()`.

**Integration test updates in `test_publish_robustness.py`:**

1. `test_incremental_snapshot_every_100_files` → renamed to `test_snapshot_built_once_at_end`, asserts `build_snapshot.call_count == 1`
2. `test_crash_at_150_preserves_first_100` → renamed to `test_crash_at_150_preserves_first_100_log`, asserts snapshot does NOT exist after crash
3. Updated `TestIncrementalFlush` class docstring to reflect new behavior

### T09: New unit tests ✅

Created `tests/unit/test_publish_stage_cleanup.py` with 11 tests:

**`TestStripYmFilename` (7 tests):**

- strips f key from YM
- no-op when f not present
- no-op for malformed JSON
- no-op for None value
- no-op for empty string
- preserves other keys
- uses compact JSON separators

**`TestPublishLogEntryWithoutDeadFields` (4 tests):**

- no source_file attribute
- no original_filename attribute
- serialization excludes dead fields
- deserialization ignores legacy fields

## Deviations

1. **T07 scope:** Plan mentioned removing `source_file=""` and `original_filename=""` from PublishLogEntry constructor. Grep confirmed these kwargs were already absent — no constructor calls passed them.
2. **T08 scope:** Plan mentioned updating `test_publish_log.py` and removing trace registry mocking. Grep confirmed no test files use the removed fields. Only `test_publish_robustness.py` needed updates (2 tests testing old periodic snapshot behavior).
3. **Pre-existing failures:** 2 test failures exist on HEAD before our changes:
   - `test_inventory_publish::test_failed_write_preserves_original` — `_save_unlocked` API removed (documented in 2 prior initiatives)
   - `test_publish_robustness::test_publish_result_includes_remaining` — `remaining` calculation already absent from publish.py
