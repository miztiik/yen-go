# Tasks: KataGo Teaching Signal Emission

> **Initiative**: 20260326-1400-feature-llm-teaching-enrichment
> **Date**: 2026-03-27 (rescoped)

---

## Task Graph

### Phase 1: ✅ DONE — Computed Signals

| task_id | title | phase | depends_on | parallel | status |
|---------|-------|-------|-----------|----------|--------|
| T1 | Add computed signal functions to estimate_difficulty.py | 1 | — | [P] | ✅ done |
| T2 | Add play_selection_value to MoveAnalysis + parse | 1 | — | [P] | ✅ done |
| T3 | Add teaching_signals to PipelineContext | 1 | — | [P] | ✅ done |
| T4 | Build basic TeachingSignalPayload builder | 1 | T1 | — | ✅ done |
| T5 | Compute signals in DifficultyStage | 1 | T1, T3 | — | ✅ done |
| T6 | Tests for R-1 signals (21 tests) | 1 | T1, T4, T5 | — | ✅ done |

### Phase 2: ✅ DONE — Signal Pipeline Enhancement

| task_id | title | phase | depends_on | parallel | status | files | evidence_gap |
|---------|-------|-------|-----------|----------|--------|-------|-------------|
| T5b | Relocate payload build to AssemblyStage (critical bug fix) | 2 | — | — | ✅ done | `analyzers/stages/difficulty_stage.py`, `analyzers/stages/assembly_stage.py` | BUG: ctx.result is None when DifficultyStage runs |
| T7 | Add `score_delta` + `wrong_move_policy` to RefutationEntry | 2 | — | [P] | ✅ done | `models/ai_analysis_result.py` | Gap-1, Gap-2 |
| T8 | Propagate score_delta + wrong_move_policy in build_refutation_entries() | 2 | T7 | — | ✅ done | `analyzers/result_builders.py` | Gap-1, Gap-2 |
| T9 | Store ownership_delta on Refutation in generate_single_refutation() | 2 | — | [P] | ✅ done | `analyzers/generate_refutations.py`, `models/refutation_result.py` | Gap-3, RC-3 |
| T8b | Propagate ownership_delta in build_refutation_entries() | 2 | T7, T9 | — | ✅ done | `analyzers/result_builders.py`, `models/ai_analysis_result.py` | Data path: ownership_delta needs to be on RefutationEntry for payload builder |
| T10 | Replace LlmTeachingConfig with TeachingSignalConfig | 2 | — | [P] | ✅ done | `config/teaching.py` | User re-scope |
| T11 | Wire TeachingSignalConfig in EnrichmentConfig | 2 | T10 | — | ✅ done | `config/__init__.py` | — |
| T12 | Upgrade teaching_signal_payload.py to Option B rich payload | 2 | T5b, T8, T8b, T11 | — | ✅ done | `analyzers/teaching_signal_payload.py` | RC-1, RC-2, RC-3 |
| T13 | Add teaching_signals to AiAnalysisResult + bump schema v10 | 2 | — | [P] | ✅ done | `models/ai_analysis_result.py` | Gap-4 |
| T14 | Wire teaching_signals persistence in AssemblyStage | 2 | T5b, T12, T13 | — | ✅ done | `analyzers/stages/assembly_stage.py` | Gap-4 |

### Phase 3: ✅ DONE — Testing

| task_id | title | phase | depends_on | parallel | status |
|---------|-------|-------|-----------|----------|--------|
| T15 | Tests for RefutationEntry new fields propagation | 3 | T8 | [P] | ✅ done |
| T16 | Tests for Option B payload (score_delta, ownership, instructiveness gate, seki exception) | 3 | T12 | [P] | ✅ done |
| T17 | Tests for AiAnalysisResult schema v10 + teaching_signals field | 3 | T13, T14 | [P] | ✅ done |
| T18 | Run enrichment-regression suite (zero behavior change) | 3 | T15, T16, T17 | — | ✅ done |
| T19 | Run backend-unit-regression | 3 | T18 | — | ✅ done |

### Phase 4: ✅ DONE — Documentation

| task_id | title | phase | depends_on | parallel | status |
|---------|-------|-------|-----------|----------|--------|
| T20 | Update AGENTS.md with teaching signal architecture | 4 | T19 | — | ✅ done |

