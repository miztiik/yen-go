# Governance Decisions: KA Train Reuse for Enrichment Lab

**Last Updated:** 2026-03-08

## Charter Preflight — GOV-CHARTER-APPROVED

**Gate:** charter-review  
**Decision:** approve  
**Status Code:** GOV-CHARTER-APPROVED  
**Unanimous:** Yes (6/6)

### Selected Option Placeholder

| field | value |
|---|---|
| option_id | PENDING |
| title | Pending Options Election |
| selection_rationale | Charter mode approved scope and constraints; options election required next. |

### Must-Hold Constraints

| constraint_id | constraint |
|---|---|
| C-1 | No backward compatibility layer required; replacement-first for 1:1 KA Train matches. |
| C-2 | Preserve enrichment-lab-specific deltas for partial/mismatch areas before deleting old code. |
| C-3 | Scope restricted to KA Train non-UI backend/core/ai/rules/utils. |
| C-4 | Mandatory evaluation areas: frame/border, legal rules validation, ELO/strength relevance, search heuristics, SGF parsing. |
| C-5 | Do not introduce Kivy/UI dependencies into enrichment-lab runtime. |
| C-6 | MIT attribution and provenance obligations are required for reused KA Train code. |

### Panel Support

| review_id | member | domain | vote | supporting_comment | evidence |
|---|---|---|---|---|---|
| GV-1 | Cho Chikun (9p, Meijin) | Classical tsumego authority | approve | Charter preserves tsumego correctness by requiring delta preservation where KA Train is partial. | `TODO/initiatives/20260308-1400-feature-katrain-reuse-enrichment-lab/00-charter.md` |
| GV-2 | Lee Sedol (9p) | Intuitive fighter | approve | Replacement-first policy is actionable and avoids over-engineering. | `TODO/initiatives/20260308-1400-feature-katrain-reuse-enrichment-lab/10-clarifications.md` |
| GV-3 | Shin Jinseo (9p) | AI-era professional | approve | Research adequately captures Kivy coupling and practical integration boundaries. | `TODO/initiatives/20260308-1400-feature-katrain-reuse-enrichment-lab/15-research.md` |
| GV-4 | Ke Jie (9p) | Strategic thinker | approve | Goals and acceptance criteria align with learning-value and engineering simplification. | `TODO/initiatives/20260308-1400-feature-katrain-reuse-enrichment-lab/00-charter.md` |
| GV-5 | Principal Staff Engineer A | Systems architect | approve | Scope, constraints, and non-goals are explicit and testable. | `TODO/initiatives/20260308-1400-feature-katrain-reuse-enrichment-lab/00-charter.md` |
| GV-6 | Principal Staff Engineer B | Data pipeline engineer | approve | Confidence/risk quantification is sufficient to proceed to options. | `TODO/initiatives/20260308-1400-feature-katrain-reuse-enrichment-lab/status.json` |

### Handover

| field | value |
|---|---|
| from_agent | Governance-Panel |
| to_agent | Feature-Planner |
| message | Proceed to options drafting with 2-3 alternatives, explicit tradeoff matrix, and replacement-first + delta-preservation constraints. |
| required_next_actions | Create `25-options.md`; include ripple/policy impact; run options governance election; update `status.json`. |
| artifacts_to_update | `25-options.md`, `20-analysis.md`, `status.json`, `70-governance-decisions.md` |
| blocking_items | None |

### Support Summary

Charter scope, constraints, and clarification decisions are complete and coherent. Research uncertainty is bounded and non-blocking for options drafting.

### Tiny Status JSON

```json
{
	"gate": "charter-review",
	"decision": "approve",
	"status_code": "GOV-CHARTER-APPROVED",
	"unanimous": true,
	"next_agent": "Feature-Planner"
}
```

## Options Election — GOV-OPTIONS-CONDITIONAL

**Gate:** options-review  
**Decision:** approve_with_conditions  
**Status Code:** GOV-OPTIONS-CONDITIONAL  
**Unanimous:** No

### Selected Option

| field | value |
|---|---|
| option_id | OPT-1 |
| title | Targeted Algorithm Port (Frame+Utilities) |
| selection_rationale | Highest weighted score (8.7/10), strongest policy compliance, and best alignment with replacement-first + delta-preservation strategy. |

### Required Conditions

| rc_id | required_condition | blocking | verification |
|---|---|---|---|
| RC-1 | Plan must include parity-first test gate for frame flip/ko-threat behavior. | No | `30-plan.md` contains parity gate and acceptance checks. |
| RC-2 | Plan/tasks must include MIT attribution handling for ported KA Train code and doc updates. | No | `30-plan.md` + `40-tasks.md` doc/attribution tasks present. |
| RC-3 | Plan must explicitly keep Kivy-coupled engine/rules migration out of scope. | No | Scope/guardrails in plan and tasks. |
| RC-4 | Options election must be persisted in `status.json` and traced in governance log. | Yes | `status.json` `selected_option_id=OPT-1` and this section appended. |

### Panel Support

