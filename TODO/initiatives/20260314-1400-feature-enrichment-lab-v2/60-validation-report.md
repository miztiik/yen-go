# Validation Report — Enrichment Lab V2 (OPT-3)

**Initiative**: `20260314-1400-feature-enrichment-lab-v2`  
**Last Updated**: 2026-03-14

---

## Phase 1 Validation

| VAL-ID | Test Suite | Command | Result | Notes |
|--------|-----------|---------|--------|-------|
| VAL-1 | Enrichment lab (Phase 1 gate) | `pytest tests/ --ignore=golden/calibration/crop` | 1713 passed, 36 skipped, RC=0 | All new + existing tests pass |
| VAL-2 | Backend pipeline | `pytest backend/ -m "not (cli or slow)"` | 1969 passed, RC=0 | No regressions |

## Phase 2 Validation

| VAL-ID | Test Suite | Command | Result | Notes |
|--------|-----------|---------|--------|-------|
| VAL-3 | Enrichment lab (Phase 2 gate) | `pytest tests/ --ignore=golden/calibration/crop` | 1818 passed, 36 skipped, RC=0 | 105 new detector tests |
| VAL-4 | Architecture guard | `pytest tests/test_architecture.py` | 10 passed | No model→analyzer, stage→stage, or detector→stage violations |

## Phase 3 Validation

| VAL-ID | Test Suite | Command | Result | Notes |
|--------|-----------|---------|--------|-------|
| VAL-5 | Enrichment lab (Phase 3 gate) | `pytest tests/ --ignore=golden/calibration/crop` | 1829 passed, 36 skipped, RC=0 | HumanSL feature gate tests pass |
| VAL-6 | Backend pipeline (final) | `pytest backend/ -m "not (cli or slow)"` | 1969 passed, RC=0 | No regressions across pipeline |

## Governance RC Remediation Validation

| VAL-ID | Test Suite | Command | Result | Notes |
|--------|-----------|---------|--------|-------|
| VAL-7 | Difficulty calibration spot-check (RC-3) | `pytest tests/test_difficulty.py::TestGoldenSetCalibration` | 52 passed, RC=0 | 50 profiles within expected YG range. Monotonic group averages verified. 0 extreme tier shifts. Formula weights: policy=15, visits=15, trap=20, structural=35, complexity=15. Score thresholds: novice≤40, beginner≤50, elementary≤62, intermediate≤70, upper-intermediate≤78, advanced≤85, low-dan≤91, high-dan≤96, expert≤100. |
| VAL-8 | Detector wiring integration (RC-1) | `pytest tests/test_technique_classifier.py::TestGetAllDetectors tests/test_technique_classifier.py::TestRunDetectorsIntegration` | 6 passed, RC=0 | 28 detectors instantiated, all implement TechniqueDetector protocol, all unique classes, run_detectors() produces positive results from typed objects |
| VAL-9 | Full lab suite (RC remediation gate) | `pytest tests/ --ignore=golden/calibration` | 1887 passed, 36 skipped, RC=0 | 58 new tests from RC remediation (1829→1887) |
| VAL-10 | Backend pipeline (RC remediation) | `pytest backend/ -m "not (cli or slow)"` | 1969 passed, RC=0 | No regressions |
| VAL-11 | Architecture guard (post-RC) | `pytest tests/test_architecture.py` | 10 passed | No dependency violations after detector wiring |

## Governance RC Remediation 2 Validation

| VAL-ID | Test Suite | Command | Result | Notes |
|--------|-----------|---------|--------|-------|
| VAL-12 | Ladder detector board-state tests | `pytest tests/test_detectors_priority1.py::TestLadderDetector` | 7 passed, RC=0 | 3 new board-state tests (shicho→True, breaker→False, net→False) + 4 existing |
| VAL-13 | Full lab suite (RC remediation 2 gate) | `pytest tests/ --ignore=golden/calibration` | 1890 passed, 36 skipped, RC=0 | 3 new tests from ladder rewrite (1887→1890) |
| VAL-14 | Backend pipeline (RC remediation 2) | `pytest backend/ -m "not (cli or slow)"` | 1969 passed, RC=0 | No regressions |
| VAL-15 | Architecture guard (post-RC2) | `pytest tests/test_architecture.py` | 11 passed | No dependency violations after all changes |

## Ripple-Effects Validation

