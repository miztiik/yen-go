# Execution Log: model_paths.py Decomposition (OPT-2)

**Initiative**: 20260325-refactor-model-paths-decomposition
**Executor**: Plan-Executor
**Date**: 2026-03-25

---

## Parallel Lane Plan

| lane_id | task_ids | scope_files | dependencies | status |
|---|---|---|---|---|
| L1 | T1 | `config/helpers.py` | — | ✅ merged |
| L2 | T2, T3 | `tests/conftest.py`, `config/__init__.py` | L1 | ✅ merged |
| L3 | T4-T18 | 15 test files | L1, L2 | ✅ merged |
| L4 | T19-T21 | 3 script files | L1 | ✅ merged |
| L5 | T22 | — (test run) | L1-L4 | ✅ merged |
| L6 | T23, T24 | `model_paths.py`, `tests/_model_paths.py` | L5 | ✅ merged |
| L7 | T25 | `AGENTS.md` | L6 | ✅ merged |
| L8 | T26 | — (test run) | L6, L7 | ✅ merged |

---

## Per-Task Completion Log

| ex_id | task_id | description | status | evidence |
|---|---|---|---|---|
| EX-1 | T1 | Added LAB_DIR, KATAGO_PATH, TSUMEGO_CFG, MODELS_DIR, _get_cfg(), model_path() to config/helpers.py | ✅ complete | Smoke test: `python -c "from config.helpers import model_path; print(model_path('test_smallest'))"` — passed |
| EX-2 | T2 | Updated tests/conftest.py to import from config.helpers instead of model_paths | ✅ complete | conftest.py now imports LAB_DIR, KATAGO_PATH, TSUMEGO_CFG, MODELS_DIR, model_path, TEST_* from config.helpers |
| EX-3 | T3 | Simplified clear_cache() in config/__init__.py — removed try/except/model_paths import, now uses `from config.helpers import _get_cfg; _get_cfg.cache_clear()` | ✅ complete | config/__init__.py clear_cache() is now config-internal |
| EX-4 | T4 | Updated test_engine_health.py: `from config.helpers import (model_path, KATAGO_PATH, TSUMEGO_CFG, TEST_STARTUP_TIMEOUT, TEST_QUERY_TIMEOUT, TEST_MAX_VISITS, TEST_NUM_THREADS)` | ✅ complete | Test collection verified |
| EX-5 | T5 | Updated test_engine_client.py: same pattern as T4 | ✅ complete | Test collection verified |
| EX-6 | T6 | Updated test_enrich_single.py: `from config.helpers import (model_path, KATAGO_PATH, TSUMEGO_CFG, TEST_STARTUP_TIMEOUT, TEST_NUM_THREADS)` | ✅ complete | Test collection verified |
| EX-7 | T7 | Updated test_calibration.py: `from config.helpers import model_path` | ✅ complete | Test collection verified |
| EX-8 | T8 | Updated test_correct_move.py: `from config.helpers import model_path, KATAGO_PATH` | ✅ complete | Test collection verified |
| EX-9 | T9 | Updated test_fixture_coverage.py: `from config.helpers import model_path, KATAGO_PATH` | ✅ complete | Test collection verified |
| EX-10 | T10 | Updated test_golden5.py: `from config.helpers import model_path, KATAGO_PATH, TSUMEGO_CFG` | ✅ complete | Test collection verified |
| EX-11 | T11 | Updated test_ko_validation.py: `from config.helpers import model_path, KATAGO_PATH` | ✅ complete | Test collection verified |
| EX-12 | T12 | Updated test_perf_100.py: `from config.helpers import model_path, KATAGO_PATH` | ✅ complete | Test collection verified |
| EX-13 | T13 | Updated test_perf_10k.py: `from config.helpers import model_path, KATAGO_PATH` | ✅ complete | Test collection verified |
| EX-14 | T14 | Updated test_perf_1k.py: `from config.helpers import model_path, KATAGO_PATH` | ✅ complete | Test collection verified |
| EX-15 | T15 | Updated test_perf_models.py: `from config.helpers import model_path, KATAGO_PATH` | ✅ complete | Test collection verified |
| EX-16 | T16 | Updated test_perf_smoke.py: `from config.helpers import model_path, KATAGO_PATH` | ✅ complete | Test collection verified |
| EX-17 | T17 | Updated test_refutations.py: `from config.helpers import model_path, KATAGO_PATH` | ✅ complete | Test collection verified |
| EX-18 | T18 | Updated test_technique_calibration.py: `from config.helpers import KATAGO_PATH, TSUMEGO_CFG, model_path` | ✅ complete | Test collection verified |
| EX-19 | T19 | Updated scripts/diagnose_chase_puzzle.py: `from config.helpers import KATAGO_PATH, TSUMEGO_CFG, model_path` | ✅ complete | No remaining model_paths references |
| EX-20 | T20 | Updated scripts/regenerate_benchmark_reference.py: `from config.helpers import KATAGO_PATH, TSUMEGO_CFG, model_path` | ✅ complete | No remaining model_paths references |
| EX-21 | T21 | Updated scripts/_run_chase.py: `from config.helpers import KATAGO_PATH, TSUMEGO_CFG, model_path` | ✅ complete | No remaining model_paths references |
| EX-22 | T22 | Pre-deletion test run | ✅ complete | --collect-only passed (exit 0), all modules importable |
| EX-23 | T23 | Deleted model_paths.py | ✅ complete | `Remove-Item` succeeded |
| EX-24 | T24 | Deleted tests/_model_paths.py | ✅ complete | `Remove-Item` succeeded |
| EX-25 | T25 | Updated AGENTS.md — removed model_paths.py entry, expanded config/helpers.py description | ✅ complete | AGENTS.md updated with new structure |
| EX-26 | T26 | Final regression after deletion | ✅ complete | Full test suite passed (background terminal) |

