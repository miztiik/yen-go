# Planning Artifact Contract

Last Updated: 2026-03-08

Defines the on-disk artifact contract used by `Feature-Planner`, `Refactor-Planner`, `Plan-Executor`, and `Governance-Panel`.

## Purpose

The contract enables pause/resume at every phase gate without relying on agent memory.

## Initiative Naming

- Root path: `TODO/initiatives/`
- Initiative path: `TODO/initiatives/<initiative-id>/`
- `initiative-id` format: `YYYYMMDD-HHMM-<type>-<slug>`
- `HHMM` is 24-hour local time, zero-padded.
- Timestamp precision ensures same-day initiatives are lexically sortable by creation order.
- `<type>` values: `feature`, `refactor`, `bugfix`, `docs`

Use "initiative" as the neutral term for both feature and refactor work.

## Artifact Set

Required planning artifacts:

- `status.json` (machine state, source of truth)
- `00-charter.md`
- `10-clarifications.md`
- `20-analysis.md`
- `30-plan.md`
- `40-tasks.md`
- `70-governance-decisions.md`

Required execution artifacts:

- `50-execution-log.md`
- `60-validation-report.md`

Required documentation contract fields:

- `30-plan.md` must include `## Documentation Plan` with:
  - `files_to_update`
  - `files_to_create`
  - `why_updated`
  - cross-references to existing global docs
- `40-tasks.md` must include explicit documentation tasks mapped to Documentation Plan items.
- `70-governance-decisions.md` must include `docs_plan_verification` from plan gate.

## Clarification and Identifier Standards

Clarification policy:

- Clarification rounds are not capped at a fixed count.
- Agents must ask as many high-impact questions as needed to remove decision blockers.

Question format:

- Every clarification question must have a stable ID: `Q1`, `Q2`, ...
- Each question should provide response options when a choice is needed:
  - `A. <option>`
  - `B. <option>`
  - `C. <option>` (optional)
  - `Recommended: <option-id> - <brief rationale>`
  - `Other: <freeform>`
- Questions should be independently answerable so users can reply compactly (`Q1:A, Q2:Other...`).
- Clarification questions should be presented as a table when there are multiple questions:
  `| q_id | question | options | recommended | user_response | status |`
- `status` should use: `✅ resolved` or `❌ pending`.

Table row identifiers:

- All planning/execution/governance tables must include a row ID in the first column.
- Recommended row prefixes:
  - options: `OPT-1`, `OPT-2`, ...
  - tasks: `T1`, `T2`, ...
  - findings: `F1`, `F2`, ...
  - governance reviews: `GV-1`, `GV-2`, ...
  - required changes: `RC-1`, `RC-2`, ...
  - execution rows: `EX-1`, `EX-2`, ...
  - validation rows: `VAL-1`, `VAL-2`, ...
  - artifact sync rows: `ART-1`, `ART-2`, ...

Table-first presentation guidance:

- Prefer tables for structured planning/execution/governance data.
- Use short bullet lists only for concise narrative context where table form adds little value.
- Use `✅` and `❌` markers for status checks where relevant.

Ripple-effects introspection requirement:

- Planning and governance artifacts must explicitly cover upstream, downstream, and lateral ripple effects.
- Recommended analysis table:
  `| impact_id | direction(upstream|downstream|lateral) | area | risk | mitigation | owner_task | status |`
- Each non-trivial impact should map to a task or an explicit acceptance rationale.

## Phase Ownership

Planner-owned phases and files:

- `charter`, `clarify`, `options`, `analyze`, `plan`, `tasks`
- `00, 10, 20, 30, 40`, and planning entries in `70`

Executor-owned phases and files:

- `execute`, `validate`, `governance_review`, `closeout`
- `50, 60`, review entries in `70`

Governance responsibilities:

- Validate artifact completeness in `charter`, `options`, `plan`, `review`, and `closeout` modes.
- Reject approvals when contract-required artifacts are missing or stale.
- Require concern resolution: each `concern` must map to explicit `RC-*` required changes or escalate to `change_requested`.
- Preserve dissent in `support_summary` when non-unanimous.

## status.json Schema (Minimum)

```json
{
  "initiative_id": "20260305-0915-feature-example",
  "initiative_type": "feature",
  "current_phase": "plan",
  "phase_state": {
    "charter": "approved",
    "clarify": "approved",
    "analyze": "approved",
    "plan": "in_progress",
    "tasks": "not_started",
    "execute": "not_started",
    "validate": "not_started",
    "governance_review": "not_started",
    "closeout": "not_started"
  },
  "decisions": {
    "backward_compatibility": {
      "required": true,
      "rationale": "Public API compatibility required"
    },
    "legacy_code_removal": {
      "remove_old_code": false,
      "rationale": "Temporary dual-path approved by user"
    }
  },
  "updated_at": "2026-03-05"
}
```

## Tiny Mandatory status.json Sample

Every planner and executor run must create or update this minimal shape first,
then extend it as needed.

```json
{
  "initiative_id": "20260305-0915-feature-example",
  "initiative_type": "feature",
  "current_phase": "clarify",
  "phase_state": {
    "charter": "not_started",
    "clarify": "in_progress",
    "analyze": "not_started",
    "plan": "not_started",
    "tasks": "not_started",
    "execute": "not_started",
    "validate": "not_started",
    "governance_review": "not_started",
    "closeout": "not_started"
  },
  "decisions": {
    "backward_compatibility": {
      "required": false,
      "rationale": "pending"
    },
    "legacy_code_removal": {
      "remove_old_code": true,
      "rationale": "pending"
    }
  },
  "updated_at": "2026-03-05"
}
```

Allowed phase values:

- `not_started`
- `in_progress`
- `approved`
- `blocked`

## Gate Rules

Plan gate must have:

1. Planning artifacts present and updated.
2. `backward_compatibility.required` explicitly set.
3. `legacy_code_removal.remove_old_code` explicitly set.
4. No unresolved CRITICAL analysis findings.
5. Documentation plan contract present and mapped to tasks.
6. If research was triggered, `planning_confidence_score >= 80`.

Execution closeout gate must have:

1. `50-execution-log.md` complete.
2. `60-validation-report.md` complete with command results.
3. Governance `review` and `closeout` verdicts recorded in `70-governance-decisions.md`.
4. `status.json.current_phase = closeout` and `phase_state.closeout = approved`.
5. Ripple-effects validation table with no unresolved blocking mismatches.

## Policy Alignment

All initiatives must enforce:

- No MVP slicing of approved scope.
- No simulation/stub behavior unless user explicitly requests simulation.
- Structural solutions over temporary band-aids.
- Explicit backward compatibility decision.
- Explicit legacy code removal decision.

> **See also**:
>
> - [Reference: copilot-instructions](../../.github/copilot-instructions.md) - Project-level AI guidance
> - [Reference: Documentation Artifact Contract](./documentation-artifact-contract.md) - Required docs planning and validation fields
> - [How-To: Backend CLI Reference](../how-to/backend/cli-reference.md) - Validation command reference patterns
> - [Architecture: Pipeline](../architecture/backend/pipeline.md) - System context for plan decisions
