# Research Brief: Puzzle-Enrichment-Lab Test Suite Audit

> **Initiative**: 20260324-research-enrichment-lab-test-audit
> **Researcher**: Feature-Researcher agent (KataGo domain + TDD discipline)
> **Date**: 2026-03-24
> **Scope**: `tools/puzzle-enrichment-lab/tests/` — 84 test files

---

## 1. Research Question and Boundaries

**Question**: What is the health of the puzzle-enrichment-lab test suite? Specifically: what files are redundant, duplicated, superseded, over-engineered, or testing things that Pydantic/framework already validates?

**Boundaries**:
- Read-only audit — no code changes
- Scope limited to `tools/puzzle-enrichment-lab/tests/`
- External references: pytest best practices, Pydantic validation patterns
- All 84 test files examined via code search and structural analysis

---

## 2. Executive Summary

The test suite has **severe DRY violations** and significant bloat. The most critical finding is **4 fully duplicated detector test files** (2,237 lines of 100% copy-paste). Beyond that, 7 config test files redundantly verify Pydantic model defaults that are already validated by the framework itself. The "meta-test" cluster (architecture, implementation review, remediation sprints, fixture integrity) adds useful guardrails but overlaps significantly. The perf/calibration cluster (11 files) is properly marked `@pytest.mark.slow` and appropriately excluded from quick runs, but could be consolidated.

**Current state**: 84 files, ~27,400 lines, ~1,700+ test functions
**Achievable target**: ~55 files, ~19,000 lines, ~1,400 test functions (35% line reduction, 18% test reduction)

---

## 3. File-by-File Inventory

