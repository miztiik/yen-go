# Tasks: KA Train Reuse for Enrichment Lab (OPT-1)

**Last Updated:** 2026-03-08

## Dependency-Ordered Checklist

- [ ] **T1** Confirm implementation baseline and collect frame fixtures (`tools/puzzle-enrichment-lab/tests/fixtures/**/*.sgf`, `tools/puzzle-enrichment-lab/tests/test_tsumego_frame.py`)
- [ ] **T2** Write scope guard tests/notes to enforce non-goals (no engine/rules vendoring) (`TODO/initiatives/20260308-1400-feature-katrain-reuse-enrichment-lab/30-plan.md`, `TODO/initiatives/20260308-1400-feature-katrain-reuse-enrichment-lab/20-analysis.md`)
- [ ] **T3** [P] Add parity harness tests for flip normalization and ko-threat expectations (`tools/puzzle-enrichment-lab/tests/test_tsumego_frame.py`)
- [ ] **T4** [P] Add coordinate-axis contract tests for KA Train adapter mapping (`tools/puzzle-enrichment-lab/tests/test_tsumego_frame.py`)
- [ ] **T5** Add regression fixtures for 9x9/13x13/19x19 and ko-tagged puzzles (`tools/puzzle-enrichment-lab/tests/fixtures/`, `tools/puzzle-enrichment-lab/tests/test_tsumego_frame.py`)
- [ ] **T6** Define and encode delta-preservation expectations before replacement (document + assertion tests) (`tools/puzzle-enrichment-lab/tests/test_tsumego_frame.py`, `TODO/initiatives/20260308-1400-feature-katrain-reuse-enrichment-lab/20-analysis.md`)
- [ ] **T7** Port KA Train pure frame helpers into adapter-aligned implementation (`tools/puzzle-enrichment-lab/analyzers/tsumego_frame.py`)
- [ ] **T8** Apply MIT attribution/provenance in code comments and docs (`tools/puzzle-enrichment-lab/analyzers/tsumego_frame.py`, `tools/puzzle-enrichment-lab/README.md`)
- [ ] **T9** Remove superseded legacy frame internals after parity gate is green (`tools/puzzle-enrichment-lab/analyzers/tsumego_frame.py`)
- [ ] **T10** [P] Evaluate whether `var_to_grid` utility is required and vendor only if used (`tools/puzzle-enrichment-lab/analyzers/`, `tools/puzzle-enrichment-lab/tests/`)
- [ ] **T11** Run focused unit tests for frame and solver integration (`tools/puzzle-enrichment-lab/tests/test_tsumego_frame.py`, `tools/puzzle-enrichment-lab/tests/test_enrich_single.py`, `tools/puzzle-enrichment-lab/tests/test_solve_position.py`)
- [ ] **T12** Run broader regression subset for enrichment-lab analyzers (`tools/puzzle-enrichment-lab/tests/`)
- [ ] **T13** Update reusable-how-to documentation for KA Train reuse policy and license checklist (`docs/how-to/backend/reuse-katrain-in-enrichment-lab.md`)
- [ ] **T14** Final governance evidence pack: update analysis coverage map + decisions + status (`TODO/initiatives/20260308-1400-feature-katrain-reuse-enrichment-lab/20-analysis.md`, `TODO/initiatives/20260308-1400-feature-katrain-reuse-enrichment-lab/70-governance-decisions.md`, `TODO/initiatives/20260308-1400-feature-katrain-reuse-enrichment-lab/status.json`)

## Dependency Graph

| task_id | depends_on | can_run_parallel | done_definition |
|---|---|---|---|
| T1 | - | No | Baseline behavior and fixtures cataloged |
| T2 | T1 | No | Scope constraints documented and traceable |
| T3 | T1 | Yes | Parity harness tests fail first (red) |
| T4 | T1 | Yes | Axis mapping tests fail first (red) |
| T5 | T1 | No | Fixture coverage extended for board-size/ko edge cases |
| T6 | T3,T4,T5 | No | Delta-preservation assertions documented and tested |
| T7 | T6 | No | Ported implementation compiles and test harness passes |
| T8 | T7 | No | Attribution text present in code and README |
| T9 | T7,T8 | No | Legacy internals removed without test regressions |
| T10 | T7 | Yes | Utility port decision documented; tests added if vendored |
| T11 | T9,T10 | No | Targeted tests all pass |
| T12 | T11 | No | Regression subset passes |
| T13 | T8 | No | How-to doc created with cross-references |
| T14 | T12,T13 | No | Artifacts updated for final governance review |

## Validation Matrix

| vm_id | validation_command | expected_result | tasks_covered |
|---|---|---|---|
| VM-1 | `python -m pytest tests/test_tsumego_frame.py -q --no-header` | All frame parity tests pass | T3,T4,T5,T6,T7,T9 |
| VM-2 | `python -m pytest tests/test_enrich_single.py tests/test_solve_position.py -q --no-header` | No pipeline regressions in key analyzers | T11 |
| VM-3 | `python -m pytest tests/ --cache-clear -x --tb=short -q --no-header` | Broader enrichment-lab regression green | T12 |

## Compatibility Strategy Tasks

| cs_id | strategy | task_trace |
|---|---|---|
| CS-1 | No backward compatibility path retained | T9 |
| CS-2 | Preserve non-matching functional delta before deletion | T6,T7 |
| CS-3 | Remove old code only after parity proof | T3,T4,T6,T9 |
