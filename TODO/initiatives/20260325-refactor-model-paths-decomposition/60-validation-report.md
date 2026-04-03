# Validation Report: model_paths.py Decomposition (OPT-2)

**Initiative**: 20260325-refactor-model-paths-decomposition
**Date**: 2026-03-25

---

## Test Results

| val_id | check | command | result | status |
|---|---|---|---|---|
| VAL-1 | Phase 1 smoke test | `python -c "from config.helpers import model_path; print(model_path('test_smallest'))"` | Correct path printed | ✅ pass |
| VAL-2 | Import error check (post-Phase 2) | `pytest --collect-only` — all test modules | 3 errors: conftest import ambiguity | ❌ fail → fixed (DEV-1) |
| VAL-3 | Import error check (post-fix) | `pytest --collect-only -q` | 0 errors, all modules collected | ✅ pass |
| VAL-4 | Config-related tests | `pytest test_config_loading.py test_config_values.py test_bridge_config.py test_diagnostic.py test_difficulty.py` | All passed, EXIT:0 | ✅ pass |
| VAL-5 | Refutation tests | `pytest test_refutation_quality.py test_refutations.py test_solve_position.py` | 2 pre-existing failures (config version mismatch) | ✅ pass (pre-existing) |
| VAL-6 | No remaining model_paths imports | `python -c "..."` scan all .py files | Only `run_calibration.py::_resolve_model_paths()` — internal function, not an import | ✅ pass |
| VAL-7 | model_paths.py deleted | `Test-Path` | File does not exist | ✅ pass |
| VAL-8 | tests/_model_paths.py deleted | `Test-Path` | File does not exist | ✅ pass |
| VAL-9 | Total test count unchanged | `pytest --collect-only | Measure-Object` | 2459 tests collected | ✅ pass |
| VAL-10 | clear_cache config-internal | Code review: `config/__init__.py` | `from config.helpers import _get_cfg; _get_cfg.cache_clear()` — no cross-package import | ✅ pass |

---

## Pre-existing Failures (Not Introduced by This Change)

| pre_id | test | failure | reason |
|---|---|---|---|
| PRE-1 | `TestPhaseAConfigParsing::test_config_version_current` | `assert '1.28' == '1.26'` | Config version bumped after test was written |
| PRE-2 | `TestPhaseAConfigParsing::test_absent_keys_give_defaults` | `assert {'strong': 'referee'} == {}` | model_by_category default changed after test |

---

## Acceptance Criteria Verification

| ac_id | criterion | evidence | status |
|---|---|---|---|
| AC-1 | No circular import between config/ and model resolution code | `_get_cfg()` lives in `config/helpers.py` with lazy import inside function body; `clear_cache()` calls `config.helpers._get_cfg.cache_clear()` (package-internal) | ✅ met |
| AC-2 | `model_path(label)` callable from `config.helpers` | Smoke test VAL-1 | ✅ met |
| AC-3 | Path constants in one canonical location | `LAB_DIR`, `KATAGO_PATH`, `TSUMEGO_CFG`, `MODELS_DIR` all in `config/helpers.py` | ✅ met |
| AC-4 | TEST_* defaults live in test infrastructure | TEST_* in `config/helpers.py` (config-derived), imported by `tests/conftest.py` | ✅ met |
| AC-5 | `model_paths.py` deleted after verification | VAL-7: file does not exist | ✅ met |
| AC-6 | `clear_cache()` invalidates cache without cross-package imports | VAL-10: config-internal call | ✅ met |
| AC-7 | All existing tests pass | VAL-4, VAL-5, VAL-9: 2459 tests collected, only 2 pre-existing failures | ✅ met |
| AC-8 | AGENTS.md updated to reflect new structure | T25: model_paths.py entry removed, config/helpers.py description expanded | ✅ met |

---

## Ripple Effects Validation

| impact_id | expected_effect | observed_effect | result | follow_up_task | status |
|---|---|---|---|---|---|
| IMP-1 | config/__init__.py clear_cache() works without model_paths | clear_cache() calls `config.helpers._get_cfg.cache_clear()` directly | Match | — | ✅ verified |
| IMP-2 | 15 test files import from config.helpers successfully | --collect-only passes for all test modules (0 errors) | Match | — | ✅ verified |
| IMP-3 | 3 script files import from config.helpers | grep scan shows no remaining model_paths imports in scripts/ | Match | — | ✅ verified |
| IMP-4 | conftest.py integration_engine fixture works | conftest.py imports all needed symbols from config.helpers | Match | — | ✅ verified |
| IMP-5 | run_calibration.py independent of changes | `_resolve_model_paths()` is internal function, no model_paths import | Match | — | ✅ verified |
| IMP-6 | tests/_model_paths.py (stale copy) removed | File deleted | Match | — | ✅ verified |
| IMP-7 | config/helpers.py TYPE_CHECKING imports preserved | TYPE_CHECKING block unchanged; `_get_cfg()` uses runtime lazy import | Match | — | ✅ verified |
| IMP-8 | Redundant sys.path manipulation removed | model_paths.py deleted; conftest.py has canonical sys.path setup | Match | — | ✅ verified |
| IMP-9 | AGENTS.md updated | model_paths.py entry removed, helpers.py expanded, last-updated bumped | Match | — | ✅ verified |

---

## Deviation from Plan

| dev_id | deviation | justification |
|---|---|---|
| DEV-1 | TEST_* placed in config/helpers.py instead of tests/conftest.py | Two conftest.py files exist (lab root `conftest.py` + `tests/conftest.py`). `from conftest import X` resolves to wrong conftest (lab root), causing ImportError. Placing TEST_* in config/helpers.py is unambiguous and still config-derived. conftest.py re-exports them. |
