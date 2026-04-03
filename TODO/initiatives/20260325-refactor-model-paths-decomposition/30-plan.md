# Plan: model_paths.py Decomposition (OPT-2)

**Initiative**: 20260325-refactor-model-paths-decomposition
**Selected Option**: OPT-2 — Full decomposition into config/ + conftest
**Date**: 2026-03-25

---

## Architecture Overview

### Current State
```
model_paths.py (root)
├── Path constants: LAB_DIR, KATAGO_PATH, TSUMEGO_CFG, MODELS_DIR
├── sys.path manipulation
├── _get_cfg() with @lru_cache → from config import load_enrichment_config  ←── CIRCULAR
├── model_path(label) → Path
└── TEST_* defaults via module __getattr__

config/__init__.py
└── clear_cache() → import model_paths → _get_cfg.cache_clear()  ←── CIRCULAR
```

### Target State
```
config/helpers.py
├── Path constants: LAB_DIR, KATAGO_PATH, TSUMEGO_CFG, MODELS_DIR  (new)
├── _get_cfg() with @lru_cache (lazy import of load_enrichment_config)  (new)
├── model_path(label) → Path  (new)
└── get_level_category(), get_effective_max_visits()  (existing)

config/__init__.py
└── clear_cache() → config.helpers._get_cfg.cache_clear()  (package-internal, no circular dep)

tests/conftest.py
├── TEST_STARTUP_TIMEOUT, TEST_QUERY_TIMEOUT  (new, eagerly resolved from config)
├── TEST_MAX_VISITS, TEST_NUM_THREADS  (new, eagerly resolved from config)
└── integration_engine fixture  (existing, now uses local constants)

model_paths.py → DELETED
tests/_model_paths.py → DELETED
```

## Design Decisions

### D1: Path constants in config/helpers.py
Path constants (`LAB_DIR`, `KATAGO_PATH`, `TSUMEGO_CFG`, `MODELS_DIR`) move into `config/helpers.py` because:
- They are computed from `Path(__file__).resolve().parent.parent` which works from config/ directory
- `config/__init__.py` already has `_LAB_DIR` computed the same way (line 57)
- `model_path()` needs MODELS_DIR — keeping them together avoids cross-module dependency
- Avoids creating a new file (YAGNI — rejected OPT-3)

### D2: Lazy config import inside _get_cfg()
```python
@lru_cache(maxsize=1)
def _get_cfg():
    from config import load_enrichment_config  # lazy import breaks cycle
    return load_enrichment_config()
```
This breaks the circular dependency at the model_paths→config direction. Since `_get_cfg()` now lives IN config/helpers.py, the import is actually config-internal (not cross-package), but keeping it lazy avoids import-order issues within the config package.

### D3: clear_cache() simplification
After decomposition, `clear_cache()` in `config/__init__.py` calls `config.helpers._get_cfg.cache_clear()` — this is a **package-internal** call, not a cross-package import. The `try/except ImportError` block is no longer needed. TEST_* global pop is also unnecessary since conftest resolves them eagerly at import time.

### D4: TEST_* as eager conftest constants
TEST_* values are resolved once at conftest import time (module level), not lazily via `__getattr__`. This is simpler and aligns with pytest conventions. Trade-off: `clear_cache()` cannot invalidate them mid-test — but test defaults don't change mid-run (they come from static config JSON), so this is acceptable.

### D5: sys.path manipulation stays in conftest.py
`conftest.py` already has `sys.path.insert(0, str(_LAB_DIR))` (lines 16-18). The sys.path manipulation in model_paths.py was redundant. After deletion, conftest.py remains the sole sys.path setup point for tests. Scripts that need sys.path (e.g., `scripts/diagnose_chase_puzzle.py`) already have their own sys.path setup.

### D6: run_calibration.py is out of scope
`scripts/run_calibration.py` has its own internal `_resolve_model_paths()` function (line 63) that is independent of `model_paths.py`. It does NOT import from `model_paths`. No changes needed.

### D7: scripts/_run_chase.py
The `scripts/_run_chase.py` script imports from model_paths and needs updating to `from config.helpers import ...`. It also has its own sys.path setup. Other scripts in `scripts/` (like `_diag_attacker.py`, `_diag_offline.py`) do NOT import from model_paths — they are out of scope.

## Risks and Mitigations

| risk_id | risk | probability | severity | mitigation |
|---|---|---|---|---|
| R-1 | Import typo in any of 20+ files | Low | Low | Mechanical regex replace; test suite catches immediately |
| R-2 | clear_cache() no longer invalidates model resolution | Low | Medium | _get_cfg lives in config/helpers.py; clear_cache() calls helpers._get_cfg.cache_clear() directly |
| R-3 | Conftest TEST_* stale after config reload | Very Low | Low | TEST_* are static config values; they are never reconfigured mid-run in tests. Only clear_cache() in parametrized config tests needs attention — those tests reload config, but TEST_* defaults are engine parameters, not config-under-test |
| R-4 | Scripts missing sys.path setup after model_paths.py deletion | Low | Low | Scripts already have their own sys.path setup. Verify each script has `sys.path.insert(0, str(LAB_DIR))` or equivalent |

## Documentation Plan

| doc_action | file | why_updated |
|---|---|---|
| files_to_update | `tools/puzzle-enrichment-lab/AGENTS.md` | Remove model_paths.py entry, add config/helpers.py model_path() entry |
| files_to_update | `tools/puzzle-enrichment-lab/config/helpers.py` | Module docstring update to reflect new responsibilities |
| files_to_update | `tools/puzzle-enrichment-lab/tests/conftest.py` | Docstring update to reflect TEST_* ownership |
| no_change | `docs/` | No user-facing docs affected — purely internal tool refactor |