---

## Task Details

### T5b: Relocate payload build to AssemblyStage (CRITICAL BUG FIX)

**Files**: `analyzers/stages/difficulty_stage.py`, `analyzers/stages/assembly_stage.py`
**Bug**: `build_teaching_signal_payload()` currently runs in DifficultyStage (stage 7) with `result=ctx.result`. But `ctx.result` is set by AssemblyStage (stage 8), which runs AFTER DifficultyStage. Therefore `ctx.result` is **always None** when the payload builder runs, and `wrong_move_signals` is **always an empty list**.
**Fix**:
1. Remove the `build_teaching_signal_payload()` call from DifficultyStage (keep the signal function computations — `compute_log_policy_score()`, `compute_score_lead_rank()`, `compute_position_closeness()` — they are correctly placed since they only need `AnalysisResponse`, not `AiAnalysisResult`)
2. Move the payload build call to AssemblyStage, after refutations are wired (`result.refutations = build_refutation_entries(ctx.refutation_result)`) and before `ctx.result = result`
3. The payload builder needs access to: `ctx.analysis_response`, `ctx.correct_move_gtp`, `ctx.policy_entropy`, `ctx.correct_move_rank`, and the now-populated `result`
**Impact**: Without this fix, T12 (Option B upgrade) is impossible — the payload builder would never have refutation data.

### T7: Add score_delta + wrong_move_policy to RefutationEntry

**File**: `models/ai_analysis_result.py`
**Change**: Add two fields to `RefutationEntry` class:
```python
score_delta: float = 0.0   # Score delta (points lost) — already on Refutation, was dropped
wrong_move_policy: float = 0.0  # KataGo policy prior for the wrong move — how tempting it looks
```
**Backward compat**: Both default to 0.0 — existing serialized data unchanged.

### T8: Propagate score_delta + wrong_move_policy in build_refutation_entries()

**File**: `analyzers/result_builders.py`
**Change**: Map `ref.score_delta` → `RefutationEntry.score_delta` and `ref.wrong_move_policy` → `RefutationEntry.wrong_move_policy`.
**Evidence**: Currently `build_refutation_entries()` drops these fields (see Gap-1, Gap-2 in research).

### T9: Store ownership_delta on Refutation in generate_single_refutation()

**File**: `analyzers/generate_refutations.py`, `models/refutation_result.py`
**Change**: 
1. Add `ownership_delta: float = 0.0` to `Refutation` model (**new field**, NOT repurposing dead `ownership_consequence: dict` which has wrong type)
2. Add `root_ownership: list[float] | None = None` parameter to `generate_single_refutation()` signature (currently missing — only `initial_winrate` and `initial_score` are passed, not ownership)
3. In `generate_single_refutation()`, after obtaining `after_wrong` analysis, call `compute_ownership_delta(root_ownership, after_wrong.ownership, board_size)` and store on `refutation.ownership_delta`
4. In `generate_refutations()` orchestrator, pass `initial_analysis.ownership` to `generate_single_refutation()` (already available as `initial_analysis: AnalysisResponse` parameter which has `.ownership: list[float] | None`)
**Evidence**: `compute_ownership_delta()` exists at generate_refutations.py:36. Currently called in `identify_candidates()` with `analysis.ownership` as root_ownership (line 228, 243, 255). The `after_wrong` analysis response already has `.ownership` because `include_ownership=True` is set at line 388.

### T8b: Propagate ownership_delta in build_refutation_entries()

**Files**: `analyzers/result_builders.py`, `models/ai_analysis_result.py`
**Change**: 
1. Add `ownership_delta: float = 0.0` to `RefutationEntry` in `ai_analysis_result.py`
2. Map `ref.ownership_delta` → `RefutationEntry.ownership_delta` in `build_refutation_entries()`
**Rationale**: The payload builder reads from `result.refutations` (RefutationEntry list). For ownership_delta_max to be available, ownership_delta must be propagated through the serialized model, not read from ephemeral `ctx.refutation_result`.
**Backward compat**: Default 0.0, add-only.

### T10: Replace LlmTeachingConfig with TeachingSignalConfig

