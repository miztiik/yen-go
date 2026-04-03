# Research Brief: model_paths.py Decomposition

**Initiative**: 20260325-refactor-model-paths-decomposition
**Status**: research_completed
**Date**: 2025-03-25

---

## 1. Research Question & Boundaries

**Question**: What is the simplest decomposition of `tools/puzzle-enrichment-lab/model_paths.py` that breaks the circular dependency with `config/__init__.py`, separates the 4 mixed concerns, and minimizes import-site churn?

**Scope**: `tools/puzzle-enrichment-lab/` only. No backend/ changes.

**Success criteria**:
- Circular dependency eliminated
- Each concern lives in a single, obvious location
- Existing 20+ importer sites require minimal mechanical edits
- No new packages or external dependencies

---

## 2. Internal Code Evidence

### 2.1 Current model_paths.py — 4 concerns in one file

| Concern | Symbols | Lines | Dependency |
|---|---|---|---|
| R-1 Path constants | `LAB_DIR`, `KATAGO_PATH`, `TSUMEGO_CFG`, `MODELS_DIR` | 25-32 | Pure `pathlib`, zero imports |
| R-2 sys.path manipulation | `sys.path.insert(0, str(LAB_DIR))` | 28-29 | Side effect at import time |
| R-3 Config-driven model resolution | `model_path(label)`, `_get_cfg()` | 37-64 | `config.load_enrichment_config` (→ circular) |
| R-4 Test defaults | `TEST_STARTUP_TIMEOUT`, `TEST_QUERY_TIMEOUT`, `TEST_MAX_VISITS`, `TEST_NUM_THREADS` | 70-98 | `_get_cfg()` → same circular path |

### 2.2 The circular dependency chain

```
model_paths.py  ──(module-level)──►  config/__init__.py :: load_enrichment_config
config/__init__.py :: clear_cache()  ──(function-level)──►  model_paths._get_cfg.cache_clear()
```

- `model_paths.py` line 37: `from config import load_enrichment_config as _load_cfg` — **module-level import**
- `config/__init__.py` line 178: `from model_paths import _get_cfg` — **inside `clear_cache()` function body** (lazy)
- `config/__init__.py` line 181: `import model_paths` — **inside `clear_cache()` function body** (to pop TEST_* globals)

The config→model_paths direction is already lazy (inside a function). The model_paths→config direction is the **eagerly-loaded** side. Making that lazy would break the cycle at zero cost.

### 2.3 config/ package already has infrastructure for models & test defaults

| File | Relevant model | Can absorb? |
|---|---|---|
| R-5 `config/analysis.py` | `ModelsConfig`, `ModelEntry` — defines the schema for model labels/filenames | Already owns the **schema**; does NOT own resolution (Path computation) |
| R-6 `config/infrastructure.py` | `TestDefaultsConfig`, `PathsConfig`, `CalibrationConfig` | Already owns the **schema** for test defaults |
| R-7 `config/__init__.py` | `resolve_path(config, path_key)` — resolves config path keys to `_LAB_DIR / value` | **Existing pattern** for config-driven path resolution |
| R-8 `config/helpers.py` | `get_effective_max_visits(config, mode_override)` — config accessor pattern | Example of config accessor helper; could house `model_path()` |

**Key insight**: `config/__init__.py` already has `resolve_path()` (line ~192) which does `_LAB_DIR / value`. The `model_path()` function is conceptually identical: resolve a config key to `_LAB_DIR / "models-data" / entry.filename`. This is a config path resolution concern, not a "model paths" concern.

### 2.4 conftest.py already provides integration_engine fixture

`tests/conftest.py` lines 20-28 imports:
- `LAB_DIR`, `KATAGO_PATH`, `TSUMEGO_CFG`, `MODELS_DIR` (path constants)
- `model_path` (config resolution)
- `TEST_STARTUP_TIMEOUT`, `TEST_MAX_VISITS`, `TEST_NUM_THREADS` (test defaults)

