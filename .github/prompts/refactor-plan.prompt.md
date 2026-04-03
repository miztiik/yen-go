---
agent: Refactor-Planner
description: Create an approved refactor plan package with tasks, analysis, and governance review.
---

Create a refactor planning package only (no implementation):

$ARGUMENTS

Create or update `TODO/initiatives/<initiative-id>/` artifacts per the planner contract.
The tiny mandatory `status.json` shape must be present and current.

Return the mandatory outputs from Refactor-Planner, including tasks.md-style decomposition, parallel lanes, analysis findings, executor handoff, artifact path, and final `status.json` summary.
Always include a compact `status.json` snippet in the response.

Mandatory sequencing:

- Run iterative clarification rounds before planning with as many questions as needed to remove decision blockers.
- Present clarification questions as a table:
  `| q_id | question | options | recommended | user_response | status |`
- Use `Q1`, `Q2`, ... and include selectable options (`A/B/C`), a `Recommended` choice, and an `Other` freeform path.
- Use `✅ resolved` / `❌ pending` in clarification status.
- Compute `planning_confidence_score` (0-100) and `risk_level` (`low|medium|high`) before options.
- Auto-invoke `Feature-Researcher` when score `< 70`, or risk is `medium/high` with incomplete evidence, or ownership/migration seams are unclear.
- If research is used, persist output to `15-research.md` and include post-research score/risk.
- Run Governance-Panel in `charter` mode after clarifications/research and before options.
- Run options hypotheses first and write `25-options.md` (multiple meaningful options; normally 2 to 3).
- Run Governance-Panel in `options` mode and lock a selected option before writing `30-plan.md` and `40-tasks.md`.
- Ensure `30-plan.md` includes `## Documentation Plan` with `files_to_update`, `files_to_create`, `why_updated`, and cross-references.
- Ensure `40-tasks.md` includes explicit documentation tasks mapped to Documentation Plan items.
- Include explicit upstream/downstream/lateral ripple-effects introspection in analysis and map each impact to tasks.
- Ensure `status.json.decisions.option_selection.selected_option_id` is set before plan/task generation.
- Enforce confidence floor at plan gate when research was triggered: `planning_confidence_score >= 80`.

Mandatory governance consumption requirements:

- Consume Governance-Panel `decision`, `status_code`, `member_reviews`, `support_summary`, `handover`, and `tiny_status_json`.
- For options gate, also consume `selected_option` and persist selection rationale.
- If governance output is missing required fields, stop and return `change_requested` with missing field list.
- Include consumed governance handover message in the final planner response.

Formatting requirements:

- Any table in the response must include row identifiers in the first column.
- Use `OPT-1..N` for options, `T1..N` for tasks, `F1..N` for findings, and `GV-1..N` for governance entries.
- Prefer tables for structured output and use short lists only for concise narrative notes.
- Use `✅` and `❌` markers for status checks where relevant.