**File**: `config/teaching.py`
**Change**: Remove `LlmTeachingConfig` class (has LLM-specific fields). Add:
```python
class TeachingSignalConfig(BaseModel):
    enabled: bool = False
    max_wrong_moves: int = 3
    instructiveness_threshold: float = 0.05  # RC-2: config-driven
    seki_closeness_threshold: float = 0.9    # RC-1: seki exception gate
    ownership_delta_threshold: float = 0.3   # RC-3: conditional emission
```
**Rationale**: User directive: "Your job is signal emission, not LLM interfacing."

### T11: Wire TeachingSignalConfig in EnrichmentConfig

**File**: `config/__init__.py`
**Change**: Add `teaching_signal: TeachingSignalConfig | None = None` field to `EnrichmentConfig`.

### T12: Upgrade teaching_signal_payload.py to Option B rich payload

**File**: `analyzers/teaching_signal_payload.py`
**Change**: 
1. Accept `config: TeachingSignalConfig | None = None` parameter (or read from `EnrichmentConfig`)
2. Accept `board_size: int = 19` parameter (fix hardcoded board_size)
3. Add to wrong-move signals: `score_delta`, `wrong_move_policy`, `refutation_depth`, `refutation_pv`, `refutation_type`, conditional `ownership_delta_max`
4. Implement instructiveness gate: `abs(delta) >= threshold` OR seki exception
5. Seki exception: `position_closeness > seki_closeness_threshold` bypasses threshold
6. Add payload `version: 1` key
7. Restructure into `correct_move`, `position`, `wrong_moves` sections (see 30-plan.md payload schema)
8. `ownership_delta_max` only emitted when > `ownership_delta_threshold` (default 0.3) per RC-3
9. `wrong_moves` capped at `max_wrong_moves` from config (default 3)
**Dependencies**: T5b (payload now runs in AssemblyStage with populated result), T8 (score_delta/wrong_move_policy on RefutationEntry), T8b (ownership_delta on RefutationEntry), T11 (config wired)

### T13: Add teaching_signals to AiAnalysisResult + bump schema v10

**File**: `models/ai_analysis_result.py`
**Change**: Add `teaching_signals: dict | None = None` field. Increment `SCHEMA_VERSION` from 9 to 10.
**Backward compat**: None default — existing tests/data unaffected.

### T14: Wire teaching_signals persistence in AssemblyStage

**File**: `analyzers/stages/assembly_stage.py` (NOT result_builders.py)
**Change**: Add `result.teaching_signals = ctx.teaching_signals` in `AssemblyStage.run()`, after existing field wiring (around line 230), before the final `ctx.result = result`.
**Evidence**: The existing pattern is direct attribute assignment: `result.refutations = build_refutation_entries(...)`, `result.difficulty = build_difficulty_snapshot(...)`, etc. The `assembly_stage.py` is where PipelineContext data gets wired into AiAnalysisResult for the full (tier-3) pipeline. `result_builders.py::build_partial_result()` only handles tier-1/tier-2 partial enrichment paths.

### T15–T17: Testing

- **T15**: Test that `build_refutation_entries()` now propagates `score_delta` and `wrong_move_policy`
- **T16**: Test Option B payload with populated refutations (not just `result=None`), instructiveness gate true/false, seki exception at boundary (closeness == threshold → inclusive), conditional ownership (above/below threshold), board_size=9 fixture, config-off behavior (enabled=false → no payload computed, validates C1)
- **T17**: Test that `AiAnalysisResult` serialization includes `teaching_signals` when present

### T18–T19: Regression

- **T18**: `enrichment-regression` task — verify all existing tests still pass
- **T19**: `backend-unit-regression` task — verify no backend regressions

### T20: Documentation

- Update AGENTS.md with: TeachingSignalConfig model, teaching_signal_payload.py architecture, Option B payload schema, schema v10 field

---

## Removed Tasks (user directive)

| Old task_id | Title | Reason removed |
|-------------|-------|----------------|
| T9 (old) | Build TeachingLLMClient interface + OpenAI impl | "I will take care of LLM interfacing" |
| T10 (old) | Build LlmTeachingStage pipeline stage | "Just emit an event" |
| T11 (old) | Add LlmTeachingStage to pipeline | Removed with stage |
| T13 (old) | Tests for LLM teaching stage (mocked) | N/A |
