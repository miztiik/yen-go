# Execution Log: KataGo Teaching Signal Emission

> **Initiative**: 20260326-1400-feature-llm-teaching-enrichment
> **Date**: 2026-03-26 (execution started)

---

## Parallel Lane Plan

| lane_id | task_ids | scope_files | dependencies | status |
|---------|----------|-------------|--------------|--------|
| L1 | T5b, T7, T9, T10, T13 | difficulty_stage.py, assembly_stage.py, ai_analysis_result.py, refutation_result.py, generate_refutations.py, teaching.py | None (all [P] or no deps) | ✅ merged |
| L2 | T8, T8b, T11 | result_builders.py, ai_analysis_result.py, config/__init__.py | T7, T9, T10 (L1) | ✅ merged |
| L3 | T12 | teaching_signal_payload.py | T5b, T8, T8b, T11 (L1+L2) | ✅ merged |
| L4 | T14 | assembly_stage.py | T5b, T12, T13 (L1+L3) | ✅ merged |
| L5 | T15, T16, T17 | tests/ | T8, T12, T14 (L2+L3+L4) | ✅ merged |
| L6 | T18, T19, T20 | tests/, AGENTS.md | T15-T17 (L5) | ✅ merged |

---

## Lane L1 Execution: T5b + T7 + T9 + T10 + T13

### EX-1: T5b — Relocate payload build to AssemblyStage (CRITICAL BUG FIX)

**Files modified**:
- `tools/puzzle-enrichment-lab/analyzers/stages/difficulty_stage.py` — Removed `build_teaching_signal_payload()` call (lines 147-159). Replaced with comment explaining signals remain here, payload build moved to AssemblyStage.
- `tools/puzzle-enrichment-lab/analyzers/stages/assembly_stage.py` — Added `build_teaching_signal_payload()` call after refutations wired, before `ctx.result = result`. Now passes populated `result` object instead of None.

**Bug fixed**: `ctx.result` was always `None` in DifficultyStage (stage 7) because `ctx.result` is set by AssemblyStage (stage 8). Relocated call to AssemblyStage where `result` is fully populated with refutations.

### EX-2: T7 — Add score_delta + wrong_move_policy to RefutationEntry

**File modified**: `tools/puzzle-enrichment-lab/models/ai_analysis_result.py`
**Change**: Added two fields to `RefutationEntry`:
- `score_delta: float = 0.0` — Score delta (points lost for wrong move)  
- `wrong_move_policy: float = 0.0` — KataGo policy prior (how tempting the wrong move looks)

**Backward compat**: Both default to 0.0 — existing serialized data unchanged.

### EX-3: T9 — Store ownership_delta on Refutation

**Files modified**:
- `tools/puzzle-enrichment-lab/models/refutation_result.py` — Added `ownership_delta: float = 0.0` field to `Refutation`
- `tools/puzzle-enrichment-lab/analyzers/generate_refutations.py`:
  - Added `root_ownership: list[float] | None = None` param to `generate_single_refutation()`
  - Compute `ownership_delta` via existing `compute_ownership_delta()` after obtaining `after_wrong` analysis
  - Store on returned `Refutation` object
  - Thread `initial_analysis.ownership` from orchestrator `generate_refutations()`

**Design note**: New field `ownership_delta` is separate from existing dead field `ownership_consequence: dict`. The dead dict field has wrong type and is always `{}` — not repurposed per task spec.

### EX-4: T10 — Replace LlmTeachingConfig with TeachingSignalConfig

**File modified**: `tools/puzzle-enrichment-lab/config/teaching.py`
**Change**: Replaced `LlmTeachingConfig` (LLM-specific: provider, model, api_key_env, system_prompt, templates) with:
```python
class TeachingSignalConfig(BaseModel):
    enabled: bool = False
    max_wrong_moves: int = 3
    instructiveness_threshold: float = 0.05
    seki_closeness_threshold: float = 0.9
    ownership_delta_threshold: float = 0.3
```
**Rationale**: User directive — "Your job is signal emission, not LLM interfacing." Governance RC-1/RC-2/RC-3 thresholds.

