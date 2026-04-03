# Validation Report

## Initiative: 20260324-2000-feature-backend-test-remediation

### Test Results

| ID | Command | Exit Code | Result | Status |
|----|---------|-----------|--------|--------|
| VAL-1 | `pytest backend/ -m "not (cli or slow)" -q --no-header --tb=line` | 1 | 3 failed, 2349 passed, 36 skipped, 36 deselected | ⚠️ see below |

### Failure Analysis

| ID | Test | Root Cause | In Scope? | Status |
|----|------|-----------|-----------|--------|
| VAL-2 | `test_detects_total_mismatch` | `check_integrity()` doesn't verify total count (FR-018) | ❌ production gap | Tracked in decommissioning artifact |
| VAL-3 | `test_detects_level_mismatch` | `check_integrity()` doesn't verify level counts (FR-019) | ❌ production gap | Tracked in decommissioning artifact |
| VAL-4 | `test_fix_flag_calls_rebuild` | Depends on FR-018/FR-019 | ❌ production gap | Tracked in decommissioning artifact |

### Baseline Comparison

| ID | Metric | Before | After | Delta |
|----|--------|--------|-------|-------|
| VAL-5 | Total failures | 90 | 3 | -87 ✅ |
| VAL-6 | Total passed | 2332 | 2349 | +17 ✅ |
| VAL-7 | Tests deleted | 0 | 42 | -42 |
| VAL-8 | Production files changed | 0 | 1 | +1 |
| VAL-9 | Test files edited | 0 | 13 | +13 |

### Ripple Effects Validation

| impact_id | expected_effect | observed_effect | result | follow_up_task | status |
|-----------|-----------------|-----------------|--------|----------------|--------|
| VAL-10 | `failed` accumulation fix doesn't break ingest path | Ingest metrics still pass (accumulates all 3 fields) | ✅ | none | ✅ verified |
| VAL-11 | `error_rate_publish` computation doesn't affect ingest error rate | `error_rate_ingest` still computed independently | ✅ | none | ✅ verified |
| VAL-12 | `daily_publish_throughput` override only applies in publish stage | `test_increment_preserves_daily_throughput` passes (preserves through increment) | ✅ | none | ✅ verified |
| VAL-13 | Deleted tests don't cover live production APIs | All deleted tests verified against dead/removed APIs (trace_map, _inject_yengo_props, periodic_reconcile, batch_writer_perf) | ✅ | none | ✅ verified |
| VAL-14 | Schema v2.0 assertions match production defaults | `PuzzleCollectionInventory.schema_version` defaults to `"2.0"` | ✅ | none | ✅ verified |
| VAL-15 | Flat path format `sgf/{NNNN}/` matches publish stage output | 9/9 publish tests pass with verified format | ✅ | none | ✅ verified |

### Lint Check

| ID | Command | Status |
|----|---------|--------|
| VAL-16 | `ruff check backend/puzzle_manager/inventory/manager.py` | ✅ 17 pre-existing warnings, 0 new warnings from this change |

_Last updated: 2026-03-24_
