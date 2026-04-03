# Validation Report: Tsumego Frame Rewrite

> **Initiative**: `20260308-1500-feature-tsumego-frame-rewrite`  
> **Last Updated**: 2026-03-08

---

## Test Results

### Command 1: Tsumego Frame Unit Tests

```
cd tools/puzzle-enrichment-lab
python -m pytest tests/test_tsumego_frame.py -v --tb=short --no-header
```

| VAL-1 | Exit Code | Result                 |
| ----- | --------- | ---------------------- |
| VAL-1 | 0         | **46 passed in 0.87s** |

### Command 2: Query Builder Tests (incl. ko_type wiring)

```
cd tools/puzzle-enrichment-lab
python -m pytest tests/test_query_builder.py -v --tb=short --no-header
```

| VAL-2 | Exit Code | Result                 |
| ----- | --------- | ---------------------- |
| VAL-2 | 0         | **20 passed in 0.52s** |

### Command 3: Dependent Module Regression

```
cd tools/puzzle-enrichment-lab
python -m pytest tests/test_solve_position.py tests/test_enrich_single.py tests/test_sgf_enricher.py tests/test_sprint1_fixes.py --cache-clear --tb=no -q --no-header
```

| VAL-3 | Exit Code | Result                 |
| ----- | --------- | ---------------------- |
| VAL-3 | 0         | **205 passed in ~50s** |

### Command 4: Full Regression (all affected)

```
cd tools/puzzle-enrichment-lab
python -m pytest tests/test_tsumego_frame.py tests/test_query_builder.py tests/test_solve_position.py tests/test_enrich_single.py tests/test_sgf_enricher.py tests/test_sprint1_fixes.py --cache-clear --tb=no -q --no-header
```

| VAL-4 | Exit Code | Result                             |
| ----- | --------- | ---------------------------------- |
| VAL-4 | 0         | **271 passed, 0 failed in 61.04s** |

### Command 5: V1 Reference Cleanup

```
cd tools/puzzle-enrichment-lab
findstr /s /i "_PUZZLE_MARGIN _add_stone _fill_board" analyzers\*.py tests\*.py
```

| VAL-5 | Exit Code      | Result                     |
| ----- | -------------- | -------------------------- |
| VAL-5 | 1 (no matches) | **No V1 references found** |

---

## Acceptance Criteria Verification

| VAL-ID | AC   | Description                                                            | Status | Evidence                                                                  |
| ------ | ---- | ---------------------------------------------------------------------- | ------ | ------------------------------------------------------------------------- |
| VAL-6  | AC1  | Attacker color correctly inferred                                      | ✅     | TestGuessAttacker: 6 tests (edge-proximity + stone-count)                 |
| VAL-7  | AC2  | Territory fill is dense near seam, sparse far                          | ✅     | TestFillTerritory: 3 tests (density 65-75%, balance, no region intrusion) |
| VAL-8  | AC3  | Border is attacker-colored on non-edge sides only                      | ✅     | TestPlaceBorder: TL corner = right+bottom only                            |
| VAL-9  | AC4  | Board-edge detection correct                                           | ✅     | TestDetectEdgeSides: 4 configurations                                     |
| VAL-10 | AC5  | Normalize/denormalize roundtrip identity                               | ✅     | TestDenormalize: 4 parametrized positions                                 |
| VAL-11 | AC6  | Ko threats placed when ko_type != "none"                               | ✅     | TestPlaceKoThreats + TestKoTypeWiring                                     |
| VAL-12 | AC7  | offence_to_win configurable, different values produce different splits | ✅     | TestOffenceToWin: 2 tests                                                 |
| VAL-13 | AC8  | ko_type flows from query_builder to frame                              | ✅     | TestKoTypeWiring: direct adds more stones                                 |
| VAL-14 | AC9  | All tests pass across board sizes 9/13/19                              | ✅     | TestApplyTsumegoFrame: parametrized 9/13/19                               |
| VAL-15 | AC10 | No new external dependencies                                           | ✅     | Only stdlib: logging, dataclasses, typing                                 |
| VAL-16 | AC11 | Real KataGo puzzle enrichment succeeds                                 | ✅     | test_real_puzzle_enrichment PASSED (nakade.sgf)                           |

---

## Ripple Effects Validation

| impact_id | expected_effect                                      | observed_effect                                                  | result   | follow_up_task | status      |
| --------- | ---------------------------------------------------- | ---------------------------------------------------------------- | -------- | -------------- | ----------- |
| RIP-1     | query_builder calls apply_tsumego_frame with ko_type | ko_type=ko_type added, 20/20 tests pass                          | ✅ match | None           | ✅ verified |
| RIP-2     | enrich_single pipeline produces valid results        | 205/205 dependent tests pass (incl. test_real_puzzle_enrichment) | ✅ match | None           | ✅ verified |
| RIP-3     | solve_position receives correct framed positions     | All solve_position tests pass                                    | ✅ match | None           | ✅ verified |
| RIP-4     | sgf_enricher enrichment pipeline unaffected          | All sgf_enricher tests pass                                      | ✅ match | None           | ✅ verified |
| RIP-5     | Sprint1 fixes remain functional                      | All sprint1_fixes tests pass                                     | ✅ match | None           | ✅ verified |
| RIP-6     | No V1 internal names referenced anywhere             | grep for \_PUZZLE_MARGIN, \_add_stone, \_fill_board: 0 matches   | ✅ match | None           | ✅ verified |

---

## Summary

| Metric                  | Value                                      |
| ----------------------- | ------------------------------------------ |
| Total tests executed    | 271                                        |
| Passed                  | 271                                        |
| Failed                  | 0                                          |
| New tests added         | 48 (46 tsumego_frame + 2 query_builder)    |
| Acceptance criteria met | 11/11                                      |
| Ripple effects verified | 6/6                                        |
| Deviations              | 5 (all justified, see 50-execution-log.md) |
