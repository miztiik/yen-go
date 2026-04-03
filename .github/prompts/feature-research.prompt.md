---
agent: Feature-Researcher
description: Build a concise research brief from internal code evidence and external references.
---

Create a research package only (no implementation):

$ARGUMENTS

Create or update `TODO/initiatives/<initiative-id>/15-research.md` with:

- Problem framing and constraints
- Internal evidence (files/symbols/behavior)
- External references (patterns/implementations/docs)
- Adaptation recommendations for Yen-Go
- Risks and license/compliance notes
- Open questions for planners
- Post-research confidence/risk recommendation (`post_research_confidence_score`, `post_research_risk_level`)

Quality bar:

- At least 2 internal references
- At least 2 external references when available
- Recommendations must map to architecture constraints and project rules
- Open questions must be numbered (`Q1`, `Q2`, ...) and include recommended answer options (`A/B/C`, `Recommended`, `Other`) when actionable choices exist
- When multiple open questions exist, present them in a table:
  `| q_id | question | options | recommended | user_response | status |`
- Use `✅ resolved` / `❌ pending` in question status.
- Any table in the output must include row IDs in the first column (`R-1`, `R-2`, ...)
- Prefer tables for structured findings and use short lists only for concise narrative notes.
- Use `✅` and `❌` markers for status checks where relevant.

Return:

- research_completed
- initiative path
- research artifact path
- top recommendations
- open questions
- post_research_confidence_score
- post_research_risk_level
