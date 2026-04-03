# Analysis — Enrichment Lab Test Audit (Phase 2)

> Last Updated: 2026-03-24
> Planning Confidence Score: **92**
> Risk Level: **low**
> Research Invoked: **yes** (Feature-Researcher + Governance-Panel with KataGo experts)

## 1. Findings

| F-ID | Severity | Category | Finding | Files |
|------|----------|----------|---------|-------|
| F-1 | **CRITICAL** | DRY | 4 detector test files are exact byte-identical duplicates of 4 other files. Both copies run, doubling execution time. | test_detectors_common.py ≡ test_detectors_priority2.py, test_detectors_high_frequency.py ≡ test_detectors_priority1.py, test_detectors_intermediate.py ≡ test_detectors_priority3.py, test_detectors_lower_frequency.py ≡ test_detectors_priority4_5_6.py |
| F-2 | **HIGH** | YAGNI | 52 config snapshot tests in `test_feature_activation.py` assert hardcoded default values. Break on every intentional config change. No behavioral coverage beyond what phase tests already provide. | test_feature_activation.py |
| F-3 | **MODERATE** | DRY | 4 refutation quality phase files (A-D) share identical `_clear_caches` autouse fixture, import boilerplate, and config loading pattern. | test_refutation_quality_phase_{a,b,c,d}.py |
| F-4 | **MODERATE** | YAGNI | Config test files include `test_config_file_exists()`, `test_config_loads_valid_json()`, `hasattr()` tests — Pydantic already validates these. | test_enrichment_config.py |
| F-5 | **MODERATE** | DRY | Mock AnalysisResponse builder (`_make_response()`) re-implemented in 4+ files instead of shared fixture. | test_refutations.py, test_ai_solve_remediation.py, test_dual_engine.py, test_solve_position.py |
| F-6 | **LOW** | KISS | Phase-based file splitting (A/B/C/D) when one file with class sections suffices. | test_refutation_quality_phase_{a,b,c,d}.py |
| F-7 | **LOW** | KISS | "Implementation review" naming — file named for when it was created, not what it tests. | test_implementation_review.py |
| F-8 | **LOW** | SOLID | Mixed concerns in `test_enrichment_config.py` — tests loading, thresholds, level IDs, ownership regions, rank bands, confidence reasons, PV caps all in one file. | test_enrichment_config.py |
| F-9 | **INFO** | Stale refs | `.vscode/tasks.json` task `RC-targeted-regression` references individual phase files by name. | .vscode/tasks.json |

## 2. Coverage Map

| Aspect | Current | After Phase 1 (deletes) | After All Phases |
|--------|---------|------------------------|-----------------|
| Test files | 84 | 80 | ~72 |
| Total lines | ~27,400 | ~25,162 | ~22,100 |
| Test functions | ~1,700 | ~1,613 | ~1,550 |
| Duplicate test runs | ~87 | 0 | 0 |
| Lines removed | — | 2,238 | ~5,300 |

## 3. Ripple-Effects Analysis

| impact_id | direction | area | risk | mitigation | owner_task | status |
|-----------|-----------|------|------|------------|------------|--------|
| RE-1 | lateral | .vscode/tasks.json | Medium | Update task refs in same commit as file changes | T-tasks-update | ❌ needs action |
| RE-2 | lateral | AGENTS.md test section | Low | Update after consolidation | T-agents-update | ❌ needs action |
| RE-3 | downstream | pytest -m "not slow" command | Low | Verify marker preservation | T-verify-markers | ❌ needs action |
| RE-4 | lateral | conftest.py shared fixtures | Low | F-5 mock builder DRY — out of scope for this initiative | — | ⏭️ deferred (F-5 out of scope) |
| RE-5 | upstream | config/katago-enrichment.json | None | No config changes — test-only initiative | — | ✅ addressed |
| RE-6 | downstream | CI pipeline test selection | Low | Same markers, same --ignore patterns — verified by phase gates | — | ✅ addressed |

## 4. Unmapped Tasks

None — all findings map to concrete consolidation phases.

## 5. Superseded Tests Summary

| File | Superseded By | Action |
|------|--------------|--------|
| test_detectors_common.py | test_detectors_priority2.py | DELETE |
| test_detectors_high_frequency.py | test_detectors_priority1.py | DELETE |
| test_detectors_intermediate.py | test_detectors_priority3.py | DELETE |
| test_detectors_lower_frequency.py | test_detectors_priority4_5_6.py | DELETE |
| test_feature_activation.py (47/52 tests) | test_refutation_quality_phase_{a,b,c,d}.py behavioral tests | Reduce to C9 guards only |
