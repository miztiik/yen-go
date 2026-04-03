# Clarifications: Teaching Comments Quality V3

**Last Updated**: 2026-03-11

---

## Clarification Rounds

### Round 1 — Pre-Charter (from Governance Panel)

| q_id | question | options | recommended | user_response | status |
|------|----------|---------|-------------|---------------|--------|
| Q1 | Is backward compatibility required? Should existing enriched puzzle comments be preserved? | A: Yes / B: No — re-enrich all / C: Partial | B | B — No backward compatibility required. | ✅ resolved |
| Q2 | For F16 (vital move placement), should the root comment be suppressed when shifting to the vital node, or should both nodes get comments? | A: Suppress root — only vital node / B: Both get comments / C: Root generic, vital technique-specific | A | A — Suppress root. Only vital node gets the teaching comment. | ✅ resolved |
| Q3 | For F17 (wrong-move confidence gate), what delta threshold should be used? | A: 0.03 / B: 0.05 / C: 0.10 / D: Configurable with default | D | D — Configurable with default **0.05 (5%)**. **Governance unanimous (6/6)**: In tsumego, <5% winrate loss corresponds to move-order transpositions or timing alternatives — genuinely “almost correct.” Threshold hierarchy: `almost_correct (0.05) < refutation_gate (0.08) < wrong_move`. Config key in `teaching-comments.json`. | ✅ resolved |
| Q4 | For F23 (almost correct), what should the feedback look like? | A: "Good move, but there's a slightly better option." / B: No comment / C: "Correct! But the strongest move is at {coordinate}." | A | A — Use option A wording as a starting point. Refine wording with a writing-expert LLM to find best phrasing, but keep the spirit of "good but not best". | ✅ resolved |
| Q5 | For F15 (wrong-move default template), should we expand the refutation conditions classifier or improve the default fallback? | A: Expand classifier / B: Improve default fallback / C: Both | B | A — Expand the classifier with more conditions. | ✅ resolved |
