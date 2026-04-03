# Plan: KataGo Teaching Signal Emission

> **Initiative**: 20260326-1400-feature-llm-teaching-enrichment
> **Date**: 2026-03-27 (rescoped)

---

## Execution Phases

### Phase 1: ✅ DONE — R-1 Computed Signals

Already implemented and verified (21/21 tests passing):

1. ✅ Added `compute_log_policy_score()`, `compute_score_lead_rank()`, `compute_position_closeness()` to `estimate_difficulty.py`
2. ✅ Added `play_selection_value` to `MoveAnalysis` model + parse from KataGo response
3. ✅ Added `teaching_signals: dict` field to `PipelineContext`
4. ✅ Built basic `TeachingSignalPayload` builder (correct move + minimal wrong move signals)
5. ✅ Wired signal computation in `DifficultyStage`
6. ✅ Added tests for all three signal functions (21 tests)

### Phase 2: ⬜ Signal Pipeline Enhancement (rescoped)

Close pipeline data gaps and upgrade to Option B rich payload:

1. **Propagate lost fields** — Add `score_delta: float = 0.0` and `wrong_move_policy: float = 0.0` to `RefutationEntry` in `ai_analysis_result.py`. Map them in `build_refutation_entries()` in `result_builders.py`.
2. **Store ownership_delta per refutation** — In `generate_single_refutation()`, add `root_ownership: list[float] | None = None` parameter. Call `compute_ownership_delta(root_ownership, after_wrong.ownership, board_size)` and store on new `Refutation.ownership_delta: float = 0.0` field. In `generate_refutations()` orchestrator, pass `initial_analysis.ownership` through to the new param.
2b. **Propagate ownership_delta** — Add `ownership_delta: float = 0.0` to `RefutationEntry`. Map in `build_refutation_entries()`.
3. **Replace LlmTeachingConfig with TeachingSignalConfig** — Remove LLM-specific fields (provider, model, api_key, system_prompt, prompts). Keep: `enabled`, `max_wrong_moves`, `instructiveness_threshold`, `seki_closeness_threshold`, `ownership_delta_threshold`.
4. **Wire TeachingSignalConfig in EnrichmentConfig** — Add `teaching_signal: TeachingSignalConfig | None = None` field.
5. **Upgrade teaching_signal_payload.py** — Add to wrong-move signals: `score_delta`, `wrong_move_policy`, `refutation_depth`, `refutation_pv`, `refutation_type`, conditional `ownership_delta_max`. Implement instructiveness gate with seki exception. Accept `board_size` parameter (fix hardcode). Accept config for thresholds.
6. **Persist teaching_signals on AiAnalysisResult** — Add `teaching_signals: dict | None = None` field. Bump schema to v10. Wire in AssemblyStage (after refutations wired, before `ctx.result = result`).

**CRITICAL BUG FIX (T5b, pre-requisite)**: Relocate `build_teaching_signal_payload()` call from DifficultyStage (stage 7) to AssemblyStage (stage 8). Current placement runs with `ctx.result=None`, making `wrong_move_signals` always empty. Individual signal computations (log_policy, score_lead_rank, position_closeness) stay in DifficultyStage.

### Phase 3: ⬜ Testing + Validation

1. Add tests for Option B payload (score_delta, refutation data, instructiveness gate, seki exception, ownership conditional)
2. Add tests for RefutationEntry new fields propagation
3. Add test for AiAnalysisResult schema v10 with teaching_signals field
4. Run enrichment-regression suite — verify zero behavior change
5. Run backend-unit-regression
6. Verify existing tests still pass with new defaults (backward compatibility)

### Phase 4: ⬜ Documentation

1. Update `tools/puzzle-enrichment-lab/AGENTS.md` with teaching signal architecture

## Documentation Plan

| files_to_update | why_updated |
|----------------|-------------|
| `tools/puzzle-enrichment-lab/AGENTS.md` | New teaching signal payload, new config model, schema v10 |

| files_to_create | why_created |
|----------------|-------------|
| (none) | Pipeline-internal feature, no user-facing docs |

## Target Teaching Signal Payload Schema (Option B: Rich Payload)

```json
{
  "version": 1,
  "correct_move": {
    "move_gtp": "D4",
    "move_sgf": "dd",
    "log_policy_score": 0.72,
    "score_lead_rank": 1.0,
    "play_selection_value": 0.85
  },
  "position": {
    "root_winrate": 0.63,
    "root_score": 2.1,
    "position_closeness": 0.74,
    "policy_entropy": 1.23,
    "correct_move_rank": 1
  },
  "wrong_moves": [
    {
      "move_gtp": "E5",
      "move_sgf": "ee",
      "log_policy": 0.61,
      "score_lead_rank": 0.2,
      "delta": -0.35,
      "score_delta": -8.2,
      "wrong_move_policy": 0.08,
      "refutation_depth": 3,
      "refutation_pv": ["ee", "df", "ce"],
      "refutation_type": "opponent_lives",
      "ownership_delta_max": 0.45,
      "instructive": true,
      "seki_exception": false
    }
  ]
}
```

**Notes:**
- `ownership_delta_max` only emitted when > `ownership_delta_threshold` (default 0.3) per RC-3
- `instructive` is true when `abs(delta) >= instructiveness_threshold` OR seki exception triggered
- `seki_exception` is true when `position_closeness > seki_closeness_threshold` and delta below instructiveness threshold
- `wrong_moves` capped at `max_wrong_moves` (default 3)
