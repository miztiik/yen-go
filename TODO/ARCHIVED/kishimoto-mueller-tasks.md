# Kishimoto-Mueller Search Optimizations — Tasks

**Feature:** Paper-inspired search optimizations for puzzle-enrichment-lab tree builder
**Plan:** `TODO/kishimoto-mueller-search-optimizations.md`
**Source Papers:**

- Kishimoto & Müller (2005), _Search vs Knowledge for Solving Life and Death Problems in Go_, AAAI-05
- Thomsen (2000), _Lambda-Search in Game Trees — with Application to Go_, ICGA Journal

---

## Phase 1: Setup

**Goal:** No code changes yet — verify existing test suite baseline and understand current budget consumption.

- [x] T001 Run existing test suite from `tools/puzzle-enrichment-lab/tests/` and record baseline pass count
- [x] T002 Record current `QueryBudget.used` values for cho-elementary calibration fixtures (manual or via test log) as the pre-optimization baseline

---

## Phase 2: Foundational — Config Extension (must complete before all user stories)

**Goal:** Add all KM-01 through KM-04 config parameters to existing Pydantic models so subsequent phases have their knobs available. Bump schema version.

- [x] T003 Add `simulation_enabled: bool = True` field to `SolutionTreeConfig` in `tools/puzzle-enrichment-lab/config.py`
- [x] T004 Add `simulation_verify_visits: int = 50` field to `SolutionTreeConfig` in `tools/puzzle-enrichment-lab/config.py`
- [x] T005 Add `forced_move_visits: int = 125` field to `SolutionTreeConfig` in `tools/puzzle-enrichment-lab/config.py`
- [x] T006 Add `forced_move_policy_threshold: float = 0.85` field to `SolutionTreeConfig` in `tools/puzzle-enrichment-lab/config.py`
- [x] T007 Add `transposition_enabled: bool = True` field to `SolutionTreeConfig` in `tools/puzzle-enrichment-lab/config.py`
- [x] T008 Add `simulation_hits`, `simulation_misses`, `transposition_hits`, `forced_move_count`, `max_resolved_depth` counter fields (default 0) to `TreeCompletenessMetrics` in `tools/puzzle-enrichment-lab/models/solve_result.py`
- [x] T009 Add `proof_depth: float = 10.0` to `StructuralDifficultyWeights` in `tools/puzzle-enrichment-lab/config.py`, rebalance existing weights (`solution_depth: 35`, `branch_count: 22`, `local_candidates: 18`, `refutation_count: 15`) so sum = 100, AND update `check_weights_sum()` validator to include `proof_depth` in the sum (currently sums only 4 fields — will fail validation without this update) (Review Panel Topic 7)
- [x] T010 Add `max_resolved_depth_ceiling: int = 20` to `DifficultyNormalizationConfig` in `tools/puzzle-enrichment-lab/config.py`
- [x] T011 [P] Add new fields under `ai_solve.solution_tree` in `config/katago-enrichment.json` matching the Pydantic defaults
- [x] T012 Update schema version from `1.14` to `1.15` in `config/katago-enrichment.json`
- [x] T013 Write test `test_km_config_parses_with_new_fields` verifying all new fields parse in `tools/puzzle-enrichment-lab/tests/test_ai_solve_config.py`
- [x] T014 Write test `test_km_config_missing_fields_use_defaults` verifying that `katago-enrichment.json` without the new KM fields (`simulation_enabled`, `transposition_enabled`, etc.) still loads correctly using Pydantic default values in `tools/puzzle-enrichment-lab/tests/test_ai_solve_config.py`
- [x] T015 Write test `test_structural_weights_sum_with_proof_depth` verifying rebalanced 5-weight sum = 100 in `tools/puzzle-enrichment-lab/tests/test_ai_solve_config.py`
- [x] T016 Write test `test_completeness_metrics_new_counters_default_zero` verifying new counters initialize to 0 in `tools/puzzle-enrichment-lab/tests/test_solve_result_models.py`
- [x] T017 Run full test suite to confirm zero regressions from config changes
- [x] T017a **GATE REVIEW — Phase 2:** ✅ Approved 2026-03-24. Review Panel verifies gate criteria from plan Phase 1 (Config Extension). All config tests pass, existing tests unaffected, defaults match pre-change behavior. Sign off before proceeding to Phases 3-6.

