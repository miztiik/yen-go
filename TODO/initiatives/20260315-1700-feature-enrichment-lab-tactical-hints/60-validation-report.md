# Validation Report — Enrichment Lab Tactical Hints

**Initiative**: `20260315-1700-feature-enrichment-lab-tactical-hints`
**Last Updated**: 2026-03-15

---

## Test Results

| VAL-ID | Test Suite | Result | Evidence |
|--------|-----------|--------|----------|
| VAL-1 | Syntax check (14 files) | ✅ pass | `py_compile` all modified/created files |
| VAL-2 | Core tests (9 test files, 333 tests) | ✅ 333 passed, 1 skipped | L4 regression test |
| VAL-3 | New tests (test_multi_orientation.py) | ✅ 35 passed | Rotation, reflection, orientation invariance, entropy, rank, instinct |
| VAL-4 | Calibration tests (test_instinct_calibration.py) | ✅ 3 skipped | Auto-skip when golden set empty (expected) |
| VAL-5 | Full regression (T23) | ✅ 1882 passed, 22 skipped | 2 pre-existing failures in test_query_params.py (unrelated to changes) |

---

## Acceptance Criteria Verification

| VAL-ID | AC-ID | Criterion | Status | Evidence |
|--------|-------|-----------|--------|----------|
| VAL-6 | AC-1 | Policy entropy computed for all puzzles | ✅ | compute_policy_entropy() in estimate_difficulty.py; wired in DifficultyStage; stored in ctx.policy_entropy |
| VAL-7 | AC-2 | Entropy correlates with human difficulty | ⏳ deferred | Requires populated golden set + KataGo. Infrastructure in test_instinct_calibration.py ready. |
| VAL-8 | AC-3 | DetectionResult evidence in Tier 2 hints | ✅ | TechniqueStage stores ctx.detection_results; TeachingStage passes to hint_generator; _generate_reasoning_hint uses evidence |
| VAL-9 | AC-4 | Instinct classification ≥70% accurate | ⏳ deferred | Requires populated golden set + KataGo. Infrastructure ready. |
| VAL-10 | AC-5 | Instinct appears in teaching comments | ✅ | instinct_phrase prefix in hint_generator.py Tier 1; teaching_comments.py summary |
| VAL-11 | AC-6 | Multi-orientation tests pass | ✅ | 35 tests in test_multi_orientation.py — all pass |
| VAL-12 | AC-7 | Level-adaptive hints differ by level | ✅ | _generate_reasoning_hint uses level_category (entry/core/strong) for different templates |
| VAL-13 | AC-8 | Top-K rank observable | ✅ | find_correct_move_rank() computed in DifficultyStage; stored in ctx.correct_move_rank; logged |
| VAL-14 | AC-9 | All existing tests pass | ✅ | 1882 passed, 22 skipped, 0 new failures (2 pre-existing in test_query_params.py) |
| VAL-15 | AC-10 | Existing hint quality maintained | ✅ | All hint/teaching tests pass; new params have None defaults; existing callers unaffected |

---

## Ripple-Effects Validation

| impact_id | expected_effect | observed_effect | result | follow_up_task | status |
|-----------|----------------|-----------------|--------|---------------|--------|
| RE-1 | AiAnalysisResult: new fields additive | No schema changes needed; hints/comments enriched via existing fields | ✅ verified | — | ✅ verified |
| RE-2 | PipelineContext: new fields default None/0 | Fields added with None/0 defaults; existing stages unaffected | ✅ verified | — | ✅ verified |
| RE-3 | hint_generator: new params optional | All new params have default values; existing calls (333 tests) pass | ✅ verified | — | ✅ verified |
| RE-4 | teaching_comments: instinct additive | instinct_phrase is optional Layer 0; existing comments unchanged | ✅ verified | — | ✅ verified |
| RE-5 | comment_assembler: 15-word cap | instinct_phrase ≤3 words; overflow strategy handles excess | ✅ verified | — | ✅ verified |
| RE-6 | 28 detectors: unchanged | Zero modifications to any detector (NG-4) | ✅ verified | — | ✅ verified |
| RE-7 | config/teaching-comments.json: unchanged | New config models are in-code defaults; JSON file not modified | ✅ verified | — | ✅ verified |
| RE-8 | KataGo queries: zero new | All data from existing AnalysisResponse (C-1) | ✅ verified | — | ✅ verified |
| RE-9 | Backend pipeline: unaffected | Changes confined to tools/puzzle-enrichment-lab/ (C-4) | ✅ verified | — | ✅ verified |

---

## Charter Goal Coverage

| VAL-ID | Goal | Tasks | Status |
|--------|------|-------|--------|
| VAL-16 | G-1: Policy entropy | T5, T6 | ✅ complete |
| VAL-17 | G-2: DetectionResult pipeline | T4, T8, T13, T14 | ✅ complete |
| VAL-18 | G-3: Instinct classification | T3, T9, T10, T11, T15 | ✅ complete (instinct_enabled=False per C-3 until AC-4 calibration) |
| VAL-19 | G-4: Multi-orientation tests | T1, T2, RC-1 | ✅ complete (55 tests: 12 rotation + 5 reflection + 4 instinct + 20 detector orientation + 14 unit) |
| VAL-20 | G-5: Level-adaptive hints | T12, T16 | ✅ complete |
| VAL-21 | G-6: Top-K rank observability | T7 | ✅ complete |

---

## RC Resolution Validation

| VAL-ID | RC-ID | Change | Status | Evidence |
|--------|-------|--------|--------|----------|
| VAL-22 | RC-1 | Detector 4-rotation tests for ladder/ko/snapback/net/throw-in | ✅ pass | 20 new parametrized tests in test_multi_orientation.py, all pass |
| VAL-23 | RC-2 | instinct_enabled gate defaults False | ✅ pass | InstinctConfig.enabled=False; hint_generator.py and teaching_comments.py skip instinct_phrase; 687 targeted tests pass |
| VAL-24 | RC-3 | Entropy docstring accuracy fix | ✅ pass | Docstring matches implementation: "H / log2(K) where K = min(top_k, count of moves with positive prior)" |
| VAL-25 | RC-1 (Att.3) | Pipe sanitization in format_yh_property | ✅ pass | `h.replace("|", " ")` in format_yh_property; new test `test_strips_pipe_from_content` passes; 451 targeted tests pass |
| VAL-26 | RC-2 (Att.3) | Remove dead LevelAdaptiveTemplates config model | ✅ pass | Class, getter, and cache variable removed from config/teaching.py; AGENTS.md updated; no import errors; 451 targeted tests pass |
