# Research Brief: Refutation Generation & Tree Building — Implementation State

> **Research question**: What is the current implementation state of refutation generation and tree building in `tools/puzzle-enrichment-lab/`, and what concrete hooks exist for the proposed improvements in `starter.md`?
>
> **Boundaries**: Code evidence only. No code changes. Map every finding to file paths, line numbers, function names, and config keys.
>
> **Last updated**: 2026-03-15

---

## 1. Refutation Generation

### 1.1 Source Files

| File | Role |
|------|------|
| [analyzers/generate_refutations.py](../../../tools/puzzle-enrichment-lab/analyzers/generate_refutations.py) | Orchestrator: candidate identification + per-candidate refutation generation |
| [config/refutations.py](../../../tools/puzzle-enrichment-lab/config/refutations.py) | Pydantic models: `RefutationsConfig`, `CandidateScoringConfig`, `RefutationOverridesConfig`, `TenukiRejectionConfig`, `SuboptimalBranchesConfig`, `RefutationEscalationConfig` |
| [analyzers/stages/refutation_stage.py](../../../tools/puzzle-enrichment-lab/analyzers/stages/refutation_stage.py) | Pipeline stage wrapper calling `generate_refutations()` |
| [models/refutation_result.py](../../../tools/puzzle-enrichment-lab/models/refutation_result.py) | `RefutationResult`, `Refutation` data models |

### 1.2 Candidate Scoring