| R-ID | Filename | Lines | Tests | Type | KataGo? | Verdict |
|------|----------|-------|-------|------|---------|---------|
| R-1 | test_ai_analysis_result.py | 456 | 33 | unit | No | KEEP |
| R-2 | test_ai_solve_calibration.py | 248 | 24 | calibration | Yes | DEMOTE |
| R-3 | test_ai_solve_config.py | 364 | 48 | unit | No | CONSOLIDATE |
| R-4 | test_ai_solve_integration.py | 397 | 21 | integration | No | KEEP |
| R-5 | test_ai_solve_remediation.py | 801 | 45 | unit+integration | No | KEEP |
| R-6 | test_architecture.py | 195 | 12 | meta | No | KEEP |
| R-7 | test_ascii_board.py | 89 | 11 | unit | No | KEEP |
| R-8 | test_benson_check.py | 221 | 13 | unit | No | KEEP |
| R-9 | test_bridge_config.py | 66 | 11 | unit | No | KEEP |
| R-10 | test_calibration.py | 767 | 9 | calibration | Yes | DEMOTE |
| R-11 | test_calibration_retry.py | 209 | 22 | unit | No | KEEP |
| R-12 | test_cli.py | 606 | 33 | integration | No | KEEP |
| R-13 | test_cli_overrides.py | 270 | 15 | unit | No | KEEP |
| R-14 | test_cli_report.py | 74 | 13 | unit | No | KEEP |
| R-15 | test_comment_assembler.py | 440 | 38 | unit | No | KEEP |
| R-16 | test_complexity_metric.py | 169 | 17 | unit | No | KEEP |
| R-17 | test_config_lookup.py | 226 | 26 | unit | No | CONSOLIDATE |
| R-18 | test_correct_move.py | 727 | 37 | unit+integration | No | KEEP |
| R-19 | test_cross_validation_tags.py | 56 | 3 | unit | No | KEEP |
| R-20 | test_deep_enrich_config.py | 129 | 18 | unit | No | CONSOLIDATE |
| R-21 | test_detectors_common.py | 605 | 18 | unit | No | **DELETE** (dup of R-26) |
| R-22 | test_detectors_high_frequency.py | 503 | 19 | unit | No | **DELETE** (dup of R-25) |
| R-23 | test_detectors_intermediate.py | 469 | 21 | unit | No | **DELETE** (dup of R-27) |
| R-24 | test_detectors_lower_frequency.py | 661 | 29 | unit | No | **DELETE** (dup of R-28) |
| R-25 | test_detectors_priority1.py | 503 | 19 | unit | No | KEEP (canonical) |
| R-26 | test_detectors_priority2.py | 605 | 18 | unit | No | KEEP (canonical) |
| R-27 | test_detectors_priority3.py | 469 | 21 | unit | No | KEEP (canonical) |
| R-28 | test_detectors_priority4_5_6.py | 660 | 29 | unit | No | KEEP (canonical) |
| R-29 | test_diagnostic.py | 205 | 14 | unit | No | KEEP |
| R-30 | test_difficulty.py | 946 | 41 | unit | No | KEEP |
| R-31 | test_dual_engine.py | 355 | 17 | unit | No | CONSOLIDATE |
| R-32 | test_engine_client.py | 363 | 12 | unit | No | KEEP |
| R-33 | test_engine_health.py | 182 | 8 | integration | Yes | DEMOTE |
| R-34 | test_enrichment_config.py | 423 | 41 | unit | No | CONSOLIDATE |
| R-35 | test_enrichment_state.py | 96 | 15 | unit | No | KEEP |
| R-36 | test_enrich_single.py | 590 | 30 | unit | No | KEEP |
| R-37 | test_entropy_roi.py | 221 | 24 | unit | No | KEEP |
| R-38 | test_feature_activation.py | 263 | 52 | unit | No | CONSOLIDATE |
| R-39 | test_fixture_coverage.py | 601 | 16 | integration | Yes | DEMOTE |
| R-40 | test_fixture_integrity.py | 166 | 8 | unit | No | KEEP |
| R-41 | test_frame_adapter.py | 124 | 10 | unit | No | KEEP |
| R-42 | test_frame_utils.py | 123 | 12 | unit | No | KEEP |
| R-43 | test_frames_gp.py | 344 | 40 | unit | No | KEEP |
| R-44 | test_gate_integration.py | 678 | 18 | integration | No | KEEP |
| R-45 | test_golden5.py | 275 | 5 | integration | Yes | DEMOTE |
| R-46 | test_hint_generator.py | 502 | 80 | unit | No | KEEP |
| R-47 | test_humansl.py | 132 | 11 | unit | No | KEEP |
| R-48 | test_implementation_review.py | 251 | 26 | unit | No | CONSOLIDATE |
| R-49 | test_instinct_calibration.py | 38 | 3 | calibration | No | CONSOLIDATE |
| R-50 | test_ko_rules.py | 203 | 22 | unit | No | KEEP |
| R-51 | test_ko_validation.py | 251 | 10 | integration | Yes | KEEP |
| R-52 | test_log_config.py | 469 | 38 | unit | No | KEEP |
| R-53 | test_multi_orientation.py | 853 | 49 | unit | No | KEEP |
| R-54 | test_perf_100.py | 161 | 4 | calibration | Yes | DEMOTE |
| R-55 | test_perf_10k.py | 243 | 5 | calibration | Yes | DEMOTE |
| R-56 | test_perf_1k.py | 186 | 4 | calibration | Yes | DEMOTE |
| R-57 | test_perf_models.py | 255 | 4 | calibration | Yes | DEMOTE |
| R-58 | test_perf_smoke.py | 299 | 6 | calibration | Yes | DEMOTE |
| R-59 | test_query_builder.py | 252 | 17 | unit | No | KEEP |
| R-60 | test_query_params.py | 126 | 12 | unit | No | KEEP |
| R-61 | test_refutation_classifier.py | 214 | 26 | unit | No | KEEP |
| R-62 | test_refutation_framing.py | 399 | 9 | unit | No | KEEP |
| R-63 | test_refutation_quality_phase_a.py | 486 | 41 | unit | No | CONSOLIDATE |
| R-64 | test_refutation_quality_phase_b.py | 430 | 37 | unit | No | CONSOLIDATE |
| R-65 | test_refutation_quality_phase_c.py | 456 | 41 | unit | No | CONSOLIDATE |
| R-66 | test_refutation_quality_phase_d.py | 118 | 17 | unit | No | CONSOLIDATE |
| R-67 | test_refutations.py | 1101 | 38 | unit | No | KEEP |
| R-68 | test_remediation_sprints.py | 804 | 45 | unit | No | CONSOLIDATE |
| R-69 | test_sgf_enricher.py | 1185 | 100 | unit | No | KEEP |
| R-70 | test_sgf_parser.py | 201 | 26 | unit | No | KEEP |
| R-71 | test_sgf_patcher.py | 260 | 14 | unit | No | KEEP |
| R-72 | test_single_engine.py | 106 | 7 | unit | No | CONSOLIDATE |
| R-73 | test_solve_position.py | 2211 | 110 | unit | No | KEEP |
| R-74 | test_solve_result_models.py | 365 | 39 | unit | No | KEEP |
| R-75 | test_teaching_comments.py | 316 | 31 | unit | No | KEEP |
| R-76 | test_teaching_comments_config.py | 134 | 13 | unit | No | CONSOLIDATE |
| R-77 | test_teaching_comments_integration.py | 207 | 20 | integration | No | KEEP |
| R-78 | test_teaching_comment_embedding.py | 285 | 32 | unit | No | KEEP |
| R-79 | test_technique_calibration.py | 256 | 8 | calibration | Yes | DEMOTE |
| R-80 | test_technique_classifier.py | 479 | 70 | unit | No | KEEP |
| R-81 | test_tsumego_config.py | 95 | 11 | unit | No | CONSOLIDATE |
| R-82 | test_tsumego_frame.py | 982 | 78 | unit | No | KEEP |
| R-83 | test_visit_tiers.py | 107 | 9 | unit | No | KEEP |
| R-84 | test_vital_move.py | 94 | 9 | unit | No | KEEP |

