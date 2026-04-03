# Charter: KataGo Teaching Signal Emission

> **Initiative**: 20260326-1400-feature-llm-teaching-enrichment
> **Type**: Feature
> **Date**: 2026-03-27 (rescoped)

---

## Goal

Emit rich, structured KataGo teaching signals from the enrichment pipeline as a persistent event payload on `AiAnalysisResult`. These signals enable downstream consumers (LLM teaching stage, eval tooling, diagnostics) to generate pedagogically meaningful explanations for both correct and wrong moves.

**What this initiative does:**
1. Compute derived signals from existing KataGo analysis data (zero new queries)
2. Build a structured teaching signal payload (correct move + wrong move signals)
3. Persist the payload on `AiAnalysisResult.teaching_signals` (schema v10)
4. Propagate missing fields (`score_delta`, `wrong_move_policy`) through the refutation pipeline

**What this initiative does NOT do:**
- Build LLM client code (user's responsibility)
- Build LLM pipeline stage (user's responsibility)
- Make API calls to any LLM provider
- Change existing template comments

## Non-Goals

- LLM client/provider implementation (user will build this)
- LLM prompt templates, personas, system prompts
- Cost optimization for LLM API calls
- R-3 through R-6 (eval tooling, rootPolicyTemperature, auto-restart) — separate initiatives
- Changing the existing template comment system
- Frontend changes
- Validation/calibration of LLM outputs (deferred per Q10)

## Approved Decisions (from clarifications + user re-scoping)

| q_id | Decision | Rationale |
|------|----------|-----------|
| Q1 | Signal emission only (R-1 rescoped) | User: "Your job is KataGo signal, not LLM interfacing" |
| Q2 | Emit structured event, provider-agnostic | User: "Just emit an event" |
| Q3 | Augment (signals additive, templates unchanged) | Confirmed |
| Q4 | N/A — no LLM cost in scope | User: "Not our problem" |
| Q5 | Backward-compatible: add-only schema changes | User confirmed |
| Q6 | Keep template system permanently | Confirmed |
| Q7 | Structured payload on PipelineContext + AiAnalysisResult | User: "Emit event like REST" |
| Q8 | Rich Payload (Option B) per governance panel | 9/9 panel votes |
| Q9 | N/A — persona is user's LLM concern | N/A |
| Q10 | Deferred — calibration later | User: "No answer now" |

## Scope

### Files Modified

| File | Change |
|------|--------|
| `analyzers/estimate_difficulty.py` | ✅ DONE: Added `compute_log_policy_score()`, `compute_score_lead_rank()`, `compute_position_closeness()` |
| `models/analysis_response.py` | ✅ DONE: Added `play_selection_value` to MoveAnalysis + parse from KataGo |
| `analyzers/stages/protocols.py` | ✅ DONE: Added `teaching_signals: dict` to PipelineContext |
| `analyzers/stages/difficulty_stage.py` | ✅ DONE: Compute and store teaching signals |
| `analyzers/teaching_signal_payload.py` | ⬜ UPGRADE: Add score_delta, refutation_depth/pv/type, conditional ownership, instructiveness gate |
| `models/ai_analysis_result.py` | ⬜ TODO: Add `teaching_signals: dict \| None` field, bump schema to v10 |
| `analyzers/result_builders.py` | ⬜ TODO: Propagate `score_delta`, `wrong_move_policy` to RefutationEntry |
| `config/teaching.py` | ⬜ TODO: Replace `LlmTeachingConfig` with `TeachingSignalConfig` (thresholds only) |
| `config/__init__.py` | ⬜ TODO: Wire `teaching_signal` config section |

### Files Created

| File | Purpose |
|------|---------|
| `tests/test_teaching_signals.py` | ✅ DONE: 21 tests for R-1 computed signals |

### Files NOT Modified (explicitly excluded)

- `analyzers/comment_assembler.py` — existing template system untouched
- `analyzers/teaching_comments.py` — existing template system untouched
- `analyzers/hint_generator.py` — hints untouched
- Frontend files — no frontend changes
- **NO LLM client file** — user's responsibility
- **NO LLM stage file** — user's responsibility

## Constraints

- C1: Zero behavior change when `teaching_signal.enabled=false` (default)
- C2: Schema v10 adds optional field only — no breaking changes, no field removals
- C3: No new KataGo queries — all signals derived from existing analysis data
- C4: Template comments continue as-is regardless of teaching signals
- C5: No LLM provider/API dependencies in this initiative
- C6: Pipeline must work identically with or without teaching signals enabled
