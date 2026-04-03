# Execution Log — Enrichment Almost-Correct Reversal

**Initiative**: `20260320-1400-feature-enrichment-almost-correct-reversal`
**Executor**: Plan-Executor
**Date**: 2026-03-20

---

## Intake Validation

| check_id | check | result | evidence |
|----------|-------|--------|----------|
| IV-1 | Plan approval | ✅ | `70-governance-decisions.md` Gate 2: GOV-PLAN-APPROVED 7/7 |
| IV-2 | Task graph valid | ✅ | 13 tasks, 6 parallel lanes, dependency order verified |
| IV-3 | Analysis findings resolved | ✅ | `20-analysis.md`: 0 CRITICAL, 0 unresolved |
| IV-4 | Backward compat decision | ✅ | `status.json`: `backward_compatibility.required = false` |
| IV-5 | Governance handover | ✅ | `70-governance-decisions.md`: GOV-PLAN-APPROVED, handover to Plan-Executor |

---

## Parallel Lane Plan

| lane_id | task_ids | scope_files | dependencies | status |
|---------|----------|-------------|--------------|--------|
| L1 | T1, T2, T5, T6 | `sgf_enricher.py` | Sequential within lane | ✅ merged |
| L2 | T3 | `config/teaching-comments.json` | none — [P] | ✅ merged |
| L3 | T4 | `teaching_comments.py` | none — [P] | ✅ merged |
| L4 | T7, T8, T9, T10, T11 | `tests/test_sgf_enricher.py`, `tests/test_comment_assembler.py`, `tests/test_teaching_comments.py` | L1+L2+L3 | ✅ merged |
| L5 | T12 | — (test execution) | L4 | ✅ merged |
| L6 | T13 | `AGENTS.md` | L1+L2+L3 | ✅ merged |

L1+L2+L3 dispatched in parallel (no file overlap). L4 sequential after L1-L3. L5+L6 after L4.

---

## Per-Task Execution Log

### T1: Remove `skipped_all_almost` all-skip gate ✅

| field | value |
|-------|-------|
| file | `tools/puzzle-enrichment-lab/analyzers/sgf_enricher.py` |
| action | Deleted `skipped_all_almost = False` variable, `all_almost` check block (lines ~414-430), and `and not skipped_all_almost` from YR fallback |
| lines_changed | ~15 removed |
| evidence | The `skipped_all_almost` variable no longer exists; all-almost refutations now proceed to branch generation |

### T2: Replace curated gate with count + cap ✅

| field | value |
|-------|-------|
| file | `tools/puzzle-enrichment-lab/analyzers/sgf_enricher.py` |
| action | Removed `not _has_existing_refutation_branches(root)` guard. Added `_count_existing_refutation_branches()`, `_collect_existing_wrong_coords()`, `_get_node_move_coord_from_child()`, `_load_max_refutation_root_trees()` helpers. Compute `budget = max(0, cap - existing_count)`, slice branches to budget. |
| lines_changed | ~60 new, ~5 removed |
| evidence | New helpers tested in `TestCountAndCollectHelpers`. Cap enforced in `TestScenarioD_Cap`. |

### T3: Fix `almost_correct` template ✅

| field | value |
|-------|-------|
| file | `config/teaching-comments.json` |
| action | Changed `"Close — {!xy} is slightly better."` to `"Close, but not the best move."` |
| lines_changed | 1 |
| evidence | Template no longer contains `{!xy}` coordinate token |

### T4: Stop passing `correct_first_coord` for almost_correct ✅

| field | value |
|-------|-------|
| file | `tools/puzzle-enrichment-lab/analyzers/teaching_comments.py` |
| action | Changed `coord=correct_first_coord` to `coord=""` for almost_correct in both `classification.causal` loop (~line 300) and `classification.default_moves` loop (~line 316) |
| lines_changed | 4 |
| evidence | No coordinate token reaches the template output for almost_correct moves |

### T5: Add dedup for AI branches vs curated ✅

| field | value |
|-------|-------|
| file | `tools/puzzle-enrichment-lab/analyzers/sgf_enricher.py` |
| action | Before building AI branches, collects `existing_wrong_coords` via `_collect_existing_wrong_coords()`. Filters `result.refutations` to skip coords already in curated set. |
| lines_changed | ~5 |
| evidence | Dedup logged; tested in `TestScenarioD_CuratedPlusAI` |

### T6: Keep `_has_existing_refutation_branches` ✅

| field | value |
|-------|-------|
| file | `tools/puzzle-enrichment-lab/analyzers/sgf_enricher.py` |
| action | Kept function — test files reference it. Cheap to retain. |
| lines_changed | 0 |
| evidence | Grep shows callers in test files |

### T7: Tests — Scenario A (all-almost, now gets branches) ✅

