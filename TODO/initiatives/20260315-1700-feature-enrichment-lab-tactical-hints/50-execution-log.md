# Execution Log — Enrichment Lab Tactical Hints

**Initiative**: `20260315-1700-feature-enrichment-lab-tactical-hints`
**Executor**: Plan-Executor
**Started**: 2026-03-15

---

## Parallel Lane Plan

| lane_id | task_ids | scope_files | dependencies | status |
|---------|----------|-------------|-------------|--------|
| L1 | T1, T3 | models/position.py, models/instinct_result.py | None | ✅ merged |
| L1-seq | T4 | analyzers/stages/protocols.py | T3 | ✅ merged |
| L2 | T5, T7, T8 | analyzers/estimate_difficulty.py, analyzers/stages/technique_stage.py | None | ✅ merged |
| L3 | T9, T6, T12 | analyzers/instinct_classifier.py, analyzers/stages/difficulty_stage.py, config/teaching.py | T3, T5, T7 | ✅ merged |
| L3-seq | protocols.py fields | analyzers/stages/protocols.py | L3 | ✅ merged |
| L4 | T13, T14, T15, T16, T17 | analyzers/stages/teaching_stage.py, analyzers/hint_generator.py, analyzers/teaching_comments.py, analyzers/comment_assembler.py | T4, T8, T10, T12 | ✅ merged |
| L4-seq | T10, T11 | analyzers/stages/instinct_stage.py, analyzers/enrich_single.py | T4, T9 | ✅ merged |
| L5 | T2, T18-T22 | tests/test_multi_orientation.py, tests/test_instinct_calibration.py, tests/fixtures/golden-calibration/ | T1, T9 | ✅ merged |
| L6 | T23, T24, T25 | AGENTS.md, docs/concepts/hints.md, docs/how-to/tools/katago-enrichment-lab.md | All | ✅ merged |

---

## Per-Task Completion Log

| EX-ID | Task | Status | Evidence |
|-------|------|--------|----------|
| EX-1 | T1: Position.rotate/reflect | ✅ | models/position.py — rotate(0/90/180/270) and reflect(x/y) methods added |
| EX-2 | T2: Multi-orientation test parametrization | ✅ | tests/test_multi_orientation.py — 35 tests (12 rotation, 5 reflection, 4 orientation invariance, 14 unit tests) |
| EX-3 | T3: InstinctResult model | ✅ | models/instinct_result.py — dataclass with INSTINCT_TYPES frozenset |
| EX-4 | T4: PipelineContext fields | ✅ | analyzers/stages/protocols.py — detection_results, instinct_results, policy_entropy, correct_move_rank |
| EX-5 | T5: compute_policy_entropy() | ✅ | analyzers/estimate_difficulty.py — Shannon entropy, normalized 0-1, top-K configurable |
| EX-6 | T6: Wire entropy into DifficultyStage | ✅ | analyzers/stages/difficulty_stage.py — compute + store ctx.policy_entropy |
| EX-7 | T7: find_correct_move_rank() | ✅ | analyzers/estimate_difficulty.py — 1-based rank by visits, 0 if not found |
| EX-8 | T8: DetectionResult pipeline | ✅ | analyzers/stages/technique_stage.py — ctx.detection_results = detection_results |
| EX-9 | T9: instinct_classifier.py | ✅ | analyzers/instinct_classifier.py — classify_instinct() with 5 patterns (push/hane/cut/descent/extend) |
| EX-10 | T10: InstinctStage | ✅ | analyzers/stages/instinct_stage.py — error_policy=DEGRADE, calls classify_instinct |
| EX-11 | T11: Register InstinctStage | ✅ | analyzers/enrich_single.py — InsertStage() between TechniqueStage and TeachingStage |
| EX-12 | T12: Config models + templates | ✅ | config/teaching.py — InstinctConfig, LevelAdaptiveTemplates, getters |
| EX-13 | T13: TeachingStage wiring | ✅ | analyzers/stages/teaching_stage.py — passes detection_results, instinct_results, level_category |
| EX-14 | T14: Detection evidence in Tier 2 | ✅ | analyzers/hint_generator.py — DetectionResult.evidence used in Tier 2 hints |
| EX-15 | T15: Instinct in Tier 1 + teaching | ✅ | analyzers/hint_generator.py + teaching_comments.py — instinct phrase prefix |
| EX-16 | T16: Level-adaptive hints | ✅ | analyzers/hint_generator.py — entry/core/strong template selection |
| EX-17 | T17: 3-layer comment assembly | ✅ | analyzers/comment_assembler.py — instinct_phrase parameter |
| EX-18 | T18: Golden calibration set | ✅ | tests/fixtures/golden-calibration/ — README.md + labels.json |
| EX-19 | T19-T22: Calibration stubs | ✅ | tests/test_instinct_calibration.py — auto-skip when golden set empty |
| EX-20 | T23: Full regression | ✅ | 1882 passed, 22 skipped, 2 pre-existing failures (test_query_params.py — unrelated) |
| EX-21 | T24: AGENTS.md update | ✅ | tools/puzzle-enrichment-lab/AGENTS.md — all sections updated |
| EX-22 | T25: Global docs update | ✅ | docs/concepts/hints.md, docs/how-to/tools/katago-enrichment-lab.md |

