# Validation Report

**Initiative:** `2026-03-07-feature-enrichment-lab-query-fix`
**Validated:** 2026-03-07

---

## Test Results

| val_id | command                                                                                                                                           | exit_code | result                                                         |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------------- | --------- | -------------------------------------------------------------- |
| VAL-1  | `pytest tests/test_query_builder.py -q --no-header --tb=short`                                                                                    | 0         | 18 passed (12 existing + 6 new)                                |
| VAL-2  | `pytest tests/test_log_config.py -q --no-header --tb=short`                                                                                       | 0         | 29 passed                                                      |
| VAL-3  | `pytest tests/test_sgf_enricher.py -q --no-header --tb=short`                                                                                     | 0         | 43 passed                                                      |
| VAL-4  | `pytest tests/test_enrich_single.py tests/test_solve_position.py -q --no-header --tb=short`                                                       | 0         | 132 passed                                                     |
| VAL-5  | `pytest tests/test_enrich_single.py tests/test_solve_position.py tests/test_query_builder.py tests/test_log_config.py tests/test_sgf_enricher.py` | 0         | 222 passed, 0 failed                                           |
| VAL-6  | `ruff check analyzers/query_builder.py log_config.py models/ai_analysis_result.py analyzers/sgf_enricher.py`                                      | 0         | All checks passed                                              |
| VAL-7  | `ruff check analyzers/solve_position.py`                                                                                                          | 1         | 2 pre-existing errors (lines 1558, 1714 — not in changed code) |

## Acceptance Criteria Verification

| ac_id | criterion                                                                         | status      | evidence                                                                                            |
| ----- | --------------------------------------------------------------------------------- | ----------- | --------------------------------------------------------------------------------------------------- |
| AC-1  | `prepare_tsumego_query()` is a pure function (no engine, no I/O, no side effects) | ✅ verified | Function only uses Position, config, and tsumego_frame — no engine imports, no file I/O             |
| AC-2  | All three query paths call `prepare_tsumego_query()`                              | ✅ verified | `build_query_from_sgf()`, `build_query_from_position()`, `SyncEngineAdapter.__init__()` all call it |
| AC-3  | `allowed_moves` structurally guaranteed in return type                            | ✅ verified | `TsumegoQueryBundle.region_moves` is a required field; all callers pass it to `AnalysisRequest`     |
| AC-4  | SyncEngineAdapter.query() includes `allowed_moves`                                | ✅ verified | `allowed_moves=self._region_moves if self._region_moves else None` at line ~510                     |
| AC-5  | Encoding: UTF-8 with errors="replace"                                             | ✅ verified | `_get_node_move_coord()` now uses `.decode("utf-8", errors="replace")`                              |
| AC-6  | No diagnostic data in C[] comments                                                | ✅ verified | Refutation comment is `"Wrong."` only; delta data logged via `logger.debug()`                       |
| AC-7  | Log files capture records from actual module prefixes                             | ✅ verified | Filter uses `_LAB_MODULE_PREFIXES` tuple with `analyzers`, `engine`, `models`, etc.                 |
| AC-8  | All existing 125+ tests still pass                                                | ✅ verified | 222 tests pass (was ~216 before, now +6 golden fixture tests)                                       |
| AC-9  | Golden fixture prevents regression                                                | ✅ verified | 6 new tests verify `allowed_moves` present, no far star points, region within bounding box          |

## Ripple Effects Validation

| impact_id | expected_effect                                          | observed_effect                                                                  | result    | follow_up_task | status      |
| --------- | -------------------------------------------------------- | -------------------------------------------------------------------------------- | --------- | -------------- | ----------- |
| RE-1      | `build_query_from_sgf` callers get same behavior         | Tests pass, AnalysisRequest has same structure                                   | match     | —              | ✅ verified |
| RE-2      | `build_query_from_position` callers get same behavior    | Tests pass, AnalysisRequest has same structure                                   | match     | —              | ✅ verified |
| RE-3      | `SyncEngineAdapter.query()` now includes `allowed_moves` | BUG-1 fixed — KataGo restricted to puzzle region                                 | match     | —              | ✅ verified |
| RE-4      | `CroppedPosition.position` no longer has komi=0 pre-crop | Only used for uncropping (board_size, offsets) — komi irrelevant                 | no impact | —              | ✅ verified |
| RE-5      | `generate_run_id()` format change                        | New format `YYYYMMDD-HHMMSS-8HEXUPPER`, used only in log file names and metadata | no impact | —              | ✅ verified |
| RE-6      | `_LabNamespaceFilter` now broader                        | Accepts actual module prefixes — log files will contain records                  | match     | —              | ✅ verified |
| RE-7      | Refutation comments shorter                              | `"Wrong."` instead of `"Wrong. Winrate drops by X%."`                            | match     | —              | ✅ verified |
| RE-8      | Pre-existing test_log_config bug fixed                   | `payload["logger"]` assertion now correct                                        | improved  | —              | ✅ verified |
