# Tasks — Enrichment Lab V2 (OPT-3)

**Initiative**: `20260314-1400-feature-enrichment-lab-v2`  
**Selected Option**: OPT-3 (Phased Delivery with Integrated Entropy)  
**Last Updated**: 2026-03-14

---

## Phase 1 — Foundation (G-2, G-3, G-4, G-5, G-6, G-10, G-13)

### Stage Cleanup & Infrastructure

| T-ID | Task | Files | Depends On | Parallel? | Goal |
|------|------|-------|------------|-----------|------|
| T1 | Delete BFS frame dead code (`tsumego_frame.py`) and associated test references | `analyzers/tsumego_frame.py`, `tests/test_tsumego_frame.py` | — | [P] | G-6 |
| T2 | Fix 8 existing test failures (config schema drift) | `tests/test_sprint4_fixes.py`, `tests/test_teaching_comments_config.py`, `tests/test_teaching_comments_integration.py`, `tests/test_tsumego_config.py` | — | [P] | G-6 |
| T2B | Extract `ValidationStatus` + `CorrectMoveResult` from `analyzers/validate_correct_move.py` to `models/validation.py` (fix V-1 inverse dependency) | `models/validation.py` (new), `analyzers/validate_correct_move.py`, `models/ai_analysis_result.py` | — | [P] | G-10 |
| T3 | Formalize solve-paths as `SolvePathStage` with StageRunner wrapping | `analyzers/stages/solve_path_stage.py` (new), `analyzers/stages/solve_paths.py` (refactor), `analyzers/enrich_single.py` | — | [P] | G-6 |
| T4 | Split TeachingStage into TechniqueStage + TeachingStage + SgfWritebackStage | `analyzers/stages/technique_stage.py` (new), `analyzers/stages/sgf_writeback_stage.py` (new), `analyzers/stages/teaching_stage.py` (modify) | — | [P] | G-6, G-10 |
| T4B | Add curated solution path pruning: skip validation of curated sub-branches (depth≥2) where KataGo visits < 1% of top. Config toggle + INFO logging of pruned branches. | `analyzers/validate_correct_move.py`, `config.py`, `config/katago-enrichment.json` | T4, T8 | [P] | G-4 |

### Remove Board Cropping (G-2)

| T-ID | Task | Files | Depends On | Parallel? | Goal |
|------|------|-------|------------|-----------|------|
| T5 | Remove `CroppedPosition` class and `crop_to_tight_board()` method | `models/position.py` | — | [P] | G-2 |
| T6 | Remove `uncrop_response()`, `uncrop_gtp()`, `uncrop_move()` functions | `analyzers/query_builder.py` | T5 | | G-2 |
| T7 | Unify query builder to single entry point accepting `Position` directly — eliminate `build_query_from_sgf()` re-parsing | `analyzers/query_builder.py` | T6 | | G-2, G-6 |
| T8 | Rename QueryStage → AnalyzeStage, accept Position from ParseStage directly. Update GUI imports if `gui/` references QueryStage. | `analyzers/stages/query_stage.py` → `analyzers/stages/analyze_stage.py`, `gui/` imports | T7 | | G-6 |
| T9 | Remove all crop-related imports and references across codebase | All files referencing CroppedPosition, crop_to_tight_board | T5, T6 | | G-2 |
| T10 | Update tests: remove crop-specific tests, update query builder tests | `tests/test_tight_board_crop.py` (delete), `tests/test_query_builder.py` (update) | T9 | | G-2 |

### Entropy ROI Module (G-3)

