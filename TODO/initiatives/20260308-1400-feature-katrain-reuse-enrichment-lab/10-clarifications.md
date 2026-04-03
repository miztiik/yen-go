# Clarifications: KA Train Reuse for Enrichment Lab

**Last Updated:** 2026-03-08

| q_id | question | options | recommended | user_response | status |
|---|---|---|---|---|---|
| Q1 | Is backward compatibility required, and should old code be removed? | A: compatibility + keep old, B: compatibility + remove internals, C: no compatibility + remove aggressively, Other | C for simplification if replacement confidence is high | No backward compatibility; replace directly where KA Train is 1:1. Preserve current delta behavior by carrying missing functionality into replacement path. | ✅ resolved |
| Q2 | What is the expected outcome of this phase? | A: research only, B: research + plan/tasks, C: research + immediate implementation proposal | B | Create a full research-driven initiative package with executor handoff (planner output for plan-executor phase). | ✅ resolved |
| Q3 | What KA Train scope is in bounds? | A: core+rules only, B: core+ai+utils (no UI), C: all except UI, Other | B | In scope: everything in KA Train backend/core/ai/engine/rules/utilities; out of scope: UI components. | ✅ resolved |
| Q4 | What reuse policy should we apply to MIT code? | A: direct vendoring, B: thin adapter, C: inspiration-only, Other | B with contextual fallback | Contextual decision: if exact match, use directly; if partial match, use adapter and preserve enrichment-lab delta; no single global choice. | ✅ resolved |
| Q5 | Which technical areas are in scope? | A: frame/border, B: legal move/rules, C: ELO/strength mapping, D: search heuristics, E: SGF parsing | A/B/C/D/E + Other | Evaluate all areas; prioritize B/C/D and keep A in scope even if another agent is also working there. | ✅ resolved |
| Q6 | Is missing flip normalization in local tsumego-frame intentional? | A: intentional, B: gap, C: unknown pending validation | C | Not explicitly confirmed yet. Plan will include an early verification task and then either full KA Train parity or scoped delta-only port. | ✅ resolved |

## Decision Summary

| decision_id | decision | rationale |
|---|---|---|
| D1 | Replacement-first strategy | Directly reduce engineering complexity by reusing battle-tested KA Train logic where exact fit exists. |
| D2 | No compatibility shim required | User explicitly prefers clean replacement over preserving old paths. |
| D3 | Delta preservation is mandatory | Any enrichment-lab-specific behavior not in KA Train must be reintroduced via adapter/delta layer before old code removal. |
| D4 | Non-UI KA Train only | Avoid coupling to KA Train frontend/Kivy UI surface. |
