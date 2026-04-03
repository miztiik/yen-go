# Research Consolidation: KataGo Teaching Signal Emission

> **Initiative**: 20260326-1400-feature-llm-teaching-enrichment
> **Date**: 2026-03-27 (updated with gap analysis)
> **Sources**: 20260326-research-katago-llm-team-analysis, 20260326-research-katascript-katago-patterns, internal codebase archaeology

---

## 1. External Research Summary

### Source 1: BrightonLiu-zZ/KataGo-LLM-Team
- **What they do**: Train Qwen3-8B to play 9×9 Go using KataGo as teacher via GRPO alignment
- **Key signals adopted**:
  - **Log-scaled policy** formula: `(log10(max(P, 1e-6)) + 6.0) / 6.0` → smooth 0-1 mapping revealing hidden tesuji vs obvious moves
  - **Percentile rank by scoreLead**: How bad a wrong move is relative to alternatives → `score_lead_rank`
  - **Position closeness**: `1.0 - 2.0 * |root_winrate - 0.5|` → adapts urgency/tone
- **Influenced decisions**: Formulas for R-1 signals, instructiveness gate concept, seki exception logic

### Source 2: psy777/katascript
- **What they do**: Minimal KataGo analysis CLI (~400 lines, 0 stars)
- **Key finding**: `playSelectionValue` KataGo field not captured by Yen-Go → now captured in MoveAnalysis
- **Assessment**: Low impact, single field addition

## 2. Signal Gap Analysis (Current vs Target)

| ID | Signal | Status | Source File | Notes |
|----|--------|--------|-------------|-------|
| SG-1 | `log_policy_score` | ✅ Implemented | `estimate_difficulty.py` | `compute_log_policy_score()` |
| SG-2 | `score_lead_rank` | ✅ Implemented | `estimate_difficulty.py` | `compute_score_lead_rank()` |
| SG-3 | `position_closeness` | ✅ Implemented | `estimate_difficulty.py` | `compute_position_closeness()` |
| SG-4 | `playSelectionValue` | ✅ Captured | `analysis_response.py` | `play_selection_value` on MoveAnalysis |
| SG-5 | `score_delta` on wrong moves | ❌ **Lost** in pipeline | See Gap-1 below | Computed in `generate_refutations.py` but dropped at `build_refutation_entries()` |
| SG-6 | `wrong_move_policy` on wrong moves | ❌ **Lost** in pipeline | See Gap-2 below | Available on `Refutation` but dropped at `build_refutation_entries()` |
| SG-7 | `ownership_delta_max` | ❌ **Ephemeral** | See Gap-3 below | Computed in `identify_candidates()` for ranking but never stored on `Refutation` |
| SG-8 | `refutation_pv` + `refutation_type` + `refutation_depth` | ✅ Available | `ai_analysis_result.py` | Already on `RefutationEntry` |
| SG-9 | Instructiveness gate | ❌ **Not implemented** | N/A | Governance RC-1/RC-2: needs seki exception + config thresholds |
| SG-10 | Teaching signals on AiAnalysisResult | ❌ **Not persisted** | `protocols.py` only | Signals on PipelineContext but NOT on output model |

## 3. Pipeline Data Flow Gaps (Detailed Evidence)

### Gap-1: `score_delta` lost at build_refutation_entries()

**Evidence chain:**
1. `generate_single_refutation()` computes `score_delta = score_after - initial_score` (generates_refutations.py)
2. Stores on `Refutation.score_delta` (refutation_result.py — field exists: `score_delta: float = 0.0`)
3. `build_refutation_entries()` in `result_builders.py` maps to `RefutationEntry` but **drops score_delta**
4. `RefutationEntry` has `delta` (winrate delta only), no `score_delta` field

**Fix**: Add `score_delta: float = 0.0` to `RefutationEntry` and map it in `build_refutation_entries()`.

### Gap-2: `wrong_move_policy` lost at build_refutation_entries()

**Evidence chain:**
1. `generate_single_refutation()` receives `policy_prior` from candidate move info
2. Stores on `Refutation.wrong_move_policy` (refutation_result.py — field exists: `wrong_move_policy: float = 0.0`)
3. `build_refutation_entries()` **drops wrong_move_policy**
4. `RefutationEntry` has no `wrong_move_policy` field

**Fix**: Add `wrong_move_policy: float = 0.0` to `RefutationEntry` and map it in `build_refutation_entries()`.

### Gap-3: `ownership_delta` computed but ephemeral

