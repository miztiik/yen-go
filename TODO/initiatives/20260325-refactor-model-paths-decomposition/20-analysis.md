# Analysis: model_paths.py Decomposition (OPT-2)

**Initiative**: 20260325-refactor-model-paths-decomposition
**Date**: 2026-03-25

---

## Planning Metrics

| Metric | Value |
|---|---|
| `planning_confidence_score` | 95 |
| `risk_level` | low |
| `research_invoked` | yes (Feature-Researcher) |
| `post_research_confidence_delta` | +42 (50 → 92 → 95 post-clarification) |

---

## Cross-Artifact Consistency Check

| finding_id | check | charter | plan | tasks | status |
|---|---|---|---|---|---|
| F1 | Goal 1 (break circular dep) → T1 (lazy import), T3 (clear_cache simplification) | ✅ G1 | ✅ D2, D3 | ✅ T1, T3 | ✅ traced |
| F2 | Goal 2 (SRP) → T1 (model_path to helpers), T2 (TEST_* to conftest) | ✅ G2 | ✅ D1, D4 | ✅ T1, T2 | ✅ traced |
| F3 | Goal 3 (align with patterns) → T1 (model_path alongside resolve_path in helpers) | ✅ G3 | ✅ D1 | ✅ T1 | ✅ traced |
| F4 | Goal 4 (update all importers) → T4-T21 (18 importer updates) | ✅ G4 | ✅ plan Phase 2 | ✅ T4-T21 | ✅ traced |
| F5 | AC-1 (no circular import) → D2 (lazy import) + D3 (config-internal clear_cache) | ✅ | ✅ | ✅ T1, T3 | ✅ traced |
| F6 | AC-2 (model_path from config.helpers) → T1 | ✅ | ✅ D1 | ✅ T1 | ✅ traced |
| F7 | AC-3 (path constants canonical location) → T1 (config/helpers.py) | ✅ | ✅ D1 | ✅ T1 | ✅ traced |
| F8 | AC-4 (TEST_* in test infra) → T2 (conftest.py) | ✅ | ✅ D4 | ✅ T2 | ✅ traced |
| F9 | AC-5 (model_paths.py deleted) → T23 | ✅ | ✅ Phase 3 | ✅ T23 | ✅ traced |
| F10 | AC-6 (clear_cache config-internal) → T3 | ✅ | ✅ D3 | ✅ T3 | ✅ traced |
| F11 | AC-7 (all tests pass) → T22, T26 | ✅ | ✅ Phase 3 | ✅ T22, T26 | ✅ traced |
| F12 | AC-8 (AGENTS.md updated) → T25 | ✅ | ✅ doc plan | ✅ T25 | ✅ traced |
| F13 | Must-hold: run_calibration.py scoping | ✅ charter | ✅ D6 (out of scope) | n/a | ✅ documented |

**Coverage**: All 8 ACs and 4 goals are traced to specific tasks. No unmapped tasks. No unmapped ACs.

---

## Ripple Effects Analysis

| impact_id | direction | area | risk | mitigation | owner_task | status |
|---|---|---|---|---|---|---|
| IMP-1 | upstream | `config/__init__.py` loads config that `_get_cfg()` caches | Low | `_get_cfg()` uses lazy import; `clear_cache()` clears it internally | T1, T3 | ✅ addressed |
| IMP-2 | downstream | 15 test files import path constants + model_path() | Low | Mechanical import replacement; test suite validates | T4-T18 | ✅ addressed |
| IMP-3 | downstream | 3 script files import from model_paths | Low | Mechanical import replacement; scripts have own sys.path setup | T19-T21 | ✅ addressed |
| IMP-4 | lateral | `conftest.py` provides `integration_engine` fixture using model_path + TEST_* | Low | conftest.py is updated first (T2); fixture logic unchanged | T2 | ✅ addressed |
| IMP-5 | lateral | `scripts/run_calibration.py` has own `_resolve_model_paths()` | None | Independent of model_paths.py; out of scope per D6 | n/a | ✅ addressed |
| IMP-6 | lateral | `tests/_model_paths.py` (stale copy) could shadow imports | Low | Deleted in T24 before it causes confusion | T24 | ✅ addressed |
| IMP-7 | downstream | `config/helpers.py` currently uses `TYPE_CHECKING` for `EnrichmentConfig` | Low | After T1, helpers.py uses lazy runtime import (`from config import load_enrichment_config` inside `_get_cfg()`); TYPE_CHECKING imports remain for type hints only | T1 | ✅ addressed |
| IMP-8 | lateral | model_paths.py `sys.path.insert(0, LAB_DIR)` side effect at import | None | conftest.py already handles sys.path; scripts have their own. Deletion removes the redundant side effect. | T23 | ✅ addressed |
| IMP-9 | lateral | `AGENTS.md` references `model_paths.py` | Low | Updated in T25 | T25 | ✅ addressed |

---

## Severity Assessment

| finding_id | severity | description |
|---|---|---|
| F14 | info | T4-T6 require importing TEST_* from conftest — in pytest, conftest symbols are auto-discoverable but direct `from conftest import X` is also valid. Plan assumes direct import for clarity. |
| F15 | info | config/helpers.py will grow from 80 lines to ~140 lines. This is acceptable — all additions are cohesive config accessors (path resolution, model resolution). |
| F16 | low | After T23 (delete model_paths.py), any PyPI or CI step that imports model_paths directly would fail. Verified: no CI config references model_paths.py (it's not a published package). |

---

## Unmapped Tasks

None. All tasks trace to charter goals/ACs. All ACs have at least one task.

---

## Test Strategy

| phase | what | command |
|---|---|---|
| After Phase 1 (T1-T3) | Smoke test: import config.helpers.model_path works | `python -c "from config.helpers import model_path; print(model_path('test_smallest'))"` |
| After Phase 2 (T4-T21) | Full regression | Task `enrichment-regression` |
| After Phase 3 (T22-T26) | Final regression after file deletion | Task `enrichment-regression` |
