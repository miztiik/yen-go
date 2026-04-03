# Plan — KataGo Winrate Perspective Fix + Enrichment Reconciliation

Last Updated: 2026-03-08

## Selected Option

**OPT-1: Config-First Fix** (GOV-OPTIONS-APPROVED, 7/7 unanimous)

## Architecture

### Core Insight

The code was written for `reportAnalysisWinratesAs = SIDETOMOVE`. The config was set to `BLACK` by mistake. Fix the config, not the code (KISS gold standard).

### Fix Strategy

| Domain                            | Strategy                                                                                                                                                                                              |
| --------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Perspective (G1)**              | Change 1 config line in both `.cfg` files                                                                                                                                                             |
| **L214 documentation (G2)**       | Document `1.0 - opp_best.winrate` at L214 as correct under SIDETOMOVE — add explanatory comment                                                                                                       |
| **Tests (G3, G8)**                | Add White-to-play parametrized tests; fix MockConfirmationEngine                                                                                                                                      |
| **Logging (G4)**                  | Add comprehensive logging to all 8 modules with zero logged today                                                                                                                                     |
| **Log naming (G5)**               | Add run_id to `enrich` CLI; align conftest format                                                                                                                                                     |
| **Dead code (G6)**                | Delete `difficulty_result.py` shim; delete orphan `level_mismatch` JSON                                                                                                                               |
| **ai_solve flag (G7)**            | Remove `enabled` guard; always-on                                                                                                                                                                     |
| **Validation (G9)**               | Re-run session evidence puzzle                                                                                                                                                                        |
| **Ko detection (G10)**            | Add capture verification to `detect_ko_in_pv()`                                                                                                                                                       |
| **Difficulty collinearity (G11)** | Rebalance weights: policy+visits combined < 40%, structural > 35%; determine exact split from fixture comparison or use 15/15/25/45 as provisional. Fix stale Pydantic defaults (T18 depends on T17). |
| **Config cleanup**                | Add `seki.score_threshold` to Pydantic model + JSON; sync 3 stale defaults                                                                                                                            |

### Must-Hold Constraints (from Governance)

1. Both `tsumego_analysis.cfg` AND `analysis_example.cfg` → SIDETOMOVE
2. `generate_refutations.py` L214 fix is independent
3. `normalize_winrate()` is KEPT (used at L242)
4. Three independent phases — G10/G11 cannot block G1-G9
5. White-to-play parametrized tests mandatory

## Execution Phases

### Phase 1: Perspective Fix + Tests (G1, G2, G3, G8, G9)

**Goal**: Fix the root cause and prove it works.

| File                                     | Change                                                                                                                                                |
| ---------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| `katago/tsumego_analysis.cfg`            | `reportAnalysisWinratesAs = SIDETOMOVE`                                                                                                               |
| `katago/analysis_example.cfg`            | `reportAnalysisWinratesAs = SIDETOMOVE`                                                                                                               |
| `analyzers/generate_refutations.py` L214 | Add explanatory comment: `1.0 - opp_best.winrate` is correct under SIDETOMOVE because KataGo reports from opponent's perspective after opponent moves |
| `tests/test_solve_position.py`           | Fix MockConfirmationEngine (remove manual `1.0 -` flip); add White-to-play parametrized classification test                                           |
| `tests/test_ko_validation.py` or similar | Add White-to-play fixture for refutation delta, difficulty                                                                                            |
| Manual validation                        | Re-run `(;SZ[19]FF[4]GM[1]PL[B]...` puzzle → correct > 0 (requires live KataGo — manual, does not gate Phase 2)                                       |

**Independence**: This phase is self-contained. If it passes, perspective is fixed.

### Phase 2: Comprehensive Logging (G4, G5)

**Goal**: Full observability into every enrichment decision.

