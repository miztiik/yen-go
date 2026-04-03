# Research Brief: Lizgoban & KaTrain Patterns for Puzzle Enrichment

**Initiative**: `20260314-research-lizgoban-katrain-patterns`
**Research question**: Which algorithms, thresholds, and architectural patterns from Lizgoban (JS) and KaTrain (Python) are directly applicable to Yen-Go's offline puzzle enrichment pipeline?
**Boundaries**: Offline batch processing only. Python pipeline. KataGo engine. No live game analysis.
**Last Updated**: 2026-03-14

---

## 1. File-by-File Analysis

### 1.1 Lizgoban — `weak_move.js`

**Purpose**: Generates weakened AI moves to simulate human-level play. Implements 5 strategies: random_candidate (winrate targeting), lose_score (score-loss targeting), random_opening (policy-weighted early moves), policy (temperature-scaled policy sampling), and persona (ownership-based board evaluation with per-region weighting).

**Key algorithms/functions**:

| R-ID | Function | What it computes |
|------|----------|------------------|
| R-1 | `weak_move(state, weaken_percent)` | Targets a specific winrate via `target = 40 × 10^(-r) × 2^(-movenum/100)` — converges winrate to 0 over time |
| R-2 | `weak_move_by_score(state, avg_losing_pts)` | Selects move closest to a target score loss — `target_score = current - random(0, 2×avg_loss) × sign` |
| R-3 | `eval_with_persona(ownership, stones, param, is_bturn)` | Evaluates board positions using per-region ownership weighting: `goodness = Σ(a × ownership_for_me + b × entropy_amplifier × entropy_term)` where `[a,b] = [u+v, u-v]` per stone category (my/your/space) |
| R-4 | `select_weak_move_by_goodness_order()` | Weighted random selection from candidates ordered by goodness, with exponential weighting `exp(-order/typical_order)` |
| R-5 | `weak_move_candidates(suggest, last, threshold)` | Filters candidates by visits threshold (default 2% of top visits) and natural PV check (tenuki_threshold = 4.0) |
| R-6 | `final_check(selected, state, sec, loss_threshold)` | Post-hoc validation: re-analyzes selected move for 0.5s, rejects if winrate_loss > 30% × sanity_coef or score_loss > 10 × sanity_coef |

**Reusable patterns for puzzle enrichment**:

- **(b) Difficulty estimation**: The `winrate → target_winrate` formula (`40 × 10^(-r)`) provides a calibrated mapping from "weakness percentage" to expected winrate. Could inform level-to-expected-winrate validation.
- **(d) Refutation generation**: `weak_move_by_score` algorithm for selecting moves with specific score losses is directly applicable to generating graded refutations — select wrong moves at specific score-loss tiers.
- **(f) KataGo query optimization**: `final_check` uses a 0.5-second re-analysis at a single position — shows that lightweight per-move re-analysis is viable for validation.
- **(g) Move-order analysis**: `natural_pv_p` detects tenuki (distance > 4.0) by checking if opponent's response in PV is closer to last_move than the candidate — useful for move-order strictness detection.

**Constants/thresholds**:

| R-ID | Threshold | Value | Controls |
|------|-----------|-------|----------|
| R-7 | `tenuki_threshold` | 4.0 | Manhattan distance for tenuki detection |
| R-8 | `too_small_visits` | 2% of top visits | Candidate filtering |
| R-9 | `max_winrate_loss` | 30.0% | Final check rejection |
| R-10 | `max_score_loss` | 10.0 points | Final check rejection |
| R-11 | `entropy_amplifier` | 2.0 | Ownership entropy weight in persona eval |
| R-12 | `initial_target_winrate` | `40 × 10^(-r)` | Weakness calibration curve |

---

### 1.2 Lizgoban — `util.js`

**Purpose**: Core utility library. Provides math helpers, array manipulation, board coordinate utilities, and global constants. Most relevant: entropy calculation, weighted random selection (KaTrain-inspired), blunder thresholds, and HumanSL profile definitions.

**Key algorithms/functions**:

| R-ID | Function | What it computes |
|------|----------|------------------|
| R-13 | `endstate_entropy(es)` | Shannon entropy of ownership: `H(p) + H(1-p)` where `p = (es+1)/2`. Range [0, 1]. High entropy = contested/uncertain. |
| R-14 | `weighted_random_choice(ary, weight_of)` | KaTrain-inspired "magic" formula: `min_by(ary, x => -log(random()) / weight)` — Gumbel trick for sampling |
| R-15 | `endstate_from_ownership(ownership)` | Converts flat ownership array to 2D grid using board_size |

**Constants/thresholds**:

