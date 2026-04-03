# Research Brief: Enrichment Lab DRY/CLI Centralization

**Last Updated**: 2026-03-21  
**Initiative**: `20260321-2100-refactor-enrichment-lab-dry-cli-centralization`  
**Status**: research_completed

---

## 1. Research Question and Boundaries

**Primary question**: What existing patterns, caches, and abstractions in the enrichment lab and backend pipeline can be leveraged to DRY-ify logging setup, config loading, engine lifecycle, and SGF parsing — without regressions?

**Boundaries**:
- Scope: `tools/puzzle-enrichment-lab/` only (all Python files)
- Excluded: `probe_frame.py`, `probe_frame_gp.py` (per constraint)
- No new external dependencies
- `bridge.py` must remain a functional HTTP server
- Scripts must remain independently runnable

---

## 2. Internal Code Evidence

### 2.1 Bootstrap Pattern (Q1)

| Ref | File | Lines | Pattern |
|-----|------|-------|---------|
| R-1 | `backend/puzzle_manager/__main__.py` | L1–15 | Thin shim: `from .cli import main; sys.exit(main())` |
| R-2 | `backend/puzzle_manager/cli.py` | L1815–1870 | `main()` calls `setup_logging(level=)` then dispatches subcommand via `if/elif` chain |
| R-3 | `backend/puzzle_manager/pm_logging.py` | L1–60 | Structured logging with `FlushingFileHandler`, run_id correlation, custom DETAIL level, separate stage log files. Clean `setup_logging(level=)` entry point. |
| R-4 | `tools/puzzle-enrichment-lab/cli.py` | L830–907 | `main()` generates `run_id` → `_setup_logging()` → dispatches subcommand. Near-identical ceremony to backend. |
| R-5 | `tools/puzzle-enrichment-lab/log_config.py` | L305–450 | Already centralized `setup_logging(run_id=, verbose=, log_dir=, console_format=)` with JSON/human formatters, file rotation, namespace filter, trace context injection. |

**Finding**: The enrichment lab already has a centralized `log_config.setup_logging()`. The duplication is in **callers** that each repeat the ceremony of `generate_run_id() → setup_logging() → set_run_id()`. The backend's `main()` is a good template — it calls `setup_logging(level=)` once and dispatches.

### 2.2 Engine Context Manager (Q2)

| Ref | File | Lines | Lifecycle Pattern |
|-----|------|-------|-------------------|
| R-6 | `analyzers/single_engine.py` | L121–132 | **No `__aenter__`/`__aexit__`** — only `start()` and `shutdown()` async methods |
| R-7 | `cli.py::_run_enrich_async()` | L270–282 | `try: await engine_manager.start() ... finally: await engine_manager.shutdown()` |
| R-8 | `cli.py::run_batch() → _run_batch_async()` | L395–470 | Same try/finally: `start()` ... loop ... `shutdown()` in finally |
| R-9 | `bridge.py::_lifespan()` | L80–110 | `asynccontextmanager` wrapping engine shutdown in the `yield` pattern for FastAPI |
| R-10 | `scripts/run_calibration.py::_run_all_puzzles()` | L350–430 | Same try/finally. Also has engine restart logic (`_create_engine()` factory, restart every N puzzles) |
| R-11 | `scripts/diagnose_chase_puzzle.py::run_pipeline()` | L190–220 | Same try/finally: `start()` → `enrich` → `shutdown()` |

**Finding**: There are **3 distinct engine lifecycle duplications** (cli batch/validate, run_calibration, diagnose_chase). All use identically-shaped `try/finally`. `SingleEngineManager` does NOT have `__aenter__`/`__aexit__` — adding them would be a clean, backward-compatible change. The bridge.py already uses its own `asynccontextmanager` for FastAPI lifespan, which could remain separate.

### 2.3 Config Caching (Q3)

| Ref | File | Lines | Pattern |
|-----|------|-------|---------|
| R-12 | `config/__init__.py` | L105–107 | Module-level `_cached_config: Optional[EnrichmentConfig] = None` — singleton on default path |
| R-13 | `config/__init__.py` | L120–155 | `load_enrichment_config(path=None)` returns cached if `path is None` and cache exists; only caches when path == default |
| R-14 | `config/__init__.py` | L162–172 | `clear_cache()` resets `_cached_config`, `_cached_levels`, `_cached_tag_ids` AND teaching comments cache |
| R-15 | `_model_paths.py` | L37–39 | **Eagerly loads at import time**: `_cfg = _load_cfg()` at module level — executes config I/O on import |
| R-16 | `estimate_difficulty.py` | multiple | Calls `load_enrichment_config()` **7 times** across different functions — but each hits the cache after first call |

