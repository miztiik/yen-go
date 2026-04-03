# Clarifications: KataGo Teaching Signal Emission

> **Initiative**: 20260326-1400-feature-llm-teaching-enrichment
> **Phase**: clarify → **RESOLVED**
> **Last updated**: 2026-03-27

---

## Round 1: Initial Decision Questions

| q_id | question | options | recommended | user_response | status |
|------|----------|---------|-------------|---------------|--------|
| Q1 | **Scope**: R-1 (computed signals) AND R-2 (LLM teaching stage), or R-1 only? | A: R-1 only / B: R-1 + R-2 together / C: R-2 only / D: All R-1 through R-6 | B | User re-scoped: "Your job is KataGo signal emission, not LLM interfacing." Effectively R-1 only + structured event emission. No LLM client code. | ✅ resolved |
| Q2 | **LLM provider/model**: Which LLM provider? | A: OpenAI / B: Anthropic / C: Local / D: Ollama / E: Provider-agnostic / F: Other | E | "Just emit an event. Provider-agnostic." — User will build LLM client separately. NOT our scope. | ✅ resolved |
| Q3 | **Comment replacement strategy**: Replace or augment? | A: Replace / B: Augment / C: A/B test | B | "Augment" — confirmed. Template stays, signals are additive. | ✅ resolved |
| Q4 | **Budget ceiling**: Cost per pipeline run? | A: $0 / B: <$5/1K / C: <$20/1K / D: No limit | — | "Not our problem" — LLM cost is user's concern, not ours. Signal emission has zero API cost. | ✅ resolved |
| Q5 | **Backward compatibility**: Required for AiAnalysisResult schema? | A: Yes, add-only / B: No, can restructure / C: Other | A | User concerned about clarity: "what are we removing?" — Answer: NOTHING removed. Only add new optional `teaching_signals` field. | ✅ resolved |
| Q6 | **Remove old template code?** | A: Yes / B: No, keep both / C: Defer | B | "Template code unclear, what does it mean?" — Keep template system permanently. Signals are a separate addition. | ✅ resolved |
| Q7 | **Signal event format**: Structured event or function args? | A: Structured payload / B: Direct function args / C: Event bus / D: Other | A | "Structured payload like REST...emit an event." — Confirmed: JSON dict on PipelineContext + persisted on AiAnalysisResult. | ✅ resolved |
| Q8 | **Which wrong moves get signals?** | A: All / B: Top-3 by severity / C: Only generic / D: Configurable | B | "Consult Cho Chikun and KataGo expert" → Governance panel selected Option B (Rich Payload) with 3 required changes: RC-1 (seki exception), RC-2 (config-driven thresholds), RC-3 (conditional ownership). | ✅ resolved |
| Q9 | **Teaching persona** | A: Go-teacher / B: Generic / C: Configurable | A | "Cho Chikun is best persona" — Persona design is user's LLM concern. Our signals should be rich enough for any persona. | ✅ resolved |
| Q10 | **Validation strategy** | A: Manual / B: Automated / C: Both / D: Side-by-side | — | "Calibration later, no answer now" — Deferred. Out of scope for signal emission. | ✅ resolved |

---

## Round 2: User Re-Scoping Directive

User provided critical feedback that fundamentally re-scoped this initiative:

> "Your job is to make sure KataGo generates the signal not interfacing to LLM. I will take care of that."
> "Just emit an event...like a REST interface...structured payload."
> "Pipeline should work with or without LLM stage."

### Scope Changes Applied

| Change | Description |
|--------|-------------|
| **REMOVED** | LLM client code (T9: `TeachingLLMClient` interface + OpenAI impl) |
| **REMOVED** | LLM pipeline stage (T10: `LlmTeachingStage`, T11: pipeline wiring) |
| **REMOVED** | LLM-specific config (provider, model, api_key, system_prompt, prompt_templates) |
| **REMOVED** | LLM-specific tests (T13: mocked LLM stage tests) |
| **REMOVED** | `llm_teaching_comments` output field (replaced by `teaching_signals`) |
| **KEPT** | Computed signal functions (log_policy, score_lead_rank, position_closeness) |
| **ADDED** | Rich wrong-move signal payload (score_delta, refutation_depth, refutation_pv, refutation_type) |
| **ADDED** | Instructiveness gate with seki exception (RC-1 from governance panel) |
| **ADDED** | Config-driven thresholds (RC-2) |
| **ADDED** | Conditional ownership_delta_max emission (RC-3) |
| **ADDED** | `teaching_signals` field on AiAnalysisResult (persisted, schema v10) |

---

## Governance Panel Expert Consultation (Q8)

### Option Selected: B — Rich Payload (9/9 panel votes)

The governance panel reviewed three options for wrong-move signal richness:

| Option | Description | Votes |
|--------|-------------|-------|
| A: Minimal | log_policy + score_lead_rank + delta only | 0/9 |
| **B: Rich (selected)** | A + score_delta, refutation_depth, refutation_pv, refutation_type, conditional ownership, instructiveness gate | **9/9** |
| C: Full depth | B + ASCII board + ownership heatmap + ladder detection | 0/9 |

### Required Changes (RC-1, RC-2, RC-3)

| RC | Requirement | Rationale |
|----|-------------|-----------|
| RC-1 | Add seki exception: when `position_closeness > 0.9`, bypass instructiveness gate | Seki positions have low delta but high instructional value |
| RC-2 | Make instructiveness threshold config-driven, not hardcoded | Different collections have different quality standards |
| RC-3 | Emit `ownership_delta_max` conditionally (only when > 0.3) | Ownership deltas are only pedagogically interesting when dramatic |

---

## Compatibility Decision Record

| Decision | Answer | Rationale |
|----------|--------|-----------|
| Backward compatibility required? | **Yes** (Q5) | Add-only changes. No fields removed. Schema v9 → v10. |
| Remove old code? | **No** (Q6) | Template system kept permanently. Signals are additive. |
| LLM code in scope? | **No** (user re-scope) | "I will take care of LLM interfacing." |
