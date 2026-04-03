# Research Brief: Browser-Side Tiny LLM for Puzzle Teaching Enrichment

**Initiative ID**: `20260317-research-browser-tiny-llm`
**Date**: 2026-03-17
**Research Question**: Can a tiny LLM run in the browser to generate contextual teaching explanations, hints, or comments for Go tsumego puzzles — and is it worth the cost vs. the current template-based system?

---

## 1. Research Boundaries

**In scope**: Model candidates ≤2B params, browser runtime frameworks, architecture patterns (offline vs browser vs hybrid), integration with existing enrichment pipeline, quality assessment for Go-specific short-form text.

**Out of scope**: Training/fine-tuning a Go-specific model, server-side API inference, move generation or board evaluation (that remains KataGo's domain), any code implementation.

---

## 2. Internal Code Evidence

### 2.1 Current Template System (Enrichment Lab)

| Ref | File | What It Does |
|-----|------|-------------|
| I-1 | [analyzers/hint_generator.py](tools/puzzle-enrichment-lab/analyzers/hint_generator.py) | 3-tier progressive hints: Tier 1 (technique name from config), Tier 2 (reasoning from analysis context — depth, refutation count, DetectionResult evidence), Tier 3 (coordinate hint with `{!xy}` token). Level-adaptive hints via `level_category` param (entry/core/strong). |
| I-2 | [analyzers/comment_assembler.py](tools/puzzle-enrichment-lab/analyzers/comment_assembler.py) | 2-layer composition engine: technique_phrase + signal_phrase assembled under **15-word cap**. V2 supports instinct_phrase (Layer 0). Overflow strategy truncates mechanism suffix. |
| I-3 | [analyzers/teaching_comments.py](tools/puzzle-enrichment-lab/analyzers/teaching_comments.py) | Entry point wiring signal detection, vital move detection, wrong-move classification, comment assembly. Outputs: `correct_comment`, `vital_comment`, `wrong_comments`, `summary`, `hc_level`. |
| I-4 | [config/teaching-comments.json](config/teaching-comments.json) | ~20 technique entries with `comment`, `technique_phrase`, `vital_move_comment`, `hint_text`, `min_confidence`. Assembly rules: `composition="{technique_phrase} -- {signal_phrase}."`, `max_words=15`. |

**Key Constraint**: Current system is **deterministic and template-driven**. Voice principles (VP-1 through VP-5) enforce precision, confidence-gating, and technique-grounding. Comments are never emitted when uncertain.

### 2.2 Frontend Hint Display Pipeline

| Ref | File | Role |
|-----|------|------|
| I-5 | [frontend/src/hooks/useHints.ts](frontend/src/hooks/useHints.ts) | Progressive disclosure: reveals 3 tiers on user request. Manages `revealedHints`, `nextHintIndex`, `hintsUsed`. |
| I-6 | [frontend/src/lib/hints/token-resolver.ts](frontend/src/lib/hints/token-resolver.ts) | Resolves `{!xy}` coordinate tokens → human-readable notation (e.g. "D16") after applying board transforms (flip/rotation). |
| I-7 | [frontend/src/components/Solver/SolverView.tsx](frontend/src/components/Solver/SolverView.tsx#L146-L149) | `resolvedHints = metadata.hints.map(hint => resolveHintTokens(hint, boardSize, transformSettings))` — pure string processing on pre-computed hint text. |

**Key Observation**: The frontend currently receives **fully-formed text** from the SGF/DB. No generation happens client-side. Adding browser-side LLM would be a new computation path.

### 2.3 Existing WASM Precedent

| Ref | Evidence |
|-----|----------|
| I-8 | `sql.js@^1.11.0` already loads a WASM binary (~500KB), initializes it, and runs SQL queries in-memory. The project has established patterns for WASM asset management (postinstall copy to `public/`, Vite config). |
| I-9 | Frontend deps are lean: Preact, sql.js, goban, TailwindCSS. No heavy frameworks. Bundle consciousness is a project value. |

### 2.4 Enrichment Data Liberation Context (R-1)

| Ref | Evidence |
|-----|----------|
| I-10 | The `attrs` TEXT column in DB-1 `puzzles` table exists but is currently unused. R-1 proposes persisting 10+ enrichment signals (policy_entropy, correct_move_rank, difficulty components, tree completeness metrics) as JSON into `attrs`. |
| I-11 | If R-1 ships, the browser would have access to rich structured signals per puzzle — the exact inputs a tiny LLM would need to generate contextual explanations. |

---

## 3. External Evidence

### 3.1 Model Candidates

| Ref | Model | Params | ONNX/Quantized Size | Browser Runtime | Quality for Short Text | License |
|-----|-------|--------|---------------------|-----------------|----------------------|---------|
| E-1 | **SmolLM2-135M** | 135M | ~270MB (q4), ~140MB (q4 aggressive) | Transformers.js (ONNX), WebLLM (MLC) | Low — trained on 2T tokens, decent for continuation but weak instruction following (IFEval 29.9% avg). GSM8K 1.4%. | Apache 2.0 |
| E-2 | **SmolLM2-360M** | 360M | ~350MB (q4) | Transformers.js, WebLLM | Moderate — better IFEval but still limited reasoning. | Apache 2.0 |
| E-3 | **SmolLM2-1.7B** | 1.7B | ~1GB (q4) | Transformers.js, WebLLM | Good for summarization/rewriting. Function calling supported in instruct variant. | Apache 2.0 |
| E-4 | **Qwen2-0.5B** | 500M | ~500MB (q4) | Transformers.js, WebLLM | Moderate — strong multilingual, reasonable instruction following for size. | Apache 2.0 |
| E-5 | **TinyLlama-1.1B** | 1.1B | ~700MB (q4) | Transformers.js, WebLLM | Moderate — 3T token training, decent general capability. | Apache 2.0 |
| E-6 | **Phi-3-mini (3.8B)** | 3.8B | ~2.2GB (q4) | WebLLM only (too large for ONNX WASM) | High — excellent reasoning, instruction following. But 2.2GB is a hard sell for a puzzle app. | MIT |
| E-7 | **Gemma-2B** | 2B | ~1.3GB (q4) | WebLLM, MediaPipe | Good — strong benchmark scores for size. Supported by Google's MediaPipe LLM Inference API. | Gemma Terms |
| E-8 | **Gemma-3-270M** | 270M | ~250MB (litert) | MediaPipe LLM Inference API (WebGPU) | Low-Moderate — very new (litert-community conversion). Smallest Gemma variant. | Gemma Terms |
| E-9 | **Gemma-3n E2B** | ~2B effective | ~1.5GB (litert int4) | MediaPipe LLM Inference API (WebGPU) | High — multimodal, very new (2026), Google's latest efficient architecture. | Gemma Terms |

**Note**: RWKV models exist in small variants but lack mature ONNX/browser tooling — not recommended for this use case. Candle (HuggingFace Rust WASM) is promising but ecosystem is immature for production text generation.

### 3.2 Runtime Frameworks

| Ref | Framework | GPU Required? | Cold Start | Memory Footprint | Vite/Preact Compat | Notes |
|-----|-----------|--------------|------------|-----------------|-------------------|-------|
| E-10 | **Transformers.js** (HuggingFace) | No (WASM default), WebGPU optional | 2-10s model load (cached) | Model size + ~50MB runtime | Excellent (npm, ESM) | Broadest model support. Uses ONNX Runtime Web internally. q4/q8 quantization built-in. |
| E-11 | **WebLLM** (MLC-AI) | **Yes** (WebGPU mandatory) | 10-30s first load (compiles WASM+shader) | Model size + ~100MB runtime | Good (npm) | Best performance for large models. OpenAI-compatible API. Requires WebGPU browser. |
| E-12 | **ONNX Runtime Web** | No (WASM), WebGPU optional | 1-5s | Model size + ~30MB runtime | Good (npm) | Lowest-level, most control. Transformers.js is built on top. |
| E-13 | **MediaPipe LLM Inference** | **Yes** (WebGPU mandatory) | 5-15s | Model size + ~50MB WASM | Moderate (CDN/npm) | Google's on-device API. Now **deprecated** in favor of LiteRT-LM. Supports Gemma natively. |
| E-14 | **llama.cpp WASM** | No (CPU only) | 5-20s | Model size + ~10MB WASM | Poor (manual build) | Slowest inference but runs everywhere. No WebGPU dependency. Not recommended for interactive use. |

### 3.3 Inference Latency Expectations (Consumer Hardware)

Based on published benchmarks and community reports:

| Model Size | Runtime | Device | Tokens/sec | Time for 30-token response |
|-----------|---------|--------|-----------|--------------------------|
| 135M (q4) | Transformers.js WASM | Mid-range laptop CPU | 15-30 tok/s | ~1-2s |
| 135M (q4) | Transformers.js WebGPU | Mid-range GPU | 40-80 tok/s | <1s |
| 500M (q4) | Transformers.js WASM | Mid-range laptop CPU | 5-10 tok/s | ~3-6s |
| 1.7B (q4) | WebLLM WebGPU | Mid-range GPU | 15-30 tok/s | ~1-2s |
| 1.7B (q4) | Transformers.js WASM | Mid-range laptop CPU | 1-3 tok/s | ~10-30s ❌ |
| 3.8B (q4) | WebLLM WebGPU | Mid-range GPU | 8-15 tok/s | ~2-4s |

**Yen-Go latency budget**: The old 100ms constraint is lifted, but a puzzle app should still feel responsive. Target: **<3s for a hint explanation** is the upper bound before UX degrades.

### 3.4 Precedent: Educational Platforms with On-Device LLMs

| Ref | Platform | Approach | Notes |
|-----|----------|----------|-------|
| E-15 | **Lichess** (chess) | No on-device LLM. Uses Stockfish WASM for analysis. Explanations are template-based. | Closest analogy — proves template-based teaching works at scale. |
| E-16 | **Chess.com** | Server-side LLM for lesson generation. No browser AI. | Shows LLM enrichment adds value but keeps it server-side. |
| E-17 | **Duolingo** | Server-side Birdbrain (GPT-4 based) for explanations. Max Score feature uses ML. No browser LLM. | Their UX research: users strongly prefer AI-generated explanations over templates. |
| E-18 | **Khan Academy (Khanmigo)** | Server-side GPT-4. Socratic questioning pattern. No browser AI. | Gold standard for AI tutoring UX — but requires API backend. |
| E-19 | **OGS (Online Go Server)** | KataGo analysis server-side. Client displays pre-computed variations. No text generation. | Shows Go domain relies on tree analysis, not natural language. |

**Key Finding**: No known Go/Chess/educational platform currently runs an LLM in the browser for teaching. All use either templates (Lichess) or server-side LLMs (Duolingo, Khan Academy). Browser-side LLM for teaching would be a **first-of-kind** in this domain.

---

## 4. Candidate Architecture Adaptations for Yen-Go

### Architecture A: Offline Enrichment (Pipeline-Side LLM)

| Aspect | Assessment |
|--------|-----------|
| **How it works** | LLM runs during Python pipeline `analyze` stage. Generates richer teaching comments, Socratic questions, skill-adaptive explanations. Stored in SGF C[] and YH properties. |
| **Pros** | Zero browser overhead. Can use large models (GPT-4, Claude, local 7B+). Quality can be human-reviewed. No latency at puzzle-solve time. Deterministic per puzzle. |
| **Cons** | Not adaptive to user skill level at runtime. Same text for all users. Requires re-running pipeline to update. Increases SGF file size. |
| **Fits Yen-Go constraints** | ✅ Zero Runtime Backend. ✅ Static files. ✅ Deterministic. ❌ Not personalized. |
| **Integration** | Modify `teaching_comments.py` to call local LLM API. Add LLM-generated fields to comment_assembler output. |

### Architecture B: Browser-Side Inference

| Aspect | Assessment |
|--------|-----------|
| **How it works** | Tiny LLM loaded in browser via Transformers.js or WebLLM. Given structured signals (from R-1 `attrs` + technique tags), generates explanations on-demand. |
| **Pros** | Personalized to user level. Adaptive. Novel UX (first-of-kind in Go). Can generate Socratic questions. "Wow factor." |
| **Cons** | 140MB-1GB+ download for model. 2-30s cold start. Latency per generation. Mobile devices excluded (WASM too slow for >500M). WebGPU not universally available. Hallucination risk for Go-specific content. |
| **Fits Yen-Go constraints** | ✅ Zero Runtime Backend (runs locally). ✅ Local-first. ⚠️ Large download for a puzzle app. ⚠️ Quality risk. |
| **Integration** | New `frontend/src/services/llmService.ts`. Web Worker for inference. Modified `useHints` hook to call LLM when structured hints insufficient. |

### Architecture C: Hybrid (Structured Signals + Browser LLM)

| Aspect | Assessment |
|--------|-----------|
| **How it works** | Pipeline stores structured signals + seed prompts in `attrs`. Browser LLM does final text generation from structured input. Fallback to pre-computed templates if LLM unavailable. |
| **Pros** | Best of both worlds. Graceful degradation. Smaller prompts = faster inference. Structured input constrains hallucination. |
| **Cons** | Most complex architecture. Two paths to maintain (template fallback + LLM). Still has download/latency cost. |
| **Fits Yen-Go constraints** | ✅ Zero Runtime Backend. ✅ Graceful degradation. ⚠️ Complexity. |
| **Integration** | R-1 ships `attrs` signals → new `frontend/src/services/llmExplanationService.ts` → consumes `attrs` + hint data → generates text OR falls back to static hints. |

---

## 5. Risks and Concerns

| Risk | Severity | Mitigation |
|------|----------|-----------|
| **Go-specific hallucination** — LLM generates incorrect Go terminology or analysis | HIGH | None of the candidate models have Go-specific training. A 135M model saying "this captures via snapback" when it's actually a ladder would be *worse than no LLM at all*. Templates never hallucinate. |
| **Download budget** — 140MB+ model weights for a puzzle app that currently loads ~500KB DB + tiny SGF files | HIGH | Progressive loading, lazy model init, user opt-in. But fundamentally changes the app's lightweight character. |
| **WebGPU availability** — Required by WebLLM and MediaPipe. Not available on Firefox (behind flag), older Safari, all iOS browsers | MEDIUM | Transformers.js WASM fallback works without WebGPU but is 3-10x slower. |
| **Mobile performance** — WASM LLM inference on phones is prohibitively slow for models >500M params | HIGH | Limits viable models to 135M-360M range on mobile, where quality is lowest. |
| **Maintenance burden** — New WASM runtime, model versioning, quantization updates | MEDIUM | Transformers.js handles most of this, but model updates require testing. |
| **License compliance** — Gemma models have restricted-use terms (not pure Apache 2.0) | LOW | SmolLM2 and TinyLlama are Apache 2.0. Phi-3 is MIT. Stick to permissive licenses. |
| **Quality floor** — At 135M params, instruction-following quality (IFEval 29.9%) is fundamentally limited | HIGH | Cannot generate reliable Socratic questions or adaptive explanations at this scale. |

---

## 6. Planner Recommendations

### R-1: Ship Architecture A first (Offline Pipeline LLM) — LOW RISK, HIGH IMPACT

**Recommendation**: Use a server-side/local LLM (e.g. Claude, GPT-4, or local Llama-3-8B) during the enrichment pipeline to generate **richer, varied teaching comments** that replace the current templates. Store them statically in SGF/DB. This is a **Level 2-3** change touching `teaching_comments.py` and `comment_assembler.py`.

*Why*: All the UX uplift of "LLM-quality explanations" with zero browser cost. The template system's 15-word cap and voice principles can be applied as post-processing constraints on LLM output. Go-specific accuracy can be validated during pipeline review. No download penalty. No latency. No hallucination at runtime.

### R-2: Defer Architecture B/C (Browser LLM) until model quality reaches a threshold — HIGH RISK, UNCERTAIN REWARD

**Recommendation**: Do NOT invest in browser-side LLM inference until:
1. A sub-500M model exists that reliably follows Go-specific prompts (current models fail at this scale)
2. R-1's enrichment data liberation ships, providing structured signals for the browser LLM to consume
3. WebGPU reaches ≥90% browser coverage (currently ~70% on desktop, <30% on mobile)

The "wow factor" of browser-side AI is real, but **incorrect Go explanations are worse than no explanations**. A 135M model with 29.9% IFEval cannot reliably compose "Snapback — allow the capture, then recapture the larger group" when given only structured signals.

### R-3: If forced to pick a browser model today, use SmolLM2-360M + Transformers.js — MODERATE RISK

**Recommendation**: If browser LLM is pursued despite R-2 concerns:
- **Model**: SmolLM2-360M-Instruct (Apache 2.0, ~350MB q4, HuggingFace native)
- **Runtime**: Transformers.js v3 (WASM default, WebGPU optional, npm install, Vite-compatible)
- **Pattern**: Web Worker + lazy loading + user opt-in ("Enable AI explanations?")
- **Scope**: ONLY Tier 2 reasoning hints (the least Go-specific tier). Do NOT generate technique names (Tier 1) or coordinates (Tier 3) — let templates handle those.
- **Fallback**: Always show template-based hint immediately; LLM-generated text appears as "enhanced explanation" after generation completes.

### R-4: The minimum viable deployment is "template enhancement" in the pipeline — ZERO BROWSER COST

**Recommendation**: The smallest useful deployment is modifying `comment_assembler.py` to accept an optional LLM-generated `enhanced_explanation` field per technique, stored alongside the template comment. The frontend shows the template by default; a "Learn more" expansion reveals the richer explanation. This requires:
- One new field in teaching-comments config
- One new column or `attrs` sub-key in DB-1
- One UI expansion in `HintOverlay.tsx`

No WASM, no model download, no latency, no hallucination risk.

---

## 7. Confidence and Risk Update

| Metric | Value |
|--------|-------|
| `post_research_confidence_score` | 72/100 |
| `post_research_risk_level` | **high** (for browser LLM) / **low** (for pipeline LLM) |

**Confidence rationale**: High confidence that Architecture A (pipeline LLM) works well. Low confidence that any sub-500M model can generate reliable Go-specific teaching text in the browser. The technology is real and improving rapidly, but the quality floor for Go domain expertise is not met today.

---

## 8. Open Questions

| q_id | question | options | recommended | user_response | status |
|------|----------|---------|-------------|---------------|--------|
| Q1 | Is the goal personalization (adapt to user level at runtime) or enrichment (richer static text)? | A: Personalization / B: Enrichment / C: Both / Other | B: Enrichment (ship faster, lower risk) | | ❌ pending |
| Q2 | What is the acceptable model download size for the browser? | A: <100MB / B: <500MB / C: <1GB / D: No limit if opt-in / Other | D: No limit if opt-in | | ❌ pending |
| Q3 | Would you accept a pipeline-side LLM (Architecture A) as the first step, deferring browser LLM? | A: Yes, pipeline first / B: No, browser is the goal / C: Explore both in parallel / Other | A: Pipeline first | | ❌ pending |
| Q4 | Is there budget/willingness to fine-tune a tiny model on Go teaching text? Fine-tuning SmolLM2-135M on ~10K Go explanations could dramatically improve domain quality. | A: Yes / B: No / C: Explore later / Other | C: Explore later | | ❌ pending |
| Q5 | Should the browser LLM be visible as an "AI assistant" feature (explicit) or invisible (seamless hint generation)? | A: Explicit opt-in / B: Seamless / C: Progressive (seamless for hints, explicit for chat) / Other | A: Explicit opt-in | | ❌ pending |

---

## Handoff

```yaml
research_completed: true
initiative_path: TODO/initiatives/20260317-research-browser-tiny-llm/
artifact: 15-research.md
top_recommendations:
  - "R-1: Ship pipeline-side LLM enrichment first (Architecture A) — low risk, high impact"
  - "R-2: Defer browser LLM until sub-500M models reach Go-domain quality threshold"
  - "R-3: If browser LLM needed now, use SmolLM2-360M + Transformers.js, limited to Tier 2 hints only"
  - "R-4: Minimum viable = 'enhanced_explanation' field in pipeline, zero browser cost"
open_questions: [Q1, Q2, Q3, Q4, Q5]
post_research_confidence_score: 72
post_research_risk_level: high
```
