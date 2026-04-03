# Technical Plan - OPT-1 Production Hardening First

## Selected Option

| plan_id | selected_option | source_gate | status |
|---|---|---|---|
| PL-1 | OPT-1 Production Hardening First | GOV-OPTIONS-CONDITIONAL | ✅ selected |

## Architecture Plan

| arch_id | area | current_state | planned_change |
|---|---|---|---|
| A-1 | Enrichment observability path | Signals exist in multiple internal contexts; closure evidence inconsistent across artifacts | Normalize and verify end-to-end propagation of production-critical metrics through result and batch summary outputs |
| A-2 | Detector test rigor | Multi-orientation coverage is uneven | Expand and standardize orientation coverage to meet acceptance baseline |
| A-3 | Governance/doc closure | Planning and implementation records are fragmented across historical docs | Create production-final trace chain linking code/tests/config/docs/governance evidence |

## Data Model and Contract Impact

| dm_id | contract | impact | compatibility_policy |
|---|---|---|---|
| DM-1 | `AiAnalysisResult` and batch summary observability fields | Additive verification and wiring hardening; no consumer-facing breaking changes intended | No backward compatibility required globally, but output compatibility preserved unless explicit change approved |
| DM-2 | Test fixture contracts for detector orientation variants | Additive test fixtures/cases | Non-breaking |
| DM-3 | Governance/status artifacts | Planning metadata only | Non-runtime |

## Risks and Mitigations

| risk_id | risk | level | mitigation | owner_task |
|---|---|---|---|---|
| R-1 | Hardening may miss latent runtime behavior drift | medium | Add targeted regression matrix over enrichment-lab core flows and selected detector sets | T8, T9 |
| R-2 | Test expansion increases suite cost and maintenance burden | low | Use fixture reuse and bounded orientation matrix for priority detectors first | T5, T6 |
| R-3 | Documentation says complete while code wiring remains partial | medium | Require evidence matrix from code+tests+config before closure | T10, T11 |
| R-4 | Legacy path cleanup may remove still-used branches | medium | Perform symbol-usage audit before removal and verify with focused regression | T3, T9 |

## Rollout Strategy

| rollout_id | step | description | success_signal |
|---|---|---|---|
| RO-1 | Hardening changes first | Apply observability and test hardening before any optional signal expansion | Regression suite stable; evidence matrix complete |
| RO-2 | Validate with non-mock checks | Execute targeted non-mock verification commands and compare expected outputs | Player-impact and quality checks pass |
| RO-3 | Final governance check | Confirm all must-hold constraints and RCs satisfied | GOV-PLAN approved/conditional with no blockers |

## Rollback Strategy

| rollback_id | trigger | rollback_action |
|---|---|---|
| RB-1 | Metric/output drift detected | Revert latest hardening commit set for affected module and restore previous stable config values |
| RB-2 | Test flakiness or false positives introduced | Roll back newly added test paths in batches to isolate failing additions |
| RB-3 | Legacy cleanup causes regressions | Restore removed paths from git history and re-run usage audit before second removal pass |

## Player-Impact Validation (RC-2)

| pv_id | player-impact criterion | measurement | pass_condition | owner_task |
|---|---|---|---|---|
| PV-1 | Wrong-move guidance remains pedagogically coherent | Review sampled enriched SGFs for wrong-move comment/refutation ordering consistency | No degraded clarity vs baseline sample set | T8 |
| PV-2 | Difficulty/ambiguity indicators remain trustworthy | Compare selected puzzle subset difficulty signals before/after hardening | No unexplained regressions in rank/entropy-derived indicators | T8, T9 |
| PV-3 | Final run confidence for production release | Non-mock validation run and governance evidence consistency | All mandatory checks green and documented | T9, T11 |

## Constraints (Inherited)

| constraint_id | constraint |
|---|---|
| C1 | No backward compatibility path required |
| C2 | Completion requires fully wired code+tests+config evidence |
| C3 | Scope centered on tools/puzzle-enrichment-lab |
| C4 | NG-4 remains out unless extraordinary evidence |
| C5 | Governance and traceability artifacts are mandatory |

## Documentation Plan

### files_to_update

| doc_id | file | why_updated |
|---|---|---|
| D-1 | docs/architecture/tools/katago-enrichment.md | Reflect production-final hardening architecture and observability closure |
| D-2 | docs/how-to/tools/katago-enrichment-lab.md | Add verification workflow for hardening-first production run |
| D-3 | docs/reference/enrichment-config.md | Confirm active config fields used in hardening scope and remove stale ambiguity |
| D-4 | TODO/ai-solve-enrichment-plan-v3.md | Add production-final status cross-reference to this initiative |

### files_to_create

| docc_id | file | why_created |
|---|---|---|
| DC-1 | TODO/initiatives/20260318-1200-feature-enrichment-lab-production-gap-closure/60-validation-report.md | Structured evidence report for objective closure |

### cross_references

| xref_id | related_doc | purpose |
|---|---|---|
| X-1 | docs/architecture/backend/enrichment.md | Ensure terminology parity for enrichment outputs |
| X-2 | docs/concepts/quality.md | Keep quality/AC semantics aligned with hardening outputs |
| X-3 | docs/reference/katago-enrichment-config.md | Validate config reference consistency |