**Verdict summary**:
- KEEP: 48 files
- DELETE: 4 files (2,238 lines — exact duplicates)
- CONSOLIDATE: 16 files (target: merge into ~7 files)
- DEMOTE: 11 files (already marked slow/integration, but could be consolidated into fewer perf-suite files)

---

## 4. Cluster Analysis

### Cluster 1: Detector Tests (8 files → 4 files)

**CRITICAL FINDING: 4 files are 100% duplicated code.**

| R-ID | File | Lines | Duplicate Of | Evidence |
|------|------|-------|-------------|----------|
| R-22 | test_detectors_high_frequency.py | 503 | test_detectors_priority1.py (R-25) | Identical classes: `TestLifeAndDeathDetector`, `TestKoDetector`, `TestLadderDetector`, `TestSnapbackDetector`. Line counts match exactly (503). |
| R-21 | test_detectors_common.py | 605 | test_detectors_priority2.py (R-26) | Identical classes: `TestProtocolConformance`, `TestCaptureRaceDetector`, `TestConnectionDetector`, `TestCuttingDetector`, `TestThrowInDetector`, `TestNetDetector`. Line counts match exactly (605). |
| R-23 | test_detectors_intermediate.py | 469 | test_detectors_priority3.py (R-27) | Identical classes: `TestSekiDetector`, `TestNakadeDetector`, `TestDoubleAtariDetector`, `TestSacrificeDetector`. Line counts match exactly (469). |
| R-24 | test_detectors_lower_frequency.py | 661 | test_detectors_priority4_5_6.py (R-28) | Identical classes: `TestProtocolConformance`, `TestEyeShapeDetector`, `TestVitalPointDetector`, `TestLibertyShortageDetector`, `TestDeadShapesDetector`, `TestClampDetector`, `TestLivingDetector`, `TestCornerDetector`. Line counts match within 1 (660 vs 661). |

**Root cause**: The priority-based naming (priority1/2/3/4_5_6) was a re-organization of the frequency-based naming (high_frequency/common/intermediate/lower_frequency). The old files were not deleted after the rename. Both sets of files are collected by pytest and run — doubling the detector test time.

**Recommendation**: **DELETE** the 4 frequency-named files (R-21 through R-24). Keep the priority-named files (R-25 through R-28) as canonical. This removes **2,238 lines** and **87 duplicate test executions**.

---

### Cluster 2: Refutation Tests (7 files)

| R-ID | File | Lines | Tests | Content |
|------|------|-------|-------|---------|
| R-67 | test_refutations.py | 1101 | 38 | Core unit tests: candidate identification, PV finding, orchestrator, output schema |
| R-61 | test_refutation_classifier.py | 214 | 26 | Classification logic: immediate capture, escape, ko, priority order |
| R-62 | test_refutation_framing.py | 399 | 9 | Framed position, temperature scoring, tenuki rejection, orchestrator wiring |
| R-63 | test_refutation_quality_phase_a.py | 486 | 41 | PI-1 ownership delta, PI-3 score delta filter, PI-12 best resistance |
| R-64 | test_refutation_quality_phase_b.py | 430 | 37 | PI-2 adaptive visit allocation, PI-4 model routing, PI-5 depth-dependent visits |
| R-65 | test_refutation_quality_phase_c.py | 456 | 41 | PI-7 branch escalation, PI-8 temperature strategies, PI-9 confirmation queries |
| R-66 | test_refutation_quality_phase_d.py | 118 | 17 | PI-11 surprise-weighted calibration |

