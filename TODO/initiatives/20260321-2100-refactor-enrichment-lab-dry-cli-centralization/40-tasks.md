# Tasks — Enrichment Lab DRY / CLI Centralization (OPT-3)

> Last Updated: 2026-03-21  
> Selected Option: OPT-3 (Hybrid Bootstrap + Targeted CLI Absorption)

---

## Pre-Implementation

| ID | Task | Status | Depends | Parallel | Files |
|----|------|--------|---------|----------|-------|
| T0.1 | Run baseline regression test suite and record results | not-started | — | — | (test output) |
| T0.2 | Create clean git commit of current state | not-started | T0.1 | — | (all enrichment lab files) |

---

## Phase 1: Bootstrap Function + All Callers

| ID | Task | Status | Depends | Parallel | Files |
|----|------|--------|---------|----------|-------|
| T1.1 | Add `bootstrap()` function to `log_config.py` | not-started | T0.2 | — | `log_config.py` |
| T1.2 | Update `cli.py` to use `bootstrap()` instead of manual ceremony | not-started | T1.1 | [P] | `cli.py` |
| T1.3 | Update `bridge.py` to use `bootstrap()` for logging init | not-started | T1.1 | [P] | `bridge.py` |
| T1.4 | Update root `conftest.py` to use `bootstrap()` | not-started | T1.1 | [P] | `conftest.py` |
| T1.5 | Update `scripts/run_calibration.py` to use `bootstrap()` | not-started | T1.1 | [P] | `scripts/run_calibration.py` |
| T1.6 | Update `scripts/diagnose_chase_puzzle.py` to use `bootstrap()` | not-started | T1.1 | [P] | `scripts/diagnose_chase_puzzle.py` |
| T1.7 | Run regression test suite — verify zero failures vs baseline | not-started | T1.2–T1.6 | — | (test output) |
| T1.8 | Phase 1 governance review | not-started | T1.7 | — | — |

---

## Phase 2: Engine Async Context Manager

| ID | Task | Status | Depends | Parallel | Files |
|----|------|--------|---------|----------|-------|
| T2.1 | Add `__aenter__`/`__aexit__` to `SingleEngineManager` | not-started | T1.8 | — | `analyzers/single_engine.py` |
| T2.2 | Update `cli.py` enrich/validate to use `async with SingleEngineManager(...)` | not-started | T2.1 | [P] | `cli.py` |
| T2.3 | Update `cli.py` batch to use `async with SingleEngineManager(...)` | not-started | T2.1 | [P] | `cli.py` |
| T2.4 | Run regression test suite — verify zero failures vs baseline | not-started | T2.2–T2.3 | — | (test output) |
| T2.5 | Phase 2 governance review | not-started | T2.4 | — | — |

Note: `bridge.py` keeps explicit `start()`/`shutdown()` — its FastAPI `_lifespan()` context manager is different and correct as-is. `scripts/run_calibration.py` keeps explicit lifecycle due to restart-every-N logic — will be addressed in Phase 6.

---

## Phase 3: `_resolve_katago_config()` Consolidation

| ID | Task | Status | Depends | Parallel | Files |
|----|------|--------|---------|----------|-------|
| T3.1 | Move `_resolve_katago_config()` to `analyzers/single_engine.py` | not-started | T2.5 | — | `analyzers/single_engine.py` |
| T3.2 | Update `cli.py` to import from `single_engine` | not-started | T3.1 | [P] | `cli.py` |
| T3.3 | Update `scripts/run_calibration.py` to import from `single_engine` | not-started | T3.1 | [P] | `scripts/run_calibration.py` |
| T3.4 | Delete duplicate function from `cli.py` and `run_calibration.py` | not-started | T3.2–T3.3 | — | `cli.py`, `scripts/run_calibration.py` |
| T3.5 | Run regression test suite — verify zero failures vs baseline | not-started | T3.4 | — | (test output) |
| T3.6 | Phase 3 governance review | not-started | T3.5 | — | — |

---

## Phase 4: `_model_paths.py` Lazy Loading

| ID | Task | Status | Depends | Parallel | Files |
|----|------|--------|---------|----------|-------|
| T4.1 | Convert `_model_paths.py` config loading to `@lru_cache` pattern | not-started | T3.6 | — | `_model_paths.py` |
| T4.2 | Add `_model_paths._get_cfg.cache_clear()` call to `config/__init__.py::clear_cache()` (MH-2) | not-started | T4.1 | — | `config/__init__.py` |
| T4.3 | Run regression test suite — verify zero failures vs baseline | not-started | T4.2 | — | (test output) |
| T4.4 | Verify `clear_cache()` + `_model_paths` interaction | not-started | T4.2 | [P] | (manual verification) |
| T4.5 | Phase 4 governance review | not-started | T4.3–T4.4 | — | — |

