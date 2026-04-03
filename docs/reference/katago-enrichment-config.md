# KataGo Enrichment Configuration Reference

**Last Updated**: 2026-03-19

## Visit Tiers

| Tier | Visits | Purpose |
|------|--------|---------|
| T0 | 50 | Policy snapshot for quick pre-classification |
| T1 | 500 | Standard analysis (correct move validation, difficulty) |
| T2 | 2000 | Deep analysis (refutation generation, complex positions) |
| T3 | 5000 | Referee (disagreement resolution, escalation endpoint) |

## Query Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `reportAnalysisWinratesAs` | `BLACK` | Always report winrates from Black's perspective |
| `rootNumSymmetriesToSample` | 4 (standard), 8 (referee) | Board symmetry sampling count |

## Refutation Configuration

| Key | Default | Description |
|-----|---------|-------------|
| `candidate_scoring.mode` | `"temperature"` | Scoring mode: `"temperature"` or `"policy_only"` |
| `candidate_scoring.temperature` | `1.5` | Temperature for weighted scoring |
| `tenuki_rejection.enabled` | `true` | Reject far-away KataGo responses |
| `tenuki_rejection.manhattan_threshold` | `4.0` | Max Manhattan distance |
| `refutation_overrides.rootPolicyTemperature` | `1.3` | Explore more candidates |
| `refutation_overrides.rootFpuReductionMax` | `0` | Don't penalize unexplored |
| `refutation_overrides.wideRootNoise` | `0.08` | Exploration noise |

## Seki Detection

| Key | Default | Description |
|-----|---------|-------------|
| `seki.winrate_low` | `0.40` | Lower winrate bound for seki classification |
| `seki.winrate_high` | `0.60` | Upper winrate bound for seki classification |

## Snapback Detection

| Key | Default | Description |
|-----|---------|-------------|
| `snapback.min_pv_length` | `3` | Minimum PV length for recapture pattern verification |

## Frame Configuration

| Key | Default | Description |
|-----|---------|-------------|
| `frame.entropy_quality_check.enabled` | `true` | Ownership-based frame validation |
| `frame.entropy_quality_check.variance_threshold` | `0.15` | Max ownership variance |
| `frame.entropy_quality_check.entropy_contest_threshold` | `0.5` | Threshold for contested-region entropy classification |

## Curated Pruning

| Key | Default | Description |
|-----|---------|-------------|
| `validation.curated_pruning.enabled` | `true` | Skip low-visit curated branches |
| `validation.curated_pruning.min_visit_ratio` | `0.01` | Below this = skip |
| `validation.curated_pruning.trap_threshold` | `0.02` | Above this = keep (tricky trap) |
| `validation.curated_pruning.min_depth` | `2` | Never prune first-moves |

## AI-Solve Section (`ai_solve`)

| Key                             | Type  | Default | Description                                                                 |
| ------------------------------- | ----- | ------- | --------------------------------------------------------------------------- |
| `enabled`                       | bool  | `false` | Master switch for AI-Solve. When `false`, pipeline behaves as pre-AI-Solve. |
| `thresholds.t_good`             | float | 0.75    | Winrate threshold for classifying a move as "correct"                       |
| `thresholds.t_bad`              | float | 0.35    | Winrate threshold below which a move is "wrong"                             |
| `thresholds.t_policy_min`       | float | 0.01    | Minimum policy prior to consider a move candidate                           |
| `confidence_metrics.min_visits` | int   | 100     | Minimum visits before trusting classification                               |

### Solution Tree (`ai_solve.solution_tree`)

| Key                         | Type  | Default | Description                                  |
| --------------------------- | ----- | ------- | -------------------------------------------- |
| `max_total_tree_queries`    | int   | 200     | Total engine queries budget across all trees |
| `tree_visits`               | int   | 500     | Visits per tree-building query               |
| `wr_epsilon`                | float | 0.02    | Winrate stability epsilon for stopping       |
| `own_epsilon`               | float | 0.05    | Ownership convergence epsilon                |
| `max_branch_width`          | int   | 3       | Max opponent responses per node              |
| `max_refutation_root_trees` | int   | 3       | Max wrong-move refutation trees              |
| `max_correct_root_trees`    | int   | 2       | Max additional correct trees                 |