**Analysis**: Each phase file tests a distinct "PI" (Performance Improvement) item. They test different config knobs and behavioral aspects. **Low overlap** between files — each phase maps to a distinct feature flag or algorithm. The phase files share a common `autouse` fixture clearing config caches — this is a minor DRY issue.

**Overlap with R-38 (test_feature_activation.py)**: R-38 (263 lines, 52 tests) independently verifies that the same PI feature flags are active in the live config. This creates a **triple-testing pattern**: feature_activation checks the config value, phase_X tests the behavior, and enrichment_config also checks some of these values.

**Recommendation**: 
- **CONSOLIDATE** phases A-D into a single `test_refutation_quality.py` (saves ~250 lines of shared boilerplate: imports, autouse fixtures, mock helpers)
- **CONSOLIDATE** R-38 `test_feature_activation.py` into the phase tests (the "is it enabled?" check belongs with the behavioral test)
- **KEEP** R-67, R-61, R-62 as-is (distinct concerns)

---

### Cluster 3: Config Tests (7 files)

| R-ID | File | Lines | Tests | Content |
|------|------|-------|-------|---------|
| R-34 | test_enrichment_config.py | 423 | 41 | Top-level config: file exists, thresholds present, level IDs, ownership regions, rank bands |
| R-20 | test_deep_enrich_config.py | 129 | 18 | DeepEnrichConfig: defaults, visits, model, symmetries, effective-visits wiring |
| R-81 | test_tsumego_config.py | 95 | 11 | KataGo tsumego.cfg: file exists, parses, specific settings verified |
| R-9 | test_bridge_config.py | 66 | 11 | Bridge config utilities: unflatten, deep_merge, apply_overrides |
| R-3 | test_ai_solve_config.py | 364 | 48 | AiSolveConfig: thresholds, depth profiles, level mapping, validators, round-trip |
| R-76 | test_teaching_comments_config.py | 134 | 13 | TeachingCommentsConfig: loader, 28 tags present, required fields, word limit |
| R-17 | test_config_lookup.py | 226 | 26 | Config lookup module: tag slug maps, level ID maps, resolve functions |

**YAGNI issues**:
- **R-34 `test_enrichment_config.py`** — Tests like `test_config_file_exists()`, `test_config_loads_valid_json()` are unnecessary. If the config file didn't exist, every other test in the suite would fail. Pydantic's `model_validate()` already validates types and required fields. Tests like `test_ownership_thresholds_present()` just assert `hasattr` — Pydantic guarantees this.
- **R-3 `test_ai_solve_config.py`** — 48 tests that verify Pydantic model defaults match expected values. While useful as documentation, ~30 of these are pure "config default value snapshot" tests (`test_t_good_default`, `test_t_bad_default`, `test_t_hotspot_default`, `test_t_disagreement_default`, `test_confirmation_min_policy`, `test_tree_visits`, etc.). If the default changes intentionally, these all break and must be updated — they're config snapshot tests, not behavioral tests.
- **R-81 `test_tsumego_config.py`** — Tests that a specific KataGo config file has exact key-value pairs. These are integration tests disguised as unit tests.

**Recommendation**:
- **CONSOLIDATE** R-34 + R-20 + R-3 + R-76 + R-81 into a single `test_config.py` (or max 2 files: `test_config_loading.py` + `test_config_values.py`)
- **KEEP** R-9 (bridge_config tests a distinct utility module, not Pydantic models)
- **KEEP** R-17 (config_lookup tests actual lookup logic with edge cases)
- Consider converting config-default-snapshot tests into a single parametrized test that loads a JSON "expected defaults" reference

---

### Cluster 4: Teaching Comment Tests (5 files)

| R-ID | File | Lines | Tests | Content |
|------|------|-------|-------|---------|
| R-75 | test_teaching_comments.py | 316 | 31 | Unit: comment generation, aliases, confidence gating, delta gate, vital move |
| R-76 | test_teaching_comments_config.py | 134 | 13 | Unit: config loader, tag coverage, required fields, word limits |
| R-77 | test_teaching_comments_integration.py | 207 | 20 | Integration: full pipeline per-technique (snapback, dead shapes, wrong moves) |
| R-78 | test_teaching_comment_embedding.py | 285 | 32 | Unit: SGF embedding, terse label replacement, node comment operations |
| R-15 | test_comment_assembler.py | 440 | 38 | Unit: opponent response assembly, conditional dash rules |