| T-ID | Task | Files | Depends On | Parallel? | Goal |
|------|------|-------|------------|-----------|------|
| T11 | Create `entropy_roi.py` with ownership entropy computation | `analyzers/entropy_roi.py` (new) | — | [P] | G-3 |
| T12 | Implement contested-region detection (bounding box of high-entropy intersections) | `analyzers/entropy_roi.py` | T11 | | G-3 |
| T12B | Add ownership-based frame quality check: `validate_frame_quality()` in `entropy_roi.py` consumed by `frame_adapter.py`. Uses ownership variance >15% to validate frame attacker detection. Config toggle + INFO logging. | `analyzers/entropy_roi.py`, `analyzers/frame_adapter.py`, `config.py`, `config/katago-enrichment.json` | T12 | | G-3, G-11 |
| T13 | Integrate entropy ROI into AnalyzeStage as `allowMoves` source | `analyzers/stages/analyze_stage.py` | T8, T12 | | G-3 |
| T14 | Implement fallback chain: frame+ROI → ROI only → bounding box | `analyzers/frame_adapter.py`, `analyzers/entropy_roi.py` | T12, T13 | | G-3, G-11 |
| T15 | Write tests for entropy ROI computation and fallback chain | `tests/test_entropy_roi.py` (new) | T14 | | G-3 |

### Fix Refutation Consistency (G-4)

| T-ID | Task | Files | Depends On | Parallel? | Goal |
|------|------|-------|------------|-----------|------|
| T16 | Pass framed position to refutation stage (fix P-5.1) | `analyzers/generate_refutations.py`, `analyzers/stages/refutation_stage.py` | T8 | | G-4 |
| T16B | Add temperature-scaled candidate scoring: replace policy-only sort in `identify_candidates()` with KaTrain-style `exp(-c × max(0, points_lost))` weighting. Config toggle (`mode: "temperature" | "policy_only"`), config `temperature` param. | `analyzers/generate_refutations.py`, `config.py`, `config/katago-enrichment.json` | T8 | [P] | G-4 |
| T17 | Add puzzle-region restriction (`allowMoves`) to refutation queries | `analyzers/generate_refutations.py` | T16 | | G-4 |
| T18 | Add refutation-specific `overrideSettings` (rootPolicyTemperature, wideRootNoise) | `analyzers/generate_refutations.py`, `config.py` | T17 | | G-4, G-13 |
| T18B | Add refutation tenuki rejector: calculate Manhattan distance between wrong move and KataGo's PV response. If distance > threshold (default 4.0), reject refutation (KataGo sees group as dead, wants tenuki). Config toggle + INFO logging of rejected count. **Highest pedagogical priority per Go domain panel.** | `analyzers/generate_refutations.py`, `models/refutation_result.py` (add `tenuki_flagged` field), `config.py`, `config/katago-enrichment.json` | T18 | | G-4 |
| T19 | Write tests for refutation framing consistency | `tests/test_refutation_framing.py` (new) | T18 | | G-4 |

### Visit Tiers (G-5)

| T-ID | Task | Files | Depends On | Parallel? | Goal |
|------|------|-------|------------|-----------|------|
| T20 | Add visit tier config model (T0/T1/T2/T3) to config.py and katago-enrichment.json | `config.py`, `config/katago-enrichment.json` | — | [P] | G-5 |
| T21 | Wire visit tiers into AnalyzeStage and escalation logic | `analyzers/stages/analyze_stage.py`, `analyzers/single_engine.py` | T8, T20 | | G-5 |
| T22 | Wire refutation visit tier (T2) into refutation stage | `analyzers/stages/refutation_stage.py` | T20 | | G-5 |
| T23 | Write tests for visit tier selection and escalation | `tests/test_visit_tiers.py` (new) | T22 | | G-5 |

### KataGo Query Improvements (G-13)

| T-ID | Task | Files | Depends On | Parallel? | Goal |
|------|------|-------|------------|-----------|------|
| T24 | Add `reportAnalysisWinratesAs=BLACK` to all analysis requests | `models/analysis_request.py` | — | [P] | G-13 |
| T25 | Increase `rootNumSymmetriesToSample` to 4 (standard) / 8 (referee) | `config.py`, `models/analysis_request.py` | T20 | | G-13 |
| T26 | Write tests for query parameter correctness | `tests/test_query_params.py` (new or extend existing) | T25 | | G-13 |

### Phase 1 Documentation & Validation

| T-ID | Task | Files | Depends On | Parallel? | Goal |
|------|------|-------|------------|-----------|------|
| T27 | Update enrichment lab README with new stage list | `tools/puzzle-enrichment-lab/README.md` | T8, T4 | | Doc |
| T28 | Create entropy ROI concept doc | `docs/concepts/entropy-roi.md` (new) | T15 | | Doc |
| T29 | Update katago enrichment config reference | `docs/reference/katago-enrichment-config.md` | T26 | | Doc |
| T30 | Run full test suite — validate no regressions (Phase 1 gate) | All tests | All Phase 1 tasks | | Gate |