| R-ID | Aspect | Current Behavior | Location |
|------|--------|-----------------|----------|
| R-1 | **Scoring mode** | Temperature-weighted: `score = policy * exp(-temperature * max(0, points_lost))`. Config: `refutations.candidate_scoring.mode = "temperature"`, `temperature = 1.5` | [generate_refutations.py](../../../tools/puzzle-enrichment-lab/analyzers/generate_refutations.py#L130-L143) `identify_candidates()` |
| R-2 | **Policy floor** | `candidate_min_policy = 0.0` — no policy floor, accepts all candidates | [config/katago-enrichment.json](../../../config/katago-enrichment.json) `refutations.candidate_min_policy` |
| R-3 | **Candidate cap** | `candidate_max_count = 5` — top 5 after scoring | [config/katago-enrichment.json](../../../config/katago-enrichment.json) `refutations.candidate_max_count` |
| R-4 | **Spatial filter** | Chebyshev distance filter via `nearby_moves` param + `locality_max_distance = 2` | [generate_refutations.py](../../../tools/puzzle-enrichment-lab/analyzers/generate_refutations.py#L106-L122) |
| R-5 | **Winrate delta** | `delta_threshold = 0.08` — primary accept/reject signal | [generate_refutations.py](../../../tools/puzzle-enrichment-lab/analyzers/generate_refutations.py#L265-L295) `generate_single_refutation()` |
| R-6 | **Score delta fallback** | Score-based fallback when `abs(winrate_delta) < delta_threshold` but `abs(score_delta) >= suboptimal_branches.score_delta_threshold (2.0)` | [generate_refutations.py](../../../tools/puzzle-enrichment-lab/analyzers/generate_refutations.py#L280-L293) |
| R-7 | **Ownership delta** | **NOT used for scoring.** `include_ownership=True` is set in the refutation query but ownership data is NOT examined for candidate ranking or accept/reject decisions. | [generate_refutations.py](../../../tools/puzzle-enrichment-lab/analyzers/generate_refutations.py#L248) (request includes it), nowhere consumed for scoring |
| R-8 | **Curated enrichment** | `_enrich_curated_policy()` back-fills policy, winrate, and score data onto curated (SGF-sourced) wrong branches from the initial KataGo analysis. Used for trap_density computation. | [generate_refutations.py](../../../tools/puzzle-enrichment-lab/analyzers/generate_refutations.py#L40-L93) |

**Key gap (F-3 from starter.md)**: Ownership delta is requested but never used for refutation scoring. The `_get_ownership()` helper exists in `solve_position.py` but exclusively serves tree stopping conditions.

### 1.3 Visit Allocation

| R-ID | Aspect | Current Behavior | Location |
|------|--------|-----------------|----------|
| R-9 | **Per-candidate visits** | Fixed: `refutation_visits = 100` for every candidate | [config/katago-enrichment.json](../../../config/katago-enrichment.json) `refutations.refutation_visits` |
| R-10 | **Escalation visits** | `escalation_visits = 500` when 0 refutations on first pass; relaxed `escalation_delta_threshold = 0.03` | [config/katago-enrichment.json](../../../config/katago-enrichment.json) `refutation_escalation.*` |
| R-11 | **No adaptive allocation** | All candidates receive the same `refutation_visits` regardless of their ambiguity, policy, or position complexity. No per-candidate visit adjustment. | [generate_refutations.py](../../../tools/puzzle-enrichment-lab/analyzers/generate_refutations.py#L232) — `refutation_visits` used as-is |

**Key gap (F-1 from starter.md)**: No multi-budget or adaptive visit schedule. Every candidate gets 100 visits regardless of ambiguity signal.

### 1.4 Forced Minimum Visits per Candidate

| R-ID | Aspect | Current Behavior | Location |
|------|--------|-----------------|----------|
| R-12 | **Forced min visits** | **NOT implemented.** No `nforced(c) = (kP(c) * sum)^0.5` formula. All candidates pass through the same pipeline at `refutation_visits`. | N/A — gap |
| R-13 | **Root FPU** | `root_fpu_reduction_max = 0` (no penalty for unexplored moves at root during refutation queries). Correctly configured per paper. | [config/katago-enrichment.json](../../../config/katago-enrichment.json) `refutations.refutation_overrides.root_fpu_reduction_max` |

**Key gap (F-2 from starter.md)**: The FPU reduction is correct, but the forced-playout formula from the paper is absent. Low-policy vital moves may be under-explored.

### 1.5 Candidate Diversity Mechanisms

| R-ID | Aspect | Current Behavior | Location |
|------|--------|-----------------|----------|
| R-14 | **Root policy temperature** | `root_policy_temperature = 1.3` — softens root policy for more diverse exploration | [config/katago-enrichment.json](../../../config/katago-enrichment.json) `refutations.refutation_overrides.root_policy_temperature` |
| R-15 | **Wide root noise** | Fixed `wide_root_noise = 0.08` — NOT board-size-scaled | [config/katago-enrichment.json](../../../config/katago-enrichment.json) `refutations.refutation_overrides.wide_root_noise` |
| R-16 | **Symmetry sampling** | `root_num_symmetries_to_sample = 4` (deep_enrich default), `referee_symmetries = 8` | [config/katago-enrichment.json](../../../config/katago-enrichment.json) `deep_enrich.*` |
| R-17 | **Score-based temperature** | Temperature scoring (`exp(-1.5 * points_lost)`) diversifies candidate ranking beyond pure policy | [generate_refutations.py](../../../tools/puzzle-enrichment-lab/analyzers/generate_refutations.py#L130-L143) |
| R-18 | **Tenuki rejection** | Rejects refutations where PV response Manhattan distance > 4.0 from wrong move | [generate_refutations.py](../../../tools/puzzle-enrichment-lab/analyzers/generate_refutations.py#L324-L340) |
| R-19 | **Single initial scan** | Candidate harvesting comes from ONE initial KataGo analysis. No multi-pass or diversified scanning. | [generate_refutations.py](../../../tools/puzzle-enrichment-lab/analyzers/generate_refutations.py#L395-L405) |

**Key gap (F-4/F-5 from starter.md)**: Noise is fixed 0.08 regardless of board size. Single scan limits discovery of hidden wrong moves.

### 1.6 Extension Points for Proposed Changes

| Hook | Description | Where |
|------|-------------|-------|
| `override_settings` parameter | Per-query KataGo config overrides already wired through `generate_single_refutation()` → `AnalysisRequest` | `generate_refutations.py` L248-250 |
| `allowed_moves` parameter | Puzzle region restriction passed to refutation queries | `generate_refutations.py` L497-L507 |
| `refutation_overrides` config section | Dedicated config for per-query engine overrides | `config/refutations.py` `RefutationOverridesConfig` |
| `suboptimal_branches` config section | Feature-gated score-delta branch generation (disabled by default) | `config/refutations.py` `SuboptimalBranchesConfig` |
| `RefutationEscalationConfig` | Retry logic with relaxed thresholds when 0 refutations found | `config/refutations.py` |

---

## 2. Tree Building

### 2.1 Source Files

| File | Role |
|------|------|
| [analyzers/solve_position.py](../../../tools/puzzle-enrichment-lab/analyzers/solve_position.py) | `build_solution_tree()`, `_build_tree_recursive()`, `analyze_position_candidates()`, `SyncEngineAdapter`, `_BoardState` (Zobrist hashing) |
| [config/solution_tree.py](../../../tools/puzzle-enrichment-lab/config/solution_tree.py) | `SolutionTreeConfig`, `DepthProfile`, `BensonGateConfig`, `AiSolveSekiDetectionConfig`, `AiSolveGoalInference`, `EdgeCaseBoosts` |
| [models/solve_result.py](../../../tools/puzzle-enrichment-lab/models/solve_result.py) | `SolutionNode`, `TreeCompletenessMetrics`, `QueryBudget`, `MoveClassification`, `MoveQuality`, `PositionAnalysis` |

### 2.2 Recursive Tree Builder

| R-ID | Aspect | Current Behavior | Location |
|------|--------|-----------------|----------|
| R-20 | **Entry point** | `build_solution_tree()` — sets up depth profile, edge-case visit boosts, transposition cache, board state, then calls `_build_tree_recursive()` | [solve_position.py](../../../tools/puzzle-enrichment-lab/analyzers/solve_position.py#L876-L1003) |
| R-21 | **Recursive core** | `_build_tree_recursive()` — single function handling both player and opponent nodes via `is_player_turn` flag | [solve_position.py](../../../tools/puzzle-enrichment-lab/analyzers/solve_position.py#L1005-L1198) |
| R-22 | **6 stopping conditions** | (1) Winrate stability `wr_epsilon=0.02`, (2) Ownership convergence `own_epsilon=0.05`, (3) Seki band for `seki_consecutive_depth=3` plies, (4) Hard cap `solution_max_depth`, (5) Budget exhausted `max_total_tree_queries=50`, (6) Pass in PV or no legal moves | [solve_position.py](../../../tools/puzzle-enrichment-lab/analyzers/solve_position.py#L1127-L1198) |
| R-23 | **Minimum floor** | `solution_min_depth` from category profile (entry=2, core=3, strong=4). Stopping conditions 1-3 suppressed before min_depth reached. | `config.ai_solve.solution_tree.depth_profiles` |

### 2.3 Visit Allocation per Node

| R-ID | Aspect | Current Behavior | Location |
|------|--------|-----------------|----------|
| R-24 | **Base visits** | Fixed `tree_visits = 500` for all tree nodes | [config/katago-enrichment.json](../../../config/katago-enrichment.json) `ai_solve.solution_tree.tree_visits` |
| R-25 | **Corner boost** | `corner_visit_boost = 1.5×` when puzzle has TL/TR/BL/BR position → 750 visits | [solve_position.py](../../../tools/puzzle-enrichment-lab/analyzers/solve_position.py#L936-L942) |
| R-26 | **Ladder boost** | `ladder_visit_boost = 2.0×` when PV > 8 moves → 1000 visits | [solve_position.py](../../../tools/puzzle-enrichment-lab/analyzers/solve_position.py#L945-L953) |
| R-27 | **Forced-move fast-path (KM-03)** | `forced_move_visits = 125` when single candidate has `policy > 0.85` (forced). Safety net re-queries at full visits if child disagrees with root. | [solve_position.py](../../../tools/puzzle-enrichment-lab/analyzers/solve_position.py#L1203-L1240) |
| R-28 | **No depth-adaptive allocation** | `effective_visits` is constant for ALL non-forced nodes at all depths. Branch decision points and continuation nodes get identical visits. | [solve_position.py](../../../tools/puzzle-enrichment-lab/analyzers/solve_position.py#L1361) — same `effective_visits` passed recursively |

**Key gap (F-1 from starter.md)**: No `visit_allocation_mode: "adaptive"`. All nodes except forced moves get the same `tree_visits=500`. No `branch_visits` vs `continuation_visits` split.

### 2.4 Player-Side Alternative Exploration

| R-ID | Aspect | Current Behavior | Location |
|------|--------|-----------------|----------|
| R-29 | **Player node logic** | Always takes the SINGLE best move (`move_infos[0]`). No branching at player nodes. | [solve_position.py](../../../tools/puzzle-enrichment-lab/analyzers/solve_position.py#L1200-L1292) — `if is_player_turn: ... child = _build_tree_recursive(...)` with only best move |
| R-30 | **No alternative rate** | No `player_alternative_rate` config. No probability-based exploration of second-best player moves. | N/A — gap |

**Key gap (F-7 from starter.md)**: Player nodes never branch. The entire "trick move discovery" is absent. Cho Chikun governance: should default to off (`rate=0.0`).

### 2.5 Opponent-Side Branching

| R-ID | Aspect | Current Behavior | Location |
|------|--------|-----------------|----------|
| R-31 | **Max branch width** | `max_branch_width = 3` — up to 3 opponent responses per node | `config.ai_solve.solution_tree.max_branch_width` |
| R-32 | **Policy threshold (L3)** | Depth-dependent: `effective_min_policy = branch_min_policy (0.05) + depth_policy_scale (0.01) * depth`. Pruned branches tracked in `completeness.branches_pruned_by_depth_policy`. | [solve_position.py](../../../tools/puzzle-enrichment-lab/analyzers/solve_position.py#L1329-L1340) |
| R-33 | **Confirmation queries (S1-G16)** | Per-candidate queries at `confirmation_visits = 500` for precise delta, in `analyze_position_candidates()` (initial position scan, not tree). | [solve_position.py](../../../tools/puzzle-enrichment-lab/analyzers/solve_position.py#L235-L270) |

### 2.6 Ownership Convergence as Stopping Condition

| R-ID | Aspect | Current Behavior | Location |
|------|--------|-----------------|----------|
| R-34 | **Ownership extraction** | `_get_ownership(analysis)` returns ownership map from top move's analysis | [solve_position.py](../../../tools/puzzle-enrichment-lab/analyzers/solve_position.py#L411-L421) |
| R-35 | **Convergence check** | `_check_ownership_convergence()` compares key stones (|ownership| > 0.3) between consecutive depths. Stops if `max_change < own_epsilon (0.05)`. | [solve_position.py](../../../tools/puzzle-enrichment-lab/analyzers/solve_position.py#L1449-L1479) |
| R-36 | **Only a tree stopping condition** | Ownership convergence ONLY stops tree expansion. NOT used for branch acceptance/rejection, candidate ranking, or refutation quality scoring. | Confirmed by code audit: `_check_ownership_convergence()` called only in `_build_tree_recursive()` stopping condition block |

### 2.7 Search Optimizations (Kishimoto-Mueller)

| R-ID | Feature | Config Key | Status | Location |
|------|---------|-----------|--------|----------|
| R-37 | **KM-01 Kawano simulation** | `simulation_enabled = true`, `simulation_verify_visits = 50` | Implemented. Replays cached player reply from proven sibling. | [solve_position.py](../../../tools/puzzle-enrichment-lab/analyzers/solve_position.py#L790-L868) `_try_simulation()` |
| R-38 | **KM-02 Transposition table** | `transposition_enabled = true` | Implemented. Zobrist hashing via `_BoardState`. | [solve_position.py](../../../tools/puzzle-enrichment-lab/analyzers/solve_position.py#L555-L735) `_BoardState` class |
| R-39 | **KM-03 Forced-move fast-path** | `forced_move_visits = 125`, `forced_move_policy_threshold = 0.85` | Implemented with safety net re-query. | [solve_position.py](../../../tools/puzzle-enrichment-lab/analyzers/solve_position.py#L1205-L1240) |
| R-40 | **KM-04 Proof depth signal** | `max_resolved_depth` computed post-build | Implemented. `_compute_max_resolved_depth()` | [solve_position.py](../../../tools/puzzle-enrichment-lab/analyzers/solve_position.py#L1468-L1491) |
| R-41 | **Terminal detection (Benson G1 + Interior G2)** | `terminal_detection_enabled = true`, `benson_gate.enabled = true`, `benson_gate.min_contest_stones = 1` | Implemented. Pre-query gate using `benson_check.py`. | [solve_position.py](../../../tools/puzzle-enrichment-lab/analyzers/solve_position.py#L1072-L1124) |

---

## 3. Config — Complete Key Inventory

### 3.1 `refutations` Section

| Key | Type | Value | Purpose |
|-----|------|-------|---------|
| `candidate_min_policy` | float | `0.0` | Min policy prior for candidate wrong moves |
| `candidate_max_count` | int | `5` | Max candidates to evaluate |
| `refutation_max_count` | int | `3` | Max refutations to keep |
| `delta_threshold` | float | `0.08` | Min winrate delta to accept refutation |
| `refutation_visits` | int | `100` | Fixed visits per refutation query |
| `locality_max_distance` | int | `2` | Chebyshev distance filter |
| `max_pv_length` | int | `4` | Max moves in refutation PV |
| `pv_mode` | str | `"multi_query"` | Per-candidate query mode |
| `pv_extract_min_depth` | int | `3` | Min PV depth for pv_extract mode |
| `pv_quality_min_visits` | int | `50` | Min visits for PV trust |
| `candidate_scoring.mode` | str | `"temperature"` | Scoring algorithm |
| `candidate_scoring.temperature` | float | `1.5` | Temperature scalar |
| `refutation_overrides.root_policy_temperature` | float | `1.3` | Root policy softening |
| `refutation_overrides.root_fpu_reduction_max` | float | `0.0` | No FPU penalty |
| `refutation_overrides.wide_root_noise` | float | `0.08` | Exploration noise (fixed) |
| `tenuki_rejection.enabled` | bool | `true` | Tenuki rejection active |
| `tenuki_rejection.manhattan_threshold` | float | `4.0` | Max distance for valid refutation |
| `suboptimal_branches.enabled` | bool | `true` | Score-delta fallback active |
| `suboptimal_branches.score_delta_threshold` | float | `2.0` | Score points lost threshold |
| `suboptimal_branches.max_branches` | int | `3` | Max suboptimal branches |
| `suboptimal_branches.max_pv_depth` | int | `8` | PV depth for suboptimal |
| `suboptimal_branches.min_policy` | float | `0.01` | Min policy for suboptimal |
| `suboptimal_branches.visits` | int | `200` | Visits for suboptimal analysis |

### 3.2 `refutation_escalation` Section

| Key | Type | Value | Purpose |
|-----|------|-------|---------|
| `enabled` | bool | `true` | Retry when 0 refutations |
| `min_refutations_required` | int | `1` | Threshold to trigger escalation |
| `escalation_visits` | int | `500` | Higher visits for retry |
| `escalation_delta_threshold` | float | `0.03` | Relaxed delta |
| `escalation_candidate_min_policy` | float | `0.003` | Relaxed policy floor |
| `use_referee_engine` | bool | `true` | Use b28 for escalation |
| `max_escalation_attempts` | int | `1` | Max retries |

### 3.3 `ai_solve.solution_tree` Section

| Key | Type | Value | Purpose |
|-----|------|-------|---------|
| `depth_profiles.entry` | obj | `{min:2, max:10}` | Novice-Elementary depth |
| `depth_profiles.core` | obj | `{min:3, max:16}` | Intermediate-Advanced depth |
| `depth_profiles.strong` | obj | `{min:4, max:28}` | Dan-Expert depth |
| `wr_epsilon` | float | `0.02` | Winrate stability threshold |
| `own_epsilon` | float | `0.05` | Ownership convergence threshold |
| `branch_min_policy` | float | `0.05` | Base min policy for opponent branches |
| `depth_policy_scale` | float | `0.01` | Per-depth policy increment (L3) |
| `max_branch_width` | int | `3` | Max opponent branches per node |
| `max_total_tree_queries` | int | `50` | Global query budget |
| `confirmation_min_policy` | float | `0.03` | Pre-filter for candidate moves |
| `confirmation_visits` | int | `500` | Per-candidate confirmation queries |
| `tree_visits` | int | `500` | MCTS visits per tree node |
| `max_correct_root_trees` | int | `2` | Max correct first-move roots |
| `max_refutation_root_trees` | int | `3` | Max wrong first-move roots |
| `simulation_enabled` | bool | `true` | KM-01 Kawano simulation |
| `simulation_verify_visits` | int | `50` | Simulation verification visits |
| `forced_move_visits` | int | `125` | KM-03 forced-move visits |
| `forced_move_policy_threshold` | float | `0.85` | KM-03 forced-move policy gate |
| `transposition_enabled` | bool | `true` | KM-02 position cache |
| `terminal_detection_enabled` | bool | `true` | Benson + interior-point gates |
| `benson_gate.enabled` | bool | `true` | Benson gate master switch |
| `benson_gate.min_contest_stones` | int | `1` | Min stones for Benson check |

### 3.4 `ai_solve.seki_detection` Section

| Key | Type | Value | Purpose |
|-----|------|-------|---------|
| `winrate_band_low` | float | `0.45` | Lower seki band |
| `winrate_band_high` | float | `0.55` | Upper seki band |
| `seki_consecutive_depth` | int | `3` | Plies in band before exit |
| `score_lead_seki_max` | float | `2.0` | Max score lead for seki |

### 3.5 `ko_analysis` Section

| Key | Type | Value | Purpose |
|-----|------|-------|---------|
| `rules_by_ko_type.none` | str | `"chinese"` | Standard superko |
| `rules_by_ko_type.direct` | str | `"tromp-taylor"` | Simple ko for ko puzzles |
| `rules_by_ko_type.approach` | str | `"tromp-taylor"` | Simple ko for approach ko |
| `pv_len_by_ko_type.none` | int | `15` | Standard PV length |
| `pv_len_by_ko_type.direct` | int | `30` | Extended PV for ko |
| `pv_len_by_ko_type.approach` | int | `30` | Extended PV for approach ko |

### 3.6 Model Definitions

| Label | Arch | Usage |
|-------|------|-------|
| `quick` | b18c384 | Standard analysis |
| `referee` | b28c512 | Escalation / disagreement resolution |
| `deep_enrich` | b18c384 | Lab-mode enrichment (2K visits) |
| `test_fast` | b10c128 | Fast integration tests |
| `test_smallest` | b6c96 | Smoke tests |
| `benchmark` | b15c192 | Performance comparison |

**Key gap (F-9)**: No model routing by level category. `deep_enrich.model = "b18c384"` is used for ALL puzzles.

---

## 4. Query Builder

### 4.1 Source File

[analyzers/query_builder.py](../../../tools/puzzle-enrichment-lab/analyzers/query_builder.py)

### 4.2 Ownership Data

| R-ID | Aspect | Current Behavior | Location |
|------|--------|-----------------|----------|
| R-42 | **`include_ownership`** | Always `True` in `build_query_from_sgf()` and `build_query_from_position()` | [query_builder.py](../../../tools/puzzle-enrichment-lab/analyzers/query_builder.py#L229) / [query_builder.py](../../../tools/puzzle-enrichment-lab/analyzers/query_builder.py#L316) |
| R-43 | **`include_pv`** | Always `True` | Same locations |
| R-44 | **`include_policy`** | Always `True` in both query builders | Same locations |
| R-45 | **Ownership consumed by** | `_get_ownership()` in `solve_position.py` for tree stopping only. Not used in refutation scoring. | [solve_position.py](../../../tools/puzzle-enrichment-lab/analyzers/solve_position.py#L411-L421) |

### 4.3 Score-Lead Data

| R-ID | Aspect | Current Behavior | Location |
|------|--------|-----------------|----------|
| R-46 | **Score in classification** | `classify_move_quality()` accepts `score_lead` param but does NOT use it in classification logic — "Available for downstream consumers but not used in classification." | [solve_position.py](../../../tools/puzzle-enrichment-lab/analyzers/solve_position.py#L87-L115) |
| R-47 | **Score in refutation** | Score delta used as fallback signal in `generate_single_refutation()` when winrate delta below threshold AND `suboptimal_branches.enabled = true`. | [generate_refutations.py](../../../tools/puzzle-enrichment-lab/analyzers/generate_refutations.py#L280-L293) |
| R-48 | **Score in difficulty** | `score_normalization_cap = 30.0` and `trap_density_floor = 0.05` in difficulty section for score-based trap density. | [config/katago-enrichment.json](../../../config/katago-enrichment.json) `difficulty.score_normalization_cap` |

### 4.4 Noise Configuration

| R-ID | Aspect | Current Behavior | Location |
|------|--------|-----------------|----------|
| R-49 | **Root noise** | Fixed `wide_root_noise = 0.08` per-query override for refutation queries only | [config/katago-enrichment.json](../../../config/katago-enrichment.json) `refutations.refutation_overrides.wide_root_noise` |
| R-50 | **Symmetry sampling** | `root_num_symmetries_to_sample = 4` default, `referee_symmetries = 8`. Wired via `override_settings` dict in `AnalysisRequest`. | [query_builder.py](../../../tools/puzzle-enrichment-lab/analyzers/query_builder.py#L220-L228) |
| R-51 | **No board-size scaling** | Noise is fixed. No formula `noise = base * reference_area / legal_moves`. | Config gap: no `noise_scaling`, `noise_base`, or `noise_reference_area` keys |
| R-52 | **Tsumego query preparation** | `prepare_tsumego_query()` is the single source of truth: komi=0, apply frame, compute region, resolve ko rules. Pure function. | [query_builder.py](../../../tools/puzzle-enrichment-lab/analyzers/query_builder.py#L61-L116) |

---

## 5. AGENTS.md Architecture Map

[AGENTS.md](../../../tools/puzzle-enrichment-lab/AGENTS.md) — 400+ lines, last updated 2026-03-14.

### Key Architecture Facts

| R-ID | Fact | Evidence |
|------|------|---------|
| R-53 | **Pipeline is stage-based** | `StageRunner.run_pipeline()` → ordered `EnrichmentStage` list. 11 stages from parse to sgf_writeback. |
| R-54 | **Engine is injected, never imported** | `PipelineContext.engine_manager` is the only engine reference. Stages call `engine_manager.analyze(request)`. |
| R-55 | **3 solve paths** | `run_position_only_path()`, `run_has_solution_path()`, `run_standard_path()` dispatched by `SolvePathStage` |
| R-56 | **Config package decomposed** | 8 sub-modules: `difficulty.py`, `refutations.py`, `technique.py`, `solution_tree.py`, `ai_solve.py`, `teaching.py`, `analysis.py`, `infrastructure.py` |
| R-57 | **28 technique detectors** | One per tag in `config/tags.json`. All inherit `TechniqueDetector`, purely board-based (no engine access). |
| R-58 | **Coordinate boundary** | GTP coords in KataGo comms, SGF coords in read/write. Conversion in `query_builder.py`. No cropping — original board size. |
| R-59 | **SyncEngineAdapter bridges async/sync** | Tree builder is synchronous; engine is async. Adapter uses `asyncio.run()` with `ThreadPoolExecutor` fallback. |

---

## 6. Planner Recommendations

1. **Ownership delta for refutation quality (F-3/P0)** — Lowest effort, highest signal gain. All infrastructure exists: `include_ownership=True` already set, `_get_ownership()` helper exists. Add a new config key `refutations.ownership_delta_weight: 0.0` and ~50 LOC in `generate_single_refutation()` to compare pre/post-wrong-move ownership of contested stones. Feature-gated via weight=0.0 default.

2. **Adaptive visit allocation per tree depth (F-1/P1)** — The tree builder already has distinct code paths for player vs opponent nodes and KM-03 forced-move fast-path. Add `visit_allocation_mode: "fixed" | "adaptive"` and `branch_visits`/`continuation_visits` to `SolutionTreeConfig`. Modify `_build_tree_recursive()` to select visits based on `is_player_turn` and depth. Backward-compatible: `"fixed"` uses current `tree_visits=500`.

3. **Board-size-scaled noise (F-5/P2)** — Pure config change with minimal algorithm work. Add `noise_scaling: "fixed" | "board_scaled"`, `noise_base: 0.03`, `noise_reference_area: 361` to `RefutationOverridesConfig`. Modify `generate_refutations()` to compute `noise = noise_base * 361 / legal_move_count` when `noise_scaling="board_scaled"`. Wired through existing `override_settings` mechanism.

4. **Model routing by level category (F-9/P0)** — Config-first change. Add `model_by_category: {entry: "test_fast", core: "quick", strong: "referee"}` to `ai_solve` section. Wire in `SolvePathStage` or `AnalyzeStage` to select model based on `get_level_category(level_slug)`. Requires a regression test proving b10 produces identical `is_correct` for entry-level puzzles.

---

## 7. Confidence & Risk

| Metric | Value |
|--------|-------|
| **Post-research confidence** | 92/100 — All five requested areas fully audited with line-level citations. Config surface is well-documented. |
| **Risk level** | **Low** — All proposed changes are additive, feature-gated, and rely on existing infrastructure (ownership data, score data, override_settings, config models). No architectural changes needed. |
| **Internal references** | 58 (R-1 through R-59) |
| **External references** | Covered via starter.md governance panel analysis (KaTrain MIT-licensed patterns, KataGo PR #261, Kishimoto-Mueller paper). |

### Open Questions

| q_id | question | options | recommended | user_response | status |
|------|----------|---------|-------------|---------------|--------|
| Q1 | Which finding should be the first implementation sprint? | A: F-3 ownership delta / B: F-1 adaptive visits / C: F-9 model routing / D: All three in parallel | A (F-3) — lowest risk, highest signal gain | | ❌ pending |
| Q2 | Should the research extend to the refutation stage wrapper (`refutation_stage.py`) and escalation retry logic? | A: Yes / B: No, starter.md scope sufficient | B | | ❌ pending |

---

## Handoff

```yaml
research_completed: true
initiative_path: TODO/initiatives/starter/
artifact: 15-research.md
top_recommendations:
  - "F-3: Ownership delta for refutation quality — lowest effort, highest signal, all infra exists"
  - "F-1: Adaptive visit allocation — tree builder already has forced-move precedent"
  - "F-5: Board-size-scaled noise — pure config change, minimal code"
  - "F-9: Model routing by level — config-first, requires regression test"
open_questions:
  - "Q1: Which finding for first sprint?"
  - "Q2: Expand research scope to escalation retry?"
post_research_confidence_score: 92
post_research_risk_level: low
```