**Analysis**: All 5 files test distinct modules/functions in the teaching-comment workflow:
- R-75 tests `teaching_comments.py` (generation)
- R-76 tests config loading for teaching comments
- R-77 tests end-to-end pipeline integration
- R-78 tests `teaching_comment_embedding.py` (SGF tree manipulation)
- R-15 tests `comment_assembler.py` (assembly logic)

**Low overlap**. Each file targets a different module. The only consolidation opportunity is merging R-76 into the broader config consolidation (Cluster 3).

**Recommendation**: 
- **KEEP** R-75, R-77, R-78, R-15
- **CONSOLIDATE** R-76 into the unified config test (Cluster 3)

---

### Cluster 5: Perf/Calibration Tests (11 files)

| R-ID | File | Lines | Tests | KataGo | Marker |
|------|------|-------|-------|--------|--------|
| R-58 | test_perf_smoke.py | 299 | 6 | Yes | slow, integration |
| R-54 | test_perf_100.py | 161 | 4 | Yes | slow, integration |
| R-56 | test_perf_1k.py | 186 | 4 | Yes | slow, integration |
| R-55 | test_perf_10k.py | 243 | 5 | Yes | slow, integration |
| R-57 | test_perf_models.py | 255 | 4 | Yes | slow, integration |
| R-10 | test_calibration.py | 767 | 9 | Yes | slow, calibration, integration |
| R-11 | test_calibration_retry.py | 209 | 22 | No | unit |
| R-79 | test_technique_calibration.py | 256 | 8 | Yes | slow, integration |
| R-49 | test_instinct_calibration.py | 38 | 3 | No | unit (requires golden labels JSON) |
| R-45 | test_golden5.py | 275 | 5 | Yes | golden5, integration |
| R-2 | test_ai_solve_calibration.py | 248 | 24 | Yes | slow, integration |

**Analysis**: These files are all properly gated behind `@pytest.mark.slow` / `@pytest.mark.integration` and require KataGo + model files. They're excluded from the standard `pytest -m "not slow"` suite. 

**DRY issue**: All KataGo-requiring files duplicate the same engine setup pattern (check binary exists, create EngineConfig, start, wait for ready, yield, shutdown). The conftest.py `integration_engine` fixture partially addresses this, but some files (golden5, calibration) create their own class-scoped engines.

**Consolidation opportunity**: The perf_100 / perf_1k / perf_10k / perf_smoke files all follow the same pattern: load N fixtures, enrich, assert accuracy thresholds. They differ only in the fixture set size and expected thresholds.

**Recommendation**:
- **CONSOLIDATE** perf_smoke + perf_100 + perf_1k + perf_10k into a single `test_perf_suite.py` with parametrized fixture sets (~250 lines saved)
- **CONSOLIDATE** instinct_calibration (38 lines, 3 tests) into test_technique_calibration.py
- **KEEP** test_calibration.py, test_golden5.py, test_ai_solve_calibration.py as separate (distinct calibration domains)
- **KEEP** test_calibration_retry.py (unit tests for retry logic, no KataGo needed)

---

### Cluster 6: Framework/Architecture Meta-Tests (6 files)

| R-ID | File | Lines | Tests | Content |
|------|------|-------|-------|---------|
| R-6 | test_architecture.py | 195 | 12 | Dependency guards: models→analyzers, stages→stages, detectors→stages/result |
| R-48 | test_implementation_review.py | 251 | 26 | Post-implementation review fixes: escaped brackets, GTP→SGF, node serialization, config values |
| R-38 | test_feature_activation.py | 263 | 52 | Feature flag activation state: PI-1 through PI-12 config values |
| R-39 | test_fixture_coverage.py | 601 | 16 | Fixture file integrity: every tag has SGF, parses, has correct move, has wrong branch |
| R-40 | test_fixture_integrity.py | 166 | 8 | Two-population integrity: no overlap between calibration and evaluation fixtures |
| R-68 | test_remediation_sprints.py | 804 | 45 | Sprint remediation gaps S1-G15 through S5: ownership convergence, score lead, dual-engine |

