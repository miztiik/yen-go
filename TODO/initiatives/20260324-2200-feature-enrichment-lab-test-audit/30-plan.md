# Plan — Enrichment Lab Test Audit Phase 2

> Last Updated: 2026-03-24
> Selected Option: **OPT-1 — Phased Consolidation (Conservative)**
> Governance Status: GOV-OPTIONS-CONDITIONAL

## Architecture & Design Decisions

### Decision: 4-Phase Execution

Each phase is an independent commit with `pytest --co -q` count verification. Phases can be rolled back individually via `git revert`.

### Decision: Q2=A — Full Deletion of test_feature_activation.py

User overrides governance recommendation (GV-2, GV-7) to keep C9 guards. RC-5 requires transitive coverage verification before Phase 2 execution.

### Decision: Q5=B — Config Tests → 2 Files

Config tests consolidate into:
- `test_config_loading.py` — tests that configs parse, files exist, schemas validate
- `test_config_values.py` — tests that specific config values match expectations (thresholds, level IDs, etc.)

---

## Phase 1: Delete 4 Duplicate Detector Files

**Risk**: Zero
**Commit message**: `refactor(tests): delete 4 duplicate detector test files (frequency-based naming)`

| Action | File | Reason |
|--------|------|--------|
| DELETE | test_detectors_common.py | Exact duplicate of test_detectors_priority2.py |
| DELETE | test_detectors_high_frequency.py | Exact duplicate of test_detectors_priority1.py |
| DELETE | test_detectors_intermediate.py | Exact duplicate of test_detectors_priority3.py |
| DELETE | test_detectors_lower_frequency.py | Exact duplicate of test_detectors_priority4_5_6.py |

**Verification**: `pytest --co -q` count drops by exactly 87 (the duplicate tests). All remaining tests pass.

---

## Phase 2: Delete test_feature_activation.py

**Risk**: Low
**Pre-condition**: RC-5 — verify and document C9 transitive coverage in execution log
**Commit message**: `refactor(tests): delete test_feature_activation.py (YAGNI config snapshots)`

| Action | File | Reason |
|--------|------|--------|
| DELETE | test_feature_activation.py | 52 config snapshot tests — pure YAGNI per Q2=A |

**Verification**: `pytest --co -q` count drops by exactly 52. All remaining tests pass.

---

## Phase 3: Merge Refutation Quality Phases A-D → 1 File

**Risk**: Low
**Commit message**: `refactor(tests): consolidate refutation quality phases A-D into single file`

| Action | Source | Target | Detail |
|--------|--------|--------|--------|
| CREATE | — | test_refutation_quality.py | New unified file |
| MERGE | test_refutation_quality_phase_a.py | → test_refutation_quality.py | Classes: TestOwnershipDelta, TestScoreDeltaFilter, TestModelRouting, TestConfigParsing, TestOpponentResponse |
| MERGE | test_refutation_quality_phase_b.py | → test_refutation_quality.py | Classes: TestAdaptiveVisitAllocation, TestDirichletNoise, TestForcedMinVisits, TestAlternativeExploration |
| MERGE | test_refutation_quality_phase_c.py | → test_refutation_quality.py | Classes: TestBranchEscalation, TestDiversifiedHarvesting, TestBestResistance |
| MERGE | test_refutation_quality_phase_d.py | → test_refutation_quality.py | Classes: TestSurpriseWeightedCalibration |
| DELETE | test_refutation_quality_phase_a.py | — | Absorbed into merged file |
| DELETE | test_refutation_quality_phase_b.py | — | Absorbed into merged file |
| DELETE | test_refutation_quality_phase_c.py | — | Absorbed into merged file |
| DELETE | test_refutation_quality_phase_d.py | — | Absorbed into merged file |

**Shared boilerplate**: Single `_clear_caches` autouse fixture at module level instead of 4 duplicates.

**VS Code tasks**: User-level workspace tasks (`RC-targeted-regression`, `RC-clean-regression`) reference individual phase files. These need manual user update to point to `test_refutation_quality.py`.

**Verification**: `pytest --co -q` count unchanged (same test classes, new file location). All tests pass.

---

## Phase 4: Consolidate Config Test Files → 2 Files

**Risk**: Low
**Commit message**: `refactor(tests): consolidate 6 config test files into 2 (loading + values)`

### Target: test_config_loading.py

Tests that verify config infrastructure works (parsing, file existence, schema validation):

| Source File | Classes/Tests to Migrate |
|-------------|------------------------|
| test_enrichment_config.py | Config file loading, JSON parsing, Pydantic validation tests |
| test_deep_enrich_config.py | DeepEnrichConfig loading, defaults |
| test_tsumego_config.py | KataGo config file parsing |
| test_teaching_comments_config.py | Teaching config loading, tag coverage |
| test_ai_solve_config.py | AiSolveConfig loading, round-trip serialization |

### Target: test_config_values.py

Tests that verify specific config values match expectations:

| Source File | Classes/Tests to Migrate |
|-------------|------------------------|
| test_enrichment_config.py | Threshold values, level IDs, ownership regions, rank bands |
| test_deep_enrich_config.py | Visit counts, model defaults |
| test_ai_solve_config.py | Threshold defaults (t_good, t_bad, etc.), depth profiles |
| test_teaching_comments_config.py | Word limits, required fields |

### Files NOT merged (kept separate)

| File | Reason |
|------|--------|
| test_config_lookup.py | Tests actual lookup logic with edge cases, not config parsing |
| test_bridge_config.py | Tests distinct utility module (unflatten, deep_merge), not Pydantic models |
| test_visit_tiers.py | Tests visit tier wiring into stages, not just config values |

**Verification**: `pytest --co -q` count unchanged. All tests pass.

---

## Risks & Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| Import errors in merged files | Low | Verify imports compile before running tests |
| Fixture isolation broken in merged file | Low | Preserve autouse cache-clearing fixtures at class level |
| tests.json references stale | Low | Document required user-level task updates |
| Loss of C9 threshold explicit guards | Medium | RC-5: verify transitive coverage before Phase 2 |

---

## Documentation Plan

| files_to_update | why_updated |
|----------------|-------------|
| tools/puzzle-enrichment-lab/AGENTS.md | Test section references new file names |

| files_to_create | why_created |
|----------------|-------------|
| None | — |

### Cross-References
- [Prior initiative](../20260322-1400-refactor-enrichment-lab-test-consolidation/00-charter.md) — Sprint files, sys.path DRY
- [Research brief](../20260324-research-enrichment-lab-test-audit/15-research.md) — Full 84-file audit