---

## Phase 2 — Detection (G-1, G-7, G-8, G-9, G-11)

### Detector Infrastructure

| T-ID | Task | Files | Depends On | Parallel? | Goal |
|------|------|-------|------------|-----------|------|
| T31 | Create `analyzers/detectors/` directory with `__init__.py` (dispatcher + protocol), import `DetectionResult` from `models/detection.py` | `analyzers/detectors/__init__.py` (new), `models/detection.py` (new) | Phase 1 complete | | G-10 |
| T32 | Refactor `technique_classifier.py` to dispatcher calling individual detectors | `analyzers/technique_classifier.py`, `analyzers/result_builders.py` | T31 | | G-1 |

### High-Frequency Detectors (Priority 1)

| T-ID | Task | Files | Depends On | Parallel? | Goal |
|------|------|-------|------------|-----------|------|
| T33 | Implement life-and-death detector (ownership thresholds, default objective) | `analyzers/detectors/life_and_death_detector.py` (new) | T31 | [P] | G-1, G-7 |
| T34 | Implement ko detector (board ko_point check + PV recapture) | `analyzers/detectors/ko_detector.py` (new) | T31 | [P] | G-1, G-7 |
| T35 | Implement pattern-based ladder detector (3×3 pattern, 8 symmetries, recursive extension) | `analyzers/detectors/ladder_detector.py` (new) | T31 | [P] | G-1, G-8 |
| T36 | Implement snapback detector (liberty counting + sacrifice pattern) | `analyzers/detectors/snapback_detector.py` (new) | T31 | [P] | G-1, G-7 |

### Common Technique Detectors (Priority 2)

| T-ID | Task | Files | Depends On | Parallel? | Goal |
|------|------|-------|------------|-----------|------|
| T37 | Implement capture-race detector (competing group liberty comparison) | `analyzers/detectors/capture_race_detector.py` (new) | T31 | [P] | G-1, G-7 |
| T38 | Implement connection detector (group connectivity before/after move) | `analyzers/detectors/connection_detector.py` (new) | T31 | [P] | G-1, G-7 |
| T39 | Implement cutting detector (group disconnection analysis) | `analyzers/detectors/cutting_detector.py` (new) | T31 | [P] | G-1, G-7 |
| T40 | Implement throw-in detector (edge position + liberty reduction verification) | `analyzers/detectors/throw_in_detector.py` (new) | T31 | [P] | G-1, G-7 |
| T41 | Implement net detector (surrounding geometry check) | `analyzers/detectors/net_detector.py` (new) | T31 | [P] | G-1, G-7 |

### Intermediate Frequency Detectors (Priority 3)

| T-ID | Task | Files | Depends On | Parallel? | Goal |
|------|------|-------|------------|-----------|------|
| T42 | Implement seki detector (balanced ownership + mutual life) | `analyzers/detectors/seki_detector.py` (new) | T31 | [P] | G-1, G-7 |
| T43 | Implement nakade detector (interior vital point + eye count) | `analyzers/detectors/nakade_detector.py` (new) | T31 | [P] | G-1, G-7 |
| T44 | Implement double-atari detector (two groups in atari after move) | `analyzers/detectors/double_atari_detector.py` (new) | T31 | [P] | G-1, G-7 |
| T45 | Implement sacrifice detector (stone count decrease + winrate increase) | `analyzers/detectors/sacrifice_detector.py` (new) | T31 | [P] | G-1, G-7 |
| T46 | Implement escape detector (liberty increase / connection to safe group) | `analyzers/detectors/escape_detector.py` (new) | T31 | [P] | G-1, G-7 |

### Lower Frequency Detectors (Priority 4)

| T-ID | Task | Files | Depends On | Parallel? | Goal |
|------|------|-------|------------|-----------|------|
| T47 | Implement eye-shape, vital-point, liberty-shortage, dead-shapes, clamp detectors | 5 files in `analyzers/detectors/` | T31 | [P] | G-1, G-7 |