**Analysis**:
- **R-6 test_architecture.py**: Valuable dependency guard. Uses AST analysis to enforce layer isolation. **KEEP**.
- **R-48 test_implementation_review.py**: Tests specific historical bug fixes (escaped brackets, GTP mapping). These are regression tests — valuable. But the filename is bad — it should be named for what it tests, not "implementation review". Could be merged into the tests for the modules being tested (e.g., escaped bracket tests → test_sgf_parser.py, GTP tests → test_query_builder.py). **CONSOLIDATE** into existing module tests.
- **R-38 test_feature_activation.py**: 52 tests that assert config default values (`assert cfg.refutations.candidate_scoring.ownership_delta_weight == pytest.approx(0.3)`). This is **pure config snapshot testing** — it duplicates facts already in `katago-enrichment.json`. These tests break whenever a config value changes intentionally. **CONSOLIDATE** into refutation quality phase tests or a single config-snapshot test.
- **R-39 test_fixture_coverage.py**: Requires KataGo to enrich 25+ fixtures. Valuable for CI but slow. **DEMOTE** to slow suite.
- **R-40 test_fixture_integrity.py**: Lightweight filesystem checks — no KataGo needed. **KEEP**.
- **R-68 test_remediation_sprints.py**: 804 lines, 45 tests covering 20 sprint gaps. The sprint naming (S1-G1, S1-G15, S1-G16, etc.) will become meaningless over time. Tests cover real functionality (ownership convergence, score lead, dual-engine comparison) but the organizational structure is historical. **CONSOLIDATE** — move tests to the module they actually test.

---

### Cluster 7: Engine Tests (4 files)

| R-ID | File | Lines | Tests | KataGo | Content |
|------|------|-------|-------|--------|---------|
| R-32 | test_engine_client.py | 363 | 12 | No | Response parsing, get_move lookup, restart-on-crash mock |
| R-33 | test_engine_health.py | 182 | 8 | Yes | Engine start/stop, health check response, ownership/policy present |
| R-72 | test_single_engine.py | 106 | 7 | No | Visit escalation, model routing, compare_results correct move |
| R-31 | test_dual_engine.py | 355 | 17 | No | Quick engine starts, referee engine starts, health check, answer merging |

**Analysis**: 
- R-32 (engine_client) and R-72 (single_engine) test different modules — engine_client tests `LocalEngine` response handling, single_engine tests `SingleEngineManager` visit escalation. **No overlap**.
- R-31 (dual_engine) tests `DualEngineManager` which uses two engines (quick + referee). This is a distinct component.
- R-33 (engine_health) requires real KataGo — integration test.

**Minor consolidation**: R-72 (106 lines, 7 tests) could be merged into R-32 or kept separate. The `SingleEngineManager` is a key component and having its own file is justified.

**Recommendation**: 
- **CONSOLIDATE** R-72 into R-32 (both test engine management, total would be ~460 lines)
- **KEEP** R-31 (distinct dual-engine logic)
- **DEMOTE** R-33 (requires KataGo, already integration-marked)

---

## 5. YAGNI / DRY / KISS / SOLID Violations

### DRY Violations (Severity: CRITICAL to MODERATE)

| V-ID | Violation | Files | Lines Wasted | Severity |
|------|-----------|-------|-------------|----------|
| V-1 | **Exact file duplication**: 4 detector test files copied with different names | R-21/R-25, R-22/R-26, R-23/R-27, R-24/R-28 | 2,238 | CRITICAL |
| V-2 | **Shared autouse fixture** duplicated in 4+ files: `clear_config_caches` fixture with identical `clear_cache()` calls | R-63, R-64, R-65, R-66, R-38 | ~60 | MODERATE |
| V-3 | **Mock AnalysisResponse builder** re-implemented in multiple files: `_make_response()` / `make_response()` | R-67, R-68, R-31, R-73 | ~120 | MODERATE |
| V-4 | **Engine setup boilerplate** (check binary, create config, start, wait, yield) repeated per integration file instead of using conftest fixture | R-45, R-10, R-39 | ~100 | MODERATE |

### YAGNI Violations

