# ADR 009: Kishimoto-Mueller Search Optimizations

**Last Updated:** 2026-03-05
**Status:** APPROVED — Implementation in progress
**Plan:** `TODO/kishimoto-mueller-search-optimizations.md`
**Tasks:** `TODO/kishimoto-mueller-tasks.md`

---

## Context

The AI-Solve solution tree builder (`analyzers/solve_position.py`) queries KataGo for every node in the tree. For puzzles with 3+ opponent responses per node, this creates significant `QueryBudget` consumption—often exhausting the budget before fully resolving deep branches.

Two academic papers describe search optimizations specifically designed for Go life-and-death problems:

1. **Kishimoto, A. & Müller, M. (2005).** _Search versus Knowledge for Solving Life and Death Problems in Go._ AAAI-05, pp. 1374–1379.
2. **Thomsen, T. (2000).** _Lambda-Search in Game Trees — with Application to Go._ ICGA Journal, 23(4), pp. 203–217.

The Kishimoto-Müller paper describes **TsumeGo Explorer**, which outperformed GoTools by 2.8× on standard problems and 20×+ on hard problems using efficient search techniques with minimal domain knowledge.

---

## Design Decisions

### DD-KM1: Simulation Across Sibling Branches

**Decision:** After building the first opponent response subtree, cache the player's winning reply sequence. For subsequent sibling opponent responses, attempt a lightweight verification query (`simulation_verify_visits=50`) using the cached reply. If the cached reply still produces a correct classification (winrate delta ≤ `t_good`), mark the sibling as resolved without recursive expansion.

**Paper reference:** §4.2 — Kawano's simulation technique.

**Invariants:**

- Simulation NEVER assumes correctness — always runs a verification query.
- On verification failure, falls back to full recursive expansion.
- Only applies at opponent nodes (AND nodes).
- `simulation_hits` and `simulation_misses` tracked in `TreeCompletenessMetrics`.

### DD-KM2: Transposition Table Within Tree Building

**Decision:** Maintain a `position_hash → SolutionNode` cache within a single `build_solution_tree()` invocation. Position hash is computed from stone configuration (not move sequence), including player-to-move and ko ban point.

**Paper reference:** §3, §6 — df-pn transposition tables.

**Invariants:**

- Cache scoped to single puzzle (not shared across puzzles).
- Position hash from `frozenset((color, row, col))` tuples + player-to-move + ko point.
- Cached nodes deep-copied to prevent mutation side effects.
- `transposition_hits` tracked in `TreeCompletenessMetrics`.

### DD-KM3: Forced Move Fast-Path

**Decision:** At player nodes, if exactly one candidate passes `branch_min_policy` AND its policy prior exceeds `forced_move_policy_threshold` (default 0.85), use `forced_move_visits` (default 125) instead of full `effective_visits` (500+).

**Paper reference:** §4.2 — forced moves reduce branching factor.

**Invariants:**

- Only at player nodes, not opponent nodes.
- Still queries the engine — just with reduced visits.
- Safety net: if forced-move winrate delta > `t_good`, re-queries at full visits.
- `forced_move_count` tracked in `TreeCompletenessMetrics`.

### DD-KM4: Proof-Depth Difficulty Signal

**Decision:** After tree build, compute `max_resolved_depth` (deepest non-truncated branch). Add as sub-signal in structural difficulty component via `StructuralDifficultyWeights.proof_depth` (weight 10/100), normalized by `max_resolved_depth_ceiling`.

**Paper reference:** §4.2 — heuristic initialization uses minimum defender moves as difficulty proxy.

**Invariants:**

- Zero additional engine cost (derived from tree data).
- Only populated for `ac:2` puzzles. For `ac:1`, signal is 0.
- Weight sum rebalanced: `solution_depth:35 + branch_count:22 + local_candidates:18 + refutation_count:15 + proof_depth:10 = 100`.

### DD-L3: Depth-Dependent Policy Threshold (Thomsen Lambda-Search)

**Decision:** Replace flat `branch_min_policy` filter with depth-dependent formula: `effective_min_policy = branch_min_policy + depth_policy_scale * depth`. Deeper opponent nodes require higher policy priors to be explored.

**Paper reference:** Thomsen (2000) — Lambda search: moves at deeper tree levels must be more forcing.

**Invariants:**

