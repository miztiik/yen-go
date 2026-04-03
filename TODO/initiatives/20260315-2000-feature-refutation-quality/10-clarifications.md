# Clarifications

> Initiative: `20260315-2000-feature-refutation-quality`
> Last Updated: 2026-03-15

---

## Round 1 — Pre-Charter Clarifications

| q_id | question | options | recommended | user_response | status |
|------|----------|---------|-------------|---------------|--------|
| Q1 | Is backward compatibility required? Should old config keys be preserved? | A: Yes, all new keys must default to current behavior / B: Breaking changes acceptable | A — v1.14 ai_solve pattern. All changes feature-gated, absent key = current behavior. | Inferred from copilot-instructions.md: "Feature-gated: enabled=false by default. Zero behavior change when ai_solve key is absent." | ✅ resolved |
| Q2 | Should old code be removed? | A: No, changes are additive / B: Remove deprecated paths | A — no legacy code to remove. All changes are new config keys and algorithm extensions. | N/A — no legacy code exists for these features. | ✅ resolved |
| Q3 | Are the 3 agent reports in `starter.md` the canonical and complete research input? | A: Yes / B: There are additional sources | A — starter.md + starter/15-research.md contain all findings (F1-F6, F-1..F-12, 1-8, plus 59 research IDs R-1..R-59). | User provided all data in the request. | ✅ resolved |
| Q4 | Should F-8 (opponent policy for teaching comments) be implemented or deferred? | A: Defer (P3/LOW consensus) / B: Implement at lowest priority / C: Separate governance review | A — all 3 reports rated LOW. Tracked as "deferred with player-impact note." Per Hana Park (RC-8): track for future sprint. | Governance consensus: P3/LOW. | ✅ resolved |
| Q5 | Are there quantitative performance budgets for the changes? | A: Define during planning / B: Specific thresholds now | A — metrics baseline (wrong-move recall, zero-refutation rate, queries/puzzle, wall-time/puzzle) to be established during planning. Staff Eng B requirement. | Planning-phase deliverable. | ✅ resolved |
| Q6 | Should we prioritize signal quality (ownership, score) or compute efficiency (adaptive visits, model routing) first? | A: Signal quality first (F-3/F-4 → F-1/F-9) / B: Compute efficiency first (F-1/F-9 → F-3/F-4) / C: Parallel tracks | A — Cho Chikun, Ke Jie, Hana Park all prioritize pedagogical quality. Compute savings amplify after signal quality improves. | Governance consensus: ownership delta is co-P0. | ✅ resolved |

---

## Governance Questions Resolved

| q_id | question | resolution |
|------|----------|------------|
| GQ-1 | Is the "Already Implemented" classification correct? | Yes — all 4 verified (config + code evidence). See charter Table 1. |
| GQ-2 | Is player-side alternative exploration correctly deferred? | **Overridden** — user reclassified to implement (PI-9). Rationale: internet puzzles have multi-solution and position-only puzzles. Tool should auto-detect, not require per-collection config. |
| GQ-3 | RC-7: Is seki detection behaviorally active? | Config + code wired (stopping condition #3 in `_build_tree_recursive()`). Behavioral verification is planning-phase check. |
| GQ-4 | RC-8: F-8 tracking | **Overridden** — user reclassified to implement (PI-10). "Why not do it now." |

---

## Round 2 — Scope Expansion (2026-03-15)

| q_id | question | options | recommended | user_response | status |
|------|----------|---------|-------------|---------------|--------|
| Q7 | Should DF-2 (player alternatives) be reclassified to implement? | A: Keep deferred / B: Implement with auto-detect by puzzle type / C: Implement but manual per-collection | B — auto-detect. Tool should decide based on whether puzzle is position-only, multi-solution, or single-answer. No babysitting. | User: "It should be implementable. The tool itself should be able to decide what to do, it is hard to baby-sit for each collection." | ✅ resolved |
| Q8 | Should DF-3 (opponent policy for teaching) be reclassified? | A: Keep deferred / B: Implement now | B — user says "why not do it now." Low effort (~40 LOC). | User: "DF3 - why not do it now." | ✅ resolved |
| Q9 | Should DF-4 (surprise calibration) be brought in? | A: Keep deferred / B: Bring into this initiative | B — essential for heterogeneous internet sources. | User: "bring them to this initiative" | ✅ resolved |
| Q10 | Should DF-5 (best resistance) be brought in? | A: Keep deferred / B: Bring into this initiative | B — for position-only puzzles, best-resistance is how solutions are discovered. | User: "bring them to this initiative" | ✅ resolved |
