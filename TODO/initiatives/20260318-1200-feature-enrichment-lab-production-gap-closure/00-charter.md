# Charter - Enrichment Lab Production Gap Closure

## Goals

| goal_id | goal | success_criteria |
|---|---|---|
| G1 | Build a production-final objective matrix for enrichment lab capabilities vs research/plans | Every in-scope objective is labeled `fully_met`, `partially_met`, `not_met`, or `superseded` with code+tests+config evidence |
| G2 | Identify accretive, low-regression improvements for final production run | At least 2 and at most 4 improvements with clear implementation path and measurable verification |
| G3 | Reassess deferred NG findings (NG-1..NG-5) under updated user direction | NG table with accept/defer rationale and explicit decision for each item |
| G4 | Produce executor-ready plan/tasks package with governance sign-off | `30-plan.md`, `40-tasks.md`, `70-governance-decisions.md` approved with no blocking items |

## Non-Goals

| ng_id | non_goal | rationale |
|---|---|---|
| NG-1 | Re-architecting backend pipeline or frontend runtime | This initiative is enrichment-lab production gap closure only |
| NG-2 | Introducing new runtime browser AI components in frontend | Out of scope for this feature package and increases release risk |
| NG-3 | Large taxonomy expansion in `config/tags.json` | User deprioritized NG-4 unless extraordinary evidence |
| NG-4 | Multi-week speculative research without executable task graph | User requested final run readiness, not open-ended exploration |
| NG-5 | MVP-only partial delivery | Planning output must cover full approved scope |

## Constraints

| constraint_id | constraint |
|---|---|
| C1 | Backward compatibility not required; legacy code removal is allowed and expected |
| C2 | Functional objective closure requires code + tests + config fully wired (no mock-only closure) |
| C3 | Architecture boundaries remain: changes scoped to tools/puzzle-enrichment-lab unless cross-module dependency is mandatory |
| C4 | Governance gates required: charter preflight, option election, plan review |
| C5 | All tables must keep row identifiers for governance traceability |

## Acceptance Criteria

| ac_id | acceptance_criterion | verification |
|---|---|---|
| AC1 | Objective matrix includes all high-impact enrichment sources requested by user | Source coverage table in research/analysis |
| AC2 | Option set includes at least 2 meaningful alternatives with tradeoffs | `25-options.md` complete and governance-reviewed |
| AC3 | Selected option includes clear rollback + risk mitigation + docs plan | `30-plan.md` sections present and non-empty |
| AC4 | Tasks are dependency-ordered, parallel-marked, and file-scoped | `40-tasks.md` task table complete |
| AC5 | Ripple-effects table maps each non-trivial impact to owner task IDs | `20-analysis.md` includes impact table with status |

## Research Decision Questions

| dq_id | decision_question | why_it_matters | mapped_acceptance |
|---|---|---|---|
| DQ-1 | Which accretive features should ship in production-final pass: hardening-first or signal-expansion-first? | Determines option quality and regression exposure | AC2, AC3 |
| DQ-2 | Can NG-3 be promoted as debug-only observability without violating scope constraints? | Decides whether multi-layer evidence output is in-scope now | AC2, AC5 |
| DQ-3 | Should objective closure require at least one non-mock benchmark artifact in addition to tests? | Aligns execution verification depth with user quality bar | AC3, AC4 |
| DQ-4 | What is the minimum documentation update set required for production-final handoff? | Prevents implementation without updated architecture/how-to/reference parity | AC3, AC4 |

## User Decisions (Binding)

| decision_id | decision | source |
|---|---|---|
| D1 | No backward compatibility; remove old code | Q1 |
| D2 | Planning-only package (no implementation in this initiative) | Q2 |
| D3 | Evaluate NG-1..NG-5, but NG-4 stays low priority | Q3 |
| D4 | Completion standard is fully wired code+tests+config, not document-only | Q4 |
| D5 | Use content-level synthesis from TODO/docs corpus | Q5 |
| D6 | Use GPT-5.3-Codex model path for research/coordination where available | Q6 |
