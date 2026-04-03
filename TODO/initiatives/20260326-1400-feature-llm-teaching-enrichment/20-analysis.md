# Analysis: KataGo Teaching Signal Emission

> **Initiative**: 20260326-1400-feature-llm-teaching-enrichment
> **Date**: 2026-03-27 (rescoped)

---

## Impact Analysis

### Correct Move Signals (already implemented)

| Signal | Formula | Input | Output Range | Computation Cost |
|--------|---------|-------|-------------|-----------------|
| `log_policy_score` | `(log10(max(P, 1e-6)) + 6.0) / 6.0` | `policy_prior` per move | [0.0, 1.0] | O(1) per move |
| `score_lead_rank` | percentile rank of score_lead among all evaluated moves | `score_lead` per move | [0.0, 1.0] | O(n log n) per puzzle |
| `position_closeness` | `1.0 - 2.0 * abs(root_winrate - 0.5)` | `root_winrate` | [0.0, 1.0] | O(1) per puzzle |

All three signals are pure functions of existing `AnalysisResponse` data. Zero new KataGo queries.

### Wrong Move Signals (Option B: Rich Payload — needs implementation)

| Signal | Source | Currently Available | Pipeline Gap |
|--------|--------|-------------------|-------------|
| `move_sgf` / `move_gtp` | RefutationEntry.wrong_move | ✅ on RefutationEntry | None |
| `log_policy` | MoveAnalysis.policy_prior | ✅ on AnalysisResponse | None (already in basic payload) |
| `score_lead_rank` | Computed from AnalysisResponse | ✅ | None (already in basic payload) |
| `delta` (winrate) | RefutationEntry.delta | ✅ on RefutationEntry | None (already in basic payload) |
| **`score_delta`** | Refutation.score_delta | ✅ on Refutation model | **❌ Dropped at build_refutation_entries()** |
| **`wrong_move_policy`** | Refutation.wrong_move_policy | ✅ on Refutation model | **❌ Dropped at build_refutation_entries()** |
| `refutation_depth` | RefutationEntry.refutation_depth | ✅ on RefutationEntry | None |
| `refutation_pv` | RefutationEntry.refutation_pv | ✅ on RefutationEntry | None |
| `refutation_type` | RefutationEntry.refutation_type | ✅ on RefutationEntry | None |
| **`ownership_delta_max`** | compute_ownership_delta() | ✅ function exists | **❌ Not stored on Refutation** |

### Instructiveness Gate (RC-1, RC-2)

The gate filters which wrong moves are "interesting enough" for teaching signal emission.

**Default logic**: Emit signal for wrong move only if `abs(delta) >= instructiveness_threshold` (configurable, default 0.05).

**Seki exception (RC-1)**: If `position_closeness > seki_closeness_threshold` (configurable, default 0.9), bypass the instructiveness gate. Rationale: Seki positions have near-zero delta but high instructional value.

**Config-driven (RC-2)**: Both thresholds are in `TeachingSignalConfig`, not hardcoded.

### Ripple Effects

| ID | Component | Effect | Risk | Evidence |
|----|-----------|--------|------|----------|
| RE-1 | `PipelineContext` | New `teaching_signals: dict` field | None — already implemented with dataclass default | ✅ Done |
| RE-2 | `AiAnalysisResult` | Schema v9 → v10, new optional `teaching_signals: dict \| None` | Low — None default, add-only | Need to verify no downstream consumers check schema version strictly |
| RE-3 | `DifficultyStage` | Computes and stores teaching signals | None — already implemented | ✅ Done |
| RE-4 | `RefutationEntry` | Two new optional fields: `score_delta`, `wrong_move_policy` | Low — both have `0.0` defaults | Need to verify serialization compatibility |
| RE-5 | `result_builders.py` | Map two additional fields from Refutation → RefutationEntry | None — pure addition | — |
| RE-6 | Config schema | New `teaching_signal` section in config | Zero impact when absent | Feature-gated |
| RE-7 | `LlmTeachingConfig` → `TeachingSignalConfig` | Rename + simplify (remove LLM fields) | None — class was only added in this initiative, no external consumers | — |
| RE-8 | Ownership delta per-refutation | Additional computation in `generate_single_refutation()` | Low — function already exists, marginal cost | Conditional emission (>0.3) limits payload size |

### Upstream/Downstream/Lateral Impact

| impact_id | direction | component | expected_effect | risk | status |
|-----------|-----------|-----------|-----------------|------|--------|
| UP-1 | Upstream | KataGo engine | Zero change — all signals from existing response | None | ✅ verified |
| UP-2 | Upstream | `generate_refutations.py` | Stores ownership_delta; propagates score_delta, wrong_move_policy | Low | ⬜ needs test |
| DN-1 | Downstream | SGF writeback | No change — teaching_signals is on AiAnalysisResult JSON, not SGF | None | ✅ verified |
| DN-2 | Downstream | Frontend | No change — teaching_signals unused by frontend (future LLM work) | None | ✅ verified |
| DN-3 | Downstream | User's LLM stage | Consumer of teaching_signals — our output is their input | N/A | User's scope |
| LAT-1 | Lateral | Template comments | Completely decoupled — zero change to comment_assembler | None | ✅ verified |
| LAT-2 | Lateral | Hint generator | Completely decoupled | None | ✅ verified |
| LAT-3 | Lateral | Instinct stage | Completely decoupled | None | ✅ verified |

### CRITICAL Finding Resolution

**CRITICAL-1 (found 2026-03-27)**: `wrong_move_signals` always empty due to stage ordering bug. `build_teaching_signal_payload()` runs in DifficultyStage (stage 7) with `result=ctx.result`, but `ctx.result` is set by AssemblyStage (stage 8). **Resolution**: T5b — relocate payload build call to AssemblyStage.

No other CRITICAL findings. All remaining changes are additive and feature-gated. The stage ordering bug affects current Phase 1 code (wrong_move_signals always []), but since no consumer reads this yet, it's latent — fix is required before T12 (Option B payload).

## Backward Compatibility

- **Required**: Yes (Q5)
- **Strategy**: Add-only schema changes. New optional fields with None/0.0 defaults.
- **Fields added to RefutationEntry**: `score_delta: float = 0.0`, `wrong_move_policy: float = 0.0` — both default to 0.0 so existing data is unchanged.
- **Field added to AiAnalysisResult**: `teaching_signals: dict | None = None` — None default.
- **Legacy code**: Kept permanently (Q6). Template system is not touched.

## Correction Level Assessment

**Level 3: Multiple Files** — 2-3 files with logic changes + config + tests.
- `teaching_signal_payload.py` — significant logic upgrade
- `ai_analysis_result.py` — schema bump + new field
- `result_builders.py` — propagate two fields
- `config/teaching.py` — replace LlmTeachingConfig with TeachingSignalConfig
- `config/__init__.py` — wire new config
- `tests/test_teaching_signals.py` — additional tests for Option B

Impact surface is well-bounded: enrichment pipeline internals only, no frontend, no SGF format changes.
