---
agent: Governance-Panel
description: End-to-end closeout governance audit.
---

Mode: closeout

Run final lifecycle closeout audit:

$ARGUMENTS

Verify initiative artifacts under `TODO/initiatives/<initiative-id>/` are complete for closeout gate:

- `status.json`
- `50-execution-log.md`
- `60-validation-report.md`
- `70-governance-decisions.md`

Required closeout quality bar:

- Scope/tests/docs/governance gates are all complete
- `60-validation-report.md` includes ripple-effects validation table with no unresolved blocking mismatches
- Documentation quality checks are complete:
  - Why rationale is captured in updated docs
  - Existing global docs were updated before creating new docs when applicable
  - Cross-references are present
  - `Last Updated` fields were refreshed
- `status.json.open_issues` is empty

Return:

- decision: approve | approve_with_conditions | change_requested
- status_code: GOV-CLOSEOUT-APPROVED | GOV-CLOSEOUT-CONDITIONAL | GOV-CLOSEOUT-REVISE
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
  - to_agent: Plan-Executor | Feature-Planner | Refactor-Planner | requester
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
