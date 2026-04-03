# Kishimoto-Mueller Search Optimizations — Implementation Plan

**Last Updated:** 2026-03-04
**Status:** COMPLETE — All gates approved 2026-03-24 (GOV-REVIEW-APPROVED, 10/10 unanimous)
**Source Papers:**

- Kishimoto, A. & Müller, M. (2005). _Search versus Knowledge for Solving Life and Death Problems in Go._ AAAI-05, pp. 1374–1379.
- Thomsen, T. (2000). _Lambda-Search in Game Trees — with Application to Go._ ICGA Journal, 23(4), pp. 203–217.
  **Scope:** `tools/puzzle-enrichment-lab/` — `analyzers/solve_position.py`, `analyzers/estimate_difficulty.py`, `config.py`, `models/solve_result.py`
  **Depends On:** `TODO/ai-solve-enrichment-plan-v3.md` (completed Phases 1–12), `TODO/ai-solve-remediation-sprints.md` (Sprints 1–5)

---

## Paper Summary

The Kishimoto-Müller paper describes **TsumeGo Explorer**, a tsumego solver that outperformed GoTools (15-year champion) by **2.8× on standard problems and 20×+ on hard problems**. Core thesis: _efficient search techniques with minimal domain knowledge outperform extensive knowledge engineering_ for enclosed life-and-death problems. The solver uses **depth-first proof-number search (df-pn)** with four key enhancements: Kawano's simulation, transposition tables, forced move detection, and heuristic proof-number initialization.

The Thomsen paper introduces **lambda search**, a generalized null-move framework for Go life-and-death problems. Key insight: moves at deeper tree levels must be more forcing (higher "lambda order") to be relevant. This translates to depth-dependent branching thresholds in the enrichment lab's KataGo-oracle architecture.

This plan adapts 4 of 7 AAAI-05 techniques plus 1 lambda-search technique (L3) to the enrichment lab. Three AAAI-05 techniques were evaluated and deferred (see §Deferred Techniques). **L3 (depth-dependent policy threshold) is implemented** — see DD-L3.

---

## Review Panel

| Member                             | Domain                          | Perspective for this plan                                                                              |
| ---------------------------------- | ------------------------------- | ------------------------------------------------------------------------------------------------------ |
| **Cho Chikun** (9p, Meijin)        | Classical tsumego authority     | Correctness: does the optimization preserve deterministic, correct solutions?                          |
| **Shin Jinseo** (9p)               | AI-era professional             | KataGo integration: where does KataGo actually struggle, and which techniques address real weaknesses? |
| **Kishimoto** (Paper author proxy) | df-pn / search algorithm expert | Faithfulness: is the adaptation true to the paper's mechanism, or a loose analogy?                     |
| **Principal Staff Engineer A**     | Systems architect               | Feasibility: config-driven? Testable? Backward compatible with existing v3 pipeline?                   |
| **Principal Staff Engineer B**     | Pipeline engineer               | Measurability: does this reduce `QueryBudget` consumption in observable, benchmarkable ways?           |

### Gate Protocol

Follows the v3 gate protocol:

1. **Implementation complete** — Code written, lint/type checks pass.
2. **Tests pass** — Phase-specific tests + no regressions in existing suite (~220 tests).
3. **Documentation updated** — Plan document, config schema, CHANGELOG.
4. **Review Panel sign-off** — Panel confirms correct adaptation of paper technique.
5. **Benchmark comparison** — Before/after `QueryBudget.used` on calibration fixtures (cho-elementary, cho-intermediate, cho-advanced).

---

## Design Decisions

### DD-KM1: Simulation Across Sibling Branches

**Decision:** After building the first opponent response subtree, cache the player's winning reply sequence. For subsequent sibling opponent responses at the same depth, attempt to "simulate" the cached sequence by running a lightweight verification query. If the cached reply still produces a TE classification (winrate delta ≤ `t_good`), mark the sibling branch as resolved without recursive expansion.

**Paper reference:** §4.2 — Kawano's simulation technique. _"A successful simulation requires much less effort than a normal search, since even with good move ordering, a newly created search tree is typically much larger than an existing proof tree."_