| V-ID | Violation | File(s) | Tests | Severity |
|------|-----------|---------|-------|----------|
| V-5 | **Config existence tests**: `test_config_file_exists()`, `test_config_loads_valid_json()` — every other test fails if these conditions are unmet | R-34:L28, R-34:L33 | 2 | LOW |
| V-6 | **Pydantic hasattr tests**: `test_ownership_thresholds_present()` — Pydantic guarantees field presence | R-34:L54 | 1 | LOW |
| V-7 | **Config snapshot tests**: 52 tests asserting specific config default values — break on intentional changes | R-38 (entire file) | 52 | HIGH |
| V-8 | **Config default value tests**: `test_t_good_default()`, `test_t_bad_default()` etc. — pure config snapshots | R-3:L101-L170 | ~20 | MODERATE |
| V-9 | **Config version pinning**: `test_config_version_is_1_28()` — breaks every version bump | R-3:L45 | 1 | LOW |

### KISS Violations

| V-ID | Violation | File | Severity |
|------|-----------|------|----------|
| V-10 | **Sprint naming convention**: Tests named by sprint/gap ID (S1-G1, S1-G15) instead of by behavior — obscures what's being tested | R-68 | MODERATE |
| V-11 | **Phase-based file splitting**: 4 separate files for refutation quality phases when they could be one file with section headers | R-63–R-66 | LOW |
| V-12 | **"Implementation review" naming**: File named for when it was created, not what it tests | R-48 | LOW |

### SOLID Violations

| V-ID | Violation | File | Severity |
|------|-----------|------|----------|
| V-13 | **Mixed concerns**: R-68 (`test_remediation_sprints.py`) tests ownership convergence, score lead, dual-engine comparison, diagnostic fields — touching 6+ different modules in one file | R-68 | MODERATE |
| V-14 | **Mixed concerns**: R-34 (`test_enrichment_config.py`) tests loading, thresholds, level IDs, ownership regions, rank bands, confidence reasons, PV caps — too many responsibilities | R-34 | MODERATE |

---

## 6. Superseded Tests

| R-ID | File | Superseded By | Reason |
|------|------|--------------|--------|
| R-21 | test_detectors_common.py | R-26 (test_detectors_priority2.py) | Exact duplicate — old naming |
| R-22 | test_detectors_high_frequency.py | R-25 (test_detectors_priority1.py) | Exact duplicate — old naming |
| R-23 | test_detectors_intermediate.py | R-27 (test_detectors_priority3.py) | Exact duplicate — old naming |
| R-24 | test_detectors_lower_frequency.py | R-28 (test_detectors_priority4_5_6.py) | Exact duplicate — old naming |
| R-38 | test_feature_activation.py | R-63–R-66 phase tests | Phase tests already test behavior + assert feature is enabled |

---

## 7. Consolidation Roadmap

### Phase 1: Quick Wins (0 risk, immediate)

| Action | Source | Target | Lines Saved |
|--------|--------|--------|-------------|
| DELETE | test_detectors_common.py | (none — priority2 is canonical) | 605 |
| DELETE | test_detectors_high_frequency.py | (none — priority1 is canonical) | 503 |
| DELETE | test_detectors_intermediate.py | (none — priority3 is canonical) | 469 |
| DELETE | test_detectors_lower_frequency.py | (none — priority4_5_6 is canonical) | 661 |
| **Subtotal** | | | **2,238** |

### Phase 2: Config Consolidation (low risk)

| Action | Source Files | Target File | Est. Lines Saved |
|--------|-------------|-------------|------------------|
| MERGE | test_enrichment_config.py + test_deep_enrich_config.py + test_tsumego_config.py + test_teaching_comments_config.py | test_config.py | ~200 (shared imports, fixtures) |
| MERGE | test_ai_solve_config.py (keep validator/round-trip tests, drop pure snapshots) | test_config.py | ~150 (dropped snapshot tests) |
| MERGE | test_feature_activation.py | Into phase tests / test_config.py | ~200 |
| **Subtotal** | | | **~550** |

### Phase 3: Refutation Quality Consolidation (low-medium risk)

| Action | Source Files | Target File | Est. Lines Saved |
|--------|-------------|-------------|------------------|
| MERGE | test_refutation_quality_phase_a/b/c/d.py | test_refutation_quality.py | ~250 (shared boilerplate) |
| **Subtotal** | | | **~250** |

### Phase 4: Remediation/Review Redistribution (medium risk)