### Context-Dependent Detectors (Priority 5-6)

| T-ID | Task | Files | Depends On | Parallel? | Goal |
|------|------|-------|------------|-----------|------|
| T48 | Implement living, corner, shape, endgame, tesuji, under-the-stones, connect-and-die detectors | 7 files in `analyzers/detectors/` | T31 | [P] | G-1 |
| T49 | Implement joseki, fuseki detectors (heuristic quality, documented limitations) | 2 files in `analyzers/detectors/` | T31 | [P] | G-1 |

### Complexity Metric (G-9)

| T-ID | Task | Files | Depends On | Parallel? | Goal |
|------|------|-------|------------|-----------|------|
| T50 | Add complexity metric formula to difficulty estimation (5th component) | `analyzers/estimate_difficulty.py`, `config.py` | Phase 1 complete | | G-9 |
| T51 | Write tests for complexity metric | `tests/test_complexity_metric.py` (new) | T50 | | G-9 |

### Graceful Degradation (G-11)

| T-ID | Task | Files | Depends On | Parallel? | Goal |
|------|------|-------|------------|-----------|------|
| T52 | Implement enrichment quality level tracking per puzzle | `models/ai_analysis_result.py`, `analyzers/stages/assembly_stage.py` | T32 | | G-11 |
| T53 | Wire fallback chain into all stages (degrade instead of fail for detection/hints/teaching) | All stage files | T52 | | G-11 |

### Phase 2 Documentation & Validation

| T-ID | Task | Files | Depends On | Parallel? | Goal |
|------|------|-------|------------|-----------|------|
| T54 | Create detector interface concept doc | `docs/concepts/detector-interface.md` (new) | T32 | | Doc |
| T55 | Update technique detection concept doc | `docs/concepts/technique-detection.md` | T49 | | Doc |

### Stretch: KaTrain Config Research Adaptations

| T-ID | Task | Files | Depends On | Parallel? | Goal |
|------|------|-------|------------|-----------|------|
| T61 | Add per-move accuracy metric (`100 × 0.75^weighted_ptloss`) as enrichment output field | `analyzers/estimate_difficulty.py`, `models/ai_analysis_result.py` | T50 | [P] | G-9 |
| T62 | Add CONFIG_MIN_VERSION pattern to `katago-enrichment.json` schema + version-gate in config loader | `config.py`, `config/katago-enrichment.json` | Phase 1 complete | [P] | G-10 |
| T63 | Add ownership settledness delta for richer teaching comments (per-move settledness: local secure but global loss) | `analyzers/teaching_comments.py`, `config/teaching-comments.json` | T32 | [P] | G-11 |

| T-ID | Task | Files | Depends On | Parallel? | Goal |
|------|------|-------|------------|-----------|------|
| T56 | Run full test suite — validate (Phase 2 gate) | All tests | All Phase 2 tasks | | Gate |
| T56B | Add `tests/test_architecture.py` dependency guard (assert no model→analyzer imports, no stage→stage imports, no detector→stage imports) | `tests/test_architecture.py` (new) | T31 | [P] | G-10 |

---

## Phase 3 — Stretch (G-12)

| T-ID | Task | Files | Depends On | Parallel? | Goal |
|------|------|-------|------------|-----------|------|
| T57 | Create HumanSL calibration module with feature gate | `analyzers/humansl_calibration.py` (new), `config.py` | Phase 2 complete | | G-12 |
| T58 | Add `humanSLProfile` query parameter support to AnalysisRequest | `models/analysis_request.py` | T57 | | G-12 |
| T59 | Write tests for HumanSL feature gate (model absent → skip) | `tests/test_humansl.py` (new) | T58 | | G-12 |
| T60 | Phase 3 test gate | All tests | T59 | | Gate |

---

## Governance RC Remediation (Post Gate 5 Review)