**Evidence chain:**
1. `compute_ownership_delta()` in `generate_refutations.py` computes max absolute ownership change
2. Parameters: `root_ownership: list[float] | None, move_ownership: list[list[float]] | list[float] | None, board_size`
3. Returns `float` — max abs delta across all intersections (0.0 if data unavailable)
4. Called in `identify_candidates()` for candidate scoring/ranking only
5. **Never stored** on `Refutation` model at all (ephemeral local variable)
6. `Refutation.ownership_consequence` field exists but is always `{}` (dead field)

**Fix for RC-3**: Compute ownership_delta per-refutation in `generate_single_refutation()` and store it. Emit in teaching signal payload conditionally (only when > 0.3 per governance RC-3).

### Gap-4: Teaching signals not persisted to output

**Evidence chain:**
1. `DifficultyStage` calls `build_teaching_signal_payload()` → stores in `ctx.teaching_signals` (PipelineContext)
2. PipelineContext is ephemeral — it dies after `enrich_single()` completes
3. `AiAnalysisResult` (the persisted output model) has NO `teaching_signals` field
4. Signals are computed but never written to the output JSON

**Fix**: Add `teaching_signals: dict | None = None` to `AiAnalysisResult` (schema v10). Wire in assembly or writeback stage.

## 4. Refutation Pipeline Field Inventory

### Stage-by-stage field propagation

| Field | `generate_single_refutation()` | `Refutation` model | `build_refutation_entries()` | `RefutationEntry` | Teaching Signal? |
|-------|------|------|------|------|------|
| `wrong_move` | ✅ | ✅ | ✅ | ✅ `wrong_move` | ✅ `move_sgf` |
| `refutation_pv` | ✅ | ✅ `refutation_sequence` | ✅ | ✅ `refutation_pv` | ✅ |
| `refutation_branches` | ✅ | ✅ | ✅ | ✅ | ❌ not in signal |
| `winrate_delta` | ✅ | ✅ | ✅ | ✅ `delta` | ✅ `delta` |
| **`score_delta`** | ✅ | ✅ | ❌ **DROPPED** | ❌ missing | ❌ **GAP** |
| **`wrong_move_policy`** | ✅ | ✅ | ❌ **DROPPED** | ❌ missing | ❌ **GAP** |
| `winrate_after_wrong` | ✅ | ✅ | ❌ dropped | ❌ | ❌ |
| **`ownership_delta`** | ❌ not computed | ❌ | ❌ | ❌ | ❌ **GAP** |
| `refutation_depth` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `refutation_type` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `tenuki_flagged` | ✅ | ✅ | ❌ dropped | ❌ | ❌ |

### Refutation Classifier Conditions (11 conditions)

The classifier in `refutation_classifier.py` maps refutations to one of 11 conditions:
1. `immediate_capture` — Wrong move leads to immediate capture
2. `opponent_escapes` — Wrong move allows opponent to escape
3. `opponent_lives` — Wrong move allows opponent to live
4. `capturing_race_lost` — Wrong move loses a capturing race
5. `opponent_takes_vital` — Wrong move allows opponent to seize vital point
6. `opponent_reduces_liberties` — Wrong move allows liberty reduction
7. `self_atari` — Wrong move is self-atari
8. `shape_death_alias` — Wrong move matches death shape pattern
9. `ko_involved` — Wrong move creates or involves a ko
10. `wrong_direction` — Move is tactically off-direction
11. `default` — Unclassified

These conditions map to `refutation_type` on `RefutationEntry` and are available for teaching signal consumers.

## 5. Existing Implementation Status

### ✅ Already Implemented (Phase 1, verified passing)

| Component | File | Tests | Status |
|-----------|------|-------|--------|
| `compute_log_policy_score()` | `estimate_difficulty.py` | 8 tests | ✅ Passing |
| `compute_score_lead_rank()` | `estimate_difficulty.py` | 6 tests | ✅ Passing |
| `compute_position_closeness()` | `estimate_difficulty.py` | 5 tests | ✅ Passing |
| `play_selection_value` parsing | `analysis_response.py` | part of existing tests | ✅ Passing |
| `teaching_signals: dict` on PipelineContext | `protocols.py` | — | ✅ |
| DifficultyStage wiring | `difficulty_stage.py` | — | ✅ |
| Basic `build_teaching_signal_payload()` | `teaching_signal_payload.py` | 3 tests | ✅ Passing |

**Total: 21/21 signal tests passing** (verified via `pytest tests/test_teaching_signals.py`)

### ⬜ Needs Implementation (Phase 2, rescoped)

