# Validation Report — Enrichment Lab Consolidated Initiative

Last Updated: 2026-03-11

## Test Results

### Phase A Regression (T8)

```
Command: cd tools/puzzle-enrichment-lab && python -m pytest tests/test_ko_validation.py tests/test_enrich_single.py tests/test_sgf_enricher.py tests/test_solve_position.py tests/test_sprint1_fixes.py --tb=short -q --no-header
Result: 214 passed, 3 skipped
Exit code: 0 (success)
```

### Phase B Regression (T14)

```
Command: cd tools/puzzle-enrichment-lab && python -m pytest tests/test_benson_check.py tests/test_solve_position.py tests/test_ko_validation.py tests/test_enrich_single.py -x --tb=short -q --no-header
Result: 164 passed, 3 skipped
Exit code: 0 (success)
```

### Final Regression (T50)

```
Command: cd tools/puzzle-enrichment-lab && python -m pytest tests/test_solve_position.py tests/test_enrich_single.py tests/test_sgf_enricher.py tests/test_ko_validation.py tests/test_benson_check.py tests/test_difficulty.py tests/test_sprint1_fixes.py tests/test_ai_solve_config.py tests/test_ai_solve_integration.py tests/test_ai_analysis_result.py tests/test_remediation_sprints.py --cache-clear --tb=short -q --no-header
Result: 384 passed, 3 skipped, 1 pre-existing failure
Exit code: 1 (pre-existing failure only)
```

Pre-existing failure: `test_composite_weights_from_config` — asserts KataGo weight >= 75% but config has 55%. Unrelated to this initiative.

## Ripple Effects

| impact_id | expected_effect | observed_effect | result | follow_up_task | status |
|-----------|-----------------|-----------------|--------|----------------|--------|
| VAL-1 | ai_solve_active removal does not change behavior | All 6 reference sites equivalent to `ai_solve_config is not None` check | ✅ verified | None | ✅ verified |
| VAL-2 | level_mismatch JSON removal retains active overwrite at threshold=3 | `_MISMATCH_THRESHOLD = 3`; test_overwrites_existing_yg_on_large_mismatch asserts overwrite at distance=4; test_preserves_yg asserts preservation at distance=1 | ✅ verified | None | ✅ verified |
| VAL-3 | Benson gate does not fire on framework groups | test_framework_false_positive_rejection passes — framework alive, contest dead | ✅ verified | None | ✅ verified |
| VAL-4 | conftest run_id format matches cli.py format | YYYYMMDD-xxxxxxxx (lowercase hex) from generate_run_id() | ✅ verified | None | ✅ verified |
| VAL-5 | Ko capture verification backward compatible | Tests pass with and without initial_stones parameter | ✅ verified | None | ✅ verified |
| VAL-6 | puzzle_region threading does not break existing tree building | All 152 solve_position tests pass with new parameter (defaults to None) | ✅ verified | None | ✅ verified |
| VAL-7 | Phase D drop does not affect functionality | sgfmill continues to work as implicit dependency | ✅ verified | None | ✅ verified |
| VAL-8 | Doc updates don't introduce broken links | All cross-references point to existing sections | ✅ verified | None | ✅ verified |

## Files Modified (This Initiative)

### Modified Files

| file | purpose |
|------|---------|
| `config/katago-enrichment.json` | Removed `level_mismatch` section |
| `tools/puzzle-enrichment-lab/analyzers/estimate_difficulty.py` | T1: Per-component debug logging |
| `tools/puzzle-enrichment-lab/analyzers/ko_validation.py` | T2: Recurrence logging. T4: Board replay verification |
| `tools/puzzle-enrichment-lab/analyzers/enrich_single.py` | T5: Removed ai_solve_active variable |
| `tools/puzzle-enrichment-lab/analyzers/sgf_enricher.py` | T6: Removed level_mismatch config loading |
| `tools/puzzle-enrichment-lab/analyzers/solve_position.py` | T11: Integrated Benson/interior-point gates |
| `tools/puzzle-enrichment-lab/conftest.py` | T3: Fixed run_id format |
| `tools/puzzle-enrichment-lab/tests/test_sgf_enricher.py` | T6: Updated test for threshold=99 |
| `docs/concepts/quality.md` | T45: Benson gate + interior-point quality signals |
| `docs/architecture/tools/katago-enrichment.md` | T46: D69/D70/D71 design decisions |
| `docs/how-to/tools/katago-enrichment-lab.md` | T47: Pre-query terminal detection usage |
| `docs/reference/enrichment-config.md` | T48: Benson/interior-point config reference |

### New Files

| file | purpose |
|------|---------|
| `tools/puzzle-enrichment-lab/analyzers/benson_check.py` | T9+T10: Benson unconditional life + interior-point death |
| `tools/puzzle-enrichment-lab/tests/test_benson_check.py` | T12+T13: 13 unit tests for both algorithms |
| `tools/puzzle-enrichment-lab/tests/test_gate_integration.py` | RT-2/3/5: 14 integration tests for gates, adjacency, board sizing, region threading |

---

## Remediation Session 1 Regression (RT-1 through RT-9)

