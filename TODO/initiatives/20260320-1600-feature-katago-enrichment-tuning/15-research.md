# Research Brief — KataGo Enrichment Threshold Fine-Tuning

**Initiative**: 20260320-1600-feature-katago-enrichment-tuning
**Date**: 2026-03-20
**Research type**: Multi-expert consensus evaluation of `config/katago-enrichment.json` v1.25

---

## 1. Research Question

Which parameters in `katago-enrichment.json` should be adjusted to improve tsumego enrichment accuracy, and what are the recommended values based on consensus across four independent expert evaluations?

## 2. Expert Panel

| ID | Persona | Domain | Source |
|----|---------|--------|--------|
| EA | Go + KataGo Domain Expert | Move classification, seki/ko, calibration | User-provided evaluation |
| EB | KataGo Expert | Visit budgets, model selection, convergence | User-provided evaluation |
| TS | Dr. Shin Jinseo (9p) — Tsumego Expert | Puzzle correctness, solution completeness, teaching quality | KataGo-Tsumego-Expert agent |
| ENG | Dr. David Wu — Engine Expert | MCTS convergence, visit allocation, computational efficiency | KataGo-Engine-Expert agent |

## 3. Four-Way Consensus Matrix

### Legend
- **✅ Consensus**: 3+ experts agree on direction and approximate value
- **⚠️ Partial**: Experts agree on direction, disagree on magnitude
- **❌ Disagreement**: Experts disagree on whether change is needed

| R-ID | Parameter | Current | EA | EB | TS | ENG | Consensus | Recommended |
|------|-----------|---------|----|----|----|----|-----------|-------------|
| R-1 | `ai_solve.thresholds.t_good` | 0.05 | 0.02 | — | 0.03 | 0.03 | ⚠️ Partial (0.03 wins) | **0.03** |
| R-2 | `ai_solve.thresholds.t_bad` | 0.15 | ≤0.08 | — | 0.12 | 0.15 (no change) | ⚠️ Partial | **0.12** |
| R-3 | `ai_solve.thresholds.t_disagreement` | 0.10 | 0.05-0.08 | — | 0.07 | — | ⚠️ Partial | **0.07** |
| R-4 | `solution_tree.depth_profiles.entry.solution_min_depth` | 2 | 3 | — | 3 | — | ✅ Consensus | **3** |
| R-5 | `solution_tree.depth_profiles.strong.solution_max_depth` | 28 | 22 | — | 24 | — | ⚠️ Partial | **24** |
| R-6 | `seki_detection.score_lead_seki_max` | 2.0 | 8-10 | — | 5.0 | — | ⚠️ Partial | **5.0** |
| R-7 | `seki_detection.winrate_band` | 0.45-0.55 | — | — | 0.43-0.57 | — | — | **0.43-0.57** |
| R-8 | `goal_inference.score_delta_ko` | 5.0 | 7.0 | — | 7.0 | — | ✅ Consensus | **7.0** |
| R-9 | `refutations.refutation_visits` | 100 | — | 200-500 | 200 | 200 | ✅ Consensus | **200** |
| R-10 | `deep_enrich.visits` | 2000 | — | 4000-8000 | 2000 (no change) | 2000 (no change) | ✅ Consensus: no change | **2000** |
| R-11 | `solution_tree.max_total_tree_queries` | 50 | — | 80-120 | 65 | 65 | ✅ Consensus | **65** |
| R-12 | `solution_tree.continuation_visits` | 125 | 300 | — | 200 | 175 | ⚠️ Partial | **200** |
| R-13 | `refutations.candidate_max_count` | 5 | — | 6-8 | 6 | 6 | ✅ Consensus | **6** |
| R-14 | `refutations.delta_threshold` | 0.08 | align w/ t_bad | 0.10-0.15 | 0.08 (no change) | 0.08 (no change) | ✅ Consensus: no change | **0.08** |
| R-15 | `models.quick.arch` | b10c128 | — | b18c384 | b10 (no change) | b10 (no change) | ✅ Consensus: no change | **b10c128** |
| R-16 | `visit_tiers.T3.visits` | 5000 | — | 8000-15000 | 5000 (no change) | 5000 (no change) | ✅ Consensus: no change | **5000** |
| R-17 | `edge_case_boosts.corner_visit_boost` | 1.5 | 3.0 | — | 1.5 (dead code) | 2.0 (latent) | ⚠️ Dead code issue | **Code fix needed** |
| R-18 | `calibration.sample_size` | 5 | "critically low" | — | 15 | 30 | ⚠️ Partial (scope question) | **20** |
| R-19 | `ownership_thresholds.alive` | 0.7 | — | 0.60-0.75 | 0.7 (no change) | — | ✅ Consensus: no change | **0.7** |
| R-20 | `ownership_thresholds.seki` | -0.3/0.3 | — | -0.40/0.40 | — | — | — Single source | **-0.3/0.3** |