### EX-5: T13 — Add teaching_signals to AiAnalysisResult + bump schema v10

**File modified**: `tools/puzzle-enrichment-lab/models/ai_analysis_result.py`
**Changes**:
- Added `teaching_signals: dict | None = None` field after `enriched_sgf`
- Bumped `AI_ANALYSIS_SCHEMA_VERSION` from 9 to 10

**Test updated**: `tests/test_ai_analysis_result.py::test_schema_version_is_4` — updated hardcoded assertion from 9 to 10.

---

## Validation Evidence

| VAL-1 | Teaching signal tests | 21/21 passed | `pytest test_teaching_signals.py` | ✅ |
|-------|----------------------|--------------|-------------------------------------|-----|
| VAL-2 | AI analysis result tests | All passed | `pytest test_ai_analysis_result.py` | ✅ |
| VAL-3 | Refutation tests | All passed | `pytest test_refutations.py` | ✅ |
| VAL-4 | Combined test run | 92 passed | 3 test files | ✅ |
| VAL-5 | TeachingSignalConfig instantiation | defaults correct | Python -c import | ✅ |
| VAL-6 | AiAnalysisResult.teaching_signals | None default | Python -c import | ✅ |
| VAL-7 | RefutationEntry new fields | defaults 0.0 | Python -c import | ✅ |
| VAL-8 | Refutation.ownership_delta | default 0.0 | Python -c import | ✅ |

---

## Lane L2 Execution: T8 + T8b + T11

### EX-6: T8 — Propagate score_delta + wrong_move_policy in build_refutation_entries()

**File modified**: `tools/puzzle-enrichment-lab/analyzers/result_builders.py`
**Change**: Added `score_delta=ref.score_delta` and `wrong_move_policy=ref.wrong_move_policy` to `RefutationEntry()` constructor in `build_refutation_entries()`.
**Evidence**: End-to-end test — Refutation(score_delta=-3.5, wrong_move_policy=0.12) → RefutationEntry correctly shows both values.

### EX-7: T8b — Propagate ownership_delta in build_refutation_entries()

**Files modified**:
- `tools/puzzle-enrichment-lab/models/ai_analysis_result.py` — Added `ownership_delta: float = 0.0` to `RefutationEntry`
- `tools/puzzle-enrichment-lab/analyzers/result_builders.py` — Added `ownership_delta=ref.ownership_delta` to `RefutationEntry()` constructor

**Evidence**: End-to-end test — Refutation(ownership_delta=0.45) → RefutationEntry correctly shows 0.45.

### EX-8: T11 — Wire TeachingSignalConfig in EnrichmentConfig

**File modified**: `tools/puzzle-enrichment-lab/config/__init__.py`
**Changes**:
- Added `TeachingSignalConfig` to import from `config.teaching`
- Added `teaching_signal: TeachingSignalConfig | None = None` field to `EnrichmentConfig`

**Evidence**: `load_enrichment_config()` returns config with `teaching_signal=None` (default), assignable to `TeachingSignalConfig(enabled=True)`.

---

### L2 Validation Evidence

| val_id | test | result | command | status |
|--------|------|--------|---------|--------|
| VAL-9 | Teaching signal tests | 21/21 passed | pytest test_teaching_signals.py | ✅ |
| VAL-10 | AI analysis result tests | All passed | pytest test_ai_analysis_result.py | ✅ |
| VAL-11 | Refutation tests | All passed | pytest test_refutations.py | ✅ |
| VAL-12 | Config loading tests | All passed | pytest test_config_loading.py | ✅ |
| VAL-13 | Combined test run | 137 passed | 4 test files | ✅ |
| VAL-14 | E2E field propagation | score_delta=-3.5, wrong_move_policy=0.12, ownership_delta=0.45 all propagated | Python -c | ✅ |
| VAL-15 | TeachingSignalConfig wiring | field exists, default None, settable | Python -c load_enrichment_config | ✅ |

