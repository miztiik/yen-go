---
agent: Plan-Executor
description: Execute an approved plan package with validation and governance implementation review.
---

Execute an approved plan package:

$ARGUMENTS

Require approved scope, plan, task graph, resolved analysis findings, and `TODO/initiatives/<initiative-id>/status.json` before implementation.

Mandatory governance consumption requirements:

- Before execution, consume planning governance payload from `70-governance-decisions.md` with required fields:
  - `decision`, `status_code`, `member_reviews`, `support_summary`, `handover`, `tiny_status_json`
- Require planning docs contract evidence:
  - `docs_plan_verification.present = true`
  - `docs_plan_verification.coverage = complete`
- Reject execution if governance fields are missing, if decision is not approved/conditional, or if handover blocking items remain.
- After implementation review, consume the new Governance-Panel review payload and append it to `70-governance-decisions.md`.
- Before final closeout, run Governance-Panel in `closeout` mode and consume that payload too.

Mandatory docs contract blockers:

- Halt execution and request planner updates if any are missing:
  - `30-plan.md` has `## Documentation Plan` with `files_to_update`, `files_to_create`, `why_updated`
  - `40-tasks.md` has explicit documentation tasks mapped to Documentation Plan items
  - `70-governance-decisions.md` includes `docs_plan_verification`

Formatting requirements:

- If execution is blocked, ask clarifications in a table:
  `| q_id | question | options | recommended | user_response | status |`
- Use numbered IDs (`Q1`, `Q2`, ...) with `A/B/C`, `Recommended`, and `Other` response paths.
- Use `✅ resolved` / `❌ pending` in clarification status.
- Any table in the response must include row IDs in the first column.
- Use `EX-1..N` for execution summaries, `VAL-1..N` for validation, `GV-1..N` for governance, and `ART-1..N` for artifact sync.
- Prefer tables for structured output and use short lists only for concise narrative notes.
- Use `✅` and `❌` markers for status checks where relevant.

Update execution-phase artifacts during work and return artifact path plus final `status.json` summary at closeout.
Always include a compact `status.json` snippet in the response.
