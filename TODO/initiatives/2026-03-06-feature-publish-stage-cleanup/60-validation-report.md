# Validation Report — Publish Stage Cleanup

> Last Updated: 2026-03-06

## Test Results

### New Unit Tests (T09)

```
$ python -m pytest tests/unit/test_publish_stage_cleanup.py -v
11 passed in 0.72s
```

### Updated Integration Tests (T08)

```
$ python -m pytest tests/integration/test_publish_robustness.py::TestIncrementalFlush -v
4 passed in 25.14s
```

### Full Test Suite

```
$ python -m pytest tests -m "not (cli or slow)" --tb=line -q
2 failed, 2051 passed, 44 deselected, 1 warning in 131.12s
```

**2 failures are PRE-EXISTING** (not caused by this initiative):

| Test                                                              | Error                    | Root Cause                                | Our Change? |
| ----------------------------------------------------------------- | ------------------------ | ----------------------------------------- | ----------- |
| `test_inventory_publish::test_failed_write_preserves_original`    | Missing `_save_unlocked` | InventoryManager refactor                 | No          |
| `test_publish_robustness::test_publish_result_includes_remaining` | `remaining` always 0     | `remaining` calculation missing from HEAD | No          |

Both documented in prior initiatives: `2026-03-05-feature-publish-snapshot-wiring` and `2026-03-05-feature-publish-incremental-flush`.

### Import Validation

```
$ python -c "from backend.puzzle_manager.models.publish_log import PublishLogEntry; from backend.puzzle_manager.stages.publish import PublishStage; print('OK')"
Imports OK
```

### Lint Check

```
$ ruff check stages/publish.py models/publish_log.py tests/unit/test_publish_stage_cleanup.py --select E,F
```

- 0 errors introduced by this initiative
- Pre-existing lint warnings in `stages/publish.py` (F401: unused datetime/validate_before_publish imports, E501 line length) — not in scope

## Must-Hold Constraint Verification

| #   | Constraint                                     | Status | Evidence                                                                                                                      |
| --- | ---------------------------------------------- | ------ | ----------------------------------------------------------------------------------------------------------------------------- |
| 1   | Periodic flush: ONLY publish log + batch state | ✅     | `_flush_periodic()` has no SnapshotBuilder calls. `test_snapshot_built_once_at_end` confirms `build_snapshot.call_count == 1` |
| 2   | Snapshot built exactly ONCE after loop         | ✅     | `_build_final_snapshot()` called once after loop. Unit test confirms call_count == 1                                          |
| 3   | trace_id from YM via `parse_pipeline_meta()`   | ✅     | `trace_id, _, _, _ = parse_pipeline_meta(game.yengo_props.pipeline_meta)` in try block. No trace registry references remain   |
| 4   | `source_file`/`original_filename` removed      | ✅     | Fields deleted from dataclass, to_jsonl, from_jsonl. Unit tests confirm `hasattr()` returns False                             |
| 5   | `f` stripped from YM before publish            | ✅     | `_strip_ym_filename(game)` called after parse, before build. 7 unit tests cover edge cases                                    |
| 6   | `write_audit_entry` called after publish       | ✅     | Import + call wired after `_update_inventory()`. audit_file path: `output_root / ".puzzle-inventory-state" / "audit.jsonl"`   |

## Consistency Analysis

Performed read-only pass across all modified files:

1. **No dangling references to removed code:**
   - `TraceRegistryReader/Writer` — 0 references in publish.py
   - `TraceEntry/TraceStatus` — 0 references in publish.py
   - `source_file` field — 0 references in PublishLogEntry
   - `original_filename` field — 0 references in PublishLogEntry
   - `_flush_incremental` — 0 references (renamed to `_flush_periodic`)

2. **No scope drift:** All changes within `models/publish_log.py`, `stages/publish.py`, and test files. No other production files modified.

3. **Test coverage matches behavioral changes:**
   - Periodic flush behavior: `test_snapshot_built_once_at_end` (was `test_incremental_snapshot_every_100_files`)
   - Crash recovery: `test_crash_at_150_preserves_first_100_log` (publish log survives, snapshot does not)
   - YM stripping: 7 unit tests
   - Field removal: 4 unit tests