- Only tightens with depth — never goes below `branch_min_policy`.
- Only applies at opponent nodes.
- `depth_policy_scale = 0.0` reverts to flat behavior.
- `branches_pruned_by_depth_policy` tracked in `TreeCompletenessMetrics`.

---

## Deferred Techniques

| ID    | Technique                              | Paper Section | Reason Deferred                                                                                                                                        |
| ----- | -------------------------------------- | ------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| KM-05 | Relevance Zone Refinement (flood-fill) | §2            | Current tight-board cropping + tsumego frame + policy filtering already achieves the paper's "enclosed region" intent. Marginal gain, regression risk. |
| KM-06 | Non-Uniform Budget Allocation          | §4.2          | Paper's df-pn threshold mechanism doesn't transfer to KataGo-oracle architecture. Partially addressed by DD-L3.                                        |
| KM-07 | Ko Re-Search                           | §4.3          | Redundant when using KataGo's MCTS which handles ko via Tromp-Taylor rules. Current `ko_validation.py` + `YK` property suffice.                        |

---

## Review Panel Consultation Record

| Member                | Key Guidance                                                                                                                                                                                                                                             |
| --------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Cho Chikun** (9p)   | "In tsumego, 80% of wrong answers fail for the same reason." (supports simulation). "Forced moves are the backbone of tsumego." "The first opponent response can be surprising [at shallow depth], but five moves deep, the comparison should be local." |
| **Shin Jinseo** (9p)  | "KataGo's policy already concentrates >90% on forced moves. 125 visits is enough." (supports forced move fast-path)                                                                                                                                      |
| **Kishimoto** (proxy) | "Simulation was our biggest performance win. The key: simulation must be _verified_, not assumed." Endorsed Zobrist hashing as the standard Go pattern.                                                                                                  |
| **Engineer A**        | Config-driven design: all features gated by config flags with safe defaults.                                                                                                                                                                             |
| **Engineer B**        | "Estimated 30-50% budget reduction. Highly measurable via counters."                                                                                                                                                                                     |

### 1. Board-State Hashing (Phase 3 — KM-02)

**Decision:** Replaced simplified `frozenset(moves)` hash with proper Zobrist hashing via `_BoardState` class.

**Trade-off Considered:**

| Option                                          | Pro                                                       | Con                                                | Panel Verdict                        |
| ----------------------------------------------- | --------------------------------------------------------- | -------------------------------------------------- | ------------------------------------ |
| `frozenset(moves)` — move-set hash              | O(1), zero complexity                                     | False positives with captures, no ko detection     | REJECTED (Cho Chikun, Kishimoto)     |
| `hash(frozenset((color,row,col)))` — scan-based | Correct stone positions, captures resolved                | O(n) per hash where n=board_size²                  | REVIEWED — sufficient for 50 queries |
| Zobrist hashing — incremental XOR               | O(1) incremental, standard for Go programs, deterministic | 722 pre-generated random values, class-level state | **APPROVED** (Kishimoto, all)        |

**Why Zobrist:** Kishimoto's paper (AAAI-05 §3, §6) uses transposition tables extensively with Zobrist hashing. Even though our 50-query budget makes the O(361) scan negligible, the Review Panel decided to follow the paper's standard technique because (a) it's the correct Go programming pattern, (b) deterministic seed (42) ensures reproducibility, (c) incremental XOR naturally tracks captures.

**Source papers:** Zobrist, A. (1970). "A New Hashing Method with Application for Game Playing." TR-88, CS Dept, U. Wisconsin.

### 2. Capture Resolution

**Decision:** `_BoardState` implements flood-fill liberty counting for capture resolution.

**Feature coverage:**

- Standard captures (group with 0 liberties removed) ✓
- Snapback (consecutive captures) ✓ — tested
- Simple ko detection (last single-stone capture tracked) ✓
- Double ko (different stone configurations hash differently) ✓ — tested
- NOT implemented: superko (full-board history required) — delegated to KataGo's rules engine

### 3. Simulation Verification Depth (Phase 4 — KM-01)

**Decision:** Verify FULL cached sequence, not just first reply.

**Trade-off:**

| Option               | Pro                                      | Con                                                | Panel Verdict        |
| -------------------- | ---------------------------------------- | -------------------------------------------------- | -------------------- |
| First reply only     | 1 query, minimal budget cost             | Partial verification — deep errors missed          | REJECTED (Kishimoto) |
| Full sequence replay | Faithful to paper's simulation technique | Same budget cost (1 query) but more moves replayed | **APPROVED**         |

