# AI-Solve: Position-Only Puzzle Enrichment Plan — v2.1

**Last Updated:** 2026-03-03  
**Reviewers:** Lee Sedol (9p) · Cho Chikun (9p, Meijin) · Shin Jinseo (9p) · Ke Jie (9p) · Principal Staff Engineer A · Principal Staff Engineer B  
**Scope:** `tools/puzzle-enrichment-lab/` — analyzers, models, config, CLI, tests  
**Goal:** Build complete solution trees (not just first moves) for position-only SGFs, and enrich ALL puzzles through AI — whether they already have solutions or not  
**Status:** DESIGN PLAN v2.1 — v2 + review panel amendments — requires approval before implementation  
**Supersedes:** `TODO/ai-solve-enrichment-plan.md` (v1)

---

## Key Changes from v1

| v1 Decision                      | v2 Revision                             | Rationale                                                                                     |
| -------------------------------- | --------------------------------------- | --------------------------------------------------------------------------------------------- |
| `--allow-ai-solve` separate flag | Removed. AI enrichment is always-on     | Every puzzle goes through AI checking. If solution exists, validate+extend. If not, build it. |
| `ac:0/1/2` (3 values)            | `ac:0/1/2/3` (4 values)                 | Need to distinguish untouched, enriched-only, solved+enriched, and human-verified             |
| Find single correct first move   | Build full solution tree with branching | Deep branching is not a future extension — it's the core deliverable                          |
| Hardcoded thresholds             | Config-driven, conflict-tested          | Everything tunable, measurable, and replaceable                                               |
| Expert panel: Cho Chikun only    | 4 Go professionals + 2 Staff Engineers  | Conflict-driven design — disagreement surfaces better decisions                               |

### Key Changes from v2 → v2.1 (Review Panel Amendments)

| v2 Decision                               | v2.1 Amendment                                                                    | Rationale                                                               |
| ----------------------------------------- | --------------------------------------------------------------------------------- | ----------------------------------------------------------------------- | ----------------------------------------- |
| `pre_winrate_floor=0.90` as validity gate | Downgraded to confidence metric (ALG-3/STR-2)                                     | Many valid puzzles have root wr < 0.90. Delta classification dominates. |
| `miai_detected` boolean                   | Renamed to `co_correct_detected`, multi-signal (ALG-5/STR-3)                      | Winrate gap alone isn't Go-theoretic miai. Added score gap check.       |
| `query_budget` optional (`                | None`)                                                                            | Required parameter (MIN-2)                                              | Optional budget defeats hard cap purpose. |
| No truncation consequence                 | Budget exhaustion before min_depth → confidence downgrade (ALG-4)                 | Partial solutions shouldn't claim ac:2.                                 |
| No batch-level observability              | `BatchSummary` + `DisagreementSink` (LOG-1/LOG-2)                                 | Per-puzzle logs insufficient for quality monitoring.                    |
| No seki stopping condition                | `seki_detection` config section (EDGE-2)                                          | Tree builder could oscillate indefinitely in seki positions.            |
| Sequential alternative tree building      | Parallel via `asyncio.gather()` (STR-4)                                           | Wall time reduction ~40-60%.                                            |
| No model-version sensitivity              | Calibration with `model_profiles` (ALG-8/CAL-3)                                   | Thresholds shift between KataGo versions.                               |
| No human solution confidence metadata     | `human_solution_confidence` field (ALG-6)                                         | Frontend needs signal when human solution is suboptimal.                |
| No pass-move handling                     | Explicit rejection path (EDGE-4)                                                  | Pass as correct first move = trivial/malformed puzzle.                  |
| No inject/extract roundtrip test          | Defensive assertion + integration test (STR-5)                                    | Fragile coupling must be tested explicitly.                             |
| 10 confirmation queries unconditionally   | `confirmation_min_policy=0.03` pre-filter (STR-1)                                 | Reduces classification from 10 to ~3-5 queries (50-70% savings).        |
| Ownership-only goal inference             | Multi-signal: score delta primary, ownership secondary with variance gate (ALG-7) | Ownership alone is brittle in ko/seki/small fights.                     |
| No collection-level disagreement tracking | Per-collection summary with WARNING threshold (ALG-9)                             | Silent drift accumulates without aggregate monitoring.                  |

---

## Motivation

### The Problem

Today, `enrich_single_puzzle()` rejects any SGF without a child node containing a correct first move:

```python
# enrich_single.py ~line 505
correct_move_sgf = extract_correct_first_move(root)
if correct_move_sgf is None:
    return _make_error_result("No correct first move found in SGF", ...)
```

This means 900+ position-only puzzles (tasuki/cho-chikun-elementary) and any future source without solution trees cannot be enriched.

### Why This Matters

1. **Not just textbooks.** Many puzzle collections exist as position-only files. There is no solution to look up.
2. **Two correct answers is fine.** If KataGo finds two winning first moves, that's a learning opportunity. We are not reproducing a book answer; we are helping people learn and have fun.
3. **All puzzles get AI enrichment.** Even puzzles WITH existing solutions benefit from AI-discovered alternative correct paths, deeper solution trees, and validated refutations. AI enrichment is universal, not opt-in.

---

## Expert Panel Consultation

### Panel Composition

| Expert                         | Role                        | Bias / Perspective                                                                    |
| ------------------------------ | --------------------------- | ------------------------------------------------------------------------------------- |
| **Cho Chikun** (9p, Meijin)    | Classical tsumego authority | Favors clean, deterministic solutions. Values single-correct-answer pedagogy.         |
| **Lee Sedol** (9p)             | Intuitive fighter           | Values creative alternative solutions. Comfortable with ambiguity and multiple paths. |
| **Shin Jinseo** (9p)           | AI-era professional         | Deeply familiar with KataGo's strengths/weaknesses. Trusts AI for tactical reading.   |
| **Ke Jie** (9p)                | Strategic thinker           | Focuses on practical learning value over theoretical purity.                          |
| **Principal Staff Engineer A** | Systems architect           | Reliability, testability, config-driven thresholds, backward compatibility            |
| **Principal Staff Engineer B** | Data pipeline engineer      | Performance, batch processing, calibration methodology, observability                 |

### Topic 1: How Many Moves Deep Should the Solution Tree Go?

**Question:** When building an AI solution tree, at what depth do we stop? Is there a natural stopping condition, or do we impose a fixed cap?

> **Cho Chikun:** "In elementary tsumego (30k-15k), the answer is typically 3-5 moves. The correct first move leads to an opponent response, then one follow-up that makes the status clear. For intermediate problems (15k-5k), 5-9 moves. Advanced (dan-level), 7-15 moves. But the key is not move count — it's **status clarity**. You stop when the group is unconditionally alive, unconditionally dead, or the ko fight has stabilized. A natural end, not an artificial cap."

> **Lee Sedol:** "I agree with Cho sensei on natural endings, but I want to add: for learning, you sometimes want to show one or two moves PAST the decisive point. If the killing move is move 5, showing moves 6-7 (the cleanup) helps beginners understand WHY move 5 was decisive. So I'd say: stop at status clarity + 1-2 confirmation moves."

> **Shin Jinseo:** "KataGo gives you a natural signal for this. When the winrate stabilizes — stops oscillating and settles to >0.95 or <0.05 — that's the engine telling you the position is decided. You can track `|Δwr_consecutive| < ε` for 2 consecutive moves. With 1000 visits, this is reliable for problems up to low-dan. For high-dan, increase to 2000-5000 visits. I'd also track ownership convergence — when key stones' ownership values stabilize (change < 0.05 between consecutive positions), the position is settled."

> **Ke Jie:** "For a learning platform, I'd argue for a hybrid approach: natural stopping condition (winrate stability) with a configurable hard cap as a safety net. The cap prevents runaway computation on positions that never fully resolve (complex ko fights, seki oscillations). Set the cap generously — say 20 moves — but rely on the natural signal 95% of the time."

> **Principal Staff Engineer A:** "I strongly endorse configuration-driven stopping. Three config parameters: `solution_min_depth` (don't stop before this, even if winrate stabilizes early — ensures non-trivial solutions), `solution_max_depth` (hard cap, never exceed), `winrate_stability_epsilon` (threshold for declaring convergence). Plus an `ownership_stability_epsilon`. All config-driven. Default: min=3, max=20, wr_epsilon=0.02, own_epsilon=0.05."

> **Principal Staff Engineer B:** "Performance implication: each depth level costs one engine query (~50-200ms). At max_depth=20, that's 2-4 seconds per puzzle worst case. In batch mode processing 1000 puzzles, that's 30-60 minutes. Acceptable for lab enrichment. For production, we'd want early termination to average 5-8 queries per puzzle. The natural stopping condition achieves this — most elementary puzzles resolve in 3-5 moves."

**Resolution:** Natural stopping with configurable bounds.

```
Stopping conditions (ANY triggers stop):
  1. Winrate stability: |Δwr| < wr_epsilon for 2 consecutive moves
  2. Ownership convergence: key stones' ownership change < own_epsilon
  3. Hard cap: solution_max_depth reached
  4. Terminal: pass detected in PV, or no legal moves in region

Do NOT stop before solution_min_depth (prevents trivially shallow solutions).

Config defaults:
  solution_min_depth: 3
  solution_max_depth: 20
  winrate_stability_epsilon: 0.02
  ownership_stability_epsilon: 0.05
```

### Topic 2: How Do We Pick Top Candidate Moves? (Good and Bad)

**Question:** The existing refutation logic uses `policy_prior` to rank wrong moves and `delta_threshold=0.08` to filter them. For finding correct moves and building solution trees, what's the right algorithm?

**Current Refutation Logic (for reference):**

```python
# generate_refutations.py — identify_candidates()
# Filters: exclude correct + pass, policy >= candidate_min_policy (0.0)
# Sorts: policy_prior descending (most tempting wrong moves first)
# Caps: candidate_max_count = 5
# Then for each: play move, get opponent response, check |Δwr| >= 0.08
```

> **Lee Sedol:** "For finding the correct move, winrate is the primary signal, not policy. Policy tells you what the neural network's first instinct is — but tsumego is about reading, not instinct. The correct move might have low policy (looks weird at first glance) but high winrate after search. Sort by winrate, not policy. Use policy as a secondary signal for difficulty estimation only."

> **Cho Chikun:** "Lee Sedol is right about winrate being primary. But I want to stress: for the WRONG moves, policy IS the right primary signal, because policy measures how tempting a move is to a student. A wrong move with high policy (looks natural, obvious) is a better trap than a wrong move with low policy (looks bizarre). For correct moves: winrate primary. For wrong moves: policy primary. The existing refutation logic has the wrong-move ranking correct."