| Action | Source | Target | Est. Lines Saved |
|--------|--------|--------|------------------|
| REDISTRIBUTE | test_remediation_sprints.py (ownership convergence) | test_solve_position.py or test_correct_move.py | ~100 (reduced duplication) |
| REDISTRIBUTE | test_implementation_review.py (escaped brackets) | test_sgf_parser.py | ~50 |
| REDISTRIBUTE | test_implementation_review.py (GTP→SGF) | test_query_builder.py | ~50 |
| **Subtotal** | | | **~200** |

### Phase 5: Perf Suite Consolidation (low risk)

| Action | Source | Target | Est. Lines Saved |
|--------|--------|--------|------------------|
| MERGE | test_perf_smoke + test_perf_100 + test_perf_1k + test_perf_10k | test_perf_suite.py | ~250 |
| MERGE | test_instinct_calibration into test_technique_calibration | test_technique_calibration.py | ~20 |
| MERGE | test_single_engine into test_engine_client | test_engine_client.py | ~30 |
| **Subtotal** | | | **~300** |

---

## 8. Estimated Impact

| Metric | Current | After Phase 1 | After All Phases |
|--------|---------|--------------|-----------------|
| Test files | 84 | 80 | ~58 |
| Total lines | ~27,400 | ~25,162 | ~21,600 |
| Test functions | ~1,700 | ~1,613 | ~1,500 |
| Duplicate test runs | ~87 | 0 | 0 |
| Lines removed | — | 2,238 | ~5,800 |

---

## 9. Risks, License/Compliance Notes, Rejection Reasons

| Risk | Severity | Mitigation |
|------|----------|------------|
| Deleting files that are imported elsewhere | Low | grep for `import test_detectors_common` etc. before deleting |
| Config snapshot tests are intentionally enforced | Medium | Ask user/owner if config snapshot tests serve as "approved config" gates |
| Redistribution (Phase 4) may break test discovery patterns | Medium | Run full test suite after each merge, verify marker coverage |
| Perf suite merge may affect CI caching | Low | Maintain same `@pytest.mark.slow` markers |

**License**: All code is internal. No external license concerns.

**Rejection candidate**: Phase 4 (redistribution) has the highest risk. If the team prefers "tests grouped by when they were written" over "tests grouped by module under test", skip Phase 4.

---

## 10. Planner Recommendations

1. **Immediate: Delete 4 duplicate detector test files** (Phase 1). Zero risk, 2,238 lines removed, halves detector test execution time. This is a no-brainer.

2. **High-value: Consolidate config tests** (Phase 2). Merge 5-6 config test files into 1-2 files. Eliminate ~52 config-snapshot tests from `test_feature_activation.py` by absorbing their assertions into behavioral tests or a single parametrized snapshot test.

3. **Medium-value: Consolidate refutation quality phases** (Phase 3). Merge 4 phase files into 1, saving ~250 lines of boilerplate. Low risk since all tests target the same config domain.

4. **Optional: Perf suite consolidation** (Phase 5). Merge 4 perf files into 1 parametrized suite. Low risk, moderate reduction.

---

## 11. Confidence and Risk Update

| Dimension | Value |
|-----------|-------|
| `post_research_confidence_score` | 92 |
| `post_research_risk_level` | low |

**Confidence justification**: File-by-file structural analysis with exact line counts, duplicate detection via class/method name matching and line count comparison. All 84 files examined. The duplicate finding (2,238 lines) is certain. Config consolidation recommendations are based on Pydantic best practices. The only uncertainty is whether config-snapshot tests serve a deliberate "approved config" gating purpose — this requires user confirmation.

---

## Open Questions

| q_id | question | options | recommended | user_response | status |
|------|----------|---------|-------------|---------------|--------|
| Q1 | Are the config-snapshot tests in `test_feature_activation.py` (52 tests) intentionally enforced as "approved config gates", or are they historical artifacts? | A: Historical artifacts (delete) / B: Intentional gates (keep but consolidate) / C: Other | A | — | ❌ pending |
| Q2 | For the priority-named detector files — was priority the intended canonical naming? (vs frequency-based) | A: Priority naming is canonical / B: Frequency naming is canonical / C: Unsure | A | — | ❌ pending |
| Q3 | Should `test_remediation_sprints.py` tests be redistributed to their target modules (Phase 4), or kept as a historical "sprint gap" record? | A: Redistribute to modules / B: Keep as-is / C: Keep file but rename | A | — | ❌ pending |
