# Plan — Enrichment Lab DRY / CLI Centralization (OPT-3)

> Last Updated: 2026-03-21  
> Selected Option: OPT-3 (Hybrid Bootstrap + Targeted CLI Absorption)  
> Correction Level: Level 3 (Multiple Files)

---

## Architecture Decisions

### AD-1: Bootstrap Function Location
**Decision:** Add `bootstrap()` to `log_config.py` (not a new file).  
**Rationale:** `log_config.py` already owns `setup_logging()`, `generate_run_id()`, and `set_run_id()`. Placing `bootstrap()` here keeps the logging ceremony cohesive (SRP). No new module needed.

**Signature:**
```python
def bootstrap(
    *,
    verbose: bool = False,
    log_dir: Path | str | None = None,
    console_format: str = "json",
) -> str:
    """Initialize enrichment lab: generate run_id, setup logging, set run_id context.
    
    Returns the generated run_id.
    """
    run_id = generate_run_id()
    setup_logging(run_id=run_id, verbose=verbose, log_dir=log_dir, console_format=console_format)
    set_run_id(run_id)
    return run_id
```

### AD-2: Engine Async Context Manager Protocol
**Decision:** Add `__aenter__`/`__aexit__` directly to `SingleEngineManager`.  
**Rationale:** Standard PEP 492 protocol. Additive — existing `start()`/`shutdown()` callers are unaffected. Bridge.py singleton continues using explicit lifecycle.

```python
async def __aenter__(self) -> "SingleEngineManager":
    await self.start()
    return self

async def __aexit__(self, *exc_info) -> None:
    await self.shutdown()
```

### AD-3: `_resolve_katago_config()` Consolidation
**Decision:** Move to `analyzers/single_engine.py` as a module-level function.  
**Rationale:** `SingleEngineManager` is the consumer. Follows "closest to usage" principle. Both `cli.py` and `run_calibration.py` import from here.

### AD-4: `_model_paths.py` Lazy Loading
**Decision:** Replace module-level `_cfg = _load_cfg()` with `@functools.lru_cache` getter `_get_cfg()`. Keep path constants (`LAB_DIR`, `KATAGO_PATH`, `MODELS_DIR`, `TSUMEGO_CFG`) eager since they're pure path computations.  
**Must-Hold (MH-2):** `clear_cache()` in `config/__init__.py` must also call `_get_cfg.cache_clear()` (or import and invalidate).

### AD-5: SGF Regex Parser Dedup
**Decision:** Extract shared functions to `tests/_sgf_render_utils.py`. Both `render_fixtures.py` and `generate_review_report.py` import from it.  
**Rationale:** These are visualization utilities, not production code. Keeping regex is simpler than adding KaTrain dependency to render scripts. Dedup is the priority, not technology change.

### AD-6: Calibrate CLI Subcommand
**Decision:** Add `calibrate` subcommand to `cli.py`. `scripts/run_calibration.py` becomes a thin wrapper calling `cli.py calibrate` logic.  
**Must-Hold (MH-1):** Preserve exact engine restart cadence (restart every N puzzles).  
**Must-Hold (MH-3):** Use same flag names as `enrich/batch` (`--katago`, `--config`, `--verbose`, `--log-dir`).

### AD-7: Shared Argparse Builder
**Decision:** Extract `_add_common_args(parser)` helper to avoid duplicating `--verbose`, `--log-dir` argument definitions.  
**Location:** In `cli.py` (internal helper, not a separate module).

---

## Data Model Impact

**None.** No data models, schemas, config formats, or database schemas are modified. This is a pure structural refactor of calling conventions.

---

## Contracts / Interfaces

### New Public Interface: `log_config.bootstrap()`
- **Signature:** `bootstrap(*, verbose=False, log_dir=None, console_format="json") -> str`
- **Returns:** Generated `run_id` string
- **Side effects:** Configures Python logging, sets run_id context

### Modified Interface: `SingleEngineManager`
- **Addition:** `__aenter__`, `__aexit__` (async context manager protocol)
- **Existing `start()`, `shutdown()`:** Unchanged, still callable directly

### Moved Interface: `resolve_katago_config()`
- **From:** `cli.py` L90 + `scripts/run_calibration.py` L73
- **To:** `analyzers/single_engine.py` (module-level function)
- **Signature unchanged**

---

## Risks & Mitigations

| Risk | Severity | Phase | Mitigation |
|------|----------|-------|------------|
| `_model_paths.py` lazy load changes test import timing | Low | Phase 4 | Config is cached; only WHEN changes, not IF. Run full test suite after. |
| `clear_cache()` doesn't invalidate `_model_paths` lru_cache | Medium | Phase 4 | MH-2: Explicit `_get_cfg.cache_clear()` call in `clear_cache()`. Test with `clear_cache()` + re-import. |
| Calibrate subcommand loses restart cadence | Medium | Phase 6 | MH-1: Directly reuse `_run_all_puzzles()` from run_calibration, not re-implement. Verify with calibration test. |
| Argparse conflicts in cli.py | Low | Phase 6 | Use parent parser pattern with `add_argument_group()`. |
| Bridge.py bootstrap breaks FastAPI lifespan | Low | Phase 1 | Bootstrap for logging only; engine lifecycle stays in `_lifespan()`. |

---

## Phased Execution Plan

### Phase 1: Bootstrap Function + All Callers
**Files:** `log_config.py`, `cli.py`, `bridge.py`, `conftest.py`, `scripts/run_calibration.py`, `scripts/diagnose_chase_puzzle.py`  
**Risk:** Low  
**Gate:** Full regression test suite before + after

### Phase 2: Engine Async Context Manager
**Files:** `analyzers/single_engine.py`, `cli.py` (enrich/validate/batch callers)  
**Risk:** Low  
**Gate:** Full regression test suite before + after

### Phase 3: `_resolve_katago_config()` Consolidation
**Files:** `analyzers/single_engine.py`, `cli.py`, `scripts/run_calibration.py`  
**Risk:** Low  
**Gate:** Full regression test suite before + after

### Phase 4: `_model_paths.py` Lazy Loading
**Files:** `_model_paths.py`, `config/__init__.py` (clear_cache update)  
**Risk:** Low  
**Gate:** Full regression test suite before + after. Extra: verify `clear_cache()` + `_model_paths` interaction.

### Phase 5: SGF Regex Parser Dedup
**Files:** `tests/_sgf_render_utils.py` (new), `tests/render_fixtures.py`, `tests/generate_review_report.py`  
**Risk:** Low  
**Gate:** Full regression test suite before + after

### Phase 6: Calibrate CLI Subcommand
**Files:** `cli.py`, `scripts/run_calibration.py`  
**Risk:** Medium  
**Gate:** Full regression test suite before + after. Extra: verify calibration-specific test (if any non-slow tests exist).

### Phase 7: AGENTS.md + Documentation Update
**Files:** `AGENTS.md`  
**Risk:** None  
**Gate:** Documentation review

---

## Documentation Plan

| doc_id | Action | File | Why |
|--------|--------|------|-----|
| DOC-1 | Update | `tools/puzzle-enrichment-lab/AGENTS.md` | Structural changes: new bootstrap(), context manager, moved functions, lazy loading |
| DOC-2 | Update (if needed) | `15-research.md` | Record final implementation notes |

### Cross-references
- [Charter](./00-charter.md) — Scope and constraints
- [Options](./25-options.md) — Selected OPT-3
- [Governance](./70-governance-decisions.md) — Panel decisions
- [Tasks](./40-tasks.md) — Execution checklist

> **See also:**
> - [Analysis](./20-analysis.md) — Ripple effects and coverage
