---
agent: Governance-Panel
description: Post-implementation governance review with mandatory code review and final sign-off.
---

Mode: review

Review this implementation through two phases — code review and artifact review — then return a gate verdict:

$ARGUMENTS

## Phase 1: Code Review (Mandatory)

Before evaluating artifacts, dispatch both code reviewer sub-agents per the Code Review Dispatch Protocol in the agent definition.

1. Extract `scope_files` from `50-execution-log.md` (or `40-tasks.md` fallback)
2. Extract `charter_goals` and `acceptance_criteria` from `00-charter.md`
3. Extract `plan_summary` from `30-plan.md`
4. Dispatch `Code-Reviewer-Alpha` (charter alignment, acceptance criteria, correctness)
5. Dispatch `Code-Reviewer-Beta` (architecture compliance, code quality, security) — in parallel with Alpha
6. Validate and integrate findings per CR Steps 5–7

Code review blockers:

- If either reviewer returns `fail`, panel decision MUST be `change_requested`
- Critical/major findings become `RC-*` required changes
- Do NOT proceed to Phase 2 if code review dispatch fails — report `change_requested` with dispatch failure evidence

## Phase 2: Artifact and Evidence Review

After integrating code review findings, evaluate governance artifacts:

Evidence should include:

- what changed (supplemented by code reviewer findings)
- tests executed and results
- documentation updates
- initiative artifacts under `TODO/initiatives/<initiative-id>/` including `50-execution-log.md`, `60-validation-report.md`, and `status.json`
- Code review reports from `Code-Reviewer-Alpha` (CR-ALPHA) and `Code-Reviewer-Beta` (CR-BETA)
- Clarification blockers (if any) are listed in a table:
  `| q_id | question | options | recommended | user_response | status |`
- Use `Q1`, `Q2`, ... with choices (`A/B/C`), a `Recommended` option, and `Other` freeform
- Use `✅ resolved` / `❌ pending` in clarification status
- Verify upstream/downstream/lateral ripple effects were validated post-implementation
- Require a ripple-effects validation table in `60-validation-report.md` with one row per planned impact:
  `| impact_id | expected_effect | observed_effect | result | follow_up_task | status |`
- Any unresolved `❌ mismatch` row must be either fixed before approval or explicitly blocked with required changes.

Return:

- decision: approve | approve_with_conditions | change_requested
- status_code: GOV-REVIEW-APPROVED | GOV-REVIEW-CONDITIONAL | GOV-REVIEW-REVISE
- required_changes (must be non-empty when not approved)
- code_review_summary:
  - alpha_verdict: pass | pass_with_findings | fail
  - alpha_ac_met: N of M
  - beta_verdict: pass | pass_with_findings | fail
  - beta_architecture_status: compliant | minor_deviations | violations_found
  - beta_security_status: clean | concerns_found | vulnerabilities_found
  - combined_critical_count: N
  - combined_major_count: N
- member_reviews: one entry per panel member
  - review_id: `GV-1`, `GV-2`, ...
  - member
  - domain
  - vote: approve | concern | change_requested
  - supporting_comment (required — MUST reference code review findings where relevant)
  - evidence (required)
- support_summary: why the final decision is justified based on panel support and code review findings
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
  "gate": "implementation-review",
  "decision": "approve_with_conditions",
  "status_code": "GOV-REVIEW-CONDITIONAL",
  "unanimous": false,
  "has_supporting_comments": true,
  "code_review_pass": true,
  "next_agent": "Plan-Executor"
}
```

Rules:

- Do not return analysis-only output.
- Code review dispatch is mandatory. Skipping code review is a protocol violation.
- If any panel member votes `change_requested`, final decision must be `change_requested`.
- If any code reviewer returns `fail`, final decision must be `change_requested`.
- Every decision must include supporting comments and evidence references.
- Every `concern` must either map to explicit `RC-*` required change rows (with owner artifact/task and verification) or be escalated to `change_requested`.
- If any member has slight doubt/uncertainty, run one explicit re-deliberation round before final decision.
- If final decision is non-unanimous, `support_summary` must include a `Non-Unanimous Members` subsection with member, vote, rationale, and evidence.
- Any response table must include an explicit row ID first column.
- Any uncertain member can trigger a re-review loop by voting `change_requested` with clarification-needed rationale.
- Prefer table format for structured content; use short lists only for concise narrative notes.
- Use `✅` and `❌` markers for status checks where relevant.