> **Shin Jinseo:** "The pseudo-algorithm in the brief has the right shape. Let me formalize:
>
> 1. Analyze position P → get `pre_metrics` (root winrate, top moves, policy distribution)
> 2. The correct move is `pre_metrics.top_move` (highest winrate after search, NOT highest policy)
> 3. For each candidate move m in top-K (say K=10):
>    - Analyze P+m → `post_metrics` (from same player's perspective)
>    - Compute `delta = pre_winrate - post_winrate`
>    - Classify: if delta < T_good → correct move. If delta > T_bad → wrong move. Otherwise → neutral.
> 4. A puzzle is valid when: at least one move has delta < T_good, AND at least one move has delta > T_bad (otherwise it's not really a puzzle — either everything works or nothing does).
>
> For thresholds, I'd start with T_good=0.02, T_bad=0.08, T_hotspot=0.25 — but these MUST be calibrated, not set by feel."

> **Ke Jie:** "I want to add a uniqueness check that the brief mentions. If two moves both have delta < T_good (both are 'correct'), that's either miai (both genuinely work, learning opportunity) or a sign that the position isn't a clean puzzle. You need `min_winrate_gap` between the best correct move and the next-best move to ensure the puzzle has a distinctive answer. But for miai positions, allow up to `max_correct_moves=2`. Gap check: if move #1 winrate - move #2 winrate < min_gap AND both are 'correct' by T_good → flag as miai, include both."

> **Principal Staff Engineer A:** "The algorithm then is:
>
> ```
> For position P:
>   Analyze(P) → pre (root_winrate, top_moves sorted by winrate desc)
>   good_move = pre.top_move  (highest winrate = best move for side-to-move)
>
>   For each move m in top_K candidates (by policy prior, to bound computation):
>     post = Analyze(P + m) from same player's perspective
>     delta = pre.winrate - post.winrate  (sign-adjusted by player color)
>
>   Classify all moves by delta:
>     delta < T_good    → TE (correct / tesuji)
>     delta > T_hotspot → BM+HO (blunder hotspot)
>     delta > T_bad     → BM (bad move)
>     else              → neutral
>
>   Require: at least 1 TE move AND at least 1 BM move
>   Check miai: if 2+ TE moves, gap < min_gap → miai
>
>   Difficulty signals:
>     visits_to_solve = visits allocated to correct move in pre-analysis
>     policy_surprise = 1.0 - correct_move.policy_prior
>     refutation_clarity = max(delta) among BM moves
>     calculation_depth = solution tree depth (from Topic 1)
> ```
>
> All thresholds config-driven. Calibration pass required on real data: adjust T_good/T_bad by precision/recall trade-off, not by intuition."

> **Principal Staff Engineer B:** "On the `top_K` bound: analyzing every legal move is computationally prohibitive (361 moves on 19×19). The refutation pipeline already uses policy as a pre-filter (`candidate_min_policy`). For the solve pipeline, I'd recommend the same pattern: take the top K moves by policy from the initial analysis (these are the moves KataGo's neural net considers plausible at ALL). K=10 is reasonable — it covers all candidates that a human might reasonably consider. Below K=10, moves typically have policy < 0.001 (totally implausible)."

**Resolution:** Winrate-primary ranking for correct moves, policy-primary for wrong moves.

```
Algorithm: analyze_position(P, config)
  1. pre = KataGo.analyze(P, visits=config.solve_visits)
  2. candidates = pre.top_moves[:config.candidate_count]  # top K by policy
  3. For each candidate m:
       post = KataGo.analyze(P + m, visits=config.confirmation_visits)
       post_wr = convert_to_same_player_perspective(post.winrate)
       delta = pre.root_winrate - post_wr
       classify(m, delta, config.thresholds)
  4. correct_moves = [m for m in candidates if m.classification == "TE"]
       sort by winrate descending
  5. wrong_moves = [m for m in candidates if m.classification in ("BM", "BM_HO")]
       sort by policy descending (most tempting traps first)
  6. Validate: len(correct_moves) >= 1 AND len(wrong_moves) >= 1
  7. Check miai: if len(correct_moves) >= 2 and gap < min_gap → set miai
  8. Build solution tree for each correct move (Topic 1 algorithm)
  9. Build refutation branches for top N wrong moves (existing logic)
```

### Topic 3: Solution Tree Branching — Not Just a Mainline

**Question:** v1 proposed building a single mainline PV (correct move → opponent → continuation). But real tsumego has branching: the opponent can respond differently, and each response needs its own correct continuation. How do we build a proper tree?

> **Cho Chikun:** "This is fundamental. A real tsumego solution is a tree, not a line. After Black's correct first move, White has perhaps 2-3 plausible responses. For EACH response, Black must have a correct follow-up. This branching is what makes tsumego tsumego. A single mainline is not a solution — it's a hint."

> **Lee Sedol:** "Cho sensei is absolutely right. But for a learning platform, you need to be practical about branching. At depth 1 (opponent's responses), include all moves where the opponent has a plausible alternative (policy > some threshold). At depth 2+, include the opponent's top 1-2 responses only. The tree explodes combinatorially otherwise. My guideline: at each opponent move, consider top 2-3 responses by policy. At each player move, there's usually only 1 correct follow-up (or the puzzle is over). So branching factor is ~2-3 at opponent nodes, ~1 at player nodes."

> **Shin Jinseo:** "The KataGo PV already gives you the mainline. For branching, you need to re-query at each opponent decision point. After playing the correct first move, analyze the resulting position. KataGo's top 2-3 moves for the opponent are the branches. For each branch, continue building the tree recursively until the stopping condition from Topic 1 triggers. Bound the total tree size: max_total_nodes or max_branching_width per opponent node."

> **Ke Jie:** "For beginners' puzzles, the solution tree is small — typically 1 mainline + 1-2 branches. For dan-level puzzles, it can be large. I'd suggest adaptive branching: at each opponent node, include responses where `policy > config.branch_min_policy`. For elementary puzzles this might be 1-2 branches; for advanced, 3-5. The policy threshold naturally adapts to difficulty."

> **Principal Staff Engineer A:** "Implementation design:
>
> ```
> build_solution_tree(engine, position, correct_move, depth=0, config):
>   if depth >= config.solution_max_depth: return leaf
>   if stopping_condition_met(position): return leaf
>
>   # Play the player's move
>   new_position = position + correct_move
>
>   # Analyze opponent's options
>   opp_analysis = engine.analyze(new_position, visits=config.tree_visits)
>   opp_branches = [m for m in opp_analysis.top_moves
>                   if m.policy >= config.branch_min_policy]
>   opp_branches = opp_branches[:config.max_branch_width]
>
>   children = []
>   for opp_move in opp_branches:
>     # For each opponent response, find player's best reply
>     after_opp = new_position + opp_move
>     player_analysis = engine.analyze(after_opp, visits=config.tree_visits)
>     player_best = player_analysis.top_move
>
>     # Recurse
>     subtree = build_solution_tree(
>       engine, after_opp, player_best, depth+2, config
>     )
>     children.append((opp_move, player_best, subtree))
>
>   return TreeNode(correct_move, children)
> ```
>
> Key config params: `branch_min_policy` (min opponent move policy to include as branch), `max_branch_width` (max branches per opponent node), `tree_visits` (visits per tree query, lower than solve_visits since these are follow-ups). Default: branch_min_policy=0.05, max_branch_width=3, tree_visits=500."

> **Principal Staff Engineer B:** "Performance: for a depth-10 tree with branching factor 2, that's ~2^5 = 32 leaf nodes, each requiring a query. At 200ms/query, that's ~6.4 seconds per puzzle. With max_branch_width=3 and depth=10, worst case is 3^5 = 243 queries = ~49 seconds. We MUST bound this. Proposal: `max_total_tree_queries` config parameter (default: 50). If the tree builder exceeds this, truncate remaining branches and mark them as `truncated` in the output. This caps worst-case at ~10 seconds per puzzle."

**Resolution:** Recursive tree building with configurable branching bounds.

```
Config defaults:
  branch_min_policy: 0.05      # Opponent moves below this policy are ignored
  max_branch_width: 3          # Max opponent responses per node
  tree_visits: 500             # Visits per follow-up query
  max_total_tree_queries: 50   # Hard cap on total engine queries per puzzle tree
  solution_min_depth: 3        # Don't stop before this depth
  solution_max_depth: 20       # Never exceed this depth
```

### Topic 4: What Does AI-Correctness (AC) Mean Now?

**Question:** v1 proposed `ac:0` (not AI-solved), `ac:1` (AI-solved), `ac:2` (human-verified). But now that ALL puzzles go through AI enrichment, what do the levels mean?

> **Lee Sedol:** "If every puzzle gets AI processing, then ac:0 means 'AI touched this puzzle but did not modify the solution.' ac:1 means 'AI built or extended the solution.' That's a meaningful distinction for quality control."

> **Cho Chikun:** "I would want four levels. Zero means untouched by AI entirely (legacy data or errors). One means AI enriched the puzzle metadata (difficulty, tags, hints) but did NOT change the solution tree. Two means AI built or extended the solution tree. Three means a human expert verified the AI's work. This progression matters for trust."

> **Ke Jie:** "I agree with Cho sensei's four levels. The key distinction is between 'AI looked at it and the existing solution was fine' versus 'AI had to create or modify the solution.' Users and quality reviewers need to know which puzzles have AI-generated solutions versus verified human solutions."

> **Principal Staff Engineer A:** "Four values. Clean semantics:
>
> | Value  | Label       | Meaning                                                                                               |
> | ------ | ----------- | ----------------------------------------------------------------------------------------------------- |
> | `ac:0` | `untouched` | AI pipeline has not processed this puzzle                                                             |
> | `ac:1` | `enriched`  | AI enriched metadata (difficulty, tags, hints, refutations) but used the existing solution tree as-is |
> | `ac:2` | `ai_solved` | AI built or extended the solution tree (correct move discovered or additional branches added)         |
> | `ac:3` | `verified`  | AI-solved puzzle reviewed and confirmed by human expert                                               |
>
> Default for all newly-processed puzzles: `ac:1` (enriched) if solution existed, `ac:2` (ai_solved) if solution was built. `ac:0` for puzzles never run through the pipeline. `ac:3` set only through explicit human review."

> **Principal Staff Engineer B:** "This also gives us a quality filter in the frontend. We could show 'AI-verified' badges for ac:3, flag ac:2 puzzles as 'AI-generated solution' for transparency, and allow filtering by quality tier. It's also useful for monitoring: track the ratio of ac:1 vs ac:2 in each collection."

**Resolution:** Four-level AC system.

```
ac:0 — untouched     — AI pipeline has NOT processed this puzzle
ac:1 — enriched      — AI enriched metadata but existing solution used as-is
ac:2 — ai_solved     — AI built or extended the solution tree
ac:3 — verified      — AI-solved puzzle confirmed by human expert

Wire format: YQ[q:2;rc:0;hc:0;ac:1]
Default:     ac:1 (existing solution) or ac:2 (AI-built solution)
```

### Topic 5: Algorithm Design — The Complete Pipeline

**Question:** Given Topics 1-4, what is the complete algorithm for processing ANY puzzle (with or without solution tree)?

> **Shin Jinseo:** "The unifying principle is: every puzzle gets the same pipeline. The only branch is whether we need to BUILD the solution tree (position-only) or VALIDATE and EXTEND the existing one (has solution). Here's my proposal:
>
> ```
> For each puzzle:
>   1. Parse SGF → extract position, metadata
>   2. pre = Analyze(position)         # Initial analysis
>   3. IF solution tree exists:
>        a. Validate existing correct move against pre.top_move
>        b. IF KataGo disagrees: flag for review, but keep human solution
>        c. Discover AI alternatives: moves with delta < T_good that aren't
>           in existing solution → append as alternative correct branches
>        d. Set ac = 1 (or ac = 2 if we extended the tree)
>      ELSE (position-only):
>        a. Classify all candidate moves by winrate delta
>        b. Select correct moves (delta < T_good)
>        c. Build full solution tree (Topic 1 + Topic 3 algorithm)
>        d. Inject solution tree into SGF
>        e. Set ac = 2
>   4. Build/extend refutation branches for wrong moves (delta > T_bad)
>   5. Estimate difficulty from signals
>   6. Generate teaching comments, hints, technique tags
>   7. Output enriched result
> ```
>
> The key insight: step 3c means even puzzles WITH existing solutions can get new correct branches appended. We never delete or replace human solutions — we only add.

> **Lee Sedol:** "I like Shin Jinseo's approach, but I want to emphasize step 3b. When KataGo disagrees with the human solution, DO NOT silently replace it. The human solution might reflect a specific teaching intent that KataGo doesn't understand (e.g., 'find the move that makes two eyes' versus 'find the move with highest winrate' — sometimes these differ because ko is better but the teacher wants the clean solution). Flag it, log it, but preserve the human solution. Only add alternatives, never delete."

> **Cho Chikun:** "Lee Sedol makes an excellent point. In classical tsumego pedagogy, the 'correct' answer sometimes excludes ko solutions intentionally, because the problem is testing whether the student can find the clean kill. KataGo might rank the ko as slightly better (higher winrate by 0.01) but that doesn't mean the clean kill is wrong. The pipeline should log disagreements but preserve the human author's intent."

> **Principal Staff Engineer A:** "Implementation: when KataGo's top move differs from the existing solution's correct move, we log a structured disagreement record:
>
> ```
> {
>   'type': 'solution_disagreement',
>   'puzzle_id': ...,
>   'human_move': 'D1',
>   'ai_move': 'E2',
>   'human_winrate': 0.93,
>   'ai_winrate': 0.95,
>   'delta': 0.02,
>   'action': 'preserved_human_added_ai_alternative'
> }
> ```
>
> If the delta is small (< T_disagreement, configurable), we keep the human solution and add KataGo's move as an alternative. If the delta is large (human move is actually LOSING), we flag for human review and set a flag in the result."

**Resolution:** Unified pipeline, additive-only for existing solutions.

```
Core algorithm:
  1. Analyze(position) → pre_metrics
  2. Classify candidate moves (correct/wrong/neutral)
  3a. IF has_solution: validate + extend (additive only, never delete)
  3b. IF position_only: build full solution tree
  4. Build refutation branches
  5. Difficulty + teaching enrichment

Rules:
  - NEVER delete or replace existing human solutions
  - AI alternatives are APPENDED, not substituted
  - Disagreements are LOGGED with structured records
  - If existing solution is LOSING (winrate < 0.3), flag for human review
```

### Topic 6: Winrate Delta Thresholds — Calibration Methodology

**Question:** What should T_good, T_bad, and T_hotspot be? How do we calibrate them?

> **Shin Jinseo:** "Start with theoretical values based on what a winrate swing means in practice:
>
> - T_good = 0.02 (2% winrate loss): in professional Go, a 2% winrate loss is already significant. In tsumego specifically, the correct move should lose essentially nothing — the position should remain won. 2% allows for some engine noise.
> - T_bad = 0.08 (8% winrate loss): a move that costs 8% winrate is decisively bad. The opponent can punish it. This aligns with the existing `refutations.delta_threshold = 0.08`.
> - T_hotspot = 0.25 (25% winrate loss): a catastrophic blunder. The group dies or a huge territory is lost.
>
> But these are starting points. They MUST be calibrated."

> **Ke Jie:** "For calibration, use a labeled dataset: take 100 puzzles where a human expert has marked the correct and wrong first moves. Run the classifier with various thresholds and measure precision/recall:
>
> - Precision: of moves classified as 'correct' (TE), what % are actually correct?
> - Recall: of actual correct moves, what % did we classify as TE?
>
> Sweep T_good from 0.01 to 0.10 in steps of 0.005. Pick the value that maximizes F1 score (harmonic mean of precision and recall). Do the same for T_bad with wrong moves. This is data-driven, not intuition-driven."

> **Principal Staff Engineer B:** "Calibration implementation:
>
> 1. Create a calibration fixture set: `tests/fixtures/calibration/labeled_moves.json`
> 2. Each entry: `{sgf, correct_moves: [...], wrong_moves: [...]}`
> 3. Calibration test sweeps thresholds, outputs precision/recall/F1 table
> 4. The test FAILS if F1 drops below a configured minimum (prevents regressions)
> 5. Threshold values stored in config, not hardcoded
>
> ````python
> @pytest.mark.calibration
> def test_threshold_calibration():
>     for t_good in np.arange(0.01, 0.10, 0.005):
>         for t_bad in np.arange(0.05, 0.20, 0.01):
>             precision, recall = evaluate(fixtures, t_good, t_bad)
>             f1 = 2 * precision * recall / (precision + recall)
>             results.append((t_good, t_bad, f1))
>     best = max(results, key=lambda r: r[2])
>     assert best[2] >= config.calibration.min_f1_score
> ```"
> ````

**Resolution:** Calibration-driven thresholds.

```
Initial values (to be calibrated):
  T_good:    0.02  (correct move threshold)
  T_bad:     0.08  (bad move threshold, aligned with refutations.delta_threshold)
  T_hotspot: 0.25  (blunder threshold)

Calibration method:
  1. Labeled fixture set (100+ puzzles with known correct/wrong moves)
  2. Threshold sweep: T_good ∈ [0.01, 0.10], T_bad ∈ [0.05, 0.20]
  3. Optimize for F1 score (precision × recall balance)
  4. Regression test: F1 must stay above configured minimum
  5. Re-calibrate when model changes (b18 → b28 may shift optimal thresholds)

Starting thresholds for pre-move analysis (from the brief):
  HIGH = 0.90  (pre-move winrate: position must be winning before wrong move)
  LOW  = 0.15  (post-move winrate: position must be losing after wrong move)
  These are SECONDARY gates, applied AFTER delta classification.
```

### Topic 7: How Existing Refutation Logic Already Picks Candidates

**Question (for documentation):** The existing pipeline already selects refutation candidates and controls depth. How exactly does this work today, and how does the solution tree builder mirror it?

**Current refutation selection** (`generate_refutations.py`):

```
1. identify_candidates():
   - Input: initial KataGo analysis of position
   - Filter: exclude correct move + pass, policy >= 0.0 (no floor)
   - Spatial: if locality_max_distance > 0, only moves within
     Chebyshev distance 2 of existing stones
   - Sort: policy_prior descending (most tempting traps first)
   - Cap: candidate_max_count = 5

2. generate_single_refutation(wrong_move):
   - Play the wrong move on the position
   - Analyze resulting position (100 visits)
   - Get opponent's best response (= the punishment)
   - Compute winrate_delta = after_wr - initial_wr
   - If |delta| < delta_threshold (0.08): skip (not punishing enough)
   - Extract PV cap at max_pv_length = 4 moves
   - Return Refutation with wrong_move, PV, delta, depth

3. generate_refutations() orchestrator:
   - Merge curated wrong branches (from SGF) + AI-discovered branches
   - Curated first (trusted), then AI
   - Cap at refutation_max_count = 3
   - If < min_refutations_required (1): escalate with higher visits
   - Escalation: 500 visits, relaxed delta 0.03, referee engine
```

**Solution tree builder mirrors this inverted:**

```
1. identify_correct_candidates():
   - Input: initial KataGo analysis (same query, reused)
   - Filter: all moves with winrate above threshold
   - Sort: winrate descending (best moves first, NOT policy)
   - Cap: max_correct_moves = 2

2. build_solution_branch(correct_move):
   - Play the correct move on the position
   - Analyze resulting position (tree_visits = 500)
   - Get opponent's top 1-3 responses (policy > branch_min_policy)
   - For EACH opponent response:
     - Analyze after-opponent position
     - Find player's best follow-up (top winrate)
     - Recurse until stopping condition
   - Natural depth: controlled by winrate stability + hard cap

3. assemble_solution_tree():
   - For each correct first move: build its solution branch
   - Merge with existing human solution (if present, additive-only)
   - Mark new branches as AI-generated in metadata
```

### Topic 8: No Separate `--allow-ai-solve` Flag

> **Principal Staff Engineer A:** "In v1, we proposed `--allow-ai-solve` as an opt-in flag. But the user correctly identified that this creates a false dichotomy. Every puzzle goes through:
>
> 1. Check for correct first move → if missing, build it
> 2. Validate existing correct move → if present, verify + extend
>
> This is not optional. It's the standard pipeline behavior. The 'AI-solve' path is just the else-branch of 'has solution tree.' No flag needed."

> **Principal Staff Engineer B:** "The config still has `ai_solve.enabled` as a feature gate during development/testing. But in production, this defaults to `true`. The flag's purpose is allowing rollback if we discover quality issues, not for day-to-day operation. Once calibrated and stable, it becomes a dead letter."

**Resolution:** Remove `--allow-ai-solve` CLI flag. Feature gated via `config.ai_solve.enabled` during development (default: `false` initially, `true` after calibration passes). No separate CLI override.

---

## Architecture

### Unified Pipeline Flow

```
Step 1:  Parse SGF & extract metadata (UNCHANGED)
Step 2:  Extract correct first move
         ├── v2.1 EDGE-4: Reject if pass is best move (trivial/malformed puzzle)
         ├── IF solution tree exists:
         │     a. Extract existing correct move(s) as today
         │     b. Validate against KataGo (existing Step 5 logic)
         │     c. Discover AI alternative correct moves (NEW)
         │     d. Build extended solution branches for alternatives IN PARALLEL (v2.1 STR-4)
         │     e. Append new branches (additive only) (NEW)
         │     f. Set human_solution_confidence (v2.1 ALG-6)
         │     g. Set ac = 1 (no changes) or ac = 2 (extended)
         │        - v2.1 ALG-4: downgrade to ac=1 if tree truncated < min_depth
         │     h. Set ai_solution_validated boolean (v2.1 AC-1)
         └── IF no solution tree:
               a. Analyze position with KataGo (v2.1 STR-1: pre-filter by policy)
               b. Classify all candidate moves (TE / BM / BM_HO / neutral)
                  - v2.1 ALG-3: delta-only classification, no absolute winrate gates
               c. Build full solution tree for correct move(s) (NEW)
                  - v2.1 EDGE-2: seki detection stopping condition
                  - v2.1 ALG-4: track tree completeness
               d. Build refutation branches for wrong moves (NEW)
               e. Inject complete tree into SGF
               f. v2.1 STR-5: Assert roundtrip (extract succeeds after inject)
               g. Set ac = 2 (or 1 if tree incomplete, v2.1 ALG-4)
Step 3:  Build analysis query with tsumego frame (UNCHANGED)
Step 4:  Run dual-engine analysis (UNCHANGED — reuse pre-analysis from Step 2)
Step 5:  Validate correct move (MODIFIED — uses pre-classified data)
Step 6:  Generate refutations (MODIFIED — uses pre-classified wrong moves)
Step 7:  Estimate difficulty (UNCHANGED)
Step 8:  Assemble result (MODIFIED — includes ac field, ai_solution_validated,
         human_solution_confidence, co_correct_detected)
Step 9:  Teaching enrichment (UNCHANGED)
Step 10: v2.1 LOG-1/LOG-2: Emit batch summary, write disagreement sink
```

### New Module: `analyzers/solve_position.py`

```python
"""AI-Solve: Discover and build solution trees for any puzzle.

Unified enrichment: whether a puzzle has an existing solution tree or not,
this module can:
  1. Discover correct first move(s) by winrate analysis
  2. Build full branching solution trees (not just mainline PV)
  3. Discover AI alternatives to existing solutions (additive only)
  4. Classify all candidate moves (TE/BM/BM_HO/neutral)

This is the functional inverse of generate_refutations.py:
  - Refutations: find moves where Δwr is large and NEGATIVE → build punishment
  - AI-Solve:    find moves where winrate is HIGHEST → build continuation

Solution trees follow natural stopping (winrate stability, ownership convergence)
with config-driven hard caps. Branching occurs at opponent decision points.

All thresholds loaded from config/katago-enrichment.json → ai_solve section.
"""
```

#### Core Functions

```python
async def analyze_position_candidates(
    engine: LocalEngine,
    position: Position,
    config: EnrichmentConfig,
    puzzle_id: str = "",
) -> PositionAnalysis:
    """Analyze position and classify all candidate moves.

    Runs high-visit analysis on initial position, then for each top-K
    candidate move, runs confirmation analysis to compute precise deltas.

    Returns PositionAnalysis with all moves classified as TE/BM/BM_HO/neutral,
    root metrics, and difficulty signals.

    This is the central analysis that both solution-building AND refutation-building
    share. Run once, use for both paths.
    """


async def build_solution_tree(
    engine: LocalEngine,
    position: Position,
    correct_move_gtp: str,
    config: EnrichmentConfig,
    depth: int = 0,
    query_budget: QueryBudget,  # v2.1 MIN-2: required, not optional
) -> SolutionNode:
    """Build a branching solution tree starting from correct_move.

    Recursive: plays correct_move → analyzes opponent responses →
    for each plausible opponent response (policy > branch_min_policy):
      → find player's best reply → recurse.

    Stops when:
      - Winrate stability: |Δwr| < wr_epsilon for 2 consecutive moves
      - Ownership convergence: key stones change < own_epsilon
      - Seki detection: winrate in [0.45, 0.55] for 3+ consecutive depths (v2.1 EDGE-2)
      - Hard cap: solution_max_depth reached
      - Budget: max_total_tree_queries exhausted
      - Terminal: pass in PV or no legal moves in region

    Does NOT stop before solution_min_depth.

    v2.1 ALG-4: If budget exhausts before solution_min_depth, sets
    confidence='low' and prevents ac:2 (returns tree with
    tree_completeness < 1.0).

    v2.1 MIN-4: All winrates normalized to puzzle player (PL[])
    perspective. Uses normalize_winrate() helper.
    """


def normalize_winrate(
    winrate: float,
    reported_player: str,
    puzzle_player: str,
) -> float:
    """Normalize winrate to puzzle player's perspective. (v2.1 MIN-4)

    KataGo reports winrate from side-to-move perspective.
    If reported_player != puzzle_player, invert: wr = 1.0 - wr.
    Convention: all winrates in this module are from PL[] perspective.
    """


def classify_move_quality(
    pre_analysis: AnalysisResponse,
    move_analysis: MoveAnalysis,
    root_winrate: float,
    player_color: Color,
    config: EnrichmentConfig,
) -> MoveClassification:
    """Classify a single move using winrate delta thresholds.

    Computes delta = pre_winrate - post_winrate (sign-adjusted by player color
    via normalize_winrate()). (v2.1 MIN-4)
    Applies config thresholds: T_good → TE, T_bad → BM, T_hotspot → BM+HO.

    v2.1 ALG-3: pre_winrate_floor and post_winrate_ceiling are NOT used
    as classification gates. They are computed and attached as confidence
    metrics to PositionAnalysis only. Delta-based classification dominates.

    v2.1 STR-1: Only confirms moves with policy >= confirmation_min_policy.
    Moves below this floor skip confirmation queries.
    "


def inject_solution_into_sgf(
    root: SgfNode,
    solution_tree: SolutionNode,
    wrong_moves: list[MoveClassification],
    existing_solution_preserved: bool = True,
) -> None:
    """Mutate parsed SGF tree: add/extend solution and wrong branches.

    For position-only puzzles: inject complete solution tree + wrong branches.
    For puzzles with existing solutions: append AI alternatives (additive only).

    Never deletes existing children. New branches get AI-generated markers.
    """


async def discover_alternatives(
    engine: LocalEngine,
    position: Position,
    existing_correct_move_gtp: str,
    pre_analysis: AnalysisResponse,
    config: EnrichmentConfig,
) -> list[SolvedMove]:
    """Find AI alternative correct moves not in existing solution.

    Checks if any move OTHER than existing_correct_move also classifies as TE.
    If found, builds solution branches for those alternatives.
    Returns empty list if no alternatives found (common for well-defined puzzles).
    """
```

### New Models: `models/solve_result.py`

```python
class QueryBudget(BaseModel):
    """Tracks engine query budget to prevent runaway tree building."""
    max_queries: int = 50
    queries_used: int = 0

    def can_query(self) -> bool:
        return self.queries_used < self.max_queries

    def use(self) -> None:
        self.queries_used += 1


class SolutionNode(BaseModel):
    """A node in the solution tree. Recursive structure."""
    move_sgf: str                        # SGF coordinate (e.g., "ac")
    move_gtp: str                        # GTP coordinate (e.g., "A3")
    player: str                          # "B" or "W"
    winrate: float                       # Winrate after this move (PL[] perspective, v2.1 MIN-4)
    score_lead: float                    # Score lead after this move
    policy_prior: float                  # Neural net policy prior
    depth: int                           # Depth in the tree (0 = first move)
    is_correct: bool                     # True for player's correct moves
    comment: str = ""                    # "Correct" / "Wrong" / teaching text
    children: list['SolutionNode'] = []  # Opponent responses → player follow-ups
    truncated: bool = False              # True if branch was cut by budget/depth
    tree_completeness: TreeCompletenessMetrics | None = None  # v2.1 ALG-4: completeness tracking (root only)


class MoveClassification(BaseModel):
    """Quality classification for a candidate move."""
    move_gtp: str
    move_sgf: str
    winrate: float
    winrate_delta: float          # Δwr from root (sign-adjusted by player color)
    score_delta: float            # Δscore from root
    policy_prior: float
    visits: int
    classification: str           # "TE" | "BM" | "BM_HO" | "neutral"


class SolvedMove(BaseModel):
    """A correct first move discovered by KataGo."""
    move_sgf: str
    move_gtp: str
    winrate: float
    score_lead: float
    policy_prior: float
    visits: int
    solution_tree: SolutionNode | None = None  # Full branching tree
    confidence: str               # "high" | "medium" | "low"
    is_alternative: bool = False  # True if discovered as alternative to existing solution


class PositionAnalysis(BaseModel):
    """Complete analysis of a position with all moves classified."""
    puzzle_id: str
    root_winrate: float
    root_score: float
    player_color: str
    correct_moves: list[SolvedMove]
    wrong_moves: list[MoveClassification]
    all_classifications: list[MoveClassification]
    solve_visits: int
    goal_inference: str     # "kill" | "live" | "ko" | "capture" | "unknown"
    has_existing_solution: bool
    ai_alternatives_found: int
    co_correct_detected: bool = False        # v2.1 ALG-5: renamed from miai_detected
    root_winrate_confidence: str = "high"    # v2.1 ALG-3: "high"|"medium"|"low"
    goal_confidence: str = "high"            # v2.1 ALG-7: "high"|"medium"|"low"
    ladder_suspected: bool = False           # v2.1 EDGE-3: ladder detected in PV
    ai_solution_validated: bool = False      # v2.1 AC-1: AI checked existing solution


class TreeCompletenessMetrics(BaseModel):
    """v2.1 ALG-4: Track solution tree completeness for confidence."""
    total_attempted_branches: int = 0
    completed_branches: int = 0
    max_reached_depth: int = 0
    budget_exhausted: bool = False
    completeness_ratio: float = 1.0  # completed / total

    def is_complete(self) -> bool:
        return self.completeness_ratio >= 0.8 and not self.budget_exhausted


class BatchSummary(BaseModel):
    """v2.1 LOG-1: Structured batch-level summary for observability."""
    total_puzzles: int = 0
    ac_distribution: dict[int, int] = {}  # {0: N, 1: N, 2: N}
    avg_tree_depth: float = 0.0
    avg_queries_per_puzzle: float = 0.0
    disagreement_count: int = 0
    co_correct_count: int = 0
    truncation_count: int = 0
    pass_move_rejected: int = 0  # v2.1 EDGE-4
    errors: int = 0
    collection_disagreement_summary: dict[str, dict] = {}  # v2.1 ALG-9


class DisagreementRecord(BaseModel):
    """v2.1 LOG-2: Structured disagreement for JSONL sink."""
    puzzle_id: str
    collection: str
    human_move: str
    ai_move: str
    human_winrate: float
    ai_winrate: float
    delta: float
    action: str  # "preserved_human_added_ai_alternative" | "flagged_losing" | ...
    human_solution_confidence: str  # v2.1 ALG-6: "strong"|"weak"|"losing"
    timestamp: str
```

---

## Config Changes: `ai_solve` Section

**File:** `config/katago-enrichment.json`  
**Schema version bump:** `1.13` → `1.14`  
**Changelog entry (v2.1 MIN-1 — expanded):**

```
"v1.14": {
  "summary": "AI-Solve: unified puzzle enrichment with full solution tree building.",
  "added": [
    "ai_solve config section (enabled, visits, thresholds, solution_tree, alternatives)",
    "ai_solve.confidence_metrics — pre/post winrate as annotation, not gates (v2.1 ALG-3)",
    "ai_solve.seki_detection — seki-specific stopping condition (v2.1 EDGE-2)",
    "ai_solve.edge_case_boosts — corner/ladder visit boosts (v2.1 EDGE-1/EDGE-3)",
    "ai_solve.calibration — model-aware threshold profiles (v2.1 ALG-8)",
    "ai_solve.observability — batch summaries, disagreement sink (v2.1 LOG-1/LOG-2)",
    "YQ ac:0-3 field for AI correctness quality tracking",
    "co_correct_score_gap for multi-signal co-correct detection (v2.1 ALG-5)",
    "confirmation_min_policy for fast pre-filtering (v2.1 STR-1)"
  ],
  "moved": [
    "pre_winrate_floor → confidence_metrics.pre_winrate_high (no longer a gate)"
  ],
  "backward_compatibility": "Fully backward compatible. Missing ai_solve key → None → disabled. No migration required.",
  "feature_gate": "ai_solve.enabled defaults to false. Enable after calibration passes."
}
```

```json
{
  "ai_solve": {
    "description": "AI-Solve: unified enrichment for all puzzles. Builds solution trees, classifies moves, discovers alternatives. Feature-gated (default: disabled during development).",
    "enabled": false,
    "solve_visits": 1000,
    "confirmation_visits": 500,
    "confirmation_min_policy": 0.03,
    "candidate_count": 10,
    "max_correct_moves": 2,
    "min_winrate_gap": 0.15,
    "co_correct_score_gap": 3.0,

    "thresholds": {
      "description": "Move classification thresholds (calibration-driven). See Topic 6. v2.1 ALG-3: pre/post absolute values are confidence metrics, NOT classification gates.",
      "T_good": 0.02,
      "T_bad": 0.08,
      "T_hotspot": 0.25,
      "T_disagreement": 0.05
    },

    "confidence_metrics": {
      "description": "v2.1 ALG-3/STR-2: Absolute winrate thresholds for confidence annotation only. NOT used as classification gates — delta-based classification dominates.",
      "pre_winrate_high": 0.9,
      "pre_winrate_medium": 0.7,
      "post_winrate_ceiling": 0.15
    },

    "solution_tree": {
      "description": "Solution tree building parameters. See Topics 1 and 3.",
      "solution_min_depth": 3,
      "solution_max_depth": 20,
      "branch_min_policy": 0.05,
      "max_branch_width": 3,
      "tree_visits": 500,
      "max_total_tree_queries": 50,
      "winrate_stability_epsilon": 0.02,
      "ownership_stability_epsilon": 0.05,
      "confirmation_moves_past_decisive": 2
    },

    "seki_detection": {
      "description": "v2.1 EDGE-2: Seki-specific early-exit heuristic for solution tree builder.",
      "winrate_seki_band": [0.45, 0.55],
      "score_lead_seki_max": 2.0,
      "seki_consecutive_depth": 3
    },

    "goal_inference": {
      "description": "Thresholds for inferring puzzle goal from KataGo analysis. v2.1 ALG-7: multi-signal — score delta primary, ownership secondary with variance gate.",
      "score_delta_kill_threshold": 15.0,
      "ownership_alive_threshold": 0.7,
      "ownership_dead_threshold": -0.7,
      "ownership_variance_threshold": 0.15
    },

    "edge_case_boosts": {
      "description": "v2.1 EDGE-1/EDGE-3: Additional visit budgets for known difficult cases.",
      "corner_position_visit_boost": 500,
      "ladder_visit_boost": 500,
      "ladder_pv_length_threshold": 8
    },

    "alternatives": {
      "description": "AI alternative discovery for puzzles with existing solutions.",
      "discover_alternatives": true,
      "max_alternatives": 2,
      "flag_disagreement_delta": 0.1,
      "flag_losing_winrate": 0.3
    },

    "calibration": {
      "description": "v2.1 ALG-8/CAL-1/CAL-2/CAL-3: Calibration methodology requirements.",
      "min_te_samples": 30,
      "min_bm_samples": 30,
      "min_neutral_samples": 30,
      "target_macro_f1": 0.85,
      "calibration_visit_counts": [500, 1000, 2000],
      "model_profiles": {
        "description": "Threshold overrides by KataGo model hash. Empty = use defaults."
      }
    },

    "observability": {
      "description": "v2.1 LOG-1/LOG-2/ALG-9: Batch-level logging and disagreement sink.",
      "disagreement_sink_path": ".pm-runtime/logs/disagreements/",
      "collection_disagreement_warning_threshold": 0.2,
      "emit_batch_summary": true
    }
  }
}
```

### Pydantic Models (in `config.py`)

```python
class AiSolveThresholds(BaseModel):
    """Move classification thresholds. v2.1 ALG-3: pre/post removed (see ConfidenceMetrics)."""
    T_good: float = 0.02
    T_bad: float = 0.08
    T_hotspot: float = 0.25
    T_disagreement: float = 0.05


class AiSolveConfidenceMetrics(BaseModel):
    """v2.1 ALG-3/STR-2: Absolute winrate thresholds as confidence annotations only."""
    pre_winrate_high: float = 0.90
    pre_winrate_medium: float = 0.70
    post_winrate_ceiling: float = 0.15


class SolutionTreeConfig(BaseModel):
    solution_min_depth: int = 3
    solution_max_depth: int = 20
    branch_min_policy: float = 0.05
    max_branch_width: int = 3
    tree_visits: int = 500
    max_total_tree_queries: int = 50
    winrate_stability_epsilon: float = 0.02
    ownership_stability_epsilon: float = 0.05
    confirmation_moves_past_decisive: int = 2


class SekiDetectionConfig(BaseModel):
    """v2.1 EDGE-2: Seki-specific stopping condition."""
    winrate_seki_band: tuple[float, float] = (0.45, 0.55)
    score_lead_seki_max: float = 2.0
    seki_consecutive_depth: int = 3


class AiSolveAlternativesConfig(BaseModel):
    discover_alternatives: bool = True
    max_alternatives: int = 2
    flag_disagreement_delta: float = 0.10
    flag_losing_winrate: float = 0.30


class AiSolveGoalInference(BaseModel):
    """v2.1 ALG-7: Multi-signal goal inference."""
    score_delta_kill_threshold: float = 15.0
    ownership_alive_threshold: float = 0.7
    ownership_dead_threshold: float = -0.7
    ownership_variance_threshold: float = 0.15  # v2.1 ALG-7


class EdgeCaseBoosts(BaseModel):
    """v2.1 EDGE-1/EDGE-3: Visit boosts for known difficult cases."""
    corner_position_visit_boost: int = 500
    ladder_visit_boost: int = 500
    ladder_pv_length_threshold: int = 8


class CalibrationConfig(BaseModel):
    """v2.1 ALG-8/CAL-1/CAL-2/CAL-3."""
    min_te_samples: int = 30
    min_bm_samples: int = 30
    min_neutral_samples: int = 30
    target_macro_f1: float = 0.85
    calibration_visit_counts: list[int] = [500, 1000, 2000]
    model_profiles: dict[str, dict] = {}  # model_hash → threshold overrides


class ObservabilityConfig(BaseModel):
    """v2.1 LOG-1/LOG-2/ALG-9."""
    disagreement_sink_path: str = ".pm-runtime/logs/disagreements/"
    collection_disagreement_warning_threshold: float = 0.20
    emit_batch_summary: bool = True


class AiSolveConfig(BaseModel):
    """Unified AI enrichment configuration. v2.1 amendments integrated."""
    enabled: bool = False
    solve_visits: int = 1000
    confirmation_visits: int = 500
    confirmation_min_policy: float = 0.03  # v2.1 STR-1
    candidate_count: int = 10
    max_correct_moves: int = 2
    min_winrate_gap: float = 0.15
    co_correct_score_gap: float = 3.0  # v2.1 ALG-5
    thresholds: AiSolveThresholds = AiSolveThresholds()
    confidence_metrics: AiSolveConfidenceMetrics = AiSolveConfidenceMetrics()  # v2.1 ALG-3
    solution_tree: SolutionTreeConfig = SolutionTreeConfig()
    seki_detection: SekiDetectionConfig = SekiDetectionConfig()  # v2.1 EDGE-2
    goal_inference: AiSolveGoalInference = AiSolveGoalInference()
    edge_case_boosts: EdgeCaseBoosts = EdgeCaseBoosts()  # v2.1 EDGE-1/EDGE-3
    alternatives: AiSolveAlternativesConfig = AiSolveAlternativesConfig()
    calibration: CalibrationConfig = CalibrationConfig()  # v2.1 ALG-8
    observability: ObservabilityConfig = ObservabilityConfig()  # v2.1 LOG-1/LOG-2
```

---

## Quality Tracking: AC (AI Correctness) — 4-Level System

### YQ Extension

| Value  | Label     | Meaning                                                                                      | When Set                                           |
| ------ | --------- | -------------------------------------------------------------------------------------------- | -------------------------------------------------- |
| `ac:0` | untouched | AI pipeline has NOT processed this puzzle                                                    | Legacy data, errors, skipped                       |
| `ac:1` | enriched  | AI enriched metadata (difficulty, tags, hints, refutations) but existing solution used as-is | Puzzle with valid solution, KataGo agrees          |
| `ac:2` | ai_solved | AI built or extended the solution tree (new correct moves or branches added)                 | Position-only puzzles, or AI alternatives appended |
| `ac:3` | verified  | AI-solved puzzle confirmed correct by human expert                                           | Manual review process                              |

**Wire format:** `YQ[q:2;rc:0;hc:0;ac:1]`

**Decision logic (v2.1 amended):**

```python
if not ai_solve_enabled:
    ac = 0  # untouched
elif has_existing_solution and not tree_extended:
    ac = 1  # enriched only
    # v2.1 AC-1: set ai_solution_validated=True if AI agrees with human solution
    ai_solution_validated = (ai_agrees_within_T_disagreement)
elif tree_built_or_extended:
    # v2.1 ALG-4: downgrade if tree incomplete
    if tree_completeness.budget_exhausted and tree_completeness.max_reached_depth < solution_min_depth:
        ac = 1  # NOT ai_solved — tree too shallow
        confidence = "low"
    else:
        ac = 2  # ai_solved
# ac = 3 only via human review tool (not set by pipeline)
# v2.1 AC-2: ac:3 workflow (review tool, queue, interface) is OUT OF SCOPE
# for this plan — tracked as future work. Do not set ac:3 programmatically.
```

**v2.1 ALG-6: Human solution confidence metadata:**

```python
# Set alongside AC level when existing solution exists
if human_move_winrate >= ai_move_winrate - T_disagreement:
    human_solution_confidence = "strong"  # AI agrees
elif human_move_winrate > 0.5:
    human_solution_confidence = "weak"    # Human still winning, AI is better
else:
    human_solution_confidence = "losing"  # Human move is objectively losing
```

---

## Logging Contract

All AI-Solve operations follow existing `log_with_context()` patterns.

```python
# Stage entry
log_with_context(logger, "INFO", "AI-Solve: analyzing position",
    puzzle_id=puzzle_id, stage="ai_solve", visits=config.ai_solve.solve_visits)

# Move classification
log_with_context(logger, "DEBUG", "Move %s → %s (Δwr=%.3f, policy=%.4f)",
    move_gtp, classification, winrate_delta, policy_prior,
    puzzle_id=puzzle_id, stage="ai_solve")

# v2.1 STR-1: Pre-filter skip logging
log_with_context(logger, "DEBUG", "Skipping confirmation for %s (policy=%.4f < min=%.4f)",
    move_gtp, policy_prior, config.ai_solve.confirmation_min_policy,
    puzzle_id=puzzle_id, stage="ai_solve")

# Solution tree building
log_with_context(logger, "INFO", "Building solution tree: depth=%d, branches=%d, queries=%d/%d",
    current_depth, branch_count, budget.queries_used, budget.max_queries,
    puzzle_id=puzzle_id, stage="ai_solve")

# v2.1 ALG-4: Truncation with confidence downgrade
log_with_context(logger, "WARNING", "Tree truncated: budget exhausted at depth=%d (min_depth=%d), confidence=low",
    max_reached_depth, config.ai_solve.solution_tree.solution_min_depth,
    puzzle_id=puzzle_id, stage="ai_solve")

# v2.1 EDGE-2: Seki detection
log_with_context(logger, "INFO", "Seki detected: wr=%.3f in band [%.2f, %.2f] for %d consecutive depths",
    winrate, seki_band[0], seki_band[1], consecutive_count,
    puzzle_id=puzzle_id, stage="ai_solve")

# v2.1 EDGE-4: Pass move rejection
log_with_context(logger, "WARNING", "Position already resolved: pass is best move (wr=%.3f)",
    pass_winrate, puzzle_id=puzzle_id, stage="ai_solve")

# Disagreement detection
log_with_context(logger, "WARNING", "Solution disagreement: human=%s (wr=%.3f), ai=%s (wr=%.3f), delta=%.3f",
    human_move, human_wr, ai_move, ai_wr, delta,
    puzzle_id=puzzle_id, stage="ai_solve")

# Structured disagreement record (JSON log)
log_with_context(logger, "INFO", "disagreement_record",
    puzzle_id=puzzle_id, stage="ai_solve",
    human_move=human_move, ai_move=ai_move,
    human_winrate=human_wr, ai_winrate=ai_wr,
    delta=delta, action=action)
```

### v2.1 LOG-2: Disagreement Sink

Disagreements are written to a JSONL file for human review:

```python
# File: .pm-runtime/logs/disagreements/{run_id}.jsonl
# One JSON record per line, append-only
disagreement_sink.write(DisagreementRecord(
    puzzle_id=puzzle_id,
    collection=collection_id,
    human_move=human_move, ai_move=ai_move,
    human_winrate=human_wr, ai_winrate=ai_wr,
    delta=delta, action=action,
    human_solution_confidence=confidence,  # v2.1 ALG-6
    timestamp=datetime.utcnow().isoformat(),
))
```

### v2.1 LOG-1: Batch Summary

Every enrichment batch emits a structured summary at completion:

```python
# Emitted as structured JSON at INFO level after each batch
log_with_context(logger, "INFO", "batch_summary",
    stage="ai_solve",
    total_puzzles=summary.total_puzzles,
    ac_distribution=summary.ac_distribution,
    avg_tree_depth=summary.avg_tree_depth,
    avg_queries_per_puzzle=summary.avg_queries_per_puzzle,
    disagreement_count=summary.disagreement_count,
    co_correct_count=summary.co_correct_count,
    truncation_count=summary.truncation_count,
    pass_move_rejected=summary.pass_move_rejected,
    errors=summary.errors,
    collection_disagreement_summary=summary.collection_disagreement_summary,
)
```

### v2.1 ALG-9: Collection-Level Disagreement Monitoring

```python
# After batch completion, check per-collection disagreement rates
for collection_id, stats in summary.collection_disagreement_summary.items():
    pct = stats["disagreements"] / stats["total"] if stats["total"] > 0 else 0
    if pct > config.ai_solve.observability.collection_disagreement_warning_threshold:
        log_with_context(logger, "WARNING",
            "Collection %s has %.1f%% disagreement rate (%d/%d) — needs human review",
            collection_id, pct * 100, stats["disagreements"], stats["total"],
            stage="ai_solve")
```

---

## Integration Point: `enrich_single.py` Step 2

Replace the hard rejection with unified processing:

```python
    # ---------------------------------------------------------------
    # Step 2: Extract correct first move and solution tree
    # ---------------------------------------------------------------
    correct_move_sgf = extract_correct_first_move(root)
    position = extract_position(root)
    board_size = position.board_size
    ai_solved = False
    tree_extended = False

    if config.ai_solve and config.ai_solve.enabled:
        # Unified AI processing for ALL puzzles
        from analyzers.solve_position import (
            analyze_position_candidates,
            build_solution_tree,
            inject_solution_into_sgf,
            discover_alternatives,
        )

        t_solve_start = time.monotonic()

        # Pre-analysis: classify all candidate moves
        # v2.1 STR-1: confirmation_min_policy pre-filters low-policy moves
        position_analysis = await analyze_position_candidates(
            engine=engine_manager.get_engine(),
            position=position,
            config=config,
            puzzle_id=puzzle_id,
        )

        # v2.1 EDGE-4: Reject if pass is the best move (puzzle is trivial/malformed)
        if position_analysis.correct_moves and position_analysis.correct_moves[0].move_gtp == "pass":
            return _make_error_result(
                "AI-Solve: position already resolved (pass is best move)",
                puzzle_id=puzzle_id, source_file=source_file,
                trace_id=trace_id, run_id=run_id,
            )

        if correct_move_sgf is None:
            # POSITION-ONLY: build full solution tree
            if not position_analysis.correct_moves:
                return _make_error_result(
                    "AI-Solve: no confident correct move found",
                    puzzle_id=puzzle_id, source_file=source_file,
                    trace_id=trace_id, run_id=run_id,
                )

            # Build full branching solution tree for each correct move
            # v2.1 MIN-2: QueryBudget is required, not optional
            for cm in position_analysis.correct_moves:
                cm.solution_tree = await build_solution_tree(
                    engine=engine_manager.get_engine(),
                    position=position,
                    correct_move_gtp=cm.move_gtp,
                    config=config,
                    query_budget=QueryBudget(
                        max_queries=config.ai_solve.solution_tree.max_total_tree_queries
                    ),
                )

            inject_solution_into_sgf(
                root,
                position_analysis.correct_moves[0].solution_tree,
                position_analysis.wrong_moves,
            )
            # v2.1 STR-5: Defensive assertion — verify roundtrip
            correct_move_sgf = extract_correct_first_move(root)
            assert correct_move_sgf is not None, \
                "Injection produced unparseable solution tree"

            # v2.1 ALG-4: Check tree completeness before claiming ai_solved
            tree_metrics = position_analysis.correct_moves[0].solution_tree.tree_completeness
            if tree_metrics and tree_metrics.budget_exhausted and \
               tree_metrics.max_reached_depth < config.ai_solve.solution_tree.solution_min_depth:
                ai_solved = False  # Downgrade — tree too shallow
                tree_confidence = "low"
            else:
                ai_solved = True

        else:
            # HAS SOLUTION: validate + discover alternatives
            correct_move_gtp = sgf_to_gtp(correct_move_sgf, board_size)

            alternatives = await discover_alternatives(
                engine=engine_manager.get_engine(),
                position=position,
                existing_correct_move_gtp=correct_move_gtp,
                pre_analysis=position_analysis,
                config=config,
            )

            if alternatives:
                # v2.1 STR-4: Build solution trees in parallel with split budgets
                budgets = [
                    QueryBudget(
                        max_queries=config.ai_solve.solution_tree.max_total_tree_queries
                                    // len(alternatives)
                    )
                    for _ in alternatives
                ]
                tree_tasks = [
                    build_solution_tree(
                        engine=engine_manager.get_engine(),
                        position=position,
                        correct_move_gtp=alt.move_gtp,
                        config=config,
                        query_budget=budget,
                    )
                    for alt, budget in zip(alternatives, budgets)
                ]
                trees = await asyncio.gather(*tree_tasks)
                for alt, tree in zip(alternatives, trees):
                    alt.solution_tree = tree

                inject_solution_into_sgf(
                    root, None, [],
                    alternative_moves=alternatives,
                )
                tree_extended = True

        timings["ai_solve"] = time.monotonic() - t_solve_start

    elif correct_move_sgf is None:
        # AI-Solve disabled and no solution → reject as before
        return _make_error_result(
            "No correct first move found in SGF",
            puzzle_id=puzzle_id, source_file=source_file,
            trace_id=trace_id, run_id=run_id,
        )

    # Set AC level (v2.1 amended: truncation downgrade, validation boolean)
    ai_solution_validated = False
    human_solution_confidence = None
    if ai_solved:
        ac_level = 2
    elif tree_extended:
        ac_level = 2
    elif config.ai_solve and config.ai_solve.enabled:
        ac_level = 1  # enriched metadata only
        # v2.1 AC-1: Track whether AI validated the existing solution
        if correct_move_sgf is not None and position_analysis:
            ai_solution_validated = True
            # v2.1 ALG-6: Compute human solution confidence
            cm_gtp = sgf_to_gtp(correct_move_sgf, board_size)
            ai_top = position_analysis.correct_moves[0] if position_analysis.correct_moves else None
            if ai_top and ai_top.move_gtp != cm_gtp:
                delta = ai_top.winrate - _get_move_winrate(position_analysis, cm_gtp)
                if delta < config.ai_solve.thresholds.T_disagreement:
                    human_solution_confidence = "strong"
                elif _get_move_winrate(position_analysis, cm_gtp) > 0.5:
                    human_solution_confidence = "weak"
                else:
                    human_solution_confidence = "losing"
            else:
                human_solution_confidence = "strong"
    else:
        ac_level = 0  # untouched
```

---

## Validation Checklist

### Config & Schema

- [ ] `config/katago-enrichment.json` bumped to v1.14 with `ai_solve` section
- [ ] `AiSolveConfig` Pydantic model validates against JSON
- [ ] Config with NO `ai_solve` key → `None` → fully backward compatible
- [ ] All thresholds read from config, zero hardcoded values
- [ ] v2.1 ALG-3: `pre_winrate_floor` moved to `confidence_metrics`, NOT used as gate
- [ ] v2.1 STR-1: `confirmation_min_policy` present in config, wired into candidate loop
- [ ] v2.1 EDGE-2: `seki_detection` config section present and validated
- [ ] v2.1 ALG-8: `calibration` section with model profiles and stratified sampling
- [ ] v2.1 LOG-1/LOG-2: `observability` section with disagreement sink path

### Unified Pipeline

- [ ] Position-only SGF + `ai_solve.enabled=true` → solution tree built → full enrichment succeeds
- [ ] SGF with existing solution + `ai_solve.enabled=true` → existing solution preserved, alternatives discovered
- [ ] SGF with existing solution + `ai_solve.enabled=false` → zero behavior change from today
- [ ] Position-only SGF + `ai_solve.enabled=false` → hard rejection as today
- [ ] v2.1 STR-5: `extract_correct_first_move(root)` succeeds after `inject_solution_into_sgf()`
- [ ] v2.1 STR-4: Alternative tree building uses `asyncio.gather()` with split budgets
- [ ] v2.1 EDGE-4: Pass as best move → rejected with clear error message

### Move Classification

- [ ] Move with Δwr < T_good (0.02) → classified as TE (correct)
- [ ] Move with Δwr > T_hotspot (0.25) → classified as BM+HO (blunder)
- [ ] Move with T_bad < Δwr < T_hotspot → classified as BM (bad move)
- [ ] Sign adjustment correct for Black-to-play and White-to-play
- [ ] v2.1 MIN-4: `normalize_winrate()` used consistently; convention documented
- [ ] All thresholds from config, not hardcoded
- [ ] v2.1 ALG-3: Classification uses ONLY delta thresholds, no absolute winrate gates
- [ ] v2.1 STR-1: Moves with policy < `confirmation_min_policy` skip confirmation queries

### Solution Tree Building

- [ ] Tree branches at opponent decision points (policy > branch_min_policy)
- [ ] Tree stops at winrate stability (|Δwr| < wr_epsilon for 2 moves)
- [ ] Tree stops at ownership convergence (key stones change < own_epsilon)
- [ ] v2.1 EDGE-2: Tree stops at seki (winrate in seki_band for consecutive depths)
- [ ] Tree never exceeds solution_max_depth
- [ ] Tree never uses more than max_total_tree_queries
- [ ] Tree doesn't stop before solution_min_depth
- [ ] Branching width capped at max_branch_width per opponent node
- [ ] Truncated branches marked with `truncated=True`
- [ ] v2.1 ALG-4: `tree_completeness` tracked; budget exhaustion before min_depth → confidence="low"
- [ ] v2.1 MIN-2: `query_budget` is required parameter, not optional
- [ ] v2.1 EDGE-1: Corner positions get `corner_position_visit_boost` extra visits
- [ ] v2.1 EDGE-3: Suspected ladders (PV > 8 moves) get `ladder_visit_boost` extra visits

### Additive-Only Rules

- [ ] Existing human solution NEVER deleted or modified
- [ ] AI alternatives APPENDED as additional children of root
- [ ] If KataGo disagrees with human solution: logged, flagged, NOT replaced
- [ ] If human solution is losing (wr < flag_losing_winrate): flagged for review
- [ ] v2.1 ALG-6: `human_solution_confidence` metadata set ("strong"/"weak"/"losing")

### Co-Correct Detection (v2.1 ALG-5 — renamed from Miai)

- [ ] Three-signal check: winrate gap < min_gap AND both Δ < T_good AND score gap < score_gap
- [ ] Field named `co_correct_detected`, NOT `miai_detected`
- [ ] Code comments explain this is NOT Go-theoretic miai detection

### AC Quality Field

- [ ] ac:0 for untouched puzzles (AI disabled or not processed)
- [ ] ac:1 for enriched-only (existing solution used as-is)
- [ ] ac:2 for AI-solved/extended (solution built or branches added)
- [ ] v2.1 ALG-4: ac:2 NOT set if tree truncated before min_depth (downgrade to ac:1)
- [ ] ac:3 never set by pipeline (human review only; v2.1 AC-2: workflow out of scope)
- [ ] v2.1 AC-1: `ai_solution_validated: bool` set when AI checks existing solution
- [ ] YQ wire format: `YQ[q:2;rc:0;hc:0;ac:1]`
- [ ] YQ regex updated to accept `ac:[0123]`

### Logging & Observability (v2.1)

- [ ] v2.1 LOG-1: `BatchSummary` emitted as structured JSON after each batch
- [ ] v2.1 LOG-2: Disagreements written to `.pm-runtime/logs/disagreements/{run_id}.jsonl`
- [ ] v2.1 ALG-9: Collection-level disagreement rates tracked; WARNING if > threshold

### Edge Cases

- [ ] Seki position → v2.1 EDGE-2: seki-specific stopping, goal="seki"
- [ ] Ko position → oscillating winrate, ko-specific stopping, goal="ko"
- [ ] Multiple equally good moves → co-correct detection (v2.1 ALG-5), up to max_correct_moves
- [ ] 9×9 and 13×13 boards → correct coordinate conversion
- [ ] White-to-play puzzles (PL[W]) → sign adjustment via `normalize_winrate()`, W[] nodes injected
- [ ] Position where all moves are bad → rejected gracefully
- [ ] Budget exhausted mid-tree → truncate and mark, v2.1 ALG-4 confidence downgrade
- [ ] v2.1 EDGE-4: Pass as correct first move → rejected with error
- [ ] v2.1 EDGE-1: Bent-four in corner → visit boost, flag, don't reject
- [ ] v2.1 EDGE-3: Ladder suspected → visit boost, flag

---

## Documentation Updates

| Document                                       | Change                                            | Type         |
| ---------------------------------------------- | ------------------------------------------------- | ------------ |
| `config/katago-enrichment.json`                | Add `ai_solve` section, bump to v1.14             | Config       |
| `CLAUDE.md` (root)                             | Add `ac:0-3` to YQ property table                 | Reference    |
| `.github/copilot-instructions.md`              | Add `ac:0-3` to YQ property table                 | Reference    |
| `docs/concepts/quality.md`                     | Add AC field definition, 4-level quality tiers    | Concepts     |
| `docs/architecture/tools/katago-enrichment.md` | Add AI-Solve architecture, expert panel decisions | Architecture |
| `docs/how-to/backend/enrichment-lab.md`        | Add AI-Solve workflow, position-only processing   | How-To       |
| `docs/reference/enrichment-config.md`          | Add `ai_solve` config reference table             | Reference    |
| `CHANGELOG.md`                                 | Add AI-Solve feature entry                        | Changelog    |

---

## Test Plan

### Unit Tests: `tests/test_solve_position.py`

```python
class TestNormalizeWinrate:  # v2.1 MIN-4
    def test_same_player_no_inversion(self): ...
    def test_opposite_player_inverted(self): ...
    def test_black_to_play(self): ...
    def test_white_to_play(self): ...

class TestClassifyMoveQuality:
    def test_te_below_t_good(self): ...
    def test_bm_above_t_bad(self): ...
    def test_bm_ho_above_t_hotspot(self): ...
    def test_neutral_between(self): ...
    def test_sign_black_to_play(self): ...
    def test_sign_white_to_play(self): ...
    def test_thresholds_from_config(self): ...
    def test_no_absolute_winrate_gate(self): ...  # v2.1 ALG-3
    def test_pre_filter_skips_low_policy(self): ...  # v2.1 STR-1

class TestBuildSolutionTree:
    async def test_stops_at_winrate_stability(self): ...
    async def test_stops_at_max_depth(self): ...
    async def test_stops_at_seki(self): ...  # v2.1 EDGE-2
    async def test_branches_at_opponent_nodes(self): ...
    async def test_respects_branch_min_policy(self): ...
    async def test_respects_max_branch_width(self): ...
    async def test_respects_query_budget(self): ...
    async def test_marks_truncated_branches(self): ...
    async def test_does_not_stop_before_min_depth(self): ...
    async def test_9x9_coordinates(self): ...
    async def test_budget_required_not_optional(self): ...  # v2.1 MIN-2
    async def test_tree_completeness_tracked(self): ...  # v2.1 ALG-4
    async def test_budget_exhausted_before_min_depth_low_confidence(self): ...  # v2.1 ALG-4
    async def test_corner_visit_boost(self): ...  # v2.1 EDGE-1
    async def test_ladder_visit_boost(self): ...  # v2.1 EDGE-3

class TestCoCorrectDetection:  # v2.1 ALG-5 (renamed from Miai)
    def test_three_signal_detection(self): ...
    def test_winrate_gap_alone_insufficient(self): ...
    def test_score_gap_required(self): ...

class TestInjectSolutionIntoSgf:
    def test_adds_correct_child_node(self): ...
    def test_adds_branching_tree(self): ...
    def test_preserves_existing_solution(self): ...
    def test_appends_alternatives(self): ...
    def test_white_to_play(self): ...
    def test_inject_then_extract_roundtrip(self): ...  # v2.1 STR-5

class TestDiscoverAlternatives:
    async def test_finds_alternative_correct_move(self): ...
    async def test_no_alternatives_when_unique(self): ...
    async def test_logs_disagreement(self): ...
    async def test_flags_losing_human_solution(self): ...
    async def test_human_solution_confidence_strong(self): ...  # v2.1 ALG-6
    async def test_human_solution_confidence_weak(self): ...  # v2.1 ALG-6
    async def test_human_solution_confidence_losing(self): ...  # v2.1 ALG-6

class TestPassMoveHandling:  # v2.1 EDGE-4
    def test_pass_as_correct_move_rejected(self): ...
    def test_pass_filtered_from_candidates(self): ...
```

### Integration Tests: `tests/test_ai_solve_integration.py`

```python
class TestUnifiedPipeline:
    async def test_position_only_full_enrichment(self): ...
    async def test_existing_solution_enriched(self): ...
    async def test_existing_solution_extended(self): ...
    async def test_ai_solve_disabled_backward_compat(self): ...
    async def test_ac_levels_set_correctly(self): ...
    async def test_yq_includes_ac_field(self): ...
    async def test_disagreement_logged_not_replaced(self): ...
    async def test_losing_human_solution_flagged(self): ...
    async def test_truncated_tree_downgrades_ac(self): ...  # v2.1 ALG-4
    async def test_ai_solution_validated_boolean(self): ...  # v2.1 AC-1
    async def test_parallel_alternative_tree_building(self): ...  # v2.1 STR-4
    async def test_batch_summary_emitted(self): ...  # v2.1 LOG-1
    async def test_disagreement_sink_written(self): ...  # v2.1 LOG-2
    async def test_collection_disagreement_warning(self): ...  # v2.1 ALG-9
```

### Calibration Tests: `tests/test_ai_solve_calibration.py`

```python
@pytest.mark.calibration
class TestThresholdCalibration:
    def test_t_good_precision_recall(self): ...
    def test_t_bad_precision_recall(self): ...
    def test_f1_above_minimum(self): ...
    def test_macro_f1_not_micro(self): ...  # v2.1 CAL-2
    def test_t_good_less_than_t_bad_enforced(self): ...  # v2.1 CAL-2
    def test_stratified_class_balance(self): ...  # v2.1 ALG-8
    def test_visit_count_sensitivity(self): ...  # v2.1 CAL-3

@pytest.mark.calibration
class TestCalibrationFixtureProvenance:  # v2.1 CAL-1
    def test_no_overlap_with_pipeline_collections(self): ...
    def test_readme_documents_source(self): ...
    def test_minimum_samples_per_class(self): ...

@pytest.mark.calibration
class TestSolutionTreeCalibration:
    async def test_cho_elementary_tree_depth(self): ...
    async def test_cho_elementary_branch_count(self): ...
    async def test_natural_stopping_covers_solution(self): ...
```

---

## Implementation Order

| Phase                         | Files                                                                                                                                                 | Effort | Dependencies |
| ----------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- | ------ | ------------ |
| **P1: Config**                | `config.py` (AiSolveConfig + v2.1 sub-models), `katago-enrichment.json` (v1.14)                                                                       | Small  | None         |
| **P2: Models**                | `models/solve_result.py` (SolutionNode, MoveClassification, PositionAnalysis, QueryBudget, TreeCompletenessMetrics, BatchSummary, DisagreementRecord) | Medium | P1           |
| **P3: Move classifier**       | `analyzers/solve_position.py` → `classify_move_quality()`, `analyze_position_candidates()`, `normalize_winrate()`                                     | Medium | P1, P2       |
| **P4: Tree builder**          | `analyzers/solve_position.py` → `build_solution_tree()` with seki detection, completeness tracking                                                    | Medium | P3           |
| **P5: SGF injection**         | `analyzers/solve_position.py` → `inject_solution_into_sgf()` + roundtrip assertion                                                                    | Medium | P4           |
| **P6: Alternatives**          | `analyzers/solve_position.py` → `discover_alternatives()` + parallel tree building                                                                    | Small  | P3           |
| **P7: Integration**           | `analyzers/enrich_single.py` (Step 2 modification + v2.1 amendments)                                                                                  | Medium | P3-P6        |
| **P8: Quality tracking**      | `analyzers/sgf_enricher.py` (YQ ac field), `models/ai_analysis_result.py` (ac_level, ai_solution_validated, human_solution_confidence)                | Small  | P7           |
| **P8.1: Observability**       | `DisagreementSink` class, `BatchSummary` emitter, collection monitoring (v2.1 LOG-1/LOG-2/ALG-9)                                                      | Medium | P7           |
| **P9: Unit tests**            | `tests/test_solve_position.py` (expanded with v2.1 tests)                                                                                             | Medium | P3-P6        |
| **P10: Integration tests**    | `tests/test_ai_solve_integration.py` (expanded with v2.1 tests)                                                                                       | Medium | P7-P8.1      |
| **P11: Calibration fixtures** | `tests/fixtures/calibration/` + README (v2.1 CAL-1), `tests/test_ai_solve_calibration.py` (expanded)                                                  | Medium | P9           |
| **P12: Documentation**        | See table above (~8 files) + v2.1 amendment docs                                                                                                      | Small  | P8           |

**Total estimated scope (v2.1 revised):**

- ~850 lines new code (1 new module + 1 new model file + observability classes, up from ~700)
- ~100 lines modified code (enrich_single.py, sgf_enricher.py, config.py, cli.py, up from ~80)
- ~800 lines tests (3 new test files, expanded, up from ~600)
- ~9 documentation files updated (up from ~8)

---

## Risks and Mitigations

| Risk                                                  | Severity | Mitigation                                                                                                                                                                                                         |
| ----------------------------------------------------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| KataGo finds wrong correct move for complex positions | MEDIUM   | Confirmation queries, T_good threshold, ac:2 flag for transparency, calibration testing                                                                                                                            |
| Solution tree too deep / too many queries             | MEDIUM   | QueryBudget hard cap (50 queries), solution_max_depth (20), truncation marking. v2.1 ALG-4: confidence downgrade if truncated before min_depth                                                                     |
| Existing human solutions overwritten                  | **NONE** | Additive-only rule. Never delete. Disagreements logged, not acted on. v2.1 ALG-6: human_solution_confidence metadata                                                                                               |
| Performance regression in batch mode                  | LOW      | max_total_tree_queries caps worst case. Early termination via natural stopping. v2.1 STR-1: confirmation_min_policy pre-filter reduces classification cost ~50-70%. v2.1 STR-4: parallel alternative tree building |
| Threshold values wrong initially                      | MEDIUM   | Calibration-driven: sweep + F1 optimization. Config-driven: change without code deploy. v2.1 ALG-8: model-version profiles, stratified datasets                                                                    |
| Breaking existing behavior                            | **NONE** | Feature gated `ai_solve.enabled=false`. Default OFF. All tests pass with old config.                                                                                                                               |
| v2.1 EDGE-1: Bent-four / dead-shape false evaluation  | LOW      | Corner visit boost, flag, don't reject. Known KataGo limitation at low visits.                                                                                                                                     |
| v2.1 EDGE-2: Seki tree oscillation                    | MEDIUM   | Seki-specific early-exit heuristic with configurable band/depth.                                                                                                                                                   |
| v2.1 EDGE-3: Ladder dependency in position-only SGF   | LOW      | Ladder suspected flag + visit boost. KataGo handles ladders well at 1000+ visits.                                                                                                                                  |
| v2.1 ALG-9: Silent quality drift across collections   | MEDIUM   | Collection-level disagreement monitoring with WARNING threshold.                                                                                                                                                   |
| v2.1 LOG-2: Disagreements logged but never actioned   | MEDIUM   | JSONL disagreement sink for future review tooling.                                                                                                                                                                 |

### Expert Risk Assessments

> **Cho Chikun:** "For elementary to upper-intermediate, KataGo's solution trees will be reliable. For dan-level puzzles with ko, seki, or deep reading: increase solve_visits to 2000+ and expect some false positives. The ac:2 flag is essential — it lets downstream quality control identify AI-generated solutions."

> **Lee Sedol:** "The biggest risk is not AI accuracy — it's the additive-only rule being violated accidentally through a bug. I would make `inject_solution_into_sgf` the ONLY function that mutates the SGF tree, and add an assertion that existing children are unchanged after the call. A property test: `count(root.children_before) <= count(root.children_after)` and `set(root.children_before) ⊆ set(root.children_after)`."

> **Shin Jinseo:** "Watch out for positions where KataGo's evaluation depends heavily on the ko threat environment. In isolation (position-only), KataGo may not have the full picture of available ko threats. For ko-tagged puzzles, use the ko-aware configuration from `ko_analysis` section (tromp-taylor rules, extended PV length)."

> **Principal Staff Engineer B:** "Observability is critical. Every enrichment run should produce a summary: puzzles processed, ac:0/1/2 distribution, disagreements logged, trees built, average tree depth, average queries per puzzle. This goes in the structured log and can be aggregated for monitoring."

---

## Non-Goals (Explicitly Out of Scope)

- **Replacing human review.** ac:3 is only set by humans. The pipeline never claims human-level verification.
- **Auto-enabling without calibration.** `ai_solve.enabled` stays `false` until calibration tests pass.
- **Modifying existing refutation pipeline.** Refutations continue to use existing `generate_refutations.py`. AI-Solve COMPLEMENTS refutations, doesn't replace them.

---

## Appendix A: Worked Example — Cho Chikun Elementary #1

**Input SGF (position-only):**

```sgf
(;SZ[19]FF[4]GM[1]PL[B]
C[problem 1 | Source: Cho Chikun - Encyclopedia of Life & Death - Elementary]
AB[be][dc][cc][eb][fb][bc]AW[bb][ab][db][da][cb])
```

**Step 2: Pre-analysis (solve_visits=1000):**

| Move (GTP) | Winrate | Δwr  | Policy | Classification |
| ---------- | ------- | ---- | ------ | -------------- |
| A3 (ac)    | 0.98    | 0.01 | 0.45   | TE ✓           |
| B1 (ba)    | 0.62    | 0.35 | 0.12   | BM+HO ✗        |
| C1 (ca)    | 0.55    | 0.42 | 0.08   | BM+HO ✗        |
| A4 (ad)    | 0.71    | 0.26 | 0.05   | BM+HO ✗        |

**Step 2: Build solution tree for A3 (correct):**

```
B[ac] (wr=0.98)
├── W[ba] (wr=0.97, policy=0.40) → B[aa] (wr=0.99) → STOP (wr stable)
├── W[aa] (wr=0.96, policy=0.25) → B[ba] (wr=0.99) → STOP (wr stable)
└── W[ca] (wr=0.97, policy=0.10) → B[aa] (wr=0.99) → STOP (wr stable)
```

**Step 2: Build refutation branches for wrong moves:**

```
B[ba] (WRONG, wr=0.62, delta=0.35) → W[ac] → B[...] → PV (4 moves)
B[ca] (WRONG, wr=0.55, delta=0.42) → W[ac] → B[...] → PV (4 moves)
```

**Injected SGF:**

```sgf
(;SZ[19]FF[4]GM[1]PL[B]
C[problem 1 | Source: Cho Chikun]
AB[be][dc][cc][eb][fb][bc]AW[bb][ab][db][da][cb]
(;B[ac]C[Correct]
  (;W[ba];B[aa])
  (;W[aa];B[ba])
  (;W[ca];B[aa]))
(;B[ba]C[Wrong])
(;B[ca]C[Wrong]))
```

**Result:** ac=2, full solution tree with 3 opponent branches, 2 wrong move branches.

---

## Appendix B: Relationship to Existing Refutation Logic

| Concept          | `generate_refutations.py` (existing)    | `solve_position.py` (new)                    |
| ---------------- | --------------------------------------- | -------------------------------------------- |
| Primary ranking  | Policy (most tempting wrong)            | Winrate (best correct move)                  |
| Engine query     | `AnalysisRequest.with_puzzle_region()`  | Same                                         |
| Move filtering   | Exclude correct, filter by policy       | Classify all by delta                        |
| Core threshold   | `delta_threshold=0.08` → wrong enough   | `T_good=0.02` → correct enough               |
| Per-move query   | Play wrong, get opponent punishment     | Play correct, get opponent responses         |
| PV depth         | `max_pv_length=4` (flat)                | Recursive tree with stopping conditions      |
| Escalation       | Higher visits, relaxed thresholds       | Not needed — initial solve_visits sufficient |
| Coord conversion | `gtp_to_sgf()`, `sgf_to_gtp()`          | Same                                         |
| Logging          | `log_with_context(stage="refutations")` | `log_with_context(stage="ai_solve")`         |

---

## Appendix C: Review Panel Assessment — v2.1 Amendments

> **Context:** Post-v2 review surfaced 27 improvements across algorithm design, structural issues, calibration gaps, edge cases, quality tracking, observability, and minor corrections. Each item was assessed by the expert panel and either accepted (🟢), partially accepted (🟡), or rejected (🔴).

---

### C.1 Core Algorithm Issues

| ID        | Issue Provided                                                                                                                                                                                                                                                                                                                                   | Review Panel Opinion                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        | Implementation Methodology                                                                                                                                                                                                                                                                                                                                                                                     | Decision                                                                            |
| --------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| **ALG-3** | **Pre/Post Winrate Floor Logic — Risk of False Puzzle Validation.** `pre_winrate_floor=0.90` and `post_winrate_ceiling=0.15` act as validity gates. Many real tsumego have root winrate < 0.90 (e.g., 0.82 in a slightly favorable position). Delta classification alone is sufficient. These should be confidence metrics, not rejection gates. | <ul><li>**Cho Chikun:** "Many classical tsumego start from positions that are only slightly favorable. A 0.90 floor would exclude positions where White has just enough compensation to make the fight interesting. The correct move's delta is what matters, not the absolute starting winrate."</li><li>**Ke Jie:** "For practical learning, a position at 0.82 winrate with a correct move that maintains 0.98 is a perfectly good puzzle. The 0.16 Δ in the wrong direction is the teaching signal."</li><li>**Principal Staff Engineer A:** "Downgrade from gate to confidence annotation. The classification logic should use delta thresholds exclusively. Pre/post absolutes become metadata attached to `PositionAnalysis` for downstream quality dashboards — not blocking conditions."</li></ul> | Refactor `classify_move_quality()`: remove pre/post floor/ceiling from classification logic. Keep values in config as `confidence_metrics` (renamed from `thresholds`). Attach `root_winrate_confidence: "high"\|"medium"\|"low"` to `PositionAnalysis` based on these thresholds. Never reject a puzzle solely on absolute winrate.                                                                           | 🟢 **Accept**                                                                       |
| **ALG-4** | **Solution Tree Builder — Truncation without Confidence Downgrade.** If query budget exhausts mid-tree before `solution_min_depth`, tree is incomplete but still marked `ac:2`. This creates partial solutions labeled as solved.                                                                                                                | <ul><li>**Lee Sedol:** "A solution tree that stops at depth 2 when the problem requires depth 5 is not a solution — it's a hint. If the budget cuts you off before the position is resolved, you cannot claim you solved it."</li><li>**Shin Jinseo:** "Track `tree_completeness` as a ratio: `completed_branches / total_branches`. If < 0.8, downgrade. If truncated before min_depth, don't set ac:2."</li><li>**Principal Staff Engineer B:** "Add explicit logic: `if budget_exhausted and max_reached_depth < solution_min_depth: confidence = 'low'; ac_level = 1`. This preserves the partial tree for data but doesn't claim a solve."</li></ul>                                                                                                                                                   | Add `tree_completeness` field to `SolutionNode`. In `build_solution_tree()`, track `completed_branches` vs `total_attempted_branches`. After tree building: if `budget.queries_used >= budget.max_queries` AND root tree depth < `solution_min_depth` → set `confidence="low"`, prevent `ac:2`, set `ac:1` instead. Add `TreeCompletenessMetrics` model.                                                       | 🟢 **Accept**                                                                       |
| **ALG-5** | **Miai Detection — Gap Rule Too Coarse.** `min_winrate_gap=0.15`: Move A at 0.97 vs Move B at 0.86 → gap 0.11 → classified as miai. But 0.86 vs 0.97 is not equivalent in tsumego. Need multi-signal: gap + absolute delta + score delta.                                                                                                        | <ul><li>**Cho Chikun:** "True miai means either move achieves the SAME result independently. Two moves both being 'correct' (Δ < T_good) is not miai — it's co-correct. Miai requires that after either move, the resulting positions are equivalent in outcome. Winrate proximity alone cannot confirm this."</li><li>**Lee Sedol:** "I agree with renaming to 'co-correct.' Real miai would require analyzing BOTH resulting positions and confirming they converge. That's expensive but worthwhile for accuracy."</li><li>**Principal Staff Engineer A:** "Three-signal check: `abs(wr1 - wr2) < min_gap AND both Δ < T_good AND abs(score1 - score2) < score_gap`. Rename field from `miai_detected` to `co_correct_detected`. Add `score_gap` config param."</li></ul>                                | Rename `miai_detected` → `co_correct_detected` in `PositionAnalysis`. Add `score_gap: float = 3.0` to config. Update detection logic to require all three conditions: winrate gap < min_gap, both moves classify as TE, AND score lead gap < score_gap. Document the distinction between "co-correct" (our detection) and "miai" (Go-theoretic concept) in code comments.                                      | 🟡 **Partial** — rename + multi-signal, defer true miai verification to future work |
| **ALG-6** | **Existing Solution Preservation — Needs Ranking Freeze + Metadata.** Human solution preserved when AI disagrees (correct). But if human move wr=0.62 and AI move wr=0.91, frontend may display human first → confuses learners. Need ranking freeze + suboptimality metadata.                                                                   | <ul><li>**Lee Sedol:** "The preservation is correct — but transparency is essential. If the human solution is significantly worse, the learner deserves to know. A 'teacher's choice' badge versus 'AI-recommended' badge gives context without deleting the human answer."</li><li>**Ke Jie:** "Don't reorder root children — that breaks backward compatibility. But attach metadata so the frontend CAN make informed display decisions."</li><li>**Principal Staff Engineer A:** "Add `human_solution_confidence: 'strong'\|'weak'\|'losing'` to the puzzle result. Weak = AI has a notably better move but human move is still winning. Losing = human move is objectively losing. This metadata flows to the frontend for display decisions."</li></ul>                                               | Add `human_solution_confidence` field to `EnrichmentResult`. Classification: `strong` (AI agrees or gap < T_disagreement), `weak` (AI finds notably better move, gap ≥ T_disagreement but human still winning wr > 0.5), `losing` (human move wr < flag_losing_winrate). Never reorder SGF children. Inject confidence as SGF comment or separate metadata field.                                              | 🟢 **Accept**                                                                       |
| **ALG-7** | **Goal Inference — Ownership Threshold Brittle.** `ownership_alive_threshold=0.7` fluctuates near edges, especially in ko/seki. Risk of false kill→seki or seki→alive classification. Should use multi-signal: score delta magnitude + ownership variance stability + territory swing.                                                           | <ul><li>**Shin Jinseo:** "Ownership is ONE signal, not THE signal. For life-and-death, score delta is more reliable: if correct move swings score by 15+ points, the group was at stake. For ko, ownership oscillates by design — don't use it as primary for ko-tagged positions."</li><li>**Ke Jie:** "Score delta + territory swing after correct move is the robust combination. Ownership confirms but shouldn't decide."</li><li>**Principal Staff Engineer B:** "Add `ownership_variance` metric — compute variance across top 3 moves' ownership maps. High variance = unstable → lower weight for ownership in goal inference. Combine: `score_delta_primary, ownership_secondary, variance_as_confidence`."</li></ul>                                                                             | Refactor `goal_inference` config to multi-signal: `score_delta_kill_threshold` (primary), `ownership_alive_threshold` (secondary), new `ownership_variance_threshold` (confidence gate). Goal inference algorithm: 1) Score delta → primary classification, 2) Ownership confirms if variance < threshold, 3) If variance high → flag as `goal_confidence="low"`. Add `goal_confidence` to `PositionAnalysis`. | 🟡 **Partial** — add multi-signal, keep ownership as secondary                      |
| **ALG-8** | **Calibration Methodology — Missing class imbalance handling and model-version sensitivity.** Most moves are neutral → F1 inflates. Need balanced calibration set. Also thresholds differ across KataGo model versions (b6/b18/b28). Need `threshold_profile_by_model`.                                                                          | <ul><li>**Shin Jinseo:** "This is critical. I've seen thresholds shift by 0.01-0.03 between b18 and b28 models. What's T_good=0.02 on b18 might need to be T_good=0.025 on b28 because the stronger model's winrate estimates are sharper."</li><li>**Principal Staff Engineer B:** "Three additions: 1) Stratified sampling for calibration set — equal TE/BM/neutral representation. 2) `model_profile` in config mapping model hash → threshold overrides. 3) Calibration test parameterized by model version."</li><li>**Principal Staff Engineer A:** "Also specify the F1 target explicitly: macro-F1 across all three classes (TE/BM/neutral), not micro-F1 which would be dominated by the neutral class."</li></ul>                                                                                | Add `calibration` section to config: `min_te_samples`, `min_bm_samples`, `min_neutral_samples`, `target_macro_f1`. Add `model_profiles` dict in config keyed by model hash → threshold overrides. Calibration test must: 1) use stratified dataset, 2) compute macro-F1, 3) be parameterized by model version. Document visit-count dependency.                                                                | 🟢 **Accept**                                                                       |
| **ALG-9** | **AC Levels — Clean but needs collection-level disagreement tracking.** `ac:1` when AI disagrees slightly (delta=0.03) but no alternative added — should stay ac:1. But silent drift accumulates without collection-level monitoring.                                                                                                            | <ul><li>**Principal Staff Engineer B:** "Per-collection disagreement counts are essential for quality monitoring. Add a `collection_disagreement_summary` to the batch log: `{collection_id: {total: N, disagreements: K, pct: K/N}}`."</li><li>**Cho Chikun:** "If a collection has >20% disagreement rate, that collection needs human review, not just individual puzzles."</li></ul>                                                                                                                                                                                                                                                                                                                                                                                                                    | Add `collection_disagreement_summary` to batch-level structured log. Track per-collection: total puzzles processed, disagreement count, disagreement percentage. If pct > configurable threshold (default 20%) → emit WARNING-level log. No change to AC semantics — stays `ac:1` for slight disagreements.                                                                                                    | 🟢 **Accept**                                                                       |

### C.2 Structural / Design Issues

| ID        | Issue Provided                                                                                                                                                                                                                                                  | Review Panel Opinion                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          | Implementation Methodology                                                                                                                                                                                                                                                                                                     | Decision                          |
| --------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------- |
| **STR-1** | **confirm_visits reuse gap.** `analyze_position_candidates()` fires per-move confirmation queries at 500 visits each for K=10 candidates = 5,000 visits for classification alone, unacknowledged in performance analysis. Need fast pre-filter by policy floor. | <ul><li>**Principal Staff Engineer B:** "This is a real performance gap. 10 × 500 = 5,000 visits = ~2 seconds just for classification, BEFORE tree building. A policy pre-filter at e.g. 0.03 would reduce confirmations to typically 3-5 moves, cutting classification cost by 50-70%."</li><li>**Shin Jinseo:** "Moves with policy < 0.03 are almost never correct in tsumego. 0.03 is safe as a pre-filter floor — you're only excluding moves the neural net considers essentially impossible."</li></ul> | Add `confirmation_min_policy: float = 0.03` to `AiSolveConfig`. In `analyze_position_candidates()`: after initial analysis, filter candidates to only those with `policy >= confirmation_min_policy` before running confirmation queries. Update performance analysis section to document: typical 3-5 confirmations (not 10). | 🟢 **Accept**                     |
| **STR-2** | **`pre_winrate_floor` / `post_winrate_ceiling` not wired into algorithm.** Appear in config and Topic 6 but never used in `classify_move_quality()`. Config bloat without enforcement.                                                                          | <ul><li>**Principal Staff Engineer A:** "This is resolved by ALG-3: they become confidence metrics, not classification gates. Move them from `thresholds` to a new `confidence_metrics` sub-section. Wire them into `PositionAnalysis.root_winrate_confidence` computation."</li></ul>                                                                                                                                                                                                                        | Combined with ALG-3. Rename config section. Wire into confidence annotation, not classification. Remove from `thresholds` section, add to `confidence_metrics` section.                                                                                                                                                        | 🟢 **Accept** — merged with ALG-3 |
| **STR-3** | **Miai detection underspecified.** `min_winrate_gap=0.15` → gap between what? Winrates or deltas? Also "miai" has specific Go meaning that winrate proximity doesn't confirm.                                                                                   | <ul><li>**Cho Chikun:** "The Go community would object to calling two co-winning moves 'miai' based on winrate alone. Miai requires both moves to be interchangeable in effect. Please use 'co-correct' or 'dual solution' instead."</li></ul>                                                                                                                                                                                                                                                                | Combined with ALG-5. Rename to `co_correct_detected`. Explicitly specify: gap = `abs(correct_move_1.winrate - correct_move_2.winrate)`. Document in code that this is NOT Go-theoretic miai detection.                                                                                                                         | 🟢 **Accept** — merged with ALG-5 |
| **STR-4** | **`discover_alternatives()` sequential when parallelizable.** `enrich_single.py` calls `discover_alternatives()` then `build_solution_tree()` for each alternative serially. With `max_alternatives=2`, this doubles wall time unnecessarily.                   | <ul><li>**Principal Staff Engineer B:** "Easy win. Use `asyncio.gather()` to build solution trees for all alternatives concurrently. The engine queries are already async. Estimated saving: 40-60% wall time for multi-alternative puzzles."</li><li>**Principal Staff Engineer A:** "Careful with query budget sharing across concurrent tree builders. Pass separate `QueryBudget` instances or use a shared atomic counter."</li></ul>                                                                    | In `enrich_single.py` Step 2 (alternatives path): replace sequential loop with `asyncio.gather()` for `build_solution_tree()` calls. Each alternative gets its own `QueryBudget` with `max_queries = config.max_total_tree_queries // len(alternatives)`. Document shared-budget approach.                                     | 🟢 **Accept**                     |
| **STR-5** | **`inject_solution_into_sgf()` / `extract_correct_first_move()` coupling.** Injection must produce structure parseable by extract. This coupling is fragile and untested.                                                                                       | <ul><li>**Lee Sedol:** "This is exactly the kind of bug that silently breaks everything. After injecting, you MUST verify the roundtrip: `inject → extract → assert extract matches what was injected`."</li><li>**Principal Staff Engineer A:** "Add an explicit integration test: `test_inject_then_extract_roundtrip()`. Also add a defensive assertion in `enrich_single.py` after injection: `assert extract_correct_first_move(root) is not None`."</li></ul>                                           | Add `test_inject_then_extract_roundtrip()` to integration tests. Add defensive assertion in `enrich_single.py` immediately after `inject_solution_into_sgf()` call: `assert extract_correct_first_move(root) is not None, "Injection produced unparseable solution tree"`. Add to validation checklist.                        | 🟢 **Accept**                     |

### C.3 Calibration Methodology Gaps

| ID        | Issue Provided                                                                                                                                                                                                     | Review Panel Opinion                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          | Implementation Methodology                                                                                                                                                                                                                                                                                                   | Decision      |
| --------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------- |
| **CAL-1** | **Calibration fixture set undefined.** "100+ puzzles" — from where? Who labels them? If from the same collection being processed → label leakage. Must be held-out and independently labeled.                      | <ul><li>**Cho Chikun:** "Use puzzles from collections NOT in the pipeline: Graded Go Problems for Beginners, Tesuji by James Davies, or hand-curated positions. The labels must come from verified human solutions in published books, NOT from our pipeline output."</li><li>**Principal Staff Engineer A:** "Document provenance: `tests/fixtures/calibration/README.md` must specify source, labeler, date, and confirm no overlap with pipeline input collections."</li></ul>                                                                                             | Create `tests/fixtures/calibration/README.md` with: provenance requirements (held-out collections only), labeling protocol (human expert labels, not pipeline output), minimum sample sizes per class, overlap verification script. Source fixtures from published book positions with verified solutions.                   | 🟢 **Accept** |
| **CAL-2** | **T_good and T_bad interact but calibrated independently.** A move can't be both TE and BM, yet the joint sweep optimizes a single F1 — unclear if it's for TE, BM, or combined. Specify loss function explicitly. | <ul><li>**Principal Staff Engineer B:** "The loss function must be explicit: macro-averaged F1 across {TE, BM, neutral} classes. Joint sweep is correct — the nested loop implicitly covers the interaction. But the constraint `T_good < T_bad` must be enforced in the sweep to prevent overlap. Add: `if T_good >= T_bad: skip`."</li></ul>                                                                                                                                                                                                                                | Update calibration test: 1) Explicit loss = macro-F1 across {TE, BM, neutral}. 2) Enforce constraint `T_good < T_bad` in sweep. 3) Report per-class precision/recall alongside overall F1. 4) Document that T_hotspot is derived (T_hotspot = T_bad × configurable multiplier, default 3.0).                                 | 🟢 **Accept** |
| **CAL-3** | **Visit-count sensitivity undocumented.** Optimal thresholds at `solve_visits=1000` may differ from `confirmation_visits=500`. Lower visits = noisier winrate = T_good=0.02 may produce false positives.           | <ul><li>**Shin Jinseo:** "At 500 visits, the standard deviation of winrate estimates is roughly 0.01-0.015 for tactical positions. So T_good=0.02 is within 1-2 standard deviations of noise at 500 visits. Either increase confirmation_visits or widen T_good for confirmation queries."</li><li>**Principal Staff Engineer B:** "Add `visit_count` as a parameter in the calibration sweep. Report threshold sensitivity: 'At 500 visits, optimal T_good = X; at 1000 visits, optimal T_good = Y.' If they differ significantly, use visit-specific thresholds."</li></ul> | Add `calibration_visit_counts: list[int] = [500, 1000, 2000]` to calibration config. Sweep includes visit count as third dimension. Report threshold stability across visit counts. If unstable → use visit-specific thresholds (`thresholds_by_visits` dict in config). Document noise characteristics at each visit level. | 🟢 **Accept** |

### C.4 Missing Edge Case Handling

| ID         | Issue Provided                                                                                                                                                                                                                 | Review Panel Opinion                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     | Implementation Methodology                                                                                                                                                                                                                                                                                                                                             | Decision                                                     |
| ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------ |
| **EDGE-1** | **Bent-four / dead-shape in isolation.** Position-only puzzles without full board context → KataGo may not evaluate bent-four-in-the-corner as dead. Known KataGo limitation at low visits.                                    | <ul><li>**Shin Jinseo:** "This is a real limitation. KataGo with Japanese rules and low visits sometimes fails on bent-four. Mitigation: use `rules: tromp-taylor` (where bent-four is unconditionally dead) and increase visits for corner positions. But full coverage is impossible without ruleset-aware analysis."</li><li>**Cho Chikun:** "Bent-four is rare in elementary-intermediate collections. Flag it but don't let it block the pipeline."</li></ul>                                                                                                                                                       | Add `corner_position_visit_boost: int = 500` to config — when `YC` indicates corner position, add 500 visits to solve_visits. Add `known_limitations` section to documentation listing bent-four, superko, and similar edge cases. Log WARNING when position is in corner with low visit count. No hard rejection — accept KataGo's result with confidence annotation. | 🟡 **Partial** — mitigate, flag, document; can't fully solve |
| **EDGE-2** | **Seki stopping condition underspecified.** `goal="seki"` listed as edge case but no detection or stopping heuristic. Winrate ~0.5 + low ownership is necessary but not sufficient. Tree builder could oscillate indefinitely. | <ul><li>**Lee Sedol:** "Seki positions have a distinctive signature: both players' best moves are pass or near-pass, territory is contested but stable. If two consecutive moves have winrate between 0.45-0.55 AND score lead < 2 points, that's seki territory."</li><li>**Principal Staff Engineer A:** "Add seki early-exit: if winrate stays in [0.45, 0.55] for 3 consecutive depth levels AND score lead oscillation < 2 points → stop, set goal='seki', confidence='medium'. The tree builder needs a seki-specific stopping condition alongside the existing winrate-stability and ownership checks."</li></ul> | Add `seki_detection` config section: `winrate_seki_band: [0.45, 0.55]`, `score_lead_seki_max: 2.0`, `seki_consecutive_depth: 3`. In `build_solution_tree()`: if last N moves' winrates all within seki_band AND score leads all within seki_max → early exit with `goal="seki"`. Mark tree as seki-terminated.                                                         | 🟢 **Accept**                                                |
| **EDGE-3** | **Ladder dependency in position-only SGF.** Ladder correctness depends on off-board stones not encoded in puzzle. Source of false correct-move classifications.                                                                | <ul><li>**Shin Jinseo:** "KataGo reads ladders well at 1000+ visits. The real risk is when the puzzle is a fragment of a larger board and the ladder extends beyond the fragment. But for published puzzle collections (19×19 with stones placed), KataGo handles this correctly."</li><li>**Ke Jie:** "Flag positions where the top move involves a ladder (PV length > 8, mostly extending in one direction), but don't reject them. Ladder puzzles are valuable."</li></ul>                                                                                                                                           | Add ladder detection heuristic: if PV from KataGo is > 8 moves and mostly diagonal/linear → set `ladder_suspected=True` in `PositionAnalysis`. Log INFO. Increase visits by `ladder_visit_boost` (default 500) for suspected ladders. No rejection — ladders are valid puzzles.                                                                                        | 🟡 **Partial** — flag + boost visits, can't fully validate   |
| **EDGE-4** | **Pass move handling.** Stopping condition mentions "pass detected in PV" but doesn't handle KataGo recommending pass as correct first move (group already alive, puzzle may be trivial/malformed).                            | <ul><li>**Cho Chikun:** "If the correct first move is pass, the puzzle is invalid. The position is already resolved — there is no problem to solve. This should be an explicit rejection."</li><li>**Principal Staff Engineer A:** "Add to classification: if `pre_analysis.top_move == 'pass'` → reject with error 'Position already resolved — no puzzle exists.' If pass appears as correct first move among candidates, exclude it from correct_moves list."</li></ul>                                                                                                                                               | In `analyze_position_candidates()`: if top move by winrate is pass → return error result: "AI-Solve: position already resolved (pass is best move)". Filter pass from candidate list before classification. Add to validation checklist. Add unit test `test_pass_as_correct_move_rejected`.                                                                           | 🟢 **Accept**                                                |

### C.5 AC Field & Quality Tracking

| ID       | Issue Provided                                                                                                                                                                                     | Review Panel Opinion                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     | Implementation Methodology                                                                                                                                                                                                                                                                                       | Decision                                             |
| -------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------- |
| **AC-1** | **`ac:1` conflates "AI agreed" with "AI not run on solution."** Reviewer can't distinguish "AI validated this solution" from "AI only enriched metadata." Consider sub-levels or separate boolean. | <ul><li>**Principal Staff Engineer A:** "Sub-levels (ac:1a/1b) break the integer format and complicate parsing. Better: add a separate boolean `ai_solution_validated: bool` to the result model. When ac:1 + ai_solution_validated=true → AI checked and agreed. When ac:1 + ai_solution_validated=false → AI enriched metadata only (shouldn't happen if ai_solve.enabled, but covers edge cases)."</li><li>**Ke Jie:** "Keep AC integer levels clean. Add the boolean as metadata, not as an AC sub-level."</li></ul> | Add `ai_solution_validated: bool = False` to `EnrichmentResult`. Set to `True` when ai_solve runs and existing solution's correct move matches AI's top move (within T_disagreement). Keep AC levels as integers. This boolean is metadata in the result, not in the SGF wire format (YQ stays `ac:0\|1\|2\|3`). | 🟡 **Partial** — boolean metadata, not AC sub-levels |
| **AC-2** | **`ac:3` has no workflow defined.** Plan states "human review only" but no tool, queue, or interface exists. Dead tier without implementation.                                                     | <ul><li>**Principal Staff Engineer B:** "Honest assessment: ac:3 is aspirational for this plan's scope. It's correct to define the value (forward compatibility) but the workflow should be a separate spec. Include a stub section acknowledging this."</li><li>**Cho Chikun:** "The level should exist because eventually there WILL be human review. But don't pretend it's operational until the tooling exists."</li></ul>                                                                                          | Keep `ac:3` in the schema for forward compatibility. Add explicit note in AC section: "ac:3 workflow (review tool, queue, interface) is OUT OF SCOPE for this plan — tracked as future work." Remove from validation checklist items that imply it's functional. Add `TODO: ac:3 review workflow` reference.     | 🟡 **Partial** — keep definition, defer workflow     |

### C.6 Logging & Observability

| ID        | Issue Provided                                                                                                                                                                               | Review Panel Opinion                                                                                                                                                                                                                                                                                                                                                                                                                                    | Implementation Methodology                                                                                                                                                                                                                                                                                                      | Decision      |
| --------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------- |
| **LOG-1** | **No structured batch-level summary event.** Logging contract is all per-puzzle. Batch aggregate (ac distribution, avg tree depth, avg queries, disagreement count) mentioned but not wired. | <ul><li>**Principal Staff Engineer B:** "Non-negotiable for production. Every batch must emit a structured summary. This is the primary observability signal for quality monitoring. Without it, degradation is invisible."</li><li>**Principal Staff Engineer A:** "Add `BatchSummary` model and a `log_batch_summary()` call at the end of each enrichment batch."</li></ul>                                                                          | Add `BatchSummary` model: `total_puzzles`, `ac_distribution: dict[int, int]`, `avg_tree_depth`, `avg_queries_per_puzzle`, `disagreement_count`, `co_correct_count`, `truncation_count`, `errors`. Add `log_batch_summary()` to logging contract. Emit as structured JSON at INFO level after each batch.                        | 🟢 **Accept** |
| **LOG-2** | **Disagreement records logged but not surfaced.** Log line is not sufficient for human action. Need a specified sink: file, database, review queue.                                          | <ul><li>**Principal Staff Engineer A:** "Disagreements should be written to a structured file: `.pm-runtime/logs/disagreements/{run_id}.jsonl`. Each line is a JSON record with puzzle_id, human_move, ai_move, deltas, action taken. This file is the input for future ac:3 review tooling."</li><li>**Principal Staff Engineer B:** "JSONL format — one record per line, append-only. Easy to grep, easy to load into pandas for analysis."</li></ul> | Add `DisagreementSink` class that writes to `.pm-runtime/logs/disagreements/{run_id}.jsonl`. Each record: `{puzzle_id, collection, human_move, ai_move, human_wr, ai_wr, delta, action, timestamp}`. Integrate into enrichment pipeline — call sink after every disagreement detection. Document file format in reference docs. | 🟢 **Accept** |

### C.7 Minor Issues

| ID        | Issue Provided                                                                                                                                                                                                | Review Panel Opinion                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           | Implementation Methodology                                                                                                                                                                                                                                                                                                              | Decision                                                         |
| --------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------- |
| **MIN-1** | **Schema version bump changelog too terse.** v1.14 adds entire ai_solve section — entry not actionable for schema migration.                                                                                  | <ul><li>**Principal Staff Engineer A:** "Expand changelog to list: new fields added, new config sections, AC field in YQ, backward compatibility notes."</li></ul>                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             | Expand v1.14 changelog to multi-line: list each new config section, note YQ ac field addition, specify backward compatibility (missing ai_solve → None → disabled), list migration steps (none required — additive only).                                                                                                               | 🟢 **Accept**                                                    |
| **MIN-2** | **`query_budget` is optional (`\| None`) in `build_solution_tree()`.** If None → no budget enforcement. Defeats purpose of hard cap. Should default to config value at call site.                             | <ul><li>**Principal Staff Engineer A:** "Make it required. Default at call site: `QueryBudget(max_queries=config.solution_tree.max_total_tree_queries)`. Remove the `\| None` type."</li></ul>                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 | Change `build_solution_tree()` signature: `query_budget: QueryBudget` (required, no None). At call site in `enrich_single.py`, always construct: `QueryBudget(max_queries=config.ai_solve.solution_tree.max_total_tree_queries)`. Remove optional handling.                                                                             | 🟢 **Accept**                                                    |
| **MIN-3** | **Worked example (Appendix A) inconsistency.** W[ca] → B[aa] branch, but B[aa] also appears in W[aa] → B[ba] branch sequence. Same response move in sibling branches.                                         | <ul><li>**Cho Chikun:** "In the position given, after B[ac], if W[ca] then B[aa] is indeed the correct response. And if W[aa] then B[ba] is correct. These are different white moves leading to different black responses. The notation is correct — aa appears as a black response in two different branches because it IS the correct move in both cases against different white responses. However, in the first branch W[ba] → B[aa], and in the third branch W[ca] → B[aa] — the same black response to two different white moves is plausible if aa is the vital point."</li></ul>                                                                                                                                                                                                       | Review the specific position stones and verify each branch's moves are legal and don't overlap illegally. Update example if any moves conflict with already-placed stones. Add note that the same coordinate CAN appear across sibling branches (different opponent moves).                                                             | 🟡 **Partial** — verify, likely correct but add explanatory note |
| **MIN-4** | **White-to-play sign adjustment in algorithm pseudocode.** `delta = pre.root_winrate - post_wr` — whose perspective? KataGo reports from side-to-move or Black depending on config. Needs explicit statement. | <ul><li>**Shin Jinseo:** "KataGo's default GTP output reports winrate from the perspective of the CURRENT side to move. So if Black plays and the position is analyzed, winrate is from Black's perspective. After Black's move, if we analyze for White, winrate is from White's perspective. The delta computation must normalize to a consistent perspective — always from the puzzle player's perspective."</li><li>**Principal Staff Engineer A:** "Add an explicit statement in the algorithm: 'All winrates are normalized to the puzzle player's perspective (the side with PL[] in the SGF root). If KataGo reports from opponent's perspective, invert: `wr = 1.0 - reported_wr`.' Add a helper function `normalize_winrate(wr, reported_player, puzzle_player) → float`."</li></ul> | Add `normalize_winrate()` helper to `solve_position.py`. Add explicit comment block in algorithm pseudocode: "Convention: all winrates normalized to puzzle player (PL[]) perspective. KataGo reports from side-to-move — invert when analyzing opponent's position." Add unit tests for Black-to-play and White-to-play normalization. | 🟢 **Accept**                                                    |

---

### C.8 Summary of Panel Decisions

| Category             | 🟢 Accepted | 🟡 Partial | 🔴 Rejected | Total  |
| -------------------- | ----------- | ---------- | ----------- | ------ |
| Core Algorithm (ALG) | 5           | 2          | 0           | 7      |
| Structural (STR)     | 5           | 0          | 0           | 5      |
| Calibration (CAL)    | 3           | 0          | 0           | 3      |
| Edge Cases (EDGE)    | 2           | 2          | 0           | 4      |
| AC/Quality (AC)      | 0           | 2          | 0           | 2      |
| Logging (LOG)        | 2           | 0          | 0           | 2      |
| Minor (MIN)          | 2           | 2          | 0           | 4      |
| **Total**            | **19**      | **8**      | **0**       | **27** |