---

## Phase 3: User Story — Transposition Table [KM-02]

**Story goal:** When the tree builder encounters the same board position via different move orders, reuse the cached analysis instead of re-querying KataGo. Reduces `QueryBudget` consumption by 10-30% for puzzles with transpositions (ko, capture races).

**Independent test criteria:** Transposition hits > 0 on a puzzle with interchangeable moves; engine query count reduced compared to baseline.

- [x] T018 [US1] Implement `_compute_position_hash(moves, initial_position, player_to_move, ko_point) -> int` in `tools/puzzle-enrichment-lab/analyzers/solve_position.py` — computes stone positions from initial board + move sequence, returns `hash(frozenset((color, row, col)) | {("turn", player_to_move), ("ko", ko_point or "none")})`. Hash MUST include player-to-move and ko ban point to prevent incorrect transposition matches (Review Panel Topic 4)
- [x] T019 [US1] Add `transposition_cache: dict[int, SolutionNode]` parameter to `_build_tree_recursive()` in `tools/puzzle-enrichment-lab/analyzers/solve_position.py`
- [x] T020 [US1] Add cache lookup before `engine.query()` in `_build_tree_recursive()` — on hit, return deep copy and increment `completeness.transposition_hits` in `tools/puzzle-enrichment-lab/analyzers/solve_position.py`
- [x] T021 [US1] Add cache store after building node in `_build_tree_recursive()` in `tools/puzzle-enrichment-lab/analyzers/solve_position.py`
- [x] T022 [US1] Create empty cache in `build_solution_tree()` and pass through to recursive calls, gated by `config.solution_tree.transposition_enabled` in `tools/puzzle-enrichment-lab/analyzers/solve_position.py`
- [x] T023 [P] [US1] Write test `test_transposition_cache_reuses_position` — mock engine that tracks query count, two move orders reaching same position → single query in `tools/puzzle-enrichment-lab/tests/test_solve_position.py`
- [x] T024 [P] [US1] Write test `test_transposition_disabled_no_caching` — `transposition_enabled=False` → no cache, all queries fire in `tools/puzzle-enrichment-lab/tests/test_solve_position.py`
- [x] T025 [P] [US1] Write test `test_transposition_cache_scoped_per_puzzle` — two separate `build_solution_tree()` calls don't share cache in `tools/puzzle-enrichment-lab/tests/test_solve_position.py`
- [x] T026 [P] [US1] Write test `test_transposition_hits_tracked` — `TreeCompletenessMetrics.transposition_hits` incremented correctly in `tools/puzzle-enrichment-lab/tests/test_solve_position.py`
- [x] T027 [US1] Run full test suite to confirm zero regressions
- [x] T027a **GATE REVIEW — Phase 3:** ✅ Approved 2026-03-24. Review Panel verifies gate criteria from plan Phase 2 (Transposition). Transposition hits > 0 on ko-heavy fixture, engine query count reduced, no regressions. Sign off before proceeding.

---

## Phase 4: User Story — Simulation (Kawano) [KM-01]

**Story goal:** After proving one opponent response via full tree expansion, attempt to reuse the same player refutation sequence for sibling opponent responses with a lightweight verification query (50 visits instead of 500). Reduces `QueryBudget` consumption by 30-50% at opponent branching points.

**Independent test criteria:** `simulation_hits > 0` on cho-elementary fixtures; budget consumption reduced ≥15%.

