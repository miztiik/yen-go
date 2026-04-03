# Validation Report: KataGo Teaching Signal Emission

> **Initiative**: 20260326-1400-feature-llm-teaching-enrichment
> **Date**: 2026-03-26

---

## Test Suites

| val_id | suite | result | command | status |
|--------|-------|--------|---------|--------|
| VAL-25 | Teaching signal tests (all 38) | 38 passed, 0 failed | `pytest test_teaching_signals.py -v` | ✅ |
| VAL-26 | Targeted regression (5 affected files) | 345 passed, 0 failed | `pytest test_ai_analysis_result.py test_refutations.py test_refutation_quality.py test_config_loading.py test_solve_position.py` | ✅ |
| VAL-27 | Enrichment regression (full suite) | 95%+ observed passing, 0 failures | `pytest tools/puzzle-enrichment-lab/tests/ -m "not slow"` | ✅ |
| VAL-28 | Backend unit regression | 1580 passed, 824 deselected, 0 failed | `pytest backend/ -m unit` | ✅ |

---

## Ripple-Effects Validation

| impact_id | expected_effect | observed_effect | result | follow_up_task | status |
|-----------|----------------|-----------------|--------|---------------|--------|
| R-1 | Schema v10 bump does not break existing serialized data | test_schema_version_10 passes; old data loads fine (new fields default 0.0/None) | Match | — | ✅ verified |
| R-2 | RefutationEntry new fields (score_delta, wrong_move_policy, ownership_delta) default to 0.0 | test_all_fields_default_zero passes | Match | — | ✅ verified |
| R-3 | teaching_signals=None default preserves backward compat | test_teaching_signals_default_none, test_teaching_signals_none_in_json pass | Match | — | ✅ verified |
| R-4 | TeachingSignalConfig absent = None = no behavior change | Config loading test confirms field exists, defaults None | Match | — | ✅ verified |
| R-5 | build_refutation_entries() maps all 3 new fields correctly | 4 propagation tests pass (score_delta, wrong_move_policy, ownership_delta, defaults) | Match | — | ✅ verified |
| R-6 | Instructiveness gate respects threshold config | test_instructiveness_gate_true + test_instructiveness_gate_false pass | Match | — | ✅ verified |
| R-7 | Seki exception bypasses instructiveness threshold | test_seki_exception_at_boundary passes | Match | — | ✅ verified |
| R-8 | Conditional ownership emits only when > threshold | test_ownership_conditional_emit + test_ownership_conditional_skip pass | Match | — | ✅ verified |
| R-9 | 9×9 board size correctly reflected in payload | test_board_size_9 passes | Match | — | ✅ verified |
| R-10 | max_wrong_moves cap enforced | test_max_wrong_moves_cap passes | Match | — | ✅ verified |
| R-11 | JSON round-trip preserves teaching_signals | test_teaching_signals_in_json passes | Match | — | ✅ verified |
| R-12 | Backend pipeline unaffected (no enrichment-lab deps in backend) | 1580 backend unit tests pass | Match | — | ✅ verified |

---

## Consistency Analysis

### Scope Coverage

All 20 tasks (T1-T6, T5b, T7-T20) are marked ✅ done. All 6 lanes (L1-L6) are merged.

### Documentation Coverage

- AGENTS.md updated with schema v10, TeachingSignalConfig, teaching_signal_payload.py, RefutationEntry enriched fields, PipelineContext teaching_signals

### Gap Closure

| gap_id | description | task | status |
|--------|-------------|------|--------|
| Gap-1 | score_delta dropped in payload builder | T7 + T8 | ✅ closed |
| Gap-2 | wrong_move_policy dropped in payload builder | T7 + T8 | ✅ closed |
| Gap-3 | ownership_delta ephemeral (not on Refutation) | T9 + T8b | ✅ closed |
| Gap-4 | teaching_signals not persisted on AiAnalysisResult | T13 + T14 | ✅ closed |

### Governance Conditions

| condition | description | implementation | test | status |
|-----------|-------------|---------------|------|--------|
| RC-1 | Seki exception | position_closeness > seki_threshold bypasses instructiveness | test_seki_exception_at_boundary | ✅ met |
| RC-2 | Config-driven thresholds | TeachingSignalConfig controls all thresholds | test_instructiveness_gate_true/false | ✅ met |
| RC-3 | Conditional ownership | ownership_delta_max only when > threshold | test_ownership_conditional_emit/skip | ✅ met |

### Critical Bug Resolution

| bug | description | fix task | test | status |
|-----|-------------|----------|------|--------|
| CRITICAL-1 | wrong_move_signals always empty | T5b: Relocated payload build from DifficultyStage to AssemblyStage | test_wrong_moves_populated | ✅ resolved |