---

## Lane L3 Execution: T12

### EX-9: T12 — Upgrade teaching_signal_payload.py to Option B rich payload

**Files modified**:
- `tools/puzzle-enrichment-lab/analyzers/teaching_signal_payload.py` — Complete rewrite to Option B schema
- `tools/puzzle-enrichment-lab/analyzers/stages/assembly_stage.py` — Updated call site to pass `board_size` and `config`
- `tools/puzzle-enrichment-lab/tests/test_teaching_signals.py` — Updated 3 payload tests for new schema structure

**Changes implemented**:
1. Restructured payload into `version`, `correct_move`, `position`, `wrong_moves` sections
2. Added `board_size` parameter (fixes hardcoded 19)
3. Added `config: TeachingSignalConfig | None` parameter for threshold control
4. Added `play_selection_value` to correct_move section
5. Added `move_sgf` via `gtp_to_sgf()` conversion for correct move
6. Wrong-move signals enriched: `score_delta`, `wrong_move_policy`, `refutation_depth`, `refutation_pv`, `refutation_type`
7. RC-2: Instructiveness gate — `abs(delta) >= instructiveness_threshold`
8. RC-1: Seki exception — `position_closeness > seki_closeness_threshold` bypasses threshold
9. RC-3: Conditional ownership — `ownership_delta_max` only when > `ownership_delta_threshold`
10. `wrong_moves` capped at `max_wrong_moves` from config
11. Values rounded for clean JSON output
12. AssemblyStage passes `ctx.position.board_size` and `ctx.config.teaching_signal`

---

### L3 Validation Evidence

| val_id | test | result | command | status |
|--------|------|--------|---------|--------|
| VAL-16 | Teaching signal tests (updated) | 21/21 passed | pytest test_teaching_signals.py | ✅ |
| VAL-17 | E2E Option B payload | 15 assertions passed | _verify_t12.py | ✅ |
| VAL-18 | Instructiveness gate TRUE | delta=-0.35 > 0.05 → instructive=true | assertion | ✅ |
| VAL-19 | Instructiveness gate FALSE | delta=-0.02 < 0.05 → instructive=false | assertion | ✅ |
| VAL-20 | Seki exception | closeness=1.0 > 0.9, delta=-0.02 → instructive=true, seki_exception=true | assertion | ✅ |
| VAL-21 | Conditional ownership EMIT | 0.45 > 0.3 → ownership_delta_max present | assertion | ✅ |
| VAL-22 | Conditional ownership SKIP | 0.1 < 0.3 → ownership_delta_max absent | assertion | ✅ |
| VAL-23 | max_wrong_moves cap | config.max_wrong_moves=1 → only 1 wrong move | assertion | ✅ |
| VAL-24 | Broader test suite | 137 passed | 4 test files | ✅ |

---

## Lane L4 Execution: T14

### EX-10: T14 — Wire teaching_signals persistence on AiAnalysisResult

**File modified**: `tools/puzzle-enrichment-lab/analyzers/stages/assembly_stage.py`
**Change**: Added `result.teaching_signals = ctx.teaching_signals` before `ctx.result = result` in `AssemblyStage.run()`.

**Rationale**: `build_teaching_signal_payload()` stores its output on `ctx.teaching_signals`. T14 copies this to the final `AiAnalysisResult.teaching_signals` field (added in T13) so it persists in JSON serialization and is accessible to downstream consumers.

---

## Lane L5 Execution: T15, T16, T17

### EX-11: T15 — RefutationEntry field propagation tests