---

## Phase 5: SGF Regex Parser Dedup

| ID | Task | Status | Depends | Parallel | Files |
|----|------|--------|---------|----------|-------|
| T5.1 | Create `tests/_sgf_render_utils.py` with shared `parse_sgf_properties()`, `parse_all_stones()`, `parse_first_move()` | not-started | T4.5 | — | `tests/_sgf_render_utils.py` (new) |
| T5.2 | Update `tests/render_fixtures.py` to import from `_sgf_render_utils` | not-started | T5.1 | [P] | `tests/render_fixtures.py` |
| T5.3 | Update `tests/generate_review_report.py` to import from `_sgf_render_utils` | not-started | T5.1 | [P] | `tests/generate_review_report.py` |
| T5.4 | Delete duplicate functions from both files | not-started | T5.2–T5.3 | — | `tests/render_fixtures.py`, `tests/generate_review_report.py` |
| T5.5 | Run regression test suite — verify zero failures vs baseline | not-started | T5.4 | — | (test output) |
| T5.6 | Phase 5 governance review | not-started | T5.5 | — | — |

---

## Phase 6: Calibrate CLI Subcommand

| ID | Task | Status | Depends | Parallel | Files |
|----|------|--------|---------|----------|-------|
| T6.1 | Add `_add_common_args(parser)` helper to `cli.py` for shared flags | not-started | T5.6 | — | `cli.py` |
| T6.2 | Refactor existing subcommands to use `_add_common_args()` | not-started | T6.1 | — | `cli.py` |
| T6.3 | Add `calibrate` subcommand to `cli.py` argparse | not-started | T6.2 | — | `cli.py` |
| T6.4 | Wire calibrate handler calling `run_calibration` core logic (MH-1: preserve restart cadence) | not-started | T6.3 | — | `cli.py` |
| T6.5 | Convert `scripts/run_calibration.py` to thin wrapper calling CLI calibrate | not-started | T6.4 | — | `scripts/run_calibration.py` |
| T6.6 | Verify calibrate subcommand uses same flag names as enrich/batch (MH-3) | not-started | T6.4 | — | (review) |
| T6.7 | Update `scripts/run_calibration.py` to use `bootstrap()` for its thin wrapper | not-started | T6.5 | — | `scripts/run_calibration.py` |
| T6.8 | Run regression test suite — verify zero failures vs baseline | not-started | T6.7 | — | (test output) |
| T6.9 | Phase 6 governance review | not-started | T6.8 | — | — |

---

## Phase 7: Documentation + AGENTS.md

| ID | Task | Status | Depends | Parallel | Files |
|----|------|--------|---------|----------|-------|
| T7.1 | Update `AGENTS.md` with structural changes (bootstrap, engine CM, moved functions, lazy loading, new CLI subcommand) | not-started | T6.9 | — | `AGENTS.md` |
| T7.2 | Run final regression test suite — confirm zero failures vs baseline | not-started | T7.1 | — | (test output) |
| T7.3 | Final governance review (plan mode) | not-started | T7.2 | — | — |

---

## Summary

| Phase | Tasks | Files Modified | Risk | Gate |
|-------|-------|---------------|------|------|
| 0 (Pre) | 2 | 0 | None | Baseline recorded |
| 1 (Bootstrap) | 8 | 6 | Low | Regression + governance |
| 2 (Engine CM) | 5 | 2 | Low | Regression + governance |
| 3 (Config resolve) | 6 | 3 | Low | Regression + governance |
| 4 (Lazy _model_paths) | 5 | 2 | Low | Regression + cache test + governance |
| 5 (SGF dedup) | 6 | 3 (1 new) | Low | Regression + governance |
| 6 (Calibrate CLI) | 9 | 2 | Medium | Regression + governance |
| 7 (Docs) | 3 | 1 | None | Final governance |
| **Total** | **44** | **~12 unique files** | **Low-Medium** | **7 regression gates + 7 governance gates** |

> **See also:**
> - [Plan](./30-plan.md) — Architecture decisions
> - [Analysis](./20-analysis.md) — Impact analysis (pending)
> - [Governance](./70-governance-decisions.md) — Panel decisions
