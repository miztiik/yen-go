---
agent: Governance-Panel
description: Pre-implementation governance plan review and gate decision.
---

Mode: plan

Review this implementation plan and return a gate verdict:

$ARGUMENTS

Verify initiative artifacts under `TODO/initiatives/<initiative-id>/` are complete for planning gates.
Verify option-election artifacts are complete before plan gate:

- `25-options.md` exists
- `status.json.decisions.option_selection.selected_option_id` is set
- selected option rationale is persisted in `70-governance-decisions.md`
- Clarification blockers (if any) are listed in a table:
  `| q_id | question | options | recommended | user_response | status |`
- Use `Q1`, `Q2`, ... with choices (`A/B/C`), a `Recommended` option, and `Other` freeform
- Use `✅ resolved` / `❌ pending` in clarification status
- Verify upstream/downstream/lateral ripple effects are mapped to tasks and mitigations

Required docs quality gate:

- `30-plan.md` includes `## Documentation Plan` with:
  - `files_to_update`
  - `files_to_create`
  - `why_updated`
  - cross-references to global docs where the "why" is recorded
- Existing docs are updated before new docs are created unless no canonical destination exists.
- `40-tasks.md` contains explicit documentation tasks mapped to Documentation Plan items.

Required confidence gate:

- If research was triggered, plan approval requires `planning_confidence_score >= 80`.
- If `risk_level = high`, each high-risk item must have mitigation mapped to a task.

Return:

- decision: approve | approve_with_conditions | change_requested
- status_code: GOV-PLAN-APPROVED | GOV-PLAN-CONDITIONAL | GOV-PLAN-REVISE
- required_changes (must be non-empty when not approved)
- member_reviews: one entry per panel member
  - review_id: `GV-1`, `GV-2`, ...
  - member
  - domain
  - vote: approve | concern | change_requested
  - supporting_comment (required)
  - evidence (required)
- support_summary: why the final decision is justified based on panel support
- handover:
  - from_agent: Governance-Panel
  - to_agent: Feature-Planner | Refactor-Planner | Plan-Executor | requester
  - message
  - required_next_actions
  - artifacts_to_update
  - blocking_items
  - re_review_requested: true | false
  - re_review_mode: charter | options | plan | review | closeout | none
- tiny_status_json:

```json
{
  "gate": "plan-review",
  "decision": "approve_with_conditions",
  "status_code": "GOV-PLAN-CONDITIONAL",
  "unanimous": false,
  "has_supporting_comments": true,
  "next_agent": "Plan-Executor"
}
```

Rules:

- Do not return analysis-only output.
- If any panel member votes `change_requested`, final decision must be `change_requested`.
- Every decision must include supporting comments and evidence references.
- Every `concern` must either map to explicit `RC-*` required change rows (with owner artifact/task and verification) or be escalated to `change_requested`.
- If any member has slight doubt/uncertainty, run one explicit re-deliberation round before final decision.
- If final decision is non-unanimous, `support_summary` must include a `Non-Unanimous Members` subsection with member, vote, rationale, and evidence.
- Include `docs_plan_verification` in response payload with at least:
  - `present: true|false`
  - `coverage: complete|partial|missing`
- Any response table must include an explicit row ID first column.
- Any uncertain member can trigger a re-review loop by voting `change_requested` with clarification-needed rationale.
- Prefer table format for structured content; use short lists only for concise narrative notes.
- Use `✅` and `❌` markers for status checks where relevant.
