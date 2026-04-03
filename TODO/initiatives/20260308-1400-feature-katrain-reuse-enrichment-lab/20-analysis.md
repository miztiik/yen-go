# Analysis: KA Train Reuse for Enrichment Lab

**Last Updated:** 2026-03-08

## Planning Confidence and Risk

| analysis_id | metric | value | notes |
|---|---|---|---|
| A1 | planning_confidence_score | 88 | Increased after Feature-Researcher evidence capture in `15-research.md`. |
| A2 | risk_level | low | Narrowed strategy avoids Kivy-coupled modules and favors pure-function ports. |
| A3 | research_invoked | true | Mandatory trigger satisfied earlier due pre-research uncertainty. |

## Cross-Artifact Consistency Findings

| finding_id | severity | finding | impact | required_action | status |
|---|---|---|---|---|---|
| F1 | high | KA Train engine/game modules are Kivy-coupled, so direct vendoring is unsafe for enrichment-lab runtime | Would violate architecture constraints and increase dependency risk | Keep these modules explicitly out-of-scope in plan/tasks | ✅ addressed |
| F2 | medium | Existing local `tsumego_frame` appears to omit KA Train flip normalization and ko-threat patterning | Potential correctness gap in non-corner/ko contexts | Add parity-first gate and regression fixtures before replacement | ✅ addressed |
| F3 | low | `var_to_grid` is exact reusable utility but optional for current functionality | Possible over-scoping if forced | Keep as conditional task with explicit decision point | ✅ addressed |
| F4 | medium | Replacement-first without compatibility requires delta-preservation proof | Functional delta may be lost if not codified | Add delta assertions and deletion gate in tasks | ✅ addressed |
| F5 | low | Documentation/provenance could be missed despite technical completion | Governance/legal debt risk | Include explicit docs + MIT attribution tasks | ✅ addressed |

## Coverage Map (Charter -> Plan -> Tasks)

| coverage_id | charter_or_constraint | plan_reference | task_trace | status |
|---|---|---|---|---|
| COV-1 | Reuse 1:1 KA Train backend logic | `30-plan.md` AD-2 | T7,T10 | ✅ covered |
| COV-2 | No backward compatibility required | `30-plan.md` constraints + rollout | T9,CS-1 | ✅ covered |
| COV-3 | Preserve enrichment-lab delta | `30-plan.md` AD-5 | T6,T7,CS-2 | ✅ covered |
| COV-4 | Exclude UI/Kivy scope | `30-plan.md` AD-1 + constraints | T2 | ✅ covered |
| COV-5 | Mandatory areas evaluation and recommendation | `15-research.md`, `25-options.md` | T14 evidence pack | ✅ covered |
| COV-6 | MIT attribution obligations | `30-plan.md` AD-6 + docs plan | T8,T13 | ✅ covered |

## Unmapped Tasks Check

| task_check_id | result | notes |
|---|---|---|
| U1 | no_unmapped_tasks | All tasks T1-T14 map to a charter goal, risk mitigation, governance condition, or validation obligation. |

## Ripple-Effects Scan (Final Pre-Plan-Review)

| impact_id | direction(upstream|downstream|lateral) | area | risk | mitigation | owner_task | status |
|---|---|---|---|---|---|---|
| IMP-1 | upstream | KA Train MIT source provenance | Missing attribution when porting functions | Attribution comments + docs update with source mapping | T8,T13 | ✅ addressed |
| IMP-2 | upstream | KA Train algorithm assumptions (axis orientation) | Wrong x/y mapping can corrupt frame placement | Coordinate contract tests + parity fixtures | T3,T4 | ✅ addressed |
| IMP-3 | downstream | `analyzers/enrich_single.py` frame invocation behavior | Behavior shift on small boards or ko cases | Board-size/ko regression fixtures and pipeline checks | T5,T11,T12 | ✅ addressed |
| IMP-4 | downstream | Difficulty/solve outputs | Indirect drift if frame changes alter upstream context | Keep scope narrow; validate with solver/enrich regression suites | T11,T12 | ✅ addressed |
| IMP-5 | lateral | `engine/local_subprocess.py` and async API | Accidental refactor into Kivy-coupled patterns | Explicit non-goal and no-touch guardrails | T2 | ✅ addressed |
| IMP-6 | lateral | Tests/docs/governance traceability | Incomplete evidence may block final approval | Evidence pack update and governance ledger updates | T14 | ✅ addressed |