- [x] T028 [US2] Implement `_extract_player_reply_sequence(node: SolutionNode) -> list[str]` in `tools/puzzle-enrichment-lab/analyzers/solve_position.py` — walks the correct-line children of a proven subtree and extracts the player move GTP strings
- [x] T029 [US2] Implement `_try_simulation(engine, moves, cached_reply_sequence, config: AiSolveConfig, query_budget, completeness) -> SolutionNode | None` in `tools/puzzle-enrichment-lab/analyzers/solve_position.py` — plays the opponent's sibling move then the FIRST cached player reply only (not the full sequence), runs verification query at `config.solution_tree.simulation_verify_visits`, checks if winrate delta ≤ `config.thresholds.t_good`. Returns completed node on success, `None` on failure. Verification at depth 1 is sufficient because if the defender's first response maintains winning advantage, the position is resolved (Review Panel Topic 3)
- [x] T030 [US2] Modify opponent-node branch in `_build_tree_recursive()` to call `_try_simulation()` for siblings after the first child is fully expanded, gated by `config.solution_tree.simulation_enabled` in `tools/puzzle-enrichment-lab/analyzers/solve_position.py`
- [x] T031 [US2] Ensure `_try_simulation()` increments `completeness.simulation_hits` on success and `completeness.simulation_misses` on failure in `tools/puzzle-enrichment-lab/analyzers/solve_position.py`
- [x] T032 [US2] Ensure `_try_simulation()` calls `query_budget.consume()` for its verification query in `tools/puzzle-enrichment-lab/analyzers/solve_position.py`
- [x] T033 [P] [US2] Write test `test_simulation_reuses_refutation` — mock engine where siblings share same refutation → simulation succeeds, query count = 1 (not full recursive) in `tools/puzzle-enrichment-lab/tests/test_solve_position.py`
- [x] T034 [P] [US2] Write test `test_simulation_fails_falls_back` — mock engine where sibling needs different reply → simulation fails, full recursive expansion used in `tools/puzzle-enrichment-lab/tests/test_solve_position.py`
- [x] T035 [P] [US2] Write test `test_simulation_disabled_no_effect` — `simulation_enabled=False` → no simulation attempted, behavior identical to pre-optimization in `tools/puzzle-enrichment-lab/tests/test_solve_position.py`
- [x] T036 [P] [US2] Write test `test_simulation_hits_tracked` — verify `simulation_hits` and `simulation_misses` counters in `TreeCompletenessMetrics` in `tools/puzzle-enrichment-lab/tests/test_solve_position.py`
- [x] T037 [P] [US2] Write test `test_simulation_respects_budget` — verification query consumes from `QueryBudget` in `tools/puzzle-enrichment-lab/tests/test_solve_position.py`
- [x] T038 [P] [US2] Write test `test_simulation_only_at_opponent_nodes` — simulation never attempted at player nodes in `tools/puzzle-enrichment-lab/tests/test_solve_position.py`
- [x] T039 [US2] Run full test suite to confirm zero regressions
- [x] T039a **GATE REVIEW — Phase 4:** ✅ Approved 2026-03-24. Review Panel verifies gate criteria from plan Phase 3 (Simulation). `simulation_hits > 0` on cho-elementary, budget reduced ≥15%, solution quality unchanged, no regressions. Sign off before proceeding.

---

## Phase 5: User Story — Forced Move Fast-Path [KM-03]

**Story goal:** Reduce MCTS visit count from 500 to 125 for trivially forced player continuations (single candidate with policy > 0.85). Saves ~375 visits per forced node without changing classification outcomes.

**Independent test criteria:** `forced_move_count > 0` on entry-level puzzles; visit consumption reduced; no classification changes.