---

## Deviations and Resolutions

| EX-ID | Deviation | Resolution |
|-------|-----------|------------|
| DEV-1 | T9 DRY note (RC-2): Group BFS exists in multiple detectors | Chose option (b): controlled duplication with comment citing detector sources. instinct_classifier._find_groups() is minimal BFS focused on instinct needs, with DRY note linking to detector implementations. |
| DEV-2 | T19-T22 calibration requires KataGo | Created infrastructure stubs that auto-skip when golden set empty. Full calibration runs separately with engine. |
| DEV-3 | T23: 2 pre-existing failures in test_query_params.py | Verified failures are in query_builder.py (reportAnalysisWinratesAs). None of our changed files touch this area. Pre-existing bug. |
| DEV-4 | ctx.policy_entropy/correct_move_rank fields | Added to PipelineContext as proper declared fields (not ad-hoc attributes) for type safety. |

---

## Governance Review RC Resolution (GOV-REVIEW-CONDITIONAL)

| EX-ID | RC | Status | Evidence |
|-------|---|--------|----------|
| EX-23 | RC-1: Detector orientation tests | ✅ | test_multi_orientation.py — 20 new parametrized tests (5 detectors × 4 rotations) for LadderDetector, KoDetector, SnapbackDetector, NetDetector, ThrowInDetector |
| EX-24 | RC-2: instinct_enabled gate | ✅ | config/teaching.py — `InstinctConfig.enabled: bool = False`; hint_generator.py and teaching_comments.py skip instinct_phrase when `enabled=False` |
| EX-25 | RC-3: Entropy docstring fix | ✅ | estimate_difficulty.py — docstring updated to "H / log2(K) where K = min(top_k, count of moves with positive prior)" |

### RC Resolution Test Results

- test_multi_orientation.py: 55 passed (was 35, +20 new detector orientation tests)
- Targeted regression (19 test files): 687 passed, 4 skipped, 0 failures
- Core hint/teaching tests: 198 passed, 1 skipped, 0 failures

---

## Governance Review RC Resolution (Attempt 3 — GOV-REVIEW-REVISE)

| EX-ID | RC | Status | Evidence |
|-------|---|--------|----------|
| EX-26 | RC-1: Pipe sanitization in format_yh_property | ✅ | hint_generator.py — `h.replace("|", " ")` applied before `"|".join()`. New test `test_strips_pipe_from_content` verifies pipe in evidence doesn't corrupt YH tiers. |
| EX-27 | RC-2: Remove dead LevelAdaptiveTemplates | ✅ | config/teaching.py — `LevelAdaptiveTemplates` class, `get_level_adaptive_templates()`, and `_DEFAULT_LEVEL_TEMPLATES` removed. AGENTS.md updated. Level-adaptive behavior remains in `_generate_reasoning_hint()` hardcoded branches (entry/core/strong). |

### RC Resolution Test Results (Attempt 3)

- New test `test_strips_pipe_from_content`: PASSED
- Targeted regression (11 test files): 451 passed, 1 skipped, 0 failures
- No regressions from LevelAdaptiveTemplates removal