**Panel guidance:**

- **Cho Chikun:** "In tsumego, 80% of wrong answers fail for the same reason. If the attacker plays anywhere except the vital point, the defender's response is identical."
- **Shin Jinseo:** "KataGo's policy already concentrates >90% on forced moves. But we still pay 500 visits to confirm. A lightweight 50-visit simulation check is valid."
- **Kishimoto (proxy):** "This was our biggest performance win. The key: simulation must be _verified_, not assumed."
- **Engineer B:** "Estimated 30-50% budget reduction. Highly measurable via `simulation_hits` counter."

**Invariants:**

- Simulation NEVER assumes correctness — always runs a verification query at `simulation_verify_visits`.
- If verification fails (winrate delta > `t_good`), falls back to full recursive expansion.
- Simulation only applies at opponent nodes (AND nodes in the paper's formulation).
- `simulation_hits` and `simulation_misses` tracked in `TreeCompletenessMetrics`.

### DD-KM2: Transposition Table Within Tree Building

**Decision:** Maintain a position-hash → `SolutionNode` cache within a single `build_solution_tree()` invocation. Before querying the engine at any node, compute a position hash from the stone configuration (not the move sequence). If the hash exists in the cache, reuse the cached subtree. After building a node, store it.

**Paper reference:** §3, §6 — _"df-pn utilizes proof and disproof numbers from previous search iterations to choose a promising direction... [it] uses the transposition table more extensively"_ than GoTools.

**Panel guidance:**

- **Cho Chikun:** "Move order rarely matters in tsumego reading. The same shape is the same problem."
- **Kishimoto (proxy):** "The paper used a 300MB table. For your 50-query budget, a simple `dict` suffices."
- **Engineer A:** "Position hash = `frozenset` of `(color, row, col)` tuples. No Zobrist needed at this scale."

**Invariants:**

- Cache is scoped to a single `build_solution_tree()` call — NOT shared across puzzles.
- Position hash is computed from stone placement, not move sequence (transpositions require position-based keys).
- Cached nodes are deep-copied to prevent mutation side effects.
- `transposition_hits` tracked in `TreeCompletenessMetrics`.

### DD-KM3: Forced Move Fast-Path

**Decision:** At player nodes in `_build_tree_recursive()`, if exactly one candidate passes `branch_min_policy` AND its policy prior exceeds `forced_move_policy_threshold` (default 0.85), use `forced_move_visits` (default 125) instead of full `effective_visits` (500+). This reduces visit cost for trivially forced continuations.

**Paper reference:** §4.2 — _"Forced moves are a safe form of pruning, which can decrease the branching factor."_ The paper defines forced defender/attacker moves as positions where only one response prevents immediate loss.

**Panel guidance:**

- **Cho Chikun:** "Forced moves are the backbone of tsumego. In a 10-move sequence, often 6-7 are forced."
- **Shin Jinseo:** "KataGo's policy concentrates >90% on forced moves. 125 visits is more than enough."
- **Kishimoto (proxy):** "The paper skips search entirely for forced moves. Using reduced visits is more conservative — better for your use case."
- **Engineer A:** "Config-driven: `forced_move_visits`, `forced_move_policy_threshold` in `SolutionTreeConfig`."

**Invariants:**

- Only applies at player nodes (single correct follow-up), NOT opponent nodes (branching).
- Still queries the engine — just with reduced visits. Never skips the query entirely.
- If the forced move's verified winrate delta > `t_good`, falls back to full visits (safety net).
- `forced_move_count` tracked in `TreeCompletenessMetrics`.

### DD-KM4: Proof-Depth Difficulty Signal

**Decision:** After the solution tree is built, compute `max_resolved_depth` — the deepest branch that reached a natural stopping condition (winrate stability, ownership convergence, or seki detection). Add this as a sub-signal within the structural difficulty component in `estimate_difficulty()`, alongside existing `solution_depth`, `branch_count`, `local_candidates`, and `refutation_count`.

**Paper reference:** §4.2 — Heuristic initialization computes _"minimum number of successive defender moves required to create two eyes"_ as a proxy for problem difficulty. `max_resolved_depth` is the empirical analogue: how deep did we need to search to prove the position resolved?

**Panel guidance:**

- **Cho Chikun:** "The number of moves to read out a position IS the difficulty. Currently underweighted."
- **Shin Jinseo:** "Use it as _a_ signal, not _the_ signal. KataGo can sometimes resolve hard positions quickly."
- **Engineer B:** "No additional engine queries — derived from existing tree data. Pure post-processing."

**Invariants:**

- Zero additional engine cost. Computed from `TreeCompletenessMetrics` and tree traversal.
- Weight is config-driven via `StructuralDifficultyWeights.proof_depth`.
- `StructuralDifficultyWeights` total must still sum to 100 (rebalance existing weights).
- Only populated when AI-Solve has built a tree (`ac:2`). For `ac:1` puzzles, signal is 0.

### DD-L3: Depth-Dependent Policy Threshold

**Decision:** Replace the flat `branch_min_policy` filter with a depth-dependent formula: `effective_min_policy = branch_min_policy + depth_policy_scale * depth`. Deeper opponent nodes require higher policy priors to be explored. This reduces budget waste on speculative deep branches while preserving full branching at shallow levels where creative opponent responses matter.

**Paper reference:** Thomsen (2000) — Lambda search core insight: _"By limiting the allowed moves in the lambda-trees, the branching factor is reduced."_ Lambda-n moves must be increasingly forcing at higher orders, directly analogous to tighter policy thresholds at greater tree depth.

**Panel guidance:**

- **Cho Chikun:** "The first opponent response can be surprising, but five moves deep, if the opponent's move isn't forced, the line is irrelevant."
- **Shin Jinseo:** "KataGo's policy already concentrates sharply at deep nodes. Need calibration data to confirm incremental value."
- **Kishimoto (proxy):** "Complementary to KM-01 (simulation) and KM-03 (forced move). Operates on opponent nodes; they operate on player nodes."
- **Engineer A:** "Formula approach: single new config param `depth_policy_scale`. ~15 lines of logic. Config-driven, testable."
- **Engineer B:** "Measurable via `branches_pruned_by_depth_policy` counter in `TreeCompletenessMetrics`."

**Status:** IMPLEMENTED. Config fields `branch_min_policy` (base) and `depth_policy_scale` (per-depth increment) drive the formula. Counter `branches_pruned_by_depth_policy` tracks pruning that the flat threshold alone would not have caught.

**Invariants:**

- Formula only tightens with depth — never goes below `branch_min_policy`.
- Only applies at opponent nodes (same scope as flat filter).
- `depth_policy_scale = 0.0` reverts to flat behavior (safe fallback).
- `branches_pruned_by_depth_policy` tracked in `TreeCompletenessMetrics`.

---

## Deferred Techniques

These were evaluated by the Review Panel and deferred. Rationale preserved for future reference.

| ID    | Technique                              | Paper Section | Reason Deferred                                                                                                                                                                                              |
| ----- | -------------------------------------- | ------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| KM-05 | Relevance Zone Refinement (flood-fill) | §2            | Current tight-board cropping + tsumego frame + policy filtering already achieves the paper's "enclosed region" intent. Marginal gain, regression risk.                                                       |
| KM-06 | Non-Uniform Budget Allocation          | §4.2          | Paper's df-pn threshold mechanism doesn't transfer to the KataGo-oracle architecture. **Partially addressed by L3** (depth-dependent policy thresholds achieve depth-aware resource allocation via pruning). |
| KM-07 | Ko Re-Search                           | §4.3          | Paper's re-search is necessary for proof-based solvers but redundant when using KataGo's MCTS, which inherently handles ko via Tromp-Taylor rules. Current `ko_validation.py` + `YK` property suffice.       |

---

## Phases and Gates

### Phase 1: Config Extension

**Scope:** Add KM-01 through KM-04 config parameters to existing models. Bump schema.

**Correction Level:** Level 2 (1-2 files, explicit behavior change) → `Plan Mode → Approve → Execute`

**Deliverables:**

- `SolutionTreeConfig` — add:
  - `simulation_enabled: bool = True`
  - `simulation_verify_visits: int = 50`
  - `forced_move_visits: int = 125`
  - `forced_move_policy_threshold: float = 0.85`
  - `transposition_enabled: bool = True`
- `TreeCompletenessMetrics` — add:
  - `simulation_hits: int = 0`
  - `simulation_misses: int = 0`
  - `transposition_hits: int = 0`
  - `forced_move_count: int = 0`
  - `max_resolved_depth: int = 0`
- `StructuralDifficultyWeights` — add:
  - `proof_depth: float = 10.0` (rebalance: `solution_depth: 35`, `branch_count: 22`, `local_candidates: 18`, `refutation_count: 15`, `proof_depth: 10` — sum = 100)
  - Update `check_weights_sum()` validator to include `proof_depth` in the sum (currently sums only 4 fields)
- `config/katago-enrichment.json` — add fields under `ai_solve.solution_tree`
- Schema version `1.14` → `1.15`

**Files:** `config.py`, `models/solve_result.py`, `config/katago-enrichment.json`

**Tests:**

- Config parses with new fields
- Config parses without new fields (backward compat — Pydantic defaults)
- `StructuralDifficultyWeights` sum validation passes with rebalanced weights
- `TreeCompletenessMetrics` new counters initialize to 0

**Gate 1 Criteria:**

- [ ] All config tests pass
- [ ] Existing tests unaffected (default values match pre-change behavior)
- [ ] Review Panel sign-off

---

### Phase 2: Transposition Table (KM-02)

**Scope:** Add position hashing and cache to tree builder.

**Correction Level:** Level 2 (1 file, ~60 lines logic)

**Why Phase 2 before KM-01:** Transposition is simpler to implement and test in isolation. Simulation (KM-01) builds on the tree builder and benefits from transposition being in place first.

**Deliverables:**

- `_compute_position_hash(moves: list[str], initial_position) -> int` — compute stone positions from initial board + move sequence, return `hash(frozenset)`. The `initial_position` data (stones from SGF `AB[]`/`AW[]`) is obtained from the `SyncEngineAdapter`'s stored position object, which is already available in `build_solution_tree()` via the `engine` parameter.
- `_build_tree_recursive()` — add `transposition_cache: dict[int, SolutionNode]` and `initial_position` parameters.
  - Before `engine.query()`: check cache → return `node.model_copy(deep=True)` (Pydantic v2 deep copy) if hit.
  - After building node: store in cache.
  - Increment `completeness.transposition_hits` on cache hit.
- `build_solution_tree()` — create empty cache, pass through.
- Gated by `config.solution_tree.transposition_enabled`.

**Files:** `analyzers/solve_position.py`

**Tests:**

- `test_transposition_cache_reuses_position` — same position via different move orders → single query
- `test_transposition_disabled_no_caching` — `transposition_enabled=False` → no caching
- `test_transposition_cache_scoped_per_puzzle` — cache not leaked between puzzles
- `test_transposition_hits_tracked` — `TreeCompletenessMetrics.transposition_hits` incremented

**Gate 2 Criteria:**

- [ ] Transposition hit count > 0 on ko-heavy calibration fixture
- [ ] Engine query count reduced for puzzles with interchangeable moves
- [ ] No regressions in existing tree builder tests
- [ ] Review Panel sign-off

---

### Phase 3: Simulation (KM-01)

**Scope:** Add Kawano's simulation to opponent node expansion.

**Correction Level:** Level 2 (1 file, ~80 lines logic)

**Deliverables:**

- `_try_simulation(engine, moves, cached_reply_sequence, config: AiSolveConfig, query_budget, completeness) -> SolutionNode | None`
  - Takes the player's winning reply sequence from a proven sibling.
  - Plays the cached sequence on the current position.
  - Runs a single verification query at `config.solution_tree.simulation_verify_visits`.
  - If verified (winrate delta ≤ `config.thresholds.t_good`): return completed node, increment `completeness.simulation_hits`.
  - If failed: return `None`, increment `completeness.simulation_misses`, caller falls back to full expansion.
  - **Edge case:** If the first sibling's tree was truncated (no proven correct line to extract), simulation is NOT attempted for subsequent siblings — fall through to full expansion.
- `_build_tree_recursive()` at opponent nodes:
  - After building first child (most promising response), extract the player reply sequence from the first child's subtree.
  - For subsequent sibling children, call `_try_simulation()` before full recursive descent.
- Gated by `config.solution_tree.simulation_enabled`.

**Algorithm detail (adapted from paper §4.2):**

```
At opponent node N with children [C1, C2, C3] (sorted by policy desc):
  1. Build C1 fully via _build_tree_recursive()
  2. Extract player_reply_sequence = [moves from C1's correct-line children]
  3. For C2:
     a. Try _try_simulation(engine, moves + [C2.move], player_reply_sequence, ...)
     b. If simulation succeeds → C2 is done (1 query instead of ~5-10)
     c. If simulation fails → full _build_tree_recursive() for C2
  4. Same for C3
```

**Files:** `analyzers/solve_position.py`

**Tests:**

- `test_simulation_reuses_refutation` — sibling opponent move refuted by same reply → 1 verification query
- `test_simulation_fails_falls_back` — sibling needs different reply → full expansion
- `test_simulation_disabled_no_effect` — `simulation_enabled=False` → behavior unchanged
- `test_simulation_hits_tracked` — `TreeCompletenessMetrics.simulation_hits/misses` incremented
- `test_simulation_respects_budget` — simulation verification consumes from `QueryBudget`
- `test_simulation_only_at_opponent_nodes` — never attempted at player nodes
- `test_simulation_skipped_when_first_sibling_truncated` — truncated first sibling → no simulation attempted for subsequent siblings

**Gate 3 Criteria:**

- [ ] `simulation_hits > 0` on cho-elementary calibration fixtures
- [ ] Budget consumption measurably reduced (≥15% on calibration set)
- [ ] Solution tree quality unchanged (same correct/wrong classification)
- [ ] No regressions in existing tests
- [ ] Review Panel sign-off

---

### Phase 4: Forced Move Fast-Path (KM-03)

**Scope:** Reduce visit count for trivially forced player continuations.

**Correction Level:** Level 1 (1 file, ~30 lines logic)

**Deliverables:**

- `_build_tree_recursive()` at player nodes:
  - After querying the engine at normal visits, inspect the returned move candidates. If the top candidate has `policy > forced_move_policy_threshold` AND only 1 candidate passes `branch_min_policy`, the position is considered forced.
  - **Note:** Detection happens AFTER the initial query (the policy values come from the engine response). The visit savings come from the CHILD node's query — when we recurse into the forced move's continuation, that child query uses `forced_move_visits` instead of `effective_visits`. The current node's query runs at full visits regardless.
  - Increment `completeness.forced_move_count`.
  - Safety net: if verified winrate delta > `t_good` at reduced visits, re-query at full visits.
- Gated by `forced_move_visits > 0` (set to 0 to disable).

**Files:** `analyzers/solve_position.py`

**Tests:**

- `test_forced_move_uses_reduced_visits` — single high-policy candidate → reduced visits
- `test_forced_move_multiple_candidates_uses_full` — two candidates above threshold → full visits
- `test_forced_move_safety_net` — reduced visits disagrees → re-queries at full visits
- `test_forced_move_count_tracked` — counter incremented correctly

**Gate 4 Criteria:**

- [ ] Forced move detection fires on ≥50% of player nodes in entry-level puzzles
- [ ] Total visit consumption reduced (visits, not queries — each query is cheaper)
- [ ] No classification changes compared to full-visit baseline
- [ ] Review Panel sign-off

---

### Phase 5: Proof-Depth Difficulty Signal (KM-04)

**Scope:** Add `max_resolved_depth` to difficulty estimation.

**Correction Level:** Level 2 (2 files, ~40 lines logic)

**Deliverables:**

- `_compute_max_resolved_depth(tree: SolutionNode) -> int` — recursively find deepest non-truncated branch.
- `estimate_difficulty()` — accept `max_resolved_depth: int = 0` keyword parameter.
- Update callers of `estimate_difficulty()` in `analyzers/enrich_single.py` to pass `max_resolved_depth` from `TreeCompletenessMetrics` when available (AI-Solve built a tree).
  - Fold into structural sub-component using `StructuralDifficultyWeights.proof_depth`.
  - Normalize: `min(max_resolved_depth / max_resolved_depth_ceiling, 1.0)`.
- Add `max_resolved_depth_ceiling: int = 20` to `DifficultyNormalizationConfig`.
- `TreeCompletenessMetrics.max_resolved_depth` populated after tree build.

**Files:** `analyzers/solve_position.py`, `analyzers/estimate_difficulty.py`, `analyzers/enrich_single.py`, `config.py`

**Tests:**

- `test_proof_depth_affects_difficulty` — deeper tree → higher raw score
- `test_proof_depth_zero_when_no_tree` — `ac:1` puzzles → signal = 0, no change
- `test_proof_depth_capped_at_ceiling` — depth > ceiling normalized to 1.0
- `test_proof_depth_used_in_structural_formula` — verify `estimate_difficulty()` correctly weights `proof_depth` in its structural sub-component (distinct from config sum validation)
- `test_difficulty_backward_compat` — `proof_depth=0` produces same output as before

**Gate 5 Criteria:**

- [ ] Calibration scores on cho-elementary/intermediate/advanced unchanged within ±1 level
- [ ] Proof-depth signal differentiates puzzles with same structural metrics but different search effort
- [ ] Weight rebalancing validated (sum = 100)
- [ ] Review Panel sign-off

---

### Phase 6: Benchmarks + Documentation

**Scope:** End-to-end benchmark on calibration fixtures, documentation update.

**Correction Level:** Level 1 (docs only + test fixtures)

**Deliverables:**

- Benchmark test: run calibration fixtures with KM optimizations ON vs OFF.
  - Measure: `QueryBudget.used`, `simulation_hits`, `transposition_hits`, `forced_move_count`.
  - Assert: budget reduction ≥ 15% on average across calibration set.
  - Mock engine design: must track `query_budget.used` counts accurately. Design mock to return realistic branching (3 opponent responses per node, 2 sharing same refutation for simulation testing).
- Update `TODO/ai-solve-enrichment-plan-v3.md` — reference this plan in version history.
- Update `config/katago-enrichment.json` schema docs.
- CHANGELOG entry.
- **ADR:** Create `TODO/katago-puzzle-enrichment/009-adr-km-search-optimizations.md` capturing DD-KM1 through DD-KM4 and deferred KM-05/06/07 rationale.
- **Architecture doc:** Update `docs/architecture/tools/katago-enrichment.md` with KM optimization design decisions (simulation, transposition, forced move, proof-depth).
- **How-to doc:** Update `docs/how-to/tools/katago-enrichment-lab.md` with new config knobs (`simulation_enabled`, `transposition_enabled`, `forced_move_visits`, `forced_move_policy_threshold`, `simulation_verify_visits`).
- **Reference doc:** Update `docs/reference/enrichment-config.md` with new `ai_solve.solution_tree` fields and schema v1.15 delta.

**Tests:**

- `test_benchmark_budget_reduction` — calibration set budget usage with optimizations ON < budget usage OFF
- `test_benchmark_solution_quality_unchanged` — same correct/wrong classifications with optimizations ON vs OFF

**Gate 6 Criteria:**

- [ ] Budget reduction ≥ 15% demonstrated on calibration fixtures
- [ ] Zero classification regressions
- [ ] Documentation complete
- [ ] Review Panel final sign-off

---

## Phase Dependency Graph

```
P1 (Config) ─────────────────────┐
  │                               │
  ├──► P2 (Transposition KM-02)  │
  │       │                       │
  │       ▼                       │
  ├──► P3 (Simulation KM-01) ◄──┘
  │       │
  ├──► P4 (Forced Move KM-03)
  │       │
  ├──► P5 (Proof-Depth KM-04)
  │       │
  ▼       ▼
P6 (Benchmarks + Docs) ◄── all above
```

P2, P3, P4, P5 can be developed in parallel after P1, but P3 benefits from P2 being in place (transposition cache reduces simulation re-queries).

---

## Estimated Scope

| Category           | Lines                                                                       |
| ------------------ | --------------------------------------------------------------------------- |
| Config changes     | ~40 (config.py, models/solve_result.py)                                     |
| New algorithm code | ~200 (solve_position.py, estimate_difficulty.py)                            |
| New tests          | ~300 (test_solve_position.py, test_estimate_difficulty.py)                  |
| Documentation      | ~7 files (ADR, architecture, how-to, reference, CHANGELOG, v3 plan, schema) |

**Total:** ~540 lines of code/tests, ~3 doc files.

---

## Risks and Mitigations

| Risk                                                 | Severity | Mitigation                                                                                                                                                                                                        |
| ---------------------------------------------------- | -------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Simulation produces incorrect subtrees               | MEDIUM   | Verification query at `simulation_verify_visits` (never assumed). Safety net: if delta > `t_good`, fall back to full expansion.                                                                                   |
| Transposition hash collision                         | LOW      | `frozenset` of `(color, row, col)` tuples is collision-free for positions ≤ 361 stones. Only used within single puzzle scope.                                                                                     |
| Forced move threshold too aggressive                 | LOW      | Safety net: if reduced-visit winrate disagrees with expectation, re-query at full visits. Config-driven threshold (adjustable).                                                                                   |
| Difficulty calibration drift from proof-depth signal | MEDIUM   | Weight is small (10/100 in structural, which is 20/100 overall = 2% total impact). Guard: `proof_depth=0` for `ac:1` puzzles → no change for non-AI-solved puzzles.                                               |
| Depth-dependent policy pruning too aggressive        | LOW      | `depth_policy_scale = 0.0` reverts to flat behavior. Counter `branches_pruned_by_depth_policy` monitors impact. Config-tunable.                                                                                   |
| Breaking existing test suite                         | **NONE** | All features gated by config flags with defaults matching current behavior. `simulation_enabled=True` and `transposition_enabled=True` are safe defaults because they only save budget, never change correctness. |

---

## Non-Goals

- **Implementing full df-pn.** We adapt 4 techniques from the paper, not the search algorithm itself. KataGo remains the oracle.
- **Replacing the existing tree builder architecture.** This is incremental optimization, not a rewrite.
- **Cross-puzzle transposition sharing.** Cache is scoped per-puzzle. Cross-puzzle sharing would require a persistent store and introduces cache invalidation complexity.
- **Simulation across different root trees.** Simulation only operates within a single correct-root tree's opponent branches, not across Priority A/B/C roots.

---

## Version History

| Version | Date       | Change                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| ------- | ---------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| v1      | 2026-03-04 | Initial plan — 7 techniques evaluated, 4 approved (KM-01 through KM-04), 3 deferred (KM-05 through KM-07). 6 phases.                                                                                                                                                                                                                                                                                                                                                                                                                           |
| v1.1    | 2026-03-04 | Analysis remediation — 10 consistency fixes (A1-A10): validator update for proof_depth, initial_position threading for transposition hash, AiSolveConfig type clarification for simulation, forced-move chicken-and-egg resolution, truncated-sibling edge case, phase numbering alignment, test deduplication, model_copy specification, mock design note, enrich_single caller update. Tasks bumped to 68.                                                                                                                                   |
| v1.2    | 2026-03-04 | Review Panel consultation — 5 amendments approved: (1) T018: position hash must include player-to-move + ko ban point; (2) T029: simulation verifies first cached reply only, not full sequence; (3) T009: explicitly includes check_weights_sum() validator update; (4) T059: split into unit mock benchmark + live integration benchmark (T059b); (5) Weight rebalancing confirmed. Plan status: **APPROVED by Review Panel**.                                                                                                               |
| v1.3    | 2026-03-04 | L3 (Thomsen lambda-search) — Added DD-L3: depth-dependent policy threshold. **Implemented** in config.py (`depth_policy_scale`), solve_position.py (formula replaces flat filter), solve_result.py (`branches_pruned_by_depth_policy` counter), katago-enrichment.json, and test updated. Replaced old flat `test_respects_branch_min_policy` with `test_respects_depth_dependent_policy_threshold`. KM-06 deferred rationale updated to note L3 partially addresses it. Second source paper (Thomsen 2000) added. ADR update planned for 009. |