- [x] T040 [US3] Add forced-move detection logic at player nodes in `_build_tree_recursive()` in `tools/puzzle-enrichment-lab/analyzers/solve_position.py` — check if top candidate has `policy > forced_move_policy_threshold` AND only 1 candidate passes `branch_min_policy`
- [x] T041 [US3] When forced-move detected, use `forced_move_visits` instead of `effective_visits` for the engine query in `tools/puzzle-enrichment-lab/analyzers/solve_position.py`
- [x] T042 [US3] Add safety net: if forced-move query produces winrate `delta > t_good`, re-query at full `effective_visits` in `tools/puzzle-enrichment-lab/analyzers/solve_position.py`
- [x] T043 [US3] Increment `completeness.forced_move_count` when forced-move fast-path is taken in `tools/puzzle-enrichment-lab/analyzers/solve_position.py`
- [x] T044 [P] [US3] Write test `test_forced_move_uses_reduced_visits` — single high-policy candidate → engine queried with `forced_move_visits` in `tools/puzzle-enrichment-lab/tests/test_solve_position.py`
- [x] T045 [P] [US3] Write test `test_forced_move_multiple_candidates_uses_full` — two candidates above `branch_min_policy` → engine queried with full `effective_visits` in `tools/puzzle-enrichment-lab/tests/test_solve_position.py`
- [x] T046 [P] [US3] Write test `test_forced_move_safety_net` — reduced visits disagrees (delta > t_good) → re-queries at full visits in `tools/puzzle-enrichment-lab/tests/test_solve_position.py`
- [x] T047 [P] [US3] Write test `test_forced_move_count_tracked` — `forced_move_count` counter incremented correctly in `tools/puzzle-enrichment-lab/tests/test_solve_position.py`
- [x] T048 [US3] Run full test suite to confirm zero regressions
- [x] T048a **GATE REVIEW — Phase 5:** ✅ Approved 2026-03-24. Review Panel verifies gate criteria from plan Phase 4 (Forced Move). Forced-move detection fires on ≥50% of player nodes in entry-level puzzles, visit consumption reduced, no classification changes. Sign off before proceeding.

---

## Phase 6: User Story — Proof-Depth Difficulty Signal [KM-04]

**Story goal:** Use the tree builder's `max_resolved_depth` (deepest non-truncated branch) as a new difficulty signal, capturing how much search effort was needed to prove the position resolved. Improves difficulty calibration accuracy at zero additional engine cost.

**Independent test criteria:** Deeper trees produce higher difficulty scores; `proof_depth=0` produces identical output to pre-change baseline.

- [x] T049 [US4] Implement `_compute_max_resolved_depth(tree: SolutionNode) -> int` in `tools/puzzle-enrichment-lab/analyzers/solve_position.py` — recursively find deepest non-truncated branch
- [x] T050 [US4] Populate `TreeCompletenessMetrics.max_resolved_depth` after tree build completes in `build_solution_tree()` in `tools/puzzle-enrichment-lab/analyzers/solve_position.py`
- [x] T051 [US4] Add `max_resolved_depth: int = 0` parameter to `estimate_difficulty()` in `tools/puzzle-enrichment-lab/analyzers/estimate_difficulty.py`
- [x] T052 [US4] Fold `max_resolved_depth` into structural sub-component using `StructuralDifficultyWeights.proof_depth` weight, normalized by `max_resolved_depth_ceiling` in `tools/puzzle-enrichment-lab/analyzers/estimate_difficulty.py`
- [x] T053 [P] [US4] Write test `test_proof_depth_affects_difficulty` — deeper tree → higher raw difficulty score in `tools/puzzle-enrichment-lab/tests/test_difficulty.py`
- [x] T054 [P] [US4] Write test `test_proof_depth_zero_when_no_tree` — `ac:1` puzzles (no AI tree) → signal = 0, no change in output in `tools/puzzle-enrichment-lab/tests/test_difficulty.py`
- [x] T055 [P] [US4] Write test `test_proof_depth_capped_at_ceiling` — depth > ceiling normalized to 1.0 in `tools/puzzle-enrichment-lab/tests/test_difficulty.py`
- [x] T056 [P] [US4] Write test `test_structural_weights_rebalanced` — 5-weight sum = 100 validated in `tools/puzzle-enrichment-lab/tests/test_difficulty.py`
- [x] T057 [P] [US4] Write test `test_difficulty_backward_compat` — `proof_depth=0` produces identical difficulty output to pre-change formula in `tools/puzzle-enrichment-lab/tests/test_difficulty.py`
- [x] T058 [US4] Run full test suite to confirm zero regressions
- [x] T058a **GATE REVIEW — Phase 6:** ✅ Approved 2026-03-24. Review Panel verifies gate criteria from plan Phase 5 (Proof-Depth). Calibration scores unchanged within ±1 level, proof-depth differentiates puzzles, weight sum = 100. Sign off before proceeding.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Goal:** Benchmark, documentation, and final validation.

