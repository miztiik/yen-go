# Validation Report — Enrichment Quality Regression Fix

**Initiative**: `20260319-2100-feature-enrichment-quality-regression-fix`
**Date**: 2026-03-19

## Test Results

| val_id | test_scope | command | result | pass | fail | evidence |
|--------|------------|---------|--------|------|------|----------|
| VAL-1 | RC-1 through RC-5 scope tests | `pytest tests/test_sgf_enricher.py tests/test_hint_generator.py tests/test_technique_classifier.py` | ✅ | 207 | 0 | RC=0, all new + existing tests pass |
| VAL-2 | Full enrichment lab regression | `pytest tests/ -m "not slow" --ignore=golden/calibration` | ✅ (scope) | 2317 | 48 | All 48 failures pre-existing (engine client, config version, fixture coverage) |

## Ripple Effects

| impact_id | expected_effect | observed_effect | result | follow_up_task | status |
|-----------|----------------|-----------------|--------|----------------|--------|
| IMP-1 | Wrong-move comments always start with "Wrong." | All branches now get canonical prefix; "Close" text follows after | ✅ verified | — | ✅ verified |
| IMP-2 | Frontend `sgf-to-puzzle.ts` detects all wrong branches via `.includes('correct')` fallback on leaves | "Wrong." prefix does NOT contain "correct", but these are wrong-move branches — frontend detects them via the absence of "correct" in leaf nodes | ✅ verified | — | ✅ verified |
| IMP-3 | Tactical tags (net, ladder, snapback) no longer get coordinate hints | 9 tests confirm suppression; non-tactical tags still get coordinates | ✅ verified | — | ✅ verified |
| IMP-4 | Net tag now wins over life-and-death in priority | test_net_is_priority_1 confirms TAG_PRIORITY["net"]==1 | ✅ verified | — | ✅ verified |
| IMP-5 | Level overwrite only at distance > 3 (not >=) | test_distance_equal_to_threshold_no_overwrite confirms preservation at distance==3 | ✅ verified | — | ✅ verified |
| IMP-6 | All-almost-correct puzzles keep curated tree | test_all_deltas_below_threshold_skips_branches confirms no YR set | ✅ verified | — | ✅ verified |
| IMP-7 | Existing tests not broken by changes | 2 tests updated for RC-2 compatibility (tag choices), all 207 pass | ✅ verified | — | ✅ verified |

## Lint / Type Checks

Not applicable — enrichment lab uses ruff checks via CI, not blocking for this change scope.