### Depth Profiles (`ai_solve.solution_tree.depth_profiles`)

| Category   | Levels                              | Min Depth | Max Depth |
| ---------- | ----------------------------------- | :-------: | :-------: |
| `beginner` | novice, beginner, elementary        |     2     |     8     |
| `core`     | intermediate, upper-intermediate    |     3     |    16     |
| `advanced` | advanced, low-dan, high-dan, expert |     4     |    24     |

### Seki Detection (`ai_solve.seki_detection`)

| Key                      | Type  | Default | Description                                         |
| ------------------------ | ----- | ------- | --------------------------------------------------- |
| `winrate_band_low`       | float | 0.45    | Lower bound of seki winrate band                    |
| `winrate_band_high`      | float | 0.55    | Upper bound of seki winrate band                    |
| `seki_consecutive_depth` | int   | 3       | Consecutive depths in band before early-exit        |
| `score_lead_seki_max`    | float | 2.0     | Max absolute score lead consistent with seki        |

### Edge Case Boosts (`ai_solve.edge_case_boosts`)

| Key                   | Type  | Default | Description                              |
| --------------------- | ----- | ------- | ---------------------------------------- |
| `corner_visit_boost`  | float | 1.5     | Visit multiplier for corner positions    |
| `ladder_visit_boost`  | float | 2.0     | Visit multiplier for suspected ladders   |
| `ladder_pv_threshold` | int   | 8       | PV length threshold for ladder detection |

### Observability (`ai_solve.observability`)

| Key                            | Type  | Default                           | Description                                  |
| ------------------------------ | ----- | --------------------------------- | -------------------------------------------- |
| `disagreement_sink_path`       | str   | `.lab-runtime/logs/disagreements` | JSONL disagreement file directory            |
| `collection_warning_threshold` | float | 0.20                              | Per-collection disagreement rate for WARNING |

### Goal Inference (`ai_solve.goal_inference`)

| Key                       | Type  | Default | Description                                  |
| ------------------------- | ----- | ------- | -------------------------------------------- |
| `score_delta_kill`        | float | 15.0    | Score delta threshold for "kill" goal        |
| `score_delta_capture`     | float | 5.0     | Score delta threshold for "capture" goal     |
| `ownership_variance_gate` | float | 0.1     | Ownership variance gate for secondary signal |

### KM Search Optimizations (`ai_solve.solution_tree`)

| Key                            | Type  | Default | Description                                                                 |
| ------------------------------ | ----- | ------- | --------------------------------------------------------------------------- |
| `simulation_enabled`           | bool  | `true`  | Kawano simulation for sibling opponent responses (KM-01)                   |
| `simulation_verify_visits`     | int   | 50      | Visits for simulation verification query                                    |
| `transposition_enabled`        | bool  | `true`  | Zobrist-hashed position cache within single tree build (KM-02)             |
| `terminal_detection_enabled`   | bool  | `true`  | Pre-query Benson (G1) + interior-point death (G2) gates                    |
| `forced_move_visits`           | int   | 125     | Reduced visits for forced player continuations (KM-03); 0 = disabled       |
| `forced_move_policy_threshold` | float | 0.85    | Policy prior threshold for forced-move detection                            |
| `depth_policy_scale`           | float | 0.01    | Per-depth increment to `branch_min_policy` at opponent nodes               |

## Quality Weights (`quality_weights`)

Config-driven weights for the `qk` quality score formula (v1.22, GQ-1 panel-validated):

