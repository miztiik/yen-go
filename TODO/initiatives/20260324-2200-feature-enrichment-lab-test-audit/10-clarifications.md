# Clarifications — Enrichment Lab Test Audit (Phase 2)

> Last Updated: 2026-03-24

## Clarification Table

| q_id | question | options | recommended | user_response | status |
|------|----------|---------|-------------|---------------|--------|
| Q1 | Is backward compatibility required? Should old detector files be preserved? | A: Delete old files / B: Keep both / C: Deprecate with warning | A: Delete — they are exact duplicates | Delete old files | ✅ resolved |
| Q2 | Should `test_feature_activation.py` be fully deleted or reduced to C9 invariant guards? | A: Delete entirely / B: Keep C9 guards only / C: Keep all | B: Keep only `TestThresholdConservation` class (C9 invariants t_good, t_bad, t_hotspot) per Governance GV-2/GV-7 recommendation | **A: Delete entirely** | ✅ resolved |
| Q3 | Keep perf test files separate or merge? | A: Merge into parametrized suite / B: Keep separate | B: Keep separate — Governance panel (GV-3, GV-9) ruled each scale tests different convergence regimes | Keep separate | ✅ resolved |
| Q4 | Redistribute `test_remediation_sprints.py` (now `test_ai_solve_remediation.py`)? | A: Redistribute to module tests / B: Keep as-is | B: Keep as-is — already renamed in prior initiative, redistribution is NG5 (deferred) | Keep as-is | ✅ resolved |
| Q5 | How to handle config test consolidation? | A: Merge 6 files → 1 / B: Merge 6 files → 2 (loading + values) / C: Keep as-is | B: Merge into `test_config_loading.py` + `test_config_values.py` | **B: Merge → 2 files** | ✅ resolved |

## Key Decisions from Prior Work

| Decision | Source | Impact |
|----------|--------|--------|
| Priority-based detector naming is canonical | Governance GV-1, GV-10 | Delete frequency-named files |
| Perf files kept separate | Governance GV-3, GV-9 (Dr. David Wu) | No merge — different convergence regimes |
| `TestThresholdConservation` preserved | Governance GV-2 (Lee Sedol), GV-7 (Hana Park) | C9 invariant guards survive any consolidation |
| Phase files NG1 was explicitly excluded from prior initiative | Prior initiative 20260322-1400 | Now IN scope for this initiative |