| T-ID | Task | Files | Depends On | Parallel? | Source |
|------|------|-------|------------|-----------|--------|
| T64 | RC-1: Wire 28 technique detectors — TechniqueStage calls `run_detectors()` with typed objects, register all 28 detector classes, remove dead `_detect_*` heuristics in classify_techniques() | `analyzers/stages/technique_stage.py`, `analyzers/technique_classifier.py` | T60 | | CRA-1/CRB-1 |
| T65 | RC-2: Fix stale docstring in generate_refutations.py — update "UNFRAMED" to reflect framed position input | `analyzers/generate_refutations.py` | T60 | [P] | CRA-2 |
| T66 | RC-4: Replace monkey-patched `_temperature_score` on MoveAnalysis with typed sorting dict | `analyzers/generate_refutations.py` | T60 | [P] | CRA-3 |
| T67 | CRA-4: TechniqueStage passes typed Position/AnalysisResponse/SolutionNode to detectors | `analyzers/stages/technique_stage.py` | T64 | | CRA-4 |
| T68 | RC-3: Run difficulty formula against ≥50 real enriched puzzles, compare YG assignments, add VAL-7 | `60-validation-report.md` | T64 | | GV-7 RC-1 |
| T69 | Add integration test: enriching sample puzzle produces detector-based tags (not just old heuristics) | `tests/test_technique_classifier.py` | T64 | | RC-1 verification |
| T70 | RC remediation test gate | All tests | T64-T69 | | Gate |

---

## Dependency Graph Summary

```
Phase 1 (Foundation):
  [P] T1, T2, T2B, T3, T4, T5, T11, T20, T24  — all independent, parallel start
  T4 + T8 → [P] T4B (curated path pruning)
  T5 → T6 → T7 → T8 → T9 → T10
  T11 → T12 → T12B → T13 → T14 → T15
  T8 + T20 → T21, T22 → T23
  T8 → [P] T16B (temperature scoring, parallel with T16)
  T8 → T16 → T17 → T18 → T18B → T19
  T24 → T25 → T26
  All → T27, T28, T29 → T30 (gate)

Phase 2 (Detection):
  T30 → T31 → T32
  T31 → [P] T33-T49 (all detectors parallel)
  T31 → [P] T56B (architecture guard)
  T30 → T50 → T51
  T50 → [P] T61 (per-move accuracy)
  T32 → T52 → T53
  T32 → [P] T63 (ownership settledness teaching)
  T30 → [P] T62 (config min version)
  All → T54, T55 → T56 (gate)

Phase 3 (Stretch):
  T56 → T57 → T58 → T59 → T60 (gate)

Governance Review RC Remediation 2 (Post Gate 6B):
  T60 → [P] T71, T72, T73, T74, T75, T76, T77, T78, T79 → T80 (gate)
```

---

## Governance Review RC Remediation 2 (Post Gate 6B Review)

| T-ID | Task | Files | Depends On | Parallel? | Source |
|------|------|-------|------------|-----------|--------|
| T71 | RC-1: Rewrite ladder detector — Replace PV diagonal-ratio heuristic with board-state 3×3 pattern matching (8-symmetry transforms). PV as confirmation signal only. Add 3 synthetic unit tests: (a) shicho runs to edge → True, (b) ladder breaker → False, (c) net/clamp → False. | `analyzers/detectors/ladder_detector.py`, `tests/test_detectors_priority1.py` | T60 | [P] | GV-7/RC-1 |
| T72 | RC-2: Fix stale import in probe_frame.py — Update `from analyzers.tsumego_frame import apply_tsumego_frame` to use `frame_adapter` | `scripts/probe_frame.py` | T60 | [P] | CRA-1/RC-2 |
| T73 | RC-3: Update stages/README.md — Replace `QueryStage` with `AnalyzeStage` as primary name in stage table | `analyzers/stages/README.md` | T60 | [P] | CRA-2/RC-3 |
| T74 | RC-4: Add clean-room documentation to ladder detector docstring — Explicit declaration of independent clean-room implementation | `analyzers/detectors/ladder_detector.py` | T71 | | CRB-3/RC-4 |
| T75 | CRA-3/CRB-1: Add warning log when config load fails in query_builder.py — Replace silent `pass` with logger.warning for production observability | `analyzers/query_builder.py` | T60 | [P] | CRA-3/CRB-1 |
| T76 | CRA-4: Remove dead classify_techniques() and internal _detect_* heuristics — Old dict-based API no longer in active pipeline path | `analyzers/technique_classifier.py` | T60 | [P] | CRA-4 |
| T77 | CRA-5: Wire referee_symmetries (8) for T3 tier queries — query_builder uses config.deep_enrich.referee_symmetries when symmetries param indicates referee tier | `analyzers/query_builder.py`, `config/katago-enrichment.json` | T60 | [P] | CRA-5 |
| T78 | CRA-6: Fix entropy ROI column bounds — Replace fallback `"A"` with `continue` for out-of-range column index | `analyzers/entropy_roi.py` | T60 | [P] | CRA-6 |
| T79 | CRB-2: Cache HumanSL feature gate result — `is_humansl_available()` caches result after first call to avoid repeated disk I/O | `analyzers/humansl_calibration.py` | T60 | [P] | CRB-2 |
| T80 | RC remediation 2 test gate | All tests | T71-T79 | | Gate |