| Component | File | Evidence Gap |
|-----------|------|-------------|
| Upgrade payload to Option B (rich wrong-move signals) | `teaching_signal_payload.py` | Gap-1, Gap-2, Gap-3 |
| Add `score_delta`, `wrong_move_policy` to `RefutationEntry` | `ai_analysis_result.py` | Gap-1, Gap-2 |
| Propagate fields in `build_refutation_entries()` | `result_builders.py` | Gap-1, Gap-2 |
| Instructiveness gate + seki exception (RC-1) | `teaching_signal_payload.py` | RC-1 |
| Config-driven thresholds (RC-2) | `config/teaching.py` | RC-2 |
| Conditional ownership emission (RC-3) | `teaching_signal_payload.py` + `generate_refutations.py` | Gap-3, RC-3 |
| Persist `teaching_signals` on `AiAnalysisResult` (schema v10) | `ai_analysis_result.py` | Gap-4 |
| Replace `LlmTeachingConfig` with `TeachingSignalConfig` | `config/teaching.py` | User re-scope |
| Wire config in EnrichmentConfig | `config/__init__.py` | — |
| Additional tests for Option B payload | `tests/test_teaching_signals.py` | — |

### ❌ Removed from Scope (user directed)

| Component | Reason |
|-----------|--------|
| `TeachingLLMClient` interface + OpenAI impl | "I will take care of LLM interfacing" |
| `LlmTeachingStage` pipeline stage | "Just emit an event" |
| `llm_teaching_comments` output field | Replaced by `teaching_signals` dict |
| LLM-specific config (provider, model, api_key, prompts) | Not our job |
| LLM mocked tests | N/A |

## 6. `compute_ownership_delta()` Implementation Reference

From `generate_refutations.py`:

```python
def compute_ownership_delta(
    root_ownership: list[float] | None,
    move_ownership: list[list[float]] | list[float] | None,
    board_size: int = 19,
) -> float:
    # Returns max absolute ownership change across all intersections
    # 0.0 if either ownership array is N/A
    # Handles both flat and nested ownership arrays
```

Currently used only for candidate ranking in `identify_candidates()`. Can be reused for per-refutation ownership delta by calling it with root ownership + post-wrong-move ownership.

## 7. Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| `score_delta`/`wrong_move_policy` propagation breaks existing serialization | Low | Medium | Add-only fields with defaults; assert backward compat in test |
| Ownership delta computation slows pipeline | Low | Low | Already computed for candidates; marginal cost per refutation |
| Seki exception triggers too broadly | Medium | Low | Config-driven threshold (RC-2), gate at closeness > 0.9 |
| Teaching signal payload too large | Low | Low | Only top-3 wrong moves; ownership conditional on > 0.3 |
| Schema v10 breaks downstream consumers | Low | High | Optional field with None default; no field removal |

## 8. Critical Bug: wrong_move_signals Always Empty (Discovered 2026-03-27)

**Severity**: CRITICAL for this initiative (Phase 2 T12 depends on fix)

**Root cause**: `build_teaching_signal_payload()` runs in DifficultyStage (stage 7) with `result=ctx.result`. But `ctx.result` is set by AssemblyStage (stage 8), which runs AFTER DifficultyStage. Therefore `result=None` when the payload builder runs, and `wrong_move_signals` is always `[]`.

**Evidence**:
- DifficultyStage calls `build_teaching_signal_payload()` at difficulty_stage.py line ~151-157 with `result=ctx.result`
- Stage pipeline order: 7=DifficultyStage → 8=AssemblyStage (which sets ctx.result)
- Phase 1 tests (21 passing) all test with `result=None` default — they never caught this

**Impact**: Without fix, T12 (Option B payload with rich wrong-move signals) is impossible — the builder would never have refutation data.

**Fix**: T5b — relocate the payload build call from DifficultyStage to AssemblyStage (after refutations are wired, before `ctx.result = result`). Keep individual signal computations (log_policy, score_lead_rank, position_closeness) in DifficultyStage since they only need `AnalysisResponse`.

## 9. Additional Findings (2026-03-27 Deep Research)

| Finding | Impact | Resolution |
|---------|--------|------------|
| `board_size` hardcoded to 19 in teaching_signal_payload.py | Minor | Fold fix into T12: accept `board_size` parameter |
| `LlmTeachingConfig` has zero references outside its definition | None | Safe to remove in T10 |
| No JSON config section exists for `teaching_signal` | None | Code-default is sufficient (disabled by default) |
| `AiAnalysisResult.from_validation()` has fixed params, no **kwargs | None | T14 uses direct attribute assignment pattern |
| `Refutation.ownership_consequence: dict` is dead field (always `{}`) | Low | Do not repurpose (wrong type); add new `ownership_delta: float = 0.0` |