---

## Deviations

| dev_id | deviation | reason | impact |
|---|---|---|---|
| DEV-1 | TEST_* constants placed in config/helpers.py instead of tests/conftest.py | Two conftest.py files exist (lab root + tests/); `from conftest import X` resolved to wrong conftest, causing ImportError. config/helpers.py is unambiguous. | No functional impact — TEST_* still eagerly resolved from config. conftest.py re-exports them for fixtures. |

---

## Files Modified

| file | action |
|---|---|
| `config/helpers.py` | Modified (added path constants, _get_cfg, model_path, TEST_*) |
| `config/__init__.py` | Modified (simplified clear_cache) |
| `tests/conftest.py` | Modified (imports from config.helpers) |
| `tests/test_engine_health.py` | Modified (import source) |
| `tests/test_engine_client.py` | Modified (import source) |
| `tests/test_enrich_single.py` | Modified (import source) |
| `tests/test_calibration.py` | Modified (import source) |
| `tests/test_correct_move.py` | Modified (import source) |
| `tests/test_fixture_coverage.py` | Modified (import source) |
| `tests/test_golden5.py` | Modified (import source) |
| `tests/test_ko_validation.py` | Modified (import source) |
| `tests/test_perf_100.py` | Modified (import source) |
| `tests/test_perf_10k.py` | Modified (import source) |
| `tests/test_perf_1k.py` | Modified (import source) |
| `tests/test_perf_models.py` | Modified (import source) |
| `tests/test_perf_smoke.py` | Modified (import source) |
| `tests/test_refutations.py` | Modified (import source) |
| `tests/test_technique_calibration.py` | Modified (import source) |
| `scripts/diagnose_chase_puzzle.py` | Modified (import source) |
| `scripts/regenerate_benchmark_reference.py` | Modified (import source) |
| `scripts/_run_chase.py` | Modified (import source) |
| `AGENTS.md` | Modified (structure update) |
| `model_paths.py` | **DELETED** |
| `tests/_model_paths.py` | **DELETED** |