| R-ID | Threshold | Value | Controls |
|------|-----------|-------|----------|
| R-16 | `blunder_threshold` | -2 points | Score loss for blunder classification |
| R-17 | `big_blunder_threshold` | -5 points | Score loss for big blunder |
| R-18 | `blunder_low_policy` | 0.1 (10%) | Policy below which move is suspicious |
| R-19 | `blunder_high_policy` | 0.75 (75%) | Policy above which blunder is concerning |
| R-20 | `humansl_rank_profiles` | `rank_1d` to `rank_20k` | KataGo HumanSL rank profile identifiers |
| R-21 | `humansl_proyear_profiles` | `proyear_1800` to `proyear_2023` | KataGo HumanSL professional year profiles |

**Reusable patterns**:

- **(b) Difficulty estimation**: `humansl_rank_profiles` and `humansl_proyear_profiles` enumerate all available KataGo HumanSL model profiles. These can be used for rank-calibrated difficulty estimation.
- **(c) Board region analysis**: `endstate_entropy` is a clean entropy formula for ownership uncertainty that we could use for contested-region detection.
- **(d) Refutation generation**: `blunder_threshold = -2` and `big_blunder_threshold = -5` are well-calibrated thresholds from years of Lizgoban use. Our current `delta_threshold` of 0.08 (winrate) maps differently — we use score-based thresholds in v1.17.
- **(f) KataGo query**: HumanSL profiles can be passed as `humanSLProfile` in KataGo analysis requests for rank-calibrated analysis.

---

### 1.3 Lizgoban — `rankcheck_move.js`

**Purpose**: Generates moves that distinguish between two rank levels. Evaluates how "diagnostic" each move is — maximizing the difference in expected winrate between a stronger and weaker HumanSL profile while keeping the position balanced.

**Key algorithms/functions**:

| R-ID | Function | What it computes |
|------|----------|------------------|
| R-22 | `eval_rankcheck_move(move, profile_pair, peek)` | Queries two HumanSL profiles (strong ± 2 ranks), gets top-5 policy moves for each, computes expected winrate, maximizes `diff = wr_strong - wr_weak` while keeping `mean ≈ 0.5`. Badness formula: `(diff - 1)² + evenness_coef × (mean - 0.5)²` |
| R-23 | `get_move_gen({policy_profile, reverse_temperature, eval_move})` | Generic framework: takes top-8 policy candidates, evaluates each with async eval function, selects minimum badness. 10% chance of pure policy play for variety. |
| R-24 | `get_hum_persona_move()` | Combines HumanSL policy with persona ownership evaluation |

**Constants/thresholds**:

| R-ID | Threshold | Value | Controls |
|------|-----------|-------|----------|
| R-25 | `rank_delta` | 2 | Rank difference for profile pair |
| R-26 | `max_candidates` | 8 | Top policy moves evaluated |
| R-27 | `policy_move_prob` | 0.1 (10%) | Random policy selection probability |
| R-28 | `winrate_samples` | 5 | Top-5 policy moves per profile for winrate estimation |
| R-29 | `evenness_coef` | 0.1 | Penalty for position imbalance in rankcheck |
| R-30 | `reverse_temperature` | 0.9 | Softening of policy distribution |

**Reusable patterns**:

- **(b) Difficulty estimation**: The profile-pair comparison algorithm is directly applicable: query KataGo with `humanSLProfile=rank_Xk` for two adjacent ranks, see which move distinguishes them. This tells us "this puzzle is between Xk and Yk difficulty" — a calibration-grade signal.
- **(f) KataGo query optimization**: Uses `reverse_temperature=0.9` for policy softening — slightly cooler than uniform but not greedy. Evaluates only top-8 candidates (not all legal moves) for efficiency.

---

### 1.4 Lizgoban — `rule.js`

**Purpose**: Core game rule engine — stone placement, capture detection, ko checking, liberty counting, and surrounding detection. Pure algorithmic Go logic with no AI dependencies.

**Key algorithms/functions**:

| R-ID | Function | What it computes |
|------|----------|------------------|
| R-31 | `get_stones_and_set_ko_state(history)` | Replays move history, tracks captures and ko state |
| R-32 | `captured_from(ij, is_black, stones)` | Flood-fill group detection with liberty counting — `low_liberty_group_from(ij, is_black, stones, 0)` |
| R-33 | `low_liberty_group_from(ij, is_black, stones, max_liberties)` | BFS group detection: finds connected stones with ≤ max_liberties. Returns empty if exceeded. |
| R-34 | `check_ko(...)` | Comprehensive ko detection: captures, two-stage ko resolution by connection, resolution by capture |
| R-35 | `has_liberty(ij, stones, min_liberty)` | Quick liberty check: does group at ij have ≥ min_liberty? |
| R-36 | `is_surrounded_by_opponent(ij, is_black, stones)` | Checks if all neighbors are opponent stones or board edge |

**Reusable patterns**:

- **(a) Technique detection**: `low_liberty_group_from` with `max_liberties=1` detects atari. With `max_liberties=2` detects under-pressure groups. Direct input to snapback detection (sacrifice into atari → recapture larger group).
- **(e) Frame/board validation**: `has_liberty` validates legal positions. `check_ko` provides multi-stage ko detection (basic, connection resolution, capture resolution) — more comprehensive than our current recapture-in-PV heuristic.
- **(a) Ko detection**: Their ko model tracks a `ko_pool` of active ko fights and handles two-stage ko (resolution by connection, resolution by capture). More sophisticated than our PV-based positional recapture check.

**Adaptation value**: **MEDIUM**. We already have `benson_check.py` and `ko_validation.py`. However, the `low_liberty_group_from` parameterized liberty check is a useful primitive we could adopt for snapback detection.

---

### 1.5 Lizgoban — `amb_gain.js`

**Purpose**: Calculates "ambiguity gain" — how much a move increases or decreases game ambiguity. Tracks stone entropy changes and moyo lead changes per player. Used for game-phase analysis, not puzzle enrichment directly.

**Key algorithms/functions**:

| R-ID | Function | What it computes |
|------|----------|------------------|
| R-37 | `get_amb_gain(game, recent)` | Computes ambiguity_gain (stone entropy change) and moyolead_gain (unsettled territory change) per player |
| R-38 | `get_amb_gain_sub(f, keys, game, recent)` | Weighted average of per-move gains using cosine weighting: `weight = 1 + cos(π × distance / recent)` |
| R-39 | `get_black_moyolead_gain(game, recent)` | `score_without_komi - komi - (black_territory - white_territory)` — measures moyo (influence not yet territory) |

**Reusable patterns**:

- **(c) Board region analysis**: Moyo lead gain could inform puzzle "phase" detection — is this a territorial or influence puzzle?
- **(g) Move-order analysis**: Ambiguity gain tracks whether moves clarify or complicate the position — high ambiguity gain on correct move suggests the puzzle tests reading depth.

**Adaptation value**: **LOW** for puzzle enrichment. Designed for mid-game analysis over move sequences, not single-position puzzle evaluation.

---

### 1.6 Lizgoban — `area.js`

**Purpose**: Ownership-based territory clustering and area segmentation. Converts continuous ownership values into discrete labeled regions with boundaries, sizes, and territory estimates. Uses morphological operations (erosion/dilation) for natural cluster separation.

**Key algorithms/functions**:

| R-ID | Function | What it computes |
|------|----------|------------------|
| R-40 | `endstate_clusters_for(endstate, stones)` | Main entry: segments ownership map into labeled clusters by color and category (major/minor) |
| R-41 | `clusters_in_category(category, grid, stones)` | Flood-fill clustering within ownership category, then divides large clusters |
| R-42 | `divide_large_cluster(cluster, grid, category)` | Splits clusters > 40 points using morphological erosion/dilation to find corridors and bottlenecks |
| R-43 | `core_in_region(region, radius, in_board)` | Erosion by `radius` to find interior core (removes thin corridors) |
| R-44 | `corridor_clusters_in(...)` | Identifies thin connecting corridors between cores via dilation after erosion |
| R-45 | `cluster_characteristics(id, ijs, grid, color, stones)` | Computes per-cluster: ownership_sum, territory_sum, center_idx, boundary points, interior detection |
| R-46 | `boundary_of(id, ijs, grid)` | Finds cluster boundary points with direction information |

**Constants/thresholds**:

| R-ID | Threshold | Value | Controls |
|------|-----------|-------|----------|
| R-47 | `minor_ownership` | 0.1 | Ownership below this is "minor" territory |
| R-48 | `too_large_cluster_size` | 40 intersections | Triggers cluster subdivision |
| R-49 | `narrow_corridor_radius` | 3 | Erosion radius for corridor detection |
| R-50 | `too_small_corridor_cluster_size` | 10 | Corridors smaller than this are absorbed |
| R-51 | `too_small_core_cluster_size` | 15 | Core clusters smaller than this are absorbed |

**Reusable patterns**:

- **(c) Board region analysis**: **HIGH VALUE**. The erosion/dilation corridor detection is directly applicable to tsumego puzzle region detection. Instead of simple bounding-box cropping, we could use ownership clustering to identify the "active" puzzle region — groups under attack, surrounding territory, and eye spaces.
- **(e) Frame validation**: `cluster_characteristics` computes interior detection (`interior(i,j,sign)` — checks if all neighbors have same-sign ownership). This is useful for verifying that the puzzle frame correctly encloses the relevant group.
- **(c) Auto-cropping alternative**: Ownership clusters with `boundary_of()` provide natural puzzle boundaries. A cluster-based approach would be more semantically meaningful than our current geometric bounding-box + margin approach in `query_builder.py`.