## 4. Structural Issues Identified (All Experts)

### S-1: Adaptive Mode Overrides Edge-Case Boosts (CRITICAL)
- **Identified by**: TS-18, TS-27, ENG-9, ENG-15
- **Issue**: Since v1.24 enabled `visit_allocation_mode=adaptive`, the code unconditionally sets `effective_visits = branch_visits`, discarding any corner/ladder boost. This means `corner_visit_boost=1.5` and `ladder_visit_boost=2.0` are **dead code** affecting 90%+ of puzzles.
- **Fix**: Code change in `solve_position.py` — adaptive allocation should compound with boosts: `effective_visits = branch_visits * boost`
- **Impact**: High — corner life-and-death puzzles (30-40% of corpus) receive no extra analysis depth

### S-2: t_bad / delta_threshold Classification Gap
- **Identified by**: EA, TS-2
- **Issue**: Moves with winrate delta 0.08-0.15 trigger refutation tree generation but are classified NEUTRAL (not BM). Creates inconsistent teaching: "Wrong" refutation branch on a move the system doesn't classify as bad.
- **Fix**: Lower `t_bad` from 0.15 to 0.12 to narrow the gap

### S-3: Depth Minimum Coherence
- **Identified by**: TS-5, TS-26
- **Issue**: `entry.solution_min_depth=2`, `curated_pruning.min_depth=2`, but `tree_validation.depth_base=3`. Tree can terminate at depth 2 then fail validation.
- **Fix**: Align all to min_depth=3

### S-4: Visit Hierarchy Inversion
- **Identified by**: ENG visit budget analysis
- **Issue**: `refutation_visits (100) < continuation_visits (125) < forced_move_visits (125)`. Refutation evaluation is adversarial and needs MORE visits than continuation.
- **Correct hierarchy**: `forced ≤ continuation < refutation ≤ branch` → `125 ≤ 200 < 200 ≤ 500`

## 5. Rejected Expert Recommendations (with rationale)

| R-ID | Recommendation | Rejected By | Rationale |
|------|----------------|-------------|-----------|
| R-10 | `deep_enrich.visits` 2000→4000-8000 | TS, ENG | b18@2000 is past convergence knee for tsumego with allowMoves restriction. Doubling would add ~100% compute for <0.5% accuracy improvement. |
| R-14 | `delta_threshold` 0.08→0.10-0.15 | TS, ENG | Would REDUCE refutation coverage — fewer wrong moves get refutation trees. 0.08 is correctly calibrated for teaching value. |
| R-15 | Quick model b10→b18 | TS, ENG | T0 is a policy-only screen at 50 visits. b10 adequate for top-20 screening. b18 would be 5x more expensive for marginal benefit. |
| R-16 | T3 referee 5000→8000-15000 | TS, ENG | b28@5000 is fully converged for tsumego. Additional visits add latency with zero accuracy gain. |
| — | `t_good` 0.02 (EA) | TS, ENG | At b18@500v noise floor. Would cause false negatives on correct moves. 0.03 provides 1% margin over noise. |

## 6. Planner Recommendations

1. **Config-only changes (14 parameters)**: R-1 through R-13 (excluding R-10, R-14-R-16) are pure config value changes in `katago-enrichment.json`. No code changes needed. Low risk, high accuracy impact.

2. **Code fix for adaptive boost override (S-1)**: Must be addressed in `solve_position.py`. Without this fix, corner_visit_boost and ladder_visit_boost are dead code. This is a Level 2 correction (1-2 files, explicit behavior change).

3. **Depth minimum alignment (S-3)**: Three values need to change together: `entry.solution_min_depth`, `curated_pruning.min_depth`, and potentially `tree_validation.depth_base`. Config-only.

4. **Phased rollout recommended**: Group 1 (zero-compute changes: R-1, R-2, R-3, R-4, R-5, R-6, R-7, R-8) → Group 2 (visit budget changes: R-9, R-11, R-12, R-13) → Group 3 (code fix: S-1) → Group 4 (calibration: R-18).

## 7. Confidence and Risk

- **Planning Confidence Score**: 82 (high internal evidence from 4 experts, clear calibration history in changelog, well-documented architecture)
- **Risk Level**: medium (visit budget changes affect compute cost; threshold changes affect classification accuracy)
- **Research invocation justified**: Yes — external pattern comparison materially affected option quality (convergence curves, MCTS behavior)
