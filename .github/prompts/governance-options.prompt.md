---
agent: Governance-Panel
description: Pre-plan governance options review and option election.
---

Mode: options

Review these solution options and elect a direction before plan drafting:

$ARGUMENTS

Verify initiative artifacts under `TODO/initiatives/<initiative-id>/` are complete for options gate:

- `status.json`
- `00-charter.md`
- `10-clarifications.md`
- `25-options.md`

Required options quality bar:

- Meaningful alternatives are present (normally 2 to 3; minimum 2 unless user explicitly constrained to one path)
- Each option includes benefits, drawbacks, risks, and validation implications
- A tradeoff matrix with explicit criteria exists
- Clarification blockers (if any) are listed in a table:
  `| q_id | question | options | recommended | user_response | status |`
- Use `Q1`, `Q2`, ... with choices (`A/B/C`), a `Recommended` option, and `Other` freeform
- Use `✅ resolved` / `❌ pending` in clarification status
- Upstream/downstream/lateral ripple effects are assessed per option

Return:

- decision: approve | approve_with_conditions | change_requested
- status_code: GOV-OPTIONS-APPROVED | GOV-OPTIONS-CONDITIONAL | GOV-OPTIONS-REVISE
- required_changes (must be non-empty when not approved)
- selected_option:
  - option_id
  - title
  - selection_rationale
  - must_hold_constraints
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
  - to_agent: Feature-Planner | Refactor-Planner | requester
  - message
  - required_next_actions
  - artifacts_to_update
  - blocking_items
  - re_review_requested: true | false
  - re_review_mode: charter | options | plan | review | closeout | none
- tiny_status_json:

```json
{
  "gate": "options-review",
  "decision": "approve_with_conditions",
  "status_code": "GOV-OPTIONS-CONDITIONAL",
  "unanimous": false,
  "has_supporting_comments": true,
  "next_agent": "Feature-Planner"
}
```

Rules:

- Do not return analysis-only output.
- If any panel member votes `change_requested`, final decision must be `change_requested`.
- Every decision must include supporting comments and evidence references.
- If any member has slight doubt/uncertainty, run one explicit re-deliberation round before final decision.
- Every `concern` must either map to explicit `RC-*` required change rows (with owner artifact/task and verification) or be escalated to `change_requested`.
- Any response table must include an explicit row ID first column.
- Any uncertain member can trigger a re-review loop by voting `change_requested` with clarification-needed rationale.
- If final decision is non-unanimous, `support_summary` must include a `Non-Unanimous Members` subsection with member, vote, rationale, and evidence.
- Fast-track route is allowed only when all are true: confidence >= 85, risk low, no new modules, <3 runtime files changed, no new dependencies, rollback is single-commit reversible.
- Prefer table format for structured content; use short lists only for concise narrative notes.
- Use `✅` and `❌` markers for status checks where relevant.