| impact_id | expected_effect | observed_effect | result | follow_up_task | status |
|-----------|----------------|-----------------|--------|---------------|--------|
| RE-1 | KataGo query params changed (reportWinratesAs, symmetries) | New fields in requests | ✅ verified | T24, T25 | ✅ verified |
| RE-2 | katago-enrichment.json extended | ~15 new config keys, no removals | ✅ verified | T20, T18 | ✅ verified |
| RE-3 | tags.json read-only | No modifications made | ✅ verified | T31-T49 | ✅ verified |
| RE-4 | No backend changes | Backend `puzzle_manager/` untouched | ✅ verified | — | ✅ verified |
| RE-5 | No frontend changes | Frontend untouched | ✅ verified | — | ✅ verified |
| RE-6 | GUI imports (QueryStage) | Backward-compat alias kept | ✅ verified | T8 | ✅ verified |
| RE-7 | CLI unchanged | `enrich_single_puzzle()` interface unchanged | ✅ verified | T3 | ✅ verified |
| RE-8 | Bridge config compat | New fields have defaults | ✅ verified | T20 | ✅ verified |
| RE-9 | Test fixtures updated | Crop tests removed, query tests updated | ✅ verified | T10 | ✅ verified |
| RE-10 | AnalysisRequest extended | New fields with defaults, backward compat | ✅ verified | T24 | ✅ verified |
| RE-11 | TechniqueStage now uses typed dispatcher | Old classify_techniques() replaced by run_detectors() with typed objects | ✅ verified | T64 | ✅ verified |
| RE-12 | Temperature scoring type-safe | Monkey-patched _temperature_score replaced by dict-based scoring | ✅ verified | T66 | ✅ verified |
| RE-13 | Difficulty formula 5-component calibrated | 50 golden-set profiles validated, no systematic miscalibration | ✅ verified | T68 | ✅ verified |
| RE-14 | Ladder detector board-state primary | Board-state simulation is primary, PV is fallback | ✅ verified | T71 | ✅ verified |
| RE-15 | probe_frame.py uses frame_adapter | No stale import of deleted tsumego_frame | ✅ verified | T72 | ✅ verified |
| RE-16 | stages/README.md reflects current names | AnalyzeStage, SolvePathStage listed | ✅ verified | T73 | ✅ verified |
| RE-17 | Query builder config warning | Silent config failure replaced with logger.warning | ✅ verified | T75 | ✅ verified |
| RE-18 | Referee symmetries wired for T3 | query_builder referee=True uses 8 symmetries | ✅ verified | T77 | ✅ verified |
| RE-19 | Entropy ROI safe bounds | Out-of-range column skipped, not mapped to A | ✅ verified | T78 | ✅ verified |
| RE-20 | HumanSL gate cached | os.path.exists result cached by model path | ✅ verified | T79 | ✅ verified |

## Governance RC Remediation 3 Validation

| VAL-ID | Test Suite | Command | Result | Notes |
|--------|-----------|---------|--------|-------|
| VAL-16 | Ladder detector capture tests | `pytest tests/test_detectors_priority1.py::TestLadderDetector` | 8+ passed, RC=0 | Capture removal during chase simulation verified |
| VAL-17 | Snapback PV verification tests | `pytest tests/test_detectors_priority1.py::TestSnapbackDetector` | passed, RC=0 | PV-confirmed vs unconfirmed confidence split verified |
| VAL-18 | Architecture guard (backend isolation) | `pytest tests/test_architecture.py::TestNoBackendImports` | passed, RC=0 | Zero backend.puzzle_manager imports confirmed |
| VAL-19 | Full lab suite (RC remediation 3 gate) | `pytest tests/ --ignore=golden/calibration` | 1894 passed, 36 skipped, RC=0 | 4 new tests from RC remediation 3 (1890→1894) |
| VAL-20 | Backend pipeline (RC remediation 3) | `pytest backend/ -m "not (cli or slow)"` | 1969 passed, RC=0 | No regressions |

## Ripple-Effects Validation (RC Remediation 3)

| impact_id | expected_effect | observed_effect | result | follow_up_task | status |
|-----------|----------------|-----------------|--------|---------------|--------|
| RE-21 | Ladder simulation removes captured stones | `_remove_captured_stones()` called at 3 points in chase loop | ✅ verified | T81 | ✅ verified |
| RE-22 | Snapback PV-confirmed confidence ≥0.85, unconfirmed 0.45 | `_pv_has_recapture_pattern()` gates confidence tier | ✅ verified | T82 | ✅ verified |
| RE-23 | Seki detection tightened to 0.40-0.60 | Config defaults and JSON updated | ✅ verified | T83 | ✅ verified |
| RE-24 | Entropy contest threshold configurable | `FrameEntropyQualityConfig.entropy_contest_threshold` = 0.5 | ✅ verified | T84 | ✅ verified |
| RE-25 | No backend.puzzle_manager imports in lab | TestNoBackendImports scans all .py files | ✅ verified | T85 | ✅ verified |
| RE-26 | result_builders uses run_detectors when position available | `build_partial_result()` dispatches to typed detectors | ✅ verified | T86 | ✅ verified |
| RE-27 | solve_paths.py passes position to build_partial_result | Both call sites updated with `position=position` | ✅ verified | T86 | ✅ verified |