---

## Governance Review RC Remediation 3 (Post Gate 9 Full Code Review)

| T-ID | Task | Files | Depends On | Parallel? | Source |
|------|------|-------|------------|-----------|--------|
| T81 | GV7-1: Add stone capture logic to ladder `_simulate_ladder_chase()` — After each stone placement, scan adjacent opponent groups and remove any with 0 liberties. Prevents board state divergence during chase simulation. Add test for ladder with interfering stones. | `analyzers/detectors/ladder_detector.py`, `tests/test_detectors_priority1.py` | T80 | [P] | GV7-1 |
| T82 | GV7-3: Improve snapback detector with board-state capture pattern verification — Add PV sequence analysis: check if solution PV contains sacrifice→capture→recapture pattern (stone count decreases then increases). Keep policy/winrate as pre-filter, add board-state verification as secondary confirmation. Add 2 tests: true snapback and false positive (throw-in). | `analyzers/detectors/snapback_detector.py`, `tests/test_detectors_priority1.py` | T80 | [P] | GV7-3 |
| T83 | GV7-5: Tighten seki detector winrate band — Change `winrate_low` 0.3→0.40, `winrate_high` 0.7→0.60 in config model defaults and JSON. True seki converges to 0.48-0.52. Update test expectations. | `config.py`, `config/katago-enrichment.json`, `tests/test_detectors_priority3.py` | T80 | [P] | GV7-5 |
| T84 | CRB-3: Add entropy contest threshold to config — Move `DEFAULT_ENTROPY_THRESHOLD = 0.5` to `FrameEntropyQualityConfig` as `entropy_contest_threshold: float = 0.5`. Thread through `compute_entropy_roi()`. Add to JSON config. | `config.py`, `analyzers/entropy_roi.py`, `config/katago-enrichment.json` | T80 | [P] | CRB-3 |
| T85 | CRB-4: Add `TestNoBackendImports` to architecture guard — AST scan all lab `.py` files for `backend.puzzle_manager` imports. Prevent future accidental coupling. | `tests/test_architecture.py` | T80 | [P] | CRB-4 |
| T86 | CRB-1/RC-3: Migrate `result_builders.py` from `classify_techniques()` to `run_detectors()` — Replace dict-based call with typed detector dispatch. Update imports. Remove `classify_techniques` from result_builders. | `analyzers/result_builders.py`, `analyzers/technique_classifier.py` | T80 | | CRB-1/RC-3 |
| T87 | CRB-2: Remove `Any` imports made unnecessary by T86 — Audit files that imported `Any` solely for `classify_techniques()` dict path. Clean up where feasible. | `analyzers/result_builders.py`, `analyzers/technique_classifier.py` | T86 | | CRB-2 |
| T88 | Update AGENTS.md and documentation for RC3 changes — Reflect seki threshold tightening, entropy config, architecture guard additions, and dead code removal in AGENTS.md and relevant docs. | `tools/puzzle-enrichment-lab/AGENTS.md`, `docs/reference/katago-enrichment-config.md` | T87 | | Doc |
| T89 | RC remediation 3 test gate | All tests | T81-T88 | | Gate |
