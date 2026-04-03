# Charter — KataGo Winrate Perspective Fix + Enrichment Reconciliation

Last Updated: 2026-03-08

## Initiative ID

`2026-03-08-fix-katago-perspective`

## Problem Statement

The puzzle-enrichment-lab's KataGo config uses `reportAnalysisWinratesAs = BLACK` while the entire codebase assumes `SIDETOMOVE`. This causes:

1. **Confirmation queries invert winrates** → correct moves classified as wrong → zero solution trees for position-only puzzles
2. **All White-to-play puzzles produce wrong results** → 20+ code sites read raw BLACK-perspective winrates as puzzle-player-perspective
3. **generate_refutations.py L214** has a `1.0 - opp_best.winrate` flip that is wrong even for Black puzzles under BLACK mode
4. **Decision logging is nearly absent** → 4 of 8 analyzer modules have ZERO logger calls; per-move, per-threshold, per-component decisions are invisible
5. **Log file naming broken** → `enrich` CLI has no run_id; test logs get `test-` prefix but format is inconsistent with production
6. **Dead code accumulation** → unused models, abandoned initiative directories, confusing config toggles

## Goals

| G-id | Goal                                                                                                                                                                                             |
| ---- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| G1   | Fix KataGo config to `reportAnalysisWinratesAs = SIDETOMOVE` — the single root cause of the perspective bug                                                                                      |
| G2   | Document `generate_refutations.py` L214 `1.0 - opp_best.winrate` — correct under SIDETOMOVE (opponent perspective flip). Add explanatory comment.                                                |
| G3   | Add White-to-play test coverage — parametrized tests for classification, validation, refutation, difficulty                                                                                      |
| G4   | Add comprehensive decision logging to all 8 analyzer modules — every move classification, validation threshold, difficulty component, technique detection, ko decision, refutation accept/reject |
| G5   | Fix log file naming: per-run files for `enrich` CLI, aligned `conftest.py` format                                                                                                                |
| G6   | Remove dead code: `difficulty_result.py` shim, `EnrichmentRunState` if dead, abandoned initiative dirs                                                                                           |
| G7   | Remove `ai_solve.enabled` flag — always-on simplification                                                                                                                                        |
| G8   | Fix co-broken test mocks that simulate wrong perspective (MockConfirmationEngine)                                                                                                                |
| G9   | Verify enrichment output by re-running the failing puzzle from session evidence                                                                                                                  |
| G10  | Fix ko detection false positives — coordinate recurrence without capture verification (S5/P1.5)                                                                                                  |
| G11  | Fix difficulty estimation collinearity — policy + visits coupled, structural under-weighted (S6/P1.6)                                                                                            |

## Non-Goals

| NG-id | Non-Goal                                           | Rationale                                        |
| ----- | -------------------------------------------------- | ------------------------------------------------ |
| NG1   | ~~Fix ko detection false positives~~               | **Moved to Goals (G10)**                         |
| NG2   | ~~Fix difficulty collinearity~~                    | **Moved to Goals (G11)**                         |
| NG3   | Add KataGo timeout/cancellation (S8)               | Infrastructure concern — separate initiative     |
| NG4   | Parallelize batch processing (M6)                  | Performance optimization — separate scope        |
| NG5   | Execute no-solution-resilience Phase II (T14-T19)  | Deferred branching improvements — separate scope |
| NG6   | Run threshold calibration sweep (S5-G18)           | Requires live KataGo with fixture sets           |
| NG7   | Write deferred documentation deliverables (S5-G19) | Separate initiative                              |
| NG8   | Complete phase-b-merge initiative                  | In-progress separately                           |

## Constraints

| C-id | Constraint                                                              |
| ---- | ----------------------------------------------------------------------- |
| C1   | KISS, DRY, SOLID principles are non-negotiable                          |
| C2   | Any governance concern = full stop and revisit                          |
| C3   | Dead code must be deleted, not deprecated                               |
| C4   | No refactoring — remove unnecessary code, fix bugs, add logging         |
| C5   | Governance panel expanded to 7 members (added purist Systems Architect) |
| C6   | All previously enriched puzzles will need re-processing after this fix  |

## Acceptance Criteria

| AC-id | Criterion                                                                                             |
| ----- | ----------------------------------------------------------------------------------------------------- |
| AC1   | KataGo config reads `reportAnalysisWinratesAs = SIDETOMOVE`                                           |
| AC2   | `generate_refutations.py` L214 has explanatory comment documenting SIDETOMOVE perspective correctness |
| AC3   | At least 1 White-to-play fixture with parametrized tests for classification, validation, difficulty   |
| AC4   | ALL 8 analyzer modules have decision-level logging (zero silent modules)                              |
| AC5   | `enrich` CLI generates and sets run_id before logging starts                                          |
| AC6   | `conftest.py` run_id format aligned with `generate_run_id()`                                          |
| AC7   | Dead code removed: `difficulty_result.py` shim, any unused models                                     |
| AC8   | `ai_solve.enabled` flag removed — always-on                                                           |
| AC9   | `MockConfirmationEngine` returns SIDETOMOVE-perspective winrates                                      |
| AC10  | Re-running the session evidence puzzle produces `correct > 0`                                         |
| AC11  | All existing tests pass (regression)                                                                  |
| AC12  | ruff clean on all modified files                                                                      |
| AC13  | Ko detection uses capture verification, not just coordinate recurrence                                |
| AC14  | Difficulty estimation weights rebalanced to reduce policy+visits collinearity                         |

> **See also**:
>
> - [Clarifications](./10-clarifications.md) — All Q&A with user decisions
> - [Research](./15-research.md) — KataGo perspective behavior, approach comparison