- [x] T059 Write unit benchmark test `test_benchmark_optimization_mechanics` — mock engine verifying optimization counters fire correctly: `simulation_hits > 0`, `transposition_hits > 0`, `forced_move_count > 0` when all optimizations enabled. Mock must return realistic branching (3 opponent responses per node, 2 sharing same refutation for simulation) in `tools/puzzle-enrichment-lab/tests/test_solve_position.py`
- [x] T059b Write integration benchmark test `test_benchmark_budget_reduction_live` — run cho-elementary fixtures with live KataGo engine, optimizations ON vs OFF, assert `QueryBudget.used` reduced ≥15%. Marked `@pytest.mark.integration` (requires live engine, not run in CI) in `tools/puzzle-enrichment-lab/tests/test_solve_position.py` (Review Panel Topic 6)
- [x] T060 Write benchmark test `test_benchmark_solution_quality_unchanged` — same correct/wrong classifications with optimizations ON vs OFF in `tools/puzzle-enrichment-lab/tests/test_solve_position.py`
- [x] T061 [P] Update `TODO/ai-solve-enrichment-plan-v3.md` version history to reference this plan
- [x] T062 [P] Add CHANGELOG entry for KM search optimizations
- [x] T064 Create ADR `TODO/katago-puzzle-enrichment/009-adr-km-search-optimizations.md` — capture DD-KM1 through DD-KM4 and DD-L3 design decisions, deferred techniques KM-05/06/07 with rationale, Review Panel consultation record, both paper citations (AAAI-05 + ICGA), and L3 implementation record
- [x] T065 Update `docs/architecture/tools/katago-enrichment.md` — add KM optimization design decisions: simulation across siblings, transposition table, forced move fast-path, proof-depth difficulty signal
- [x] T066 Update `docs/how-to/tools/katago-enrichment-lab.md` — add new config knobs documentation: `simulation_enabled`, `transposition_enabled`, `forced_move_visits`, `forced_move_policy_threshold`, `simulation_verify_visits`
- [x] T067 Update `docs/reference/enrichment-config.md` — add new `ai_solve.solution_tree` fields table and schema v1.15 delta
- [x] T063 Run full test suite with all optimizations enabled — final regression check
- [x] T063a **GATE REVIEW — Phase 7 (Final):** ✅ Approved 2026-03-24. Review Panel verifies gate criteria from plan Phase 6 (Benchmarks + Docs). Budget reduction ≥15% demonstrated, zero classification regressions, all documentation complete. **Final sign-off — feature complete.**

---

## L3: Depth-Dependent Policy Threshold [Thomsen Lambda-Search] — COMPLETED

**Status:** All tasks completed and verified (166 tests passing).

