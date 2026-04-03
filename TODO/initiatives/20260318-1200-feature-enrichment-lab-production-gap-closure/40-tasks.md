# Tasks - OPT-1 Production Hardening First

## Dependency-Ordered Task Graph

| T-ID | title | scope_files | depends_on | parallel | status |
|---|---|---|---|---|---|
| T1 | Build objective evidence matrix | tools/puzzle-enrichment-lab/**, config/katago-enrichment.json, TODO/**/*.md | - | no | not_started |
| T2 | Confirm observability field trace | tools/puzzle-enrichment-lab/analyzers/observability.py; tools/puzzle-enrichment-lab/analyzers/stages/**; tools/puzzle-enrichment-lab/models/** | T1 | no | not_started |
| T3 | Remove obsolete legacy branches | tools/puzzle-enrichment-lab/analyzers/**; tools/puzzle-enrichment-lab/config/** | T2 | no | not_started |
| T4 | Add/adjust observability wiring tests | tools/puzzle-enrichment-lab/tests/test_*.py | T2 | [P] yes | not_started |
| T5 | Expand multi-orientation detector tests batch-1 | tools/puzzle-enrichment-lab/tests/test_detectors_*.py | T1 | [P] yes | not_started |
| T6 | Expand multi-orientation detector tests batch-2 | tools/puzzle-enrichment-lab/tests/test_detectors_*.py | T5 | [P] yes | not_started |
| T7 | Add player-impact regression fixtures | tools/puzzle-enrichment-lab/tests/fixtures/**; tools/puzzle-enrichment-lab/tests/test_*.py | T4,T6 | no | not_started |
| T8 | Execute player-impact quality validation | tools/puzzle-enrichment-lab/tests/**; sampled SGF outputs in lab runtime | T7 | no | not_started |
| T9 | Run non-mock regression + benchmark checks | tools/puzzle-enrichment-lab/tests/**; command scripts/docs | T3,T8 | no | not_started |
| T10 | Update architecture/how-to/reference docs | docs/architecture/tools/katago-enrichment.md; docs/how-to/tools/katago-enrichment-lab.md; docs/reference/enrichment-config.md | T3,T9 | [P] yes | not_started |
| T11 | Produce validation report and governance evidence | TODO/initiatives/20260318-1200-feature-enrichment-lab-production-gap-closure/60-validation-report.md; 70-governance-decisions.md; status.json | T8,T9,T10 | no | not_started |

## Parallel Groups

| PG-ID | tasks | rule |
|---|---|---|
| PG-1 | T4 + T5 | Can run in parallel after evidence/tracing baseline is defined |
| PG-2 | T6 + documentation prep notes | T6 may run while doc deltas are drafted, but final doc edits wait for T9 outcomes |
| PG-3 | T10 subtasks | Architecture/how-to/reference updates can be parallelized once validation outcomes are known |

## Legacy Removal Tasks (Explicit)

| LR-ID | task | rationale |
|---|---|---|
| LR-1 | T3 remove obsolete legacy branches/flags | No backward compatibility requirement; reduce dormant path risk |
| LR-2 | T10 remove stale doc references to superseded paths | Keep docs consistent with post-cleanup runtime |

## Validation Matrix

| VM-ID | check | command_or_method | owner_task |
|---|---|---|---|
| VM-1 | Enrichment lab non-slow suite | `pytest tools/puzzle-enrichment-lab/tests/ --ignore=tests/test_golden5.py --ignore=tests/test_calibration.py --ignore=tests/test_ai_solve_calibration.py -m "not slow" -q --no-header --tb=short` | T9 |
| VM-2 | Targeted detector regression | `pytest tools/puzzle-enrichment-lab/tests/test_detectors_*.py -q --no-header --tb=short` | T6,T9 |
| VM-3 | Config parsing/sanity | `pytest tools/puzzle-enrichment-lab/tests/test_config*.py -q --no-header --tb=short` | T3,T9 |
| VM-4 | Player-impact sample review | Structured sample checklist in validation report | T8,T11 |

## Deliverables

| DEL-ID | artifact | produced_by |
|---|---|---|
| DEL-1 | Updated hardening code and tests | T3-T7 |
| DEL-2 | Updated docs (architecture/how-to/reference) | T10 |
| DEL-3 | Validation report and final governance package | T11 |