| Key                    | Type  | Default | Description                                         |
| ---------------------- | ----- | ------- | --------------------------------------------------- |
| `trap_density`         | float | 0.40    | Weight for trap density signal                      |
| `avg_refutation_depth` | float | 0.30    | Weight for average refutation depth signal          |
| `correct_move_rank`    | float | 0.20    | Weight for correct move rank in policy ordering     |
| `policy_entropy`       | float | 0.10    | Weight for Shannon entropy of top-K priors          |
| `avg_depth_max`        | float | 10.0    | Normalization ceiling for avg refutation depth      |
| `rank_clamp_max`       | int   | 8       | Max rank value before clamping                      |
| `rank_min_visits`      | int   | 500     | Visit-count gate: below this, apply penalty         |
| `low_visit_multiplier` | float | 0.70    | Penalty multiplier when visits < rank_min_visits    |

Formula: `qk = round(qk_raw × 5)` where `qk_raw = Σ(weight_i × norm(signal_i))`. See [Architecture: Signal Formulas](../architecture/tools/katago-enrichment.md#signal-formulas) for derivation.

## Quality Gates (`quality_gates`)

| Key                    | Type  | Default | Description                                |
| ---------------------- | ----- | ------- | ------------------------------------------ |
| `acceptance_threshold` | float | 0.80    | Min acceptance rate for batch quality gate |

## Teaching Comment Thresholds (`teaching`)

| Key                          | Type  | Default | Description                                                                 |
| ---------------------------- | ----- | ------- | --------------------------------------------------------------------------- |
| `non_obvious_policy`         | float | 0.10    | Policy prior ceiling for "surprising move" signal                          |
| `ko_delta_threshold`         | float | 0.12    | Minimum ownership delta for ko wrong-move classification                   |
| `capture_depth_threshold`    | int   | 1       | PV depth ceiling for "immediate capture" condition                         |
| `significant_loss_threshold` | float | 0.50    | Winrate delta above which wrong move gets loss annotation                  |
| `moderate_loss_threshold`    | float | 0.20    | Winrate delta for "significant disadvantage" annotation                    |
| `use_opponent_policy`        | bool  | false   | Enable opponent-response teaching comments (PI-10)                         |

## Feature Activation Phases

All refutation quality improvements (PI-1 through PI-12) are feature-gated. Activation is tracked in the config changelog:

| Phase | Config Version | Activated Features |
|-------|---------------|--------------------|
| **1a** (v1.23) | PI-1 `ownership_delta_weight=0.3`, PI-3 `score_delta_enabled=true`, PI-12 `best_resistance_enabled=true` |
| **1b** (v1.23) | PI-5 `noise_scaling=board_scaled`, PI-6 `forced_min_visits_formula=true` |
| **1c** (v1.23) | PI-10 `use_opponent_policy=true`, PI-11 `surprise_weighting=true` |
| **2** (v1.24) | PI-2 `visit_allocation_mode=adaptive`, PI-7 `branch_escalation_enabled=true`, PI-8 `multi_pass_harvesting=true`, PI-9 `player_alternative_rate=0.15` |

## Dependencies

| Package | Version | Purpose |
|---------|---------|--------|
| `pydantic` | `>=2.0` | Data models and validation |
| `fastapi` | `>=0.100` | Bridge server API |
| `uvicorn` | `>=0.20` | ASGI server |

> **Note:** sgfmill was replaced by a stripped copy of KaTrain's pure-Python SGF parser in March 2026. The KaTrain parser lives in `core/sgf_parser.py`.

---

> **See also:**
>
> - [How-To: KataGo Enrichment Lab](../how-to/tools/katago-enrichment-lab.md) — usage guide
> - [Architecture: KataGo Enrichment](../architecture/tools/katago-enrichment.md) — design decisions
> - [Concepts: Quality](../concepts/quality.md) — AC quality levels
> - [Concepts: Teaching Comments](../concepts/teaching-comments.md) — Teaching comment system
> - [Concepts: Entropy ROI](../concepts/entropy-roi.md) — Ownership entropy formula
