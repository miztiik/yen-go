# Clarifications — Enrichment Data Liberation + Browser AI Teaching

> Initiative: `20260317-1400-feature-enrichment-data-liberation`
> Last Updated: 2026-03-17
> Status: Round 1 — awaiting user input

---

## Round 1: Decision-Critical Questions

### Part A: Data Liberation (R-1 core scope)

| q_id | question | options | recommended | user_response | status |
|------|----------|---------|-------------|---------------|--------|
| Q1 | Should `attrs` JSON include ALL 10+ discarded signals or a curated high-value subset? | A: All signals (~10 fields) / B: Top 5-6 highest-value / C: Difficulty components only (5 fields) | **B** — ship the 6-7 signals with clear frontend use cases; add others later | | ❌ pending |
| Q2 | Is backward compatibility required for DB-1 consumers? (i.e., must `attrs=null` still work?) | A: Yes, existing frontend must handle missing attrs gracefully / B: No, re-enrich all puzzles before shipping | **A** — `attrs` is already null today, so null-safe is current behavior | | ❌ pending |
| Q3 | Should old code (the current `attrs`-ignoring path) be removed? | A: Yes, remove after migration / B: No, keep as fallback | **A** — nothing to remove; `attrs` is additive (empty→populated) | | ❌ pending |
| Q4 | Which frontend feature should prototype the liberated data first? | A: "Sort by reading depth" dropdown / B: Multi-dimensional difficulty radar / C: "Deceptive puzzles" filter / D: Quality confidence badge / Other | **A** — simplest; proves the pipeline end-to-end | | ❌ pending |
| Q5 | Should this initiative include prerequisite edges in `tags.json` (R-3, lightweight config-only addition)? | A: Yes, bundle it / B: No, separate initiative | **B** — separate concern; keep this initiative focused on data liberation | | ❌ pending |
| Q6 | Scope: enrichment lab only, or enrichment lab + backend publish + frontend consumption (full pipeline)? | A: Lab only (persist to AiAnalysisResult; let backend/frontend follow separately) / B: Full pipeline (lab → publish stage → DB-1 attrs → frontend decode) | **B** — the value is only realized when the frontend can read the data; otherwise it's just a model change | | ❌ pending |

### Part B: Browser AI / LLM Teaching (new scope after constraint relaxation)

| q_id | question | options | recommended | user_response | status |
|------|----------|---------|-------------|---------------|--------|
| Q7 | Is the goal personalization (adapt to user level at runtime) or enrichment (richer static text)? | A: Personalization / B: Enrichment / C: Both / Other | **B** — enrichment first (ship faster, lower risk); personalization follows | | ❌ pending |
| Q8 | What is the acceptable model download size for the browser? | A: <100MB / B: <500MB / C: <1GB / D: No limit if opt-in | **D** — user opt-in makes any size acceptable | | ❌ pending |
| Q9 | Would you accept a pipeline-side LLM (Architecture A) as the first step, deferring browser LLM? | A: Yes, pipeline first / B: No, browser is the goal / C: Explore both in parallel | **A** — pipeline LLM has zero browser cost and can use larger models; proves the concept | | ❌ pending |
| Q10 | Is there willingness to fine-tune a tiny model on Go teaching text later? | A: Yes / B: No / C: Explore later | **C** — establish the prompt/output format first, fine-tuning is a future optimization | | ❌ pending |
| Q11 | Should the browser LLM be visible as an "AI assistant" feature (explicit opt-in) or seamless? | A: Explicit opt-in / B: Seamless / C: Progressive (seamless for hints, explicit for deeper questions) | **A** — explicit opt-in avoids surprise download, manages expectations | | ❌ pending |
| Q12 | Should this LLM scope be bundled into the Data Liberation initiative or be a separate initiative? | A: Bundle (one initiative covers R-1 + LLM teaching) / B: Separate (R-1 is foundation, LLM teaching is a follow-on initiative) | **B** — very different risk profiles; Data Liberation is low-risk, Browser LLM is higher-risk; keep them independent | | ❌ pending |

### Part C: Cross-Cutting

| q_id | question | options | recommended | user_response | status |
|------|----------|---------|-------------|---------------|--------|
| Q13 | Is backward compatibility required, and should old code be removed? (Mandatory governance question) | A: Yes backward compat required, remove old code / B: Yes backward compat, keep old code / C: No backward compat needed | **A** — `attrs` is additive (null→populated), existing consumers tolerant of null; old code simply doesn't populate attrs yet | | ❌ pending |
| Q14 | Priority ordering: should we plan both features as a sequence, or can they proceed in parallel? | A: Sequential (R-1 Data Liberation → LLM Teaching) / B: Parallel (independent tracks) / C: R-1 only, LLM deferred to separate planning cycle | **A** — R-1 provides the structured signals the LLM would consume; R-1 is a prerequisite | | ❌ pending |
