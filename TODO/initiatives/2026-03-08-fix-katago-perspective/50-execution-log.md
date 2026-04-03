# Execution Log — KataGo Winrate Perspective Fix

Last Updated: 2026-03-08

## Phase 1: Perspective Fix + Tests

| Task | Status      | Evidence                                                                                | Deviations                                                                                |
| ---- | ----------- | --------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| T1   | ✅ Complete | `tsumego_analysis.cfg` L44, `analysis_example.cfg` L30 → SIDETOMOVE                     | None                                                                                      |
| T2   | ✅ Complete | `generate_refutations.py` L214: 5-line comment explaining SIDETOMOVE correctness        | Action changed from "fix" to "document" per governance (L214 is correct under SIDETOMOVE) |
| T3   | ✅ Complete | `test_solve_position.py` MockConfirmationEngine: comment updated to document SIDETOMOVE | Mock logic unchanged — was already correct for SIDETOMOVE                                 |
| T4   | ✅ Complete | 7 new tests: `TestWhiteToPlayClassification` (4) + `TestBlackWhiteParametrized` (3)     | Initial test had wrong root_winrate setup (single-move analysis), fixed                   |
| T5   | ✅ Complete | 234 passed, 0 failed                                                                    | —                                                                                         |
| T6   | ⏸️ Manual   | Requires live KataGo — does not gate Phase 2                                            | Deferred to post-implementation                                                           |

## Phase 2: Comprehensive Logging

| Task | Status      | Evidence                                                                             | Deviations                                                                            |
| ---- | ----------- | ------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------- |
| T7   | ✅ Complete | `solve_position.py`: per-move classification + root winrate context                  | —                                                                                     |
| T8   | ✅ Complete | `validate_correct_move.py`: dispatch + classify + status + threshold logging         | Initially had duplicate `_status_from_classification` call — fixed in governance RC-6 |
| T9   | ✅ Complete | `estimate_difficulty.py`: 4-component score breakdown logging                        | —                                                                                     |
| T10  | ✅ Complete | `technique_classifier.py`: ko/ladder/snapback detector results + tag list            | —                                                                                     |
| T11  | ✅ Complete | `ko_validation.py`: detection result + type inference logging                        | —                                                                                     |
| T12  | ✅ Complete | `generate_refutations.py`: per-candidate baseline + ko-aware threshold               | —                                                                                     |
| T13  | ✅ Complete | `enrich_single.py`: goal inference logging. `query_builder.py`: allowed_moves coords | —                                                                                     |
| T14  | ✅ Complete | `cli.py`: run_id generation for enrich. `conftest.py`: format aligned                | —                                                                                     |
| T15  | ✅ Complete | 234 passed, 0 failed                                                                 | —                                                                                     |

## Phase 3: Quality + Cleanup

| Task | Status      | Evidence                                                                                                  | Deviations                                                                                                               |
| ---- | ----------- | --------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| T16  | ✅ Complete | `ko_validation.py`: `_are_adjacent()` with Manhattan distance, `_has_recapture_pattern()` adjacency check | Initially used Chebyshev distance — fixed to Manhattan per governance RC-5                                               |
| T17  | ✅ Complete | JSON weights: 15/15/25/45. Pydantic defaults synced.                                                      | —                                                                                                                        |
| T18  | ✅ Complete | TeachingConfig (0.10, 0.12), QualityGatesConfig (0.95), SekiDetectionConfig +score_threshold              | —                                                                                                                        |
| T19  | ✅ Complete | `difficulty_result.py` deleted. `level_mismatch` JSON KEPT.                                               | Deviation: plan said remove `level_mismatch` but `sgf_enricher.py` reads it via raw JSON. Kept to avoid behavior change. |
| T20  | ✅ Complete | `enabled` removed from AiSolveConfig + JSON + enrich_single.py gating                                     | Ghost `enabled=True` at L315 also removed per governance RC-4                                                            |
| T21  | ✅ Complete | 354 passed, 0 failed (after governance fixes: 307 verified)                                               | Pre-existing test bug fixed: `StructuralDifficultyWeights` sum test missing `proof_depth`                                |

## Governance Fixes Applied

| RC   | Fix                                                          | Evidence                 |
| ---- | ------------------------------------------------------------ | ------------------------ |
| RC-4 | Removed `AiSolveConfig(enabled=True)` → `AiSolveConfig()`    | enrich_single.py L315    |
| RC-5 | Changed `_are_adjacent` from Chebyshev to Manhattan distance | ko_validation.py         |
| RC-6 | Removed duplicate `_status_from_classification` call         | validate_correct_move.py |
| RC-7 | Updated stale JSON descriptions to match 15/15/25/45 weights | katago-enrichment.json   |