**Adaptation value**: **HIGH**. The morphological operations pattern (erosion → core detection → dilation → corridor identification) is a novel approach we don't currently have. Could replace or complement our `tsumego_frame.py` / `tsumego_frame_gp.py`.

---

### 1.7 Lizgoban — `branch.js`

**Purpose**: Manages branching structure for game trees — tracks where games diverge from the main line. Minimal module, primarily for UI navigation.

**Key algorithms/functions**:

| R-ID | Function | What it computes |
|------|----------|------------------|
| R-52 | `update_branch_for(game, all_games)` | Finds common header length between current game and all other loaded games, records branch points |
| R-53 | `branch_at(move_count)` | Returns games that branch off at a given move number |

**Adaptation value**: **NEGLIGIBLE**. This is a UI navigation module. Our solution tree structure already handles branching via the AI-Solve tree builder.

---

### 1.8 Lizgoban — `ladder.js`

**Purpose**: Algorithmic ladder detection without AI — uses pattern matching on 3×3 stone configurations with liberty counting to detect and extend ladder sequences. Pure Go logic.

**Key algorithms/functions**:

| R-ID | Function | What it computes |
|------|----------|------------------|
| R-54 | `succeeding_ladder(game, stones)` | Checks if last two moves continue a ladder (try escape, try capture) |
| R-55 | `try_to_escape_or_capture(recent_move, move_count, stones, pattern, liberty_pattern, attack_p)` | Matches 3×3 patterns against 8 rotations/reflections, checks liberty constraints |
| R-56 | `continue_ladder(ladder, prop, move_count, stones)` | Recursive ladder extension: places stone, checks if stopped, recurses. Returns sequence of ladder moves |
| R-57 | `stopped(idx, is_black, u, v, stones)` | Checks if ladder is blocked by existing stone or board edge at predicted path |
| R-58 | `match_pattern_sub(...)` | 3×3 pattern matching with 8 symmetry transforms (uv_candidates), checks stone patterns AND liberty patterns independently |
| R-59 | `next_prop(prop)` | Alternating direction for ladder zigzag: escape has `[v, u]` swap, attack has `[u, v]` |

**Pattern definitions**:

| R-ID | Pattern | Configuration | Description |
|------|---------|---------------|-------------|
| R-60 | `attack_pattern` | `?S1 / X2. / x3.` | Attacker places at 3 to chase stone at 2 |
| R-61 | `escape_pattern` | `?SO / S13 / ?2?` | Escapee places at 3 to extend from stone 2 |
| R-62 | Liberty checks | `a = ≤1 liberty`, `b = ≤2 liberties`, `2/3 = ≥2/≥3 liberties` | Liberty constraints on pattern positions |

**Constants/thresholds**:

| R-ID | Threshold | Value | Controls |
|------|-----------|-------|----------|
| R-63 | `too_short` | 4 | Minimum ladder length to be considered valid |

**Reusable patterns**:

- **(a) Technique detection**: **HIGH VALUE**. This is a pure algorithmic ladder detector that does NOT rely on AI PV sequences. Our current `_detect_ladder` in `technique_classifier.py` uses a diagonal-chase heuristic on PV moves (R-64, internal). Lizgoban's approach is fundamentally different — it uses stone pattern matching with liberty constraints on the board position itself. This is:
  1. **More accurate**: Detects ladders from board position, not PV artifacts
  2. **Board-aware**: Checks if ladder is blocked by existing stones (`stopped()`)
  3. **Direction-tracking**: Models the zigzag path with u,v vectors and 8 symmetries
  
  Our PV-based diagonal heuristic can produce false positives (any diagonal sequence of moves) and false negatives (ladders where PV is short). The pattern-based approach from Lizgoban would be strictly superior.

**Adaptation value**: **VERY HIGH**. Direct port candidate for replacing our PV-based ladder detection.

---

### 1.9 KaTrain — `ai.py`

**Purpose**: Complete AI strategy system with 15+ strategies for human-like play. Most relevant: difficulty estimation via ELO mapping, score-loss weighted move selection, ownership-based strategy evaluation, HumanSL integration, and game report analysis.

**Key algorithms/functions**:

| R-ID | Function | What it computes |
|------|----------|------------------|
| R-65 | `ai_rank_estimation(strategy, settings)` | Maps AI strategy+settings to kyu rank via calibrated ELO lookup tables |
| R-66 | `interp1d(lst, x)` / `interp2d(gridspec, x, y)` | Piecewise linear interpolation for ELO lookup |
| R-67 | `game_report(game, thresholds, depth_filter)` | Full game analysis: histogram by loss buckets, accuracy (`100 × 0.75^weighted_loss`), complexity (prior-weighted loss), ai_top_move rate |
| R-68 | `ScoreLossStrategy.generate_move()` | Weights moves by `exp(-c × max(0, points_lost))` — smooth exponential preference for less-losing moves |
| R-69 | `OwnershipBaseStrategy.settledness(d, player_sign, player)` | Sum of absolute ownership values for player's stones — measures how "settled" the position is |
| R-70 | `OwnershipBaseStrategy.get_moves_with_settledness()` | Ranks moves by: `points_lost + attach_penalty × is_attach + tenuki_penalty × is_tenuki - settled_weight × (own_settled + opponent_fac × opp_settled)` |
| R-71 | `RankStrategy.get_n_moves()` | Complex calibrated formula: `n_moves = board_squares × norm_leg_moves / (1.31165 × (modified_calib_avemodrank + 1) - 0.082653)` |
| R-72 | `generate_influence_territory_weights(ai_mode, settings, policy_grid, size)` | Distance-from-edge weighting: `weight = (1/line_weight)^(max(0, threshold - min_edge_dist))` |
| R-73 | `generate_local_tenuki_weights(ai_mode, settings, policy_grid, cn, size)` | Gaussian proximity weighting: `exp(-0.5 × ((x-mx)² + (y-my)²) / variance)` |
| R-74 | `HumanStyleStrategy.generate_move()` | Full HumanSL integration: requests `humanSLProfile`, receives `humanPolicy` array (362 values for 19×19+pass), weighted random selection |
| R-75 | `weighted_selection_without_replacement(candidates, n)` | Core selection algorithm used throughout |
| R-76 | `policy_weighted_move(policy_moves, lower_bound, weaken_fac)` | Policy-weighted random: `weight = policy^(1/weaken_fac)` for moves above lower_bound |

**Constants/thresholds**:

| R-ID | Threshold | Value | Controls |
|------|-----------|-------|----------|
| R-77 | `CALIBRATED_RANK_ELO` | Lookup table (imported from constants) | ELO → kyu mapping. **Already adopted in v1.17 of our config.** |
| R-78 | `AI_WEIGHTED_ELO` | Lookup table | weaken_fac → ELO for AI_WEIGHTED strategy |
| R-79 | `AI_SCORELOSS_ELO` | Lookup table | strength → ELO for AI_SCORELOSS strategy |
| R-80 | `accuracy = 100 × 0.75^weighted_loss` | n/a | Game accuracy formula: exponential decay from point loss |
| R-81 | `ADDITIONAL_MOVE_ORDER` | Imported constant | Max order for "approved" moves in game report |
| R-82 | `MOVE_VALUE = 14` | points | Value of one move (handicap calculation) |
| R-83 | `max PDA = 3` | n/a | Playout Doubling Advantage cap at 8-stone handicap |
| R-84 | `attach_penalty` / `tenuki_penalty` | Config-driven | Ownership strategy penalties |
| R-85 | `max_points_lost` | Config-driven | Move filtering: exclude moves losing more than this |
| R-86 | `endgame threshold` | 0.75 × board_squares | Move depth for endgame transition |
| R-87 | `override threshold` | 0.8 × (1 - 0.5 × ratio) | Dynamic top-move override based on board filling |

**Reusable patterns**:

- **(b) Difficulty estimation**: The `game_report` function computes:
  - `accuracy = 100 × 0.75^weighted_ptloss` — a calibrated accuracy percentage
  - `complexity = Σ(prior × max(points_lost, 0)) / Σ(prior)` — difficulty from move alternatives
  - `adj_weight = max(0.05, min(1.0, max(weight, points_lost / 4)))` — importance weighting
  
  The **complexity** metric is directly applicable to puzzle enrichment: for each candidate move, compute `prior × max(score_delta, 0)` summed over alternatives. This is similar to our `trap_density` but weighted by policy and capped differently.

- **(b) Difficulty estimation**: `RankStrategy.get_n_moves()` formula maps kyu rank + legal move count to expected "number of reasonable moves" — could validate our level assignments (if a beginner-level puzzle has too many reasonable candidates, it may be misclassified).

- **(d) Refutation generation**: `ScoreLossStrategy` weightings (`exp(-c × max(0, points_lost))`) provide a smooth spectrum of "human-likeness" for wrong moves. For refutation generation, we could use the inverse: `1 - exp(-c × points_lost)` to prioritize high-loss wrong moves as primary refutations.

- **(f) KataGo query optimization**: HumanSL integration pattern:
  1. Request with `humanSLProfile=rank_Xk` and `includePolicy=True`
  2. Receive `humanPolicy` (362-element array for 19×19 + pass)
  3. Use human policy to weight candidates
  
  For puzzles: request analysis at the target difficulty level's rank profile. If the correct move has high human policy at that rank, the puzzle is well-calibrated for that level.

