# Tasks — KataGo Enrichment Threshold Fine-Tuning

**Initiative**: 20260320-1600-feature-katago-enrichment-tuning
**Date**: 2026-03-20

---

## Task Graph

| T-ID | Task | File(s) | Depends | Parallel | Status |
|------|------|---------|---------|----------|--------|
| T1 | Update 14 config values in katago-enrichment.json | `config/katago-enrichment.json` | — | [P] | not_started |
| T2 | Add v1.26 changelog entry | `config/katago-enrichment.json` | T1 | — | not_started |
| T3 | Fix adaptive boost override in solve_position.py | `tools/puzzle-enrichment-lab/analyzers/solve_position.py` | — | [P] | not_started |
| T4 | Add test for adaptive+boost compounding | `tools/puzzle-enrichment-lab/tests/test_remediation_sprints.py` | T3 | — | not_started |
| T5 | Update AGENTS.md adaptive mode documentation | `tools/puzzle-enrichment-lab/AGENTS.md` | T3 | [P] | not_started |
| T6 | Run enrichment lab test suite | — | T1,T2,T3,T4,T5 | — | not_started |
| T7 | Run backend unit tests (regression) | — | T1 | — | not_started |

## Parallel Lane Plan

| lane_id | task_ids | scope_files | dependencies | status |
|---------|----------|-------------|--------------|--------|
| L1 | T1, T2 | `config/katago-enrichment.json` | none | not_started |
| L2 | T3, T4, T5 | `solve_position.py`, `test_remediation_sprints.py`, `AGENTS.md` | none | not_started |
| L3 | T6, T7 | (validation) | L1, L2 | not_started |

L1 and L2 have no file overlap — can execute in parallel.
L3 is the validation gate — sequential after L1+L2 merge.

## Detailed Task Descriptions

### T1: Update 14 config values
Changes to `config/katago-enrichment.json`:
1. `ai_solve.thresholds.t_good`: 0.05 → 0.03
2. `ai_solve.thresholds.t_bad`: 0.15 → 0.12
3. `ai_solve.thresholds.t_disagreement`: 0.10 → 0.07
4. `ai_solve.solution_tree.depth_profiles.entry.solution_min_depth`: 2 → 3
5. `ai_solve.solution_tree.depth_profiles.strong.solution_max_depth`: 28 → 24
6. `ai_solve.seki_detection.score_lead_seki_max`: 2.0 → 5.0
7. `ai_solve.goal_inference.score_delta_ko`: 5.0 → 7.0
8. `refutations.refutation_visits`: 100 → 200
9. `ai_solve.solution_tree.max_total_tree_queries`: 50 → 65
10. `ai_solve.solution_tree.continuation_visits`: 125 → 200
11. `refutations.candidate_max_count`: 5 → 6
12. `ai_solve.solution_tree.branch_disagreement_threshold`: 0.10 → 0.07
13. `validation.curated_pruning.min_depth`: 2 → 3
14. `calibration.sample_size`: 5 → 20

### T2: Add v1.26 changelog entry
Add changelog entry: "v1.26": "Tsumego threshold fine-tuning (4-expert consensus). ..."

### T3: Fix adaptive boost override
In `solve_position.py` ~L948: change adaptive mode to compound with boosts rather than replace.

### T4: Add tests for adaptive+boost interaction (RC-5)
New tests in `test_remediation_sprints.py`:
1. **adaptive+corner**: `visit_allocation_mode="adaptive"` + `corner_position="TL"` → `effective_visits = branch_visits * corner_visit_boost`
2. **adaptive+ladder**: `visit_allocation_mode="adaptive"` + `pv_length > threshold` → `effective_visits = branch_visits * ladder_visit_boost`
3. **adaptive+corner+ladder**: Both boosts compound with adaptive allocation
4. **fixed mode unchanged**: `visit_allocation_mode="fixed"` still applies boosts to `tree_visits` (no regression)

### T5: Update AGENTS.md
Correct the bullet point about "adaptive mode unconditionally sets effective_visits = branch_visits, discarding any boost" to reflect the new compounding behavior.

### T6: Run enrichment lab tests (RC-7)
`cd tools/puzzle-enrichment-lab && python -B -m pytest tests/ -m "not slow" --ignore=tests/test_golden5.py --ignore=tests/test_calibration.py --ignore=tests/test_ai_solve_calibration.py -q --no-header --tb=short -p no:cacheprovider`

**Potentially affected tests from threshold changes:**
- `tests/test_ai_solve_config.py` — Config loading assertions (sample_size, candidate_max_count)
- `tests/test_feature_activation.py` — PI-2 adaptive allocation assertions
- `tests/test_remediation_sprints.py` — Edge-case boost tests
- `tests/test_refutation_quality_phase_a.py` — Refutation visit assertions
- `tests/test_refutation_quality_phase_b.py` — Adaptive allocation assertions
- `tests/test_refutation_quality_phase_c.py` — Branch disagreement threshold assertions

### T7: Run backend unit tests
`pytest backend/ -m unit -q --no-header --tb=short`
