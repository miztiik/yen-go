# Validation Report — Enrichment Lab DRY / CLI Centralization

> Last Updated: 2026-03-22

## Test Results

| VAL-1 | Command | Exit Code | Result |
|-------|---------|-----------|--------|
| VAL-1a | `python -B -m pytest tools/puzzle-enrichment-lab/tests/ -m "not slow" --ignore=...golden5/calibration/ai_solve -q --tb=short` | 1 | 2351 passed, 31 failed, 3 skipped, 19 deselected |
| VAL-1b | `get_errors` on all 13 modified files | 0 | No errors found (all files clean) |

## Pre-existing Failure Verification

| VAL-2 | Check | Result | Status |
|-------|-------|--------|--------|
| VAL-2a | Failing test files overlap with modified files | 0 overlap (12 failing test files vs 13 modified files) | ✅ verified |
| VAL-2b | Pre-existing `_test_output.txt` shows same failures | 52 failures (superset of current 31) before initiative | ✅ verified |
| VAL-2c | All 31 failures are config version, fixture, or engine API issues | All categorized, none relate to bootstrap/CM/config/lazy/dedup/calibrate | ✅ verified |

## Scope Compliance

| VAL-3 | Requirement | Result | Status |
|-------|------------|--------|--------|
| VAL-3a | probe_frame.py untouched | Not in modified files list | ✅ verified |
| VAL-3b | No new external dependencies | No pyproject.toml changes, only stdlib imports (functools.lru_cache) | ✅ verified |
| VAL-3c | AGENTS.md updated in same commit | Updated in Phase 7 | ✅ verified |

## Must-Hold Constraints

| VAL-4 | Constraint | Verification Method | Status |
|-------|-----------|-------------------|--------|
| VAL-4a | MH-1: restart cadence preserved | `_run_calibrate()` loops with `SingleEngineManager` restart at cadence interval | ✅ verified |
| VAL-4b | MH-2: clear_cache invalidates _model_paths | `config/__init__.py` calls `_get_cfg.cache_clear()` + pops TEST_* globals | ✅ verified |
| VAL-4c | MH-3: calibrate accepts required flags | Subparser has `--input-dir`, `--quick-only`, `--num-puzzles`, `--restart-every-n` | ✅ verified |

## Ripple Effects

| impact_id | expected_effect | observed_effect | result | follow_up_task | status |
|-----------|----------------|-----------------|--------|----------------|--------|
| R-1 | bootstrap() replaces manual ceremony in all 5 callers | All callers use bootstrap(), no manual generate_run_id+setup_logging left | Match | — | ✅ verified |
| R-2 | async with replaces try/finally in 2 functions | _run_enrich_async and _run_batch_async both use async with | Match | — | ✅ verified |
| R-3 | resolve_katago_config centralized, 2 callsites delegate | cli.py and run_calibration.py both import from single_engine | Match | — | ✅ verified |
| R-4 | _model_paths lazy loading backward-compatible | from _model_paths import TEST_STARTUP_TIMEOUT still works via __getattr__ | Match | — | ✅ verified |
| R-5 | _sgf_render_utils shared by 2 consumers | render_fixtures.py and generate_review_report.py both import from shared | Match | — | ✅ verified |
| R-6 | Dead code _setup_logging removed | Function removed, imports cleaned | Match | — | ✅ verified |
| R-7 | calibrate subcommand accessible via CLI | Subparser registered with handler function | Match | — | ✅ verified |
