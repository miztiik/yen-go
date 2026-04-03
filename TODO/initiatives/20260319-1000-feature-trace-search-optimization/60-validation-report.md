# Validation Report

## Test Results

| val_id | command | exit_code | result |
|--------|---------|-----------|--------|
| VAL-1 | `pytest backend/puzzle_manager/tests/unit/test_publish_log.py -q --tb=short` | 0 | 50 passed |
| VAL-2 | `pytest backend/ -m unit -q --tb=short` | 0 | 1589 passed, 430 deselected |
| VAL-3 | `pytest backend/ -m "not (cli or slow)" -q --tb=no` | 0 | 1975 passed, 44 deselected |

## Ripple Effects

| impact_id | expected_effect | observed_effect | result | follow_up_task | status |
|-----------|----------------|-----------------|--------|----------------|--------|
| R-1 | Existing search_by_run_id callers get same results | 3 tests pass (TestPublishLogReader + TestPublishLogRunIdFormats) | ✅ verified | — | ✅ verified |
| R-2 | Existing search_by_puzzle_id callers get same results | Test passes | ✅ verified | — | ✅ verified |
| R-3 | Existing search_by_source callers get same results | Test passes | ✅ verified | — | ✅ verified |
| R-4 | Writer still creates .jsonl files correctly | Test passes (write_single, write_batch, write_appends) | ✅ verified | — | ✅ verified |
| R-5 | Missing indexes → graceful fallback to scan | Test `test_corrupt_index_falls_back_to_scan` passes | ✅ verified | — | ✅ verified |
| R-6 | Pre-filter rejects substring false positives | Test `test_prefilter_rejects_substring_match` passes | ✅ verified | — | ✅ verified |