**Finding**: The caching mechanism is already functional and correct. The `_model_paths.py` eager import (R-15) is the main risk: it loads config on import, which means any import of `_model_paths` triggers file I/O. Making it lazy (e.g., `functools.lru_cache` or property) would defer I/O to first use. **Risk**: Tests import `_model_paths` via `conftest.py` (R-16 in tests/conftest.py L24). A lazy approach would only change WHEN config loads, not IF — so test behavior should be unchanged. `clear_cache()` would need no changes since `_model_paths` would just call `load_enrichment_config()` which already respects the cache.

### 2.4 SGF Parser (Q4)

| Ref | File | Lines | Pattern |
|-----|------|-------|---------|
| R-17 | `core/tsumego_analysis.py::parse_sgf()` | L37–45 | Returns `SGFNode` (KaTrain tree). Has `extract_position()`, `extract_correct_first_move()`. Full API. |
| R-18 | `tests/render_fixtures.py` | L20–65 | Regex parser: `parse_sgf_properties()`, `parse_all_stones()`, `parse_first_move()` — standalone, no KaTrain dependency |
| R-19 | `tests/generate_review_report.py` | L90–130 | **Exact copy** of the same 3 regex functions from `render_fixtures.py`, plus SVG rendering |

**Finding**: `render_fixtures.py` and `generate_review_report.py` share identical regex SGF parsers (copy-paste). Both are standalone utilities (`__test__ = False`), not test modules. `core/tsumego_analysis.parse_sgf()` returns a KaTrain `SGFNode` tree with full stone extraction. **Drop-in replacement?** Not quite — the regex parsers return `list[tuple[int,int]]` (x,y coords), while `extract_position()` returns a `Position` with `Stone` objects. A thin adapter (`position.stones → [(s.x, s.y)]`) would bridge the gap. Both scripts already import from the lab root (via `sys.path.insert`), so there's no import barrier. The regex approach is ~10 lines simpler but fragile; the KaTrain parser handles edge cases (escaped brackets, multi-value properties).

### 2.5 Test Infrastructure (Q5)

| Ref | File | Lines | Pattern |
|-----|------|-------|---------|
| R-20 | `conftest.py` (lab root) | L1–52 | `pytest_configure()` calls `setup_logging(run_id=, verbose=, console_format="human", log_dir=)` — single centralized logging init for all tests |
| R-21 | `tests/conftest.py` | L1–80 | Imports `_model_paths` for `KATAGO_PATH`, `TSUMEGO_CFG`, `model_path()`, test defaults. Provides `integration_engine` fixture (module-scoped, starts/shuts down `LocalEngine` directly) |
| R-22 | `tests/conftest.py` | L44–80 | `integration_engine` fixture creates `EngineConfig` + `LocalEngine` directly — does NOT use `SingleEngineManager`, bypasses config/engine-manager layer |

**Finding**: Test logging is already centralized (R-20). The test `integration_engine` fixture (R-22) uses `LocalEngine` directly, not `SingleEngineManager`. This is intentional — tests test the engine at a lower level. If we add `__aenter__`/`__aexit__` to `SingleEngineManager`, the test fixture would NOT need changes. The lab root `conftest.py` is the single place where test logging is initialized — no per-test-file logging setup.

### 2.6 Script Categorization (Q6)

| Ref | Script | Type | Uses KataGo? | Logging? | Config? | Production? | CLI Subcommand Candidate? |
|-----|--------|------|-------------|----------|---------|-------------|---------------------------|
| R-23 | `scripts/run_calibration.py` | Production workflow | Yes (engine) | `setup_logging()` | `load_enrichment_config()` x2 | **Yes** — core calibration | Yes — `cli.py calibrate` |
| R-24 | `scripts/analyze_batch.py` | One-off analysis | No (reads JSON output) | None | None | No — reads Phase R results | No — keep standalone |
| R-25 | `scripts/diagnose_chase_puzzle.py` | Debug/diagnostic | Yes (engine) | `setup_logging()` | `load_enrichment_config()` | No — dev-only diagnostic | No — keep standalone |
| R-26 | `scripts/show_frame.py` | Debug visualization | No | None | None | No — visual inspection | No — keep standalone |
| R-27 | `scripts/download_models.py` | Setup tool | No | None | `load_enrichment_config()` | **Yes** — setup | Possible but low value |
| R-28 | `scripts/prepare_calibration_fixtures.py` | Setup tool | No | None | None | **Yes** — fixture prep | No — infrequent, standalone OK |
| R-29 | `scripts/hydrate_calibration_fixtures.py` | Setup tool | No | None | None | **Yes** — fixture prep | No — infrequent, standalone OK |
| R-30 | `scripts/measure_enrichment_quality.py` | Quality measurement | No | None | None | **Yes** — analysis | Possible — `cli.py measure` |
| R-31 | `scripts/probe_frame.py` | Debug (EXCLUDED) | No | — | — | — | — |
| R-32 | `scripts/probe_frame_gp.py` | Debug (EXCLUDED) | No | — | — | — | — |
| R-33 | `tests/render_fixtures.py` | Utility (not a test) | No | None | None | No | No |
| R-34 | `tests/generate_review_report.py` | Utility (not a test) | No | None | `load_enrichment_config()` | **Yes** — expert review | Possible — `cli.py report` |
| R-35 | `render_debug.py` | One-off debug | No | None | None | No | No |