It uses these to build the `integration_engine` fixture (lines 40-76). **7 test files** already use `integration_engine` from conftest instead of building their own engines.

However, **3 test files** (`test_engine_client.py`, `test_engine_health.py`, `test_enrich_single.py`) import TEST_* constants directly because they build custom engine configurations (not using the shared fixture).

### 2.5 Production code does NOT import model_paths

| Layer | Uses model_paths? | How it gets paths |
|---|---|---|
| R-9 `cli.py` | ❌ No | Receives `katago_path` from CLI args |
| R-10 `bridge.py` | ❌ No | Receives `katago_path` from CLI args |
| R-11 `engine/` | ❌ No | Receives paths via `EngineConfig` injection |
| R-12 `analyzers/` | ❌ No | Receives paths via constructor args |
| R-13 `config/` | ❌ (only clear_cache lazy ref) | N/A |

**model_paths.py is exclusively a test/script convenience module.** Production code receives all paths via dependency injection from CLI.

---

## 3. Importer Analysis — Grouped by Need

### Group A: Path constants + model_path() only (no TEST_*)

| # | File | Imports | Category |
|---|---|---|---|
| R-14 | `tests/conftest.py` | `LAB_DIR, KATAGO_PATH, TSUMEGO_CFG, MODELS_DIR, model_path, TEST_STARTUP_TIMEOUT, TEST_MAX_VISITS, TEST_NUM_THREADS` | Test infra (all 4 concerns) |
| R-15 | `tests/test_calibration.py` | `model_path` | model_path only |
| R-16 | `tests/test_correct_move.py` | `model_path, KATAGO_PATH` | paths + model_path |
| R-17 | `tests/test_fixture_coverage.py` | `model_path, KATAGO_PATH` | paths + model_path |
| R-18 | `tests/test_golden5.py` | `model_path, KATAGO_PATH, TSUMEGO_CFG` | paths + model_path |
| R-19 | `tests/test_ko_validation.py` | `model_path, KATAGO_PATH` | paths + model_path |
| R-20 | `tests/test_perf_100.py` | `model_path, KATAGO_PATH` | paths + model_path |
| R-21 | `tests/test_perf_10k.py` | `model_path, KATAGO_PATH` | paths + model_path |
| R-22 | `tests/test_perf_1k.py` | `model_path, KATAGO_PATH` | paths + model_path |
| R-23 | `tests/test_perf_models.py` | `model_path, KATAGO_PATH` | paths + model_path |
| R-24 | `tests/test_perf_smoke.py` | `model_path, KATAGO_PATH` | paths + model_path |
| R-25 | `tests/test_refutations.py` | `model_path, KATAGO_PATH` | paths + model_path |
| R-26 | `tests/test_technique_calibration.py` | `KATAGO_PATH, TSUMEGO_CFG, model_path` | paths + model_path |
| R-27 | `scripts/diagnose_chase_puzzle.py` | `KATAGO_PATH, TSUMEGO_CFG, model_path` | paths + model_path |
| R-28 | `scripts/regenerate_benchmark_reference.py` | `KATAGO_PATH, TSUMEGO_CFG, model_path` | paths + model_path |
| R-29 | `scripts/_run_chase.py` | `KATAGO_PATH, TSUMEGO_CFG, model_path` | paths + model_path |

### Group B: Path constants + model_path() + TEST_* defaults

| # | File | Imports | Category |
|---|---|---|---|
| R-30 | `tests/conftest.py` | All 4 concerns | Central fixture provider |
| R-31 | `tests/test_engine_client.py` | `model_path, KATAGO_PATH, TSUMEGO_CFG, TEST_STARTUP_TIMEOUT, TEST_QUERY_TIMEOUT, TEST_MAX_VISITS, TEST_NUM_THREADS` | All 4 concerns |
| R-32 | `tests/test_engine_health.py` | Same as above | All 4 concerns |
| R-33 | `tests/test_enrich_single.py` | `model_path, KATAGO_PATH, TSUMEGO_CFG, TEST_STARTUP_TIMEOUT, TEST_NUM_THREADS` | All 4 concerns (partial TEST_*) |

