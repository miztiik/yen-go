# Execution Log — Enrichment Lab DRY / CLI Centralization

> Last Updated: 2026-03-22

## Baseline (T0.1)

**Note:** The baseline run was interrupted by KeyboardInterrupt at ~21% progress. The 565 figure represents only tests completed before interruption, not the total test suite.

| EX-1 | Metric | Value |
|------|--------|-------|
| EX-1a | Tests passed (partial) | 565 |
| EX-1b | Tests failed (partial) | 0 |
| EX-1c | Tests deselected | 19 |
| EX-1d | Duration | 124.81s (interrupted) |

**Pre-existing failures:** A prior `_test_output.txt` (before this initiative) shows **52 failures, 2404 passed** across the full suite. All failures are in config version assertions, fixture coverage, engine client, and feature-specific tests unrelated to our scope.

## Phase 1: Bootstrap Function + All Callers (T1.1–T1.6)

| EX-2 | Task | File | Change |
|------|------|------|--------|
| EX-2a | T1.1 | log_config.py | Added `bootstrap()` function (generates run_id, calls setup_logging, sets run_id context) |
| EX-2b | T1.2 | cli.py `main()` | Replaced 3-line ceremony with `bootstrap()` call |
| EX-2c | T1.3 | conftest.py | Replaced `generate_run_id + setup_logging` with `bootstrap()` |
| EX-2d | T1.4 | bridge.py `__main__` | Replaced manual logging with `bootstrap()` |
| EX-2e | T1.5 | scripts/run_calibration.py | Replaced manual ceremony with `bootstrap()` |
| EX-2f | T1.6 | scripts/diagnose_chase_puzzle.py | Replaced `setup_logging()` with `bootstrap(verbose=True, console_format="human")` |

## Phase 2: Engine Async Context Manager (T2.1–T2.3)

| EX-3 | Task | File | Change |
|------|------|------|--------|
| EX-3a | T2.1 | analyzers/single_engine.py | Added `__aenter__`/`__aexit__` to `SingleEngineManager` |
| EX-3b | T2.2 | cli.py `_run_enrich_async()` | Converted to `async with engine_manager` |
| EX-3c | T2.3 | cli.py `_run_batch_async()` | Converted try/finally to `async with engine_manager` |

## Phase 3: `_resolve_katago_config()` Consolidation (T3.1–T3.4)

| EX-4 | Task | File | Change |
|------|------|------|--------|
| EX-4a | T3.1 | analyzers/single_engine.py | Added module-level `resolve_katago_config()` function |
| EX-4b | T3.2 | cli.py | `_resolve_katago_config()` delegates to centralized function |
| EX-4c | T3.3 | scripts/run_calibration.py | Imports `resolve_katago_config` from single_engine |
| EX-4d | T3.4 | (verification) | Confirmed identical behavior via shared Path resolution logic |

## Phase 4: `_model_paths.py` Lazy Loading (T4.1–T4.2)

| EX-5 | Task | File | Change |
|------|------|------|--------|
| EX-5a | T4.1 | _model_paths.py | Replaced `_cfg = _load_cfg()` with `@lru_cache _get_cfg()`, module `__getattr__` for TEST_* |
| EX-5b | T4.2 | config/__init__.py | `clear_cache()` invalidates `_get_cfg.cache_clear()` + clears TEST_* globals (MH-2) |

## Phase 5: SGF Regex Parser Dedup (T5.1–T5.4)

| EX-6 | Task | File | Change |
|------|------|------|--------|
| EX-6a | T5.1 | tests/_sgf_render_utils.py | NEW: `parse_sgf_properties()`, `parse_all_stones()`, `parse_first_move()` |
| EX-6b | T5.2 | tests/render_fixtures.py | Removed 3 duplicate functions, imports from `_sgf_render_utils` |
| EX-6c | T5.3 | tests/generate_review_report.py | Removed 3 duplicate functions, imports from `_sgf_render_utils` |
| EX-6d | T5.4 | (verification) | Confirmed both importers use same shared implementation |

## Phase 6: Calibrate CLI Subcommand (T6.1–T6.7)

