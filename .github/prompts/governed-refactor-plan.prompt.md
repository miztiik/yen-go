---
agent: Governed-Refactor-Planner
description: Create an approved governed refactor package (plan + tasks) without implementation.
---

Create a governed planning package only (no code changes). Specify mode:
- `mode: refactor` for existing-code changes
- `mode: feature-plan` for new feature planning

$ARGUMENTS

Follow clarification, scope lock, plan drafting, task decomposition, cross-artifact consistency analysis, and Governance-Panel plan review from the Governed-Refactor-Planner profile. Return an executor-ready handoff package with ordered tasks, parallel lanes, analysis summary, test strategy, and documentation obligations.
