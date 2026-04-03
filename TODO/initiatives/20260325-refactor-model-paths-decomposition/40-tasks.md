# Tasks: model_paths.py Decomposition (OPT-2)

**Initiative**: 20260325-refactor-model-paths-decomposition
**Selected Option**: OPT-2 — Full decomposition into config/ + conftest
**Date**: 2026-03-25

---

## Task List

### Phase 1: Core decomposition (config/helpers.py + conftest.py)

| task_id | title | file(s) | depends_on | parallel | description |
|---|---|---|---|---|---|
| T1 | Add path constants + model_path() to config/helpers.py | `config/helpers.py` | — | — | Add `LAB_DIR`, `KATAGO_PATH`, `TSUMEGO_CFG`, `MODELS_DIR` path constants. Add `_get_cfg()` with `@lru_cache` (lazy import of `load_enrichment_config` inside function body). Add `model_path(label)` function. Update module docstring. |
| T2 | Add TEST_* constants to tests/conftest.py | `tests/conftest.py` | T1 | — | Add `TEST_STARTUP_TIMEOUT`, `TEST_QUERY_TIMEOUT`, `TEST_MAX_VISITS`, `TEST_NUM_THREADS` as module-level constants resolved from config. Import `_get_cfg` from `config.helpers`. Replace existing `model_paths` import block with `config.helpers` imports. Update module docstring. |
| T3 | Simplify clear_cache() in config/__init__.py | `config/__init__.py` | T1 | [P] with T2 | Replace cross-package `import model_paths` block with internal `from config.helpers import _get_cfg; _get_cfg.cache_clear()`. Remove TEST_* global pop logic (no longer needed — conftest resolves eagerly). |

### Phase 2: Update all importers [P] (all parallel-safe)

| task_id | title | file(s) | depends_on | parallel | description |
|---|---|---|---|---|---|
| T4 | Update test_engine_health.py imports | `tests/test_engine_health.py` | T1,T2 | [P] | Replace `from model_paths import (model_path, KATAGO_PATH, TSUMEGO_CFG, TEST_STARTUP_TIMEOUT, TEST_QUERY_TIMEOUT, TEST_MAX_VISITS, TEST_NUM_THREADS)` with `from config.helpers import model_path, KATAGO_PATH, TSUMEGO_CFG` + `from conftest import TEST_STARTUP_TIMEOUT, TEST_QUERY_TIMEOUT, TEST_MAX_VISITS, TEST_NUM_THREADS` (or import from conftest since pytest auto-provides). |
| T5 | Update test_engine_client.py imports | `tests/test_engine_client.py` | T1,T2 | [P] | Same pattern as T4. |
| T6 | Update test_enrich_single.py imports | `tests/test_enrich_single.py` | T1,T2 | [P] | Replace `from model_paths import (model_path, KATAGO_PATH, TSUMEGO_CFG, TEST_STARTUP_TIMEOUT, TEST_NUM_THREADS)` with config.helpers + conftest imports. |
| T7 | Update test_calibration.py imports | `tests/test_calibration.py` | T1 | [P] | Replace `from model_paths import model_path` with `from config.helpers import model_path`. |
| T8 | Update test_correct_move.py imports | `tests/test_correct_move.py` | T1 | [P] | Replace `from model_paths import model_path, KATAGO_PATH` with `from config.helpers import model_path, KATAGO_PATH`. |
| T9 | Update test_fixture_coverage.py imports | `tests/test_fixture_coverage.py` | T1 | [P] | Same as T8. |
| T10 | Update test_golden5.py imports | `tests/test_golden5.py` | T1 | [P] | Replace `from model_paths import model_path, KATAGO_PATH, TSUMEGO_CFG` with `from config.helpers import model_path, KATAGO_PATH, TSUMEGO_CFG`. |
| T11 | Update test_ko_validation.py imports | `tests/test_ko_validation.py` | T1 | [P] | Same as T8. |
| T12 | Update test_perf_100.py imports | `tests/test_perf_100.py` | T1 | [P] | Same as T8. |
| T13 | Update test_perf_10k.py imports | `tests/test_perf_10k.py` | T1 | [P] | Same as T8. |
| T14 | Update test_perf_1k.py imports | `tests/test_perf_1k.py` | T1 | [P] | Same as T8. |
| T15 | Update test_perf_models.py imports | `tests/test_perf_models.py` | T1 | [P] | Same as T8. |
| T16 | Update test_perf_smoke.py imports | `tests/test_perf_smoke.py` | T1 | [P] | Same as T8. |
| T17 | Update test_refutations.py imports | `tests/test_refutations.py` | T1 | [P] | Same as T8. |
| T18 | Update test_technique_calibration.py imports | `tests/test_technique_calibration.py` | T1 | [P] | Replace `from model_paths import KATAGO_PATH, TSUMEGO_CFG, model_path` with `from config.helpers import ...`. |
| T19 | Update scripts/diagnose_chase_puzzle.py imports | `scripts/diagnose_chase_puzzle.py` | T1 | [P] | Replace `from model_paths import ...` with `from config.helpers import ...`. |
| T20 | Update scripts/regenerate_benchmark_reference.py imports | `scripts/regenerate_benchmark_reference.py` | T1 | [P] | Same as T19. |
| T21 | Update scripts/_run_chase.py imports | `scripts/_run_chase.py` | T1 | [P] | Same as T19. |

### Phase 3: Cleanup + documentation

| task_id | title | file(s) | depends_on | parallel | description |
|---|---|---|---|---|---|
| T22 | Run full test suite — verify all pass | — | T1-T21 | — | Run `pytest tools/puzzle-enrichment-lab/tests/ -m "not slow" --ignore=... -q --no-header --tb=short`. All tests must pass. |
| T23 | Delete model_paths.py | `model_paths.py` | T22 | [P] | Delete the now-unused root-level `model_paths.py`. Verify no remaining imports. |
| T24 | Delete tests/_model_paths.py | `tests/_model_paths.py` | T22 | [P] | Delete the stale test-level copy. |
| T25 | Update AGENTS.md | `AGENTS.md` | T23 | — | Remove `model_paths.py` line. Update `config/helpers.py` description to include model path resolution and path constants. |
| T26 | Final regression run | — | T23,T24,T25 | — | Run full test suite one more time after deletion to confirm no lingering imports. |

---

## Summary

| Metric | Value |
|---|---|
| Total tasks | 26 |
| Core tasks (T1-T3) | 3 |
| Importer updates (T4-T21) | 18 (all [P] parallel-safe) |
| Cleanup + verification (T22-T26) | 5 |
| Files modified | ~24 |
| Files deleted | 2 (model_paths.py, tests/_model_paths.py) |
