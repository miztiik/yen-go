# Options: model_paths.py Decomposition

**Initiative**: 20260325-refactor-model-paths-decomposition
**Date**: 2026-03-25

---

## Options Comparison

| Dimension | OPT-1: Minimal (lazy import only) | OPT-2: Full decomposition into config/ + conftest | OPT-3: New lab_paths.py + config/ + conftest |
|---|---|---|---|
| **Approach** | Make `from config import ...` lazy inside `_get_cfg()`. model_paths.py stays as-is. | Move `model_path()` + path constants → `config/helpers.py`. Move TEST_* → `conftest.py`. Delete model_paths.py. Update all 20+ importers. | Extract path constants to new `lab_paths.py`, move model_path() to config/, TEST_* to conftest. |
| **Files changed** | 1 (model_paths.py) | ~6 core + 20 importers | ~7 core + 20 importers + new file |
| **Circular dep** | Broken (lazy import) | Eliminated (model_path lives in config/) | Eliminated |
| **SRP compliance** | ❌ Still 4 concerns in 1 file | ✅ Each concern in canonical location | ✅ But adds unnecessary file |
| **Import churn** | 0 importers changed | 20+ importers updated | 20+ importers updated |
| **clear_cache() fix** | Still needs cross-package reach | Config-internal: `_get_cfg.cache_clear()` stays in config/ | Same as OPT-2 |
| **Test defaults** | Still coupled to model resolution | Decoupled into test infrastructure | Same as OPT-2 |
| **Complexity** | Trivial | Moderate (mechanical) | Moderate + unnecessary abstraction |
| **Risk** | Very low | Low (mechanical refactor) | Low + over-engineering risk |
| **Rollback** | Revert 1 line | Revert ~26 files (all mechanical) | Same + delete extra file |
| **Architecture compliance** | Partial fix (cycle broken, SRP violated) | Full compliance | Over-engineered |
| **User direction alignment** | ❌ Does NOT match "full decomposition, NOT facade" | ✅ Matches user direction exactly | ❌ Over-engineers path constants split |

---

## OPT-1: Minimal — Lazy Import Only

**Summary**: Move `from config import load_enrichment_config` from module-level (line 37) into `_get_cfg()` function body. Everything else stays.

**Benefits**: 1-line change, zero blast radius, breaks cycle immediately.
**Drawbacks**: model_paths.py still mixes 4 concerns. Doesn't satisfy user's "full decomposition" direction.
**Architecture compliance**: Breaks cycle but retains SRP violation.
**Recommendation**: Rejected — user explicitly chose CR-Beta decomposition.

---

## OPT-2: Full Decomposition into config/ + conftest (RECOMMENDED)

**Summary**:
1. Move `model_path(label)`, `_get_cfg()`, path constants (LAB_DIR, KATAGO_PATH, TSUMEGO_CFG, MODELS_DIR) into `config/helpers.py`
2. Move TEST_* defaults resolution into `tests/conftest.py` as module-level constants
3. Update `config/__init__.py` `clear_cache()` to clear `_get_cfg` cache internally (no cross-package import)
4. Update all 20+ test/script importers to use `from config.helpers import model_path, KATAGO_PATH, ...`
5. Delete `model_paths.py` and `tests/_model_paths.py`

**Benefits**:
- Circular dependency completely eliminated (model_path lives IN config/)
- SRP: config resolution in config/, test infra in conftest, path constants in config/helpers
- Aligns `model_path()` with existing `resolve_path()` and `get_effective_max_visits()` patterns
- `clear_cache()` only clears its own package's state — no cross-package invalidation
- Matches user direction: "full decomposition, NOT facade"

**Drawbacks**:
- 20+ files touched (all mechanical find-replace)
- config/helpers.py grows (but these are cohesive config accessors)

**Risks**:
- R-35: Import-site typos (mitigation: mechanical regex replace, test suite validates)
- R-38: clear_cache() invalidation (mitigation: cache lives in config/ now, self-contained)

**Test impact**: All tests must be re-run; import paths change but behavior is identical.
**Rollback**: Revert the commit (all changes are mechanical).

---

## OPT-3: New lab_paths.py + config/ + conftest

**Summary**: Same as OPT-2 but also extracts path constants (LAB_DIR, KATAGO_PATH, etc.) into a new `lab_paths.py` at root, separate from config/.

**Benefits**: Maximum separation of concerns.
**Drawbacks**: Over-engineering — `config/__init__.py` already computes `_LAB_DIR` internally (line 57). Creating a separate file just to export `LAB_DIR` adds a module with no new value. Adding yet another root-level file goes against the cleanup direction.
**Recommendation**: Rejected — YAGNI. config/ already knows its own paths.

---

## Evaluation Matrix

| Criterion | Weight | OPT-1 | OPT-2 | OPT-3 |
|---|---|---|---|---|
| Breaks circular dep | 20% | ✅ 10/10 | ✅ 10/10 | ✅ 10/10 |
| SRP compliance | 20% | ❌ 3/10 | ✅ 9/10 | ✅ 9/10 |
| User direction match | 25% | ❌ 2/10 | ✅ 10/10 | ⚠️ 7/10 |
| Minimal complexity | 15% | ✅ 10/10 | ✅ 8/10 | ⚠️ 6/10 |
| Architecture alignment | 10% | ⚠️ 5/10 | ✅ 9/10 | ⚠️ 7/10 |
| YAGNI/KISS | 10% | ✅ 9/10 | ✅ 9/10 | ❌ 4/10 |
| **Weighted Score** | 100% | **5.8** | **9.2** | **7.4** |

**Recommendation**: **OPT-2** — Full decomposition into config/ + conftest.
