# Execution Log — Enrichment Quality Regression Fix

**Initiative**: `20260319-2100-feature-enrichment-quality-regression-fix`
**Date**: 2026-03-19

## Parallel Lane Plan

| lane_id | task_ids | scope_files | dependencies | status |
|---------|----------|-------------|--------------|--------|
| L1 | T1, T4 | sgf_enricher.py | none | ✅ merged |
| L2 | T2 | hint_generator.py | none | ✅ merged |
| L3 | T3 | technique_classifier.py | none | ✅ merged |
| L4 | T5 | sgf_enricher.py | L1 (same file) | ✅ merged |
| L5 | T6 | test_sgf_enricher.py, test_hint_generator.py, test_technique_classifier.py | L1-L4 | ✅ merged |
| L6 | T7 | (test suite execution) | L5 | ✅ merged |
| L7 | T8 | AGENTS.md | L1-L4 | ✅ merged |

## Per-Task Log

| ex_id | task_id | description | files_changed | status | evidence |
|-------|---------|-------------|---------------|--------|----------|
| EX-1 | T1 | RC-1: Remove "Close" special-casing, enforce "Wrong." prefix | sgf_enricher.py | ✅ | Removed `if text.startswith("Close"): marked = text`. All wrong-move comments now get `f"Wrong. {text}"` prefix unless already prefixed. |
| EX-2 | T2 | RC-2: Add TIER3_TACTICAL_SUPPRESS_TAGS for net/ladder/snapback/throw-in/oiotoshi | hint_generator.py | ✅ | Added `TIER3_TACTICAL_SUPPRESS_TAGS` frozenset + `elif primary_tag in TIER3_TACTICAL_SUPPRESS_TAGS` branch that suppresses coordinate hints. |
| EX-3 | T3 | RC-3: Add `"net": 1` to TAG_PRIORITY | technique_classifier.py | ✅ | Net now has priority 1, same as snapback/ladder/ko. Listed first so it wins alphabetically. |
| EX-4 | T4 | RC-4: Change `>=` to `>` in level mismatch threshold | sgf_enricher.py | ✅ | `if distance > threshold:` — exact threshold distance preserves curated level. |
| EX-5 | T5 | RC-5: Guard against all-almost-correct refutations | sgf_enricher.py | ✅ | Added `skipped_all_almost` flag. When all refutation deltas < 0.05, skips branch building AND YR population. |
| EX-6 | T6 | Tests for RC-1 through RC-5 | test_sgf_enricher.py, test_hint_generator.py, test_technique_classifier.py | ✅ | 3 new test classes: TestWrongMovePrefixEnforcement (2 tests), TestLevelMismatchStrictThreshold (2 tests), TestAllAlmostCorrectGuard (3 tests). TestTacticalTagTier3Suppression (9 tests). test_net_is_priority_1. Updated 2 existing tests for RC-2 compatibility. |
| EX-7 | T7 | Run regression suite | (none) | ✅ | 207 passed, 0 failed (scope tests). Full suite: 2317 passed, 48 failed (all pre-existing: engine/config/fixture failures). |
| EX-8 | T8 | Update AGENTS.md | AGENTS.md | ✅ | Documented TIER3_TACTICAL_SUPPRESS_TAGS, wrong-move prefix enforcement, all-almost-correct guard, net priority, strict threshold. |

## Deviations

| dev_id | description | resolution |
|--------|-------------|------------|
| DEV-1 | RC-5 initial implementation didn't block YR fallback path. `_derive_yr_from_branches()` was empty but `elif` branch derived YR from raw refutation coords. | Added `skipped_all_almost` flag to guard both branch building AND YR fallback. |
| DEV-2 | Two pre-existing tests (`test_coordinate_correct_for_known_move`, `test_all_hints_are_strings`) used tactical tags (snapback, ladder) that are now suppressed. | Updated tests to use non-suppressed tags (`life-and-death`, `life-and-death + ko`). Tests now correctly validate coordinate generation for non-tactical tags. |