| Module                               | Logging to add                                                                                                                                                                                                             |
| ------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `analyzers/solve_position.py`        | Per-move classification decisions (move, delta, threshold, quality). Root winrate with perspective context. Tree stopping condition at each branch termination. Co-correct three-signal check detail for each alternative. |
| `analyzers/validate_correct_move.py` | Validation decision (ACCEPTED/FLAGGED/REJECTED) with reason. Classifier results (is_top, in_top_n, winrate, policy, rank). Threshold comparisons. Ownership rescue trigger. Dispatcher selection.                          |
| `analyzers/estimate_difficulty.py`   | All 4 component scores with inputs. Structural sub-weights breakdown. Final raw_score, level, confidence with reasoning.                                                                                                   |
| `analyzers/technique_classifier.py`  | Each detector invocation result. Fallback trigger. Final tag list.                                                                                                                                                         |
| `analyzers/ko_validation.py`         | Ko detection result with PV analysis. Ko type inference. Validation status with thresholds.                                                                                                                                |
| `analyzers/generate_refutations.py`  | Per-candidate accept/reject with delta, threshold, policy. Initial winrate baseline. Ko-aware threshold overrides.                                                                                                         |
| `analyzers/enrich_single.py`         | Goal inference reasoning (score_delta, ownership). Winrate perspective context.                                                                                                                                            |
| `analyzers/query_builder.py`         | Allowed_moves coordinate list.                                                                                                                                                                                             |
| `cli.py`                             | Generate run_id for `enrich` subcommand                                                                                                                                                                                    |
| `conftest.py`                        | Align test run_id format to `test-YYYYMMDD-HHMMSS-8HEXUPPER`                                                                                                                                                               |

**Independence**: Logging changes are purely additive. They don't change behavior.

### Phase 3: Quality Fixes + Cleanup (G6, G7, G10, G11, Config)

**Goal**: Fix remaining bugs, remove dead code, sync config.

| Item                                | Change                                                                                                                                                                                                                                                 |
| ----------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Ko detection (G10)**              | Add capture verification in `detect_ko_in_pv()`: a coordinate recurrence is ko only if the recaptured intersection changes ownership (stone removed then placed). Check that the PV shows a capture-recapture pattern, not just coordinate repetition. |
| **Difficulty collinearity (G11)**   | Reduce policy+visits combined to < 40%; increase structural to > 35%. Determine exact values from fixture comparison or use 15/15/25/45 as provisional.                                                                                                |
| **Stale Pydantic defaults**         | Sync `DifficultyWeights` (30/30/20/20 → new T17 values), `TeachingConfig` (0.10, 0.12), `QualityGatesConfig` (0.95). Depends on T17.                                                                                                                   |
| **Seki score_threshold**            | Add `score_threshold: float = 5.0` to `SekiDetectionConfig` + JSON                                                                                                                                                                                     |
| **Dead code: difficulty_result.py** | Delete backward-compat shim; update any imports                                                                                                                                                                                                        |
| **Dead code: level_mismatch JSON**  | Remove orphan section from `katago-enrichment.json`                                                                                                                                                                                                    |
| **ai_solve.enabled removal (G7)**   | Remove `enabled` field from `AiSolveConfig`; remove `ai_solve_active` gating in `enrich_single.py`                                                                                                                                                     |

**Independence**: Can proceed in parallel with Phase 2. G10/G11 don't affect G1-G9.

## Risks and Mitigations

| Risk                                                   | Severity | Mitigation                                                                                                                         |
| ------------------------------------------------------ | -------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| SIDETOMOVE changes KataGo calibration baseline         | Medium   | All current calibration data is from Black puzzles (SIDETOMOVE = no change for Black). White puzzles are new territory either way. |
| MockConfirmationEngine fix breaks existing tests       | Low      | The mock is co-broken with the code — fixing both simultaneously maintains alignment                                               |
| Difficulty weight rebalancing shifts level assignments | Medium   | Run baseline enrichment on golden fixtures before and after; compare distributions                                                 |
| Ko capture verification too strict (rejects valid ko)  | Medium   | Test against known ko fixtures; allow configurable strictness                                                                      |
| Comprehensive logging adds performance overhead        | Low      | Python logging is lazy-evaluated with `%s` formatting; no overhead when level is filtered                                          |

## Data Model Impact

None. No model schema changes. Config additions are additive (`seki.score_threshold`).

## Rollback

- Phase 1: Revert 2 config lines in `.cfg` files + revert L214 fix
- Phase 2: Revert logging additions (pure additions, no behavior change)
- Phase 3: Revert dead code deletions (git history preserves)

> **See also**:
>
> - [Charter](./00-charter.md) — Goals G1-G11, AC1-AC14
> - [Governance](./70-governance-decisions.md) — OPT-1 selection rationale
> - [Research](./15-research.md) — KataGo perspective documentation