**Finding**: Only `run_calibration.py` is a strong candidate for CLI subcommand absorption. `measure_enrichment_quality.py` and `generate_review_report.py` are good secondary candidates. The remaining scripts (show_frame, diagnose_chase, prepare/hydrate fixtures, analyze_batch, download_models, render_debug) are either debug tools, one-off utilities, or setup scripts that benefit from standalone operation.

---

## 3. External References

| Ref | Source | Pattern | Relevance |
|-----|--------|---------|-----------|
| E-1 | Python `contextlib.asynccontextmanager` | Standard library pattern for async resource management | Direct match for engine lifecycle DRY |
| E-2 | Python `__aenter__`/`__aexit__` protocol | Standard async context manager protocol (PEP 492) | Can add to `SingleEngineManager` without breaking existing code |
| E-3 | Click/Typer CLI frameworks | Subcommand grouping with shared options | Backend uses argparse; enrichment lab already uses argparse. No benefit from switching. |
| E-4 | `functools.lru_cache` / `functools.cached_property` | Standard lazy initialization patterns | Applicable to `_model_paths.py` eager loading |

---

## 4. Candidate Adaptations for Yen-Go

### Adaptation A: Bootstrap Ceremony DRY

**Current**: 4 entry points repeat `generate_run_id() → setup_logging() → set_run_id()`:
- `cli.py::main()` (L830–835)
- `bridge.py::__main__` (L507–515)
- `scripts/run_calibration.py::main()` (L624–626)
- `conftest.py::pytest_configure()` (L41–52)

**Proposal**: Create `bootstrap(*, verbose=False, log_dir=None, console_format="json") → str` in `log_config.py` that wraps the 3-call ceremony and returns `run_id`. Each entry point reduces to one line.

**Risk**: Low. All callers already use these three functions.

### Adaptation B: Engine Async Context Manager

**Current**: 3+ copies of `try: await mgr.start() ... finally: await mgr.shutdown()`.

**Proposal**: Add `__aenter__`/`__aexit__` to `SingleEngineManager`:
```python
async def __aenter__(self):
    await self.start()
    return self
    
async def __aexit__(self, *exc_info):
    await self.shutdown()
```

Callers become: `async with SingleEngineManager(config, ...) as engine:`. Existing `start()`/`shutdown()` remain for bridge.py's long-lived singleton.

**Risk**: Low. Additive change. Bridge.py can continue using explicit start/shutdown.

### Adaptation C: _model_paths.py Lazy Loading

**Current**: `_cfg = _load_cfg()` at module level (L39) — executes config file I/O on import.

**Proposal**: Wrap in a lazy accessor:
```python
@functools.lru_cache(maxsize=1)
def _get_cfg():
    return _load_cfg()
```
Then replace `_cfg` references with `_get_cfg()`.

**Risk**: Low. Config is already cached internally. `clear_cache()` won't invalidate `lru_cache` — but `_model_paths` values are constant for a process lifetime per test process anyway. If cache invalidation is needed, use `_get_cfg.cache_clear()`.

### Adaptation D: SGF Regex Parser Dedup

**Current**: `render_fixtures.py` and `generate_review_report.py` have identical `parse_all_stones()`, `parse_first_move()`, `parse_sgf_properties()`.

**Proposal**: Two options:
1. **Extract shared module**: Move regex parsers to a `tests/_sgf_render_utils.py` helper, import from both scripts.
2. **Replace with KaTrain parser**: Use `core/tsumego_analysis.parse_sgf()` + `extract_position()` with a thin adapter. More robust but heavier import chain.