| field | value |
|-------|-------|
| file | `tools/puzzle-enrichment-lab/tests/test_sgf_enricher.py` |
| action | Added `TestScenarioA_AllAlmostCorrect` class. 2 tests: branches ARE added, teaching comment contains "Close". Updated old `TestAllAlmostCorrectGuard` to expect branches added (reversed). |
| lines_changed | ~40 new |

### T8: Tests — Scenario D (curated + AI coexist, capped) ✅

| field | value |
|-------|-------|
| file | `tools/puzzle-enrichment-lab/tests/test_sgf_enricher.py` |
| action | Added `TestScenarioD_CuratedPlusAI` class (AI added alongside curated, dedup applied). Added `TestScenarioD_Cap` class (cap limits AI branches, cap=0 no AI added). |
| lines_changed | ~60 new |

### T9: Tests — Scenario B/C (unchanged, regression) ✅

| field | value |
|-------|-------|
| file | `tools/puzzle-enrichment-lab/tests/test_sgf_enricher.py` |
| action | Added `TestScenarioBC_Unchanged` class — verifies plain wrong/correct still get branches, YR derived. Renamed `test_skips_branches_when_already_present` → `test_adds_ai_branches_alongside_curated_wrongs`. |
| lines_changed | ~30 new |

### T10: Tests — Template has no `{!xy}` ✅

| field | value |
|-------|-------|
| file | `tests/test_comment_assembler.py`, `tests/test_teaching_comments.py` |
| action | Updated `test_comment_assembler.py` fixture template and assertion (no `{!of}` or "slightly better"). Updated `test_teaching_comments.py` delta gate assertion to check `{!` not in result. |
| lines_changed | ~10 modified |

### T11: Tests — Cap logic helpers ✅

| field | value |
|-------|-------|
| file | `tools/puzzle-enrichment-lab/tests/test_sgf_enricher.py` |
| action | Added `TestCountAndCollectHelpers` class. 5 tests: count zero/one/multiple wrongs, collect coords empty/mixed. |
| lines_changed | ~20 new |

### T12: Regression suite ✅

| field | value |
|-------|-------|
| evidence | In-scope tests: **232 passed, 0 failed** (`test_sgf_enricher.py`, `test_comment_assembler.py`, `test_teaching_comments.py`, `test_teaching_comment_embedding.py`). Full suite: ~10 pre-existing failures in `test_refutation_quality_phase_a.py` and `test_ai_solve_config.py` (config version 1.25 vs 1.24/1.21 mismatch — NOT caused by this initiative). Zero new failures beyond test file scope. |

### T13: Update AGENTS.md ✅

| field | value |
|-------|-------|
| file | `tools/puzzle-enrichment-lab/AGENTS.md` |
| action | Updated "Last updated" trigger. Replaced "All-almost-correct guard" bullet with "Curated+AI refutation cap" description. Added 3 new helper function entries. Added "Almost-correct template is spoiler-free" bullet. |
| lines_changed | ~15 modified |

---

## Deviations and Resolutions

| dev_id | deviation | resolution |
|--------|-----------|------------|
| DEV-1 | T6: `_has_existing_refutation_branches` had test callers | Kept function (decision: cheaper than updating tests) |
| DEV-2 | YR fallback set AI coords when cap reached (budget=0) | Rewrote YR derivation: index ALL wrongs (curated+AI) when branches added; index curated-only when absent |
| DEV-3 | `_derive_yr_from_branches()` only indexed AI branches | Replaced with curated+AI combined approach using `_collect_existing_wrong_coords()` + branch coords |

---

## Governance Review RC Remediation (2026-03-21)

### RC-1: Delete dead `_derive_yr_from_branches` ✅

| field | value |
|-------|-------|
| file | `sgf_enricher.py`, `test_sgf_enricher.py` |
| action | Deleted `_derive_yr_from_branches()` (11 lines). Removed import. Deleted `test_derives_yr` and `test_derives_yr_deduplicates` (2 test methods, ~16 lines). |
| verification | `grep _derive_yr_from_branches **/*.py` → 0 matches |

### RC-2: Add `TestScenarioF_PositionOnly` ✅

| field | value |
|-------|-------|
| file | `test_sgf_enricher.py` |
| action | Added `TestScenarioF_PositionOnly` class with position-only SGF fixture (AB/AW, no children). Verifies AI branches added and YR set. |
| verification | `test_position_only_gets_branches` passes |

### RC-3: Fix stale AGENTS.md text ✅

| field | value |
|-------|-------|
| file | `tools/puzzle-enrichment-lab/AGENTS.md` |
| action | Replaced `"Good move"` with `"Close, but not the best move."` at line 300 |
| verification | `grep "Good move" AGENTS.md` → 0 matches |

### Regression after RC fixes

| field | value |
|-------|-------|
| scope | `test_sgf_enricher.py`, `test_comment_assembler.py`, `test_teaching_comments.py`, `test_teaching_comment_embedding.py` |
| result | **231 passed, 0 failed** (net -1 from 232: removed 2 dead tests, added 1 new) |

---

Last Updated: 2026-03-21
