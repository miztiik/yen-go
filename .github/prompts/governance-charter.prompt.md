---
agent: Governance-Panel
description: Pre-options governance charter and research-readiness review.
---

Mode: charter

Review this initiative charter and research readiness before options drafting:

$ARGUMENTS

Verify initiative artifacts under `TODO/initiatives/<initiative-id>/` are complete for charter gate:

- `status.json`
- `00-charter.md`
- `10-clarifications.md`
- `15-research.md` (if research was triggered)

Required charter quality bar:

- Scope boundaries are explicit (goals, non-goals, constraints, acceptance criteria)
- Clarification blockers are tracked in a table:
  `| q_id | question | options | recommended | user_response | status |`
- Decisions for backward compatibility and legacy removal are captured or explicitly blocked pending clarification
- Research objective is clear where uncertainty exists (what evidence is needed and why)

Return:

- decision: approve | approve_with_conditions | change_requested
- status_code: GOV-CHARTER-APPROVED | GOV-CHARTER-CONDITIONAL | GOV-CHARTER-REVISE
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
  - to_agent: Feature-Planner | Refactor-Planner | requester
  - message
  - required_next_actions
  - artifacts_to_update
  - blocking_items
  - re_review_requested: true | false
  - re_review_mode: charter | options | plan | review | closeout | none

Rules:

- Do not return analysis-only output.
- If any panel member votes `change_requested`, final decision must be `change_requested`.
- Every `concern` must either map to explicit `RC-*` required change rows (with owner artifact/task and verification) or be escalated to `change_requested`.
- If any member has slight doubt/uncertainty, run one explicit re-deliberation round before final decision.
- Any response table must include an explicit row ID first column.
- Prefer table format for structured content; use short lists only for concise narrative notes.
- Use `✅` and `❌` markers for status checks where relevant.