### Group C: config/__init__.py (circular dependency participant)

| # | File | Import style | Purpose |
|---|---|---|---|
| R-34 | `config/__init__.py::clear_cache()` | `from model_paths import _get_cfg` (lazy, inside function) | Invalidate lru_cache + pop TEST_* globals |

### Summary counts

| Need | # Files |
|---|---|
| Only `model_path()` | 1 |
| Path constants + `model_path()` | 14 |
| Path constants + `model_path()` + TEST_* | 4 |
| Circular dep (clear_cache) | 1 |
| **Total unique importers** | **20** |

---

## 4. External Patterns & References

### 4.1 puzzle_intent tool pattern

`tools/puzzle_intent/config_loader.py` uses a self-contained pattern:
- `@lru_cache` loader resolves path relative to `__file__`
- No sys.path manipulation; no circular deps
- Config path is computed from `Path(__file__).parent.parent.parent / "config/..."``

This is the **cleanest internal pattern**: config loading lives in its own module with no cross-dependencies.

### 4.2 Python lazy-import pattern (PEP 690 / importlib)

The standard approach for breaking circular imports:
- Move the module-level `from config import ...` **inside** the function that needs it
- Python 3.12+ has `importlib.util.lazy_import()` but stdlib `lru_cache` + local import achieves the same

### 4.3 pytest fixture-first pattern

The pytest-native approach to shared test constants:
- Define constants/fixtures in `conftest.py` (auto-discovered, no import needed)
- Tests request fixtures by parameter name, never import from utility modules
- This eliminates the TEST_* constants from model_paths entirely

### 4.4 Django settings pattern (for reference)

Django separates path computation (`BASE_DIR = Path(__file__).parent`) from config loading (settings module). The paths are pure constants; config is loaded separately. This maps directly to the proposed decomposition.

---

## 5. Candidate Decomposition Options

### Option A: Minimal — Lazy import only (break the cycle, keep the file)

**Change**: Move `from config import load_enrichment_config` inside `_get_cfg()`.

```python
# model_paths.py - line 37 becomes:
@lru_cache(maxsize=1)
def _get_cfg():
    from config import load_enrichment_config  # lazy import breaks cycle
    return load_enrichment_config()