```
Scope: 6 fixes (RT-1,4,6,8,9) + 6 integration tests (RT-2,3,5)
Files modified: enrich_single.py, ko_validation.py, validate_correct_move.py,
                katago-enrichment.json, 4 doc files, requirements.txt
New file: test_gate_integration.py (6 tests)
Result: All tests pass; no new regressions
```

## Remediation Session 2 Regression (NF-01, NF-02, R1/NF-03, R3, R5)

```
Command: pytest tests/test_gate_integration.py (14 tests)
Result: 14 passed
Exit code: 0

Command: pytest core test files (enrich_single, solve_position, gate, ko_validation,
         ai_solve_integration, sprint1, query_builder, sgf_enricher)
Result: 268 passed, 3 skipped, 1 pre-existing error
Exit code: 1 (pre-existing only)

Command: pytest extended files (remediation_sprints, sprint2-5, benson, correct_move,
         tsumego_frame)
Result: 191 passed, 2 skipped, 2 pre-existing failures, 4 pre-existing errors
Exit code: 1 (pre-existing only)
```

Pre-existing failures (NOT related to remediation):
- `test_composite_weights_from_config` — weights sum=110, expected 100
- `StructuralDifficultyWeights` validation error — same root cause
- `TestCollectionDisagreementWarning` — fixture setup error
- `TestKoThreatNoRoom` — fixture setup error

## Remediation Ripple Effects

| impact_id | expected_effect | observed_effect | result | follow_up_task | status |
|-----------|-----------------|-----------------|--------|----------------|--------|
| VAL-9 | NF-01: `_BoardState` derives board_size from engine | 9x9/13x13 tests pass; 19x19 fallback works | ✅ verified | None | ✅ verified |
| VAL-10 | NF-02: `_are_adjacent` rejects identical coords | `test_identical_coordinates_not_adjacent` passes | ✅ verified | None | ✅ verified |
| VAL-11 | R1/NF-03: `discover_alternatives()` receives puzzle_region | `test_puzzle_region_forwarded_to_alt_tree_build` passes | ✅ verified | None | ✅ verified |
| VAL-12 | has-solution path computes puzzle_region | 5 previously-failing tests in test_enrich_single now pass (29/29+1skip) | ✅ verified | None | ✅ verified |
| VAL-13 | Gate depth thresholds respect depth_profiles config | Tests with min_depth=1 see gates fire at depth=1; no queries issued | ✅ verified | None | ✅ verified |
| VAL-14 | puzzle_region coords match GTP→(row,col) mapping | D4 on 19x19 → (15,3); Benson gate fires correctly | ✅ verified | None | ✅ verified |
| VAL-15 | Existing solve_position tests unbroken by new params | 152+ solve_position tests pass with puzzle_region=None default | ✅ verified | None | ✅ verified |
| VAL-16 | Ko validation backward compatible with adjacency fix | All ko tests pass; identical-coord edge case now rejected | ✅ verified | None | ✅ verified |

## Post-Closeout Amendment: Audit Finding Fixes + Config Decoupling

### Amendment Regression

```
Command: cd tools/puzzle-enrichment-lab && python -m pytest tests/test_gate_integration.py tests/test_ai_solve_config.py tests/test_sgf_enricher.py --tb=no -q --no-header -p no:logging
Result: 108 passed
Exit code: 0

Broader regression (9 core files):
Command: cd tools/puzzle-enrichment-lab && python -m pytest tests/test_solve_position.py tests/test_enrich_single.py tests/test_gate_integration.py tests/test_ko_validation.py tests/test_ai_solve_integration.py tests/test_sprint1_fixes.py tests/test_benson_check.py tests/test_ai_solve_config.py tests/test_sgf_enricher.py --tb=no -q --no-header -p no:logging
Result: 312 passed, 3 skipped, 1 pre-existing error (TestCollectionDisagreementWarning)
Exit code: 1 (pre-existing only)
```

### Amendment Ripple Effects

| impact_id | expected_effect | observed_effect | result | follow_up_task | status |
|-----------|-----------------|-----------------|--------|----------------|--------|
| VAL-17 | G9/AC11: Changelog annotations match actual threshold=3 | v1.6 and v1.11 annotations corrected to state threshold=3 | ✅ verified | None | ✅ verified |
| VAL-18 | EX-6 deviation note matches actual code behavior | Corrected: states _MISMATCH_THRESHOLD=3 and test_overwrites_existing_yg_on_large_mismatch | ✅ verified | None | ✅ verified |
| VAL-19 | New test_preserves_existing_yg_on_small_mismatch passes | Tests beginner→elementary (distance=1 < 3), asserts preservation | ✅ verified | None | ✅ verified |
| VAL-20 | terminal_detection_enabled=True (default) = zero behavior change | Existing 14 gate tests + 152 solve_position tests pass unchanged | ✅ verified | None | ✅ verified |
| VAL-21 | terminal_detection_enabled=False disables gates | test_gates_disabled_queries_not_short_circuited: gates-disabled uses more queries than gates-enabled | ✅ verified | None | ✅ verified |
| VAL-22 | transposition_enabled=False + terminal_detection_enabled=True = gates still fire | test_transposition_disabled_gates_still_fire: 1 query (gate fires at depth=2) | ✅ verified | None | ✅ verified |
| VAL-23 | Config field present in Pydantic model with correct default | terminal_detection_enabled=True in config assertions, backward compat test passes | ✅ verified | None | ✅ verified |