**Recommendation**: Option 1 (extract shared module). These are visualization utilities, not production code. A regex parser is simpler and sufficient for rendering boards. Adding a KaTrain dependency to standalone scripts increases coupling unnecessarily.

**Risk**: Low. Both files are standalone utilities (`__test__ = False`), not test modules.

### Adaptation E: CLI Subcommand Absorption (run_calibration)

**Current**: `scripts/run_calibration.py` is a 700-line standalone script with its own argparse, logging, config loading, and engine lifecycle.

**Proposal**: Add `calibrate` subcommand to `cli.py` that delegates to `run_calibration.run_calibration()`. Keep `scripts/run_calibration.py` as a standalone entry point that calls through to `cli.py calibrate`.

**Risk**: Medium. `run_calibration.py` has complex restart logic (R-10) and config override resolution. The function signature is already clean (`run_calibration(sgf_files, ...)`) so wiring it as a subcommand is mechanically straightforward, but the argparse surface is large.

---

## 5. Risks, License/Compliance, and Rejection Reasons

| Ref | Risk | Severity | Mitigation |
|-----|------|----------|------------|
| K-1 | `_model_paths.py` lazy loading could change test import timing | Low | Config is already cached; lazy just defers first I/O. Run existing tests to verify. |
| K-2 | Adding `__aenter__`/`__aexit__` to SingleEngineManager could conflict with bridge.py singleton pattern | Low | Bridge uses explicit `start()`/`shutdown()` — async CM is additive, not replacing. |
| K-3 | CLI subcommand absorption increases `cli.py` complexity | Medium | Only absorb `run_calibration`; keep others standalone. |
| K-4 | SGF regex parser extraction could break if imports aren't set up correctly | Low | Both scripts already add lab root to `sys.path`. |
| K-5 | Bootstrap DRY could mask errors if `setup_logging()` changes signature | Low | `setup_logging()` API is stable and tested. |
| K-6 | Constraint: `bridge.py` must remain a functional HTTP server | N/A | All proposals preserve bridge.py's architecture (FastAPI lifespan, explicit engine management). |

**License**: No new dependencies. All changes use Python stdlib (`contextlib`, `functools`).

**Rejection reasons for considered alternatives**:
- **Full CLI framework switch (Click/Typer)**: Rejected. Backend uses argparse; consistency outweighs marginal ergonomic gains. Would require touching all test stubs.
- **Global engine singleton module**: Rejected. Engine lifecycle is per-task, not per-process. Bridge.py's singleton is the exception, not the rule.
- **Replacing regex parsers with KaTrain for render utilities**: Rejected for primary recommendation. Overengineering for visualization scripts that work correctly.

---

## 6. Planner Recommendations

1. **Bootstrap DRY (Adaptation A)**: Add a `bootstrap()` convenience in `log_config.py`. Estimated 4 files touched, ~20 lines net reduction. **Recommend first** — lowest risk, highest consistency gain.

2. **Engine Async Context Manager (Adaptation B)**: Add `__aenter__`/`__aexit__` to `SingleEngineManager`. 1 file changed, 3+ callers simplified. **Recommend second** — clean Python pattern, backward-compatible.

3. **SGF Regex Dedup (Adaptation D, Option 1)**: Extract `tests/_sgf_render_utils.py`. 3 files touched. **Recommend third** — eliminates the most obvious copy-paste duplication.

4. **_model_paths.py Lazy Loading (Adaptation C)**: Convert to `lru_cache`. 1 file changed. **Optional** — current eager loading works fine, lazy is a nice-to-have.

5. **CLI Subcommand (Adaptation E)**: Absorb `run_calibration` into `cli.py calibrate`. **Defer** — high effort, medium value. The standalone script works and is well-structured.

---

## 7. Confidence and Risk Update

| Metric | Value |
|--------|-------|
| `post_research_confidence_score` | 88 |
| `post_research_risk_level` | low |

**Confidence rationale**: All source files read in full; all patterns verified with line numbers. The codebase already has the right abstractions (`log_config.setup_logging`, `config.__init__.load_enrichment_config` with caching, `SingleEngineManager`). The DRY gaps are in callers, not in the abstractions themselves.

**Risk rationale**: All recommended changes are additive or refactor-only. No public API changes, no new dependencies, no architectural shifts. The highest-risk item (CLI absorption) is deferred.

---

> **See also**:
> - [00-charter.md](00-charter.md) — Initiative charter
> - [10-clarifications.md](10-clarifications.md) — Clarification questions