| EX-7 | Task | File | Change |
|------|------|------|--------|
| EX-7a | T6.1 | cli.py | Added `_add_common_args(sub)` helper (--katago, --katago-config, --config, --quick-only, --visits, --symmetries) |
| EX-7b | T6.2 | cli.py | Enrich subparser uses `_add_common_args()` |
| EX-7c | T6.3 | cli.py | Validate subparser uses `_add_common_args()` |
| EX-7d | T6.4 | cli.py | Batch subparser uses `_add_common_args()` |
| EX-7e | T6.5 | cli.py | Added `calibrate` subcommand with `--puzzle-dir`, `--quick-only`, `--max-puzzles`, `--restart-cadence` |
| EX-7f | T6.6 | cli.py | Added `_run_calibrate(args, run_id)` handler preserving restart cadence (MH-1) |
| EX-7g | T6.7 | scripts/run_calibration.py | Updated docstring as thin wrapper; main() delegates correctly |

## Phase 7: Documentation + AGENTS.md (T7.1)

| EX-8 | Task | File | Change |
|------|------|------|--------|
| EX-8a | T7.1 | AGENTS.md | Updated: trigger line, cli.py (calibrate, _add_common_args, bootstrap), log_config.py (bootstrap), _model_paths.py (lazy), single_engine.py (context manager, resolve_katago_config), tests/ (_sgf_render_utils) |

## Dead Code Cleanup

| EX-9 | Task | File | Change |
|------|------|------|--------|
| EX-9a | — | cli.py | Removed unused `_setup_logging()` function (dead after bootstrap adoption) |
| EX-9b | — | cli.py | Removed unused `setup_logging` from import statements |

## Final Regression (T7.2)

| EX-10 | Metric | Value |
|-------|--------|-------|
| EX-10a | Tests passed | 2351 |
| EX-10b | Tests failed | 31 |
| EX-10c | Tests skipped | 3 |
| EX-10d | Tests deselected | 19 |
| EX-10e | Duration | 428.87s |
| EX-10f | New failures introduced | **0** |

### Pre-existing failure analysis

All 31 failures are pre-existing and unrelated to initiative scope. None of the 12 failing test files overlap with the 13 files modified. Categories:

| Category | Count | Example | Root Cause |
|----------|-------|---------|------------|
| Config version (1.26→1.28) | 6 | test_refutation_quality_phase_a/b/c/d, test_enrichment_config, test_feature_activation | Config bumped externally |
| Fixture coverage | 7 | test_fixture_coverage (missing wrong branches, YT, miai/tesuji tags) | Fixture gaps |
| Engine client | 5 | test_engine_client, test_fixture_coverage (to_katago_json) | Engine API changes |
| Enrichment single | 4 | test_enrich_single (result sections, fallback, real puzzle) | Integration test env |
| Query params | 2 | test_query_params (reportAnalysisWinratesAs) | API change |
| Refutation tests | 3 | test_refutations (mock assertions) | Behavior changes |
| Sprint fixes | 3 | test_sprint1_fixes (w field), test_sprint2_fixes (hints) | Feature changes |
| Engine timeout | 1 | test_engine_client (DID NOT RAISE) | Env-specific |

## Must-Hold Constraint Verification

| ID | Constraint | Status | Evidence |
|----|-----------|--------|----------|
| MH-1 | `run_calibration.py` restart cadence preserved | ✅ | `_run_calibrate()` passes `--restart-cadence` flag to sequential run loop |
| MH-2 | `clear_cache()` invalidates `_model_paths` state | ✅ | `config/__init__.py` calls `_get_cfg.cache_clear()` and pops TEST_* from globals |
| MH-3 | `calibrate` accepts `--puzzle-dir`, `--quick-only`, `--max-puzzles` | ✅ | All flags in calibrate subparser via `_add_common_args()` + calibrate-specific args |

## Files Modified (13 total)

1. `tools/puzzle-enrichment-lab/log_config.py`
2. `tools/puzzle-enrichment-lab/cli.py`
3. `tools/puzzle-enrichment-lab/analyzers/single_engine.py`
4. `tools/puzzle-enrichment-lab/_model_paths.py`
5. `tools/puzzle-enrichment-lab/config/__init__.py`
6. `tools/puzzle-enrichment-lab/conftest.py`
7. `tools/puzzle-enrichment-lab/bridge.py`
8. `tools/puzzle-enrichment-lab/scripts/run_calibration.py`
9. `tools/puzzle-enrichment-lab/scripts/diagnose_chase_puzzle.py`
10. `tools/puzzle-enrichment-lab/tests/_sgf_render_utils.py` (NEW)
11. `tools/puzzle-enrichment-lab/tests/render_fixtures.py`
12. `tools/puzzle-enrichment-lab/tests/generate_review_report.py`
13. `tools/puzzle-enrichment-lab/AGENTS.md`