- [x] T-L3-01 Replace flat `branch_min_policy` field description with depth-aware description in `SolutionTreeConfig` in `tools/puzzle-enrichment-lab/config.py`
- [x] T-L3-02 Add `depth_policy_scale: float = 0.01` field to `SolutionTreeConfig` in `tools/puzzle-enrichment-lab/config.py`
- [x] T-L3-03 Add `branches_pruned_by_depth_policy: int = 0` counter to `TreeCompletenessMetrics` in `tools/puzzle-enrichment-lab/models/solve_result.py`
- [x] T-L3-04 Replace flat `branch_min_policy` filter in `_build_tree_recursive()` opponent-node loop with depth-dependent formula `branch_min_policy + depth_policy_scale * depth` in `tools/puzzle-enrichment-lab/analyzers/solve_position.py`
- [x] T-L3-05 Add depth-policy pruning tracking: increment `completeness.branches_pruned_by_depth_policy` when a candidate passes flat threshold but fails depth-adjusted threshold in `tools/puzzle-enrichment-lab/analyzers/solve_position.py`
- [x] T-L3-06 Add `"depth_policy_scale": 0.01` to `config/katago-enrichment.json` under `ai_solve.solution_tree`
- [x] T-L3-07 Replace test `test_respects_branch_min_policy` with `test_respects_depth_dependent_policy_threshold` — tests depth-adjusted filtering and counter tracking in `tools/puzzle-enrichment-lab/tests/test_solve_position.py`
- [x] T-L3-08 Run test suite (166 passed, 0 failed) to confirm zero regressions

---

## Dependencies

```
T001-T002 (Setup baseline)
  │
  ▼
T-L3-01–T-L3-08 (L3 Depth-Dependent Policy — COMPLETED)
  │
  ▼
T003-T017 (Config — must complete first)
  │
  ├──► T018-T027 (Transposition [US1])
  │       │
  │       ▼
  ├──► T028-T039 (Simulation [US2]) — benefits from transposition being in place
  │
  ├──► T040-T048 (Forced Move [US3]) — independent of US1/US2
  │
  ├──► T049-T058 (Proof-Depth [US4]) — independent of US1/US2/US3
  │
  ▼       ▼
T059-T063 (Benchmarks + Docs — after all user stories)
```

## Parallel Execution Opportunities

**Within Phase 2 (Config):** T003-T012 are independent file edits — can be parallelized.

**After Phase 2:** US1 (T018-T027), US3 (T040-T048), and US4 (T049-T058) are fully independent and can execute in parallel. US2 (T028-T039) benefits from US1 being done first but is not strictly blocked.

**Within each user story:** Implementation tasks are sequential, but test tasks marked [P] can be written in parallel with each other.

---

## Summary

| Metric                             | Count                   |
| ---------------------------------- | ----------------------- |
| Total tasks                        | 83                      |
| Phase 1 (Setup)                    | 2                       |
| L3 (Depth-Dependent Policy — DONE) | 8                       |
| Phase 2 (Config)                   | 16 (incl. gate)         |
| Phase 3 (Transposition US1)        | 11 (incl. gate)         |
| Phase 4 (Simulation US2)           | 13 (incl. gate)         |
| Phase 5 (Forced Move US3)          | 10 (incl. gate)         |
| Phase 6 (Proof-Depth US4)          | 11 (incl. gate)         |
| Phase 7 (Polish)                   | 12 (incl. gate)         |
| Parallelizable tasks               | 24                      |
| Completed tasks                    | 75 (all implementation) |

**All 75 tasks across all 7 phases are required (including 6 gate reviews).** No phase is optional or deferrable. Tests, documentation updates, and benchmarks are part of the definition of done — not follow-up work.

### Implementation Strategy

1. **All phases are MVP.** Every phase (Config, Transposition, Simulation, Forced Move, Proof-Depth, Benchmarks + Docs) must be completed. No partial delivery.
2. **Execution order:** Phase 1 (Setup) → Phase 2 (Config) → Phases 3-6 (user stories, parallelizable after Config) → Phase 7 (Polish). Each phase gated by its test suite passing.
3. **Safety via config gates:** All features enabled by default but can be disabled per-field (`simulation_enabled`, `transposition_enabled`, `forced_move_visits=0`). Rollback is a config change, not a code revert.
4. **Definition of done:** Implementation + tests + documentation + benchmark validation. Skipping tests or docs is NEVER acceptable (per project conventions).