- **(c) Board region analysis**: `settledness` metric (sum of absolute ownership for player's stones) measures how resolved the position is. Low settledness = many stones in contested regions → harder puzzle.

---

## 2. Cross-Cutting Analysis by Category

### (a) Technique Detection

| R-ID | Source | Algorithm | Applicable? | Notes |
|------|--------|-----------|-------------|-------|
| R-54 | ladder.js | 3×3 pattern match + liberty + 8 symmetries | **YES — HIGH** | Superior to our PV diagonal heuristic. Pure board analysis. |
| R-31 | rule.js | `low_liberty_group_from(ij, color, stones, max_lib)` | **YES — MEDIUM** | Useful primitive for snapback (atari → recapture) and throw-in detection |
| R-34 | rule.js | ko_pool tracking with resolution types | **YES — LOW** | More comprehensive ko model but we already have `ko_validation.py` |
| R-3 | weak_move.js | persona ownership evaluation | **NO** | Too tied to live-play context |

**Internal comparison** (R-64): Our `_detect_ladder` in `technique_classifier.py` (lines 195-248) uses `_is_diagonal_chase(pv, min_length=4, diagonal_ratio=0.5)` — purely PV-based. Lizgoban's `ladder.js` operates on the board state directly.

### (b) Difficulty/Rank Estimation

| R-ID | Source | Algorithm | Applicable? | Notes |
|------|--------|-----------|-------------|-------|
| R-77 | ai.py | `CALIBRATED_RANK_ELO` | **ALREADY ADOPTED** | v1.17 Elo anchor gate |
| R-22 | rankcheck_move.js | Profile-pair winrate comparison | **YES — MEDIUM** | Expensive (2 KataGo queries per profile pair) but could be a calibration oracle |
| R-67 | ai.py | `game_report` complexity formula | **YES — HIGH** | `complexity = Σ(prior × loss) / Σ(prior)` — directly comparable to our trap_density |
| R-80 | ai.py | `accuracy = 100 × 0.75^weighted_loss` | **YES — MEDIUM** | Could validate our level assignments: "would a Xk player solve this?" |
| R-71 | ai.py | `RankStrategy.get_n_moves()` calibrated formula | **YES — LOW** | Complex formula, less relevant for puzzle vs game context |
| R-20 | util.js | HumanSL rank profiles list | **YES — MEDIUM** | Reference for querying KataGo with rank-specific analysis |

### (c) Board Region Analysis

| R-ID | Source | Algorithm | Applicable? | Notes |
|------|--------|-----------|-------------|-------|
| R-40 | area.js | Ownership clustering with erosion/dilation | **YES — HIGH** | Novel approach for puzzle region detection |
| R-42 | area.js | Large cluster subdivision via corridors | **YES — HIGH** | Natural boundary detection for auto-cropping |
| R-13 | util.js | Ownership entropy `H(p) + H(1-p)` | **YES — MEDIUM** | Contested region detection |
| R-69 | ai.py | Settledness (sum abs ownership for stones) | **YES — MEDIUM** | Position resolution metric |
| R-72 | ai.py | Distance-from-edge weighting | **YES — LOW** | Could identify corner/edge puzzles |

### (d) Refutation Generation

| R-ID | Source | Algorithm | Applicable? | Notes |
|------|--------|-----------|-------------|-------|
| R-2 | weak_move.js | Score-targeted move selection | **YES — HIGH** | Generate wrong moves at specific loss tiers |
| R-68 | ai.py | `exp(-c × max(0, points_lost))` weighting | **YES — MEDIUM** | Smooth loss-to-weight mapping for refutation prioritization |
| R-16 | util.js | Blunder thresholds (-2, -5 points) | **YES — MEDIUM** | Reference thresholds for refutation severity |

### (e) Frame/Board Validation

| R-ID | Source | Algorithm | Applicable? | Notes |
|------|--------|-----------|-------------|-------|
| R-35 | rule.js | `has_liberty(ij, stones, min_liberty)` | **YES — LOW** | We have Benson check already |
| R-45 | area.js | Interior detection (all neighbors same-sign) | **YES — MEDIUM** | Frame quality validation |
| R-36 | rule.js | `is_surrounded_by_opponent` | **YES — LOW** | Capture detection primitive |

### (f) KataGo Query Optimization

| R-ID | Source | Algorithm | Applicable? | Notes |
|------|--------|-----------|-------------|-------|
| R-74 | ai.py | HumanSL policy request pattern | **YES — HIGH** | New query mode for rank-calibrated analysis |
| R-23 | rankcheck_move.js | Top-8 + eval pattern | **YES — MEDIUM** | Query top-N only, evaluate subset |
| R-6 | weak_move.js | 0.5s re-analysis validation | **YES — LOW** | Lightweight per-move verification |

**Tsumego-specific considerations**: For puzzles, the KataGo query should differ from game analysis:
- `komi = 0.0` (already implemented in our query_builder)
- `allowedMoves` restricted to puzzle region (already implemented)
- `analysisPVLen` ≥ 30 for ko puzzles (already in v1.9 config)
- HumanSL profiles: **NEW** — could request `humanSLProfile` at the target level to validate puzzle calibration

### (g) Move-Order Analysis

| R-ID | Source | Algorithm | Applicable? | Notes |
|------|--------|-----------|-------------|-------|
| R-5 | weak_move.js | `natural_pv_p` tenuki detection (distance > 4.0) | **YES — MEDIUM** | Useful for miai/flexible detection |
| R-37 | amb_gain.js | Ambiguity gain per move | **NO** | Game-context only |

---

## 3. Internal Code Evidence

| R-ID | File | What exists | Gap vs. external |
|------|------|-------------|------------------|
| R-64 | `technique_classifier.py` L195-248 | PV-based diagonal chase ladder detection | Lizgoban's pattern-based detection is structurally superior |
| R-65-INT | `estimate_difficulty.py` L315-365 | Score-based trap density | Already KaTrain-inspired (v1.17). Could add complexity metric from `game_report`. |
| R-66-INT | `estimate_difficulty.py` L434-470 | Elo anchor gate via CALIBRATED_RANK_ELO | Already adopted. Could expand with HumanSL calibration queries. |
| R-67-INT | `ko_validation.py` | Ko detection via PV recapture | Lizgoban's ko_pool model is more comprehensive but our approach works for tsumego. |
| R-68-INT | `query_builder.py` L81-113 | Bounding box + margin based region | Lizgoban's ownership clustering (area.js) would be semantically better. |
| R-69-INT | `config.py` L29+ | OwnershipThresholds | Already has alive/dead/seki thresholds. Missing entropy-based metrics. |
| R-70-INT | `benson_check.py` | Unconditional life via Benson's algorithm | Stronger than Lizgoban for life/death but doesn't do area segmentation. |

---

## 4. Candidate Adaptations for Yen-Go

### Adaptation A: Pattern-Based Ladder Detector (from `ladder.js`)

**What**: Port Lizgoban's 3×3 pattern matcher with 8-symmetry transforms and recursive ladder extension to Python. Replace PV-based diagonal heuristic.

**Effort**: ~200 lines Python. The pattern definitions (R-60, R-61) and matching logic (R-58) are self-contained.

**Benefit**: Accurate ladder detection from board position. No dependency on KataGo PV length or quality.

**Risk**: Requires board state access in `technique_classifier.py` (currently only gets validation/refutation dicts). Implementation scope is Level 2 (1-2 files, explicit behavior change).

### Adaptation B: Ownership Clustering for Puzzle Region (from `area.js`)

**What**: Port ownership-based clustering with erosion/dilation to Python. Use for semantic puzzle region detection instead of geometric bounding-box cropping.

**Effort**: ~300 lines Python. Core algorithm is straightforward but needs ownership data from KataGo query.

**Benefit**: Better puzzle framing, natural boundary detection, corridor awareness.

**Risk**: Requires ownership data at query-build time (chicken-and-egg: need to query KataGo to get ownership, but we're building the query). Could be a post-initial-analysis refinement step. Level 3 change (2-3 files).

### Adaptation C: HumanSL Calibration Queries (from `ai.py` + `rankcheck_move.js`)

**What**: After enrichment, validate puzzle difficulty by querying KataGo with `humanSLProfile=rank_{target_level}k` and checking if correct move has high human policy at that level.

**Effort**: ~100 lines. Query builder change + result validation.

**Benefit**: Ground truth validation of difficulty assignment. "Would a 10k player find this move?" directly answered by KataGo's human model.

**Risk**: Requires KataGo human model files (separate download). Doubles analysis time per puzzle. Level 2 change.

### Adaptation D: Complexity Metric (from `ai.py` `game_report`)

**What**: Add KaTrain's complexity formula `Σ(prior × max(score_delta, 0)) / Σ(prior)` as a secondary difficulty signal alongside trap density.

**Effort**: ~30 lines. Pure formula addition to `estimate_difficulty.py`.

**Benefit**: Captures different dimension of difficulty: how "tricky" is the position (many plausible-looking wrong moves).

**Risk**: Minimal. Level 1 change.

### Adaptation E: Entropy-Based Region Contestation (from `util.js`)

**What**: Compute ownership entropy per intersection: `H((ownership+1)/2)`. Sum entropy in puzzle region to measure "how contested" the position is.

**Effort**: ~20 lines. Pure math addition.

**Benefit**: Second signal for difficulty and technique detection (high entropy + ko = hard ko puzzle; low entropy + accepted = seki candidate).

**Risk**: None. Level 0-1 change.

---

## 5. Risks, License/Compliance, and Rejection Reasons

### License

| Source | License | Status |
|--------|---------|--------|
| Lizgoban | GPL-3.0 | **CAUTION**: GPL-3.0 requires derivative works to be GPL. We must NOT copy code verbatim. Extract algorithmic ideas only. |
| KaTrain | MIT | **CLEAR**: Already adopted (`CALIBRATED_RANK_ELO` cited in v1.17 changelog). Algorithm adoption is fine. |

### Rejections

| R-ID | Pattern | Reason |
|------|---------|--------|
| R-37 | Ambiguity gain | Game-context metric, not applicable to single-position puzzles |
| R-52 | Branch structure | UI navigation module, no enrichment value |
| R-1 | Winrate convergence formula | Live-play weakening, not puzzle analysis |
| R-71 | get_n_moves calibrated formula | Too complex for offline puzzle context, marginal value |
| R-24 | Persona move generation | Live-play interaction, not batch-applicable |

### Risks

| Risk | Mitigation |
|------|------------|
| GPL contamination from Lizgoban | Implement algorithms from scratch based on descriptions, never copy JS |
| HumanSL model availability | Feature-gate behind model file existence check |
| Ownership clustering adds query overhead | Make it a post-analysis refinement, not a pre-query step |
| Pattern-based ladder detector scope creep | Bound to ladder + escape patterns only, not general pattern matching engine |

---

## 6. Planner Recommendations

1. **Adopt Adaptation D (Complexity Metric) immediately** — Level 1 change, ~30 lines, pure formula addition. Captures a different difficulty dimension than trap density. No dependencies. Ship as part of next enrichment config bump.

2. **Adopt Adaptation E (Entropy-Based Region Contestation) immediately** — Level 0-1 change, ~20 lines. Adds ownership entropy calculation for better seki detection and contested-region identification. Complements existing ownership thresholds in config.

3. **Plan Adaptation A (Pattern-Based Ladder Detector) as next sprint** — Level 2 change, ~200 lines. Replaces PV-based diagonal heuristic with structurally superior board-state pattern matching. Requires passing board position to technique classifier (currently missing). High accuracy improvement.

4. **Evaluate Adaptation C (HumanSL Calibration Queries) as stretch goal** — Level 2 change but doubles per-puzzle analysis time. Most valuable as a batch calibration oracle: run on a sample of puzzles per difficulty level to validate thresholds. Not for per-puzzle enrichment.

5. **Defer Adaptation B (Ownership Clustering)** — Level 3 change with chicken-and-egg dependency (need ownership to define region, need region to query). Current bounding-box + margin approach is adequate. Revisit if frame quality issues arise.

---

## 7. Confidence and Risk Assessment

| Metric | Value |
|--------|-------|
| `post_research_confidence_score` | 82 |
| `post_research_risk_level` | low |
| Internal references | 7 files (technique_classifier.py, estimate_difficulty.py, ko_validation.py, query_builder.py, config.py, benson_check.py, bridge.py) |
| External references | 9 files (8 Lizgoban modules + 1 KaTrain module) |
| Coverage | All 7 enrichment categories assessed with explicit applicability ratings |

### Open Questions

| q_id | question | options | recommended | user_response | status |
|------|----------|---------|-------------|---------------|--------|
| Q1 | Should HumanSL calibration (Adaptation C) be per-puzzle or batch-sample only? | A: Per-puzzle (accurate, 2× time) / B: Batch sample (fast, statistical) / C: Skip entirely | B | | ❌ pending |
| Q2 | Is KataGo human model file available in the lab environment? | A: Yes / B: No / C: Unknown | | | ❌ pending |
| Q3 | Should pattern-based ladder detection (Adaptation A) require board state refactoring in technique_classifier, or should it be a separate pre-classifier module? | A: Extend technique_classifier / B: Separate module / Other | A | | ❌ pending |
| Q4 | For the complexity metric (Adaptation D), should it replace trap_density or be a complementary signal? | A: Replace / B: Complementary with separate weight / C: Complementary, merged into trap_density | B | | ❌ pending |

---

## Handoff

```yaml
research_completed: true
initiative_path: TODO/initiatives/20260314-research-lizgoban-katrain-patterns/
artifact: 15-research.md
top_recommendations:
  - "Adopt Complexity Metric (Adaptation D) — Level 1, immediate"
  - "Adopt Entropy Contestation (Adaptation E) — Level 0-1, immediate"
  - "Plan Pattern-Based Ladder Detector (Adaptation A) — Level 2, next sprint"
  - "Evaluate HumanSL Calibration (Adaptation C) — Level 2, stretch goal"
open_questions:
  - "Q1: HumanSL per-puzzle vs batch-sample"
  - "Q2: KataGo human model availability"
  - "Q3: Ladder detector module placement"
  - "Q4: Complexity metric relationship to trap_density"
post_research_confidence_score: 82
post_research_risk_level: low
```