| review_id | member | domain | vote | supporting_comment | evidence |
|---|---|---|---|---|---|
| GV-1 | Cho Chikun (9p, Meijin) | Classical tsumego authority | concern | Needs deterministic parity proof for corner normalization and ko-threat behavior before replacement. | `15-research.md`, `25-options.md` |
| GV-2 | Lee Sedol (9p) | Intuitive fighter | approve | OPT-1 has highest practical benefit and lowest migration risk. | `25-options.md` |
| GV-3 | Shin Jinseo (9p) | AI-era professional | concern | Requires explicit solver-impact validation after frame parity port. | `20-analysis.md` |
| GV-4 | Ke Jie (9p) | Strategic thinker | approve | Strongest learning-value to complexity ratio among options. | `25-options.md` |
| GV-5 | Principal Staff Engineer A | Systems architect | concern | Governance traceability must be written to status + ledger before plan gate. | `status.json`, `70-governance-decisions.md` |
| GV-6 | Principal Staff Engineer B | Data pipeline engineer | approve | Keeps blast radius narrow and rollback path simple. | `20-analysis.md`, `25-options.md` |

### Handover

| field | value |
|---|---|
| from_agent | Governance-Panel |
| to_agent | Feature-Planner |
| message | Proceed to plan with OPT-1. Include parity test gate, attribution tasks, and explicit non-goals for engine/rules migration. |
| required_next_actions | Update `status.json`; produce `30-plan.md` and `40-tasks.md`; run plan governance review. |
| artifacts_to_update | `status.json`, `30-plan.md`, `40-tasks.md`, `20-analysis.md`, `70-governance-decisions.md` |
| blocking_items | RC-4 (resolved once persisted) |

### Support Summary

OPT-1 was elected because it gives the best value/risk balance while respecting replacement-first and delta-preservation constraints. Conditions RC-1..RC-4 were accepted and traced into plan/tasks/status artifacts.

### Tiny Status JSON

```json
{
	"gate": "options-review",
	"decision": "approve_with_conditions",
	"status_code": "GOV-OPTIONS-CONDITIONAL",
	"unanimous": false,
	"next_agent": "Feature-Planner"
}
```

## Plan Review — GOV-PLAN-CONDITIONAL

**Gate:** plan-review  
**Decision:** approve_with_conditions  
**Status Code:** GOV-PLAN-CONDITIONAL  
**Unanimous:** No

### Required Changes (Non-Blocking)

| rc_id | required_change | blocking | verification_condition |
|---|---|---|---|
| RC-1 | Use concrete canonical doc file paths in `30-plan.md` cross-references (not directory placeholders). | No | `30-plan.md` references explicit docs files. |
| RC-2 | Append plan-gate verdict to governance ledger. | No | This section present in `70-governance-decisions.md`. |
| RC-3 | Update `status.json` with plan review result and phase progression intent. | No | `status.json` includes `GOV-PLAN-CONDITIONAL` and execute handoff state. |

### Panel Support

| review_id | member | domain | vote | supporting_comment | evidence |
|---|---|---|---|---|---|
| GV-1 | Cho Chikun (9p, Meijin) | Classical tsumego authority | approve | Deterministic parity gate protects tsumego integrity before replacement. | `30-plan.md`, `40-tasks.md` |
| GV-2 | Lee Sedol (9p) | Intuitive fighter | approve | Focused OPT-1 scope avoids heavyweight migration risk. | `25-options.md`, `30-plan.md` |
| GV-3 | Shin Jinseo (9p) | AI-era professional | approve | AI-path safety is preserved via explicit non-goal on Kivy-coupled migration and regression checks. | `30-plan.md`, `40-tasks.md` |
| GV-4 | Ke Jie (9p) | Strategic thinker | approve | Delta-preservation before cleanup is well represented in tasks. | `30-plan.md`, `20-analysis.md` |
| GV-5 | Principal Staff Engineer A | Systems architect | concern | Documentation references needed file-level specificity. | `30-plan.md` |
| GV-6 | Principal Staff Engineer B | Data pipeline engineer | approve | Task graph and ripple mitigation are executor-ready. | `40-tasks.md`, `20-analysis.md` |

### Handover

| field | value |
|---|---|
| from_agent | Governance-Panel |
| to_agent | Plan-Executor |
| message | Execute OPT-1 using parity-first gates, with explicit non-goals and provenance compliance. |
| required_next_actions | Apply RC-1..RC-3, execute tasks in dependency order, then run governance review checkpoint with validation evidence. |
| artifacts_to_update | `30-plan.md`, `40-tasks.md`, `20-analysis.md`, `status.json`, `70-governance-decisions.md` |
| blocking_items | None |

### Selected Option (Confirmed at Plan Gate)

| field | value |
|---|---|
| option_id | OPT-1 |
| title | Targeted Algorithm Port (Frame+Utilities) |
| selection_rationale | Highest score with strongest compliance and lowest migration blast radius. |
| must_hold_constraints | No Kivy vendoring, parity-first gate, MIT attribution, delta preservation, no scope expansion beyond OPT-1 |

### Support Summary

Plan is executor-ready with non-blocking documentation and status housekeeping conditions applied. Confidence floor requirement is satisfied (`88 >= 80`).

### Tiny Status JSON

```json
{
	"gate": "plan-review",
	"decision": "approve_with_conditions",
	"status_code": "GOV-PLAN-CONDITIONAL",
	"unanimous": false,
	"next_agent": "Plan-Executor"
}
```
