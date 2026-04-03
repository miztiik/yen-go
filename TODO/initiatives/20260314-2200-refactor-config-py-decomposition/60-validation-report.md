# Validation Report — config.py SRP Decomposition

> Initiative: `20260314-2200-refactor-config-py-decomposition`
> Last Updated: 2026-03-14

## Test Results

| val_id | Command | Exit Code | Result | Status |
|--------|---------|-----------|--------|--------|
| VAL-1 | `pytest tests/ -x --ignore=golden5,calibration,ai_solve_calibration` | 0 | 1894 passed, 36 skipped | ✅ |
| VAL-2 | Smoke test: `from config import load_enrichment_config; cfg = load_enrichment_config()` | 0 | OK: v1.17 | ✅ |
| VAL-3 | All config/ sub-module files ≤250 lines | — | Max: analysis.py at 248 | ✅ |
| VAL-4 | config.py monolith deleted | — | File does not exist | ✅ |
| VAL-5 | config/__init__.py exists | — | 208 lines | ✅ |
| VAL-6 | No circular imports | 0 | Config package imports cleanly | ✅ |
| VAL-7 | RC-1 fix: `from config.solution_tree import DepthProfile` | 0 | Import resolves correctly | ✅ |
| VAL-8 | RC-2 fix: `clear_teaching_cache()` encapsulation | 0 | `clear_cache()` calls teaching sub-module API | ✅ |
| VAL-9 | RC-3 fix: Dead import removed | 0 | No `_cached_teaching_comments` import in __init__ | ✅ |
| VAL-10 | Full test suite after RC fixes | 0 | 1894 passed, 36 skipped | ✅ |

## AC Verification

| ac_id | Criterion | Evidence | Status |
|-------|-----------|----------|--------|
| AC-1 | config.py deleted, config/ directory exists | `config.py` gone, 10 files in `config/` | ✅ verified |
| AC-2 | All 71 models importable from domain sub-module | Smoke test + full test suite pass | ✅ verified |
| AC-3 | Loaders importable from `config` (top-level) | `from config import load_enrichment_config, clear_cache, resolve_path` works | ✅ verified |
| AC-4 | All consumer import sites updated | Import rewrites in 27 source + test files; detectors + top-level unchanged (valid as-is) | ✅ verified |
| AC-5 | Full test suite passes | 1894 passed, 36 skipped, 0 failed | ✅ verified |
| AC-6 | No sub-module exceeds 250 lines | Max=248 (analysis.py), __init__=208 | ✅ verified |
| AC-7 | AGENTS.md updated | config.py → config/ package in directory structure and entity table | ✅ verified |
| AC-8 | No circular imports | Dependency DAG verified; only ai_solve → solution_tree cross-ref | ✅ verified |

## Line Count Summary

| file | lines | status |
|------|-------|--------|
| __init__.py | 208 | ✅ |
| ai_solve.py | 160 | ✅ |
| analysis.py | 248 | ✅ |
| difficulty.py | 236 | ✅ |
| helpers.py | 70 | ✅ |
| infrastructure.py | 89 | ✅ |
| refutations.py | 131 | ✅ |
| solution_tree.py | 200 | ✅ |
| teaching.py | 150 | ✅ |
| technique.py | 91 | ✅ |

## Ripple-Effects Validation

| impact_id | expected_effect | observed_effect | result | follow_up_task | status |
|-----------|-----------------|-----------------|--------|----------------|--------|
| R-1 | Detectors import EnrichmentConfig unchanged | All 29 detector files work via config/__init__ re-export | Match | — | ✅ verified |
| R-2 | Analyzer imports rewritten to sub-modules | 8 analyzer files rewritten, all pass | Match | — | ✅ verified |
| R-3 | Test imports rewritten to sub-modules | 19 test files rewritten, all pass | Match | — | ✅ verified |
| R-4 | config/katago-enrichment.json unchanged | JSON file not modified | Match | — | ✅ verified |
| R-5 | config/teaching-comments.json unchanged | JSON file not modified | Match | — | ✅ verified |
| R-6 | AGENTS.md updated | Updated directory structure + entity table | Match | — | ✅ verified |
| R-7 | engine/local_subprocess.py unchanged | Only imports load_enrichment_config, resolve_path (in __init__) | Match | — | ✅ verified |
| R-8 | scripts/run_calibration.py unchanged | Only imports from __init__ symbols | Match | — | ✅ verified |
| R-9 | backend/puzzle_manager/ unaffected | Separate config system, no changes | Match | — | ✅ verified |
| R-10 | Frontend unaffected | No dependency on Python config | Match | — | ✅ verified |
| R-11 | config_lookup.py _find_project_root() fix | Shadow detection: checks for config/tags.json instead of config/ dir | Match | — | ✅ verified |
| R-12 | RC-1: DepthProfile import in solve_position.py | `from config.solution_tree import DepthProfile` resolves correctly | Match | T43 | ✅ verified |
| R-13 | RC-2: clear_cache() encapsulation | Calls `clear_teaching_cache()` API instead of manipulating internal state | Match | T44 | ✅ verified |
| R-14 | RC-3: Dead import removed | No `_cached_teaching_comments` import in clear_cache() | Match | T45 | ✅ verified |

## Deviation Log

| dev_id | Deviation | Rationale | Impact |
|--------|-----------|-----------|--------|
| DEV-1 | `config_lookup.py::_find_project_root()` fixed to check `config/tags.json` instead of `config/` directory | New `config/` Python package shadowed the project root detection. Not caught in analysis. | Low — single-line fix, test_config_lookup now passes |
| DEV-2 | `__init__.py` trimmed to 208 lines (from initial 478) | Removed __all__ list and unnecessary re-exports. Only imports types needed for EnrichmentConfig composition. | Positive — well under AC-6 boundary |
| DEV-3 | Most detector + top-level imports unchanged | Imports like `from config import EnrichmentConfig` still work via __init__.py re-export | None — correct by design per plan |