**Why full sequence:** Kishimoto's paper (§4.2): "A successful simulation requires much less effort than a normal search, since even with good move ordering, a newly created search tree is typically much larger than an existing proof tree." Replaying the full sequence costs the SAME budget (1 query) — the sequence is the move list sent to KataGo. The winrate at the endpoint reflects the full continuation.

### 4. Winrate Reference for Simulation (Phase 4)

**Decision:** Depth-dependent reference: root_winrate at depth 1-2, local (first sibling) winrate at depth ≥3.

**Trade-off:**

| Option                | Shallow depth behavior                                  | Deep position behavior                                 | Panel Verdict         |
| --------------------- | ------------------------------------------------------- | ------------------------------------------------------ | --------------------- |
| Always root_winrate   | Correct (root is relevant)                              | False rejections (root irrelevant for seki at depth 5) | REJECTED (Cho Chikun) |
| Always local_winrate  | Risk of masking errors if first sibling is anomalous    | Correct local comparison                               | REJECTED (Cho Chikun) |
| Depth-dependent guard | Root WR at 1-2 (where it's still relevant), local at ≥3 | Correct in both cases                                  | **APPROVED**          |

**Why depth guard:** Cho Chikun: "The first opponent response can be surprising [at shallow depth], but five moves deep, the comparison should be local." At depth 1-2, root_winrate and local winrate are typically within t_good=0.05 of each other. At depth ≥3, positions may diverge significantly (seki, ko fights).

### 5. Forced-Move Safety Net (Phase 5 — KM-03)

**Decision:** Implement re-query at full visits when reduced-visit result disagrees.

**Mechanism:** After building forced-move child at 125 visits, check `abs(root_winrate - child.winrate) > t_good`. If true AND budget allows, re-build at full visits.

**Paper comparison:** Kishimoto skips search entirely for forced moves. Our approach is MORE conservative — we still query at 125 visits, and fall back to 500 if results diverge. This is appropriate for the KataGo-oracle architecture where each query produces a global evaluation.

---

## Config Parameters

| Parameter                      | Type  | Default | Location                 |
| ------------------------------ | ----- | ------- | ------------------------ |
| `simulation_enabled`           | bool  | `true`  | `ai_solve.solution_tree` |
| `simulation_verify_visits`     | int   | 50      | `ai_solve.solution_tree` |
| `transposition_enabled`        | bool  | `true`  | `ai_solve.solution_tree` |
| `forced_move_visits`           | int   | 125     | `ai_solve.solution_tree` |
| `forced_move_policy_threshold` | float | 0.85    | `ai_solve.solution_tree` |
| `depth_policy_scale`           | float | 0.01    | `ai_solve.solution_tree` |

---

## Metrics Tracked

| Counter                           | Model                     | Description                              |
| --------------------------------- | ------------------------- | ---------------------------------------- |
| `simulation_hits`                 | `TreeCompletenessMetrics` | Sibling branches resolved via simulation |
| `simulation_misses`               | `TreeCompletenessMetrics` | Simulation verification failures         |
| `transposition_hits`              | `TreeCompletenessMetrics` | Position cache hits                      |
| `forced_move_count`               | `TreeCompletenessMetrics` | Forced-move fast-path activations        |
| `max_resolved_depth`              | `TreeCompletenessMetrics` | Deepest non-truncated branch             |
| `branches_pruned_by_depth_policy` | `TreeCompletenessMetrics` | L3 depth-policy pruning                  |

---

## References

- Kishimoto, A. & Müller, M. (2005). _Search versus Knowledge for Solving Life and Death Problems in Go._ AAAI-05, pp. 1374–1379.
- Thomsen, T. (2000). _Lambda-Search in Game Trees — with Application to Go._ ICGA Journal, 23(4), pp. 203–217.

> **See also:**
>
> - [Architecture: KataGo Enrichment](../../docs/architecture/tools/katago-enrichment.md) — full design decisions
> - [How-To: Enrichment Lab](../../docs/how-to/tools/katago-enrichment-lab.md) — config usage guide
> - [Reference: Enrichment Config](../../docs/reference/enrichment-config.md) — config field reference
> - [Plan: KM Search Optimizations](../kishimoto-mueller-search-optimizations.md) — implementation plan
