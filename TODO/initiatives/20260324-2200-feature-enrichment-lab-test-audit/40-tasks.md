# Tasks — Enrichment Lab Test Audit Phase 2

> Last Updated: 2026-03-24
> Selected Option: OPT-1 — Phased Consolidation

## Task Dependency Graph

```
T1 ──→ T2 ──→ T3 ──→ T4 ──→ T5
 │       │
 │      RC-5
 └──→ [P] T6 (parallel with any phase)
```

---

## Phase 1: Delete 4 Duplicate Detector Files

| Task | Title | Files | Depends | Parallel | Done Criteria |
|------|-------|-------|---------|----------|--------------|
| T1 | Delete 4 frequency-named detector test files | test_detectors_common.py, test_detectors_high_frequency.py, test_detectors_intermediate.py, test_detectors_lower_frequency.py | — | — | Files deleted. `pytest --co -q` count drops by 87. `pytest tests/ -m "not slow" --ignore=...` green. |

---

## Phase 2: Delete test_feature_activation.py

| Task | Title | Files | Depends | Parallel | Done Criteria |
|------|-------|-------|---------|----------|--------------|
| T2-RC5 | Verify C9 transitive coverage | test_refutation_quality_phase_a.py (search for t_good, t_bad, t_hotspot assertions) | T1 | — | Document in execution log: which test functions exercise C9 thresholds transitively. If none, log gap for user awareness. |
| T2 | Delete test_feature_activation.py | test_feature_activation.py | T2-RC5 | — | File deleted. `pytest --co -q` count drops by 52. All tests pass. |

---

## Phase 3: Merge Refutation Quality Phases

| Task | Title | Files | Depends | Parallel | Done Criteria |
|------|-------|-------|---------|----------|--------------|
| T3a | Create test_refutation_quality.py with shared fixture | (new file) | T2 | — | File created with single `_clear_caches` autouse fixture, shared imports |
| T3b | Merge Phase A classes into test_refutation_quality.py | test_refutation_quality_phase_a.py → test_refutation_quality.py | T3a | — | Classes: TestOwnershipDelta, TestScoreDeltaFilter, TestModelRouting, TestConfigParsing, TestOpponentResponse |
| T3c | Merge Phase B classes | test_refutation_quality_phase_b.py → test_refutation_quality.py | T3b | — | Classes: TestAdaptiveVisitAllocation, TestDirichletNoise, TestForcedMinVisits, TestAlternativeExploration |
| T3d | Merge Phase C classes | test_refutation_quality_phase_c.py → test_refutation_quality.py | T3c | — | Classes: TestBranchEscalation, TestDiversifiedHarvesting, TestBestResistance |
| T3e | Merge Phase D classes | test_refutation_quality_phase_d.py → test_refutation_quality.py | T3d | — | Classes: TestSurpriseWeightedCalibration |
| T3f | Delete 4 old phase files | test_refutation_quality_phase_{a,b,c,d}.py | T3e | — | Old files deleted. `pytest --co -q` count unchanged. All tests pass. |

---

## Phase 4: Consolidate Config Tests

| Task | Title | Files | Depends | Parallel | Done Criteria |
|------|-------|-------|---------|----------|--------------|
| T4a | Create test_config_loading.py with infrastructure tests | (new file) ← test_enrichment_config.py, test_deep_enrich_config.py, test_tsumego_config.py, test_teaching_comments_config.py, test_ai_solve_config.py | T3f | — | File exists with loading/parsing/schema tests from all 5 sources |
| T4b | Create test_config_values.py with value assertion tests | (new file) ← same 5 source files | T4a | — | File exists with threshold/default-value tests from all 5 sources |
| T4c | Delete 5 old config test files | test_enrichment_config.py, test_deep_enrich_config.py, test_tsumego_config.py, test_teaching_comments_config.py, test_ai_solve_config.py | T4b | — | Old files deleted. `pytest --co -q` count unchanged. All tests pass. |

---

## Cross-Cutting Tasks

| Task | Title | Files | Depends | Parallel | Done Criteria |
|------|-------|-------|---------|----------|--------------|
| T5 | Update AGENTS.md test section | tools/puzzle-enrichment-lab/AGENTS.md | T4c | — | Test file references match new names |
| T6 | Document VS Code task updates needed | (execution log) | — | [P] any phase | Note which user-level workspace tasks reference deleted/renamed files |

---

## Summary

| Metric | Value |
|--------|-------|
| Total tasks | 13 |
| Files deleted | 14 (4 duplicates + 1 feature_activation + 4 phase files + 5 config files) |
| Files created | 3 (test_refutation_quality.py + test_config_loading.py + test_config_values.py) |
| Net file reduction | 84 → 73 |
| Parallel tasks | T6 only |
| Must-hold constraints | MH-1 through MH-6 from governance |

### File Count Arithmetic

| Phase | Start | Deleted | Created | End |
|-------|-------|---------|---------|-----|
| 1 | 84 | 4 | 0 | 80 |
| 2 | 80 | 1 | 0 | 79 |
| 3 | 79 | 4 | 1 | 76 |
| 4 | 76 | 5 | 2 | 73 |
| **Final** | | **14 deleted** | **3 created** | **73** |