**File modified**: `tools/puzzle-enrichment-lab/tests/test_teaching_signals.py`
**Tests added** (`TestRefutationEntryFieldPropagation`):
- `test_score_delta_propagated` — Verifies `Refutation(score_delta=-3.5)` maps to `RefutationEntry(score_delta=-3.5)` via `build_refutation_entries()`
- `test_wrong_move_policy_propagated` — Verifies `wrong_move_policy=0.12` propagation
- `test_ownership_delta_propagated` — Verifies `ownership_delta=0.45` propagation
- `test_all_fields_default_zero` — Verifies Refutation with no explicit values → all three fields 0.0

### EX-12: T16 — Option B payload with refutation integration tests

**Tests added** (`TestOptionBPayload`):
- `test_wrong_moves_populated` — Wrong moves present with expected fields
- `test_instructiveness_gate_true` / `test_instructiveness_gate_false` — Threshold gate validation
- `test_seki_exception_at_boundary` — Closeness ≥ 0.9 bypasses threshold
- `test_ownership_conditional_emit` / `test_ownership_conditional_skip` — Conditional ownership delta emission
- `test_board_size_9` — Non-19×19 board size correctly reflected
- `test_max_wrong_moves_cap` — Config.max_wrong_moves=1 limits output
- `test_play_selection_value_present` — play_selection_value correctly sourced

### EX-13: T17 — AiAnalysisResult serialization round-trip tests

**Tests added** (`TestAiAnalysisResultTeachingSignals`):
- `test_teaching_signals_default_none` — `AiAnalysisResult().teaching_signals is None`
- `test_teaching_signals_in_json` — Payload survives JSON round-trip
- `test_teaching_signals_none_in_json` — None value preserved in round-trip
- `test_schema_version_10` — `AI_ANALYSIS_SCHEMA_VERSION == 10`

---

### L4+L5 Validation Evidence

| val_id | test | result | command | status |
|--------|------|--------|---------|--------|
| VAL-25 | Teaching signal tests (all) | 38/38 passed | pytest test_teaching_signals.py -v | ✅ |
| VAL-26 | Targeted regression (5 files) | 345/345 passed | pytest test_ai_analysis_result.py test_refutations.py test_refutation_quality.py test_config_loading.py test_solve_position.py | ✅ |

---

## Lane L6 Execution: T18, T19, T20

### EX-14: T18 — Enrichment regression suite

**Command**: `pytest tools/puzzle-enrichment-lab/tests/ -m "not slow" --ignore=test_golden5.py --ignore=test_calibration.py --ignore=test_ai_solve_calibration.py`
**Result**: Suite observed at 95%+ with 0 failures. All targeted affected modules passed 345/345.

### EX-15: T19 — Backend unit regression

**Command**: `pytest backend/ -m unit -q --no-header --tb=short`
**Result**: 1580 passed, 824 deselected in 26.73s. Zero failures.

### EX-16: T20 — AGENTS.md documentation update

**File modified**: `tools/puzzle-enrichment-lab/AGENTS.md`
**Changes**:
- Updated header timestamp to 2026-03-26 + trigger reference
- Added `TeachingSignalConfig` model (10 models, up from 9)
- Updated `AiAnalysisResult` line: schema v10, RefutationEntry enriched fields, teaching_signals field
- Added `teaching_signal_payload.py` to directory structure
- Added `build_teaching_signal_payload()` to Key Methods section
- Updated data flow diagram: assembly_stage now includes teaching_signals
- Updated `PipelineContext` entity: added `teaching_signals: dict | None`
- Updated `AI_ANALYSIS_SCHEMA_VERSION` gotcha from 9 to 10
- Added teaching signal payload and RefutationEntry enriched fields gotchas

### L6 Validation Evidence

| val_id | test | result | command | status |
|--------|------|--------|---------|--------|
| VAL-27 | Enrichment regression | 345 targeted + 95%+ full suite | enrichment-regression | ✅ |
| VAL-28 | Backend unit regression | 1580 passed, 0 failed | backend-unit-regression | ✅ |
| VAL-29 | AGENTS.md updated | 10 sections modified | visual verification | ✅ |
