# Validation Report — Enrichment Almost-Correct Reversal

**Initiative**: `20260320-1400-feature-enrichment-almost-correct-reversal`
**Date**: 2026-03-20

---

## Test Validation

### In-Scope Tests (Definitive)

| val_id | test_file | tests | result | evidence |
|--------|-----------|-------|--------|----------|
| VAL-1 | `test_sgf_enricher.py` | 180 | ✅ 180 passed | Direct run, 0 failures |
| VAL-2 | `test_comment_assembler.py` | 28 | ✅ 28 passed | Direct run, 0 failures |
| VAL-3 | `test_teaching_comments.py` | 18 | ✅ 18 passed | Direct run, 0 failures |
| VAL-4 | `test_teaching_comment_embedding.py` | 6 | ✅ 6 passed | Direct run, 0 failures |
| | **Total in-scope** | **232** | **✅ 232 passed** | `pytest ... -q --no-header --tb=short` |

### Full Regression Suite

| val_id | scope | result | evidence |
|--------|-------|--------|----------|
| VAL-5 | Full enrichment lab (`-m "not slow"`, ignoring golden5/calibration) | ✅ ~10 pre-existing failures only | Failures in `test_refutation_quality_phase_a.py` (config v1.25 vs v1.21) and `test_ai_solve_config.py` (v1.25 vs v1.24). Zero new failures from 5% onward. |

### Pre-Existing Failures (NOT caused by this initiative)

| val_id | file | count | root_cause |
|--------|------|-------|------------|
| VAL-6 | `test_refutation_quality_phase_a.py` | 7 | Config version mismatch: tests expect v1.21, actual is v1.25. Also: `ownership_delta_weight` changed 0.0→0.3, `score_delta_enabled` False→True, `use_opponent_policy` False→True |
| VAL-7 | `test_ai_solve_config.py` | 3 | Config version mismatch: tests expect v1.24, actual is v1.25 |

---

## Scenario Coverage Matrix

| val_id | scenario | description | test_class | result |
|--------|----------|-------------|------------|--------|
| VAL-8 | A | All refutations almost-correct → branches NOW added | `TestScenarioA_AllAlmostCorrect` | ✅ |
| VAL-9 | A-old | Old guard test reversed — expects branches added | `TestAllAlmostCorrectGuard` | ✅ |
| VAL-10 | B/C | Plain wrong/correct — still get branches + YR | `TestScenarioBC_Unchanged` | ✅ |
| VAL-11 | D | Curated + AI coexist, dedup applied | `TestScenarioD_CuratedPlusAI` | ✅ |
| VAL-12 | D-cap | Cap limits AI branches (2 curated + 3 AI → 1 added) | `TestScenarioD_Cap::test_cap_limits_ai_branches` | ✅ |
| VAL-13 | D-cap-zero | 3 curated at cap → zero AI branches, no AI coords in YR | `TestScenarioD_Cap::test_cap_reached_no_ai_added` | ✅ |
| VAL-14 | E | Fresh puzzle, no existing wrongs → AI branches added | Existing `test_derives_yr_from_added_branches` | ✅ |
| VAL-15 | F | No refutations → no branches, no YR | Existing `test_no_refutations_no_branches` | ✅ |
| VAL-16 | Template | No `{!xy}` coordinate token in almost_correct template | `test_comment_assembler.py`, `test_teaching_comments.py` | ✅ |
| VAL-17 | Helpers | Count/collect helper functions work correctly | `TestCountAndCollectHelpers` (5 tests) | ✅ |

---

## Ripple-Effects Validation

| impact_id | expected_effect | observed_effect | result | follow_up_task | status |
|-----------|-----------------|-----------------|--------|----------------|--------|
| RE-1 | YR indexes curated wrong coords when cap reached | YR fallback uses `_collect_existing_wrong_coords()` | ✅ match | — | ✅ verified |
| RE-2 | YR combines curated+AI when AI branches added | Tested: curated coord `ef` included alongside AI coords | ✅ match | — | ✅ verified |
| RE-3 | Teaching comments for almost_correct have no coord | `coord=""` passed, template has no `{!xy}` | ✅ match | — | ✅ verified |
| RE-4 | Non-almost-correct wrong moves still get branches | `TestScenarioBC_Unchanged` passes | ✅ match | — | ✅ verified |
| RE-5 | Rejected results still return original SGF | Existing `TestRejectedSkipsEnrichment` passes | ✅ match | — | ✅ verified |
| RE-6 | Wrong-move prefix enforcement preserved | `_embed_teaching_comments()` unchanged | ✅ match | — | ✅ verified |

---

## Commands and Exit Codes

| cmd_id | command | exit_code | result |
|--------|---------|-----------|--------|
| CMD-1 | `pytest tests/test_sgf_enricher.py tests/test_comment_assembler.py tests/test_teaching_comments.py tests/test_teaching_comment_embedding.py -q --no-header --tb=short` | 0 | 232 passed |
| CMD-2 | Full regression (`-m "not slow"`, ignoring golden5/calibration) | 1 | Pre-existing failures only; zero new |
| CMD-3 | Same as CMD-1 after RC-1/RC-2/RC-3 fixes | 0 | **231 passed** (net -1: removed 2 dead tests, added 1 new) |

---

## RC Remediation Validation (2026-03-21)

| val_id | check | result | evidence |
|--------|-------|--------|----------|
| VAL-18 | `_derive_yr_from_branches` deleted from production code | ✅ | grep → 0 matches across repo |
| VAL-19 | `_derive_yr_from_branches` import + 2 tests removed | ✅ | grep → 0 matches in test file |
| VAL-20 | `TestScenarioF_PositionOnly` exists and passes | ✅ | 1 test: `test_position_only_gets_branches` ✅ |
| VAL-21 | AGENTS.md "Good move" stale text fixed | ✅ | grep → 0 matches; now says "Close, but not the best move." |
| VAL-22 | 231 in-scope tests pass, 0 failures | ✅ | `pytest ... -q --tb=short` exit code 0 |

---

Last Updated: 2026-03-21