```

| Pros | Cons |
|---|---|
| 1-line change | File still mixes 4 concerns |
| Zero importer churn | test defaults still coupled to config resolution |
| Breaks circular dep immediately | clear_cache() still needs to reach into model_paths |

### Option B: Split into 2 files — paths.py + model_paths.py

**New file**: `lab_paths.py` — pure path constants + sys.path side effect (R-1, R-2)
**Slimmed**: `model_paths.py` — `model_path()` + TEST_* defaults, imports from `lab_paths.py`

| Pros | Cons |
|---|---|
| Pure constants in one place | Still 2 concerns in model_paths |
| Import sites can choose lightweight `lab_paths` | 20 import-site edits if we move symbols |

### Option C: Absorb model_path() into config/, TEST_* into conftest — **recommended**

1. **Move `model_path(label)`** into `config/helpers.py` (aligns with `resolve_path()` and `get_effective_max_visits()` patterns already there)
2. **Move TEST_* defaults** into `tests/conftest.py` as module-level constants (or add a tiny `tests/test_defaults.py`)
3. **Keep `model_paths.py` as a thin re-export shim** for backward compat:
   ```python
   # model_paths.py - becomes a pure re-export, no config import needed
   from config.helpers import model_path, KATAGO_PATH, TSUMEGO_CFG, MODELS_DIR, LAB_DIR
   # TEST_* are no longer here; tests import from conftest fixtures or test_defaults
   ```
4. **clear_cache()** invalidation: `config/__init__.py` controls its own `_get_cfg` cache — no need to reach outside the package.

| Pros | Cons |
|---|---|
| Circular dep eliminated entirely | ~20 import sites to update (mechanical) |
| Single Responsibility per module | conftest grows slightly |
| config/ owns all config resolution | Needs Option A first as Phase 0 |
| TEST_* live where tests live | |
| `model_paths.py` can be deprecated gradually | |

### Option D: Full extraction — new `lab_paths.py` + absorb into config/ + conftest

Same as C but also extracts path constants into `lab_paths.py` so `config/` doesn't need to define them (it already has `_LAB_DIR` internally).

| Pros | Cons |
|---|---|
| Maximum separation | 3 new locations for symbols that lived in 1 |
| config/ has no path constants | Over-engineering — config/ already knows _LAB_DIR |

---

## 6. Risks, License/Compliance, Rejection Reasons

| # | Risk | Severity | Mitigation |
|---|---|---|---|
| R-35 | Import-site churn introduces typos | Low | Regex find-replace; model_paths re-export shim during transition |
| R-36 | conftest.py auto-discovery masks import errors | Low | TEST_* constants are simple scalars — failure is obvious |
| R-37 | `tests/_model_paths.py` (old shim) may confuse imports | Low | Delete it — it's the pre-rename relic |
| R-38 | Breaking `clear_cache()` invalidation | Medium | If model_path() moves to config/, its cache lives in config/ — clear_cache() just clears its own package's cache. No cross-package invalidation needed. |

No license/compliance concerns — all code is internal, no external code being absorbed.

**Rejection reasons for Option D**: Over-engineers the path constants split. `config/` already computes `_LAB_DIR` internally (line 57 of `__init__.py`). Creating a separate `lab_paths.py` just to export `LAB_DIR` adds a file with no new value.

---

## 7. Planner Recommendations

1. **Phase 0 (Level 1 fix, 1 file, <5 lines)**: Apply Option A — make the `from config import load_enrichment_config` lazy inside `_get_cfg()`. This immediately breaks the circular dependency with zero importer churn. Can be done and shipped independently.

2. **Phase 1 (Level 3 refactor, ~5 files)**: Apply Option C — move `model_path()` + path constants into `config/helpers.py`, move TEST_* into `tests/conftest.py` as module constants. Keep `model_paths.py` as a thin re-export shim (`from config.helpers import *`) so existing imports don't break. This is the minimal-churn path to clean separation.

3. **Phase 2 (Level 1 cleanup, optional)**: Delete the re-export shim and update all 20 import sites to use direct imports. Also delete `tests/_model_paths.py` (stale relic). This can be deferred indefinitely since the shim has zero runtime cost.

4. **Do NOT pursue Option D** — extracting a separate `lab_paths.py` adds complexity with no benefit since `config/` already computes `_LAB_DIR` internally.

---

## 8. Confidence & Risk Assessment

| Metric | Value |
|---|---|
| `post_research_confidence_score` | 92 |
| `post_research_risk_level` | low |

**Rationale**: The circular dependency is well-understood (one eager import on one side, lazy on the other). The decomposition targets are clear (config/ absorbs resolution, conftest absorbs test defaults). The main risk is mechanical churn, mitigated by the re-export shim strategy.

---

## Open Questions

| q_id | question | options | recommended | user_response | status |
|---|---|---|---|---|---|
| Q1 | Should Phase 0 (lazy import fix) be shipped as a standalone commit before Phase 1? | A: Yes, ship independently / B: Bundle with Phase 1 | A | | ❌ pending |
| Q2 | Should `model_paths.py` re-export shim be kept permanently or scheduled for deletion? | A: Keep permanently / B: Delete in Phase 2 / C: Delete after 30 days | B | | ❌ pending |
| Q3 | Should `tests/_model_paths.py` (stale relic from rename) be deleted as part of this initiative or separately? | A: Delete in Phase 0 / B: Delete in Phase 1 / C: Separate cleanup | A | | ❌ pending |
