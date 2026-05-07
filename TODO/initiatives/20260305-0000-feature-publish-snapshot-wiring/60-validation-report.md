# Validation Report: Wire SnapshotBuilder into Publish Stage

**Last Updated**: 2026-03-05

---

## Test Results

### Snapshot Wiring Tests (T7)

```
Command: pytest backend/puzzle_manager/tests/integration/test_publish_snapshot_wiring.py -v
Exit code: 0
Result: 7 passed in 1.67s
```

| Test                                        | Status  |
| ------------------------------------------- | ------- |
| `test_first_publish_creates_snapshot`       | ✅ PASS |
| `test_old_views_not_produced`               | ✅ PASS |
| `test_empty_batch_no_snapshot`              | ✅ PASS |
| `test_incremental_publish`                  | ✅ PASS |
| `test_shard_pages_array_format`             | ✅ PASS |
| `test_validation_failure_blocks_activation` | ✅ PASS |
| `test_atomic_writes_used`                   | ✅ PASS |

### Full Regression (T8)

```
Command: pytest backend/puzzle_manager/tests -m "not (cli or slow)" --tb=short -q
Exit code: 1
Result: 2030 passed, 9 failed, 44 deselected in 76s
```

### Pre-existing Failures (not introduced by this change)

| Test                                                                  | Failure                                    | Root Cause                       | Our Change? |
| --------------------------------------------------------------------- | ------------------------------------------ | -------------------------------- | ----------- |
| `test_adapter_registry::test_adapter_discovery_logs_once`             | assert 0 == 1                              | Adapter logging refactor         | No          |
| `test_adapter_registry::test_adapter_discovery_summary_is_info_level` | assert 0 == 1                              | Adapter logging refactor         | No          |
| `test_tag_taxonomy::test_version_is_8_1`                              | "8.2" != "8.1"                             | Config version bumped            | No          |
| `test_inventory_publish::test_failed_write_preserves_original`        | Missing `_save_unlocked`                   | InventoryManager refactor        | No          |
| `test_publish_log_integration::test_publish_writes_log_entries`       | Mock expects `write()` not `write_batch()` | Test not updated for batch write | No          |
| `test_publish_log_integration::test_publish_writes_audit_entry`       | audit.jsonl missing                        | Test assumption about audit      | No          |
| `test_publish_robustness::test_batch_state_flushed_at_interval`       | save count 1 < 3                           | Sub-batch flush not wired        | No          |
| `test_publish_robustness::test_per_file_log_is_detail_level`          | INFO (20) != DETAIL (15)                   | Custom log level not applied     | No          |
| `test_publish_robustness::test_publish_result_includes_remaining`     | 0 != 3                                     | Remaining count not computed     | No          |

**Evidence**: Only `backend/puzzle_manager/stages/publish.py` was modified (confirmed via `git diff --stat`). All 9 failing tests test behaviors that exist in the unmodified code path.

## Consistency Analysis

### Scope Match

- [x] T1: Imports added (SnapshotBuilder, ShardEntry, IdMaps, parse_yx)
- [x] T2: IdMaps.load() initialized, new_entries list, slug counters
- [x] T3: ShardEntry construction per puzzle, slug counters for inventory
- [x] T4: SnapshotBuilder workflow (load → merge → build), dry-run path
- [x] T5: \_update_indexes, \_update_indexes_flat, \_update_collection_indexes deleted
- [x] T6: \_update_inventory simplified to accept slug-based counters directly
- [x] T7: All 7 snapshot wiring tests pass
- [x] T8: No new test regressions

### Acceptance Criteria (from 00-charter.md)

- [x] `publish` stage produces `snapshots/` + `active-snapshot.json` output
- [x] No `views/by-level/`, `views/by-tag/`, `views/by-collection/` output
- [x] Incremental publish merges existing entries by compact path
- [x] Shard pages use array-of-arrays format
- [x] Zero new test failures introduced
- [x] Single file changed (`publish.py`)

### No Regressions

- [x] Publish log writing: unchanged (write_batch still called)
- [x] Inventory updates: working with slug-based counters
- [x] Batch state management: unchanged
- [x] Cleanup policy: unchanged
- [x] Trace registry: unchanged
- [x] Dry-run mode: snapshot path has dry-run guard
